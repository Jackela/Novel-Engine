"""Structural review artifact builder used by the hybrid publication gate."""

from __future__ import annotations

from src.contexts.narrative.application.services.story_context_pack import (
    StoryContextPack,
)
from src.contexts.narrative.application.services.story_pipeline_context import (
    StoryWorkflowContext,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    StoryReviewArtifact,
    StoryReviewIssue,
    StoryReviewMetrics,
    utcnow_iso,
)
from src.contexts.narrative.application.services.structural_review_service import (
    StructuralReviewService,
)

MIN_QUALITY_SCORE = 85
MIN_CONTINUITY_SCORE = 85
MIN_PACING_SCORE = 70
MIN_HOOK_SCORE = 70
MIN_CHARACTER_SCORE = 80
MIN_TIMELINE_SCORE = 80

PACING_ISSUE_CODES = {
    "missing_hook",
    "missing_outline_hook",
    "thin_chapter",
    "flat_scene_stack",
    "hook_debt",
    "missing_pacing_phase",
    "flat_pacing_signature",
    "pacing_phase_stall",
}
CHARACTER_ISSUE_CODES = {
    "character_drift",
    "unknown_focus_character",
    "missing_focus_character",
    "motivation_drift",
    "relationship_drift",
    "missing_relationship_state",
    "relationship_ledger_gap",
}
TIMELINE_ISSUE_CODES = {"timeline_regression", "non_sequential_chapter"}
HOOK_ISSUE_CODES = {"missing_hook", "missing_outline_hook", "hook_debt"}


class ContinuityReviewService:
    """Run the structural pass and emit the structural review artifact."""

    def __init__(self) -> None:
        self._structural_review = StructuralReviewService()

    def review(self, ctx: StoryWorkflowContext) -> StoryReviewArtifact:
        pack = StoryContextPack.from_context(ctx)
        structural = self._structural_review.review(ctx, pack)

        issues = structural.issues
        blocker_count = sum(1 for issue in issues if issue.severity == "blocker")
        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        metrics = self._build_metrics(issues)
        quality_score = round(
            (
                metrics.continuity_score
                + metrics.pacing_score
                + metrics.hook_score
                + metrics.character_consistency_score
                + metrics.timeline_consistency_score
            )
            / 5
        )
        ready_for_publish = (
            blocker_count == 0
            and quality_score >= MIN_QUALITY_SCORE
            and metrics.continuity_score >= MIN_CONTINUITY_SCORE
            and metrics.pacing_score >= MIN_PACING_SCORE
            and metrics.hook_score >= MIN_HOOK_SCORE
            and metrics.character_consistency_score >= MIN_CHARACTER_SCORE
            and metrics.timeline_consistency_score >= MIN_TIMELINE_SCORE
        )
        summary = (
            "Story passes the structural publication gate."
            if ready_for_publish
            else (
                "Story needs "
                f"{blocker_count} blocker(s) and {warning_count} warning(s) addressed."
            )
        )
        report = StoryReviewArtifact(
            story_id=str(ctx.story.id),
            quality_score=quality_score,
            ready_for_publish=ready_for_publish,
            summary=summary,
            version=ctx.artifact_version("review"),
            source_run_id=ctx.workflow.current_run_id,
            source_provider="system",
            source_model="structural-review-v1",
            issues=issues,
            revision_notes=list(ctx.workflow.revision_notes),
            chapter_count=ctx.story.chapter_count,
            scene_count=sum(chapter.scene_count for chapter in ctx.story.chapters),
            continuity_checks=structural.continuity_checks,
            checked_at=utcnow_iso(),
            metrics=metrics,
        )
        ctx.workflow.last_structural_review = report
        ctx.workflow.status = "reviewed"
        parent_artifact_ids = [
            entry.artifact_id
            for entry in (
                ctx.latest_artifact_entry("blueprint"),
                ctx.latest_artifact_entry("outline"),
            )
            if entry is not None
        ]
        ctx.record_artifact(
            kind="review",
            payload=report.to_dict(),
            version=report.version,
            generated_at=report.checked_at,
            source_stage="review",
            source_provider=report.source_provider,
            source_model=report.source_model,
            parent_artifact_ids=parent_artifact_ids,
            artifact_id=report.artifact_id,
        )
        return report

    def _build_metrics(self, issues: list[StoryReviewIssue]) -> StoryReviewMetrics:
        continuity_blockers = sum(
            1
            for issue in issues
            if issue.severity == "blocker" and issue.code not in PACING_ISSUE_CODES
        )
        continuity_warnings = sum(
            1
            for issue in issues
            if issue.severity == "warning" and issue.code not in PACING_ISSUE_CODES
        )
        pacing_blockers = sum(
            1
            for issue in issues
            if issue.severity == "blocker" and issue.code in PACING_ISSUE_CODES
        )
        pacing_warnings = sum(
            1
            for issue in issues
            if issue.severity == "warning" and issue.code in PACING_ISSUE_CODES
        )
        hook_blockers = sum(
            1
            for issue in issues
            if issue.severity == "blocker" and issue.code in HOOK_ISSUE_CODES
        )
        hook_warnings = sum(
            1
            for issue in issues
            if issue.severity == "warning" and issue.code in HOOK_ISSUE_CODES
        )
        character_blockers = sum(
            1
            for issue in issues
            if issue.severity == "blocker" and issue.code in CHARACTER_ISSUE_CODES
        )
        character_warnings = sum(
            1
            for issue in issues
            if issue.severity == "warning" and issue.code in CHARACTER_ISSUE_CODES
        )
        timeline_blockers = sum(
            1
            for issue in issues
            if issue.severity == "blocker" and issue.code in TIMELINE_ISSUE_CODES
        )
        timeline_warnings = sum(
            1
            for issue in issues
            if issue.severity == "warning" and issue.code in TIMELINE_ISSUE_CODES
        )

        return StoryReviewMetrics(
            continuity_score=max(
                0, 100 - continuity_blockers * 20 - continuity_warnings * 6
            ),
            pacing_score=max(0, 100 - pacing_blockers * 20 - pacing_warnings * 10),
            hook_score=max(0, 100 - hook_blockers * 25 - hook_warnings * 15),
            character_consistency_score=max(
                0, 100 - character_blockers * 25 - character_warnings * 10
            ),
            timeline_consistency_score=max(
                0, 100 - timeline_blockers * 25 - timeline_warnings * 10
            ),
        )


__all__ = [
    "ContinuityReviewService",
    "MIN_CHARACTER_SCORE",
    "MIN_CONTINUITY_SCORE",
    "MIN_HOOK_SCORE",
    "MIN_PACING_SCORE",
    "MIN_QUALITY_SCORE",
    "MIN_TIMELINE_SCORE",
]
