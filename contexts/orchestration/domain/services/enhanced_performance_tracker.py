#!/usr/bin/env python3
"""
Enhanced Performance Tracker with Prometheus Integration

M10 enhanced performance tracking that integrates Prometheus metrics collection
with the existing performance tracking capabilities. Provides backward compatibility
while adding enterprise-grade observability features.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple

from .performance_tracker import PerformanceTracker
from ..entities import Turn
from ..value_objects import (
    TurnId, PhaseType, PipelineResult, PhaseResult, CompensationAction
)
from ...infrastructure.monitoring import PrometheusMetricsCollector

logger = logging.getLogger(__name__)


class EnhancedPerformanceTracker(PerformanceTracker):
    """
    Enhanced performance tracker with Prometheus metrics integration.
    
    Extends the base PerformanceTracker with enterprise-grade observability:
    - Prometheus metrics collection for the core KPIs (llm_cost_per_req, turn_duration_seconds)
    - Real-time business metrics export
    - Enhanced alerting and anomaly detection
    - Integration with monitoring systems
    
    Maintains full backward compatibility with existing PerformanceTracker API
    while adding comprehensive observability capabilities.
    """
    
    def __init__(self, metrics_collector: Optional[PrometheusMetricsCollector] = None):
        """
        Initialize enhanced performance tracker.
        
        Args:
            metrics_collector: Optional Prometheus metrics collector
        """
        # Initialize base tracker
        super().__init__()
        
        # Initialize Prometheus integration
        self.prometheus_collector = metrics_collector or PrometheusMetricsCollector()
        
        # Enhanced tracking state
        self.active_turns_tracking: Dict[str, Dict[str, Any]] = {}
        self.recent_performance_data: List[Dict[str, Any]] = []
        
        logger.info("EnhancedPerformanceTracker initialized with Prometheus integration")
    
    def track_turn_start(self, turn: Turn) -> None:
        """
        Track turn execution start with enhanced Prometheus metrics.
        
        Args:
            turn: Turn that is starting execution
        """
        # Call parent implementation for existing functionality
        super().track_turn_start(turn)
        
        # Enhanced tracking with Prometheus
        turn_id = str(turn.turn_id.turn_uuid)
        participants_count = len(turn.configuration.participants) if hasattr(turn.configuration, 'participants') else 0
        ai_enabled = turn.configuration.ai_integration_enabled
        
        # Store turn start data for completion correlation
        self.active_turns_tracking[turn_id] = {
            'start_time': datetime.now(),
            'participants_count': participants_count,
            'ai_enabled': ai_enabled,
            'configuration': {
                'narrative_depth': turn.configuration.narrative_analysis_depth,
                'max_execution_time_ms': turn.configuration.max_execution_time_ms,
                'estimated_cost': turn.configuration.get_estimated_ai_cost() if hasattr(turn.configuration, 'get_estimated_ai_cost') else Decimal('0')
            }
        }
        
        # Record start metrics in Prometheus
        self.prometheus_collector.record_turn_start(
            turn_id=turn.turn_id.turn_uuid,
            participants_count=participants_count,
            ai_enabled=ai_enabled,
            configuration={
                'narrative_depth': turn.configuration.narrative_analysis_depth,
                'timeout_ms': turn.configuration.max_execution_time_ms
            }
        )
        
        logger.debug(f"Enhanced tracking started for turn {turn_id} with {participants_count} participants")
    
    def track_turn_completion(
        self,
        turn: Turn,
        pipeline_result: PipelineResult
    ) -> Dict[str, Any]:
        """
        Track turn execution completion with comprehensive Prometheus metrics.
        
        Args:
            turn: Completed turn
            pipeline_result: Final pipeline execution result
            
        Returns:
            Enhanced performance analysis results
        """
        # Call parent implementation
        base_results = super().track_turn_completion(turn, pipeline_result)
        
        # Enhanced Prometheus metrics collection
        turn_id = str(turn.turn_id.turn_uuid)
        
        # Get turn start data
        turn_start_data = self.active_turns_tracking.get(turn_id, {})
        start_time = turn_start_data.get('start_time', datetime.now())
        participants_count = turn_start_data.get('participants_count', 0)
        ai_enabled = turn_start_data.get('ai_enabled', False)
        
        # Calculate execution metrics
        execution_time_seconds = (datetime.now() - start_time).total_seconds()
        success = pipeline_result.was_fully_successful()
        total_ai_cost = pipeline_result.total_ai_cost if hasattr(pipeline_result, 'total_ai_cost') else Decimal('0')
        
        # Collect phase results for detailed metrics
        phase_results = {}
        if hasattr(pipeline_result, 'phase_results'):
            for phase_result in pipeline_result.phase_results:
                phase_name = phase_result.phase_type.value if hasattr(phase_result, 'phase_type') else 'unknown'
                phase_results[phase_name] = {
                    'success': phase_result.was_successful() if hasattr(phase_result, 'was_successful') else False,
                    'execution_time_ms': phase_result.get_execution_time().total_seconds() * 1000 if hasattr(phase_result, 'get_execution_time') and phase_result.get_execution_time() else 0,
                    'events_processed': len(phase_result.events_consumed) if hasattr(phase_result, 'events_consumed') else 0,
                    'events_generated': len(phase_result.events_generated) if hasattr(phase_result, 'events_generated') else 0,
                    'ai_cost': float(phase_result.get_ai_cost()) if hasattr(phase_result, 'get_ai_cost') else 0
                }
        
        # Record comprehensive metrics in Prometheus
        self.prometheus_collector.record_turn_completion(
            turn_id=turn.turn_id.turn_uuid,
            participants_count=participants_count,
            ai_enabled=ai_enabled,
            success=success,
            execution_time_seconds=execution_time_seconds,
            total_ai_cost=total_ai_cost,
            phase_results=phase_results
        )
        
        # Record phase-specific metrics
        for phase_name, phase_data in phase_results.items():
            self.prometheus_collector.record_phase_execution(
                phase_name=phase_name,
                participants_count=participants_count,
                success=phase_data['success'],
                execution_time_seconds=phase_data['execution_time_ms'] / 1000,
                events_processed=phase_data['events_processed'],
                events_generated=phase_data['events_generated'],
                ai_cost=Decimal(str(phase_data['ai_cost']))
            )
        
        # Update success rate metrics
        self._update_success_rate_metrics()
        
        # Clean up tracking data
        if turn_id in self.active_turns_tracking:
            del self.active_turns_tracking[turn_id]
        
        # Store recent performance data for analysis
        performance_data = {
            'turn_id': turn_id,
            'timestamp': datetime.now(),
            'execution_time_seconds': execution_time_seconds,
            'success': success,
            'participants_count': participants_count,
            'ai_enabled': ai_enabled,
            'total_ai_cost': float(total_ai_cost),
            'phase_results': phase_results
        }
        self.recent_performance_data.append(performance_data)
        
        # Keep only recent data (last 1000 entries)
        if len(self.recent_performance_data) > 1000:
            self.recent_performance_data = self.recent_performance_data[-1000:]
        
        # Enhanced analysis
        enhanced_results = {
            **base_results,
            'prometheus_metrics_recorded': True,
            'execution_time_seconds': execution_time_seconds,
            'business_kpis': {
                'llm_cost_per_request': float(total_ai_cost),
                'turn_duration_seconds': execution_time_seconds,
                'success_rate': 1.0 if success else 0.0,
                'participants_count': participants_count
            },
            'phase_breakdown': phase_results
        }
        
        logger.info(
            f"Enhanced turn {turn_id} completed - "
            f"duration: {execution_time_seconds:.2f}s, "
            f"cost: ${total_ai_cost:.2f}, "
            f"success: {success}"
        )
        
        return enhanced_results
    
    def track_phase_execution(
        self,
        turn: Turn,
        phase_type: PhaseType,
        phase_result: PhaseResult,
        execution_context: Dict[str, Any]
    ) -> None:
        """
        Track individual phase execution with enhanced Prometheus metrics.
        
        Args:
            turn: Turn containing the phase
            phase_type: Type of executed phase
            phase_result: Phase execution result
            execution_context: Phase execution context
        """
        # Call parent implementation
        super().track_phase_execution(turn, phase_type, phase_result, execution_context)
        
        # Enhanced Prometheus metrics
        turn_id = str(turn.turn_id.turn_uuid)
        turn_data = self.active_turns_tracking.get(turn_id, {})
        participants_count = turn_data.get('participants_count', 0)
        
        # Extract phase metrics
        success = phase_result.was_successful() if hasattr(phase_result, 'was_successful') else False
        execution_time = phase_result.get_execution_time() if hasattr(phase_result, 'get_execution_time') else timedelta(0)
        execution_time_seconds = execution_time.total_seconds() if execution_time else 0
        
        events_processed = len(phase_result.events_consumed) if hasattr(phase_result, 'events_consumed') else 0
        events_generated = len(phase_result.events_generated) if hasattr(phase_result, 'events_generated') else 0
        ai_cost = phase_result.get_ai_cost() if hasattr(phase_result, 'get_ai_cost') else Decimal('0')
        
        # Record enhanced phase metrics
        self.prometheus_collector.record_phase_execution(
            phase_name=phase_type.value,
            participants_count=participants_count,
            success=success,
            execution_time_seconds=execution_time_seconds,
            events_processed=events_processed,
            events_generated=events_generated,
            ai_cost=ai_cost
        )
        
        # Record cross-context calls if present in execution context
        if 'cross_context_calls' in execution_context:
            for call_data in execution_context['cross_context_calls']:
                self.prometheus_collector.record_cross_context_call(
                    target_context=call_data.get('target_context', 'unknown'),
                    operation=call_data.get('operation', 'unknown'),
                    success=call_data.get('success', False),
                    duration_seconds=call_data.get('duration_seconds', 0)
                )
        
        logger.debug(f"Enhanced phase tracking: {phase_type.value} for turn {turn_id}")
    
    def track_compensation_execution(
        self,
        turn: Turn,
        compensation_actions: List[CompensationAction],
        compensation_results: Dict[str, Any]
    ) -> None:
        """
        Track saga compensation execution with Prometheus metrics.
        
        Args:
            turn: Turn requiring compensation
            compensation_actions: List of compensation actions executed
            compensation_results: Results of compensation execution
        """
        # Call parent implementation
        super().track_compensation_execution(turn, compensation_actions, compensation_results)
        
        # Enhanced Prometheus metrics for each compensation action
        for action in compensation_actions:
            compensation_type = action.compensation_type.value if hasattr(action, 'compensation_type') else 'unknown'
            success = action.status == 'completed' if hasattr(action, 'status') else False
            execution_time = action.get_execution_time() if hasattr(action, 'get_execution_time') else timedelta(0)
            execution_time_seconds = execution_time.total_seconds() if execution_time else 0
            rollback_reason = compensation_results.get('rollback_reason', 'phase_failure')
            
            self.prometheus_collector.record_compensation_execution(
                compensation_type=compensation_type,
                success=success,
                execution_time_seconds=execution_time_seconds,
                rollback_reason=rollback_reason
            )
        
        logger.info(f"Enhanced compensation tracking: {len(compensation_actions)} actions for turn {turn.turn_id}")
    
    def record_resource_usage(
        self,
        component: str,
        memory_bytes: int,
        cpu_percent: float
    ) -> None:
        """
        Record resource usage metrics.
        
        Args:
            component: Component name
            memory_bytes: Memory usage in bytes
            cpu_percent: CPU usage percentage
        """
        self.prometheus_collector.record_resource_usage(
            component=component,
            memory_bytes=memory_bytes,
            cpu_percent=cpu_percent
        )
    
    def record_error_with_recovery(
        self,
        error_type: str,
        severity: str,
        component: str,
        recovery_attempted: bool = False,
        recovery_success: bool = False
    ) -> None:
        """
        Record error with recovery attempt information.
        
        Args:
            error_type: Type of error that occurred
            severity: Error severity level
            component: Component where error occurred
            recovery_attempted: Whether error recovery was attempted
            recovery_success: Whether recovery was successful
        """
        self.prometheus_collector.record_error(
            error_type=error_type,
            severity=severity,
            component=component,
            recovery_attempted=recovery_attempted,
            recovery_success=recovery_success
        )
    
    def get_business_kpi_summary(self, time_window: timedelta = None) -> Dict[str, Any]:
        """
        Get business KPI summary including core M10 metrics.
        
        Args:
            time_window: Time window for analysis (defaults to last hour)
            
        Returns:
            Business KPI summary with core metrics
        """
        if time_window is None:
            time_window = timedelta(hours=1)
        
        cutoff_time = datetime.now() - time_window
        
        # Filter recent data
        recent_data = [
            entry for entry in self.recent_performance_data
            if entry['timestamp'] > cutoff_time
        ]
        
        if not recent_data:
            return {
                'llm_cost_per_request_avg': 0.0,
                'turn_duration_seconds_avg': 0.0,
                'turn_duration_seconds_p95': 0.0,
                'success_rate': 0.0,
                'total_turns': 0,
                'total_ai_cost': 0.0,
                'message': 'No data available for the specified time window'
            }
        
        # Calculate KPIs
        total_turns = len(recent_data)
        successful_turns = len([entry for entry in recent_data if entry['success']])
        
        avg_duration = sum(entry['execution_time_seconds'] for entry in recent_data) / total_turns
        durations_sorted = sorted([entry['execution_time_seconds'] for entry in recent_data])
        p95_duration = durations_sorted[int(0.95 * len(durations_sorted))] if durations_sorted else 0
        
        avg_cost = sum(entry['total_ai_cost'] for entry in recent_data) / total_turns
        total_cost = sum(entry['total_ai_cost'] for entry in recent_data)
        
        success_rate = successful_turns / total_turns if total_turns > 0 else 0
        
        return {
            'llm_cost_per_request_avg': avg_cost,
            'turn_duration_seconds_avg': avg_duration,
            'turn_duration_seconds_p95': p95_duration,
            'success_rate': success_rate,
            'total_turns': total_turns,
            'successful_turns': successful_turns,
            'total_ai_cost': total_cost,
            'time_window_hours': time_window.total_seconds() / 3600
        }
    
    def get_prometheus_metrics(self) -> str:
        """
        Get Prometheus metrics data for /metrics endpoint.
        
        Returns:
            Prometheus metrics data
        """
        return self.prometheus_collector.get_metrics_data()
    
    def get_prometheus_content_type(self) -> str:
        """
        Get Prometheus metrics content type.
        
        Returns:
            Content type for metrics response
        """
        return self.prometheus_collector.get_metrics_content_type()
    
    def _update_success_rate_metrics(self) -> None:
        """Update success rate metrics for different time windows."""
        time_windows = {
            '5min': timedelta(minutes=5),
            '1hour': timedelta(hours=1),
            '24hour': timedelta(hours=24)
        }
        
        for window_name, window_duration in time_windows.items():
            cutoff_time = datetime.now() - window_duration
            recent_data = [
                entry for entry in self.recent_performance_data
                if entry['timestamp'] > cutoff_time
            ]
            
            if recent_data:
                successful = len([entry for entry in recent_data if entry['success']])
                success_rate = successful / len(recent_data)
                self.prometheus_collector.update_success_rate(window_name, success_rate)
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status including Prometheus metrics health.
        
        Returns:
            Comprehensive health status
        """
        base_health = super().get_orchestrator_health() if hasattr(super(), 'get_orchestrator_health') else {}
        
        # Add Prometheus integration health
        prometheus_health = {
            'prometheus_integration': 'healthy',
            'active_turns_tracking': len(self.active_turns_tracking),
            'recent_performance_entries': len(self.recent_performance_data),
            'metrics_collector_initialized': self.prometheus_collector is not None
        }
        
        return {
            **base_health,
            **prometheus_health,
            'enhanced_features': {
                'business_kpi_tracking': True,
                'prometheus_metrics': True,
                'real_time_monitoring': True,
                'error_tracking': True
            }
        }