"""Professional DI Container using dependency-injector.

This module provides a comprehensive dependency injection container
for the Novel Engine application, replacing manual dependency management.
"""

from __future__ import annotations

from dependency_injector import containers, providers

from src.contexts.identity.application.services.authentication_service import (
    AuthenticationService,
)
from src.contexts.identity.infrastructure.repositories.postgres_user_repository import (
    PostgresUserRepository,
)
from src.contexts.knowledge.application.services.knowledge_service import (
    KnowledgeApplicationService,
)
from src.contexts.knowledge.infrastructure.repositories.postgres_knowledge_repository import (
    PostgresKnowledgeRepository,
)
from src.contexts.knowledge.infrastructure.services.openai_embedding_service import (
    OpenAIEmbeddingService,
)
from src.contexts.knowledge.infrastructure.services.recursive_chunking_service import (
    RecursiveChunkingService,
)
from src.contexts.knowledge.infrastructure.vectorStores.chroma_vector_store import (
    ChromaVectorStore,
)
from src.shared.infrastructure.auth.jwt_utils import JWTManager
from src.shared.infrastructure.honcho.client import HonchoClient
from src.shared.infrastructure.honcho.config import HonchoSettings
from src.shared.infrastructure.persistence.connection_pool import DatabaseConnectionPool


class CoreContainer(containers.DeclarativeContainer):
    """Core infrastructure container.

    This container manages core infrastructure services that are
    shared across all bounded contexts.
    """

    config = providers.Configuration()

    # Database connection pool (Singleton - one pool per application)
    db_pool = providers.Singleton(
        DatabaseConnectionPool,
        database_url=config.database.url,
        max_connections=config.database.max_connections,
    )

    # Honcho client (Singleton - one client per application)
    honcho_client = providers.Singleton(
        HonchoClient,
        settings=providers.Factory(
            HonchoSettings,
            base_url=config.honcho.base_url,
            api_key=config.honcho.api_key,
        ),
    )

    # JWT Manager (Singleton - shared across all authentication operations)
    jwt_manager = providers.Singleton(
        JWTManager,
        secret_key=config.security.secret_key,
        algorithm=config.security.algorithm,
        access_token_expire_minutes=config.security.access_token_expire_minutes,
        refresh_token_expire_days=config.security.refresh_token_expire_days,
    )


class IdentityContainer(containers.DeclarativeContainer):
    """Identity bounded context container.

    Manages all dependencies related to user identity,
    authentication, and authorization.
    """

    core = providers.DependenciesContainer()

    # Repositories (Factory - new instance per request)
    user_repository = providers.Factory(
        PostgresUserRepository,
        pool=core.db_pool.provided.pool,
    )

    # Services (Factory - new instance per request)
    authentication_service = providers.Factory(
        AuthenticationService,
        user_repository=user_repository,
        jwt_manager=core.jwt_manager,
    )


class KnowledgeContainer(containers.DeclarativeContainer):
    """Knowledge bounded context container.

    Manages all dependencies related to knowledge management,
    document processing, and semantic search.
    """

    core = providers.DependenciesContainer()
    config = providers.Configuration()

    # Repositories (Factory - new instance per request)
    knowledge_repo = providers.Factory(
        PostgresKnowledgeRepository,
        pool=core.db_pool.provided.pool,
    )

    # Vector Store (Factory - new instance per request)
    vector_store = providers.Factory(
        ChromaVectorStore,
        host=config.vector_store.host,
        port=config.vector_store.port,
    )

    # Embedding Service (Factory - new instance per request)
    embedding_service = providers.Factory(
        OpenAIEmbeddingService,
        api_key=config.llm.api_key,
        model=config.llm.embedding_model,
    )

    # Chunking Service (Factory - new instance per request)
    chunking_service = providers.Factory(
        RecursiveChunkingService,
        chunk_size=config.knowledge.chunk_size,
        chunk_overlap=config.knowledge.chunk_overlap,
    )

    # Knowledge Application Service (Factory - new instance per request)
    knowledge_service = providers.Factory(
        KnowledgeApplicationService,
        knowledge_repo=knowledge_repo,
        vector_store=vector_store,
        embedding_service=embedding_service,
        chunking_service=chunking_service,
    )


class WorldContainer(containers.DeclarativeContainer):
    """World bounded context container.

    Manages all dependencies related to world state management,
    simulation, and rumors.
    """

    core = providers.DependenciesContainer()

    # Services will be added when world state repositories are fully implemented


class NarrativeContainer(containers.DeclarativeContainer):
    """Narrative bounded context container.

    Manages all dependencies related to story, chapter, and scene management.
    """

    core = providers.DependenciesContainer()

    # Services will be added when narrative repositories are fully implemented


class ApplicationContainer(containers.DeclarativeContainer):
    """Main application container composing all bounded context containers.

    This is the root container that wires together all context containers
    and provides a unified interface for dependency resolution.

    Example:
        >>> container = ApplicationContainer()
        >>> container.config.from_yaml('config/settings.yaml')
        >>> auth_service = container.identity.authentication_service()
    """

    config = providers.Configuration()

    # Core infrastructure container
    core = providers.Container(
        CoreContainer,
        config=config,
    )

    # Bounded context containers
    identity = providers.Container(
        IdentityContainer,
        core=core,
    )

    knowledge = providers.Container(
        KnowledgeContainer,
        core=core,
        config=config,
    )

    world = providers.Container(
        WorldContainer,
        core=core,
    )

    narrative = providers.Container(
        NarrativeContainer,
        core=core,
    )
