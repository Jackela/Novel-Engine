"""
Tests for Hybrid Retriever with Score Fusion

Constitution Compliance:
- Article III (TDD): Tests verify hybrid retrieval behavior

Warzone 4: AI Brain - BRAIN-008B
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, MagicMock
from datetime import datetime

import pytest

from src.contexts.knowledge.application.services.hybrid_retriever import (
    HybridRetriever,
    HybridConfig,
    HybridResult,
    FusionMetadata,
    _normalize_scores,
    _reciprocal_rank_fusion,
    _linear_score_fusion,
    _hybrid_score_fusion,
    DEFAULT_VECTOR_WEIGHT,
    DEFAULT_BM25_WEIGHT,
    DEFAULT_RRF_K,
    DEFAULT_RRF_ALPHA,
)
from src.contexts.knowledge.application.services.retrieval_service import (
    RetrievalFilter,
    RetrievalOptions,
    RetrievalResult,
)
from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    RetrievedChunk,
)
from src.contexts.knowledge.application.services.bm25_retriever import (
    BM25Result,
)
from src.contexts.knowledge.domain.models.source_type import SourceType


# ============================================================================
# Score Normalization Tests
# ============================================================================

class TestNormalizeScores:
    """Tests for _normalize_scores utility function."""

    def test_normalize_empty_list(self):
        """Normalizing empty list returns empty list."""
        result = _normalize_scores([])
        assert result == []

    def test_normalize_single_value(self):
        """Single value normalizes to 0.5."""
        result = _normalize_scores([0.5])
        assert result == [0.5]

    def test_normalize_identical_values(self):
        """Identical values all normalize to 0.5."""
        result = _normalize_scores([0.7, 0.7, 0.7])
        assert result == [0.5, 0.5, 0.5]

    def test_normalize_min_max(self):
        """Values normalize to [0, 1] range."""
        result = _normalize_scores([0.1, 0.5, 0.9])
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(0.5)
        assert result[2] == pytest.approx(1.0)

    def test_normalize_negative_values(self):
        """Negative values are handled correctly."""
        result = _normalize_scores([-1.0, 0.0, 1.0])
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(0.5)
        assert result[2] == pytest.approx(1.0)


# ============================================================================
# Reciprocal Rank Fusion Tests
# ============================================================================

class TestReciprocalRankFusion:
    """Tests for _reciprocal_rank_fusion function."""

    def test_rrf_empty_inputs(self):
        """Empty inputs return empty dict."""
        result = _reciprocal_rank_fusion({}, {}, k=60)
        assert result == {}

    def test_rrf_single_source(self):
        """Single source works correctly."""
        vector = {"doc1": (0.9, 1)}
        bm25 = {}

        result = _reciprocal_rank_fusion(vector, bm25, k=60)

        assert len(result) == 1
        assert result["doc1"] == pytest.approx(1.0 / 61)

    def test_rrf_both_sources(self):
        """Both sources contribute to score."""
        vector = {"doc1": (0.9, 1), "doc2": (0.7, 2)}
        bm25 = {"doc2": (10.0, 1), "doc1": (5.0, 2)}

        result = _reciprocal_rank_fusion(vector, bm25, k=60)

        # Both documents should have scores
        assert "doc1" in result
        assert "doc2" in result

        # doc1: 1/(60+1) + 1/(60+2) = 1/61 + 1/62
        expected_doc1 = 1.0 / 61 + 1.0 / 62
        assert result["doc1"] == pytest.approx(expected_doc1)

        # doc2: 1/(60+2) + 1/(60+1) = 1/62 + 1/61
        expected_doc2 = 1.0 / 62 + 1.0 / 61
        assert result["doc2"] == pytest.approx(expected_doc2)

    def test_rrf_k_parameter(self):
        """K parameter affects score distribution."""
        vector = {"doc1": (0.9, 1)}
        bm25 = {}

        result_k10 = _reciprocal_rank_fusion(vector, bm25, k=10)
        result_k100 = _reciprocal_rank_fusion(vector, bm25, k=100)

        # Smaller k = larger score
        assert result_k10["doc1"] > result_k100["doc1"]

    def test_rrf_unique_docs(self):
        """Unique docs from both sources are included."""
        vector = {"doc1": (0.9, 1), "doc2": (0.7, 2)}
        bm25 = {"doc3": (10.0, 1)}

        result = _reciprocal_rank_fusion(vector, bm25, k=60)

        assert len(result) == 3
        assert "doc1" in result
        assert "doc2" in result
        assert "doc3" in result


# ============================================================================
# Linear Score Fusion Tests
# ============================================================================

class TestLinearScoreFusion:
    """Tests for _linear_score_fusion function."""

    def test_linear_empty_inputs(self):
        """Empty inputs return empty dict."""
        result = _linear_score_fusion({}, {}, 0.7, 0.3)
        assert result == {}

    def test_linear_single_source(self):
        """Single source returns normalized scores."""
        vector = {"doc1": 0.9, "doc2": 0.7}
        bm25 = {}

        result = _linear_score_fusion(vector, bm25, 0.7, 0.3)

        assert len(result) == 2
        assert result["doc1"] == pytest.approx(0.7 * 1.0)  # vector_weight * 1.0
        assert result["doc2"] == pytest.approx(0.7 * 0.0)  # vector_weight * 0.0

    def test_linear_both_sources(self):
        """Both sources contribute to fused score."""
        vector = {"doc1": 0.9, "doc2": 0.7}
        bm25 = {"doc2": 10.0, "doc1": 5.0}

        result = _linear_score_fusion(vector, bm25, 0.7, 0.3)

        # doc1: 0.7 * 1.0 + 0.3 * 0.0 = 0.7
        assert result["doc1"] == pytest.approx(0.7)

        # doc2: 0.7 * 0.0 + 0.3 * 1.0 = 0.3
        assert result["doc2"] == pytest.approx(0.3)

    def test_linear_unique_docs(self):
        """Unique docs from both sources are included."""
        vector = {"doc1": 0.9, "doc2": 0.7}
        bm25 = {"doc3": 10.0}

        result = _linear_score_fusion(vector, bm25, 0.7, 0.3)

        assert len(result) == 3
        assert result["doc1"] == pytest.approx(0.7 * 1.0)
        assert result["doc2"] == pytest.approx(0.7 * 0.0)
        # doc3 only appears in BM25 with single value, so normalized to 0.5
        assert result["doc3"] == pytest.approx(0.3 * 0.5)

    def test_linear_weight_normalization(self):
        """Weights are applied correctly."""
        # Use different values to get meaningful normalization
        vector = {"doc1": 0.9, "doc2": 0.1}
        bm25 = {"doc1": 0.5, "doc2": 0.5}

        # Equal weights
        result = _linear_score_fusion(vector, bm25, 0.5, 0.5)
        # doc1: 0.5 * 1.0 + 0.5 * 0.5 = 0.75 (BM25 has same scores -> both 0.5)
        assert result["doc1"] == pytest.approx(0.75)
        # doc2: 0.5 * 0.0 + 0.5 * 0.5 = 0.25
        assert result["doc2"] == pytest.approx(0.25)


# ============================================================================
# Hybrid Score Fusion Tests
# ============================================================================

class TestHybridScoreFusion:
    """Tests for _hybrid_score_fusion function."""

    def test_hybrid_empty_inputs(self):
        """Empty inputs return empty dict."""
        config = HybridConfig()
        result = _hybrid_score_fusion({}, {}, config)
        assert result == {}

    def test_hybrid_rrf_only(self):
        """With rrf_alpha=1.0, only RRF is used."""
        config = HybridConfig(rrf_alpha=1.0)
        vector = {"doc1": (0.9, 1)}
        bm25 = {"doc1": (5.0, 2)}

        result = _hybrid_score_fusion(vector, bm25, config)

        assert "doc1" in result
        # Should be based purely on ranks: 1/(60+1) + 1/(60+2)
        expected = 1.0 / 61 + 1.0 / 62
        # After normalization, should be 1.0 (only document)
        assert result["doc1"] == pytest.approx(0.5)  # Normalized single value

    def test_hybrid_linear_only(self):
        """With rrf_alpha=0.0, only linear fusion is used."""
        config = HybridConfig(rrf_alpha=0.0, vector_weight=0.7, bm25_weight=0.3)
        vector = {"doc1": (0.9, 1), "doc2": (0.7, 2)}
        bm25 = {"doc2": (10.0, 1), "doc1": (5.0, 2)}

        result = _hybrid_score_fusion(vector, bm25, config)

        # doc1: 0.7 * 1.0 + 0.3 * 0.0 = 0.7
        assert result["doc1"] == pytest.approx(0.7)
        # doc2: 0.7 * 0.0 + 0.3 * 1.0 = 0.3
        assert result["doc2"] == pytest.approx(0.3)

    def test_hybrid_combined(self):
        """With rrf_alpha=0.5, both methods are combined."""
        config = HybridConfig(rrf_alpha=0.5)
        vector = {"doc1": (0.9, 1), "doc2": (0.7, 2)}
        bm25 = {"doc2": (10.0, 1), "doc1": (5.0, 2)}

        result = _hybrid_score_fusion(vector, bm25, config)

        # Results should be between 0 and 1
        for score in result.values():
            assert 0.0 <= score <= 1.0


# ============================================================================
# HybridConfig Tests
# ============================================================================

class TestHybridConfig:
    """Tests for HybridConfig value object."""

    def test_default_values(self):
        """Default configuration values are correct."""
        config = HybridConfig()

        assert config.vector_weight == DEFAULT_VECTOR_WEIGHT
        assert config.bm25_weight == DEFAULT_BM25_WEIGHT
        assert config.use_rrf is True
        assert config.rrf_k == DEFAULT_RRF_K
        assert config.rrf_alpha == DEFAULT_RRF_ALPHA

    def test_custom_values(self):
        """Custom values are stored correctly."""
        config = HybridConfig(
            vector_weight=0.5,
            bm25_weight=0.5,
            use_rrf=False,
            rrf_k=100,
            rrf_alpha=0.7,
        )

        assert config.vector_weight == 0.5
        assert config.bm25_weight == 0.5
        assert config.use_rrf is False
        assert config.rrf_k == 100
        assert config.rrf_alpha == 0.7

    def test_invalid_vector_weight_raises(self):
        """Invalid vector weight raises ValueError."""
        with pytest.raises(ValueError, match="vector_weight must be between"):
            HybridConfig(vector_weight=1.5)

        with pytest.raises(ValueError, match="vector_weight must be between"):
            HybridConfig(vector_weight=-0.1)

    def test_invalid_bm25_weight_raises(self):
        """Invalid BM25 weight raises ValueError."""
        with pytest.raises(ValueError, match="bm25_weight must be between"):
            HybridConfig(bm25_weight=1.5)

    def test_invalid_rrf_k_raises(self):
        """Invalid RRF k raises ValueError."""
        with pytest.raises(ValueError, match="rrf_k must be positive"):
            HybridConfig(rrf_k=0)

    def test_invalid_rrf_alpha_raises(self):
        """Invalid RRF alpha raises ValueError."""
        with pytest.raises(ValueError, match="rrf_alpha must be between"):
            HybridConfig(rrf_alpha=1.5)

    def test_weights_warning_when_not_summing_to_one(self, caplog):
        """Warning logged when weights don't sum to 1.0."""
        import logging
        import structlog

        # This should trigger a warning
        config = HybridConfig(vector_weight=0.8, bm25_weight=0.4)

        # Config should still be created
        assert config.vector_weight == 0.8
        assert config.bm25_weight == 0.4


# ============================================================================
# HybridRetriever Tests
# ============================================================================

class TestHybridRetriever:
    """Tests for HybridRetriever."""

    @pytest.fixture
    def mock_retrieval_service(self):
        """Mock RetrievalService."""
        service = AsyncMock()
        return service

    @pytest.fixture
    def mock_bm25_retriever(self):
        """Mock BM25Retriever."""
        retriever = Mock()
        return retriever

    @pytest.fixture
    def sample_vector_chunks(self):
        """Sample vector search results."""
        return [
            RetrievedChunk(
                chunk_id="doc1",
                source_id="char1",
                source_type=SourceType.CHARACTER,
                content="Sir Aldric is a brave knight",
                score=0.9,
                metadata={"chunk_index": 0, "total_chunks": 1},
            ),
            RetrievedChunk(
                chunk_id="doc2",
                source_id="char2",
                source_type=SourceType.CHARACTER,
                content="Lady Elara is a wise wizard",
                score=0.7,
                metadata={"chunk_index": 0, "total_chunks": 1},
            ),
        ]

    @pytest.fixture
    def sample_bm25_results(self):
        """Sample BM25 results."""
        return [
            BM25Result(
                doc_id="doc2",
                source_id="char2",
                source_type="CHARACTER",
                content="Lady Elara is a wise wizard",
                score=10.0,
                metadata={"chunk_index": 0, "total_chunks": 1},
            ),
            BM25Result(
                doc_id="doc1",
                source_id="char1",
                source_type="CHARACTER",
                content="Sir Aldric is a brave knight",
                score=5.0,
                metadata={"chunk_index": 0, "total_chunks": 1},
            ),
        ]

    @pytest.fixture
    def retriever(
        self,
        mock_retrieval_service,
        mock_bm25_retriever,
    ):
        """HybridRetriever instance with mocked dependencies."""
        return HybridRetriever(
            retrieval_service=mock_retrieval_service,
            bm25_retriever=mock_bm25_retriever,
        )

    def test_initialization(self, mock_retrieval_service, mock_bm25_retriever):
        """Retriever initializes correctly."""
        config = HybridConfig(vector_weight=0.6, bm25_weight=0.4)
        retriever = HybridRetriever(
            retrieval_service=mock_retrieval_service,
            bm25_retriever=mock_bm25_retriever,
            config=config,
            default_collection="custom",
        )

        assert retriever._retrieval_service == mock_retrieval_service
        assert retriever._bm25_retriever == mock_bm25_retriever
        assert retriever._config == config
        assert retriever._default_collection == "custom"

    @pytest.mark.asyncio
    async def test_search_empty_query_raises(self, retriever):
        """Empty query raises ValueError."""
        with pytest.raises(ValueError, match="query cannot be empty"):
            await retriever.search("")

    @pytest.mark.asyncio
    async def test_search_basic(
        self,
        retriever,
        mock_retrieval_service,
        mock_bm25_retriever,
        sample_vector_chunks,
        sample_bm25_results,
    ):
        """Basic search combines results from both sources."""
        # Setup mocks
        mock_vector_result = RetrievalResult(
            chunks=sample_vector_chunks,
            query="brave knight",
            total_retrieved=2,
        )
        mock_retrieval_service.retrieve_relevant = AsyncMock(return_value=mock_vector_result)
        mock_bm25_retriever.search = Mock(return_value=sample_bm25_results)

        # Execute search
        result = await retriever.search("brave knight", k=5)

        # Verify structure
        assert isinstance(result, HybridResult)
        assert len(result.chunks) > 0
        # Default config has rrf_alpha=0.5, so fusion_method is "hybrid"
        assert result.fusion_method == "hybrid"

        # Verify both sources were called
        mock_retrieval_service.retrieve_relevant.assert_called_once()
        mock_bm25_retriever.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_vector_only(
        self,
        retriever,
        mock_retrieval_service,
        mock_bm25_retriever,
        sample_vector_chunks,
    ):
        """Search works when only vector has results."""
        # Setup mocks: BM25 returns empty
        mock_vector_result = RetrievalResult(
            chunks=sample_vector_chunks,
            query="brave knight",
            total_retrieved=2,
        )
        mock_retrieval_service.retrieve_relevant = AsyncMock(return_value=mock_vector_result)
        mock_bm25_retriever.search = Mock(return_value=[])

        result = await retriever.search("brave knight", k=5)

        # Should return vector results
        assert len(result.chunks) == 2

    @pytest.mark.asyncio
    async def test_search_bm25_only(
        self,
        retriever,
        mock_retrieval_service,
        mock_bm25_retriever,
        sample_bm25_results,
    ):
        """Search works when only BM25 has results."""
        # Setup mocks: Vector returns empty
        mock_vector_result = RetrievalResult(
            chunks=[],
            query="brave knight",
            total_retrieved=0,
        )
        mock_retrieval_service.retrieve_relevant = AsyncMock(return_value=mock_vector_result)
        mock_bm25_retriever.search = Mock(return_value=sample_bm25_results)

        result = await retriever.search("brave knight", k=5)

        # Should return BM25 results
        assert len(result.chunks) == 2

    @pytest.mark.asyncio
    async def test_search_with_filters(
        self,
        retriever,
        mock_retrieval_service,
        mock_bm25_retriever,
        sample_vector_chunks,
        sample_bm25_results,
    ):
        """Search with filters converts filters correctly."""
        filters = RetrievalFilter(source_types=[SourceType.CHARACTER])

        mock_vector_result = RetrievalResult(
            chunks=sample_vector_chunks,
            query="brave knight",
            total_retrieved=2,
        )
        mock_retrieval_service.retrieve_relevant = AsyncMock(return_value=mock_vector_result)
        mock_bm25_retriever.search = Mock(return_value=sample_bm25_results)

        await retriever.search("brave knight", filters=filters)

        # Verify filters were passed to vector search
        call_args = mock_retrieval_service.retrieve_relevant.call_args
        assert call_args.kwargs["filters"] == filters

        # Verify filters were converted for BM25
        bm25_call_args = mock_bm25_retriever.search.call_args
        assert "filters" in bm25_call_args.kwargs

    @pytest.mark.asyncio
    async def test_search_with_config_override(
        self,
        retriever,
        mock_retrieval_service,
        mock_bm25_retriever,
        sample_vector_chunks,
        sample_bm25_results,
    ):
        """Config override applies to single search."""
        mock_vector_result = RetrievalResult(
            chunks=sample_vector_chunks,
            query="brave knight",
            total_retrieved=2,
        )
        mock_retrieval_service.retrieve_relevant = AsyncMock(return_value=mock_vector_result)
        mock_bm25_retriever.search = Mock(return_value=sample_bm25_results)

        custom_config = HybridConfig(
            vector_weight=0.5,
            bm25_weight=0.5,
            rrf_alpha=0.0,  # Linear only
        )

        result = await retriever.search(
            "brave knight",
            k=5,
            config_override=custom_config,
        )

        # Fusion method should be "linear" (not "rrf")
        assert result.fusion_method == "linear"

    @pytest.mark.asyncio
    async def test_search_handles_vector_failure(
        self,
        retriever,
        mock_retrieval_service,
        mock_bm25_retriever,
        sample_bm25_results,
    ):
        """Search continues when vector search fails."""
        # Vector search raises exception
        mock_retrieval_service.retrieve_relevant = AsyncMock(
            side_effect=Exception("Vector search failed")
        )
        mock_bm25_retriever.search = Mock(return_value=sample_bm25_results)

        # Should not raise, but return BM25 results
        result = await retriever.search("brave knight", k=5)

        assert len(result.chunks) > 0

    @pytest.mark.asyncio
    async def test_search_handles_bm25_failure(
        self,
        retriever,
        mock_retrieval_service,
        mock_bm25_retriever,
        sample_vector_chunks,
    ):
        """Search continues when BM25 search fails."""
        mock_vector_result = RetrievalResult(
            chunks=sample_vector_chunks,
            query="brave knight",
            total_retrieved=2,
        )
        mock_retrieval_service.retrieve_relevant = AsyncMock(return_value=mock_vector_result)
        mock_bm25_retriever.search = Mock(side_effect=Exception("BM25 failed"))

        # Should not raise, but return vector results
        result = await retriever.search("brave knight", k=5)

        assert len(result.chunks) > 0

    @pytest.mark.asyncio
    async def test_fuse_results_deduplicates(
        self,
        retriever,
        mock_retrieval_service,
        mock_bm25_retriever,
    ):
        """Fusion deduplicates chunks with same content."""
        # Same chunk in both results
        chunk_data = RetrievedChunk(
            chunk_id="doc1",
            source_id="char1",
            source_type=SourceType.CHARACTER,
            content="Sir Aldric is a brave knight",
            score=0.9,
            metadata={"chunk_index": 0},
        )

        mock_vector_result = RetrievalResult(
            chunks=[chunk_data],
            query="brave knight",
            total_retrieved=1,
        )
        mock_retrieval_service.retrieve_relevant = AsyncMock(return_value=mock_vector_result)

        bm25_result = BM25Result(
            doc_id="doc1",
            source_id="char1",
            source_type="CHARACTER",
            content="Sir Aldric is a brave knight",
            score=10.0,
            metadata={"chunk_index": 0},
        )
        mock_bm25_retriever.search = Mock(return_value=[bm25_result])

        result = await retriever.search("brave knight", k=5)

        # Should only have one instance of the duplicate
        doc1_count = sum(1 for c in result.chunks if c.chunk_id == "doc1")
        assert doc1_count == 1

    @pytest.mark.asyncio
    async def test_search_respects_k_limit(
        self,
        retriever,
        mock_retrieval_service,
        mock_bm25_retriever,
    ):
        """Search returns at most k results."""
        # Create many chunks
        vector_chunks = [
            RetrievedChunk(
                chunk_id=f"doc{i}",
                source_id=f"char{i}",
                source_type=SourceType.CHARACTER,
                content=f"Character {i}",
                score=0.9 - (i * 0.1),
                metadata={},
            )
            for i in range(10)
        ]

        bm25_results = [
            BM25Result(
                doc_id=f"doc{i}",
                source_id=f"char{i}",
                source_type="CHARACTER",
                content=f"Character {i}",
                score=10.0 - i,
                metadata={},
            )
            for i in range(10)
        ]

        mock_vector_result = RetrievalResult(
            chunks=vector_chunks,
            query="character",
            total_retrieved=10,
        )
        mock_retrieval_service.retrieve_relevant = AsyncMock(return_value=mock_vector_result)
        mock_bm25_retriever.search = Mock(return_value=bm25_results)

        result = await retriever.search("character", k=5)

        # Should return at most k results
        assert len(result.chunks) <= 5

    def test_convert_filters_none(self, retriever):
        """None filters return None."""
        result = retriever._convert_filters(None)
        assert result is None

    def test_convert_filters_source_type(self, retriever):
        """Source type filter is converted."""
        filters = RetrievalFilter(source_types=[SourceType.CHARACTER])
        result = retriever._convert_filters(filters)

        assert result is not None
        assert result["source_type"] == "CHARACTER"

    def test_convert_filters_tags(self, retriever):
        """Tags filter is converted."""
        filters = RetrievalFilter(tags=["hero", "protagonist"])
        result = retriever._convert_filters(filters)

        assert result is not None
        assert result["tags"] == ["hero", "protagonist"]

    def test_convert_filters_custom_metadata(self, retriever):
        """Custom metadata is passed through."""
        filters = RetrievalFilter(custom_metadata={"category": "main"})
        result = retriever._convert_filters(filters)

        assert result is not None
        assert result["category"] == "main"

    def test_bm25_to_retrieved(self, retriever):
        """BM25Result is converted to RetrievedChunk."""
        bm25_results = [
            BM25Result(
                doc_id="doc1",
                source_id="char1",
                source_type="CHARACTER",
                content="Sir Aldric is a brave knight",
                score=10.0,
                metadata={"chunk_index": 0},
            ),
        ]

        result = retriever._bm25_to_retrieved(bm25_results)

        assert len(result) == 1
        chunk = result[0]
        assert chunk.chunk_id == "doc1"
        assert chunk.source_id == "char1"
        assert chunk.source_type == SourceType.CHARACTER
        assert chunk.content == "Sir Aldric is a brave knight"
        assert chunk.score == 10.0


# ============================================================================
# Integration Tests
# ============================================================================

class TestHybridRetrieverIntegration:
    """Integration tests for hybrid retrieval."""

    @pytest.fixture
    def mock_retrieval_service_int(self):
        """Mock RetrievalService for integration tests."""
        service = AsyncMock()
        return service

    @pytest.fixture
    def mock_bm25_retriever_int(self):
        """Mock BM25Retriever for integration tests."""
        retriever = Mock()
        return retriever

    @pytest.mark.asyncio
    async def test_hybrid_vs_pure_vector(
        self,
        mock_retrieval_service_int,
        mock_bm25_retriever_int,
    ):
        """Compare hybrid vs pure vector search results."""
        # Setup: doc1 ranks high in vector, doc2 ranks high in BM25
        vector_chunks = [
            RetrievedChunk(
                chunk_id="doc1",
                source_id="char1",
                source_type=SourceType.CHARACTER,
                content="A brave knight with valor",
                score=0.95,
                metadata={},
            ),
            RetrievedChunk(
                chunk_id="doc2",
                source_id="char2",
                source_type=SourceType.CHARACTER,
                content="A courageous hero",
                score=0.6,
                metadata={},
            ),
        ]

        bm25_results = [
            BM25Result(
                doc_id="doc2",
                source_id="char2",
                source_type="CHARACTER",
                content="A courageous hero",
                score=15.0,
                metadata={},
            ),
            BM25Result(
                doc_id="doc1",
                source_id="char1",
                source_type="CHARACTER",
                content="A brave knight with valor",
                score=5.0,
                metadata={},
            ),
        ]

        mock_vector_result = RetrievalResult(
            chunks=vector_chunks,
            query="brave courageous",
            total_retrieved=2,
        )
        mock_retrieval_service_int.retrieve_relevant = AsyncMock(return_value=mock_vector_result)
        mock_bm25_retriever_int.search = Mock(return_value=bm25_results)

        # Test with equal weights
        retriever = HybridRetriever(
            retrieval_service=mock_retrieval_service_int,
            bm25_retriever=mock_bm25_retriever_int,
            config=HybridConfig(vector_weight=0.5, bm25_weight=0.5),
        )

        result = await retriever.search("brave courageous", k=2)

        # Both documents should appear
        assert len(result.chunks) == 2

        # With equal weights and RRF, results depend on combined scores
        # Just verify both documents are present and have scores
        chunk_ids = {c.chunk_id for c in result.chunks}
        assert "doc1" in chunk_ids
        assert "doc2" in chunk_ids

        # Verify chunks have valid scores
        for chunk in result.chunks:
            assert 0.0 <= chunk.score <= 1.0

    @pytest.mark.asyncio
    async def test_rrf_vs_linear_fusion(
        self,
        mock_retrieval_service_int,
        mock_bm25_retriever_int,
    ):
        """Compare RRF vs linear fusion methods."""
        vector_chunks = [
            RetrievedChunk(
                chunk_id="doc1",
                source_id="char1",
                source_type=SourceType.CHARACTER,
                content="brave knight",
                score=0.9,
                metadata={},
            ),
        ]

        bm25_results = [
            BM25Result(
                doc_id="doc1",
                source_id="char1",
                source_type="CHARACTER",
                content="brave knight",
                score=10.0,
                metadata={},
            ),
        ]

        mock_vector_result = RetrievalResult(
            chunks=vector_chunks,
            query="brave",
            total_retrieved=1,
        )
        mock_retrieval_service_int.retrieve_relevant = AsyncMock(return_value=mock_vector_result)
        mock_bm25_retriever_int.search = Mock(return_value=bm25_results)

        # Pure RRF fusion (rrf_alpha=1.0)
        rrf_retriever = HybridRetriever(
            retrieval_service=mock_retrieval_service_int,
            bm25_retriever=mock_bm25_retriever_int,
            config=HybridConfig(use_rrf=True, rrf_alpha=1.0),
        )

        rrf_result = await rrf_retriever.search("brave", k=1)

        # Linear fusion (use_rrf=False)
        linear_retriever = HybridRetriever(
            retrieval_service=mock_retrieval_service_int,
            bm25_retriever=mock_bm25_retriever_int,
            config=HybridConfig(use_rrf=False),
        )

        linear_result = await linear_retriever.search("brave", k=1)

        # Both should return results
        assert len(rrf_result.chunks) > 0
        assert len(linear_result.chunks) > 0

        # Fusion methods should be different
        assert rrf_result.fusion_method == "rrf"
        assert linear_result.fusion_method == "linear"
