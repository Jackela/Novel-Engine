"""
State machine for managing narrative story arc progression.

The StoryArcManager coordinates transitions between StoryArcPhase values while
maintaining domain invariants defined in the V2 design document.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, Optional, Sequence

from ..value_objects import StoryArcPhase, StoryArcState

PhaseSequence = Sequence[StoryArcPhase]


class StoryArcManager:
    """
    Coordinate StoryArcState life-cycle events and enforce valid transitions.
    """

    DEFAULT_SEQUENCE: PhaseSequence = (
        StoryArcPhase.EXPOSITION,
        StoryArcPhase.RISING_ACTION,
        StoryArcPhase.CLIMAX,
        StoryArcPhase.FALLING_ACTION,
        StoryArcPhase.RESOLUTION,
    )

    def __init__(
        self,
        initial_state: StoryArcState,
        *,
        phase_sequence: Optional[PhaseSequence] = None,
    ) -> None:
        self._phase_sequence: PhaseSequence = phase_sequence or self.DEFAULT_SEQUENCE
        self._phase_index_map = {phase: idx for idx, phase in enumerate(self._phase_sequence)}
        self._validate_sequence(self._phase_sequence)
        self._state: StoryArcState = self._validate_initial_state(initial_state)

    @property
    def current_state(self) -> StoryArcState:
        """Return the latest StoryArcState snapshot."""

        return self._state

    @property
    def current_phase(self) -> StoryArcPhase:
        """Convenience accessor for the phase of the current state."""

        return self._state.current_phase

    def update_state(self, new_state: StoryArcState) -> StoryArcState:
        """
        Replace the current state with a new snapshot.

        The new state must belong to the same arc and may only advance a single
        phase at a time. Regressions to earlier phases are not permitted.
        """

        self._validate_state_transition(new_state)
        self._state = new_state
        return self._state

    def can_advance(self) -> bool:
        """Determine whether the state machine is able to advance phases."""

        return (
            self._next_phase(self._state.current_phase) is not None
            and self._state.is_phase_complete
            and not self._state.transition_requirements
        )

    def advance_to_next_phase(
        self,
        *,
        metadata_updates: Optional[Dict[str, Any]] = None,
        state_overrides: Optional[Dict[str, Any]] = None,
    ) -> StoryArcState:
        """
        Transition the story arc to the next phase if all requirements are met.

        Args:
            metadata_updates: Optional metadata entries to merge into the new state.
            state_overrides: Optional raw field overrides applied to the resulting state.

        Returns:
            The newly created StoryArcState after the transition.

        Raises:
            RuntimeError: If the transition is invalid or the phase sequence is complete.
        """

        self._ensure_can_advance()
        next_phase = self._require_next_phase(self._state.current_phase)

        next_state_data = self._state.model_dump()
        next_state_data.update(
            {
                "current_phase": next_phase,
                "phase_progress": Decimal("0"),
                "turns_in_current_phase": 0,
                "ready_for_phase_transition": False,
                "next_phase": self._next_phase(next_phase),
                "transition_requirements": [],
                "previous_phase": self._state.current_phase,
                "state_timestamp": datetime.now(timezone.utc),
            }
        )

        metadata = dict(self._state.metadata)
        if metadata_updates:
            metadata.update(metadata_updates)
        next_state_data["metadata"] = metadata

        if state_overrides:
            next_state_data.update(state_overrides)

        next_state = StoryArcState(**next_state_data)
        return self.update_state(next_state)

    def _ensure_can_advance(self) -> None:
        if self._next_phase(self._state.current_phase) is None:
            raise RuntimeError("Story arc is already at the final phase.")

        if not self._state.is_phase_complete:
            raise RuntimeError(
                "Cannot advance phase: current phase is not marked complete."
            )

        if self._state.transition_requirements:
            raise RuntimeError(
                "Cannot advance phase: transition requirements are still pending."
            )

        expected_next = self._next_phase(self._state.current_phase)
        if (
            self._state.next_phase is not None
            and expected_next is not None
            and self._state.next_phase != expected_next
        ):
            raise RuntimeError(
                f"Invalid next_phase hint ({self._state.next_phase}); "
                f"expected {expected_next}."
            )

    def _require_next_phase(self, current: StoryArcPhase) -> StoryArcPhase:
        next_phase = self._next_phase(current)
        if next_phase is None:
            raise RuntimeError("No further phases available in the sequence.")
        return next_phase

    def _next_phase(self, phase: StoryArcPhase) -> Optional[StoryArcPhase]:
        idx = self._phase_index_map[phase]
        if idx == len(self._phase_sequence) - 1:
            return None
        return self._phase_sequence[idx + 1]

    def _validate_state_transition(self, new_state: StoryArcState) -> None:
        if new_state.arc_id != self._state.arc_id:
            raise ValueError("StoryArcManager cannot switch to a different arc_id.")

        current_index = self._phase_index_map[self._state.current_phase]
        new_index = self._phase_index_map[new_state.current_phase]

        if new_index < current_index:
            raise ValueError("Story arc cannot regress to an earlier phase.")

        if new_index - current_index > 1:
            raise ValueError("Cannot skip phases during update.")

    def _validate_initial_state(self, state: StoryArcState) -> StoryArcState:
        if state.current_phase not in self._phase_index_map:
            raise ValueError("Initial state contains a phase outside of the sequence.")
        return state

    @staticmethod
    def _validate_sequence(sequence: Iterable[StoryArcPhase]) -> None:
        values = list(sequence)
        if not values:
            raise ValueError("Story arc sequence cannot be empty.")
        if len(set(values)) != len(values):
            raise ValueError("Story arc sequence contains duplicate phases.")
