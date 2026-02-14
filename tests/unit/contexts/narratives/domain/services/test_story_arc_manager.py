"""
Unit tests for the StoryArcManager state machine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.contexts.narratives.domain.services import StoryArcManager
from src.contexts.narratives.domain.value_objects import StoryArcPhase, StoryArcState

pytestmark = pytest.mark.unit


def build_state(
    phase: StoryArcPhase,
    *,
    phase_progress: Decimal = Decimal("0.2"),
    ready_for_transition: bool = False,
    transition_requirements: list[str] | None = None,
    next_phase: StoryArcPhase | None = None,
) -> StoryArcState:
    """Create a StoryArcState with sensible defaults for testing."""

    return StoryArcState(
        current_phase=phase,
        phase_progress=phase_progress,
        overall_progress=Decimal("0.1"),
        arc_id="arc-123",
        turn_number=5,
        sequence_number=8,
        turns_in_current_phase=3,
        current_tension_level=Decimal("4.5"),
        active_plot_thread_count=2,
        unresolved_conflict_count=1,
        ready_for_phase_transition=ready_for_transition,
        transition_requirements=transition_requirements or [],
        next_phase=next_phase,
    )


class TestStoryArcManager:
    """StoryArcManager transition behaviour."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_initial_state_available(self) -> None:
        state = build_state(StoryArcPhase.EXPOSITION)
        manager = StoryArcManager(state)

        assert manager.current_state is state
        assert manager.current_phase == StoryArcPhase.EXPOSITION

    @pytest.mark.unit
    def test_advance_through_sequence(self) -> None:
        initial_state = build_state(
            StoryArcPhase.EXPOSITION,
            phase_progress=Decimal("0.97"),
            ready_for_transition=True,
            next_phase=StoryArcPhase.RISING_ACTION,
        )
        manager = StoryArcManager(initial_state)

        rising_state = manager.advance_to_next_phase()
        assert rising_state.current_phase == StoryArcPhase.RISING_ACTION
        assert rising_state.previous_phase == StoryArcPhase.EXPOSITION
        assert rising_state.phase_progress == Decimal("0")
        assert rising_state.turns_in_current_phase == 0
        assert rising_state.next_phase == StoryArcPhase.CLIMAX

        # Prepare the rising action state to transition again
        prepared_rising = StoryArcState(
            **{
                **rising_state.model_dump(),
                "phase_progress": Decimal("0.99"),
                "ready_for_phase_transition": True,
                "transition_requirements": [],
            }
        )
        manager.update_state(prepared_rising)

        climax_state = manager.advance_to_next_phase()
        assert climax_state.current_phase == StoryArcPhase.CLIMAX
        assert climax_state.previous_phase == StoryArcPhase.RISING_ACTION

    @pytest.mark.unit
    def test_cannot_advance_when_not_ready(self) -> None:
        manager = StoryArcManager(
            build_state(
                StoryArcPhase.EXPOSITION,
                phase_progress=Decimal("0.8"),
                ready_for_transition=False,
            )
        )

        with pytest.raises(RuntimeError):
            manager.advance_to_next_phase()

    @pytest.mark.unit
    def test_cannot_advance_with_pending_requirements(self) -> None:
        manager = StoryArcManager(
            build_state(
                StoryArcPhase.EXPOSITION,
                phase_progress=Decimal("0.96"),
                ready_for_transition=True,
                transition_requirements=["introduce_inciting_incident"],
            )
        )

        with pytest.raises(RuntimeError):
            manager.advance_to_next_phase()

    @pytest.mark.unit
    def test_cannot_skip_phases_with_update(self) -> None:
        manager = StoryArcManager(
            build_state(
                StoryArcPhase.EXPOSITION,
                phase_progress=Decimal("0.5"),
            )
        )

        skipping_state = build_state(
            StoryArcPhase.CLIMAX,
            phase_progress=Decimal("0.1"),
        )

        with pytest.raises(ValueError):
            manager.update_state(skipping_state)

    @pytest.mark.unit
    def test_cannot_rewind_phases(self) -> None:
        manager = StoryArcManager(
            build_state(
                StoryArcPhase.RISING_ACTION,
                phase_progress=Decimal("0.5"),
            )
        )

        rewinding_state = build_state(StoryArcPhase.EXPOSITION)

        with pytest.raises(ValueError):
            manager.update_state(rewinding_state)

    @pytest.mark.unit
    def test_cannot_advance_past_final_phase(self) -> None:
        manager = StoryArcManager(
            build_state(
                StoryArcPhase.RESOLUTION,
                phase_progress=Decimal("0.99"),
                ready_for_transition=True,
            )
        )

        with pytest.raises(RuntimeError):
            manager.advance_to_next_phase()

    @pytest.mark.unit
    def test_metadata_merges_when_advancing(self) -> None:
        state = StoryArcState(
            **{
                **build_state(
                    StoryArcPhase.EXPOSITION,
                    phase_progress=Decimal("0.97"),
                    ready_for_transition=True,
                    next_phase=StoryArcPhase.RISING_ACTION,
                ).model_dump(),
                "metadata": {"existing": "value"},
            }
        )
        manager = StoryArcManager(state)

        new_state = manager.advance_to_next_phase(
            metadata_updates={"transitioned_at": datetime.now(timezone.utc).isoformat()}
        )

        assert new_state.metadata["existing"] == "value"
        assert "transitioned_at" in new_state.metadata
