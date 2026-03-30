"""Runtime wiring for the narrative story workflow."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from src.contexts.ai.infrastructure.providers import create_text_generation_provider
from src.contexts.narrative.application.services.story_workflow_service import (
    StoryWorkflowService,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_generation_run_repository import (
    InMemoryGenerationRunRepository,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_story_artifact_repository import (
    InMemoryStoryArtifactRepository,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_story_generation_state_repository import (
    InMemoryStoryGenerationStateRepository,
)
from src.contexts.narrative.infrastructure.repositories.in_memory_story_repository import (
    InMemoryStoryRepository,
)
from src.contexts.narrative.infrastructure.repositories.postgres_generation_run_repository_adapter import (
    PostgresGenerationRunRepositoryAdapter,
)
from src.contexts.narrative.infrastructure.repositories.postgres_story_artifact_repository_adapter import (
    PostgresStoryArtifactRepositoryAdapter,
)
from src.contexts.narrative.infrastructure.repositories.postgres_story_generation_state_repository_adapter import (
    PostgresStoryGenerationStateRepositoryAdapter,
)
from src.contexts.narrative.infrastructure.repositories.postgres_story_repository_adapter import (
    PostgresStoryRepositoryAdapter,
)
from src.shared.infrastructure.config.settings import NovelEngineSettings, get_settings

_story_repository: InMemoryStoryRepository | PostgresStoryRepositoryAdapter | None = (
    None
)
_story_generation_state_repository: (
    InMemoryStoryGenerationStateRepository
    | PostgresStoryGenerationStateRepositoryAdapter
    | None
) = None
_generation_run_repository: (
    InMemoryGenerationRunRepository | PostgresGenerationRunRepositoryAdapter | None
) = None
_story_artifact_repository: (
    InMemoryStoryArtifactRepository | PostgresStoryArtifactRepositoryAdapter | None
) = None
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


def _build_story_generation_state_repository(
    settings: NovelEngineSettings,
) -> (
    InMemoryStoryGenerationStateRepository
    | PostgresStoryGenerationStateRepositoryAdapter
):
    if settings.is_testing or settings.is_development:
        return InMemoryStoryGenerationStateRepository()
    return PostgresStoryGenerationStateRepositoryAdapter(_LazyConnectionPoolProxy())


def _build_generation_run_repository(
    settings: NovelEngineSettings,
) -> InMemoryGenerationRunRepository | PostgresGenerationRunRepositoryAdapter:
    if settings.is_testing or settings.is_development:
        return InMemoryGenerationRunRepository()
    return PostgresGenerationRunRepositoryAdapter(_LazyConnectionPoolProxy())


def _build_story_artifact_repository(
    settings: NovelEngineSettings,
) -> InMemoryStoryArtifactRepository | PostgresStoryArtifactRepositoryAdapter:
    if settings.is_testing or settings.is_development:
        return InMemoryStoryArtifactRepository()
    return PostgresStoryArtifactRepositoryAdapter(_LazyConnectionPoolProxy())


def get_story_workflow_service() -> StoryWorkflowService:
    """Return the canonical story workflow service singleton."""
    global _generation_run_repository, _story_artifact_repository
    global _story_generation_state_repository, _story_repository, _story_workflow_service
    if _story_workflow_service is None:
        settings = get_settings()
        if _story_repository is None:
            _story_repository = _build_story_repository(settings)
        if _story_generation_state_repository is None:
            _story_generation_state_repository = _build_story_generation_state_repository(
                settings
            )
        if _generation_run_repository is None:
            _generation_run_repository = _build_generation_run_repository(settings)
        if _story_artifact_repository is None:
            _story_artifact_repository = _build_story_artifact_repository(settings)
        _story_workflow_service = StoryWorkflowService(
            story_repository=_story_repository,
            generation_state_repository=_story_generation_state_repository,
            generation_run_repository=_generation_run_repository,
            story_artifact_repository=_story_artifact_repository,
            text_generation_provider=create_text_generation_provider(settings),
            review_generation_provider=create_text_generation_provider(
                settings,
                provider_name=settings.llm.provider,
                model_name=settings.llm.resolved_review_model(settings.llm.provider),
            ),
            default_target_chapters=12,
        )
    return _story_workflow_service


def reset_story_workflow_service() -> None:
    """Reset the story workflow singleton for tests and app rebuilds."""
    global _generation_run_repository, _story_artifact_repository
    global _story_generation_state_repository, _story_repository, _story_workflow_service
    if isinstance(_story_repository, InMemoryStoryRepository):
        _story_repository.reset()
    if isinstance(
        _story_generation_state_repository,
        InMemoryStoryGenerationStateRepository,
    ):
        _story_generation_state_repository.reset()
    if isinstance(_generation_run_repository, InMemoryGenerationRunRepository):
        _generation_run_repository.reset()
    if isinstance(_story_artifact_repository, InMemoryStoryArtifactRepository):
        _story_artifact_repository.reset()
    _story_repository = None
    _story_generation_state_repository = None
    _generation_run_repository = None
    _story_artifact_repository = None
    _story_workflow_service = None


__all__ = ["get_story_workflow_service", "reset_story_workflow_service"]
