"""
Unit tests for the narrative engine V2 core value objects.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.contexts.narratives.domain.value_objects import (
    NarrativeGuidance,
    PacingAdjustment,
    StoryArcPhase,
    StoryArcState,
)

try:
    from src.contexts.narratives.domain.value_objects.plot_point import PlotPointType
except ModuleNotFoundError:
    from contexts.narratives.domain.value_objects.plot_point import PlotPointType


class TestStoryArcPhase:
    """Behaviour validation for StoryArcPhase enum helpers."""

    def test_enum_contains_expected_members(self) -> None:
        phase_names = {phase.name for phase in StoryArcPhase}
        assert phase_names == {
            "EXPOSITION",
            "RISING_ACTION",
            "CLIMAX",
            "FALLING_ACTION",
            "RESOLUTION",
        }

    def test_phase_properties_expose_expected_metadata(self) -> None:
        assert StoryArcPhase.EXPOSITION.typical_position_ratio == (0.0, 0.15)
        assert StoryArcPhase.CLIMAX.typical_pacing_intensity == "fast"

        tension_low, tension_high = StoryArcPhase.FALLING_ACTION.typical_tension_range
        assert tension_low == Decimal("5.0")
        assert tension_high == Decimal("7.0")


class TestStoryArcState:
    """Tests for the StoryArcState immutable snapshot model."""

    def _build_state(self, **overrides: object) -> StoryArcState:
        base_kwargs: dict[str, object] = {
            "current_phase": StoryArcPhase.RISING_ACTION,
            "phase_progress": Decimal("0.4"),
            "overall_progress": Decimal("0.3"),
            "arc_id": "arc-001",
            "turn_number": 12,
            "sequence_number": 27,
            "turns_in_current_phase": 5,
            "current_tension_level": Decimal("6.5"),
            "active_plot_thread_count": 3,
            "unresolved_conflict_count": 2,
        }
        base_kwargs.update(overrides)
        return StoryArcState(**base_kwargs)

    def test_defaults_are_applied(self) -> None:
        state = self._build_state()
        assert state.transition_requirements == []
        assert state.metadata == {}
        assert state.state_timestamp <= datetime.now(timezone.utc)
        assert state.phase_position_description == "early"

    def test_is_phase_complete_true_when_progress_and_transition_ready(self) -> None:
        state = self._build_state(
            phase_progress=Decimal("0.96"),
            ready_for_phase_transition=True,
        )
        assert state.is_phase_complete is True

    def test_is_phase_complete_false_when_below_threshold(self) -> None:
        state = self._build_state(phase_progress=Decimal("0.7"))
        assert state.is_phase_complete is False

    def test_to_context_dict_contains_expected_fields(self) -> None:
        state = self._build_state()
        context = state.to_context_dict()

        assert context["current_phase"] == StoryArcPhase.RISING_ACTION.value
        assert pytest.approx(context["phase_progress"], rel=1e-6) == 0.4
        assert context["active_plot_threads"] == 3
        assert context["ready_for_transition"] is False

    def test_state_is_immutable(self) -> None:
        state = self._build_state()
        with pytest.raises(ValidationError):
            state.turn_number = 13  # type: ignore[misc]

    @pytest.mark.parametrize(
        "field,value",
        [
            ("phase_progress", Decimal("1.2")),
            ("overall_progress", Decimal("-0.1")),
            ("current_tension_level", Decimal("12")),
        ],
    )
    def test_invalid_progress_values_raise(self, field: str, value: Decimal) -> None:
        with pytest.raises(ValidationError):
            self._build_state(**{field: value})

    def test_transition_requirements_reject_empty_strings(self) -> None:
        with pytest.raises(ValidationError):
            self._build_state(transition_requirements=[""])


class TestNarrativeGuidance:
    """Tests for the NarrativeGuidance value object."""

    def _build_guidance(self, **overrides: object) -> NarrativeGuidance:
        base_state = StoryArcState(
            current_phase=StoryArcPhase.EXPOSITION,
            phase_progress=Decimal("0.2"),
            overall_progress=Decimal("0.1"),
            arc_id="arc-100",
            turn_number=3,
            sequence_number=5,
            turns_in_current_phase=2,
            current_tension_level=Decimal("3.5"),
            active_plot_thread_count=1,
            unresolved_conflict_count=0,
        )
        base_kwargs: dict[str, object] = {
            "guidance_id": "guidance-123",
            "turn_number": 3,
            "arc_state": base_state,
            "primary_narrative_goal": "Introduce key conflict",
        }
        base_kwargs.update(overrides)
        return NarrativeGuidance(**base_kwargs)

    def test_defaults_populate_lists_and_metadata(self) -> None:
        guidance = self._build_guidance()
        assert guidance.secondary_narrative_goals == []
        assert guidance.themes_to_emphasize == []
        assert guidance.metadata == {}
        assert guidance.target_tension_level == Decimal("5.0")
        assert guidance.created_timestamp <= datetime.now(timezone.utc)

    def test_to_director_context_matches_expected_shape(self) -> None:
        guidance = self._build_guidance(
            secondary_narrative_goals=["Foreshadow villain"],
            suggested_plot_point_type=PlotPointType.INCITING_INCIDENT,
            must_include_elements=["mysterious symbol"],
        )
        context = guidance.to_director_context()

        assert context["narrative_goal"] == "Introduce key conflict"
        assert context["secondary_goals"] == ["Foreshadow villain"]
        assert pytest.approx(context["content_mix"]["dialogue"], rel=1e-6) == 0.3
        assert context["required_elements"] == ["mysterious symbol"]

    def test_guidance_is_immutable(self) -> None:
        guidance = self._build_guidance()
        with pytest.raises(ValidationError):
            guidance.narrative_tone = "dark"  # type: ignore[misc]

    def test_invalid_ratio_sum_raises(self) -> None:
        with pytest.raises(ValidationError):
            self._build_guidance(
                dialogue_ratio=Decimal("0.5"),
                action_ratio=Decimal("0.5"),
                reflection_ratio=Decimal("0.5"),
            )

    def test_empty_primary_goal_not_allowed(self) -> None:
        with pytest.raises(ValidationError):
            self._build_guidance(primary_narrative_goal="  ")


class TestPacingAdjustment:
    """Tests for the PacingAdjustment value object."""

    def _build_adjustment(self, **overrides: object) -> PacingAdjustment:
        base_kwargs: dict[str, object] = {
            "adjustment_id": "adjustment-22",
            "turn_number": 7,
            "intensity_modifier": Decimal("1.0"),
            "tension_target": Decimal("6.0"),
        }
        base_kwargs.update(overrides)
        return PacingAdjustment(**base_kwargs)

    def test_defaults_initialise_metadata(self) -> None:
        adjustment = self._build_adjustment()
        assert adjustment.dialogue_adjustment == Decimal("0")
        assert adjustment.metadata == {}
        assert (
            adjustment.created_timestamp
            <= datetime.now(timezone.utc) + timedelta(seconds=1)
        )

    def test_adjustment_is_immutable(self) -> None:
        adjustment = self._build_adjustment()
        with pytest.raises(ValidationError):
            adjustment.intensity_modifier = Decimal("2.0")  # type: ignore[misc]

    @pytest.mark.parametrize(
        "field,value",
        [
            ("intensity_modifier", Decimal("3.5")),
            ("tension_target", Decimal("12")),
            ("dialogue_adjustment", Decimal("0.5")),
        ],
    )
    def test_out_of_bounds_values_raise(self, field: str, value: Decimal) -> None:
        with pytest.raises(ValidationError):
            self._build_adjustment(**{field: value})

    def test_negative_turn_number_raises(self) -> None:
        with pytest.raises(ValidationError):
            self._build_adjustment(turn_number=-1)
