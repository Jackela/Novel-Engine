"""
TDD starter tests for the upcoming NarrativePlanningEngine.

These tests describe the expected behaviour of generate_guidance_for_turn
before the engine itself is implemented.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.contexts.narratives.domain.services.narrative_planning_engine import (
    NarrativePlanningEngine,
)
from src.contexts.narratives.domain.value_objects import (
    NarrativeGuidance,
    StoryArcPhase,
    StoryArcState,
)


def _build_state(phase: StoryArcPhase) -> StoryArcState:
    """Helper for constructing minimal StoryArcState fixtures."""

    return StoryArcState(
        current_phase=phase,
        phase_progress=Decimal("0.3"),
        overall_progress=Decimal("0.2"),
        arc_id="arc-test",
        turn_number=4,
        sequence_number=7,
        turns_in_current_phase=2,
        current_tension_level=Decimal("3.4"),
        active_plot_thread_count=1,
        unresolved_conflict_count=0,
    )


class TestNarrativePlanningEngine:
    """Desired behaviours for generate_guidance_for_turn."""

    def test_generate_guidance_in_exposition_focuses_on_character_intros(self) -> None:
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(
            state=_build_state(StoryArcPhase.EXPOSITION)
        )

        assert isinstance(guidance, NarrativeGuidance)
        combined_objectives = " ".join(
            [guidance.primary_narrative_goal, *guidance.secondary_narrative_goals]
        ).lower()
        assert "introduc" in combined_objectives and "character" in combined_objectives

    def test_generate_guidance_in_climax_highlights_high_tension(self) -> None:
        engine = NarrativePlanningEngine()
        state = StoryArcState(
            **{
                **_build_state(StoryArcPhase.CLIMAX).model_dump(),
                "current_tension_level": Decimal("8.5"),
                "phase_progress": Decimal("0.9"),
            }
        )

        guidance = engine.generate_guidance_for_turn(state=state)

        assert isinstance(guidance, NarrativeGuidance)
        assert (
            "high tension" in guidance.primary_narrative_goal.lower()
            or guidance.target_tension_level >= Decimal("8")
        )

    def test_generate_guidance_in_rising_action_increases_tension(self) -> None:
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(
            state=_build_state(StoryArcPhase.RISING_ACTION)
        )

        assert isinstance(guidance, NarrativeGuidance)
        combined_objectives = " ".join(
            [guidance.primary_narrative_goal, *guidance.secondary_narrative_goals]
        ).lower()
        assert "increase tension" in combined_objectives

    def test_generate_guidance_in_falling_action_resolves_subplots(self) -> None:
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(
            state=_build_state(StoryArcPhase.FALLING_ACTION)
        )

        assert isinstance(guidance, NarrativeGuidance)
        combined_objectives = " ".join(
            [guidance.primary_narrative_goal, *guidance.secondary_narrative_goals]
        ).lower()
        assert "resolve subplots" in combined_objectives

    def test_generate_guidance_in_resolution_provides_closure(self) -> None:
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(
            state=_build_state(StoryArcPhase.RESOLUTION)
        )

        assert isinstance(guidance, NarrativeGuidance)
        combined_objectives = " ".join(
            [guidance.primary_narrative_goal, *guidance.secondary_narrative_goals]
        ).lower()
        assert "provide closure" in combined_objectives
