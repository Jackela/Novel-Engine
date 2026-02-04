"""
In-Memory Prompt Usage Repository Adapter

Warzone 4: AI Brain - BRAIN-022A
In-memory implementation of IPromptUsageRepository for testing and development.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter implements application port
- Article I (DDD): No business logic, only persistence
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Optional

from ...application.ports.i_prompt_usage_repository import (
    IPromptUsageRepository,
    PromptUsageRepositoryError,
)
from ...domain.models.prompt_usage import PromptUsage, PromptUsageStats


def _utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class InMemoryPromptUsageRepository(IPromptUsageRepository):
    """
    In-memory implementation of prompt usage repository.

    Why OrderedDict:
        Maintains insertion order for predictable test results.
        Provides O(1) lookups by ID.

    Why thread-safe:
        Uses asyncio.Lock for concurrent access protection.

    Attributes:
        _usages: Storage for usage events (ID -> PromptUsage)
        _lock: Async lock for thread-safe operations
        _prompt_index: Index for quick prompt-based lookups
        _workspace_index: Index for quick workspace-based lookups
        _user_index: Index for quick user-based lookups
    """

    def __init__(self, max_entries: int = 10000) -> None:
        """
        Initialize the in-memory repository.

        Args:
            max_entries: Maximum number of usage events to store (LRU eviction)
        """
        self._usages: OrderedDict[str, PromptUsage] = OrderedDict()
        self._lock = asyncio.Lock()
        self._max_entries = max_entries

        # Indexes for efficient querying
        self._prompt_index: dict[str, list[str]] = {}  # prompt_id -> [usage_ids]
        self._workspace_index: dict[str, list[str]] = {}  # workspace_id -> [usage_ids]
        self._user_index: dict[str, list[str]] = {}  # user_id -> [usage_ids]

    async def record(self, usage: PromptUsage) -> str:
        """
        Record a prompt usage event.

        Args:
            usage: PromptUsage entity to record

        Returns:
            The ID of the recorded usage event

        Raises:
            PromptUsageRepositoryError: If record operation fails
        """
        async with self._lock:
            try:
                # Check if we need to evict (LRU)
                if len(self._usages) >= self._max_entries:
                    # Remove oldest entry
                    self._usages.popitem(last=False)

                # Store usage
                self._usages[usage.id] = usage

                # Update indexes
                self._update_indexes(usage)

                return usage.id

            except Exception as e:
                raise PromptUsageRepositoryError(f"Failed to record usage: {e}") from e

    async def record_batch(self, usages: list[PromptUsage]) -> list[str]:
        """
        Record multiple prompt usage events efficiently.

        Args:
            usages: List of PromptUsage entities to record

        Returns:
            List of IDs of the recorded usage events

        Raises:
            PromptUsageRepositoryError: If batch record operation fails
        """
        async with self._lock:
            try:
                ids = []
                for usage in usages:
                    # Check if we need to evict (LRU)
                    if len(self._usages) >= self._max_entries:
                        self._usages.popitem(last=False)

                    self._usages[usage.id] = usage
                    self._update_indexes(usage)
                    ids.append(usage.id)

                return ids

            except Exception as e:
                raise PromptUsageRepositoryError(f"Failed to record batch: {e}") from e

    async def get_stats(
        self,
        prompt_id: str,
        workspace_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> PromptUsageStats:
        """
        Get aggregated statistics for a prompt template.

        Args:
            prompt_id: ID of the prompt template
            workspace_id: Optional filter by workspace
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            Aggregated PromptUsageStats

        Raises:
            PromptUsageRepositoryError: If stats retrieval fails
        """
        async with self._lock:
            try:
                # Get usages for the prompt
                usage_ids = self._prompt_index.get(prompt_id, [])
                usages = [self._usages[uid] for uid in usage_ids if uid in self._usages]

                # Filter by workspace
                if workspace_id is not None:
                    usages = [u for u in usages if u.workspace_id == workspace_id]

                # Filter by date range
                if start_date is not None:
                    usages = [u for u in usages if u.timestamp >= start_date]
                if end_date is not None:
                    usages = [u for u in usages if u.timestamp <= end_date]

                return PromptUsageStats.from_usages(usages)

            except Exception as e:
                raise PromptUsageRepositoryError(f"Failed to get stats: {e}") from e

    async def get_usage_by_id(self, usage_id: str) -> Optional[PromptUsage]:
        """
        Retrieve a usage event by its unique identifier.

        Args:
            usage_id: Unique identifier of the usage event

        Returns:
            PromptUsage if found, None otherwise

        Raises:
            PromptUsageRepositoryError: If retrieval operation fails
        """
        async with self._lock:
            try:
                return self._usages.get(usage_id)
            except Exception as e:
                raise PromptUsageRepositoryError(f"Failed to get usage by id: {e}") from e

    async def list_by_prompt(
        self,
        prompt_id: str,
        limit: int = 100,
        offset: int = 0,
        workspace_id: Optional[str] = None,
    ) -> list[PromptUsage]:
        """
        List usage events for a specific prompt template.

        Args:
            prompt_id: ID of the prompt template
            limit: Maximum number of results
            offset: Number of results to skip
            workspace_id: Optional filter by workspace

        Returns:
            List of PromptUsage entities ordered by timestamp (descending)

        Raises:
            PromptUsageRepositoryError: If listing operation fails
        """
        async with self._lock:
            try:
                usage_ids = self._prompt_index.get(prompt_id, [])
                usages = [self._usages[uid] for uid in usage_ids if uid in self._usages]

                # Filter by workspace
                if workspace_id is not None:
                    usages = [u for u in usages if u.workspace_id == workspace_id]

                # Sort by timestamp descending
                usages.sort(key=lambda u: u.timestamp, reverse=True)

                # Apply pagination
                start = offset
                end = start + limit
                return usages[start:end]

            except Exception as e:
                raise PromptUsageRepositoryError(f"Failed to list by prompt: {e}") from e

    async def list_by_workspace(
        self,
        workspace_id: str,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
    ) -> list[PromptUsage]:
        """
        List usage events for a specific workspace.

        Args:
            workspace_id: Workspace identifier
            limit: Maximum number of results
            offset: Number of results to skip
            start_date: Optional filter by start date

        Returns:
            List of PromptUsage entities ordered by timestamp (descending)

        Raises:
            PromptUsageRepositoryError: If listing operation fails
        """
        async with self._lock:
            try:
                usage_ids = self._workspace_index.get(workspace_id, [])
                usages = [self._usages[uid] for uid in usage_ids if uid in self._usages]

                # Filter by date
                if start_date is not None:
                    usages = [u for u in usages if u.timestamp >= start_date]

                # Sort by timestamp descending
                usages.sort(key=lambda u: u.timestamp, reverse=True)

                # Apply pagination
                start = offset
                end = start + limit
                return usages[start:end]

            except Exception as e:
                raise PromptUsageRepositoryError(f"Failed to list by workspace: {e}") from e

    async def list_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
    ) -> list[PromptUsage]:
        """
        List usage events for a specific user.

        Args:
            user_id: User identifier
            limit: Maximum number of results
            offset: Number of results to skip
            start_date: Optional filter by start date

        Returns:
            List of PromptUsage entities ordered by timestamp (descending)

        Raises:
            PromptUsageRepositoryError: If listing operation fails
        """
        async with self._lock:
            try:
                usage_ids = self._user_index.get(user_id, [])
                usages = [self._usages[uid] for uid in usage_ids if uid in self._usages]

                # Filter by date
                if start_date is not None:
                    usages = [u for u in usages if u.timestamp >= start_date]

                # Sort by timestamp descending
                usages.sort(key=lambda u: u.timestamp, reverse=True)

                # Apply pagination
                start = offset
                end = start + limit
                return usages[start:end]

            except Exception as e:
                raise PromptUsageRepositoryError(f"Failed to list by user: {e}") from e

    async def list_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000,
        offset: int = 0,
        workspace_id: Optional[str] = None,
    ) -> list[PromptUsage]:
        """
        List usage events within a date range.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            limit: Maximum number of results
            offset: Number of results to skip
            workspace_id: Optional filter by workspace

        Returns:
            List of PromptUsage entities ordered by timestamp (descending)

        Raises:
            PromptUsageRepositoryError: If listing operation fails
        """
        async with self._lock:
            try:
                usages = list(self._usages.values())

                # Filter by date range
                usages = [
                    u for u in usages
                    if start_date <= u.timestamp <= end_date
                ]

                # Filter by workspace
                if workspace_id is not None:
                    usages = [u for u in usages if u.workspace_id == workspace_id]

                # Sort by timestamp descending
                usages.sort(key=lambda u: u.timestamp, reverse=True)

                # Apply pagination
                start = offset
                end = start + limit
                return usages[start:end]

            except Exception as e:
                raise PromptUsageRepositoryError(f"Failed to list by date range: {e}") from e

    async def delete_old_usages(
        self, cutoff_date: datetime, workspace_id: Optional[str] = None
    ) -> int:
        """
        Delete usage events older than a cutoff date.

        Args:
            cutoff_date: Delete usages older than this date
            workspace_id: Optional filter by workspace

        Returns:
            Number of usage events deleted

        Raises:
            PromptUsageRepositoryError: If deletion fails
        """
        async with self._lock:
            try:
                to_delete = []

                for usage_id, usage in self._usages.items():
                    if usage.timestamp < cutoff_date:
                        if workspace_id is None or usage.workspace_id == workspace_id:
                            to_delete.append(usage_id)

                for usage_id in to_delete:
                    usage = self._usages[usage_id]
                    self._remove_from_indexes(usage)
                    del self._usages[usage_id]

                return len(to_delete)

            except Exception as e:
                raise PromptUsageRepositoryError(f"Failed to delete old usages: {e}") from e

    async def count(
        self,
        prompt_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> int:
        """
        Count total number of usage events.

        Args:
            prompt_id: Optional filter by prompt ID
            workspace_id: Optional filter by workspace

        Returns:
            Total count of usage events

        Raises:
            PromptUsageRepositoryError: If count operation fails
        """
        async with self._lock:
            try:
                if prompt_id is not None and workspace_id is not None:
                    # Filter by both
                    usage_ids = self._prompt_index.get(prompt_id, [])
                    return sum(
                        1
                        for uid in usage_ids
                        if uid in self._usages and self._usages[uid].workspace_id == workspace_id
                    )
                elif prompt_id is not None:
                    # Filter by prompt only
                    return len(self._prompt_index.get(prompt_id, []))
                elif workspace_id is not None:
                    # Filter by workspace only
                    return len(self._workspace_index.get(workspace_id, []))
                else:
                    # No filter
                    return len(self._usages)

            except Exception as e:
                raise PromptUsageRepositoryError(f"Failed to count usages: {e}") from e

    async def update_rating(self, usage_id: str, rating: float) -> bool:
        """
        Update the user rating for a usage event.

        Args:
            usage_id: ID of the usage event
            rating: New rating value (1-5)

        Returns:
            True if updated, False if not found

        Raises:
            PromptUsageRepositoryError: If update operation fails
        """
        async with self._lock:
            try:
                if usage_id not in self._usages:
                    return False

                usage = self._usages[usage_id]
                # Create new usage with updated rating
                updated = usage.with_rating(rating)
                self._usages[usage_id] = updated

                return True

            except Exception as e:
                raise PromptUsageRepositoryError(f"Failed to update rating: {e}") from e

    def _update_indexes(self, usage: PromptUsage) -> None:
        """
        Update indexes for efficient querying.

        Args:
            usage: Usage event to index
        """
        # Update prompt index
        if usage.prompt_id not in self._prompt_index:
            self._prompt_index[usage.prompt_id] = []
        if usage.id not in self._prompt_index[usage.prompt_id]:
            self._prompt_index[usage.prompt_id].append(usage.id)

        # Update workspace index
        if usage.workspace_id is not None:
            if usage.workspace_id not in self._workspace_index:
                self._workspace_index[usage.workspace_id] = []
            if usage.id not in self._workspace_index[usage.workspace_id]:
                self._workspace_index[usage.workspace_id].append(usage.id)

        # Update user index
        if usage.user_id is not None:
            if usage.user_id not in self._user_index:
                self._user_index[usage.user_id] = []
            if usage.id not in self._user_index[usage.user_id]:
                self._user_index[usage.user_id].append(usage.id)

    def _remove_from_indexes(self, usage: PromptUsage) -> None:
        """
        Remove usage from indexes.

        Args:
            usage: Usage event to remove from indexes
        """
        # Remove from prompt index
        if usage.prompt_id in self._prompt_index:
            self._prompt_index[usage.prompt_id] = [
                uid for uid in self._prompt_index[usage.prompt_id] if uid != usage.id
            ]

        # Remove from workspace index
        if usage.workspace_id is not None:
            if usage.workspace_id in self._workspace_index:
                self._workspace_index[usage.workspace_id] = [
                    uid for uid in self._workspace_index[usage.workspace_id] if uid != usage.id
                ]

        # Remove from user index
        if usage.user_id is not None:
            if usage.user_id in self._user_index:
                self._user_index[usage.user_id] = [
                    uid for uid in self._user_index[usage.user_id] if uid != usage.id
                ]

    def clear(self) -> None:
        """Clear all stored usage events (useful for testing)."""
        """Clear all stored usage events (useful for testing)."""
        self._usages.clear()
        self._prompt_index.clear()
        self._workspace_index.clear()
        self._user_index.clear()


__all__ = ["InMemoryPromptUsageRepository"]
