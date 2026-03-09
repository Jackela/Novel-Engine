"""
Extended test suite for Retrieval Service module.

Additional tests to achieve comprehensive coverage.
Tests query processing, relevance scoring, context assembly, and edge cases.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from src.contexts.knowledge.application.ports.i_embedding_service import EmbeddingError
from src.contexts.knowledge.application.ports.i_vector_store import (
    QueryResult as QueryResult,
)
from src.contexts.knowledge.application.ports.i_vector_store import VectorStoreError
from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    RetrievedChunk,
)
from src.contexts.knowledge.application.services.retrieval_service import (
    FormattedContext,
    RetrievalFilter,
    RetrievalOptions,
    RetrievalResult,
    RetrievalService,
)
from src.contexts.knowledge.domain.models.source_type import SourceType

pytestmark = pytest.mark.unit


class TestRetrievalFilterExtended:
    """Extended tests for RetrievalFilter dataclass."""

    def test_filter_with_date_range(self):
        """Test filter with date range constraints."""
        date_from = datetime(2024, 1, 1)
        date_to = datetime(2024, 12, 31)
        filter_obj = RetrievalFilter(
            source_types=[SourceType.CHARACTER],
            date_from=date_from,
            date_to=date_to,
        )

        assert filter_obj.date_from == date_from
        assert filter_obj.date_to == date_to

    def test_to_where_clause_with_multiple_source_types(self):
        """Test where clause with multiple source types."""
        filter_obj = RetrievalFilter(
            source_types=[SourceType.CHARACTER, SourceType.LORE, SourceType.SCENE],
        )
        clause = filter_obj.to_where_clause()

        assert "source_type" in clause
        assert "$in" in clause["source_type"]
        # Source types are uppercase (CHARACTER, LORE, SCENE)
        assert "CHARACTER" in clause["source_type"]["$in"]
        assert "LORE" in clause["source_type"]["$in"]
        assert "SCENE" in clause["source_type"]["$in"]

    def test_to_where_clause_with_tags(self):
        """Test where clause with tags filter."""
        filter_obj = RetrievalFilter(tags=["important", "hero", "magic"])
        clause = filter_obj.to_where_clause()

        assert "tags" in clause
        assert "$in" in clause["tags"]

    def test_to_where_clause_with_custom_metadata(self):
        """Test where clause with custom metadata."""
        filter_obj = RetrievalFilter(
            custom_metadata={"author": "test_author", "version": 1}
        )
        clause = filter_obj.to_where_clause()

        assert clause["author"] == "test_author"
        assert clause["version"] == 1

    def test_matches_with_none_metadata(self):
        """Test matching with None metadata returns False."""
        filter_obj = RetrievalFilter()
        assert filter_obj.matches(None) is False

    def test_matches_with_date_from_valid(self):
        """Test matching with valid date_from."""
        filter_obj = RetrievalFilter(date_from=datetime(2024, 1, 1))
        metadata = {"created_at": datetime(2024, 6, 15)}

        assert filter_obj.matches(metadata) is True

    def test_matches_with_date_from_invalid(self):
        """Test matching with invalid date_from (too early)."""
        filter_obj = RetrievalFilter(date_from=datetime(2024, 6, 1))
        metadata = {"created_at": datetime(2024, 1, 15)}

        assert filter_obj.matches(metadata) is False

    def test_matches_with_date_to_valid(self):
        """Test matching with valid date_to."""
        filter_obj = RetrievalFilter(date_to=datetime(2024, 12, 31))
        metadata = {"created_at": datetime(2024, 6, 15)}

        assert filter_obj.matches(metadata) is True

    def test_matches_with_date_to_invalid(self):
        """Test matching with invalid date_to (too late)."""
        filter_obj = RetrievalFilter(date_to=datetime(2024, 6, 1))
        metadata = {"created_at": datetime(2024, 12, 15)}

        assert filter_obj.matches(metadata) is False

    def test_matches_with_date_string_parsing(self):
        """Test matching with date as ISO string."""
        filter_obj = RetrievalFilter(date_from=datetime(2024, 1, 1))
        metadata = {"created_at": "2024-06-15T10:00:00"}

        assert filter_obj.matches(metadata) is True

    def test_matches_with_invalid_date_string(self):
        """Test matching with invalid date string."""
        filter_obj = RetrievalFilter(date_from=datetime(2024, 1, 1))
        metadata = {"created_at": "invalid-date"}

        assert filter_obj.matches(metadata) is False

    def test_matches_with_no_date_constraints(self):
        """Test matching with no date constraints."""
        filter_obj = RetrievalFilter()
        metadata = {"source_id": "test_001"}

        assert filter_obj.matches(metadata) is True


class TestRetrievalOptionsExtended:
    """Extended tests for RetrievalOptions dataclass."""

    def test_options_with_candidate_k(self):
        """Test options with candidate_k specified."""
        options = RetrievalOptions(k=5, candidate_k=20, final_k=10)

        assert options.candidate_k == 20
        assert options.final_k == 10

    def test_options_with_rerank_disabled(self):
        """Test options with reranking disabled."""
        options = RetrievalOptions(enable_rerank=False)

        assert options.enable_rerank is False

    def test_options_with_custom_deduplication_threshold(self):
        """Test options with custom deduplication threshold."""
        options = RetrievalOptions(deduplication_threshold=0.95)

        assert options.deduplication_threshold == 0.95


class TestFormattedContextExtended:
    """Extended tests for FormattedContext dataclass."""

    def test_context_with_source_references(self):
        """Test context with detailed source references."""
        context = FormattedContext(
            text="Context text here",
            sources=["char1", "loc1"],
            total_tokens=100,
            chunk_count=2,
            source_references={
                "sources": [{"id": "char1", "name": "Character 1"}],
                "citations": [{"chunk_id": "c1", "index": 1}],
            },
        )

        assert "sources" in context.source_references
        assert "citations" in context.source_references

    def test_context_empty(self):
        """Test empty context creation."""
        context = FormattedContext(
            text="",
            sources=[],
            total_tokens=0,
            chunk_count=0,
        )

        assert context.text == ""
        assert context.chunk_count == 0


@pytest.mark.asyncio
class TestRetrievalServiceExtended:
    """Extended tests for RetrievalService class."""

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
    async def retrieval_service(self, mock_embedding_service, mock_vector_store):
        """Create retrieval service with mocks."""
        return RetrievalService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            default_collection="test_collection",
        )

    async def test_retrieve_relevant_empty_query(self, retrieval_service):
        """Test retrieve with empty query returns error."""
        result = await retrieval_service.retrieve_relevant(query="")

        assert result.is_error
        assert "cannot be empty" in result.error.lower()

    async def test_retrieve_relevant_whitespace_query(self, retrieval_service):
        """Test retrieve with whitespace-only query returns error."""
        result = await retrieval_service.retrieve_relevant(query="   ")

        assert result.is_error
        assert "cannot be empty" in result.error.lower()

    async def test_retrieve_relevant_embedding_error(
        self, retrieval_service, mock_embedding_service
    ):
        """Test retrieve with embedding error."""
        mock_embedding_service.embed = AsyncMock(
            side_effect=EmbeddingError("Embedding failed")
        )

        result = await retrieval_service.retrieve_relevant(query="test query")

        assert result.is_error
        assert "embedding" in result.error.lower()

    async def test_retrieve_relevant_vector_store_error(
        self, retrieval_service, mock_vector_store
    ):
        """Test retrieve with vector store error."""
        mock_vector_store.query = AsyncMock(
            side_effect=VectorStoreError("Query failed", "query")
        )

        result = await retrieval_service.retrieve_relevant(query="test query")

        assert result.is_error
        assert "vector store" in result.error.lower()

    async def test_retrieve_relevant_with_results(
        self, retrieval_service, mock_vector_store
    ):
        """Test retrieve with successful results."""
        mock_results = [
            QueryResult(
                id="chunk_1",
                text="Test content 1 - unique first chunk",
                score=0.9,
                metadata={
                    "source_id": "source_1",
                    "source_type": "CHARACTER",
                    "chunk_index": 1,
                    "total_chunks": 2,
                },
            ),
            QueryResult(
                id="chunk_2",
                text="Test content 2 - completely different second chunk with unique information",
                score=0.8,
                metadata={
                    "source_id": "source_1",
                    "source_type": "CHARACTER",
                    "chunk_index": 2,
                    "total_chunks": 2,
                },
            ),
        ]
        mock_vector_store.query = AsyncMock(return_value=mock_results)

        result = await retrieval_service.retrieve_relevant(query="test query", k=2)

        assert result.is_ok
        # Chunks have unique content so both should be returned (no deduplication)
        assert len(result.value.chunks) == 2
        assert result.value.total_retrieved == 2

    async def test_retrieve_relevant_with_filters(
        self, retrieval_service, mock_vector_store
    ):
        """Test retrieve with filters applied."""
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

        assert result.is_ok
        # Verify filter was passed to vector store
        call_args = mock_vector_store.query.call_args
        assert "where" in call_args.kwargs

    async def test_retrieve_relevant_score_filtering(
        self, retrieval_service, mock_vector_store
    ):
        """Test that low-scoring results are filtered out."""
        mock_results = [
            QueryResult(
                id="chunk_1",
                text="High score content",
                score=0.9,
                metadata={"source_id": "source_1", "source_type": "CHARACTER"},
            ),
            QueryResult(
                id="chunk_2",
                text="Low score content",
                score=0.1,
                metadata={"source_id": "source_2", "source_type": "CHARACTER"},
            ),
        ]
        mock_vector_store.query = AsyncMock(return_value=mock_results)

        result = await retrieval_service.retrieve_relevant(
            query="test query",
            options=RetrievalOptions(min_score=0.5),
        )

        assert result.is_ok
        assert len(result.value.chunks) == 1
        assert result.value.filtered == 1

    async def test_retrieve_relevant_with_reranking(
        self, retrieval_service, mock_vector_store
    ):
        """Test retrieve with reranking enabled."""
        mock_rerank_service = AsyncMock()
        mock_rerank_service.rerank = AsyncMock(
            return_value=Mock(
                reranked=True,
                chunks=[
                    RetrievedChunk(
                        chunk_id="chunk_1",
                        source_id="source_1",
                        source_type=SourceType.CHARACTER,
                        content="Test content",
                        score=0.95,
                        metadata={},
                    ),
                ],
                model="test_model",
                latency_ms=100.0,
                score_improvement=0.05,
            )
        )

        retrieval_service._rerank_service = mock_rerank_service

        mock_results = [
            QueryResult(
                id="chunk_1",
                text="Test content",
                score=0.9,
                metadata={"source_id": "source_1", "source_type": "CHARACTER"},
            ),
        ]
        mock_vector_store.query = AsyncMock(return_value=mock_results)

        result = await retrieval_service.retrieve_relevant(
            query="test query",
            options=RetrievalOptions(enable_rerank=True),
        )

        assert result.is_ok
        mock_rerank_service.rerank.assert_called_once()

    def test_format_context_with_chunks(self, retrieval_service):
        """Test formatting context with chunks."""
        chunks = [
            RetrievedChunk(
                chunk_id="chunk_1",
                source_id="char_1",
                source_type=SourceType.CHARACTER,
                content="Character description here",
                score=0.9,
                metadata={"chunk_index": 1, "total_chunks": 1},
            ),
        ]
        result = RetrievalResult(
            chunks=chunks,
            query="test query",
            total_retrieved=1,
        )

        context = retrieval_service.format_context(result)

        assert context.text != ""
        assert context.chunk_count == 1
        assert len(context.sources) == 1
        assert context.total_tokens > 0

    def test_format_context_empty(self, retrieval_service):
        """Test formatting empty context."""
        result = RetrievalResult(
            chunks=[],
            query="test query",
            total_retrieved=0,
        )

        context = retrieval_service.format_context(result)

        assert context.text == ""
        assert context.chunk_count == 0
        assert context.total_tokens == 0

    def test_format_context_with_max_tokens(self, retrieval_service):
        """Test formatting context with token limit."""
        chunks = [
            RetrievedChunk(
                chunk_id=f"chunk_{i}",
                source_id=f"source_{i}",
                source_type=SourceType.LORE,
                content="This is a test content that is reasonably long for testing purposes. "
                * 10,
                score=0.9,
                metadata={"chunk_index": i, "total_chunks": 10},
            )
            for i in range(10)
        ]
        result = RetrievalResult(
            chunks=chunks,
            query="test query",
            total_retrieved=10,
        )

        context = retrieval_service.format_context(result, max_tokens=100)

        # Should limit chunks based on token budget
        assert context.chunk_count < 10

    def test_format_context_simple(self, retrieval_service):
        """Test simple context formatting."""
        chunks = [
            RetrievedChunk(
                chunk_id="chunk_1",
                source_id="char_1",
                source_type=SourceType.CHARACTER,
                content="Character description",
                score=0.9,
                metadata={},
            ),
        ]

        text = retrieval_service.format_context_simple(chunks)

        assert text != ""
        assert "Character description" in text

    def test_get_sources_grouping(self, retrieval_service):
        """Test getting sources with grouping."""
        chunks = [
            RetrievedChunk(
                chunk_id="chunk_1",
                source_id="char_1",
                source_type=SourceType.CHARACTER,
                content="Content 1",
                score=0.9,
                metadata={"name": "Character One"},
            ),
            RetrievedChunk(
                chunk_id="chunk_2",
                source_id="char_1",
                source_type=SourceType.CHARACTER,
                content="Content 2",
                score=0.85,
                metadata={"name": "Character One"},
            ),
            RetrievedChunk(
                chunk_id="chunk_3",
                source_id="loc_1",
                source_type=SourceType.LOCATION,
                content="Location content",
                score=0.8,
                metadata={},
            ),
        ]

        sources = retrieval_service.get_sources(chunks)

        assert len(sources) == 2  # Two unique sources
        # Check that chunk counts are correct
        char_source = next(s for s in sources if s["source_id"] == "char_1")
        assert char_source["chunk_count"] == 2

    def test_get_sources_with_display_names(self, retrieval_service):
        """Test getting sources with custom display names."""
        chunks = [
            RetrievedChunk(
                chunk_id="chunk_1",
                source_id="char_1",
                source_type=SourceType.CHARACTER,
                content="Content",
                score=0.9,
                metadata={},
            ),
        ]
        source_names = {"char_1": "Custom Character Name"}

        sources = retrieval_service.get_sources(chunks, source_names)

        assert sources[0]["display_name"] == "Custom Character Name"

    def test_get_source_type_prefix_all_types(self, retrieval_service):
        """Test getting prefixes for all source types."""
        prefixes = {
            SourceType.CHARACTER: "C",
            SourceType.LORE: "L",
            SourceType.SCENE: "S",
            SourceType.PLOTLINE: "P",
            SourceType.ITEM: "I",
            SourceType.LOCATION: "Loc",
        }

        for source_type, expected_prefix in prefixes.items():
            prefix = retrieval_service._get_source_type_prefix(source_type)
            assert prefix == expected_prefix, f"Failed for {source_type}"

    def test_format_chunk_with_citation(self, retrieval_service):
        """Test formatting chunk with citation."""
        chunk = RetrievedChunk(
            chunk_id="chunk_1",
            source_id="char_1",
            source_type=SourceType.CHARACTER,
            content="Test content",
            score=0.9,
            metadata={"chunk_index": 1, "total_chunks": 3},
        )

        formatted = retrieval_service._format_chunk_with_citation(chunk, 1)

        assert "[1]" in formatted
        assert "CHARACTER:char_1" in formatted
        assert "part 1/3" in formatted
        assert "Test content" in formatted

    def test_format_chunk_basic(self, retrieval_service):
        """Test basic chunk formatting."""
        chunk = RetrievedChunk(
            chunk_id="chunk_1",
            source_id="char_1",
            source_type=SourceType.CHARACTER,
            content="Test content",
            score=0.9,
            metadata={"chunk_index": 1, "total_chunks": 1},
        )

        formatted = retrieval_service._format_chunk(chunk, 1)

        assert "[1]" in formatted
        assert "Test content" in formatted

    def test_format_source(self, retrieval_service):
        """Test source formatting."""
        chunk = RetrievedChunk(
            chunk_id="chunk_1",
            source_id="char_1",
            source_type=SourceType.CHARACTER,
            content="Test",
            score=0.9,
            metadata={},
        )

        source = retrieval_service._format_source(chunk)

        assert source == "CHARACTER:char_1"

    def test_deduplicate_chunks_exact_duplicates(self, retrieval_service):
        """Test deduplication of exact duplicates."""
        chunks = [
            RetrievedChunk(
                chunk_id="chunk_1",
                source_id="source_1",
                source_type=SourceType.LORE,
                content="Duplicate content",
                score=0.9,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="chunk_2",
                source_id="source_1",
                source_type=SourceType.LORE,
                content="Duplicate content",
                score=0.8,
                metadata={},
            ),
        ]

        result = retrieval_service._deduplicate_chunks(chunks)

        assert len(result) == 1
        # Should keep the higher scoring one
        assert result[0].score == 0.9

    def test_deduplicate_chunks_similar_content(self, retrieval_service):
        """Test deduplication of similar content."""
        chunks = [
            RetrievedChunk(
                chunk_id="chunk_1",
                source_id="source_1",
                source_type=SourceType.LORE,
                content="The quick brown fox jumps over the lazy dog",
                score=0.9,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="chunk_2",
                source_id="source_1",
                source_type=SourceType.LORE,
                content="The quick brown fox jumps over the lazy dog",  # Identical
                score=0.85,
                metadata={},
            ),
        ]

        result = retrieval_service._deduplicate_chunks(chunks, threshold=0.95)

        assert len(result) == 1

    def test_deduplicate_chunks_unique_content(self, retrieval_service):
        """Test deduplication with unique content."""
        chunks = [
            RetrievedChunk(
                chunk_id="chunk_1",
                source_id="source_1",
                source_type=SourceType.LORE,
                content="Completely different content one",
                score=0.9,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="chunk_2",
                source_id="source_1",
                source_type=SourceType.LORE,
                content="Totally unrelated and different content two",
                score=0.85,
                metadata={},
            ),
        ]

        result = retrieval_service._deduplicate_chunks(chunks, threshold=0.9)

        assert len(result) == 2

    def test_content_similarity_identical(self, retrieval_service):
        """Test similarity of identical strings."""
        similarity = retrieval_service._content_similarity("hello world", "hello world")
        assert similarity == 1.0

    def test_content_similarity_different(self, retrieval_service):
        """Test similarity of different strings."""
        similarity = retrieval_service._content_similarity(
            "hello world", "goodbye world"
        )
        assert 0 < similarity < 1.0

    def test_content_similarity_partial(self, retrieval_service):
        """Test similarity of partially similar strings."""
        similarity = retrieval_service._content_similarity(
            "The quick brown fox", "The quick brown dog"
        )
        assert 0.5 < similarity < 1.0

    def test_content_similarity_case_insensitive(self, retrieval_service):
        """Test similarity is case insensitive."""
        similarity = retrieval_service._content_similarity("HELLO WORLD", "hello world")
        assert similarity == 1.0

    async def test_retrieve_relevant_without_reranker(
        self, retrieval_service, mock_vector_store
    ):
        """Test retrieve when reranker is not configured."""
        mock_results = [
            QueryResult(
                id="chunk_1",
                text="Test content",
                score=0.9,
                metadata={"source_id": "source_1", "source_type": "CHARACTER"},
            ),
        ]
        mock_vector_store.query = AsyncMock(return_value=mock_results)

        result = await retrieval_service.retrieve_relevant(
            query="test query",
            options=RetrievalOptions(enable_rerank=True),  # Request reranking
        )

        # Should succeed without reranking since no reranker is configured
        assert result.is_ok

    async def test_retrieve_relevant_reranker_exception(
        self, retrieval_service, mock_vector_store
    ):
        """Test retrieve when reranker raises exception."""
        mock_rerank_service = AsyncMock()
        mock_rerank_service.rerank = AsyncMock(side_effect=Exception("Reranker failed"))
        retrieval_service._rerank_service = mock_rerank_service

        mock_results = [
            QueryResult(
                id="chunk_1",
                text="Test content",
                score=0.9,
                metadata={"source_id": "source_1", "source_type": "CHARACTER"},
            ),
        ]
        mock_vector_store.query = AsyncMock(return_value=mock_results)

        result = await retrieval_service.retrieve_relevant(
            query="test query",
            options=RetrievalOptions(enable_rerank=True),
        )

        # Should succeed with original ordering on reranker failure
        assert result.is_ok
