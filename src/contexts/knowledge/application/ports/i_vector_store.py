"""
IVectorStore Port Interface

Hexagonal architecture port defining the contract for vector storage operations.
This port enables semantic search through vector embeddings.

Constitution Compliance:
- Article II (Hexagonal): Domain/Application layer defines port, Infrastructure provides adapter
- Article I (DDD): Pure interface with no infrastructure coupling
- Article IV (SSOT): ChromaDB as authoritative vector storage

Warzone 4: AI Brain - BRAIN-001
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VectorDocument:
    """
    A document with its vector embedding for semantic search.

    Why frozen:
        Immutable snapshot ensures stored vectors cannot be modified
        after creation, preventing cache inconsistency.

    Attributes:
        id: Unique identifier for this document/chunk
        embedding: Vector embedding (list of floats)
        text: Original text content
        metadata: Optional metadata (source_type, source_id, chunk_index, etc.)
    """

    id: str
    embedding: list[float]
    text: str
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class QueryResult:
    """
    Result from a vector similarity search.

    Attributes:
        id: Document identifier
        text: Original text content
        score: Similarity score (0-1, higher is more similar)
        metadata: Associated metadata
    """

    id: str
    text: str
    score: float
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class UpsertResult:
    """
    Result of an upsert operation.

    Attributes:
        count: Number of documents upserted
        success: Whether the operation completed successfully
    """

    count: int
    success: bool


class IVectorStore(ABC):
    """
    Port for vector storage operations.

    This interface defines the contract for storing and querying
    vector embeddings, enabling semantic search capabilities.

    Per Article II (Hexagonal Architecture):
    - Domain/Application layer defines this port
    - Infrastructure layer provides ChromaDB adapter implementation
    - Application use cases depend ONLY on this abstraction

    Methods:
        upsert: Insert or update documents with their embeddings
        query: Search for similar documents by vector
        delete: Remove documents by ID or filter
        clear: Remove all documents from a collection

    Constitution Compliance:
    - Article II (Hexagonal): Port interface in application layer
    - Article V (SOLID): ISP - Interface Segregation Principle
    - Article V (SOLID): DIP - Depend on abstractions, not concretions
    """

    @abstractmethod
    async def upsert(
        self,
        collection: str,
        documents: list[VectorDocument],
    ) -> UpsertResult:
        """
        Insert or update documents in the vector store.

        Args:
            collection: Name of the collection/table
            documents: List of documents with embeddings to store

        Returns:
            UpsertResult with count of documents affected

        Raises:
            VectorStoreError: If upsert operation fails

        Why async:
            Vector operations can be slow with large batches.
            Async prevents blocking the event loop.
        """

    @abstractmethod
    async def query(
        self,
        collection: str,
        query_embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
        where_document: dict[str, Any] | None = None,
    ) -> list[QueryResult]:
        """
        Search for similar documents by vector embedding.

        Args:
            collection: Name of the collection to search
            query_embedding: Query vector to find similar documents
            n_results: Maximum number of results to return
            where: Filter on metadata fields (e.g., {"source_type": "CHARACTER"})
            where_document: Filter on document content

        Returns:
            List of QueryResult sorted by similarity (highest first)

        Raises:
            VectorStoreError: If query operation fails

        Why async:
            Vector search can be slow with large collections.
            Async prevents blocking the event loop.
        """

    @abstractmethod
    async def delete(
        self,
        collection: str,
        ids: list[str] | None = None,
        where: dict[str, Any] | None = None,
    ) -> int:
        """
        Delete documents from the vector store.

        Args:
            collection: Name of the collection
            ids: Specific document IDs to delete (optional)
            where: Filter to delete matching documents (optional)

        Returns:
            Number of documents deleted

        Raises:
            VectorStoreError: If delete operation fails

        Note:
            Either ids or where must be provided. If both provided,
            only ids is used.
        """

    @abstractmethod
    async def clear(self, collection: str) -> None:
        """
        Remove all documents from a collection.

        Args:
            collection: Name of the collection to clear

        Raises:
            VectorStoreError: If clear operation fails

        Why separate from delete:
        - Clear is more efficient for full collection deletion
        - Explicit intent (clear all vs selective delete)
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Verify the vector store connection is healthy.

        Returns:
            True if connection is working, False otherwise

        Why async:
            May require actual network/database call to verify health.
        """

    @abstractmethod
    async def count(self, collection: str) -> int:
        """
        Get the number of documents in a collection.

        Args:
            collection: Name of the collection

        Returns:
            Number of documents in the collection

        Raises:
            VectorStoreError: If count operation fails
        """


class VectorStoreError(Exception):
    """Base exception for vector store operations."""

    def __init__(
        self,
        message: str,
        code: str = "VECTOR_STORE_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.details = details or {}


__all__ = [
    "IVectorStore",
    "VectorDocument",
    "QueryResult",
    "UpsertResult",
    "VectorStoreError",
]
