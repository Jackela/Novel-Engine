"""
Embedding Service Port Interface

Defines the interface for embedding service implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingError(Exception):
    """Error during embedding generation."""

    pass


class IEmbeddingService(ABC):
    """Abstract interface for embedding services."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        raise NotImplementedError

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        raise NotImplementedError

    @abstractmethod
    def get_dimension(self) -> int:
        """Get the dimension of the embeddings."""
        raise NotImplementedError
