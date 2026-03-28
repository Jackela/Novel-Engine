"""Revision stage for the typed story workflow."""

from __future__ import annotations

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationResult,
    TextGenerationTask,
)
from src.contexts.narrative.application.services.chapter_drafting_service import (
    ChapterDraftingService,
)
from src.contexts.narrative.application.services.story_pipeline_context import (
    StoryWorkflowContext,
)
from src.contexts.narrative.application.services.story_workflow_support import (
    ensure_hook,
    ensure_payoff_anchor,
    outline_chapter_for_number,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    StoryReviewArtifact,
    StoryReviewIssue,
)
from src.contexts.narrative.domain.entities.chapter import Chapter


class StoryRevisionService:
    """Apply targeted repairs based on review issues."""

    def __init__(self, drafting_service: ChapterDraftingService) -> None:
        self._drafting_service = drafting_service

    async def revise(
        self,
        ctx: StoryWorkflowContext,
        review: StoryReviewArtifact,
    ) -> list[str]:
        issues = review.issues
        revision_notes = await self._generate_revision_notes(ctx, issues)
        repair_notes = await self._repair_story(ctx, issues)
        revision_notes.extend(repair_notes)
        ctx.workflow.revision_notes = revision_notes
        ctx.workflow.revision_history = ctx.workflow.revision_history + [
            {
                "timestamp": ctx.workflow.last_updated_at,
                "notes": revision_notes,
                "issue_count": len(issues),
            }
        ]
        ctx.workflow.status = "revised"
        ctx.memory.revision_notes = revision_notes
        return revision_notes

    async def _generate_revision_notes(
        self,
        ctx: StoryWorkflowContext,
        issues: list[StoryReviewIssue],
    ) -> list[str]:
        task = TextGenerationTask(
            step="revision",
            system_prompt=(
                "You repair story structure, continuity, pacing, and hooks. "
                "Return concise revision notes."
            ),
            user_prompt=(
                f"Story title: {ctx.story.title}\n"
                f"Review issues: {[issue.to_dict() for issue in issues]}\n"
                "Revision target: strengthen continuity, pacing, and hooks."
            ),
            response_schema={
                "revision_notes": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
            temperature=0.2,
            metadata={
                "story_id": str(ctx.story.id),
                "issue_count": len(issues),
                "issues": [issue.to_dict() for issue in issues],
                "chapter_count": ctx.story.chapter_count,
            },
        )
        result = await ctx.provider.generate_structured(task)
        ctx.record_generation_trace(result)
        return self._extract_revision_notes(result)

    def _extract_revision_notes(
        self,
        result: TextGenerationResult,
    ) -> list[str]:
        revision_notes = result.content.get("revision_notes")
        if not isinstance(revision_notes, list) or not revision_notes:
            raise ValueError("Revision payload missing revision_notes")
        notes = [str(note).strip() for note in revision_notes if str(note).strip()]
        if not notes:
            raise ValueError("Revision notes cannot be empty")
        return notes

    async def _repair_story(
        self,
        ctx: StoryWorkflowContext,
        issues: list[StoryReviewIssue],
    ) -> list[str]:
        repair_notes: list[str] = []
        issue_map: dict[str, list[StoryReviewIssue]] = {}
        for issue in issues:
            if issue.location is None:
                continue
            issue_map.setdefault(issue.location, []).append(issue)

        outline = ctx.workflow.outline
        for chapter in ctx.story.chapters:
            location = f"chapter-{chapter.chapter_number}"
            chapter_issues = issue_map.get(location, [])
            if not chapter_issues:
                continue
            chapter_spec = (
                outline_chapter_for_number(outline, chapter.chapter_number)
                if outline is not None
                else {
                    "chapter_number": chapter.chapter_number,
                    "title": chapter.title,
                    "summary": chapter.summary or "",
                    "hook": str(chapter.metadata.get("outline_hook", "")),
                }
            )
            issue_codes = {issue.code for issue in chapter_issues}

            if not chapter.summary or not chapter.summary.strip():
                summary = str(chapter_spec.get("summary", "")).strip()
                if summary:
                    chapter.summary = summary
                    repair_notes.append(
                        f"Restored the summary for chapter {chapter.chapter_number}."
                    )

            focus_character = str(chapter.metadata.get("focus_character", "")).strip()
            if (
                focus_character
                and ctx.memory.active_characters
                and focus_character not in set(ctx.memory.active_characters)
            ):
                focus_character = ctx.memory.active_characters[
                    (chapter.chapter_number - 1) % len(ctx.memory.active_characters)
                ]
                chapter.metadata["focus_character"] = focus_character
                repair_notes.append(
                    f"Reassigned the focus character for chapter {chapter.chapter_number}."
                )

            if not focus_character and ctx.memory.active_characters:
                focus_character = ctx.memory.active_characters[
                    (chapter.chapter_number - 1) % len(ctx.memory.active_characters)
                ]
                chapter.metadata["focus_character"] = focus_character
                repair_notes.append(
                    f"Restored the focus character for chapter {chapter.chapter_number}."
                )

            focus_motivation = str(chapter.metadata.get("focus_motivation", "")).strip()
            if not focus_motivation:
                for character_state in ctx.memory.character_states:
                    if (
                        character_state.chapter_number == chapter.chapter_number
                        and character_state.name == focus_character
                    ):
                        focus_motivation = character_state.motivation
                        chapter.metadata["focus_motivation"] = focus_motivation
                        break

            relationship_target = str(
                chapter.metadata.get("relationship_target", "")
            ).strip()
            relationship_status = str(
                chapter.metadata.get("relationship_status", "")
            ).strip()
            if (not relationship_target or not relationship_status) and ctx.memory.relationship_states:
                for relationship_state in ctx.memory.relationship_states:
                    if (
                        relationship_state.chapter_number == chapter.chapter_number
                        and relationship_state.source == focus_character
                    ):
                        relationship_target = relationship_state.target
                        relationship_status = relationship_state.status
                        chapter.metadata["relationship_target"] = relationship_target
                        chapter.metadata["relationship_status"] = relationship_status
                        repair_notes.append(
                            f"Restored the relationship state for chapter {chapter.chapter_number}."
                        )
                        break

            needs_scene_regen = bool(
                issue_codes
                & {
                    "empty_chapter",
                    "empty_scene",
                    "character_drift",
                    "motivation_drift",
                    "flat_scene_stack",
                    "thin_chapter",
                    "unknown_focus_character",
                    "world_rule_conflict",
                    "relationship_drift",
                    "missing_relationship_state",
                }
            )
            if needs_scene_regen:
                scene_result = await self._drafting_service._generate_chapter_scenes(
                    ctx=ctx,
                    chapter_spec={
                        "chapter_number": chapter.chapter_number,
                        "title": chapter.title,
                        "summary": chapter.summary or str(chapter_spec.get("summary", "")),
                        "hook": str(chapter_spec.get("hook", "")),
                    },
                    focus_character=focus_character,
                    focus_motivation=focus_motivation,
                    previous_hook=str(chapter.metadata.get("previous_hook", "")).strip(),
                )
                scenes = self._drafting_service._extract_scenes(
                    scene_result,
                    {
                        "chapter_number": chapter.chapter_number,
                        "title": chapter.title,
                    },
                )
                chapter.scenes.clear()
                self._drafting_service._apply_scene_payload(
                    chapter=chapter,
                    scenes=scenes,
                    focus_character=focus_character,
                    focus_motivation=focus_motivation,
                    previous_hook=str(chapter.metadata.get("previous_hook", "")).strip(),
                    relationship_target=relationship_target,
                    relationship_status=relationship_status,
                    hook=str(chapter_spec.get("hook", "")),
                )
                ctx.record_generation_trace(scene_result)
                repair_notes.append(
                    f"Rebuilt the scene stack for chapter {chapter.chapter_number}."
                )

            if chapter.scenes and "missing_hook_payoff" in issue_codes:
                previous_hook = str(chapter.metadata.get("previous_hook", "")).strip()
                if previous_hook:
                    chapter.scenes[0].update_content(
                        ensure_payoff_anchor(chapter.scenes[0].content, previous_hook)
                    )
                    summary_text = str(chapter.summary or "").strip()
                    if previous_hook.lower() not in summary_text.lower():
                        chapter.summary = (
                            f"{summary_text} {previous_hook}".strip()
                            if summary_text
                            else previous_hook
                        )
                    promise_text = str(chapter_spec.get("promise", "")).strip()
                    if promise_text and promise_text.lower() not in str(chapter.summary).lower():
                        chapter.summary = (
                            f"{chapter.summary} {promise_text}".strip()
                            if chapter.summary
                            else promise_text
                        )
                    repair_notes.append(
                        f"Restored the hook payoff in chapter {chapter.chapter_number}."
                    )

            if chapter.metadata.get("timeline_day") != chapter.chapter_number:
                chapter.metadata["timeline_day"] = chapter.chapter_number
                repair_notes.append(
                    f"Realigned the timeline marker for chapter {chapter.chapter_number}."
                )

            if chapter.current_scene and issue_codes & {"missing_hook", "weak_hook"}:
                hook = self._repair_hook(chapter_spec, chapter)
                if hook and hook.lower() not in chapter.current_scene.content.lower():
                    chapter.metadata["outline_hook"] = hook
                    chapter.current_scene.update_content(
                        ensure_hook(chapter.current_scene.content, hook)
                    )
                    summary_text = str(chapter.summary or "").strip()
                    if hook.lower() not in summary_text.lower():
                        chapter.summary = (
                            f"{summary_text} {hook}".strip()
                            if summary_text
                            else hook
                        )
                    repair_notes.append(
                        f"Strengthened the hook for chapter {chapter.chapter_number}."
                    )

            if chapter.current_scene and "missing_outline_hook" in issue_codes:
                hook = self._repair_hook(chapter_spec, chapter)
                if outline is not None:
                    for outline_chapter in outline.chapters:
                        if outline_chapter.chapter_number == chapter.chapter_number:
                            outline_chapter.hook = hook
                            break
                chapter.metadata["outline_hook"] = hook
                chapter.current_scene.update_content(
                    ensure_hook(chapter.current_scene.content, hook)
                )
                summary_text = str(chapter.summary or "").strip()
                if hook.lower() not in summary_text.lower():
                    chapter.summary = (
                        f"{summary_text} {hook}".strip() if summary_text else hook
                    )
                repair_notes.append(
                    f"Restored an explicit outline hook for chapter {chapter.chapter_number}."
                )

            if "relationship_progression_stall" in issue_codes:
                relationship_status = str(
                    chapter.metadata.get("relationship_status", "")
                ).strip()
                if relationship_status:
                    chapter.metadata["relationship_status"] = (
                        f"{relationship_status} -> shift {chapter.chapter_number}"
                    )
                    repair_notes.append(
                        f"Advanced the relationship state for chapter {chapter.chapter_number}."
                    )

        self._drafting_service.synchronize_memory(ctx)
        return repair_notes

    @staticmethod
    def _repair_hook(chapter_spec: dict[str, str], chapter: Chapter) -> str:
        hook = str(chapter_spec.get("hook", "")).strip()
        if hook:
            return hook
        return f"What changes after {chapter.title}?"


__all__ = ["StoryRevisionService"]
