"""Tests for the generic narrative repair strategy layer."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast

from src.contexts.narrative.application.services.narrative_repair_strategy import (
    NarrativeRepairStrategy,
)
from src.contexts.narrative.application.services.story_pipeline_context import (
    StoryWorkflowContext,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    StoryReviewIssue,
)
from src.contexts.narrative.domain.entities.chapter import Chapter


def test_narrative_repair_strategy_handles_new_cast_without_fixed_plot() -> None:
    chapter = Chapter(
        story_id="story-new-fixture",
        chapter_number=2,
        title="The Glass Kiln",
        summary="",
        metadata={},
    )
    chapter.add_scene("Professor Iona finds the kiln tally missing.")
    ctx = cast(
        StoryWorkflowContext,
        SimpleNamespace(
            story=SimpleNamespace(
                chapter_count=3,
                chapters=[
                    Chapter(
                        story_id="story-new-fixture",
                        chapter_number=1,
                        title="Arrival",
                    ),
                    chapter,
                    Chapter(
                        story_id="story-new-fixture",
                        chapter_number=3,
                        title="Aftermath",
                    ),
                ],
                metadata={},
            ),
            memory=SimpleNamespace(revision_notes=[]),
        ),
    )
    issue = StoryReviewIssue(
        code="continuity_gap",
        severity="warning",
        message="Professor Iona's kiln tally disappears before Captain Rell can pay it off.",
        location="chapter-2",
        suggestion="Carry the kiln tally through an observable consequence.",
    )

    plan, notes = NarrativeRepairStrategy().repair(ctx, [issue])

    assert plan.steps[0].chapter_number == 2
    assert "continuity_ledger" in plan.steps[0].categories
    assert "scene_anchor" in plan.steps[0].categories
    assert notes == ["Applied generic repair for continuity_gap in chapter 2."]
    assert chapter.metadata["continuity_ledger"][0]["issue_id"].startswith(
        "continuity_gap:chapter-2:"
    )
    assert chapter.metadata["repair_provenance"][0]["changed_fields"] == [
        "metadata.continuity_ledger",
        "scenes[0].content",
    ]

    repaired_text = " ".join(
        [
            plan.summary,
            plan.steps[0].intent,
            chapter.scenes[0].content,
            str(chapter.metadata),
        ]
    ).lower()
    forbidden_story_terms = (
        "april",
        "first oath",
        "archive purge",
        "blank-slate",
        "fee mark",
        "lin wei",
        "kael",
        "vane",
    )
    assert not any(term in repaired_text for term in forbidden_story_terms)


def test_narrative_repair_strategy_module_has_no_legacy_story_terms() -> None:
    source = Path(
        "src/contexts/narrative/application/services/narrative_repair_strategy.py"
    ).read_text(encoding="utf-8")

    forbidden_story_terms = (
        "April",
        "First Oath",
        "Archive Purge",
        "blank-slate",
        "fee mark",
        "Lin Wei",
        "Kael",
        "Vane",
    )
    assert not any(term in source for term in forbidden_story_terms)
