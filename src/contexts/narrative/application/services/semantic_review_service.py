"""Provider-backed semantic review pass for reader pull and clarity."""

from __future__ import annotations

import re

from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationResult,
    TextGenerationTask,
)
from src.contexts.narrative.application.services.story_context_pack import (
    StoryContextPack,
)
from src.contexts.narrative.application.services.story_pipeline_context import (
    StoryWorkflowContext,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    PromiseLedgerEntry,
    SemanticReviewArtifact,
    SemanticReviewMetrics,
    StoryReviewIssue,
    utcnow_iso,
)

MIN_SEMANTIC_SCORE = 80
MIN_READER_PULL_SCORE = 78
MIN_PLOT_CLARITY_SCORE = 75
MAX_OOC_RISK_SCORE = 35

ALLOWED_SEMANTIC_CODES = {
    "promise_break",
    "ooc_behavior",
    "plot_confusion",
    "weak_serial_pull",
    "world_logic_soft_conflict",
    "relationship_progression_stall",
}

SEMANTIC_CODE_ALIASES = {
    "broken_promise": "promise_break",
    "hook_payoff_break": "promise_break",
    "logic_contradiction": "world_logic_soft_conflict",
    "missing_character_trait": "ooc_behavior",
    "ooc": "ooc_behavior",
    "ooc_drift": "ooc_behavior",
    "ooc_voice": "ooc_behavior",
    "pacing_overload": "weak_serial_pull",
    "plot_incoherence": "plot_confusion",
    "plot_inconsistency": "plot_confusion",
    "reader_pull_weakness": "weak_serial_pull",
    "relationship_stall": "relationship_progression_stall",
    "serial_pull_weakness": "weak_serial_pull",
    "world_logic_conflict": "world_logic_soft_conflict",
}


class SemanticReviewService:
    """Run provider-backed semantic review over the latest mutable workspace."""

    def __init__(self, provider: TextGenerationProvider) -> None:
        self._provider = provider

    async def review(
        self,
        ctx: StoryWorkflowContext,
        pack: StoryContextPack,
    ) -> SemanticReviewArtifact:
        result = await self._provider.generate_structured(self._task(ctx, pack))
        ctx.record_generation_trace(result)
        return self._extract_artifact(ctx, pack, result)

    def _task(
        self,
        ctx: StoryWorkflowContext,
        pack: StoryContextPack,
    ) -> TextGenerationTask:
        overdue_promises = self._overdue_promises(ctx, pack)
        blueprint = ctx.workflow.blueprint
        outline = ctx.workflow.outline
        return TextGenerationTask(
            step="semantic_review",
            system_prompt=(
                "You are a senior Chinese commercial webnovel editor. "
                "Review only for serial-reader pull, plot clarity, character voice stability, "
                "soft world logic, relationship progression, and promise/payoff trust. "
                "Return strict JSON that follows the schema."
            ),
            user_prompt=(
                f"Story title: {ctx.story.title}\n"
                f"Premise: {ctx.workflow.premise}\n"
                f"Tone: {ctx.workflow.tone}\n"
                f"Target chapters: {pack.target_chapters}\n"
                f"World rules: {pack.world_rules}\n"
                f"Recent chapter summaries: {pack.recent_chapter_summaries}\n"
                f"Unresolved hooks: {pack.unresolved_hooks}\n"
                f"Outstanding promises: {[entry.promise for entry in pack.unresolved_promises]}\n"
                f"Relationship states: {[entry.to_dict() for entry in pack.relationship_states]}\n"
                f"Outline nodes: {[chapter.to_dict() for chapter in (outline.chapters if outline else [])]}\n"
                f"Blueprint premise summary: {(blueprint.premise_summary if blueprint else '')}\n"
                f"Revision notes: {pack.revision_notes}"
            ),
            response_schema={
                "semantic_score": {"type": "integer"},
                "reader_pull_score": {"type": "integer"},
                "plot_clarity_score": {"type": "integer"},
                "ooc_risk_score": {"type": "integer"},
                "summary": {"type": "string"},
                "repair_suggestions": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string"},
                            "severity": {"type": "string"},
                            "message": {"type": "string"},
                            "location": {"type": "string"},
                            "suggestion": {"type": "string"},
                        },
                    },
                },
            },
            temperature=0.15,
            metadata={
                "story_id": str(ctx.story.id),
                "chapter_count": ctx.story.chapter_count,
                "target_chapters": pack.target_chapters,
                "unresolved_hook_count": len(pack.unresolved_hooks),
                "unresolved_promise_count": len(pack.unresolved_promises),
                "overdue_promise_count": len(overdue_promises),
                "recent_chapter_summaries": pack.recent_chapter_summaries,
                "world_rules": pack.world_rules,
                "relationship_states": [
                    entry.to_dict() for entry in pack.relationship_states
                ],
            },
        )

    def _extract_artifact(
        self,
        ctx: StoryWorkflowContext,
        pack: StoryContextPack,
        result: TextGenerationResult,
    ) -> SemanticReviewArtifact:
        content = result.content
        summary = str(content.get("summary", "")).strip()
        if not summary:
            raise ValueError("Semantic review payload missing summary")

        issues = self._extract_issues(content.get("issues"))
        heuristic_issues = self._heuristic_issues(ctx, pack)
        issues.extend(
            issue
            for issue in heuristic_issues
            if (issue.code, issue.location, issue.message)
            not in {(item.code, item.location, item.message) for item in issues}
        )
        metrics = SemanticReviewMetrics(
            semantic_score=int(content.get("semantic_score", 0)),
            reader_pull_score=int(content.get("reader_pull_score", 0)),
            plot_clarity_score=int(content.get("plot_clarity_score", 0)),
            ooc_risk_score=int(content.get("ooc_risk_score", 0)),
        )
        ready_for_publish = (
            not any(issue.severity == "blocker" for issue in issues)
            and metrics.semantic_score >= MIN_SEMANTIC_SCORE
            and metrics.reader_pull_score >= MIN_READER_PULL_SCORE
            and metrics.plot_clarity_score >= MIN_PLOT_CLARITY_SCORE
            and metrics.ooc_risk_score <= MAX_OOC_RISK_SCORE
        )
        return SemanticReviewArtifact(
            story_id=str(ctx.story.id),
            semantic_score=metrics.semantic_score,
            ready_for_publish=ready_for_publish,
            summary=summary,
            version=ctx.artifact_version("semantic_review"),
            source_run_id=ctx.workflow.current_run_id,
            source_provider=result.provider,
            source_model=result.model,
            issues=issues,
            repair_suggestions=[
                str(note).strip()
                for note in content.get("repair_suggestions", [])
                if str(note).strip()
            ],
            checked_at=utcnow_iso(),
            metrics=metrics,
        )

    def _extract_issues(self, payload: object) -> list[StoryReviewIssue]:
        if not isinstance(payload, list):
            raise ValueError("Semantic review payload missing issues")
        issues: list[StoryReviewIssue] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            issue = StoryReviewIssue.from_dict(item)
            issue.code = self._normalize_issue_code(issue.code)
            if issue.code not in ALLOWED_SEMANTIC_CODES:
                raise ValueError(f"Unsupported semantic issue code: {issue.code}")
            issues.append(issue)
        return issues

    def _normalize_issue_code(self, raw_code: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "_", raw_code.strip().lower()).strip("_")
        if not normalized:
            return "unknown"
        if normalized in ALLOWED_SEMANTIC_CODES:
            return normalized
        if normalized in SEMANTIC_CODE_ALIASES:
            return SEMANTIC_CODE_ALIASES[normalized]
        if "promise" in normalized:
            return "promise_break"
        if "relationship" in normalized:
            return "relationship_progression_stall"
        if (
            "ooc" in normalized
            or "voice" in normalized
            or "character" in normalized
            or "trait" in normalized
            or "motivation" in normalized
        ):
            return "ooc_behavior"
        if "logic" in normalized or "world" in normalized:
            return "world_logic_soft_conflict"
        if "plot" in normalized or "confus" in normalized:
            return "plot_confusion"
        if (
            "pull" in normalized
            or "serial" in normalized
            or "hook" in normalized
            or "pacing" in normalized
        ):
            return "weak_serial_pull"
        return "plot_confusion"

    def _heuristic_issues(
        self,
        ctx: StoryWorkflowContext,
        pack: StoryContextPack,
    ) -> list[StoryReviewIssue]:
        issues: list[StoryReviewIssue] = []
        overdue_promises = self._overdue_promises(ctx, pack)
        if overdue_promises:
            issues.append(
                StoryReviewIssue(
                    code="promise_break",
                    severity="blocker" if len(overdue_promises) >= 4 else "warning",
                    message="Long-running promises remain unpaid for too many chapters.",
                    location="story",
                    suggestion="Resolve or deliberately escalate the oldest promise thread.",
                )
            )
        if len(pack.recent_chapter_summaries) >= 3 and len(
            set(pack.recent_chapter_summaries[-3:])
        ) == 1:
            issues.append(
                StoryReviewIssue(
                    code="weak_serial_pull",
                    severity="warning",
                    message="Recent chapters feel too similar, weakening serial pull.",
                    location="story",
                    suggestion="Change the payoff rhythm or conflict pressure in the next chapter block.",
                )
            )
        if len(pack.relationship_states) >= 4 and len(
            {entry.status for entry in pack.relationship_states[-4:]}
        ) == 1:
            issues.append(
                StoryReviewIssue(
                    code="relationship_progression_stall",
                    severity="warning",
                    message="Relationship progression has stalled across multiple chapters.",
                    location="story",
                    suggestion="Advance or rupture a key relationship instead of repeating the same state.",
                )
            )
        if pack.unresolved_hooks and not pack.world_rules:
            issues.append(
                StoryReviewIssue(
                    code="world_logic_soft_conflict",
                    severity="warning",
                    message="Hooks escalate without enough stable world-rule grounding.",
                    location="story",
                    suggestion="Re-anchor pressure beats in explicit world rules or costs.",
                )
            )
        return issues

    def _overdue_promises(
        self,
        ctx: StoryWorkflowContext,
        pack: StoryContextPack,
    ) -> list[PromiseLedgerEntry]:
        current_chapter = ctx.story.chapter_count
        return [
            entry
            for entry in pack.unresolved_promises
            if entry.promise
            and entry.due_by_chapter is not None
            and entry.due_by_chapter + 2 <= current_chapter
            and current_chapter - entry.chapter_number <= 6
        ]


__all__ = [
    "MAX_OOC_RISK_SCORE",
    "MIN_PLOT_CLARITY_SCORE",
    "MIN_READER_PULL_SCORE",
    "MIN_SEMANTIC_SCORE",
    "SemanticReviewService",
]
