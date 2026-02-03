#!/usr/bin/env python3
"""
Cost Tracking Service Adapter for AI Gateway

Provides comprehensive cost monitoring, budget enforcement, and usage analytics
for LLM operations across different providers, models, and consumers.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Tuple

from ...application.ports.cost_tracking_port import (
    BudgetStatus,
    CostEntry,
    ICostTracker,
)
from ...domain.value_objects.common import ProviderId, TokenBudget


@dataclass
class UsageSummary:
    """
    Aggregated usage statistics for analysis and reporting.
    """

    period_start: datetime
    period_end: datetime

    total_requests: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    total_cost: Decimal = field(default_factory=lambda: Decimal("0"))
    input_cost: Decimal = field(default_factory=lambda: Decimal("0"))
    output_cost: Decimal = field(default_factory=lambda: Decimal("0"))

    provider_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    model_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    avg_cost_per_request: Optional[Decimal] = None
    avg_tokens_per_request: Optional[float] = None

    def __post_init__(self) -> None:
        """Calculate derived metrics."""
        if self.total_requests > 0:
            self.avg_cost_per_request = (
                self.total_cost / self.total_requests
            ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            self.avg_tokens_per_request = self.total_tokens / self.total_requests


class BudgetStatusHelper:
    """Helper class for creating BudgetStatus from budget and entries."""

    @staticmethod
    def from_budget_and_entries(
        budget: TokenBudget,
        entries: List[CostEntry],
        projection_factor: float = 1.2,
    ) -> BudgetStatus:
        """
        Create budget status from budget and cost entries.

        Args:
            budget: Token budget to analyze
            entries: Recent cost entries for the budget
            projection_factor: Factor for projecting future usage

        Returns:
            Current budget status with analysis
        """
        current_cost = sum(entry.total_cost for entry in entries)
        projected_cost = current_cost * Decimal(str(projection_factor))

        cost_limit = budget.cost_limit or Decimal("0")
        remaining_budget = max(Decimal("0"), cost_limit - current_cost)

        utilization = float(current_cost / cost_limit * 100) if cost_limit > 0 else 0.0
        is_exceeded = current_cost > cost_limit if cost_limit > 0 else False
        is_at_risk = utilization > 80.0

        return BudgetStatus(
            budget=budget,
            current_consumption=current_cost.quantize(Decimal("0.0001")),
            projected_consumption=projected_cost.quantize(Decimal("0.0001")),
            remaining_budget=remaining_budget.quantize(Decimal("0.0001")),
            utilization_percentage=round(utilization, 2),
            is_exceeded=is_exceeded,
            is_at_risk=is_at_risk,
            recent_entries=list(entries[-10:]),
        )


class DefaultCostTracker(ICostTracker):
    """
    Default in-memory implementation of cost tracking service.

    Provides comprehensive cost tracking with budget enforcement,
    usage analytics, and projection capabilities.
    """

    def __init__(self, retention_days: int = 90):
        """
        Initialize cost tracker.

        Args:
            retention_days: Days to retain cost entries
        """
        self._retention_days = retention_days
        self._cost_entries: List[CostEntry] = []
        self._budget_entries: Dict[str, List[CostEntry]] = {}
        self._lock = asyncio.Lock()

    async def record_cost_async(self, entry: CostEntry) -> None:
        """Record cost entry with automatic cleanup."""
        async with self._lock:
            self._cost_entries.append(entry)

            # Record in budget-specific tracking
            if entry.budget_id:
                if entry.budget_id not in self._budget_entries:
                    self._budget_entries[entry.budget_id] = []
                self._budget_entries[entry.budget_id].append(entry)

            # Periodic cleanup of old entries
            if len(self._cost_entries) % 100 == 0:
                await self._cleanup_old_entries()

    async def check_budget_async(
        self, budget: TokenBudget, estimated_cost: Decimal
    ) -> Tuple[bool, BudgetStatus]:
        """Check budget with comprehensive status analysis."""
        async with self._lock:
            # Get recent entries for this budget
            budget_entries = self._budget_entries.get(budget.budget_id, [])

            # Filter to recent entries (last 30 days)
            cutoff_time = datetime.now() - timedelta(days=30)
            recent_entries = [
                entry for entry in budget_entries if entry.timestamp > cutoff_time
            ]

            # Calculate current status
            status = BudgetStatusHelper.from_budget_and_entries(budget, recent_entries)

            # Check if estimated cost would exceed budget
            cost_limit = budget.cost_limit or Decimal("0")
            would_exceed = (status.current_consumption + estimated_cost) > cost_limit

            is_allowed = not would_exceed if cost_limit > 0 else True

            return is_allowed, status

    async def get_usage_summary_async(
        self,
        start_time: datetime,
        end_time: datetime,
        provider_id: Optional[ProviderId] = None,
        client_id: Optional[str] = None,
    ) -> UsageSummary:
        """Generate comprehensive usage summary."""
        async with self._lock:
            # Filter entries by time range and optional filters
            filtered_entries = [
                entry
                for entry in self._cost_entries
                if start_time <= entry.timestamp <= end_time
            ]

            if provider_id:
                filtered_entries = [
                    entry
                    for entry in filtered_entries
                    if entry.provider_id.provider_name == provider_id.provider_name
                ]

            if client_id:
                filtered_entries = [
                    entry for entry in filtered_entries if entry.client_id == client_id
                ]

            # Calculate aggregations
            total_requests = len(filtered_entries)
            total_tokens = sum(entry.total_tokens for entry in filtered_entries)
            input_tokens = sum(entry.input_tokens for entry in filtered_entries)
            output_tokens = sum(entry.output_tokens for entry in filtered_entries)

            total_cost = sum(entry.total_cost for entry in filtered_entries)
            input_cost = sum(entry.input_cost for entry in filtered_entries)
            output_cost = sum(entry.output_cost for entry in filtered_entries)

            # Provider breakdown
            provider_breakdown = {}
            for entry in filtered_entries:
                provider_name = entry.provider_id.provider_name
                if provider_name not in provider_breakdown:
                    provider_breakdown[provider_name] = {
                        "requests": 0,
                        "tokens": 0,
                        "cost": Decimal("0"),
                    }

                provider_breakdown[provider_name]["requests"] += 1
                provider_breakdown[provider_name]["tokens"] += entry.total_tokens
                provider_breakdown[provider_name]["cost"] += entry.total_cost

            # Model breakdown
            model_breakdown = {}
            for entry in filtered_entries:
                model_name = entry.model_id.model_name
                if model_name not in model_breakdown:
                    model_breakdown[model_name] = {
                        "requests": 0,
                        "tokens": 0,
                        "cost": Decimal("0"),
                    }

                model_breakdown[model_name]["requests"] += 1
                model_breakdown[model_name]["tokens"] += entry.total_tokens
                model_breakdown[model_name]["cost"] += entry.total_cost

            return UsageSummary(
                period_start=start_time,
                period_end=end_time,
                total_requests=total_requests,
                total_tokens=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_cost=total_cost,
                input_cost=input_cost,
                output_cost=output_cost,
                provider_breakdown=provider_breakdown,
                model_breakdown=model_breakdown,
            )

    async def get_budget_status_async(self, budget_id: str) -> Optional[BudgetStatus]:
        """Get current budget status with analysis."""
        async with self._lock:
            if budget_id not in self._budget_entries:
                return None

            entries = self._budget_entries[budget_id]
            if not entries:
                return None

            # Get the most recent budget from entries (assuming consistent budget)
            max(entries, key=lambda e: e.timestamp)

            # Create a TokenBudget for analysis (simplified)
            # In a real implementation, this would be stored separately
            budget = TokenBudget(
                budget_id=budget_id,
                allocated_tokens=100000,  # Would be retrieved from storage
                cost_limit=Decimal("100.00"),  # Would be retrieved from storage
            )

            return BudgetStatusHelper.from_budget_and_entries(budget, entries)

    async def get_cost_projection_async(
        self, budget_id: str, days_ahead: int = 30
    ) -> Dict[str, Any]:
        """Generate cost projection based on historical usage."""
        async with self._lock:
            entries = self._budget_entries.get(budget_id, [])
            if not entries:
                return {
                    "projection": Decimal("0"),
                    "confidence": "low",
                    "daily_average": Decimal("0"),
                    "trend": "unknown",
                }

            # Calculate daily usage for last 30 days
            cutoff_time = datetime.now() - timedelta(days=30)
            recent_entries = [
                entry for entry in entries if entry.timestamp > cutoff_time
            ]

            if not recent_entries:
                return {
                    "projection": Decimal("0"),
                    "confidence": "low",
                    "daily_average": Decimal("0"),
                    "trend": "unknown",
                }

            # Calculate daily averages
            total_cost = sum(entry.total_cost for entry in recent_entries)
            days_with_data = len(
                set(entry.timestamp.date() for entry in recent_entries)
            )
            daily_average = total_cost / max(1, days_with_data)

            # Simple linear projection
            projected_cost = daily_average * days_ahead

            # Determine confidence based on data consistency
            confidence = (
                "high"
                if days_with_data > 20
                else "medium"
                if days_with_data > 10
                else "low"
            )

            # Simple trend analysis (compare first half vs second half)
            mid_point = len(recent_entries) // 2
            if mid_point > 0:
                first_half_avg = (
                    sum(entry.total_cost for entry in recent_entries[:mid_point])
                    / mid_point
                )
                second_half_avg = sum(
                    entry.total_cost for entry in recent_entries[mid_point:]
                ) / (len(recent_entries) - mid_point)

                if second_half_avg > first_half_avg * 1.1:
                    trend = "increasing"
                elif second_half_avg < first_half_avg * 0.9:
                    trend = "decreasing"
                else:
                    trend = "stable"
            else:
                trend = "unknown"

            return {
                "projection": projected_cost.quantize(Decimal("0.0001")),
                "confidence": confidence,
                "daily_average": daily_average.quantize(Decimal("0.0001")),
                "trend": trend,
                "data_points": len(recent_entries),
                "period_days": days_with_data,
            }

    async def _cleanup_old_entries(self) -> None:
        """Remove entries older than retention period."""
        cutoff_time = datetime.now() - timedelta(days=self._retention_days)

        # Clean main entries list
        self._cost_entries = [
            entry for entry in self._cost_entries if entry.timestamp > cutoff_time
        ]

        # Clean budget-specific entries
        for budget_id in list(self._budget_entries.keys()):
            self._budget_entries[budget_id] = [
                entry
                for entry in self._budget_entries[budget_id]
                if entry.timestamp > cutoff_time
            ]

            # Remove empty budget entries
            if not self._budget_entries[budget_id]:
                del self._budget_entries[budget_id]
