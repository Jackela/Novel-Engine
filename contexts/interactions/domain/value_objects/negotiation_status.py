#!/usr/bin/env python3
"""
Negotiation Status Value Objects

This module implements value objects for tracking the status and state
of negotiations within the Interaction bounded context.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class NegotiationPhase(Enum):
    """Enumeration of negotiation phases."""

    INITIATION = "initiation"
    PREPARATION = "preparation"
    OPENING = "opening"
    BARGAINING = "bargaining"
    CLOSING = "closing"
    IMPLEMENTATION = "implementation"
    TERMINATED = "terminated"


class NegotiationOutcome(Enum):
    """Enumeration of possible negotiation outcomes."""

    PENDING = "pending"
    AGREEMENT_REACHED = "agreement_reached"
    PARTIAL_AGREEMENT = "partial_agreement"
    STALEMATE = "stalemate"
    WALKAWAY = "walkaway"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class TerminationReason(Enum):
    """Enumeration of negotiation termination reasons."""

    MUTUAL_AGREEMENT = "mutual_agreement"
    UNILATERAL_WITHDRAWAL = "unilateral_withdrawal"
    TIMEOUT_EXCEEDED = "timeout_exceeded"
    IRRECONCILABLE_DIFFERENCES = "irreconcilable_differences"
    EXTERNAL_INTERVENTION = "external_intervention"
    VIOLATION_OF_TERMS = "violation_of_terms"
    FORCE_MAJEURE = "force_majeure"


@dataclass(frozen=True)
class NegotiationStatus:
    """
    Value object representing the current status of a negotiation.

    Tracks the phase, outcome, and timing information for negotiations,
    providing immutable state representation following DDD principles.
    """

    phase: NegotiationPhase
    outcome: NegotiationOutcome
    started_at: datetime
    last_activity_at: datetime
    expected_completion_at: Optional[datetime] = None
    actual_completion_at: Optional[datetime] = None
    termination_reason: Optional[TerminationReason] = None

    def __post_init__(self):
        """Validate the negotiation status data."""
        # Ensure timestamps are timezone-aware
        for field_name in [
            "started_at",
            "last_activity_at",
            "expected_completion_at",
            "actual_completion_at",
        ]:
            timestamp = getattr(self, field_name)
            if timestamp and timestamp.tzinfo is None:
                raise ValueError(f"{field_name} must be timezone-aware")

        # Validate logical consistency
        if self.started_at > self.last_activity_at:
            raise ValueError(
                "started_at cannot be later than last_activity_at"
            )

        if (
            self.expected_completion_at
            and self.started_at > self.expected_completion_at
        ):
            raise ValueError(
                "started_at cannot be later than expected_completion_at"
            )

        if (
            self.actual_completion_at
            and self.started_at > self.actual_completion_at
        ):
            raise ValueError(
                "started_at cannot be later than actual_completion_at"
            )

        # Validate outcome-phase consistency
        if self.phase == NegotiationPhase.TERMINATED:
            if self.outcome == NegotiationOutcome.PENDING:
                raise ValueError(
                    "Terminated negotiations cannot have pending outcome"
                )
            if not self.termination_reason:
                raise ValueError(
                    "Terminated negotiations must have a termination reason"
                )
            if not self.actual_completion_at:
                raise ValueError(
                    "Terminated negotiations must have actual completion time"
                )

        if (
            self.outcome != NegotiationOutcome.PENDING
            and self.phase != NegotiationPhase.TERMINATED
        ):
            if self.outcome in [
                NegotiationOutcome.AGREEMENT_REACHED,
                NegotiationOutcome.PARTIAL_AGREEMENT,
            ]:
                if self.phase not in [
                    NegotiationPhase.CLOSING,
                    NegotiationPhase.IMPLEMENTATION,
                ]:
                    raise ValueError(
                        f"Outcome {self.outcome.value} inconsistent with phase {self.phase.value}"
                    )

    @classmethod
    def create_initial(
        cls,
        started_at: Optional[datetime] = None,
        expected_completion_at: Optional[datetime] = None,
    ) -> "NegotiationStatus":
        """Create initial negotiation status."""
        now = started_at or datetime.now(timezone.utc)
        return cls(
            phase=NegotiationPhase.INITIATION,
            outcome=NegotiationOutcome.PENDING,
            started_at=now,
            last_activity_at=now,
            expected_completion_at=expected_completion_at,
        )

    def advance_to_phase(
        self,
        new_phase: NegotiationPhase,
        activity_time: Optional[datetime] = None,
    ) -> "NegotiationStatus":
        """Advance negotiation to a new phase."""
        if not self._is_valid_phase_transition(self.phase, new_phase):
            raise ValueError(
                f"Invalid phase transition from {self.phase.value} to {new_phase.value}"
            )

        activity_time = activity_time or datetime.now(timezone.utc)

        return NegotiationStatus(
            phase=new_phase,
            outcome=self.outcome,
            started_at=self.started_at,
            last_activity_at=activity_time,
            expected_completion_at=self.expected_completion_at,
            actual_completion_at=self.actual_completion_at,
            termination_reason=self.termination_reason,
        )

    def complete_with_outcome(
        self,
        outcome: NegotiationOutcome,
        completion_time: Optional[datetime] = None,
        termination_reason: Optional[TerminationReason] = None,
    ) -> "NegotiationStatus":
        """Complete negotiation with specific outcome."""
        completion_time = completion_time or datetime.now(timezone.utc)

        return NegotiationStatus(
            phase=NegotiationPhase.TERMINATED,
            outcome=outcome,
            started_at=self.started_at,
            last_activity_at=completion_time,
            expected_completion_at=self.expected_completion_at,
            actual_completion_at=completion_time,
            termination_reason=termination_reason,
        )

    def update_last_activity(
        self, activity_time: Optional[datetime] = None
    ) -> "NegotiationStatus":
        """Update last activity timestamp."""
        activity_time = activity_time or datetime.now(timezone.utc)

        return NegotiationStatus(
            phase=self.phase,
            outcome=self.outcome,
            started_at=self.started_at,
            last_activity_at=activity_time,
            expected_completion_at=self.expected_completion_at,
            actual_completion_at=self.actual_completion_at,
            termination_reason=self.termination_reason,
        )

    def _is_valid_phase_transition(
        self, from_phase: NegotiationPhase, to_phase: NegotiationPhase
    ) -> bool:
        """Check if phase transition is valid."""
        valid_transitions = {
            NegotiationPhase.INITIATION: [
                NegotiationPhase.PREPARATION,
                NegotiationPhase.TERMINATED,
            ],
            NegotiationPhase.PREPARATION: [
                NegotiationPhase.OPENING,
                NegotiationPhase.TERMINATED,
            ],
            NegotiationPhase.OPENING: [
                NegotiationPhase.BARGAINING,
                NegotiationPhase.TERMINATED,
            ],
            NegotiationPhase.BARGAINING: [
                NegotiationPhase.CLOSING,
                NegotiationPhase.TERMINATED,
            ],
            NegotiationPhase.CLOSING: [
                NegotiationPhase.IMPLEMENTATION,
                NegotiationPhase.TERMINATED,
            ],
            NegotiationPhase.IMPLEMENTATION: [NegotiationPhase.TERMINATED],
            NegotiationPhase.TERMINATED: [],  # Terminal state
        }

        # P3 Sprint 2 Pattern: Explicit type cast for operator compatibility
        from typing import List, cast

        allowed_phases = cast(
            List[NegotiationPhase], valid_transitions.get(from_phase, [])
        )
        return to_phase in allowed_phases

    @property
    def is_active(self) -> bool:
        """Check if negotiation is currently active."""
        return self.phase != NegotiationPhase.TERMINATED

    @property
    def is_completed(self) -> bool:
        """Check if negotiation is completed."""
        return self.outcome != NegotiationOutcome.PENDING

    @property
    def duration(self) -> Optional[int]:
        """Get negotiation duration in seconds."""
        if self.actual_completion_at:
            return int(
                (self.actual_completion_at - self.started_at).total_seconds()
            )
        return None

    @property
    def time_since_last_activity(self) -> int:
        """Get time since last activity in seconds."""
        now = datetime.now(timezone.utc)
        return int((now - self.last_activity_at).total_seconds())

    def __eq__(self, other: Any) -> bool:
        """Compare NegotiationStatus instances for equality."""
        if not isinstance(other, NegotiationStatus):
            return False
        return (
            self.phase == other.phase
            and self.outcome == other.outcome
            and self.started_at == other.started_at
            and self.last_activity_at == other.last_activity_at
            and self.expected_completion_at == other.expected_completion_at
            and self.actual_completion_at == other.actual_completion_at
            and self.termination_reason == other.termination_reason
        )

    def __str__(self) -> str:
        """Return string representation of negotiation status."""
        return f"NegotiationStatus(phase={self.phase.value}, outcome={self.outcome.value})"
