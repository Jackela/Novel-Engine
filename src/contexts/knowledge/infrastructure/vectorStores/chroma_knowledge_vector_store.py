"""Knowledge-service adapter for Chroma-backed vector search."""

from __future__ import annotations

from typing import Any

from src.contexts.knowledge.infrastructure.vectorStores.chroma_vector_store import (
    ChromaVectorStore,
)


class ChromaKnowledgeVectorStore:
    """Adapt ``ChromaVectorStore`` to the knowledge service contract."""

    def __init__(
        self,
        store: ChromaVectorStore,
        *,
        collection: str = "knowledge",
    ) -> None:
        self._store = store
        self._collection = collection

    async def store_embedding(
        self,
        document_id: str,
        content: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        await self._store.upsert(
            collection=self._collection,
            documents=[content],
            embeddings=[embedding],
            metadatas=[dict(metadata or {})],
            ids=[document_id],
        )

    async def search_similar(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        results = await self._store.query(
            query_embedding=query_embedding,
            n_results=top_k,
            where=filters,
            collection=self._collection,
        )
        return [
            {
                "document_id": result.id,
                "content": result.text,
                "score": self._distance_to_similarity(result.score),
                "metadata": result.metadata,
            }
            for result in results
        ]

    async def delete_document(self, document_id: str) -> None:
        await self._store.delete(collection=self._collection, ids=[document_id])

    @staticmethod
    def _distance_to_similarity(distance: float) -> float:
        """Normalize Chroma's smaller-is-better distance into a similarity score."""
        bounded_distance = max(distance, 0.0)
        return 1.0 / (1.0 + bounded_distance)
