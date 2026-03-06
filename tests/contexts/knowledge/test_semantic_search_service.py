"""
Test suite for Semantic Search Service (QueryAwareRetrievalService).

Tests query-aware retrieval with multi-query expansion and result merging.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch

from src.contexts.knowledge.application.services.query_aware_retrieval_service import (
    QueryAwareRetrievalService,
    QueryAwareConfig,
    QueryAwareRetrievalResult,
    QueryAwareMetrics,
    DEFAULT_MAX_CONCURRENT,
)
from src.contexts.knowledge.application.services.retrieval_service import (
    RetrievalService,
    RetrievalFilter,
    RetrievalOptions,
    RetrievalResult,
)
from src.contexts.knowledge.application.services.query_rewriter import (
    QueryRewriter,
    RewriteConfig,
    RewriteResult,
    RewriteStrategy,
)
from src.contexts.knowledge.application.services.knowledge_ingestion_service import RetrievedChunk
from src.contexts.knowledge.domain.models.source_type import SourceType
from src.contexts.knowledge.application.ports.i_vector_store import QueryResult


class TestQueryAwareConfig:
    """Tests for QueryAwareConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = QueryAwareConfig()
        
        assert config.enable_rewriting is True
        assert config.rewrite_strategy == RewriteStrategy.HYBRID
        assert config.max_variants == 3
        assert config.merge_strategy == "rrf"
        assert config.max_concurrent == DEFAULT_MAX_CONCURRENT
        assert config.deduplicate_results is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = QueryAwareConfig(
            enable_rewriting=False,
            rewrite_strategy=RewriteStrategy.SEMANTIC,
            max_variants=5,
            merge_strategy="score",
            max_concurrent=5,
            deduplicate_results=False,
        )
        
        assert config.enable_rewriting is False
        assert config.rewrite_strategy == RewriteStrategy.SEMANTIC
        assert config.max_variants == 5
        assert config.merge_strategy == "score"
        assert config.max_concurrent == 5
        assert config.deduplicate_results is False


class TestQueryAwareRetrievalResult:
    """Tests for QueryAwareRetrievalResult dataclass."""

    def test_result_creation(self):
        """Test creating retrieval result."""
        result = QueryAwareRetrievalResult(
            chunks=[],
            original_query="test query",
            queries_executed=["test query"],
            total_retrieved=0,
        )
        
        assert result.original_query == "test query"
        assert result.queries_executed == ["test query"]
        assert result.total_retrieved == 0
        assert result.deduplicated == 0
        assert result.tokens_used == 0

    def test_result_with_rewrite(self):
        """Test result with query rewrite information."""
        rewrite_result = RewriteResult(
            original_query="test",
            variants=["test", "variant"],
            tokens_used=100,
        )
        
        result = QueryAwareRetrievalResult(
            chunks=[],
            original_query="test query",
            queries_executed=["test query", "variant query"],
            total_retrieved=10,
            rewrite_result=rewrite_result,
            tokens_used=100,
        )
        
        assert result.rewrite_result is not None
        assert len(result.queries_executed) == 2


class TestQueryAwareMetrics:
    """Tests for QueryAwareMetrics dataclass."""

    def test_default_metrics(self):
        """Test default metrics."""
        metrics = QueryAwareMetrics()
        
        assert metrics.queries_total == 0
        assert metrics.rewrites_total == 0
        assert metrics.cache_hits_total == 0
        assert metrics.tokens_used_total == 0
        assert metrics.tokens_saved_total == 0
        assert metrics.merged_results_total == 0

    def test_metrics_increment(self):
        """Test incrementing metrics."""
        metrics = QueryAwareMetrics()
        
        metrics.queries_total += 1
        metrics.rewrites_total += 1
        
        assert metrics.queries_total == 1
        assert metrics.rewrites_total == 1


@pytest.mark.asyncio
class TestQueryAwareRetrievalService:
    """Tests for QueryAwareRetrievalService."""

    @pytest_asyncio.fixture
    async def mock_embedding_service(self):
        """Create mock embedding service."""
        service = AsyncMock()
        service.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])
        return service

    @pytest_asyncio.fixture
    async def mock_vector_store(self):
        """Create mock vector store."""
        store = AsyncMock()
        store.query = AsyncMock(return_value=[])
        return store

    @pytest_asyncio.fixture
    async def mock_query_rewriter(self):
        """Create mock query rewriter."""
        rewriter = AsyncMock()
        rewriter.rewrite = AsyncMock(return_value=RewriteResult(
            original_query="test",
            variants=["test", "variant 1", "variant 2"],
            tokens_used=50,
        ))
        return rewriter

    @pytest_asyncio.fixture
    async def retrieval_service(self, mock_embedding_service, mock_vector_store, mock_query_rewriter):
        """Create query-aware retrieval service."""
        return QueryAwareRetrievalService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            query_rewriter=mock_query_rewriter,
        )

    async def test_initialization(self, mock_embedding_service, mock_vector_store):
        """Test service initialization."""
        service = QueryAwareRetrievalService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            default_collection="custom_collection",
        )
        
        assert service._default_collection == "custom_collection"
        assert service._query_rewriter is None

    async def test_initialization_with_rewriter(self, retrieval_service, mock_query_rewriter):
        """Test initialization with query rewriter."""
        assert retrieval_service._query_rewriter == mock_query_rewriter

    async def test_retrieve_relevant_empty_query(self, retrieval_service):
        """Test retrieval with empty query raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await retrieval_service.retrieve_relevant("")

    async def test_retrieve_relevant_whitespace_query(self, retrieval_service):
        """Test retrieval with whitespace-only query raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            await retrieval_service.retrieve_relevant("   ")

    async def test_retrieve_relevant_without_rewriting(self, retrieval_service, mock_vector_store):
        """Test retrieval without query rewriting."""
        mock_results = [
            QueryResult(
                id="chunk_1",
                text="Test content",
                score=0.9,
                metadata={"source_id": "source_1", "source_type": "CHARACTER"},
            ),
        ]
        mock_vector_store.query = AsyncMock(return_value=mock_results)
        
        config = QueryAwareConfig(enable_rewriting=False)
        result = await retrieval_service.retrieve_relevant(
            query="test query",
            config_override=config,
        )
        
        assert result.original_query == "test query"
        assert len(result.queries_executed) == 1
        assert result.queries_executed[0] == "test query"

    async def test_retrieve_relevant_with_rewriting(self, retrieval_service, mock_query_rewriter, mock_vector_store):
        """Test retrieval with query rewriting."""
        mock_results = [
            QueryResult(
                id="chunk_1",
                text="Test content",
                score=0.9,
                metadata={"source_id": "source_1"},
            ),
        ]
        mock_vector_store.query = AsyncMock(return_value=mock_results)
        
        result = await retrieval_service.retrieve_relevant("test query")
        
        assert len(result.queries_executed) > 1  # Should have variants
        mock_query_rewriter.rewrite.assert_called_once()

    async def test_retrieve_relevant_no_rewriter(self, retrieval_service, mock_query_rewriter, mock_vector_store):
        """Test retrieval when rewriter is None but rewriting is enabled."""
        retrieval_service._query_rewriter = None
        
        mock_results = [
            QueryResult(
                id="chunk_1",
                text="Test content",
                score=0.9,
                metadata={"source_id": "source_1"},
            ),
        ]
        mock_vector_store.query = AsyncMock(return_value=mock_results)
        
        result = await retrieval_service.retrieve_relevant("test query")
        
        # Should still work with just original query
        assert len(result.queries_executed) == 1

    async def test_retrieve_relevant_with_filters(self, retrieval_service, mock_vector_store):
        """Test retrieval with filters."""
        mock_results = [
            QueryResult(
                id="chunk_1",
                text="Test content",
                score=0.9,
                metadata={"source_id": "source_1", "source_type": "CHARACTER"},
            ),
        ]
        mock_vector_store.query = AsyncMock(return_value=mock_results)
        
        filters = RetrievalFilter(source_types=[SourceType.CHARACTER])
        result = await retrieval_service.retrieve_relevant(
            query="test query",
            filters=filters,
        )
        
        # Verify filter was passed to underlying query
        assert result.original_query == "test query"

    async def test_retrieve_relevant_with_custom_collection(self, retrieval_service, mock_vector_store):
        """Test retrieval with custom collection."""
        mock_results = [
            QueryResult(
                id="chunk_1",
                text="Test content",
                score=0.9,
                metadata={"source_id": "source_1"},
            ),
        ]
        mock_vector_store.query = AsyncMock(return_value=mock_results)
        
        result = await retrieval_service.retrieve_relevant(
            query="test query",
            collection="custom_collection",
        )
        
        assert result.original_query == "test query"


@pytest.mark.asyncio
class TestQueryAwareRetrievalServiceMerging:
    """Tests for result merging strategies."""

    @pytest_asyncio.fixture
    async def retrieval_service(self):
        """Create retrieval service."""
        embedding_service = AsyncMock()
        vector_store = AsyncMock()
        
        return QueryAwareRetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

    def test_merge_rrf_empty_list(self, retrieval_service):
        """Test RRF merge with empty list."""
        result = retrieval_service._merge_rrf([], k=5)
        
        assert result == []

    def test_merge_rrf_single_chunk(self, retrieval_service):
        """Test RRF merge with single chunk."""
        chunk = RetrievedChunk(
            chunk_id="chunk_1",
            source_id="source_1",
            source_type=SourceType.CHARACTER,
            content="Test content",
            score=0.9,
            metadata={},
        )
        all_chunks = [(chunk, 0, 0)]  # (chunk, query_idx, rank)
        
        result = retrieval_service._merge_rrf(all_chunks, k=5)
        
        assert len(result) == 1
        assert result[0].chunk_id == "chunk_1"

    def test_merge_rrf_multiple_chunks_same_query(self, retrieval_service):
        """Test RRF merge with multiple chunks from same query."""
        chunks = [
            RetrievedChunk(
                chunk_id=f"chunk_{i}",
                source_id="source_1",
                source_type=SourceType.CHARACTER,
                content=f"Content {i}",
                score=0.9 - i * 0.1,
                metadata={},
            )
            for i in range(3)
        ]
        all_chunks = [(chunk, 0, i) for i, chunk in enumerate(chunks)]
        
        result = retrieval_service._merge_rrf(all_chunks, k=5)
        
        assert len(result) == 3
        # Higher rank (lower index) should have higher score
        assert result[0].score > result[1].score

    def test_merge_rrf_deduplicates_same_chunk(self, retrieval_service):
        """Test RRF merge deduplicates same chunk from different queries."""
        chunk = RetrievedChunk(
            chunk_id="chunk_1",
            source_id="source_1",
            source_type=SourceType.CHARACTER,
            content="Test content",
            score=0.9,
            metadata={},
        )
        # Same chunk appears in results from different queries
        all_chunks = [
            (chunk, 0, 0),
            (chunk, 1, 1),
        ]
        
        result = retrieval_service._merge_rrf(all_chunks, k=5)
        
        assert len(result) == 1
        # Score should be accumulated from both appearances
        assert result[0].score > 0.9

    def test_merge_by_score_empty_list(self, retrieval_service):
        """Test score-based merge with empty list."""
        result = retrieval_service._merge_by_score([], k=5)
        
        assert result == []

    def test_merge_by_score_single_chunk(self, retrieval_service):
        """Test score-based merge with single chunk."""
        chunk = RetrievedChunk(
            chunk_id="chunk_1",
            source_id="source_1",
            source_type=SourceType.CHARACTER,
            content="Test content",
            score=0.9,
            metadata={},
        )
        all_chunks = [(chunk, 0, 0)]
        
        result = retrieval_service._merge_by_score(all_chunks, k=5)
        
        assert len(result) == 1

    def test_merge_by_score_keeps_highest_score(self, retrieval_service):
        """Test that score merge keeps highest score for duplicate chunks."""
        chunk_low = RetrievedChunk(
            chunk_id="chunk_1",
            source_id="source_1",
            source_type=SourceType.CHARACTER,
            content="Test content",
            score=0.7,
            metadata={},
        )
        chunk_high = RetrievedChunk(
            chunk_id="chunk_1",
            source_id="source_1",
            source_type=SourceType.CHARACTER,
            content="Test content",
            score=0.9,
            metadata={},
        )
        all_chunks = [
            (chunk_low, 0, 1),
            (chunk_high, 1, 0),
        ]
        
        result = retrieval_service._merge_by_score(all_chunks, k=5)
        
        assert len(result) == 1
        assert result[0].score == 0.9

    def test_merge_results_rrf_strategy(self, retrieval_service):
        """Test merge results with RRF strategy."""
        chunk = RetrievedChunk(
            chunk_id="chunk_1",
            source_id="source_1",
            source_type=SourceType.CHARACTER,
            content="Test",
            score=0.9,
            metadata={},
        )
        all_chunks = [(chunk, 0, 0)]
        
        result = retrieval_service._merge_results(all_chunks, merge_strategy="rrf", k=5)
        
        assert len(result) == 1

    def test_merge_results_score_strategy(self, retrieval_service):
        """Test merge results with score strategy."""
        chunk = RetrievedChunk(
            chunk_id="chunk_1",
            source_id="source_1",
            source_type=SourceType.CHARACTER,
            content="Test",
            score=0.9,
            metadata={},
        )
        all_chunks = [(chunk, 0, 0)]
        
        result = retrieval_service._merge_results(all_chunks, merge_strategy="score", k=5)
        
        assert len(result) == 1


class TestQueryAwareRetrievalServiceDeduplication:
    """Tests for chunk deduplication."""

    @pytest_asyncio.fixture
    async def retrieval_service(self):
        """Create retrieval service."""
        embedding_service = AsyncMock()
        vector_store = AsyncMock()
        
        return QueryAwareRetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

    def test_deduplicate_chunks_empty_list(self, retrieval_service):
        """Test deduplication with empty list."""
        result = retrieval_service._deduplicate_chunks([])
        
        assert result == []

    def test_deduplicate_chunks_single_chunk(self, retrieval_service):
        """Test deduplication with single chunk."""
        chunks = [
            RetrievedChunk(
                chunk_id="chunk_1",
                source_id="source_1",
                source_type=SourceType.CHARACTER,
                content="Test content",
                score=0.9,
                metadata={},
            ),
        ]
        
        result = retrieval_service._deduplicate_chunks(chunks)
        
        assert len(result) == 1

    def test_deduplicate_chunks_unique_content(self, retrieval_service):
        """Test deduplication with unique content."""
        chunks = [
            RetrievedChunk(
                chunk_id="chunk_1",
                source_id="source_1",
                source_type=SourceType.CHARACTER,
                content="Unique content one",
                score=0.9,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="chunk_2",
                source_id="source_1",
                source_type=SourceType.CHARACTER,
                content="Unique content two",
                score=0.8,
                metadata={},
            ),
        ]
        
        result = retrieval_service._deduplicate_chunks(chunks)
        
        assert len(result) == 2

    def test_deduplicate_chunks_duplicate_content(self, retrieval_service):
        """Test deduplication removes duplicate content."""
        chunks = [
            RetrievedChunk(
                chunk_id="chunk_1",
                source_id="source_1",
                source_type=SourceType.CHARACTER,
                content="Duplicate content",
                score=0.9,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="chunk_2",
                source_id="source_2",
                source_type=SourceType.CHARACTER,
                content="Duplicate content",
                score=0.8,
                metadata={},
            ),
        ]
        
        result = retrieval_service._deduplicate_chunks(chunks)
        
        assert len(result) == 1


@pytest.mark.asyncio
class TestQueryAwareRetrievalServiceFormatting:
    """Tests for context formatting."""

    @pytest_asyncio.fixture
    async def retrieval_service(self):
        """Create retrieval service."""
        embedding_service = AsyncMock()
        vector_store = AsyncMock()
        
        return QueryAwareRetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

    async def test_format_context(self, retrieval_service):
        """Test formatting context from retrieval result."""
        chunks = [
            RetrievedChunk(
                chunk_id="chunk_1",
                source_id="source_1",
                source_type=SourceType.CHARACTER,
                content="Character description",
                score=0.9,
                metadata={"chunk_index": 1, "total_chunks": 1},
            ),
        ]
        result = QueryAwareRetrievalResult(
            chunks=chunks,
            original_query="test query",
            queries_executed=["test query"],
            total_retrieved=1,
        )
        
        context = retrieval_service.format_context(result)
        
        assert context.text != ""
        assert context.chunk_count == 1

    async def test_format_context_empty(self, retrieval_service):
        """Test formatting empty context."""
        result = QueryAwareRetrievalResult(
            chunks=[],
            original_query="test query",
            queries_executed=["test query"],
            total_retrieved=0,
        )
        
        context = retrieval_service.format_context(result)
        
        assert context.text == ""
        assert context.chunk_count == 0


class TestQueryAwareRetrievalServiceMetrics:
    """Tests for metrics tracking."""

    @pytest_asyncio.fixture
    async def retrieval_service(self):
        """Create retrieval service."""
        embedding_service = AsyncMock()
        vector_store = AsyncMock()
        
        return QueryAwareRetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

    def test_get_metrics_initial(self, retrieval_service):
        """Test getting initial metrics."""
        metrics = retrieval_service.get_metrics()
        
        assert metrics["queries_total"] == 0
        assert metrics["rewrites_total"] == 0
        assert metrics["cache_hits_total"] == 0

    def test_reset_metrics(self, retrieval_service):
        """Test resetting metrics."""
        # Modify metrics
        retrieval_service._metrics.queries_total = 10
        
        # Reset
        retrieval_service.reset_metrics()
        
        metrics = retrieval_service.get_metrics()
        assert metrics["queries_total"] == 0

    def test_metrics_cache_hit_rate(self, retrieval_service):
        """Test cache hit rate calculation."""
        retrieval_service._metrics.rewrites_total = 10
        retrieval_service._metrics.cache_hits_total = 7
        
        metrics = retrieval_service.get_metrics()
        
        assert metrics["cache_hit_rate"] == 0.7

    def test_metrics_cache_hit_rate_no_rewrites(self, retrieval_service):
        """Test cache hit rate when no rewrites."""
        metrics = retrieval_service.get_metrics()
        
        assert metrics["cache_hit_rate"] == 0.0
