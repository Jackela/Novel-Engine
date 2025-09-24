"""
LLM Cost Tracker
================

Tracks and manages LLM usage costs and budgets for multi-agent coordination.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

__all__ = ["CostTracker"]


@dataclass
class CostTracker:
    """
    Tracks LLM costs and enforces budget limits.

    Responsibilities:
    - Monitor costs per request type
    - Enforce per-turn and total budget limits
    - Track token usage and cost efficiency
    - Provide cost optimization recommendations
    """

    max_cost_per_turn: float = 0.10
    max_total_cost: float = 1.0
    current_turn_cost: float = 0.0
    total_cost: float = 0.0
    costs_by_type: Dict[str, float] = field(default_factory=dict)
    tokens_by_type: Dict[str, int] = field(default_factory=dict)
    request_counts: Dict[str, int] = field(default_factory=dict)
    cost_history: List[Dict[str, Any]] = field(default_factory=list)
    logger: Optional[logging.Logger] = field(default=None, init=False)

    def __post_init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def update_cost(self, request_type: str, cost: float, tokens: int) -> bool:
        """
        Update cost tracking for a request.

        Args:
            request_type: Type of request ('dialogue', 'coordination', etc.)
            cost: Cost in USD
            tokens: Number of tokens used

        Returns:
            bool: True if under budget, False if budget exceeded
        """
        try:
            # Update costs
            self.current_turn_cost += cost
            self.total_cost += cost

            # Update by type
            if request_type not in self.costs_by_type:
                self.costs_by_type[request_type] = 0.0
                self.tokens_by_type[request_type] = 0
                self.request_counts[request_type] = 0

            self.costs_by_type[request_type] += cost
            self.tokens_by_type[request_type] += tokens
            self.request_counts[request_type] += 1

            # Record in history
            self.cost_history.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "request_type": request_type,
                    "cost": cost,
                    "tokens": tokens,
                    "cumulative_cost": self.total_cost,
                }
            )

            # Check budget limits
            if self.current_turn_cost > self.max_cost_per_turn:
                self.logger.warning(
                    f"Turn cost exceeded: ${self.current_turn_cost:.4f}> ${self.max_cost_per_turn:.4f}"
                )
                return False

            if self.total_cost > self.max_total_cost:
                self.logger.warning(
                    f"Total cost exceeded: ${self.total_cost:.4f}> ${self.max_total_cost:.4f}"
                )
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error updating cost tracking: {e}")
            return False

    def start_new_turn(self) -> None:
        """Reset turn-specific cost tracking."""
        self.current_turn_cost = 0.0

    def is_under_budget(self, estimated_additional_cost: float = 0.0) -> bool:
        """Check if we're under budget for additional spending."""
        projected_turn_cost = (
            self.current_turn_cost + estimated_additional_cost
        )
        projected_total_cost = self.total_cost + estimated_additional_cost

        return (
            projected_turn_cost <= self.max_cost_per_turn
            and projected_total_cost <= self.max_total_cost
        )

    def get_remaining_turn_budget(self) -> float:
        """Get remaining budget for current turn."""
        return max(0.0, self.max_cost_per_turn - self.current_turn_cost)

    def get_remaining_total_budget(self) -> float:
        """Get remaining total budget."""
        return max(0.0, self.max_total_cost - self.total_cost)

    def get_cost_efficiency_stats(self) -> Dict[str, Any]:
        """Get cost efficiency statistics."""
        try:
            stats = {
                "total_cost": self.total_cost,
                "current_turn_cost": self.current_turn_cost,
                "remaining_turn_budget": self.get_remaining_turn_budget(),
                "remaining_total_budget": self.get_remaining_total_budget(),
                "costs_by_type": self.costs_by_type.copy(),
                "tokens_by_type": self.tokens_by_type.copy(),
                "request_counts": self.request_counts.copy(),
                "cost_per_token_by_type": {},
                "avg_cost_per_request_by_type": {},
            }

            # Calculate efficiency metrics
            for request_type in self.costs_by_type:
                tokens = self.tokens_by_type.get(request_type, 0)
                cost = self.costs_by_type.get(request_type, 0)
                count = self.request_counts.get(request_type, 0)

                if tokens > 0:
                    stats["cost_per_token_by_type"][request_type] = (
                        cost / tokens
                    )

                if count > 0:
                    stats["avg_cost_per_request_by_type"][request_type] = (
                        cost / count
                    )

            return stats

        except Exception as e:
            self.logger.error(f"Error calculating cost efficiency stats: {e}")
            return {}

    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get cost optimization recommendations."""
        try:
            recommendations = []

            # Check high-cost request types
            total_requests = sum(self.request_counts.values())
            if total_requests > 0:
                for request_type, cost in self.costs_by_type.items():
                    cost_percentage = (
                        (cost / self.total_cost) * 100
                        if self.total_cost > 0
                        else 0
                    )
                    count_percentage = (
                        self.request_counts[request_type] / total_requests
                    ) * 100

                    if cost_percentage > 50 and count_percentage < 30:
                        recommendations.append(
                            {
                                "type": "high_cost_low_volume",
                                "request_type": request_type,
                                "issue": f"{request_type} requests consume {cost_percentage:.1f}% of budget but only {count_percentage:.1f}% of volume",
                                "suggestion": f"Consider batching or optimizing {request_type} requests",
                            }
                        )

            # Budget utilization check
            budget_utilization = (self.total_cost / self.max_total_cost) * 100
            if budget_utilization > 80:
                recommendations.append(
                    {
                        "type": "budget_warning",
                        "issue": f"Budget {budget_utilization:.1f}% utilized",
                        "suggestion": "Consider enabling cost optimization or increasing budget",
                    }
                )

            return recommendations

        except Exception as e:
            self.logger.error(
                f"Error generating optimization recommendations: {e}"
            )
            return []

    def reset_costs(self) -> None:
        """Reset all cost tracking (use with caution)."""
        self.current_turn_cost = 0.0
        self.total_cost = 0.0
        self.costs_by_type.clear()
        self.tokens_by_type.clear()
        self.request_counts.clear()
        self.cost_history.clear()
        self.logger.info("Cost tracking reset")
