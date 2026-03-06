"""
Test suite for BM25 Retriever module.

Tests BM25 scoring, ranking, and retrieval functionality.
"""

import pytest
from unittest.mock import Mock, patch

from src.contexts.knowledge.application.services.bm25_retriever import (
    BM25Retriever,
    BM25Result,
    BM25IndexStats,
    IndexedDocument,
    tokenize,
    DEFAULT_K1,
    DEFAULT_B,
)
pytestmark = pytest.mark.unit



class TestTokenize:
    """Test tokenize function."""

    def test_basic_tokenization(self):
        """Test basic word tokenization."""
        result = tokenize("Hello World")
        assert result == ["hello", "world"]

    def test_tokenization_with_punctuation(self):
        """Test tokenization with punctuation."""
        result = tokenize("Hello, World! How are you?")
        assert result == ["hello", "world", "how", "are", "you"]

    def test_empty_string(self):
        """Test tokenization of empty string."""
        result = tokenize("")
        assert result == []


class TestIndexedDocument:
    """Test IndexedDocument dataclass."""

    def test_document_creation(self):
        """Test creating an indexed document."""
        doc = IndexedDocument(
            doc_id="doc1",
            source_id="source1",
            source_type="CHARACTER",
            content="Test content",
            tokens=["test", "content"],
            metadata={"key": "value"},
        )
        
        assert doc.doc_id == "doc1"
        assert doc.source_id == "source1"
        assert doc.source_type == "CHARACTER"


class TestBM25Result:
    """Test BM25Result dataclass."""

    def test_result_creation(self):
        """Test creating a BM25 result."""
        result = BM25Result(
            doc_id="doc1",
            source_id="source1",
            source_type="CHARACTER",
            content="Test content",
            score=1.5,
            metadata={"key": "value"},
        )
        
        assert result.doc_id == "doc1"
        assert result.score == 1.5


class TestBM25IndexStats:
    """Test BM25IndexStats dataclass."""

    def test_stats_creation(self):
        """Test creating index statistics."""
        stats = BM25IndexStats(
            total_documents=100,
            total_tokens=5000,
            avg_doc_length=50.0,
            last_updated="2024-01-01T00:00:00",
        )
        
        assert stats.total_documents == 100
        assert stats.total_tokens == 5000


class TestBM25Retriever:
    """Test BM25Retriever implementation."""

    @pytest.fixture
    def retriever(self):
        """Create a fresh BM25 retriever."""
        return BM25Retriever(k1=DEFAULT_K1, b=DEFAULT_B)

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        retriever = BM25Retriever()
        assert retriever._k1 == DEFAULT_K1
        assert retriever._b == DEFAULT_B

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        retriever = BM25Retriever(k1=2.0, b=0.5)
        assert retriever._k1 == 2.0
        assert retriever._b == 0.5

    def test_index_empty_list(self, retriever):
        """Test indexing empty document list."""
        count = retriever.index_documents([])
        assert count == 0

    def test_search_empty_query(self, retriever):
        """Test search with empty query."""
        with pytest.raises(ValueError, match="query cannot be empty"):
            retriever.search("")

    def test_search_whitespace_query(self, retriever):
        """Test search with whitespace-only query."""
        with pytest.raises(ValueError, match="query cannot be empty"):
            retriever.search("   ")

    def test_search_nonexistent_collection(self, retriever):
        """Test search on non-existent collection."""
        results = retriever.search("query", collection="nonexistent")
        assert results == []

    def test_remove_nonexistent_document(self, retriever):
        """Test removing a non-existent document."""
        result = retriever.remove_document("nonexistent")
        assert result is False

    def test_clear_nonexistent_collection(self, retriever):
        """Test clearing a non-existent collection."""
        count = retriever.clear_collection(collection="nonexistent")
        assert count == 0

    def test_get_stats_nonexistent_collection(self, retriever):
        """Test getting stats for non-existent collection."""
        stats = retriever.get_stats(collection="nonexistent")
        assert stats is None


class TestBM25RetrieverFilters:
    """Test BM25Retriever filter functionality."""

    @pytest.fixture
    def retriever(self):
        return BM25Retriever()

    @pytest.fixture
    def sample_document(self):
        return IndexedDocument(
            doc_id="doc1",
            source_id="char1",
            source_type="CHARACTER",
            content="Test content",
            tokens=["test", "content"],
            metadata={"tags": ["hero", "knight"], "level": 10},
        )

    def test_matches_filters_source_type(self, retriever, sample_document):
        """Test source_type filter matching."""
        matches = retriever._matches_filters(
            sample_document, {"source_type": "CHARACTER"}
        )
        assert matches is True

    def test_matches_filters_source_type_no_match(self, retriever, sample_document):
        """Test source_type filter not matching."""
        matches = retriever._matches_filters(
            sample_document, {"source_type": "LOCATION"}
        )
        assert matches is False

    def test_matches_filters_tags_single(self, retriever, sample_document):
        """Test single tag filter matching."""
        matches = retriever._matches_filters(
            sample_document, {"tags": "hero"}
        )
        assert matches is True

    def test_matches_filters_metadata(self, retriever, sample_document):
        """Test metadata filter matching."""
        matches = retriever._matches_filters(
            sample_document, {"level": 10}
        )
        assert matches is True

    def test_matches_filters_no_filters(self, retriever, sample_document):
        """Test with no filters."""
        matches = retriever._matches_filters(sample_document, {})
        assert matches is True
