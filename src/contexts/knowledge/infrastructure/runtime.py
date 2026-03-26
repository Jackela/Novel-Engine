"""Runtime wiring for knowledge application services."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.contexts.knowledge.application.services.knowledge_service import (
    EmbeddingService,
    KnowledgeApplicationService,
)
from src.contexts.knowledge.domain.aggregates.knowledge_base import KnowledgeBase
from src.contexts.knowledge.infrastructure.services.recursive_chunking_service import (
    RecursiveChunkingService,
)
from src.shared.infrastructure.config.settings import NovelEngineSettings


class InMemoryKnowledgeRepository:
    """In-memory knowledge repository for testing and local development."""

    def __init__(self) -> None:
        self._knowledge_bases: dict[UUID, KnowledgeBase] = {}

    async def get_by_id(self, knowledge_base_id: UUID) -> KnowledgeBase | None:
        return self._knowledge_bases.get(knowledge_base_id)

    async def save(self, knowledge_base: KnowledgeBase) -> None:
        self._knowledge_bases[knowledge_base.id] = knowledge_base

    async def delete(self, knowledge_base_id: UUID) -> None:
        self._knowledge_bases.pop(knowledge_base_id, None)


@dataclass(slots=True)
class _StoredEmbedding:
    document_id: str
    content: str
    embedding: list[float]
    metadata: dict[str, Any]


class InMemoryVectorStore:
    """Deterministic in-memory vector store for testing and development."""

    def __init__(self) -> None:
        self._documents: dict[str, _StoredEmbedding] = {}

    async def store_embedding(
        self,
        document_id: str,
        content: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._documents[document_id] = _StoredEmbedding(
            document_id=document_id,
            content=content,
            embedding=list(embedding),
            metadata=dict(metadata or {}),
        )

    async def search_similar(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        for stored in self._documents.values():
            if filters and any(
                stored.metadata.get(key) != value for key, value in filters.items()
            ):
                continue

            matches.append(
                {
                    "document_id": stored.document_id,
                    "score": self._cosine_similarity(query_embedding, stored.embedding),
                    "metadata": dict(stored.metadata),
                    "content": stored.content,
                }
            )

        matches.sort(key=lambda item: item["score"], reverse=True)
        return matches[:top_k]

    async def delete_document(self, document_id: str) -> None:
        self._documents.pop(document_id, None)

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0

        limit = min(len(left), len(right))
        dot_product = sum(left[index] * right[index] for index in range(limit))
        left_norm = math.sqrt(sum(value * value for value in left[:limit]))
        right_norm = math.sqrt(sum(value * value for value in right[:limit]))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        return dot_product / (left_norm * right_norm)


class DeterministicEmbeddingService(EmbeddingService):
    """Simple deterministic embedding service for local use."""

    def __init__(self, dimensions: int = 16) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self._dimensions = dimensions

    async def embed_text(self, text: str) -> list[float]:
        return self._embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        tokens = [token.strip(".,;:!?()[]{}").lower() for token in text.split()]

        for index, token in enumerate(token for token in tokens if token):
            bucket = (sum(ord(char) for char in token) + index) % self._dimensions
            vector[bucket] += 1.0 + len(token) / 10.0

        if not any(vector):
            vector[0] = 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector]


def create_in_memory_knowledge_service(
    settings: NovelEngineSettings,
) -> KnowledgeApplicationService:
    """Create a self-contained knowledge service for testing/local development."""
    return KnowledgeApplicationService(
        knowledge_repo=InMemoryKnowledgeRepository(),
        vector_store=InMemoryVectorStore(),
        embedding_service=DeterministicEmbeddingService(),
        chunking_service=RecursiveChunkingService(
            chunk_size=settings.knowledge.chunk_size,
            chunk_overlap=settings.knowledge.chunk_overlap,
        ),
    )
