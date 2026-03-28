"""Structural review pass for hard continuity and shape checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
    RelationshipSnapshot,
    StoryReviewIssue,
)
from src.contexts.narrative.domain.entities.chapter import Chapter

LOW_TENSION_ISSUE_CODES = {
    "missing_hook",
    "missing_hook_payoff",
    "thin_chapter",
    "flat_scene_stack",
}


@dataclass(slots=True)
class StructuralReviewResult:
    """Mutable structural review result shared with downstream review passes."""

    issues: list[StoryReviewIssue] = field(default_factory=list)
    continuity_checks: dict[str, bool] = field(default_factory=dict)
    chapter_issue_codes: dict[int, set[str]] = field(default_factory=dict)


class StructuralReviewService:
    """Review structural continuity, hard blockers, and ledger completeness."""

    def review(
        self,
        ctx: StoryWorkflowContext,
        pack: StoryContextPack,
    ) -> StructuralReviewResult:
        blueprint = ctx.workflow.blueprint
        outline = ctx.workflow.outline
        result = StructuralReviewResult(
            continuity_checks={
                "blueprint_present": blueprint is not None,
                "outline_present": outline is not None,
                "chapters_present": ctx.story.chapter_count > 0,
                "chapter_count_complete": ctx.story.chapter_count >= pack.target_chapters,
                "character_alignment": True,
                "motivation_alignment": True,
                "timeline_alignment": True,
                "hook_alignment": True,
                "world_rule_alignment": True,
                "relationship_alignment": True,
                "pacing_alignment": True,
                "promise_alignment": True,
                "strand_alignment": True,
            }
        )

        if blueprint is None:
            result.issues.append(
                StoryReviewIssue(
                    code="missing_blueprint",
                    severity="blocker",
                    message="The world and character bible has not been generated.",
                    location="story",
                    suggestion="Generate the blueprint before reviewing or publishing.",
                )
            )
        if outline is None:
            result.issues.append(
                StoryReviewIssue(
                    code="missing_outline",
                    severity="blocker",
                    message="The chapter outline has not been generated.",
                    location="story",
                    suggestion="Generate the outline before drafting or publishing.",
                )
            )
        if ctx.story.chapter_count == 0:
            result.issues.append(
                StoryReviewIssue(
                    code="no_chapters",
                    severity="blocker",
                    message="The story does not contain any chapters yet.",
                    location="story",
                    suggestion="Draft chapters before attempting to publish.",
                )
            )
        if ctx.story.chapter_count < pack.target_chapters:
            result.issues.append(
                StoryReviewIssue(
                    code="incomplete_story",
                    severity="blocker",
                    message=(
                        f"The story has {ctx.story.chapter_count} chapters but needs "
                        f"{pack.target_chapters} to match the configured target."
                    ),
                    location="story",
                    suggestion="Draft the remaining chapters before publishing.",
                    details={
                        "actual_chapters": ctx.story.chapter_count,
                        "target_chapters": pack.target_chapters,
                    },
                )
            )

        expected_character_names = (
            set(character_names(blueprint.character_bible)) if blueprint else set()
        )
        for index, chapter in enumerate(ctx.story.chapters, start=1):
            outline_entry = pack.outline_for_chapter(index)
            expected_outline = outline_entry.to_dict() if outline_entry is not None else {}
            self._review_chapter(
                ctx=ctx,
                pack=pack,
                chapter=chapter,
                index=index,
                expected_outline=expected_outline,
                expected_character_names=expected_character_names,
                issues=result.issues,
                continuity_checks=result.continuity_checks,
                chapter_issue_codes=result.chapter_issue_codes,
                is_final_chapter=index == ctx.story.chapter_count,
            )

        self._review_ledgers(
            ctx,
            pack,
            issues=result.issues,
            continuity_checks=result.continuity_checks,
            chapter_issue_codes=result.chapter_issue_codes,
        )
        return result

    def _review_chapter(
        self,
        *,
        ctx: StoryWorkflowContext,
        pack: StoryContextPack,
        chapter: Chapter,
        index: int,
        expected_outline: dict[str, Any],
        expected_character_names: set[str],
        issues: list[StoryReviewIssue],
        continuity_checks: dict[str, bool],
        chapter_issue_codes: dict[int, set[str]],
        is_final_chapter: bool,
    ) -> None:
        location = f"chapter-{chapter.chapter_number}"
        local_issue_codes = chapter_issue_codes.setdefault(chapter.chapter_number, set())

        if chapter.chapter_number != index:
            continuity_checks["timeline_alignment"] = False
            local_issue_codes.add("non_sequential_chapter")
            issues.append(
                StoryReviewIssue(
                    code="non_sequential_chapter",
                    severity="blocker",
                    message=(
                        f"Chapter {chapter.chapter_number} is out of order; expected "
                        f"chapter {index}."
                    ),
                    location=location,
                    suggestion="Renumber or reorder chapters to restore continuity.",
                )
            )

        timeline_day = int(chapter.metadata.get("timeline_day", chapter.chapter_number))
        if timeline_day != index:
            continuity_checks["timeline_alignment"] = False
            local_issue_codes.add("timeline_regression")
            issues.append(
                StoryReviewIssue(
                    code="timeline_regression",
                    severity="blocker",
                    message=(
                        f"Chapter {chapter.chapter_number} breaks the established timeline "
                        f"sequence with day {timeline_day}."
                    ),
                    location=location,
                    suggestion="Realign the chapter timeline marker with the canonical day order.",
                )
            )

        if not chapter.summary or not chapter.summary.strip():
            local_issue_codes.add("missing_summary")
            issues.append(
                StoryReviewIssue(
                    code="missing_summary",
                    severity="blocker",
                    message="The chapter summary is missing.",
                    location=location,
                    suggestion="Add a concise summary to keep the outline coherent.",
                )
            )

        if chapter.scene_count == 0:
            local_issue_codes.add("empty_chapter")
            issues.append(
                StoryReviewIssue(
                    code="empty_chapter",
                    severity="blocker",
                    message="The chapter does not contain any scenes.",
                    location=location,
                    suggestion="Draft or repair the chapter scenes before publishing.",
                )
            )
            return

        if any(not scene.content.strip() for scene in chapter.scenes):
            local_issue_codes.add("empty_scene")
            issues.append(
                StoryReviewIssue(
                    code="empty_scene",
                    severity="blocker",
                    message="At least one scene is empty.",
                    location=location,
                    suggestion="Regenerate or rewrite the empty scene.",
                )
            )

        focus_character = str(chapter.metadata.get("focus_character", "")).strip()
        if not focus_character:
            local_issue_codes.add("missing_focus_character")
            issues.append(
                StoryReviewIssue(
                    code="missing_focus_character",
                    severity="warning",
                    message="The chapter has no focus character metadata.",
                    location=location,
                    suggestion="Store the focus character in chapter metadata during drafting.",
                )
            )
        elif expected_character_names and focus_character not in expected_character_names:
            continuity_checks["character_alignment"] = False
            local_issue_codes.add("unknown_focus_character")
            issues.append(
                StoryReviewIssue(
                    code="unknown_focus_character",
                    severity="blocker",
                    message=(
                        f"The focus character '{focus_character}' is not present in the blueprint."
                    ),
                    location=location,
                    suggestion="Reset the chapter focus to a canonical character from the blueprint.",
                )
            )
        elif not any(
            focus_character.lower() in scene.content.lower() for scene in chapter.scenes
        ):
            continuity_checks["character_alignment"] = False
            local_issue_codes.add("character_drift")
            issues.append(
                StoryReviewIssue(
                    code="character_drift",
                    severity="blocker",
                    message="The chapter scenes no longer materially feature the stored focus character.",
                    location=location,
                    suggestion="Rewrite the chapter so the declared focus character stays on-page.",
                )
            )

        focus_motivation = str(chapter.metadata.get("focus_motivation", "")).strip()
        if focus_motivation and not any(
            focus_motivation.lower() in scene.content.lower() for scene in chapter.scenes
        ):
            continuity_checks["motivation_alignment"] = False
            local_issue_codes.add("motivation_drift")
            issues.append(
                StoryReviewIssue(
                    code="motivation_drift",
                    severity="blocker" if chapter.chapter_number == 1 else "warning",
                    message="The chapter scenes do not materially reflect the stored motivation.",
                    location=location,
                    suggestion="Surface the current chapter motivation in scene text.",
                )
            )

        hook = str(expected_outline.get("hook", "")).strip()
        current_content = (
            chapter.current_scene.content if chapter.current_scene is not None else ""
        )
        if not is_final_chapter and not hook:
            continuity_checks["hook_alignment"] = False
            local_issue_codes.add("missing_outline_hook")
            issues.append(
                StoryReviewIssue(
                    code="missing_outline_hook",
                    severity="warning",
                    message="The outline does not define a chapter-end hook for a non-final chapter.",
                    location=location,
                    suggestion="Add an explicit hook to the outline before publishing.",
                )
            )
        elif not is_final_chapter and not (
            hook.lower() in current_content.lower() or current_content.rstrip().endswith("?")
        ):
            continuity_checks["hook_alignment"] = False
            continuity_checks["pacing_alignment"] = False
            local_issue_codes.add("missing_hook")
            issues.append(
                StoryReviewIssue(
                    code="missing_hook",
                    severity="warning",
                    message="The chapter does not surface its outline hook clearly.",
                    location=location,
                    suggestion="Close the chapter with a stronger cliffhanger or reveal.",
                )
            )

        previous_hook = str(chapter.metadata.get("previous_hook", "")).strip()
        opening_scene_text = chapter.scenes[0].content.lower() if chapter.scenes else ""
        if (
            chapter.chapter_number > 1
            and previous_hook
            and previous_hook.lower() not in opening_scene_text
        ):
            continuity_checks["hook_alignment"] = False
            local_issue_codes.add("missing_hook_payoff")
            issues.append(
                StoryReviewIssue(
                    code="missing_hook_payoff",
                    severity="warning",
                    message="The chapter opening does not pay off the previous chapter hook.",
                    location=location,
                    suggestion="Open by addressing or escalating the prior hook before pivoting.",
                )
            )

        if chapter.scene_count < 3:
            continuity_checks["pacing_alignment"] = False
            local_issue_codes.add("thin_chapter")
            issues.append(
                StoryReviewIssue(
                    code="thin_chapter",
                    severity="warning",
                    message="The chapter is too thin to sustain web-fiction pacing.",
                    location=location,
                    suggestion="Expand the chapter to at least three meaningful scenes.",
                )
            )

        if len({scene.scene_type for scene in chapter.scenes}) < 2:
            continuity_checks["pacing_alignment"] = False
            local_issue_codes.add("flat_scene_stack")
            issues.append(
                StoryReviewIssue(
                    code="flat_scene_stack",
                    severity="warning",
                    message="The chapter reuses the same scene energy throughout.",
                    location=location,
                    suggestion="Mix setup, dialogue, action, and payoff beats more intentionally.",
                )
            )

        relationship_target = str(chapter.metadata.get("relationship_target", "")).strip()
        relationship_status = str(chapter.metadata.get("relationship_status", "")).strip()
        expected_relationship = self._expected_relationship_state(
            pack=pack,
            chapter_number=chapter.chapter_number,
            focus_character=focus_character,
        )
        if not relationship_target or not relationship_status:
            continuity_checks["relationship_alignment"] = False
            local_issue_codes.add("missing_relationship_state")
            issues.append(
                StoryReviewIssue(
                    code="missing_relationship_state",
                    severity="warning",
                    message="The chapter is missing relationship state metadata.",
                    location=location,
                    suggestion="Persist relationship target and status during drafting.",
                )
            )
        elif expected_relationship is not None and (
            relationship_target != expected_relationship.target
            or relationship_status != expected_relationship.status
        ):
            continuity_checks["relationship_alignment"] = False
            local_issue_codes.add("relationship_drift")
            issues.append(
                StoryReviewIssue(
                    code="relationship_drift",
                    severity="blocker",
                    message="The chapter relationship metadata drifts from the canonical relationship ledger.",
                    location=location,
                    suggestion="Restore the chapter relationship target and status to the canonical state.",
                )
            )

        expected_title = str(expected_outline.get("title", "")).strip()
        if expected_title and expected_title != chapter.title:
            local_issue_codes.add("outline_mismatch")
            issues.append(
                StoryReviewIssue(
                    code="outline_mismatch",
                    severity="warning",
                    message="The chapter title diverges from the outline.",
                    location=location,
                    suggestion="Align the drafted chapter title with the outline.",
                )
            )

        world_rule_conflicts = self._find_world_rule_conflicts(ctx, chapter)
        for rule in world_rule_conflicts:
            continuity_checks["world_rule_alignment"] = False
            local_issue_codes.add("world_rule_conflict")
            issues.append(
                StoryReviewIssue(
                    code="world_rule_conflict",
                    severity="blocker",
                    message=(
                        f"Chapter {chapter.chapter_number} contradicts the world rule: {rule}."
                    ),
                    location=location,
                    suggestion="Rewrite the chapter so the scene logic respects the blueprint rule.",
                    details={"rule": rule},
                )
            )

    def _review_ledgers(
        self,
        ctx: StoryWorkflowContext,
        pack: StoryContextPack,
        *,
        issues: list[StoryReviewIssue],
        continuity_checks: dict[str, bool],
        chapter_issue_codes: dict[int, set[str]],
    ) -> None:
        if ctx.workflow.blueprint and not pack.world_rules:
            continuity_checks["world_rule_alignment"] = False
            issues.append(
                StoryReviewIssue(
                    code="world_rule_gap",
                    severity="warning",
                    message="The workflow memory does not retain any world rules.",
                    location="story",
                    suggestion="Persist core world rules into the continuity ledger.",
                )
            )

        if len(ctx.memory.timeline_ledger) != ctx.story.chapter_count:
            continuity_checks["timeline_alignment"] = False
            issues.append(
                StoryReviewIssue(
                    code="timeline_ledger_gap",
                    severity="warning",
                    message="The timeline ledger is missing one or more drafted chapters.",
                    location="story",
                    suggestion="Resynchronize chapter memory before publishing.",
                )
            )

        if len(ctx.memory.hook_ledger) != ctx.story.chapter_count:
            continuity_checks["hook_alignment"] = False
            issues.append(
                StoryReviewIssue(
                    code="hook_ledger_gap",
                    severity="warning",
                    message="The hook ledger is missing one or more drafted chapters.",
                    location="story",
                    suggestion="Resynchronize the hook ledger before publishing.",
                )
            )

        unresolved_hooks = [
            chapter_number
            for chapter_number, issue_codes in chapter_issue_codes.items()
            if chapter_number < ctx.story.chapter_count
            and ("missing_hook" in issue_codes or "missing_outline_hook" in issue_codes)
        ]
        if len(unresolved_hooks) >= 2:
            continuity_checks["hook_alignment"] = False
            continuity_checks["pacing_alignment"] = False
            issues.append(
                StoryReviewIssue(
                    code="hook_debt",
                    severity="blocker" if len(unresolved_hooks) >= 4 else "warning",
                    message=(
                        "Multiple non-final chapters close without surfacing their hooks, "
                        f"creating hook debt in chapters {unresolved_hooks}."
                    ),
                    location="story",
                    suggestion="Strengthen the ending beats for the unresolved hook chapters.",
                    details={"chapters": unresolved_hooks},
                )
            )

        low_tension_chapters = [
            chapter_number
            for chapter_number, issue_codes in sorted(chapter_issue_codes.items())
            if issue_codes & LOW_TENSION_ISSUE_CODES
        ]
        for index in range(len(low_tension_chapters) - 2):
            window = low_tension_chapters[index : index + 3]
            if window[2] - window[0] == 2:
                continuity_checks["pacing_alignment"] = False
                issues.append(
                    StoryReviewIssue(
                        code="consecutive_low_tension_chapters",
                        severity="blocker",
                        message=(
                            "Three consecutive chapters flatten tension and weaken serial momentum "
                            f"in chapters {window}."
                        ),
                        location="story",
                        suggestion="Rebuild the affected chapter run with stronger hooks, variation, and escalation.",
                        details={"chapters": window},
                    )
                )
                break

    @staticmethod
    def _expected_relationship_state(
        *,
        pack: StoryContextPack,
        chapter_number: int,
        focus_character: str,
    ) -> RelationshipSnapshot | None:
        return next(
            (
                entry
                for entry in reversed(pack.relationship_states)
                if entry.chapter_number == chapter_number
                and (not focus_character or entry.source == focus_character)
            ),
            None,
        )

    @staticmethod
    def _find_world_rule_conflicts(
        ctx: StoryWorkflowContext,
        chapter: Chapter,
    ) -> list[str]:
        if not ctx.memory.world_rules:
            return []

        combined_text = " ".join(scene.content.lower() for scene in chapter.scenes)
        conflicts: list[str] = []
        for entry in ctx.memory.world_rules:
            rule = entry.rule.strip()
            if not rule:
                continue
            rule_lower = rule.lower()
            contradiction_markers = StructuralReviewService._contradiction_markers(rule_lower)
            if contradiction_markers and any(
                marker in combined_text for marker in contradiction_markers
            ):
                conflicts.append(rule)
        return conflicts

    @staticmethod
    def _contradiction_markers(rule_lower: str) -> tuple[str, ...]:
        if "cost" in rule_lower:
            return (
                "power comes free",
                "power has no cost",
                "without paying any cost",
            )
        if "faction" in rule_lower:
            return (
                "no factions matter",
                "without faction pressure",
            )
        if "reputation" in rule_lower:
            return (
                "reputation never matters",
                "public opinion never matters",
            )
        return ()


__all__ = ["StructuralReviewResult", "StructuralReviewService"]
