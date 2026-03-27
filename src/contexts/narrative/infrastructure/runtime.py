"""Runtime wiring for the narrative story workflow."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from src.contexts.ai.infrastructure.providers import create_text_generation_provider
from src.contexts.narrative.application.services.story_workflow_service import (
    StoryWorkflowService,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_story_repository import (
    InMemoryStoryRepository,
)
from src.contexts.narrative.infrastructure.repositories.postgres_story_repository_adapter import (
    PostgresStoryRepositoryAdapter,
)
from src.shared.infrastructure.config.settings import NovelEngineSettings, get_settings

_story_repository: InMemoryStoryRepository | PostgresStoryRepositoryAdapter | None = (
    None
)
_story_workflow_service: StoryWorkflowService | None = None


class _LazyConnectionPoolProxy:
    """Proxy that resolves the shared connection pool only when used."""

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[Any, None]:
        from src.apps.api.dependencies import get_connection_pool

        pool = await get_connection_pool()
        async with pool.acquire() as connection:
            yield connection


def _build_story_repository(
    settings: NovelEngineSettings,
) -> InMemoryStoryRepository | PostgresStoryRepositoryAdapter:
    if settings.is_testing or settings.is_development:
        return InMemoryStoryRepository()
    return PostgresStoryRepositoryAdapter(_LazyConnectionPoolProxy())


def get_story_workflow_service() -> StoryWorkflowService:
    """Return the canonical story workflow service singleton."""
    global _story_repository, _story_workflow_service
    if _story_workflow_service is None:
        settings = get_settings()
        if _story_repository is None:
            _story_repository = _build_story_repository(settings)
        _story_workflow_service = StoryWorkflowService(
            story_repository=_story_repository,
            text_generation_provider=create_text_generation_provider(settings),
            default_target_chapters=12,
        )
    return _story_workflow_service


def reset_story_workflow_service() -> None:
    """Reset the story workflow singleton for tests and app rebuilds."""
    global _story_repository, _story_workflow_service
    if isinstance(_story_repository, InMemoryStoryRepository):
        _story_repository.reset()
    _story_repository = None
    _story_workflow_service = None


__all__ = ["get_story_workflow_service", "reset_story_workflow_service"]
