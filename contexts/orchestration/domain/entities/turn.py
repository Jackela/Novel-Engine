#!/usr/bin/env python3
"""
Turn Aggregate Root Entity

Central domain entity managing complete turn lifecycle, saga coordination,
and pipeline orchestration across all Novel Engine contexts.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from ..value_objects import (
    CompensationAction,
    CompensationType,
    PhaseResult,
    PhaseStatus,
    PhaseStatusEnum,
    PhaseType,
    PipelineResult,
    TurnConfiguration,
    TurnId,
)


class TurnState(Enum):
    """
    Enumeration of turn aggregate states.

    Tracks overall turn lifecycle with proper state transitions
    and saga coordination support.
    """

    CREATED = "created"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPENSATING = "compensating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def __str__(self) -> str:
        return self.value

    def is_terminal(self) -> bool:
        """Check if this is a terminal state."""
        return self in {
            TurnState.COMPLETED,
            TurnState.FAILED,
            TurnState.CANCELLED,
        }

    def is_active(self) -> bool:
        """Check if turn is actively executing."""
        return self in {
            TurnState.PLANNING,
            TurnState.EXECUTING,
            TurnState.COMPENSATING,
        }

    def can_transition_to(self, new_state: "TurnState") -> bool:
        """Check if transition to new state is valid."""
        # Use explicit enum type checking for MyPy compatibility
        if self == TurnState.CREATED:
            return new_state in {TurnState.PLANNING, TurnState.CANCELLED}
        elif self == TurnState.PLANNING:
            return new_state in {
                TurnState.EXECUTING,
                TurnState.FAILED,
                TurnState.CANCELLED,
            }
        elif self == TurnState.EXECUTING:
            return new_state in {
                TurnState.COMPLETED,
                TurnState.COMPENSATING,
                TurnState.FAILED,
            }
        elif self == TurnState.COMPENSATING:
            return new_state in {TurnState.COMPLETED, TurnState.FAILED}
        elif self in {
            TurnState.COMPLETED,
            TurnState.FAILED,
            TurnState.CANCELLED,
        }:
            return False  # Terminal states
        else:
            return False


@dataclass
class Turn:
    """
    Turn aggregate root managing complete turn pipeline execution.

    Coordinates all phases of turn execution, manages saga patterns for
    reliability, tracks performance metrics, and ensures consistency
    across all Novel Engine contexts.

    Attributes:
        turn_id: Unique turn identifier
        configuration: Turn execution configuration
        state: Current turn lifecycle state
        created_at: Turn creation timestamp
        started_at: Turn execution start timestamp
        completed_at: Turn completion timestamp
        updated_at: Last modification timestamp
        phase_statuses: Current status of each pipeline phase
        compensation_actions: List of compensation actions
        pipeline_result: Final pipeline execution result
        events_generated: Domain events generated during execution
        saga_state: Current saga coordination state
        execution_context: Runtime execution context and metadata
        performance_metrics: Real-time performance tracking
        error_history: History of errors encountered
        audit_trail: Complete audit log for compliance
        version: Aggregate version for optimistic locking

    Business Rules:
        - Turn must progress through phases in order
        - Failed phases trigger appropriate compensation
        - Saga compensation must maintain consistency
        - All state changes must generate domain events
        - Performance metrics must be continuously tracked
        - Audit trail must be complete and immutable
    """

    # Core identity and configuration
    turn_id: TurnId
    configuration: TurnConfiguration
    state: TurnState = TurnState.CREATED

    # Timing and lifecycle
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.now)

    # Phase execution state
    phase_statuses: Dict[PhaseType, PhaseStatus] = field(default_factory=dict)
    current_phase: Optional[PhaseType] = None

    # Saga coordination
    compensation_actions: List[CompensationAction] = field(
        default_factory=list
    )
    saga_state: Dict[str, Any] = field(default_factory=dict)
    rollback_snapshots: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Results and events
    pipeline_result: Optional[PipelineResult] = None
    events_generated: List[Dict[str, Any]] = field(default_factory=list)

    # Runtime tracking
    execution_context: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    error_history: List[Dict[str, Any]] = field(default_factory=list)
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)

    # Versioning
    version: int = 1

    def __post_init__(self):
        """Initialize turn aggregate and validate business rules."""
        # Initialize phase statuses
        if not self.phase_statuses:
            for phase_type in PhaseType.get_all_phases_ordered():
                self.phase_statuses[phase_type] = PhaseStatus.create_pending(
                    phase_type
                )

        # Initialize saga state
        if not self.saga_state:
            self.saga_state = {
                "compensation_required": False,
                "rollback_points": {},
                "committed_phases": [],
                "pending_compensations": [],
            }

        # Initialize performance metrics
        if not self.performance_metrics:
            self.performance_metrics = {
                "start_time": None,
                "phase_durations": {},
                "events_processed": 0,
                "ai_operations_count": 0,
                "total_ai_cost": Decimal("0.00"),
                "cross_context_calls": 0,
                "memory_peak_mb": 0,
                "cpu_time_ms": 0,
            }

        # Record creation in audit trail
        self._record_audit_event(
            "turn_created",
            {
                "turn_id": str(self.turn_id.turn_uuid),
                "configuration_summary": str(self.configuration),
                "initial_state": self.state.value,
            },
        )

    def start_planning(self) -> None:
        """
        Transition turn to planning state and prepare for execution.

        Raises:
            ValueError: If transition is not valid
        """
        self._validate_state_transition(TurnState.PLANNING)

        # Update state and timing
        old_state = self.state
        self.state = TurnState.PLANNING
        self.updated_at = datetime.now()
        self.version += 1

        # Initialize execution planning
        self.execution_context = {
            "planning_started_at": datetime.now(),
            "participant_count": len(self.configuration.participants),
            "estimated_duration": self.configuration.get_total_phase_timeout(),
            "estimated_ai_cost": self.configuration.get_estimated_ai_cost(),
            "phases_planned": list(PhaseType.get_all_phases_ordered()),
            "saga_enabled": self.configuration.rollback_enabled,
        }

        # Create rollback snapshots preparation
        if self.configuration.rollback_enabled:
            self.rollback_snapshots = {
                "world_state": {},
                "narrative_state": {},
                "participant_states": {},
                "event_log": {},
            }

        # Record state transition
        self._record_audit_event(
            "state_transition",
            {
                "from_state": old_state.value,
                "to_state": self.state.value,
                "planning_context": self.execution_context,
            },
        )

        # Generate domain event
        self._generate_domain_event(
            "TurnPlanningStarted",
            {
                "turn_id": self.turn_id.turn_uuid,
                "configuration": self.configuration.__dict__,
                "estimated_duration_ms": self.execution_context[
                    "estimated_duration"
                ],
            },
        )

    def start_execution(self) -> None:
        """
        Begin turn execution by starting the first pipeline phase.

        Raises:
            ValueError: If turn is not ready for execution
        """
        self._validate_state_transition(TurnState.EXECUTING)

        # Update state and timing
        self.state = TurnState.EXECUTING
        self.started_at = datetime.now()
        self.updated_at = datetime.now()
        self.version += 1

        # Initialize performance tracking
        self.performance_metrics["start_time"] = self.started_at

        # Start first phase
        first_phase = PhaseType.WORLD_UPDATE
        self.current_phase = first_phase

        # Update phase status to running
        self.phase_statuses[first_phase] = self.phase_statuses[
            first_phase
        ].transition_to(PhaseStatusEnum.RUNNING, started_at=self.started_at)

        # Record execution start
        self._record_audit_event(
            "execution_started",
            {
                "started_at": self.started_at.isoformat(),
                "first_phase": first_phase.value,
                "total_phases": len(self.phase_statuses),
            },
        )

        # Generate domain event
        self._generate_domain_event(
            "TurnExecutionStarted",
            {
                "turn_id": self.turn_id.turn_uuid,
                "started_at": self.started_at,
                "first_phase": first_phase.value,
                "estimated_completion": (
                    self.started_at
                    + timedelta(
                        milliseconds=self.configuration.get_total_phase_timeout()
                    )
                ),
            },
        )

    def complete_phase(
        self,
        phase_type: PhaseType,
        events_processed: int = 0,
        events_generated: Optional[List[UUID]] = None,
        artifacts_created: Optional[List[str]] = None,
        performance_metrics: Optional[Dict[str, float]] = None,
        ai_usage: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Complete a pipeline phase successfully.

        Args:
            phase_type: Type of phase being completed
            events_processed: Number of events processed
            events_generated: List of event IDs generated
            artifacts_created: List of artifacts created
            performance_metrics: Phase performance measurements
            ai_usage: AI service usage statistics
            metadata: Additional phase metadata

        Raises:
            ValueError: If phase completion is invalid
        """
        if phase_type not in self.phase_statuses:
            raise ValueError(f"Unknown phase type: {phase_type}")

        current_status = self.phase_statuses[phase_type]
        if current_status.status != PhaseStatusEnum.RUNNING:
            raise ValueError(f"Phase {phase_type} is not running")

        # Complete phase status
        completed_status = current_status.transition_to(
            PhaseStatusEnum.COMPLETED,
            events_processed=events_processed,
            metadata=metadata or {},
        )

        self.phase_statuses[phase_type] = completed_status

        # Update performance metrics
        self._update_performance_metrics(
            phase_type, performance_metrics or {}, ai_usage or {}
        )

        # Create phase result
        phase_result = PhaseResult.create_successful(
            phase_type=phase_type,
            phase_status=completed_status,
            events_generated=events_generated or [],
            events_consumed=[],  # Will be populated by phase implementation
            artifacts_created=artifacts_created or [],
            performance_metrics=performance_metrics or {},
            ai_usage=ai_usage,
            metadata=metadata or {},
        )

        # Add to saga committed phases
        self.saga_state["committed_phases"].append(phase_type.value)

        # Record phase completion
        self._record_audit_event(
            "phase_completed",
            {
                "phase": phase_type.value,
                "duration_ms": completed_status.duration_ms,
                "events_processed": events_processed,
                "events_generated": len(events_generated or []),
                "artifacts_created": len(artifacts_created or []),
            },
        )

        # Generate domain event
        self._generate_domain_event(
            "PhaseCompleted",
            {
                "turn_id": self.turn_id.turn_uuid,
                "phase_type": phase_type.value,
                "phase_result": phase_result.get_performance_summary(),
                "next_phase": self._get_next_phase(phase_type),
            },
        )

        # Check if turn is complete
        if self._are_all_phases_complete():
            self._complete_turn_successfully()
        else:
            # Move to next phase
            next_phase = self._get_next_phase(phase_type)
            if next_phase:
                self._start_next_phase(next_phase)

        self.updated_at = datetime.now()
        self.version += 1

    def fail_phase(
        self,
        phase_type: PhaseType,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
        can_compensate: bool = True,
    ) -> None:
        """
        Mark a pipeline phase as failed and initiate compensation if needed.

        Args:
            phase_type: Type of phase that failed
            error_message: Description of the failure
            error_details: Detailed error information
            can_compensate: Whether compensation is possible

        Raises:
            ValueError: If phase failure handling is invalid
        """
        if phase_type not in self.phase_statuses:
            raise ValueError(f"Unknown phase type: {phase_type}")

        current_status = self.phase_statuses[phase_type]
        if current_status.status != PhaseStatusEnum.RUNNING:
            raise ValueError(f"Phase {phase_type} is not running")

        # Fail phase status
        failed_status = current_status.transition_to(
            PhaseStatusEnum.FAILED,
            error_message=error_message,
            metadata=error_details or {},
        )

        self.phase_statuses[phase_type] = failed_status

        # Record error in history
        error_record = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase_type.value,
            "error_message": error_message,
            "error_details": error_details or {},
            "can_compensate": can_compensate,
        }
        self.error_history.append(error_record)

        # Record phase failure
        self._record_audit_event("phase_failed", error_record)

        # Generate domain event
        self._generate_domain_event(
            "PhaseFailed",
            {
                "turn_id": self.turn_id.turn_uuid,
                "phase_type": phase_type.value,
                "error_message": error_message,
                "compensation_required": can_compensate
                and self.configuration.rollback_enabled,
            },
        )

        # Initiate compensation if enabled and possible
        if can_compensate and self.configuration.rollback_enabled:
            self._initiate_compensation(phase_type, error_details or {})
        else:
            # Fail turn completely
            self._fail_turn_permanently(error_message, error_details)

        self.updated_at = datetime.now()
        self.version += 1

    def _initiate_compensation(
        self, failed_phase: PhaseType, error_context: Dict[str, Any]
    ) -> None:
        """
        Initiate saga compensation for failed phase.

        Args:
            failed_phase: Phase that failed requiring compensation
            error_context: Context about the failure
        """
        # Transition to compensating state
        self.state = TurnState.COMPENSATING
        self.saga_state["compensation_required"] = True

        # Get appropriate compensation actions for the failed phase
        compensation_types = CompensationType.get_phase_compensations(
            failed_phase.value
        )

        # Create compensation actions for all committed phases
        committed_phases = self.saga_state["committed_phases"]

        for phase_name in reversed(
            committed_phases
        ):  # Reverse order compensation
            for compensation_type in compensation_types:
                if self._should_apply_compensation(
                    phase_name, compensation_type
                ):
                    compensation_action = (
                        CompensationAction.create_for_phase_failure(
                            action_id=uuid4(),
                            turn_id=self.turn_id.turn_uuid,
                            failed_phase=phase_name,
                            compensation_type=compensation_type,
                            rollback_data=self.rollback_snapshots.get(
                                phase_name, {}
                            ),
                            affected_entities=self.configuration.participants,
                            metadata={
                                "original_failure": failed_phase.value,
                                "error_context": error_context,
                                "compensation_sequence": len(
                                    self.compensation_actions
                                )
                                + 1,
                            },
                        )
                    )

                    self.compensation_actions.append(compensation_action)
                    self.saga_state["pending_compensations"].append(
                        str(compensation_action.action_id)
                    )

        # Record compensation initiation
        self._record_audit_event(
            "compensation_initiated",
            {
                "failed_phase": failed_phase.value,
                "committed_phases": committed_phases,
                "compensation_actions_created": len(self.compensation_actions),
                "error_context": error_context,
            },
        )

        # Generate domain event
        self._generate_domain_event(
            "CompensationInitiated",
            {
                "turn_id": self.turn_id.turn_uuid,
                "failed_phase": failed_phase.value,
                "compensation_actions": [
                    {
                        "action_id": str(action.action_id),
                        "type": action.compensation_type.value,
                        "target_phase": action.target_phase,
                    }
                    for action in self.compensation_actions
                ],
            },
        )

    def complete_compensation_action(
        self,
        action_id: UUID,
        results: Dict[str, Any],
        actual_cost: Optional[Decimal] = None,
    ) -> None:
        """
        Mark a compensation action as completed.

        Args:
            action_id: ID of compensation action to complete
            results: Results of compensation execution
            actual_cost: Actual cost incurred

        Raises:
            ValueError: If compensation action is not found or invalid
        """
        # Find and update compensation action
        action_index = None
        for i, action in enumerate(self.compensation_actions):
            if action.action_id == action_id:
                action_index = i
                break

        if action_index is None:
            raise ValueError(f"Compensation action not found: {action_id}")

        # Complete the action
        completed_action = self.compensation_actions[
            action_index
        ].complete_execution(results=results, actual_cost=actual_cost)

        self.compensation_actions[action_index] = completed_action

        # Remove from pending compensations
        if str(action_id) in self.saga_state["pending_compensations"]:
            self.saga_state["pending_compensations"].remove(str(action_id))

        # Record compensation completion
        self._record_audit_event(
            "compensation_completed",
            {
                "action_id": str(action_id),
                "compensation_type": completed_action.compensation_type.value,
                "target_phase": completed_action.target_phase,
                "execution_time_ms": (
                    exec_time.total_seconds() * 1000
                    if (exec_time := completed_action.get_execution_time())
                    is not None
                    else None
                ),
                "results_summary": results,
            },
        )

        # Check if all compensations are complete
        if not self.saga_state["pending_compensations"]:
            self._complete_compensation()

        self.updated_at = datetime.now()
        self.version += 1

    def _complete_compensation(self) -> None:
        """Complete saga compensation and finalize turn."""
        # Update saga state
        self.saga_state["compensation_required"] = False

        # Create pipeline result with compensation
        self._create_compensated_pipeline_result()

        # Transition to completed state
        self.state = TurnState.COMPLETED
        self.completed_at = datetime.now()

        # Record compensation completion
        self._record_audit_event(
            "compensation_completed_all",
            {
                "total_compensations": len(self.compensation_actions),
                "successful_compensations": len(
                    [
                        a
                        for a in self.compensation_actions
                        if a.status == "completed"
                    ]
                ),
                "completed_at": self.completed_at.isoformat(),
            },
        )

        # Generate domain event
        self._generate_domain_event(
            "TurnCompensationCompleted",
            {
                "turn_id": self.turn_id.turn_uuid,
                "completed_at": self.completed_at,
                "compensation_summary": {
                    "total_actions": len(self.compensation_actions),
                    "successful_actions": len(
                        [
                            a
                            for a in self.compensation_actions
                            if a.status == "completed"
                        ]
                    ),
                },
            },
        )

    def _complete_turn_successfully(self) -> None:
        """Complete turn successfully with all phases completed."""
        # Transition to completed state
        self.state = TurnState.COMPLETED
        self.completed_at = datetime.now()

        # Create successful pipeline result
        phase_results = []
        for phase_type in PhaseType.get_all_phases_ordered():
            phase_status = self.phase_statuses[phase_type]
            phase_result = PhaseResult.create_successful(
                phase_type=phase_type,
                phase_status=phase_status,
                performance_metrics=self.performance_metrics.get(
                    f"phase_{phase_type.value}", {}
                ),
            )
            phase_results.append(phase_result)

        total_execution_time = (self.completed_at or datetime.now()) - (
            self.started_at or self.created_at
        )

        self.pipeline_result = PipelineResult.create_successful(
            turn_id=self.turn_id.turn_uuid,
            phase_results=phase_results,
            total_execution_time=total_execution_time,
            metadata={
                "turn_configuration": self.configuration.__dict__,
                "performance_metrics": self.performance_metrics,
                "compensation_actions": len(self.compensation_actions),
            },
        )

        # Record successful completion
        self._record_audit_event(
            "turn_completed_successfully",
            {
                "completed_at": self.completed_at.isoformat(),
                "total_execution_time_ms": total_execution_time.total_seconds()
                * 1000,
                "phases_completed": len(phase_results),
                "performance_summary": self.pipeline_result.get_executive_summary(),
            },
        )

        # Generate domain event
        self._generate_domain_event(
            "TurnCompleted",
            {
                "turn_id": self.turn_id.turn_uuid,
                "completed_at": self.completed_at,
                "execution_time_seconds": total_execution_time.total_seconds(),
                "performance_summary": self.pipeline_result.get_executive_summary(),
            },
        )

        self.updated_at = datetime.now()
        self.version += 1

    def _fail_turn_permanently(
        self,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Permanently fail turn without compensation."""
        # Transition to failed state
        self.state = TurnState.FAILED
        self.completed_at = datetime.now()

        # Create failed pipeline result
        phase_results = []
        for phase_type in PhaseType.get_all_phases_ordered():
            phase_status = self.phase_statuses[phase_type]
            if phase_status.status == PhaseStatusEnum.COMPLETED:
                phase_result = PhaseResult.create_successful(
                    phase_type=phase_type, phase_status=phase_status
                )
            else:
                phase_result = PhaseResult.create_failed(
                    phase_type=phase_type,
                    phase_status=phase_status,
                    error_details=error_details or {"message": error_message},
                )
            phase_results.append(phase_result)

        total_execution_time = (
            self.completed_at - self.started_at
            if self.started_at
            else timedelta(seconds=0)
        )

        error_summary = {
            "primary_error": error_message,
            "error_details": error_details or {},
            "failed_phases": [
                r.phase_type.value
                for r in phase_results
                if not r.was_successful()
            ],
        }

        self.pipeline_result = PipelineResult.create_failed(
            turn_id=self.turn_id.turn_uuid,
            phase_results=phase_results,
            total_execution_time=total_execution_time,
            error_summary=error_summary,
            metadata={
                "turn_configuration": self.configuration.__dict__,
                "error_history": self.error_history,
            },
        )

        # Record failure
        self._record_audit_event(
            "turn_failed_permanently",
            {
                "failed_at": self.completed_at.isoformat(),
                "error_message": error_message,
                "error_details": error_details or {},
                "compensation_disabled": not self.configuration.rollback_enabled,
            },
        )

        # Generate domain event
        self._generate_domain_event(
            "TurnFailed",
            {
                "turn_id": self.turn_id.turn_uuid,
                "failed_at": self.completed_at,
                "error_message": error_message,
                "error_summary": error_summary,
            },
        )

        self.updated_at = datetime.now()
        self.version += 1

    # Application Service Interface Methods

    @property
    def participants(self) -> List[str]:
        """Get list of participant agent IDs from configuration."""
        return getattr(self.configuration, "participants", [])

    def mark_phase_completed(
        self, phase_type: PhaseType, success: bool
    ) -> None:
        """
        Mark a phase as completed (application service convenience method).

        Args:
            phase_type: Phase that was completed
            success: Whether phase completed successfully
        """
        if success:
            if phase_type in self.phase_statuses:
                self.phase_statuses[phase_type] = self.phase_statuses[
                    phase_type
                ].transition_to(PhaseStatusEnum.COMPLETED)
        else:
            if phase_type in self.phase_statuses:
                self.phase_statuses[phase_type] = self.phase_statuses[
                    phase_type
                ].transition_to(
                    PhaseStatusEnum.FAILED,
                    error_message="Phase execution failed",
                )

        self.updated_at = datetime.now()
        self.version += 1

    def mark_completed(self) -> None:
        """Mark turn as successfully completed (application service convenience method)."""
        if self.state.can_transition_to(TurnState.COMPLETED):
            self.state = TurnState.COMPLETED
            self.completed_at = datetime.now()
            self.updated_at = datetime.now()
            self.version += 1

    def mark_failed(self, error_message: str) -> None:
        """
        Mark turn as failed (application service convenience method).

        Args:
            error_message: Reason for failure
        """
        if self.state.can_transition_to(TurnState.FAILED):
            self.state = TurnState.FAILED
            self.completed_at = datetime.now()
            self.updated_at = datetime.now()
            self.version += 1

            # Record error in history
            self.error_history.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "error_message": error_message,
                    "error_type": "turn_failure",
                }
            )

    def add_compensation_action(self, action: CompensationAction) -> None:
        """
        Add compensation action to turn (application service convenience method).

        Args:
            action: Compensation action to add
        """
        self.compensation_actions.append(action)
        self.updated_at = datetime.now()
        self.version += 1

    # Helper methods

    def _validate_state_transition(self, new_state: TurnState) -> None:
        """Validate state transition is allowed."""
        if not self.state.can_transition_to(new_state):
            raise ValueError(
                f"Invalid state transition from {self.state} to {new_state}"
            )

    def _get_next_phase(self, current_phase: PhaseType) -> Optional[PhaseType]:
        """Get next phase in pipeline sequence."""
        return current_phase.get_next_phase()

    def _start_next_phase(self, phase_type: PhaseType) -> None:
        """Start execution of next pipeline phase."""
        self.current_phase = phase_type

        self.phase_statuses[phase_type] = self.phase_statuses[
            phase_type
        ].transition_to(PhaseStatusEnum.RUNNING, started_at=datetime.now())

        # Generate domain event
        self._generate_domain_event(
            "PhaseStarted",
            {
                "turn_id": self.turn_id.turn_uuid,
                "phase_type": phase_type.value,
                "started_at": datetime.now(),
            },
        )

    def _are_all_phases_complete(self) -> bool:
        """Check if all pipeline phases are completed."""
        for phase_status in self.phase_statuses.values():
            if not phase_status.status.is_successful():
                return False
        return True

    def _should_apply_compensation(
        self, phase_name: str, compensation_type: CompensationType
    ) -> bool:
        """Determine if compensation should be applied to phase."""
        # Apply compensation to all committed phases by default
        return True

    def _update_performance_metrics(
        self,
        phase_type: PhaseType,
        phase_metrics: Dict[str, float],
        ai_usage: Dict[str, Any],
    ) -> None:
        """Update aggregate performance metrics."""
        # Store phase-specific metrics
        phase_key = f"phase_{phase_type.value}"
        self.performance_metrics[
            f"{phase_key}_duration_ms"
        ] = phase_metrics.get("duration_ms", 0)
        self.performance_metrics[f"{phase_key}_events"] = phase_metrics.get(
            "events_processed", 0
        )

        # Update aggregate metrics
        self.performance_metrics["events_processed"] += phase_metrics.get(
            "events_processed", 0
        )

        if ai_usage:
            self.performance_metrics["ai_operations_count"] += 1
            ai_cost = Decimal(str(ai_usage.get("total_cost", "0.00")))
            self.performance_metrics["total_ai_cost"] += ai_cost

    def _create_compensated_pipeline_result(self) -> None:
        """Create pipeline result for compensated turn."""
        # Get results for completed phases
        phase_results = []
        for phase_type in PhaseType.get_all_phases_ordered():
            phase_status = self.phase_statuses[phase_type]
            if phase_status.status.is_successful():
                phase_result = PhaseResult.create_successful(
                    phase_type=phase_type, phase_status=phase_status
                )
            else:
                phase_result = PhaseResult.create_failed(
                    phase_type=phase_type,
                    phase_status=phase_status,
                    error_details={"compensated": True},
                )
            phase_results.append(phase_result)

        total_execution_time = (self.completed_at or datetime.now()) - (
            self.started_at or self.created_at
        )

        saga_actions = [
            action.compensation_type.value
            for action in self.compensation_actions
        ]

        self.pipeline_result = PipelineResult.create_failed(
            turn_id=self.turn_id.turn_uuid,
            phase_results=phase_results,
            total_execution_time=total_execution_time,
            error_summary={"compensated": True, "saga_actions": saga_actions},
            saga_actions_taken=saga_actions,
            metadata={
                "compensation_summary": {
                    "total_actions": len(self.compensation_actions),
                    "successful_actions": len(
                        [
                            a
                            for a in self.compensation_actions
                            if a.status == "completed"
                        ]
                    ),
                }
            },
        )

    def _record_audit_event(
        self, event_type: str, event_data: Dict[str, Any]
    ) -> None:
        """Record event in audit trail."""
        audit_event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "turn_id": str(self.turn_id.turn_uuid),
            "turn_state": self.state.value,
            "version": self.version,
            "data": event_data,
        }
        self.audit_trail.append(audit_event)

    def _generate_domain_event(
        self, event_type: str, event_data: Dict[str, Any]
    ) -> None:
        """Generate domain event for external consumption."""
        domain_event = {
            "event_id": str(uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "aggregate_id": str(self.turn_id.turn_uuid),
            "aggregate_type": "Turn",
            "version": self.version,
            "data": event_data,
        }
        self.events_generated.append(domain_event)

    # Query methods

    def get_current_phase_status(self) -> Optional[PhaseStatus]:
        """Get status of currently executing phase."""
        if self.current_phase:
            return self.phase_statuses.get(self.current_phase)
        return None

    def get_completed_phases(self) -> List[PhaseType]:
        """Get list of successfully completed phases."""
        return [
            phase_type
            for phase_type, status in self.phase_statuses.items()
            if status.status.is_successful()
        ]

    def get_failed_phases(self) -> List[PhaseType]:
        """Get list of failed phases."""
        return [
            phase_type
            for phase_type, status in self.phase_statuses.items()
            if status.status.is_failure()
        ]

    def get_pending_compensations(self) -> List[CompensationAction]:
        """Get list of pending compensation actions."""
        return [
            action
            for action in self.compensation_actions
            if action.status == "pending"
        ]

    def get_execution_time(self) -> Optional[timedelta]:
        """Get current execution time."""
        if self.started_at:
            end_time = self.completed_at or datetime.now()
            return end_time - self.started_at
        return None

    def is_overdue(self) -> bool:
        """Check if turn execution is overdue."""
        if not self.started_at or self.state.is_terminal():
            return False

        elapsed = datetime.now() - self.started_at
        max_time = timedelta(
            milliseconds=self.configuration.max_execution_time_ms
        )

        return elapsed > max_time

    def get_completion_percentage(self) -> float:
        """Get overall completion percentage."""
        if self.pipeline_result:
            return self.pipeline_result.get_completion_percentage()

        completed_phases = len(self.get_completed_phases())
        total_phases = len(PhaseType.get_all_phases_ordered())

        return completed_phases / total_phases

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        execution_time = self.get_execution_time()

        return {
            "turn_id": str(self.turn_id.turn_uuid),
            "state": self.state.value,
            "completion_percentage": self.get_completion_percentage() * 100,
            "execution_time_seconds": (
                execution_time.total_seconds() if execution_time else None
            ),
            "phases_completed": len(self.get_completed_phases()),
            "phases_failed": len(self.get_failed_phases()),
            "compensation_actions": len(self.compensation_actions),
            "events_processed": self.performance_metrics.get(
                "events_processed", 0
            ),
            "ai_operations": self.performance_metrics.get(
                "ai_operations_count", 0
            ),
            "total_ai_cost": float(
                self.performance_metrics.get("total_ai_cost", 0)
            ),
            "is_overdue": self.is_overdue(),
        }

    @classmethod
    def create(
        cls,
        turn_id: TurnId,
        configuration: TurnConfiguration,
        participants: List[str],
    ) -> "Turn":
        """
        Create a new Turn with proper initialization.

        Args:
            turn_id: Unique turn identifier
            configuration: Turn execution configuration
            participants: List of participant agent IDs

        Returns:
            New Turn instance in CREATED state
        """
        # Create configuration with participants if not present
        if (
            not hasattr(configuration, "participants")
            or not configuration.participants
        ):
            # Create new configuration with participants
            configuration = TurnConfiguration(
                **{
                    field.name: getattr(configuration, field.name)
                    for field in configuration.__dataclass_fields__.values()
                },
                participants=participants,
            )

        return cls(
            turn_id=turn_id,
            configuration=configuration,
            state=TurnState.CREATED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def __str__(self) -> str:
        """String representation for general use."""
        return (
            f"Turn({self.turn_id.to_short_string()}, {self.state.value}, "
            f"{self.get_completion_percentage() * 100:.0f}%)"
        )

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"Turn(id={self.turn_id.turn_uuid}, state={self.state}, "
            f"current_phase={self.current_phase}, version={self.version})"
        )
