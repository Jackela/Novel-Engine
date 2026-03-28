"""Canonical context pack assembled from workflow, memory, and story state."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.contexts.narrative.application.services.story_pipeline_context import (
    StoryWorkflowContext,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    PacingLedgerEntry,
    PromiseLedgerEntry,
    RelationshipSnapshot,
    StoryOutlineChapter,
    StoryPromise,
    StrandLedgerEntry,
)


@dataclass(slots=True)
class StoryContextPack:
    """Convenience projection for stage services that need normalized story context."""

    target_chapters: int
    active_characters: list[str] = field(default_factory=list)
    outline_chapters: dict[int, StoryOutlineChapter] = field(default_factory=dict)
    recent_chapter_summaries: list[str] = field(default_factory=list)
    unresolved_hooks: list[str] = field(default_factory=list)
    story_promises: list[StoryPromise] = field(default_factory=list)
    unresolved_promises: list[PromiseLedgerEntry] = field(default_factory=list)
    relationship_states: list[RelationshipSnapshot] = field(default_factory=list)
    pacing_entries: list[PacingLedgerEntry] = field(default_factory=list)
    strand_entries: list[StrandLedgerEntry] = field(default_factory=list)
    world_rules: list[str] = field(default_factory=list)
    revision_notes: list[str] = field(default_factory=list)

    @classmethod
    def from_context(cls, ctx: StoryWorkflowContext) -> StoryContextPack:
        outline = ctx.workflow.outline
        outline_chapters = (
            {chapter.chapter_number: chapter for chapter in outline.chapters}
            if outline is not None
            else {}
        )
        return cls(
            target_chapters=ctx.resolve_target_chapters(ctx.workflow.target_chapters),
            active_characters=list(ctx.memory.active_characters),
            outline_chapters=outline_chapters,
            recent_chapter_summaries=[
                summary.summary for summary in ctx.memory.chapter_summaries[-5:]
            ],
            unresolved_hooks=[
                entry.hook
                for entry in ctx.memory.hook_ledger
                if entry.hook and not entry.surfaced
            ],
            story_promises=list(ctx.memory.story_promises),
            unresolved_promises=[
                entry for entry in ctx.memory.promise_ledger if not entry.surfaced
            ],
            relationship_states=list(ctx.memory.relationship_states),
            pacing_entries=list(ctx.memory.pacing_ledger),
            strand_entries=list(ctx.memory.strand_ledger),
            world_rules=[entry.rule for entry in ctx.memory.world_rules if entry.rule],
            revision_notes=list(ctx.memory.revision_notes),
        )

    def outline_for_chapter(self, chapter_number: int) -> StoryOutlineChapter | None:
        """Return the normalized outline entry for a chapter number."""
        return self.outline_chapters.get(chapter_number)


ContextPack = StoryContextPack


__all__ = ["ContextPack", "StoryContextPack"]
