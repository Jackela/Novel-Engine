"""
Brain Router Dependencies

FastAPI dependency injection functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from fastapi import Request

from src.api.routers.brain.repositories.brain_settings import (
    BrainSettingsRepository,
    InMemoryBrainSettingsRepository,
)
from src.api.routers.brain.repositories.ingestion import IngestionJobStore
from src.api.routers.brain.repositories.token_usage import (
    InMemoryTokenUsageRepository,
    seed_mock_data,
)
from src.api.routers.brain.services.usage_broadcaster import (
    RealtimeUsageBroadcaster,
    get_usage_broadcaster,
)

if TYPE_CHECKING:
    from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
        KnowledgeIngestionService,
    )

logger = structlog.get_logger(__name__)


def get_brain_settings_repository(request: Request) -> BrainSettingsRepository:
    """
    Get or create the brain settings repository from app state.

    Why: Lazy initialization and singleton pattern for the repository.

    Args:
        request: FastAPI request object

    Returns:
        The brain settings repository instance
    """
    repository = getattr(request.app.state, "brain_settings_repository", None)
    if repository is None:
        repository = InMemoryBrainSettingsRepository()
        request.app.state.brain_settings_repository = repository
        logger.info("Initialized InMemoryBrainSettingsRepository")
    return repository


def get_token_usage_repository(request: Request) -> InMemoryTokenUsageRepository:
    """
    Get or create the token usage repository from app state.

    Why: Lazy initialization and singleton pattern for the repository.

    Args:
        request: FastAPI request object

    Returns:
        The token usage repository instance
    """
    repository = getattr(request.app.state, "token_usage_repository", None)
    if repository is None:
        repository = InMemoryTokenUsageRepository()
        # Seed with mock data for BRAIN-035A testing
        seed_mock_data(repository)
        request.app.state.token_usage_repository = repository
        logger.info("Initialized InMemoryTokenUsageRepository with mock data")
    return repository


def get_ingestion_job_store(request: Request) -> IngestionJobStore:
    """
    Get the ingestion job store from app state.

    Why: Dependency injection for testability.

    Args:
        request: FastAPI request object

    Returns:
        The ingestion job store instance
    """
    store = getattr(request.app.state, "ingestion_job_store", None)
    if store is None:
        store = IngestionJobStore()
        request.app.state.ingestion_job_store = store
        logger.info("Initialized IngestionJobStore")
    return store


def get_ingestion_service(request: Request) -> KnowledgeIngestionService:
    """
    Get or create the ingestion service from app state.

    Args:
        request: FastAPI request object

    Returns:
        The knowledge ingestion service instance
    """
    from src.contexts.knowledge.infrastructure.adapters.chromadb_vector_store import (
        ChromaDBVectorStore,
    )
    from src.contexts.knowledge.infrastructure.adapters.embedding_generator_adapter import (
        EmbeddingServiceAdapter,
    )

    service = getattr(request.app.state, "ingestion_service", None)
    if service is None:
        # Create dependencies
        embedding_service = EmbeddingServiceAdapter(use_mock=True)
        vector_store = ChromaDBVectorStore()

        # Create service
        from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
            KnowledgeIngestionService,
        )

        service = KnowledgeIngestionService(
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
        request.app.state.ingestion_service = service
        logger.info("Initialized KnowledgeIngestionService for async jobs")

    return service


def get_usage_broadcaster_dep() -> RealtimeUsageBroadcaster:
    """Get the global usage broadcaster instance."""
    return get_usage_broadcaster()


def get_context_window_manager(request: Request) -> None:
    """
    Get or create the context window manager from app state.

    OPT-009: Context Window Manager integration

    Args:
        request: FastAPI request object

    Returns:
        The context window manager instance
    """
    from src.contexts.knowledge.application.services.context_window_manager import (
        create_context_window_manager,
    )

    manager = getattr(request.app.state, "context_window_manager", None)
    if manager is None:
        manager = create_context_window_manager(
            model_name="gpt-4o",
            enable_rag_optimization=True,
        )
        request.app.state.context_window_manager = manager
        logger.info("Initialized ContextWindowManager")

    return manager


__all__ = [
    "get_brain_settings_repository",
    "get_token_usage_repository",
    "get_ingestion_job_store",
    "get_ingestion_service",
    "get_usage_broadcaster_dep",
    "get_context_window_manager",
]
