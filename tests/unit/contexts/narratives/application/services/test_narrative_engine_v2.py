"""
TDD integration test for the NarrativeEngineV2 application service facade.

This test validates that the facade properly coordinates the domain services
(StoryArcManager, NarrativePlanningEngine, PacingManager) to produce
narrative context for a turn.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, Mock

import pytest

from src.contexts.narratives.application.services.narrative_engine_v2 import (
    NarrativeEngineV2,
)
from src.contexts.narratives.domain.value_objects import (
    NarrativeGuidance,
    PacingAdjustment,
    StoryArcPhase,
    StoryArcState,
)


def _build_test_state() -> StoryArcState:
    """Helper for constructing a minimal StoryArcState for testing."""

    return StoryArcState(
        current_phase=StoryArcPhase.RISING_ACTION,
        phase_progress=Decimal("0.5"),
        overall_progress=Decimal("0.4"),
        arc_id="arc-integration-test",
        turn_number=10,
        sequence_number=15,
        turns_in_current_phase=5,
        current_tension_level=Decimal("6.0"),
        active_plot_thread_count=3,
        unresolved_conflict_count=2,
    )


class TestNarrativeEngineV2:
    """Integration tests for the NarrativeEngineV2 facade."""

    def test_get_narrative_context_for_turn_coordinates_managers(self) -> None:
        """
        Verify that get_narrative_context_for_turn properly coordinates
        the planning and pacing managers and returns a NarrativeGuidance.
        """

        test_state = _build_test_state()

        mock_story_arc_manager = Mock()
        mock_planning_engine = Mock()
        mock_pacing_manager = Mock()

        mock_guidance = NarrativeGuidance(
            guidance_id="test-guidance-1",
            turn_number=10,
            arc_state=test_state,
            primary_narrative_goal="Test primary goal",
            target_tension_level=Decimal("6.5"),
        )

        mock_pacing_adjustment = PacingAdjustment(
            adjustment_id="test-pacing-1",
            turn_number=10,
            intensity_modifier=Decimal("0.5"),
            tension_target=Decimal("6.5"),
            speed_modifier=Decimal("1.2"),
        )

        mock_planning_engine.generate_guidance_for_turn.return_value = mock_guidance
        mock_pacing_manager.adjust_pacing.return_value = mock_pacing_adjustment

        engine = NarrativeEngineV2(
            story_arc_manager=mock_story_arc_manager,
            planning_engine=mock_planning_engine,
            pacing_manager=mock_pacing_manager,
        )

        result = engine.get_narrative_context_for_turn(state=test_state)

        assert isinstance(result, NarrativeGuidance)
        mock_planning_engine.generate_guidance_for_turn.assert_called_once_with(
            state=test_state
        )
        mock_pacing_manager.adjust_pacing.assert_called_once_with(state=test_state)

    def test_get_narrative_context_for_turn_integrates_pacing_into_guidance(
        self,
    ) -> None:
        """
        Verify that pacing adjustments are integrated into the returned guidance.
        """

        test_state = _build_test_state()

        mock_story_arc_manager = Mock()
        mock_planning_engine = Mock()
        mock_pacing_manager = Mock()

        base_guidance = NarrativeGuidance(
            guidance_id="test-guidance-2",
            turn_number=10,
            arc_state=test_state,
            primary_narrative_goal="Base goal",
            target_tension_level=Decimal("5.0"),
        )

        pacing_adjustment = PacingAdjustment(
            adjustment_id="test-pacing-2",
            turn_number=10,
            intensity_modifier=Decimal("1.5"),
            tension_target=Decimal("7.5"),
            speed_modifier=Decimal("1.8"),
        )

        mock_planning_engine.generate_guidance_for_turn.return_value = base_guidance
        mock_pacing_manager.adjust_pacing.return_value = pacing_adjustment

        engine = NarrativeEngineV2(
            story_arc_manager=mock_story_arc_manager,
            planning_engine=mock_planning_engine,
            pacing_manager=mock_pacing_manager,
        )

        result = engine.get_narrative_context_for_turn(state=test_state)

        assert isinstance(result, NarrativeGuidance)
        assert result.target_tension_level == Decimal("7.5")
