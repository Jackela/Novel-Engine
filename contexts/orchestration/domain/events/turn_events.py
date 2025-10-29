#!/usr/bin/env python3
"""
Turn Lifecycle Domain Events

Domain events for turn creation, state transitions, and completion
with comprehensive event data for event sourcing and integration.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from ..value_objects import TurnConfiguration, TurnId


@dataclass(frozen=True)
class TurnCreated:
    """
    Domain event fired when a new turn is created.

    Signals turn initialization and configuration setup
    for downstream processing and notification systems.
    """

    event_id: UUID
    timestamp: datetime
    turn_id: UUID
    turn_configuration: Dict[str, Any]
    participants: List[str]
    estimated_duration_ms: int
    estimated_ai_cost: Optional[str]  # Decimal as string
    campaign_id: Optional[UUID]
    metadata: Dict[str, Any]

    @classmethod
    def create(
        cls,
        turn_id: TurnId,
        configuration: TurnConfiguration,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "TurnCreated":
        """
        Create TurnCreated event from turn data.

        Args:
            turn_id: Turn identifier
            configuration: Turn execution configuration
            metadata: Additional event metadata

        Returns:
            TurnCreated domain event
        """
        return cls(
            event_id=uuid4(),
            timestamp=datetime.now(),
            turn_id=turn_id.turn_uuid,
            turn_configuration={
                "world_time_advance": configuration.world_time_advance,
                "ai_integration_enabled": configuration.ai_integration_enabled,
                "narrative_analysis_depth": configuration.narrative_analysis_depth,
                "max_execution_time_ms": configuration.max_execution_time_ms,
                "rollback_enabled": configuration.rollback_enabled,
            },
            participants=configuration.participants,
            estimated_duration_ms=configuration.get_total_phase_timeout(),
            estimated_ai_cost=(
                str(configuration.get_estimated_ai_cost())
                if configuration.get_estimated_ai_cost()
                else None
            ),
            campaign_id=turn_id.campaign_id,
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class TurnPlanningStarted:
    """
    Domain event fired when turn enters planning state.

    Indicates turn is ready for resource allocation,
    dependency resolution, and execution preparation.
    """

    event_id: UUID
    timestamp: datetime
    turn_id: UUID
    planning_context: Dict[str, Any]
    participant_count: int
    phases_planned: List[str]
    saga_enabled: bool
    metadata: Dict[str, Any]

    @classmethod
    def create(
        cls,
        turn_id: UUID,
        planning_context: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "TurnPlanningStarted":
        """
        Create TurnPlanningStarted event.

        Args:
            turn_id: Turn identifier
            planning_context: Planning execution context
            metadata: Additional event metadata

        Returns:
            TurnPlanningStarted domain event
        """
        return cls(
            event_id=uuid4(),
            timestamp=datetime.now(),
            turn_id=turn_id,
            planning_context=planning_context,
            participant_count=planning_context.get("participant_count", 0),
            phases_planned=planning_context.get("phases_planned", []),
            saga_enabled=planning_context.get("saga_enabled", False),
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class TurnExecutionStarted:
    """
    Domain event fired when turn execution begins.

    Marks start of pipeline execution with first phase
    and performance monitoring initialization.
    """

    event_id: UUID
    timestamp: datetime
    turn_id: UUID
    started_at: datetime
    first_phase: str
    estimated_completion: datetime
    execution_timeout_ms: int
    performance_targets: Dict[str, float]
    metadata: Dict[str, Any]

    @classmethod
    def create(
        cls,
        turn_id: UUID,
        started_at: datetime,
        first_phase: str,
        estimated_completion: datetime,
        execution_timeout_ms: int = 30000,
        performance_targets: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "TurnExecutionStarted":
        """
        Create TurnExecutionStarted event.

        Args:
            turn_id: Turn identifier
            started_at: Execution start timestamp
            first_phase: Name of first pipeline phase
            estimated_completion: Estimated completion time
            execution_timeout_ms: Maximum execution time
            performance_targets: Performance expectations
            metadata: Additional event metadata

        Returns:
            TurnExecutionStarted domain event
        """
        return cls(
            event_id=uuid4(),
            timestamp=datetime.now(),
            turn_id=turn_id,
            started_at=started_at,
            first_phase=first_phase,
            estimated_completion=estimated_completion,
            execution_timeout_ms=execution_timeout_ms,
            performance_targets=performance_targets or {},
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class TurnCompleted:
    """
    Domain event fired when turn completes successfully.

    Contains comprehensive execution results, performance
    metrics, and success indicators for analytics.
    """

    event_id: UUID
    timestamp: datetime
    turn_id: UUID
    completed_at: datetime
    execution_time_seconds: float
    performance_summary: Dict[str, Any]
    phases_completed: int
    events_processed: int
    ai_operations_count: int
    total_ai_cost: str  # Decimal as string
    success_metrics: Dict[str, float]
    metadata: Dict[str, Any]

    @classmethod
    def create(
        cls,
        turn_id: UUID,
        completed_at: datetime,
        execution_time_seconds: float,
        performance_summary: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "TurnCompleted":
        """
        Create TurnCompleted event.

        Args:
            turn_id: Turn identifier
            completed_at: Completion timestamp
            execution_time_seconds: Total execution duration
            performance_summary: Comprehensive performance data
            metadata: Additional event metadata

        Returns:
            TurnCompleted domain event
        """
        return cls(
            event_id=uuid4(),
            timestamp=datetime.now(),
            turn_id=turn_id,
            completed_at=completed_at,
            execution_time_seconds=execution_time_seconds,
            performance_summary=performance_summary,
            phases_completed=performance_summary.get("phases_completed", 0),
            events_processed=performance_summary.get("events_processed", 0),
            ai_operations_count=performance_summary.get("ai_operations", 0),
            total_ai_cost=str(performance_summary.get("total_ai_cost", "0.00")),
            success_metrics={
                "completion_percentage": performance_summary.get(
                    "completion_percentage", 0
                ),
                "performance_score": performance_summary.get("performance_score", 0),
                "resource_efficiency": performance_summary.get(
                    "resource_efficiency", 0
                ),
            },
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class TurnFailed:
    """
    Domain event fired when turn fails permanently.

    Contains failure analysis, error details, and
    context for debugging and monitoring systems.
    """

    event_id: UUID
    timestamp: datetime
    turn_id: UUID
    failed_at: datetime
    error_message: str
    error_summary: Dict[str, Any]
    failed_phases: List[str]
    completed_phases: List[str]
    compensation_attempted: bool
    execution_time_seconds: Optional[float]
    failure_metrics: Dict[str, Any]
    metadata: Dict[str, Any]

    @classmethod
    def create(
        cls,
        turn_id: UUID,
        failed_at: datetime,
        error_message: str,
        error_summary: Dict[str, Any],
        execution_time_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "TurnFailed":
        """
        Create TurnFailed event.

        Args:
            turn_id: Turn identifier
            failed_at: Failure timestamp
            error_message: Primary error message
            error_summary: Detailed error analysis
            execution_time_seconds: Execution time until failure
            metadata: Additional event metadata

        Returns:
            TurnFailed domain event
        """
        return cls(
            event_id=uuid4(),
            timestamp=datetime.now(),
            turn_id=turn_id,
            failed_at=failed_at,
            error_message=error_message,
            error_summary=error_summary,
            failed_phases=error_summary.get("failed_phases", []),
            completed_phases=error_summary.get("completed_phases", []),
            compensation_attempted=error_summary.get("compensation_attempted", False),
            execution_time_seconds=execution_time_seconds,
            failure_metrics={
                "completion_percentage": error_summary.get("completion_percentage", 0),
                "phases_attempted": error_summary.get("phases_attempted", 0),
                "compensation_success_rate": error_summary.get(
                    "compensation_success_rate", 0
                ),
            },
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class TurnCompensationCompleted:
    """
    Domain event fired when saga compensation completes.

    Indicates successful rollback and recovery after
    failure with comprehensive compensation results.
    """

    event_id: UUID
    timestamp: datetime
    turn_id: UUID
    completed_at: datetime
    compensation_summary: Dict[str, Any]
    total_compensation_actions: int
    successful_actions: int
    failed_actions: int
    rollback_phases: List[str]
    recovery_time_seconds: float
    compensation_cost: Optional[str]  # Decimal as string
    metadata: Dict[str, Any]

    @classmethod
    def create(
        cls,
        turn_id: UUID,
        completed_at: datetime,
        compensation_summary: Dict[str, Any],
        recovery_time_seconds: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "TurnCompensationCompleted":
        """
        Create TurnCompensationCompleted event.

        Args:
            turn_id: Turn identifier
            completed_at: Compensation completion timestamp
            compensation_summary: Summary of compensation actions
            recovery_time_seconds: Time to complete recovery
            metadata: Additional event metadata

        Returns:
            TurnCompensationCompleted domain event
        """
        total_actions = compensation_summary.get("total_actions", 0)
        successful_actions = compensation_summary.get("successful_actions", 0)

        return cls(
            event_id=uuid4(),
            timestamp=datetime.now(),
            turn_id=turn_id,
            completed_at=completed_at,
            compensation_summary=compensation_summary,
            total_compensation_actions=total_actions,
            successful_actions=successful_actions,
            failed_actions=total_actions - successful_actions,
            rollback_phases=compensation_summary.get("rollback_phases", []),
            recovery_time_seconds=recovery_time_seconds,
            compensation_cost=str(
                compensation_summary.get("compensation_cost", "0.00")
            ),
            metadata=metadata or {},
        )
