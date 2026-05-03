"""Merge structural and semantic review into a single publication gate."""

from __future__ import annotations

from src.contexts.narrative.application.services.semantic_review_service import (
    MIN_PLOT_CLARITY_SCORE,
    MIN_READER_PULL_SCORE,
    MIN_SEMANTIC_SCORE,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    HybridReviewReport,
    SemanticReviewArtifact,
    StoryReviewArtifact,
    StoryReviewIssue,
    utcnow_iso,
)


class HybridPublicationGate:
    """Combine structural and semantic review into a single canonical report."""

    def evaluate(
        self,
        *,
        story_id: str,
        run_id: str | None,
        structural_review: StoryReviewArtifact,
        semantic_review: SemanticReviewArtifact,
        version: int,
    ) -> HybridReviewReport:
        blocked_by: list[str] = []
        structural_gate_passed = bool(structural_review.ready_for_publish)
        semantic_gate_passed = bool(semantic_review.ready_for_publish)
        if not structural_gate_passed:
            blocked_by.append("structural")
        if not semantic_gate_passed:
            blocked_by.append("semantic")

        issues = list(structural_review.issues) + list(semantic_review.issues)
        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        quality_score = round(
            (structural_review.quality_score + semantic_review.semantic_score) / 2
        )
        publish_gate_passed = (
            structural_gate_passed
            and semantic_gate_passed
            and warning_count == 0
            and not any(issue.severity == "blocker" for issue in issues)
            and semantic_review.metrics.semantic_score >= MIN_SEMANTIC_SCORE
            and semantic_review.metrics.reader_pull_score >= MIN_READER_PULL_SCORE
            and semantic_review.metrics.plot_clarity_score >= MIN_PLOT_CLARITY_SCORE
        )
        if publish_gate_passed:
            summary = "Story passes the hybrid publication gate with zero unresolved warnings."
        else:
            summary = (
                "Story is blocked by "
                + ", ".join(blocked_by or ["hybrid quality checks"])
                + (" and unresolved warnings." if warning_count else ".")
            )

        return HybridReviewReport(
            story_id=story_id,
            quality_score=quality_score,
            ready_for_publish=publish_gate_passed,
            summary=summary,
            version=version,
            source_run_id=run_id,
            source_provider="system",
            source_model="hybrid-publication-gate-v1",
            structural_review=structural_review,
            semantic_review=semantic_review,
            issues=self._dedupe_issues(issues),
            blocked_by=blocked_by,
            structural_gate_passed=structural_gate_passed,
            semantic_gate_passed=semantic_gate_passed,
            publish_gate_passed=publish_gate_passed,
            checked_at=utcnow_iso(),
        )

    def _dedupe_issues(
        self,
        issues: list[StoryReviewIssue],
    ) -> list[StoryReviewIssue]:
        seen: set[tuple[str, str | None, str]] = set()
        deduped: list[StoryReviewIssue] = []
        for issue in issues:
            key = (issue.code, issue.location, issue.message)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(issue)
        return deduped


__all__ = ["HybridPublicationGate"]
