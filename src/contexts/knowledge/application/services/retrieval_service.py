"""
Context Retrieval Service (RAG)

The 'Recall' mechanism for fetching relevant knowledge from the vector store.
Converts user queries into formatted context for LLM generation.

Constitution Compliance:
- Article II (Hexagonal): Application service coordinating domain and infrastructure
- Article V (SOLID): SRP - retrieval and formatting only

Warzone 4: AI Brain - BRAIN-006
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Any

import structlog

from ...application.ports.i_embedding_service import EmbeddingError, IEmbeddingService
from ...application.ports.i_vector_store import (
    IVectorStore,
    VectorStoreError,
)
from ...domain.models.source_type import SourceType
from ..services.knowledge_ingestion_service import RetrievedChunk

if TYPE_CHECKING:
    from .rerank_service import RerankService


logger = structlog.get_logger()


# Default collection name for knowledge retrieval
DEFAULT_COLLECTION = "knowledge"

# Default relevance threshold (0.0 - 1.0)
DEFAULT_RELEVANCE_THRESHOLD = 0.5

# Default similarity threshold for deduplication (0.0 - 1.0)
DEFAULT_DEDUPLICATION_SIMILARITY = 0.85


@dataclass(frozen=True, slots=True)
class RetrievalFilter:
    """
    Filter options for retrieval operations.

    Why frozen:
        Immutable snapshot ensures filters aren't modified during retrieval.

    Attributes:
        source_types: Filter by source types (CHARACTER, LORE, etc.)
        tags: Filter by tags (any match)
        date_from: Filter for entries after this date
        date_to: Filter for entries before this date
        custom_metadata: Additional metadata filters
    """

    source_types: list[SourceType] | None = None
    tags: list[str] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    custom_metadata: dict[str, Any] | None = None

    def to_where_clause(self) -> dict[str, Any]:
        """
        Convert filter to vector store where clause.

        Returns:
            Dict suitable for vector_store.query(where=...)
        """
        where: dict[str, Any] = {}

        if self.source_types:
            # ChromaDB supports $in for OR queries
            where["source_type"] = {"$in": [st.value for st in self.source_types]}

        if self.tags:
            # For tags, we need to check if any tag matches
            # This is stored as a list in metadata
            where["tags"] = {"$in": self.tags}

        if self.custom_metadata:
            where.update(self.custom_metadata)

        # Note: date filtering is done post-query since metadata dates may be strings
        return where if where else {}

    def matches(self, metadata: dict[str, Any] | None) -> bool:
        """
        Check if metadata matches this filter.

        Used for post-query filtering (e.g., date ranges).

        Args:
            metadata: Document metadata to check

        Returns:
            True if metadata matches all filter conditions
        """
        # None metadata never matches (document doesn't exist)
        if metadata is None:
            return False

        # If no date constraints, empty metadata passes
        if not self.date_from and not self.date_to:
            return True

        # Check date range
        created_at = metadata.get("created_at")
        if created_at:
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except ValueError:
                    # Invalid date format, treat as non-matching
                    return False
            elif not isinstance(created_at, datetime):
                # Unexpected type, treat as non-matching
                return False

            if self.date_from and created_at < self.date_from:
                return False
            if self.date_to and created_at > self.date_to:
                return False
        elif self.date_from or self.date_to:
            # Date constraint exists but no date in metadata
            return False

        return True


@dataclass(frozen=True, slots=True)
class RetrievalOptions:
    """
    Options for retrieval operations.

    Attributes:
        k: Number of results to retrieve (alias for final_k when reranking is enabled)
        candidate_k: Number of candidates to retrieve before reranking (None = 2x final_k)
        final_k: Final number of results after reranking (None = use k)
        min_score: Minimum relevance score (0.0 - 1.0)
        deduplicate: Whether to deduplicate similar results
        deduplication_threshold: Similarity threshold for deduplication
        enable_rerank: Whether to apply reranking after retrieval
    """

    k: int = 5
    candidate_k: int | None = None
    final_k: int | None = None
    min_score: float = DEFAULT_RELEVANCE_THRESHOLD
    deduplicate: bool = True
    deduplication_threshold: float = DEFAULT_DEDUPLICATION_SIMILARITY
    enable_rerank: bool = True


@dataclass(frozen=True, slots=True)
class FormattedContext:
    """
    Formatted context block for LLM prompts.

    Attributes:
        text: Formatted context string
        sources: List of source references
        total_tokens: Estimated token count
        chunk_count: Number of chunks included
        source_references: Detailed source references with citation data
    """

    text: str
    sources: list[str]
    total_tokens: int
    chunk_count: int
    source_references: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """
    Result of a retrieval operation.

    Attributes:
        chunks: List of retrieved chunks
        query: Original query string
        total_retrieved: Total chunks retrieved (before filtering)
        filtered: Chunks filtered by relevance score
        deduplicated: Chunks removed by deduplication
    """

    chunks: list[RetrievedChunk]
    query: str
    total_retrieved: int
    filtered: int = 0
    deduplicated: int = 0


class RetrievalService:
    """
    Service for retrieving relevant context from the knowledge base.

    Orchestrates the retrieval pipeline:
    1. Embed the query
    2. Search vector database
    3. Apply filters and thresholds
    4. Deduplicate similar results
    5. Rerank results (if RerankService is provided)
    6. Format for LLM consumption

    Constitution Compliance:
        - Article II (Hexagonal): Application service coordinating ports
        - Article V (SOLID): SRP - retrieval and formatting only
        - Article III (TDD): Tested via mock ports

    Example:
        >>> service = RetrievalService(
        ...     embedding_service=embedding_svc,
        ...     vector_store=vector_store,
        ...     rerank_service=rerank_svc,  # Optional
        ... )
        >>> results = await service.retrieve_relevant(
        ...     query="brave warrior",
        ...     k=5,
        ... )
        >>> context = service.format_context(results)
        >>> print(context.text)
    """

    def __init__(
        self,
        embedding_service: IEmbeddingService,
        vector_store: IVectorStore,
        default_collection: str = DEFAULT_COLLECTION,
        rerank_service: RerankService | None = None,
    ):
        """
        Initialize the retrieval service.

        Args:
            embedding_service: Service for generating query embeddings
            vector_store: Vector storage backend for semantic search
            default_collection: Default collection name for queries
            rerank_service: Optional reranking service for result reordering
        """
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._default_collection = default_collection
        self._rerank_service = rerank_service

    async def retrieve_relevant(
        self,
        query: str,
        k: int = 5,
        filters: RetrievalFilter | None = None,
        options: RetrievalOptions | None = None,
        collection: str | None = None,
    ) -> RetrievalResult:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: Search query text
            k: Number of results to retrieve
            filters: Optional filters for source_type, tags, dates
            options: Optional retrieval options (threshold, deduplication)
            collection: Optional collection name (uses default if None)

        Returns:
            RetrievalResult with retrieved chunks

        Raises:
            ValueError: If query is empty
            EmbeddingError: If query embedding fails
            VectorStoreError: If vector search fails

        Example:
            >>> results = await service.retrieve_relevant(
            ...     query="brave warrior with a sword",
            ...     k=5,
            ...     filters=RetrievalFilter(source_types=[SourceType.CHARACTER]),
            ... )
            >>> for chunk in results.chunks:
            ...     print(f"{chunk.source_id}: {chunk.score:.2f}")
        """
        if not query or not query.strip():
            raise ValueError("query cannot be empty")

        # Use provided options or defaults
        retrieval_options = options or RetrievalOptions(k=k)
        target_collection = collection or self._default_collection

        logger.debug(
            "retrieval_start",
            query=query,
            k=k,
            collection=target_collection,
        )

        # Step 1: Embed the query
        try:
            query_embedding = await self._embedding_service.embed(query)
        except EmbeddingError as e:
            logger.error(
                "retrieval_embedding_failed",
                query=query,
                error=str(e),
            )
            raise

        # Step 2: Build filter clause
        where_clause: dict[str, Any] = {}
        if filters:
            where_clause = filters.to_where_clause()

        # Step 3: Determine candidate and final k for reranking
        # If reranking is enabled and available, retrieve more candidates
        final_k = retrieval_options.final_k or k
        candidate_k = retrieval_options.candidate_k or (
            final_k * 2 if retrieval_options.enable_rerank else k
        )

        logger.debug(
            "retrieval_k_calculation",
            k=k,
            candidate_k=candidate_k,
            final_k=final_k,
            enable_rerank=retrieval_options.enable_rerank,
            has_reranker=self._rerank_service is not None,
        )

        # Step 4: Search vector store (retrieve candidate_k for potential reranking)
        fetch_k = max(candidate_k, 10)

        try:
            query_results = await self._vector_store.query(
                collection=target_collection,
                query_embedding=query_embedding,
                n_results=fetch_k,
                where=where_clause if where_clause else None,
            )
        except VectorStoreError as e:
            logger.error(
                "retrieval_query_failed",
                query=query,
                error=str(e),
            )
            raise

        logger.debug(
            "retrieval_query_complete",
            query=query,
            results_count=len(query_results),
        )

        # Step 5: Convert to RetrievedChunk and apply score threshold
        chunks: list[RetrievedChunk] = []
        filtered_count = 0

        for qr in query_results:
            # Apply relevance score threshold
            if qr.score < retrieval_options.min_score:
                filtered_count += 1
                continue

            # Apply date filters if present (post-query)
            if filters and not filters.matches(qr.metadata):
                filtered_count += 1
                continue

            chunk = RetrievedChunk(
                chunk_id=qr.id,
                source_id=(
                    qr.metadata.get("source_id", "unknown")
                    if qr.metadata
                    else "unknown"
                ),
                source_type=SourceType(
                    qr.metadata.get("source_type", "LORE") if qr.metadata else "LORE"
                ),
                content=qr.text,
                score=qr.score,
                metadata=qr.metadata or {},
            )
            chunks.append(chunk)

        # Step 6: Deduplicate similar chunks
        if retrieval_options.deduplicate:
            chunks_before_dedup = len(chunks)
            chunks = self._deduplicate_chunks(
                chunks,
                threshold=retrieval_options.deduplication_threshold,
            )
            deduplicated_count = chunks_before_dedup - len(chunks)
        else:
            deduplicated_count = 0

        # Step 7: Apply reranking if enabled and available
        reranked = False
        rerank_error = None

        if (
            retrieval_options.enable_rerank
            and self._rerank_service is not None
            and chunks
        ):
            logger.debug(
                "retrieval_rerank_start",
                query=query,
                candidate_count=len(chunks),
                final_k=final_k,
            )

            try:
                rerank_result = await self._rerank_service.rerank(
                    query=query,
                    chunks=chunks,
                    top_k=final_k,
                )

                if rerank_result.reranked:
                    chunks = rerank_result.chunks
                    reranked = True
                    logger.info(
                        "retrieval_rerank_complete",
                        query=query,
                        model=rerank_result.model,
                        latency_ms=rerank_result.latency_ms,
                        score_improvement=rerank_result.score_improvement,
                    )
                else:
                    # Reranking was disabled or returned original order
                    logger.debug(
                        "retrieval_rerank_skipped",
                        reason=rerank_result.error or "reranking not applied",
                    )
                    rerank_error = rerank_result.error

            except Exception as e:
                # On any error, fall back to original order with warning
                rerank_error = str(e)
                logger.warning(
                    "retrieval_rerank_error",
                    query=query,
                    error=str(e),
                    error_type=type(e).__name__,
                    fallback_to_original=True,
                )
                # Continue with original chunk order

        # Step 8: Limit to final_k results (or k if no reranking)
        if reranked:
            # Reranking already applied top_k, but ensure we don't exceed
            chunks = chunks[:final_k]
        else:
            chunks = chunks[:k]

        logger.info(
            "retrieval_complete",
            query=query,
            total_retrieved=len(query_results),
            filtered=filtered_count,
            deduplicated=deduplicated_count,
            final_count=len(chunks),
            reranked=reranked,
            rerank_error=rerank_error,
        )

        return RetrievalResult(
            chunks=chunks,
            query=query,
            total_retrieved=len(query_results),
            filtered=filtered_count,
            deduplicated=deduplicated_count,
        )

    def format_context(
        self,
        result: RetrievalResult,
        max_tokens: int | None = None,
        include_sources: bool = True,
        include_citation_data: bool = False,
    ) -> FormattedContext:
        """
        Convert retrieved chunks to formatted context for LLM.

        Args:
            result: RetrievalResult from retrieve_relevant
            max_tokens: Maximum tokens to include (None for unlimited)
            include_sources: Whether to include source citations
            include_citation_data: Whether to include detailed citation data

        Returns:
            FormattedContext with text, sources, token count, and citation data

        Example:
            >>> context = service.format_context(results, max_tokens=2000)
            >>> # Use context.text in prompt construction
            >>> prompt = f"System: You are a narrator.\\nRelevant Context: {context.text}"
        """
        if not result.chunks:
            return FormattedContext(
                text="",
                sources=[],
                total_tokens=0,
                chunk_count=0,
                source_references={},
            )

        # Build context sections
        sections: list[str] = []
        sources: list[str] = []
        citation_data: dict[str, Any] = {}

        # Estimate tokens (rough estimate: ~4 chars per token)
        char_budget = max_tokens * 4 if max_tokens else None

        for i, chunk in enumerate(result.chunks, 1):
            # Format chunk with citation marker
            section = self._format_chunk_with_citation(chunk, i)
            section_with_newline = section + "\n\n"

            # Check token budget
            if char_budget is not None:
                current_length = sum(len(s) for s in sections) + len(
                    section_with_newline
                )
                if current_length > char_budget:
                    # Would exceed budget, stop here
                    logger.debug(
                        "format_context_token_limit",
                        included_chunks=i - 1,
                        total_chunks=len(result.chunks),
                    )
                    break

            sections.append(section_with_newline)

            # Track source
            if include_sources:
                source_ref = self._format_source(chunk)
                if source_ref not in sources:
                    sources.append(source_ref)

        # Combine sections
        context_text = "".join(sections)

        # Estimate tokens
        estimated_tokens = len(context_text) // 4

        # Include citation data if requested
        if include_citation_data:
            citation_data["sources"] = self.get_sources(result.chunks)
            citation_data["citations"] = [
                {
                    "chunk_id": chunk.chunk_id,
                    "source_id": chunk.source_id,
                    "source_type": chunk.source_type.value,
                    "citation_index": i,
                    "citation_id": f"[{i}]",
                }
                for i, chunk in enumerate(result.chunks, 1)
            ]

        return FormattedContext(
            text=context_text.strip(),
            sources=sources,
            total_tokens=estimated_tokens,
            chunk_count=len(sections),
            source_references=citation_data,
        )

    def format_context_simple(
        self,
        chunks: list[RetrievedChunk],
        max_tokens: int | None = None,
    ) -> str:
        """
        Simple format that returns just the context text.

        Convenience method for quick formatting.

        Args:
            chunks: List of retrieved chunks
            max_tokens: Optional token limit

        Returns:
            Formatted context string
        """
        # Create a dummy result for formatting
        result = RetrievalResult(
            chunks=chunks,
            query="",
            total_retrieved=len(chunks),
        )
        formatted = self.format_context(result, max_tokens=max_tokens)
        return formatted.text

    def get_sources(
        self,
        chunks: list[RetrievedChunk],
        source_names: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Extract unique sources from retrieved chunks.

        Provides a summary of all sources that contributed to the retrieved
        chunks, including chunk counts and average relevance scores.

        Args:
            chunks: List of retrieved chunks
            source_names: Optional mapping of source_id to display names

        Returns:
            List of source dictionaries with:
                - source_type: Type of source (CHARACTER, LORE, etc.)
                - source_id: Unique ID of the source
                - display_name: Human-readable name
                - chunk_count: Number of chunks from this source
                - relevance_score: Average relevance score
                - citation_id: Short ID for display (e.g., "1", "C1")

        Example:
            >>> sources = service.get_sources(result.chunks)
            >>> for source in sources:
            >>>     print(f"{source['source_type']}:{source['source_id']}")
        """
        if not chunks:
            return []

        # Group chunks by source
        from collections import defaultdict

        source_groups: dict[tuple[SourceType, str], list[RetrievedChunk]] = defaultdict(
            list
        )
        for chunk in chunks:
            key = (chunk.source_type, chunk.source_id)
            source_groups[key].append(chunk)

        # Build source list
        sources: list[dict[str, Any]] = []
        for idx, ((source_type, source_id), group_chunks) in enumerate(
            source_groups.items(), 1
        ):
            avg_score = sum(c.score for c in group_chunks) / len(group_chunks)

            # Get display name
            if source_names and source_id in source_names:
                display_name = source_names[source_id]
            else:
                # Try to extract from metadata
                metadata = group_chunks[0].metadata or {}
                display_name = metadata.get("name", source_id)

            # Generate citation ID with source type prefix
            prefix = self._get_source_type_prefix(source_type)
            citation_id = f"{prefix}{idx}"

            sources.append(
                {
                    "source_type": source_type.value,
                    "source_id": source_id,
                    "display_name": display_name,
                    "chunk_count": len(group_chunks),
                    "relevance_score": round(avg_score, 3),
                    "citation_id": citation_id,
                }
            )

        # Sort by relevance score
        sources.sort(key=lambda s: s["relevance_score"], reverse=True)
        return sources

    def _get_source_type_prefix(self, source_type: SourceType) -> str:
        """
        Get the citation prefix for a source type.

        Args:
            source_type: The source type

        Returns:
            Single or double character prefix (C, L, S, P, I, Loc)
        """
        prefixes = {
            SourceType.CHARACTER: "C",
            SourceType.LORE: "L",
            SourceType.SCENE: "S",
            SourceType.PLOTLINE: "P",
            SourceType.ITEM: "I",
            SourceType.LOCATION: "Loc",
        }
        return prefixes.get(source_type, source_type.value[0].upper())

    def _format_chunk_with_citation(self, chunk: RetrievedChunk, index: int) -> str:
        """
        Format a single chunk with citation marker.

        Args:
            chunk: Chunk to format
            index: Chunk index in results

        Returns:
            Formatted chunk string with citation marker
        """
        # Extract metadata
        source_type = chunk.source_type.value
        chunk_index = chunk.metadata.get("chunk_index", "?")
        total_chunks = chunk.metadata.get("total_chunks", "?")

        header = f"[{index}] {source_type}:{chunk.source_id} (part {chunk_index}/{total_chunks})"

        return f"{header}\n{chunk.content}"

    def _format_chunk(self, chunk: RetrievedChunk, index: int) -> str:
        """
        Format a single chunk for context display.

        Args:
            chunk: Chunk to format
            index: Chunk index in results

        Returns:
            Formatted chunk string
        """
        # Extract metadata
        source_type = chunk.source_type.value
        chunk_index = chunk.metadata.get("chunk_index", "?")
        total_chunks = chunk.metadata.get("total_chunks", "?")

        header = f"[{index}] {source_type}:{chunk.source_id} (part {chunk_index}/{total_chunks})"

        return f"{header}\n{chunk.content}"

    def _format_source(self, chunk: RetrievedChunk) -> str:
        """
        Format a source reference for citations.

        Args:
            chunk: Chunk to format

        Returns:
            Source reference string
        """
        return f"{chunk.source_type.value}:{chunk.source_id}"

    def _deduplicate_chunks(
        self,
        chunks: list[RetrievedChunk],
        threshold: float = DEFAULT_DEDUPLICATION_SIMILARITY,
    ) -> list[RetrievedChunk]:
        """
        Remove duplicate/similar chunks from results.

        Uses content similarity to detect duplicates.
        Keeps the highest-scoring chunk when duplicates are found.

        Args:
            chunks: Chunks to deduplicate
            threshold: Similarity threshold (0.0 - 1.0)

        Returns:
            Deduplicated chunk list
        """
        if len(chunks) <= 1:
            return chunks

        # Sort by score (highest first) so we keep best chunks
        sorted_chunks = sorted(chunks, key=lambda c: c.score, reverse=True)

        deduplicated: list[RetrievedChunk] = []
        seen_hashes: set[str] = set()

        for chunk in sorted_chunks:
            # Check for exact duplicates via content hash
            content_hash = hashlib.md5(chunk.content.encode()).hexdigest()

            if content_hash in seen_hashes:
                continue

            # Check for similar content
            is_duplicate = False
            for existing in deduplicated:
                similarity = self._content_similarity(chunk.content, existing.content)
                if similarity >= threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduplicated.append(chunk)
                seen_hashes.add(content_hash)

        return deduplicated

    def _content_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings.

        Uses SequenceMatcher for a basic similarity score.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0 - 1.0)
        """
        # Normalize texts
        text1_normalized = " ".join(text1.lower().split())
        text2_normalized = " ".join(text2.lower().split())

        # Use SequenceMatcher for similarity
        return SequenceMatcher(None, text1_normalized, text2_normalized).ratio()


__all__ = [
    "RetrievalService",
    "RetrievalFilter",
    "RetrievalOptions",
    "FormattedContext",
    "RetrievalResult",
    "DEFAULT_RELEVANCE_THRESHOLD",
    "DEFAULT_DEDUPLICATION_SIMILARITY",
]
