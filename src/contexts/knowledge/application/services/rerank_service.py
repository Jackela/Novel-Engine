"""
Rerank Service

Re-ranks retrieved search results based on query relevance.
Provides graceful fallback if reranking fails.

Constitution Compliance:
- Article II (Hexagonal): Application service coordinating domain and infrastructure
- Article V (SOLID): SRP - reranking only

Warzone 4: AI Brain - BRAIN-010A, BRAIN-010B
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import structlog

from ...application.ports.i_reranker import (
    IReranker,
    RerankDocument,
    RerankerError,
    RerankOutput,
)
from ...application.ports.i_reranker import RerankResult as PortRerankResult
from ..services.knowledge_ingestion_service import RetrievedChunk

logger = structlog.get_logger()


# Default number of results to return after reranking
DEFAULT_TOP_K = 5


@dataclass(frozen=True, slots=True)
class RerankConfig:
    """
    Configuration for reranking operations.

    Why frozen:
        Immutable snapshot ensures config doesn't change during reranking.

    Attributes:
        top_k: Number of top results to return (None for all)
        enabled: Whether reranking is enabled
        fallback_to_original: Whether to use original order on failure
        min_score_threshold: Minimum relevance score to include results
    """

    top_k: int | None = DEFAULT_TOP_K
    enabled: bool = True
    fallback_to_original: bool = True
    min_score_threshold: float = 0.0


@dataclass
class RerankServiceResult:
    """
    Result of a reranking operation.

    Attributes:
        chunks: Reranked list of RetrievedChunk
        query: Original query string
        total_input: Total number of input chunks
        total_output: Total number of output chunks
        reranked: Whether reranking was applied
        model: Model/algorithm used for reranking
        latency_ms: Reranking latency in milliseconds
        score_improvement: Average score improvement from reranking (0.0 - 1.0)
        error: Error message if reranking failed
    """

    chunks: list[RetrievedChunk]
    query: str
    total_input: int
    total_output: int
    reranked: bool
    model: str = "none"
    latency_ms: float = 0.0
    score_improvement: float = 0.0
    error: str | None = None


class RerankService:
    """
    Service for reranking retrieved chunks based on query relevance.

    Wraps an IReranker implementation and provides:
    - Fallback to original order if reranking fails
    - Configurable top-k selection
    - Minimum score threshold filtering
    - Latency tracking

    Constitution Compliance:
        - Article II (Hexagonal): Application service coordinating ports
        - Article V (SOLID): SRP - reranking only
        - Article III (TDD): Tested via mock ports

    Example:
        >>> service = RerankService(reranker=CohereReranker(...))
        >>> results = await service.rerank(
        ...     query="brave knight",
        ...     chunks=retrieved_chunks,
        ...     top_k=3,
        ... )
        >>> for chunk in results.chunks:
        ...     print(f"{chunk.score:.2f}: {chunk.content[:50]}...")
    """

    def __init__(
        self,
        reranker: IReranker | None = None,
        default_config: RerankConfig | None = None,
    ):
        """
        Initialize the rerank service.

        Args:
            reranker: Optional reranker implementation (no reranking if None)
            default_config: Default configuration for reranking
        """
        self._reranker = reranker
        self._default_config = default_config or RerankConfig()

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int | None = None,
        config_override: RerankConfig | None = None,
    ) -> RerankServiceResult:
        """
        Rerank chunks based on query relevance.

        Args:
            query: Search query text
            chunks: List of retrieved chunks to rerank
            top_k: Optional number of top results to return
            config_override: Optional configuration override

        Returns:
            RerankServiceResult with reranked chunks

        Example:
            >>> results = await service.rerank(
            ...     query="protagonist motivation",
            ...     chunks=retrieved_chunks,
            ...     top_k=5,
            ... )
        """
        # Determine configuration
        config = config_override or self._default_config
        target_top_k = top_k or config.top_k

        # Validate input
        if not query or not query.strip():
            logger.warning("rerank_empty_query", returning_original=True)
            return RerankServiceResult(
                chunks=chunks,
                query=query,
                total_input=len(chunks),
                total_output=len(chunks),
                reranked=False,
            )

        if not chunks:
            logger.debug("rerank_empty_chunks")
            return RerankServiceResult(
                chunks=[],
                query=query,
                total_input=0,
                total_output=0,
                reranked=False,
            )

        # Check if reranking is enabled and available
        if not config.enabled or self._reranker is None:
            logger.debug(
                "rerank_disabled",
                enabled=config.enabled,
                has_reranker=self._reranker is not None,
            )
            return self._return_original(chunks, query, target_top_k)

        # Convert chunks to RerankDocument format
        input_documents = [
            RerankDocument(
                index=i,
                content=chunk.content,
                score=chunk.score,
            )
            for i, chunk in enumerate(chunks)
        ]

        # Attempt reranking
        start_time = time.perf_counter()
        try:
            output = await self._reranker.rerank(
                query=query,
                documents=input_documents,
                top_k=target_top_k,
            )
            latency_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "rerank_complete",
                query=query,
                model=output.model,
                latency_ms=latency_ms,
                input_count=len(input_documents),
                output_count=len(output.results),
                score_improvement=output.score_improvement,
            )

            # Reorder chunks based on reranking results
            reranked_chunks = self._apply_reranking(
                chunks=chunks,
                rerank_output=output,
                min_score_threshold=config.min_score_threshold,
            )

            return RerankServiceResult(
                chunks=reranked_chunks,
                query=query,
                total_input=len(chunks),
                total_output=len(reranked_chunks),
                reranked=True,
                model=output.model,
                latency_ms=latency_ms,
                score_improvement=output.score_improvement,
            )

        except RerankerError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(
                "rerank_failed",
                query=query,
                error=str(e),
                latency_ms=latency_ms,
                fallback=config.fallback_to_original,
            )

            if config.fallback_to_original:
                return self._return_original(chunks, query, target_top_k, error=str(e))

            # Return empty result if fallback is disabled
            return RerankServiceResult(
                chunks=[],
                query=query,
                total_input=len(chunks),
                total_output=0,
                reranked=False,
                latency_ms=latency_ms,
                error=str(e),
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "rerank_unexpected_error",
                query=query,
                error=str(e),
                error_type=type(e).__name__,
                latency_ms=latency_ms,
            )

            if config.fallback_to_original:
                return self._return_original(chunks, query, target_top_k, error=str(e))

            return RerankServiceResult(
                chunks=[],
                query=query,
                total_input=len(chunks),
                total_output=0,
                reranked=False,
                latency_ms=latency_ms,
                error=str(e),
            )

    def _return_original(
        self,
        chunks: list[RetrievedChunk],
        query: str,
        top_k: int | None,
        error: str | None = None,
    ) -> RerankServiceResult:
        """
        Return chunks in original order.

        Args:
            chunks: Original chunks
            query: Query string
            top_k: Optional limit on number of results
            error: Optional error message

        Returns:
            RerankServiceResult with original order
        """
        output_chunks = chunks[:top_k] if top_k is not None else chunks

        return RerankServiceResult(
            chunks=output_chunks,
            query=query,
            total_input=len(chunks),
            total_output=len(output_chunks),
            reranked=False,
            model="original",
            error=error,
        )

    def _apply_reranking(
        self,
        chunks: list[RetrievedChunk],
        rerank_output: RerankOutput,
        min_score_threshold: float,
    ) -> list[RetrievedChunk]:
        """
        Apply reranking results to chunks.

        Args:
            chunks: Original chunks
            rerank_output: Reranking output
            min_score_threshold: Minimum relevance score

        Returns:
            Reordered and filtered chunks
        """
        reranked: list[RetrievedChunk] = []

        for result in rerank_output.results:
            # Apply minimum score threshold
            if result.relevance_score < min_score_threshold:
                continue

            # Get original chunk by index
            if 0 <= result.index < len(chunks):
                chunk = chunks[result.index]

                # Update score with reranked relevance score
                updated_chunk = RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    source_id=chunk.source_id,
                    source_type=chunk.source_type,
                    content=chunk.content,
                    score=result.relevance_score,  # Use reranked score
                    metadata=chunk.metadata,
                )
                reranked.append(updated_chunk)

        return reranked


# Mock implementation for testing
class MockReranker:
    """
    Mock reranker for testing.

    Implements IReranker protocol without calling external APIs.
    Returns results based on simple keyword matching in content.
    """

    def __init__(self, latency_ms: float = 50.0):
        """
        Initialize mock reranker.

        Args:
            latency_ms: Simulated latency in milliseconds
        """
        self._latency_ms = latency_ms
        self._call_count = 0

    async def rerank(
        self,
        query: str,
        documents: list[RerankDocument],
        top_k: int | None = None,
    ) -> RerankOutput:
        """
        Mock reranking based on keyword presence in content.

        Args:
            query: Search query
            documents: Documents to rerank with content
            top_k: Optional top-k limit

        Returns:
            RerankOutput with reranked results
        """
        import asyncio

        self._call_count += 1

        # Simulate latency
        await asyncio.sleep(self._latency_ms / 1000.0)

        # Calculate average original score
        avg_original_score = (
            sum(d.score for d in documents) / len(documents) if documents else 0.0
        )

        # Score each document based on keyword matches in content
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored_results = []
        for doc in documents:
            content_lower = doc.content.lower()
            # Count how many query words appear in content
            matches = sum(1 for word in query_words if word in content_lower)
            # Boost score based on matches (max boost of 0.3)
            keyword_boost = (matches / len(query_words)) * 0.3 if query_words else 0
            new_score = min(doc.score + keyword_boost, 1.0)

            scored_results.append(
                PortRerankResult(
                    index=doc.index,
                    score=new_score,
                    relevance_score=new_score,
                )
            )

        # Sort by relevance score
        scored_results.sort(key=lambda r: r.relevance_score, reverse=True)

        # Apply top_k
        if top_k is not None:
            scored_results = scored_results[:top_k]

        # Calculate score improvement
        avg_new_score = (
            sum(r.relevance_score for r in scored_results) / len(scored_results)
            if scored_results
            else 0.0
        )
        score_improvement = max(0.0, avg_new_score - avg_original_score)

        return RerankOutput(
            results=scored_results,
            query=query,
            total_reranked=len(documents),
            model="mock",
            latency_ms=self._latency_ms,
            score_improvement=score_improvement,
        )


class FailingReranker:
    """
    Mock reranker that always fails.

    Useful for testing fallback behavior.
    """

    def __init__(self, error_message: str = "Reranking failed"):
        """
        Initialize failing reranker.

        Args:
            error_message: Error message to raise
        """
        self._error_message = error_message

    async def rerank(
        self,
        query: str,
        documents: list[RerankDocument],
        top_k: int | None = None,
    ) -> RerankOutput:
        """Always raise a RerankerError."""
        raise RerankerError(self._error_message)


__all__ = [
    "RerankService",
    "RerankConfig",
    "RerankServiceResult",
    "MockReranker",
    "FailingReranker",
    "DEFAULT_TOP_K",
    "RerankerType",
    "create_reranker",
]


# Reranker type enumeration
class RerankerType:
    """
    Enumeration of available reranker types.

    Attributes:
        COHERE: Cohere API-based reranker (requires API key)
        LOCAL: Local sentence-transformers reranker
        MOCK: Mock reranker for testing
        NOOP: No-op reranker that preserves original order
    """

    COHERE = "cohere"
    LOCAL = "local"
    MOCK = "mock"
    NOOP = "noop"

    @classmethod
    def all_types(cls) -> list[str]:
        """Get all available reranker types."""
        return [cls.COHERE, cls.LOCAL, cls.MOCK, cls.NOOP]

    @classmethod
    def is_valid(cls, reranker_type: str) -> bool:
        """Check if a reranker type is valid."""
        return reranker_type in cls.all_types()


def create_reranker(
    reranker_type: str = RerankerType.LOCAL,
    **kwargs: Any,
) -> IReranker | None:
    """
    Factory function to create a reranker instance.

    Args:
        reranker_type: Type of reranker to create (default: local)
        **kwargs: Additional arguments passed to reranker constructor
            - For COHERE: api_key, model, base_url
            - For LOCAL: model, device, cache_dir
            - For MOCK: latency_ms
            - For NOOP: latency_ms

    Returns:
        IReranker instance or None if type is invalid

    Raises:
        ValueError: If reranker_type is not valid

    Example:
        >>> # Create local reranker
        >>> reranker = create_reranker("local", model="ms-marco-MiniLM-L-6-v2")
        >>> # Create Cohere reranker
        >>> reranker = create_reranker("cohere", api_key="...")
        >>> # Create mock reranker for testing
        >>> reranker = create_reranker("mock")
    """
    if not RerankerType.is_valid(reranker_type):
        raise ValueError(
            f"Invalid reranker type: {reranker_type}. "
            f"Must be one of: {RerankerType.all_types()}"
        )

    # Lazy import to avoid circular dependencies
    from ...infrastructure.adapters.reranker_adapters import (
        CohereReranker,
        LocalReranker,
        NoOpReranker,
    )

    if reranker_type == RerankerType.COHERE:
        return CohereReranker(**kwargs)
    elif reranker_type == RerankerType.LOCAL:
        return LocalReranker(**kwargs)
    elif reranker_type == RerankerType.MOCK:
        return MockReranker(**kwargs)
    elif reranker_type == RerankerType.NOOP:
        return NoOpReranker(**kwargs)

    return None
