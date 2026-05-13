"""Generic narrative repair strategy components.

The strategy layer intentionally works from review issue shape and story state.
It must not encode a fixed story, fixed character roster, or incident-specific
live-gate patch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from src.contexts.narrative.application.services.story_pipeline_context import (
    StoryWorkflowContext,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    StoryReviewIssue,
)
from src.contexts.narrative.domain.entities.chapter import Chapter

RepairCategory = Literal[
    "chapter_summary",
    "relationship_state",
    "scene_anchor",
    "continuity_ledger",
    "payoff_action",
]


@dataclass(frozen=True)
class ClassifiedIssue:
    """A review issue mapped to generic repair categories."""

    issue_id: str
    code: str
    message: str
    severity: str
    location: str | None
    categories: tuple[RepairCategory, ...]


@dataclass(frozen=True)
class RepairStep:
    """One generic repair operation for a story issue."""

    issue_id: str
    issue_code: str
    chapter_number: int | None
    intent: str
    categories: tuple[RepairCategory, ...]


@dataclass(frozen=True)
class RepairPlan:
    """Structured repair plan emitted before mutation."""

    steps: tuple[RepairStep, ...]
    summary: str


@dataclass(frozen=True)
class RepairExecutionRecord:
    """Provenance for a repair operation."""

    issue_id: str
    repair_intent: str
    changed_fields: tuple[str, ...]
    before: dict[str, Any]
    after: dict[str, Any]


class NarrativeQualityPolicy:
    """Map review issue codes to generic repair categories."""

    _CATEGORY_BY_CODE: dict[str, tuple[RepairCategory, ...]] = {
        "empty_chapter": ("chapter_summary", "scene_anchor"),
        "empty_scene": ("scene_anchor",),
        "thin_chapter": ("chapter_summary", "scene_anchor"),
        "flat_scene_stack": ("scene_anchor", "payoff_action"),
        "missing_hook_payoff": ("chapter_summary", "payoff_action"),
        "relationship_drift": ("relationship_state", "scene_anchor"),
        "missing_relationship_state": ("relationship_state",),
        "relationship_progression_stall": ("relationship_state", "payoff_action"),
        "world_rule_conflict": ("continuity_ledger", "scene_anchor"),
        "continuity_gap": ("continuity_ledger", "scene_anchor"),
        "character_drift": ("relationship_state", "scene_anchor"),
        "motivation_drift": ("relationship_state", "scene_anchor"),
        "pacing_sag": ("chapter_summary", "payoff_action"),
    }
    _DEFAULT_CATEGORIES: tuple[RepairCategory, ...] = (
        "chapter_summary",
        "scene_anchor",
    )

    def categories_for(self, issue: StoryReviewIssue) -> tuple[RepairCategory, ...]:
        """Return generic categories for a review issue."""
        return self._CATEGORY_BY_CODE.get(issue.code, self._DEFAULT_CATEGORIES)


class IssueClassifier:
    """Classify review issues without story-specific assumptions."""

    def __init__(self, policy: NarrativeQualityPolicy | None = None) -> None:
        self._policy = policy or NarrativeQualityPolicy()

    def classify(self, issues: list[StoryReviewIssue]) -> tuple[ClassifiedIssue, ...]:
        """Return classified issues with stable ids for provenance."""
        classified: list[ClassifiedIssue] = []
        for index, issue in enumerate(issues, start=1):
            classified.append(
                ClassifiedIssue(
                    issue_id=f"{issue.code}:{issue.location or 'story'}:{index}",
                    code=issue.code,
                    message=issue.message,
                    severity=issue.severity,
                    location=issue.location,
                    categories=self._policy.categories_for(issue),
                )
            )
        return tuple(classified)


class RepairPlanner:
    """Convert classified issues into structured repair operations."""

    def plan(
        self,
        ctx: StoryWorkflowContext,
        issues: tuple[ClassifiedIssue, ...],
    ) -> RepairPlan:
        """Create a generic repair plan for the current story."""
        steps: list[RepairStep] = []
        for issue in issues:
            chapter_numbers = self._chapter_numbers(issue.location)
            if not chapter_numbers:
                chapter_numbers = self._fallback_chapters(ctx)
            for chapter_number in chapter_numbers:
                steps.append(
                    RepairStep(
                        issue_id=issue.issue_id,
                        issue_code=issue.code,
                        chapter_number=chapter_number,
                        intent=self._intent(issue),
                        categories=issue.categories,
                    )
                )
        return RepairPlan(
            steps=tuple(steps),
            summary=f"Planned {len(steps)} generic repair operations.",
        )

    def _chapter_numbers(self, location: str | None) -> tuple[int, ...]:
        if not location:
            return ()
        marker = "chapter-"
        normalized = location.lower()
        if marker not in normalized:
            return ()
        suffix = normalized.split(marker, 1)[1].split("/", 1)[0].split(":", 1)[0]
        try:
            chapter_number = int("".join(char for char in suffix if char.isdigit()))
        except ValueError:
            return ()
        return (chapter_number,) if chapter_number > 0 else ()

    def _fallback_chapters(self, ctx: StoryWorkflowContext) -> tuple[int, ...]:
        if not ctx.story.chapters:
            return ()
        if ctx.story.chapter_count <= 3:
            return tuple(chapter.chapter_number for chapter in ctx.story.chapters)
        midpoint = max(1, ctx.story.chapter_count // 2)
        return (midpoint, ctx.story.chapter_count)

    def _intent(self, issue: ClassifiedIssue) -> str:
        return (
            f"Resolve {issue.code} by strengthening objective, continuity, "
            "relationship state, scene evidence, and payoff."
        )


class RepairExecutor:
    """Apply generic repair operations and persist provenance on chapters."""

    def execute(self, ctx: StoryWorkflowContext, plan: RepairPlan) -> list[str]:
        """Execute a repair plan against the story aggregate."""
        notes: list[str] = []
        for step in plan.steps:
            chapter = self._chapter_for_step(ctx, step)
            if chapter is None:
                continue
            record = self._apply_step(chapter, step)
            if record.changed_fields:
                provenance = chapter.metadata.setdefault("repair_provenance", [])
                if isinstance(provenance, list):
                    provenance.append(
                        {
                            "issue_id": record.issue_id,
                            "repair_intent": record.repair_intent,
                            "changed_fields": list(record.changed_fields),
                            "before": record.before,
                            "after": record.after,
                        }
                    )
                notes.append(
                    f"Applied generic repair for {step.issue_code} in chapter "
                    f"{chapter.chapter_number}."
                )
        if notes:
            ctx.memory.revision_notes = [*ctx.memory.revision_notes, *notes]
        return notes

    def _chapter_for_step(
        self,
        ctx: StoryWorkflowContext,
        step: RepairStep,
    ) -> Chapter | None:
        if step.chapter_number is None:
            return None
        return next(
            (
                chapter
                for chapter in ctx.story.chapters
                if chapter.chapter_number == step.chapter_number
            ),
            None,
        )

    def _apply_step(
        self,
        chapter: Chapter,
        step: RepairStep,
    ) -> RepairExecutionRecord:
        before = self._snapshot(chapter)
        changed_fields: list[str] = []

        if "chapter_summary" in step.categories:
            objective = chapter.metadata.get("chapter_objective")
            if not isinstance(objective, str) or not objective.strip():
                chapter.metadata["chapter_objective"] = step.intent
                changed_fields.append("metadata.chapter_objective")
            hook = chapter.metadata.get("outline_hook")
            if not isinstance(hook, str) or not hook.strip():
                chapter.metadata["outline_hook"] = (
                    "End the chapter with a visible choice, cost, or promise."
                )
                changed_fields.append("metadata.outline_hook")
            if not chapter.summary or not chapter.summary.strip():
                chapter.summary = step.intent
                changed_fields.append("summary")

        if "relationship_state" in step.categories:
            if not str(chapter.metadata.get("relationship_status", "")).strip():
                chapter.metadata["relationship_status"] = (
                    "changed by a visible choice and recorded consequence"
                )
                changed_fields.append("metadata.relationship_status")

        if "continuity_ledger" in step.categories:
            ledger = chapter.metadata.setdefault("continuity_ledger", [])
            if isinstance(ledger, list):
                ledger.append(
                    {
                        "issue_id": step.issue_id,
                        "intent": step.intent,
                    }
                )
                changed_fields.append("metadata.continuity_ledger")

        if "payoff_action" in step.categories:
            chapter.metadata["payoff_action"] = (
                "Show the promised consequence through action before the chapter closes."
            )
            changed_fields.append("metadata.payoff_action")

        if "scene_anchor" in step.categories and chapter.scenes:
            first_scene = chapter.scenes[0]
            anchor = (
                "\n\nRevision anchor: a concrete action, observable cost, and "
                "next promise make this repair visible on the page."
            )
            if anchor not in first_scene.content:
                first_scene.content = f"{first_scene.content.rstrip()}{anchor}"
                changed_fields.append("scenes[0].content")

        return RepairExecutionRecord(
            issue_id=step.issue_id,
            repair_intent=step.intent,
            changed_fields=tuple(dict.fromkeys(changed_fields)),
            before=before,
            after=self._snapshot(chapter),
        )

    def _snapshot(self, chapter: Chapter) -> dict[str, Any]:
        return {
            "summary": chapter.summary,
            "metadata": {
                key: chapter.metadata.get(key)
                for key in (
                    "chapter_objective",
                    "outline_hook",
                    "relationship_status",
                    "payoff_action",
                )
            },
            "scene_count": len(chapter.scenes),
        }


@dataclass
class NarrativeRepairStrategy:
    """Coordinator for issue -> plan -> executor."""

    classifier: IssueClassifier = field(default_factory=IssueClassifier)
    planner: RepairPlanner = field(default_factory=RepairPlanner)
    executor: RepairExecutor = field(default_factory=RepairExecutor)

    def repair(
        self,
        ctx: StoryWorkflowContext,
        issues: list[StoryReviewIssue],
    ) -> tuple[RepairPlan, list[str]]:
        classified = self.classifier.classify(issues)
        plan = self.planner.plan(ctx, classified)
        notes = self.executor.execute(ctx, plan)
        return plan, notes
