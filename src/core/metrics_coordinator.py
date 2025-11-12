#!/usr/bin/env python3
"""
Metrics Coordinator
===================

Extracted from IntegrationOrchestrator as part of God Class refactoring.
Manages performance metrics collection, processing, and reporting.

Responsibilities:
- Track operation counts and error rates
- Record response times and performance data
- Generate integration metrics snapshots
- Maintain metrics history
- Calculate health scores and averages

This class follows the Single Responsibility Principle by focusing solely on
metrics management, separate from integration orchestration.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class IntegrationMetrics:
    """Metrics for system integration performance."""

    timestamp: datetime = field(default_factory=datetime.now)
    traditional_operations: int = 0
    ai_enhanced_operations: int = 0
    fallback_activations: int = 0
    integration_errors: int = 0
    average_response_time: float = 0.0
    ai_enhancement_rate: float = 0.0  # Percentage of operations using AI
    system_health_score: float = 1.0  # Overall integration health (0.0-1.0)
    cross_system_events: int = 0
    performance_improvements: Dict[str, float] = field(default_factory=dict)


class MetricsCoordinator:
    """
    Coordinates performance metrics collection and reporting.

    This class encapsulates all metrics management logic, providing a clean
    interface for recording operations, tracking performance, and generating
    comprehensive metrics reports.
    """

    def __init__(self):
        """Initialize the metrics coordinator."""
        self.startup_time = datetime.now()
        self.operation_count = 0
        self.error_count = 0
        self.response_times: List[float] = []
        self.error_rates: List[float] = []
        self.metrics_history: List[IntegrationMetrics] = []

        logger.info("Metrics Coordinator initialized successfully")

    # ===================================================================
    # Metrics Recording Methods
    # ===================================================================

    def record_operation(self, response_time: float, success: bool = True):
        """
        Record an operation and its outcome.

        Args:
            response_time: Time taken to complete the operation (seconds)
            success: Whether the operation succeeded
        """
        self.operation_count += 1
        self.response_times.append(response_time)

        if not success:
            self.error_count += 1

    def record_error(self):
        """Record an error occurrence."""
        self.error_count += 1

    # ===================================================================
    # Metrics Calculation Methods
    # ===================================================================

    def get_uptime_seconds(self) -> float:
        """
        Calculate uptime in seconds.

        Returns:
            float: Seconds since initialization
        """
        return (datetime.now() - self.startup_time).total_seconds()

    def get_average_response_time(self, window_size: int = 100) -> float:
        """
        Calculate average response time over recent operations.

        Args:
            window_size: Number of recent operations to consider

        Returns:
            float: Average response time in seconds
        """
        if not self.response_times:
            return 0.0

        recent_times = self.response_times[-window_size:]
        return sum(recent_times) / len(recent_times)

    def get_error_rate(self) -> float:
        """
        Calculate current error rate.

        Returns:
            float: Error rate (0.0 - 1.0)
        """
        if self.operation_count == 0:
            return 0.0

        return self.error_count / self.operation_count

    def get_system_health_score(self) -> float:
        """
        Calculate overall system health score.

        Returns:
            float: Health score (0.0 - 1.0), where 1.0 is perfect health
        """
        error_rate = self.get_error_rate()
        # Convert error rate to health score (10% error = 0.0 health)
        return max(0.0, 1.0 - min(error_rate * 10, 1.0))

    # ===================================================================
    # Integration Metrics Generation
    # ===================================================================

    async def generate_integration_metrics(
        self, integration_mode: str = "ai_enhanced"
    ) -> IntegrationMetrics:
        """
        Generate current integration performance metrics snapshot.

        Args:
            integration_mode: Current integration mode for calculating enhancement rate

        Returns:
            IntegrationMetrics: Current metrics snapshot
        """
        current_time = datetime.now()

        # Calculate averages
        avg_response_time = self.get_average_response_time()
        error_rate = self.get_error_rate()
        health_score = self.get_system_health_score()

        # Determine AI enhancement rate based on mode
        ai_enhancement_rate = 0.0 if integration_mode == "traditional_only" else 0.8

        metrics = IntegrationMetrics(
            timestamp=current_time,
            traditional_operations=self.operation_count // 2,  # Approximate
            ai_enhanced_operations=self.operation_count // 2,  # Approximate
            average_response_time=avg_response_time,
            ai_enhancement_rate=ai_enhancement_rate,
            system_health_score=health_score,
            integration_errors=self.error_count,
        )

        self.metrics_history.append(metrics)
        return metrics

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary of current metrics for status reporting.

        Returns:
            Dictionary with key metrics
        """
        return {
            "uptime_seconds": self.get_uptime_seconds(),
            "total_operations": self.operation_count,
            "error_count": self.error_count,
            "error_rate": self.get_error_rate(),
            "average_response_time": self.get_average_response_time(),
            "system_health_score": self.get_system_health_score(),
            "metrics_history_size": len(self.metrics_history),
        }


__all__ = ["MetricsCoordinator", "IntegrationMetrics"]
