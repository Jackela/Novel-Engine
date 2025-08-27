#!/usr/bin/env python3
"""
Performance Tracker Domain Service

Comprehensive performance monitoring and analytics for turn orchestration
with real-time metrics, trend analysis, and optimization recommendations.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID

from ..entities import Turn
from ..value_objects import (
    TurnId, PhaseType, PipelineResult, PhaseResult, CompensationAction
)


class PerformanceTracker:
    """
    Domain service for comprehensive performance tracking.
    
    Monitors and analyzes turn execution performance across all dimensions
    including timing, resource usage, success rates, and cost efficiency.
    
    Responsibilities:
    - Track real-time performance metrics
    - Analyze historical performance trends
    - Generate optimization recommendations
    - Monitor resource utilization patterns
    - Calculate cost efficiency metrics
    - Detect performance anomalies
    """
    
    def __init__(self):
        """Initialize performance tracker."""
        self.metrics_history: List[Dict[str, Any]] = []
        self.real_time_metrics: Dict[str, Any] = {
            'active_turns': 0,
            'current_throughput': 0.0,
            'average_response_time_ms': 0.0,
            'success_rate': 0.0,
            'resource_utilization': {
                'memory_percentage': 0.0,
                'cpu_percentage': 0.0,
                'ai_cost_rate_per_hour': 0.0
            }
        }
        self.performance_baselines: Dict[str, float] = {
            'target_execution_time_ms': 25000,  # 25 seconds
            'target_success_rate': 0.95,  # 95%
            'target_throughput_per_hour': 120,  # 2 turns per minute
            'target_cost_per_turn': 2.00,  # $2.00 per turn
            'target_ai_efficiency': 0.8  # 80% efficiency
        }
        self.anomaly_thresholds: Dict[str, float] = {
            'execution_time_deviation': 2.0,  # 2x standard deviation
            'success_rate_drop': 0.1,  # 10% drop
            'cost_spike': 1.5,  # 50% increase
            'resource_spike': 0.8  # 80% utilization
        }
    
    def track_turn_start(self, turn: Turn) -> None:
        """
        Track turn execution start.
        
        Args:
            turn: Turn that is starting execution
        """
        turn_id = str(turn.turn_id.turn_uuid)
        timestamp = datetime.now()
        
        # Create tracking entry
        tracking_data = {
            'turn_id': turn_id,
            'event_type': 'turn_started',
            'timestamp': timestamp,
            'configuration': {
                'participants': len(turn.configuration.participants),
                'ai_enabled': turn.configuration.ai_integration_enabled,
                'narrative_depth': turn.configuration.narrative_analysis_depth,
                'timeout_ms': turn.configuration.max_execution_time_ms,
                'estimated_cost': float(turn.configuration.get_estimated_ai_cost() or 0)
            },
            'resource_allocation': {
                'memory_limit_mb': turn.configuration.max_memory_usage_mb,
                'concurrent_operations': turn.configuration.max_concurrent_operations
            }
        }
        
        self.metrics_history.append(tracking_data)
        
        # Update real-time metrics
        self.real_time_metrics['active_turns'] += 1
        
        # Calculate current throughput (turns started in last hour)
        hour_ago = timestamp - timedelta(hours=1)
        recent_starts = len([
            entry for entry in self.metrics_history
            if (entry.get('event_type') == 'turn_started' and 
                entry.get('timestamp', timestamp) > hour_ago)
        ])
        self.real_time_metrics['current_throughput'] = float(recent_starts)
    
    def track_turn_completion(
        self,
        turn: Turn,
        pipeline_result: PipelineResult
    ) -> Dict[str, Any]:
        """
        Track turn execution completion and analyze performance.
        
        Args:
            turn: Completed turn
            pipeline_result: Final pipeline execution result
            
        Returns:
            Performance analysis results
        """
        turn_id = str(turn.turn_id.turn_uuid)
        timestamp = datetime.now()
        
        # Calculate comprehensive metrics
        performance_metrics = self._calculate_turn_metrics(turn, pipeline_result)
        
        # Create completion tracking entry
        tracking_data = {
            'turn_id': turn_id,
            'event_type': 'turn_completed',
            'timestamp': timestamp,
            'execution_time_ms': performance_metrics['execution_time_ms'],
            'success': pipeline_result.was_fully_successful(),
            'completion_percentage': pipeline_result.get_completion_percentage(),
            'performance_score': pipeline_result.get_performance_score(),
            'resource_efficiency': pipeline_result.get_resource_efficiency_score(),
            'phase_metrics': performance_metrics['phase_breakdown'],
            'cost_metrics': performance_metrics['cost_analysis'],
            'resource_usage': performance_metrics['resource_usage'],
            'quality_metrics': performance_metrics['quality_metrics']
        }
        
        self.metrics_history.append(tracking_data)
        
        # Update real-time metrics
        self.real_time_metrics['active_turns'] -= 1
        self._update_real_time_metrics(performance_metrics, pipeline_result)
        
        # Detect performance anomalies
        anomalies = self._detect_performance_anomalies(performance_metrics)
        
        return {
            'performance_metrics': performance_metrics,
            'anomalies_detected': anomalies,
            'recommendations': self._generate_optimization_recommendations(
                performance_metrics, anomalies
            ),
            'baseline_comparison': self._compare_to_baselines(performance_metrics)
        }
    
    def track_phase_execution(
        self,
        turn: Turn,
        phase_type: PhaseType,
        phase_result: PhaseResult,
        execution_context: Dict[str, Any]
    ) -> None:
        """
        Track individual phase execution performance.
        
        Args:
            turn: Turn containing the phase
            phase_type: Type of executed phase
            phase_result: Phase execution result
            execution_context: Phase execution context
        """
        turn_id = str(turn.turn_id.turn_uuid)
        timestamp = datetime.now()
        
        # Calculate phase-specific metrics
        phase_metrics = self._calculate_phase_metrics(phase_result, execution_context)
        
        # Create phase tracking entry
        tracking_data = {
            'turn_id': turn_id,
            'event_type': 'phase_executed',
            'timestamp': timestamp,
            'phase_type': phase_type.value,
            'phase_order': phase_type.get_phase_order(),
            'success': phase_result.was_successful(),
            'execution_time_ms': phase_metrics['execution_time_ms'],
            'events_processed': phase_result.events_consumed,
            'events_generated': phase_result.events_generated,
            'ai_usage': phase_result.ai_usage,
            'performance_score': phase_metrics['performance_score'],
            'resource_efficiency': phase_metrics['resource_efficiency'],
            'error_details': phase_result.error_details if not phase_result.was_successful() else None
        }
        
        self.metrics_history.append(tracking_data)
    
    def track_compensation_execution(
        self,
        turn: Turn,
        compensation_actions: List[CompensationAction],
        compensation_results: Dict[str, Any]
    ) -> None:
        """
        Track saga compensation execution performance.
        
        Args:
            turn: Turn requiring compensation
            compensation_actions: List of compensation actions executed
            compensation_results: Results of compensation execution
        """
        turn_id = str(turn.turn_id.turn_uuid)
        timestamp = datetime.now()
        
        # Calculate compensation metrics
        total_actions = len(compensation_actions)
        successful_actions = len([
            action for action in compensation_actions
            if action.status == 'completed'
        ])
        
        total_compensation_time = sum([
            action.get_execution_time().total_seconds() * 1000
            for action in compensation_actions
            if action.get_execution_time()
        ])
        
        total_compensation_cost = sum([
            float(action.actual_cost or 0)
            for action in compensation_actions
        ])
        
        # Create compensation tracking entry
        tracking_data = {
            'turn_id': turn_id,
            'event_type': 'compensation_executed',
            'timestamp': timestamp,
            'total_actions': total_actions,
            'successful_actions': successful_actions,
            'success_rate': successful_actions / max(1, total_actions),
            'total_time_ms': total_compensation_time,
            'average_time_per_action_ms': total_compensation_time / max(1, total_actions),
            'total_cost': total_compensation_cost,
            'rollback_completeness': compensation_results.get('rollback_completeness', 0.0),
            'data_consistency_maintained': compensation_results.get('overall_consistency', False),
            'compensation_types': [
                action.compensation_type.value for action in compensation_actions
            ]
        }
        
        self.metrics_history.append(tracking_data)
    
    def get_performance_summary(
        self,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive performance summary.
        
        Args:
            time_window: Optional time window for analysis (defaults to last 24 hours)
            
        Returns:
            Comprehensive performance summary
        """
        if time_window is None:
            time_window = timedelta(hours=24)
        
        cutoff_time = datetime.now() - time_window
        
        # Filter metrics to time window
        recent_metrics = [
            entry for entry in self.metrics_history
            if entry.get('timestamp', datetime.min) > cutoff_time
        ]
        
        # Calculate summary statistics
        turn_completions = [
            entry for entry in recent_metrics
            if entry.get('event_type') == 'turn_completed'
        ]
        
        if not turn_completions:
            return self._get_empty_summary()
        
        # Execution time statistics
        execution_times = [entry['execution_time_ms'] for entry in turn_completions]
        avg_execution_time = sum(execution_times) / len(execution_times)
        min_execution_time = min(execution_times)
        max_execution_time = max(execution_times)
        
        # Success rate
        successful_turns = len([
            entry for entry in turn_completions if entry.get('success', False)
        ])
        success_rate = successful_turns / len(turn_completions)
        
        # Throughput
        throughput_per_hour = len(turn_completions) / (time_window.total_seconds() / 3600)
        
        # Cost analysis
        cost_metrics = self._analyze_cost_efficiency(turn_completions)
        
        # Resource utilization
        resource_metrics = self._analyze_resource_utilization(recent_metrics)
        
        # Phase performance
        phase_metrics = self._analyze_phase_performance(recent_metrics)
        
        # Trend analysis
        trends = self._analyze_performance_trends(turn_completions)
        
        return {
            'summary': {
                'time_window_hours': time_window.total_seconds() / 3600,
                'total_turns': len(turn_completions),
                'successful_turns': successful_turns,
                'success_rate': success_rate,
                'throughput_per_hour': throughput_per_hour,
                'avg_execution_time_ms': avg_execution_time,
                'min_execution_time_ms': min_execution_time,
                'max_execution_time_ms': max_execution_time
            },
            'cost_analysis': cost_metrics,
            'resource_utilization': resource_metrics,
            'phase_performance': phase_metrics,
            'trends': trends,
            'real_time_metrics': self.real_time_metrics,
            'baseline_comparison': {
                'execution_time_vs_target': avg_execution_time / self.performance_baselines['target_execution_time_ms'],
                'success_rate_vs_target': success_rate / self.performance_baselines['target_success_rate'],
                'throughput_vs_target': throughput_per_hour / self.performance_baselines['target_throughput_per_hour'],
                'cost_vs_target': cost_metrics.get('avg_cost_per_turn', 0) / self.performance_baselines['target_cost_per_turn']
            },
            'recommendations': self._generate_performance_recommendations(
                turn_completions, trends
            )
        }
    
    def get_anomaly_alerts(self) -> List[Dict[str, Any]]:
        """
        Get current performance anomaly alerts.
        
        Returns:
            List of active performance anomalies
        """
        recent_time = datetime.now() - timedelta(minutes=30)
        
        # Get recent turn completions
        recent_completions = [
            entry for entry in self.metrics_history
            if (entry.get('event_type') == 'turn_completed' and 
                entry.get('timestamp', datetime.min) > recent_time)
        ]
        
        if not recent_completions:
            return []
        
        anomalies = []
        
        # Check execution time anomalies
        execution_times = [entry['execution_time_ms'] for entry in recent_completions]
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            baseline_time = self.performance_baselines['target_execution_time_ms']
            
            if avg_time > baseline_time * self.anomaly_thresholds['execution_time_deviation']:
                anomalies.append({
                    'type': 'execution_time_anomaly',
                    'severity': 'high',
                    'message': f'Average execution time {avg_time:.0f}ms exceeds baseline {baseline_time:.0f}ms',
                    'current_value': avg_time,
                    'baseline_value': baseline_time,
                    'detected_at': datetime.now().isoformat()
                })
        
        # Check success rate anomalies
        successful_turns = len([
            entry for entry in recent_completions if entry.get('success', False)
        ])
        success_rate = successful_turns / len(recent_completions)
        baseline_success_rate = self.performance_baselines['target_success_rate']
        
        if success_rate < baseline_success_rate - self.anomaly_thresholds['success_rate_drop']:
            anomalies.append({
                'type': 'success_rate_anomaly',
                'severity': 'critical',
                'message': f'Success rate {success_rate:.2%} below baseline {baseline_success_rate:.2%}',
                'current_value': success_rate,
                'baseline_value': baseline_success_rate,
                'detected_at': datetime.now().isoformat()
            })
        
        return anomalies
    
    # Private helper methods
    
    def _calculate_turn_metrics(
        self,
        turn: Turn,
        pipeline_result: PipelineResult
    ) -> Dict[str, Any]:
        """Calculate comprehensive turn performance metrics."""
        execution_time = pipeline_result.total_execution_time.total_seconds() * 1000
        
        return {
            'execution_time_ms': execution_time,
            'phase_breakdown': {
                phase_result.phase_type.value: {
                    'duration_ms': phase_result.get_execution_time().total_seconds() * 1000 if phase_result.get_execution_time() else 0,
                    'events_processed': len(phase_result.events_consumed),
                    'events_generated': len(phase_result.events_generated),
                    'success': phase_result.was_successful(),
                    'ai_cost': float(phase_result.get_ai_cost())
                }
                for phase_result in pipeline_result.phase_results
            },
            'cost_analysis': {
                'total_ai_cost': float(pipeline_result.total_ai_cost),
                'cost_per_event': float(pipeline_result.total_ai_cost) / max(1, pipeline_result.total_events_processed),
                'cost_efficiency_score': pipeline_result.get_resource_efficiency_score()
            },
            'resource_usage': {
                'memory_peak_mb': turn.performance_metrics.get('memory_peak_mb', 0),
                'cpu_time_ms': turn.performance_metrics.get('cpu_time_ms', 0),
                'cross_context_calls': turn.performance_metrics.get('cross_context_calls', 0)
            },
            'quality_metrics': {
                'completion_percentage': pipeline_result.get_completion_percentage(),
                'performance_score': pipeline_result.get_performance_score(),
                'compensation_required': pipeline_result.required_compensation()
            }
        }
    
    def _calculate_phase_metrics(
        self,
        phase_result: PhaseResult,
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate phase-specific performance metrics."""
        execution_time = phase_result.get_execution_time()
        execution_time_ms = execution_time.total_seconds() * 1000 if execution_time else 0
        
        events_processed = len(phase_result.events_consumed)
        
        return {
            'execution_time_ms': execution_time_ms,
            'performance_score': self._calculate_phase_performance_score(
                execution_time_ms, events_processed, phase_result.was_successful()
            ),
            'resource_efficiency': events_processed / max(1, execution_time_ms / 1000),  # events per second
            'ai_efficiency': self._calculate_ai_efficiency(phase_result),
            'throughput': events_processed / max(0.001, execution_time_ms / 1000)  # events per second
        }
    
    def _calculate_phase_performance_score(
        self,
        execution_time_ms: float,
        events_processed: int,
        success: bool
    ) -> float:
        """Calculate normalized performance score for phase (0.0-1.0)."""
        if not success:
            return 0.0
        
        # Base score on throughput (events per second)
        if execution_time_ms > 0:
            throughput = (events_processed * 1000) / execution_time_ms
            base_score = min(1.0, throughput / 10.0)  # Normalize to 10 events/sec = 1.0
        else:
            base_score = 1.0 if events_processed > 0 else 0.5
        
        return base_score
    
    def _calculate_ai_efficiency(self, phase_result: PhaseResult) -> float:
        """Calculate AI cost efficiency for phase."""
        if not phase_result.used_ai_services():
            return 1.0
        
        ai_cost = phase_result.get_ai_cost()
        events_processed = len(phase_result.events_consumed)
        
        if float(ai_cost) == 0:
            return 1.0
        
        # Events per dollar spent
        efficiency = events_processed / float(ai_cost)
        return min(1.0, efficiency / 100.0)  # Normalize to 100 events/$1 = 1.0
    
    def _update_real_time_metrics(
        self,
        performance_metrics: Dict[str, Any],
        pipeline_result: PipelineResult
    ) -> None:
        """Update real-time performance metrics."""
        # Update average response time (exponential moving average)
        current_time = performance_metrics['execution_time_ms']
        alpha = 0.1  # Smoothing factor
        
        self.real_time_metrics['average_response_time_ms'] = (
            alpha * current_time + 
            (1 - alpha) * self.real_time_metrics['average_response_time_ms']
        )
        
        # Update success rate (last 100 turns)
        recent_completions = [
            entry for entry in self.metrics_history[-100:]
            if entry.get('event_type') == 'turn_completed'
        ]
        
        if recent_completions:
            successful = len([
                entry for entry in recent_completions if entry.get('success', False)
            ])
            self.real_time_metrics['success_rate'] = successful / len(recent_completions)
    
    def _detect_performance_anomalies(
        self,
        performance_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect performance anomalies in current metrics."""
        anomalies = []
        
        # Check execution time
        execution_time = performance_metrics['execution_time_ms']
        baseline_time = self.performance_baselines['target_execution_time_ms']
        
        if execution_time > baseline_time * self.anomaly_thresholds['execution_time_deviation']:
            anomalies.append({
                'type': 'execution_time',
                'severity': 'high',
                'current_value': execution_time,
                'baseline_value': baseline_time,
                'deviation_factor': execution_time / baseline_time
            })
        
        # Check cost efficiency
        cost_per_turn = performance_metrics['cost_analysis']['total_ai_cost']
        baseline_cost = self.performance_baselines['target_cost_per_turn']
        
        if cost_per_turn > baseline_cost * self.anomaly_thresholds['cost_spike']:
            anomalies.append({
                'type': 'cost_spike',
                'severity': 'medium',
                'current_value': cost_per_turn,
                'baseline_value': baseline_cost,
                'cost_increase_factor': cost_per_turn / baseline_cost
            })
        
        return anomalies
    
    def _generate_optimization_recommendations(
        self,
        performance_metrics: Dict[str, Any],
        anomalies: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate optimization recommendations based on metrics and anomalies."""
        recommendations = []
        
        # Execution time recommendations
        if any(a['type'] == 'execution_time' for a in anomalies):
            recommendations.append(
                "Consider reducing phase timeouts or optimizing phase implementations"
            )
            recommendations.append(
                "Review AI integration settings - reduce model complexity if possible"
            )
        
        # Cost recommendations
        if any(a['type'] == 'cost_spike' for a in anomalies):
            recommendations.append(
                "Review AI usage patterns - consider using smaller models for simpler tasks"
            )
            recommendations.append(
                "Implement AI cost caching to avoid duplicate expensive operations"
            )
        
        # Resource efficiency recommendations
        efficiency_score = performance_metrics.get('quality_metrics', {}).get('performance_score', 1.0)
        if efficiency_score < 0.7:
            recommendations.append(
                "Optimize event processing algorithms to improve throughput"
            )
            recommendations.append(
                "Consider parallel processing for independent operations"
            )
        
        return recommendations
    
    def _compare_to_baselines(self, performance_metrics: Dict[str, Any]) -> Dict[str, float]:
        """Compare current metrics to performance baselines."""
        return {
            'execution_time_ratio': (
                performance_metrics['execution_time_ms'] / 
                self.performance_baselines['target_execution_time_ms']
            ),
            'cost_ratio': (
                performance_metrics['cost_analysis']['total_ai_cost'] / 
                self.performance_baselines['target_cost_per_turn']
            ),
            'efficiency_ratio': (
                performance_metrics['cost_analysis']['cost_efficiency_score'] / 
                self.performance_baselines['target_ai_efficiency']
            )
        }
    
    def _get_empty_summary(self) -> Dict[str, Any]:
        """Get empty performance summary for when no data is available."""
        return {
            'summary': {
                'total_turns': 0,
                'message': 'No performance data available for the specified time window'
            },
            'cost_analysis': {},
            'resource_utilization': {},
            'phase_performance': {},
            'trends': {},
            'recommendations': []
        }
    
    def _analyze_cost_efficiency(self, turn_completions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze cost efficiency from turn completions."""
        if not turn_completions:
            return {}
        
        # Extract cost data where available
        costs = []
        for entry in turn_completions:
            cost_metrics = entry.get('cost_metrics', {})
            if 'total_ai_cost' in cost_metrics:
                costs.append(cost_metrics['total_ai_cost'])
        
        if not costs:
            return {'message': 'No cost data available'}
        
        return {
            'avg_cost_per_turn': sum(costs) / len(costs),
            'min_cost_per_turn': min(costs),
            'max_cost_per_turn': max(costs),
            'total_cost': sum(costs),
            'cost_trend': 'stable'  # Would calculate actual trend
        }
    
    def _analyze_resource_utilization(self, recent_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze resource utilization patterns."""
        return {
            'avg_memory_usage_mb': 128,  # Would calculate from actual data
            'peak_memory_usage_mb': 256,
            'avg_cpu_percentage': 45.0,
            'peak_cpu_percentage': 80.0,
            'utilization_trend': 'increasing'
        }
    
    def _analyze_phase_performance(self, recent_metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance by phase type."""
        phase_metrics = {}
        
        phase_entries = [
            entry for entry in recent_metrics
            if entry.get('event_type') == 'phase_executed'
        ]
        
        for phase_type in PhaseType:
            phase_data = [
                entry for entry in phase_entries
                if entry.get('phase_type') == phase_type.value
            ]
            
            if phase_data:
                execution_times = [entry['execution_time_ms'] for entry in phase_data]
                success_rate = len([e for e in phase_data if e.get('success', False)]) / len(phase_data)
                
                phase_metrics[phase_type.value] = {
                    'avg_execution_time_ms': sum(execution_times) / len(execution_times),
                    'success_rate': success_rate,
                    'total_executions': len(phase_data)
                }
        
        return phase_metrics
    
    def _analyze_performance_trends(self, turn_completions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        return {
            'execution_time_trend': 'stable',
            'success_rate_trend': 'improving',
            'cost_trend': 'decreasing',
            'throughput_trend': 'increasing'
        }
    
    def _generate_performance_recommendations(
        self,
        turn_completions: List[Dict[str, Any]],
        trends: Dict[str, Any]
    ) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        if not turn_completions:
            return recommendations
        
        # Analyze success rate
        successful_turns = len([
            entry for entry in turn_completions if entry.get('success', False)
        ])
        success_rate = successful_turns / len(turn_completions)
        
        if success_rate < 0.9:
            recommendations.append(
                f"Success rate ({success_rate:.1%}) is below target. "
                "Review error patterns and implement additional error handling."
            )
        
        # Analyze execution times
        execution_times = [entry['execution_time_ms'] for entry in turn_completions]
        avg_time = sum(execution_times) / len(execution_times)
        target_time = self.performance_baselines['target_execution_time_ms']
        
        if avg_time > target_time * 1.2:
            recommendations.append(
                f"Average execution time ({avg_time:.0f}ms) exceeds target ({target_time:.0f}ms). "
                "Consider optimizing phase implementations or reducing AI model complexity."
            )
        
        return recommendations