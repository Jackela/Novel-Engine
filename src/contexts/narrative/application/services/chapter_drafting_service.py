"""Chapter drafting stage for the typed story workflow."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, cast

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationResult,
    TextGenerationTask,
)
from src.contexts.narrative.application.services.story_context_pack import (
    StoryContextPack,
)
from src.contexts.narrative.application.services.story_pipeline_context import (
    StoryWorkflowContext,
)
from src.contexts.narrative.application.services.story_workflow_support import (
    character_names,
    character_profile,
    ensure_character_anchor,
    ensure_hook,
    ensure_motivation_anchor,
    ensure_payoff_anchor,
    ensure_relationship_anchor,
    normalize_scene_type,
    outline_chapter_for_number,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    CharacterStateSnapshot,
    DraftFailureArtifact,
    HookLedgerEntry,
    PacingLedgerEntry,
    PayoffBeat,
    PromiseLedgerEntry,
    RelationshipSnapshot,
    StoryChapterMemorySummary,
    StrandLedgerEntry,
    TimelineLedgerEntry,
    utcnow_iso,
)
from src.contexts.narrative.domain.entities.chapter import Chapter
from src.contexts.narrative.domain.entities.scene import Scene
from src.contexts.narrative.domain.events.story_events import ChapterAdded
from src.contexts.narrative.domain.types import SceneType


class DraftChapterFailure(ValueError):
    """Structured draft failure that preserves the invalid payload for playback."""

    def __init__(
        self,
        *,
        chapter_number: int,
        failure_code: str,
        message: str,
        raw_text: str,
        raw_payload: dict[str, Any],
        normalized_payload: dict[str, Any],
        validation_errors: list[str],
        source_provider: str,
        source_model: str,
    ) -> None:
        super().__init__(message)
        self.chapter_number = chapter_number
        self.failure_code = failure_code
        self.message = message
        self.raw_text = raw_text
        self.raw_payload = raw_payload
        self.normalized_payload = normalized_payload
        self.validation_errors = validation_errors
        self.source_provider = source_provider
        self.source_model = source_model
        self.details = {
            "chapter_number": chapter_number,
            "failure_code": failure_code,
            "failure_message": message,
            "raw_text": raw_text,
            "raw_payload": deepcopy(raw_payload),
            "normalized_payload": deepcopy(normalized_payload),
            "validation_errors": list(validation_errors),
            "source_provider": source_provider,
            "source_model": source_model,
            "manuscript_preserved": True,
        }


class ChapterDraftingService:
    """Draft chapters and keep memory ledgers synchronized."""

    async def draft(
        self,
        ctx: StoryWorkflowContext,
        *,
        target_chapters: int | None = None,
    ) -> tuple[int, bool]:
        outline = ctx.workflow.outline
        if outline is None:
            raise ValueError("Outline must be generated before drafting chapters")
        if not outline.chapters:
            raise ValueError("Outline does not contain chapters")

        pack = StoryContextPack.from_context(ctx)
        target_count = ctx.resolve_target_chapters(
            target_chapters if target_chapters is not None else ctx.workflow.target_chapters
        )
        target_count = min(target_count, len(outline.chapters))
        start_number = ctx.story.chapter_count + 1
        if start_number > target_count:
            return ctx.story.chapter_count, True

        for chapter_number in range(start_number, target_count + 1):
            chapter_spec = outline_chapter_for_number(outline, chapter_number)
            chapter_spec = {
                **chapter_spec,
                "summary": self._surface_promise_in_summary(
                    str(chapter_spec.get("summary", "")),
                    chapter_spec,
                ),
            }
            focus_character = self._select_focus_character(ctx, chapter_number)
            focus_motivation = self._focus_character_motivation(ctx, focus_character)
            previous_hook = self._previous_hook(ctx, pack)
            relationship_target = self._select_relationship_target(
                ctx, chapter_number, focus_character
            )
            relationship_status = self._relationship_status(chapter_number)
            scene_result = await self._generate_chapter_scenes(
                ctx=ctx,
                chapter_spec=chapter_spec,
                focus_character=focus_character,
                focus_motivation=focus_motivation,
                previous_hook=previous_hook,
            )
            ctx.record_generation_trace(scene_result)
            try:
                scenes = self._extract_scenes(scene_result, chapter_spec)
            except DraftChapterFailure as exc:
                self._record_draft_failure_artifact(
                    ctx=ctx,
                    chapter_spec=chapter_spec,
                    result=scene_result,
                    failure=exc,
                )
                raise
            chapter = Chapter(
                story_id=str(ctx.story.id),
                chapter_number=chapter_number,
                title=str(chapter_spec["title"]),
                summary=str(chapter_spec["summary"]),
            )
            chapter.metadata.update(
                {
                    "chapter_number": chapter_number,
                    "focus_character": focus_character,
                    "focus_motivation": focus_motivation,
                    "timeline_day": chapter_number,
                    "outline_hook": str(chapter_spec.get("hook", "")),
                    "promise": str(chapter_spec.get("promise", "")),
                    "pacing_phase": str(chapter_spec.get("pacing_phase", "")),
                    "narrative_strand": str(chapter_spec.get("narrative_strand", "")),
                    "primary_strand": str(
                        chapter_spec.get(
                            "primary_strand", chapter_spec.get("narrative_strand", "")
                        )
                    ),
                    "secondary_strand": str(
                        chapter_spec.get("secondary_strand", "")
                    ).strip(),
                    "chapter_objective": str(
                        chapter_spec.get("chapter_objective", "")
                    ),
                    "promised_payoff": str(
                        chapter_spec.get(
                            "promised_payoff", chapter_spec.get("promise", "")
                        )
                    ),
                    "hook_strength": int(chapter_spec.get("hook_strength", 0) or 0),
                    "previous_hook": previous_hook,
                    "relationship_target": relationship_target,
                    "relationship_status": relationship_status,
                    "drafted_at": utcnow_iso(),
                }
            )
            self._apply_scene_payload(
                chapter=chapter,
                scenes=scenes,
                focus_character=focus_character,
                focus_motivation=focus_motivation,
                previous_hook=previous_hook,
                relationship_target=relationship_target,
                relationship_status=relationship_status,
                hook=str(chapter_spec.get("hook", "")),
            )
            ctx.story.chapters.append(chapter)
            ctx.story.current_chapter_id = str(chapter.id)
            ctx.story.updated_at = datetime.utcnow()
            ctx.story.add_event(
                ChapterAdded(
                    aggregate_id=str(ctx.story.id),
                    chapter_id=str(chapter.id),
                    chapter_number=chapter.chapter_number,
                    title=chapter.title,
                )
            )
            self._append_memory_entry(
                ctx=ctx,
                chapter=chapter,
                focus_character=focus_character,
                focus_motivation=focus_motivation,
                relationship_target=relationship_target,
                relationship_status=relationship_status,
                hook=str(chapter_spec.get("hook", "")),
                promise=str(chapter_spec.get("promise", "")),
                pacing_phase=str(chapter_spec.get("pacing_phase", "")),
                narrative_strand=str(chapter_spec.get("narrative_strand", "")),
                chapter_objective=str(chapter_spec.get("chapter_objective", "")),
                hook_strength=int(chapter_spec.get("hook_strength", 0) or 0),
            )

        ctx.workflow.drafted_chapters = ctx.story.chapter_count
        ctx.workflow.status = "drafted"
        return ctx.story.chapter_count, False

    def synchronize_memory(self, ctx: StoryWorkflowContext) -> None:
        """Rebuild chapter-level memory ledgers from the current story snapshot."""
        ctx.workflow.chapter_memory.clear()
        ctx.memory.chapter_summaries.clear()
        ctx.memory.timeline_ledger.clear()
        ctx.memory.hook_ledger.clear()
        ctx.memory.promise_ledger.clear()
        ctx.memory.pacing_ledger.clear()
        ctx.memory.strand_ledger.clear()
        ctx.memory.character_states.clear()
        ctx.memory.relationship_states.clear()

        for chapter in ctx.story.chapters:
            focus_character = str(chapter.metadata.get("focus_character", "")).strip()
            focus_motivation = str(
                chapter.metadata.get("focus_motivation", "")
            ).strip()
            relationship_target = str(
                chapter.metadata.get("relationship_target", "")
            ).strip()
            relationship_status = str(
                chapter.metadata.get("relationship_status", "")
            ).strip()
            hook = str(chapter.metadata.get("outline_hook", "")).strip()
            promise = str(chapter.metadata.get("promise", "")).strip()
            pacing_phase = str(chapter.metadata.get("pacing_phase", "")).strip()
            narrative_strand = str(chapter.metadata.get("narrative_strand", "")).strip()
            self._append_memory_entry(
                ctx=ctx,
                chapter=chapter,
                focus_character=focus_character,
                focus_motivation=focus_motivation,
                relationship_target=relationship_target,
                relationship_status=relationship_status,
                hook=hook,
                promise=promise,
                pacing_phase=pacing_phase,
                narrative_strand=narrative_strand,
                chapter_objective=str(
                    chapter.metadata.get("chapter_objective", "")
                ).strip(),
                hook_strength=int(chapter.metadata.get("hook_strength", 0) or 0),
            )

    async def _generate_chapter_scenes(
        self,
        *,
        ctx: StoryWorkflowContext,
        chapter_spec: dict[str, Any],
        focus_character: str,
        focus_motivation: str,
        previous_hook: str,
    ) -> TextGenerationResult:
        task = TextGenerationTask(
            step="chapter_scenes",
            system_prompt=(
                "You write coherent chapter scenes for a long-form Chinese web novel. "
                "Keep the pacing commercial, the continuity stable, and the hook strong. "
                "Use scene_type values from: opening, narrative, dialogue, action, "
                "decision, climax, ending."
            ),
            user_prompt=(
                f"Story title: {ctx.story.title}\n"
                f"Chapter number: {chapter_spec['chapter_number']}\n"
                f"Chapter title: {chapter_spec['title']}\n"
                f"Chapter summary: {chapter_spec['summary']}\n"
                f"Chapter hook: {chapter_spec.get('hook', '')}\n"
                f"Previous hook to resolve: {previous_hook}\n"
                f"Focus character: {focus_character}\n"
                f"Focus motivation: {focus_motivation}\n"
                f"Premise: {ctx.workflow.premise}"
            ),
            response_schema={
                "scenes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "scene_type": {"type": "string"},
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                        },
                    },
                }
            },
            temperature=0.5,
            metadata={
                "story_id": str(ctx.story.id),
                "chapter_number": chapter_spec["chapter_number"],
                "chapter_title": chapter_spec["title"],
                "focus_character": focus_character,
                "focus_motivation": focus_motivation,
                "previous_hook": previous_hook,
                "outline_hook": chapter_spec.get("hook", ""),
                "previous_summary": self._previous_chapter_summary(ctx),
            },
        )
        return await ctx.provider.generate_structured(task)

    def _extract_scenes(
        self,
        result: TextGenerationResult,
        chapter_spec: dict[str, Any],
    ) -> list[dict[str, Any]]:
        scenes = result.content.get("scenes")
        if not isinstance(scenes, list) or not scenes:
            raise DraftChapterFailure(
                chapter_number=int(chapter_spec["chapter_number"]),
                failure_code="DRAFT_VALIDATION_ERROR",
                message=f"Chapter {chapter_spec['chapter_number']} did not contain scenes",
                raw_text=result.raw_text,
                raw_payload=deepcopy(result.content),
                normalized_payload={"scenes": []},
                validation_errors=[
                    f"Chapter {chapter_spec['chapter_number']} did not contain scenes"
                ],
                source_provider=result.provider,
                source_model=result.model,
            )

        normalized: list[dict[str, Any]] = []
        for index, scene in enumerate(scenes, start=1):
            if not isinstance(scene, dict):
                raise DraftChapterFailure(
                    chapter_number=int(chapter_spec["chapter_number"]),
                    failure_code="DRAFT_VALIDATION_ERROR",
                    message="Scene payload must be an object",
                    raw_text=result.raw_text,
                    raw_payload=deepcopy(result.content),
                    normalized_payload={"scenes": normalized},
                    validation_errors=[f"Scene {index} payload must be an object"],
                    source_provider=result.provider,
                    source_model=result.model,
                )
            content = str(scene.get("content", "")).strip()
            scene_type = normalize_scene_type(scene.get("scene_type", "narrative"))
            title = str(scene.get("title", "")).strip() or (
                f"{chapter_spec['title']} - Scene {index}"
            )
            if not content:
                raise DraftChapterFailure(
                    chapter_number=int(chapter_spec["chapter_number"]),
                    failure_code="DRAFT_VALIDATION_ERROR",
                    message="Scene content cannot be empty",
                    raw_text=result.raw_text,
                    raw_payload=deepcopy(result.content),
                    normalized_payload={"scenes": normalized},
                    validation_errors=[f"Scene {index} content cannot be empty"],
                    source_provider=result.provider,
                    source_model=result.model,
                )
            normalized.append(
                {
                    "scene_type": scene_type,
                    "title": title,
                    "content": content,
                }
            )
        return normalized

    def _record_draft_failure_artifact(
        self,
        *,
        ctx: StoryWorkflowContext,
        chapter_spec: dict[str, Any],
        result: TextGenerationResult,
        failure: DraftChapterFailure,
    ) -> DraftFailureArtifact:
        parent_artifact_ids = [
            entry.artifact_id
            for entry in (
                ctx.latest_artifact_entry("blueprint"),
                ctx.latest_artifact_entry("outline"),
            )
            if entry is not None
        ]
        artifact = DraftFailureArtifact(
            story_id=str(ctx.story.id),
            stage_name="draft",
            chapter_number=failure.chapter_number or int(chapter_spec["chapter_number"]),
            failure_code=failure.failure_code,
            failure_message=failure.message,
            raw_text=result.raw_text,
            raw_payload=deepcopy(result.content),
            normalized_payload=deepcopy(failure.normalized_payload),
            validation_errors=list(failure.validation_errors),
            version=ctx.artifact_version("draft_failure"),
            source_run_id=ctx.workflow.current_run_id,
            source_provider=result.provider,
            source_model=result.model,
        )
        ctx.record_artifact(
            kind="draft_failure",
            payload=artifact.to_dict(),
            version=artifact.version,
            generated_at=artifact.generated_at,
            source_stage="draft",
            source_provider=artifact.source_provider,
            source_model=artifact.source_model,
            parent_artifact_ids=parent_artifact_ids,
            artifact_id=artifact.artifact_id,
        )
        return artifact

    def _apply_scene_payload(
        self,
        *,
        chapter: Chapter,
        scenes: list[dict[str, Any]],
        focus_character: str,
        focus_motivation: str,
        previous_hook: str,
        relationship_target: str,
        relationship_status: str,
        hook: str,
    ) -> None:
        for index, scene_payload in enumerate(scenes, start=1):
            content = str(scene_payload["content"]).strip()
            if index == 1 and focus_character:
                content = ensure_character_anchor(content, focus_character)
            if index == 1 and focus_motivation:
                content = ensure_motivation_anchor(content, focus_motivation)
            if index == 1 and previous_hook:
                content = ensure_payoff_anchor(content, previous_hook)
            if index == min(2, len(scenes)) and relationship_target and relationship_status:
                content = ensure_relationship_anchor(
                    content,
                    focus_character,
                    relationship_target,
                    relationship_status,
                )
            if index == len(scenes):
                content = ensure_hook(content, hook)
            scene_type = cast(
                SceneType,
                normalize_scene_type(scene_payload["scene_type"]),
            )
            scene: Scene = chapter.add_scene(
                content=content,
                scene_type=scene_type,
                title=str(scene_payload["title"]),
            )
            scene.metadata.update(
                {
                    "focus_character": focus_character,
                    "focus_motivation": focus_motivation,
                    "timeline_day": chapter.chapter_number,
                    "outline_hook": hook,
                    "scene_index": index,
                }
            )

    def _append_memory_entry(
        self,
        *,
        ctx: StoryWorkflowContext,
        chapter: Chapter,
        focus_character: str,
        focus_motivation: str,
        relationship_target: str,
        relationship_status: str,
        hook: str,
        promise: str,
        pacing_phase: str,
        narrative_strand: str,
        chapter_objective: str,
        hook_strength: int,
    ) -> None:
        summary = StoryChapterMemorySummary(
            chapter_number=chapter.chapter_number,
            title=chapter.title,
            summary=chapter.summary or "",
            focus_character=focus_character,
            focus_motivation=focus_motivation,
            hook=hook,
            promise=promise,
            pacing_phase=pacing_phase,
            narrative_strand=narrative_strand,
        )
        ctx.memory.chapter_summaries.append(summary)
        ctx.workflow.chapter_memory.append(summary)
        ctx.memory.timeline_ledger.append(
            TimelineLedgerEntry(
                chapter_number=chapter.chapter_number,
                timeline_day=int(chapter.metadata.get("timeline_day", chapter.chapter_number)),
                summary=chapter.summary or "",
            )
        )
        current_scene_text = chapter.current_scene.content if chapter.current_scene else ""
        ctx.memory.hook_ledger.append(
            HookLedgerEntry(
                chapter_number=chapter.chapter_number,
                hook=hook,
                surfaced=bool(hook)
                and (
                    (hook.lower() in current_scene_text.lower())
                    or current_scene_text.rstrip().endswith("?")
                ),
            )
        )
        current_summary_text = " ".join(
            part
            for part in (
                chapter.summary or "",
                current_scene_text,
            )
            if part
        ).lower()
        ctx.memory.promise_ledger.append(
            PromiseLedgerEntry(
                chapter_number=chapter.chapter_number,
                promise=promise,
                surfaced=bool(promise) and promise.lower() in current_summary_text,
                promise_id=f"{ctx.story.id}:{chapter.chapter_number}",
                strand=narrative_strand,
                chapter_objective=chapter_objective,
                due_by_chapter=min(
                    ctx.resolve_target_chapters(ctx.workflow.target_chapters),
                    chapter.chapter_number + 3,
                ),
                status=(
                    "paid_off"
                    if bool(promise) and promise.lower() in current_summary_text
                    else "open"
                ),
            )
        )
        if promise and promise.lower() in current_summary_text:
            ctx.memory.payoff_beats.append(
                PayoffBeat(
                    promise_id=f"{ctx.story.id}:{chapter.chapter_number}",
                    chapter_number=chapter.chapter_number,
                    payoff_text=current_scene_text[:240],
                    strength=min(100, max(0, self._tension_score(chapter))),
                )
            )
        ctx.memory.pacing_ledger.append(
            PacingLedgerEntry(
                chapter_number=chapter.chapter_number,
                phase=pacing_phase,
                signature=self._pacing_signature(chapter, pacing_phase),
                tension=self._tension_score(chapter),
                hook_strength=hook_strength,
                chapter_objective=chapter_objective,
            )
        )
        ctx.memory.strand_ledger.append(
            StrandLedgerEntry(
                chapter_number=chapter.chapter_number,
                strand=narrative_strand,
                status="active" if narrative_strand else "unset",
            )
        )
        role = "focus" if focus_character else "unknown"
        if focus_character:
            ctx.memory.character_states.append(
                CharacterStateSnapshot(
                    chapter_number=chapter.chapter_number,
                    name=focus_character,
                    motivation=focus_motivation,
                    role=role,
                )
            )
        if focus_character and relationship_target and relationship_status:
            ctx.memory.relationship_states.append(
                RelationshipSnapshot(
                    chapter_number=chapter.chapter_number,
                    source=focus_character,
                    target=relationship_target,
                    status=relationship_status,
                )
            )

    def _select_focus_character(
        self,
        ctx: StoryWorkflowContext,
        chapter_number: int,
    ) -> str:
        blueprint = ctx.workflow.blueprint
        if blueprint is not None:
            names = character_names(blueprint.character_bible)
            if names:
                return str(names[(chapter_number - 1) % len(names)])
        return str(ctx.story.author_id)

    def _focus_character_motivation(
        self,
        ctx: StoryWorkflowContext,
        focus_character: str,
        chapter: Chapter | None = None,
    ) -> str:
        if chapter is not None:
            motivation = str(chapter.metadata.get("focus_motivation", "")).strip()
            if motivation:
                return motivation

        blueprint = ctx.workflow.blueprint
        if blueprint is None:
            return ""
        profile = character_profile(blueprint.character_bible, focus_character)
        motivation = str(profile.get("motivation", "")).strip()
        return motivation

    def _select_relationship_target(
        self,
        ctx: StoryWorkflowContext,
        chapter_number: int,
        focus_character: str,
    ) -> str:
        candidates = [
            name for name in ctx.memory.active_characters if name and name != focus_character
        ]
        if not candidates:
            return ""
        return str(candidates[(chapter_number - 1) % len(candidates)])

    @staticmethod
    def _relationship_status(chapter_number: int) -> str:
        statuses = ["allies", "tense allies", "rivals"]
        return str(statuses[(chapter_number - 1) % len(statuses)])

    def _previous_chapter_summary(self, ctx: StoryWorkflowContext) -> str:
        if not ctx.story.chapters:
            return ""
        previous = ctx.story.chapters[-1]
        return previous.summary or ""

    @staticmethod
    def _surface_promise_in_summary(summary: str, chapter_spec: dict[str, Any]) -> str:
        text = str(summary).strip()
        promise = str(
            chapter_spec.get("promise", chapter_spec.get("promised_payoff", ""))
        ).strip()
        if not promise:
            return text
        if promise.lower() in text.lower():
            return text
        if text:
            return f"{text} Promise: {promise}"
        return promise

    def _previous_hook(self, ctx: StoryWorkflowContext, pack: StoryContextPack) -> str:
        if pack.unresolved_promises:
            return str(pack.unresolved_promises[-1].promise)
        if not ctx.story.chapters:
            return ""
        previous = ctx.story.chapters[-1]
        return str(previous.metadata.get("outline_hook", "")).strip()

    @staticmethod
    def _pacing_signature(chapter: Chapter, pacing_phase: str) -> str:
        scene_types = "-".join(scene.scene_type for scene in chapter.scenes)
        if pacing_phase:
            return f"{pacing_phase}:{scene_types}"
        return scene_types

    @staticmethod
    def _tension_score(chapter: Chapter) -> int:
        score = 0
        for scene in chapter.scenes:
            if scene.scene_type in {"action", "climax"}:
                score += 2
            elif scene.scene_type in {"decision", "ending"}:
                score += 1
        return score


__all__ = ["ChapterDraftingService"]
