"""Monitoring Module.

Tracks performance metrics, costs, and bridge health.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .types import CostTracker, PerformanceBudget


class BridgeMonitor:
    """Monitors bridge performance and health."""

    def __init__(
        self,
        cost_tracker: CostTracker,
        performance_budget: PerformanceBudget,
        coordination_stats: Dict[str, Any],
    ) -> None:
        """Initialize the bridge monitor.

        Args:
            cost_tracker: Cost tracking instance
            performance_budget: Performance budget instance
            coordination_stats: Coordination statistics dict
        """
        self.cost_tracker = cost_tracker
        self.performance_budget = performance_budget
        self.coordination_stats = coordination_stats

    def get_budget_status(self) -> Dict[str, Any]:
        """Get current budget status."""
        hour_usage = self.cost_tracker.current_hour_spend / max(
            0.01, self.cost_tracker.hourly_budget
        )
        day_usage = self.cost_tracker.current_day_spend / max(
            0.01, self.cost_tracker.daily_budget
        )

        return {
            "hourly_usage_percent": min(100, hour_usage * 100),
            "daily_usage_percent": min(100, day_usage * 100),
            "remaining_hourly_budget": max(
                0,
                self.cost_tracker.hourly_budget - self.cost_tracker.current_hour_spend,
            ),
            "remaining_daily_budget": max(
                0, self.cost_tracker.daily_budget - self.cost_tracker.current_day_spend
            ),
            "total_requests_today": self.cost_tracker.total_requests,
            "average_cost_per_request": self.cost_tracker.average_cost_per_request,
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance and cost metrics."""
        budget_status = self.get_budget_status()

        # Calculate performance scores
        avg_batch_time = sum(self.performance_budget.batch_timings[-10:]) / max(
            1, len(self.performance_budget.batch_timings[-10:])
        )
        avg_llm_time = sum(self.performance_budget.llm_call_timings[-10:]) / max(
            1, len(self.performance_budget.llm_call_timings[-10:])
        )

        performance_score = 1.0
        if avg_batch_time > self.performance_budget.max_batch_time:
            performance_score *= 0.8
        if avg_llm_time > self.performance_budget.max_llm_call_time:
            performance_score *= 0.8
        if self.performance_budget.budget_violations > 0:
            performance_score *= max(
                0.3, 1.0 - (self.performance_budget.budget_violations * 0.1)
            )

        self.coordination_stats["performance_score"] = performance_score

        return {
            "coordination_stats": self.coordination_stats.copy(),
            "budget_status": budget_status,
            "performance_metrics": {
                "average_batch_time": avg_batch_time,
                "average_llm_call_time": avg_llm_time,
                "budget_violations": self.performance_budget.budget_violations,
                "performance_score": performance_score,
                "remaining_turn_time": self.performance_budget.get_remaining_time(),
            },
            "cost_breakdown": self.cost_tracker.cost_by_request_type.copy(),
            "efficiency_metrics": {
                "batch_utilization": self.coordination_stats.get(
                    "average_batch_size", 0
                )
                / max(1, self.llm_config.max_batch_size if hasattr(self, 'llm_config') else 5),
                "priority_bypass_rate": self.coordination_stats.get(
                    "priority_bypasses", 0
                )
                / max(1, self.coordination_stats.get("total_llm_calls", 1)),
                "cost_per_quality_point": self.coordination_stats.get(
                    "cost_per_request", 0
                )
                / max(0.1, self.coordination_stats.get("dialogue_quality_score", 0.1)),
            },
        }

    def check_budget_availability(self, estimated_cost: float) -> bool:
        """Check if request can proceed within budget constraints."""
        current_hour_remaining = (
            self.cost_tracker.hourly_budget - self.cost_tracker.current_hour_spend
        )
        current_day_remaining = (
            self.cost_tracker.daily_budget - self.cost_tracker.current_day_spend
        )

        return (
            estimated_cost <= current_hour_remaining
            and estimated_cost <= current_day_remaining
        )

    def record_cost(self, request_type: str, cost: float, tokens: int) -> bool:
        """Record cost and return budget status."""
        return self.cost_tracker.update_cost(request_type, cost, tokens)

    def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the monitoring system."""
        budget_status = self.get_budget_status()

        return {
            "healthy": True,
            "budget_critical": budget_status["hourly_usage_percent"] > 90
            or budget_status["daily_usage_percent"] > 90,
            "budget_warning": budget_status["hourly_usage_percent"] > 75
            or budget_status["daily_usage_percent"] > 75,
            "metrics": budget_status,
        }


__all__ = ["BridgeMonitor"]
