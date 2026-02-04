"""
Rerank Service

Re-ranks retrieved search results based on query relevance.
Provides graceful fallback if reranking fails.

Constitution Compliance:
- Article II (Hexagonal): Application service coordinating domain and infrastructure
- Article V (SOLID): SRP - reranking only

Warzone 4: AI Brain - BRAIN-010A
"""

from __future__ import annotations

from dataclasses import dataclass
import time

import structlog

from ...application.ports.i_reranker import (
    IReranker,
    RerankerError,
    RerankOutput,
    RerankResult as PortRerankResult,
)
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
        error: Error message if reranking failed
    """

    chunks: list[RetrievedChunk]
    query: str
    total_input: int
    total_output: int
    reranked: bool
    model: str = "none"
    latency_ms: float = 0.0
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

        # Convert chunks to RerankResult format
        input_results = [
            PortRerankResult(
                index=i,
                score=chunk.score,
                relevance_score=chunk.score,  # Use original score as relevance
            )
            for i, chunk in enumerate(chunks)
        ]

        # Attempt reranking
        start_time = time.perf_counter()
        try:
            output = await self._reranker.rerank(
                query=query,
                results=input_results,
                top_k=target_top_k,
            )
            latency_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "rerank_complete",
                query=query,
                model=output.model,
                latency_ms=latency_ms,
                input_count=len(input_results),
                output_count=len(output.results),
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
    Returns results based on simple keyword matching.
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
        results: list[PortRerankResult],
        top_k: int | None = None,
    ) -> RerankOutput:
        """
        Mock reranking based on keyword presence.

        Args:
            query: Search query
            results: Results to rerank
            top_k: Optional top-k limit

        Returns:
            RerankOutput with reranked results
        """
        import asyncio

        self._call_count += 1

        # Simulate latency
        await asyncio.sleep(self._latency_ms / 1000.0)

        # Score each result based on keyword matches
        scored_results = []
        for i, result in enumerate(results):
            # In a real mock, we'd need access to chunk content
            # For now, just use the original score
            scored_results.append(
                PortRerankResult(
                    index=result.index,
                    score=result.score,
                    relevance_score=min(result.score + 0.1, 1.0),  # Slight boost
                )
            )

        # Sort by relevance score
        scored_results.sort(key=lambda r: r.relevance_score, reverse=True)

        # Apply top_k
        if top_k is not None:
            scored_results = scored_results[:top_k]

        return RerankOutput(
            results=scored_results,
            query=query,
            total_reranked=len(results),
            model="mock",
            latency_ms=self._latency_ms,
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
        results: list[PortRerankResult],
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
]
