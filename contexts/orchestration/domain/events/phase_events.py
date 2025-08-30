#!/usr/bin/env python3
"""
Phase Execution Domain Events

Domain events for pipeline phase lifecycle including
phase starts, completions, failures, and transitions.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from ..value_objects import PhaseType


@dataclass(frozen=True)
class PhaseStarted:
    """
    Domain event fired when pipeline phase begins execution.

    Marks start of phase processing with timing and
    resource allocation information.
    """

    event_id: UUID
    timestamp: datetime
    turn_id: UUID
    phase_type: str
    phase_order: int
    started_at: datetime
    timeout_ms: int
    previous_phase: Optional[str]
    estimated_events: int
    ai_integration_enabled: bool
    metadata: Dict[str, Any]

    @classmethod
    def create(
        cls,
        turn_id: UUID,
        phase_type: PhaseType,
        started_at: datetime,
        timeout_ms: int = 10000,
        previous_phase: Optional[PhaseType] = None,
        estimated_events: int = 0,
        ai_integration_enabled: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "PhaseStarted":
        """
        Create PhaseStarted event.

        Args:
            turn_id: Turn identifier
            phase_type: Type of phase being started
            started_at: Phase start timestamp
            timeout_ms: Phase execution timeout
            previous_phase: Previously completed phase
            estimated_events: Estimated events to process
            ai_integration_enabled: Whether AI is enabled for this phase
            metadata: Additional event metadata

        Returns:
            PhaseStarted domain event
        """
        return cls(
            event_id=uuid4(),
            timestamp=datetime.now(),
            turn_id=turn_id,
            phase_type=phase_type.value,
            phase_order=phase_type.get_phase_order(),
            started_at=started_at,
            timeout_ms=timeout_ms,
            previous_phase=previous_phase.value if previous_phase else None,
            estimated_events=estimated_events,
            ai_integration_enabled=ai_integration_enabled,
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class PhaseCompleted:
    """
    Domain event fired when pipeline phase completes successfully.

    Contains comprehensive phase execution results,
    performance metrics, and generated artifacts.
    """

    event_id: UUID
    timestamp: datetime
    turn_id: UUID
    phase_type: str
    phase_order: int
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    events_processed: int
    events_generated: int
    artifacts_created: int
    performance_metrics: Dict[str, float]
    ai_usage: Optional[Dict[str, Any]]
    next_phase: Optional[str]
    success_indicators: Dict[str, Any]
    metadata: Dict[str, Any]

    @classmethod
    def create(
        cls,
        turn_id: UUID,
        phase_type: PhaseType,
        started_at: datetime,
        completed_at: datetime,
        events_processed: int = 0,
        events_generated: int = 0,
        artifacts_created: int = 0,
        performance_metrics: Optional[Dict[str, float]] = None,
        ai_usage: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "PhaseCompleted":
        """
        Create PhaseCompleted event.

        Args:
            turn_id: Turn identifier
            phase_type: Type of completed phase
            started_at: Phase start timestamp
            completed_at: Phase completion timestamp
            events_processed: Number of events processed
            events_generated: Number of events generated
            artifacts_created: Number of artifacts created
            performance_metrics: Phase performance measurements
            ai_usage: AI service usage statistics
            metadata: Additional event metadata

        Returns:
            PhaseCompleted domain event
        """
        duration = completed_at - started_at
        duration_ms = int(duration.total_seconds() * 1000)

        next_phase = phase_type.get_next_phase()

        # Calculate success indicators
        success_indicators = {
            "completion_rate": 1.0,  # Successful completion
            "performance_score": cls._calculate_performance_score(
                duration_ms, events_processed, performance_metrics or {}
            ),
            "efficiency_ratio": (
                events_processed / duration_ms if duration_ms > 0 else 0
            ),
            "ai_cost_efficiency": cls._calculate_ai_efficiency(
                events_processed, ai_usage
            ),
        }

        return cls(
            event_id=uuid4(),
            timestamp=datetime.now(),
            turn_id=turn_id,
            phase_type=phase_type.value,
            phase_order=phase_type.get_phase_order(),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            events_processed=events_processed,
            events_generated=events_generated,
            artifacts_created=artifacts_created,
            performance_metrics=performance_metrics or {},
            ai_usage=ai_usage,
            next_phase=next_phase.value if next_phase else None,
            success_indicators=success_indicators,
            metadata=metadata or {},
        )

    @staticmethod
    def _calculate_performance_score(
        duration_ms: int, events_processed: int, performance_metrics: Dict[str, float]
    ) -> float:
        """Calculate phase performance score (0.0-1.0)."""
        # Base score on events per second
        if duration_ms > 0:
            events_per_second = (events_processed * 1000) / duration_ms
            base_score = min(
                1.0, events_per_second / 10.0
            )  # Normalize to 10 events/sec
        else:
            base_score = 0.5

        # Apply performance metric bonuses/penalties
        if performance_metrics.get("memory_efficiency", 0) > 0.8:
            base_score *= 1.1

        if performance_metrics.get("error_rate", 0) > 0.1:
            base_score *= 0.8

        return min(1.0, base_score)

    @staticmethod
    def _calculate_ai_efficiency(
        events_processed: int, ai_usage: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate AI cost efficiency."""
        if not ai_usage or events_processed == 0:
            return 0.0

        ai_cost = float(ai_usage.get("total_cost", 0))
        if ai_cost == 0:
            return 1.0

        # Events per dollar spent
        return min(1.0, events_processed / (ai_cost * 100))


@dataclass(frozen=True)
class PhaseFailed:
    """
    Domain event fired when pipeline phase fails.

    Contains failure analysis, error context, and
    compensation requirements for saga coordination.
    """

    event_id: UUID
    timestamp: datetime
    turn_id: UUID
    phase_type: str
    phase_order: int
    started_at: datetime
    failed_at: datetime
    duration_ms: int
    error_message: str
    error_code: Optional[str]
    error_details: Dict[str, Any]
    events_processed_before_failure: int
    partial_results: Dict[str, Any]
    compensation_required: bool
    compensation_priority: int  # 1-10 scale
    rollback_data_available: bool
    retry_possible: bool
    failure_impact: Dict[str, Any]
    metadata: Dict[str, Any]

    @classmethod
    def create(
        cls,
        turn_id: UUID,
        phase_type: PhaseType,
        started_at: datetime,
        failed_at: datetime,
        error_message: str,
        error_code: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        events_processed_before_failure: int = 0,
        partial_results: Optional[Dict[str, Any]] = None,
        compensation_required: bool = True,
        rollback_data_available: bool = True,
        retry_possible: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "PhaseFailed":
        """
        Create PhaseFailed event.

        Args:
            turn_id: Turn identifier
            phase_type: Type of failed phase
            started_at: Phase start timestamp
            failed_at: Phase failure timestamp
            error_message: Primary error message
            error_code: Optional error code
            error_details: Detailed error information
            events_processed_before_failure: Events processed before failure
            partial_results: Partial phase results if available
            compensation_required: Whether compensation is needed
            rollback_data_available: Whether rollback data exists
            retry_possible: Whether retry is possible
            metadata: Additional event metadata

        Returns:
            PhaseFailed domain event
        """
        duration = failed_at - started_at
        duration_ms = int(duration.total_seconds() * 1000)

        # Determine compensation priority based on phase and impact
        compensation_priority = cls._calculate_compensation_priority(
            phase_type, error_details or {}, events_processed_before_failure
        )

        # Analyze failure impact
        failure_impact = {
            "severity": cls._determine_failure_severity(
                phase_type, error_details or {}
            ),
            "affects_downstream_phases": cls._affects_downstream_phases(phase_type),
            "requires_human_intervention": cls._requires_human_intervention(
                error_details or {}
            ),
            "estimated_recovery_time_ms": cls._estimate_recovery_time(
                phase_type, compensation_priority
            ),
            "partial_progress_salvageable": events_processed_before_failure > 0,
        }

        return cls(
            event_id=uuid4(),
            timestamp=datetime.now(),
            turn_id=turn_id,
            phase_type=phase_type.value,
            phase_order=phase_type.get_phase_order(),
            started_at=started_at,
            failed_at=failed_at,
            duration_ms=duration_ms,
            error_message=error_message,
            error_code=error_code,
            error_details=error_details or {},
            events_processed_before_failure=events_processed_before_failure,
            partial_results=partial_results or {},
            compensation_required=compensation_required,
            compensation_priority=compensation_priority,
            rollback_data_available=rollback_data_available,
            retry_possible=retry_possible,
            failure_impact=failure_impact,
            metadata=metadata or {},
        )

    @staticmethod
    def _calculate_compensation_priority(
        phase_type: PhaseType, error_details: Dict[str, Any], events_processed: int
    ) -> int:
        """Calculate compensation priority (1-10, higher is more urgent)."""
        # Base priority on phase criticality
        phase_priorities = {
            PhaseType.WORLD_UPDATE: 9,  # Critical - affects game state
            PhaseType.EVENT_INTEGRATION: 8,  # High - affects event consistency
            PhaseType.INTERACTION_ORCHESTRATION: 6,  # Medium - affects player experience
            PhaseType.SUBJECTIVE_BRIEF: 4,  # Lower - affects AI quality
            PhaseType.NARRATIVE_INTEGRATION: 3,  # Lowest - affects story quality
        }

        base_priority = phase_priorities.get(phase_type, 5)

        # Adjust based on error severity
        if error_details.get("severity") == "critical":
            base_priority += 2
        elif error_details.get("severity") == "high":
            base_priority += 1

        # Adjust based on partial progress
        if events_processed > 0:
            base_priority += 1  # Higher priority to preserve work

        return min(10, max(1, base_priority))

    @staticmethod
    def _determine_failure_severity(
        phase_type: PhaseType, error_details: Dict[str, Any]
    ) -> str:
        """Determine failure severity level."""
        # Check for critical error indicators
        if error_details.get("data_corruption", False):
            return "critical"

        if error_details.get("system_resource_exhausted", False):
            return "critical"

        # Phase-specific severity
        if phase_type in {PhaseType.WORLD_UPDATE, PhaseType.EVENT_INTEGRATION}:
            return "high"

        return error_details.get("severity", "medium")

    @staticmethod
    def _affects_downstream_phases(phase_type: PhaseType) -> bool:
        """Check if phase failure affects downstream phases."""
        # Earlier phases affect more downstream phases
        return phase_type.get_phase_order() <= 3

    @staticmethod
    def _requires_human_intervention(error_details: Dict[str, Any]) -> bool:
        """Check if failure requires human intervention."""
        intervention_indicators = {
            "permission_denied",
            "authentication_failed",
            "resource_quota_exceeded",
            "data_corruption",
            "configuration_error",
        }

        return any(
            indicator in error_details.get("error_type", "")
            for indicator in intervention_indicators
        )

    @staticmethod
    def _estimate_recovery_time(
        phase_type: PhaseType, compensation_priority: int
    ) -> int:
        """Estimate recovery time in milliseconds."""
        # Base recovery time by phase complexity
        base_times = {
            PhaseType.WORLD_UPDATE: 5000,  # 5 seconds
            PhaseType.SUBJECTIVE_BRIEF: 3000,  # 3 seconds
            PhaseType.INTERACTION_ORCHESTRATION: 8000,  # 8 seconds
            PhaseType.EVENT_INTEGRATION: 4000,  # 4 seconds
            PhaseType.NARRATIVE_INTEGRATION: 6000,  # 6 seconds
        }

        base_time = base_times.get(phase_type, 5000)

        # Adjust based on compensation priority (higher priority = faster recovery)
        priority_multiplier = 1.5 - (compensation_priority / 20.0)  # 0.5x to 1.0x

        return int(base_time * priority_multiplier)
