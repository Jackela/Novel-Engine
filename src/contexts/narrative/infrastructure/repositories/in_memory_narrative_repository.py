"""In-Memory Narrative Repository Implementation.

This module provides an in-memory implementation of INarrativeRepository
for testing and development purposes.

Why in-memory:
    An in-memory repository provides a fast, simple implementation that
    doesn't require database setup. It's ideal for unit testing domain
    logic without infrastructure concerns, and for rapid prototyping.
"""

from copy import deepcopy
from typing import Optional
from uuid import UUID

from ...application.ports.narrative_repository_port import INarrativeRepository
from ...domain import Story


class InMemoryNarrativeRepository(INarrativeRepository):
    """In-memory implementation of the narrative repository.

    Stores Story aggregates in a dictionary keyed by story ID. Uses deep
    copying to prevent external mutations from affecting stored data.

    Why deep copy:
        Without copying, callers could modify the stored entities directly,
        bypassing domain invariants. Deep copying ensures the repository
        maintains its own isolated copy of each aggregate.

    Attributes:
        _stories: Dictionary mapping story IDs to Story aggregates.

    Example:
        >>> repo = InMemoryNarrativeRepository()
        >>> story = Story(title="My Novel")
        >>> repo.save(story)
        >>> assert repo.exists(story.id)
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory repository.

        Why explicit init:
            Makes the initialization state clear and allows for
            future extension (e.g., pre-seeding with test data).
        """
        self._stories: dict[UUID, Story] = {}

    def save(self, story: Story) -> None:
        """Save a Story aggregate to the in-memory store.

        Creates a deep copy of the story to prevent external mutations
        from affecting the stored version.

        Args:
            story: The Story aggregate to save.

        Why deep copy on save:
            If we stored the original reference, external code could
            modify the story after saving, leading to inconsistencies
            between what was "saved" and what's actually stored.
        """
        self._stories[story.id] = deepcopy(story)

    def get_by_id(self, story_id: UUID) -> Optional[Story]:
        """Retrieve a Story aggregate by its ID.

        Returns a deep copy to prevent callers from modifying the
        stored version directly.

        Args:
            story_id: The UUID of the story to retrieve.

        Returns:
            A copy of the Story if found, None otherwise.

        Why deep copy on get:
            Returning the original reference would allow callers to
            modify the repository's internal state without going
            through the save() method.
        """
        story = self._stories.get(story_id)
        if story is None:
            return None
        return deepcopy(story)

    def list_all(self) -> list[Story]:
        """Retrieve all stories from the repository.

        Returns deep copies of all stored stories, sorted by creation time.

        Returns:
            List of Story aggregates, sorted by created_at (oldest first).

        Why sorted by created_at:
            Provides a predictable, consistent ordering for UI display
            and testing purposes.
        """
        stories = [deepcopy(story) for story in self._stories.values()]
        return sorted(stories, key=lambda s: s.created_at)

    def delete(self, story_id: UUID) -> bool:
        """Delete a Story aggregate from the repository.

        Args:
            story_id: The UUID of the story to delete.

        Returns:
            True if the story was deleted, False if not found.

        Why return bool:
            Callers can distinguish between "successfully deleted" and
            "nothing to delete" without needing to check existence first.
        """
        if story_id in self._stories:
            del self._stories[story_id]
            return True
        return False

    def exists(self, story_id: UUID) -> bool:
        """Check if a story exists in the repository.

        Args:
            story_id: The UUID to check.

        Returns:
            True if the story exists, False otherwise.

        Why this method:
            Avoids loading the full aggregate just to check existence,
            which is more efficient for validation scenarios.
        """
        return story_id in self._stories

    def clear(self) -> None:
        """Remove all stories from the repository.

        Why this method:
            Useful for test setup/teardown to ensure a clean state
            between test cases. Not part of the port interface since
            it's specific to in-memory testing needs.
        """
        self._stories.clear()

    @property
    def count(self) -> int:
        """Get the number of stories in the repository.

        Returns:
            The count of stored stories.

        Why a property:
            Simple read-only access that's useful for testing assertions.
            Not part of the port interface since it's testing-specific.
        """
        return len(self._stories)
