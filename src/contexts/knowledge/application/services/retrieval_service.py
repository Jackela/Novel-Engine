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

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from difflib import SequenceMatcher
import hashlib

import structlog

from ...application.ports.i_embedding_service import IEmbeddingService, EmbeddingError
from ...application.ports.i_vector_store import (
    IVectorStore,
    QueryResult,
    VectorStoreError,
)
from ...domain.models.source_type import SourceType
from ..services.knowledge_ingestion_service import RetrievedChunk


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
            where["source_type"] = {
                "$in": [st.value for st in self.source_types]
            }

        if self.tags:
            # For tags, we need to check if any tag matches
            # This is stored as a list in metadata
            where["tags"] = {
                "$in": self.tags
            }

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
        k: Number of results to retrieve
        min_score: Minimum relevance score (0.0 - 1.0)
        deduplicate: Whether to deduplicate similar results
        deduplication_threshold: Similarity threshold for deduplication
    """

    k: int = 5
    min_score: float = DEFAULT_RELEVANCE_THRESHOLD
    deduplicate: bool = True
    deduplication_threshold: float = DEFAULT_DEDUPLICATION_SIMILARITY


@dataclass(frozen=True, slots=True)
class FormattedContext:
    """
    Formatted context block for LLM prompts.

    Attributes:
        text: Formatted context string
        sources: List of source references
        total_tokens: Estimated token count
        chunk_count: Number of chunks included
    """

    text: str
    sources: list[str]
    total_tokens: int
    chunk_count: int


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
    5. Format for LLM consumption

    Constitution Compliance:
        - Article II (Hexagonal): Application service coordinating ports
        - Article V (SOLID): SRP - retrieval and formatting only
        - Article III (TDD): Tested via mock ports

    Example:
        >>> service = RetrievalService(
        ...     embedding_service=embedding_svc,
        ...     vector_store=vector_store,
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
    ):
        """
        Initialize the retrieval service.

        Args:
            embedding_service: Service for generating query embeddings
            vector_store: Vector storage backend for semantic search
            default_collection: Default collection name for queries
        """
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._default_collection = default_collection

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

        # Step 3: Search vector store (retrieve more than k for filtering/dedup)
        # Retrieve 2x what we need to account for filtering
        fetch_k = max(k * 2, 10)

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

        # Step 4: Convert to RetrievedChunk and apply score threshold
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
                source_id=qr.metadata.get("source_id", "unknown") if qr.metadata else "unknown",
                source_type=SourceType(
                    qr.metadata.get("source_type", "LORE") if qr.metadata else "LORE"
                ),
                content=qr.text,
                score=qr.score,
                metadata=qr.metadata or {},
            )
            chunks.append(chunk)

        # Step 5: Deduplicate similar chunks
        if retrieval_options.deduplicate:
            chunks_before_dedup = len(chunks)
            chunks = self._deduplicate_chunks(
                chunks,
                threshold=retrieval_options.deduplication_threshold,
            )
            deduplicated_count = chunks_before_dedup - len(chunks)
        else:
            deduplicated_count = 0

        # Step 6: Limit to k results
        chunks = chunks[:k]

        logger.info(
            "retrieval_complete",
            query=query,
            total_retrieved=len(query_results),
            filtered=filtered_count,
            deduplicated=deduplicated_count,
            final_count=len(chunks),
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
    ) -> FormattedContext:
        """
        Convert retrieved chunks to formatted context for LLM.

        Args:
            result: RetrievalResult from retrieve_relevant
            max_tokens: Maximum tokens to include (None for unlimited)
            include_sources: Whether to include source citations

        Returns:
            FormattedContext with text, sources, and token count

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
            )

        # Build context sections
        sections: list[str] = []
        sources: list[str] = []

        # Estimate tokens (rough estimate: ~4 chars per token)
        char_budget = max_tokens * 4 if max_tokens else None

        for i, chunk in enumerate(result.chunks, 1):
            # Format chunk
            section = self._format_chunk(chunk, i)
            section_with_newline = section + "\n\n"

            # Check token budget
            if char_budget is not None:
                current_length = sum(len(s) for s in sections) + len(section_with_newline)
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

        return FormattedContext(
            text=context_text.strip(),
            sources=sources,
            total_tokens=estimated_tokens,
            chunk_count=len(sections),
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
