"""
In-Memory Token Usage Repository Adapter

Warzone 4: AI Brain - BRAIN-034A
In-memory implementation of token usage persistence.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter implementing application port
- Article V (SOLID): SRP - in-memory storage only

Note: This implementation is suitable for development and testing.
For production, use a persistent database adapter.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from ...application.ports.i_token_usage_repository import (
    ITokenUsageRepository,
    RepositoryError,
    TokenUsageFilter,
    TokenUsageSummary,
)
from ...domain.models.token_usage import TokenUsage, TokenUsageStats

if TYPE_CHECKING:
    pass


logger = structlog.get_logger()


@dataclass
class InMemoryTokenUsageRepository(ITokenUsageRepository):
    """
    In-memory storage for token usage records.

    Why:
        - Fast, zero-dependency storage for development
        - Useful for testing without database setup
        - Provides reference implementation for repository interface

    Limitations:
        - Data lost on process restart
        - Not suitable for production use
        - No persistence guarantees

    Attributes:
        _max_records: Maximum number of records to keep (acts as retention limit)
        _records: List of stored TokenUsage records
        _lock: Async lock for thread-safe operations
    """

    _max_records: int = field(default=10000, kw_only=True)
    _records: list[TokenUsage] = field(default_factory=list, init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    async def save(self, usage: TokenUsage) -> None:
        """
        Save a token usage record.

        Args:
            usage: TokenUsage record to save

        Raises:
            RepositoryError: If save fails
        """
        try:
            async with self._lock:
                self._records.append(usage)

                # Enforce max records limit (FIFO eviction)
                if len(self._records) > self._max_records:
                    evicted = self._records.pop(0)
                    logger.debug(
                        "token_usage_evicted",
                        evicted_id=evicted.id,
                        current_count=len(self._records),
                    )

                logger.debug(
                    "token_usage_saved",
                    usage_id=usage.id,
                    provider=usage.provider,
                    model=usage.model_name,
                    tokens=usage.total_tokens,
                )

        except Exception as e:
            logger.error("token_usage_save_failed", usage_id=usage.id, error=str(e))
            raise RepositoryError(f"Failed to save token usage: {e}") from e

    async def save_batch(self, usages: list[TokenUsage]) -> None:
        """
        Save multiple token usage records efficiently.

        Args:
            usages: List of TokenUsage records to save

        Raises:
            RepositoryError: If save fails
        """
        if not usages:
            return

        try:
            async with self._lock:
                self._records.extend(usages)

                # Enforce max records limit
                while len(self._records) > self._max_records:
                    self._records.pop(0)

                logger.debug(
                    "token_usage_batch_saved",
                    count=len(usages),
                    total_records=len(self._records),
                )

        except Exception as e:
            logger.error(
                "token_usage_batch_save_failed", count=len(usages), error=str(e)
            )
            raise RepositoryError(f"Failed to save token usage batch: {e}") from e

    async def get_by_id(self, usage_id: str) -> TokenUsage | None:
        """
        Retrieve a usage record by ID.

        Args:
            usage_id: UUID of the usage record

        Returns:
            TokenUsage if found, None otherwise
        """
        async with self._lock:
            for record in self._records:
                if record.id == usage_id:
                    return record
            return None

    async def query(self, filters: TokenUsageFilter) -> list[TokenUsage]:
        """
        Query usage records with filters.

        Args:
            filters: Filter criteria for the query

        Returns:
            List of TokenUsage records matching the filters
        """
        async with self._lock:
            results = self._records.copy()

            # Apply filters
            if filters.provider:
                results = [r for r in results if r.provider == filters.provider]

            if filters.model_name:
                results = [r for r in results if r.model_name == filters.model_name]

            if filters.workspace_id:
                results = [r for r in results if r.workspace_id == filters.workspace_id]

            if filters.user_id:
                results = [r for r in results if r.user_id == filters.user_id]

            if filters.start_time:
                results = [r for r in results if r.timestamp >= filters.start_time]

            if filters.end_time:
                results = [r for r in results if r.timestamp <= filters.end_time]

            if filters.success_only:
                results = [r for r in results if r.success]

            if filters.min_tokens > 0:
                results = [r for r in results if r.total_tokens >= filters.min_tokens]

            # Sort by timestamp descending (most recent first)
            results.sort(key=lambda r: r.timestamp, reverse=True)

            # Apply pagination
            if filters.offset > 0:
                results = results[filters.offset :]

            if filters.limit > 0:
                results = results[: filters.limit]

            return results

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
        filters = TokenUsageFilter(
            start_time=start_time,
            end_time=end_time,
            provider=provider,
            model_name=model_name,
            workspace_id=workspace_id,
            limit=0,  # No limit for aggregation
        )

        usages = await self.query(filters)

        if not usages:
            return TokenUsageSummary(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                total_tokens=0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_cost=0.0,
                period_start=start_time,
                period_end=end_time,
            )

        total_requests = len(usages)
        successful_requests = sum(1 for u in usages if u.success)
        failed_requests = total_requests - successful_requests
        total_tokens = sum(u.total_tokens for u in usages)
        total_input_tokens = sum(u.input_tokens for u in usages)
        total_output_tokens = sum(u.output_tokens for u in usages)
        total_cost = float(sum(u.total_cost for u in usages))

        return TokenUsageSummary(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_tokens=total_tokens,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_cost=total_cost,
            period_start=start_time,
            period_end=end_time,
        )

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
        filters = TokenUsageFilter(
            start_time=start_time,
            end_time=end_time,
            provider=provider,
            model_name=model_name,
            workspace_id=workspace_id,
            limit=0,  # No limit for aggregation
        )

        usages = await self.query(filters)

        return TokenUsageStats.from_usages(
            usages=usages,
            provider=provider or "all",
            model_name=model_name or "all",
            workspace_id=workspace_id,
        )

    async def delete_old(self, cutoff_time: datetime) -> int:
        """
        Delete usage records older than the cutoff time.

        Args:
            cutoff_time: Delete records with timestamp < cutoff_time

        Returns:
            Number of records deleted
        """
        async with self._lock:
            original_count = len(self._records)
            self._records = [r for r in self._records if r.timestamp >= cutoff_time]
            deleted_count = original_count - len(self._records)

            if deleted_count > 0:
                logger.info(
                    "token_usage_deleted_old",
                    deleted_count=deleted_count,
                    cutoff_time=cutoff_time.isoformat(),
                    remaining_count=len(self._records),
                )

            return deleted_count

    async def count(self, filters: TokenUsageFilter | None = None) -> int:
        """
        Count usage records matching filters.

        Args:
            filters: Optional filter criteria (default: count all)

        Returns:
            Number of matching records
        """
        async with self._lock:
            if filters is None:
                return len(self._records)

            # Use query with no limit to count
            results = self._records.copy()

            if filters.provider:
                results = [r for r in results if r.provider == filters.provider]

            if filters.model_name:
                results = [r for r in results if r.model_name == filters.model_name]

            if filters.workspace_id:
                results = [r for r in results if r.workspace_id == filters.workspace_id]

            if filters.user_id:
                results = [r for r in results if r.user_id == filters.user_id]

            if filters.start_time:
                results = [r for r in results if r.timestamp >= filters.start_time]

            if filters.end_time:
                results = [r for r in results if r.timestamp <= filters.end_time]

            if filters.success_only:
                results = [r for r in results if r.success]

            if filters.min_tokens > 0:
                results = [r for r in results if r.total_tokens >= filters.min_tokens]

            return len(results)


def create_in_memory_token_usage_repository(
    max_records: int = 10000,
) -> InMemoryTokenUsageRepository:
    """
    Factory function to create an InMemoryTokenUsageRepository.

    Args:
        max_records: Maximum number of records to retain

    Returns:
        Configured InMemoryTokenUsageRepository instance
    """
    return InMemoryTokenUsageRepository(_max_records=max_records)


__all__ = [
    "InMemoryTokenUsageRepository",
    "create_in_memory_token_usage_repository",
]
