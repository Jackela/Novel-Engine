"""
Tests for Reranker Adapters

Tests for CohereReranker and LocalReranker adapters implementing IReranker.

Warzone 4: AI Brain - BRAIN-010B
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.contexts.knowledge.application.ports.i_reranker import (
    RerankDocument,
    RerankerError,
)
from src.contexts.knowledge.infrastructure.adapters.reranker_adapters import (
    DEFAULT_COHERE_MODEL,
    DEFAULT_LOCAL_MODEL,
    CohereReranker,
    LocalReranker,
    NoOpReranker,
)

# Check if sentence-transformers is available for conditional test skipping
try:
    import sentence_transformers  # noqa: F401

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# ===== NoOpReranker Tests =====


pytestmark = pytest.mark.unit


class TestNoOpReranker:
    """Tests for NoOpReranker."""

    @pytest.mark.asyncio
    async def test_rerank_returns_original_order(self):
        """Test that NoOpReranker preserves original order."""
        reranker = NoOpReranker()

        documents = [
            RerankDocument(index=0, content="first", score=0.5),
            RerankDocument(index=1, content="second", score=0.7),
            RerankDocument(index=2, content="third", score=0.3),
        ]

        output = await reranker.rerank("test query", documents)

        assert output.model == "noop"
        assert output.total_reranked == 3
        assert output.latency_ms == 0.0
        assert output.score_improvement == 0.0
        assert len(output.results) == 3
        assert output.results[0].index == 0
        assert output.results[1].index == 1
        assert output.results[2].index == 2
        assert output.results[0].relevance_score == 0.5
        assert output.results[1].relevance_score == 0.7
        assert output.results[2].relevance_score == 0.3

    @pytest.mark.asyncio
    async def test_rerank_with_top_k(self):
        """Test that NoOpReranker respects top_k parameter."""
        reranker = NoOpReranker()

        documents = [
            RerankDocument(index=0, content="first", score=0.5),
            RerankDocument(index=1, content="second", score=0.7),
            RerankDocument(index=2, content="third", score=0.3),
        ]

        output = await reranker.rerank("test query", documents, top_k=2)

        assert len(output.results) == 2
        assert output.results[0].index == 0
        assert output.results[1].index == 1

    @pytest.mark.asyncio
    async def test_rerank_with_latency(self):
        """Test that NoOpReranker simulates latency."""
        import asyncio

        reranker = NoOpReranker(latency_ms=100.0)

        documents = [RerankDocument(index=0, content="test", score=0.5)]

        start = asyncio.get_event_loop().time()
        output = await reranker.rerank("test query", documents)
        elapsed = asyncio.get_event_loop().time() - start

        assert output.latency_ms == 100.0
        assert elapsed >= 0.05  # At least 50ms actual delay

    @pytest.mark.asyncio
    async def test_rerank_empty_documents(self):
        """Test NoOpReranker with empty document list."""
        reranker = NoOpReranker()

        output = await reranker.rerank("test query", [])

        assert output.total_reranked == 0
        assert len(output.results) == 0


# ===== CohereReranker Tests =====


class TestCohereReranker:
    """Tests for CohereReranker."""

    def test_init_requires_api_key(self):
        """Test that CohereReranker raises ValueError without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="COHERE_API_KEY"):
                CohereReranker()

    def test_init_with_api_key_parameter(self):
        """Test that CohereReranker accepts API key via parameter."""
        with patch.dict("os.environ", {}, clear=True):
            reranker = CohereReranker(api_key="test-key")
            assert reranker._api_key == "test-key"

    def test_init_with_env_var(self):
        """Test that CohereReranker reads API key from environment."""
        with patch.dict("os.environ", {"COHERE_API_KEY": "env-key"}):
            reranker = CohereReranker()
            assert reranker._api_key == "env-key"

    def test_init_custom_model(self):
        """Test that CohereReranker accepts custom model name."""
        with patch.dict("os.environ", {"COHERE_API_KEY": "test-key"}):
            reranker = CohereReranker(model="custom-model")
            assert reranker._model == "custom-model"

    def test_init_default_model(self):
        """Test that CohereReranker uses default model."""
        with patch.dict("os.environ", {"COHERE_API_KEY": "test-key"}):
            reranker = CohereReranker()
            assert reranker._model == DEFAULT_COHERE_MODEL

    @pytest.mark.asyncio
    async def test_rerank_success(self):
        """Test successful Cohere reranking."""
        mock_response = {
            "results": [
                {"index": 1, "relevance_score": 0.95},
                {"index": 0, "relevance_score": 0.75},
                {"index": 2, "relevance_score": 0.60},
            ]
        }

        documents = [
            RerankDocument(index=0, content="brave knight", score=0.5),
            RerankDocument(index=1, content="brave warrior fights", score=0.6),
            RerankDocument(index=2, content="sad princess", score=0.4),
        ]

        with patch.dict("os.environ", {"COHERE_API_KEY": "test-key"}):
            reranker = CohereReranker()

            with patch.object(
                reranker,
                "_make_request",
                new=AsyncMock(return_value=mock_response),
            ):
                output = await reranker.rerank("brave knight", documents)

        assert output.model == DEFAULT_COHERE_MODEL
        assert output.total_reranked == 3
        assert len(output.results) == 3
        # Results should be reranked by Cohere scores
        assert output.results[0].index == 1
        assert output.results[0].relevance_score == 0.95
        assert output.results[1].index == 0
        assert output.results[1].relevance_score == 0.75
        assert output.results[2].index == 2
        assert output.results[2].relevance_score == 0.60
        assert output.latency_ms > 0
        assert output.score_improvement >= 0

    @pytest.mark.asyncio
    async def test_rerank_with_top_k(self):
        """Test that CohereReranker respects top_k parameter."""
        mock_response = {
            "results": [
                {"index": 1, "relevance_score": 0.95},
                {"index": 0, "relevance_score": 0.75},
                {"index": 2, "relevance_score": 0.60},
            ]
        }

        documents = [
            RerankDocument(index=0, content="brave knight", score=0.5),
            RerankDocument(index=1, content="brave warrior", score=0.6),
            RerankDocument(index=2, content="sad princess", score=0.4),
        ]

        with patch.dict("os.environ", {"COHERE_API_KEY": "test-key"}):
            reranker = CohereReranker()

            with patch.object(
                reranker,
                "_make_request",
                new=AsyncMock(return_value=mock_response),
            ):
                output = await reranker.rerank("brave knight", documents, top_k=2)

        assert len(output.results) == 2
        assert output.results[0].index == 1
        assert output.results[1].index == 0

    @pytest.mark.asyncio
    async def test_rerank_empty_documents(self):
        """Test CohereReranker with empty document list."""
        with patch.dict("os.environ", {"COHERE_API_KEY": "test-key"}):
            reranker = CohereReranker()

        # Empty documents should return early without making API call
        output = await reranker.rerank("test query", [])

        assert output.total_reranked == 0
        assert len(output.results) == 0
        assert output.latency_ms == 0.0

    @pytest.mark.asyncio
    async def test_rerank_401_error(self):
        """Test that CohereReranker handles 401 authentication errors."""
        documents = [RerankDocument(index=0, content="test", score=0.5)]

        with patch.dict("os.environ", {"COHERE_API_KEY": "test-key"}):
            reranker = CohereReranker()

            # Mock _make_request to raise RerankerError with auth message
            async def mock_request(request_body):
                from src.contexts.knowledge.application.ports.i_reranker import (
                    RerankerError,
                )

                raise RerankerError(
                    "Cohere API authentication failed - check COHERE_API_KEY"
                )

            with patch.object(reranker, "_make_request", new=mock_request):
                with pytest.raises(RerankerError, match="authentication failed"):
                    await reranker.rerank("test", documents)

    @pytest.mark.asyncio
    async def test_rerank_429_error(self):
        """Test that CohereReranker handles 429 rate limit errors."""
        documents = [RerankDocument(index=0, content="test", score=0.5)]

        with patch.dict("os.environ", {"COHERE_API_KEY": "test-key"}):
            reranker = CohereReranker()

            # Mock _make_request to raise RerankerError with rate limit message
            async def mock_request(request_body):
                from src.contexts.knowledge.application.ports.i_reranker import (
                    RerankerError,
                )

                raise RerankerError("Cohere API rate limit exceeded")

            with patch.object(reranker, "_make_request", new=mock_request):
                with pytest.raises(RerankerError, match="rate limit"):
                    await reranker.rerank("test", documents)

    @pytest.mark.asyncio
    async def test_rerank_invalid_response_structure(self):
        """Test that CohereReranker handles invalid response structure."""
        mock_response = {}  # Missing 'results' key

        documents = [RerankDocument(index=0, content="test", score=0.5)]

        with patch.dict("os.environ", {"COHERE_API_KEY": "test-key"}):
            reranker = CohereReranker()

            with patch.object(
                reranker,
                "_make_request",
                new=AsyncMock(return_value=mock_response),
            ):
                with pytest.raises(RerankerError, match="Invalid Cohere response"):
                    await reranker.rerank("test", documents)

    @pytest.mark.asyncio
    async def test_make_request_includes_headers(self):
        """Test that _make_request includes proper headers."""
        with patch.dict("os.environ", {"COHERE_API_KEY": "test-key"}):
            reranker = CohereReranker()

            request_body = {
                "query": "test",
                "documents": ["doc1"],
                "top_n": 5,
                "model": reranker._model,
            }

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"results": []}

            with patch("httpx.AsyncClient") as mock_client:
                mock_post = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value.post = mock_post

                await reranker._make_request(request_body)

                call_kwargs = mock_post.call_args.kwargs
                assert "Authorization" in call_kwargs["headers"]
                assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"
                assert call_kwargs["headers"]["Content-Type"] == "application/json"


# ===== LocalReranker Tests =====


class TestLocalReranker:
    """Tests for LocalReranker."""

    def test_init_default_values(self):
        """Test that LocalReranker uses default configuration."""
        reranker = LocalReranker()
        assert reranker._model_name == DEFAULT_LOCAL_MODEL
        assert reranker._device == "cpu"
        assert reranker._model is None  # Lazy loaded

    def test_init_custom_model(self):
        """Test that LocalReranker accepts custom model."""
        reranker = LocalReranker(model="custom-model")
        assert reranker._model_name == "custom-model"

    def test_init_custom_device(self):
        """Test that LocalReranker accepts custom device."""
        reranker = LocalReranker(device="cuda")
        assert reranker._device == "cuda"

    def test_init_with_env_vars(self):
        """Test that LocalReranker reads from environment."""
        with patch.dict(
            "os.environ",
            {"LOCAL_RERANK_MODEL": "env-model", "LOCAL_RERANK_DEVICE": "cuda"},
        ):
            reranker = LocalReranker()
            assert reranker._model_name == "env-model"
            assert reranker._device == "cuda"

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        SENTENCE_TRANSFORMERS_AVAILABLE,
        reason="Test requires sentence-transformers to NOT be installed",
    )
    async def test_rerank_import_error_message(self):
        """Test that LocalReranker provides helpful error on import failure."""
        reranker = LocalReranker()

        with patch.dict("sys.modules", {"sentence_transformers": None}):
            # Force import to fail by removing the module from cache
            import sys

            sys.modules.pop("sentence_transformers", None)

            documents = [RerankDocument(index=0, content="test", score=0.5)]

            with pytest.raises(
                RerankerError, match="sentence-transformers package is required"
            ):
                await reranker.rerank("test", documents)

    @pytest.mark.asyncio
    async def test_rerank_empty_documents(self):
        """Test LocalReranker with empty document list."""
        reranker = LocalReranker()

        output = await reranker.rerank("test query", [])

        assert output.total_reranked == 0
        assert len(output.results) == 0
        assert output.latency_ms >= 0

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires sentence-transformers installation")
    async def test_rerank_with_mock_model(self):
        """Test LocalReranker with mocked model."""
        # This test requires sentence-transformers to be installed
        # Skip in CI unless package is available
        documents = [
            RerankDocument(index=0, content="brave knight", score=0.5),
            RerankDocument(index=1, content="brave warrior fights", score=0.6),
            RerankDocument(index=2, content="sad princess", score=0.4),
        ]

        reranker = LocalReranker()

        # Mock the model to avoid actual loading
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.1, 0.9, 0.3]
        reranker._model = mock_model

        output = await reranker.rerank("brave knight", documents)

        assert output.model == DEFAULT_LOCAL_MODEL
        assert output.total_reranked == 3
        assert len(output.results) == 3
        # Result with highest score (0.9) should be first
        assert output.results[0].index == 1
        assert output.latency_ms >= 0


# ===== Reranker Creation Factory Tests =====


class TestCreateReranker:
    """Tests for the create_reranker factory function."""

    def test_create_local_reranker(self):
        """Test creating a local reranker via factory."""
        from src.contexts.knowledge.application.services.rerank_service import (
            RerankerType,
            create_reranker,
        )

        reranker = create_reranker(RerankerType.LOCAL)
        assert reranker is not None
        assert reranker.__class__.__name__ == "LocalReranker"

    def test_create_noop_reranker(self):
        """Test creating a no-op reranker via factory."""
        from src.contexts.knowledge.application.services.rerank_service import (
            RerankerType,
            create_reranker,
        )

        reranker = create_reranker(RerankerType.NOOP)
        assert reranker is not None
        assert reranker.__class__.__name__ == "NoOpReranker"

    def test_create_mock_reranker(self):
        """Test creating a mock reranker via factory."""
        from src.contexts.knowledge.application.services.rerank_service import (
            RerankerType,
            create_reranker,
        )

        reranker = create_reranker(RerankerType.MOCK, latency_ms=100.0)
        assert reranker is not None
        assert reranker.__class__.__name__ == "MockReranker"

    def test_create_cohere_reranker(self):
        """Test creating a Cohere reranker via factory."""
        from src.contexts.knowledge.application.services.rerank_service import (
            RerankerType,
            create_reranker,
        )

        with patch.dict("os.environ", {"COHERE_API_KEY": "test-key"}):
            reranker = create_reranker(RerankerType.COHERE)
            assert reranker is not None
            assert reranker.__class__.__name__ == "CohereReranker"

    def test_create_invalid_type(self):
        """Test that factory raises ValueError for invalid type."""
        from src.contexts.knowledge.application.services.rerank_service import (
            create_reranker,
        )

        with pytest.raises(ValueError, match="Invalid reranker type"):
            create_reranker("invalid_type")

    def test_reranker_type_all_types(self):
        """Test that all_types returns expected types."""
        from src.contexts.knowledge.application.services.rerank_service import (
            RerankerType,
        )

        types = RerankerType.all_types()
        assert RerankerType.COHERE in types
        assert RerankerType.LOCAL in types
        assert RerankerType.MOCK in types
        assert RerankerType.NOOP in types

    def test_reranker_type_is_valid(self):
        """Test that is_valid correctly identifies valid types."""
        from src.contexts.knowledge.application.services.rerank_service import (
            RerankerType,
        )

        assert RerankerType.is_valid(RerankerType.COHERE) is True
        assert RerankerType.is_valid(RerankerType.LOCAL) is True
        assert RerankerType.is_valid("invalid") is False
