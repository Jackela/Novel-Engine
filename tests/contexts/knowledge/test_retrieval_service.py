"""
Test suite for Retrieval Service module.

Tests query processing, relevance scoring, and context assembly.
"""

import pytest
from unittest.mock import Mock

from src.contexts.knowledge.application.services.retrieval_service import (
    RetrievalService,
    RetrievalFilter,
    RetrievalOptions,
    RetrievalResult,
    FormattedContext,
    DEFAULT_RELEVANCE_THRESHOLD,
    DEFAULT_DEDUPLICATION_SIMILARITY,
)
from src.contexts.knowledge.domain.models.source_type import SourceType
pytestmark = pytest.mark.unit



class TestRetrievalFilter:
    """Test RetrievalFilter dataclass."""

    def test_filter_creation(self):
        """Test creating a retrieval filter."""
        filter_obj = RetrievalFilter(
            source_types=[SourceType.CHARACTER, SourceType.LORE],
            tags=["important", "hero"],
        )
        
        assert filter_obj.source_types == [SourceType.CHARACTER, SourceType.LORE]
        assert filter_obj.tags == ["important", "hero"]

    def test_to_where_clause_empty(self):
        """Test converting empty filter to where clause."""
        filter_obj = RetrievalFilter()
        clause = filter_obj.to_where_clause()
        
        assert clause == {}

    def test_to_where_clause_with_source_types(self):
        """Test where clause with source types."""
        filter_obj = RetrievalFilter(source_types=[SourceType.CHARACTER])
        clause = filter_obj.to_where_clause()
        
        assert "source_type" in clause

    def test_matches_no_metadata(self):
        """Test matching with no metadata."""
        filter_obj = RetrievalFilter()
        assert filter_obj.matches(None) is False


class TestRetrievalOptions:
    """Test RetrievalOptions dataclass."""

    def test_default_options(self):
        """Test default retrieval options."""
        options = RetrievalOptions()
        
        assert options.k == 5
        assert options.min_score == DEFAULT_RELEVANCE_THRESHOLD
        assert options.deduplicate is True
        assert options.enable_rerank is True

    def test_custom_options(self):
        """Test custom retrieval options."""
        options = RetrievalOptions(
            k=10,
            min_score=0.7,
            deduplicate=False,
            enable_rerank=False,
        )
        
        assert options.k == 10
        assert options.min_score == 0.7


class TestFormattedContext:
    """Test FormattedContext dataclass."""

    def test_context_creation(self):
        """Test creating formatted context."""
        context = FormattedContext(
            text="Context text here",
            sources=["char1", "loc1"],
            total_tokens=100,
            chunk_count=2,
        )
        
        assert context.text == "Context text here"
        assert context.sources == ["char1", "loc1"]
        assert context.total_tokens == 100
        assert context.chunk_count == 2


class TestRetrievalService:
    """Test RetrievalService implementation."""

    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        return Mock()

    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store."""
        return Mock()

    @pytest.fixture
    def retrieval_service(self, mock_embedding_service, mock_vector_store):
        """Create retrieval service with mocks."""
        return RetrievalService(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            default_collection="test_collection",
        )

    def test_service_initialization(self, retrieval_service):
        """Test service initialization."""
        assert retrieval_service._default_collection == "test_collection"
        assert retrieval_service._rerank_service is None

    def test_get_source_type_prefix_character(self, retrieval_service):
        """Test getting citation prefix for CHARACTER type."""
        prefix = retrieval_service._get_source_type_prefix(SourceType.CHARACTER)
        assert prefix == "C"

    def test_get_source_type_prefix_lore(self, retrieval_service):
        """Test getting citation prefix for LORE type."""
        prefix = retrieval_service._get_source_type_prefix(SourceType.LORE)
        assert prefix == "L"

    def test_get_source_type_prefix_scene(self, retrieval_service):
        """Test getting citation prefix for SCENE type."""
        prefix = retrieval_service._get_source_type_prefix(SourceType.SCENE)
        assert prefix == "S"

    def test_content_similarity_identical(self, retrieval_service):
        """Test similarity between identical texts."""
        similarity = retrieval_service._content_similarity(
            "The quick brown fox",
            "The quick brown fox",
        )
        
        assert similarity == 1.0

    def test_content_similarity_different(self, retrieval_service):
        """Test similarity between different texts."""
        similarity = retrieval_service._content_similarity(
            "The quick brown fox",
            "A completely different sentence",
        )
        
        assert 0 <= similarity < 1.0


class TestRetrievalServiceDeduplication:
    """Test deduplication functionality."""

    @pytest.fixture
    def retrieval_service(self):
        mock_embedding = Mock()
        mock_store = Mock()
        return RetrievalService(mock_embedding, mock_store)

    def test_deduplicate_empty_list(self, retrieval_service):
        """Test deduplication with empty list."""
        result = retrieval_service._deduplicate_chunks([])
        assert result == []

    def test_deduplicate_single_chunk(self, retrieval_service):
        """Test deduplication with single chunk."""
        from src.contexts.knowledge.application.services.knowledge_ingestion_service import RetrievedChunk
        
        chunks = [
            RetrievedChunk(
                chunk_id="chunk1",
                source_id="char1",
                source_type=SourceType.CHARACTER,
                content="Content",
                score=0.9,
                metadata={},
            ),
        ]
        
        result = retrieval_service._deduplicate_chunks(chunks)
        assert len(result) == 1

    def test_deduplicate_unique_chunks(self, retrieval_service):
        """Test deduplication with unique chunks."""
        from src.contexts.knowledge.application.services.knowledge_ingestion_service import RetrievedChunk
        
        chunks = [
            RetrievedChunk(
                chunk_id="chunk1",
                source_id="char1",
                source_type=SourceType.CHARACTER,
                content="Unique content one",
                score=0.9,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="chunk2",
                source_id="char2",
                source_type=SourceType.CHARACTER,
                content="Unique content two",
                score=0.85,
                metadata={},
            ),
        ]
        
        result = retrieval_service._deduplicate_chunks(chunks, threshold=0.9)
        assert len(result) == 2
