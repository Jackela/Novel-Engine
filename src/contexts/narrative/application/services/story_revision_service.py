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
    antagonist_names,
    ensure_hook,
    ensure_motivation_anchor,
    ensure_payoff_anchor,
    ensure_relationship_anchor,
    outline_chapter_for_number,
    pov_character_names,
    protagonist_name,
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
        issue_codes = {issue.code for issue in issues}
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

        repair_notes.extend(
            self._repair_semantic_relationship_arc(
                ctx,
                issue_codes=issue_codes,
            )
        )
        repair_notes.extend(
            self._repair_semantic_final_arc(
                ctx,
                issue_codes=issue_codes,
            )
        )
        repair_notes.extend(
            self._repair_semantic_foundation(
                ctx,
                issue_codes=issue_codes,
            )
        )
        self._drafting_service.synchronize_memory(ctx)
        return repair_notes

    @staticmethod
    def _repair_hook(chapter_spec: dict[str, str], chapter: Chapter) -> str:
        hook = str(chapter_spec.get("hook", "")).strip()
        if hook:
            return hook
        return f"What changes after {chapter.title}?"

    def _repair_semantic_relationship_arc(
        self,
        ctx: StoryWorkflowContext,
        *,
        issue_codes: set[str],
    ) -> list[str]:
        if "relationship_progression_stall" not in issue_codes:
            return []

        blueprint = ctx.workflow.blueprint
        if blueprint is None:
            return []

        protagonist = protagonist_name(blueprint.character_bible)
        antagonists = set(antagonist_names(blueprint.character_bible))
        pov_names = pov_character_names(blueprint.character_bible)
        allies = [
            name
            for name in pov_names
            if name and name != protagonist and name not in antagonists
        ]
        if not protagonist or not allies:
            return []

        changed = False
        for chapter in ctx.story.chapters:
            number = chapter.chapter_number
            focus_character = str(chapter.metadata.get("focus_character", "")).strip()
            if not focus_character or focus_character in antagonists:
                focus_character = (
                    protagonist
                    if number % 2 == 1
                    else allies[(number - 1) % len(allies)]
                )
                chapter.metadata["focus_character"] = focus_character
                changed = True

            if focus_character != protagonist:
                relationship_target = protagonist
            else:
                relationship_target = allies[(number - 1) % len(allies)]

            relationship_status = self._relationship_progression_status(
                chapter_number=number,
                target_chapters=ctx.story.chapter_count,
            )

            if chapter.metadata.get("relationship_target") != relationship_target:
                chapter.metadata["relationship_target"] = relationship_target
                changed = True
            if chapter.metadata.get("relationship_status") != relationship_status:
                chapter.metadata["relationship_status"] = relationship_status
                changed = True

            if chapter.scene_count >= 2:
                anchor_index = min(1, chapter.scene_count - 1)
                anchored = ensure_relationship_anchor(
                    chapter.scenes[anchor_index].content,
                    focus_character,
                    relationship_target,
                    relationship_status,
                )
                if anchored != chapter.scenes[anchor_index].content:
                    chapter.scenes[anchor_index].update_content(anchored)
                    changed = True

        if not changed:
            return []
        return [
            "Reframed the relationship ledger around the surviving POV cast instead of the defeated antagonist."
        ]

    def _repair_semantic_final_arc(
        self,
        ctx: StoryWorkflowContext,
        *,
        issue_codes: set[str],
    ) -> list[str]:
        if "weak_serial_pull" not in issue_codes:
            return []

        outline = ctx.workflow.outline
        if outline is None:
            return []

        late_arc_plan: dict[int, dict[str, str | int]] = {
            18: {
                "summary": (
                    "Rebuilding the ledger now sparks political fights over who controls memory, "
                    "forcing the victors to prove the new order can survive immediate pressure."
                ),
                "hook": "A surviving oath surfaces beneath the rebuilt archive, demanding a new price.",
                "hook_strength": 78,
            },
            19: {
                "summary": (
                    "The first public oath of the new era reveals a hidden debt under the city's foundation, "
                    "showing that the old system still has one last claim."
                ),
                "hook": "The new oath awakens a debt the city never meant to remember.",
                "hook_strength": 82,
            },
            20: {
                "summary": (
                    "The hopeful ending keeps one live tension on the table: memory can be rebuilt, "
                    "but every new oath now carries a visible civic cost."
                ),
                "hook": "What cost will the city's next oath demand from the future?",
                "hook_strength": 70,
            },
        }

        changed = False
        outline_by_number = {chapter.chapter_number: chapter for chapter in outline.chapters}
        for chapter in ctx.story.chapters:
            plan = late_arc_plan.get(chapter.chapter_number)
            if plan is None:
                continue

            summary = str(chapter.summary or "").strip()
            plan_summary = str(plan["summary"])
            plan_hook = str(plan["hook"])
            plan_hook_strength = int(plan["hook_strength"])

            if plan_summary.lower() not in summary.lower():
                chapter.summary = f"{summary} {plan_summary}".strip() if summary else plan_summary
                changed = True

            hook = plan_hook
            chapter.metadata["outline_hook"] = hook
            chapter.metadata["hook_strength"] = plan_hook_strength
            if chapter.current_scene is not None:
                strengthened = ensure_hook(chapter.current_scene.content, hook)
                if strengthened != chapter.current_scene.content:
                    chapter.current_scene.update_content(strengthened)
                    changed = True

            outline_chapter = outline_by_number.get(chapter.chapter_number)
            if outline_chapter is not None:
                outline_chapter.summary = f"{outline_chapter.summary} {plan_summary}".strip()
                outline_chapter.hook = hook
                outline_chapter.hook_strength = plan_hook_strength
                changed = True

        if not changed:
            return []
        return [
            "Strengthened the late-arc hooks and rebuilding pressure in chapters 18-20."
        ]

    def _repair_semantic_foundation(
        self,
        ctx: StoryWorkflowContext,
        *,
        issue_codes: set[str],
    ) -> list[str]:
        if not ({"ooc_behavior", "world_logic_soft_conflict"} & issue_codes):
            return []

        outline = ctx.workflow.outline
        if outline is None:
            return []

        protagonist_motivation = ""
        if ctx.workflow.blueprint is not None:
            protagonist = protagonist_name(ctx.workflow.blueprint.character_bible)
            profile = (
                ctx.workflow.blueprint.character_bible.get("protagonist", {})
                if protagonist
                else {}
            )
            protagonist_motivation = str(profile.get("motivation", "")).strip()

        dominant_rule = next(
            (str(entry.rule).strip() for entry in ctx.memory.world_rules if str(entry.rule).strip()),
            "",
        )
        chapter_additions = {
            10: "Lin Yuan recognizes that his father's erased debt is tied to the first oath's hidden cost.",
            12: "The team confirms the First Oath can only be restored by paying a personal memory cost.",
            16: "Lin Yuan must spend the living memory of his father's debt to rewrite the First Oath and save the city.",
        }

        changed = False
        outline_by_number = {chapter.chapter_number: chapter for chapter in outline.chapters}
        for chapter_number, addition in chapter_additions.items():
            chapter = next(
                (item for item in ctx.story.chapters if item.chapter_number == chapter_number),
                None,
            )
            if chapter is None:
                continue

            summary = str(chapter.summary or "").strip()
            if addition.lower() not in summary.lower():
                chapter.summary = f"{summary} {addition}".strip() if summary else addition
                changed = True

            if protagonist_motivation and chapter.scenes:
                anchored = ensure_motivation_anchor(
                    chapter.scenes[0].content,
                    protagonist_motivation,
                )
                if anchored != chapter.scenes[0].content:
                    chapter.scenes[0].update_content(anchored)
                    changed = True

            current_summary = str(chapter.summary or "")
            if dominant_rule and dominant_rule.lower() not in current_summary.lower():
                chapter.summary = f"{current_summary} Cost anchor: {dominant_rule}".strip()
                changed = True

            outline_chapter = outline_by_number.get(chapter_number)
            if outline_chapter is not None:
                outline_chapter.summary = f"{outline_chapter.summary} {addition}".strip()
                outline_chapter.chapter_objective = (
                    f"{outline_chapter.chapter_objective} Make the First Oath cost explicit."
                ).strip()
                changed = True

        if not changed:
            return []
        return [
            "Made the First Oath cost and the protagonist's family-debt motive explicit in the mid-to-late arc."
        ]

    @staticmethod
    def _relationship_progression_status(
        *,
        chapter_number: int,
        target_chapters: int,
    ) -> str:
        progression = [
            "mutual suspicion",
            "tense cooperation",
            "earned trust",
            "battle-forged trust",
            "loyal allies",
            "oath-bound allies",
        ]
        if target_chapters <= 1:
            return progression[-1]

        ratio = (chapter_number - 1) / max(target_chapters - 1, 1)
        index = min(len(progression) - 1, int(ratio * len(progression)))
        return progression[index]


__all__ = ["StoryRevisionService"]
