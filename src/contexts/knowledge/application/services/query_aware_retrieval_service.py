"""
Query-Aware Retrieval Service

Integrates QueryRewriter with RetrievalService to execute retrieval for all
query variants and merge results for better RAG performance.

Constitution Compliance:
- Article II (Hexagonal): Application service using ports
- Article V (SOLID): SRP - multi-query retrieval orchestration only

Warzone 4: AI Brain - BRAIN-009B
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

from ...application.ports.i_embedding_service import IEmbeddingService
from ...application.ports.i_vector_store import IVectorStore
from .retrieval_service import (
    RetrievalService,
    RetrievalFilter,
    RetrievalOptions,
    FormattedContext,
)
from .knowledge_ingestion_service import RetrievedChunk
from .query_rewriter import (
    QueryRewriter,
    RewriteConfig,
    RewriteStrategy,
    RewriteResult,
)

if TYPE_CHECKING:
    pass


logger = structlog.get_logger()


# Default collection name
DEFAULT_COLLECTION = "knowledge"

# Default max concurrent queries
DEFAULT_MAX_CONCURRENT = 3


@dataclass(frozen=True, slots=True)
class QueryAwareConfig:
    """
    Configuration for query-aware retrieval.

    Attributes:
        enable_rewriting: Whether to use query rewriting
        rewrite_strategy: Strategy for query rewriting
        max_variants: Maximum query variants to generate
        merge_strategy: How to merge results from multiple queries
        max_concurrent: Maximum concurrent retrieval queries
        deduplicate_results: Whether to deduplicate results across queries
    """

    enable_rewriting: bool = True
    rewrite_strategy: RewriteStrategy = RewriteStrategy.HYBRID
    max_variants: int = 3
    merge_strategy: str = "rrf"  # "rrf" (reciprocal rank fusion) or "score"
    max_concurrent: int = DEFAULT_MAX_CONCURRENT
    deduplicate_results: bool = True


@dataclass
class QueryAwareRetrievalResult:
    """
    Result of query-aware retrieval.

    Attributes:
        chunks: Merged list of retrieved chunks
        original_query: The original input query
        queries_executed: List of queries that were executed
        total_retrieved: Total chunks retrieved across all queries
        deduplicated: Chunks removed by deduplication
        rewrite_result: QueryRewriter result if rewriting was used
        tokens_used: Total tokens used for query rewriting
    """

    chunks: list[RetrievedChunk]
    original_query: str
    queries_executed: list[str]
    total_retrieved: int
    deduplicated: int = 0
    rewrite_result: RewriteResult | None = None
    tokens_used: int = 0


@dataclass
class QueryAwareMetrics:
    """
    Metrics tracking for query-aware retrieval.

    Attributes:
        queries_total: Total number of queries processed
        rewrites_total: Total number of query rewrites
        cache_hits_total: Total cache hits
        tokens_used_total: Total tokens used
        tokens_saved_total: Total tokens saved by caching
        merged_results_total: Total merged results
    """

    queries_total: int = 0
    rewrites_total: int = 0
    cache_hits_total: int = 0
    tokens_used_total: int = 0
    tokens_saved_total: int = 0
    merged_results_total: int = 0


class QueryAwareRetrievalService:
    """
    Service for query-aware retrieval using multiple query variants.

    Enhances RAG retrieval by:
    1. Rewriting queries into multiple variants
    2. Executing retrieval for all variants concurrently
    3. Merging results using Reciprocal Rank Fusion (RRF) or score-based merging

    Constitution Compliance:
        - Article II (Hexarchical): Application service using ports
        - Article V (SOLID): SRP - multi-query retrieval orchestration only

    Example:
        >>> service = QueryAwareRetrievalService(
        ...     embedding_service=embedding_svc,
        ...     vector_store=vector_store,
        ...     query_rewriter=rewriter,
        ... )
        >>> result = await service.retrieve_relevant("protagonist motivation", k=5)
        >>> print(f"Executed {len(result.queries_executed)} queries")
        >>> for chunk in result.chunks:
        ...     print(f"{chunk.source_id}: {chunk.score:.2f}")
    """

    def __init__(
        self,
        embedding_service: IEmbeddingService,
        vector_store: IVectorStore,
        default_collection: str = DEFAULT_COLLECTION,
        query_rewriter: QueryRewriter | None = None,
        default_config: QueryAwareConfig | None = None,
    ):
        """
        Initialize the query-aware retrieval service.

        Args:
            embedding_service: Service for generating query embeddings
            vector_store: Vector storage backend for semantic search
            default_collection: Default collection name for queries
            query_rewriter: Optional query rewriter for multi-query expansion
            default_config: Default configuration for query-aware retrieval
        """
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._default_collection = default_collection
        self._query_rewriter = query_rewriter
        self._config = default_config or QueryAwareConfig()
        self._metrics = QueryAwareMetrics()

        # Create base retrieval service
        self._retrieval_service = RetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
            default_collection=default_collection,
        )

        logger.info(
            "query_aware_retrieval_service_initialized",
            rewriting_enabled=self._config.enable_rewriting,
            rewrite_strategy=self._config.rewrite_strategy.value if self._config.enable_rewriting else None,
            max_variants=self._config.max_variants,
        )

    async def retrieve_relevant(
        self,
        query: str,
        k: int = 5,
        filters: RetrievalFilter | None = None,
        options: RetrievalOptions | None = None,
        collection: str | None = None,
        config_override: QueryAwareConfig | None = None,
    ) -> QueryAwareRetrievalResult:
        """
        Retrieve relevant chunks using query-aware multi-query expansion.

        Args:
            query: Search query text
            k: Number of results to retrieve
            filters: Optional filters for source_type, tags, dates
            options: Optional retrieval options
            collection: Optional collection name
            config_override: Optional config override for this retrieval

        Returns:
            QueryAwareRetrievalResult with merged chunks

        Raises:
            ValueError: If query is empty

        Example:
            >>> result = await service.retrieve_relevant(
            ...     query="brave warrior",
            ...     k=5,
            ...     filters=RetrievalFilter(source_types=[SourceType.CHARACTER]),
            ... )
            >>> print(f"Retrieved {len(result.chunks)} chunks from {len(result.queries_executed)} queries")
        """
        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        config = config_override or self._config
        queries_to_execute: list[str] = [query]
        rewrite_result: RewriteResult | None = None

        # Step 1: Generate query variants if rewriting is enabled
        if config.enable_rewriting and self._query_rewriter:
            self._metrics.rewrites_total += 1

            rewrite_config = RewriteConfig(
                strategy=config.rewrite_strategy,
                max_variants=config.max_variants,
                include_original=True,
            )

            rewrite_result = await self._query_rewriter.rewrite(query, rewrite_config)
            queries_to_execute = rewrite_result.variants

            # Track metrics
            self._metrics.tokens_used_total += rewrite_result.tokens_used
            self._metrics.tokens_saved_total += rewrite_result.tokens_saved
            if rewrite_result.cached:
                self._metrics.cache_hits_total += 1

            logger.info(
                "query_aware_rewriting_complete",
                original_query=query,
                variant_count=len(queries_to_execute),
                cached=rewrite_result.cached,
                tokens_saved=rewrite_result.tokens_saved,
            )

        # Step 2: Execute retrieval for all queries concurrently
        self._metrics.queries_total += len(queries_to_execute)

        retrieval_options = options or RetrievalOptions(k=k)
        target_collection = collection or self._default_collection

        # Limit concurrent queries to avoid overwhelming the system
        chunks_by_query: list[tuple[str, list[RetrievedChunk]]] = []

        if len(queries_to_execute) == 1:
            # Single query - no need for concurrency control
            result = await self._retrieval_service.retrieve_relevant(
                query=queries_to_execute[0],
                k=k,
                filters=filters,
                options=retrieval_options,
                collection=target_collection,
            )
            chunks_by_query.append((queries_to_execute[0], result.chunks))
        else:
            # Multiple queries - use semaphore for concurrency control
            semaphore = asyncio.Semaphore(config.max_concurrent)

            async def retrieve_with_semaphore(q: str) -> tuple[str, list[RetrievedChunk]]:
                async with semaphore:
                    result = await self._retrieval_service.retrieve_relevant(
                        query=q,
                        k=k,
                        filters=filters,
                        options=retrieval_options,
                        collection=target_collection,
                    )
                    return (q, result.chunks)

            tasks = [retrieve_with_semaphore(q) for q in queries_to_execute]
            chunks_by_query = await asyncio.gather(*tasks)

        # Flatten results
        all_chunks: list[tuple[RetrievedChunk, int, int]] = []
        # Store (chunk, query_index, rank_in_query) for RRF
        for query_idx, (q, chunks) in enumerate(chunks_by_query):
            for rank, chunk in enumerate(chunks):
                all_chunks.append((chunk, query_idx, rank))

        total_retrieved = len(all_chunks)

        logger.info(
            "query_aware_multi_retrieval_complete",
            query=query,
            queries_executed=len(queries_to_execute),
            total_chunks=total_retrieved,
        )

        # Step 3: Merge and deduplicate results
        merged_chunks = self._merge_results(
            all_chunks=all_chunks,
            merge_strategy=config.merge_strategy,
            k=k,
        )

        # Deduplicate if enabled
        deduplicated_count = 0
        if config.deduplicate_results:
            merged_chunks_before = len(merged_chunks)
            merged_chunks = self._deduplicate_chunks(merged_chunks)
            deduplicated_count = merged_chunks_before - len(merged_chunks)

        self._metrics.merged_results_total += len(merged_chunks)

        logger.info(
            "query_aware_merge_complete",
            original_query=query,
            final_count=len(merged_chunks),
            deduplicated=deduplicated_count,
        )

        return QueryAwareRetrievalResult(
            chunks=merged_chunks[:k],
            original_query=query,
            queries_executed=queries_to_execute,
            total_retrieved=total_retrieved,
            deduplicated=deduplicated_count,
            rewrite_result=rewrite_result,
            tokens_used=rewrite_result.tokens_used if rewrite_result else 0,
        )

    def format_context(
        self,
        result: QueryAwareRetrievalResult,
        max_tokens: int | None = None,
        include_sources: bool = True,
    ) -> FormattedContext:
        """
        Convert query-aware retrieval result to formatted context.

        Args:
            result: QueryAwareRetrievalResult from retrieve_relevant
            max_tokens: Maximum tokens to include
            include_sources: Whether to include source citations

        Returns:
            FormattedContext with text, sources, and token count
        """
        # Use base retrieval service's format_context with a synthetic RetrievalResult
        from .retrieval_service import RetrievalResult

        synthetic_result = RetrievalResult(
            chunks=result.chunks,
            query=result.original_query,
            total_retrieved=result.total_retrieved,
            deduplicated=result.deduplicated,
        )

        return self._retrieval_service.format_context(
            synthetic_result,
            max_tokens=max_tokens,
            include_sources=include_sources,
        )

    def get_metrics(self) -> dict[str, Any]:
        """
        Get service metrics.

        Returns:
            Dict with metrics including cache efficiency
        """
        return {
            "queries_total": self._metrics.queries_total,
            "rewrites_total": self._metrics.rewrites_total,
            "cache_hits_total": self._metrics.cache_hits_total,
            "tokens_used_total": self._metrics.tokens_used_total,
            "tokens_saved_total": self._metrics.tokens_saved_total,
            "merged_results_total": self._metrics.merged_results_total,
            "cache_hit_rate": (
                self._metrics.cache_hits_total / self._metrics.rewrites_total
                if self._metrics.rewrites_total > 0
                else 0.0
            ),
        }

    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        self._metrics = QueryAwareMetrics()
        logger.debug("query_aware_metrics_reset")

    def _merge_results(
        self,
        all_chunks: list[tuple[RetrievedChunk, int, int]],
        merge_strategy: str,
        k: int,
    ) -> list[RetrievedChunk]:
        """
        Merge results from multiple queries.

        Args:
            all_chunks: List of (chunk, query_index, rank) tuples
            merge_strategy: "rrf" (reciprocal rank fusion) or "score"
            k: Target number of results

        Returns:
            Merged and sorted list of chunks
        """
        if not all_chunks:
            return []

        if merge_strategy == "rrf":
            return self._merge_rrf(all_chunks, k)
        else:  # score-based
            return self._merge_by_score(all_chunks, k)

    def _merge_rrf(
        self,
        all_chunks: list[tuple[RetrievedChunk, int, int]],
        k: int,
    ) -> list[RetrievedChunk]:
        """
        Merge using Reciprocal Rank Fusion (RRF).

        RRF formula: score = 1 / (k + rank)
        where k is a constant (default 60)

        Args:
            all_chunks: List of (chunk, query_index, rank) tuples
            k: RRF constant (default 60)

        Returns:
            Merged list sorted by RRF score
        """
        rrf_constant = 60  # Standard RRF constant

        # Track RRF scores by chunk_id
        chunk_scores: dict[str, tuple[RetrievedChunk, float]] = {}

        for chunk, query_idx, rank in all_chunks:
            chunk_id = chunk.chunk_id
            rrf_score = 1 / (rrf_constant + rank + 1)

            if chunk_id in chunk_scores:
                # Accumulate RRF scores
                existing_chunk, existing_score = chunk_scores[chunk_id]
                chunk_scores[chunk_id] = (existing_chunk, existing_score + rrf_score)
            else:
                chunk_scores[chunk_id] = (chunk, rrf_score)

        # Sort by RRF score (descending)
        sorted_chunks = sorted(
            chunk_scores.values(),
            key=lambda x: x[1],
            reverse=True,
        )

        # Update chunk scores to RRF scores and return
        result = []
        for chunk, rrf_score in sorted_chunks:
            # Create a new chunk with the RRF score
            updated_chunk = RetrievedChunk(
                chunk_id=chunk.chunk_id,
                source_id=chunk.source_id,
                source_type=chunk.source_type,
                content=chunk.content,
                score=rrf_score,  # Use RRF score
                metadata=chunk.metadata,
            )
            result.append(updated_chunk)

        return result

    def _merge_by_score(
        self,
        all_chunks: list[tuple[RetrievedChunk, int, int]],
        k: int,
    ) -> list[RetrievedChunk]:
        """
        Merge using original similarity scores.

        Args:
            all_chunks: List of (chunk, query_index, rank) tuples
            k: Target number of results (not used in score-based merge)

        Returns:
            Merged list sorted by original score
        """
        # Track highest score for each chunk
        chunk_best_score: dict[str, RetrievedChunk] = {}

        for chunk, query_idx, rank in all_chunks:
            chunk_id = chunk.chunk_id

            if chunk_id in chunk_best_score:
                # Keep the chunk with higher score
                existing = chunk_best_score[chunk_id]
                if chunk.score > existing.score:
                    chunk_best_score[chunk_id] = chunk
            else:
                chunk_best_score[chunk_id] = chunk

        # Sort by score (descending)
        sorted_chunks = sorted(
            chunk_best_score.values(),
            key=lambda c: c.score,
            reverse=True,
        )

        return sorted_chunks

    def _deduplicate_chunks(
        self,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        """
        Remove duplicate chunks by content hash.

        Args:
            chunks: Chunks to deduplicate

        Returns:
            Deduplicated chunk list
        """
        if len(chunks) <= 1:
            return chunks

        seen_hashes: set[str] = set()
        deduplicated: list[RetrievedChunk] = []

        import hashlib

        for chunk in chunks:
            content_hash = hashlib.md5(chunk.content.encode()).hexdigest()

            if content_hash not in seen_hashes:
                deduplicated.append(chunk)
                seen_hashes.add(content_hash)

        return deduplicated


__all__ = [
    "QueryAwareRetrievalService",
    "QueryAwareConfig",
    "QueryAwareRetrievalResult",
    "QueryAwareMetrics",
    "DEFAULT_MAX_CONCURRENT",
]
