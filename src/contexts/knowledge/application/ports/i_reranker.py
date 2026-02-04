"""
Reranker Port

Protocol for re-ranking retrieved search results based on query relevance.
Provides a unified interface for different reranking implementations (Cohere, local, etc.).

Constitution Compliance:
- Article II (Hexagonal): Application port defining reranking contract
- Article V (SOLID): Dependency Inversion - services depend on this abstraction

Warzone 4: AI Brain - BRAIN-010A
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RerankResult:
    """
    Result of reranking a single document.

    Why frozen:
        Immutable snapshot ensures reranking results don't change during processing.

    Attributes:
        index: Original index in the input results list
        score: Reranking relevance score (higher = more relevant)
        relevance_score: Normalized relevance score (0.0 - 1.0)
    """

    index: int
    score: float
    relevance_score: float


@dataclass(frozen=True, slots=True)
class RerankOutput:
    """
    Output of the reranking process.

    Attributes:
        results: List of RerankResult, sorted by relevance (highest first)
        query: Original query string
        total_reranked: Total number of results reranked
        model: Model/algorithm used for reranking
        latency_ms: Reranking latency in milliseconds
    """

    results: list[RerankResult]
    query: str
    total_reranked: int
    model: str
    latency_ms: float


class RerankerError(Exception):
    """Base exception for reranker-related errors."""

    pass


class IReranker(Protocol):
    """
    Protocol for reranker implementations.

    Defines the interface for re-ranking search results based on query relevance.
    Implementations can wrap Cohere API, local sentence-transformers, or other providers.

    Example:
        >>> reranker = CohereReranker(api_key="...")
        >>> results = [
        ...     RetrievedChunk(content="...", score=0.7, ...),
        ...     RetrievedChunk(content="...", score=0.6, ...),
        ... ]
        >>> output = await reranker.rerank(
        ...     query="brave knight",
        ...     results=results,
        ...     top_k=3,
        ... )
        >>> # Reorder results based on output.results
    """

    async def rerank(
        self,
        query: str,
        results: list[RerankResult],
        top_k: int | None = None,
    ) -> RerankOutput:
        """
        Rerank results based on query relevance.

        Args:
            query: Search query text
            results: List of RerankResult with original indices and scores
            top_k: Optional number of top results to return (returns all if None)

        Returns:
            RerankOutput with reranked results sorted by relevance

        Raises:
            RerankerError: If reranking fails
        """
        raise NotImplementedError("IReranker implementations must define `rerank`.")
