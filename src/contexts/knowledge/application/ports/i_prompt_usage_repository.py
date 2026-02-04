"""
IPromptUsageRepository Port Interface

Hexagonal architecture port defining the contract for prompt usage persistence.

Warzone 4: AI Brain - BRAIN-022A

Constitution Compliance:
- Article II (Hexagonal): Domain/Application layer defines port, Infrastructure provides adapter
- Article I (DDD): Pure interface with no infrastructure coupling
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from ...domain.models.prompt_usage import PromptUsage, PromptUsageStats


class PromptUsageRepositoryError(Exception):
    """Base exception for prompt usage repository errors."""

    pass


class IPromptUsageRepository(ABC):
    """
    Repository port for prompt usage persistence.

    This interface defines the contract that infrastructure adapters must implement
    for persisting and retrieving PromptUsage entities.

    Per Article II (Hexagonal Architecture):
    - Domain/Application layer defines this port
    - Infrastructure layer provides adapter implementation (SQLite, PostgreSQL, etc.)
    - Application use cases depend ONLY on this abstraction, never on concrete adapters

    Methods:
        record: Record a new usage event
        get_stats: Get aggregated stats for a prompt
        get_usage_by_id: Get a specific usage event by ID
        list_by_prompt: List usage events for a specific prompt
        list_by_workspace: List usage events for a workspace
        list_by_user: List usage events for a user
        list_by_date_range: List usage events within a date range
        delete_old_usages: Delete usage events older than a cutoff

    Constitution Compliance:
    - Article II (Hexagonal): Port interface in application layer
    - Article V (SOLID): ISP - Interface Segregation Principle (focused contract)
    - Article V (SOLID): DIP - Depend on abstractions, not concretions
    """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass


__all__ = [
    "IPromptUsageRepository",
    "PromptUsageRepositoryError",
]
