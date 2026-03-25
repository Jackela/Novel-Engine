"""Story repository port."""

from typing import Protocol
from uuid import UUID

from src.contexts.narrative.domain.aggregates.story import Story


class StoryRepositoryPort(Protocol):
    """Repository port for Story aggregate."""

    async def get_by_id(self, story_id: UUID) -> Story | None:
        """Get story by ID."""
        ...

    async def get_by_title(self, title: str) -> Story | None:
        """Get story by title."""
        ...

    async def save(self, story: Story) -> None:
        """Save story."""
        ...

    async def delete(self, story_id: UUID) -> bool:
        """Delete story."""
        ...

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Story]:
        """List all stories."""
        ...

    async def list_by_author(self, author_id: str, limit: int = 100) -> list[Story]:
        """List stories by author."""
        ...
