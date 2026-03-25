"""Chapter repository port."""

from typing import Protocol
from uuid import UUID

from src.contexts.narrative.domain.entities.chapter import Chapter


class ChapterRepositoryPort(Protocol):
    """Repository port for Chapter entity."""

    async def get_by_id(self, chapter_id: UUID) -> Chapter | None:
        """Get chapter by ID."""
        ...

    async def get_by_story(self, story_id: UUID) -> list[Chapter]:
        """Get chapters by story ID."""
        ...

    async def save(self, chapter: Chapter) -> None:
        """Save chapter."""
        ...

    async def delete(self, chapter_id: UUID) -> bool:
        """Delete chapter."""
        ...

    async def reorder_chapters(self, story_id: UUID, chapter_order: list[UUID]) -> None:
        """Reorder chapters in a story."""
        ...
