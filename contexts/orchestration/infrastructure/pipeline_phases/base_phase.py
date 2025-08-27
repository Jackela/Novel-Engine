#!/usr/bin/env python3
"""
Base Phase Implementation

Abstract base class for all pipeline phase implementations with
common functionality, error handling, and integration patterns.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Set
from uuid import UUID, uuid4

from ...domain.value_objects import PhaseType, TurnConfiguration


class PhaseExecutionContext:
    """
    Execution context for pipeline phases.
    
    Provides access to turn configuration, participant data,
    cross-context services, and execution state.
    """
    
    def __init__(
        self,
        turn_id: UUID,
        phase_type: PhaseType,
        configuration: TurnConfiguration,
        participants: List[str],
        execution_metadata: Dict[str, Any]
    ):
        self.turn_id = turn_id
        self.phase_type = phase_type
        self.configuration = configuration
        self.participants = participants
        self.execution_metadata = execution_metadata
        self.started_at = datetime.now()
        self.rollback_data: Dict[str, Any] = {}
        self.performance_metrics: Dict[str, float] = {}
        self.ai_usage_tracking: Dict[str, Any] = {}
        self.cross_context_calls: List[Dict[str, Any]] = []
        self.generated_events: List[UUID] = []
        self.consumed_events: List[UUID] = []
        self.artifacts_created: List[str] = []
    
    def record_cross_context_call(
        self,
        target_context: str,
        operation: str,
        parameters: Dict[str, Any],
        response_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a cross-context service call."""
        self.cross_context_calls.append({
            'timestamp': datetime.now().isoformat(),
            'target_context': target_context,
            'operation': operation,
            'parameters': parameters,
            'response_data': response_data,
            'call_id': str(uuid4())
        })
    
    def record_ai_usage(
        self,
        service: str,
        operation: str,
        tokens_used: int,
        cost: Decimal,
        response_time_ms: float,
        model_used: Optional[str] = None
    ) -> None:
        """Record AI service usage for cost tracking."""
        if 'total_cost' not in self.ai_usage_tracking:
            self.ai_usage_tracking['total_cost'] = Decimal('0.00')
            self.ai_usage_tracking['total_tokens'] = 0
            self.ai_usage_tracking['operations'] = []
        
        self.ai_usage_tracking['total_cost'] += cost
        self.ai_usage_tracking['total_tokens'] += tokens_used
        self.ai_usage_tracking['operations'].append({
            'timestamp': datetime.now().isoformat(),
            'service': service,
            'operation': operation,
            'tokens_used': tokens_used,
            'cost': float(cost),
            'response_time_ms': response_time_ms,
            'model_used': model_used
        })
    
    def store_rollback_data(self, key: str, data: Any) -> None:
        """Store data needed for potential rollback."""
        self.rollback_data[key] = {
            'data': data,
            'timestamp': datetime.now().isoformat(),
            'context': {
                'phase': self.phase_type.value,
                'turn_id': str(self.turn_id)
            }
        }
    
    def record_performance_metric(self, metric_name: str, value: float) -> None:
        """Record performance metric for this phase."""
        self.performance_metrics[metric_name] = value
    
    def get_execution_time_ms(self) -> float:
        """Get current execution time in milliseconds."""
        return (datetime.now() - self.started_at).total_seconds() * 1000


class PhaseResult:
    """
    Result of phase execution with comprehensive metadata.
    """
    
    def __init__(
        self,
        success: bool,
        events_processed: int = 0,
        events_generated: Optional[List[UUID]] = None,
        artifacts_created: Optional[List[str]] = None,
        performance_metrics: Optional[Dict[str, float]] = None,
        ai_usage: Optional[Dict[str, Any]] = None,
        error_details: Optional[Dict[str, Any]] = None,
        rollback_data: Optional[Dict[str, Any]] = None,
        cross_context_calls: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.events_processed = events_processed
        self.events_generated = events_generated or []
        self.artifacts_created = artifacts_created or []
        self.performance_metrics = performance_metrics or {}
        self.ai_usage = ai_usage
        self.error_details = error_details
        self.rollback_data = rollback_data or {}
        self.cross_context_calls = cross_context_calls or []
        self.metadata = metadata or {}
        self.execution_completed_at = datetime.now()


class BasePhaseImplementation(ABC):
    """
    Abstract base class for all pipeline phase implementations.
    
    Provides common functionality including error handling, timeout management,
    rollback data collection, performance monitoring, and cross-context integration.
    """
    
    def __init__(self, phase_type: PhaseType):
        self.phase_type = phase_type
        self.execution_timeout_ms = 10000  # 10 seconds default
        self.retry_attempts = 3
        self.rollback_enabled = True
    
    async def execute(self, context: PhaseExecutionContext) -> PhaseResult:
        """
        Execute pipeline phase with comprehensive error handling and monitoring.
        
        Args:
            context: Phase execution context
            
        Returns:
            PhaseResult with execution results and metadata
            
        Raises:
            PhaseExecutionError: If phase execution fails
        """
        # Validate execution preconditions
        self._validate_preconditions(context)
        
        # Set up timeout monitoring
        timeout_seconds = context.configuration.get_phase_timeout(self.phase_type.value) / 1000.0
        
        try:
            # Execute phase with timeout
            result = await asyncio.wait_for(
                self._execute_phase_implementation(context),
                timeout=timeout_seconds
            )
            
            # Validate and enrich result
            self._validate_phase_result(result, context)
            self._enrich_result_with_context_data(result, context)
            
            return result
            
        except asyncio.TimeoutError:
            # Handle timeout
            error_details = {
                'error_type': 'timeout',
                'timeout_seconds': timeout_seconds,
                'execution_time_ms': context.get_execution_time_ms(),
                'phase_type': self.phase_type.value
            }
            
            return self._create_failure_result(
                context, "Phase execution timed out", error_details
            )
            
        except Exception as e:
            # Handle general execution errors
            error_details = {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'execution_time_ms': context.get_execution_time_ms(),
                'phase_type': self.phase_type.value
            }
            
            return self._create_failure_result(
                context, f"Phase execution failed: {e}", error_details
            )
    
    @abstractmethod
    async def _execute_phase_implementation(
        self,
        context: PhaseExecutionContext
    ) -> PhaseResult:
        """
        Implement phase-specific execution logic.
        
        Args:
            context: Phase execution context
            
        Returns:
            PhaseResult with execution results
        """
        pass
    
    @abstractmethod
    def _validate_preconditions(self, context: PhaseExecutionContext) -> None:
        """
        Validate that preconditions for phase execution are met.
        
        Args:
            context: Phase execution context
            
        Raises:
            ValueError: If preconditions are not met
        """
        pass
    
    def _validate_phase_result(
        self,
        result: PhaseResult,
        context: PhaseExecutionContext
    ) -> None:
        """
        Validate phase execution result structure and content.
        
        Args:
            result: Phase execution result
            context: Phase execution context
            
        Raises:
            ValueError: If result is invalid
        """
        if not isinstance(result, PhaseResult):
            raise ValueError("Phase must return PhaseResult instance")
        
        if result.success is None:
            raise ValueError("PhaseResult must specify success status")
        
        if result.events_processed < 0:
            raise ValueError("Events processed cannot be negative")
        
        # Validate AI usage if present
        if result.ai_usage:
            required_ai_fields = ['total_cost', 'total_tokens', 'operations']
            if not all(field in result.ai_usage for field in required_ai_fields):
                raise ValueError("AI usage data is incomplete")
    
    def _enrich_result_with_context_data(
        self,
        result: PhaseResult,
        context: PhaseExecutionContext
    ) -> None:
        """
        Enrich phase result with context data and metrics.
        
        Args:
            result: Phase execution result to enrich
            context: Phase execution context
        """
        # Add execution timing
        result.performance_metrics.update(context.performance_metrics)
        result.performance_metrics['execution_time_ms'] = context.get_execution_time_ms()
        
        # Add cross-context call data
        result.cross_context_calls = context.cross_context_calls.copy()
        
        # Add AI usage data if available
        if context.ai_usage_tracking:
            result.ai_usage = context.ai_usage_tracking.copy()
        
        # Add rollback data
        result.rollback_data = context.rollback_data.copy()
        
        # Add events tracking
        result.events_generated = context.generated_events.copy()
        result.artifacts_created = context.artifacts_created.copy()
        
        # Add metadata
        result.metadata.update({
            'phase_type': self.phase_type.value,
            'turn_id': str(context.turn_id),
            'participant_count': len(context.participants),
            'ai_integration_enabled': context.configuration.ai_integration_enabled,
            'execution_timestamp': datetime.now().isoformat()
        })
    
    def _create_failure_result(
        self,
        context: PhaseExecutionContext,
        error_message: str,
        error_details: Dict[str, Any]
    ) -> PhaseResult:
        """
        Create standardized failure result.
        
        Args:
            context: Phase execution context
            error_message: Primary error message
            error_details: Detailed error information
            
        Returns:
            PhaseResult indicating failure
        """
        result = PhaseResult(
            success=False,
            events_processed=0,
            error_details={
                'message': error_message,
                'details': error_details,
                'timestamp': datetime.now().isoformat(),
                'phase_type': self.phase_type.value,
                'turn_id': str(context.turn_id)
            }
        )
        
        # Add any partial results or context data
        self._enrich_result_with_context_data(result, context)
        
        return result
    
    # Helper methods for common phase operations
    
    async def _call_external_service(
        self,
        context: PhaseExecutionContext,
        service_name: str,
        operation: str,
        parameters: Dict[str, Any],
        timeout_seconds: float = 5.0
    ) -> Dict[str, Any]:
        """
        Call external service with timeout and error handling.
        
        Args:
            context: Phase execution context
            service_name: Name of external service
            operation: Operation to perform
            parameters: Operation parameters
            timeout_seconds: Request timeout
            
        Returns:
            Service response data
            
        Raises:
            RuntimeError: If service call fails
        """
        start_time = datetime.now()
        
        try:
            # In a real implementation, this would make actual HTTP/RPC calls
            # For now, we'll simulate the call
            await asyncio.sleep(0.1)  # Simulate network delay
            
            response_data = {
                'success': True,
                'operation': operation,
                'timestamp': datetime.now().isoformat(),
                'service': service_name
            }
            
            # Record the call
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            context.record_cross_context_call(
                target_context=service_name,
                operation=operation,
                parameters=parameters,
                response_data=response_data
            )
            
            # Record performance metric
            context.record_performance_metric(
                f'{service_name}_response_time_ms',
                response_time_ms
            )
            
            return response_data
            
        except Exception as e:
            raise RuntimeError(f"Failed to call {service_name}.{operation}: {e}")
    
    async def _call_ai_service(
        self,
        context: PhaseExecutionContext,
        service: str,
        operation: str,
        prompt: str,
        model: str = "gpt-3.5-turbo",
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Call AI service with usage tracking.
        
        Args:
            context: Phase execution context
            service: AI service name
            operation: Operation type
            prompt: AI prompt
            model: Model to use
            max_tokens: Maximum tokens
            temperature: Model temperature
            
        Returns:
            AI service response
            
        Raises:
            RuntimeError: If AI service call fails
        """
        if not context.configuration.ai_integration_enabled:
            raise RuntimeError("AI integration is disabled")
        
        start_time = datetime.now()
        
        try:
            # Simulate AI service call
            await asyncio.sleep(0.5)  # Simulate AI processing time
            
            # Simulate response
            tokens_used = min(max_tokens, len(prompt.split()) * 2)  # Rough estimate
            cost = Decimal(str(tokens_used * 0.001))  # $0.001 per token
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            response = {
                'content': f"AI response for {operation}",
                'model': model,
                'tokens_used': tokens_used,
                'finish_reason': 'completed'
            }
            
            # Track AI usage
            context.record_ai_usage(
                service=service,
                operation=operation,
                tokens_used=tokens_used,
                cost=cost,
                response_time_ms=response_time_ms,
                model_used=model
            )
            
            return response
            
        except Exception as e:
            raise RuntimeError(f"AI service call failed: {e}")
    
    def _create_rollback_snapshot(
        self,
        context: PhaseExecutionContext,
        data_category: str,
        current_state: Dict[str, Any]
    ) -> None:
        """
        Create rollback snapshot for potential saga compensation.
        
        Args:
            context: Phase execution context
            data_category: Category of data being snapshotted
            current_state: Current state to snapshot
        """
        if self.rollback_enabled:
            context.store_rollback_data(
                f"{data_category}_snapshot",
                {
                    'state': current_state,
                    'phase': self.phase_type.value,
                    'snapshot_time': datetime.now().isoformat()
                }
            )
    
    def _record_event_generation(
        self,
        context: PhaseExecutionContext,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> UUID:
        """
        Record generation of a domain or integration event.
        
        Args:
            context: Phase execution context
            event_type: Type of event generated
            event_data: Event data
            
        Returns:
            Generated event ID
        """
        event_id = uuid4()
        
        # Record event generation
        context.generated_events.append(event_id)
        
        # Store event details in metadata
        if 'generated_events_details' not in context.execution_metadata:
            context.execution_metadata['generated_events_details'] = []
        
        context.execution_metadata['generated_events_details'].append({
            'event_id': str(event_id),
            'event_type': event_type,
            'event_data': event_data,
            'generated_at': datetime.now().isoformat(),
            'phase': self.phase_type.value
        })
        
        return event_id
    
    def _validate_participants(
        self,
        context: PhaseExecutionContext,
        required_participants: Optional[List[str]] = None
    ) -> None:
        """
        Validate that required participants are available.
        
        Args:
            context: Phase execution context
            required_participants: List of required participant IDs
            
        Raises:
            ValueError: If required participants are not available
        """
        if required_participants:
            missing_participants = set(required_participants) - set(context.participants)
            if missing_participants:
                raise ValueError(
                    f"Required participants not available: {missing_participants}"
                )