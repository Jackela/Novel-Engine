"""Publication gate stage for the typed story workflow."""

from __future__ import annotations

from src.contexts.narrative.application.services.continuity_review_service import (
    MIN_CHARACTER_SCORE,
    MIN_CONTINUITY_SCORE,
    MIN_HOOK_SCORE,
    MIN_PACING_SCORE,
    MIN_QUALITY_SCORE,
    MIN_TIMELINE_SCORE,
)
from src.contexts.narrative.application.services.story_pipeline_context import (
    StoryWorkflowContext,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    HybridReviewReport,
    utcnow_iso,
)


class StoryPublicationService:
    """Validate and publish a story that passes the quality gate."""

    def publish(
        self,
        ctx: StoryWorkflowContext,
        report: HybridReviewReport,
    ) -> None:
        if not report.ready_for_publish:
            raise ValueError("Story does not pass the publication quality gate")
        if report.quality_score < MIN_QUALITY_SCORE:
            raise ValueError("Story quality score is below the publication threshold")
        if any(issue.severity == "warning" for issue in report.issues):
            raise ValueError("Story still has unresolved review warnings")
        if any(issue.severity == "blocker" for issue in report.issues):
            raise ValueError("Story still has unresolved review blockers")
        structural_review = report.structural_review
        semantic_review = report.semantic_review
        if structural_review is None:
            raise ValueError("Structural review is required before publication")
        if semantic_review is None:
            raise ValueError("Semantic review is required before publication")
        if structural_review.metrics.continuity_score < MIN_CONTINUITY_SCORE:
            raise ValueError("Story continuity score is below the publication threshold")
        if structural_review.metrics.pacing_score < MIN_PACING_SCORE:
            raise ValueError("Story pacing score is below the publication threshold")
        if structural_review.metrics.hook_score < MIN_HOOK_SCORE:
            raise ValueError("Story hook score is below the publication threshold")
        if structural_review.metrics.character_consistency_score < MIN_CHARACTER_SCORE:
            raise ValueError(
                "Story character consistency score is below the publication threshold"
            )
        if structural_review.metrics.timeline_consistency_score < MIN_TIMELINE_SCORE:
            raise ValueError(
                "Story timeline consistency score is below the publication threshold"
            )
        if not semantic_review.ready_for_publish:
            raise ValueError("Semantic review blocks publication")

        ctx.story.publish()
        ctx.workflow.status = "published"
        ctx.workflow.published_at = utcnow_iso()


__all__ = ["StoryPublicationService"]
