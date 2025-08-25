"""
Performance Metrics Collector
=============================

Collects and analyzes comprehensive performance metrics for the multi-agent bridge.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field

from .cost_tracker import CostTracker
from .performance_budget import PerformanceBudget

__all__ = ['PerformanceMetrics']


@dataclass
class PerformanceMetrics:
    """
    Comprehensive performance metrics collection and analysis.
    
    Responsibilities:
    - Aggregate metrics from cost tracker and performance budget
    - Calculate coordination effectiveness scores
    - Track agent interaction patterns
    - Generate performance insights and recommendations
    """
    
    cost_tracker: CostTracker
    performance_budget: PerformanceBudget
    logger: Optional[logging.Logger] = field(default=None, init=False)
    
    def __post_init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Coordination metrics
        self._coordination_stats = {
            'total_coordinations': 0,
            'successful_coordinations': 0,
            'coordination_quality_sum': 0.0,
            'agent_interactions': {},
            'coordination_types': {}
        }
        
        # Turn performance tracking
        self._turn_metrics = []
    
    def record_coordination_event(self, coordination_type: str, participants: List[str], 
                                quality_score: float, success: bool) -> None:
        """Record a coordination event."""
        try:
            self._coordination_stats['total_coordinations'] += 1
            
            if success:
                self._coordination_stats['successful_coordinations'] += 1
                self._coordination_stats['coordination_quality_sum'] += quality_score
            
            # Track by type
            if coordination_type not in self._coordination_stats['coordination_types']:
                self._coordination_stats['coordination_types'][coordination_type] = 0
            self._coordination_stats['coordination_types'][coordination_type] += 1
            
            # Track agent interactions
            for participant in participants:
                if participant not in self._coordination_stats['agent_interactions']:
                    self._coordination_stats['agent_interactions'][participant] = 0
                self._coordination_stats['agent_interactions'][participant] += 1
            
        except Exception as e:
            self.logger.error(f"Error recording coordination event: {e}")
    
    def record_turn_metrics(self, turn_number: int, additional_metrics: Dict[str, Any] = None) -> None:
        """Record metrics for a completed turn."""
        try:
            # Get base metrics
            cost_stats = self.cost_tracker.get_cost_efficiency_stats()
            perf_stats = self.performance_budget.get_performance_stats()
            
            turn_data = {
                'turn_number': turn_number,
                'timestamp': datetime.now().isoformat(),
                'cost_data': cost_stats,
                'performance_data': perf_stats,
                'coordination_effectiveness': self._calculate_coordination_effectiveness()
            }
            
            if additional_metrics:
                turn_data.update(additional_metrics)
            
            self._turn_metrics.append(turn_data)
            
            # Keep recent history
            if len(self._turn_metrics) > 50:
                self._turn_metrics = self._turn_metrics[-25:]
            
        except Exception as e:
            self.logger.error(f"Error recording turn metrics: {e}")
    
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get all performance metrics in one comprehensive report."""
        try:
            return {
                'timestamp': datetime.now().isoformat(),
                'cost_efficiency': self.cost_tracker.get_cost_efficiency_stats(),
                'performance_stats': self.performance_budget.get_performance_stats(),
                'coordination_metrics': self._get_coordination_metrics(),
                'trend_analysis': self._get_trend_analysis(),
                'system_health_score': self._calculate_system_health_score(),
                'optimization_recommendations': self._get_combined_recommendations()
            }
        except Exception as e:
            self.logger.error(f"Error generating comprehensive metrics: {e}")
            return {}
    
    def _get_coordination_metrics(self) -> Dict[str, Any]:
        """Get coordination-specific metrics."""
        try:
            total = self._coordination_stats['total_coordinations']
            successful = self._coordination_stats['successful_coordinations']
            
            return {
                'total_coordinations': total,
                'successful_coordinations': successful,
                'success_rate': (successful / max(1, total)) * 100,
                'avg_quality_score': (self._coordination_stats['coordination_quality_sum'] / max(1, successful)),
                'most_active_agents': sorted(
                    self._coordination_stats['agent_interactions'].items(),
                    key=lambda x: x[1], reverse=True
                )[:5],
                'coordination_types_breakdown': self._coordination_stats['coordination_types']
            }
        except Exception as e:
            self.logger.error(f"Error getting coordination metrics: {e}")
            return {}
    
    def _calculate_coordination_effectiveness(self) -> float:
        """Calculate overall coordination effectiveness score."""
        try:
            if not self._coordination_stats['total_coordinations']:
                return 0.0
            
            # Base score from success rate
            success_rate = self._coordination_stats['successful_coordinations'] / self._coordination_stats['total_coordinations']
            
            # Quality factor
            if self._coordination_stats['successful_coordinations'] > 0:
                avg_quality = self._coordination_stats['coordination_quality_sum'] / self._coordination_stats['successful_coordinations']
            else:
                avg_quality = 0.0
            
            # Combined effectiveness (70% success rate, 30% quality)
            effectiveness = (success_rate * 0.7) + (avg_quality * 0.3)
            
            return min(1.0, effectiveness)
            
        except Exception:
            return 0.0
    
    def _get_trend_analysis(self) -> Dict[str, Any]:
        """Analyze performance trends over recent turns."""
        try:
            if len(self._turn_metrics) < 5:
                return {'status': 'insufficient_data'}
            
            # Analyze last 10 turns
            recent_turns = self._turn_metrics[-10:]
            
            # Cost trend
            costs = [turn['cost_data']['current_turn_cost'] for turn in recent_turns if 'cost_data' in turn]
            cost_trend = 'stable'
            if len(costs) >= 2:
                if costs[-1] > costs[0] * 1.2:
                    cost_trend = 'increasing'
                elif costs[-1] < costs[0] * 0.8:
                    cost_trend = 'decreasing'
            
            # Performance trend
            perf_data = [turn['performance_data'] for turn in recent_turns if 'performance_data' in turn]
            perf_trend = 'stable'
            if len(perf_data) >= 2:
                recent_avg = sum(p.get('avg_turn_time', 0) for p in perf_data[-3:]) / 3
                older_avg = sum(p.get('avg_turn_time', 0) for p in perf_data[:3]) / 3
                
                if recent_avg > older_avg * 1.1:
                    perf_trend = 'degrading'
                elif recent_avg < older_avg * 0.9:
                    perf_trend = 'improving'
            
            return {
                'status': 'analyzed',
                'cost_trend': cost_trend,
                'performance_trend': perf_trend,
                'turns_analyzed': len(recent_turns),
                'overall_trend': self._determine_overall_trend(cost_trend, perf_trend)
            }
            
        except Exception as e:
            self.logger.error(f"Error in trend analysis: {e}")
            return {'status': 'error'}
    
    def _determine_overall_trend(self, cost_trend: str, perf_trend: str) -> str:
        """Determine overall system trend."""
        if cost_trend == 'increasing' and perf_trend == 'degrading':
            return 'concerning'
        elif cost_trend == 'decreasing' and perf_trend == 'improving':
            return 'excellent'
        elif cost_trend == 'stable' and perf_trend == 'stable':
            return 'stable'
        else:
            return 'mixed'
    
    def _calculate_system_health_score(self) -> float:
        """Calculate overall system health score (0-1)."""
        try:
            scores = []
            
            # Cost health (budget utilization)
            cost_stats = self.cost_tracker.get_cost_efficiency_stats()
            remaining_budget_pct = (cost_stats.get('remaining_total_budget', 0) / max(0.01, self.cost_tracker.max_total_cost)) * 100
            cost_health = min(1.0, remaining_budget_pct / 50)  # 50% remaining = full health
            scores.append(cost_health)
            
            # Performance health
            perf_stats = self.performance_budget.get_performance_stats()
            if perf_stats:
                exceed_rate = perf_stats.get('budget_exceed_rate', 0)
                perf_health = max(0.0, (100 - exceed_rate) / 100)
                scores.append(perf_health)
            
            # Coordination health
            coord_effectiveness = self._calculate_coordination_effectiveness()
            scores.append(coord_effectiveness)
            
            # Overall health is average of all scores
            return sum(scores) / len(scores) if scores else 0.5
            
        except Exception as e:
            self.logger.error(f"Error calculating system health score: {e}")
            return 0.5
    
    def _get_combined_recommendations(self) -> List[Dict[str, Any]]:
        """Get combined recommendations from all components."""
        try:
            recommendations = []
            
            # Cost recommendations
            recommendations.extend(self.cost_tracker.get_optimization_recommendations())
            
            # Performance recommendations
            recommendations.extend(self.performance_budget.get_optimization_recommendations())
            
            # Coordination recommendations
            coord_effectiveness = self._calculate_coordination_effectiveness()
            if coord_effectiveness < 0.6:
                recommendations.append({
                    'type': 'coordination_effectiveness',
                    'issue': f'Low coordination effectiveness: {coord_effectiveness:.1%}',
                    'suggestion': 'Review dialogue quality and agent interaction patterns'
                })
            
            # System health recommendations
            health_score = self._calculate_system_health_score()
            if health_score < 0.5:
                recommendations.append({
                    'type': 'system_health',
                    'issue': f'Low system health score: {health_score:.1%}',
                    'suggestion': 'Consider system optimization or resource scaling'
                })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting combined recommendations: {e}")
            return []
    
    def get_agent_interaction_analysis(self) -> Dict[str, Any]:
        """Analyze agent interaction patterns."""
        try:
            interactions = self._coordination_stats['agent_interactions']
            
            if not interactions:
                return {'status': 'no_data'}
            
            total_interactions = sum(interactions.values())
            
            return {
                'total_interactions': total_interactions,
                'unique_agents': len(interactions),
                'avg_interactions_per_agent': total_interactions / len(interactions),
                'most_active_agent': max(interactions.items(), key=lambda x: x[1]),
                'least_active_agent': min(interactions.items(), key=lambda x: x[1]),
                'interaction_distribution': {
                    agent: (count / total_interactions) * 100
                    for agent, count in interactions.items()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in agent interaction analysis: {e}")
            return {'status': 'error'}
    
    def reset_metrics(self) -> None:
        """Reset all collected metrics (use with caution)."""
        try:
            self._coordination_stats = {
                'total_coordinations': 0,
                'successful_coordinations': 0,
                'coordination_quality_sum': 0.0,
                'agent_interactions': {},
                'coordination_types': {}
            }
            self._turn_metrics.clear()
            self.logger.info("Performance metrics reset")
        except Exception as e:
            self.logger.error(f"Error resetting metrics: {e}")