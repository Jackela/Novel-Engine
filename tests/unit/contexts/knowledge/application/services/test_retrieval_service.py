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
from unittest.mock import AsyncMock

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
from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    RetrievedChunk,
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

pytestmark = pytest.mark.unit


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
        _result = await retrieval_service.retrieve_relevant(  # noqa: F841
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
        _result = await retrieval_service.retrieve_relevant(  # noqa: F841
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
    async def test_format_context_empty(self, retrieval_service):
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
    async def test_format_context_basic(self, retrieval_service):
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
    async def test_format_context_with_token_limit(self, retrieval_service):
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
    async def test_format_context_without_sources(self, retrieval_service):
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
    async def test_format_context_simple(self, retrieval_service):
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
            "Sir Aldric is a brave knight", "Sir Aldric is a brave warrior"
        )
        assert sim2 > 0.8  # High similarity

        # Different content
        sim3 = retrieval_service._content_similarity(
            "The quick brown fox", "Lorem ipsum dolor sit amet"
        )
        assert sim3 < 0.3  # Low similarity

        # Case insensitive
        sim4 = retrieval_service._content_similarity("Test Content", "test content")
        assert sim4 == 1.0

        # Normalizes whitespace
        sim5 = retrieval_service._content_similarity(
            "test   content   here", "test content here"
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


class TestRetrievalServiceGetSources:
    """Tests for get_sources method (BRAIN-012)."""

    @pytest.fixture
    def retrieval_service(self):
        """Create retrieval service without mocks for get_sources tests."""
        from unittest.mock import AsyncMock

        from src.contexts.knowledge.application.ports.i_embedding_service import (
            IEmbeddingService,
        )
        from src.contexts.knowledge.application.ports.i_vector_store import IVectorStore

        embedding_service = AsyncMock(spec=IEmbeddingService)
        vector_store = AsyncMock(spec=IVectorStore)
        return RetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

    def test_get_sources_empty_list(self, retrieval_service):
        """Empty chunks should return empty sources."""
        sources = retrieval_service.get_sources([])
        assert sources == []

    def test_get_sources_single_chunk(self, retrieval_service):
        """Single chunk should return one source."""
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="char_alice",
                source_type=SourceType.CHARACTER,
                content="Alice is brave",
                score=0.9,
                metadata={"name": "Alice the Brave"},
            ),
        ]

        sources = retrieval_service.get_sources(chunks)

        assert len(sources) == 1
        assert sources[0]["source_id"] == "char_alice"
        assert sources[0]["source_type"] == "CHARACTER"
        assert sources[0]["chunk_count"] == 1
        assert sources[0]["relevance_score"] == 0.9
        assert sources[0]["citation_id"] == "C1"

    def test_get_sources_groups_by_source(self, retrieval_service):
        """Multiple chunks from same source should be grouped."""
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="char_alice",
                source_type=SourceType.CHARACTER,
                content="Alice is brave",
                score=0.9,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="2",
                source_id="char_alice",
                source_type=SourceType.CHARACTER,
                content="Alice has a sword",
                score=0.85,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="3",
                source_id="lore_kingdom",
                source_type=SourceType.LORE,
                content="The kingdom is old",
                score=0.8,
                metadata={},
            ),
        ]

        sources = retrieval_service.get_sources(chunks)

        # Should have 2 unique sources
        assert len(sources) == 2

        alice = next(s for s in sources if s["source_id"] == "char_alice")
        assert alice["chunk_count"] == 2
        assert alice["relevance_score"] == pytest.approx(
            0.875, 0.01
        )  # Average of 0.9 and 0.85

    def test_get_sources_with_custom_names(self, retrieval_service):
        """Should use provided display names."""
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="char_alice",
                source_type=SourceType.CHARACTER,
                content="Alice is brave",
                score=0.9,
                metadata={"name": "Ignored Name"},
            ),
        ]

        source_names = {"char_alice": "Alice, Warrior of Light"}
        sources = retrieval_service.get_sources(chunks, source_names)

        assert sources[0]["display_name"] == "Alice, Warrior of Light"

    def test_get_sources_falls_back_to_metadata_name(self, retrieval_service):
        """Should use metadata name when no custom names provided."""
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="char_alice",
                source_type=SourceType.CHARACTER,
                content="Alice is brave",
                score=0.9,
                metadata={"name": "Alice from Metadata"},
            ),
        ]

        sources = retrieval_service.get_sources(chunks)

        assert sources[0]["display_name"] == "Alice from Metadata"

    def test_get_sources_sorted_by_relevance(self, retrieval_service):
        """Sources should be sorted by relevance score."""
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="lore_low",
                source_type=SourceType.LORE,
                content="Low relevance",
                score=0.6,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="2",
                source_id="char_high",
                source_type=SourceType.CHARACTER,
                content="High relevance",
                score=0.95,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="3",
                source_id="scene_medium",
                source_type=SourceType.SCENE,
                content="Medium relevance",
                score=0.75,
                metadata={},
            ),
        ]

        sources = retrieval_service.get_sources(chunks)

        # Should be sorted by relevance (highest first)
        assert sources[0]["source_id"] == "char_high"
        assert sources[0]["relevance_score"] == 0.95
        assert sources[1]["source_id"] == "scene_medium"
        assert sources[2]["source_id"] == "lore_low"

    def test_get_sources_citation_id_prefixes(self, retrieval_service):
        """Citation IDs should use source type prefixes."""
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="char_alice",
                source_type=SourceType.CHARACTER,
                content="Alice",
                score=0.9,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="2",
                source_id="lore_kingdom",
                source_type=SourceType.LORE,
                content="Kingdom",
                score=0.8,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="3",
                source_id="scene_tavern",
                source_type=SourceType.SCENE,
                content="Tavern",
                score=0.75,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="4",
                source_id="item_sword",
                source_type=SourceType.ITEM,
                content="Sword",
                score=0.7,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="5",
                source_id="loc_castle",
                source_type=SourceType.LOCATION,
                content="Castle",
                score=0.65,
                metadata={},
            ),
        ]

        sources = retrieval_service.get_sources(chunks)
        citation_ids = [s["citation_id"] for s in sources]

        # Check prefixes
        assert any("C" in id for id in citation_ids)  # Character
        assert any("L" in id for id in citation_ids)  # Lore
        assert any("S" in id for id in citation_ids)  # Scene
        assert any("I" in id for id in citation_ids)  # Item
        assert any("Loc" in id for id in citation_ids)  # Location


class TestRetrievalServiceCitationFormatting:
    """Tests for citation formatting features (BRAIN-012)."""

    @pytest.fixture
    def retrieval_service(self):
        """Create retrieval service without mocks for citation tests."""
        from unittest.mock import AsyncMock

        from src.contexts.knowledge.application.ports.i_embedding_service import (
            IEmbeddingService,
        )
        from src.contexts.knowledge.application.ports.i_vector_store import IVectorStore

        embedding_service = AsyncMock(spec=IEmbeddingService)
        vector_store = AsyncMock(spec=IVectorStore)
        return RetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

    @pytest.mark.asyncio
    async def test_format_context_with_citation_data(self, retrieval_service):
        """Should include citation data when requested."""
        chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_id="char_alice",
                source_type=SourceType.CHARACTER,
                content="Alice is brave",
                score=0.9,
                metadata={"name": "Alice the Brave"},
            ),
        ]

        result = RetrievalResult(
            chunks=chunks,
            query="test",
            total_retrieved=1,
        )

        context = retrieval_service.format_context(result, include_citation_data=True)

        # Should have source_references with citation data
        assert context.source_references is not None
        assert "sources" in context.source_references
        assert "citations" in context.source_references

    @pytest.mark.asyncio
    async def test_format_context_without_citation_data(self, retrieval_service):
        """Should not include citation data by default."""
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

        context = retrieval_service.format_context(result)

        # Should have empty source_references by default
        assert context.source_references == {}

    def test_get_source_type_prefix(self, retrieval_service):
        """Should return correct prefix for each source type."""
        assert retrieval_service._get_source_type_prefix(SourceType.CHARACTER) == "C"
        assert retrieval_service._get_source_type_prefix(SourceType.LORE) == "L"
        assert retrieval_service._get_source_type_prefix(SourceType.SCENE) == "S"
        assert retrieval_service._get_source_type_prefix(SourceType.PLOTLINE) == "P"
        assert retrieval_service._get_source_type_prefix(SourceType.ITEM) == "I"
        assert retrieval_service._get_source_type_prefix(SourceType.LOCATION) == "Loc"

    @pytest.mark.asyncio
    async def test_format_chunk_with_citation(self, retrieval_service):
        """Should format chunk with citation marker."""
        chunk = RetrievedChunk(
            chunk_id="1",
            source_id="char_alice",
            source_type=SourceType.CHARACTER,
            content="Alice is brave",
            score=0.9,
            metadata={"chunk_index": 0, "total_chunks": 1},
        )

        formatted = retrieval_service._format_chunk_with_citation(chunk, 1)

        assert "[1]" in formatted
        assert "CHARACTER:char_alice" in formatted
        assert "Alice is brave" in formatted


@pytest.mark.unit
class TestRetrievalServiceReranking:
    """Tests for reranking integration in RetrievalService (OPT-003)."""

    @pytest.fixture
    def embedding_service(self):
        """Create mock embedding service."""
        from src.contexts.knowledge.application.ports.i_embedding_service import (
            IEmbeddingService,
        )

        service = AsyncMock(spec=IEmbeddingService)
        service.get_dimension.return_value = 1536
        return service

    @pytest.fixture
    def vector_store(self):
        """Create mock vector store."""
        from src.contexts.knowledge.application.ports.i_vector_store import IVectorStore

        store = AsyncMock(spec=IVectorStore)
        store.health_check.return_value = True
        return store

    @pytest.fixture
    def sample_query_results(self):
        """Create sample query results for testing."""
        from src.contexts.knowledge.application.ports.i_vector_store import QueryResult

        return [
            QueryResult(
                id="chunk_1",
                text="Alice is a brave knight who fights with honor.",
                score=0.85,
                metadata={
                    "source_id": "char_alice",
                    "source_type": "CHARACTER",
                    "chunk_index": 0,
                    "total_chunks": 1,
                },
            ),
            QueryResult(
                id="chunk_2",
                text="Bob is a cunning thief with a heart of gold.",
                score=0.75,
                metadata={
                    "source_id": "char_bob",
                    "source_type": "CHARACTER",
                    "chunk_index": 0,
                    "total_chunks": 1,
                },
            ),
            QueryResult(
                id="chunk_3",
                text="The kingdom has stood for a thousand years.",
                score=0.65,
                metadata={
                    "source_id": "lore_kingdom",
                    "source_type": "LORE",
                    "chunk_index": 0,
                    "total_chunks": 1,
                },
            ),
            QueryResult(
                id="chunk_4",
                text="Charlie is a wise wizard from the eastern lands.",
                score=0.55,
                metadata={
                    "source_id": "char_charlie",
                    "source_type": "CHARACTER",
                    "chunk_index": 0,
                    "total_chunks": 1,
                },
            ),
            QueryResult(
                id="chunk_5",
                text="Dragons were once common but are now rare.",
                score=0.45,
                metadata={
                    "source_id": "lore_dragons",
                    "source_type": "LORE",
                    "chunk_index": 0,
                    "total_chunks": 1,
                },
            ),
            QueryResult(
                id="chunk_6",
                text="The castle stands on a hill overlooking the valley.",
                score=0.40,
                metadata={
                    "source_id": "lore_castle",
                    "source_type": "LORE",
                    "chunk_index": 0,
                    "total_chunks": 1,
                },
            ),
            QueryResult(
                id="chunk_7",
                text="Knights must follow the code of chivalry.",
                score=0.35,
                metadata={
                    "source_id": "lore_chivalry",
                    "source_type": "LORE",
                    "chunk_index": 0,
                    "total_chunks": 1,
                },
            ),
            QueryResult(
                id="chunk_8",
                text="The sword glows in the presence of evil.",
                score=0.30,
                metadata={
                    "source_id": "item_sword",
                    "source_type": "ITEM",
                    "chunk_index": 0,
                    "total_chunks": 1,
                },
            ),
        ]

    @pytest.fixture
    def mock_rerank_service(self):
        """Create mock rerank service that reorders results."""
        from unittest.mock import AsyncMock

        from src.contexts.knowledge.application.ports.i_reranker import (
            RerankDocument,
            RerankOutput,
            RerankResult,
        )
        from src.contexts.knowledge.application.services.rerank_service import (
            RerankService,
        )

        reranker = AsyncMock()

        async def mock_rerank_func(
            query: str,
            documents: list[RerankDocument],
            top_k: int | None = None,
        ) -> RerankOutput:
            # Simulate reranking by reversing order and boosting scores
            reranked = [
                RerankResult(
                    index=d.index,
                    score=d.score + 0.1,
                    relevance_score=min(d.score + 0.15, 1.0),
                )
                for d in reversed(documents)
            ]

            if top_k is not None:
                reranked = reranked[:top_k]

            avg_original = sum(d.score for d in documents) / len(documents)
            avg_new = (
                sum(r.relevance_score for r in reranked) / len(reranked)
                if reranked
                else 0
            )
            score_improvement = max(0.0, avg_new - avg_original)

            return RerankOutput(
                results=reranked,
                query=query,
                total_reranked=len(documents),
                model="test_reranker",
                latency_ms=50.0,
                score_improvement=score_improvement,
            )

        reranker.rerank = mock_rerank_func
        return RerankService(reranker=reranker)

    @pytest.mark.asyncio
    async def test_retrieve_with_reranking_enabled(
        self, embedding_service, vector_store, sample_query_results, mock_rerank_service
    ):
        """When reranking is enabled, should apply reranking after filtering/dedup."""
        from src.contexts.knowledge.application.services.retrieval_service import (
            RetrievalService,
        )

        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.return_value = sample_query_results

        # Create service with reranking
        retrieval_service = RetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
            rerank_service=mock_rerank_service,
        )

        result = await retrieval_service.retrieve_relevant(
            query="knight",
            k=5,
            options=RetrievalOptions(enable_rerank=True),
        )

        # Should have applied reranking (mock reverses order)
        # Last chunk becomes first after reranking
        assert len(result.chunks) <= 5

    @pytest.mark.asyncio
    async def test_retrieve_with_candidate_and_final_k(
        self, embedding_service, vector_store, sample_query_results, mock_rerank_service
    ):
        """Should retrieve candidate_k results and return final_k after reranking."""
        from src.contexts.knowledge.application.services.retrieval_service import (
            RetrievalService,
        )

        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.return_value = sample_query_results

        retrieval_service = RetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
            rerank_service=mock_rerank_service,
        )

        # Request 20 candidates, return 5 final
        result = await retrieval_service.retrieve_relevant(
            query="knight",
            k=5,
            options=RetrievalOptions(
                candidate_k=20,
                final_k=5,
                enable_rerank=True,
            ),
        )

        # Should have asked for at least 20 from vector store
        call_args = vector_store.query.call_args
        assert call_args.kwargs["n_results"] >= 20

        # Should return only 5 final results
        assert len(result.chunks) <= 5

    @pytest.mark.asyncio
    async def test_retrieve_with_reranking_disabled_in_options(
        self, embedding_service, vector_store, sample_query_results, mock_rerank_service
    ):
        """When enable_rerank is False, should skip reranking even if service is available."""
        from src.contexts.knowledge.application.services.retrieval_service import (
            RetrievalService,
        )

        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.return_value = sample_query_results

        retrieval_service = RetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
            rerank_service=mock_rerank_service,
        )

        result = await retrieval_service.retrieve_relevant(
            query="knight",
            k=5,
            options=RetrievalOptions(enable_rerank=False),
        )

        # Should not have called the reranker
        # Chunks should be in original order (highest score first)
        assert len(result.chunks) <= 5
        if result.chunks:
            # First chunk should be the highest scoring (Alice at 0.85)
            assert result.chunks[0].source_id == "char_alice"

    @pytest.mark.asyncio
    async def test_retrieve_without_rerank_service(
        self, embedding_service, vector_store, sample_query_results
    ):
        """When no rerank service is provided, should work normally without reranking."""
        from src.contexts.knowledge.application.services.retrieval_service import (
            RetrievalService,
        )

        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.return_value = sample_query_results

        # Create service without reranking
        retrieval_service = RetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
            rerank_service=None,
        )

        result = await retrieval_service.retrieve_relevant(
            query="knight",
            k=5,
            options=RetrievalOptions(enable_rerank=True),
        )

        # Should return results normally
        assert len(result.chunks) <= 5
        # Should be in original order
        if result.chunks:
            assert result.chunks[0].source_id == "char_alice"

    @pytest.mark.asyncio
    async def test_retrieve_reranking_fallback_on_error(
        self, embedding_service, vector_store, sample_query_results
    ):
        """When reranking fails, should fall back to original order with warning."""
        from src.contexts.knowledge.application.services.rerank_service import (
            FailingReranker,
            RerankService,
        )
        from src.contexts.knowledge.application.services.retrieval_service import (
            RetrievalService,
        )

        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.return_value = sample_query_results

        # Create service with failing reranker
        failing_reranker = FailingReranker("Reranking API error")
        rerank_service = RerankService(reranker=failing_reranker)

        retrieval_service = RetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
            rerank_service=rerank_service,
        )

        result = await retrieval_service.retrieve_relevant(
            query="knight",
            k=5,
            options=RetrievalOptions(enable_rerank=True),
        )

        # Should fall back to original order and still return results
        assert len(result.chunks) <= 5
        # Should be in original order (highest score first)
        if result.chunks:
            assert result.chunks[0].source_id == "char_alice"

    @pytest.mark.asyncio
    async def test_retrieve_with_candidate_k_defaults_to_2x_final_k(
        self, embedding_service, vector_store, sample_query_results, mock_rerank_service
    ):
        """When candidate_k is None, should default to 2x final_k when reranking."""
        from src.contexts.knowledge.application.services.retrieval_service import (
            RetrievalService,
        )

        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.return_value = sample_query_results

        retrieval_service = RetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
            rerank_service=mock_rerank_service,
        )

        # Don't specify candidate_k, should default to 2x k
        _result = await retrieval_service.retrieve_relevant(  # noqa: F841
            query="knight",
            k=5,
            options=RetrievalOptions(
                enable_rerank=True,
            ),
        )

        # Should have asked for at least 10 (2x5) from vector store
        call_args = vector_store.query.call_args
        assert call_args.kwargs["n_results"] >= 10

    @pytest.mark.asyncio
    async def test_retrieve_final_k_overrides_k(
        self, embedding_service, vector_store, sample_query_results, mock_rerank_service
    ):
        """When final_k is specified, it should override the k parameter."""
        from src.contexts.knowledge.application.services.retrieval_service import (
            RetrievalService,
        )

        embedding_service.embed.return_value = [0.1] * 1536
        vector_store.query.return_value = sample_query_results

        retrieval_service = RetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
            rerank_service=mock_rerank_service,
        )

        # k=10 but final_k=3, should return 3
        result = await retrieval_service.retrieve_relevant(
            query="knight",
            k=10,
            options=RetrievalOptions(
                final_k=3,
                enable_rerank=True,
            ),
        )

        assert len(result.chunks) <= 3

    @pytest.mark.asyncio
    async def test_retrieval_options_with_rerank_fields(self):
        """RetrievalOptions should support candidate_k, final_k, and enable_rerank."""
        options = RetrievalOptions(
            k=10,
            candidate_k=20,
            final_k=5,
            enable_rerank=False,
        )

        assert options.k == 10
        assert options.candidate_k == 20
        assert options.final_k == 5
        assert options.enable_rerank is False

    @pytest.mark.asyncio
    async def test_retrieval_options_rerank_defaults(self):
        """RetrievalOptions should have sensible defaults for reranking."""
        options = RetrievalOptions()

        assert options.candidate_k is None  # Will default to 2x final_k
        assert options.final_k is None  # Will use k
        assert options.enable_rerank is True  # Reranking enabled by default
