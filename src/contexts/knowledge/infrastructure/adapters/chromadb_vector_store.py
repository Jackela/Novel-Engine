"""
ChromaDB Vector Store Adapter

Hexagonal architecture adapter implementing IVectorStore port using ChromaDB.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter implements application port
- Article I (DDD): No domain logic, only external integration
- Article IV (SSOT): ChromaDB as authoritative vector storage

Warzone 4: AI Brain - BRAIN-001
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import structlog

from ...application.ports.i_vector_store import (
    IVectorStore,
    QueryResult,
    UpsertResult,
    VectorDocument,
    VectorStoreError,
)

logger = structlog.get_logger()


class ChromaDBVectorStore(IVectorStore):
    """
    ChromaDB adapter for vector storage operations.

    Provides persistent vector storage with semantic search capabilities.
    Data is stored in `.data/chroma/` directory by default.

    Why ChromaDB:
        - Open-source, lightweight vector database
        - Embedded mode (no separate server needed)
        - Excellent for RAG (Retrieval-Augmented Generation)
        - Built-in similarity search with multiple metrics

    Configuration:
        ChromaDB persists to `.data/chroma/` directory.
        Set CHROMA_PERSIST_DIR environment variable to customize.

    Constitution Compliance:
    - Article II (Hexagonal): Implements IVectorStore port
    - Article I (DDD): No business logic, pure adapter
    - Article IV (SSOT): ChromaDB as authoritative vector storage

    Example:
        >>> store = ChromaDBVectorStore()
        >>> docs = [VectorDocument(id="1", embedding=[0.1, 0.2], text="hello")]
        >>> result = await store.upsert("knowledge", docs)
        >>> results = await store.query("knowledge", [0.1, 0.2], n_results=1)
    """

    _DEFAULT_PERSIST_DIR = ".data/chroma"

    def __init__(
        self,
        persist_dir: str | None = None,
        embedding_dimension: int = 1536,
    ):
        """
        Initialize ChromaDB vector store.

        Args:
            persist_dir: Directory for persistent storage (default: .data/chroma/)
            embedding_dimension: Dimension of embeddings (default: 1536 for OpenAI)

        Raises:
            VectorStoreError: If ChromaDB is not installed or initialization fails
        """
        self._persist_dir = persist_dir or os.environ.get(
            "CHROMA_PERSIST_DIR", self._DEFAULT_PERSIST_DIR
        )
        self._embedding_dimension = embedding_dimension
        self._client: Any = None
        self._initialized = False
        self._collection_cache: dict[str, Any] = {}

    def _get_client(self) -> Any:
        """
        Lazy-initialize ChromaDB client.

        Returns:
            ChromaDB client instance

        Raises:
            VectorStoreError: If ChromaDB is not installed or fails to initialize
        """
        if self._client is not None:
            return self._client

        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as e:
            raise VectorStoreError(
                "ChromaDB is not installed. Run: pip install chromadb",
                code="CHROMADB_NOT_INSTALLED",
                details={"import_error": str(e)},
            )

        try:
            # Ensure persist directory exists
            persist_path = Path(self._persist_dir)
            persist_path.mkdir(parents=True, exist_ok=True)

            # Initialize ChromaDB client with persistent storage
            self._client = chromadb.PersistentClient(
                path=str(persist_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )

            self._initialized = True
            logger.info(
                "chromadb_initialized",
                persist_dir=str(persist_path),
                embedding_dimension=self._embedding_dimension,
            )

            return self._client

        except Exception as e:
            raise VectorStoreError(
                f"Failed to initialize ChromaDB: {e}",
                code="CHROMADB_INIT_FAILED",
                details={"persist_dir": self._persist_dir, "error": str(e)},
            )

    def _get_collection(self, name: str) -> Any:
        """
        Get or create a ChromaDB collection.

        Args:
            name: Collection name

        Returns:
            ChromaDB collection object
        """
        client = self._get_client()

        # Check cache first
        if name in self._collection_cache:
            return self._collection_cache[name]

        # Get or create collection
        try:
            collection = client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},  # Cosine similarity for text
            )
            self._collection_cache[name] = collection
            return collection
        except Exception as e:
            raise VectorStoreError(
                f"Failed to get collection '{name}': {e}",
                code="COLLECTION_ERROR",
                details={"collection": name, "error": str(e)},
            )

    async def upsert(
        self,
        collection: str,
        documents: list[VectorDocument],
    ) -> UpsertResult:
        """
        Insert or update documents in the vector store.

        Args:
            collection: Name of the collection
            documents: List of documents with embeddings

        Returns:
            UpsertResult with count of documents upserted

        Raises:
            VectorStoreError: If upsert fails
        """
        if not documents:
            return UpsertResult(count=0, success=True)

        try:
            chroma_collection = self._get_collection(collection)

            # Prepare data for ChromaDB
            ids = [doc.id for doc in documents]
            embeddings = [doc.embedding for doc in documents]
            texts = [doc.text for doc in documents]
            metadatas = [doc.metadata or {} for doc in documents]

            # ChromaDB upsert
            chroma_collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )

            logger.debug(
                "chromadb_upsert",
                collection=collection,
                count=len(documents),
            )

            return UpsertResult(count=len(documents), success=True)

        except Exception as e:
            logger.error(
                "chromadb_upsert_failed",
                collection=collection,
                error=str(e),
            )
            raise VectorStoreError(
                f"Upsert failed: {e}",
                code="UPSERT_FAILED",
                details={"collection": collection, "document_count": len(documents)},
            )

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
            collection: Name of the collection
            query_embedding: Query vector
            n_results: Maximum number of results
            where: Metadata filter
            where_document: Document content filter

        Returns:
            List of QueryResult sorted by similarity

        Raises:
            VectorStoreError: If query fails
        """
        try:
            chroma_collection = self._get_collection(collection)

            # Query ChromaDB
            result = chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document,
            )

            # Format results
            query_results = []
            if result and result["ids"] and result["ids"][0]:
                for i, doc_id in enumerate(result["ids"][0]):
                    query_results.append(
                        QueryResult(
                            id=doc_id,
                            text=(
                                result["documents"][0][i]
                                if result.get("documents")
                                else ""
                            ),
                            score=(
                                1.0
                                / (
                                    1.0
                                    + max(
                                        0.0,
                                        float(result["distances"][0][i]),
                                    )
                                )
                                if result.get("distances")
                                else 0.0
                            ),
                            metadata=(
                                result["metadatas"][0][i]
                                if result.get("metadatas")
                                else None
                            ),
                        )
                    )

            logger.debug(
                "chromadb_query",
                collection=collection,
                results_count=len(query_results),
            )

            return query_results

        except Exception as e:
            logger.error(
                "chromadb_query_failed",
                collection=collection,
                error=str(e),
            )
            raise VectorStoreError(
                f"Query failed: {e}",
                code="QUERY_FAILED",
                details={
                    "collection": collection,
                    "n_results": n_results,
                },
            )

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
            ids: Specific document IDs to delete
            where: Filter for deletion

        Returns:
            Number of documents deleted

        Raises:
            VectorStoreError: If delete fails
        """
        if not ids and not where:
            raise VectorStoreError(
                "Either ids or where must be provided for deletion",
                code="INVALID_DELETE",
            )

        try:
            chroma_collection = self._get_collection(collection)

            # Count before deletion
            count_before = chroma_collection.count()

            # Delete from ChromaDB
            chroma_collection.delete(ids=ids, where=where)

            # Count after deletion
            count_after = chroma_collection.count()

            deleted_count = count_before - count_after

            logger.debug(
                "chromadb_delete",
                collection=collection,
                deleted_count=deleted_count,
            )

            return deleted_count

        except Exception as e:
            logger.error(
                "chromadb_delete_failed",
                collection=collection,
                error=str(e),
            )
            raise VectorStoreError(
                f"Delete failed: {e}",
                code="DELETE_FAILED",
                details={"collection": collection, "has_ids": ids is not None},
            )

    async def clear(self, collection: str) -> None:
        """
        Remove all documents from a collection.

        Args:
            collection: Name of the collection

        Raises:
            VectorStoreError: If clear fails
        """
        try:
            client = self._get_client()

            # Delete and recreate collection
            try:
                client.delete_collection(name=collection)
            except Exception:
                # Collection might not exist, that's ok
                pass

            # Clear cache
            self._collection_cache.pop(collection, None)

            logger.info(
                "chromadb_collection_cleared",
                collection=collection,
            )

        except Exception as e:
            logger.error(
                "chromadb_clear_failed",
                collection=collection,
                error=str(e),
            )
            raise VectorStoreError(
                f"Clear collection failed: {e}",
                code="CLEAR_FAILED",
                details={"collection": collection},
            )

    async def health_check(self) -> bool:
        """
        Verify the vector store connection is healthy.

        Returns:
            True if connection is working, False otherwise
        """
        try:
            client = self._get_client()

            # Simple heartbeat: list collections
            client.list_collections()

            return True

        except Exception as e:
            logger.warning(
                "chromadb_health_check_failed",
                error=str(e),
            )
            return False

    async def count(self, collection: str) -> int:
        """
        Get the number of documents in a collection.

        Args:
            collection: Name of the collection

        Returns:
            Number of documents in the collection

        Raises:
            VectorStoreError: If count fails
        """
        try:
            chroma_collection = self._get_collection(collection)
            return chroma_collection.count()

        except Exception as e:
            raise VectorStoreError(
                f"Count failed: {e}",
                code="COUNT_FAILED",
                details={"collection": collection},
            )

    async def reset(self) -> None:
        """
        Reset the entire vector store.

        WARNING: This deletes all data from all collections.
        Use only for testing or full reset scenarios.

        Raises:
            VectorStoreError: If reset fails
        """
        try:
            client = self._get_client()
            client.reset()

            # Clear collection cache
            self._collection_cache.clear()

            logger.warning("chromadb_reset", message="All collections deleted")

        except Exception as e:
            raise VectorStoreError(
                f"Reset failed: {e}",
                code="RESET_FAILED",
            )


__all__ = ["ChromaDBVectorStore"]
