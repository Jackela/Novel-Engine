"""
Token Usage Repository Port

Warzone 4: AI Brain - BRAIN-034A
Defines the interface for token usage persistence.

Constitution Compliance:
- Article II (Hexagonal): Application port defining repository contract
- Article V (SOLID): Dependency Inversion - services depend on this abstraction
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ...domain.models.token_usage import TokenUsage, TokenUsageStats


@dataclass
class TokenUsageFilter:
    """
    Filter criteria for token usage queries.

    Attributes:
        provider: Optional LLM provider filter
        model_name: Optional model name filter
        workspace_id: Optional workspace filter
        user_id: Optional user filter
        start_time: Optional start of time range
        end_time: Optional end of time range
        success_only: Only include successful requests
        min_tokens: Minimum token count filter
        limit: Maximum results to return
        offset: Result offset for pagination
    """

    provider: Optional[str] = None
    model_name: Optional[str] = None
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    success_only: bool = False
    min_tokens: int = 0
    limit: int = 1000
    offset: int = 0


@dataclass
class TokenUsageSummary:
    """
    Summary of token usage for a time period.

    Attributes:
        total_requests: Total number of requests
        successful_requests: Number of successful requests
        failed_requests: Number of failed requests
        total_tokens: Total tokens consumed
        total_input_tokens: Total input tokens
        total_output_tokens: Total output tokens
        total_cost: Total cost in USD
        period_start: Start of aggregation period
        period_end: End of aggregation period
    """

    total_requests: int
    successful_requests: int
    failed_requests: int
    total_tokens: int
    total_input_tokens: int
    total_output_tokens: int
    total_cost: float
    period_start: datetime
    period_end: datetime

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def avg_tokens_per_request(self) -> float:
        """Calculate average tokens per request."""
        if self.total_requests == 0:
            return 0.0
        return self.total_tokens / self.total_requests

    @property
    def avg_cost_per_request(self) -> float:
        """Calculate average cost per request."""
        if self.total_requests == 0:
            return 0.0
        return self.total_cost / self.total_requests


class ITokenUsageRepository(ABC):
    """
    Repository interface for token usage persistence.

    Why port not repository:
        Defines the contract that infrastructure adapters must implement.
        Application layer depends on this abstraction, not concrete implementations.

    Implementations must:
        - Store usage records efficiently for high-volume writes
        - Support time-range queries for analytics
        - Support aggregation by provider, model, workspace
        - Handle concurrent writes safely
    """

    @abstractmethod
    async def save(self, usage: TokenUsage) -> None:
        """
        Save a token usage record.

        Args:
            usage: TokenUsage record to save

        Raises:
            RepositoryError: If save fails
        """

    @abstractmethod
    async def save_batch(self, usages: list[TokenUsage]) -> None:
        """
        Save multiple token usage records efficiently.

        Args:
            usages: List of TokenUsage records to save

        Raises:
            RepositoryError: If save fails
        """

    @abstractmethod
    async def get_by_id(self, usage_id: str) -> TokenUsage | None:
        """
        Retrieve a usage record by ID.

        Args:
            usage_id: UUID of the usage record

        Returns:
            TokenUsage if found, None otherwise
        """

    @abstractmethod
    async def query(self, filters: TokenUsageFilter) -> list[TokenUsage]:
        """
        Query usage records with filters.

        Args:
            filters: Filter criteria for the query

        Returns:
            List of TokenUsage records matching the filters
        """

    @abstractmethod
    async def get_summary(
        self,
        start_time: datetime,
        end_time: datetime,
        provider: str | None = None,
        model_name: str | None = None,
        workspace_id: str | None = None,
    ) -> TokenUsageSummary:
        """
        Get aggregated usage summary for a time period.

        Args:
            start_time: Start of aggregation period
            end_time: End of aggregation period
            provider: Optional provider filter
            model_name: Optional model filter
            workspace_id: Optional workspace filter

        Returns:
            Aggregated TokenUsageSummary
        """

    @abstractmethod
    async def get_stats(
        self,
        start_time: datetime,
        end_time: datetime,
        provider: str | None = None,
        model_name: str | None = None,
        workspace_id: str | None = None,
    ) -> TokenUsageStats:
        """
        Get detailed statistics for a time period.

        Args:
            start_time: Start of aggregation period
            end_time: End of aggregation period
            provider: Optional provider filter
            model_name: Optional model filter
            workspace_id: Optional workspace filter

        Returns:
            Detailed TokenUsageStats
        """

    @abstractmethod
    async def delete_old(self, cutoff_time: datetime) -> int:
        """
        Delete usage records older than the cutoff time.

        Args:
            cutoff_time: Delete records with timestamp < cutoff_time

        Returns:
            Number of records deleted
        """

    @abstractmethod
    async def count(self, filters: TokenUsageFilter | None = None) -> int:
        """
        Count usage records matching filters.

        Args:
            filters: Optional filter criteria (default: count all)

        Returns:
            Number of matching records
        """


class RepositoryError(Exception):
    """Base exception for repository errors."""

    pass


__all__ = [
    "ITokenUsageRepository",
    "TokenUsageFilter",
    "TokenUsageSummary",
    "RepositoryError",
]
