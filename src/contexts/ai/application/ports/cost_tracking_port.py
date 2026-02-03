#!/usr/bin/env python3
"""
Cost Tracking Service Port for AI Gateway

Defines the abstract interface for cost monitoring and budget enforcement.
Infrastructure adapters implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, Optional, Tuple
from uuid import UUID, uuid4

from ...domain.services.llm_provider import LLMRequest, LLMResponse
from ...domain.value_objects.common import ModelId, ProviderId, TokenBudget


@dataclass(frozen=True)
class CostEntry:
    """
    Immutable record of a cost-incurring operation.

    Tracks the cost details for individual LLM operations
    including provider, model, token usage, and calculated costs.
    """

    entry_id: UUID
    timestamp: datetime
    provider_id: ProviderId
    model_id: ModelId
    request_id: UUID
    operation_type: str

    input_tokens: int
    output_tokens: int
    total_tokens: int

    input_cost: Decimal
    output_cost: Decimal
    total_cost: Decimal

    budget_id: Optional[str] = None
    client_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate cost entry data integrity."""
        if self.input_tokens < 0:
            raise ValueError("input_tokens cannot be negative")
        if self.output_tokens < 0:
            raise ValueError("output_tokens cannot be negative")
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("total_tokens must equal input_tokens + output_tokens")

        if self.input_cost < 0:
            raise ValueError("input_cost cannot be negative")
        if self.output_cost < 0:
            raise ValueError("output_cost cannot be negative")
        if abs(self.total_cost - (self.input_cost + self.output_cost)) > Decimal(
            "0.0001"
        ):
            raise ValueError("total_cost must equal input_cost + output_cost")

    @classmethod
    def from_request_response(
        cls,
        request: LLMRequest,
        response: LLMResponse,
        budget_id: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> "CostEntry":
        """
        Create cost entry from request/response pair.

        Args:
            request: Original LLM request
            response: LLM response with usage statistics
            budget_id: Associated budget identifier
            client_id: Client identifier for attribution

        Returns:
            Cost entry with calculated costs
        """
        # Extract token usage from response
        usage_stats = response.usage_stats or {}
        input_tokens = usage_stats.get("input_tokens", 0)
        output_tokens = usage_stats.get("output_tokens", 0)
        total_tokens = usage_stats.get("total_tokens", input_tokens + output_tokens)

        # Calculate costs using model pricing
        model_id = request.model_id
        input_cost = Decimal("0")
        output_cost = Decimal("0")

        if model_id.cost_per_input_token:
            input_cost = Decimal(str(input_tokens)) * model_id.cost_per_input_token

        if model_id.cost_per_output_token:
            output_cost = Decimal(str(output_tokens)) * model_id.cost_per_output_token

        # Round to reasonable precision (4 decimal places)
        input_cost = input_cost.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        output_cost = output_cost.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        total_cost = input_cost + output_cost

        return cls(
            entry_id=uuid4(),
            timestamp=datetime.now(),
            provider_id=model_id.provider_id,
            model_id=model_id,
            request_id=request.request_id,
            operation_type=request.request_type.value,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            budget_id=budget_id,
            client_id=client_id,
            metadata=request.metadata.copy() if request.metadata else {},
        )


@dataclass
class BudgetStatus:
    """
    Current status of a token budget including consumption and projections.
    """

    budget: TokenBudget
    current_consumption: Decimal
    projected_consumption: Decimal
    remaining_budget: Decimal
    utilization_percentage: float
    is_exceeded: bool
    is_at_risk: bool  # >80% utilization

    recent_entries: list = field(default_factory=list)


class ICostTracker(ABC):
    """
    Abstract interface for AI Gateway cost tracking service.

    Provides cost monitoring, budget enforcement, and usage analytics
    for LLM operations across providers and consumers.
    """

    @abstractmethod
    async def record_cost_async(self, entry: CostEntry) -> None:
        """
        Record cost entry for tracking and analysis.

        Args:
            entry: Cost entry to record
        """

    @abstractmethod
    async def check_budget_async(
        self, budget: TokenBudget, estimated_cost: Decimal
    ) -> Tuple[bool, BudgetStatus]:
        """
        Check if operation is within budget limits.

        Args:
            budget: Budget to check against
            estimated_cost: Estimated cost of operation

        Returns:
            Tuple of (is_allowed, budget_status)
        """

    @abstractmethod
    async def get_usage_summary_async(
        self,
        start_time: datetime,
        end_time: datetime,
        provider_id: Optional[ProviderId] = None,
        client_id: Optional[str] = None,
    ) -> Any:
        """
        Get aggregated usage summary for time period.

        Args:
            start_time: Start of analysis period
            end_time: End of analysis period
            provider_id: Optional provider filter
            client_id: Optional client filter

        Returns:
            Usage summary with aggregated metrics
        """

    @abstractmethod
    async def get_budget_status_async(self, budget_id: str) -> Optional[BudgetStatus]:
        """
        Get current status of specific budget.

        Args:
            budget_id: Budget identifier

        Returns:
            Budget status if found, None otherwise
        """

    @abstractmethod
    async def get_cost_projection_async(
        self, budget_id: str, days_ahead: int = 30
    ) -> Dict[str, Any]:
        """
        Get cost projection for budget based on historical usage.

        Args:
            budget_id: Budget identifier
            days_ahead: Days to project into future

        Returns:
            Dictionary with projection data and confidence metrics
        """
