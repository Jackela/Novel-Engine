"""
TDD tests for the PacingManager service.

These tests describe the expected behaviour of adjust_pacing
before the manager itself is implemented.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.contexts.narratives.domain.services.pacing_manager import (
    PacingManager,
)
from src.contexts.narratives.domain.value_objects import (
    PacingAdjustment,
    StoryArcPhase,
    StoryArcState,
)

pytestmark = pytest.mark.unit


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


class TestPacingManager:
    """Desired behaviours for adjust_pacing."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_adjust_pacing_in_climax_increases_speed(self) -> None:
        manager = PacingManager()
        state = _build_state(StoryArcPhase.CLIMAX)
        adjustment = manager.adjust_pacing(state=state)

        assert isinstance(adjustment, PacingAdjustment)
        assert adjustment.speed_modifier > Decimal("1.0")

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_adjust_pacing_in_resolution_decreases_speed(self) -> None:
        manager = PacingManager()
        state = _build_state(StoryArcPhase.RESOLUTION)
        adjustment = manager.adjust_pacing(state=state)

        assert isinstance(adjustment, PacingAdjustment)
        assert adjustment.speed_modifier < Decimal("1.0")
