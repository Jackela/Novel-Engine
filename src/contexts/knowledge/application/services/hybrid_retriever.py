"""
Hybrid Retriever with Score Fusion

Combines vector (semantic) search and BM25 (keyword) search using
Reciprocal Rank Fusion (RRF) for optimal retrieval performance.

Constitution Compliance:
- Article II (Hexagonal): Application service coordinating retrieval methods
- Article V (SOLID): SRP - hybrid retrieval and score fusion only

Warzone 4: AI Brain - BRAIN-008B
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from .knowledge_ingestion_service import RetrievedChunk


logger = structlog.get_logger()


# Default collection name
DEFAULT_COLLECTION = "knowledge"

# Default weights for score fusion
DEFAULT_VECTOR_WEIGHT = 0.7
DEFAULT_BM25_WEIGHT = 0.3

# Default RRF parameters
DEFAULT_RRF_K = 60  # RRF constant (higher = more rank influence)
DEFAULT_RRF_ALPHA = 0.5  # Fusion weight between linear score and RRF


@dataclass(frozen=True, slots=True)
class HybridConfig:
    """
    Configuration for hybrid retrieval.

    Attributes:
        vector_weight: Weight for vector search scores (0.0 - 1.0)
        bm25_weight: Weight for BM25 scores (0.0 - 1.0)
        use_rrf: Whether to use Reciprocal Rank Fusion
        rrf_k: RRF constant (higher = more rank influence)
        rrf_alpha: Fusion weight between linear score and RRF (0.0 = score only, 1.0 = RRF only)
    """

    vector_weight: float = DEFAULT_VECTOR_WEIGHT
    bm25_weight: float = DEFAULT_BM25_WEIGHT
    use_rrf: bool = True
    rrf_k: float = DEFAULT_RRF_K
    rrf_alpha: float = DEFAULT_RRF_ALPHA

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        # Weights should sum to approximately 1.0
        total = self.vector_weight + self.bm25_weight
        if abs(total - 1.0) > 0.01:
            logger.warning(
                "hybrid_config_weights_not_normalized",
                vector_weight=self.vector_weight,
                bm25_weight=self.bm25_weight,
                total=total,
                message="Weights should sum to 1.0 for optimal results",
            )

        # Validate ranges
        if not (0.0 <= self.vector_weight <= 1.0):
            raise ValueError(
                f"vector_weight must be between 0.0 and 1.0, got {self.vector_weight}"
            )
        if not (0.0 <= self.bm25_weight <= 1.0):
            raise ValueError(
                f"bm25_weight must be between 0.0 and 1.0, got {self.bm25_weight}"
            )
        if self.rrf_k <= 0:
            raise ValueError(f"rrf_k must be positive, got {self.rrf_k}")
        if not (0.0 <= self.rrf_alpha <= 1.0):
            raise ValueError(
                f"rrf_alpha must be between 0.0 and 1.0, got {self.rrf_alpha}"
            )


@dataclass
class HybridResult:
    """
    Result of a hybrid retrieval operation.

    Attributes:
        chunks: List of retrieved chunks with fused scores
        vector_results: Original vector search results
        bm25_results: Original BM25 search results
        fusion_method: Method used for score fusion
    """

    chunks: list[RetrievedChunk]
    vector_results: list[RetrievedChunk]
    bm25_results: list[RetrievedChunk]
    fusion_method: str = "rrf"


@dataclass
class FusionMetadata:
    """
    Metadata for fusion operations.

    Why frozen:
        Immutable snapshot ensures fusion results are consistent.

    Attributes:
        doc_id: Document identifier
        vector_score: Original vector similarity score
        vector_rank: Rank in vector results (1-indexed)
        bm25_score: Original BM25 score
        bm25_rank: Rank in BM25 results (1-indexed)
        fused_score: Final fused score
    """

    doc_id: str
    vector_score: float
    vector_rank: int
    bm25_score: float
    bm25_rank: int
    fused_score: float


def _normalize_scores(scores: list[float]) -> list[float]:
    """
    Min-max normalize scores to [0, 1] range.

    Args:
        scores: List of raw scores

    Returns:
        Normalized scores

    Example:
        >>> _normalize_scores([0.1, 0.5, 0.9])
        [0.0, 0.5, 1.0]
    """
    if not scores:
        return []

    min_score = min(scores)
    max_score = max(scores)

    if max_score == min_score:
        # All scores are the same
        return [0.5] * len(scores)

    return [(s - min_score) / (max_score - min_score) for s in scores]


def _reciprocal_rank_fusion(
    vector_scores: dict[str, tuple[float, int]],  # doc_id -> (score, rank)
    bm25_scores: dict[str, tuple[float, int]],  # doc_id -> (score, rank)
    k: float = DEFAULT_RRF_K,
) -> dict[str, float]:
    """
    Apply Reciprocal Rank Fusion (RRF) to combine rankings.

    RRF formula: score(d) = sum(ranker_weight / (k + rank))

    Args:
        vector_scores: Vector search scores with ranks
        bm25_scores: BM25 scores with ranks
        k: RRF constant (higher = more rank influence)

    Returns:
        Dictionary mapping doc_id to fused score

    Example:
        >>> vector = {"doc1": (0.9, 1), "doc2": (0.7, 2)}
        >>> bm25 = {"doc2": (10.0, 1), "doc1": (5.0, 2)}
        >>> _reciprocal_rank_fusion(vector, bm25, k=60)
        {'doc1': 0.0333..., 'doc2': 0.0333...}
    """
    fused_scores: dict[str, float] = {}

    # Process vector scores
    for doc_id, (score, rank) in vector_scores.items():
        rrf_score = 1.0 / (k + rank)
        fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + rrf_score

    # Process BM25 scores
    for doc_id, (score, rank) in bm25_scores.items():
        rrf_score = 1.0 / (k + rank)
        fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + rrf_score

    return fused_scores


def _linear_score_fusion(
    vector_scores: dict[str, float],
    bm25_scores: dict[str, float],
    vector_weight: float,
    bm25_weight: float,
) -> dict[str, float]:
    """
    Apply linear score fusion with normalized scores.

    fused_score = vector_weight * norm(vector_score) + bm25_weight * norm(bm25_score)

    Args:
        vector_scores: Vector search scores
        bm25_scores: BM25 scores
        vector_weight: Weight for vector scores
        bm25_weight: Weight for BM25 scores

    Returns:
        Dictionary mapping doc_id to fused score

    Example:
        >>> vector = {"doc1": 0.9, "doc2": 0.7}
        >>> bm25 = {"doc2": 10.0, "doc1": 5.0}
        >>> _linear_score_fusion(vector, bm25, 0.7, 0.3)
        {'doc1': 0.7 * 1.0 + 0.3 * 0.0, 'doc2': 0.7 * 0.0 + 0.3 * 1.0}
    """
    # Normalize scores separately
    all_vector_scores = list(vector_scores.values())
    all_bm25_scores = list(bm25_scores.values())

    norm_vector = dict(zip(vector_scores.keys(), _normalize_scores(all_vector_scores)))
    norm_bm25 = dict(zip(bm25_scores.keys(), _normalize_scores(all_bm25_scores)))

    # Combine scores
    fused_scores: dict[str, float] = {}

    for doc_id in set(list(vector_scores.keys()) + list(bm25_scores.keys())):
        v_score = norm_vector.get(doc_id, 0.0)
        b_score = norm_bm25.get(doc_id, 0.0)

        fused_scores[doc_id] = vector_weight * v_score + bm25_weight * b_score

    return fused_scores


def _hybrid_score_fusion(
    vector_scores: dict[str, tuple[float, int]],
    bm25_scores: dict[str, tuple[float, int]],
    config: HybridConfig,
) -> dict[str, float]:
    """
    Apply hybrid score fusion combining RRF and linear fusion.

    fused_score = alpha * rrf_score + (1 - alpha) * linear_score

    Args:
        vector_scores: Vector search scores with ranks
        bm25_scores: BM25 scores with ranks
        config: Hybrid configuration

    Returns:
        Dictionary mapping doc_id to fused score
    """
    # Get linear fusion scores (always needed)
    vector_only = {doc_id: score for doc_id, (score, _) in vector_scores.items()}
    bm25_only = {doc_id: score for doc_id, (score, _) in bm25_scores.items()}

    linear_scores = _linear_score_fusion(
        vector_only,
        bm25_only,
        config.vector_weight,
        config.bm25_weight,
    )

    # If alpha is 0, return pure linear fusion
    if config.rrf_alpha <= 0.0:
        return linear_scores

    # If alpha is 1, return pure RRF
    if config.rrf_alpha >= 1.0:
        rrf_scores = _reciprocal_rank_fusion(
            vector_scores,
            bm25_scores,
            k=config.rrf_k,
        )
        # Normalize RRF scores
        if rrf_scores:
            rrf_values = list(rrf_scores.values())
            rrf_min, rrf_max = min(rrf_values), max(rrf_values)
            if rrf_max > rrf_min:
                rrf_scores = {
                    doc_id: (score - rrf_min) / (rrf_max - rrf_min)
                    for doc_id, score in rrf_scores.items()
                }
            else:
                rrf_scores = {doc_id: 0.5 for doc_id in rrf_scores}
        return rrf_scores

    # Otherwise, combine RRF and linear fusion
    # Get RRF scores
    rrf_scores = _reciprocal_rank_fusion(
        vector_scores,
        bm25_scores,
        k=config.rrf_k,
    )

    # Normalize RRF scores
    if rrf_scores:
        rrf_values = list(rrf_scores.values())
        rrf_min, rrf_max = min(rrf_values), max(rrf_values)
        if rrf_max > rrf_min:
            rrf_scores = {
                doc_id: (score - rrf_min) / (rrf_max - rrf_min)
                for doc_id, score in rrf_scores.items()
            }
        else:
            rrf_scores = {doc_id: 0.5 for doc_id in rrf_scores}

    # Combine RRF and linear fusion
    fused_scores: dict[str, float] = {}

    for doc_id in set(list(rrf_scores.keys()) + list(linear_scores.keys())):
        rrf = rrf_scores.get(doc_id, 0.0)
        linear = linear_scores.get(doc_id, 0.0)

        fused_scores[doc_id] = config.rrf_alpha * rrf + (1 - config.rrf_alpha) * linear

    return fused_scores


class HybridRetriever:
    """
    Hybrid retrieval service combining vector and keyword search.

    Uses Reciprocal Rank Fusion (RRF) to combine results from:
    - Vector (semantic) search: Good for conceptual similarity
    - BM25 (keyword) search: Good for exact term matching

    The fusion method can be configured:
    - RRF only (rrf_alpha = 1.0): Pure rank-based fusion
    - Linear only (rrf_alpha = 0.0): Pure score-based fusion
    - Hybrid (rrf_alpha = 0.5): Combines both approaches

    Constitution Compliance:
        - Article II (Hexagonal): Application service
        - Article V (SOLID): SRP - hybrid retrieval only
        - Article III (TDD): Tested via mocks

    Example:
        >>> retriever = HybridRetriever(
        ...     retrieval_service=vector_svc,
        ...     bm25_retriever=bm25_svc,
        ...     config=HybridConfig(vector_weight=0.7, bm25_weight=0.3),
        ... )
        >>> results = await retriever.search("brave warrior", k=5)
        >>> for chunk in results.chunks:
        ...     print(f"{chunk.chunk_id}: {chunk.score:.2f}")
    """

    def __init__(
        self,
        retrieval_service: Any,  # RetrievalService
        bm25_retriever: Any,  # BM25Retriever
        config: HybridConfig | None = None,
        default_collection: str = DEFAULT_COLLECTION,
    ):
        """
        Initialize the hybrid retriever.

        Args:
            retrieval_service: Vector search service
            bm25_retriever: BM25 keyword search service
            config: Hybrid fusion configuration
            default_collection: Default collection name
        """
        self._retrieval_service = retrieval_service
        self._bm25_retriever = bm25_retriever
        self._config = config or HybridConfig()
        self._default_collection = default_collection

        logger.info(
            "hybrid_retriever_initialized",
            vector_weight=self._config.vector_weight,
            bm25_weight=self._config.bm25_weight,
            use_rrf=self._config.use_rrf,
            rrf_k=self._config.rrf_k,
            rrf_alpha=self._config.rrf_alpha,
        )

    async def search(
        self,
        query: str,
        k: int = 5,
        filters: Any | None = None,  # RetrievalFilter
        options: Any | None = None,  # RetrievalOptions
        collection: str | None = None,
        config_override: HybridConfig | None = None,
    ) -> HybridResult:
        """
        Perform hybrid search combining vector and BM25 results.

        Args:
            query: Search query text
            k: Number of results to retrieve
            filters: Optional filters for source_type, tags, dates
            options: Optional retrieval options
            collection: Optional collection name
            config_override: Override hybrid config for this search

        Returns:
            HybridResult with fused results

        Raises:
            ValueError: If query is empty

        Example:
            >>> results = await retriever.search(
            ...     query="brave knight",
            ...     k=5,
            ...     config_override=HybridConfig(vector_weight=0.5, bm25_weight=0.5),
            ... )
            >>> for chunk in results.chunks:
            ...     print(f"{chunk.chunk_id}: {chunk.score:.2f}")
        """
        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        target_collection = collection or self._default_collection
        config = config_override or self._config

        logger.debug(
            "hybrid_search_start",
            query=query,
            k=k,
            collection=target_collection,
            vector_weight=config.vector_weight,
            bm25_weight=config.bm25_weight,
        )

        # Execute both searches in parallel
        # Note: In production, these would be truly parallel with asyncio.gather
        # For now, we execute sequentially since both are async

        # Step 1: Vector search
        try:
            vector_result = await self._retrieval_service.retrieve_relevant(
                query=query,
                k=k * 2,  # Get more candidates for fusion
                filters=filters,
                options=options,
                collection=target_collection,
            )
            vector_chunks = vector_result.chunks
        except Exception as e:
            logger.warning(
                "hybrid_vector_search_failed",
                query=query,
                error=str(e),
            )
            vector_chunks = []

        # Step 2: BM25 search
        try:
            # Convert RetrievalFilter to dict filters for BM25
            bm25_filters = self._convert_filters(filters) if filters else None

            bm25_results = self._bm25_retriever.search(
                query=query,
                k=k * 2,  # Get more candidates for fusion
                collection=target_collection,
                filters=bm25_filters,
            )
            bm25_chunks = self._bm25_to_retrieved(bm25_results)
        except Exception as e:
            logger.warning(
                "hybrid_bm25_search_failed",
                query=query,
                error=str(e),
            )
            bm25_chunks = []

        logger.debug(
            "hybrid_search_results",
            query=query,
            vector_count=len(vector_chunks),
            bm25_count=len(bm25_chunks),
        )

        # Step 3: Fuse results
        fused_chunks = self._fuse_results(
            vector_chunks,
            bm25_chunks,
            k=k,
            config=config,
        )

        # Determine fusion method
        if not config.use_rrf:
            fusion_method = "linear"
        elif config.rrf_alpha >= 1.0:
            fusion_method = "rrf"
        elif config.rrf_alpha <= 0.0:
            fusion_method = "linear"
        else:
            fusion_method = "hybrid"

        logger.info(
            "hybrid_search_complete",
            query=query,
            vector_count=len(vector_chunks),
            bm25_count=len(bm25_chunks),
            fused_count=len(fused_chunks),
            fusion_method=fusion_method,
        )

        return HybridResult(
            chunks=fused_chunks,
            vector_results=vector_chunks,
            bm25_results=bm25_chunks,
            fusion_method=fusion_method,
        )

    def _convert_filters(self, filters: Any) -> dict[str, Any] | None:
        """
        Convert RetrievalFilter to dict filters for BM25.

        Args:
            filters: RetrievalFilter object

        Returns:
            Dict filters for BM25 retriever
        """
        if filters is None:
            return None

        bm25_filters: dict[str, Any] = {}

        if filters.source_types:
            if len(filters.source_types) == 1:
                bm25_filters["source_type"] = filters.source_types[0].value
            else:
                # BM25 filter method doesn't support list, take first
                bm25_filters["source_type"] = filters.source_types[0].value

        if filters.tags:
            bm25_filters["tags"] = filters.tags

        if filters.custom_metadata:
            bm25_filters.update(filters.custom_metadata)

        return bm25_filters if bm25_filters else None

    def _bm25_to_retrieved(
        self,
        bm25_results: list[Any],  # list[BM25Result]
    ) -> list[Any]:  # list[RetrievedChunk]
        """
        Convert BM25Result to RetrievedChunk.

        Args:
            bm25_results: List of BM25Result objects

        Returns:
            List of RetrievedChunk objects
        """
        from ...domain.models.source_type import SourceType
        from .knowledge_ingestion_service import RetrievedChunk

        chunks: list[Any] = []

        for result in bm25_results:
            chunk = RetrievedChunk(
                chunk_id=result.doc_id,
                source_id=result.source_id,
                source_type=SourceType(result.source_type),
                content=result.content,
                score=result.score,
                metadata=result.metadata,
            )
            chunks.append(chunk)

        return chunks

    def _fuse_results(
        self,
        vector_chunks: list[Any],  # list[RetrievedChunk]
        bm25_chunks: list[Any],  # list[RetrievedChunk]
        k: int,
        config: HybridConfig,
    ) -> list[Any]:  # list[RetrievedChunk]
        """
        Fuse vector and BM25 results using configured fusion method.

        Args:
            vector_chunks: Vector search results
            bm25_chunks: BM25 search results
            k: Number of final results
            config: Fusion configuration

        Returns:
            Fused and sorted list of RetrievedChunk
        """
        from .knowledge_ingestion_service import RetrievedChunk

        if not vector_chunks and not bm25_chunks:
            return []

        # If only one source has results, return those
        if not vector_chunks:
            return bm25_chunks[:k]
        if not bm25_chunks:
            return vector_chunks[:k]

        # Build score dictionaries with ranks
        vector_scores: dict[str, tuple[float, int]] = {}
        for rank, chunk in enumerate(vector_chunks, 1):
            vector_scores[chunk.chunk_id] = (chunk.score, rank)

        bm25_scores: dict[str, tuple[float, int]] = {}
        for rank, chunk in enumerate(bm25_chunks, 1):
            bm25_scores[chunk.chunk_id] = (chunk.score, rank)

        # Apply fusion
        if config.use_rrf:
            fused_scores = _hybrid_score_fusion(
                vector_scores,
                bm25_scores,
                config,
            )
        else:
            # Linear fusion only
            vector_only = {
                doc_id: score for doc_id, (score, _) in vector_scores.items()
            }
            bm25_only = {doc_id: score for doc_id, (score, _) in bm25_scores.items()}
            fused_scores = _linear_score_fusion(
                vector_only,
                bm25_only,
                config.vector_weight,
                config.bm25_weight,
            )

        # Sort by fused score
        sorted_doc_ids = sorted(
            fused_scores.keys(),
            key=lambda doc_id: fused_scores[doc_id],
            reverse=True,
        )

        # Build final chunk list with fused scores
        fused_chunks: list[Any] = []
        seen_chunks: set[str] = set()

        # Use content hash for deduplication
        chunk_content: dict[str, Any] = {}

        for chunk in vector_chunks + bm25_chunks:
            content_hash = hashlib.md5(chunk.content.encode()).hexdigest()
            if content_hash not in chunk_content:
                chunk_content[content_hash] = chunk
            elif chunk.score > chunk_content[content_hash].score:
                # Keep higher scoring version
                chunk_content[content_hash] = chunk

        for doc_id in sorted_doc_ids[:k]:
            if doc_id in seen_chunks:
                continue

            # Find the chunk
            chunk = next(
                (c for c in vector_chunks + bm25_chunks if c.chunk_id == doc_id),
                None,
            )

            if chunk is None:
                continue

            # Check for duplicate content
            content_hash = hashlib.md5(chunk.content.encode()).hexdigest()
            if content_hash in seen_chunks:
                continue

            # Create new chunk with fused score
            fused_chunk = RetrievedChunk(
                chunk_id=chunk.chunk_id,
                source_id=chunk.source_id,
                source_type=chunk.source_type,
                content=chunk.content,
                score=fused_scores[doc_id],
                metadata=chunk.metadata,
            )

            fused_chunks.append(fused_chunk)
            seen_chunks.add(doc_id)
            seen_chunks.add(content_hash)

            if len(fused_chunks) >= k:
                break

        return fused_chunks


__all__ = [
    "HybridRetriever",
    "HybridConfig",
    "HybridResult",
    "FusionMetadata",
    "DEFAULT_VECTOR_WEIGHT",
    "DEFAULT_BM25_WEIGHT",
    "DEFAULT_RRF_K",
    "DEFAULT_RRF_ALPHA",
]
