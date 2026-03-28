"""Adapter that binds the Story repository port to the shared connection pool."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar
from uuid import UUID

from src.contexts.narrative.domain.aggregates.story import Story
from src.contexts.narrative.domain.ports.story_repository_port import (
    StoryRepositoryPort,
)
from src.contexts.narrative.infrastructure.repositories.postgres_story_repository import (
    PostgresStoryRepository,
)

T = TypeVar("T")


class PostgresStoryRepositoryAdapter(StoryRepositoryPort):
    """Open a fresh repository instance per operation using a shared pool."""

    def __init__(self, connection_pool: Any) -> None:
        self._connection_pool = connection_pool

    async def _run(
        self,
        operation: Callable[[PostgresStoryRepository], Awaitable[T]],
    ) -> T:
        async with self._connection_pool.acquire() as connection:
            repository = PostgresStoryRepository(connection)
            return await operation(repository)

    async def get_by_id(self, story_id: UUID) -> Story | None:
        return await self._run(lambda repository: repository.get_by_id(story_id))

    async def get_by_title(self, title: str) -> Story | None:
        return await self._run(lambda repository: repository.get_by_title(title))

    async def save(self, story: Story) -> None:
        await self._run(lambda repository: repository.save(story))

    async def delete(self, story_id: UUID) -> bool:
        return await self._run(lambda repository: repository.delete(story_id))

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Story]:
        return await self._run(
            lambda repository: repository.list_all(limit=limit, offset=offset)
        )

    async def list_by_author(self, author_id: str, limit: int = 100) -> list[Story]:
        return await self._run(
            lambda repository: repository.list_by_author(author_id, limit=limit)
        )


__all__ = ["PostgresStoryRepositoryAdapter"]
