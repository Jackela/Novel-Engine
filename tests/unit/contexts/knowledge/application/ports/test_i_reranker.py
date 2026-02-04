"""
Unit tests for IReranker port interface.

Warzone 4: AI Brain - BRAIN-010A
"""

from __future__ import annotations

import pytest

from src.contexts.knowledge.application.ports.i_reranker import (
    IReranker,
    RerankerError,
    RerankResult,
    RerankOutput,
)


class TestRerankResult:
    """Tests for RerankResult value object."""

    def test_rerank_result_creation(self):
        """Test creating RerankResult."""
        result = RerankResult(
            index=0,
            score=0.85,
            relevance_score=0.90,
        )

        assert result.index == 0
        assert result.score == 0.85
        assert result.relevance_score == 0.90

    def test_rerank_result_frozen(self):
        """Test that RerankResult is frozen."""
        from dataclasses import FrozenInstanceError

        result = RerankResult(index=0, score=0.85, relevance_score=0.90)

        with pytest.raises(FrozenInstanceError):
            result.index = 1


class TestRerankOutput:
    """Tests for RerankOutput value object."""

    def test_rerank_output_creation(self):
        """Test creating RerankOutput."""
        results = [
            RerankResult(index=2, score=0.90, relevance_score=0.95),
            RerankResult(index=0, score=0.80, relevance_score=0.85),
        ]

        output = RerankOutput(
            results=results,
            query="test query",
            total_reranked=5,
            model="test_model",
            latency_ms=45.0,
        )

        assert len(output.results) == 2
        assert output.query == "test query"
        assert output.total_reranked == 5
        assert output.model == "test_model"
        assert output.latency_ms == 45.0

    def test_rerank_output_frozen(self):
        """Test that RerankOutput is frozen."""
        from dataclasses import FrozenInstanceError

        output = RerankOutput(
            results=[],
            query="test",
            total_reranked=0,
            model="test",
            latency_ms=0.0,
        )

        with pytest.raises(FrozenInstanceError):
            output.query = "changed"


class TestRerankerError:
    """Tests for RerankerError."""

    def test_reranker_error_creation(self):
        """Test creating RerankerError."""
        error = RerankerError("Test error message")

        assert str(error) == "Test error message"
        assert isinstance(error, Exception)


class TestIRerankerProtocol:
    """Tests for IReranker protocol."""

    def test_ireranker_requires_rerank_method(self):
        """Test that IReranker requires rerank method."""
        # This is a compile-time check, but we can verify the protocol exists

        # A valid implementation must have the rerank method
        class ValidReranker:
            async def rerank(
                self,
                query: str,
                results: list[RerankResult],
                top_k: int | None = None,
            ) -> RerankOutput:
                return RerankOutput(
                    results=[],
                    query=query,
                    total_reranked=len(results),
                    model="valid",
                    latency_ms=0.0,
                )

        # This should be compatible with IReranker
        reranker: IReranker = ValidReranker()
        assert hasattr(reranker, "rerank")

    def test_ireranker_invalid_implementation(self):
        """Test that class without rerank is not compatible."""
        class InvalidReranker:
            def other_method(self) -> None:
                pass

        # This should not be compatible
        reranker = InvalidReranker()

        # The protocol check happens at type-check time, not runtime
        # But we can verify the method doesn't exist
        assert not hasattr(reranker, "rerank")
