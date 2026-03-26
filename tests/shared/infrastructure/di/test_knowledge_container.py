"""Tests for Knowledge DI container integration.

This module provides tests for the knowledge context DI container
configuration and dependency resolution.
"""

from __future__ import annotations

import pytest
from dependency_injector import providers

from src.shared.infrastructure.di.container import ApplicationContainer


@pytest.fixture
def knowledge_test_config() -> dict:
    """Provide test configuration for knowledge context."""
    return {
        "database": {
            "url": "postgresql://test:test@localhost:5432/test_db",
            "max_connections": 5,
        },
        "security": {
            "secret_key": "test-secret-key-32-chars-long!!!",
            "algorithm": "HS256",
            "access_token_expire_minutes": 30,
            "refresh_token_expire_days": 7,
        },
        "honcho": {
            "base_url": "https://api.honcho.dev",
            "api_key": None,
        },
        "llm": {
            "api_key": "test-api-key",
            "embedding_model": "text-embedding-3-small",
        },
        "vector_store": {
            "host": "localhost",
            "port": 8000,
            "collection_name": "test_knowledge",
        },
        "knowledge": {
            "chunk_size": 500,
            "chunk_overlap": 50,
            "max_document_size": 10_000_000,
        },
    }


@pytest.fixture
def container(knowledge_test_config: dict) -> ApplicationContainer:
    """Create test container with knowledge configuration."""
    container = ApplicationContainer()
    container.config.from_dict(knowledge_test_config)
    return container


class TestKnowledgeContainerConfiguration:
    """Test knowledge container configuration loading."""

    def test_knowledge_container_exists(self, container: ApplicationContainer) -> None:
        """Test knowledge container is accessible."""
        assert container.knowledge is not None

    def test_knowledge_repo_provider_exists(
        self, container: ApplicationContainer
    ) -> None:
        """Test knowledge repository provider is configured."""
        assert container.knowledge.knowledge_repo is not None
        assert isinstance(container.knowledge.knowledge_repo, providers.Factory)

    def test_vector_store_provider_exists(
        self, container: ApplicationContainer
    ) -> None:
        """Test vector store provider is configured."""
        assert container.knowledge.vector_store is not None
        assert isinstance(container.knowledge.vector_store, providers.Factory)

    def test_embedding_service_provider_exists(
        self, container: ApplicationContainer
    ) -> None:
        """Test embedding service provider is configured."""
        assert container.knowledge.embedding_service is not None
        assert isinstance(container.knowledge.embedding_service, providers.Factory)

    def test_chunking_service_provider_exists(
        self, container: ApplicationContainer
    ) -> None:
        """Test chunking service provider is configured."""
        assert container.knowledge.chunking_service is not None
        assert isinstance(container.knowledge.chunking_service, providers.Factory)

    def test_knowledge_service_provider_exists(
        self, container: ApplicationContainer
    ) -> None:
        """Test knowledge service provider is configured."""
        assert container.knowledge.knowledge_service is not None
        assert isinstance(container.knowledge.knowledge_service, providers.Factory)


class TestKnowledgeServiceCreation:
    """Test knowledge service creation via DI container."""

    def test_vector_store_can_be_created(self, container: ApplicationContainer) -> None:
        """Test vector store can be resolved from container."""
        from src.contexts.knowledge.infrastructure.vectorStores.chroma_vector_store import (
            ChromaVectorStore,
        )

        # This will work without actual ChromaDB server
        # because the client is lazily initialized
        vector_store = container.knowledge.vector_store()
        assert vector_store is not None
        assert isinstance(vector_store, ChromaVectorStore)
        assert vector_store._host == "localhost"
        assert vector_store._port == 8000

    def test_embedding_service_can_be_created(
        self, container: ApplicationContainer
    ) -> None:
        """Test embedding service can be resolved from container."""
        from src.contexts.knowledge.infrastructure.services.openai_embedding_service import (
            OpenAIEmbeddingService,
        )

        embedding_service = container.knowledge.embedding_service()
        assert embedding_service is not None
        assert isinstance(embedding_service, OpenAIEmbeddingService)
        assert embedding_service._api_key == "test-api-key"
        assert embedding_service._model == "text-embedding-3-small"

    def test_chunking_service_can_be_created(
        self, container: ApplicationContainer
    ) -> None:
        """Test chunking service can be resolved from container."""
        from src.contexts.knowledge.infrastructure.services.recursive_chunking_service import (
            RecursiveChunkingService,
        )

        chunking_service = container.knowledge.chunking_service()
        assert chunking_service is not None
        assert isinstance(chunking_service, RecursiveChunkingService)
        assert chunking_service.chunk_size == 500
        assert chunking_service.chunk_overlap == 50

    @pytest.mark.skip(
        reason="Requires initialized database pool - tested in integration tests"
    )
    def test_knowledge_repo_can_be_created(
        self, container: ApplicationContainer
    ) -> None:
        """Test knowledge repository can be resolved from container."""
        # This requires a real database connection pool
        # The factory pattern is tested by verifying the provider type
        repo = container.knowledge.knowledge_repo
        assert isinstance(repo, providers.Factory)

    @pytest.mark.skip(
        reason="Requires initialized database pool - tested in integration tests"
    )
    def test_knowledge_service_can_be_created(
        self, container: ApplicationContainer
    ) -> None:
        """Test knowledge service can be resolved from container."""
        from src.contexts.knowledge.application.services.knowledge_service import (
            KnowledgeApplicationService,
        )

        # This requires a real database connection pool
        service = container.knowledge.knowledge_service()
        assert service is not None
        assert isinstance(service, KnowledgeApplicationService)


class TestKnowledgeContainerEdgeCases:
    """Test edge cases and error handling."""

    def test_vector_store_with_different_config(self) -> None:
        """Test vector store with different configuration."""
        config = {
            "database": {"url": "sqlite:///./test.db"},
            "vector_store": {"host": "chroma.example.com", "port": 9000},
            "llm": {"api_key": "test"},
            "knowledge": {"chunk_size": 1000, "chunk_overlap": 100},
        }

        container = ApplicationContainer()
        container.config.from_dict(config)


        vector_store = container.knowledge.vector_store()
        assert vector_store._host == "chroma.example.com"
        assert vector_store._port == 9000

    def test_chunking_service_with_different_config(self) -> None:
        """Test chunking service with different configuration."""
        config = {
            "database": {"url": "sqlite:///./test.db"},
            "vector_store": {"host": "localhost", "port": 8000},
            "llm": {"api_key": "test"},
            "knowledge": {"chunk_size": 1000, "chunk_overlap": 100},
        }

        container = ApplicationContainer()
        container.config.from_dict(config)


        chunking_service = container.knowledge.chunking_service()
        assert chunking_service.chunk_size == 1000
        assert chunking_service.chunk_overlap == 100

    def test_config_override(self, container: ApplicationContainer) -> None:
        """Test configuration can be overridden."""
        # Override config
        container.config.vector_store.host.from_value("new-host.example.com")
        container.config.vector_store.port.from_value(8080)


        vector_store = container.knowledge.vector_store()
        assert vector_store._host == "new-host.example.com"
        assert vector_store._port == 8080


class TestKnowledgeServiceIntegration:
    """Test knowledge service integration with DI container."""

    def test_all_providers_are_independent_factories(
        self, container: ApplicationContainer
    ) -> None:
        """Test that all providers create independent instances."""
        # Vector store
        store1 = container.knowledge.vector_store()
        store2 = container.knowledge.vector_store()
        assert store1 is not store2  # Factory creates new instances

        # Embedding service
        embed1 = container.knowledge.embedding_service()
        embed2 = container.knowledge.embedding_service()
        assert embed1 is not embed2  # Factory creates new instances

        # Chunking service
        chunk1 = container.knowledge.chunking_service()
        chunk2 = container.knowledge.chunking_service()
        assert chunk1 is not chunk2  # Factory creates new instances

    def test_embedding_service_dimension(self, container: ApplicationContainer) -> None:
        """Test embedding service returns correct dimension."""
        embedding_service = container.knowledge.embedding_service()
        dimension = embedding_service.get_dimension()
        assert dimension == 1536  # text-embedding-3-small dimension

    def test_chunking_service_functionality(
        self, container: ApplicationContainer
    ) -> None:
        """Test chunking service can chunk documents."""
        chunking_service = container.knowledge.chunking_service()

        # Test with a simple document
        content = "This is a test document. It has multiple sentences. " * 10
        chunks = chunking_service.chunk_document(content, chunk_size=100, overlap=20)

        assert len(chunks) > 0
        assert all("content" in chunk for chunk in chunks)
        assert all("metadata" in chunk for chunk in chunks)
