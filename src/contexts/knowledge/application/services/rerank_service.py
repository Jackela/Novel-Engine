"""
Rerank Service

Service for reranking retrieved results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RerankResult:
    """Result of reranking."""

    id: str
    score: float
    text: str
    metadata: dict[str, Any]


class MockReranker:
    """Mock reranker for testing."""

    def __init__(self, latency_ms: float = 0.0):
        self.latency_ms = latency_ms

    async def rerank(
        self, query: str, results: list[dict[str, Any]]
    ) -> list[RerankResult]:
        """Rerank results."""
        return [
            RerankResult(
                id=r.get("id", ""),
                score=r.get("score", 0.0),
                text=r.get("text", ""),
                metadata=r.get("metadata", {}),
            )
            for r in results
        ]


class RerankService:
    """Service for reranking results."""

    def __init__(self, reranker: MockReranker | None = None):
        self.reranker = reranker or MockReranker()

    async def rerank(
        self, query: str, results: list[dict[str, Any]]
    ) -> list[RerankResult]:
        """Rerank results."""
        return await self.reranker.rerank(query, results)
