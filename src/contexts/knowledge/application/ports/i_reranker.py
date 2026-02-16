"""
Reranker Port

Protocol for re-ranking retrieved search results based on query relevance.
Provides a unified interface for different reranking implementations (Cohere, local, etc.).

Constitution Compliance:
- Article II (Hexagonal): Application port defining reranking contract
- Article V (SOLID): Dependency Inversion - services depend on this abstraction

Warzone 4: AI Brain - BRAIN-010A, BRAIN-010B
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RerankDocument:
    """
    Document to be reranked.

    Why frozen:
        Immutable snapshot ensures document doesn't change during reranking.

    Attributes:
        index: Original index in the input results list
        content: Document text content for relevance scoring
        score: Original relevance score from initial retrieval
    """

    index: int
    content: str
    score: float


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
        score_improvement: Average score improvement from reranking (0.0 - 1.0)
    """

    results: list[RerankResult]
    query: str
    total_reranked: int
    model: str
    latency_ms: float
    score_improvement: float = 0.0


class RerankerError(Exception):
    """Base exception for reranker-related errors."""


class IReranker(Protocol):
    """
    Protocol for reranker implementations.

    Defines the interface for re-ranking search results based on query relevance.
    Implementations can wrap Cohere API, local sentence-transformers, or other providers.

    Example:
        >>> reranker = CohereReranker(api_key="...")
        >>> documents = [
        ...     RerankDocument(index=0, content="brave knight fights", score=0.7),
        ...     RerankDocument(index=1, content="sad princess cries", score=0.6),
        ... ]
        >>> output = await reranker.rerank(
        ...     query="brave knight",
        ...     documents=documents,
        ...     top_k=3,
        ... )
        >>> # Reorder results based on output.results
    """

    async def rerank(
        self,
        query: str,
        documents: list[RerankDocument],
        top_k: int | None = None,
    ) -> RerankOutput:
        """
        Rerank documents based on query relevance.

        Args:
            query: Search query text
            documents: List of RerankDocument with index, content, and original scores
            top_k: Optional number of top results to return (returns all if None)

        Returns:
            RerankOutput with reranked results sorted by relevance

        Raises:
            RerankerError: If reranking fails
        """
        raise NotImplementedError("IReranker implementations must define `rerank`.")
