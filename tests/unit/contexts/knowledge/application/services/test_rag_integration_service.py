"""
Unit Tests for RAG Integration Service

Warzone 4: AI Brain - BRAIN-007A

Tests for the RAG integration service that combines retrieval
with prompt enrichment.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    RetrievedChunk,
)
from src.contexts.knowledge.application.services.rag_integration_service import (
    DEFAULT_CONTEXT_TOKEN_LIMIT,
    DEFAULT_ENABLED,
    DEFAULT_MAX_CHUNKS,
    EnrichedPrompt,
    RAGConfig,
    RAGIntegrationService,
    RAGMetrics,
)
from src.contexts.knowledge.application.services.retrieval_service import (
    FormattedContext,
    RetrievalFilter,
    RetrievalResult,
    RetrievalService,
)
from src.contexts.knowledge.domain.models.source_type import SourceType

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_retrieval_service():
    """Create a mock retrieval service."""
    service = AsyncMock(spec=RetrievalService)
    service.retrieve_relevant = AsyncMock()
    service.format_context = MagicMock()
    return service


@pytest.fixture
def mock_chunks():
    """Create mock retrieved chunks."""
    return [
        RetrievedChunk(
            chunk_id="chunk1",
            source_id="char1",
            source_type=SourceType.CHARACTER,
            content="Sir Arthur is a brave warrior known for his exceptional courage.",
            score=0.92,
            metadata={"chunk_index": 0, "total_chunks": 1},
        ),
        RetrievedChunk(
            chunk_id="chunk2",
            source_id="lore1",
            source_type=SourceType.LORE,
            content="The Sword of Valor was forged in the dragon's fire.",
            score=0.85,
            metadata={"chunk_index": 0, "total_chunks": 1},
        ),
    ]


@pytest.fixture
def formatted_context():
    """Create a mock formatted context."""
    return FormattedContext(
        text="[1] CHARACTER:char1 (part 1/1)\nSir Arthur is a brave warrior.\n\n[2] LORE:lore1 (part 1/1)\nThe Sword of Valor was forged.",
        sources=["CHARACTER:char1", "LORE:lore1"],
        total_tokens=50,
        chunk_count=2,
    )


class TestRAGConfig:
    """Tests for RAGConfig value object."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RAGConfig()

        assert config.max_chunks == DEFAULT_MAX_CHUNKS
        assert config.score_threshold == 0.5  # DEFAULT_RELEVANCE_THRESHOLD
        assert config.context_token_limit == DEFAULT_CONTEXT_TOKEN_LIMIT
        assert config.enabled is DEFAULT_ENABLED
        assert config.include_sources is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = RAGConfig(
            max_chunks=10,
            score_threshold=0.7,
            context_token_limit=2000,
            enabled=False,
            include_sources=False,
        )

        assert config.max_chunks == 10
        assert config.score_threshold == 0.7
        assert config.context_token_limit == 2000
        assert config.enabled is False
        assert config.include_sources is False

    def test_config_is_immutable(self):
        """Test that config is frozen/immutable."""
        config = RAGConfig()

        with pytest.raises(Exception):  # FrozenInstanceError
            config.max_chunks = 10


class TestRAGMetrics:
    """Tests for RAGMetrics value object."""

    def test_default_metrics(self):
        """Test default metrics values."""
        metrics = RAGMetrics()

        assert metrics.queries_total == 0
        assert metrics.chunks_retrieved_total == 0
        assert metrics.tokens_added_total == 0
        assert metrics.failed_queries == 0

    def test_avg_chunks_per_query_no_queries(self):
        """Test average chunks with no queries."""
        metrics = RAGMetrics()

        assert metrics.avg_chunks_per_query == 0.0

    def test_avg_chunks_per_query_with_data(self):
        """Test average chunks calculation."""
        metrics = RAGMetrics(
            queries_total=10,
            chunks_retrieved_total=50,
        )

        assert metrics.avg_chunks_per_query == 5.0


class TestRAGIntegrationService:
    """Tests for RAGIntegrationService."""

    def test_init_with_defaults(self, mock_retrieval_service):
        """Test service initialization with defaults."""
        service = RAGIntegrationService(retrieval_service=mock_retrieval_service)

        assert service._retrieval_service == mock_retrieval_service
        assert isinstance(service._config, RAGConfig)
        assert isinstance(service._metrics, RAGMetrics)

    def test_init_with_custom_config(self, mock_retrieval_service):
        """Test service initialization with custom config."""
        config = RAGConfig(max_chunks=10, enabled=False)
        service = RAGIntegrationService(
            retrieval_service=mock_retrieval_service,
            config=config,
        )

        assert service._config == config

    def test_create_factory_method(self):
        """Test the factory create method."""
        mock_embedding = MagicMock()
        mock_vector_store = MagicMock()

        with patch.object(
            RetrievalService,
            "__init__",
            return_value=None,
        ):
            service = RAGIntegrationService.create(
                embedding_service=mock_embedding,
                vector_store=mock_vector_store,
            )

            assert isinstance(service, RAGIntegrationService)

    @pytest.mark.asyncio
    async def test_enrich_prompt_success(
        self,
        mock_retrieval_service,
        mock_chunks,
        formatted_context,
    ):
        """Test successful prompt enrichment."""
        # Setup mock retrieval
        retrieval_result = RetrievalResult(
            chunks=mock_chunks,
            query="brave warrior",
            total_retrieved=2,
        )
        mock_retrieval_service.retrieve_relevant.return_value = retrieval_result
        mock_retrieval_service.format_context.return_value = formatted_context

        service = RAGIntegrationService(retrieval_service=mock_retrieval_service)

        # Execute
        result = await service.enrich_prompt(
            query="brave warrior",
            base_prompt="Write a scene about a warrior.",
        )

        # Verify
        assert result.chunks_retrieved == 2
        assert result.tokens_added == 50
        assert result.sources == ["CHARACTER:char1", "LORE:lore1"]
        assert "Relevant Context:" in result.prompt
        assert "Sir Arthur is a brave warrior" in result.prompt
        assert "Write a scene about a warrior" in result.prompt

        # Verify retrieval was called correctly
        mock_retrieval_service.retrieve_relevant.assert_called_once()
        call_args = mock_retrieval_service.retrieve_relevant.call_args
        assert call_args[1]["query"] == "brave warrior"
        assert call_args[1]["k"] == DEFAULT_MAX_CHUNKS

    @pytest.mark.asyncio
    async def test_enrich_prompt_with_filters(
        self,
        mock_retrieval_service,
        mock_chunks,
        formatted_context,
    ):
        """Test prompt enrichment with source type filters."""
        retrieval_result = RetrievalResult(
            chunks=mock_chunks,
            query="brave warrior",
            total_retrieved=2,
        )
        mock_retrieval_service.retrieve_relevant.return_value = retrieval_result
        mock_retrieval_service.format_context.return_value = formatted_context

        service = RAGIntegrationService(retrieval_service=mock_retrieval_service)

        filters = RetrievalFilter(source_types=[SourceType.CHARACTER])

        await service.enrich_prompt(
            query="brave warrior",
            base_prompt="Write a scene.",
            filters=filters,
        )

        # Verify filters were passed
        call_args = mock_retrieval_service.retrieve_relevant.call_args
        assert call_args[1]["filters"] == filters

    @pytest.mark.asyncio
    async def test_enrich_prompt_with_config_override(
        self,
        mock_retrieval_service,
        mock_chunks,
        formatted_context,
    ):
        """Test prompt enrichment with config override."""
        retrieval_result = RetrievalResult(
            chunks=mock_chunks,
            query="brave warrior",
            total_retrieved=2,
        )
        mock_retrieval_service.retrieve_relevant.return_value = retrieval_result
        mock_retrieval_service.format_context.return_value = formatted_context

        service = RAGIntegrationService(retrieval_service=mock_retrieval_service)

        override_config = RAGConfig(max_chunks=10, score_threshold=0.8)

        await service.enrich_prompt(
            query="brave warrior",
            base_prompt="Write a scene.",
            config_override=override_config,
        )

        # Verify override config was used
        call_args = mock_retrieval_service.retrieve_relevant.call_args
        assert call_args[1]["k"] == 10

    @pytest.mark.asyncio
    async def test_enrich_prompt_disabled_rag(
        self,
        mock_retrieval_service,
    ):
        """Test prompt enrichment when RAG is disabled."""
        config = RAGConfig(enabled=False)
        service = RAGIntegrationService(
            retrieval_service=mock_retrieval_service,
            config=config,
        )

        result = await service.enrich_prompt(
            query="brave warrior",
            base_prompt="Write a scene.",
        )

        # Verify no retrieval was performed
        mock_retrieval_service.retrieve_relevant.assert_not_called()
        assert result.chunks_retrieved == 0
        assert result.tokens_added == 0
        assert result.sources == []
        assert result.prompt == "Write a scene."

    @pytest.mark.asyncio
    async def test_enrich_prompt_empty_results(
        self,
        mock_retrieval_service,
    ):
        """Test prompt enrichment when no chunks are retrieved."""
        retrieval_result = RetrievalResult(
            chunks=[],
            query="unknown topic",
            total_retrieved=0,
        )
        mock_retrieval_service.retrieve_relevant.return_value = retrieval_result

        # Setup format_context to return empty context
        empty_context = FormattedContext(
            text="",
            sources=[],
            total_tokens=0,
            chunk_count=0,
        )
        mock_retrieval_service.format_context.return_value = empty_context

        service = RAGIntegrationService(retrieval_service=mock_retrieval_service)

        result = await service.enrich_prompt(
            query="unknown topic",
            base_prompt="Write a scene.",
        )

        # Context should be empty
        assert result.chunks_retrieved == 0
        assert result.tokens_added == 0
        # Base prompt should be returned unchanged
        assert result.prompt == "Write a scene."

    @pytest.mark.asyncio
    async def test_enrich_prompt_empty_query_raises_error(
        self,
        mock_retrieval_service,
    ):
        """Test that empty query raises ValueError."""
        service = RAGIntegrationService(retrieval_service=mock_retrieval_service)

        with pytest.raises(ValueError, match="query cannot be empty"):
            await service.enrich_prompt(
                query="",
                base_prompt="Write a scene.",
            )

        with pytest.raises(ValueError, match="query cannot be empty"):
            await service.enrich_prompt(
                query="   ",
                base_prompt="Write a scene.",
            )

    @pytest.mark.asyncio
    async def test_enrich_prompt_empty_base_prompt_raises_error(
        self,
        mock_retrieval_service,
    ):
        """Test that empty base_prompt raises ValueError."""
        service = RAGIntegrationService(retrieval_service=mock_retrieval_service)

        with pytest.raises(ValueError, match="base_prompt cannot be empty"):
            await service.enrich_prompt(
                query="warrior",
                base_prompt="",
            )

    @pytest.mark.asyncio
    async def test_enrich_prompt_metrics_tracking(
        self,
        mock_retrieval_service,
        mock_chunks,
        formatted_context,
    ):
        """Test that metrics are tracked correctly."""
        retrieval_result = RetrievalResult(
            chunks=mock_chunks,
            query="warrior",
            total_retrieved=2,
        )
        mock_retrieval_service.retrieve_relevant.return_value = retrieval_result
        mock_retrieval_service.format_context.return_value = formatted_context

        service = RAGIntegrationService(retrieval_service=mock_retrieval_service)

        # Perform two enrichments
        await service.enrich_prompt(
            query="warrior",
            base_prompt="Scene 1",
        )
        await service.enrich_prompt(
            query="sword",
            base_prompt="Scene 2",
        )

        metrics = service.get_metrics()
        assert metrics.queries_total == 2
        assert metrics.chunks_retrieved_total == 4  # 2 per query
        assert metrics.tokens_added_total == 100  # 50 per query
        assert metrics.failed_queries == 0
        assert metrics.avg_chunks_per_query == 2.0

    @pytest.mark.asyncio
    async def test_enrich_prompt_failure_tracking(
        self,
        mock_retrieval_service,
    ):
        """Test that failed queries are tracked."""
        from src.contexts.knowledge.application.ports.i_vector_store import (
            VectorStoreError,
        )

        mock_retrieval_service.retrieve_relevant.side_effect = VectorStoreError(
            "DB error"
        )

        service = RAGIntegrationService(retrieval_service=mock_retrieval_service)

        with pytest.raises(VectorStoreError):
            await service.enrich_prompt(
                query="warrior",
                base_prompt="Scene",
            )

        metrics = service.get_metrics()
        assert metrics.queries_total == 1
        assert metrics.failed_queries == 1

    def test_get_metrics(self, mock_retrieval_service):
        """Test getting metrics returns a copy."""
        service = RAGIntegrationService(retrieval_service=mock_retrieval_service)

        metrics1 = service.get_metrics()
        metrics2 = service.get_metrics()

        # Should be equal but different objects
        assert metrics1 == metrics2
        assert metrics1 is not metrics2

    @pytest.mark.asyncio
    async def test_reset_metrics(
        self,
        mock_retrieval_service,
        mock_chunks,
        formatted_context,
    ):
        """Test resetting metrics."""
        # Setup mock to avoid actual calls
        retrieval_result = RetrievalResult(
            chunks=mock_chunks,
            query="test",
            total_retrieved=2,
        )
        mock_retrieval_service.retrieve_relevant.return_value = retrieval_result
        mock_retrieval_service.format_context.return_value = formatted_context

        service = RAGIntegrationService(retrieval_service=mock_retrieval_service)

        await service.enrich_prompt(query="test", base_prompt="test")

        metrics = service.get_metrics()
        assert metrics.queries_total > 0

        service.reset_metrics()

        metrics_after = service.get_metrics()
        assert metrics_after.queries_total == 0
        assert metrics_after.chunks_retrieved_total == 0

    def test_update_config(self, mock_retrieval_service):
        """Test updating configuration."""
        service = RAGIntegrationService(retrieval_service=mock_retrieval_service)

        new_config = RAGConfig(max_chunks=20, enabled=False)
        service.update_config(new_config)

        assert service.get_config() == new_config

    def test_get_config(self, mock_retrieval_service):
        """Test getting configuration returns a copy."""
        config = RAGConfig(max_chunks=15)
        service = RAGIntegrationService(
            retrieval_service=mock_retrieval_service,
            config=config,
        )

        retrieved_config = service.get_config()
        assert retrieved_config == config

    def test_build_enriched_prompt_no_context(
        self,
        mock_retrieval_service,
    ):
        """Test building enriched prompt with no context."""
        service = RAGIntegrationService(retrieval_service=mock_retrieval_service)

        empty_context = FormattedContext(
            text="",
            sources=[],
            total_tokens=0,
            chunk_count=0,
        )

        result = service._build_enriched_prompt(
            base_prompt="Write a scene.",
            context=empty_context,
        )

        # Should return base prompt unchanged
        assert result == "Write a scene."

    def test_build_enriched_prompt_with_context(
        self,
        mock_retrieval_service,
        formatted_context,
    ):
        """Test building enriched prompt with context."""
        service = RAGIntegrationService(retrieval_service=mock_retrieval_service)

        result = service._build_enriched_prompt(
            base_prompt="Write a scene.",
            context=formatted_context,
        )

        # Should contain context section
        assert "Relevant Context:" in result
        assert "Sir Arthur is a brave warrior" in result
        assert "Write a scene." in result

        # Verify the separator
        assert "---" in result


class TestEnrichedPrompt:
    """Tests for EnrichedPrompt value object."""

    def test_enriched_prompt_attributes(self):
        """Test EnrichedPrompt data class."""
        context = FormattedContext(
            text="Sample context",
            sources=["CHAR:test"],
            total_tokens=10,
            chunk_count=1,
        )

        enriched = EnrichedPrompt(
            prompt="Sample prompt",
            context=context,
            chunks_retrieved=1,
            sources=["CHAR:test"],
            tokens_added=10,
        )

        assert enriched.prompt == "Sample prompt"
        assert enriched.context == context
        assert enriched.chunks_retrieved == 1
        assert enriched.sources == ["CHAR:test"]
        assert enriched.tokens_added == 10
