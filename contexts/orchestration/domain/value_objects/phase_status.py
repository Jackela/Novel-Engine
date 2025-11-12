#!/usr/bin/env python3
"""
Phase Status Value Objects

Immutable value objects for tracking pipeline phase execution status,
types, and state transitions in the turn orchestration system.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class PhaseType(Enum):
    """
    Enumeration of turn pipeline phase types.

    Defines the 5-phase turn pipeline with proper ordering
    and dependency relationships for orchestration.
    """

    WORLD_UPDATE = "world_update"
    SUBJECTIVE_BRIEF = "subjective_brief"
    INTERACTION_ORCHESTRATION = "interaction_orchestration"
    EVENT_INTEGRATION = "event_integration"
    NARRATIVE_INTEGRATION = "narrative_integration"

    def __str__(self) -> str:
        return self.value

    def get_display_name(self) -> str:
        """Get human-readable phase name."""
        names = {
            self.WORLD_UPDATE: "World State Update",
            self.SUBJECTIVE_BRIEF: "Subjective Brief Generation",
            self.INTERACTION_ORCHESTRATION: "Interaction Orchestration",
            self.EVENT_INTEGRATION: "Event Integration",
            self.NARRATIVE_INTEGRATION: "Narrative Integration",
        }
        return names[self]

    def get_phase_order(self) -> int:
        """Get numeric ordering of phases."""
        order = {
            self.WORLD_UPDATE: 1,
            self.SUBJECTIVE_BRIEF: 2,
            self.INTERACTION_ORCHESTRATION: 3,
            self.EVENT_INTEGRATION: 4,
            self.NARRATIVE_INTEGRATION: 5,
        }
        return order[self]

    def get_next_phase(self) -> Optional["PhaseType"]:
        """Get the next phase in sequence."""
        order = self.get_phase_order()
        if order >= 5:
            return None  # Last phase

        next_phases = {
            1: self.SUBJECTIVE_BRIEF,
            2: self.INTERACTION_ORCHESTRATION,
            3: self.EVENT_INTEGRATION,
            4: self.NARRATIVE_INTEGRATION,
        }
        return next_phases.get(order)

    def get_previous_phase(self) -> Optional["PhaseType"]:
        """Get the previous phase in sequence."""
        order = self.get_phase_order()
        if order <= 1:
            return None  # First phase

        prev_phases = {
            2: self.WORLD_UPDATE,
            3: self.SUBJECTIVE_BRIEF,
            4: self.INTERACTION_ORCHESTRATION,
            5: self.EVENT_INTEGRATION,
        }
        return prev_phases.get(order)

    @classmethod
    def get_all_phases_ordered(cls) -> List["PhaseType"]:
        """Get all phases in execution order."""
        return [
            cls.WORLD_UPDATE,
            cls.SUBJECTIVE_BRIEF,
            cls.INTERACTION_ORCHESTRATION,
            cls.EVENT_INTEGRATION,
            cls.NARRATIVE_INTEGRATION,
        ]


class PhaseStatusEnum(Enum):
    """
    Enumeration of phase execution status values.

    Tracks the lifecycle of each pipeline phase with support
    for saga compensation patterns and error handling.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    SKIPPED = "skipped"

    def __str__(self) -> str:
        return self.value

    def is_terminal(self) -> bool:
        """Check if this is a terminal state."""
        return self in {self.COMPLETED, self.FAILED, self.COMPENSATED, self.SKIPPED}

    def is_active(self) -> bool:
        """Check if phase is actively executing."""
        return self in {self.RUNNING, self.COMPENSATING}

    def is_successful(self) -> bool:
        """Check if phase completed successfully."""
        return self == self.COMPLETED

    def is_failure(self) -> bool:
        """Check if phase failed."""
        return self in {self.FAILED, self.COMPENSATED}

    def can_transition_to(self, new_status: "PhaseStatusEnum") -> bool:
        """Check if transition to new status is valid."""
        valid_transitions = {
            self.PENDING: {self.RUNNING, self.SKIPPED},
            self.RUNNING: {self.COMPLETED, self.FAILED},
            self.COMPLETED: {self.COMPENSATING},
            self.FAILED: {self.COMPENSATING, self.COMPENSATED},
            self.COMPENSATING: {self.COMPENSATED, self.FAILED},
            self.COMPENSATED: set(),  # Terminal
            self.SKIPPED: set(),  # Terminal
        }
        return new_status in valid_transitions.get(self, set())


@dataclass(frozen=True)
class PhaseStatus:
    """
    Immutable value object representing the status of a pipeline phase.

    Encapsulates complete phase state including execution status, timing,
    progress tracking, error information, and saga coordination data.

    Attributes:
        phase_type: Type of pipeline phase
        status: Current execution status
        started_at: Timestamp when phase started
        completed_at: Timestamp when phase completed
        duration_ms: Phase execution duration in milliseconds
        progress_percentage: Completion percentage (0-100)
        events_processed: Number of events processed in this phase
        error_message: Error details if phase failed
        compensation_actions: List of compensation actions if needed
        metadata: Additional phase-specific information

    Business Rules:
        - Status transitions must follow valid state machine
        - Completed phases must have completion timestamp
        - Failed phases must have error information
        - Duration is calculated from timestamps
        - Progress must be between 0 and 100
    """

    phase_type: PhaseType
    status: PhaseStatusEnum
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    progress_percentage: int = 0
    events_processed: int = 0
    error_message: Optional[str] = None
    compensation_actions: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Validate phase status structure and business rules."""
        # Initialize mutable defaults
        if self.compensation_actions is None:
            object.__setattr__(self, "compensation_actions", [])

        if self.metadata is None:
            object.__setattr__(self, "metadata", {})

        # Validate progress percentage
        if not 0 <= self.progress_percentage <= 100:
            raise ValueError("progress_percentage must be between 0 and 100")

        # Validate events processed
        if self.events_processed < 0:
            raise ValueError("events_processed cannot be negative")

        # Validate business rules based on status
        if self.status.is_terminal() and self.status.is_successful():
            if self.completed_at is None:
                raise ValueError("Completed phases must have completion timestamp")
            if self.progress_percentage != 100:
                raise ValueError("Completed phases must have 100% progress")

        if self.status.is_failure() and not self.error_message:
            raise ValueError("Failed phases must have error message")

        # Calculate duration if both timestamps available
        if self.started_at and self.completed_at and self.duration_ms is None:
            duration = self.completed_at - self.started_at
            object.__setattr__(
                self, "duration_ms", int(duration.total_seconds() * 1000)
            )

    @classmethod
    def create_pending(cls, phase_type: PhaseType) -> "PhaseStatus":
        """
        Create a pending phase status.

        Args:
            phase_type: Type of pipeline phase

        Returns:
            PhaseStatus in pending state
        """
        return cls(phase_type=phase_type, status=PhaseStatusEnum.PENDING)

    @classmethod
    def create_running(
        cls, phase_type: PhaseType, started_at: Optional[datetime] = None
    ) -> "PhaseStatus":
        """
        Create a running phase status.

        Args:
            phase_type: Type of pipeline phase
            started_at: Phase start time (defaults to now)

        Returns:
            PhaseStatus in running state
        """
        return cls(
            phase_type=phase_type,
            status=PhaseStatusEnum.RUNNING,
            started_at=started_at or datetime.now(),
        )

    @classmethod
    def create_completed(
        cls,
        phase_type: PhaseType,
        started_at: datetime,
        events_processed: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "PhaseStatus":
        """
        Create a completed phase status.

        Args:
            phase_type: Type of pipeline phase
            started_at: Phase start time
            events_processed: Number of events processed
            metadata: Additional phase information

        Returns:
            PhaseStatus in completed state
        """
        completed_at = datetime.now()

        return cls(
            phase_type=phase_type,
            status=PhaseStatusEnum.COMPLETED,
            started_at=started_at,
            completed_at=completed_at,
            progress_percentage=100,
            events_processed=events_processed,
            metadata=metadata or {},
        )

    @classmethod
    def create_failed(
        cls,
        phase_type: PhaseType,
        error_message: str,
        started_at: Optional[datetime] = None,
        progress_percentage: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "PhaseStatus":
        """
        Create a failed phase status.

        Args:
            phase_type: Type of pipeline phase
            error_message: Description of failure
            started_at: Phase start time if available
            progress_percentage: Progress before failure
            metadata: Additional error context

        Returns:
            PhaseStatus in failed state
        """
        return cls(
            phase_type=phase_type,
            status=PhaseStatusEnum.FAILED,
            started_at=started_at,
            completed_at=datetime.now(),
            progress_percentage=progress_percentage,
            error_message=error_message,
            metadata=metadata or {},
        )

    def transition_to(self, new_status: PhaseStatusEnum, **updates) -> "PhaseStatus":
        """
        Create new phase status with status transition.

        Args:
            new_status: Target status to transition to
            **updates: Additional field updates

        Returns:
            New PhaseStatus instance with updated status

        Raises:
            ValueError: If transition is not valid
        """
        if not self.status.can_transition_to(new_status):
            raise ValueError(
                f"Invalid status transition from {self.status} to {new_status}"
            )

        # Set defaults for specific transitions
        if new_status == PhaseStatusEnum.RUNNING and "started_at" not in updates:
            updates["started_at"] = datetime.now()

        if new_status == PhaseStatusEnum.COMPLETED:
            if "completed_at" not in updates:
                updates["completed_at"] = datetime.now()
            if "progress_percentage" not in updates:
                updates["progress_percentage"] = 100

        if new_status == PhaseStatusEnum.FAILED:
            if "completed_at" not in updates:
                updates["completed_at"] = datetime.now()

        # Create new instance with updates
        return PhaseStatus(
            phase_type=self.phase_type,
            status=new_status,
            started_at=updates.get("started_at", self.started_at),
            completed_at=updates.get("completed_at", self.completed_at),
            duration_ms=updates.get("duration_ms", self.duration_ms),
            progress_percentage=updates.get(
                "progress_percentage", self.progress_percentage
            ),
            events_processed=updates.get("events_processed", self.events_processed),
            error_message=updates.get("error_message", self.error_message),
            compensation_actions=updates.get(
                "compensation_actions", self.compensation_actions
            ),
            metadata={**self.metadata, **updates.get("metadata", {})},
        )

    def update_progress(
        self,
        progress_percentage: int,
        events_processed: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "PhaseStatus":
        """
        Update phase progress without changing status.

        Args:
            progress_percentage: New progress percentage
            events_processed: Updated event count
            metadata: Additional metadata updates

        Returns:
            New PhaseStatus with updated progress
        """
        updates = {
            "progress_percentage": progress_percentage,
            "metadata": metadata or {},
        }

        if events_processed is not None:
            updates["events_processed"] = events_processed

        return PhaseStatus(
            phase_type=self.phase_type,
            status=self.status,
            started_at=self.started_at,
            completed_at=self.completed_at,
            duration_ms=self.duration_ms,
            progress_percentage=progress_percentage,
            events_processed=events_processed or self.events_processed,
            error_message=self.error_message,
            compensation_actions=self.compensation_actions,
            metadata={**self.metadata, **updates["metadata"]},
        )

    def get_execution_time(self) -> Optional[timedelta]:
        """
        Get phase execution time as timedelta.

        Returns:
            Phase execution duration or None if not available
        """
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at and self.status.is_active():
            return datetime.now() - self.started_at
        return None

    def is_overdue(self, timeout_seconds: int) -> bool:
        """
        Check if phase is overdue based on timeout.

        Args:
            timeout_seconds: Maximum allowed execution time

        Returns:
            True if phase has exceeded timeout
        """
        if not self.started_at or self.status.is_terminal():
            return False

        elapsed = datetime.now() - self.started_at
        return elapsed.total_seconds() > timeout_seconds

    def get_display_summary(self) -> str:
        """
        Get human-readable phase summary.

        Returns:
            Formatted summary for display
        """
        name = self.phase_type.get_display_name()
        status = self.status.value.title()

        if self.status.is_successful():
            duration = f" ({self.duration_ms}ms)" if self.duration_ms else ""
            events = (
                f" - {self.events_processed} events"
                if self.events_processed > 0
                else ""
            )
            return f"{name}: {status}{duration}{events}"
        elif self.status.is_failure():
            return f"{name}: {status} - {self.error_message}"
        elif self.status.is_active():
            return f"{name}: {status} ({self.progress_percentage}%)"
        else:
            return f"{name}: {status}"

    def __str__(self) -> str:
        """String representation for general use."""
        return f"{self.phase_type.value}:{self.status.value}"

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"PhaseStatus(phase={self.phase_type}, status={self.status}, "
            f"progress={self.progress_percentage}%, events={self.events_processed})"
        )
