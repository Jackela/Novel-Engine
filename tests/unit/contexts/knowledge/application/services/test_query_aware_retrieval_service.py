"""
Unit Tests for Query-Aware Retrieval Service

Warzone 4: AI Brain - BRAIN-009B

Tests for the query-aware retrieval service that integrates QueryRewriter
with RetrievalService to execute retrieval for all query variants and merge results.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.contexts.knowledge.application.services.query_aware_retrieval_service import (
    QueryAwareRetrievalService,
    QueryAwareConfig,
    QueryAwareRetrievalResult,
    QueryAwareMetrics,
    DEFAULT_MAX_CONCURRENT,
)
from src.contexts.knowledge.application.services.query_rewriter import (
    QueryRewriter,
    RewriteStrategy,
    RewriteConfig,
    RewriteResult,
)
from src.contexts.knowledge.application.services.retrieval_service import (
    RetrievedChunk,
    RetrievalFilter,
    RetrievalOptions,
)
from src.contexts.knowledge.domain.models.source_type import SourceType
from src.contexts.knowledge.application.ports.i_embedding_service import IEmbeddingService
from src.contexts.knowledge.application.ports.i_vector_store import IVectorStore
from src.contexts.knowledge.infrastructure.adapters.gemini_llm_client import (
    MockLLMClient,
)


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = AsyncMock(spec=IEmbeddingService)

    async def mock_embed(text: str) -> list[float]:
        # Return deterministic mock embedding
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        return [(hash_val + i) % 100 / 100.0 for i in range(1536)]

    service.embed = mock_embed
    return service


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = AsyncMock(spec=IVectorStore)
    store.query = AsyncMock(return_value=[])
    store.health_check = AsyncMock(return_value=True)
    return store


@pytest.fixture
def mock_query_rewriter():
    """Create a mock query rewriter."""
    rewriter = AsyncMock(spec=QueryRewriter)

    async def mock_rewrite(query: str, config: RewriteConfig | None = None) -> RewriteResult:
        return RewriteResult(
            original_query=query,
            variants=[query, f"{query} variant 1", f"{query} variant 2"],
            strategy=RewriteStrategy.HYBRID,
            cached=False,
            tokens_used=100,
        )

    rewriter.rewrite = mock_rewrite
    return rewriter


@pytest.fixture
def query_aware_service(
    mock_embedding_service,
    mock_vector_store,
):
    """Create a QueryAwareRetrievalService with mocked dependencies."""
    return QueryAwareRetrievalService(
        embedding_service=mock_embedding_service,
        vector_store=mock_vector_store,
        query_rewriter=None,  # Start without rewriter
    )


class TestQueryAwareConfig:
    """Tests for QueryAwareConfig value object."""

    def test_default_config(self):
        """Test default configuration values."""
        config = QueryAwareConfig()

        assert config.enable_rewriting is True
        assert config.rewrite_strategy == RewriteStrategy.HYBRID
        assert config.max_variants == 3
        assert config.merge_strategy == "rrf"
        assert config.max_concurrent == DEFAULT_MAX_CONCURRENT
        assert config.deduplicate_results is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = QueryAwareConfig(
            enable_rewriting=False,
            rewrite_strategy=RewriteStrategy.SYNONYM,
            max_variants=5,
            merge_strategy="score",
            max_concurrent=5,
            deduplicate_results=False,
        )

        assert config.enable_rewriting is False
        assert config.rewrite_strategy == RewriteStrategy.SYNONYM
        assert config.max_variants == 5
        assert config.merge_strategy == "score"
        assert config.max_concurrent == 5
        assert config.deduplicate_results is False

    def test_config_frozen(self):
        """Test config is immutable (frozen dataclass)."""
        config = QueryAwareConfig()
        with pytest.raises(AttributeError):
            config.max_variants = 5


class TestQueryAwareRetrievalResult:
    """Tests for QueryAwareRetrievalResult value object."""

    def test_result_creation(self):
        """Test creating a query-aware retrieval result."""
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="char1",
                source_type=SourceType.CHARACTER,
                content="A brave warrior",
                score=0.9,
                metadata={},
            )
        ]

        result = QueryAwareRetrievalResult(
            chunks=chunks,
            original_query="warrior",
            queries_executed=["warrior", "warrior variant 1"],
            total_retrieved=5,
            deduplicated=2,
        )

        assert result.original_query == "warrior"
        assert len(result.chunks) == 1
        assert len(result.queries_executed) == 2
        assert result.total_retrieved == 5
        assert result.deduplicated == 2


class TestQueryAwareRetrievalService:
    """Tests for QueryAwareRetrievalService."""

    def test_initialization(self, mock_embedding_service, mock_vector_store):
        """Test QueryAwareRetrievalService initialization."""
        service = QueryAwareRetrievalService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
        )

        assert service._embedding_service == mock_embedding_service
        assert service._vector_store == mock_vector_store
        assert service._config.enable_rewriting is True

    def test_initialization_with_rewriter(
        self,
        mock_embedding_service,
        mock_vector_store,
        mock_query_rewriter,
    ):
        """Test initialization with query rewriter."""
        service = QueryAwareRetrievalService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            query_rewriter=mock_query_rewriter,
        )

        assert service._query_rewriter == mock_query_rewriter

    @pytest.mark.asyncio
    async def test_retrieve_without_rewriting(self, query_aware_service):
        """Test retrieval without query rewriting."""
        # Configure with rewriting disabled
        config = QueryAwareConfig(enable_rewriting=False)

        result = await query_aware_service.retrieve_relevant(
            query="brave warrior",
            k=5,
            config_override=config,
        )

        assert result.original_query == "brave warrior"
        assert len(result.queries_executed) == 1  # Only original query
        assert result.queries_executed[0] == "brave warrior"
        assert result.rewrite_result is None

    @pytest.mark.asyncio
    async def test_retrieve_with_rewriting(
        self,
        mock_embedding_service,
        mock_vector_store,
        mock_query_rewriter,
    ):
        """Test retrieval with query rewriting."""
        # Set up mock to return some chunks
        chunk = RetrievedChunk(
            chunk_id="1",
            source_id="char1",
            source_type=SourceType.CHARACTER,
            content="A brave warrior",
            score=0.9,
            metadata={},
        )

        mock_vector_store.query = AsyncMock(return_value=[
            MagicMock(
                id="1",
                text="A brave warrior",
                score=0.9,
                metadata={"source_id": "char1", "source_type": "CHARACTER"},
            )
        ])

        service = QueryAwareRetrievalService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            query_rewriter=mock_query_rewriter,
        )

        result = await service.retrieve_relevant(
            query="brave warrior",
            k=5,
        )

        assert result.original_query == "brave warrior"
        assert len(result.queries_executed) == 3  # Original + 2 variants
        assert result.rewrite_result is not None
        assert result.tokens_used == 100

    @pytest.mark.asyncio
    async def test_retrieve_empty_query_raises_error(self, query_aware_service):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="query cannot be empty"):
            await query_aware_service.retrieve_relevant(query="")

    @pytest.mark.asyncio
    async def test_format_context(self, query_aware_service):
        """Test formatting context from query-aware result."""
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="char1",
                source_type=SourceType.CHARACTER,
                content="A brave warrior",
                score=0.9,
                metadata={},
            )
        ]

        result = QueryAwareRetrievalResult(
            chunks=chunks,
            original_query="warrior",
            queries_executed=["warrior"],
            total_retrieved=1,
        )

        formatted = query_aware_service.format_context(result)

        assert formatted.text
        assert formatted.chunk_count == 1
        assert len(formatted.sources) == 1

    def test_get_metrics(self, query_aware_service):
        """Test getting service metrics."""
        metrics = query_aware_service.get_metrics()

        assert "queries_total" in metrics
        assert "rewrites_total" in metrics
        assert "cache_hits_total" in metrics
        assert "tokens_used_total" in metrics
        assert "tokens_saved_total" in metrics
        assert "cache_hit_rate" in metrics

    def test_reset_metrics(self, query_aware_service):
        """Test resetting metrics."""
        # Set some metrics by doing a retrieval
        import asyncio

        async def do_retrieval():
            await query_aware_service.retrieve_relevant(
                query="test",
                config_override=QueryAwareConfig(enable_rewriting=False),
            )

        asyncio.run(do_retrieval())

        metrics_before = query_aware_service.get_metrics()
        assert metrics_before["queries_total"] > 0

        # Reset
        query_aware_service.reset_metrics()

        metrics_after = query_aware_service.get_metrics()
        assert metrics_after["queries_total"] == 0


class TestMergeResults:
    """Tests for result merging strategies."""

    @pytest.fixture
    def service(self, mock_embedding_service, mock_vector_store):
        """Create service for merge testing."""
        return QueryAwareRetrievalService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            query_rewriter=None,
        )

    def test_merge_rrf(self, service):
        """Test Reciprocal Rank Fusion merging."""
        all_chunks = [
            # Same chunk appearing in different queries
            (
                RetrievedChunk(
                    chunk_id="1",
                    source_id="char1",
                    source_type=SourceType.CHARACTER,
                    content="Content 1",
                    score=0.5,
                    metadata={},
                ),
                0,  # query_index
                0,  # rank (first in query 0)
            ),
            (
                RetrievedChunk(
                    chunk_id="1",
                    source_id="char1",
                    source_type=SourceType.CHARACTER,
                    content="Content 1",
                    score=0.7,
                    metadata={},
                ),
                1,  # query_index
                2,  # rank (third in query 1)
            ),
            # Different chunk
            (
                RetrievedChunk(
                    chunk_id="2",
                    source_id="char2",
                    source_type=SourceType.CHARACTER,
                    content="Content 2",
                    score=0.8,
                    metadata={},
                ),
                0,
                1,
            ),
        ]

        merged = service._merge_rrf(all_chunks, k=60)

        # Should have 2 unique chunks
        assert len(merged) == 2
        # Chunk 1 should have higher RRF score (appears twice, once at rank 0)
        assert merged[0].chunk_id == "1"
        assert merged[1].chunk_id == "2"

    def test_merge_by_score(self, service):
        """Test score-based merging."""
        all_chunks = [
            # Same chunk with different scores
            (
                RetrievedChunk(
                    chunk_id="1",
                    source_id="char1",
                    source_type=SourceType.CHARACTER,
                    content="Content 1",
                    score=0.5,
                    metadata={},
                ),
                0,
                1,
            ),
            (
                RetrievedChunk(
                    chunk_id="1",
                    source_id="char1",
                    source_type=SourceType.CHARACTER,
                    content="Content 1",
                    score=0.9,  # Higher score
                    metadata={},
                ),
                1,
                0,
            ),
            # Different chunk
            (
                RetrievedChunk(
                    chunk_id="2",
                    source_id="char2",
                    source_type=SourceType.CHARACTER,
                    content="Content 2",
                    score=0.7,
                    metadata={},
                ),
                0,
                0,
            ),
        ]

        merged = service._merge_by_score(all_chunks, k=5)

        # Should have 2 unique chunks
        assert len(merged) == 2
        # Chunk 1 should have score 0.9 (highest)
        assert merged[0].chunk_id == "1"
        assert merged[0].score == 0.9
        assert merged[1].chunk_id == "2"


class TestDeduplication:
    """Tests for chunk deduplication."""

    @pytest.fixture
    def service(self, mock_embedding_service, mock_vector_store):
        """Create service for deduplication testing."""
        return QueryAwareRetrievalService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            query_rewriter=None,
        )

    def test_deduplicate_chunks(self, service):
        """Test removing duplicate chunks by content hash."""
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="char1",
                source_type=SourceType.CHARACTER,
                content="Same content",
                score=0.9,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="2",  # Different ID, same content
                source_id="char2",
                source_type=SourceType.CHARACTER,
                content="Same content",
                score=0.8,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="3",
                source_id="char3",
                source_type=SourceType.CHARACTER,
                content="Different content",
                score=0.7,
                metadata={},
            ),
        ]

        deduplicated = service._deduplicate_chunks(chunks)

        # Should keep 2 chunks (first "Same content" and "Different content")
        assert len(deduplicated) == 2
        assert deduplicated[0].chunk_id == "1"  # First duplicate kept
        assert deduplicated[1].chunk_id == "3"  # Unique content kept


class TestClarificationStrategy:
    """Tests for CLARIFICATION strategy in query rewriting."""

    @pytest.mark.asyncio
    async def test_clarification_strategy(self):
        """Test CLARIFICATION strategy generates questions."""
        from src.contexts.knowledge.application.ports.i_llm_client import (
            ILLMClient,
            LLMRequest,
            LLMResponse,
        )

        # Create mock LLM that returns clarifying questions
        client = AsyncMock(spec=ILLMClient)

        async def mock_generate(request: LLMRequest) -> LLMResponse:
            return LLMResponse(
                text='["Did you mean the protagonist or antagonist?", "Which scene are you referring to?"]',
                model="mock-model",
            )

        client.generate = mock_generate

        rewriter = QueryRewriter(llm_client=client)

        result = await rewriter.rewrite(
            "the character",
            RewriteConfig(strategy=RewriteStrategy.CLARIFICATION),
        )

        assert result.strategy == RewriteStrategy.CLARIFICATION
        assert len(result.clarifications) > 0
        assert any("protagonist" in q.lower() for q in result.clarifications)

    def test_parse_clarifications(self):
        """Test parsing clarifying questions from LLM response."""
        from src.contexts.knowledge.application.services.query_rewriter import (
            QueryRewriter,
        )

        rewriter = QueryRewriter(llm_client=MockLLMClient())

        # Test JSON array format
        questions = rewriter._parse_clarifications(
            '["Question 1?", "Question 2?", "Question 3?"]'
        )
        assert len(questions) == 3
        assert questions[0] == "Question 1?"

        # Test markdown format
        questions = rewriter._parse_clarifications(
            '```json\n["Q1?", "Q2?"]\n```'
        )
        assert len(questions) == 2

        # Test fallback extraction (questions ending with ?)
        questions = rewriter._parse_clarifications(
            "Some text\nWhat do you mean?\nAnother question?\nMore text"
        )
        assert len(questions) >= 1


class TestTokenTracking:
    """Tests for token usage tracking."""

    @pytest.mark.asyncio
    async def test_token_tracking_on_cache_miss(self):
        """Test token tracking on cache miss."""
        from src.contexts.knowledge.application.ports.i_llm_client import (
            ILLMClient,
            LLMRequest,
            LLMResponse,
        )

        client = AsyncMock(spec=ILLMClient)

        async def mock_generate(request: LLMRequest) -> LLMResponse:
            # Return a long response to test token estimation
            return LLMResponse(
                text='["variant one", "variant two", "variant three", "variant four"]',
                model="mock-model",
            )

        client.generate = mock_generate

        rewriter = QueryRewriter(llm_client=client)

        result = await rewriter.rewrite("test query")

        # Tokens used should be estimated
        assert result.tokens_used > 0
        assert result.tokens_saved == 0  # No tokens saved on cache miss
        assert result.cached is False

    @pytest.mark.asyncio
    async def test_token_tracking_on_cache_hit(self):
        """Test token tracking on cache hit."""
        from src.contexts.knowledge.application.ports.i_llm_client import (
            ILLMClient,
            LLMRequest,
            LLMResponse,
        )

        client = AsyncMock(spec=ILLMClient)

        async def mock_generate(request: LLMRequest) -> LLMResponse:
            return LLMResponse(
                text='["variant one", "variant two"]',
                model="mock-model",
            )

        client.generate = mock_generate

        rewriter = QueryRewriter(llm_client=client)

        # First call - cache miss
        result1 = await rewriter.rewrite("test query")
        assert result1.cached is False
        tokens_used_first = result1.tokens_used

        # Second call - cache hit
        result2 = await rewriter.rewrite("test query")
        assert result2.cached is True
        assert result2.tokens_used == 0  # No tokens used on cache hit
        assert result2.tokens_saved == tokens_used_first  # Tokens saved equal to first call

    def test_estimate_tokens(self):
        """Test token estimation."""
        from src.contexts.knowledge.application.services.query_rewriter import (
            QueryRewriter,
        )

        rewriter = QueryRewriter(llm_client=MockLLMClient())

        # Empty text
        assert rewriter._estimate_tokens("") == 0

        # Short text (rough estimate: ~4 chars per token)
        tokens = rewriter._estimate_tokens("test query")
        assert tokens >= 1  # At least 1 token

        # Longer text
        tokens = rewriter._estimate_tokens("a" * 100)
        assert tokens == 25  # 100 chars / 4 = 25 tokens

    def test_cache_stats_includes_tokens(self):
        """Test cache stats include token tracking."""
        from src.contexts.knowledge.application.ports.i_llm_client import (
            ILLMClient,
            LLMRequest,
            LLMResponse,
        )
        from unittest.mock import AsyncMock

        client = AsyncMock(spec=ILLMClient)

        async def mock_generate(request: LLMRequest) -> LLMResponse:
            return LLMResponse(
                text='["variant one", "variant two"]',
                model="mock-model",
            )

        client.generate = mock_generate

        rewriter = QueryRewriter(llm_client=client)

        stats = rewriter.get_cache_stats()
        assert stats["total_tokens_saved"] == 0

        # Do a rewrite
        import asyncio

        async def do_rewrite():
            await rewriter.rewrite("test query")
            # Second call for cache hit
            await rewriter.rewrite("test query")

        asyncio.run(do_rewrite())

        stats = rewriter.get_cache_stats()
        assert stats["total_tokens_saved"] > 0
