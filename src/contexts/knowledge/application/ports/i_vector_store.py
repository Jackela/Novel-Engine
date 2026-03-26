"""
Vector Store Port Interface

Defines the interface for vector store implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class QueryResult:
    """Result from a vector store query."""

    id: str
    text: str
    score: float
    metadata: dict[str, Any]


class IVectorStore(ABC):
    """Abstract interface for vector stores."""

    @abstractmethod
    async def upsert(
        self,
        collection: str,
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        ids: list[str],
    ) -> None:
        """Upsert documents into the vector store."""
        raise NotImplementedError

    @abstractmethod
    async def query(
        self,
        query_embedding: list[float],
        n_results: int = 10,
        where: dict[str, Any] | None = None,
        collection: str = "knowledge",
    ) -> list[QueryResult]:
        """Query the vector store."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, collection: str, ids: list[str]) -> None:
        """Delete documents from the vector store."""
        raise NotImplementedError

    @abstractmethod
    async def clear(self, collection: str) -> None:
        """Clear all documents from a collection."""
        raise NotImplementedError

    @abstractmethod
    async def count(self, collection: str) -> int:
        """Count documents in a collection."""
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the vector store is healthy."""
        raise NotImplementedError
