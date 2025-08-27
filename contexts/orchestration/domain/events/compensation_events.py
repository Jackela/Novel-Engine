#!/usr/bin/env python3
"""
Compensation Domain Events

Domain events for saga compensation lifecycle including
compensation initiation, action completion, and recovery.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from ..value_objects import CompensationType


@dataclass(frozen=True)
class CompensationInitiated:
    """
    Domain event fired when saga compensation begins.
    
    Signals start of rollback operations with comprehensive
    compensation plan and execution strategy.
    """
    event_id: UUID
    timestamp: datetime
    turn_id: UUID
    failed_phase: str
    compensation_actions: List[Dict[str, Any]]
    committed_phases: List[str]
    rollback_strategy: str
    estimated_recovery_time_ms: int
    total_compensation_cost: Optional[str]  # Decimal as string
    requires_manual_approval: bool
    compensation_priority: int  # 1-10 scale
    metadata: Dict[str, Any]
    
    @classmethod
    def create(
        cls,
        turn_id: UUID,
        failed_phase: str,
        compensation_actions: List[Dict[str, Any]],
        committed_phases: List[str],
        rollback_strategy: str = "reverse_order",
        estimated_recovery_time_ms: int = 15000,
        total_compensation_cost: Optional[str] = None,
        compensation_priority: int = 5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'CompensationInitiated':
        """
        Create CompensationInitiated event.
        
        Args:
            turn_id: Turn identifier requiring compensation
            failed_phase: Phase that failed triggering compensation
            compensation_actions: List of compensation actions to execute
            committed_phases: Phases that were committed and need rollback
            rollback_strategy: Strategy for rollback execution
            estimated_recovery_time_ms: Estimated time for full recovery
            total_compensation_cost: Estimated cost of all compensations
            compensation_priority: Overall compensation priority
            metadata: Additional event metadata
            
        Returns:
            CompensationInitiated domain event
        """
        # Check if any action requires manual approval
        requires_manual_approval = any(
            action.get('requires_manual_approval', False)
            for action in compensation_actions
        )
        
        return cls(
            event_id=uuid4(),
            timestamp=datetime.now(),
            turn_id=turn_id,
            failed_phase=failed_phase,
            compensation_actions=compensation_actions,
            committed_phases=committed_phases,
            rollback_strategy=rollback_strategy,
            estimated_recovery_time_ms=estimated_recovery_time_ms,
            total_compensation_cost=total_compensation_cost,
            requires_manual_approval=requires_manual_approval,
            compensation_priority=compensation_priority,
            metadata=metadata or {}
        )


@dataclass(frozen=True)  
class CompensationActionCompleted:
    """
    Domain event fired when individual compensation action completes.
    
    Tracks progress of saga compensation with detailed
    action results and remaining compensation work.
    """
    event_id: UUID
    timestamp: datetime
    turn_id: UUID
    action_id: UUID
    compensation_type: str
    target_phase: str
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    execution_results: Dict[str, Any]
    actual_cost: Optional[str]  # Decimal as string
    rollback_data_processed: Dict[str, Any]
    entities_affected: List[str]
    success_metrics: Dict[str, Any]
    remaining_actions: int
    compensation_progress_percentage: float
    metadata: Dict[str, Any]
    
    @classmethod
    def create(
        cls,
        turn_id: UUID,
        action_id: UUID,
        compensation_type: CompensationType,
        target_phase: str,
        started_at: datetime,
        completed_at: datetime,
        execution_results: Dict[str, Any],
        actual_cost: Optional[str] = None,
        rollback_data_processed: Optional[Dict[str, Any]] = None,
        entities_affected: Optional[List[str]] = None,
        remaining_actions: int = 0,
        compensation_progress_percentage: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'CompensationActionCompleted':
        """
        Create CompensationActionCompleted event.
        
        Args:
            turn_id: Turn identifier
            action_id: Completed compensation action ID
            compensation_type: Type of compensation performed
            target_phase: Phase that was compensated
            started_at: Action start timestamp
            completed_at: Action completion timestamp
            execution_results: Results of compensation execution
            actual_cost: Actual cost incurred
            rollback_data_processed: Data that was rolled back
            entities_affected: Entities affected by compensation
            remaining_actions: Number of remaining compensation actions
            compensation_progress_percentage: Overall compensation progress
            metadata: Additional event metadata
            
        Returns:
            CompensationActionCompleted domain event
        """
        duration = completed_at - started_at
        duration_ms = int(duration.total_seconds() * 1000)
        
        # Calculate success metrics
        success_metrics = {
            'execution_success': execution_results.get('success', False),
            'rollback_completeness': cls._calculate_rollback_completeness(
                rollback_data_processed or {}
            ),
            'performance_score': cls._calculate_performance_score(
                duration_ms, compensation_type
            ),
            'entities_restored': len(entities_affected or []),
            'data_integrity_maintained': execution_results.get('data_integrity', True)
        }
        
        return cls(
            event_id=uuid4(),
            timestamp=datetime.now(),
            turn_id=turn_id,
            action_id=action_id,
            compensation_type=compensation_type.value,
            target_phase=target_phase,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            execution_results=execution_results,
            actual_cost=actual_cost,
            rollback_data_processed=rollback_data_processed or {},
            entities_affected=entities_affected or [],
            success_metrics=success_metrics,
            remaining_actions=remaining_actions,
            compensation_progress_percentage=compensation_progress_percentage,
            metadata=metadata or {}
        )
    
    @staticmethod
    def _calculate_rollback_completeness(rollback_data: Dict[str, Any]) -> float:
        """Calculate rollback completeness score (0.0-1.0)."""
        if not rollback_data:
            return 0.0
        
        # Check key rollback indicators
        completeness_indicators = {
            'world_state_restored': rollback_data.get('world_state_restored', False),
            'events_removed': rollback_data.get('events_removed', False),
            'entities_restored': rollback_data.get('entities_restored', False),
            'relationships_maintained': rollback_data.get('relationships_maintained', True)
        }
        
        completed_count = sum(1 for indicator in completeness_indicators.values() if indicator)
        total_indicators = len(completeness_indicators)
        
        return completed_count / total_indicators if total_indicators > 0 else 0.0
    
    @staticmethod
    def _calculate_performance_score(duration_ms: int, compensation_type: CompensationType) -> float:
        """Calculate compensation performance score (0.0-1.0)."""
        # Expected durations for different compensation types (in ms)
        expected_durations = {
            CompensationType.ROLLBACK_WORLD_STATE: 10000,  # 10 seconds
            CompensationType.INVALIDATE_SUBJECTIVE_BRIEFS: 2000,  # 2 seconds
            CompensationType.CANCEL_INTERACTIONS: 5000,  # 5 seconds
            CompensationType.REMOVE_EVENTS: 8000,  # 8 seconds
            CompensationType.REVERT_NARRATIVE_CHANGES: 6000,  # 6 seconds
            CompensationType.NOTIFY_PARTICIPANTS: 1000,  # 1 second
            CompensationType.LOG_FAILURE: 500,  # 0.5 seconds
            CompensationType.TRIGGER_MANUAL_REVIEW: 200  # 0.2 seconds
        }
        
        expected_duration = expected_durations.get(compensation_type, 5000)
        
        # Score based on how close to expected duration
        if duration_ms <= expected_duration:
            # Bonus for faster execution
            return 1.0 + (expected_duration - duration_ms) / expected_duration * 0.2
        else:
            # Penalty for slower execution
            return max(0.1, expected_duration / duration_ms)


@dataclass(frozen=True)
class CompensationActionFailed:
    """
    Domain event fired when compensation action fails.
    
    Indicates compensation failure with error analysis
    and escalation requirements for manual intervention.
    """
    event_id: UUID
    timestamp: datetime
    turn_id: UUID
    action_id: UUID
    compensation_type: str
    target_phase: str
    started_at: datetime
    failed_at: datetime
    duration_ms: int
    error_message: str
    error_details: Dict[str, Any]
    retry_count: int
    max_retries: int
    can_retry: bool
    requires_manual_intervention: bool
    partial_completion: Dict[str, Any]
    failure_impact: Dict[str, Any]
    escalation_required: bool
    metadata: Dict[str, Any]
    
    @classmethod
    def create(
        cls,
        turn_id: UUID,
        action_id: UUID,
        compensation_type: CompensationType,
        target_phase: str,
        started_at: datetime,
        failed_at: datetime,
        error_message: str,
        error_details: Dict[str, Any],
        retry_count: int = 0,
        max_retries: int = 3,
        partial_completion: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'CompensationActionFailed':
        """
        Create CompensationActionFailed event.
        
        Args:
            turn_id: Turn identifier
            action_id: Failed compensation action ID
            compensation_type: Type of compensation that failed
            target_phase: Phase that was being compensated
            started_at: Action start timestamp
            failed_at: Action failure timestamp
            error_message: Primary error message
            error_details: Detailed error information
            retry_count: Current retry attempt count
            max_retries: Maximum retry attempts allowed
            partial_completion: Any partial results achieved
            metadata: Additional event metadata
            
        Returns:
            CompensationActionFailed domain event
        """
        duration = failed_at - started_at
        duration_ms = int(duration.total_seconds() * 1000)
        
        can_retry = retry_count < max_retries
        
        # Determine if manual intervention is required
        requires_manual_intervention = cls._requires_manual_intervention(
            compensation_type, error_details, retry_count, max_retries
        )
        
        # Analyze failure impact
        failure_impact = {
            'severity': cls._determine_failure_severity(compensation_type, error_details),
            'affects_other_compensations': cls._affects_other_compensations(
                compensation_type, error_details
            ),
            'partial_rollback_possible': bool(partial_completion),
            'data_consistency_at_risk': cls._data_consistency_at_risk(error_details),
            'estimated_manual_effort_hours': cls._estimate_manual_effort(
                compensation_type, error_details
            )
        }
        
        escalation_required = (
            requires_manual_intervention or
            failure_impact['severity'] == 'critical' or
            not can_retry
        )
        
        return cls(
            event_id=uuid4(),
            timestamp=datetime.now(),
            turn_id=turn_id,
            action_id=action_id,
            compensation_type=compensation_type.value,
            target_phase=target_phase,
            started_at=started_at,
            failed_at=failed_at,
            duration_ms=duration_ms,
            error_message=error_message,
            error_details=error_details,
            retry_count=retry_count,
            max_retries=max_retries,
            can_retry=can_retry,
            requires_manual_intervention=requires_manual_intervention,
            partial_completion=partial_completion or {},
            failure_impact=failure_impact,
            escalation_required=escalation_required,
            metadata=metadata or {}
        )
    
    @staticmethod
    def _requires_manual_intervention(
        compensation_type: CompensationType,
        error_details: Dict[str, Any],
        retry_count: int,
        max_retries: int
    ) -> bool:
        """Determine if manual intervention is required."""
        # Always require manual intervention for destructive rollbacks
        if compensation_type.is_destructive() and retry_count >= max_retries:
            return True
        
        # Check for error types requiring intervention
        manual_intervention_errors = {
            'permission_denied',
            'authentication_failed',
            'data_corruption',
            'external_system_unavailable',
            'resource_locked'
        }
        
        return any(
            error in error_details.get('error_type', '')
            for error in manual_intervention_errors
        )
    
    @staticmethod
    def _determine_failure_severity(
        compensation_type: CompensationType,
        error_details: Dict[str, Any]
    ) -> str:
        """Determine failure severity level."""
        # Critical failures
        if error_details.get('data_corruption', False):
            return 'critical'
        
        if compensation_type.is_destructive():
            return 'high'
        
        return error_details.get('severity', 'medium')
    
    @staticmethod
    def _affects_other_compensations(
        compensation_type: CompensationType,
        error_details: Dict[str, Any]
    ) -> bool:
        """Check if failure affects other compensation actions."""
        # World state rollback failures affect everything
        if compensation_type == CompensationType.ROLLBACK_WORLD_STATE:
            return True
        
        # System-wide errors affect other actions
        system_wide_errors = {
            'database_connection_lost',
            'system_resource_exhausted',
            'external_system_unavailable'
        }
        
        return any(
            error in error_details.get('error_type', '')
            for error in system_wide_errors
        )
    
    @staticmethod
    def _data_consistency_at_risk(error_details: Dict[str, Any]) -> bool:
        """Check if data consistency is at risk."""
        consistency_risks = {
            'partial_rollback',
            'transaction_failed',
            'data_corruption',
            'referential_integrity_violation'
        }
        
        return any(
            risk in error_details.get('error_type', '')
            for risk in consistency_risks
        )
    
    @staticmethod
    def _estimate_manual_effort(
        compensation_type: CompensationType,
        error_details: Dict[str, Any]
    ) -> float:
        """Estimate manual effort required in hours."""
        # Base effort by compensation type
        base_efforts = {
            CompensationType.ROLLBACK_WORLD_STATE: 2.0,
            CompensationType.REMOVE_EVENTS: 1.5,
            CompensationType.CANCEL_INTERACTIONS: 1.0,
            CompensationType.REVERT_NARRATIVE_CHANGES: 0.5,
            CompensationType.INVALIDATE_SUBJECTIVE_BRIEFS: 0.25,
            CompensationType.NOTIFY_PARTICIPANTS: 0.1,
            CompensationType.LOG_FAILURE: 0.05,
            CompensationType.TRIGGER_MANUAL_REVIEW: 0.25
        }
        
        base_effort = base_efforts.get(compensation_type, 1.0)
        
        # Adjust based on error complexity
        if error_details.get('data_corruption', False):
            base_effort *= 3.0
        elif error_details.get('severity') == 'high':
            base_effort *= 1.5
        
        return base_effort