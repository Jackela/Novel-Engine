#!/usr/bin/env python3
"""
Compensation Action Value Objects

Immutable value objects for saga pattern compensation including
action types, execution details, and reliability tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID


class CompensationType(Enum):
    """
    Enumeration of compensation action types for saga pattern.
    
    Defines the types of compensating actions that can be performed
    to rollback or correct failed pipeline phases.
    """
    ROLLBACK_WORLD_STATE = "rollback_world_state"
    INVALIDATE_SUBJECTIVE_BRIEFS = "invalidate_subjective_briefs"
    CANCEL_INTERACTIONS = "cancel_interactions"
    REMOVE_EVENTS = "remove_events"
    REVERT_NARRATIVE_CHANGES = "revert_narrative_changes"
    NOTIFY_PARTICIPANTS = "notify_participants"
    LOG_FAILURE = "log_failure"
    TRIGGER_MANUAL_REVIEW = "trigger_manual_review"
    
    def __str__(self) -> str:
        return self.value
    
    def get_display_name(self) -> str:
        """Get human-readable compensation action name."""
        names = {
            self.ROLLBACK_WORLD_STATE: "Rollback World State Changes",
            self.INVALIDATE_SUBJECTIVE_BRIEFS: "Invalidate Subjective Briefs",
            self.CANCEL_INTERACTIONS: "Cancel Active Interactions",
            self.REMOVE_EVENTS: "Remove Generated Events",
            self.REVERT_NARRATIVE_CHANGES: "Revert Narrative Modifications",
            self.NOTIFY_PARTICIPANTS: "Notify Affected Participants",
            self.LOG_FAILURE: "Log Failure Details",
            self.TRIGGER_MANUAL_REVIEW: "Trigger Manual Review Process"
        }
        return names[self]
    
    def get_severity(self) -> str:
        """Get severity level of compensation action."""
        severity_map = {
            self.ROLLBACK_WORLD_STATE: "critical",
            self.INVALIDATE_SUBJECTIVE_BRIEFS: "high", 
            self.CANCEL_INTERACTIONS: "high",
            self.REMOVE_EVENTS: "critical",
            self.REVERT_NARRATIVE_CHANGES: "medium",
            self.NOTIFY_PARTICIPANTS: "low",
            self.LOG_FAILURE: "low",
            self.TRIGGER_MANUAL_REVIEW: "medium"
        }
        return severity_map[self]
    
    def is_destructive(self) -> bool:
        """Check if compensation action is destructive to game state."""
        destructive_actions = {
            self.ROLLBACK_WORLD_STATE,
            self.REMOVE_EVENTS,
            self.CANCEL_INTERACTIONS
        }
        return self in destructive_actions
    
    def requires_confirmation(self) -> bool:
        """Check if action requires user confirmation."""
        confirmation_required = {
            self.ROLLBACK_WORLD_STATE,
            self.REMOVE_EVENTS,
            self.TRIGGER_MANUAL_REVIEW
        }
        return self in confirmation_required
    
    @classmethod
    def get_phase_compensations(cls, phase_name: str) -> List['CompensationType']:
        """Get appropriate compensations for failed phase."""
        phase_compensations = {
            "world_update": [
                cls.ROLLBACK_WORLD_STATE,
                cls.LOG_FAILURE,
                cls.NOTIFY_PARTICIPANTS
            ],
            "subjective_brief": [
                cls.INVALIDATE_SUBJECTIVE_BRIEFS,
                cls.LOG_FAILURE
            ],
            "interaction_orchestration": [
                cls.CANCEL_INTERACTIONS,
                cls.NOTIFY_PARTICIPANTS,
                cls.LOG_FAILURE
            ],
            "event_integration": [
                cls.REMOVE_EVENTS,
                cls.ROLLBACK_WORLD_STATE,
                cls.LOG_FAILURE
            ],
            "narrative_integration": [
                cls.REVERT_NARRATIVE_CHANGES,
                cls.LOG_FAILURE
            ]
        }
        return phase_compensations.get(phase_name, [cls.LOG_FAILURE])


@dataclass(frozen=True)
class CompensationAction:
    """
    Immutable value object representing a saga compensation action.
    
    Encapsulates complete compensation action details including type,
    execution parameters, timing, results, and audit information.
    
    Attributes:
        action_id: Unique identifier for the compensation action
        compensation_type: Type of compensation to perform
        target_phase: Phase that requires compensation
        turn_id: Turn being compensated
        triggered_at: When compensation was initiated
        completed_at: When compensation finished (if completed)
        status: Current execution status
        execution_parameters: Parameters for executing compensation
        execution_results: Results of compensation execution
        rollback_data: Data needed to perform rollback
        affected_entities: List of entities affected by compensation
        estimated_cost: Estimated cost of performing compensation
        actual_cost: Actual cost incurred during compensation
        priority: Execution priority (1-10, higher is more urgent)
        requires_manual_approval: Whether manual approval is needed
        approval_granted_at: When manual approval was granted
        approved_by: User who approved the compensation
        execution_timeout_ms: Maximum time allowed for execution
        retry_count: Number of retry attempts made
        max_retries: Maximum retry attempts allowed
        error_details: Details of any execution errors
        metadata: Additional compensation-specific information
        
    Business Rules:
        - Action ID must be unique
        - Compensation type must be valid for target phase
        - Destructive actions require confirmation
        - High-severity actions have shorter timeouts
        - Critical compensations cannot be skipped
        - Rollback data must be preserved for destructive actions
    """
    
    action_id: UUID
    compensation_type: CompensationType
    target_phase: str
    turn_id: UUID
    triggered_at: datetime
    
    # Execution tracking
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, executing, completed, failed, skipped
    execution_parameters: Dict[str, Any] = field(default_factory=dict)
    execution_results: Dict[str, Any] = field(default_factory=dict)
    
    # Rollback and recovery data
    rollback_data: Dict[str, Any] = field(default_factory=dict)
    affected_entities: List[str] = field(default_factory=list)
    
    # Cost and resource tracking  
    estimated_cost: Optional[Decimal] = None
    actual_cost: Optional[Decimal] = None
    
    # Priority and approval
    priority: int = 5  # 1-10 scale, higher is more urgent
    requires_manual_approval: bool = False
    approval_granted_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    
    # Execution configuration
    execution_timeout_ms: int = 10000  # 10 seconds default
    retry_count: int = 0
    max_retries: int = 3
    
    # Error handling
    error_details: Optional[Dict[str, Any]] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Class constants
    VALID_STATUSES = {"pending", "executing", "completed", "failed", "skipped"}
    DEFAULT_TIMEOUTS = {
        "rollback_world_state": 15000,  # 15 seconds
        "invalidate_subjective_briefs": 5000,  # 5 seconds
        "cancel_interactions": 8000,  # 8 seconds
        "remove_events": 12000,  # 12 seconds
        "revert_narrative_changes": 10000,  # 10 seconds
        "notify_participants": 3000,  # 3 seconds
        "log_failure": 2000,  # 2 seconds
        "trigger_manual_review": 1000  # 1 second
    }
    
    def __post_init__(self):
        """Validate compensation action structure and business rules."""
        # Validate status
        if self.status not in self.VALID_STATUSES:
            raise ValueError(f"Status must be one of {self.VALID_STATUSES}")
        
        # Validate priority
        if not 1 <= self.priority <= 10:
            raise ValueError("Priority must be between 1 and 10")
        
        # Validate retry configuration
        if self.retry_count < 0:
            raise ValueError("retry_count cannot be negative")
        
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        
        if self.retry_count > self.max_retries:
            raise ValueError("retry_count cannot exceed max_retries")
        
        # Validate execution timeout
        if self.execution_timeout_ms <= 0:
            raise ValueError("execution_timeout_ms must be positive")
        
        # Validate costs are non-negative
        if self.estimated_cost is not None and self.estimated_cost < 0:
            raise ValueError("estimated_cost cannot be negative")
        
        if self.actual_cost is not None and self.actual_cost < 0:
            raise ValueError("actual_cost cannot be negative")
        
        # Set default timeout if not provided
        if self.execution_timeout_ms == 10000:  # Default value
            default_timeout = self.DEFAULT_TIMEOUTS.get(
                self.compensation_type.value, 
                10000
            )
            object.__setattr__(self, 'execution_timeout_ms', default_timeout)
        
        # Set manual approval requirement for destructive actions
        if self.compensation_type.requires_confirmation():
            object.__setattr__(self, 'requires_manual_approval', True)
        
        # Set priority based on compensation severity
        if self.priority == 5:  # Default priority
            severity_priorities = {
                "critical": 9,
                "high": 7,
                "medium": 5,
                "low": 3
            }
            severity = self.compensation_type.get_severity()
            object.__setattr__(self, 'priority', severity_priorities.get(severity, 5))
    
    @classmethod
    def create_for_phase_failure(
        cls,
        action_id: UUID,
        turn_id: UUID,
        failed_phase: str,
        compensation_type: CompensationType,
        rollback_data: Optional[Dict[str, Any]] = None,
        affected_entities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'CompensationAction':
        """
        Create compensation action for phase failure.
        
        Args:
            action_id: Unique compensation action identifier
            turn_id: Turn requiring compensation
            failed_phase: Name of phase that failed
            compensation_type: Type of compensation to perform
            rollback_data: Data needed for rollback operations
            affected_entities: Entities affected by the failure
            metadata: Additional compensation context
            
        Returns:
            CompensationAction configured for phase failure
        """
        return cls(
            action_id=action_id,
            compensation_type=compensation_type,
            target_phase=failed_phase,
            turn_id=turn_id,
            triggered_at=datetime.now(),
            rollback_data=rollback_data or {},
            affected_entities=affected_entities or [],
            metadata=metadata or {}
        )
    
    @classmethod
    def create_rollback(
        cls,
        action_id: UUID,
        turn_id: UUID,
        target_phase: str,
        rollback_data: Dict[str, Any],
        affected_entities: List[str]
    ) -> 'CompensationAction':
        """
        Create world state rollback compensation.
        
        Args:
            action_id: Unique compensation action identifier
            turn_id: Turn requiring rollback
            target_phase: Phase to rollback
            rollback_data: Complete state rollback information
            affected_entities: All entities to rollback
            
        Returns:
            CompensationAction for world state rollback
        """
        return cls(
            action_id=action_id,
            compensation_type=CompensationType.ROLLBACK_WORLD_STATE,
            target_phase=target_phase,
            turn_id=turn_id,
            triggered_at=datetime.now(),
            rollback_data=rollback_data,
            affected_entities=affected_entities,
            priority=9,  # Critical priority
            requires_manual_approval=True
        )
    
    def start_execution(self, executor: Optional[str] = None) -> 'CompensationAction':
        """
        Mark compensation as started.
        
        Args:
            executor: Entity performing the compensation
            
        Returns:
            New CompensationAction in executing state
        """
        if self.status != "pending":
            raise ValueError(f"Cannot start execution from status: {self.status}")
        
        metadata = {**self.metadata}
        if executor:
            metadata['executor'] = executor
        
        return CompensationAction(
            action_id=self.action_id,
            compensation_type=self.compensation_type,
            target_phase=self.target_phase,
            turn_id=self.turn_id,
            triggered_at=self.triggered_at,
            completed_at=self.completed_at,
            status="executing",
            execution_parameters=self.execution_parameters,
            execution_results=self.execution_results,
            rollback_data=self.rollback_data,
            affected_entities=self.affected_entities,
            estimated_cost=self.estimated_cost,
            actual_cost=self.actual_cost,
            priority=self.priority,
            requires_manual_approval=self.requires_manual_approval,
            approval_granted_at=self.approval_granted_at,
            approved_by=self.approved_by,
            execution_timeout_ms=self.execution_timeout_ms,
            retry_count=self.retry_count,
            max_retries=self.max_retries,
            error_details=self.error_details,
            metadata=metadata
        )
    
    def complete_execution(
        self,
        results: Dict[str, Any],
        actual_cost: Optional[Decimal] = None
    ) -> 'CompensationAction':
        """
        Mark compensation as completed.
        
        Args:
            results: Results of compensation execution
            actual_cost: Actual cost incurred
            
        Returns:
            New CompensationAction in completed state
        """
        if self.status != "executing":
            raise ValueError(f"Cannot complete from status: {self.status}")
        
        return CompensationAction(
            action_id=self.action_id,
            compensation_type=self.compensation_type,
            target_phase=self.target_phase,
            turn_id=self.turn_id,
            triggered_at=self.triggered_at,
            completed_at=datetime.now(),
            status="completed",
            execution_parameters=self.execution_parameters,
            execution_results=results,
            rollback_data=self.rollback_data,
            affected_entities=self.affected_entities,
            estimated_cost=self.estimated_cost,
            actual_cost=actual_cost or self.actual_cost,
            priority=self.priority,
            requires_manual_approval=self.requires_manual_approval,
            approval_granted_at=self.approval_granted_at,
            approved_by=self.approved_by,
            execution_timeout_ms=self.execution_timeout_ms,
            retry_count=self.retry_count,
            max_retries=self.max_retries,
            error_details=self.error_details,
            metadata=self.metadata
        )
    
    def fail_execution(
        self,
        error_details: Dict[str, Any],
        can_retry: bool = True
    ) -> 'CompensationAction':
        """
        Mark compensation as failed.
        
        Args:
            error_details: Details of execution failure
            can_retry: Whether retry is possible
            
        Returns:
            New CompensationAction in failed state or with incremented retry
        """
        if self.status != "executing":
            raise ValueError(f"Cannot fail from status: {self.status}")
        
        # Check if retry is possible
        if can_retry and self.retry_count < self.max_retries:
            return CompensationAction(
                action_id=self.action_id,
                compensation_type=self.compensation_type,
                target_phase=self.target_phase,
                turn_id=self.turn_id,
                triggered_at=self.triggered_at,
                completed_at=self.completed_at,
                status="pending",  # Back to pending for retry
                execution_parameters=self.execution_parameters,
                execution_results=self.execution_results,
                rollback_data=self.rollback_data,
                affected_entities=self.affected_entities,
                estimated_cost=self.estimated_cost,
                actual_cost=self.actual_cost,
                priority=self.priority,
                requires_manual_approval=self.requires_manual_approval,
                approval_granted_at=self.approval_granted_at,
                approved_by=self.approved_by,
                execution_timeout_ms=self.execution_timeout_ms,
                retry_count=self.retry_count + 1,
                max_retries=self.max_retries,
                error_details=error_details,
                metadata=self.metadata
            )
        else:
            # Failed permanently
            return CompensationAction(
                action_id=self.action_id,
                compensation_type=self.compensation_type,
                target_phase=self.target_phase,
                turn_id=self.turn_id,
                triggered_at=self.triggered_at,
                completed_at=datetime.now(),
                status="failed",
                execution_parameters=self.execution_parameters,
                execution_results=self.execution_results,
                rollback_data=self.rollback_data,
                affected_entities=self.affected_entities,
                estimated_cost=self.estimated_cost,
                actual_cost=self.actual_cost,
                priority=self.priority,
                requires_manual_approval=self.requires_manual_approval,
                approval_granted_at=self.approval_granted_at,
                approved_by=self.approved_by,
                execution_timeout_ms=self.execution_timeout_ms,
                retry_count=self.retry_count,
                max_retries=self.max_retries,
                error_details=error_details,
                metadata=self.metadata
            )
    
    def grant_approval(self, approved_by: str) -> 'CompensationAction':
        """
        Grant manual approval for compensation.
        
        Args:
            approved_by: User granting approval
            
        Returns:
            New CompensationAction with approval granted
        """
        if not self.requires_manual_approval:
            raise ValueError("Compensation does not require manual approval")
        
        if self.approval_granted_at is not None:
            raise ValueError("Approval already granted")
        
        return CompensationAction(
            action_id=self.action_id,
            compensation_type=self.compensation_type,
            target_phase=self.target_phase,
            turn_id=self.turn_id,
            triggered_at=self.triggered_at,
            completed_at=self.completed_at,
            status=self.status,
            execution_parameters=self.execution_parameters,
            execution_results=self.execution_results,
            rollback_data=self.rollback_data,
            affected_entities=self.affected_entities,
            estimated_cost=self.estimated_cost,
            actual_cost=self.actual_cost,
            priority=self.priority,
            requires_manual_approval=self.requires_manual_approval,
            approval_granted_at=datetime.now(),
            approved_by=approved_by,
            execution_timeout_ms=self.execution_timeout_ms,
            retry_count=self.retry_count,
            max_retries=self.max_retries,
            error_details=self.error_details,
            metadata=self.metadata
        )
    
    def is_ready_to_execute(self) -> bool:
        """Check if compensation is ready for execution."""
        if self.status != "pending":
            return False
        
        if self.requires_manual_approval and self.approval_granted_at is None:
            return False
        
        return True
    
    def is_terminal(self) -> bool:
        """Check if compensation is in terminal state."""
        return self.status in {"completed", "failed", "skipped"}
    
    def is_overdue(self) -> bool:
        """Check if compensation execution is overdue."""
        if self.status != "executing":
            return False
        
        if not self.triggered_at:
            return False
        
        elapsed = datetime.now() - self.triggered_at
        timeout_seconds = self.execution_timeout_ms / 1000.0
        
        return elapsed.total_seconds() > timeout_seconds
    
    def get_execution_time(self) -> Optional[timedelta]:
        """Get compensation execution duration."""
        if self.completed_at and self.triggered_at:
            return self.completed_at - self.triggered_at
        elif self.status == "executing" and self.triggered_at:
            return datetime.now() - self.triggered_at
        return None
    
    def get_estimated_duration(self) -> timedelta:
        """Get estimated execution duration."""
        return timedelta(milliseconds=self.execution_timeout_ms)
    
    def get_display_summary(self) -> str:
        """Get human-readable compensation summary."""
        action_name = self.compensation_type.get_display_name()
        status = self.status.title()
        
        if self.is_terminal():
            duration = self.get_execution_time()
            duration_str = f" ({duration.total_seconds():.1f}s)" if duration else ""
            return f"{action_name}: {status}{duration_str}"
        elif self.requires_manual_approval and self.approval_granted_at is None:
            return f"{action_name}: Awaiting Approval"
        else:
            return f"{action_name}: {status}"
    
    def __str__(self) -> str:
        """String representation for general use."""
        return f"{self.compensation_type.value}:{self.status}"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"CompensationAction(type={self.compensation_type}, "
            f"phase={self.target_phase}, status={self.status}, "
            f"priority={self.priority})"
        )