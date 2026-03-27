"""ChromaDB implementation of vector store.

This module provides a ChromaDB-based implementation of the vector store
port interface for semantic search operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from src.contexts.knowledge.application.ports.i_vector_store import (
    IVectorStore,
    QueryResult,
)

if TYPE_CHECKING:
    import chromadb


class ChromaVectorStore(IVectorStore):
    """ChromaDB implementation of vector store.

    Uses ChromaDB HTTP client for vector storage and semantic search.

    Example:
        >>> store = ChromaVectorStore(host="localhost", port=8000)
        >>> await store.upsert(
        ...     collection="knowledge",
        ...     documents=["doc1", "doc2"],
        ...     embeddings=[[0.1, 0.2], [0.3, 0.4]],
        ...     metadatas=[{"key": "value"}, {"key": "value2"}],
        ...     ids=["id1", "id2"]
        ... )
    """

    def __init__(self, host: str, port: int = 8000) -> None:
        """Initialize ChromaDB vector store.

        Args:
            host: ChromaDB server host
            port: ChromaDB server port (default: 8000)
        """
        self._host = host
        self._port = port
        self._client: chromadb.ClientAPI | None = None

    def _get_client(self) -> "chromadb.ClientAPI":
        """Get or create ChromaDB client.

        Returns:
            ChromaDB client instance

        Raises:
            ImportError: If chromadb is not installed
            ConnectionError: If cannot connect to ChromaDB
        """
        if self._client is None:
            try:
                import chromadb

                self._client = chromadb.HttpClient(host=self._host, port=self._port)
            except ImportError as e:
                raise ImportError(
                    "chromadb is required for ChromaVectorStore. "
                    "Install it with: pip install chromadb"
                ) from e
            except Exception as e:
                raise ConnectionError(
                    f"Failed to connect to ChromaDB at {self._host}:{self._port}"
                ) from e
        return self._client

    async def upsert(
        self,
        collection: str,
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        ids: list[str],
    ) -> None:
        """Upsert documents into the vector store.

        Args:
            collection: Collection name
            documents: List of document texts
            embeddings: List of embedding vectors
            metadatas: List of metadata dictionaries
            ids: List of document IDs

        Raises:
            ValueError: If input lists have different lengths
            ConnectionError: If ChromaDB connection fails
        """
        if not (len(documents) == len(embeddings) == len(metadatas) == len(ids)):
            raise ValueError("All input lists must have the same length")

        try:
            client = self._get_client()
            coll = client.get_or_create_collection(collection)
            coll.upsert(
                documents=documents,
                embeddings=cast(Any, embeddings),
                metadatas=cast(Any, metadatas),
                ids=ids,
            )
        except Exception as e:
            raise ConnectionError(f"Failed to upsert documents: {e}") from e

    async def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
        collection: str = "knowledge",
    ) -> list[QueryResult]:
        """Query the vector store.

        Args:
            query_embedding: Query embedding vector
            n_results: Number of results to return (default: 10)
            where: Optional metadata filters
            collection: Collection name (default: "knowledge")

        Returns:
            List of query results

        Raises:
            ConnectionError: If ChromaDB connection fails
        """
        try:
            client = self._get_client()
            coll = client.get_or_create_collection(collection)
            results = coll.query(
                query_embeddings=cast(Any, [query_embedding]),
                n_results=n_results,
                where=where,
            )

            # Convert ChromaDB results to QueryResult objects
            query_results: list[QueryResult] = []
            if results["ids"] and len(results["ids"]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    query_results.append(
                        QueryResult(
                            id=doc_id,
                            text=results["documents"][0][i]
                            if results["documents"]
                            else "",
                            score=float(results["distances"][0][i])
                            if results["distances"]
                            else 0.0,
                            metadata=(
                                dict(results["metadatas"][0][i])
                                if results["metadatas"]
                                else {}
                            ),
                        )
                    )
            return query_results
        except Exception as e:
            raise ConnectionError(f"Failed to query vector store: {e}") from e

    async def delete(self, collection: str, ids: list[str]) -> None:
        """Delete documents from the vector store.

        Args:
            collection: Collection name
            ids: List of document IDs to delete

        Raises:
            ConnectionError: If ChromaDB connection fails
        """
        try:
            client = self._get_client()
            coll = client.get_or_create_collection(collection)
            coll.delete(ids=ids)
        except Exception as e:
            raise ConnectionError(f"Failed to delete documents: {e}") from e

    async def clear(self, collection: str) -> None:
        """Clear all documents from a collection.

        Args:
            collection: Collection name

        Raises:
            ConnectionError: If ChromaDB connection fails
        """
        try:
            client = self._get_client()
            coll = client.get_or_create_collection(collection)
            # Get all IDs and delete them
            all_ids = coll.get()["ids"]
            if all_ids:
                coll.delete(ids=all_ids)
        except Exception as e:
            raise ConnectionError(f"Failed to clear collection: {e}") from e

    async def count(self, collection: str) -> int:
        """Count documents in a collection.

        Args:
            collection: Collection name

        Returns:
            Number of documents in the collection

        Raises:
            ConnectionError: If ChromaDB connection fails
        """
        try:
            client = self._get_client()
            coll = client.get_or_create_collection(collection)
            return cast(int, coll.count())
        except Exception as e:
            raise ConnectionError(f"Failed to count documents: {e}") from e

    async def health_check(self) -> bool:
        """Check if the vector store is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            client = self._get_client()
            # Try a simple operation to verify connection
            client.list_collections()
            return True
        except Exception:
            return False
