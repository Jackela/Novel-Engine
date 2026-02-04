"""
Unit Tests for Retrieval Service

Tests the RAG retrieval pipeline including:
- Query embedding
- Vector store search
- Filtering by source_type, tags, dates
- Relevance threshold
- Deduplication
- Context formatting

Constitution Compliance:
- Article III (TDD): Tests drive implementation
- Article V (SOLID): Each test has single responsibility

Warzone 4: AI Brain - BRAIN-006
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.contexts.knowledge.application.ports.i_embedding_service import (
    EmbeddingError,
    IEmbeddingService,
)
from src.contexts.knowledge.application.ports.i_vector_store import (
    IVectorStore,
    QueryResult,
    VectorStoreError,
)
from src.contexts.knowledge.application.services.retrieval_service import (
    DEFAULT_DEDUPLICATION_SIMILARITY,
    DEFAULT_RELEVANCE_THRESHOLD,
    FormattedContext,
    RetrievalFilter,
    RetrievalOptions,
    RetrievalResult,
    RetrievalService,
)
from src.contexts.knowledge.domain.models.source_type import SourceType
from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    RetrievedChunk,
)


@pytest.mark.unit
class TestRetrievalFilter:
    """Test RetrievalFilter value object."""

    def test_filter_empty(self):
        """Empty filter should produce empty where clause."""
        filter = RetrievalFilter()
        assert filter.to_where_clause() == {}

    def test_filter_by_source_types(self):
        """Filter should convert source types to where clause."""
        filter = RetrievalFilter(source_types=[SourceType.CHARACTER, SourceType.LORE])
        where = filter.to_where_clause()
        assert where["source_type"]["$in"] == ["CHARACTER", "LORE"]

    def test_filter_by_tags(self):
        """Filter should convert tags to where clause."""
        filter = RetrievalFilter(tags=["protagonist", "knight"])
        where = filter.to_where_clause()
        assert where["tags"]["$in"] == ["protagonist", "knight"]

    def test_filter_by_custom_metadata(self):
        """Filter should include custom metadata."""
        filter = RetrievalFilter(custom_metadata={"author": "alice"})
        where = filter.to_where_clause()
        assert where["author"] == "alice"

    def test_filter_combined(self):
        """Filter should combine multiple conditions."""
        filter = RetrievalFilter(
            source_types=[SourceType.CHARACTER],
            tags=["hero"],
            custom_metadata={"status": "active"},
        )
        where = filter.to_where_clause()
        assert "source_type" in where
        assert "tags" in where
        assert "status" in where

    def test_matches_no_metadata(self):
        """Filter should not match None metadata."""
        filter = RetrievalFilter()
        assert not filter.matches(None)

    def test_matches_empty_metadata(self):
        """Filter should match empty metadata when no constraints."""
        filter = RetrievalFilter()
        assert filter.matches({})

    def test_matches_date_range(self):
        """Filter should check date range."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        filter = RetrievalFilter(date_from=yesterday, date_to=tomorrow)

        # Matching date
        metadata = {"created_at": now.isoformat()}
        assert filter.matches(metadata)

        # Before range
        old_metadata = {"created_at": (yesterday - timedelta(days=1)).isoformat()}
        assert not filter.matches(old_metadata)

        # After range
        future_metadata = {"created_at": (tomorrow + timedelta(days=1)).isoformat()}
        assert not filter.matches(future_metadata)

    def test_matches_datetime_object(self):
        """Filter should handle datetime objects in metadata."""
        now = datetime.now()
        filter = RetrievalFilter(date_from=now - timedelta(hours=1))

        metadata = {"created_at": now}
        assert filter.matches(metadata)

    def test_matches_invalid_date_format(self):
        """Filter should reject invalid date formats."""
        filter = RetrievalFilter(date_from=datetime.now())

        metadata = {"created_at": "not-a-date"}
        assert not filter.matches(metadata)


@pytest.mark.unit
class TestRetrievalOptions:
    """Test RetrievalOptions value object."""

    def test_default_options(self):
        """Default options should have sensible defaults."""
        options = RetrievalOptions()
        assert options.k == 5
        assert options.min_score == DEFAULT_RELEVANCE_THRESHOLD
        assert options.deduplicate is True
        assert options.deduplication_threshold == DEFAULT_DEDUPLICATION_SIMILARITY

    def test_custom_options(self):
        """Custom options should override defaults."""
        options = RetrievalOptions(
            k=10,
            min_score=0.7,
            deduplicate=False,
            deduplication_threshold=0.9,
        )
        assert options.k == 10
        assert options.min_score == 0.7
        assert options.deduplicate is False
        assert options.deduplication_threshold == 0.9


@pytest.mark.unit
class TestFormattedContext:
    """Test FormattedContext value object."""

    def test_empty_context(self):
        """Empty context should have zero values."""
        context = FormattedContext(
            text="",
            sources=[],
            total_tokens=0,
            chunk_count=0,
        )
        assert context.text == ""
        assert context.sources == []
        assert context.total_tokens == 0
        assert context.chunk_count == 0


@pytest.mark.unit
class TestRetrievalResult:
    """Test RetrievalResult value object."""

    def test_result_creation(self):
        """Result should store retrieval data."""
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="char_alice",
                source_type=SourceType.CHARACTER,
                content="Alice is brave",
                score=0.9,
                metadata={},
            )
        ]

        result = RetrievalResult(
            chunks=chunks,
            query="brave warrior",
            total_retrieved=10,
            filtered=2,
            deduplicated=1,
        )

        assert len(result.chunks) == 1
        assert result.query == "brave warrior"
        assert result.total_retrieved == 10
        assert result.filtered == 2
        assert result.deduplicated == 1


@pytest.mark.unit
class TestRetrievalService:
    """Test RetrievalService."""

    @pytest.fixture
    def embedding_service(self):
        """Create mock embedding service."""
        service = AsyncMock(spec=IEmbeddingService)
        service.get_dimension.return_value = 1536
        return service

    @pytest.fixture
    def vector_store(self):
        """Create mock vector store."""
        store = AsyncMock(spec=IVectorStore)
        store.health_check.return_value = True
        return store

    @pytest.fixture
    def retrieval_service(self, embedding_service, vector_store):
        """Create retrieval service with mock dependencies."""
        return RetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

    @pytest.fixture
    def sample_query_results(self):
        """Create sample query results for testing."""
        return [
            QueryResult(
                id="chunk_1",
                text="Sir Aldric is a brave knight",
                score=0.95,
                metadata={
                    "source_id": "char_aldric",
                    "source_type": "CHARACTER",
                    "chunk_index": 0,
                    "total_chunks": 1,
                },
            ),
            QueryResult(
                id="chunk_2",
                text="The kingdom of Eldoria",
                score=0.85,
                metadata={
                    "source_id": "lore_eldoria",
                    "source_type": "LORE",
                    "chunk_index": 0,
                    "total_chunks": 1,
                },
            ),
            QueryResult(
                id="chunk_3",
                text="He wields a legendary sword",
                score=0.75,
                metadata={
                    "source_id": "char_aldric",
                    "source_type": "CHARACTER",
                    "chunk_index": 1,
                    "total_chunks": 2,
                },
            ),
            QueryResult(
                id="chunk_4",
                text="Unrelated content",
                score=0.3,  # Below threshold
                metadata={
                    "source_id": "lore_other",
                    "source_type": "LORE",
                    "chunk_index": 0,
                    "total_chunks": 1,
                },
            ),
        ]

    @pytest.mark.asyncio
    async def test_retrieve_relevant_basic(
        self, retrieval_service, embedding_service, vector_store, sample_query_results
    ):
        """Basic retrieval should embed query and search vector store."""
        # Setup mocks
        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.return_value = sample_query_results

        # Execute
        result = await retrieval_service.retrieve_relevant(
            query="brave knight",
            k=5,
        )

        # Verify
        assert result.query == "brave knight"
        assert embedding_service.embed.called
        assert vector_store.query.called

        # Should filter out low-score result
        assert len(result.chunks) == 3
        assert result.filtered == 1

    @pytest.mark.asyncio
    async def test_retrieve_relevant_empty_query(self, retrieval_service):
        """Empty query should raise ValueError."""
        with pytest.raises(ValueError, match="query cannot be empty"):
            await retrieval_service.retrieve_relevant(query="")

        with pytest.raises(ValueError, match="query cannot be empty"):
            await retrieval_service.retrieve_relevant(query="   ")

    @pytest.mark.asyncio
    async def test_retrieve_relevant_embedding_error(
        self, retrieval_service, embedding_service
    ):
        """Embedding error should propagate."""
        embedding_service.embed.side_effect = EmbeddingError("API error")

        with pytest.raises(EmbeddingError):
            await retrieval_service.retrieve_relevant(query="test")

    @pytest.mark.asyncio
    async def test_retrieve_relevant_vector_store_error(
        self, retrieval_service, embedding_service, vector_store
    ):
        """Vector store error should propagate."""
        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.side_effect = VectorStoreError("Connection failed")

        with pytest.raises(VectorStoreError):
            await retrieval_service.retrieve_relevant(query="test")

    @pytest.mark.asyncio
    async def test_retrieve_with_source_type_filter(
        self, retrieval_service, embedding_service, vector_store, sample_query_results
    ):
        """Should filter by source type."""
        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.return_value = sample_query_results

        filters = RetrievalFilter(source_types=[SourceType.CHARACTER])
        result = await retrieval_service.retrieve_relevant(
            query="brave knight",
            k=5,
            filters=filters,
        )

        # Verify where clause was passed
        call_args = vector_store.query.call_args
        where_clause = call_args.kwargs.get("where")
        assert where_clause is not None
        assert where_clause["source_type"]["$in"] == ["CHARACTER"]

    @pytest.mark.asyncio
    async def test_retrieve_with_tags_filter(
        self, retrieval_service, embedding_service, vector_store, sample_query_results
    ):
        """Should filter by tags."""
        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.return_value = sample_query_results

        filters = RetrievalFilter(tags=["protagonist", "knight"])
        result = await retrieval_service.retrieve_relevant(
            query="brave knight",
            k=5,
            filters=filters,
        )

        # Verify where clause was passed
        call_args = vector_store.query.call_args
        where_clause = call_args.kwargs.get("where")
        assert where_clause is not None
        assert where_clause["tags"]["$in"] == ["protagonist", "knight"]

    @pytest.mark.asyncio
    async def test_retrieve_with_custom_relevance_threshold(
        self, retrieval_service, embedding_service, vector_store, sample_query_results
    ):
        """Should filter results by custom relevance threshold."""
        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.return_value = sample_query_results

        options = RetrievalOptions(min_score=0.8)
        result = await retrieval_service.retrieve_relevant(
            query="brave knight",
            k=5,
            options=options,
        )

        # Only results with score >= 0.8 should remain
        assert len(result.chunks) == 2
        assert all(c.score >= 0.8 for c in result.chunks)
        assert result.filtered == 2

    @pytest.mark.asyncio
    async def test_retrieve_with_deduplication_disabled(
        self, retrieval_service, embedding_service, vector_store
    ):
        """Should not deduplicate when disabled."""
        # Create duplicate results
        duplicate_results = [
            QueryResult(
                id="chunk_1",
                text="Sir Aldric is a brave knight",
                score=0.95,
                metadata={"source_id": "char_aldric", "source_type": "CHARACTER"},
            ),
            QueryResult(
                id="chunk_2",
                text="Sir Aldric is a brave knight",  # Duplicate content
                score=0.90,
                metadata={"source_id": "char_aldric", "source_type": "CHARACTER"},
            ),
        ]

        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.return_value = duplicate_results

        options = RetrievalOptions(deduplicate=False)
        result = await retrieval_service.retrieve_relevant(
            query="brave knight",
            k=5,
            options=options,
        )

        # Both should be present
        assert len(result.chunks) == 2
        assert result.deduplicated == 0

    @pytest.mark.asyncio
    async def test_retrieve_with_deduplication_enabled(
        self, retrieval_service, embedding_service, vector_store
    ):
        """Should deduplicate similar chunks."""
        # Create duplicate results
        duplicate_results = [
            QueryResult(
                id="chunk_1",
                text="Sir Aldric is a brave knight",
                score=0.95,
                metadata={"source_id": "char_aldric", "source_type": "CHARACTER"},
            ),
            QueryResult(
                id="chunk_2",
                text="Sir Aldric is a brave knight",  # Exact duplicate
                score=0.90,
                metadata={"source_id": "char_aldric_2", "source_type": "CHARACTER"},
            ),
        ]

        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.return_value = duplicate_results

        options = RetrievalOptions(deduplicate=True)
        result = await retrieval_service.retrieve_relevant(
            query="brave knight",
            k=5,
            options=options,
        )

        # Only one should remain (highest score)
        assert len(result.chunks) == 1
        assert result.chunks[0].score == 0.95
        assert result.deduplicated == 1

    @pytest.mark.asyncio
    async def test_retrieve_limits_to_k_results(
        self, retrieval_service, embedding_service, vector_store
    ):
        """Should limit results to k."""
        # Create many results
        many_results = [
            QueryResult(
                id=f"chunk_{i}",
                text=f"Content {i}",
                score=0.9 - (i * 0.01),
                metadata={"source_id": f"source_{i}", "source_type": "LORE"},
            )
            for i in range(10)
        ]

        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.return_value = many_results

        result = await retrieval_service.retrieve_relevant(
            query="test",
            k=3,
        )

        # Should return at most k results
        assert len(result.chunks) <= 3

    @pytest.mark.asyncio
    async def test_retrieve_custom_collection(
        self, retrieval_service, embedding_service, vector_store
    ):
        """Should use custom collection name."""
        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.return_value = []

        await retrieval_service.retrieve_relevant(
            query="test",
            collection="custom_collection",
        )

        # Verify collection name
        call_args = vector_store.query.call_args
        assert call_args.kwargs["collection"] == "custom_collection"

    @pytest.mark.asyncio
    async def test_format_context_empty(
        self, retrieval_service
    ):
        """Empty result should produce empty context."""
        result = RetrievalResult(
            chunks=[],
            query="test",
            total_retrieved=0,
        )

        context = retrieval_service.format_context(result)

        assert context.text == ""
        assert context.sources == []
        assert context.total_tokens == 0
        assert context.chunk_count == 0

    @pytest.mark.asyncio
    async def test_format_context_basic(
        self, retrieval_service
    ):
        """Should format chunks into context string."""
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="char_alice",
                source_type=SourceType.CHARACTER,
                content="Alice is brave",
                score=0.9,
                metadata={"chunk_index": 0, "total_chunks": 1},
            ),
            RetrievedChunk(
                chunk_id="2",
                source_id="lore_kingdom",
                source_type=SourceType.LORE,
                content="The kingdom is old",
                score=0.8,
                metadata={"chunk_index": 0, "total_chunks": 1},
            ),
        ]

        result = RetrievalResult(
            chunks=chunks,
            query="test",
            total_retrieved=2,
        )

        context = retrieval_service.format_context(result)

        assert "CHARACTER:char_alice" in context.text
        assert "Alice is brave" in context.text
        assert "LORE:lore_kingdom" in context.text
        assert "The kingdom is old" in context.text
        assert context.chunk_count == 2
        assert len(context.sources) == 2

    @pytest.mark.asyncio
    async def test_format_context_with_token_limit(
        self, retrieval_service
    ):
        """Should respect token limit."""
        # Create chunks that would exceed token limit
        large_chunks = [
            RetrievedChunk(
                chunk_id=str(i),
                source_id=f"source_{i}",
                source_type=SourceType.LORE,
                content="x" * 1000,  # Large content
                score=0.9,
                metadata={"chunk_index": i, "total_chunks": 5},
            )
            for i in range(5)
        ]

        result = RetrievalResult(
            chunks=large_chunks,
            query="test",
            total_retrieved=5,
        )

        # Limit to ~500 tokens (2000 chars)
        context = retrieval_service.format_context(result, max_tokens=500)

        # Should include fewer chunks due to token limit
        assert context.chunk_count < 5
        assert context.total_tokens <= 500

    @pytest.mark.asyncio
    async def test_format_context_without_sources(
        self, retrieval_service
    ):
        """Should not include sources when disabled."""
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="char_alice",
                source_type=SourceType.CHARACTER,
                content="Alice is brave",
                score=0.9,
                metadata={},
            ),
        ]

        result = RetrievalResult(
            chunks=chunks,
            query="test",
            total_retrieved=1,
        )

        context = retrieval_service.format_context(result, include_sources=False)

        assert context.sources == []
        assert context.text != ""

    @pytest.mark.asyncio
    async def test_format_context_simple(
        self, retrieval_service
    ):
        """Simple format should return just text."""
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="char_alice",
                source_type=SourceType.CHARACTER,
                content="Alice is brave",
                score=0.9,
                metadata={"chunk_index": 0, "total_chunks": 1},
            ),
        ]

        text = retrieval_service.format_context_simple(chunks)

        assert "Alice is brave" in text
        assert isinstance(text, str)

    def test_content_similarity(self, retrieval_service):
        """Should calculate content similarity."""
        # Identical content
        sim1 = retrieval_service._content_similarity("test content", "test content")
        assert sim1 == 1.0

        # Similar content
        sim2 = retrieval_service._content_similarity(
            "Sir Aldric is a brave knight",
            "Sir Aldric is a brave warrior"
        )
        assert sim2 > 0.8  # High similarity

        # Different content
        sim3 = retrieval_service._content_similarity(
            "The quick brown fox",
            "Lorem ipsum dolor sit amet"
        )
        assert sim3 < 0.3  # Low similarity

        # Case insensitive
        sim4 = retrieval_service._content_similarity("Test Content", "test content")
        assert sim4 == 1.0

        # Normalizes whitespace
        sim5 = retrieval_service._content_similarity(
            "test   content   here",
            "test content here"
        )
        assert sim5 == 1.0

    def test_deduplicate_chunks_keeps_highest_score(self, retrieval_service):
        """Deduplication should keep highest-scoring chunk."""
        chunks = [
            RetrievedChunk(
                chunk_id="2",
                source_id="source_2",
                source_type=SourceType.LORE,
                content="duplicate content",
                score=0.7,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="1",
                source_id="source_1",
                source_type=SourceType.LORE,
                content="duplicate content",
                score=0.9,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="3",
                source_id="source_3",
                source_type=SourceType.LORE,
                content="unique content",
                score=0.5,
                metadata={},
            ),
        ]

        deduplicated = retrieval_service._deduplicate_chunks(chunks)

        # Should keep the highest-scoring duplicate and the unique one
        assert len(deduplicated) == 2
        assert deduplicated[0].score == 0.9  # Highest score first
        assert any(c.content == "unique content" for c in deduplicated)

    def test_deduplicate_chunks_empty(self, retrieval_service):
        """Empty list should return empty."""
        assert retrieval_service._deduplicate_chunks([]) == []

    def test_deduplicate_chunks_single(self, retrieval_service):
        """Single chunk should return as-is."""
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="source_1",
                source_type=SourceType.LORE,
                content="content",
                score=0.9,
                metadata={},
            ),
        ]

        deduplicated = retrieval_service._deduplicate_chunks(chunks)

        assert len(deduplicated) == 1
        assert deduplicated[0] == chunks[0]

    def test_format_chunk(self, retrieval_service):
        """Should format chunk with metadata."""
        chunk = RetrievedChunk(
            chunk_id="1",
            source_id="char_alice",
            source_type=SourceType.CHARACTER,
            content="Alice is brave",
            score=0.9,
            metadata={"chunk_index": 2, "total_chunks": 5},
        )

        formatted = retrieval_service._format_chunk(chunk, 1)

        assert "[1]" in formatted
        assert "CHARACTER:char_alice" in formatted
        assert "(part 2/5)" in formatted
        assert "Alice is brave" in formatted

    def test_format_source(self, retrieval_service):
        """Should format source reference."""
        chunk = RetrievedChunk(
            chunk_id="1",
            source_id="char_alice",
            source_type=SourceType.CHARACTER,
            content="Alice is brave",
            score=0.9,
            metadata={},
        )

        source = retrieval_service._format_source(chunk)

        assert source == "CHARACTER:char_alice"
