"""
Unit tests for RerankService and IReranker port.

Warzone 4: AI Brain - BRAIN-010A, BRAIN-010B
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.contexts.knowledge.application.ports.i_reranker import (
    IReranker,
    RerankDocument,
    RerankerError,
    RerankOutput,
    RerankResult,
)
from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    RetrievedChunk,
)
from src.contexts.knowledge.application.services.rerank_service import (
    DEFAULT_TOP_K,
    FailingReranker,
    MockReranker,
    RerankConfig,
    RerankService,
    RerankServiceResult,
)
from src.contexts.knowledge.domain.models.source_type import SourceType

pytestmark = pytest.mark.unit


@pytest.fixture
def sample_chunks() -> list[RetrievedChunk]:
    """Create sample chunks for testing."""
    return [
        RetrievedChunk(
            chunk_id="chunk_1",
            source_id="char_alice",
            source_type=SourceType.CHARACTER,
            content="Alice is a brave warrior who fights with honor.",
            score=0.85,
            metadata={"chunk_index": 0, "total_chunks": 1},
        ),
        RetrievedChunk(
            chunk_id="chunk_2",
            source_id="char_bob",
            source_type=SourceType.CHARACTER,
            content="Bob is a cunning thief with a heart of gold.",
            score=0.75,
            metadata={"chunk_index": 0, "total_chunks": 1},
        ),
        RetrievedChunk(
            chunk_id="chunk_3",
            source_id="lore_kingdom",
            source_type=SourceType.LORE,
            content="The kingdom has stood for a thousand years.",
            score=0.65,
            metadata={"chunk_index": 0, "total_chunks": 1},
        ),
        RetrievedChunk(
            chunk_id="chunk_4",
            source_id="char_charlie",
            source_type=SourceType.CHARACTER,
            content="Charlie is a wise wizard from the eastern lands.",
            score=0.55,
            metadata={"chunk_index": 0, "total_chunks": 1},
        ),
        RetrievedChunk(
            chunk_id="chunk_5",
            source_id="lore_dragons",
            source_type=SourceType.LORE,
            content="Dragons were once common but are now rare.",
            score=0.45,
            metadata={"chunk_index": 0, "total_chunks": 1},
        ),
    ]


@pytest.fixture
def mock_reranker_impl() -> IReranker:
    """Create a mock IReranker implementation."""
    reranker = AsyncMock()

    async def mock_rerank(
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

        # Calculate score improvement
        avg_original = sum(d.score for d in documents) / len(documents)
        avg_new = sum(r.relevance_score for r in reranked) / len(reranked)
        score_improvement = max(0.0, avg_new - avg_original)

        return RerankOutput(
            results=reranked,
            query=query,
            total_reranked=len(documents),
            model="test_model",
            latency_ms=50.0,
            score_improvement=score_improvement,
        )

    reranker.rerank = mock_rerank
    return reranker


class TestRerankService:
    """Tests for RerankService."""

    @pytest.mark.asyncio
    async def test_rerank_reorders_chunks(
        self, sample_chunks: list[RetrievedChunk], mock_reranker_impl: IReranker
    ):
        """Test that reranking reorders chunks based on reranker output."""
        service = RerankService(reranker=mock_reranker_impl)

        result = await service.rerank(
            query="brave warrior",
            chunks=sample_chunks,
            top_k=3,
        )

        assert result.reranked is True
        assert result.model == "test_model"
        assert result.total_input == 5
        assert result.total_output == 3
        assert len(result.chunks) == 3

        # Chunks should be in reverse order (reversed by mock)
        # Last chunk becomes first
        assert result.chunks[0].chunk_id == "chunk_5"
        assert result.chunks[1].chunk_id == "chunk_4"
        assert result.chunks[2].chunk_id == "chunk_3"

    @pytest.mark.asyncio
    async def test_rerank_updates_scores(
        self, sample_chunks: list[RetrievedChunk], mock_reranker_impl: IReranker
    ):
        """Test that reranking updates relevance scores."""
        service = RerankService(reranker=mock_reranker_impl)

        result = await service.rerank(
            query="brave warrior",
            chunks=sample_chunks,
        )

        # Scores should be updated
        # Mock adds 0.15 to original scores
        assert result.chunks[0].score > sample_chunks[4].score
        assert result.chunks[1].score > sample_chunks[3].score

    @pytest.mark.asyncio
    async def test_rerank_with_config_override(
        self, sample_chunks: list[RetrievedChunk], mock_reranker_impl: IReranker
    ):
        """Test that config override is applied."""
        service = RerankService(
            reranker=mock_reranker_impl,
            default_config=RerankConfig(top_k=2),
        )

        result = await service.rerank(
            query="brave warrior",
            chunks=sample_chunks,
            config_override=RerankConfig(top_k=4),
        )

        # Config override should take precedence
        assert result.total_output == 4

    @pytest.mark.asyncio
    async def test_rerank_disabled_returns_original(
        self, sample_chunks: list[RetrievedChunk]
    ):
        """Test that disabled reranking returns original chunks."""
        service = RerankService(
            reranker=None,  # No reranker
            default_config=RerankConfig(enabled=False),
        )

        result = await service.rerank(
            query="brave warrior",
            chunks=sample_chunks,
        )

        assert result.reranked is False
        assert result.model == "original"
        assert len(result.chunks) == len(sample_chunks)
        # Order should be preserved
        assert result.chunks[0].chunk_id == "chunk_1"
        assert result.chunks[4].chunk_id == "chunk_5"

    @pytest.mark.asyncio
    async def test_rerank_with_no_reranker_returns_original(
        self, sample_chunks: list[RetrievedChunk]
    ):
        """Test that no reranker returns original chunks."""
        service = RerankService(reranker=None)

        result = await service.rerank(
            query="brave warrior",
            chunks=sample_chunks,
        )

        assert result.reranked is False
        assert result.model == "original"
        assert len(result.chunks) == DEFAULT_TOP_K  # Should apply default top_k

    @pytest.mark.asyncio
    async def test_rerank_empty_query_returns_original(
        self, sample_chunks: list[RetrievedChunk]
    ):
        """Test that empty query returns original chunks."""
        service = RerankService(reranker=MagicMock())

        result = await service.rerank(
            query="",
            chunks=sample_chunks,
        )

        assert result.reranked is False
        assert len(result.chunks) == len(sample_chunks)

    @pytest.mark.asyncio
    async def test_rerank_empty_chunks(self, mock_reranker_impl: IReranker):
        """Test that empty chunks list returns empty result."""
        service = RerankService(reranker=mock_reranker_impl)

        result = await service.rerank(
            query="brave warrior",
            chunks=[],
        )

        assert result.total_input == 0
        assert result.total_output == 0
        assert len(result.chunks) == 0

    @pytest.mark.asyncio
    async def test_rerank_with_top_k_limit(
        self, sample_chunks: list[RetrievedChunk], mock_reranker_impl: IReranker
    ):
        """Test that top_k limits output."""
        service = RerankService(reranker=mock_reranker_impl)

        result = await service.rerank(
            query="brave warrior",
            chunks=sample_chunks,
            top_k=2,
        )

        assert result.total_output == 2
        assert len(result.chunks) == 2

    @pytest.mark.asyncio
    async def test_rerank_fallback_on_error(self, sample_chunks: list[RetrievedChunk]):
        """Test that fallback returns original order on error."""
        failing_reranker = FailingReranker("API error")
        service = RerankService(
            reranker=failing_reranker,
            default_config=RerankConfig(fallback_to_original=True),
        )

        result = await service.rerank(
            query="brave warrior",
            chunks=sample_chunks,
            top_k=3,
        )

        assert result.reranked is False
        assert result.error == "API error"
        assert result.model == "original"
        assert len(result.chunks) == 3
        # Order should be preserved
        assert result.chunks[0].chunk_id == "chunk_1"

    @pytest.mark.asyncio
    async def test_rerank_no_fallback_on_error(
        self, sample_chunks: list[RetrievedChunk]
    ):
        """Test that disabled fallback returns empty result on error."""
        failing_reranker = FailingReranker("API error")
        service = RerankService(
            reranker=failing_reranker,
            default_config=RerankConfig(fallback_to_original=False),
        )

        result = await service.rerank(
            query="brave warrior",
            chunks=sample_chunks,
        )

        assert result.reranked is False
        assert result.error == "API error"
        assert len(result.chunks) == 0

    @pytest.mark.asyncio
    async def test_rerank_min_score_threshold(
        self, sample_chunks: list[RetrievedChunk], mock_reranker_impl: IReranker
    ):
        """Test that minimum score threshold filters results."""
        service = RerankService(
            reranker=mock_reranker_impl,
            default_config=RerankConfig(min_score_threshold=0.70),
        )

        result = await service.rerank(
            query="brave warrior",
            chunks=sample_chunks,
        )

        # Only chunks with score >= 0.70 should be included
        # Mock adds 0.15 to scores, so original scores 0.55+ pass threshold
        # Reversed order: chunk_5 (0.45+0.15=0.60), chunk_4 (0.55+0.15=0.70), etc.
        assert all(c.score >= 0.70 for c in result.chunks)

    @pytest.mark.asyncio
    async def test_rerank_latency_tracking(
        self, sample_chunks: list[RetrievedChunk], mock_reranker_impl: IReranker
    ):
        """Test that reranking latency is tracked."""
        service = RerankService(reranker=mock_reranker_impl)

        result = await service.rerank(
            query="brave warrior",
            chunks=sample_chunks,
        )

        assert result.latency_ms > 0
        assert result.model == "test_model"


class TestMockReranker:
    """Tests for MockReranker."""

    @pytest.mark.asyncio
    async def test_mock_reranker_returns_results(self):
        """Test that MockReranker returns valid results."""
        reranker = MockReranker(latency_ms=10.0)

        documents = [
            RerankDocument(index=0, content="test content 1", score=0.7),
            RerankDocument(index=1, content="test content 2", score=0.6),
        ]

        output = await reranker.rerank(
            query="test query",
            documents=documents,
            top_k=2,
        )

        assert output.model == "mock"
        assert output.total_reranked == 2
        assert output.latency_ms == 10.0
        assert len(output.results) == 2

    @pytest.mark.asyncio
    async def test_mock_reranker_applies_top_k(self):
        """Test that MockReranker respects top_k parameter."""
        reranker = MockReranker()

        documents = [
            RerankDocument(index=i, content=f"content {i}", score=0.5 + i * 0.1)
            for i in range(5)
        ]

        output = await reranker.rerank(
            query="test query",
            documents=documents,
            top_k=3,
        )

        assert len(output.results) == 3


class TestFailingReranker:
    """Tests for FailingReranker."""

    @pytest.mark.asyncio
    async def test_failing_reranker_raises_error(self):
        """Test that FailingReranker always raises RerankerError."""
        reranker = FailingReranker("Test failure")

        documents = [
            RerankDocument(index=0, content="test content", score=0.7),
        ]

        with pytest.raises(RerankerError, match="Test failure"):
            await reranker.rerank(
                query="test query",
                documents=documents,
            )


class TestRerankConfig:
    """Tests for RerankConfig value object."""

    def test_rerank_config_defaults(self):
        """Test default values of RerankConfig."""
        config = RerankConfig()

        assert config.top_k == DEFAULT_TOP_K
        assert config.enabled is True
        assert config.fallback_to_original is True
        assert config.min_score_threshold == 0.0

    def test_rerank_config_custom_values(self):
        """Test custom values in RerankConfig."""
        config = RerankConfig(
            top_k=10,
            enabled=False,
            fallback_to_original=False,
            min_score_threshold=0.5,
        )

        assert config.top_k == 10
        assert config.enabled is False
        assert config.fallback_to_original is False
        assert config.min_score_threshold == 0.5

    def test_rerank_config_frozen(self):
        """Test that RerankConfig is frozen."""
        from dataclasses import FrozenInstanceError

        config = RerankConfig()

        with pytest.raises(FrozenInstanceError):
            config.top_k = 10


class TestRerankServiceResult:
    """Tests for RerankServiceResult value object."""

    def test_rerank_service_result_creation(self):
        """Test creating RerankServiceResult."""
        result = RerankServiceResult(
            chunks=[],
            query="test",
            total_input=5,
            total_output=3,
            reranked=True,
            model="test_model",
            latency_ms=50.0,
            error=None,
        )

        assert result.query == "test"
        assert result.total_input == 5
        assert result.total_output == 3
        assert result.reranked is True
        assert result.model == "test_model"
        assert result.latency_ms == 50.0
        assert result.error is None
