"""Revision stage for the typed story workflow."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

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
    character_names,
    character_profile,
    ensure_character_anchor,
    ensure_hook,
    ensure_motivation_anchor,
    ensure_payoff_anchor,
    ensure_relationship_anchor,
    extract_world_rules,
    outline_chapter_for_number,
    pov_character_names,
    protagonist_name,
    relationship_progression_status,
)
from src.contexts.narrative.application.services.story_workflow_types import (
    RelationshipSnapshot,
    StoryOutlineArtifact,
    StoryOutlineChapter,
    StoryReviewArtifact,
    StoryReviewIssue,
    WorldRuleLedgerEntry,
)
from src.contexts.narrative.domain.entities.chapter import Chapter

GENERIC_TERMINAL_PLACEHOLDERS = {
    "the public witness",
    "public witness",
    "a public witness",
    "the witness line",
    "witness line",
    "a witness line",
    "the line",
    "the public line",
    "a witness",
    "the witness",
    "witness",
}

GENERIC_TERMINAL_ROLE_TITLES = {
    "guard",
    "keeper",
    "witness",
    "silencer",
    "vessel",
    "echo",
    "line",
    "circle",
    "clerk",
    "scribe",
    "archivist",
    "warden",
    "sentinel",
    "steward",
    "speaker",
    "confessor",
    "record",
    "ledger",
    "oath",
    "rite",
    "banner",
    "watch",
    "herald",
    "custodian",
    "seal",
    "rail",
    "judge",
}


@dataclass(frozen=True)
class TerminalArcSemanticFrame:
    protagonist: str
    primary_keeper: str
    vessel_label: str
    supporting_witnesses: tuple[str, ...]
    continuity_anchor: str
    confirmation_trigger: str
    phase_map: dict[str, int]
    motif_ledger: tuple[str, ...]
    closure_beats: tuple[str, ...]
    public_cost_example: str

    @property
    def supporting_witness(self) -> str:
        for witness in self.supporting_witnesses:
            normalized = " ".join(str(witness).split()).strip()
            if (
                normalized
                and normalized != self.primary_keeper
                and not StoryRevisionService._is_generic_terminal_placeholder(normalized)
                and not StoryRevisionService._is_generic_terminal_role_title(normalized)
            ):
                return normalized
        for fallback in (self.continuity_anchor, self.primary_keeper):
            normalized = " ".join(str(fallback).split()).strip()
            if (
                normalized
                and not StoryRevisionService._is_generic_terminal_placeholder(normalized)
                and not StoryRevisionService._is_generic_terminal_role_title(normalized)
            ):
                return normalized
        return next(
            (
                normalized
                for normalized in (
                    " ".join(str(self.continuity_anchor).split()).strip(),
                    " ".join(str(self.primary_keeper).split()).strip(),
                )
                if normalized
                and not StoryRevisionService._is_generic_terminal_placeholder(normalized)
                and not StoryRevisionService._is_generic_terminal_role_title(normalized)
            ),
            "",
        )

    @property
    def public_witness(self) -> str:
        for witness in self.supporting_witnesses:
            normalized = " ".join(str(witness).split()).strip()
            if (
                normalized
                and normalized not in {self.primary_keeper, self.supporting_witness}
                and not StoryRevisionService._is_generic_terminal_placeholder(normalized)
                and not StoryRevisionService._is_generic_terminal_role_title(normalized)
            ):
                return normalized
        for fallback in (self.supporting_witness, self.continuity_anchor, self.primary_keeper):
            normalized = " ".join(str(fallback).split()).strip()
            if (
                normalized
                and normalized != self.supporting_witness
                and not StoryRevisionService._is_generic_terminal_placeholder(normalized)
                and not StoryRevisionService._is_generic_terminal_role_title(normalized)
            ):
                return normalized
        return next(
            (
                normalized
                for normalized in (
                    " ".join(str(self.supporting_witness).split()).strip(),
                    " ".join(str(self.continuity_anchor).split()).strip(),
                    " ".join(str(self.primary_keeper).split()).strip(),
                )
                if normalized
                and normalized != self.supporting_witness
                and not StoryRevisionService._is_generic_terminal_placeholder(normalized)
                and not StoryRevisionService._is_generic_terminal_role_title(normalized)
            ),
            "",
        )


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
        global_issue_codes = {issue.code for issue in issues}
        issue_context = self._issue_context(issues)
        issue_verbatim_context = self._issue_verbatim_context(issues)
        world_rule_note = self._ensure_world_rule_ledger(ctx, issue_context)
        if world_rule_note:
            repair_notes.append(world_rule_note)
        terminal_arc_rewrite = await self._plan_terminal_arc_revision(
            ctx,
            issues,
            issue_context=issue_context,
        )
        used_terminal_arc_rewrite = bool(terminal_arc_rewrite)
        if used_terminal_arc_rewrite:
            repair_notes.append(
                "Replanned the terminal arc from the judge issue ledger so living keepers carry agency and the public cost stays concrete."
            )
        issue_map: dict[str, list[StoryReviewIssue]] = {}
        for issue in issues:
            if issue.location is None:
                continue
            for chapter_number in self._extract_issue_chapters(issue.location):
                issue_map.setdefault(f"chapter-{chapter_number}", []).append(issue)
            issue_map.setdefault(issue.location, []).append(issue)

        outline = ctx.workflow.outline
        protagonist, allies = self._resolve_cast_labels(ctx)
        blueprint = ctx.workflow.blueprint
        antagonists = (
            set(antagonist_names(blueprint.character_bible))
            if blueprint is not None
            else set()
        )
        departed_characters = self._combined_departed_characters(
            ctx,
            protagonist,
            issue_context=issue_context,
        )
        active_focus_pool = [
            name
            for name in ctx.memory.active_characters
            if name
            and name not in antagonists
            and self._departure_chapter_for_name(name, departed_characters) is None
        ]
        late_arc_numbers = set(self._late_arc_chapter_numbers(ctx.story.chapter_count).values())
        late_arc_custom_focus = set(
            self._late_arc_metadata_candidates(ctx, protagonist, departed_characters)
        )
        for chapter in ctx.story.chapters:
            location = f"chapter-{chapter.chapter_number}"
            chapter_issues = issue_map.get(location, [])
            chapter_plan = terminal_arc_rewrite.get(chapter.chapter_number)
            if not chapter_issues and chapter_plan is None:
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
            chapter_issue_codes = {issue.code for issue in chapter_issues}
            outline_model_chapter = (
                next(
                    (item for item in outline.chapters if item.chapter_number == chapter.chapter_number),
                    None,
                )
                if outline is not None
                else None
            )
            if chapter_plan:
                planned_summary = str(chapter_plan.get("summary", "")).strip()
                planned_objective = str(chapter_plan.get("objective", "")).strip()
                planned_hook = str(chapter_plan.get("hook", "")).strip()
                planned_focus_character = str(
                    chapter_plan.get("focus_character", "")
                ).strip()
                planned_target = str(
                    chapter_plan.get("relationship_target", "")
                ).strip()
                planned_status = str(
                    chapter_plan.get("relationship_status", "")
                ).strip()
                if planned_summary and chapter.summary != planned_summary:
                    chapter.summary = planned_summary
                    repair_notes.append(
                        f"Replanned the terminal phase summary for chapter {chapter.chapter_number}."
                    )
                if planned_objective:
                    chapter.metadata["chapter_objective"] = planned_objective
                if planned_hook:
                    chapter.metadata["outline_hook"] = planned_hook
                if planned_focus_character:
                    chapter.metadata["focus_character"] = planned_focus_character
                if planned_target:
                    chapter.metadata["relationship_target"] = planned_target
                if planned_status:
                    chapter.metadata["relationship_status"] = planned_status
                if outline_model_chapter is not None:
                    if planned_summary:
                        outline_model_chapter.summary = planned_summary
                    if planned_objective:
                        outline_model_chapter.chapter_objective = planned_objective
                    if planned_hook:
                        outline_model_chapter.hook = planned_hook
                chapter_spec = {
                    "chapter_number": chapter.chapter_number,
                    "title": chapter.title,
                    "summary": planned_summary
                    or chapter.summary
                    or str(chapter_spec.get("summary", "")),
                    "chapter_objective": planned_objective
                    or str(chapter.metadata.get("chapter_objective", "")).strip(),
                    "hook": planned_hook
                    or str(chapter.metadata.get("outline_hook", "")).strip(),
                }

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
                and active_focus_pool
                and focus_character not in set(active_focus_pool)
                and not (
                    chapter.chapter_number in late_arc_numbers
                    and focus_character in late_arc_custom_focus
                )
            ):
                focus_character = active_focus_pool[
                    (chapter.chapter_number - 1) % len(active_focus_pool)
                ]
                chapter.metadata["focus_character"] = focus_character
                repair_notes.append(
                    f"Reassigned the focus character for chapter {chapter.chapter_number}."
                )

            if not focus_character and active_focus_pool:
                focus_character = active_focus_pool[
                    (chapter.chapter_number - 1) % len(active_focus_pool)
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
            if focus_character and not focus_motivation:
                resolved_motivation = self._focus_motivation_for_character(
                    ctx,
                    chapter_number=chapter.chapter_number,
                    focus_character=focus_character,
                )
                if resolved_motivation:
                    focus_motivation = resolved_motivation
                    chapter.metadata["focus_motivation"] = focus_motivation

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
                chapter_issue_codes
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
            needs_scene_regen = needs_scene_regen or chapter_plan is not None
            if needs_scene_regen:
                scene_result = await self._drafting_service._generate_chapter_scenes(
                    ctx=ctx,
                    chapter_spec={
                        "chapter_number": chapter.chapter_number,
                        "title": chapter.title,
                        "summary": chapter.summary or str(chapter_spec.get("summary", "")),
                        "chapter_objective": str(
                            chapter.metadata.get(
                                "chapter_objective",
                                chapter_spec.get("chapter_objective", ""),
                            )
                        ).strip(),
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
                        "summary": chapter.summary or str(chapter_spec.get("summary", "")),
                        "chapter_objective": str(
                            chapter.metadata.get(
                                "chapter_objective",
                                chapter_spec.get("chapter_objective", ""),
                            )
                        ).strip(),
                        "hook": str(chapter_spec.get("hook", "")),
                    },
                    allow_empty_scene_salvage=True,
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

            if chapter.scenes and "missing_hook_payoff" in chapter_issue_codes:
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

            if chapter.current_scene and chapter_issue_codes & {"missing_hook", "weak_hook"}:
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

            if chapter.current_scene and "missing_outline_hook" in chapter_issue_codes:
                hook = self._repair_hook(chapter_spec, chapter)
                if outline is not None:
                    for outline_node in outline.chapters:
                        if outline_node.chapter_number == chapter.chapter_number:
                            outline_node.hook = hook
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

        repair_notes.extend(
            self._repair_semantic_relationship_arc(
                ctx,
                issue_codes=global_issue_codes,
                issue_context=issue_context,
            )
        )
        if not used_terminal_arc_rewrite:
            repair_notes.extend(
                self._repair_semantic_final_arc(
                    ctx,
                    issue_codes=global_issue_codes,
                    issue_context=issue_context,
                )
            )
            repair_notes.extend(
                self._repair_semantic_foundation(
                    ctx,
                    issue_codes=global_issue_codes,
                    issue_context=issue_context,
                )
            )
            repair_notes.extend(
                self._repair_semantic_plot_clarity(
                    ctx,
                    issue_codes=global_issue_codes,
                    issue_context=issue_context,
                )
            )
            repair_notes.extend(
                self._repair_semantic_promise_payoff(
                    ctx,
                    issue_codes=global_issue_codes,
                    issue_context=issue_context,
                )
            )
        else:
            normalized_terminal_surface = self._sanitize_storycraft_language(ctx)
            clarified_terminal_phases = self._enforce_terminal_arc_phase_clarity(
                ctx,
                issue_context=issue_context,
                issue_verbatim_context=issue_verbatim_context,
            )
            if normalized_terminal_surface:
                repair_notes.append(
                    "Normalized terminal-arc role language and surface prose after the judge-driven rewrite."
                )
            if clarified_terminal_phases:
                repair_notes.append(
                    "Clarified terminal-arc aftermath, farewell, and reckoning beats after the judge-driven rewrite."
                )
        repair_notes.extend(
            self._repair_departed_character_cleanup(ctx, issue_context=issue_context)
        )
        repair_notes.extend(
            self._repair_relationship_metadata_integrity(
                ctx,
                issue_context=issue_context,
            )
        )
        repair_notes.extend(self._repair_structural_hooks(ctx))
        repair_notes.extend(self._repair_focus_character_presence(ctx))
        repair_notes.extend(self._repair_placeholder_promises(ctx))
        if used_terminal_arc_rewrite and ctx.workflow.outline is not None:
            self._compact_live_late_arc_summaries(
                ctx,
                ctx.workflow.outline,
                issue_codes=global_issue_codes,
                issue_context=issue_context,
            )
            protagonist, allies = self._resolve_cast_labels(ctx)
            keeper_pool = self._resolve_late_arc_keeper_pool(
                ctx,
                protagonist,
                allies,
                issue_context=issue_context,
            )
            primary_keeper = keeper_pool[0] if keeper_pool else protagonist
            vessel_label = self._resolve_terminal_vessel_label(
                ctx,
                protagonist,
                primary_keeper=primary_keeper,
            )
            self._finalize_terminal_arc_surface(
                ctx,
                protagonist=protagonist,
                primary_keeper=primary_keeper,
                vessel_label=vessel_label,
            )
        self._drafting_service.synchronize_memory(ctx)
        return repair_notes

    async def _plan_terminal_arc_revision(
        self,
        ctx: StoryWorkflowContext,
        issues: list[StoryReviewIssue],
        *,
        issue_context: str,
    ) -> dict[int, dict[str, str]]:
        if not self._should_plan_terminal_arc_revision(
            ctx,
            issues,
            issue_context=issue_context,
        ):
            return {}

        blueprint = ctx.workflow.blueprint
        outline = ctx.workflow.outline
        frame = self._build_terminal_arc_semantic_frame(
            ctx,
            issue_context=issue_context,
        )
        protagonist = frame.protagonist
        cast_names = (
            set(character_names(blueprint.character_bible))
            if blueprint is not None
            else set()
        )
        continuity_anchor = frame.continuity_anchor
        primary_keeper = frame.primary_keeper
        vessel_label = frame.vessel_label
        supporting_witness = frame.supporting_witness
        public_witness = frame.public_witness
        confirmation_trigger = frame.confirmation_trigger
        phases = frame.phase_map
        phase_nodes: list[dict[str, Any]] = []
        for phase, chapter_number in phases.items():
            chapter = next(
                (item for item in ctx.story.chapters if item.chapter_number == chapter_number),
                None,
            )
            outline_entry = outline_chapter_for_number(outline, chapter_number) if outline else None
            phase_nodes.append(
                {
                    "phase": phase,
                    "chapter_number": chapter_number,
                    "story_summary": chapter.summary if chapter is not None else "",
                    "scene_excerpt": (
                        chapter.current_scene.content if chapter is not None and chapter.current_scene is not None else ""
                    ),
                    "outline_summary": outline_entry.get("summary", "") if isinstance(outline_entry, dict) else "",
                    "outline_objective": (
                        outline_entry.get("chapter_objective", "") if isinstance(outline_entry, dict) else ""
                    ),
                    "outline_hook": outline_entry.get("hook", "") if isinstance(outline_entry, dict) else "",
                }
            )

        recent_relationships = [
            snapshot.to_dict()
            for snapshot in ctx.memory.relationship_states
            if snapshot.chapter_number >= min(phases.values())
        ][-8:]
        world_rules = [entry.rule for entry in ctx.memory.world_rules][-8:]
        task = TextGenerationTask(
            step="terminal_arc_revision",
            system_prompt=(
                "You repair the terminal arc of a commercial serialized novel. "
                "Use generic role logic, not story-specific trivia. "
                "Output a structured rewrite plan for the final five phases: sacrifice, aftermath, "
                "rule_revelation, public_reckoning, closure. "
                "Once a vessel state exists, intentional action must stay with living keepers or witnesses. "
                "Keep the vessel passive. If the vessel moves at all, describe it as only an old trained motion or a brief reflex; never as instinct, intention, or returning consciousness. "
                "Make public cost concrete, closure three-beat, and prose non-repetitive."
            ),
            user_prompt=(
                f"Story title: {ctx.story.title}\n"
                f"Premise: {ctx.workflow.premise}\n"
                f"Review issues: {[issue.to_dict() for issue in issues]}\n"
                f"Role slots: protagonist={protagonist}, primary_keeper={primary_keeper}, supporting_witness={supporting_witness}, public_witness={public_witness}, vessel_label={vessel_label}\n"
                f"Continuity anchor: {continuity_anchor or 'none'}\n"
                f"Confirmation trigger: {confirmation_trigger}\n"
                f"World rules: {world_rules}\n"
                f"Motif ledger: {list(frame.motif_ledger)}\n"
                f"Closure beats: {list(frame.closure_beats)}\n"
                f"Public cost example: {frame.public_cost_example}\n"
                f"Recent relationship states: {recent_relationships}\n"
                f"Late arc nodes: {phase_nodes}\n"
                f"Cast names: {sorted(cast_names)}\n"
                "Return a generic terminal-arc rewrite plan that resolves actor attribution, vessel agency, closure spacing, and abstract public-cost problems without hardcoding to one named story. "
                "If the continuity anchor is alive during the sacrifice and aftermath phases, keep that character visible in the final arc or explicitly resolve their fate. "
                "Show one failed public attempt before organized resistance stabilizes. "
                "Give the aftermath a quiet private beat before the witness interruption so grief can register before duty resumes. "
                "Split the public reckoning into a physical crisis beat and a ritual resolution beat, with a clear pause between them. "
                "Before closure begins, leave one full beat of silence after the public reckoning so the first private scene can carry a reflection on the vessel's silence. "
                "Use a recurring sensory motif such as the scratch of ink drying to connect the public reckoning, the private reflection, and the ledger scene. "
                "Use explicit time jumps such as 'By noon,' 'By dusk,' or 'By night' between the private, public, and ledger scenes. "
                "Finish any farewell or dissolving-witness beat inside public_reckoning so closure can focus on aftermath. "
                "In closure, include one witness interaction grounded in a concrete remembered detail from the protagonist's earlier life."
            ),
            response_schema={
                "revision_notes": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "chapters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "chapter_number": {"type": "integer"},
                            "phase": {"type": "string"},
                            "summary": {"type": "string"},
                            "objective": {"type": "string"},
                            "hook": {"type": "string"},
                            "focus_character": {"type": "string"},
                            "relationship_target": {"type": "string"},
                            "relationship_status": {"type": "string"},
                            "scene_brief": {"type": "string"},
                        },
                    },
                },
            },
            temperature=0.2,
            metadata={
                "story_id": str(ctx.story.id),
                "target_chapters": ctx.story.chapter_count,
                "protagonist": protagonist,
                "primary_keeper": primary_keeper,
                "supporting_witness": supporting_witness,
                "public_witness": public_witness,
                "vessel_label": vessel_label,
                "continuity_anchor": continuity_anchor,
                "confirmation_trigger": confirmation_trigger,
                "issues": [issue.to_dict() for issue in issues],
                "late_arc_nodes": phase_nodes,
                "motif_ledger": list(frame.motif_ledger),
                "closure_beats": list(frame.closure_beats),
                "public_cost_example": frame.public_cost_example,
            },
        )
        try:
            result = await ctx.provider.generate_structured(task)
        except Exception:
            return {}
        ctx.record_generation_trace(result)
        return self._extract_terminal_arc_rewrite_plan(
            result,
            phases=phases,
            protagonist=protagonist,
            primary_keeper=primary_keeper,
            supporting_witness=supporting_witness,
            public_witness=public_witness,
            vessel_label=vessel_label,
            continuity_anchor=continuity_anchor,
            confirmation_trigger=confirmation_trigger,
            cast_names=cast_names,
            motif_ledger=frame.motif_ledger,
            closure_beats=frame.closure_beats,
            public_cost_example=frame.public_cost_example,
        )

    def _extract_terminal_arc_rewrite_plan(
        self,
        result: TextGenerationResult,
        *,
        phases: dict[str, int],
        protagonist: str,
        primary_keeper: str,
        supporting_witness: str,
        public_witness: str,
        vessel_label: str,
        continuity_anchor: str,
        confirmation_trigger: str,
        cast_names: set[str],
        motif_ledger: tuple[str, ...] = (),
        closure_beats: tuple[str, ...] = (),
        public_cost_example: str = "",
    ) -> dict[int, dict[str, str]]:
        payload = result.content if isinstance(result.content, dict) else {}
        raw_chapters = payload.get("chapters")
        raw_chapters = raw_chapters if isinstance(raw_chapters, list) else []

        phase_by_number = {chapter_number: phase for phase, chapter_number in phases.items()}
        allowed_numbers = set(phase_by_number)
        sacrifice_number = phases.get("sacrifice")
        plan: dict[int, dict[str, str]] = {
            chapter_number: self._default_terminal_arc_phase_plan(
                phase=phase,
                chapter_number=chapter_number,
                protagonist=protagonist,
                primary_keeper=primary_keeper,
                supporting_witness=supporting_witness,
                public_witness=public_witness,
                vessel_label=vessel_label,
                continuity_anchor=continuity_anchor,
                confirmation_trigger=confirmation_trigger,
                motif_ledger=motif_ledger,
                closure_beats=closure_beats,
                public_cost_example=public_cost_example,
            )
            for chapter_number, phase in phase_by_number.items()
        }
        for item in raw_chapters:
            if not isinstance(item, dict):
                continue
            try:
                chapter_number = int(item.get("chapter_number", 0) or 0)
            except (TypeError, ValueError):
                continue
            if chapter_number not in allowed_numbers:
                continue
            phase = phase_by_number[chapter_number]
            summary = str(item.get("summary", "")).strip()
            objective = str(item.get("objective", "")).strip()
            hook = str(item.get("hook", "")).strip()
            focus_character = self._canonicalize_character_name(
                str(item.get("focus_character", "")).strip(),
                cast_names,
            )
            if focus_character not in cast_names:
                focus_character = ""
            if not focus_character:
                focus_character = protagonist if chapter_number == sacrifice_number else primary_keeper
            if chapter_number != sacrifice_number and focus_character in {protagonist, vessel_label}:
                focus_character = primary_keeper
            relationship_target = str(item.get("relationship_target", "")).strip()
            relationship_target = self._normalize_vessel_target_label(
                relationship_target,
                cast_names,
            )
            relationship_status = str(item.get("relationship_status", "")).strip()
            planned = self._default_terminal_arc_phase_plan(
                phase=phase,
                chapter_number=chapter_number,
                protagonist=protagonist,
                primary_keeper=primary_keeper,
                supporting_witness=supporting_witness,
                public_witness=public_witness,
                vessel_label=vessel_label,
                continuity_anchor=continuity_anchor,
                confirmation_trigger=confirmation_trigger,
                motif_ledger=motif_ledger,
                closure_beats=closure_beats,
                public_cost_example=public_cost_example,
            )
            if summary and not self._looks_authorial_terminal_summary(summary):
                planned["summary"] = summary
            if objective:
                planned["objective"] = objective
            if hook:
                planned["hook"] = hook
            planned["focus_character"] = focus_character
            if relationship_target:
                planned["relationship_target"] = relationship_target
            if relationship_status:
                planned["relationship_status"] = relationship_status
            plan[chapter_number] = planned
        return plan

    def _default_terminal_arc_phase_plan(
        self,
        *,
        phase: str,
        chapter_number: int,
        protagonist: str,
        primary_keeper: str,
        supporting_witness: str,
        public_witness: str,
        vessel_label: str,
        continuity_anchor: str,
        confirmation_trigger: str,
        motif_ledger: tuple[str, ...] = (),
        closure_beats: tuple[str, ...] = (),
        public_cost_example: str = "",
    ) -> dict[str, str]:
        late_arc_exclusions = {primary_keeper, protagonist, vessel_label}

        def distinct_terminal_name(
            *candidates: str,
            fallback: str = "",
            extra_exclusions: set[str] | None = None,
        ) -> str:
            exclusions = set(late_arc_exclusions)
            if extra_exclusions:
                exclusions.update(
                    normalized
                    for normalized in (
                        " ".join(str(item).split()).strip() for item in extra_exclusions
                    )
                    if normalized
                )
            for candidate in candidates:
                normalized = " ".join(str(candidate).split()).strip()
                if (
                    normalized
                    and normalized not in exclusions
                    and not self._is_generic_terminal_placeholder(normalized)
                    and not self._is_generic_terminal_role_title(normalized)
                ):
                    return normalized
            fallback_normalized = " ".join(str(fallback).split()).strip()
            if (
                fallback_normalized
                and fallback_normalized not in exclusions
                and not self._is_generic_terminal_placeholder(fallback_normalized)
                and not self._is_generic_terminal_role_title(fallback_normalized)
            ):
                return fallback_normalized
            return ""

        def display_terminal_name(*candidates: str) -> str:
            for candidate in candidates:
                normalized = " ".join(str(candidate).split()).strip()
                if (
                    normalized
                    and not self._is_generic_terminal_placeholder(normalized)
                    and not self._is_generic_terminal_role_title(normalized)
                ):
                    return normalized
            return ""

        living_anchor = distinct_terminal_name(
            continuity_anchor,
            supporting_witness,
            public_witness,
            fallback=primary_keeper,
        )
        if not living_anchor:
            living_anchor = primary_keeper or continuity_anchor or supporting_witness or public_witness
        sacrifice_witness = distinct_terminal_name(
            continuity_anchor,
            supporting_witness,
            public_witness,
            fallback=living_anchor or primary_keeper,
        )
        if sacrifice_witness == protagonist:
            sacrifice_witness = distinct_terminal_name(
                supporting_witness,
                public_witness,
                continuity_anchor,
                fallback=living_anchor or primary_keeper,
            )
        if sacrifice_witness == protagonist:
            sacrifice_witness = living_anchor or primary_keeper
        visible_witness = distinct_terminal_name(
            public_witness,
            supporting_witness,
            continuity_anchor,
            fallback=living_anchor or primary_keeper,
        )
        second_witness = distinct_terminal_name(
            supporting_witness,
            continuity_anchor,
            public_witness,
            fallback=living_anchor or primary_keeper,
            extra_exclusions={visible_witness},
        )
        if second_witness == visible_witness:
            second_witness = distinct_terminal_name(
                continuity_anchor,
                supporting_witness,
                public_witness,
                fallback=living_anchor or primary_keeper,
                extra_exclusions={visible_witness},
            )
        if second_witness == visible_witness:
            for candidate in (
                primary_keeper,
                living_anchor,
                continuity_anchor,
                supporting_witness,
                public_witness,
            ):
                normalized = " ".join(str(candidate).split()).strip()
                if (
                    normalized
                    and normalized != visible_witness
                    and not self._is_generic_terminal_placeholder(normalized)
                ):
                    second_witness = normalized
                    break
        if not visible_witness:
            visible_witness = living_anchor or primary_keeper
        if second_witness == visible_witness:
            for candidate in (
                supporting_witness,
                public_witness,
                continuity_anchor,
                living_anchor,
                primary_keeper,
                protagonist,
            ):
                normalized = " ".join(str(candidate).split()).strip()
                if (
                    normalized
                    and normalized != visible_witness
                    and not self._is_generic_terminal_placeholder(normalized)
                    and not self._is_generic_terminal_role_title(normalized)
                ):
                    second_witness = normalized
                    break
        if second_witness == visible_witness:
            second_witness = ""
        motif_anchor = motif_ledger[0] if motif_ledger else "the public record"
        public_cost_clause = (
            public_cost_example
            or "the new cost landing on ordinary people in public instead of hiding behind the dead"
        )
        closure_sequence = ", ".join(
            closure_beats or ("private closure", "public confession", "lasting aftermath")
        )
        if second_witness:
            public_sequence_clause = f"{visible_witness} tastes metal and {second_witness} closes the gap"
            public_move_clause = f"{visible_witness} and {second_witness} make the first public move"
        else:
            public_sequence_clause = f"{visible_witness} tastes metal and the crowd holds the line"
            public_move_clause = f"{visible_witness} makes the first public move"
        handoff_recipient = distinct_terminal_name(
            continuity_anchor,
            supporting_witness,
            public_witness,
            fallback="",
            extra_exclusions={protagonist},
        )
        if not handoff_recipient:
            handoff_recipient = distinct_terminal_name(
                sacrifice_witness,
                visible_witness,
                second_witness,
                living_anchor,
                fallback="",
                extra_exclusions={protagonist},
            )
        if not handoff_recipient:
            handoff_recipient = sacrifice_witness or visible_witness or second_witness or living_anchor or primary_keeper
        living_anchor = display_terminal_name(
            living_anchor,
            primary_keeper,
            continuity_anchor,
            supporting_witness,
            public_witness,
            protagonist,
        ) or protagonist or primary_keeper or continuity_anchor or supporting_witness or public_witness
        primary_keeper = display_terminal_name(
            primary_keeper,
            living_anchor,
            continuity_anchor,
            supporting_witness,
            public_witness,
            protagonist,
        ) or protagonist or living_anchor or continuity_anchor
        sacrifice_witness = display_terminal_name(
            sacrifice_witness,
            handoff_recipient,
            living_anchor,
            primary_keeper,
            continuity_anchor,
            supporting_witness,
            public_witness,
            protagonist,
        ) or protagonist or primary_keeper or living_anchor
        visible_witness = display_terminal_name(
            visible_witness,
            supporting_witness,
            continuity_anchor,
            living_anchor,
            primary_keeper,
            public_witness,
            protagonist,
        ) or protagonist or primary_keeper or living_anchor
        second_witness = display_terminal_name(
            second_witness,
            visible_witness,
            supporting_witness,
            continuity_anchor,
            living_anchor,
            primary_keeper,
            protagonist,
        ) or protagonist or primary_keeper or visible_witness or living_anchor
        handoff_recipient = display_terminal_name(
            handoff_recipient,
            sacrifice_witness,
            visible_witness,
            second_witness,
            living_anchor,
            primary_keeper,
            protagonist,
        ) or protagonist or primary_keeper or sacrifice_witness or living_anchor
        if phase == "sacrifice":
            return {
                "summary": (
                    f"{protagonist} makes the final choice in full view of {sacrifice_witness}, "
                    f"{protagonist} places a marked token into {handoff_recipient}'s hand before stepping away, and the next duty settles on {handoff_recipient} through visible preparation."
                ),
                "objective": (
                    f"{protagonist}'s final choice lands in full view of {sacrifice_witness}, {protagonist} places a marked token into {handoff_recipient}'s hand before stepping away, and the next duty moves to {handoff_recipient} through visible preparation."
                ),
                "hook": (
                    f"{confirmation_trigger} confirms the old life cannot return unchanged, and the marked token reaching {handoff_recipient} makes the handoff visible."
                ),
                "focus_character": protagonist,
                "relationship_target": self._resolve_terminal_relationship_target(
                    protagonist,
                    handoff_recipient,
                    living_anchor,
                    primary_keeper,
                    continuity_anchor,
                    sacrifice_witness,
                ),
                "relationship_status": "final living handoff before the irreversible cost",
            }
        if phase == "aftermath":
            return {
                "summary": (
                    f"After the sacrifice, the marked token reaches {primary_keeper} at the first private break while rain taps the eaves and the rail stays cold in the palm. A cold answer from the seal jars {primary_keeper}'s hand off the rail, the frame cracks one line wider, and a draft slams the shutters before {primary_keeper} can take another step. "
                    f"{primary_keeper} already knows the return failed before reaching for {vessel_label}, so the touch reads as a final goodbye rather than a rescue. A pulse of winter-blue ink curls across the ledger and points toward the next choice while {visible_witness} cuts in with one blunt question, and the public record keeps the city's debt ahead of private grief. "
                    f"The seal's hard answer proves the old life is gone for good."
                ),
                "objective": (
                    f"{primary_keeper} reaches for {vessel_label}, finds only cold weight, and lets grief tighten into duty while the marked token and the seal keep the loss visible. A pulse of winter-blue ink marks the next choice on the ledger, {visible_witness} interrupts the silence, and the room stays rooted in the city's debt instead of the old return."
                ),
                "hook": f"{confirmation_trigger} points toward the buried rule tied to {motif_anchor}, and the rail gives one cold physical answer in {primary_keeper}'s hand before the room settles.",
                "focus_character": primary_keeper,
                "relationship_target": self._resolve_terminal_relationship_target(
                    primary_keeper,
                    visible_witness,
                    supporting_witness,
                    living_anchor,
                    vessel_label,
                ),
                "relationship_status": "keeper choosing the city's debt over private grief",
            }
        if phase == "rule_revelation":
            return {
                "summary": (
                    f"An early attempt to stabilize the aftermath fails under lamp heat and chalk dust. Then {primary_keeper} and {supporting_witness or living_anchor} uncover concrete evidence tied to {motif_anchor}, and the lost rule cracks through the wall before it can spread. "
                    f"{vessel_label} gives one brief residual shiver and then goes still without any hint that a mind has returned. "
                    f"{supporting_witness or living_anchor} reads the reflex as memorial proof rather than a reply, and breaks visibly at the ledger edge."
                ),
                "objective": f"Concrete evidence makes the rule legible through visible sequence and consequence. The first response fails in view of {supporting_witness or living_anchor}, the vessel contact stays proof rather than interior life or restored consciousness, and one sharp look or spoken line interrupts the motion. The proof reads as a residual shiver, lamp flicker, or last trained residue, never as conscious return.",
                "hook": "Once the living understand the rule, the confession has to leave the room and survive public pressure, with the evidence still warm from the lamp.",
                "focus_character": primary_keeper,
                "relationship_target": self._resolve_terminal_relationship_target(
                    primary_keeper,
                    supporting_witness,
                    living_anchor,
                    continuity_anchor,
                    vessel_label,
                ),
                "relationship_status": "keeper aligning the public record around hard evidence",
            }
        if phase == "public_reckoning":
            return {
                "summary": (
                    f"Wind drives rain across the square, a loose banner snaps overhead, and a guarded figure stands under watch while the crowd keeps shifting around the still vessel. {public_sequence_clause}. "
                    f"{primary_keeper} names the mechanism out loud and writes the final entry once while {supporting_witness or visible_witness} takes the still hand of {vessel_label} and presses it to the ledger before the ritual seal lands. "
                    f"{supporting_witness or visible_witness} reacts to the chalk mark or lost name with a visible flinch, and the living contact stays physical at the ledger edge. "
                    f"{vessel_label} remains a mute shape at the edge of the crowd while the burned names darken on the ledger and the lantern glass cracks once. "
                    f"By the end of the scene, one living hand is still on the record and the new order has a human shape."
                ),
                "objective": f"The reckoning unfolds in two beats with an explicit pause between them: first the surge and line break, then the naming and sealing. {public_move_clause}, and the guarded figure faces the square while {primary_keeper} names the mechanism. {supporting_witness or visible_witness} physically touches the still hand of {vessel_label} before the seal lands, and {vessel_label} remains a mute shape at the ledger edge.",
                "hook": "A fresh black seal on the ledger gives the conflict a visible shape before the city can confess what it owes in daylight, and the square feels the cost in its teeth.",
                "focus_character": primary_keeper,
                "relationship_target": self._resolve_terminal_relationship_target(
                    primary_keeper,
                    visible_witness,
                    second_witness,
                    living_anchor,
                    vessel_label,
                ),
                "relationship_status": "living witnesses carrying the public reckoning together",
            }
        return {
            "summary": (
                f"{visible_witness} names one ordinary detail from the life now gone, and the corridor window shudders in a fresh gust while {primary_keeper} keeps the ledger line in view. "
                f"By night, as the crowd shifts back from the square and the first hands lower from the seal, {public_move_clause}, and a small ordinary task resumes to show the city still belongs to the living. "
                f"By dawn, after the walk to the ledger room and the last bell in the hall, {primary_keeper} writes the final entry once before passing the record forward, and {public_cost_clause} while {vessel_label} remains a cold presence. "
                f"Before the page dries, {visible_witness} speaks the new name aloud into winter-blue ink, the blank page takes it, the lamp flame gutters, and the room admits the leak before the ink dries. {closure_sequence}."
            ),
            "objective": (
                f"Private grief, public confession, and the final ledger handoff stay distinct: {visible_witness} names a remembered detail from the earlier life, the city carries the rule in daylight without collapsing into one explanation block, and {primary_keeper} completes the closing entry while the room watches a visible anomaly instead of a metaphor. The vessel remains a cold presence, the living answer the cost in public, and the ending keeps its beats separate."
            ),
            "hook": "At dawn, the blank page takes a name in winter-blue ink, the lamp flame gutters, and the colder room proves the rewritten rule is permanent instead of ghostly.",
            "focus_character": primary_keeper,
            "relationship_target": self._resolve_terminal_relationship_target(
                primary_keeper,
                visible_witness,
                second_witness,
                living_anchor,
                vessel_label,
            ),
            "relationship_status": "living line confirming the lasting public debt",
        }

    def _should_plan_terminal_arc_revision(
        self,
        ctx: StoryWorkflowContext,
        issues: list[StoryReviewIssue],
        *,
        issue_context: str,
    ) -> bool:
        if ctx.story.chapter_count < 5:
            return False
        issue_codes = {issue.code for issue in issues}
        if {
            "plot_confusion",
            "world_logic_soft_conflict",
            "ooc_behavior",
            "weak_serial_pull",
            "promise_break",
            "relationship_progression_stall",
        } & issue_codes:
            return True
        lowered_context = issue_context.lower()
        return any(
            token in lowered_context
            for token in (
                "terminal-arc",
                "terminal arc",
                "vessel",
                "shell",
                "sacrifice",
                "closure",
                "fee mark",
                "memory tax",
                "public cost",
                "relationship states",
            )
        )

    def _resolve_terminal_arc_confirmation_trigger(
        self,
        ctx: StoryWorkflowContext,
    ) -> str:
        combined_rules = " ".join(
            str(entry.rule).strip().lower()
            for entry in ctx.memory.world_rules
            if str(entry.rule).strip()
        )
        if "knock" in combined_rules and any(
            token in combined_rules for token in ("seal", "gate", "oath", "ledger")
        ):
            return "the first hard answer from the seal"
        if any(token in combined_rules for token in ("seal", "gate", "ledger", "oath")):
            return "the first hard answer from the old rule"
        return "the first hard answer that the sacrifice was accepted"

    def _resolve_terminal_arc_continuity_anchor(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
        allies: list[str],
        *,
        issue_context: str = "",
    ) -> str:
        departed_characters = self._combined_departed_characters(
            ctx,
            protagonist,
            issue_context=issue_context,
        )
        blueprint = ctx.workflow.blueprint
        cast_names = (
            set(character_names(blueprint.character_bible))
            if blueprint is not None
            else set()
        )
        excluded_markers = self._late_arc_excluded_markers(
            ctx,
            protagonist,
            cast_names,
        )
        surviving_allies = [
            name
            for name in self._resolve_surviving_allies(
                ctx,
                protagonist,
                allies,
                issue_context=issue_context,
            )
            if name
            and name != protagonist
            and not self._is_symbolic_late_arc_candidate(name)
            and not self._is_generic_terminal_role_title(name)
            and self._departure_chapter_for_name(name, departed_characters) is None
            and not self._is_restrained_late_arc_candidate(
                ctx,
                name,
                cast_names=cast_names,
            )
            and not self._is_late_arc_excluded_candidate(
                name,
                cast_names=cast_names,
                excluded_markers=excluded_markers,
            )
        ]
        if not surviving_allies:
            return ""

        phases = self._terminal_phase_numbers(ctx.story.chapter_count)
        anchor_window = {
            max(1, phases["sacrifice"] - 1),
            phases["sacrifice"],
            phases["aftermath"],
            phases["rule_revelation"],
        }
        scores: dict[str, int] = {name: 0 for name in surviving_allies}

        def score(candidate: str, weight: int) -> None:
            normalized = self._canonicalize_character_name(
                self._normalize_protagonist_name_drift(
                    str(candidate).strip(),
                    protagonist,
                    cast_names,
                ),
                cast_names,
            )
            if normalized in scores:
                scores[normalized] += weight

        for chapter in ctx.story.chapters:
            if chapter.chapter_number not in anchor_window:
                continue
            score(str(chapter.metadata.get("focus_character", "")), 42)
            score(str(chapter.metadata.get("relationship_target", "")), 28)

        for summary in ctx.memory.chapter_summaries:
            if summary.chapter_number not in anchor_window:
                continue
            score(summary.focus_character, 24)

        for relationship_state in ctx.memory.relationship_states:
            if relationship_state.chapter_number not in anchor_window:
                continue
            score(relationship_state.source, 36)
            score(relationship_state.target, 20)

        outline = ctx.workflow.outline
        if outline is not None:
            outline_by_number = {
                chapter.chapter_number: chapter
                for chapter in outline.chapters
                if chapter.chapter_number in anchor_window
            }
            for canonical_name in surviving_allies:
                aliases = {
                    alias.lower()
                    for alias in (
                        self._character_detection_aliases(canonical_name)
                        + self._character_reference_aliases(canonical_name)
                    )
                    if alias
                }
                if not aliases:
                    continue
                for outline_chapter in outline_by_number.values():
                    combined_text = " ".join(
                        part
                        for part in (
                            outline_chapter.summary,
                            outline_chapter.chapter_objective,
                            outline_chapter.hook,
                        )
                        if part
                    ).lower()
                    if any(alias in combined_text for alias in aliases):
                        score(canonical_name, 16)

        for name in ctx.memory.active_characters:
            score(name, 6)

        return max(
            surviving_allies,
            key=lambda name: (scores.get(name, 0), -surviving_allies.index(name)),
        )

    @staticmethod
    def _terminal_phase_numbers(target_chapters: int) -> dict[str, int]:
        return {
            "sacrifice": max(1, target_chapters - 4),
            "aftermath": max(1, target_chapters - 3),
            "rule_revelation": max(1, target_chapters - 2),
            "public_reckoning": max(1, target_chapters - 1),
            "closure": max(1, target_chapters),
        }

    def _build_terminal_arc_semantic_frame(
        self,
        ctx: StoryWorkflowContext,
        *,
        issue_context: str = "",
    ) -> TerminalArcSemanticFrame:
        protagonist, allies = self._resolve_cast_labels(ctx)
        continuity_anchor = self._resolve_terminal_arc_continuity_anchor(
            ctx,
            protagonist,
            allies,
            issue_context=issue_context,
        )
        keeper_pool = self._resolve_late_arc_keeper_pool(
            ctx,
            protagonist,
            allies,
            issue_context=issue_context,
        )
        primary_keeper = keeper_pool[0] if keeper_pool else protagonist
        supporting_witness = self._resolve_late_arc_supporting_witness(
            ctx,
            protagonist,
            primary_keeper,
            issue_context=issue_context,
        )
        public_witness = self._resolve_late_arc_public_witness(
            ctx,
            protagonist,
            primary_keeper,
            supporting_witness,
            issue_context=issue_context,
        )
        witness_slots = tuple(
            dict.fromkeys(
                candidate
                for candidate in (
                    supporting_witness,
                    public_witness,
                    continuity_anchor,
                )
                if candidate and candidate not in {protagonist, primary_keeper}
            )
        )
        confirmation_trigger = self._resolve_terminal_arc_confirmation_trigger(ctx)
        vessel_label = self._resolve_terminal_vessel_label(
            ctx,
            protagonist,
            primary_keeper=primary_keeper,
        )
        phase_map = self._terminal_phase_numbers(ctx.story.chapter_count)
        motif_ledger = self._resolve_terminal_arc_motif_ledger(
            ctx,
            protagonist=protagonist,
            primary_keeper=primary_keeper,
            supporting_witnesses=witness_slots,
            confirmation_trigger=confirmation_trigger,
        )
        return TerminalArcSemanticFrame(
            protagonist=protagonist,
            primary_keeper=primary_keeper,
            vessel_label=vessel_label,
            supporting_witnesses=witness_slots,
            continuity_anchor=continuity_anchor,
            confirmation_trigger=confirmation_trigger,
            phase_map=phase_map,
            motif_ledger=motif_ledger,
            closure_beats=(
                "private closure",
                "public confession",
                "lasting aftermath",
            ),
            public_cost_example=self._resolve_terminal_public_cost_example(
                ctx,
                public_witness=public_witness or supporting_witness or primary_keeper,
            ),
        )

    def _resolve_terminal_arc_motif_ledger(
        self,
        ctx: StoryWorkflowContext,
        *,
        protagonist: str,
        primary_keeper: str,
        supporting_witnesses: tuple[str, ...],
        confirmation_trigger: str,
    ) -> tuple[str, ...]:
        motifs: list[str] = []
        for candidate in (
            self._resolve_anchor_label(ctx),
            self._resolve_civic_target_label(ctx),
            self._resolve_terminal_memory_detail(ctx, protagonist),
            confirmation_trigger,
            primary_keeper,
            *supporting_witnesses,
        ):
            normalized = " ".join(str(candidate).split()).strip()
            if normalized and normalized not in motifs:
                motifs.append(normalized)
        for entry in ctx.memory.world_rules[-3:]:
            rule = " ".join(str(entry.rule).split()).strip()
            if rule and rule not in motifs:
                motifs.append(rule)
        return tuple(motifs)

    def _resolve_terminal_public_cost_example(
        self,
        ctx: StoryWorkflowContext,
        *,
        public_witness: str,
    ) -> str:
        combined_rules = " ".join(
            str(entry.rule).strip().lower() for entry in ctx.memory.world_rules if entry.rule
        )
        civic_target = self._resolve_civic_target_label(ctx)
        if "memory" in combined_rules or "name" in combined_rules:
            return (
                f"at {civic_target}, a blank stall tag fills with a missing name before the ink dries, and "
                f"{public_witness or 'the keeper'} has to call it back before the crowd can move; "
                "a chalk mark stays on the board as visible proof"
            )
        if any(token in combined_rules for token in ("ledger", "oath", "debt", "record")):
            return (
                f"a clerk drops one practiced count at {civic_target}, and "
                f"{public_witness or 'the keeper'} has to restore it aloud in public; "
                "a fresh black debt seal lands on the ledger margin"
            )
        return (
            f"one witness in the crowd falters under the new cost, and "
            f"{public_witness or 'the keeper'} has to answer it in public instead of hiding it; "
            "the ledger keeps a fresh black mark where the cost was named"
        )

    @classmethod
    def _terminal_phase_for_chapter(
        cls,
        chapter_number: int,
        target_chapters: int,
    ) -> str | None:
        for phase, phase_number in cls._terminal_phase_numbers(target_chapters).items():
            if phase_number == chapter_number:
                return phase
        return None

    def _focus_motivation_for_character(
        self,
        ctx: StoryWorkflowContext,
        *,
        chapter_number: int,
        focus_character: str,
    ) -> str:
        for character_state in reversed(ctx.memory.character_states):
            if (
                character_state.name == focus_character
                and character_state.chapter_number <= chapter_number
                and character_state.motivation.strip()
            ):
                return character_state.motivation.strip()
        blueprint = ctx.workflow.blueprint
        if blueprint is None:
            return ""
        profile = character_profile(blueprint.character_bible, focus_character)
        return " ".join(
            str(profile.get(key, "")).strip()
            for key in ("motivation", "goal", "arc")
            if str(profile.get(key, "")).strip()
        ).strip()

    def _ensure_world_rule_ledger(
        self,
        ctx: StoryWorkflowContext,
        issue_context: str,
    ) -> str | None:
        blueprint = ctx.workflow.blueprint
        world_bible = blueprint.world_bible if blueprint is not None else None
        changed = False

        if not ctx.memory.world_rules and isinstance(world_bible, dict):
            hydrated_rules = extract_world_rules(world_bible)
            if hydrated_rules:
                ctx.memory.world_rules = [
                    WorldRuleLedgerEntry(rule=str(rule).strip(), source="blueprint")
                    for rule in hydrated_rules
                    if str(rule).strip()
                ]
                changed = True
        deduped_rules = self._dedupe_world_rule_entries(ctx.memory.world_rules)
        if len(deduped_rules) != len(ctx.memory.world_rules):
            ctx.memory.world_rules = deduped_rules
            changed = True

        combined_rules = " ".join(
            str(entry.rule).strip().lower()
            for entry in ctx.memory.world_rules
            if str(entry.rule).strip()
        )
        combined_story_text = " ".join(
            fragment.strip().lower()
            for fragment in (
                ctx.workflow.premise,
                *(chapter.summary or "" for chapter in ctx.story.chapters),
            )
            if fragment and fragment.strip()
        )

        needs_archive_canon = (
            "world_rule_gap" in issue_context
            or "knocking" in issue_context
            or "public ledger" in issue_context
            or "memory-thread" in issue_context
            or (
                any(token in combined_story_text for token in ("archive", "oath", "ledger", "debt"))
                and ctx.story.chapter_count >= 10
            )
        )
        if not needs_archive_canon:
            return "Hydrated the world-rule ledger from the blueprint." if changed else None

        canonical_rules = [
            (
                "knock",
                "Whenever the Archive seal touches a rewritten oath, it answers with a physical knock before the hidden debt surfaces.",
            ),
            (
                "public ledger",
                "A public ledger of named witnesses stands in order and speaks the burned names aloud before the city can pay an erased debt.",
            ),
            (
                "memory-thread",
                "Memory-threading lets a living witness carry trapped guidance through the Archive seal, but it cannot restore a blank-slate shell's consciousness.",
            ),
        ]
        for marker, rule in canonical_rules:
            if marker in combined_rules:
                continue
            ctx.memory.world_rules.append(
                WorldRuleLedgerEntry(rule=rule, source="revision")
            )
            combined_rules = f"{combined_rules} {rule.lower()}".strip()
            changed = True
        deduped_rules = self._dedupe_world_rule_entries(ctx.memory.world_rules)
        if len(deduped_rules) != len(ctx.memory.world_rules):
            ctx.memory.world_rules = deduped_rules
            changed = True

        if not changed:
            return None
        return (
            "Hydrated the world-rule ledger with explicit seal-knock, witness-line, "
            "and memory-threading constraints."
        )

    @staticmethod
    def _world_rule_marker(rule: str) -> str:
        normalized = " ".join(str(rule).split()).strip().lower()
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        normalized = normalized.replace("cost using", "cost")
        normalized = normalized.replace("costs using", "cost")
        if normalized.startswith("cost "):
            normalized = normalized[5:].strip()
        if normalized.startswith("using "):
            normalized = normalized[6:].strip()
        return normalized

    @classmethod
    def _dedupe_world_rule_entries(
        cls,
        entries: list[WorldRuleLedgerEntry],
    ) -> list[WorldRuleLedgerEntry]:
        deduped: list[WorldRuleLedgerEntry] = []
        seen_markers: set[str] = set()
        for entry in entries:
            marker = cls._world_rule_marker(entry.rule)
            if not marker or marker in seen_markers:
                continue
            seen_markers.add(marker)
            deduped.append(entry)
        return deduped

    @staticmethod
    def _repair_hook(chapter_spec: dict[str, Any], chapter: Chapter) -> str:
        hook = str(chapter_spec.get("hook", "")).strip()
        if hook:
            return hook
        return f"What changes after {chapter.title}?"

    def _repair_semantic_relationship_arc(
        self,
        ctx: StoryWorkflowContext,
        *,
        issue_codes: set[str],
        issue_context: str,
    ) -> list[str]:
        if not (
            {
                "relationship_progression_stall",
                "plot_confusion",
                "world_logic_soft_conflict",
                "ooc_behavior",
            }
            & issue_codes
        ):
            return []

        blueprint = ctx.workflow.blueprint
        if blueprint is None:
            return []

        protagonist, allies = self._resolve_cast_labels(ctx)
        antagonists = set(antagonist_names(blueprint.character_bible))
        cast_names = set(character_names(blueprint.character_bible))
        if not protagonist or not allies:
            return []

        changed = False
        outline = ctx.workflow.outline
        outline_by_number = (
            {chapter.chapter_number: chapter for chapter in outline.chapters}
            if outline is not None
            else {}
        )
        departed_characters = self._combined_departed_characters(
            ctx,
            protagonist,
            issue_context=issue_context,
        )
        latest_surviving_allies = (
            self._surviving_allies_for_chapter(
                allies,
                departed_characters,
                ctx.story.chapter_count,
            )
            or self._resolve_surviving_allies(
                ctx,
                protagonist,
                allies,
                issue_context=issue_context,
            )
        )
        late_arc_overrides: dict[int, tuple[str, str, str]] = {}
        for chapter in ctx.story.chapters:
            number = chapter.chapter_number
            chapter_allies = (
                self._surviving_allies_for_chapter(allies, departed_characters, number)
                or latest_surviving_allies
                or [protagonist]
            )
            focus_character = self._normalize_protagonist_name_drift(
                str(chapter.metadata.get("focus_character", "")).strip(),
                protagonist,
                cast_names,
            )
            focus_character = self._canonicalize_character_name(
                focus_character,
                cast_names,
            )
            if number in late_arc_overrides:
                (
                    focus_character,
                    relationship_target,
                    relationship_status,
                ) = late_arc_overrides[number]
            else:
                relationship_target = self._normalize_protagonist_name_drift(
                    str(chapter.metadata.get("relationship_target", "")).strip(),
                    protagonist,
                    cast_names,
                )
                relationship_target = self._canonicalize_character_name(
                    relationship_target,
                    cast_names,
                )
                if (
                    not focus_character
                    or focus_character not in cast_names
                    or focus_character in antagonists
                    or (
                        self._departure_chapter_for_name(focus_character, departed_characters)
                        or number + 1
                    )
                    <= number
                ):
                    focus_character = (
                        protagonist
                        if number % 2 == 1 or not chapter_allies
                        else chapter_allies[(number - 1) % len(chapter_allies)]
                    )
                    chapter.metadata["focus_character"] = focus_character
                    changed = True

                if focus_character != protagonist:
                    relationship_target = protagonist
                elif chapter_allies:
                    relationship_target = chapter_allies[(number - 1) % len(chapter_allies)]
                    if relationship_target == focus_character:
                        relationship_target = next(
                            (
                                ally
                                for ally in chapter_allies
                                if ally and ally != focus_character
                            ),
                            "",
                        )
                else:
                    relationship_target = ""

                relationship_status = self._relationship_progression_status(
                    chapter_number=number,
                    target_chapters=ctx.story.chapter_count,
                )
                if (
                    number == max(1, ctx.story.chapter_count - 5)
                    and relationship_status == "strained trust"
                    and any(
                        token in issue_context
                        for token in (
                            "strained trust",
                            "relationship status for ch 15",
                            "tactical reliance",
                            "shared grief",
                        )
                    )
                ):
                    relationship_status = "tactical reliance"

            normalized_target = self._normalize_relationship_target(
                focus_character=focus_character,
                relationship_target=relationship_target,
                protagonist=protagonist,
                chapter_allies=chapter_allies,
                surviving_allies=latest_surviving_allies,
                cast_names=cast_names,
                departed_characters=departed_characters,
                chapter_number=number,
                target_chapters=ctx.story.chapter_count,
                prefer_vessel_target=str(relationship_target).strip().lower().endswith("(vessel)"),
            )
            if normalized_target != relationship_target:
                relationship_target = normalized_target
                changed = True

            if chapter.metadata.get("focus_character") != focus_character:
                chapter.metadata["focus_character"] = focus_character
                changed = True

            if chapter.metadata.get("relationship_target") != relationship_target:
                chapter.metadata["relationship_target"] = relationship_target
                changed = True
            relationship_status = self._normalize_departed_relationship_status(
                relationship_status=relationship_status,
                focus_character=focus_character,
                relationship_target=relationship_target,
                departed_characters=departed_characters,
                chapter_number=number,
                target_chapters=ctx.story.chapter_count,
            )
            if chapter.metadata.get("relationship_status") != relationship_status:
                chapter.metadata["relationship_status"] = relationship_status
                changed = True

            if focus_character and chapter.scenes and not any(
                focus_character.lower() in scene.content.lower()
                for scene in chapter.scenes
            ):
                anchored_focus = ensure_character_anchor(
                    chapter.scenes[0].content,
                    focus_character,
                )
                if anchored_focus != chapter.scenes[0].content:
                    chapter.scenes[0].update_content(anchored_focus)
                    changed = True

            outline_chapter = outline_by_number.get(number)
            if self._repair_departed_character_references(
                chapter,
                outline_chapter,
                departed_characters=departed_characters,
                chapter_number=number,
            ):
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
                normalized_anchor = self._normalize_self_relationship_anchor(
                    chapter.scenes[anchor_index].content,
                    focus_character=focus_character,
                    relationship_target=relationship_target,
                    relationship_status=relationship_status,
                )
                if normalized_anchor != chapter.scenes[anchor_index].content:
                    chapter.scenes[anchor_index].update_content(normalized_anchor)
                    changed = True

        if any(
            token in issue_context
            for token in (
                "turning point",
                "shared threat",
                "chapters 6-10",
                "master chen",
                "enemy surveillance",
                "battle-forged trust",
            )
        ):
            bridge_number = max(
                2,
                min(ctx.story.chapter_count - 1, round(ctx.story.chapter_count * 0.4)),
            )
            bridge_partner = latest_surviving_allies[0] if latest_surviving_allies else allies[0]
            bridge_summary = (
                f"{bridge_partner} breaks protocol to pull {protagonist} out of the collapsing archive "
                "and reveals the shared mortal threat that makes cooperation unavoidable."
            )
            bridge_objective = (
                f"{protagonist} and {bridge_partner} survive a forced rescue, name the shared mortal threat, "
                "and earn the shift out of pure hostility."
            )
            bridge_chapter = next(
                (chapter for chapter in ctx.story.chapters if chapter.chapter_number == bridge_number),
                None,
            )
            if bridge_chapter is not None:
                updated_summary = self._append_unique_sentence(
                    bridge_chapter.summary or "",
                    bridge_summary,
                )
                if updated_summary != (bridge_chapter.summary or "").strip():
                    bridge_chapter.summary = updated_summary
                    changed = True
                if bridge_chapter.metadata.get("focus_character") != protagonist:
                    bridge_chapter.metadata["focus_character"] = protagonist
                    changed = True
                if bridge_chapter.metadata.get("relationship_target") != bridge_partner:
                    bridge_chapter.metadata["relationship_target"] = bridge_partner
                    changed = True
                if bridge_chapter.metadata.get("relationship_status") != "guarded cooperation":
                    bridge_chapter.metadata["relationship_status"] = "guarded cooperation"
                    changed = True
                if bridge_chapter.current_scene is not None:
                    updated_scene = self._append_unique_sentence(
                        bridge_chapter.current_scene.content,
                        f"{bridge_partner} breaks protocol to pull {protagonist} clear and openly names the shared mortal threat."
                    )
                    if updated_scene != bridge_chapter.current_scene.content:
                        bridge_chapter.current_scene.update_content(updated_scene)
                        changed = True
                outline_chapter = outline_by_number.get(bridge_number)
                if outline_chapter is not None:
                    new_summary = self._append_unique_sentence(
                        outline_chapter.summary,
                        bridge_summary,
                    )
                    if new_summary != outline_chapter.summary:
                        outline_chapter.summary = new_summary
                        changed = True
                    new_objective = self._append_unique_sentence(
                        outline_chapter.chapter_objective,
                        bridge_objective,
                    )
                    if new_objective != outline_chapter.chapter_objective:
                        outline_chapter.chapter_objective = new_objective
                        changed = True
                    if outline_chapter.hook != "The shared mortal threat leaves no room for private feuds.":
                        outline_chapter.hook = "The shared mortal threat leaves no room for private feuds."
                        changed = True
                    if outline_chapter.hook_strength != 74:
                        outline_chapter.hook_strength = 74
                        changed = True

                followup_number = min(ctx.story.chapter_count, bridge_number + 1)
                followup_chapter = next(
                    (chapter for chapter in ctx.story.chapters if chapter.chapter_number == followup_number),
                    None,
                )
                if followup_chapter is not None:
                    followup_summary = (
                        f"Because {bridge_partner} exposed the shared mortal threat, {protagonist} accepts a "
                        "forced alliance under duress rather than pretending the feud can continue."
                    )
                    updated_followup = self._append_unique_sentence(
                        followup_chapter.summary or "",
                        followup_summary,
                    )
                    if updated_followup != (followup_chapter.summary or "").strip():
                        followup_chapter.summary = updated_followup
                        changed = True
                    if followup_chapter.metadata.get("focus_character") != protagonist:
                        followup_chapter.metadata["focus_character"] = protagonist
                        changed = True
                    if followup_chapter.metadata.get("relationship_target") != bridge_partner:
                        followup_chapter.metadata["relationship_target"] = bridge_partner
                        changed = True
                    if (
                        followup_chapter.metadata.get("relationship_status")
                        != "forced alliance under duress"
                    ):
                        followup_chapter.metadata["relationship_status"] = "forced alliance under duress"
                        changed = True

        late_arc_setup_candidate = self._resolve_late_arc_setup_candidate(
            ctx,
            protagonist,
            cast_names,
            issue_context=issue_context,
        )
        if late_arc_setup_candidate:
            pronoun = self._candidate_object_pronoun(ctx, late_arc_setup_candidate)
            possessive = self._candidate_possessive_pronoun(ctx, late_arc_setup_candidate)
            mid_arc_setup_specs = [
                (
                    max(2, min(ctx.story.chapter_count, ctx.story.chapter_count - 8)),
                    f"{late_arc_setup_candidate} keeps a public count moving under pressure, steadies the younger witnesses, and hands the corrected tally back to {protagonist} before the next escalation lands.",
                    f"{late_arc_setup_candidate} must steady the younger witnesses under pressure, keep the public count coherent, and earn visible trust before the final confession depends on {possessive} judgment.",
                    f"{late_arc_setup_candidate} takes the open count from a panicking witness, repeats the missing names aloud, and forces the line back into order before handing the tally back to {protagonist}.",
                ),
                (
                    max(3, min(ctx.story.chapter_count, ctx.story.chapter_count - 6)),
                    f"When the corridor buckles, {late_arc_setup_candidate} drags two shaken witnesses behind cover, keeps the public line from scattering, and passes the open register to {protagonist} with orders instead of apology.",
                    f"{late_arc_setup_candidate} must hold the public line together under pressure, keep the witnesses moving, and prove {pronoun} can carry the count under fire.",
                    f"When the corridor buckles, {late_arc_setup_candidate} drags two shaken witnesses behind cover, pushes the open register into {protagonist}'s hands, and keeps calling the missing until the line obeys.",
                ),
            ]
            seeded_chapters: set[int] = set()
            for chapter_number, setup_summary, setup_objective, setup_scene in mid_arc_setup_specs:
                if (
                    chapter_number < 1
                    or chapter_number > ctx.story.chapter_count
                    or chapter_number in seeded_chapters
                ):
                    continue
                seeded_chapters.add(chapter_number)
                setup_chapter = next(
                    (
                        chapter
                        for chapter in ctx.story.chapters
                        if chapter.chapter_number == chapter_number
                    ),
                    None,
                )
                if setup_chapter is not None:
                    updated_summary = self._append_unique_sentence(
                        setup_chapter.summary or "",
                        setup_summary,
                    )
                    if updated_summary != (setup_chapter.summary or "").strip():
                        setup_chapter.summary = updated_summary
                        changed = True
                    if setup_chapter.current_scene is not None:
                        updated_scene = self._append_unique_sentence(
                            setup_chapter.current_scene.content,
                            setup_scene,
                        )
                        if updated_scene != setup_chapter.current_scene.content:
                            setup_chapter.current_scene.update_content(updated_scene)
                            changed = True
                outline_chapter = outline_by_number.get(chapter_number)
                if outline_chapter is not None:
                    updated_outline_summary = self._append_unique_sentence(
                        outline_chapter.summary,
                        setup_summary,
                    )
                    if updated_outline_summary != outline_chapter.summary:
                        outline_chapter.summary = updated_outline_summary
                        changed = True
                    updated_outline_objective = self._append_unique_sentence(
                        outline_chapter.chapter_objective,
                        setup_objective,
                    )
                    if updated_outline_objective != outline_chapter.chapter_objective:
                        outline_chapter.chapter_objective = updated_outline_objective
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
        issue_context: str,
    ) -> list[str]:
        needs_late_arc_repair = bool(
            {"weak_serial_pull", "plot_confusion", "world_logic_soft_conflict", "promise_break"}
            & issue_codes
        ) or any(
            token in issue_context
            for token in ("civic debt", "missing page", "blank-slate", "promise")
        )
        if not needs_late_arc_repair:
            return []

        outline = ctx.workflow.outline
        if outline is None:
            return []

        late_arc_sequence = self._late_arc_sequence(ctx, issue_context=issue_context)
        late_arc_plan = {
            int(stage["number"]): stage for stage in late_arc_sequence.values()
        }

        changed = False
        outline_by_number = {chapter.chapter_number: chapter for chapter in outline.chapters}
        discovery_number = int(late_arc_sequence["discovery"]["number"])
        for chapter in ctx.story.chapters:
            plan = late_arc_plan.get(chapter.chapter_number)
            if plan is None:
                continue

            summary = str(chapter.summary or "").strip()
            plan_summary = str(plan["summary"])
            plan_hook = str(plan["hook"])
            plan_hook_strength = int(plan["hook_strength"])
            plan_objective = str(plan["objective"])

            if summary != plan_summary:
                chapter.summary = plan_summary
                changed = True

            hook = plan_hook
            chapter.metadata["outline_hook"] = hook
            chapter.metadata["hook_strength"] = plan_hook_strength
            for field in ("focus_character", "relationship_target", "relationship_status"):
                planned_value = str(plan[field])
                if chapter.metadata.get(field) != planned_value:
                    chapter.metadata[field] = planned_value
                    changed = True
            if chapter.metadata.get("chapter_objective") != plan_objective:
                chapter.metadata["chapter_objective"] = plan_objective
                changed = True
            if chapter.current_scene is not None:
                strengthened = ensure_hook(chapter.current_scene.content, hook)
                if strengthened != chapter.current_scene.content:
                    chapter.current_scene.update_content(strengthened)
                    changed = True

            outline_chapter = outline_by_number.get(chapter.chapter_number)
            if outline_chapter is not None:
                if outline_chapter.summary != plan_summary:
                    outline_chapter.summary = plan_summary
                    changed = True
                if outline_chapter.hook != hook:
                    outline_chapter.hook = hook
                    changed = True
                if outline_chapter.hook_strength != plan_hook_strength:
                    outline_chapter.hook_strength = plan_hook_strength
                    changed = True
                if outline_chapter.chapter_objective != plan_objective:
                    outline_chapter.chapter_objective = plan_objective
                    changed = True
                if chapter.chapter_number == discovery_number and self._set_outline_chapter_strands(
                    outline_chapter,
                    primary_strand="mystery",
                    secondary_strand="tension",
                ):
                    changed = True

        if not changed:
            return []
        return [
            "Rebuilt the late arc into a one-way sacrifice, first-night aftermath, failed private rehearsal, and public payment sequence."
        ]

    def _repair_semantic_foundation(
        self,
        ctx: StoryWorkflowContext,
        *,
        issue_codes: set[str],
        issue_context: str,
    ) -> list[str]:
        if not ({"ooc_behavior", "world_logic_soft_conflict", "plot_confusion"} & issue_codes):
            return []

        outline = ctx.workflow.outline
        if outline is None:
            return []

        protagonist, allies = self._resolve_cast_labels(ctx)
        protagonist_motivation = ""
        if ctx.workflow.blueprint is not None:
            canonical_protagonist = protagonist_name(ctx.workflow.blueprint.character_bible)
            if canonical_protagonist:
                protagonist = canonical_protagonist
            profile = ctx.workflow.blueprint.character_bible.get("protagonist", {})
            protagonist_motivation = str(profile.get("motivation", "")).strip()
        protagonist = protagonist or "the protagonist"
        anchor_label = self._resolve_anchor_label(ctx)
        founding_lie_event = self._resolve_founding_lie_event(ctx)
        public_ledger_label = self._resolve_civic_target_label(ctx)
        sibling_reference = self._resolve_sibling_reference(ctx, protagonist)
        keeper_pool = self._resolve_late_arc_keeper_pool(
            ctx,
            protagonist,
            allies,
            issue_context=issue_context,
        )
        primary_keeper = keeper_pool[0] if keeper_pool else protagonist
        primary_antagonist = self._resolve_primary_antagonist_label(ctx, protagonist)

        needs_anchor_explicit = "anchor" in issue_context or "physical anchor" in issue_context
        chapter_additions = {
            3: (
                f"During a minor tally at {anchor_label}, the seal knocks once against the registry chest before the ink settles, "
                "warning every witness nearby that rewritten oaths always announce their price with a physical knock."
            ),
            5: (
                "The archivists prove that memory-threading can carry trapped guidance through a living witness, but it can never restore a lost consciousness once the price is paid."
            ),
            7: (
                "A ward-market singer repeats the half-lullaby the family once used while searching for "
                f"{sibling_reference}, making that family loss a live wound long before the finale."
            ),
            9: (
                "The Ledger of Missing Names exposes unpaid balances and burning gaps in the inked record, warning that any restored "
                "oath will leave a civic debt behind."
            ),
            10: (
                f"{protagonist} finds an erased petition tied to {sibling_reference} beside the scorched registry from "
                f"{founding_lie_event}, and the same burning gaps in the ledger link the family loss to the city's oldest hidden debt."
            ),
            12: (
                "The team confirms the First Oath can only be restored by paying a personal memory cost, "
                "and the Ledger of Missing Names hints that every erased oath leaves a second civic debt behind."
            ),
            13: (
                "The survivors realize the missing names ledger is hiding a civic debt that will surface if the "
                "First Oath is ever restored, and they finally understand why writing that lie does not create a stronger Hollow: "
                "the rewrite demands total self-erasure, leaving no intact self for corruption to seize once the price comes due."
            ),
            15: (
                f"Because {protagonist} prepares to pay with an entire identity, {primary_keeper} learns to thread living "
                "memory echoes through the ledger so the city can survive the aftermath without losing reality."
            ),
            16: (
                f"{protagonist} must spend the living memory tied to the family debt and use {anchor_label} as the "
                "physical anchor to rewrite the First Oath and save the city, leaving only a trapped last vow in the "
                f"shell that can answer with pressure and movement, not speech, while the surviving witnesses formally "
                f"become the confession circle later called {public_ledger_label}, a line of living witnesses that will speak for the city after that consciousness ends. "
                f"Because the rite spends the whole self as payment, the rewrite bypasses ordinary Hollow conversion and leaves only the silent shell behind. The same binding strips the glamour from {primary_antagonist}, turns the outline ash-transparent at the edges, and drops the last of the tyrant choking onto the stone."
            ),
            17: (
                f"{primary_keeper} keeps the first memorial watch while the silent shell is held under guard as proof of the price, "
                f"finds {protagonist}'s last warning still returning through the public record whenever ash flakes off the scorched sleeve, "
                f"gets only silence back the first time the shell is addressed, reaches as if one harder shake might wake the body, stops with both hands hovering over the scorched cloth, and then watches trembling clerks steady each other before they can name the burned victims from {founding_lie_event}. "
                f"Before dawn, {primary_keeper} wipes ash across the ledger edge, reads the next erased name aloud, and orders the clerks to answer it back until the square can keep the register open without them."
            ),
        }
        if needs_anchor_explicit:
            chapter_additions[11] = (
                f"{anchor_label} becomes the physical anchor that can hold the First Oath once someone pays the "
                "living memory cost."
            )

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

            if chapter_number in {3, 5, 11, 16, 17} and chapter.current_scene is not None:
                if chapter_number == 3:
                    anchor_sentence = (
                        f"When a clerk tests a harmless line of oath-ink at {anchor_label}, the seal answers with a single knock before the hidden cost surfaces."
                    )
                elif chapter_number == 5:
                    anchor_sentence = (
                        "The lesson makes clear that memory-threading can carry trapped guidance through a living witness, but it cannot restore a consciousness once the price is paid."
                    )
                elif chapter_number == 16:
                    anchor_sentence = (
                        f"As the rewrite locks at {anchor_label}, the seal rips the pen from {primary_antagonist}'s hand, slams both wrists onto the rail, forces the tyrant to his knees, and keeps the loop of erased names tight until the outline turns ash-transparent at the edges."
                    )
                elif chapter_number == 17:
                    anchor_sentence = (
                        f"{primary_keeper} touches the ash on the shell's sleeve, gets no answer from the shell, almost reaches to wake the body anyway, forces both hands back to the ledger edge before anyone can see that hope break, hears the last warning return through the public record, catches the shell's thumb tap once against the bier board in the old counting beat, accepts that the city must carry the confession without pretending {protagonist} came back, reads the next erased name aloud, and orders the clerks to answer it back until the square can keep the register open without them."
                    )
                else:
                    anchor_sentence = (
                        f"{anchor_label} is the physical anchor that lets the rewritten oath hold when the memory cost "
                        "is finally paid."
                    )
                anchored_scene = self._append_unique_sentence(
                    chapter.current_scene.content,
                    anchor_sentence,
                )
                if anchored_scene != chapter.current_scene.content:
                    chapter.current_scene.update_content(anchored_scene)
                    changed = True

            if chapter_number in {7, 10} and chapter.current_scene is not None:
                sibling_scene = (
                    f"The margin note carries the same half-lullaby once used while searching for {sibling_reference}, "
                    "so the family loss stays visible before the late-arc reveal lands."
                )
                updated_scene = self._append_unique_sentence(
                    chapter.current_scene.content,
                    sibling_scene,
                )
                if updated_scene != chapter.current_scene.content:
                    chapter.current_scene.update_content(updated_scene)
                    changed = True

            outline_chapter = outline_by_number.get(chapter_number)
            if outline_chapter is not None:
                outline_chapter.summary = self._append_unique_sentence(
                    outline_chapter.summary,
                    addition,
                )
                if chapter_number in {11, 16}:
                    outline_chapter.chapter_objective = self._append_unique_sentence(
                        outline_chapter.chapter_objective,
                        f"The rewrite only holds if {anchor_label} stays in the line as the physical anchor when the price comes due.",
                    )
                changed = True

        if self._sanitize_storycraft_language(ctx):
            changed = True

        if not changed:
            return []
        return [
            "Made the First Oath cost and the protagonist's family-debt motive explicit in the mid-to-late arc."
        ]

    def _repair_semantic_plot_clarity(
        self,
        ctx: StoryWorkflowContext,
        *,
        issue_codes: set[str],
        issue_context: str,
    ) -> list[str]:
        if not ({"plot_confusion", "world_logic_soft_conflict"} & issue_codes) and not any(
            token in issue_context for token in ("blank-slate", "civic debt", "missing page")
        ):
            return []

        outline = ctx.workflow.outline
        if outline is None or not ctx.story.chapters:
            return []

        changed = self._sanitize_storycraft_language(ctx)
        if self._clarify_finale_state(ctx, outline, issue_context=issue_context):
            changed = True
        if self._compact_live_late_arc_summaries(
            ctx,
            outline,
            issue_codes=issue_codes,
            issue_context=issue_context,
        ):
            changed = True

        if not changed:
            return []
        return [
            "Clarified the late-arc payoff so the hidden debt, survivor grief, and final oath state read as one continuous consequence."
        ]

    def _repair_semantic_promise_payoff(
        self,
        ctx: StoryWorkflowContext,
        *,
        issue_codes: set[str],
        issue_context: str,
    ) -> list[str]:
        if not (
            {"promise_break", "weak_serial_pull", "world_logic_soft_conflict", "ooc_behavior", "plot_confusion"}
            & issue_codes
        ):
            return []
        if not any(
            token in issue_context
            for token in (
                "civic debt",
                "promise",
                "missing page",
                "blank-slate",
                "writes the first entry",
                "founding lie",
                "fee mark",
                "archive seal",
                "memory toll",
            )
        ):
            return []

        outline = ctx.workflow.outline
        if outline is None:
            return []

        frame = self._build_terminal_arc_semantic_frame(
            ctx,
            issue_context=issue_context,
        )
        late_arc_sequence = self._late_arc_sequence(ctx, issue_context=issue_context)
        changed = False
        outline_by_number = {chapter.chapter_number: chapter for chapter in outline.chapters}
        motif_anchor = frame.motif_ledger[0] if frame.motif_ledger else "the public record"
        private_loss_anchor = (
            frame.motif_ledger[2]
            if len(frame.motif_ledger) > 2
            else "one private loss the city still has not named honestly"
        )
        chapter_numbers = {
            "rule_revelation": int(late_arc_sequence["discovery"]["number"]),
            "public_reckoning": int(late_arc_sequence["attempt"]["number"]),
            "closure": int(late_arc_sequence["resolution"]["number"]),
        }

        setup_number = max(2, min(ctx.story.chapter_count, ctx.story.chapter_count - 6))
        setup_chapter = next(
            (chapter for chapter in ctx.story.chapters if chapter.chapter_number == setup_number),
            None,
        )
        if setup_chapter is not None:
            setup_summary = (
                f"{frame.primary_keeper} keeps a frightened public count coherent under pressure, proving the living line can survive one break before the terminal cost goes public."
            )
            updated_summary = self._append_unique_sentence(
                setup_chapter.summary or "",
                setup_summary,
            )
            if updated_summary != (setup_chapter.summary or "").strip():
                setup_chapter.summary = updated_summary
                changed = True
            setup_objective = (
                f"{frame.primary_keeper} must earn visible trust by steadying witnesses before the sacrifice makes that burden permanent."
            )
            if setup_chapter.metadata.get("chapter_objective") != setup_objective:
                setup_chapter.metadata["chapter_objective"] = setup_objective
                changed = True
            outline_setup = outline_by_number.get(setup_number)
            if outline_setup is not None:
                if outline_setup.summary != updated_summary:
                    outline_setup.summary = updated_summary
                    changed = True
                if outline_setup.chapter_objective != setup_objective:
                    outline_setup.chapter_objective = setup_objective
                    changed = True

        foreshadow_number = min(6, ctx.story.chapter_count)
        foreshadow_chapter = next(
            (chapter for chapter in ctx.story.chapters if chapter.chapter_number == foreshadow_number),
            None,
        )
        if foreshadow_chapter is not None:
            foreshadow_summary = (
                f"A small irregularity around {motif_anchor} hints that {private_loss_anchor} already belongs to a wider public debt."
            )
            updated_foreshadow = self._append_unique_sentence(
                foreshadow_chapter.summary or "",
                foreshadow_summary,
            )
            if updated_foreshadow != (foreshadow_chapter.summary or "").strip():
                foreshadow_chapter.summary = updated_foreshadow
                changed = True
            foreshadow_objective = self._append_unique_sentence(
                str(foreshadow_chapter.metadata.get("chapter_objective", "")),
                f"Notice one concrete clue tied to {motif_anchor} so the later public confession feels like continuity rather than exposition.",
            )
            if foreshadow_chapter.metadata.get("chapter_objective") != foreshadow_objective:
                foreshadow_chapter.metadata["chapter_objective"] = foreshadow_objective
                changed = True
            outline_foreshadow = outline_by_number.get(foreshadow_number)
            if outline_foreshadow is not None:
                if outline_foreshadow.summary != updated_foreshadow:
                    outline_foreshadow.summary = updated_foreshadow
                    changed = True
                if outline_foreshadow.chapter_objective != foreshadow_objective:
                    outline_foreshadow.chapter_objective = foreshadow_objective
                    changed = True

        for phase, chapter_number in chapter_numbers.items():
            chapter = next(
                (item for item in ctx.story.chapters if item.chapter_number == chapter_number),
                None,
            )
            if chapter is None:
                continue
            alias = {
                "rule_revelation": "discovery",
                "public_reckoning": "attempt",
                "closure": "resolution",
            }[phase]
            plan = late_arc_sequence[alias]
            planned_summary = str(plan["summary"])
            planned_objective = str(plan["objective"])
            planned_hook = str(plan["hook"])
            if chapter.summary != planned_summary:
                chapter.summary = planned_summary
                changed = True
            if chapter.metadata.get("chapter_objective") != planned_objective:
                chapter.metadata["chapter_objective"] = planned_objective
                changed = True
            if chapter.metadata.get("outline_hook") != planned_hook:
                chapter.metadata["outline_hook"] = planned_hook
                changed = True
            if chapter.current_scene is not None:
                if phase == "rule_revelation":
                    scene_reinforcement = (
                        f"{frame.primary_keeper} and {frame.supporting_witness} pin the aftermath to concrete evidence around {motif_anchor}, while {frame.vessel_label} gives one brief trained twitch and then goes still so {frame.confirmation_trigger} reads as memorial proof rather than a reply."
                    )
                elif phase == "public_reckoning":
                    scene_reinforcement = (
                        f"When the line nearly breaks, one beat of silence opens, {frame.public_witness} tastes metal and moves first, {frame.supporting_witness} closes the gap, and only then does {frame.primary_keeper} name the mechanism. A fresh black seal blooms on the ledger as the burned names are spoken, and {frame.vessel_label} stays still while the crowd feels the break."
                    )
                else:
                    scene_reinforcement = (
                        f"The ending separates {', '.join(frame.closure_beats)}. {frame.primary_keeper} holds the silence of {frame.vessel_label} in mind before the private scene opens, and the scratch of ink drying recurs through each beat; {frame.public_witness} and {frame.supporting_witness} act before {frame.primary_keeper} confirms the new order, and the public cost lands through {frame.public_cost_example}."
                    )
                updated_scene = self._append_unique_sentence(
                    chapter.current_scene.content,
                    ensure_hook(scene_reinforcement, planned_hook),
                )
                if updated_scene != chapter.current_scene.content:
                    chapter.current_scene.update_content(updated_scene)
                    changed = True
            outline_chapter = outline_by_number.get(chapter_number)
            if outline_chapter is not None:
                if outline_chapter.summary != planned_summary:
                    outline_chapter.summary = planned_summary
                    changed = True
                if outline_chapter.chapter_objective != planned_objective:
                    outline_chapter.chapter_objective = planned_objective
                    changed = True
                if outline_chapter.hook != planned_hook:
                    outline_chapter.hook = planned_hook
                    changed = True
                if outline_chapter.hook_strength != int(plan["hook_strength"]):
                    outline_chapter.hook_strength = int(plan["hook_strength"])
                    changed = True
                if phase == "rule_revelation":
                    if outline_chapter.promise != (
                        f"Concrete evidence around {motif_anchor} will prove whether the private wound belongs to a larger public rule."
                    ):
                        outline_chapter.promise = (
                            f"Concrete evidence around {motif_anchor} will prove whether the private wound belongs to a larger public rule."
                        )
                        changed = True
                    if self._set_outline_chapter_strands(
                        outline_chapter,
                        primary_strand="mystery",
                        secondary_strand="tension",
                    ):
                        changed = True
                elif phase == "public_reckoning":
                    if outline_chapter.promise != (
                        "The public record carries the working rule into daylight after one failed private attempt leaves a visible mark on the ledger and the vessel remains a cold presence."
                    ):
                        outline_chapter.promise = (
                            "The public record carries the working rule into daylight after one failed private attempt leaves a visible mark on the ledger and the vessel remains a cold presence."
                        )
                        changed = True
                    if outline_chapter.promised_payoff != (
                        "The living line nearly breaks, recovers through named witness action, and leaves the ledger marked by the public cost."
                    ):
                        outline_chapter.promised_payoff = (
                            "The living line nearly breaks, recovers through named witness action, and leaves the ledger marked by the public cost."
                        )
                        changed = True
                else:
                    if outline_chapter.promise != (
                        "The ending lands as private closure, public confession, and lasting aftermath while the vessel remains a cold presence."
                    ):
                        outline_chapter.promise = (
                            "The ending lands as private closure, public confession, and lasting aftermath while the vessel remains a cold presence."
                        )
                        changed = True
                    if outline_chapter.promised_payoff != (
                        f"The living absorb the public cost through {frame.public_cost_example}, while the vessel remains a cold presence and the new order becomes ordinary fact."
                    ):
                        outline_chapter.promised_payoff = (
                            f"The living absorb the public cost through {frame.public_cost_example}, while the vessel remains a cold presence and the new order becomes ordinary fact."
                        )
                        changed = True

        if self._compact_live_late_arc_summaries(
            ctx,
            outline,
            issue_codes=issue_codes,
            issue_context=issue_context,
        ):
            changed = True

        if not changed:
            return []
        return [
            "Closed the terminal promise/payoff line through phase-based witness action, concrete rule evidence, and visible public cost."
        ]

    def _repair_departed_character_cleanup(
        self,
        ctx: StoryWorkflowContext,
        *,
        issue_context: str = "",
    ) -> list[str]:
        outline = ctx.workflow.outline
        if outline is None:
            return []

        protagonist, allies = self._resolve_cast_labels(ctx)
        blueprint = ctx.workflow.blueprint
        cast_names = (
            set(character_names(blueprint.character_bible))
            if blueprint is not None
            else set()
        )
        departed_characters = self._combined_departed_characters(
            ctx,
            protagonist,
            issue_context=issue_context,
        )
        if not departed_characters:
            return []

        surviving_allies = self._resolve_surviving_allies(
            ctx,
            protagonist,
            allies,
            issue_context=issue_context,
        )
        fallback_focus = surviving_allies[0] if surviving_allies else protagonist
        changed = False
        outline_by_number = {chapter.chapter_number: chapter for chapter in outline.chapters}

        for chapter in ctx.story.chapters:
            outline_chapter = outline_by_number.get(chapter.chapter_number)
            if self._repair_departed_character_references(
                chapter,
                outline_chapter,
                departed_characters=departed_characters,
                chapter_number=chapter.chapter_number,
            ):
                changed = True

            focus_character = self._canonicalize_character_name(
                str(chapter.metadata.get("focus_character", "")).strip(),
                cast_names,
            )
            if chapter.metadata.get("focus_character") != focus_character:
                chapter.metadata["focus_character"] = focus_character
                changed = True
            if (
                self._departure_chapter_for_name(focus_character, departed_characters)
                or chapter.chapter_number + 1
            ) < chapter.chapter_number:
                if chapter.metadata.get("focus_character") != fallback_focus:
                    chapter.metadata["focus_character"] = fallback_focus
                    changed = True

            relationship_target = self._canonicalize_character_name(
                str(chapter.metadata.get("relationship_target", "")).strip(),
                cast_names,
            )
            if chapter.metadata.get("relationship_target") != relationship_target:
                chapter.metadata["relationship_target"] = relationship_target
                changed = True
            relationship_departure = self._departure_chapter_for_name(
                relationship_target,
                departed_characters,
            )
            if (relationship_departure or chapter.chapter_number + 1) < chapter.chapter_number:
                fallback_target = next(
                    (
                        candidate
                        for candidate in surviving_allies
                        if candidate and candidate != focus_character
                    ),
                    "",
                )
                current_target = str(chapter.metadata.get("relationship_target", "")).strip()
                if current_target.lower().endswith("(vessel)"):
                    fallback_target = current_target
                elif not fallback_target:
                    fallback_target = protagonist if protagonist != focus_character else ""
                if chapter.metadata.get("relationship_target") != fallback_target:
                    chapter.metadata["relationship_target"] = fallback_target
                    changed = True

        if not changed:
            return []
        return [
            "Recast post-departure character appearances as legacy or memory traces instead of living participants."
        ]

    def _repair_structural_hooks(
        self,
        ctx: StoryWorkflowContext,
    ) -> list[str]:
        outline = ctx.workflow.outline
        if outline is None or not ctx.story.chapters:
            return []

        outline_by_number = {chapter.chapter_number: chapter for chapter in outline.chapters}
        hook_changed = False
        payoff_changed = False
        previous_hook = ""

        for chapter in ctx.story.chapters:
            outline_chapter = outline_by_number.get(chapter.chapter_number)
            hook = str(chapter.metadata.get("outline_hook", "")).strip()
            if not hook and outline_chapter is not None:
                hook = str(outline_chapter.hook).strip()
            if hook and chapter.metadata.get("outline_hook") != hook:
                chapter.metadata["outline_hook"] = hook
                hook_changed = True
            if hook and outline_chapter is not None and outline_chapter.hook != hook:
                outline_chapter.hook = hook
                hook_changed = True

            if (
                chapter.chapter_number < ctx.story.chapter_count
                and hook
                and chapter.current_scene is not None
            ):
                repaired_scene = ensure_hook(chapter.current_scene.content, hook)
                if repaired_scene != chapter.current_scene.content:
                    chapter.current_scene.update_content(repaired_scene)
                    hook_changed = True
                summary_with_hook = self._append_unique_sentence(chapter.summary or "", hook)
                if summary_with_hook != (chapter.summary or "").strip():
                    chapter.summary = summary_with_hook
                    hook_changed = True

            if chapter.chapter_number > 1 and previous_hook and chapter.scenes:
                repaired_opening = ensure_payoff_anchor(chapter.scenes[0].content, previous_hook)
                if repaired_opening != chapter.scenes[0].content:
                    chapter.scenes[0].update_content(repaired_opening)
                    payoff_changed = True

            previous_hook = hook

        notes: list[str] = []
        if hook_changed:
            notes.append("Repaired chapter-end hook surfacing across the structural ledger.")
        if payoff_changed:
            notes.append("Restored previous-hook payoffs at chapter openings before the next pivot.")
        return notes

    def _repair_focus_character_presence(
        self,
        ctx: StoryWorkflowContext,
    ) -> list[str]:
        changed = False
        for chapter in ctx.story.chapters:
            focus_character = str(chapter.metadata.get("focus_character", "")).strip()
            if not focus_character or not chapter.scenes:
                continue
            if any(focus_character.lower() in scene.content.lower() for scene in chapter.scenes):
                continue
            opening_scene = chapter.scenes[0]
            realigned = self._realign_focus_anchor(opening_scene.content, focus_character)
            if realigned != opening_scene.content:
                opening_scene.update_content(realigned)
                changed = True
        if not changed:
            return []
        return ["Realigned opening scenes with the final focus-character ledger."]

    def _repair_placeholder_promises(
        self,
        ctx: StoryWorkflowContext,
    ) -> list[str]:
        outline = ctx.workflow.outline
        outline_by_number = (
            {chapter.chapter_number: chapter for chapter in outline.chapters}
            if outline is not None
            else {}
        )
        changed = False

        for chapter in ctx.story.chapters:
            promise = str(chapter.metadata.get("promise", "")).strip()
            normalized_promise = promise.lower()
            if not (
                normalized_promise.startswith(f"chapter {chapter.chapter_number} promises")
                or normalized_promise == "make the first oath cost explicit."
            ):
                continue

            summary_sentence = re.split(r"(?<=[.!?])\s+", str(chapter.summary or "").strip(), maxsplit=1)[
                0
            ].strip()
            hook = str(chapter.metadata.get("outline_hook", "")).strip()
            replacement = summary_sentence or hook
            if not replacement:
                continue

            if chapter.metadata.get("promise") != replacement:
                chapter.metadata["promise"] = replacement
                changed = True

            outline_chapter = outline_by_number.get(chapter.chapter_number)
            if outline_chapter is not None and outline_chapter.promise != replacement:
                outline_chapter.promise = replacement
                changed = True

        if not changed:
            return []
        return ["Converted placeholder chapter promises into surfaced payoff lines before the final review pass."]

    def _repair_relationship_metadata_integrity(
        self,
        ctx: StoryWorkflowContext,
        *,
        issue_context: str = "",
    ) -> list[str]:
        blueprint = ctx.workflow.blueprint
        if blueprint is None:
            return []

        protagonist, allies = self._resolve_cast_labels(ctx)
        if not protagonist:
            return []

        cast_names = set(character_names(blueprint.character_bible))
        antagonists = set(antagonist_names(blueprint.character_bible))
        departed_characters = self._combined_departed_characters(
            ctx,
            protagonist,
            issue_context=issue_context,
        )
        latest_surviving_allies = self._resolve_surviving_allies(
            ctx,
            protagonist,
            allies,
            issue_context=issue_context,
        )
        late_arc_numbers = set(self._late_arc_chapter_numbers(ctx.story.chapter_count).values())
        late_arc_plan = {
            chapter.chapter_number: {
                "focus_character": str(chapter.metadata.get("focus_character", "")).strip(),
                "relationship_target": str(chapter.metadata.get("relationship_target", "")).strip(),
                "relationship_status": str(chapter.metadata.get("relationship_status", "")).strip(),
            }
            for chapter in ctx.story.chapters
            if chapter.chapter_number in late_arc_numbers
        }
        late_arc_custom_focus = set(
            self._late_arc_metadata_candidates(ctx, protagonist, departed_characters)
        )
        changed = False
        chapter_relationship_snapshots: dict[int, tuple[str, str, str]] = {}

        for chapter in ctx.story.chapters:
            chapter_allies = (
                self._surviving_allies_for_chapter(
                    allies,
                    departed_characters,
                    chapter.chapter_number,
                )
                or latest_surviving_allies
            )
            if chapter.chapter_number in late_arc_plan:
                planned_stage = late_arc_plan[chapter.chapter_number]
                focus_character = self._canonicalize_character_name(
                    str(planned_stage["focus_character"]),
                    cast_names,
                )
                if self._is_generic_terminal_placeholder(focus_character):
                    focus_character = protagonist
                relationship_target = self._canonicalize_character_name(
                    str(planned_stage["relationship_target"]),
                    cast_names,
                )
                relationship_status = str(planned_stage["relationship_status"]).strip()
            else:
                focus_character = self._normalize_protagonist_name_drift(
                    str(chapter.metadata.get("focus_character", "")).strip(),
                    protagonist,
                    cast_names,
                )
                focus_character = self._canonicalize_character_name(
                    focus_character,
                    cast_names,
                )
                relationship_target = self._normalize_protagonist_name_drift(
                    str(chapter.metadata.get("relationship_target", "")).strip(),
                    protagonist,
                    cast_names,
                )
                relationship_target = self._canonicalize_character_name(
                    relationship_target,
                    cast_names,
                )
                relationship_status = str(chapter.metadata.get("relationship_status", "")).strip()

            if (
                focus_character
                and (
                    focus_character not in cast_names
                    or focus_character in antagonists
                    or (
                        self._departure_chapter_for_name(
                            focus_character,
                            departed_characters,
                        )
                        or chapter.chapter_number + 1
                    )
                    <= chapter.chapter_number
                )
                and not (
                    chapter.chapter_number in late_arc_numbers
                    and focus_character in late_arc_custom_focus
                )
            ):
                focus_character = next(
                    (name for name in chapter_allies if name and name in cast_names),
                    protagonist,
                )
                changed = True

            normalized_target = self._normalize_relationship_target(
                focus_character=focus_character,
                relationship_target=relationship_target,
                protagonist=protagonist,
                chapter_allies=chapter_allies,
                surviving_allies=latest_surviving_allies,
                cast_names=cast_names,
                departed_characters=departed_characters,
                chapter_number=chapter.chapter_number,
                target_chapters=ctx.story.chapter_count,
                prefer_vessel_target=str(relationship_target).strip().lower().endswith("(vessel)"),
            )
            if not normalized_target and relationship_status:
                for pool in (chapter_allies, latest_surviving_allies, allies):
                    fallback_target = next(
                        (name for name in pool if name and name != focus_character),
                        "",
                    )
                    if fallback_target:
                        normalized_target = fallback_target
                        break

            if focus_character and chapter.metadata.get("focus_character") != focus_character:
                chapter.metadata["focus_character"] = focus_character
                changed = True
            if normalized_target and chapter.metadata.get("relationship_target") != normalized_target:
                chapter.metadata["relationship_target"] = normalized_target
                changed = True
            if normalized_target and not relationship_status:
                chapter.metadata["relationship_status"] = self._relationship_progression_status(
                    chapter_number=chapter.chapter_number,
                    target_chapters=ctx.story.chapter_count,
                )
                changed = True
                relationship_status = str(chapter.metadata["relationship_status"]).strip()
            relationship_status = self._normalize_departed_relationship_status(
                relationship_status=relationship_status,
                focus_character=focus_character,
                relationship_target=normalized_target,
                departed_characters=departed_characters,
                chapter_number=chapter.chapter_number,
                target_chapters=ctx.story.chapter_count,
            )
            if chapter.metadata.get("relationship_status") != relationship_status:
                chapter.metadata["relationship_status"] = relationship_status
                changed = True

            if focus_character and normalized_target and relationship_status:
                chapter_relationship_snapshots[chapter.chapter_number] = (
                    focus_character,
                    normalized_target,
                    relationship_status,
                )

        if chapter_relationship_snapshots:
            synced_states: list[RelationshipSnapshot] = []
            synced_chapters: set[int] = set()
            memory_changed = False
            for relationship_state in ctx.memory.relationship_states:
                override = chapter_relationship_snapshots.get(relationship_state.chapter_number)
                if override is None:
                    synced_states.append(relationship_state)
                    continue
                if relationship_state.chapter_number in synced_chapters:
                    memory_changed = True
                    continue
                synced_chapters.add(relationship_state.chapter_number)
                source, target, status = override
                if (
                    relationship_state.source != source
                    or relationship_state.target != target
                    or relationship_state.status != status
                ):
                    memory_changed = True
                synced_states.append(
                    RelationshipSnapshot(
                        chapter_number=relationship_state.chapter_number,
                        source=source,
                        target=target,
                        status=status,
                    )
                )
            for chapter_number, (source, target, status) in sorted(chapter_relationship_snapshots.items()):
                if chapter_number in synced_chapters:
                    continue
                synced_states.append(
                    RelationshipSnapshot(
                        chapter_number=chapter_number,
                        source=source,
                        target=target,
                        status=status,
                    )
                )
                memory_changed = True
            if memory_changed:
                ctx.memory.relationship_states = synced_states
                changed = True

        if not changed:
            return []
        return ["Normalized relationship targets and statuses before the final review pass."]

    def _normalize_relationship_target(
        self,
        *,
        focus_character: str,
        relationship_target: str,
        protagonist: str,
        chapter_allies: list[str],
        surviving_allies: list[str],
        cast_names: set[str],
        departed_characters: dict[str, int],
        chapter_number: int,
        target_chapters: int,
        prefer_vessel_target: bool = False,
    ) -> str:
        focus = str(focus_character).strip()
        raw_target = str(relationship_target).strip()
        target_base, target_is_vessel = self._split_vessel_label(raw_target)
        canonical_target_base = self._canonicalize_character_name(
            target_base,
            cast_names,
        )
        target = (
            self._vessel_label_for_character(canonical_target_base)
            if target_is_vessel and canonical_target_base
            else canonical_target_base
        )
        late_closure_window = chapter_number >= max(1, target_chapters - 7)
        protagonist_departure = self._departure_chapter_for_name(
            protagonist,
            departed_characters,
        )
        protagonist_vessel = (
            self._late_arc_vessel_label(protagonist)
            if prefer_vessel_target
            or (protagonist_departure is not None and protagonist_departure <= chapter_number)
            else protagonist
        )
        target_partner = (
            canonical_target_base
            if target_is_vessel and canonical_target_base
            else target
        )

        def _is_available_partner(name: str) -> bool:
            departure = self._departure_chapter_for_name(name, departed_characters)
            if departure is None:
                return True
            if late_closure_window:
                return departure > chapter_number + 1
            return departure >= chapter_number

        if target and not target_partner:
            target = ""
        if target:
            target_departure = self._departure_chapter_for_name(
                target_partner,
                departed_characters,
            )
            if (
                target_partner == protagonist
                and protagonist_departure is not None
                and protagonist_departure <= chapter_number
            ):
                if target_is_vessel or prefer_vessel_target:
                    target = protagonist_vessel
                    target_departure = None
                else:
                    target = ""
                    target_departure = protagonist_departure
            if target_departure is not None and (
                target_departure <= chapter_number
                or (
                    late_closure_window
                    and target_departure <= chapter_number + 1
                )
            ):
                target = ""
        if focus and target and focus != target:
            return target

        if focus and protagonist and focus != protagonist and _is_available_partner(protagonist):
            if protagonist_departure is None or protagonist_departure > chapter_number:
                return protagonist
            if prefer_vessel_target or target_is_vessel:
                return protagonist_vessel

        for pool in (chapter_allies, surviving_allies):
            partner = next(
                (
                    candidate
                    for candidate in (
                        self._canonicalize_character_name(name, cast_names)
                        for name in pool
                    )
                    if candidate
                    and candidate in cast_names
                    and candidate != focus
                    and _is_available_partner(candidate)
                ),
                "",
            )
            if partner:
                return partner
        return target if target and target != focus else ""

    @staticmethod
    def _normalize_self_relationship_anchor(
        text: str,
        *,
        focus_character: str,
        relationship_target: str,
        relationship_status: str,
    ) -> str:
        normalized_text = " ".join(str(text).split())
        focus = str(focus_character).strip()
        target = str(relationship_target).strip()
        status = str(relationship_status).strip()
        if not normalized_text or not focus or not target or not status or focus == target:
            return normalized_text
        pattern = re.compile(
            rf"Relationship status:\s*{re.escape(focus)}\s+and\s+{re.escape(focus)}\s+are\s+[^.]+\.?",
            flags=re.IGNORECASE,
        )
        if not pattern.search(normalized_text):
            return normalized_text
        replacement = f"Relationship status: {focus} and {target} are {status}."
        return " ".join(pattern.sub(replacement, normalized_text).split()).strip()

    @staticmethod
    def _append_unique_sentence(text: str, sentence: str) -> str:
        base = str(text).strip()
        normalized_sentence = " ".join(sentence.split())
        if not base:
            return normalized_sentence
        if normalized_sentence.lower() in base.lower():
            return " ".join(base.split())
        return f"{base} {normalized_sentence}".strip()

    @staticmethod
    def _realign_focus_anchor(text: str, focus_character: str) -> str:
        normalized = " ".join(str(text).split())
        if not normalized or not focus_character:
            return normalized
        anchor_pattern = re.compile(r"[^.?!]*anchors the chapter\.", flags=re.IGNORECASE)
        if anchor_pattern.search(normalized):
            return anchor_pattern.sub(f"{focus_character} anchors the chapter.", normalized, count=1)
        return ensure_character_anchor(normalized, focus_character)

    @staticmethod
    def _normalize_storycraft_text(text: str) -> str:
        normalized = str(text).strip()
        replacements = {
            "Make the First Oath cost explicit.": "",
            "Make the First Oath cost explicit": "",
            "Cost anchor:": "",
        }
        for source, replacement in replacements.items():
            normalized = normalized.replace(source, replacement)
        normalized = re.sub(
            r"\bThe cast must pay a visible civic price to rewrite the First Oath\.?",
            "",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            r"\bThe oath exacts a visible civic price:\s*",
            "",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            r"(,\s+a Debt Ghost,)(?:\s*,?\s*a Debt Ghost,)+",
            r"\1",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            r"\b([A-Z][A-Za-z-]*(?:\s+[A-Z][A-Za-z-]*)*),\s+a Debt Ghost,",
            r"the legacy of \1",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            r"\b([A-Z][A-Za-z-]*(?:\s+[A-Z][A-Za-z-]*)*)'s debt ghost\b",
            r"the legacy of \1",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            r"\bdebt ghost of ([A-Z][A-Za-z-]*(?:\s+[A-Z][A-Za-z-]*)*)\b",
            r"the legacy of \1",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(r",\s*,", ", ", normalized)
        normalized = re.sub(r"\s+,", ",", normalized)
        return " ".join(normalized.split())

    @staticmethod
    def _normalize_late_arc_surface_text(
        text: str,
        *,
        chapter_number: int,
        target_chapters: int,
    ) -> str:
        normalized = " ".join(str(text).split())
        if not normalized or chapter_number < max(1, target_chapters - 4):
            return normalized

        replacements = {
            "ledger anomalies": "burning gaps in the ledger",
            "memetic resonance": "the pressure of borrowed memory",
            "The Silent Council": "The public record",
            "the Silent Council": "the public record",
            "the silent council": "the public record",
        }
        for source, replacement in replacements.items():
            normalized = normalized.replace(source, replacement)
        return " ".join(normalized.split())

    @staticmethod
    def _normalize_terminal_role_language(
        text: str,
        *,
        chapter_number: int,
        target_chapters: int,
        protagonist: str,
        primary_keeper: str,
        vessel_label: str,
    ) -> str:
        normalized = " ".join(str(text).split())
        if (
            not normalized
            or not protagonist
            or chapter_number < max(1, target_chapters - 4)
        ):
            return normalized

        passive_vessel_label = vessel_label or "the vessel"
        vessel_possessive = (
            f"{passive_vessel_label}'"
            if passive_vessel_label.endswith("s")
            else f"{passive_vessel_label}'s"
        )
        vessel_phase_start = max(1, target_chapters - 4)
        living_qualifier_pattern = (
            rf"\b{re.escape(protagonist)}\s+\((?:living|alive|mortal|human|keeper)\)"
        )
        vessel_qualifier_pattern = (
            rf"\b{re.escape(protagonist)}\s+\((?:vessel|shell|blank[- ]slate|silent|mute)\)"
        )
        protagonist_explicitly_marked_as_vessel = (
            re.search(vessel_qualifier_pattern, normalized, flags=re.IGNORECASE) is not None
            or passive_vessel_label.lower() not in {"the vessel", "vessel", "silent vessel"}
        )
        if chapter_number > vessel_phase_start:
            normalized = re.sub(
                living_qualifier_pattern,
                primary_keeper,
                normalized,
                flags=re.IGNORECASE,
            )
            normalized = re.sub(
                vessel_qualifier_pattern,
                passive_vessel_label,
                normalized,
                flags=re.IGNORECASE,
            )
        normalized = re.sub(
            rf"\b{re.escape(protagonist)}\s+understands the duty now falls on {re.escape(protagonist)}\b",
            f"{primary_keeper} understands the duty now falls on {primary_keeper}",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            rf"\b{re.escape(protagonist)}\s+admits {re.escape(protagonist)}\b",
            f"{primary_keeper} admits {passive_vessel_label}",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            rf"\b{re.escape(protagonist)}\s+catches {re.escape(protagonist)}'?s wrist\b",
            f"{primary_keeper} catches {passive_vessel_label}'s wrist",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            rf"\b{re.escape(protagonist)}\s+guides {re.escape(protagonist)}'?s hand\b",
            f"{primary_keeper} guides {passive_vessel_label}'s hand",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            rf"\b{re.escape(protagonist)}\s+\(vessel\)\b",
            passive_vessel_label,
            normalized,
            flags=re.IGNORECASE,
        )
        if chapter_number > vessel_phase_start:
            physical_markers = (
                "hand|wrist|body|mouth|shoulder|voice|silence|weight|face|knuckles|"
                "fingers|arm|arms|eyes|skin|breath|steps|footing|posture"
            )
            if protagonist_explicitly_marked_as_vessel:
                normalized = re.sub(
                    rf"\b{re.escape(protagonist)}'s\s+({physical_markers})\b",
                    lambda match: f"{vessel_possessive} {match.group(1)}",
                    normalized,
                    flags=re.IGNORECASE,
                )
            passive_state_verbs = "waits|sits|lies|slumps|hangs|stays|remains|falls|rests|stands"
            if protagonist_explicitly_marked_as_vessel:
                normalized = re.sub(
                    rf"\b{re.escape(protagonist)}\b(?=\s+({passive_state_verbs})\b)",
                    passive_vessel_label,
                    normalized,
                    flags=re.IGNORECASE,
                )
            intentional_verbs = (
                "leads|guides|orders|writes|speaks|confesses|decides|chooses|explains|reveals|admits|commands|declares|confirms|organizes|directs|teaches|pulls|shoves|drives|forces|moves|reaches|pushes|calls|tells|keeps|holds|carries|names|finishes"
            )
            actor_patterns: list[str] = [
                r"the shell",
                r"the vessel",
                re.escape(passive_vessel_label),
                living_qualifier_pattern,
                vessel_qualifier_pattern,
            ]
            if protagonist_explicitly_marked_as_vessel:
                actor_patterns.append(re.escape(protagonist))
            for actor in actor_patterns:
                normalized = re.sub(
                    rf"\b{actor}\s+({intentional_verbs})\b",
                    lambda match: f"{primary_keeper} {match.group(1)}",
                    normalized,
                    flags=re.IGNORECASE,
                )
            sentence_pattern = re.compile(r"[^.!?]+(?:[.!?]|$)")
            protagonist_pattern = re.compile(rf"\b{re.escape(protagonist)}\b", flags=re.IGNORECASE)
            action_pattern = re.compile(
                rf"\b{re.escape(protagonist)}\b(?=\s+({intentional_verbs}|keeps|holds|carries|names|finishes)\b)",
                flags=re.IGNORECASE,
            )
            passive_actor_pattern = re.compile(
                rf"\b{re.escape(protagonist)}\b(?=\s+(remains|stays|waits|sits|lies|slumps|hangs|rests|stands)\b)",
                flags=re.IGNORECASE,
            )
            rewritten_sentences: list[str] = []
            cursor = 0
            for match in sentence_pattern.finditer(normalized):
                sentence = match.group(0)
                if len(protagonist_pattern.findall(sentence)) > 1:
                    sentence = action_pattern.sub(primary_keeper, sentence, count=1)
                    if len(protagonist_pattern.findall(sentence)) > 1:
                        sentence = protagonist_pattern.sub(passive_vessel_label, sentence, count=1)
                elif (
                    protagonist_pattern.search(sentence) is not None
                    and passive_actor_pattern.search(sentence) is not None
                    and any(
                        token in sentence.lower()
                        for token in (
                            passive_vessel_label.lower(),
                            "the shell",
                            "the vessel",
                            "vessel's",
                            "shell's",
                        )
                    )
                ):
                    sentence = passive_actor_pattern.sub(passive_vessel_label, sentence, count=1)
                rewritten_sentences.append(sentence)
                cursor = match.end()
            if rewritten_sentences and cursor >= len(normalized):
                normalized = "".join(rewritten_sentences)
            normalized = re.sub(
                rf"\b{re.escape(protagonist)}\b(?=\s+(remains|stays|waits|sits|lies|slumps|hangs|rests|stands)\s+(silent|still|unmoving|mute)\b)",
                passive_vessel_label,
                normalized,
                flags=re.IGNORECASE,
            )
            normalized = re.sub(
                rf"\b{re.escape(protagonist)}\s+remains\s+silent\b",
                f"{passive_vessel_label} remains silent",
                normalized,
                flags=re.IGNORECASE,
            )
        return " ".join(normalized.split())

    def _sanitize_storycraft_language(self, ctx: StoryWorkflowContext) -> bool:
        outline = ctx.workflow.outline
        blueprint = ctx.workflow.blueprint
        protagonist = (
            protagonist_name(blueprint.character_bible).strip()
            if blueprint is not None
            else ""
        )
        protagonist, allies = self._resolve_cast_labels(ctx)
        cast_names = (
            set(character_names(blueprint.character_bible))
            if blueprint is not None
            else set()
        )
        keeper_pool = self._resolve_late_arc_keeper_pool(
            ctx,
            protagonist,
            allies,
        )
        primary_keeper = keeper_pool[0] if keeper_pool else protagonist
        vessel_label = self._resolve_terminal_vessel_label(
            ctx,
            protagonist,
            primary_keeper=primary_keeper,
        )
        changed = False
        target_chapters = ctx.story.chapter_count
        phases = self._terminal_phase_numbers(target_chapters)
        sacrifice_number = phases["sacrifice"]
        for chapter in ctx.story.chapters:
            cleaned_summary = self._normalize_storycraft_text(chapter.summary or "")
            cleaned_summary = self._normalize_late_arc_surface_text(
                cleaned_summary,
                chapter_number=chapter.chapter_number,
                target_chapters=target_chapters,
            )
            cleaned_summary = self._normalize_protagonist_name_drift(
                cleaned_summary,
                protagonist,
                cast_names,
            )
            cleaned_summary = self._normalize_terminal_role_language(
                cleaned_summary,
                chapter_number=chapter.chapter_number,
                target_chapters=target_chapters,
                protagonist=protagonist,
                primary_keeper=primary_keeper,
                vessel_label=vessel_label,
            )
            if chapter.chapter_number == sacrifice_number:
                cleaned_summary = self._dedupe_terminal_identity_seal_sentences(cleaned_summary)
            cleaned_summary = self._dedupe_sentences(cleaned_summary)
            if cleaned_summary != (chapter.summary or "").strip():
                chapter.summary = cleaned_summary
                changed = True
            normalized_focus = self._normalize_protagonist_name_drift(
                str(chapter.metadata.get("focus_character", "")).strip(),
                protagonist,
                cast_names,
            )
            if self._is_generic_terminal_placeholder(normalized_focus):
                normalized_focus = primary_keeper or protagonist
            if normalized_focus != str(chapter.metadata.get("focus_character", "")).strip():
                chapter.metadata["focus_character"] = normalized_focus
                changed = True
            if (
                chapter.chapter_number >= max(1, target_chapters - 3)
                and str(chapter.metadata.get("focus_character", "")).strip() in {protagonist, vessel_label}
                and primary_keeper
            ):
                chapter.metadata["focus_character"] = primary_keeper
                changed = True
            normalized_target = self._normalize_protagonist_name_drift(
                str(chapter.metadata.get("relationship_target", "")).strip(),
                protagonist,
                cast_names,
            )
            if normalized_target != str(chapter.metadata.get("relationship_target", "")).strip():
                chapter.metadata["relationship_target"] = normalized_target
                changed = True
            for scene in chapter.scenes:
                cleaned_content = self._normalize_storycraft_text(scene.content)
                cleaned_content = self._normalize_late_arc_surface_text(
                    cleaned_content,
                    chapter_number=chapter.chapter_number,
                    target_chapters=target_chapters,
                )
                cleaned_content = self._normalize_protagonist_name_drift(
                    cleaned_content,
                    protagonist,
                    cast_names,
                )
                cleaned_content = self._normalize_terminal_role_language(
                    cleaned_content,
                    chapter_number=chapter.chapter_number,
                    target_chapters=target_chapters,
                    protagonist=protagonist,
                    primary_keeper=primary_keeper,
                    vessel_label=vessel_label,
                )
                if chapter.chapter_number == sacrifice_number:
                    cleaned_content = self._dedupe_terminal_identity_seal_sentences(cleaned_content)
                cleaned_content = self._dedupe_sentences(cleaned_content)
                if cleaned_content != scene.content:
                    scene.update_content(cleaned_content)
                    changed = True

        if outline is None:
            return changed

        for outline_chapter in outline.chapters:
            cleaned_summary = self._normalize_storycraft_text(outline_chapter.summary)
            cleaned_summary = self._normalize_late_arc_surface_text(
                cleaned_summary,
                chapter_number=outline_chapter.chapter_number,
                target_chapters=target_chapters,
            )
            cleaned_summary = self._normalize_protagonist_name_drift(
                cleaned_summary,
                protagonist,
                cast_names,
            )
            cleaned_summary = self._normalize_terminal_role_language(
                cleaned_summary,
                chapter_number=outline_chapter.chapter_number,
                target_chapters=target_chapters,
                protagonist=protagonist,
                primary_keeper=primary_keeper,
                vessel_label=vessel_label,
            )
            if outline_chapter.chapter_number == sacrifice_number:
                cleaned_summary = self._dedupe_terminal_identity_seal_sentences(cleaned_summary)
            cleaned_summary = self._dedupe_sentences(cleaned_summary)
            if cleaned_summary != outline_chapter.summary.strip():
                outline_chapter.summary = cleaned_summary
                changed = True

            cleaned_objective = self._normalize_storycraft_text(outline_chapter.chapter_objective)
            cleaned_objective = self._normalize_late_arc_surface_text(
                cleaned_objective,
                chapter_number=outline_chapter.chapter_number,
                target_chapters=target_chapters,
            )
            cleaned_objective = self._normalize_protagonist_name_drift(
                cleaned_objective,
                protagonist,
                cast_names,
            )
            cleaned_objective = self._normalize_terminal_role_language(
                cleaned_objective,
                chapter_number=outline_chapter.chapter_number,
                target_chapters=target_chapters,
                protagonist=protagonist,
                primary_keeper=primary_keeper,
                vessel_label=vessel_label,
            )
            if outline_chapter.chapter_number == sacrifice_number:
                cleaned_objective = self._dedupe_terminal_identity_seal_sentences(cleaned_objective)
            cleaned_objective = self._dedupe_sentences(cleaned_objective)
            if cleaned_objective != outline_chapter.chapter_objective.strip():
                outline_chapter.chapter_objective = cleaned_objective
                changed = True

            cleaned_hook = self._normalize_storycraft_text(outline_chapter.hook)
            cleaned_hook = self._normalize_late_arc_surface_text(
                cleaned_hook,
                chapter_number=outline_chapter.chapter_number,
                target_chapters=target_chapters,
            )
            cleaned_hook = self._normalize_protagonist_name_drift(
                cleaned_hook,
                protagonist,
                cast_names,
            )
            cleaned_hook = self._normalize_terminal_role_language(
                cleaned_hook,
                chapter_number=outline_chapter.chapter_number,
                target_chapters=target_chapters,
                protagonist=protagonist,
                primary_keeper=primary_keeper,
                vessel_label=vessel_label,
            )
            cleaned_hook = self._dedupe_sentences(cleaned_hook)
            if cleaned_hook != outline_chapter.hook.strip():
                outline_chapter.hook = cleaned_hook
                changed = True

            cleaned_promise = self._normalize_storycraft_text(outline_chapter.promise)
            cleaned_promise = self._normalize_late_arc_surface_text(
                cleaned_promise,
                chapter_number=outline_chapter.chapter_number,
                target_chapters=target_chapters,
            )
            cleaned_promise = self._normalize_protagonist_name_drift(
                cleaned_promise,
                protagonist,
                cast_names,
            )
            cleaned_promise = self._normalize_terminal_role_language(
                cleaned_promise,
                chapter_number=outline_chapter.chapter_number,
                target_chapters=target_chapters,
                protagonist=protagonist,
                primary_keeper=primary_keeper,
                vessel_label=vessel_label,
            )
            cleaned_promise = self._dedupe_sentences(cleaned_promise)
            if cleaned_promise != outline_chapter.promise.strip():
                outline_chapter.promise = cleaned_promise
                changed = True

            cleaned_payoff = self._normalize_storycraft_text(outline_chapter.promised_payoff)
            cleaned_payoff = self._normalize_late_arc_surface_text(
                cleaned_payoff,
                chapter_number=outline_chapter.chapter_number,
                target_chapters=target_chapters,
            )
            cleaned_payoff = self._normalize_protagonist_name_drift(
                cleaned_payoff,
                protagonist,
                cast_names,
            )
            cleaned_payoff = self._normalize_terminal_role_language(
                cleaned_payoff,
                chapter_number=outline_chapter.chapter_number,
                target_chapters=target_chapters,
                protagonist=protagonist,
                primary_keeper=primary_keeper,
                vessel_label=vessel_label,
            )
            cleaned_payoff = self._dedupe_sentences(cleaned_payoff)
            if cleaned_payoff != outline_chapter.promised_payoff.strip():
                outline_chapter.promised_payoff = cleaned_payoff
                changed = True

        return changed

    def _enforce_terminal_arc_phase_clarity(
        self,
        ctx: StoryWorkflowContext,
        *,
        issue_context: str = "",
        issue_verbatim_context: str = "",
    ) -> bool:
        outline = ctx.workflow.outline
        blueprint = ctx.workflow.blueprint
        protagonist = (
            protagonist_name(blueprint.character_bible).strip()
            if blueprint is not None
            else ""
        )
        frame = self._build_terminal_arc_semantic_frame(
            ctx,
            issue_context=issue_context,
        )
        protagonist = protagonist or frame.protagonist
        primary_keeper = frame.primary_keeper
        supporting_witness = frame.supporting_witness
        public_witness = frame.public_witness
        vessel_label = frame.vessel_label
        antagonist_label = self._resolve_primary_antagonist_label(ctx, protagonist)
        phases = frame.phase_map
        changed = False
        outline_by_number = (
            {chapter.chapter_number: chapter for chapter in outline.chapters}
            if outline is not None
            else {}
        )
        phase_clarity_sentences = {
            phases["aftermath"]: {
                "summary": (
                    f"{primary_keeper} fails once in front of the line, {public_witness or supporting_witness or primary_keeper} catches the break before it spreads, and a fresh echo from the broken rule forces the room to react while {vessel_label} stays heavy and unchanged."
                ),
                "objective": (
                    f"{primary_keeper} moves from visible grief into command only after one failed wake attempt, and the loss registers as a bodily reaction before command resumes. A new disturbance forces the line to move instead of merely observe, and the earlier promise remains only a remembered echo."
                ),
            },
            phases["rule_revelation"]: {
                "summary": (
                    f"Before the seal closes, {supporting_witness or primary_keeper} tests the evidence in public, one cold touch or token at {vessel_label} stays answerless, and the rule surfaces through proof while a fresh echo presses back from the wall and the frame sheds dust."
                ),
                "objective": (
                    f"Give the phase one tangible gesture between {supporting_witness or primary_keeper} and {vessel_label}, then show why that gesture cannot restore consciousness and why the evidence has to move outward. The breaking event should feel immediate enough that the living have to answer it, while the vessel motion stays limited to residual muscle memory or a brief lamp-shiver."
                ),
            },
            phases["public_reckoning"]: {
                "summary": (
                    f"The first surge hits before the keeper can finish the explanation. First, {public_witness or primary_keeper} moves while rain drives across the square and a banner snaps overhead. Then, {supporting_witness or primary_keeper} closes the gap. {antagonist_label} stands under guard while the line names the mechanism and {vessel_label} remains a mute shape at the edge of the square. When the burned names are spoken aloud, the ledger darkens again."
                ),
                "objective": (
                    f"The public reckoning moves in distinct beats: threat, near-break tension, witness intervention, mechanism, and resolution. Burned names darken the ledger when they are spoken aloud, {antagonist_label} faces the square, and the vessel stays mute while the living answer the cost."
                ),
            },
            phases["closure"]: {
                "summary": (
                    f"Closure lands in three separate scenes: private closure first, public square second, and ledger interaction last. {frame.public_witness} names one remembered habit aloud in the private scene, {vessel_label} gives no answering voice while the rain ticks on the eaves, and {primary_keeper} turns that silence into the public form the survivors now have to keep while {frame.public_cost_example}. A blank page then takes a new name as {frame.public_witness} speaks it aloud, the lamp flame gutters, and a window shudders in the draft so the ending closes on a visible leak rather than a quiet hint."
                ),
                "objective": (
                    "Three distinct scenes carry the ending: private closure, public confession, and a ledger handoff. The living witness names a remembered detail, the vessel remains a cold presence, the public square keeps the cost concrete, and the final ledger scene ends on a visible anomaly that triggers a small physical reaction."
                ),
            },
        }
        for chapter in ctx.story.chapters:
            clarity = phase_clarity_sentences.get(chapter.chapter_number)
            if clarity is None:
                continue
            updated_summary = self._append_unique_sentence(chapter.summary or "", clarity["summary"])
            if chapter.chapter_number == phases["aftermath"]:
                updated_summary = self._prefer_terminal_phase_summary(
                    updated_summary,
                    clarity["summary"],
                    required_markers=("permanent", "ordered"),
                )
            if chapter.chapter_number == phases["rule_revelation"]:
                updated_summary = self._prefer_terminal_phase_summary(
                    updated_summary,
                    clarity["summary"],
                    required_markers=("memorial proof", "returning mind"),
                )
            if chapter.chapter_number == phases["public_reckoning"]:
                updated_summary = self._prefer_terminal_phase_summary(
                    updated_summary,
                    clarity["summary"],
                    required_markers=("break", "gap", "mechanism"),
                )
            if chapter.chapter_number == phases["closure"]:
                updated_summary = self._prefer_terminal_phase_summary(
                    updated_summary,
                    clarity["summary"],
                    required_markers=("blank page", "visible leak"),
                )
            if updated_summary != (chapter.summary or "").strip():
                chapter.summary = updated_summary
                changed = True
            updated_objective = self._append_unique_sentence(
                str(chapter.metadata.get("chapter_objective", "")).strip(),
                clarity["objective"],
            )
            if chapter.chapter_number == phases["aftermath"]:
                updated_objective = self._prefer_terminal_phase_summary(
                    updated_objective,
                    clarity["objective"],
                    required_markers=("permanent", "stillness"),
                )
            if chapter.chapter_number == phases["rule_revelation"]:
                updated_objective = self._prefer_terminal_phase_summary(
                    updated_objective,
                    clarity["objective"],
                    required_markers=("restore consciousness", "touch"),
                )
            if chapter.chapter_number == phases["public_reckoning"]:
                updated_objective = self._prefer_terminal_phase_summary(
                    updated_objective,
                    clarity["objective"],
                    required_markers=("break", "mechanism"),
                )
            if chapter.chapter_number == phases["closure"]:
                updated_objective = self._prefer_terminal_phase_summary(
                    updated_objective,
                    clarity["objective"],
                    required_markers=("no answering voice", "silence"),
                )
            if updated_objective != str(chapter.metadata.get("chapter_objective", "")).strip():
                chapter.metadata["chapter_objective"] = updated_objective
                changed = True
            outline_chapter = outline_by_number.get(chapter.chapter_number)
            if outline_chapter is not None:
                outlined_summary = self._append_unique_sentence(
                    outline_chapter.summary,
                    clarity["summary"],
                )
                if chapter.chapter_number == phases["aftermath"]:
                    outlined_summary = self._prefer_terminal_phase_summary(
                        outlined_summary,
                        clarity["summary"],
                        required_markers=("permanent", "ordered"),
                    )
                if chapter.chapter_number == phases["rule_revelation"]:
                    outlined_summary = self._prefer_terminal_phase_summary(
                        outlined_summary,
                        clarity["summary"],
                        required_markers=("memorial proof", "returning mind"),
                    )
                if chapter.chapter_number == phases["public_reckoning"]:
                    outlined_summary = self._prefer_terminal_phase_summary(
                        outlined_summary,
                        clarity["summary"],
                        required_markers=("break", "gap", "mechanism"),
                    )
                if chapter.chapter_number == phases["closure"]:
                    outlined_summary = self._prefer_terminal_phase_summary(
                        outlined_summary,
                        clarity["summary"],
                        required_markers=("no answering voice", "silence"),
                    )
                if outlined_summary != outline_chapter.summary.strip():
                    outline_chapter.summary = outlined_summary
                    changed = True
                outlined_objective = self._append_unique_sentence(
                    outline_chapter.chapter_objective,
                    clarity["objective"],
                )
                if chapter.chapter_number == phases["aftermath"]:
                    outlined_objective = self._prefer_terminal_phase_summary(
                        outlined_objective,
                        clarity["objective"],
                        required_markers=("permanent", "stillness"),
                    )
                if chapter.chapter_number == phases["rule_revelation"]:
                    outlined_objective = self._prefer_terminal_phase_summary(
                        outlined_objective,
                        clarity["objective"],
                        required_markers=("restore consciousness", "touch"),
                    )
                if chapter.chapter_number == phases["public_reckoning"]:
                    outlined_objective = self._prefer_terminal_phase_summary(
                        outlined_objective,
                        clarity["objective"],
                        required_markers=("break", "mechanism"),
                    )
                if chapter.chapter_number == phases["closure"]:
                    outlined_objective = self._prefer_terminal_phase_summary(
                        outlined_objective,
                        clarity["objective"],
                        required_markers=("no answering voice", "silence"),
                    )
                if outlined_objective != outline_chapter.chapter_objective.strip():
                    outline_chapter.chapter_objective = outlined_objective
                    changed = True
        continuity_witness = next(
            (
                candidate
                for candidate in (public_witness, supporting_witness)
                if candidate and candidate not in {primary_keeper, protagonist}
            ),
            "",
        )
        if continuity_witness and self._ensure_terminal_witness_continuity(
            ctx,
            witness_name=continuity_witness,
        ):
            changed = True
        if self._reinforce_terminal_rule_contrast(
            ctx,
            primary_keeper=primary_keeper,
            issue_verbatim_context=issue_verbatim_context,
        ):
            changed = True
        if self._honor_departed_allies_in_rule_revelation(ctx):
            changed = True
        if self._amplify_terminal_witness_interactions(
            ctx,
            primary_keeper=primary_keeper,
            supporting_witness=supporting_witness,
            public_witness=public_witness,
        ):
            changed = True
        concrete_memory_detail = self._resolve_terminal_memory_detail(
            ctx,
            protagonist,
        )
        if concrete_memory_detail and self._concretize_terminal_memory_language(
            ctx,
            memory_detail=concrete_memory_detail,
        ):
            changed = True
        if concrete_memory_detail and self._anchor_terminal_keeper_interiority(
            ctx,
            primary_keeper=primary_keeper,
            vessel_label=vessel_label,
            memory_detail=concrete_memory_detail,
        ):
            changed = True
        if self._clarify_terminal_motor_residue_language(
            ctx,
            protagonist=protagonist,
            vessel_label=vessel_label,
        ):
            changed = True
        if self._finalize_terminal_arc_surface(
            ctx,
            protagonist=protagonist,
            primary_keeper=primary_keeper,
            vessel_label=vessel_label,
        ):
            changed = True
        return changed

    def _finalize_terminal_arc_surface(
        self,
        ctx: StoryWorkflowContext,
        *,
        protagonist: str,
        primary_keeper: str,
        vessel_label: str,
    ) -> bool:
        target_chapters = ctx.story.chapter_count
        late_start = max(1, target_chapters - 4)
        outline = ctx.workflow.outline
        outline_by_number = (
            {chapter.chapter_number: chapter for chapter in outline.chapters}
            if outline is not None
            else {}
        )
        changed = False
        for chapter in ctx.story.chapters:
            if chapter.chapter_number < late_start:
                continue
            cleaned_summary = self._strip_authorial_terminal_summary_instructions(
                chapter.summary or ""
            )
            cleaned_summary = self._normalize_terminal_role_language(
                cleaned_summary,
                chapter_number=chapter.chapter_number,
                target_chapters=target_chapters,
                protagonist=protagonist,
                primary_keeper=primary_keeper,
                vessel_label=vessel_label,
            )
            cleaned_summary = self._dedupe_sentences(cleaned_summary)
            if cleaned_summary != (chapter.summary or "").strip():
                chapter.summary = cleaned_summary
                changed = True

            outline_chapter = outline_by_number.get(chapter.chapter_number)
            if outline_chapter is not None:
                outlined_summary = self._strip_authorial_terminal_summary_instructions(
                    outline_chapter.summary
                )
                outlined_summary = self._normalize_terminal_role_language(
                    outlined_summary,
                    chapter_number=outline_chapter.chapter_number,
                    target_chapters=target_chapters,
                    protagonist=protagonist,
                    primary_keeper=primary_keeper,
                    vessel_label=vessel_label,
                )
                outlined_summary = self._dedupe_sentences(outlined_summary)
                if outlined_summary != outline_chapter.summary.strip():
                    outline_chapter.summary = outlined_summary
                    changed = True
        return changed

    def _anchor_terminal_keeper_interiority(
        self,
        ctx: StoryWorkflowContext,
        *,
        primary_keeper: str,
        vessel_label: str,
        memory_detail: str,
    ) -> bool:
        if not primary_keeper or not memory_detail:
            return False
        phases = self._terminal_phase_numbers(ctx.story.chapter_count)
        objective_by_phase = {
            phases["aftermath"]: (
                f"Keep {memory_detail} on the page while {primary_keeper} turns from the failed wake attempt to visible public duty, and keep {vessel_label} silent so the memory reads as surviving witness knowledge rather than returning interior life."
            ),
            phases["closure"]: (
                f"Let a living witness name {memory_detail} before {primary_keeper} confirms the new public order, and keep {vessel_label} silent so the remembered detail closes the loss without implying a return."
            ),
        }
        outline = ctx.workflow.outline
        outline_by_number = (
            {chapter.chapter_number: chapter for chapter in outline.chapters}
            if outline is not None
            else {}
        )
        changed = False
        for chapter in ctx.story.chapters:
            sentence = objective_by_phase.get(chapter.chapter_number)
            if sentence is None:
                continue
            updated_objective = self._append_unique_sentence(
                str(chapter.metadata.get("chapter_objective", "")).strip(),
                sentence,
            )
            if updated_objective != str(chapter.metadata.get("chapter_objective", "")).strip():
                chapter.metadata["chapter_objective"] = updated_objective
                changed = True
            outline_chapter = outline_by_number.get(chapter.chapter_number)
            if outline_chapter is not None:
                outlined_objective = self._append_unique_sentence(
                    outline_chapter.chapter_objective,
                    sentence,
                )
                if outlined_objective != outline_chapter.chapter_objective.strip():
                    outline_chapter.chapter_objective = outlined_objective
                    changed = True
        return changed

    def _reinforce_terminal_rule_contrast(
        self,
        ctx: StoryWorkflowContext,
        *,
        primary_keeper: str,
        issue_verbatim_context: str,
    ) -> bool:
        normalized_issue_text = " ".join(str(issue_verbatim_context).split())
        if "distinction between" not in normalized_issue_text.lower():
            return False
        match = re.search(
            r"distinction between ['\"]([^'\"]+)['\"] and ['\"]([^'\"]+)['\"]",
            normalized_issue_text,
            flags=re.IGNORECASE,
        )
        if match is None:
            return False
        first_entity = " ".join(match.group(1).split()).strip()
        second_entity = " ".join(match.group(2).split()).strip()
        if not first_entity or not second_entity:
            return False

        lowered_issue_text = normalized_issue_text.lower()
        first_behavior = (
            "haunt the wider public line"
            if "haunt" in lowered_issue_text
            else "spread with the wider public debt"
        )
        second_behavior = (
            "trap one breaker inside a private contradiction"
            if "trap" in lowered_issue_text
            else "close around one broken contradiction at a time"
        )
        contrast_sentence = (
            f"{primary_keeper} states the rule aloud: {first_entity} {first_behavior}, while {second_entity} {second_behavior}, so the crowd stops treating the two threats as interchangeable before the final sacrifice."
        )
        objective_sentence = (
            f"Make {primary_keeper} name the difference between {first_entity} and {second_entity} in plain causal terms before the terminal sacrifice so the climax keeps its world-rule logic."
        )
        phases = self._terminal_phase_numbers(ctx.story.chapter_count)
        bridge_number = max(1, phases["sacrifice"] - 2)
        outline = ctx.workflow.outline
        changed = False

        chapter = next(
            (item for item in ctx.story.chapters if item.chapter_number == bridge_number),
            None,
        )
        if chapter is not None:
            updated_summary = self._append_unique_sentence(chapter.summary or "", contrast_sentence)
            if updated_summary != (chapter.summary or "").strip():
                chapter.summary = updated_summary
                changed = True
            current_objective = str(chapter.metadata.get("chapter_objective", "")).strip()
            updated_objective = self._append_unique_sentence(
                current_objective,
                objective_sentence,
            )
            if updated_objective != current_objective:
                chapter.metadata["chapter_objective"] = updated_objective
                changed = True

        if outline is not None:
            outline_chapter = next(
                (item for item in outline.chapters if item.chapter_number == bridge_number),
                None,
            )
            if outline_chapter is not None:
                updated_summary = self._append_unique_sentence(
                    outline_chapter.summary,
                    contrast_sentence,
                )
                if updated_summary != outline_chapter.summary.strip():
                    outline_chapter.summary = updated_summary
                    changed = True
                updated_objective = self._append_unique_sentence(
                    outline_chapter.chapter_objective,
                    objective_sentence,
                )
                if updated_objective != outline_chapter.chapter_objective.strip():
                    outline_chapter.chapter_objective = updated_objective
                    changed = True

        return changed

    def _honor_departed_allies_in_rule_revelation(
        self,
        ctx: StoryWorkflowContext,
    ) -> bool:
        blueprint = ctx.workflow.blueprint
        if blueprint is None:
            return False
        protagonist = protagonist_name(blueprint.character_bible).strip()
        departed_characters = self._combined_departed_characters(ctx, protagonist)
        phases = self._terminal_phase_numbers(ctx.story.chapter_count)
        rule_revelation_number = phases["rule_revelation"]
        departed_allies = [
            name
            for name, chapter_number in sorted(
                departed_characters.items(),
                key=lambda item: item[1],
            )
            if name
            and name != protagonist
            and chapter_number <= rule_revelation_number
        ]
        if not departed_allies:
            return False
        named_allies = ", ".join(departed_allies[:2])
        sentence = (
            f"Before the seal closes, the public record names {named_allies} aloud so the city carries their sacrifice in public record instead of leaving it as private grief."
        )
        outline = ctx.workflow.outline
        changed = False
        chapter = next(
            (
                item
                for item in ctx.story.chapters
                if item.chapter_number == rule_revelation_number
            ),
            None,
        )
        if chapter is not None:
            updated_summary = self._append_unique_sentence(chapter.summary or "", sentence)
            if updated_summary != (chapter.summary or "").strip():
                chapter.summary = updated_summary
                changed = True
        if outline is not None:
            outline_chapter = next(
                (
                    item
                    for item in outline.chapters
                    if item.chapter_number == rule_revelation_number
                ),
                None,
            )
            if outline_chapter is not None:
                outlined_summary = self._append_unique_sentence(
                    outline_chapter.summary,
                    sentence,
                )
                if outlined_summary != outline_chapter.summary.strip():
                    outline_chapter.summary = outlined_summary
                    changed = True
        return changed

    def _amplify_terminal_witness_interactions(
        self,
        ctx: StoryWorkflowContext,
        *,
        primary_keeper: str,
        supporting_witness: str,
        public_witness: str,
    ) -> bool:
        if not supporting_witness and not public_witness:
            return False
        phases = self._terminal_phase_numbers(ctx.story.chapter_count)
        aftermath_sentence = (
            f"{supporting_witness or primary_keeper} keeps the burned names audible while {public_witness} pins the rail steady long enough for {primary_keeper} to give the first living order."
            if public_witness and public_witness not in {supporting_witness, primary_keeper}
            else f"{supporting_witness or primary_keeper} keeps the burned names audible and braces the rail long enough for {primary_keeper} to force the line through the first break."
        )
        reckoning_sentence = (
            f"{public_witness} drags the wavering edge of the line back into place while {supporting_witness or primary_keeper} names the next mark, giving {primary_keeper} room to expose the mechanism in public."
            if public_witness and public_witness not in {supporting_witness, primary_keeper}
            else f"{supporting_witness or primary_keeper} names the next mark and braces the rail long enough for {primary_keeper} to expose the mechanism in public."
        )
        closure_sentence = (
            f"{supporting_witness or primary_keeper} starts the first clean entry while {public_witness} passes the ledger forward, proving the new order can move on living hands instead of on the silent vessel."
            if public_witness and public_witness not in {supporting_witness, primary_keeper}
            else f"{supporting_witness or primary_keeper} starts the first clean entry in front of the square, proving the new order can move on living hands instead of on the silent vessel."
        )
        interaction_specs = {
            phases["aftermath"]: aftermath_sentence,
            phases["public_reckoning"]: reckoning_sentence,
            phases["closure"]: closure_sentence,
        }
        outline = ctx.workflow.outline
        outline_by_number = (
            {chapter.chapter_number: chapter for chapter in outline.chapters}
            if outline is not None
            else {}
        )
        changed = False
        for chapter in ctx.story.chapters:
            interaction_sentence = interaction_specs.get(chapter.chapter_number)
            if not interaction_sentence:
                continue
            updated_summary = self._append_unique_sentence(
                chapter.summary or "",
                interaction_sentence,
            )
            if updated_summary != (chapter.summary or "").strip():
                chapter.summary = updated_summary
                changed = True
            outline_chapter = outline_by_number.get(chapter.chapter_number)
            if outline_chapter is not None:
                outlined_summary = self._append_unique_sentence(
                    outline_chapter.summary,
                    interaction_sentence,
                )
                if outlined_summary != outline_chapter.summary.strip():
                    outline_chapter.summary = outlined_summary
                    changed = True
        return changed

    def _ensure_terminal_witness_continuity(
        self,
        ctx: StoryWorkflowContext,
        *,
        witness_name: str,
    ) -> bool:
        outline = ctx.workflow.outline
        phases = self._terminal_phase_numbers(ctx.story.chapter_count)
        aftermath_number = phases["aftermath"]
        sacrifice_number = phases["sacrifice"]
        early_numbers = {sacrifice_number, aftermath_number}
        early_text = " ".join(
            part
            for chapter in ctx.story.chapters
            if chapter.chapter_number in early_numbers
            for part in (
                chapter.summary or "",
                str(chapter.metadata.get("chapter_objective", "")).strip(),
            )
            if part
        )
        if outline is not None:
            early_text = " ".join(
                [
                    early_text,
                    *(
                        part
                        for chapter in outline.chapters
                        if chapter.chapter_number in early_numbers
                        for part in (chapter.summary, chapter.chapter_objective, chapter.hook)
                        if part
                    ),
                ]
            ).strip()
        if witness_name.lower() in early_text.lower():
            return False

        aftermath_chapter = next(
            (
                chapter
                for chapter in ctx.story.chapters
                if chapter.chapter_number == aftermath_number
            ),
            None,
        )
        if aftermath_chapter is None:
            return False

        summary_sentence = (
            f"{witness_name} stays at the edge of the public line from the first night onward, counting hands and watching the rail long before the public reckoning needs that steadiness."
        )
        objective_sentence = (
            f"Let {witness_name} register the line from the edge early enough that the later intervention feels earned instead of sudden."
        )
        changed = False
        updated_summary = self._append_unique_sentence(
            aftermath_chapter.summary or "",
            summary_sentence,
        )
        if updated_summary != (aftermath_chapter.summary or "").strip():
            aftermath_chapter.summary = updated_summary
            changed = True
        updated_objective = self._append_unique_sentence(
            str(aftermath_chapter.metadata.get("chapter_objective", "")).strip(),
            objective_sentence,
        )
        if updated_objective != str(
            aftermath_chapter.metadata.get("chapter_objective", "")
        ).strip():
            aftermath_chapter.metadata["chapter_objective"] = updated_objective
            changed = True
        if outline is not None:
            outline_chapter = next(
                (
                    chapter
                    for chapter in outline.chapters
                    if chapter.chapter_number == aftermath_number
                ),
                None,
            )
            if outline_chapter is not None:
                outlined_summary = self._append_unique_sentence(
                    outline_chapter.summary,
                    summary_sentence,
                )
                if outlined_summary != outline_chapter.summary.strip():
                    outline_chapter.summary = outlined_summary
                    changed = True
                outlined_objective = self._append_unique_sentence(
                    outline_chapter.chapter_objective,
                    objective_sentence,
                )
                if outlined_objective != outline_chapter.chapter_objective.strip():
                    outline_chapter.chapter_objective = outlined_objective
                    changed = True
        return changed

    def _resolve_terminal_memory_detail(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
    ) -> str:
        blueprint = ctx.workflow.blueprint
        outline = ctx.workflow.outline
        candidate_fragments: list[str] = []
        if blueprint is not None:
            profile = character_profile(blueprint.character_bible, protagonist)
            candidate_fragments.extend(
                str(profile.get(key, "")).strip()
                for key in ("summary", "motivation", "goal", "arc", "notes")
                if str(profile.get(key, "")).strip()
            )
        early_cutoff = max(3, min(ctx.story.chapter_count // 3, 6))
        outline_by_number = (
            {chapter.chapter_number: chapter for chapter in outline.chapters}
            if outline is not None
            else {}
        )
        for chapter in ctx.story.chapters:
            if chapter.chapter_number > early_cutoff:
                continue
            outline_chapter = outline_by_number.get(chapter.chapter_number)
            candidate_fragments.extend(
                part
                for part in (
                    chapter.summary or "",
                    chapter.current_scene.content if chapter.current_scene is not None else "",
                    outline_chapter.summary if outline_chapter is not None else "",
                )
                if part
            )

        concrete_tokens = (
            "rain",
            "smoke",
            "ink",
            "bell",
            "coat",
            "cuff",
            "rope",
            "ledger",
            "lantern",
            "market",
            "dock",
            "stone",
            "bread",
            "salt",
            "tea",
            "mud",
            "wood",
            "step",
            "street",
            "child",
            "ferry",
            "stair",
            "wrist",
            "thumb",
        )
        abstract_tokens = (
            "chapter",
            "objective",
            "hook",
            "must",
            "public reckoning",
            "witness line",
            "closure",
            "phase",
        )
        best_clause = ""
        best_score = -1
        for fragment in candidate_fragments:
            clauses = re.split(r"(?<=[,.;!?])\s+|(?<=:)\s+", str(fragment))
            for clause in clauses:
                normalized = " ".join(str(clause).split()).strip(" .,:;!?")
                if not normalized:
                    continue
                lowered = normalized.lower()
                if any(token in lowered for token in abstract_tokens):
                    continue
                words = normalized.split()
                if len(words) < 4 or len(words) > 18:
                    continue
                score = 0
                if protagonist and protagonist.lower() in lowered:
                    score += 3
                if any(token in lowered for token in concrete_tokens):
                    score += 4
                if any(char.isdigit() for char in normalized):
                    score += 1
                if score > best_score:
                    best_clause = normalized
                    best_score = score
        if not best_clause:
            return "the ordinary habit the hero used before every risk"

        detail = re.sub(
            rf"^\b{re.escape(protagonist)}\b\s+",
            "",
            best_clause,
            flags=re.IGNORECASE,
        ).strip(" .,:;!?")
        if not detail:
            detail = best_clause.strip(" .,:;!?")
        if not re.match(r"^(the|a|an|his|her|their)\b", detail, flags=re.IGNORECASE):
            detail = f"the {detail[:1].lower()}{detail[1:]}"
        return detail

    def _concretize_terminal_memory_language(
        self,
        ctx: StoryWorkflowContext,
        *,
        memory_detail: str,
    ) -> bool:
        if not memory_detail:
            return False
        outline = ctx.workflow.outline
        phases = self._terminal_phase_numbers(ctx.story.chapter_count)
        target_numbers = {phases["public_reckoning"], phases["closure"]}
        changed = False
        for chapter in ctx.story.chapters:
            if chapter.chapter_number not in target_numbers:
                continue
            for field in ("summary",):
                current = getattr(chapter, field) or ""
                updated = self._replace_abstract_terminal_memory_reference(
                    current,
                    memory_detail,
                )
                if updated != current:
                    setattr(chapter, field, updated)
                    changed = True
            current_objective = str(chapter.metadata.get("chapter_objective", "")).strip()
            updated_objective = self._replace_abstract_terminal_memory_reference(
                current_objective,
                memory_detail,
            )
            if updated_objective != current_objective:
                chapter.metadata["chapter_objective"] = updated_objective
                changed = True
            current_hook = str(chapter.metadata.get("outline_hook", "")).strip()
            updated_hook = self._replace_abstract_terminal_memory_reference(
                current_hook,
                memory_detail,
            )
            if updated_hook != current_hook:
                chapter.metadata["outline_hook"] = updated_hook
                changed = True
        if outline is not None:
            for outline_chapter in outline.chapters:
                if outline_chapter.chapter_number not in target_numbers:
                    continue
                updated_summary = self._replace_abstract_terminal_memory_reference(
                    outline_chapter.summary,
                    memory_detail,
                )
                if updated_summary != outline_chapter.summary:
                    outline_chapter.summary = updated_summary
                    changed = True
                updated_objective = self._replace_abstract_terminal_memory_reference(
                    outline_chapter.chapter_objective,
                    memory_detail,
                )
                if updated_objective != outline_chapter.chapter_objective:
                    outline_chapter.chapter_objective = updated_objective
                    changed = True
                updated_hook = self._replace_abstract_terminal_memory_reference(
                    outline_chapter.hook,
                    memory_detail,
                )
                if updated_hook != outline_chapter.hook:
                    outline_chapter.hook = updated_hook
                    changed = True
        return changed

    def _clarify_terminal_motor_residue_language(
        self,
        ctx: StoryWorkflowContext,
        *,
        protagonist: str,
        vessel_label: str,
    ) -> bool:
        outline = ctx.workflow.outline
        phases = self._terminal_phase_numbers(ctx.story.chapter_count)
        target_numbers = {
            phases["rule_revelation"],
            phases["public_reckoning"],
            phases["closure"],
        }
        residue_clause = (
            f"Any movement left in the hand is only the old training finishing itself as a reflex through {vessel_label}; it carries no fresh intent and does not signal returning consciousness in {protagonist}."
        )
        trigger_tokens = ("note", "written", "writes", "hand")
        safety_tokens = (
            "memory-thread residue",
            "motor habit",
            "motor-residue",
            "echo-remnant",
            "involuntary",
            "no fresh intent",
            "ink artifact",
        )
        changed = False

        def needs_clarification(text: str) -> bool:
            lowered = " ".join(str(text).split()).lower()
            return bool(lowered) and any(token in lowered for token in trigger_tokens) and not any(
                token in lowered for token in safety_tokens
            )

        for chapter in ctx.story.chapters:
            if chapter.chapter_number not in target_numbers:
                continue
            if needs_clarification(chapter.summary or ""):
                updated_summary = self._append_unique_sentence(
                    chapter.summary or "",
                    residue_clause,
                )
                if updated_summary != (chapter.summary or "").strip():
                    chapter.summary = updated_summary
                    changed = True
            current_hook = str(chapter.metadata.get("outline_hook", "")).strip()
            if needs_clarification(current_hook):
                updated_hook = self._append_unique_sentence(current_hook, residue_clause)
                if updated_hook != current_hook:
                    chapter.metadata["outline_hook"] = updated_hook
                    changed = True
            current_objective = str(chapter.metadata.get("chapter_objective", "")).strip()
            if needs_clarification(current_objective):
                updated_objective = self._append_unique_sentence(
                    current_objective,
                    residue_clause,
                )
                if updated_objective != current_objective:
                    chapter.metadata["chapter_objective"] = updated_objective
                    changed = True
        if outline is not None:
            for outline_chapter in outline.chapters:
                if outline_chapter.chapter_number not in target_numbers:
                    continue
                if needs_clarification(outline_chapter.summary):
                    updated_summary = self._append_unique_sentence(
                        outline_chapter.summary,
                        residue_clause,
                    )
                    if updated_summary != outline_chapter.summary:
                        outline_chapter.summary = updated_summary
                        changed = True
                if needs_clarification(outline_chapter.chapter_objective):
                    updated_objective = self._append_unique_sentence(
                        outline_chapter.chapter_objective,
                        residue_clause,
                    )
                    if updated_objective != outline_chapter.chapter_objective:
                        outline_chapter.chapter_objective = updated_objective
                        changed = True
                if needs_clarification(outline_chapter.hook):
                    updated_hook = self._append_unique_sentence(
                        outline_chapter.hook,
                        residue_clause,
                    )
                    if updated_hook != outline_chapter.hook:
                        outline_chapter.hook = updated_hook
                        changed = True
        return changed

    @staticmethod
    def _replace_abstract_terminal_memory_reference(
        text: str,
        memory_detail: str,
    ) -> str:
        normalized = " ".join(str(text).split())
        if not normalized or not memory_detail:
            return normalized
        patterns = (
            r"one specific,\s*small truth about (?:the hero|the protagonist)",
            r"one specific,\s*small truth",
            r"a specific,\s*small truth",
            r"small truth",
            r"one concrete remembered detail from the protagonist's earlier life",
            r"one concrete remembered detail from the life now gone",
            r"one concrete remembered detail",
            r"a concrete remembered detail",
        )
        updated = normalized
        for pattern in patterns:
            updated = re.sub(pattern, memory_detail, updated, flags=re.IGNORECASE)
        return updated

    @staticmethod
    def _late_arc_signals_protagonist_absence(
        ctx: StoryWorkflowContext,
        protagonist: str,
    ) -> bool:
        outline = ctx.workflow.outline
        late_arc_numbers = {
            number
            for number in (ctx.story.chapter_count - 1, ctx.story.chapter_count)
            if number >= 1
        }
        late_arc_text = []
        outline_by_number = (
            {chapter.chapter_number: chapter for chapter in outline.chapters}
            if outline is not None
            else {}
        )
        for chapter in ctx.story.chapters:
            if chapter.chapter_number not in late_arc_numbers:
                continue
            outline_chapter = outline_by_number.get(chapter.chapter_number)
            late_arc_text.extend(
                [
                    chapter.summary or "",
                    chapter.current_scene.content if chapter.current_scene is not None else "",
                    outline_chapter.summary if outline_chapter is not None else "",
                ]
            )

        combined_text = " ".join(late_arc_text).lower()
        return any(
            token in combined_text
            for token in (
                "blank slate",
                "blank-slate",
                "erased",
                "erasure",
                "silent witness",
                "hollow husk",
                "living archive",
                "mindless vessel",
                "biological shell",
                "no higher consciousness",
            )
        )

    def _clarify_finale_state(
        self,
        ctx: StoryWorkflowContext,
        outline: StoryOutlineArtifact,
        *,
        issue_context: str = "",
    ) -> bool:
        late_arc_sequence = self._late_arc_sequence(ctx, issue_context=issue_context)
        outline_by_number = {chapter.chapter_number: chapter for chapter in outline.chapters}
        changed = False
        for chapter in ctx.story.chapters:
            stage = next(
                (
                    details
                    for details in late_arc_sequence.values()
                    if int(details["number"]) == chapter.chapter_number
                ),
                None,
            )
            if stage is None:
                continue
            rewritten = str(stage["summary"])
            if chapter.summary != rewritten:
                chapter.summary = rewritten
                changed = True
            objective = str(stage["objective"])
            if chapter.metadata.get("chapter_objective") != objective:
                chapter.metadata["chapter_objective"] = objective
                changed = True
            outline_chapter = outline_by_number.get(chapter.chapter_number)
            if outline_chapter is not None and outline_chapter.summary != rewritten:
                outline_chapter.summary = rewritten
                changed = True
            if outline_chapter is not None and outline_chapter.chapter_objective != objective:
                outline_chapter.chapter_objective = objective
                changed = True
            if chapter.current_scene is not None and chapter.chapter_number == ctx.story.chapter_count:
                clarified_scene = self._append_unique_sentence(
                    chapter.current_scene.content,
                    f"The survivors repeat the last line {protagonist_name(ctx.workflow.blueprint.character_bible) if ctx.workflow.blueprint is not None else 'the protagonist'} spoke before the rite while the body remains beside {self._resolve_anchor_label(ctx)} as the cost everyone can see; "
                    "they explicitly name the lost sister as free, not here, and not coming back, then wait for one learned knock against the oath seal before the public rail answers.",
                )
                if clarified_scene != chapter.current_scene.content:
                    chapter.current_scene.update_content(clarified_scene)
                    changed = True

        return changed

    def _detect_departed_characters(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
    ) -> dict[str, int]:
        blueprint = ctx.workflow.blueprint
        if blueprint is None:
            return {}

        candidates = [
            name
            for name in character_names(blueprint.character_bible)
            if name and name != protagonist
        ]
        if not candidates:
            return {}

        outline = ctx.workflow.outline
        outline_by_number = (
            {chapter.chapter_number: chapter for chapter in outline.chapters}
            if outline is not None
            else {}
        )
        departure_templates = (
            r"\b{alias}\b\s+dies\b",
            r"\b{alias}\b\s+died\b",
            r"\b{alias}\b\s+is\s+dead\b",
            r"\b{alias}\b\s+was\s+killed\b",
            r"\b{alias}\b\s+is\s+killed\b",
            r"\b{alias}\b\s+is\s+defeated\b",
            r"\b{alias}\b\s+is\s+stripped\s+of\s+power\b",
            r"\b{alias}\b\s+is\s+removed\s+from\s+power\b",
            r"\b{alias}\b\s+is\s+deposed\b",
            r"\b{alias}\b\s+is\s+imprisoned\b",
            r"\b{alias}\b\s+is\s+bound\s+in\s+chains\b",
            r"\b{alias}\b\s+sacrifices\b",
            r"\b{alias}\b\s+is\s+sacrificed\b",
            r"\b{alias}\b\s+falls\b",
            r"\b{alias}\b\s+vanishes\b",
            r"\b{alias}\b\s+vanished\b",
            r"\b{alias}\b\s+gives\s+(?:his|her|their)\s+life\b",
            r"\b{alias}\b\s+gave\s+(?:his|her|their)\s+life\b",
            r"\b{alias}\b\s+is\s+slain\b",
            r"\b{alias}\b\s+was\s+slain\b",
            r"\b{alias}\b\s+is\s+mortally\s+wounded\b",
            r"\b{alias}\b\s+was\s+mortally\s+wounded\b",
            r"\b{alias}\b\s+will\s+not\s+return\b",
            r"\b{alias}\b\s+never\s+returns?\b",
            r"\b{alias}'s\s+death\b",
            r"\b{alias}'s\s+self[- ]erasure\b",
            r"\bafter\s+{alias}'s\s+death\b",
        )
        departed: dict[str, int] = {}

        for chapter in ctx.story.chapters:
            outline_chapter = outline_by_number.get(chapter.chapter_number)
            fragments = [
                chapter.summary or "",
                *(scene.content for scene in chapter.scenes),
                outline_chapter.summary if outline_chapter is not None else "",
                outline_chapter.chapter_objective if outline_chapter is not None else "",
            ]
            sentences = re.split(r"(?<=[.!?])\s+", " ".join(fragment.strip() for fragment in fragments))
            for name in candidates:
                if name in departed:
                    continue
                aliases = [alias.lower() for alias in self._character_detection_aliases(name)]
                for sentence in sentences:
                    lowered_sentence = sentence.lower()
                    if not any(alias in lowered_sentence for alias in aliases):
                        continue
                    if any(
                        re.search(
                            template.format(alias=re.escape(alias)),
                            lowered_sentence,
                            flags=re.IGNORECASE,
                        )
                        for alias in aliases
                        for template in departure_templates
                    ):
                        departed[name] = chapter.chapter_number
                        break
        return departed

    def _combined_departed_characters(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
        *,
        issue_context: str = "",
    ) -> dict[str, int]:
        blueprint = ctx.workflow.blueprint
        cast_names = (
            set(character_names(blueprint.character_bible))
            if blueprint is not None
            else set()
        )
        candidate_names = set(cast_names)
        candidate_names.update(
            " ".join(str(candidate).split()).strip()
            for candidate in ctx.memory.active_characters
            if str(candidate).strip()
        )
        for chapter in ctx.story.chapters:
            for field in ("focus_character", "relationship_target"):
                value = " ".join(str(chapter.metadata.get(field, "")).split()).strip()
                if value:
                    candidate_names.add(value)
        departed = self._detect_departed_characters(ctx, protagonist)
        if not issue_context or not candidate_names:
            return departed

        for candidate, chapter_number in self._issue_departure_hints(
            issue_context,
            candidate_names,
        ).items():
            existing = departed.get(candidate)
            if existing is None or chapter_number < existing:
                departed[candidate] = chapter_number
        fallback_departure_chapter = self._terminal_phase_numbers(
            ctx.story.chapter_count
        )["sacrifice"]
        for candidate, chapter_number in self._soft_issue_departure_hints(
            issue_context,
            candidate_names,
            fallback_chapter=fallback_departure_chapter,
        ).items():
            existing = departed.get(candidate)
            if existing is None or chapter_number < existing:
                departed[candidate] = chapter_number
        return departed

    def _issue_departure_hints(
        self,
        issue_context: str,
        cast_names: set[str],
    ) -> dict[str, int]:
        normalized_context = " ".join(str(issue_context).lower().split())
        if not normalized_context or not cast_names:
            return {}

        hints: dict[str, int] = {}
        chapter_pattern_templates = (
            r"{alias}\s+died\s+in\s+ch(?:apter)?\s+(\d+)",
            r"{alias}\s+dies\s+in\s+ch(?:apter)?\s+(\d+)",
            r"{alias}'s\s+death\s+in\s+ch(?:apter)?\s+(\d+)",
            r"after\s+{alias}'s\s+death\s+in\s+ch(?:apter)?\s+(\d+)",
            r"{alias}\s+is\s+listed\s+as\s+having\s+active\s+relationship\s+status[^.]*?ch(?:apter)?\s+(\d+)[^.]*?(?:death(?:/sacrifice)?|dies|died|sacrific(?:e|ed|es))",
            r"{alias}[^.]*?appears[^.]*?late-arc relationship ledger[^.]*?ch(?:apter)?\s+(\d+)[^.]*?(?:death(?:/sacrifice)?|dies|died|sacrific(?:e|ed|es))",
            r"{alias}[^.]*?despite\s+dying\s+in\s+ch(?:apter)?\s+(\d+)",
            r"{alias}[^.]*?after\s+dying\s+in\s+ch(?:apter)?\s+(\d+)",
        )
        for canonical_name in cast_names:
            aliases = {
                alias.lower()
                for alias in (
                    self._character_detection_aliases(canonical_name)
                    + self._character_reference_aliases(canonical_name)
                )
                if alias
            }
            hinted_chapters: list[int] = []
            for alias in aliases:
                escaped_alias = re.escape(alias)
                for template in chapter_pattern_templates:
                    for match in re.finditer(
                        template.format(alias=escaped_alias),
                        normalized_context,
                        flags=re.IGNORECASE,
                    ):
                        hinted_chapters.append(int(match.group(1)))
                if hinted_chapters:
                    hints[canonical_name] = min(hinted_chapters)
        return hints

    def _soft_issue_departure_hints(
        self,
        issue_context: str,
        cast_names: set[str],
        *,
        fallback_chapter: int,
    ) -> dict[str, int]:
        normalized_context = " ".join(str(issue_context).lower().split())
        if not normalized_context or not cast_names:
            return {}

        departure_markers = (
            "deceased",
            "dead",
            "will not return",
            "not coming back",
            "sacrificed",
            "legacy influence",
            "spirit guide",
            "memory guide",
        )
        hints: dict[str, int] = {}
        for canonical_name in cast_names:
            aliases = {
                alias.lower()
                for alias in (
                    self._character_detection_aliases(canonical_name)
                    + self._character_reference_aliases(canonical_name)
                )
                if alias
            }
            if not aliases:
                continue
            if not any(alias in normalized_context for alias in aliases):
                continue
            if any(
                re.search(
                    rf"\b{re.escape(alias)}\b[^.{{0,80}}]*(?:{'|'.join(re.escape(marker) for marker in departure_markers)})",
                    normalized_context,
                    flags=re.IGNORECASE,
                )
                or re.search(
                    rf"(?:{'|'.join(re.escape(marker) for marker in departure_markers)})[^.{{0,80}}]*\b{re.escape(alias)}\b",
                    normalized_context,
                    flags=re.IGNORECASE,
                )
                or re.search(
                    rf"\b{re.escape(alias)}\b.{{0,80}}\bdeath\b",
                    normalized_context,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                or re.search(
                    rf"\bdeath\b.{{0,80}}\b{re.escape(alias)}\b",
                    normalized_context,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                for alias in aliases
            ):
                hints[canonical_name] = fallback_chapter
        return hints

    def _surviving_allies_for_chapter(
        self,
        allies: list[str],
        departed_characters: dict[str, int],
        chapter_number: int,
    ) -> list[str]:
        return [
            ally
            for ally in allies
            if ally
            and (
                (
                    self._departure_chapter_for_name(ally, departed_characters)
                    or chapter_number + 1
                )
                > chapter_number
            )
        ]

    def _repair_departed_character_references(
        self,
        chapter: Chapter,
        outline_chapter: StoryOutlineChapter | None,
        *,
        departed_characters: dict[str, int],
        chapter_number: int,
    ) -> bool:
        changed = False
        for name, departed_at in departed_characters.items():
            if departed_at >= chapter_number:
                continue

            cleaned_summary = chapter.summary or ""
            for alias in self._character_reference_aliases(name):
                cleaned_summary = self._legacyize_character_reference(cleaned_summary, alias)
            if cleaned_summary != (chapter.summary or "").strip():
                chapter.summary = cleaned_summary
                changed = True

            for scene in chapter.scenes:
                cleaned_content = scene.content
                for alias in self._character_reference_aliases(name):
                    cleaned_content = self._legacyize_character_reference(cleaned_content, alias)
                if cleaned_content != scene.content:
                    scene.update_content(cleaned_content)
                    changed = True

            if outline_chapter is None:
                continue

            cleaned_outline_summary = outline_chapter.summary
            for alias in self._character_reference_aliases(name):
                cleaned_outline_summary = self._legacyize_character_reference(
                    cleaned_outline_summary,
                    alias,
                )
            if cleaned_outline_summary != outline_chapter.summary.strip():
                outline_chapter.summary = cleaned_outline_summary
                changed = True

            cleaned_objective = outline_chapter.chapter_objective
            for alias in self._character_reference_aliases(name):
                cleaned_objective = self._legacyize_character_reference(
                    cleaned_objective,
                    alias,
                )
            if cleaned_objective != outline_chapter.chapter_objective.strip():
                outline_chapter.chapter_objective = cleaned_objective
                changed = True
        return changed

    def _resolve_cast_labels(
        self,
        ctx: StoryWorkflowContext,
    ) -> tuple[str, list[str]]:
        blueprint = ctx.workflow.blueprint
        protagonist = (
            protagonist_name(blueprint.character_bible) if blueprint is not None else ""
        ).strip()
        if not protagonist:
            protagonist = next(
                (
                    str(chapter.metadata.get("focus_character", "")).strip()
                    for chapter in ctx.story.chapters
                    if str(chapter.metadata.get("focus_character", "")).strip()
                ),
                "",
            )
        if not protagonist and ctx.memory.active_characters:
            protagonist = ctx.memory.active_characters[0]
        protagonist = protagonist or "the protagonist"

        if blueprint is not None:
            blocked = set(antagonist_names(blueprint.character_bible))
            allies = [
                name
                for name in pov_character_names(blueprint.character_bible)
                if name and name != protagonist and name not in blocked
            ]
        else:
            allies = []

        if not allies:
            allies = [
                name
                for name in ctx.memory.active_characters
                if name and name != protagonist
            ]

        return protagonist, allies

    def _resolve_surviving_allies(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
        allies: list[str],
        *,
        issue_context: str = "",
    ) -> list[str]:
        departed_characters = self._combined_departed_characters(
            ctx,
            protagonist,
            issue_context=issue_context,
        )
        blueprint = ctx.workflow.blueprint
        cast_names = (
            set(character_names(blueprint.character_bible))
            if blueprint is not None
            else set()
        )
        excluded_markers = self._late_arc_excluded_markers(
            ctx,
            protagonist,
            cast_names,
        )
        surviving_allies = self._surviving_allies_for_chapter(
            allies,
            departed_characters,
            ctx.story.chapter_count,
        )
        surviving_allies = [
            name
            for name in surviving_allies
            if name
            and not self._is_late_arc_excluded_candidate(
                name,
                cast_names=cast_names,
                excluded_markers=excluded_markers,
            )
            and not self._is_generic_terminal_role_title(name)
        ]
        if surviving_allies:
            return surviving_allies

        memory_candidates = [
            name
            for name in ctx.memory.active_characters
            if name
            and self._departure_chapter_for_name(name, departed_characters) is None
            and not self._is_late_arc_excluded_candidate(
                name,
                cast_names=cast_names,
                excluded_markers=excluded_markers,
            )
            and not self._is_generic_terminal_role_title(name)
        ]
        if memory_candidates:
            return memory_candidates

        metadata_candidates: list[str] = []
        for chapter in ctx.story.chapters:
            for field in ("focus_character", "relationship_target"):
                candidate = self._canonicalize_character_name(
                    self._normalize_protagonist_name_drift(
                        str(chapter.metadata.get(field, "")).strip(),
                        protagonist,
                        cast_names,
                    ),
                    cast_names,
                )
                if (
                    not candidate
                    or candidate in metadata_candidates
                    or self._departure_chapter_for_name(candidate, departed_characters)
                    is not None
                    or self._is_late_arc_excluded_candidate(
                        candidate,
                        cast_names=cast_names,
                        excluded_markers=excluded_markers,
                    )
                    or self._is_generic_terminal_role_title(candidate)
                ):
                    continue
                metadata_candidates.append(candidate)
        if metadata_candidates:
            return metadata_candidates

        return [protagonist]

    def _late_arc_excluded_markers(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
        cast_names: set[str],
    ) -> set[str]:
        blueprint = ctx.workflow.blueprint
        protagonist_name_marker = " ".join(str(protagonist).split()).strip().lower()
        protagonist_surname = (
            protagonist_name_marker.split()[-1] if protagonist_name_marker else ""
        )
        excluded_names: set[str] = {
            " ".join(str(protagonist).split()).strip(),
            self._resolve_primary_antagonist_label(ctx, protagonist),
        }
        if blueprint is not None:
            excluded_names.update(
                " ".join(str(name).split()).strip()
                for name in antagonist_names(blueprint.character_bible)
                if str(name).strip()
            )
            for candidate_name in character_names(blueprint.character_bible):
                if not str(candidate_name).strip():
                    continue
                profile = character_profile(blueprint.character_bible, candidate_name)
                profile_text = " ".join(
                    str(profile.get(key, "")).strip()
                    for key in (
                        "role",
                        "motivation",
                        "goal",
                        "arc",
                        "summary",
                        "notes",
                        "relationship_to_protagonist",
                    )
                    if str(profile.get(key, "")).strip()
                ).lower()
                if self._is_antagonistic_profile_text(profile_text):
                    excluded_names.add(" ".join(str(candidate_name).split()).strip())

        markers: set[str] = set()
        for name in excluded_names:
            normalized = self._canonicalize_character_name(
                " ".join(str(name).split()).strip(),
                cast_names,
            )
            if not normalized:
                continue

            normalized_lower = normalized.lower()
            markers.add(normalized_lower)
            markers.update(
                alias.lower()
                for alias in (
                    self._character_detection_aliases(normalized)
                    + self._character_reference_aliases(normalized)
                )
                if alias
            )
            if normalized_lower == protagonist_name_marker:
                continue

            surname = normalized.split()[-1].lower()
            if surname and surname != protagonist_surname:
                markers.add(surname)
                markers.update(
                    alias.lower()
                    for alias in self._character_title_aliases(normalized.split()[-1])
                    if alias
                )
        return markers

    def _is_late_arc_excluded_candidate(
        self,
        candidate_name: str,
        *,
        cast_names: set[str],
        excluded_markers: set[str],
    ) -> bool:
        raw_candidate = " ".join(str(candidate_name).split()).strip()
        if not raw_candidate:
            return True

        candidate_markers = {raw_candidate.lower()}
        normalized_candidate = self._canonicalize_character_name(
            raw_candidate,
            cast_names,
        )
        if normalized_candidate:
            candidate_markers.add(normalized_candidate.lower())
        for base_name in {raw_candidate, normalized_candidate}:
            if not base_name:
                continue
            candidate_markers.update(
                alias.lower()
                for alias in (
                    self._character_detection_aliases(base_name)
                    + self._character_reference_aliases(base_name)
                )
                if alias
            )
            surname = base_name.split()[-1].lower()
            if surname:
                candidate_markers.add(surname)
                candidate_markers.update(
                    alias.lower()
                    for alias in self._character_title_aliases(base_name.split()[-1])
                    if alias
                )

        return bool(candidate_markers & excluded_markers)

    def _is_restrained_late_arc_candidate(
        self,
        ctx: StoryWorkflowContext,
        candidate_name: str,
        *,
        cast_names: set[str],
    ) -> bool:
        raw_candidate = " ".join(str(candidate_name).split()).strip()
        if not raw_candidate:
            return False

        candidate_markers = {raw_candidate.lower()}
        normalized_candidate = self._canonicalize_character_name(
            raw_candidate,
            cast_names,
        )
        if normalized_candidate:
            candidate_markers.add(normalized_candidate.lower())
        for base_name in {raw_candidate, normalized_candidate}:
            if not base_name:
                continue
            candidate_markers.update(
                alias.lower()
                for alias in (
                    self._character_detection_aliases(base_name)
                    + self._character_reference_aliases(base_name)
                )
                if alias
            )

        restraint_markers = (
            "captured",
            "capture",
            "under guard",
            "held under guard",
            "kept under guard",
            "guarded beneath",
            "in custody",
            "custody",
            "imprisoned",
            "locked in the ward",
            "ward cell",
            "locked in a cell",
            "cell beneath",
            "bound in chains",
            "shackled",
            "chained",
            "confined",
            "caged",
            "under ward",
        )
        release_markers = (
            "released",
            "release",
            "escaped",
            "escape",
            "broke free",
            "breaks free",
            "slipped free",
            "slips free",
            "cut loose",
            "freed",
            "let out",
            "dragged out",
            "brought out",
            "turned loose",
            "amnestied",
        )

        last_restraint_chapter = 0
        last_release_chapter = 0

        def scan_text(text: str, chapter_number: int) -> None:
            nonlocal last_release_chapter, last_restraint_chapter
            normalized_text = " ".join(str(text).split()).lower()
            if not normalized_text:
                return
            for sentence in re.split(r"(?<=[.!?])\s+", normalized_text):
                if not sentence or not any(marker in sentence for marker in candidate_markers):
                    continue
                if any(marker in sentence for marker in restraint_markers):
                    last_restraint_chapter = max(last_restraint_chapter, chapter_number)
                if any(marker in sentence for marker in release_markers):
                    last_release_chapter = max(last_release_chapter, chapter_number)

        for chapter in ctx.story.chapters:
            scan_text(chapter.summary or "", chapter.chapter_number)
            scan_text(str(chapter.metadata.get("chapter_objective", "")), chapter.chapter_number)
            scan_text(str(chapter.metadata.get("relationship_status", "")), chapter.chapter_number)
            if chapter.current_scene is not None:
                scan_text(chapter.current_scene.content, chapter.chapter_number)

        outline = ctx.workflow.outline
        if outline is not None:
            for outline_chapter in outline.chapters:
                chapter_number = outline_chapter.chapter_number
                for text in (
                    outline_chapter.summary,
                    outline_chapter.chapter_objective,
                    outline_chapter.hook,
                    outline_chapter.promise,
                    outline_chapter.promised_payoff,
                ):
                    scan_text(text or "", chapter_number)

        return last_restraint_chapter > 0 and last_release_chapter < last_restraint_chapter

    def _resolve_restrained_late_arc_candidate(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
        cast_names: set[str],
    ) -> str:
        blueprint = ctx.workflow.blueprint
        candidates: list[str] = []
        if blueprint is not None:
            candidates.extend(character_names(blueprint.character_bible))
        candidates.extend(str(candidate).strip() for candidate in ctx.memory.active_characters)

        seen: set[str] = set()
        for candidate in candidates:
            normalized = self._canonicalize_character_name(
                " ".join(str(candidate).split()).strip(),
                cast_names,
            )
            if not normalized or normalized == protagonist or normalized in seen:
                continue
            seen.add(normalized)
            if self._is_restrained_late_arc_candidate(
                ctx,
                normalized,
                cast_names=cast_names,
            ):
                return normalized
        return ""

    def _late_arc_metadata_candidates(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
        departed_characters: dict[str, int],
    ) -> list[str]:
        blueprint = ctx.workflow.blueprint
        cast_names = (
            set(character_names(blueprint.character_bible))
            if blueprint is not None
            else set()
        )
        excluded_markers = self._late_arc_excluded_markers(
            ctx,
            protagonist,
            cast_names,
        )
        late_arc_numbers = set(self._late_arc_chapter_numbers(ctx.story.chapter_count).values())
        scores: dict[str, int] = {}

        def score(candidate: str, weight: int) -> None:
            raw_candidate = " ".join(str(candidate).split()).strip()
            if self._is_symbolic_late_arc_candidate(raw_candidate):
                return
            normalized = self._canonicalize_character_name(
                self._normalize_protagonist_name_drift(
                    raw_candidate,
                    protagonist,
                    cast_names,
                ),
                cast_names,
            )
            if (
                not normalized
                or self._is_generic_terminal_placeholder(normalized)
                or self._is_generic_terminal_role_title(normalized)
                or self._is_symbolic_late_arc_candidate(normalized)
                or self._departure_chapter_for_name(normalized, departed_characters)
                is not None
                or self._is_restrained_late_arc_candidate(
                    ctx,
                    normalized,
                    cast_names=cast_names,
                )
                or self._is_late_arc_excluded_candidate(
                    normalized,
                    cast_names=cast_names,
                    excluded_markers=excluded_markers,
                )
            ):
                return
            scores[normalized] = scores.get(normalized, 0) + weight

        for summary in ctx.memory.chapter_summaries:
            if summary.chapter_number not in late_arc_numbers:
                continue
            score(summary.focus_character, 8)

        for chapter in ctx.story.chapters:
            if chapter.chapter_number not in late_arc_numbers:
                continue
            score(str(chapter.metadata.get("focus_character", "")), 30)
            score(str(chapter.metadata.get("relationship_target", "")), 14)
        for relationship_state in ctx.memory.relationship_states:
            if relationship_state.chapter_number not in late_arc_numbers:
                continue
            score(relationship_state.source, 24)
            score(relationship_state.target, 12)

        outline = ctx.workflow.outline
        if outline is not None:
            outline_by_number = {
                chapter.chapter_number: chapter
                for chapter in outline.chapters
                if chapter.chapter_number in late_arc_numbers
            }
            for canonical_name in cast_names:
                aliases = {
                    alias.lower()
                    for alias in (
                        self._character_detection_aliases(canonical_name)
                        + self._character_reference_aliases(canonical_name)
                    )
                    if alias
                }
                if not aliases:
                    continue
                for outline_chapter in outline_by_number.values():
                    combined_outline_text = " ".join(
                        part
                        for part in (
                            outline_chapter.summary,
                            outline_chapter.chapter_objective,
                            outline_chapter.hook,
                            outline_chapter.promise,
                            outline_chapter.promised_payoff,
                        )
                        if part
                    ).lower()
                    if any(alias in combined_outline_text for alias in aliases):
                        score(canonical_name, 10)

        if blueprint is not None:
            for entry in blueprint.character_bible.get("key_supporting", []):
                if isinstance(entry, dict):
                    score(str(entry.get("name", "")).strip(), 6)

        return [
            name
            for name, _ in sorted(
                scores.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

    def _resolve_primary_antagonist_label(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
    ) -> str:
        blueprint = ctx.workflow.blueprint
        if blueprint is None:
            return "the defeated usurper"

        for candidate in antagonist_names(blueprint.character_bible):
            normalized = " ".join(str(candidate).split()).strip()
            if normalized and normalized != protagonist:
                return normalized
        return "the defeated usurper"

    def _resolve_late_arc_supporting_witness(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
        primary_keeper: str,
        *,
        issue_context: str = "",
    ) -> str:
        departed_characters = self._combined_departed_characters(
            ctx,
            protagonist,
            issue_context=issue_context,
        )
        _protagonist, allies = self._resolve_cast_labels(ctx)
        blueprint = ctx.workflow.blueprint
        cast_names = (
            set(character_names(blueprint.character_bible))
            if blueprint is not None
            else set()
        )
        missing_sibling = self._canonicalize_character_name(
            self._resolve_sibling_reference(ctx, protagonist),
            cast_names,
        )
        excluded_markers = self._late_arc_excluded_markers(
            ctx,
            protagonist,
            cast_names,
        )
        continuity_anchor = self._resolve_terminal_arc_continuity_anchor(
            ctx,
            protagonist,
            allies,
            issue_context=issue_context,
        )
        grief_scores: dict[str, int] = {}
        tactical_candidates: set[str] = set()

        def score_grief(candidate: str, weight: int) -> None:
            raw_candidate = " ".join(str(candidate).split()).strip()
            if self._is_symbolic_late_arc_candidate(raw_candidate):
                return
            normalized = self._canonicalize_character_name(
                raw_candidate,
                cast_names,
            )
            if (
                normalized
                and normalized != protagonist
                and normalized != primary_keeper
                and normalized != missing_sibling
                and not self._is_symbolic_late_arc_candidate(normalized)
                and not self._is_generic_terminal_role_title(normalized)
                and self._departure_chapter_for_name(normalized, departed_characters) is None
                and not self._is_restrained_late_arc_candidate(
                    ctx,
                    normalized,
                    cast_names=cast_names,
                )
                and not self._is_late_arc_excluded_candidate(
                    normalized,
                    cast_names=cast_names,
                    excluded_markers=excluded_markers,
                )
            ):
                grief_scores[normalized] = grief_scores.get(normalized, 0) + weight

        if continuity_anchor:
            score_grief(continuity_anchor, 48)

        for relationship_state in ctx.memory.relationship_states:
            status = str(relationship_state.status).lower()
            if any(
                token in status
                for token in ("shared grief", "mourning", "witness line", "confession line", "memorial")
            ):
                score_grief(relationship_state.source, 22)
                score_grief(relationship_state.target, 22)
            if any(token in status for token in ("tactical", "reliance", "holding line", "shield")):
                for candidate in (relationship_state.source, relationship_state.target):
                    normalized = self._canonicalize_character_name(
                        " ".join(str(candidate).split()).strip(),
                        cast_names,
                    )
                    if normalized:
                        tactical_candidates.add(normalized)

        for chapter in ctx.story.chapters:
            status = str(chapter.metadata.get("relationship_status", "")).lower()
            if any(
                token in status
                for token in ("shared grief", "mourning", "witness line", "confession line", "memorial")
            ):
                score_grief(str(chapter.metadata.get("focus_character", "")), 16)
                score_grief(str(chapter.metadata.get("relationship_target", "")), 16)
            if any(token in status for token in ("tactical", "reliance", "holding line", "shield")):
                for candidate in (
                    str(chapter.metadata.get("focus_character", "")),
                    str(chapter.metadata.get("relationship_target", "")),
                ):
                    normalized = self._canonicalize_character_name(
                        " ".join(str(candidate).split()).strip(),
                        cast_names,
                    )
                    if normalized:
                        tactical_candidates.add(normalized)

        if grief_scores:
            for candidate, _weight in sorted(
                grief_scores.items(),
                key=lambda item: (-item[1], item[0]),
            ):
                if (
                    candidate
                    and candidate != protagonist
                    and candidate != primary_keeper
                    and candidate != missing_sibling
                    and not self._is_symbolic_late_arc_candidate(candidate)
                    and not self._is_generic_terminal_role_title(candidate)
                    and self._departure_chapter_for_name(candidate, departed_characters) is None
                    and not self._is_restrained_late_arc_candidate(
                        ctx,
                        candidate,
                        cast_names=cast_names,
                    )
                    and not self._is_late_arc_excluded_candidate(
                        candidate,
                        cast_names=cast_names,
                        excluded_markers=excluded_markers,
                    )
                ):
                    return candidate

        ranked_candidates = self._late_arc_metadata_candidates(
            ctx,
            protagonist,
            departed_characters,
        )

        for candidate in ranked_candidates:
            if (
                candidate
                and candidate != protagonist
                and candidate != primary_keeper
                and candidate != missing_sibling
                and candidate not in tactical_candidates
                and not self._is_symbolic_late_arc_candidate(candidate)
                and not self._is_generic_terminal_role_title(candidate)
                and self._departure_chapter_for_name(candidate, departed_characters) is None
                and not self._is_restrained_late_arc_candidate(
                    ctx,
                    candidate,
                    cast_names=cast_names,
                )
                and not self._is_late_arc_excluded_candidate(
                    candidate,
                    cast_names=cast_names,
                    excluded_markers=excluded_markers,
                )
            ):
                return candidate

        for candidate in self._resolve_surviving_allies(
            ctx,
            protagonist,
            allies,
            issue_context=issue_context,
        ):
            if (
                candidate
                and candidate != protagonist
                and candidate != primary_keeper
                and candidate != missing_sibling
                and not self._is_symbolic_late_arc_candidate(candidate)
                and not self._is_generic_terminal_role_title(candidate)
                and self._departure_chapter_for_name(candidate, departed_characters) is None
                and not self._is_restrained_late_arc_candidate(
                    ctx,
                    candidate,
                    cast_names=cast_names,
                )
                and not self._is_late_arc_excluded_candidate(
                    candidate,
                    cast_names=cast_names,
                    excluded_markers=excluded_markers,
                )
            ):
                return candidate

        if blueprint is not None:
            for entry in blueprint.character_bible.get("key_supporting", []):
                if not isinstance(entry, dict):
                    continue
                candidate = " ".join(str(entry.get("name", "")).split()).strip()
                if (
                    candidate
                    and candidate != protagonist
                    and candidate != primary_keeper
                    and candidate != missing_sibling
                    and not self._is_symbolic_late_arc_candidate(candidate)
                    and not self._is_generic_terminal_role_title(candidate)
                    and self._departure_chapter_for_name(candidate, departed_characters) is None
                    and not self._is_restrained_late_arc_candidate(
                        ctx,
                        candidate,
                        cast_names=cast_names,
                    )
                    and not self._is_late_arc_excluded_candidate(
                        candidate,
                        cast_names=cast_names,
                        excluded_markers=excluded_markers,
                    )
                ):
                    return candidate
        return next(
            (
                candidate
                for candidate in (primary_keeper, continuity_anchor, protagonist)
                if candidate
                and not self._is_generic_terminal_placeholder(candidate)
                and not self._is_generic_terminal_role_title(candidate)
            ),
            "",
        )

    def _resolve_late_arc_public_witness(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
        primary_keeper: str,
        supporting_witness: str,
        *,
        issue_context: str = "",
    ) -> str:
        departed_characters = self._combined_departed_characters(
            ctx,
            protagonist,
            issue_context=issue_context,
        )
        blueprint = ctx.workflow.blueprint
        cast_names = (
            set(character_names(blueprint.character_bible))
            if blueprint is not None
            else set()
        )
        missing_sibling = self._canonicalize_character_name(
            self._resolve_sibling_reference(ctx, protagonist),
            cast_names,
        )
        excluded_markers = self._late_arc_excluded_markers(
            ctx,
            protagonist,
            cast_names,
        )
        _protagonist, allies = self._resolve_cast_labels(ctx)
        continuity_anchor = self._resolve_terminal_arc_continuity_anchor(
            ctx,
            protagonist,
            allies,
            issue_context=issue_context,
        )
        scores: dict[str, int] = {}

        def is_eligible(candidate: str) -> bool:
            return bool(
                candidate
                and candidate not in {protagonist, missing_sibling}
                and not self._is_symbolic_late_arc_candidate(candidate)
                and not self._is_generic_terminal_role_title(candidate)
                and self._departure_chapter_for_name(candidate, departed_characters) is None
                and not self._is_restrained_late_arc_candidate(
                    ctx,
                    candidate,
                    cast_names=cast_names,
                )
                and not self._is_late_arc_excluded_candidate(
                    candidate,
                    cast_names=cast_names,
                    excluded_markers=excluded_markers,
                )
            )

        def score(candidate: str, weight: int) -> None:
            raw_candidate = " ".join(str(candidate).split()).strip()
            if self._is_symbolic_late_arc_candidate(raw_candidate):
                return
            normalized = self._canonicalize_character_name(
                raw_candidate,
                cast_names,
            )
            if is_eligible(normalized):
                scores[normalized] = scores.get(normalized, 0) + weight

        score(continuity_anchor, 52)

        tactical_window = {
            max(1, ctx.story.chapter_count - 6),
            max(1, ctx.story.chapter_count - 5),
            max(1, ctx.story.chapter_count - 4),
        }
        for relationship_state in ctx.memory.relationship_states:
            if relationship_state.chapter_number not in tactical_window:
                continue
            status = str(relationship_state.status).lower()
            if any(
                token in status
                for token in ("tactical", "reliance", "shared grief", "mutual", "holding line")
            ):
                source = self._canonicalize_character_name(
                    " ".join(str(relationship_state.source).split()).strip(),
                    cast_names,
                )
                target = self._canonicalize_character_name(
                    " ".join(str(relationship_state.target).split()).strip(),
                    cast_names,
                )
                if source == primary_keeper:
                    score(target, 40)
                elif target == primary_keeper:
                    score(source, 40)
                score(source, 18)
                score(target, 18)
        for chapter in ctx.story.chapters:
            if chapter.chapter_number not in tactical_window:
                continue
            status = str(chapter.metadata.get("relationship_status", "")).lower()
            if any(
                token in status
                for token in ("tactical", "reliance", "shared grief", "mutual", "holding line")
            ):
                focus_character = self._canonicalize_character_name(
                    " ".join(str(chapter.metadata.get("focus_character", "")).split()).strip(),
                    cast_names,
                )
                relationship_target = self._canonicalize_character_name(
                    " ".join(str(chapter.metadata.get("relationship_target", "")).split()).strip(),
                    cast_names,
                )
                if focus_character == primary_keeper:
                    score(relationship_target, 34)
                elif relationship_target == primary_keeper:
                    score(focus_character, 34)
                score(focus_character, 16)
                score(relationship_target, 16)

        if blueprint is not None:
            for candidate_name in character_names(blueprint.character_bible):
                profile = character_profile(blueprint.character_bible, candidate_name)
                profile_text = " ".join(
                    str(profile.get(key, "")).strip()
                    for key in ("role", "summary", "notes", "relationship_to_protagonist")
                    if str(profile.get(key, "")).strip()
                ).lower()
                if any(
                    token in profile_text
                    for token in ("guard", "warden", "captain", "watch", "scribe", "tactical")
                ):
                    score(candidate_name, 6)

        if scores:
            for candidate, _weight in sorted(scores.items(), key=lambda item: (-item[1], item[0])):
                if is_eligible(candidate):
                    return candidate

        for candidate in self._late_arc_metadata_candidates(
            ctx,
            protagonist,
            departed_characters,
        ):
            if is_eligible(candidate):
                return candidate

        for candidate in self._resolve_surviving_allies(
            ctx,
            protagonist,
            allies,
            issue_context=issue_context,
        ):
            if is_eligible(candidate):
                return candidate

        if blueprint is not None:
            for entry in blueprint.character_bible.get("key_supporting", []):
                if not isinstance(entry, dict):
                    continue
                candidate = " ".join(str(entry.get("name", "")).split()).strip()
                if self._is_symbolic_late_arc_candidate(candidate):
                    continue
                if is_eligible(candidate):
                    return candidate

        for candidate in ctx.memory.active_characters:
            raw_candidate = " ".join(str(candidate).split()).strip()
            if self._is_symbolic_late_arc_candidate(raw_candidate):
                continue
            normalized = self._canonicalize_character_name(
                raw_candidate,
                cast_names,
            )
            if is_eligible(normalized):
                return normalized

        for candidate in (primary_keeper, supporting_witness, continuity_anchor, protagonist):
            if (
                candidate
                and candidate != supporting_witness
                and not self._is_generic_terminal_placeholder(candidate)
                and not self._is_generic_terminal_role_title(candidate)
            ):
                return candidate
        return ""

    def _resolve_terminal_relationship_target(
        self,
        focus_character: str,
        *candidates: str,
    ) -> str:
        normalized_focus = " ".join(str(focus_character).split()).strip()
        for candidate in candidates:
            normalized = " ".join(str(candidate).split()).strip()
            if (
                normalized
                and normalized != normalized_focus
                and not self._is_generic_terminal_placeholder(normalized)
                and not self._is_generic_terminal_role_title(normalized)
            ):
                return normalized
        return ""

    def _resolve_late_arc_heroic_witness(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
        primary_keeper: str,
        supporting_witness: str,
        public_witness: str,
        *,
        issue_context: str = "",
    ) -> str:
        blueprint = ctx.workflow.blueprint
        cast_names = (
            set(character_names(blueprint.character_bible))
            if blueprint is not None
            else set()
        )
        missing_sibling = self._canonicalize_character_name(
            self._resolve_sibling_reference(ctx, protagonist),
            cast_names,
        )
        departed_characters = self._combined_departed_characters(
            ctx,
            protagonist,
            issue_context=issue_context,
        )
        excluded_markers = self._late_arc_excluded_markers(
            ctx,
            protagonist,
            cast_names,
        )

        def eligible(candidate: str) -> str:
            normalized = self._canonicalize_character_name(
                " ".join(str(candidate).split()).strip(),
                cast_names,
            )
            if not normalized:
                return ""
            if normalized in {
                protagonist,
                primary_keeper,
                supporting_witness,
                public_witness,
                missing_sibling,
            }:
                return ""
            if self._is_symbolic_late_arc_candidate(normalized):
                return ""
            if self._is_generic_terminal_role_title(normalized):
                return ""
            if self._departure_chapter_for_name(normalized, departed_characters) is not None:
                return ""
            if self._is_restrained_late_arc_candidate(
                ctx,
                normalized,
                cast_names=cast_names,
            ):
                return ""
            if self._is_late_arc_excluded_candidate(
                normalized,
                cast_names=cast_names,
                excluded_markers=excluded_markers,
            ):
                return ""
            return normalized

        setup_candidate = self._resolve_late_arc_setup_candidate(
            ctx,
            protagonist,
            cast_names,
            issue_context=issue_context,
        )
        resolved_setup_candidate = eligible(setup_candidate)
        if resolved_setup_candidate:
            return resolved_setup_candidate

        setup_numbers = {
            max(1, ctx.story.chapter_count - 7),
            max(1, ctx.story.chapter_count - 6),
        }
        for chapter in ctx.story.chapters:
            if chapter.chapter_number not in setup_numbers:
                continue
            for candidate in (
                str(chapter.metadata.get("focus_character", "")),
                str(chapter.metadata.get("relationship_target", "")),
            ):
                resolved = eligible(candidate)
                if resolved:
                    return resolved

        if blueprint is not None:
            for entry in blueprint.character_bible.get("key_supporting", []):
                if isinstance(entry, dict):
                    resolved = eligible(entry.get("name", ""))
                else:
                    resolved = eligible(getattr(entry, "name", ""))
                if resolved:
                    return resolved

        return next(
            (
                candidate
                for candidate in (supporting_witness, public_witness, primary_keeper)
                if candidate
                and not self._is_generic_terminal_placeholder(candidate)
                and not self._is_generic_terminal_role_title(candidate)
            ),
            "",
        )

    def _resolve_late_arc_setup_candidate(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
        cast_names: set[str],
        *,
        issue_context: str = "",
    ) -> str:
        normalized_issue_context = issue_context.lower()
        protagonist_label, allies = self._resolve_cast_labels(ctx)
        keeper_pool = self._resolve_late_arc_keeper_pool(
            ctx,
            protagonist_label or protagonist,
            allies,
            issue_context=issue_context,
        )
        for candidate in keeper_pool:
            raw_candidate = " ".join(str(candidate).split()).strip()
            if self._is_symbolic_late_arc_candidate(raw_candidate):
                continue
            normalized = self._canonicalize_character_name(raw_candidate, cast_names)
            if not normalized or normalized == protagonist:
                continue
            if self._is_generic_terminal_role_title(normalized):
                continue
            if normalized.lower() in normalized_issue_context:
                return normalized

        for candidate in keeper_pool:
            normalized = self._canonicalize_character_name(candidate, cast_names)
            if normalized and normalized != protagonist and not self._is_generic_terminal_role_title(normalized):
                return normalized
        return ""

    @staticmethod
    def _candidate_object_pronoun(
        ctx: StoryWorkflowContext,
        candidate_name: str,
    ) -> str:
        return "them"

    @staticmethod
    def _candidate_possessive_pronoun(
        ctx: StoryWorkflowContext,
        candidate_name: str,
    ) -> str:
        return "their"

    @staticmethod
    def _set_outline_chapter_strands(
        outline_chapter: StoryOutlineChapter,
        *,
        primary_strand: str,
        secondary_strand: str | None = None,
    ) -> bool:
        changed = False
        if outline_chapter.narrative_strand != primary_strand:
            outline_chapter.narrative_strand = primary_strand
            changed = True
        if outline_chapter.primary_strand != primary_strand:
            outline_chapter.primary_strand = primary_strand
            changed = True
        if outline_chapter.secondary_strand != secondary_strand:
            outline_chapter.secondary_strand = secondary_strand
            changed = True
        return changed

    def _late_arc_intervention_clause(
        self,
        ctx: StoryWorkflowContext,
        actor: str,
        protagonist: str,
    ) -> str:
        normalized_actor = " ".join(str(actor).split()).strip()
        if not normalized_actor or normalized_actor == protagonist:
            return ""

        blueprint = ctx.workflow.blueprint
        if blueprint is None:
            return (
                ", because the second silence is already chewing through the public line and "
                "will strip more names away if nobody speaks first,"
            )

        antagonists = set(antagonist_names(blueprint.character_bible))
        key_supporting = {
            " ".join(str(entry.get("name", "")).split()).strip()
            for entry in blueprint.character_bible.get("key_supporting", [])
            if isinstance(entry, dict)
        }
        if normalized_actor in antagonists:
            return (
                f", with the same erased debt already chewing through the last shards of {normalized_actor}'s authority "
                "because the confession will finish swallowing that name next if nobody speaks first,"
            )
        if normalized_actor not in key_supporting:
            return (
                ", because the second silence is already stripping nerve and memory out of the line if nobody speaks first,"
            )
        return ""

    @staticmethod
    def _relationship_progression_status(
        *,
        chapter_number: int,
        target_chapters: int,
    ) -> str:
        return relationship_progression_status(
            chapter_number=chapter_number,
            target_chapters=target_chapters,
        )

    @staticmethod
    def _is_symbolic_late_arc_candidate(name: str) -> bool:
        lowered = str(name).strip().lower()
        if not lowered:
            return False
        return any(
            token in lowered
            for token in (
                "ghost",
                "ledger",
                "shell",
                "vessel",
                "witness line",
                "confession circle",
                "oath",
                "rite",
                "echo",
            )
        )

    @staticmethod
    def _is_antagonistic_profile_text(profile_text: str) -> bool:
        lowered = " ".join(str(profile_text).split()).lower()
        if not lowered:
            return False
        return any(
            token in lowered
            for token in (
                "antagonist",
                "usurper",
                "tyrant",
                "despot",
                "eraser",
                "erase",
                "erasure",
                "purge",
                "purger",
                "obliterate",
                "suppression",
                "censor",
                "dominion",
                "dominate",
                "executioner",
            )
        )

    @staticmethod
    def _dedupe_sentences(text: str) -> str:
        normalized_text = " ".join(str(text).split())
        if not normalized_text:
            return ""
        sentences = re.split(r"(?<=[.!?])\s+", normalized_text)
        unique: list[str] = []
        seen: set[str] = set()
        for sentence in sentences:
            cleaned = sentence.strip()
            if not cleaned:
                continue
            marker = cleaned.lower()
            if marker in seen:
                continue
            seen.add(marker)
            unique.append(cleaned)
        return " ".join(unique).strip()

    @staticmethod
    def _strip_authorial_terminal_summary_instructions(text: str) -> str:
        normalized_text = " ".join(str(text).split())
        if not normalized_text:
            return ""
        sentences = re.split(r"(?<=[.!?])\s+", normalized_text)
        kept: list[str] = []
        directive_pattern = re.compile(
            r"^(stage|keep|make|contrast|break|let|if)\b",
            flags=re.IGNORECASE,
        )
        directive_markers = (
            "reckoning",
            "vessel",
            "closure",
            "ending",
            "public line",
            "witness line",
            "returning consciousness",
            "written mark",
            "physical cadence",
            "visible markers",
        )
        inline_rewrites = (
            (r"\bthe prose makes clear that\b", ""),
            (r"\bthe duty shift lands inside the keeper\b", "the duty settles on the keeper"),
            (r"\bthe duty shift lands\b", "the duty settles"),
            (r"\bkeeps the ending intimate without implying a return\b", ""),
            (r"\bkeeps the ending intimate\b", ""),
            (r"\bon the page\b", ""),
        )
        embedded_authorial_markers = (
            "objective",
            "writer",
            "reader",
            "story mechanic",
            "writing mechanic",
        )
        for sentence in sentences:
            cleaned = sentence.strip()
            if not cleaned:
                continue
            rewritten = cleaned
            for pattern, replacement in inline_rewrites:
                rewritten = re.sub(pattern, replacement, rewritten, flags=re.IGNORECASE)
            rewritten = re.sub(r"\s+", " ", rewritten).strip(" ,;:-")
            lowered = rewritten.lower()
            if any(marker in lowered for marker in embedded_authorial_markers):
                continue
            if directive_pattern.match(cleaned) and any(
                marker in lowered for marker in directive_markers
            ):
                continue
            if not rewritten:
                continue
            kept.append(rewritten)
        return " ".join(kept).strip()

    @classmethod
    def _looks_authorial_terminal_summary(cls, text: str) -> bool:
        if not text:
            return False
        cleaned = " ".join(str(text).split())
        stripped = cls._strip_authorial_terminal_summary_instructions(cleaned)
        return bool(cleaned and not stripped) or stripped != cleaned

    @staticmethod
    def _is_generic_terminal_placeholder(text: str) -> bool:
        normalized = " ".join(str(text).split()).strip().lower()
        return normalized in GENERIC_TERMINAL_PLACEHOLDERS

    @staticmethod
    def _is_generic_terminal_role_title(text: str) -> bool:
        normalized = " ".join(str(text).split()).strip().lower()
        if not normalized.startswith("the "):
            return False
        remainder = normalized.removeprefix("the ").strip()
        if not remainder:
            return True
        tokens = {
            token.strip(".,;:!?")
            for token in remainder.split()
            if token.strip(".,;:!?")
        }
        return bool(tokens) and tokens <= GENERIC_TERMINAL_ROLE_TITLES

    @staticmethod
    def _dedupe_terminal_identity_seal_sentences(text: str) -> str:
        normalized_text = " ".join(str(text).split())
        if not normalized_text:
            return ""
        sentences = re.split(r"(?<=[.!?])\s+", normalized_text)
        unique: list[str] = []
        seen_identity_seal = False
        speech_pattern = re.compile(
            r"\b(speak|speaks|spoke|say|says|said|utter|utters|uttered|voice|voices|named|names|name aloud)\b",
            flags=re.IGNORECASE,
        )
        for sentence in sentences:
            cleaned = sentence.strip()
            if not cleaned:
                continue
            lowered = cleaned.lower()
            mentions_identity_seal = "name" in lowered and speech_pattern.search(cleaned) is not None
            if mentions_identity_seal:
                if seen_identity_seal:
                    continue
                seen_identity_seal = True
            unique.append(cleaned)
        return " ".join(unique).strip()

    @staticmethod
    def _prefer_terminal_phase_summary(
        text: str,
        replacement: str,
        *,
        required_markers: tuple[str, ...],
        max_words: int = 42,
    ) -> str:
        normalized = " ".join(str(text).split())
        if not normalized:
            return " ".join(str(replacement).split())
        lowered = normalized.lower()
        if len(normalized.split()) <= max_words and all(marker in lowered for marker in required_markers):
            return normalized
        return " ".join(str(replacement).split())

    def _normalize_departed_relationship_status(
        self,
        *,
        relationship_status: str,
        focus_character: str,
        relationship_target: str,
        departed_characters: dict[str, int],
        chapter_number: int,
        target_chapters: int,
    ) -> str:
        normalized_status = " ".join(str(relationship_status).split()).strip()
        if not normalized_status:
            return ""
        target_base, target_is_vessel = self._split_vessel_label(relationship_target)
        focus_departed_at = self._departure_chapter_for_name(focus_character, departed_characters)
        target_departed_at = self._departure_chapter_for_name(target_base, departed_characters)
        focus_is_departed = focus_departed_at is not None and focus_departed_at <= chapter_number
        target_is_departed = (
            not target_is_vessel
            and target_departed_at is not None
            and target_departed_at <= chapter_number
        )
        if not (focus_is_departed or target_is_departed or target_is_vessel):
            return normalized_status
        lowered = normalized_status.lower()
        if any(token in lowered for token in ("legacy influence", "spirit guide", "memory guide", "echo")):
            if not target_is_vessel:
                phase = self._terminal_phase_for_chapter(chapter_number, target_chapters)
                if phase == "aftermath":
                    return "grief sharpened by absence"
                if phase == "rule_revelation":
                    return "absence steering the search for proof"
                if phase == "public_reckoning":
                    return "legacy carried into public witness"
                if phase == "closure":
                    return "legacy accepted in public"
            return normalized_status
        if target_is_vessel:
            phase = self._terminal_phase_for_chapter(chapter_number, target_chapters)
            if phase == "aftermath":
                return "keeper confronting the vessel"
            if phase == "rule_revelation":
                return "keeper reading the cost through the vessel"
            if phase == "public_reckoning":
                return "keeper carrying the vessel before witnesses"
            if phase == "closure":
                return "living line carrying the vessel's cost"
            return "keeper of the vessel"
        phase = self._terminal_phase_for_chapter(chapter_number, target_chapters)
        if phase == "aftermath":
            return "grief sharpened by absence"
        if phase == "rule_revelation":
            return "absence steering the search for proof"
        if phase == "public_reckoning":
            return "legacy carried into public witness"
        if phase == "closure":
            return "legacy accepted in public"
        return "legacy influence"

    def _late_arc_sequence(
        self,
        ctx: StoryWorkflowContext,
        *,
        issue_context: str = "",
    ) -> dict[str, dict[str, str | int]]:
        frame = self._build_terminal_arc_semantic_frame(
            ctx,
            issue_context=issue_context,
        )
        blueprint = ctx.workflow.blueprint
        cast_names = (
            set(character_names(blueprint.character_bible))
            if blueprint is not None
            else set()
        )
        vessel_target = self._normalize_vessel_target_label(
            frame.vessel_label,
            cast_names,
        )
        alias_to_phase = {
            "sacrifice": "sacrifice",
            "aftermath": "aftermath",
            "discovery": "rule_revelation",
            "attempt": "public_reckoning",
            "resolution": "closure",
        }
        hook_strength_by_phase = {
            "sacrifice": 79,
            "aftermath": 80,
            "rule_revelation": 82,
            "public_reckoning": 84,
            "closure": 78,
        }
        relationship_status_by_phase = {
            "sacrifice": "final living handoff before the irreversible cost",
            "aftermath": "guardian of the empty shell",
            "rule_revelation": "keeper of the vessel",
            "public_reckoning": "accepted voice of the public record",
            "closure": "living voice of the confession line",
        }

        sequence: dict[str, dict[str, str | int]] = {}
        for alias, phase in alias_to_phase.items():
            chapter_number = frame.phase_map[phase]
            plan: dict[str, str | int] = dict(
                self._default_terminal_arc_phase_plan(
                phase=phase,
                chapter_number=chapter_number,
                protagonist=frame.protagonist,
                primary_keeper=frame.primary_keeper,
                supporting_witness=frame.supporting_witness,
                public_witness=frame.public_witness,
                vessel_label=frame.vessel_label,
                continuity_anchor=frame.continuity_anchor,
                confirmation_trigger=frame.confirmation_trigger,
                motif_ledger=frame.motif_ledger,
                closure_beats=frame.closure_beats,
                public_cost_example=frame.public_cost_example,
                )
            )
            plan["number"] = chapter_number
            plan["hook_strength"] = hook_strength_by_phase[phase]
            plan["relationship_status"] = relationship_status_by_phase[phase]
            if phase == "sacrifice":
                plan["focus_character"] = frame.protagonist
                plan["relationship_target"] = frame.primary_keeper
            else:
                plan["focus_character"] = frame.primary_keeper
                plan["relationship_target"] = (
                    vessel_target
                    if vessel_target
                    and vessel_target not in {frame.primary_keeper, frame.protagonist}
                    else frame.public_witness or frame.supporting_witness
                )
            sequence[alias] = plan
        return sequence

    def _compact_live_late_arc_summaries(
        self,
        ctx: StoryWorkflowContext,
        outline: StoryOutlineArtifact,
        *,
        issue_codes: set[str] | None = None,
        issue_context: str,
    ) -> bool:
        lowered_context = issue_context.lower()
        active_issue_codes = issue_codes or set()
        needs_compaction = bool(
            {"weak_serial_pull", "plot_confusion", "world_logic_soft_conflict", "ooc_behavior", "promise_break"}
            & active_issue_codes
        ) or any(
            token in lowered_context
            for token in (
                "extremely dense with simultaneous events",
                "shift from lin yuan",
                "living voice",
                "maintenance tax",
                "memory tax",
                "continuing costs",
                "failed rehearsal",
                "public confession",
                "character agency violation",
                "exposition overload",
                "unclear resolution of grief",
                "echo-leader",
                "sealed blank line",
                "specific citizen-level grief reaction",
            )
        )
        if not needs_compaction:
            return False
        frame = self._build_terminal_arc_semantic_frame(
            ctx,
            issue_context=issue_context,
        )
        memory_detail = self._resolve_terminal_memory_detail(ctx, frame.protagonist)
        anchor_label = self._resolve_anchor_label(ctx)
        civic_target = self._resolve_civic_target_label(ctx)
        antagonist_label = self._resolve_primary_antagonist_label(ctx, frame.protagonist)
        chapter_numbers = self._late_arc_chapter_numbers(ctx.story.chapter_count)
        phase_aliases = {
            "sacrifice": "sacrifice",
            "aftermath": "aftermath",
            "discovery": "rule_revelation",
            "attempt": "public_reckoning",
            "resolution": "closure",
        }
        second_witness = (
            frame.supporting_witness
            if frame.supporting_witness != frame.public_witness
            else frame.continuity_anchor or frame.primary_keeper
        )
        heroic_witness = self._resolve_late_arc_heroic_witness(
            ctx,
            frame.protagonist,
            frame.primary_keeper,
            frame.supporting_witness,
            frame.public_witness,
            issue_context=issue_context,
        )
        concrete_memory = memory_detail or "one ordinary habit from the earlier life"
        phase_scene_additions = {
            chapter_numbers["aftermath"]: (
                f"In the first private break, the marked token reaches {frame.primary_keeper} while rain taps the eaves and rough wood stays under the palm. A cold answer from the seal jars {frame.primary_keeper}'s hand off the rail, the seal in the frame cracks one line wider, and a draft slams the shutters before {frame.primary_keeper} can take another step. Only after that pause does {frame.primary_keeper} try once to wake {frame.vessel_label} and get only cold weight and silence back. A pulse of winter-blue ink curls across the ledger and points toward the next choice while {frame.public_witness} cuts in with one blunt question, and {frame.primary_keeper} chooses the city's debt over private grief before the room settles. {frame.primary_keeper} sets a marked token down before stepping away."
            ),
            chapter_numbers["discovery"]: (
                f"Testing the proof at {anchor_label}, {frame.supporting_witness or frame.primary_keeper} finds a visible consequence instead of an explanation, and {frame.vessel_label} gives one brief residual shiver before going still while chalk dust and lamp heat press against the wall. The keeper and {frame.supporting_witness or frame.public_witness} exchange one sharp look before the proof is touched, and the reaction stays with the living line."
            ),
            chapter_numbers["attempt"]: (
                f"At {civic_target}, the first surge hits before the explanation ends and the chapter splits into two beats. A pulse of winter-blue ink curls across the ledger and points toward the next choice without waking the vessel. {frame.public_witness} moves while {heroic_witness or second_witness} takes the still hand of {frame.vessel_label} and presses it to the ledger, and {antagonist_label} stands under guard while boots and wind keep moving around the still vessel and a loose banner snaps in the gale. After one clear silence, {frame.primary_keeper} says the needed name out loud and {frame.supporting_witness or frame.public_witness} reacts to the chalk mark with a visible flinch before the ritual seal lands. "
                f"{frame.vessel_label} remains a mute shape while the burned names darken on the ledger and the lantern glass cracks once."
            ),
            chapter_numbers["resolution"]: (
                f"As noon gives way to dusk and then to night, the ending passes through private grief, public confession, and a final ledger handoff. In the private scene, {frame.public_witness} speaks {concrete_memory} into silence with no answer from {frame.vessel_label} and pauses on the loss before moving on; in the public square, the city adopts the rule in daylight and one ordinary task resumes; in the ledger scene, {frame.primary_keeper} writes the final entry once before the record passes forward, and {frame.public_cost_example}. Before the page dries, {frame.primary_keeper} sees a blank line take a new name in winter-blue ink, the lamp flame gutters, the room cools, and the window shudders in the draft."
            ),
        }

        changed = False
        outline_by_number = {chapter.chapter_number: chapter for chapter in outline.chapters}
        for alias, chapter_number in chapter_numbers.items():
            phase = phase_aliases[alias]
            plan = self._default_terminal_arc_phase_plan(
                phase=phase,
                chapter_number=chapter_number,
                protagonist=frame.protagonist,
                primary_keeper=frame.primary_keeper,
                supporting_witness=frame.supporting_witness,
                public_witness=frame.public_witness,
                vessel_label=frame.vessel_label,
                continuity_anchor=frame.continuity_anchor,
                confirmation_trigger=frame.confirmation_trigger,
                motif_ledger=frame.motif_ledger,
                closure_beats=frame.closure_beats,
                public_cost_example=frame.public_cost_example,
            )
            chapter = next(
                (item for item in ctx.story.chapters if item.chapter_number == chapter_number),
                None,
            )
            if chapter is None:
                continue
            outline_chapter = outline_by_number.get(chapter_number)

            if chapter.summary != plan["summary"]:
                chapter.summary = plan["summary"]
                changed = True
            if str(chapter.metadata.get("chapter_objective", "")).strip() != plan["objective"]:
                chapter.metadata["chapter_objective"] = plan["objective"]
                changed = True
            if str(chapter.metadata.get("outline_hook", "")).strip() != plan["hook"]:
                chapter.metadata["outline_hook"] = plan["hook"]
                changed = True
            if str(chapter.metadata.get("focus_character", "")).strip() != plan["focus_character"]:
                chapter.metadata["focus_character"] = plan["focus_character"]
                changed = True
            if str(chapter.metadata.get("relationship_target", "")).strip() != plan["relationship_target"]:
                chapter.metadata["relationship_target"] = plan["relationship_target"]
                changed = True
            if str(chapter.metadata.get("relationship_status", "")).strip() != plan["relationship_status"]:
                chapter.metadata["relationship_status"] = plan["relationship_status"]
                changed = True

            if outline_chapter is not None:
                if outline_chapter.summary != plan["summary"]:
                    outline_chapter.summary = plan["summary"]
                    changed = True
                if outline_chapter.chapter_objective != plan["objective"]:
                    outline_chapter.chapter_objective = plan["objective"]
                    changed = True
                if outline_chapter.hook != plan["hook"]:
                    outline_chapter.hook = plan["hook"]
                    changed = True

            if chapter.current_scene is not None:
                scene_text = chapter.current_scene.content
                scene_addition = phase_scene_additions.get(chapter_number, "")
                if scene_addition:
                    updated_scene = self._append_unique_sentence(scene_text, scene_addition)
                    if updated_scene != scene_text:
                        chapter.current_scene.update_content(updated_scene)
                        changed = True
                updated_scene_with_hook = ensure_hook(chapter.current_scene.content, plan["hook"])
                if updated_scene_with_hook != chapter.current_scene.content:
                    chapter.current_scene.update_content(updated_scene_with_hook)
                    changed = True
                previous_hook = str(chapter.metadata.get("previous_hook", "")).strip()
                if previous_hook:
                    updated_scene_with_payoff = ensure_payoff_anchor(
                        chapter.current_scene.content,
                        previous_hook,
                    )
                    if updated_scene_with_payoff != chapter.current_scene.content:
                        chapter.current_scene.update_content(updated_scene_with_payoff)
                        changed = True

        return changed

    @staticmethod
    def _late_arc_chapter_numbers(total_chapters: int) -> dict[str, int]:
        return {
            "sacrifice": max(1, total_chapters - 4),
            "aftermath": max(1, total_chapters - 3),
            "discovery": max(1, total_chapters - 2),
            "attempt": max(1, total_chapters - 1),
            "resolution": max(1, total_chapters),
        }

    def _resolve_terminal_vessel_label(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
        *,
        primary_keeper: str,
    ) -> str:
        blueprint = ctx.workflow.blueprint
        cast_names = (
            set(character_names(blueprint.character_bible))
            if blueprint is not None
            else set()
        )
        late_arc_numbers = set(self._terminal_phase_numbers(ctx.story.chapter_count).values())
        keeper_vessel = self._vessel_label_for_character(primary_keeper)
        protagonist_name = " ".join(str(protagonist).split()).strip()
        for chapter in ctx.story.chapters:
            if chapter.chapter_number not in late_arc_numbers:
                continue
            for field in ("relationship_target", "focus_character"):
                normalized_target = self._normalize_vessel_target_label(
                    str(chapter.metadata.get(field, "")).strip(),
                    cast_names,
                )
                if (
                    normalized_target
                    and normalized_target.lower().endswith("(vessel)")
                    and normalized_target != keeper_vessel
                ):
                    target_base, _ = self._split_vessel_label(normalized_target)
                    canonical_target = self._canonicalize_character_name(target_base, cast_names)
                    if canonical_target and canonical_target != protagonist_name:
                        return normalized_target
        return self._late_arc_vessel_label(protagonist)

    @staticmethod
    def _vessel_label_for_character(character_name: str) -> str:
        normalized = " ".join(str(character_name).split()).strip()
        if not normalized:
            return "The Vessel"
        if normalized.endswith("(Vessel)"):
            return normalized
        return f"{normalized} (Vessel)"

    @classmethod
    def _late_arc_vessel_label(cls, protagonist: str) -> str:
        del protagonist
        return "The Vessel"

    @staticmethod
    def _split_vessel_label(candidate: str) -> tuple[str, bool]:
        normalized = " ".join(str(candidate).split()).strip()
        if normalized.lower() in {"the vessel", "vessel", "silent vessel"}:
            return "", True
        if normalized.lower().endswith("(vessel)"):
            return normalized[:-9].strip(), True
        return normalized, False

    def _normalize_vessel_target_label(
        self,
        candidate: str,
        cast_names: set[str],
    ) -> str:
        normalized = " ".join(str(candidate).split()).strip()
        if normalized.lower() in {"the vessel", "vessel", "silent vessel"}:
            return "The Vessel"
        base_name, is_vessel = self._split_vessel_label(candidate)
        canonical = self._canonicalize_character_name(base_name, cast_names)
        if not canonical or canonical not in cast_names:
            return ""
        if is_vessel:
            return self._vessel_label_for_character(canonical)
        return canonical

    @staticmethod
    def _normalize_protagonist_name_drift(
        text: str,
        protagonist: str,
        cast_names: set[str],
    ) -> str:
        normalized_text = " ".join(str(text).split())
        if not normalized_text or not protagonist:
            return normalized_text
        parts = protagonist.split()
        if len(parts) < 2:
            return normalized_text

        surname = parts[0]
        pattern = re.compile(rf"\b{re.escape(surname)}\s+[A-Z][A-Za-z-]+\b")

        def replace_candidate(match: re.Match[str]) -> str:
            candidate = match.group(0).strip()
            if candidate == protagonist or candidate in cast_names:
                return candidate
            return protagonist

        return pattern.sub(replace_candidate, normalized_text)

    @staticmethod
    def _character_title_aliases(base_name: str) -> list[str]:
        normalized_base = str(base_name).strip()
        if not normalized_base:
            return []
        titles = (
            "Lady",
            "Lord",
            "Master",
            "Captain",
            "Commander",
            "Archivist",
            "Scribe",
            "High Scribe",
            "Grand Scribe",
            "Chancellor",
            "Grand Chancellor",
            "Archon",
            "High Archon",
            "Magistrate",
            "Grand Magistrate",
            "Elder",
        )
        return [f"{title} {normalized_base}" for title in titles]

    @staticmethod
    def _character_detection_aliases(character_name: str) -> list[str]:
        aliases = [character_name.strip()]
        parts = character_name.split()
        if parts:
            aliases.append(parts[-1])
            if len(parts) >= 2:
                aliases.append(f"Old {parts[-1]}")
            if len(parts) == 1:
                aliases.extend(StoryRevisionService._character_title_aliases(parts[-1]))
        return [alias for alias in aliases if alias]

    @staticmethod
    def _character_reference_aliases(character_name: str) -> list[str]:
        aliases = [character_name.strip()]
        parts = character_name.split()
        if len(parts) >= 2:
            aliases.append(f"Old {parts[-1]}")
        if len(parts) == 1:
            aliases.extend(StoryRevisionService._character_title_aliases(parts[-1]))
        return [alias for alias in aliases if alias]

    def _canonicalize_character_name(
        self,
        candidate_name: str,
        cast_names: set[str],
    ) -> str:
        normalized_candidate = " ".join(str(candidate_name).split()).strip()
        if not normalized_candidate or not cast_names:
            return normalized_candidate

        lower_to_canonical = {
            canonical.lower(): canonical for canonical in cast_names if canonical
        }
        direct_match = lower_to_canonical.get(normalized_candidate.lower())
        if direct_match:
            return direct_match

        for canonical_name in cast_names:
            aliases = {
                alias.lower()
                for alias in (
                    self._character_detection_aliases(canonical_name)
                    + self._character_reference_aliases(canonical_name)
                )
            }
            if normalized_candidate.lower() in aliases:
                return canonical_name
        return normalized_candidate

    def _departure_chapter_for_name(
        self,
        candidate_name: str,
        departed_characters: dict[str, int],
    ) -> int | None:
        normalized_candidate = str(candidate_name).strip().lower()
        if not normalized_candidate:
            return None
        for canonical_name, departed_at in departed_characters.items():
            aliases = {
                alias.lower()
                for alias in (
                    self._character_detection_aliases(canonical_name)
                    + self._character_reference_aliases(canonical_name)
                    + self._character_title_aliases(canonical_name.split()[-1])
                )
            }
            if normalized_candidate in aliases:
                return departed_at
        return None

    @staticmethod
    def _legacyize_character_reference(text: str, character_name: str) -> str:
        normalized_text = " ".join(str(text).split())
        if not normalized_text or character_name not in normalized_text:
            return normalized_text

        lower_text = normalized_text.lower()
        lower_name = character_name.lower()
        normalized_text = re.sub(
            rf"\b{re.escape(character_name)},\s+a Debt Ghost,\s*",
            f"the legacy of {character_name} ",
            normalized_text,
            flags=re.IGNORECASE,
        )
        normalized_text = re.sub(
            rf"\b{re.escape(character_name)}'s debt ghost\b",
            f"the legacy of {character_name}",
            normalized_text,
            flags=re.IGNORECASE,
        )
        normalized_text = re.sub(
            rf"\bdebt ghost of {re.escape(character_name)}\b",
            f"the legacy of {character_name}",
            normalized_text,
            flags=re.IGNORECASE,
        )
        lower_text = normalized_text.lower()

        if (
            f"{lower_name}'s legacy" in lower_text
            or f"legacy of {lower_name}" in lower_text
            or f"memory of {lower_name}" in lower_text
            or f"{lower_name}'s memory projection" in lower_text
        ):
            return StoryRevisionService._stabilize_legacy_subject(
                normalized_text,
                character_name,
            )

        possessive_pattern = re.compile(rf"(?<!-)\b{re.escape(character_name)}'s\b(?!-)")
        if possessive_pattern.search(normalized_text):
            normalized_text = possessive_pattern.sub(
                f"{character_name}'s legacy",
                normalized_text,
            )
            return StoryRevisionService._stabilize_legacy_subject(
                normalized_text,
                character_name,
            )

        plain_pattern = re.compile(rf"(?<!-)\b{re.escape(character_name)}\b(?!-)")
        normalized_text = plain_pattern.sub(
            f"the legacy of {character_name}",
            normalized_text,
        )
        return StoryRevisionService._stabilize_legacy_subject(
            normalized_text,
            character_name,
        )

    @staticmethod
    def _stabilize_legacy_subject(text: str, character_name: str) -> str:
        normalized_text = " ".join(str(text).split())
        if not normalized_text:
            return normalized_text

        subject_patterns = {
            rf"\bthe legacy of {re.escape(character_name)} guides\b": f"The surviving archivists follow guidance preserved by {character_name} and lead",
            rf"\bthe legacy of {re.escape(character_name)} remains\b": f"The memory of {character_name} remains",
            rf"\bthe legacy of {re.escape(character_name)} uses\b": f"The surviving archivists use records left by {character_name} to",
            rf"\bthe legacy of {re.escape(character_name)} helps\b": f"The surviving archivists use records left by {character_name} to help",
            rf"\bthe legacy of {re.escape(character_name)} performs\b": f"The surviving archivists perform rites first taught by {character_name} to",
            rf"\bthe legacy of {re.escape(character_name)} leads\b": f"The surviving archivists follow the example {character_name} left behind and lead",
        }
        for pattern, replacement in subject_patterns.items():
            normalized_text = re.sub(
                pattern,
                replacement,
                normalized_text,
                flags=re.IGNORECASE,
            )
        return " ".join(normalized_text.split())

    @staticmethod
    def _issue_context(issues: list[StoryReviewIssue]) -> str:
        fragments: list[str] = []
        for issue in issues:
            fragments.extend(
                [
                    issue.code,
                    issue.message,
                    issue.location or "",
                    issue.suggestion or "",
                ]
            )
            if issue.details:
                fragments.extend(str(value) for value in issue.details.values())
        return " ".join(
            fragment.strip().lower()
            for fragment in fragments
            if fragment and fragment.strip()
        )

    @staticmethod
    def _issue_verbatim_context(issues: list[StoryReviewIssue]) -> str:
        fragments: list[str] = []
        for issue in issues:
            fragments.extend(
                [
                    issue.code,
                    issue.message,
                    issue.location or "",
                    issue.suggestion or "",
                ]
            )
            if issue.details:
                fragments.extend(str(value) for value in issue.details.values())
        return " ".join(
            fragment.strip()
            for fragment in fragments
            if fragment and fragment.strip()
        )

    @staticmethod
    def _extract_issue_chapters(location: str | None) -> list[int]:
        if not location:
            return []
        normalized_location = str(location)
        chapters: set[int] = set()
        for start_text, end_text in re.findall(
            r"(?:chapters?|ch)\s*(\d+)\s*[-–]\s*(\d+)",
            normalized_location,
            flags=re.IGNORECASE,
        ):
            start = int(start_text)
            end = int(end_text)
            chapters.update(range(min(start, end), max(start, end) + 1))
        for number_text in re.findall(
            r"(?:chapter|ch)\s*(\d+)",
            normalized_location,
            flags=re.IGNORECASE,
        ):
            chapters.add(int(number_text))
        return sorted(chapters)

    @staticmethod
    def _resolve_anchor_label(ctx: StoryWorkflowContext) -> str:
        outline = ctx.workflow.outline
        fragments: list[str] = [ctx.story.title]
        fragments.extend(chapter.summary or "" for chapter in ctx.story.chapters)
        fragments.extend(entry.rule for entry in ctx.memory.world_rules)
        if outline is not None:
            fragments.extend(chapter.summary for chapter in outline.chapters)
        combined = " ".join(fragments).lower()
        if "archive" in combined:
            return "the Archive seal"
        return "the surviving oath seal"

    @staticmethod
    def _resolve_civic_target_label(ctx: StoryWorkflowContext) -> str:
        outline = ctx.workflow.outline
        fragments: list[str] = [ctx.story.title, ctx.workflow.premise]
        fragments.extend(chapter.summary or "" for chapter in ctx.story.chapters)
        if outline is not None:
            fragments.extend(chapter.summary for chapter in outline.chapters)
            fragments.extend(chapter.chapter_objective for chapter in outline.chapters)
        combined = " ".join(fragment for fragment in fragments if fragment).lower()
        if any(token in combined for token in ("ledger", "archive", "oath", "debt")):
            return "The Public Ledger"
        if any(token in combined for token in ("council", "chancellor", "senate", "ministry")):
            return "The City Council"
        return "The City Council"

    @staticmethod
    def _resolve_founding_lie_event(ctx: StoryWorkflowContext) -> str:
        outline = ctx.workflow.outline
        fragments: list[str] = [ctx.story.title, ctx.workflow.premise]
        fragments.extend(chapter.summary or "" for chapter in ctx.story.chapters)
        if outline is not None:
            fragments.extend(chapter.summary for chapter in outline.chapters)
            fragments.extend(chapter.chapter_objective for chapter in outline.chapters)
        combined = " ".join(fragment for fragment in fragments if fragment).lower()
        if "archive" in combined and any(token in combined for token in ("burn", "fire", "scorch", "purge")):
            return "the Archive Purge"
        if any(token in combined for token in ("ledger", "archive", "oath", "debt", "memory")):
            return "the Archive Purge"
        return "the founding purge"

    @staticmethod
    def _resolve_founding_lie_definition(ctx: StoryWorkflowContext) -> str:
        founding_lie_event = StoryRevisionService._resolve_founding_lie_event(ctx)
        if founding_lie_event.lower() == "the archive purge":
            return (
                "the Archive Purge, when the founders burned the first debtors' names out of the public ledger"
            )
        return (
            f"{founding_lie_event}, when the founders burned the first debtors' names out of the public ledger"
        )

    def _resolve_late_arc_keeper_pool(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
        allies: list[str],
        *,
        issue_context: str = "",
    ) -> list[str]:
        departed_characters = self._combined_departed_characters(
            ctx,
            protagonist,
            issue_context=issue_context,
        )
        blueprint = ctx.workflow.blueprint
        cast_names = (
            set(character_names(blueprint.character_bible))
            if blueprint is not None
            else set()
        )
        excluded_markers = self._late_arc_excluded_markers(
            ctx,
            protagonist,
            cast_names,
        )
        late_arc_candidates = self._late_arc_metadata_candidates(
            ctx,
            protagonist,
            departed_characters,
        )
        surviving_allies = self._resolve_surviving_allies(
            ctx,
            protagonist,
            allies,
            issue_context=issue_context,
        )
        filtered_surviving_allies = [
            name
            for name in surviving_allies
            if name
            and name != protagonist
            and not self._is_symbolic_late_arc_candidate(name)
            and not self._is_generic_terminal_role_title(name)
            and not self._is_late_arc_excluded_candidate(
                name,
                cast_names=cast_names,
                excluded_markers=excluded_markers,
            )
        ]
        continuity_anchor = self._resolve_terminal_arc_continuity_anchor(
            ctx,
            protagonist,
            allies,
            issue_context=issue_context,
        )
        if filtered_surviving_allies:
            if continuity_anchor and continuity_anchor in filtered_surviving_allies:
                return [continuity_anchor]
            late_arc_numbers = set(self._late_arc_chapter_numbers(ctx.story.chapter_count).values())
            explicit_candidates: list[str] = []
            for chapter in ctx.story.chapters:
                if chapter.chapter_number not in late_arc_numbers:
                    continue
                for field in ("focus_character", "relationship_target"):
                    candidate = self._canonicalize_character_name(
                        str(chapter.metadata.get(field, "")).strip(),
                        cast_names,
                    )
                    if (
                        candidate
                        and candidate in filtered_surviving_allies
                        and not self._is_symbolic_late_arc_candidate(candidate)
                        and not self._is_generic_terminal_role_title(candidate)
                        and candidate not in explicit_candidates
                        and not self._is_late_arc_excluded_candidate(
                            candidate,
                            cast_names=cast_names,
                            excluded_markers=excluded_markers,
                        )
                    ):
                        explicit_candidates.append(candidate)
            ranked_candidates = [
                name for name in late_arc_candidates if name in filtered_surviving_allies
            ]
            if explicit_candidates:
                for candidate in ranked_candidates:
                    if candidate in explicit_candidates:
                        return [candidate]
                return [explicit_candidates[0]]
            if ranked_candidates:
                return [ranked_candidates[0]]
            return [filtered_surviving_allies[0]]

        if late_arc_candidates:
            return [late_arc_candidates[0]]

        blueprint = ctx.workflow.blueprint
        if blueprint is not None:
            supporting_cast = [
                name
                for name in character_names(blueprint.character_bible)
                if name and name != protagonist
                and not self._is_symbolic_late_arc_candidate(name)
                and not self._is_generic_terminal_role_title(name)
                and self._departure_chapter_for_name(name, departed_characters) is None
                and not self._is_late_arc_excluded_candidate(
                    name,
                    cast_names=cast_names,
                    excluded_markers=excluded_markers,
                )
            ]
            if supporting_cast:
                return supporting_cast

        if allies:
            filtered_allies = [
                name
                for name in allies
                if name
                and name != protagonist
                and not self._is_symbolic_late_arc_candidate(name)
                and not self._is_generic_terminal_role_title(name)
                and self._departure_chapter_for_name(name, departed_characters) is None
                and not self._is_late_arc_excluded_candidate(
                    name,
                    cast_names=cast_names,
                    excluded_markers=excluded_markers,
                )
            ]
            if filtered_allies:
                return filtered_allies

        memory_candidates = [
            name
            for name in ctx.memory.active_characters
            if name
            and name != protagonist
            and not self._is_symbolic_late_arc_candidate(name)
            and not self._is_generic_terminal_role_title(name)
            and self._departure_chapter_for_name(name, departed_characters) is None
            and not self._is_late_arc_excluded_candidate(
                name,
                cast_names=cast_names,
                excluded_markers=excluded_markers,
            )
        ]
        if memory_candidates:
            return memory_candidates

        return [protagonist]

    def _resolve_late_arc_legacy_voice(
        self,
        ctx: StoryWorkflowContext,
        protagonist: str,
        primary_keeper: str,
        *,
        issue_context: str = "",
    ) -> str:
        departed_characters = self._combined_departed_characters(
            ctx,
            protagonist,
            issue_context=issue_context,
        )
        _protagonist, allies = self._resolve_cast_labels(ctx)

        for candidate in allies:
            if (
                candidate
                and candidate != protagonist
                and candidate != primary_keeper
                and not self._is_symbolic_late_arc_candidate(candidate)
                and self._departure_chapter_for_name(candidate, departed_characters)
                is not None
            ):
                return candidate

        blueprint = ctx.workflow.blueprint
        cast_names = (
            character_names(blueprint.character_bible)
            if blueprint is not None
            else []
        )
        for candidate in cast_names:
            if (
                candidate
                and candidate != protagonist
                and candidate != primary_keeper
                and not self._is_symbolic_late_arc_candidate(candidate)
                and self._departure_chapter_for_name(candidate, departed_characters)
                is not None
            ):
                return candidate
        return ""

    @staticmethod
    def _resolve_sibling_reference(
        ctx: StoryWorkflowContext,
        protagonist: str,
    ) -> str:
        blueprint = ctx.workflow.blueprint
        default_reference = "the missing sister"
        if blueprint is None:
            return default_reference

        character_bible = blueprint.character_bible
        protagonist_profile = character_profile(character_bible, protagonist)
        motivation_text = " ".join(
            str(protagonist_profile.get(key, "")).strip()
            for key in ("motivation", "goal", "arc", "summary", "notes")
            if str(protagonist_profile.get(key, "")).strip()
        ).lower()
        possessive = "their"
        if "his sister" in motivation_text:
            possessive = "his"
        elif "her sister" in motivation_text:
            possessive = "her"

        antagonists = set(antagonist_names(character_bible))
        protagonist_parts = protagonist.split()
        protagonist_surname = protagonist_parts[0] if len(protagonist_parts) >= 2 else ""

        for name in character_names(character_bible):
            if not name or name == protagonist or name in antagonists:
                continue
            profile = character_profile(character_bible, name)
            profile_text = " ".join(
                str(profile.get(key, "")).strip()
                for key in (
                    "role",
                    "motivation",
                    "goal",
                    "arc",
                    "summary",
                    "notes",
                    "relationship_to_protagonist",
                )
                if str(profile.get(key, "")).strip()
            ).lower()
            if "sister" in profile_text:
                return name
            if protagonist_surname and name.startswith(f"{protagonist_surname} "):
                return name

        if "sister" in motivation_text:
            return f"{possessive} missing sister"
        return default_reference

    @staticmethod
    def _resolve_sibling_memory_detail(
        ctx: StoryWorkflowContext,
        protagonist: str,
    ) -> str:
        sibling_reference = StoryRevisionService._resolve_sibling_reference(
            ctx,
            protagonist,
        )
        lowered_reference = sibling_reference.lower()
        if "missing sister" not in lowered_reference:
            return f"the dock-step count the household used when calling {sibling_reference} home"
        return "the dock-step count the household used while calling the missing child home through the ferry fog"

    @staticmethod
    def _resolve_sibling_public_proof(
        ctx: StoryWorkflowContext,
        protagonist: str,
    ) -> str:
        sibling_reference = StoryRevisionService._resolve_sibling_reference(ctx, protagonist)
        return (
            f"The dock porter copies the restored name for {sibling_reference} onto the morning ferry slate with shaking care, mouths each syllable like an act of love before touching the public rail, "
            "and the first harbor queue moves without skipping that family again."
        )

    @staticmethod
    def _resolve_sibling_closure_beat(
        ctx: StoryWorkflowContext,
        protagonist: str,
    ) -> str:
        sibling_reference = StoryRevisionService._resolve_sibling_reference(ctx, protagonist)
        return (
            f"the family names {sibling_reference} to one another, lets the silence after that name stand as proof the child is still gone, feels the loss settle back into the public record as a carried memory the room must keep, and lets that private grief settle before dawn"
        )

    def _resolve_late_arc_liminal_witness_clause(
        self,
        ctx: StoryWorkflowContext,
        *candidates: str,
    ) -> str:
        blueprint = ctx.workflow.blueprint
        if blueprint is None:
            return ""

        cast_names = set(character_names(blueprint.character_bible))
        authority_tokens = {
            "ruler",
            "queen",
            "king",
            "empress",
            "emperor",
            "sovereign",
            "crown",
            "throne",
            "regent",
            "heir",
            "princess",
            "prince",
        }
        liminal_tokens = {
            "ghost",
            "spirit",
            "specter",
            "shade",
            "witness",
            "anchor",
            "echo",
        }

        for candidate in candidates:
            normalized = self._canonicalize_character_name(
                " ".join(str(candidate).split()).strip(),
                cast_names,
            )
            if not normalized:
                continue
            profile = character_profile(blueprint.character_bible, normalized)
            profile_text = " ".join(
                str(profile.get(key, "")).strip()
                for key in ("role", "summary", "notes", "arc", "relationship_to_protagonist")
                if str(profile.get(key, "")).strip()
            ).lower()
            if not profile_text:
                continue
            has_authority = any(token in profile_text for token in authority_tokens)
            has_liminal = any(token in profile_text for token in liminal_tokens)
            if has_authority and has_liminal:
                return (
                    f"Beside the rail, {normalized}'s outline stops flickering and settles into one stable witness-shape, "
                    "no longer passing for a restored ruler and not fading into rumor either. "
                )
            if has_liminal:
                return (
                    f"Beside the rail, {normalized}'s outline stops flickering and settles into one stable witness-shape that will remain when the bells stop. "
                )
        return ""


__all__ = ["StoryRevisionService"]
