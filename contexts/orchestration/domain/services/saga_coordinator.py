#!/usr/bin/env python3
"""
Saga Coordinator Domain Service

Coordinates saga pattern implementation for reliable distributed
transactions across Novel Engine contexts with compensation logic.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Set
from uuid import UUID, uuid4

from ..entities import Turn
from ..value_objects import (
    TurnId, PhaseType, CompensationAction, CompensationType,
    PhaseStatus, PhaseStatusEnum
)


class SagaCoordinator:
    """
    Domain service managing saga pattern coordination.
    
    Implements distributed transaction patterns with compensation
    logic for reliable turn execution across multiple contexts.
    
    Responsibilities:
    - Plan and coordinate compensation strategies
    - Execute rollback operations in correct order
    - Manage compensation action lifecycles
    - Ensure data consistency during failures
    - Coordinate cross-context compensation
    """
    
    def __init__(self):
        """Initialize saga coordinator."""
        self.active_compensations: Dict[UUID, List[CompensationAction]] = {}
        self.compensation_strategies: Dict[str, Dict[str, Any]] = {}
        self.rollback_snapshots: Dict[UUID, Dict[str, Any]] = {}
        self.coordination_state: Dict[str, Any] = {
            'total_compensations_executed': 0,
            'successful_compensations': 0,
            'failed_compensations': 0,
            'average_compensation_time_ms': 0.0,
            'data_consistency_violations': 0
        }
    
    def plan_compensation_strategy(
        self,
        turn: Turn,
        failed_phase: PhaseType,
        error_context: Dict[str, Any]
    ) -> List[CompensationAction]:
        """
        Plan comprehensive compensation strategy for failed turn.
        
        Args:
            turn: Turn requiring compensation
            failed_phase: Phase that failed requiring rollback
            error_context: Context about the failure
            
        Returns:
            List of compensation actions in execution order
            
        Raises:
            ValueError: If compensation planning fails
        """
        if not turn.configuration.rollback_enabled:
            raise ValueError("Rollback not enabled for this turn")
        
        # Get committed phases that need compensation
        committed_phases = self._get_committed_phases(turn, failed_phase)
        
        if not committed_phases:
            return []  # No compensation needed
        
        compensation_actions = []
        
        # Plan compensation in reverse order (LIFO)
        for phase_type in reversed(committed_phases):
            phase_compensations = self._plan_phase_compensation(
                turn, phase_type, failed_phase, error_context
            )
            compensation_actions.extend(phase_compensations)
        
        # Add global cleanup compensations
        global_compensations = self._plan_global_compensation(
            turn, failed_phase, error_context
        )
        compensation_actions.extend(global_compensations)
        
        # Set execution order and dependencies
        self._set_compensation_dependencies(compensation_actions)
        
        # Store strategy for tracking
        strategy_id = str(turn.turn_id.turn_uuid)
        self.compensation_strategies[strategy_id] = {
            'turn_id': turn.turn_id.turn_uuid,
            'failed_phase': failed_phase.value,
            'total_actions': len(compensation_actions),
            'planned_at': datetime.now(),
            'estimated_duration_ms': self._estimate_total_compensation_time(
                compensation_actions
            ),
            'compensation_types': [
                action.compensation_type.value for action in compensation_actions
            ]
        }
        
        return compensation_actions
    
    def execute_compensation_action(
        self,
        turn: Turn,
        action: CompensationAction,
        rollback_context: Optional[Dict[str, Any]] = None
    ) -> CompensationAction:
        """
        Execute individual compensation action.
        
        Args:
            turn: Turn being compensated
            action: Compensation action to execute
            rollback_context: Additional rollback context
            
        Returns:
            Updated compensation action with execution results
            
        Raises:
            ValueError: If action execution fails
        """
        if not action.is_ready_to_execute():
            raise ValueError(f"Action {action.action_id} is not ready for execution")
        
        # Start action execution
        executing_action = action.start_execution(executor="SagaCoordinator")
        
        try:
            # Execute based on compensation type
            execution_results = self._execute_compensation_by_type(
                turn, executing_action, rollback_context or {}
            )
            
            # Calculate actual cost if applicable
            actual_cost = self._calculate_compensation_cost(
                executing_action.compensation_type, execution_results
            )
            
            # Complete action successfully
            completed_action = executing_action.complete_execution(
                results=execution_results,
                actual_cost=actual_cost
            )
            
            # Update coordination state
            self._update_compensation_metrics(completed_action, success=True)
            
            return completed_action
            
        except Exception as e:
            # Handle execution failure
            error_details = {
                'error_message': str(e),
                'error_type': type(e).__name__,
                'execution_context': rollback_context or {},
                'timestamp': datetime.now().isoformat()
            }
            
            # Fail action with retry possibility
            failed_action = executing_action.fail_execution(
                error_details=error_details,
                can_retry=self._can_retry_action(executing_action, error_details)
            )
            
            # Update coordination state
            self._update_compensation_metrics(failed_action, success=False)
            
            # Re-raise if cannot retry
            if failed_action.status == "failed":
                raise ValueError(f"Compensation action failed: {e}") from e
            
            return failed_action
    
    def coordinate_parallel_compensations(
        self,
        turn: Turn,
        actions: List[CompensationAction],
        max_parallel: int = 3
    ) -> List[CompensationAction]:
        """
        Coordinate parallel execution of compatible compensation actions.
        
        Args:
            turn: Turn being compensated
            actions: List of compensation actions to execute
            max_parallel: Maximum parallel executions
            
        Returns:
            List of completed compensation actions
        """
        if not actions:
            return []
        
        # Group actions by compatibility for parallel execution
        parallel_groups = self._group_actions_for_parallel_execution(actions)
        completed_actions = []
        
        for group in parallel_groups:
            # Execute group in parallel (simulated - actual implementation
            # would use async/await or thread pools)
            group_results = []
            
            for action in group[:max_parallel]:  # Limit parallel execution
                try:
                    completed_action = self.execute_compensation_action(turn, action)
                    group_results.append(completed_action)
                except Exception:
                    # Handle individual action failure
                    failed_action = action.fail_execution(
                        error_details={'parallel_execution_failed': True}
                    )
                    group_results.append(failed_action)
            
            completed_actions.extend(group_results)
            
            # Check for critical failures that should stop compensation
            if self._has_critical_failures(group_results):
                break
        
        return completed_actions
    
    def validate_compensation_consistency(
        self,
        turn: Turn,
        completed_actions: List[CompensationAction]
    ) -> Dict[str, Any]:
        """
        Validate compensation consistency and data integrity.
        
        Args:
            turn: Turn that was compensated
            completed_actions: List of completed compensation actions
            
        Returns:
            Validation results with consistency status
        """
        validation_results = {
            'overall_consistency': True,
            'data_integrity_maintained': True,
            'rollback_completeness': 1.0,
            'consistency_violations': [],
            'manual_review_required': False,
            'validation_timestamp': datetime.now().isoformat()
        }
        
        # Check rollback completeness
        rollback_completeness = self._calculate_rollback_completeness(
            turn, completed_actions
        )
        validation_results['rollback_completeness'] = rollback_completeness
        
        if rollback_completeness < 0.95:  # Less than 95% complete
            validation_results['overall_consistency'] = False
            validation_results['consistency_violations'].append(
                f"Rollback only {rollback_completeness*100:.1f}% complete"
            )
        
        # Check for data integrity violations
        integrity_violations = self._check_data_integrity(turn, completed_actions)
        if integrity_violations:
            validation_results['data_integrity_maintained'] = False
            validation_results['consistency_violations'].extend(integrity_violations)
        
        # Check for compensation failures
        failed_actions = [a for a in completed_actions if a.status == "failed"]
        if failed_actions:
            validation_results['overall_consistency'] = False
            validation_results['manual_review_required'] = True
            
            for action in failed_actions:
                validation_results['consistency_violations'].append(
                    f"Failed compensation: {action.compensation_type.value}"
                )
        
        # Update coordination metrics
        if not validation_results['overall_consistency']:
            self.coordination_state['data_consistency_violations'] += 1
        
        return validation_results
    
    def get_compensation_status(self, turn_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive compensation status for turn.
        
        Args:
            turn_id: Turn identifier
            
        Returns:
            Compensation status and progress information
        """
        strategy_id = str(turn_id)
        strategy = self.compensation_strategies.get(strategy_id)
        
        if not strategy:
            return {'status': 'no_compensation_required'}
        
        active_actions = self.active_compensations.get(turn_id, [])
        
        return {
            'status': 'in_progress' if active_actions else 'completed',
            'total_actions': strategy['total_actions'],
            'completed_actions': len([a for a in active_actions if a.is_terminal()]),
            'failed_actions': len([a for a in active_actions if a.status == 'failed']),
            'pending_actions': len([a for a in active_actions if a.status == 'pending']),
            'estimated_duration_ms': strategy['estimated_duration_ms'],
            'started_at': strategy['planned_at'],
            'compensation_types': strategy['compensation_types']
        }
    
    # Private helper methods
    
    def _get_committed_phases(
        self,
        turn: Turn,
        failed_phase: PhaseType
    ) -> List[PhaseType]:
        """Get list of phases that were committed and need compensation."""
        committed_phases = []
        
        for phase_type in PhaseType.get_all_phases_ordered():
            # Only compensate phases that completed before the failure
            if phase_type.get_phase_order() < failed_phase.get_phase_order():
                phase_status = turn.phase_statuses.get(phase_type)
                if phase_status and phase_status.status.is_successful():
                    committed_phases.append(phase_type)
            else:
                break  # Don't compensate phases that didn't run
        
        return committed_phases
    
    def _plan_phase_compensation(
        self,
        turn: Turn,
        phase_type: PhaseType,
        failed_phase: PhaseType,
        error_context: Dict[str, Any]
    ) -> List[CompensationAction]:
        """Plan compensation actions for specific phase."""
        compensation_types = CompensationType.get_phase_compensations(phase_type.value)
        actions = []
        
        for compensation_type in compensation_types:
            # Skip compensations that don't apply to this scenario
            if not self._should_apply_compensation(
                phase_type, compensation_type, error_context
            ):
                continue
            
            action = CompensationAction.create_for_phase_failure(
                action_id=uuid4(),
                turn_id=turn.turn_id.turn_uuid,
                failed_phase=phase_type.value,
                compensation_type=compensation_type,
                rollback_data=self._get_rollback_data(turn, phase_type),
                affected_entities=turn.configuration.participants,
                metadata={
                    'original_failed_phase': failed_phase.value,
                    'compensation_order': len(actions) + 1,
                    'error_context': error_context
                }
            )
            
            actions.append(action)
        
        return actions
    
    def _plan_global_compensation(
        self,
        turn: Turn,
        failed_phase: PhaseType,
        error_context: Dict[str, Any]
    ) -> List[CompensationAction]:
        """Plan global compensation actions (logging, notifications, etc.)."""
        global_actions = []
        
        # Always log the failure
        log_action = CompensationAction.create_for_phase_failure(
            action_id=uuid4(),
            turn_id=turn.turn_id.turn_uuid,
            failed_phase="global",
            compensation_type=CompensationType.LOG_FAILURE,
            metadata={
                'failed_phase': failed_phase.value,
                'error_summary': error_context
            }
        )
        global_actions.append(log_action)
        
        # Notify participants if configured
        if turn.configuration.participants:
            notify_action = CompensationAction.create_for_phase_failure(
                action_id=uuid4(),
                turn_id=turn.turn_id.turn_uuid,
                failed_phase="global",
                compensation_type=CompensationType.NOTIFY_PARTICIPANTS,
                affected_entities=turn.configuration.participants,
                metadata={
                    'notification_type': 'turn_failed_compensation',
                    'failed_phase': failed_phase.value
                }
            )
            global_actions.append(notify_action)
        
        # Trigger manual review for critical failures
        if self._is_critical_failure(failed_phase, error_context):
            review_action = CompensationAction.create_for_phase_failure(
                action_id=uuid4(),
                turn_id=turn.turn_id.turn_uuid,
                failed_phase="global",
                compensation_type=CompensationType.TRIGGER_MANUAL_REVIEW,
                metadata={
                    'review_priority': 'high',
                    'failed_phase': failed_phase.value,
                    'requires_immediate_attention': True
                }
            )
            global_actions.append(review_action)
        
        return global_actions
    
    def _set_compensation_dependencies(
        self,
        actions: List[CompensationAction]
    ) -> None:
        """Set execution dependencies between compensation actions."""
        # For now, implement simple serial execution
        # More sophisticated dependency management could be added
        for i, action in enumerate(actions):
            action.metadata['execution_order'] = i + 1
    
    def _estimate_total_compensation_time(
        self,
        actions: List[CompensationAction]
    ) -> int:
        """Estimate total time to execute all compensation actions."""
        return sum(action.execution_timeout_ms for action in actions)
    
    def _execute_compensation_by_type(
        self,
        turn: Turn,
        action: CompensationAction,
        rollback_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute compensation action based on its type."""
        compensation_type = action.compensation_type
        
        if compensation_type == CompensationType.ROLLBACK_WORLD_STATE:
            return self._execute_world_state_rollback(turn, action, rollback_context)
        elif compensation_type == CompensationType.INVALIDATE_SUBJECTIVE_BRIEFS:
            return self._execute_subjective_brief_invalidation(turn, action, rollback_context)
        elif compensation_type == CompensationType.CANCEL_INTERACTIONS:
            return self._execute_interaction_cancellation(turn, action, rollback_context)
        elif compensation_type == CompensationType.REMOVE_EVENTS:
            return self._execute_event_removal(turn, action, rollback_context)
        elif compensation_type == CompensationType.REVERT_NARRATIVE_CHANGES:
            return self._execute_narrative_reversion(turn, action, rollback_context)
        elif compensation_type == CompensationType.NOTIFY_PARTICIPANTS:
            return self._execute_participant_notification(turn, action, rollback_context)
        elif compensation_type == CompensationType.LOG_FAILURE:
            return self._execute_failure_logging(turn, action, rollback_context)
        elif compensation_type == CompensationType.TRIGGER_MANUAL_REVIEW:
            return self._execute_manual_review_trigger(turn, action, rollback_context)
        else:
            raise ValueError(f"Unknown compensation type: {compensation_type}")
    
    def _execute_world_state_rollback(
        self,
        turn: Turn,
        action: CompensationAction,
        rollback_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute world state rollback compensation."""
        # This would integrate with the World context to rollback changes
        rollback_data = action.rollback_data
        
        return {
            'success': True,
            'entities_restored': len(action.affected_entities),
            'state_changes_reverted': len(rollback_data.get('state_changes', [])),
            'rollback_timestamp': datetime.now().isoformat(),
            'data_integrity': True
        }
    
    def _execute_subjective_brief_invalidation(
        self,
        turn: Turn,
        action: CompensationAction,
        rollback_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute subjective brief invalidation compensation."""
        # This would integrate with the AI Gateway to invalidate briefs
        return {
            'success': True,
            'briefs_invalidated': len(action.affected_entities),
            'ai_cache_cleared': True,
            'invalidation_timestamp': datetime.now().isoformat()
        }
    
    def _execute_interaction_cancellation(
        self,
        turn: Turn,
        action: CompensationAction,
        rollback_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute interaction cancellation compensation."""
        # This would integrate with the Interaction context to cancel active interactions
        return {
            'success': True,
            'interactions_cancelled': len(action.affected_entities),
            'negotiations_terminated': True,
            'cancellation_timestamp': datetime.now().isoformat()
        }
    
    def _execute_event_removal(
        self,
        turn: Turn,
        action: CompensationAction,
        rollback_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute event removal compensation."""
        # This would integrate with the event bus to remove generated events
        return {
            'success': True,
            'events_removed': len(rollback_context.get('events_to_remove', [])),
            'event_log_cleaned': True,
            'removal_timestamp': datetime.now().isoformat()
        }
    
    def _execute_narrative_reversion(
        self,
        turn: Turn,
        action: CompensationAction,
        rollback_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute narrative changes reversion compensation."""
        # This would integrate with the Narrative context to revert changes
        return {
            'success': True,
            'narrative_segments_reverted': len(rollback_context.get('narrative_changes', [])),
            'story_consistency_maintained': True,
            'reversion_timestamp': datetime.now().isoformat()
        }
    
    def _execute_participant_notification(
        self,
        turn: Turn,
        action: CompensationAction,
        rollback_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute participant notification compensation."""
        # This would send notifications to affected participants
        return {
            'success': True,
            'participants_notified': len(action.affected_entities),
            'notification_method': 'system_message',
            'notification_timestamp': datetime.now().isoformat()
        }
    
    def _execute_failure_logging(
        self,
        turn: Turn,
        action: CompensationAction,
        rollback_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute failure logging compensation."""
        # This would log the failure details for analysis
        return {
            'success': True,
            'log_entries_created': 1,
            'audit_trail_updated': True,
            'logging_timestamp': datetime.now().isoformat()
        }
    
    def _execute_manual_review_trigger(
        self,
        turn: Turn,
        action: CompensationAction,
        rollback_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute manual review trigger compensation."""
        # This would create a manual review ticket
        return {
            'success': True,
            'review_ticket_created': True,
            'priority': action.metadata.get('review_priority', 'medium'),
            'ticket_timestamp': datetime.now().isoformat()
        }
    
    def _calculate_compensation_cost(
        self,
        compensation_type: CompensationType,
        execution_results: Dict[str, Any]
    ) -> Optional[Decimal]:
        """Calculate actual cost of compensation execution."""
        # Simple cost estimation - could be more sophisticated
        base_costs = {
            CompensationType.ROLLBACK_WORLD_STATE: Decimal('0.10'),
            CompensationType.INVALIDATE_SUBJECTIVE_BRIEFS: Decimal('0.05'),
            CompensationType.CANCEL_INTERACTIONS: Decimal('0.02'),
            CompensationType.REMOVE_EVENTS: Decimal('0.08'),
            CompensationType.REVERT_NARRATIVE_CHANGES: Decimal('0.06'),
            CompensationType.NOTIFY_PARTICIPANTS: Decimal('0.01'),
            CompensationType.LOG_FAILURE: Decimal('0.001'),
            CompensationType.TRIGGER_MANUAL_REVIEW: Decimal('0.001')
        }
        
        return base_costs.get(compensation_type)
    
    def _can_retry_action(
        self,
        action: CompensationAction,
        error_details: Dict[str, Any]
    ) -> bool:
        """Determine if compensation action can be retried."""
        # Don't retry certain error types
        non_retryable_errors = {
            'permission_denied',
            'authentication_failed',
            'data_corruption'
        }
        
        error_type = error_details.get('error_type', '')
        return error_type not in non_retryable_errors
    
    def _update_compensation_metrics(
        self,
        action: CompensationAction,
        success: bool
    ) -> None:
        """Update coordination metrics with action results."""
        self.coordination_state['total_compensations_executed'] += 1
        
        if success:
            self.coordination_state['successful_compensations'] += 1
        else:
            self.coordination_state['failed_compensations'] += 1
        
        # Update average compensation time
        if action.get_execution_time():
            total_compensations = self.coordination_state['total_compensations_executed']
            current_avg = self.coordination_state['average_compensation_time_ms']
            new_time = action.get_execution_time().total_seconds() * 1000
            
            # Calculate running average
            self.coordination_state['average_compensation_time_ms'] = (
                (current_avg * (total_compensations - 1) + new_time) / total_compensations
            )
    
    def _group_actions_for_parallel_execution(
        self,
        actions: List[CompensationAction]
    ) -> List[List[CompensationAction]]:
        """Group compensation actions for parallel execution."""
        # Simple grouping - more sophisticated dependency analysis could be added
        parallel_groups = []
        current_group = []
        
        for action in actions:
            # Actions that can run in parallel with others
            if action.compensation_type in {
                CompensationType.NOTIFY_PARTICIPANTS,
                CompensationType.LOG_FAILURE,
                CompensationType.TRIGGER_MANUAL_REVIEW
            }:
                current_group.append(action)
            else:
                # Finish current group and start new one
                if current_group:
                    parallel_groups.append(current_group)
                    current_group = []
                parallel_groups.append([action])  # Execute alone
        
        if current_group:
            parallel_groups.append(current_group)
        
        return parallel_groups
    
    def _has_critical_failures(self, action_results: List[CompensationAction]) -> bool:
        """Check if any critical compensation failures occurred."""
        for action in action_results:
            if (action.status == "failed" and 
                action.compensation_type.is_destructive()):
                return True
        return False
    
    def _calculate_rollback_completeness(
        self,
        turn: Turn,
        completed_actions: List[CompensationAction]
    ) -> float:
        """Calculate percentage of rollback completeness."""
        if not completed_actions:
            return 0.0
        
        successful_actions = [a for a in completed_actions if a.status == "completed"]
        return len(successful_actions) / len(completed_actions)
    
    def _check_data_integrity(
        self,
        turn: Turn,
        completed_actions: List[CompensationAction]
    ) -> List[str]:
        """Check for data integrity violations after compensation."""
        violations = []
        
        # Check for failed destructive operations
        for action in completed_actions:
            if (action.status == "failed" and 
                action.compensation_type.is_destructive()):
                violations.append(
                    f"Failed destructive compensation: {action.compensation_type.value}"
                )
        
        return violations
    
    def _should_apply_compensation(
        self,
        phase_type: PhaseType,
        compensation_type: CompensationType,
        error_context: Dict[str, Any]
    ) -> bool:
        """Determine if specific compensation should be applied."""
        # Apply all compensations by default - could add more logic here
        return True
    
    def _get_rollback_data(
        self,
        turn: Turn,
        phase_type: PhaseType
    ) -> Dict[str, Any]:
        """Get rollback data for specific phase."""
        return turn.rollback_snapshots.get(phase_type.value, {})
    
    def _is_critical_failure(
        self,
        failed_phase: PhaseType,
        error_context: Dict[str, Any]
    ) -> bool:
        """Determine if failure is critical and requires manual review."""
        # World state and event integration failures are always critical
        critical_phases = {PhaseType.WORLD_UPDATE, PhaseType.EVENT_INTEGRATION}
        
        if failed_phase in critical_phases:
            return True
        
        # Check error severity
        return error_context.get('severity') == 'critical'