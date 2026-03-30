"""Planning stages for the typed story workflow."""

from __future__ import annotations

from typing import Any

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProviderError,
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
)
from src.contexts.narrative.application.services.story_workflow_types import (
    StoryBlueprintArtifact,
    StoryOutlineArtifact,
    StoryOutlineChapter,
    StoryPromise,
    WorldRuleLedgerEntry,
    utcnow_iso,
)


class StoryPlanningService:
    """Generate the blueprint and outline artifacts."""

    async def generate_blueprint(
        self,
        ctx: StoryWorkflowContext,
    ) -> StoryBlueprintArtifact:
        pack = StoryContextPack.from_context(ctx)
        task = TextGenerationTask(
            step="bible",
            system_prompt=(
                "You design durable long-form Chinese web novels. Return a compact "
                "world bible and character bible that can support many chapters."
            ),
            user_prompt=(
                f"Story title: {ctx.story.title}\n"
                f"Genre: {ctx.story.genre}\n"
                f"Premise: {ctx.workflow.premise}\n"
                f"Target chapters: {pack.target_chapters}\n"
                f"Tone: {ctx.workflow.tone or 'commercial web fiction'}"
            ),
            response_schema={
                "world_bible": {"type": "object"},
                "character_bible": {"type": "object"},
                "premise_summary": {"type": "string"},
            },
            temperature=0.35,
            metadata={
                "story_id": str(ctx.story.id),
                "title": ctx.story.title,
                "genre": ctx.story.genre,
                "author_id": ctx.story.author_id,
                "premise": ctx.workflow.premise,
                "tone": ctx.workflow.tone,
                "target_chapters": pack.target_chapters,
            },
        )
        result = await ctx.provider.generate_structured(task)
        blueprint = self._extract_blueprint(
            result,
            str(ctx.story.id),
            version=ctx.artifact_version("blueprint"),
        )
        ctx.workflow.blueprint = blueprint
        ctx.workflow.blueprint_generated_at = blueprint.generated_at
        ctx.workflow.status = "blueprinted"
        ctx.story.metadata["world_bible"] = blueprint.world_bible
        ctx.story.metadata["character_bible"] = blueprint.character_bible
        ctx.story.metadata["premise_summary"] = blueprint.premise_summary
        ctx.memory.active_characters = character_names(blueprint.character_bible)
        ctx.memory.world_rules = [
            WorldRuleLedgerEntry(rule=str(rule).strip(), source="blueprint")
            for rule in blueprint.world_bible.get("core_rules", [])
            if str(rule).strip()
        ]
        ctx.record_generation_trace(result)
        ctx.record_artifact(
            kind="blueprint",
            payload=blueprint.to_dict(),
            version=blueprint.version,
            generated_at=blueprint.generated_at,
            source_stage="blueprint",
            source_provider=blueprint.provider,
            source_model=blueprint.model,
        )
        return blueprint

    async def generate_outline(
        self,
        ctx: StoryWorkflowContext,
    ) -> StoryOutlineArtifact:
        blueprint = ctx.workflow.blueprint
        if blueprint is None:
            raise ValueError("Blueprint must be generated before the outline")

        pack = StoryContextPack.from_context(ctx)
        target_chapters = pack.target_chapters
        task = TextGenerationTask(
            step="outline",
            system_prompt=(
                "You design long-form Chinese web fiction outlines. Return a chapter "
                "list with stable hooks, rising tension, coherent pacing phases, "
                "explicit promises, and durable narrative strands."
            ),
            user_prompt=(
                f"Story title: {ctx.story.title}\n"
                f"Premise: {ctx.workflow.premise}\n"
                f"World bible: {blueprint.world_bible}\n"
                f"Character bible: {blueprint.character_bible}\n"
                f"Target chapters: {target_chapters}\n"
                f"Tone: {ctx.workflow.tone or 'commercial web fiction'}"
            ),
            response_schema={
                "chapters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "chapter_number": {"type": "integer"},
                            "title": {"type": "string"},
                            "summary": {"type": "string"},
                            "hook": {"type": "string"},
                            "promise": {"type": "string"},
                            "pacing_phase": {"type": "string"},
                            "narrative_strand": {"type": "string"},
                            "chapter_objective": {"type": "string"},
                            "primary_strand": {"type": "string"},
                            "secondary_strand": {"type": "string"},
                            "promised_payoff": {"type": "string"},
                            "hook_strength": {"type": "integer"},
                        },
                    },
                }
            },
            temperature=0.4,
            metadata={
                "story_id": str(ctx.story.id),
                "target_chapters": target_chapters,
                "chapter_count": ctx.story.chapter_count,
                "character_names": character_names(blueprint.character_bible),
            },
        )
        result = await ctx.provider.generate_structured(task)
        outline = self._extract_outline(
            result,
            target_chapters,
            version=ctx.artifact_version("outline"),
        )
        ctx.workflow.outline = outline
        ctx.workflow.outline_generated_at = outline.generated_at
        ctx.workflow.status = "outlined"
        ctx.memory.outline_titles = [chapter.title for chapter in outline.chapters]
        ctx.memory.story_promises = [
            StoryPromise(
                promise_id=f"{ctx.story.id}:{chapter.chapter_number}",
                chapter_number=chapter.chapter_number,
                text=chapter.promised_payoff or chapter.promise,
                strand=chapter.primary_strand or chapter.narrative_strand,
                chapter_objective=chapter.chapter_objective,
                due_by_chapter=min(target_chapters, chapter.chapter_number + 3),
            )
            for chapter in outline.chapters
            if (chapter.promised_payoff or chapter.promise)
        ]
        ctx.record_generation_trace(result)
        latest_blueprint = ctx.latest_artifact_entry("blueprint")
        ctx.record_artifact(
            kind="outline",
            payload=outline.to_dict(),
            version=outline.version,
            generated_at=outline.generated_at,
            source_stage="outline",
            source_provider=outline.provider,
            source_model=outline.model,
            parent_artifact_ids=(
                [latest_blueprint.artifact_id] if latest_blueprint is not None else []
            ),
        )
        return outline

    def _extract_blueprint(
        self,
        result: TextGenerationResult,
        story_id: str,
        *,
        version: int,
    ) -> StoryBlueprintArtifact:
        world_bible = result.content.get("world_bible")
        character_bible = result.content.get("character_bible")
        premise_summary = str(result.content.get("premise_summary", "")).strip()
        if not isinstance(world_bible, dict):
            raise ValueError("Blueprint payload missing world_bible")
        if not isinstance(character_bible, dict):
            raise ValueError("Blueprint payload missing character_bible")
        return StoryBlueprintArtifact(
            step=result.step,
            provider=result.provider,
            model=result.model,
            generated_at=utcnow_iso(),
            story_id=story_id,
            version=version,
            world_bible=world_bible,
            character_bible=character_bible,
            premise_summary=premise_summary,
        )

    def _extract_outline(
        self,
        result: TextGenerationResult,
        target_chapters: int,
        *,
        version: int,
    ) -> StoryOutlineArtifact:
        chapters = result.content.get("chapters")
        if not isinstance(chapters, list) or not chapters:
            raise ValueError("Outline payload missing chapters")

        normalized_chapters: list[StoryOutlineChapter] = []
        for index, chapter in enumerate(chapters, start=1):
            if not isinstance(chapter, dict):
                raise ValueError("Outline chapter must be an object")
            chapter_number = self._chapter_number(chapter, index)
            title = str(chapter.get("title", "")).strip() or f"Chapter {index}"
            summary = str(chapter.get("summary", "")).strip()
            hook = str(chapter.get("hook", "")).strip()
            promise = str(chapter.get("promise", "")).strip()
            pacing_phase = str(chapter.get("pacing_phase", "")).strip()
            primary_strand = str(
                chapter.get("primary_strand", chapter.get("narrative_strand", ""))
            ).strip()
            secondary_strand = str(chapter.get("secondary_strand", "")).strip() or None
            chapter_objective = str(chapter.get("chapter_objective", "")).strip()
            promised_payoff = str(
                chapter.get("promised_payoff", chapter.get("promise", ""))
            ).strip()
            hook_strength = int(chapter.get("hook_strength", 0) or 0)
            if not summary:
                raise ValueError("Outline chapter summary cannot be empty")
            normalized_chapters.append(
                StoryOutlineChapter(
                    chapter_number=chapter_number,
                    title=title,
                    summary=summary,
                    hook=hook,
                    promise=promise or promised_payoff,
                    pacing_phase=pacing_phase,
                    narrative_strand=primary_strand,
                    chapter_objective=chapter_objective,
                    primary_strand=primary_strand,
                    secondary_strand=secondary_strand,
                    promised_payoff=promised_payoff or promise,
                    hook_strength=max(0, min(100, hook_strength)),
                )
            )

        normalized_chapters.sort(key=lambda chapter: chapter.chapter_number)
        return StoryOutlineArtifact(
            step=result.step,
            provider=result.provider,
            model=result.model,
            generated_at=utcnow_iso(),
            target_chapters=target_chapters,
            version=version,
            chapters=normalized_chapters[:target_chapters],
        )

    @staticmethod
    def _chapter_number(chapter: dict[str, Any], fallback: int) -> int:
        value = chapter.get("chapter_number", fallback)
        try:
            chapter_number = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Chapter number must be an integer") from exc
        if chapter_number < 1:
            raise ValueError("Chapter number must be positive")
        return chapter_number


__all__ = ["StoryPlanningService", "TextGenerationProviderError"]
