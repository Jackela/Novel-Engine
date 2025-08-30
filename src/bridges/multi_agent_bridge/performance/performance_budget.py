"""
Performance Budget Manager
==========================

Manages performance budgets and time constraints for multi-agent coordination.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

__all__ = ["PerformanceBudget"]


@dataclass
class PerformanceBudget:
    """
    Manages performance budgets and timing constraints.

    Responsibilities:
    - Track turn timing and performance budgets
    - Monitor batch processing performance
    - Enforce time limits and optimize scheduling
    - Provide performance insights and recommendations
    """

    max_turn_time_seconds: float = 5.0
    max_batch_time_seconds: float = 2.0
    max_llm_wait_seconds: float = 10.0
    turn_start_time: Optional[float] = field(default=None, init=False)
    batch_times: List[float] = field(default_factory=list)
    llm_times: List[float] = field(default_factory=list)
    performance_history: List[Dict[str, Any]] = field(default_factory=list)
    logger: Optional[logging.Logger] = field(default=None, init=False)

    def __post_init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def start_turn(self) -> None:
        """Start timing a new turn."""
        self.turn_start_time = time.time()
        self.logger.debug("Turn timing started")

    def get_elapsed_turn_time(self) -> float:
        """Get elapsed time since turn start."""
        if self.turn_start_time is None:
            return 0.0
        return time.time() - self.turn_start_time

    def get_remaining_time(self) -> float:
        """Get remaining time in current turn."""
        elapsed = self.get_elapsed_turn_time()
        return max(0.0, self.max_turn_time_seconds - elapsed)

    def is_time_budget_exceeded(self) -> bool:
        """Check if time budget has been exceeded."""
        return self.get_elapsed_turn_time() > self.max_turn_time_seconds

    def is_batch_budget_available(self, estimated_batch_time: float = 0.0) -> bool:
        """Check if there's enough time budget for a batch operation."""
        remaining = self.get_remaining_time()
        required = estimated_batch_time + 0.5  # Add buffer
        return remaining >= required

    def record_batch_time(self, duration: float) -> None:
        """Record batch processing time."""
        self.batch_times.append(duration)

        # Keep only recent history
        if len(self.batch_times) > 100:
            self.batch_times = self.batch_times[-50:]

        if duration > self.max_batch_time_seconds:
            self.logger.warning(
                f"Batch time exceeded budget: {duration:.3f}s > {self.max_batch_time_seconds:.3f}s"
            )

    def record_llm_time(self, duration: float) -> None:
        """Record LLM processing time."""
        self.llm_times.append(duration)

        # Keep only recent history
        if len(self.llm_times) > 100:
            self.llm_times = self.llm_times[-50:]

        if duration > self.max_llm_wait_seconds:
            self.logger.warning(
                f"LLM time exceeded budget: {duration:.3f}s > {self.max_llm_wait_seconds:.3f}s"
            )

    def complete_turn(self) -> Dict[str, Any]:
        """Complete turn timing and record performance data."""
        if self.turn_start_time is None:
            return {}

        try:
            total_time = time.time() - self.turn_start_time

            performance_data = {
                "timestamp": datetime.now().isoformat(),
                "total_turn_time": total_time,
                "budget_exceeded": total_time > self.max_turn_time_seconds,
                "budget_utilization": (total_time / self.max_turn_time_seconds) * 100,
                "batch_operations": len(self.batch_times),
                "llm_operations": len(self.llm_times),
                "avg_batch_time": (
                    sum(self.batch_times) / len(self.batch_times)
                    if self.batch_times
                    else 0.0
                ),
                "avg_llm_time": (
                    sum(self.llm_times) / len(self.llm_times) if self.llm_times else 0.0
                ),
            }

            self.performance_history.append(performance_data)

            # Keep only recent history
            if len(self.performance_history) > 50:
                self.performance_history = self.performance_history[-25:]

            # Reset for next turn
            self.turn_start_time = None
            self.batch_times.clear()
            self.llm_times.clear()

            return performance_data

        except Exception as e:
            self.logger.error(f"Error completing turn performance tracking: {e}")
            return {}

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        try:
            if not self.performance_history:
                return {
                    "total_turns": 0,
                    "avg_turn_time": 0.0,
                    "budget_exceed_rate": 0.0,
                    "avg_budget_utilization": 0.0,
                }

            total_turns = len(self.performance_history)
            turn_times = [
                entry["total_turn_time"] for entry in self.performance_history
            ]
            budget_exceeds = sum(
                1 for entry in self.performance_history if entry["budget_exceeded"]
            )
            utilizations = [
                entry["budget_utilization"] for entry in self.performance_history
            ]

            stats = {
                "total_turns": total_turns,
                "avg_turn_time": sum(turn_times) / total_turns,
                "min_turn_time": min(turn_times),
                "max_turn_time": max(turn_times),
                "budget_exceed_rate": (budget_exceeds / total_turns) * 100,
                "avg_budget_utilization": sum(utilizations) / total_turns,
                "current_budget_seconds": self.max_turn_time_seconds,
                "performance_trend": self._calculate_performance_trend(),
            }

            return stats

        except Exception as e:
            self.logger.error(f"Error calculating performance stats: {e}")
            return {}

    def _calculate_performance_trend(self) -> str:
        """Calculate recent performance trend."""
        try:
            if len(self.performance_history) < 5:
                return "insufficient_data"

            # Compare recent 5 vs previous 5
            recent_avg = (
                sum(entry["total_turn_time"] for entry in self.performance_history[-5:])
                / 5
            )
            previous_avg = (
                sum(
                    entry["total_turn_time"]
                    for entry in self.performance_history[-10:-5]
                )
                / 5
            )

            if recent_avg < previous_avg * 0.9:
                return "improving"
            elif recent_avg > previous_avg * 1.1:
                return "degrading"
            else:
                return "stable"

        except Exception:
            return "unknown"

    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get performance optimization recommendations."""
        try:
            recommendations = []
            stats = self.get_performance_stats()

            if not stats or stats["total_turns"] == 0:
                return recommendations

            # Budget utilization recommendations
            if stats["avg_budget_utilization"] > 90:
                recommendations.append(
                    {
                        "type": "budget_optimization",
                        "issue": f"High budget utilization: {stats['avg_budget_utilization']:.1f}%",
                        "suggestion": "Consider enabling fast mode or increasing turn time budget",
                    }
                )
            elif stats["avg_budget_utilization"] < 50:
                recommendations.append(
                    {
                        "type": "budget_optimization",
                        "issue": f"Low budget utilization: {stats['avg_budget_utilization']:.1f}%",
                        "suggestion": "Budget could be reduced or more features enabled",
                    }
                )

            # Performance trend recommendations
            if stats["performance_trend"] == "degrading":
                recommendations.append(
                    {
                        "type": "performance_degradation",
                        "issue": "Performance degrading over recent turns",
                        "suggestion": "Check for resource constraints or optimize batch processing",
                    }
                )

            # Budget exceed rate recommendations
            if stats["budget_exceed_rate"] > 20:
                recommendations.append(
                    {
                        "type": "budget_exceeds",
                        "issue": f"Budget exceeded in {stats['budget_exceed_rate']:.1f}% of turns",
                        "suggestion": "Increase budget or enable more aggressive optimizations",
                    }
                )

            return recommendations

        except Exception as e:
            self.logger.error(f"Error generating performance recommendations: {e}")
            return []

    def adjust_budgets_for_performance(
        self, target_utilization: float = 80.0
    ) -> Dict[str, float]:
        """Automatically adjust budgets based on performance history."""
        try:
            stats = self.get_performance_stats()

            if not stats or stats["total_turns"] < 3:
                return {"status": "insufficient_data"}

            current_utilization = stats["avg_budget_utilization"]
            adjustment_factor = (
                target_utilization / current_utilization
                if current_utilization > 0
                else 1.0
            )

            # Apply reasonable bounds to adjustment
            adjustment_factor = max(0.8, min(1.5, adjustment_factor))

            new_turn_budget = self.max_turn_time_seconds * adjustment_factor
            new_batch_budget = self.max_batch_time_seconds * adjustment_factor
            new_llm_budget = self.max_llm_wait_seconds * adjustment_factor

            # Apply the adjustments
            self.max_turn_time_seconds = new_turn_budget
            self.max_batch_time_seconds = new_batch_budget
            self.max_llm_wait_seconds = new_llm_budget

            self.logger.info(f"Auto-adjusted budgets by factor {adjustment_factor:.2f}")

            return {
                "status": "adjusted",
                "adjustment_factor": adjustment_factor,
                "new_turn_budget": new_turn_budget,
                "new_batch_budget": new_batch_budget,
                "new_llm_budget": new_llm_budget,
            }

        except Exception as e:
            self.logger.error(f"Error adjusting budgets: {e}")
            return {"status": "error", "error": str(e)}
