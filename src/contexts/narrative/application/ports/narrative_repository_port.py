"""Narrative Repository Port (Interface).

This module defines the abstract interface for Story aggregate persistence
operations. The port belongs to the application layer and is implemented
by infrastructure adapters.

Why this port exists:
    Following hexagonal architecture, the domain and application layers
    should not depend on specific persistence technologies. This port
    defines the contract that any persistence adapter must implement,
    whether it's in-memory, PostgreSQL, or any other storage.
"""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from ...domain import Story


class INarrativeRepository(ABC):
    """Abstract repository interface for Story aggregate persistence.

    This interface defines the contract for persisting and retrieving
    Story aggregates with their chapters. The actual implementation
    will be provided by infrastructure adapters.

    Why Story as the aggregate root for persistence:
        Story owns chapters, and chapters are part of the Story aggregate
        boundary. We save and load entire Story aggregates rather than
        individual chapters to maintain consistency.

    Attributes:
        None - this is a pure interface.

    Example:
        >>> repo: INarrativeRepository = InMemoryNarrativeRepository()
        >>> story = Story(title="My Novel")
        >>> repo.save(story)
        >>> loaded = repo.get_by_id(story.id)
        >>> assert loaded is not None
    """

    @abstractmethod
    def save(self, story: Story) -> None:
        """Save a Story aggregate to the repository.

        This method handles both new story creation and updates to
        existing stories. If a story with the same ID exists, it
        will be overwritten.

        Args:
            story: The Story aggregate to save, including all chapters.

        Raises:
            RepositoryException: If the save operation fails.

        Why no return value:
            The story already has an ID; we don't need to return it.
            Errors are signaled via exceptions.
        """

    @abstractmethod
    def get_by_id(self, story_id: UUID) -> Optional[Story]:
        """Retrieve a Story aggregate by its unique identifier.

        Args:
            story_id: The UUID of the story to retrieve.

        Returns:
            The Story aggregate if found (including chapters), None otherwise.

        Raises:
            RepositoryException: If retrieval fails due to infrastructure issues.

        Why Optional return:
            We use None to indicate "not found" rather than exceptions,
            following the "Tell, Don't Ask" principle for expected cases.
        """

    @abstractmethod
    def list_all(self) -> list[Story]:
        """Retrieve all stories from the repository.

        Returns:
            A list of all Story aggregates (may be empty).

        Raises:
            RepositoryException: If retrieval fails.

        Why a simple list:
            For the MVP, we retrieve all stories. Pagination and filtering
            can be added later when needed.
        """

    @abstractmethod
    def delete(self, story_id: UUID) -> bool:
        """Delete a Story aggregate from the repository.

        Args:
            story_id: The UUID of the story to delete.

        Returns:
            True if the story was deleted, False if not found.

        Raises:
            RepositoryException: If deletion fails due to infrastructure issues.

        Why return bool:
            Allows callers to know whether a story was actually deleted
            without needing to check existence first.
        """

    @abstractmethod
    def exists(self, story_id: UUID) -> bool:
        """Check if a story exists in the repository.

        Args:
            story_id: The UUID to check.

        Returns:
            True if the story exists, False otherwise.

        Raises:
            RepositoryException: If the check fails.

        Why this method:
            Allows existence checks without loading the full aggregate,
            which can be useful for validation.
        """


class RepositoryException(Exception):
    """Base exception for repository operations.

    Why a custom exception:
        Allows callers to catch repository-specific errors without
        depending on infrastructure-specific exception types.
    """
