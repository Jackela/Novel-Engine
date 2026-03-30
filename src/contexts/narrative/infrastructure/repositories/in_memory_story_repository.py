"""In-memory StoryRepositoryPort implementation for local development and tests."""

from __future__ import annotations

import copy
from uuid import UUID

from src.contexts.narrative.domain.aggregates.story import Story
from src.contexts.narrative.domain.ports.story_repository_port import (
    StoryRepositoryPort,
)


class InMemoryStoryRepository(StoryRepositoryPort):
    """Persist stories in process memory with deterministic behavior."""

    def __init__(self) -> None:
        self._stories_by_id: dict[UUID, Story] = {}

    def reset(self) -> None:
        """Clear all stored stories."""
        self._stories_by_id.clear()

    async def get_by_id(self, story_id: UUID) -> Story | None:
        story = self._stories_by_id.get(story_id)
        return copy.deepcopy(story) if story is not None else None

    async def get_by_title(self, title: str) -> Story | None:
        normalized_title = self._normalize_title(title)
        for story in self._stories_by_id.values():
            if self._normalize_title(story.title) == normalized_title:
                return copy.deepcopy(story)
        return None

    async def save(self, story: Story) -> None:
        self._stories_by_id[story.id] = copy.deepcopy(story)

    async def delete(self, story_id: UUID) -> bool:
        return self._stories_by_id.pop(story_id, None) is not None

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Story]:
        if limit < 0:
            raise ValueError("Limit must be non-negative")
        if offset < 0:
            raise ValueError("Offset must be non-negative")

        ordered = sorted(
            self._stories_by_id.values(),
            key=lambda story: story.updated_at,
            reverse=True,
        )
        sliced = ordered[offset : offset + limit] if limit else []
        return [copy.deepcopy(story) for story in sliced]

    async def list_by_author(self, author_id: str, limit: int = 100) -> list[Story]:
        if limit < 0:
            raise ValueError("Limit must be non-negative")

        ordered = [
            story
            for story in sorted(
                self._stories_by_id.values(),
                key=lambda current: current.updated_at,
                reverse=True,
            )
            if story.author_id == author_id
        ]
        return [copy.deepcopy(story) for story in ordered[:limit]]

    @staticmethod
    def _normalize_title(title: str) -> str:
        return " ".join(title.strip().lower().split())


__all__ = ["InMemoryStoryRepository"]
