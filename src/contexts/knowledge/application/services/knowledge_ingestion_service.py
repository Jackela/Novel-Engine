"""
Knowledge Ingestion Service

Orchestrates the ingestion pipeline for RAG (Retrieval-Augmented Generation).
Text -> Chunk -> Embed -> Store in ChromaDB.

Constitution Compliance:
- Article II (Hexagonal): Application service orchestrating domain and infrastructure
- Article V (SOLID): SRP - ingestion pipeline coordination only

Warzone 4: AI Brain - BRAIN-004
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import structlog

from ...application.ports.i_embedding_service import EmbeddingError, IEmbeddingService
from ...application.ports.i_vector_store import (
    IVectorStore,
    VectorDocument,
    VectorStoreError,
)
from ...domain.models.chunking_strategy import ChunkingStrategy
from ...domain.models.source_knowledge_entry import SourceKnowledgeEntry
from ...domain.models.source_type import SourceType
from ...domain.services.text_chunker import TextChunker, TextChunk
from .ingestion_processor_factory import IngestionProcessorFactory


logger = structlog.get_logger()


# Default collection name for knowledge storage
DEFAULT_COLLECTION = "knowledge"


@dataclass(frozen=True, slots=True)
class IngestionProgress:
    """
    Progress update for ingestion operations.

    Why frozen:
        Immutable snapshot ensures progress data isn't modified
        during callback processing.

    Attributes:
        current: Current entry being processed (1-indexed)
        total: Total number of entries to process
        source_id: ID of the source being processed
        success: Whether the current entry succeeded
        error: Error message if success is False
    """

    current: int
    total: int
    source_id: str
    success: bool = True
    error: str | None = None

    @property
    def percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total == 0:
            return 100.0
        return (self.current / self.total) * 100


@dataclass(frozen=True, slots=True)
class IngestionResult:
    """
    Result of an ingestion operation.

    Why frozen:
        Immutable result prevents accidental modification after return.

    Attributes:
        success: Whether the operation completed successfully
        source_id: ID of the source that was ingested
        chunk_count: Number of chunks created
        entries_created: Number of new entries created
        entries_updated: Number of existing entries updated
        entries_deleted: Number of entries deleted (for updates)
        error: Error message if success is False
    """

    success: bool
    source_id: str
    chunk_count: int
    entries_created: int = 0
    entries_updated: int = 0
    entries_deleted: int = 0
    error: str | None = None


@dataclass(frozen=True, slots=True)
class BatchIngestionResult:
    """
    Result of a batch ingestion operation.

    Attributes:
        success: Whether all operations completed successfully
        total_entries: Total number of entries in the batch
        successful: Number of successfully processed entries
        failed: Number of failed entries
        errors: Dict mapping source_id to error messages
    """

    success: bool
    total_entries: int
    successful: int
    failed: int
    errors: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SourceChunk:
    """
    A chunk from a source with its entry representation.

    Attributes:
        chunk: The TextChunk from chunking
        entry: The SourceKnowledgeEntry for this chunk
        embedding: The embedding vector for this chunk
    """

    chunk: TextChunk
    entry: SourceKnowledgeEntry
    embedding: list[float]


@dataclass
class RetrievedChunk:
    """
    A retrieved chunk from storage.

    Attributes:
        chunk_id: ID of the chunk
        source_id: Source ID
        source_type: Type of source
        content: Chunk content
        score: Relevance score
        metadata: Additional metadata
    """

    chunk_id: str
    source_id: str
    source_type: SourceType
    content: str
    score: float
    metadata: dict[str, Any]


class KnowledgeIngestionService:
    """
    Service for ingesting knowledge into the RAG system.

    Orchestrates the complete ingestion pipeline:
    1. Validate input
    2. Chunk text using configured strategy
    3. Generate embeddings for each chunk
    4. Store chunks in vector database

    Supports single and batch ingestion with progress tracking.

    Constitution Compliance:
        - Article II (Hexagonal): Application service coordinating ports
        - Article V (SOLID): SRP - ingestion pipeline only
        - Article III (TDD): Tested via mock ports

    Example:
        >>> service = KnowledgeIngestionService(
        ...     embedding_service=embedding_svc,
        ...     vector_store=vector_store,
        ... )
        >>> result = await service.ingest(
        ...     content="Character profile text...",
        ...     source_type=SourceType.CHARACTER,
        ...     source_id="char_alice",
        ... )
        >>> print(f"Created {result.chunk_count} chunks")
    """

    def __init__(
        self,
        embedding_service: IEmbeddingService,
        vector_store: IVectorStore,
        processor_factory: IngestionProcessorFactory | None = None,
        default_chunking_strategy: ChunkingStrategy | None = None,
        default_collection: str = DEFAULT_COLLECTION,
    ):
        """
        Initialize the ingestion service.

        Args:
            embedding_service: Service for generating embeddings
            vector_store: Vector storage backend
            processor_factory: Optional processor factory for source-type-specific handling.
                If None, creates a default factory with all standard processors.
            default_chunking_strategy: Default chunking strategy (uses default if None).
                Used only when processor returns None or for backward compatibility.
            default_collection: Default collection name for storage
        """
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._processor_factory = processor_factory or IngestionProcessorFactory.get_default_factory()
        self._default_chunking_strategy = (
            default_chunking_strategy or ChunkingStrategy.default()
        )
        self._default_collection = default_collection

    async def ingest(
        self,
        content: str,
        source_type: SourceType | str,
        source_id: str,
        chunking_strategy: ChunkingStrategy | None = None,
        tags: list[str] | None = None,
        extra_metadata: dict[str, Any] | None = None,
        collection: str | None = None,
    ) -> IngestionResult:
        """
        Ingest a single knowledge entry into the RAG system.

        Pipeline: Text -> Processor (chunking + metadata) -> Embed -> Store

        Args:
            content: Text content to ingest
            source_type: Type of source (CHARACTER, LORE, etc.)
            source_id: Unique ID of the source entity
            chunking_strategy: Optional chunking strategy override.
                If provided, takes precedence over processor default.
            tags: Optional tags for filtering
            extra_metadata: Optional additional metadata base for enrichment
            collection: Optional collection name (uses default if None)

        Returns:
            IngestionResult with operation details

        Raises:
            ValueError: If content or source_id is empty
            EmbeddingError: If embedding generation fails
            VectorStoreError: If vector storage fails

        Example:
            >>> result = await service.ingest(
            ...     content="Sir Aldric is a brave knight...",
            ...     source_type=SourceType.CHARACTER,
            ...     source_id="char_aldric",
            ...     tags=["protagonist", "knight"],
            ... )
            >>> print(f"Created {result.chunk_count} chunks")
        """
        # Validate input
        if not content or not content.strip():
            raise ValueError("content cannot be empty")

        if not source_id or not source_id.strip():
            raise ValueError("source_id cannot be empty")

        # Normalize source_type
        if isinstance(source_type, str):
            source_type = SourceType.from_string(source_type)

        target_collection = collection or self._default_collection

        # Get processor for source type and determine strategy
        processor = self._processor_factory.get_processor(source_type)

        # Use provided strategy override, or processor's default, or service default
        if chunking_strategy:
            strategy = chunking_strategy
        else:
            strategy = processor.get_chunking_strategy(self._default_chunking_strategy)

        # Build base metadata for enrichment
        base_metadata = {
            "tags": tags or [],
            **(extra_metadata or {}),
        }

        # Enrich metadata using processor
        enriched_metadata = processor.enrich_metadata(base_metadata, content)

        # Step 1: Chunk the content
        logger.debug(
            "ingestion_chunking_start",
            source_id=source_id,
            source_type=source_type.value,
            processor=type(processor).__name__,
            content_length=len(content),
        )

        chunked_doc = TextChunker.chunk(content, strategy)

        logger.debug(
            "ingestion_chunking_complete",
            source_id=source_id,
            chunk_count=chunked_doc.total_chunks,
            total_words=chunked_doc.total_words,
        )

        # Step 2: Generate embeddings for each chunk
        chunk_texts = [chunk.content for chunk in chunked_doc.chunks]

        logger.debug(
            "ingestion_embedding_start",
            source_id=source_id,
            chunk_count=len(chunk_texts),
        )

        try:
            embeddings = await self._embedding_service.embed_batch(chunk_texts)
        except EmbeddingError as e:
            logger.error(
                "ingestion_embedding_failed",
                source_id=source_id,
                error=str(e),
            )
            raise

        if len(embeddings) != len(chunked_doc.chunks):
            raise EmbeddingError(
                f"Embedding count mismatch: expected {len(chunked_doc.chunks)}, "
                f"got {len(embeddings)}"
            )

        logger.debug(
            "ingestion_embedding_complete",
            source_id=source_id,
            embedding_dimension=len(embeddings[0]) if embeddings else 0,
        )

        # Step 3: Create VectorDocuments and store
        vector_documents = []
        entries = []

        for i, (chunk, embedding) in enumerate(zip(chunked_doc.chunks, embeddings)):
            # Create SourceKnowledgeEntry with enriched metadata
            entry = SourceKnowledgeEntry.create(
                content=chunk.content,
                source_type=source_type,
                source_id=source_id,
                word_count=chunk.word_count,
                chunk_index=chunk.chunk_index,
                total_chunks=chunked_doc.total_chunks,
                tags=enriched_metadata.get("tags"),
                extra_metadata={
                    k: v for k, v in enriched_metadata.items()
                    if k != "tags"  # tags handled separately
                } or None,
            )

            # Set embedding ID
            embedding_id = f"{source_id}_chunk_{chunk.chunk_index}"
            entry.set_embedding_id(embedding_id)

            entries.append(entry)

            # Create VectorDocument
            vector_doc = VectorDocument(
                id=entry.get_vector_document_id(),
                embedding=embedding,
                text=chunk.content,
                metadata=entry.to_vector_metadata(),
            )
            vector_documents.append(vector_doc)

        # Step 4: Store in vector database
        logger.debug(
            "ingestion_storage_start",
            source_id=source_id,
            document_count=len(vector_documents),
            collection=target_collection,
        )

        try:
            upsert_result = await self._vector_store.upsert(
                collection=target_collection,
                documents=vector_documents,
            )
        except VectorStoreError as e:
            logger.error(
                "ingestion_storage_failed",
                source_id=source_id,
                error=str(e),
            )
            raise

        if not upsert_result.success:
            raise VectorStoreError(
                f"Failed to upsert documents for source {source_id}",
                code="UPSERT_FAILED",
            )

        logger.info(
            "ingestion_complete",
            source_id=source_id,
            source_type=source_type.value,
            chunk_count=chunked_doc.total_chunks,
            collection=target_collection,
        )

        return IngestionResult(
            success=True,
            source_id=source_id,
            chunk_count=chunked_doc.total_chunks,
            entries_created=len(entries),
        )

    async def batch_ingest(
        self,
        entries: list[dict[str, Any]],
        on_progress: Callable[[IngestionProgress], None] | None = None,
    ) -> BatchIngestionResult:
        """
        Ingest multiple knowledge entries in batch.

        Args:
            entries: List of entry dicts with keys:
                - content: str
                - source_type: SourceType | str
                - source_id: str
                - chunking_strategy: Optional[ChunkingStrategy]
                - tags: Optional[list[str]]
                - extra_metadata: Optional[dict[str, Any]]
                - collection: Optional[str]
            on_progress: Optional callback for progress updates

        Returns:
            BatchIngestionResult with aggregate statistics

        Example:
            >>> entries = [
            ...     {"content": "...", "source_type": SourceType.CHARACTER, "source_id": "char_1"},
            ...     {"content": "...", "source_type": SourceType.LORE, "source_id": "lore_1"},
            ... ]
            >>> result = await service.batch_ingest(entries)
            >>> print(f"Processed {result.successful} of {result.total_entries}")
        """
        total = len(entries)
        successful = 0
        failed = 0
        errors: dict[str, str] = {}

        for i, entry_spec in enumerate(entries):
            source_id = entry_spec.get("source_id", f"unknown_{i}")

            try:
                await self.ingest(
                    content=entry_spec["content"],
                    source_type=entry_spec["source_type"],
                    source_id=source_id,
                    chunking_strategy=entry_spec.get("chunking_strategy"),
                    tags=entry_spec.get("tags"),
                    extra_metadata=entry_spec.get("extra_metadata"),
                    collection=entry_spec.get("collection"),
                )

                successful += 1

                # Report progress
                if on_progress:
                    await self._call_progress_callback(
                        on_progress,
                        IngestionProgress(
                            current=i + 1,
                            total=total,
                            source_id=source_id,
                            success=True,
                        ),
                    )

            except Exception as e:
                failed += 1
                error_msg = f"{type(e).__name__}: {e}"
                errors[source_id] = error_msg

                logger.warning(
                    "batch_ingest_entry_failed",
                    source_id=source_id,
                    error=error_msg,
                )

                # Report failure progress
                if on_progress:
                    await self._call_progress_callback(
                        on_progress,
                        IngestionProgress(
                            current=i + 1,
                            total=total,
                            source_id=source_id,
                            success=False,
                            error=error_msg,
                        ),
                    )

        overall_success = failed == 0

        logger.info(
            "batch_ingestion_complete",
            total=total,
            successful=successful,
            failed=failed,
        )

        return BatchIngestionResult(
            success=overall_success,
            total_entries=total,
            successful=successful,
            failed=failed,
            errors=errors,
        )

    async def delete(
        self,
        source_id: str,
        source_type: SourceType | str | None = None,
        collection: str | None = None,
    ) -> int:
        """
        Delete all chunks for a given source.

        Args:
            source_id: ID of the source to delete
            source_type: Optional filter by source type
            collection: Optional collection name (uses default if None)

        Returns:
            Number of chunks deleted

        Example:
            >>> deleted = await service.delete("char_aldric")
            >>> print(f"Deleted {deleted} chunks")
        """
        target_collection = collection or self._default_collection

        # Build filter
        where_filter: dict[str, Any] = {"source_id": source_id}

        if source_type:
            if isinstance(source_type, str):
                source_type = SourceType.from_string(source_type)
            where_filter["source_type"] = source_type.value

        logger.debug(
            "ingestion_delete_start",
            source_id=source_id,
            collection=target_collection,
            filter=where_filter,
        )

        deleted_count = await self._vector_store.delete(
            collection=target_collection,
            where=where_filter,
        )

        logger.info(
            "ingestion_delete_complete",
            source_id=source_id,
            deleted_count=deleted_count,
        )

        return deleted_count

    async def update(
        self,
        source_id: str,
        new_content: str,
        source_type: SourceType | str,
        chunking_strategy: ChunkingStrategy | None = None,
        tags: list[str] | None = None,
        extra_metadata: dict[str, Any] | None = None,
        collection: str | None = None,
    ) -> IngestionResult:
        """
        Update knowledge for a source (replace old chunks with new).

        Args:
            source_id: ID of the source to update
            new_content: New content to ingest
            source_type: Type of source
            chunking_strategy: Optional chunking strategy
            tags: Optional tags for filtering
            extra_metadata: Optional additional metadata
            collection: Optional collection name

        Returns:
            IngestionResult with operation details

        Example:
            >>> result = await service.update(
            ...     source_id="char_aldric",
            ...     new_content="Updated character profile...",
            ...     source_type=SourceType.CHARACTER,
            ... )
        """
        if not new_content or not new_content.strip():
            raise ValueError("new_content cannot be empty")

        # Normalize source_type
        if isinstance(source_type, str):
            source_type = SourceType.from_string(source_type)

        target_collection = collection or self._default_collection

        # Delete existing chunks
        deleted_count = await self.delete(
            source_id=source_id,
            source_type=source_type,
            collection=target_collection,
        )

        logger.debug(
            "ingestion_update_deleted_old",
            source_id=source_id,
            deleted_count=deleted_count,
        )

        # Ingest new content
        result = await self.ingest(
            content=new_content,
            source_type=source_type,
            source_id=source_id,
            chunking_strategy=chunking_strategy,
            tags=tags,
            extra_metadata=extra_metadata,
            collection=target_collection,
        )

        # Return combined result
        return IngestionResult(
            success=result.success,
            source_id=source_id,
            chunk_count=result.chunk_count,
            entries_created=result.entries_created,
            entries_deleted=deleted_count,
        )

    async def query_by_source(
        self,
        source_id: str,
        source_type: SourceType | str | None = None,
        collection: str | None = None,
    ) -> list[RetrievedChunk]:
        """
        Query all chunks for a given source.

        Args:
            source_id: ID of the source to query
            source_type: Optional filter by source type
            collection: Optional collection name

        Returns:
            List of RetrievedChunk objects

        Example:
            >>> chunks = await service.query_by_source("char_aldric")
            >>> for chunk in chunks:
            ...     print(f"{chunk.chunk_id}: {chunk.content[:50]}...")
        """
        target_collection = collection or self._default_collection

        # Build filter
        where_filter: dict[str, Any] = {"source_id": source_id}

        if source_type:
            if isinstance(source_type, str):
                source_type = SourceType.from_string(source_type)
            where_filter["source_type"] = source_type.value

        logger.debug(
            "ingestion_query_by_source",
            source_id=source_id,
            collection=target_collection,
            filter=where_filter,
        )

        # We need to query by metadata filter
        # Since vector store needs an embedding, we use a dummy query
        # and filter by source_id
        import random

        dummy_embedding = [random.gauss(0, 1) for _ in range(self._embedding_service.get_dimension())]

        try:
            query_results = await self._vector_store.query(
                collection=target_collection,
                query_embedding=dummy_embedding,
                n_results=1000,  # Large number to get all chunks
                where=where_filter,
            )
        except VectorStoreError:
            # If query fails, return empty list
            return []

        # Convert to RetrievedChunk
        retrieved = []
        for qr in query_results:
            retrieved.append(
                RetrievedChunk(
                    chunk_id=qr.id,
                    source_id=qr.metadata.get("source_id", source_id) if qr.metadata else source_id,
                    source_type=SourceType(
                        qr.metadata.get("source_type", "LORE") if qr.metadata else "LORE"
                    ),
                    content=qr.text,
                    score=qr.score,
                    metadata=qr.metadata or {},
                )
            )

        return retrieved

    async def health_check(self) -> bool:
        """
        Verify the ingestion pipeline is healthy.

        Returns:
            True if vector store is healthy, False otherwise
        """
        return await self._vector_store.health_check()

    async def get_count(
        self,
        collection: str | None = None,
    ) -> int:
        """
        Get the total number of chunks in storage.

        Args:
            collection: Optional collection name (uses default if None)

        Returns:
            Number of chunks stored
        """
        target_collection = collection or self._default_collection
        return await self._vector_store.count(target_collection)

    async def _call_progress_callback(
        self,
        callback: Callable[[IngestionProgress], None],
        progress: IngestionProgress,
    ) -> None:
        """
        Safely call progress callback.

        Args:
            callback: Progress callback function
            progress: Progress data to report
        """
        try:
            if callback:
                # Check if callback is async
                import inspect

                if inspect.iscoroutinefunction(callback):
                    await callback(progress)
                else:
                    callback(progress)
        except Exception as e:
            logger.warning(
                "progress_callback_failed",
                error=str(e),
            )


__all__ = [
    "KnowledgeIngestionService",
    "IngestionProgress",
    "IngestionResult",
    "BatchIngestionResult",
    "SourceChunk",
    "RetrievedChunk",
    "DEFAULT_COLLECTION",
]
