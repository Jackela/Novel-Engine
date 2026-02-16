"""
Embedding Service Port Interface

Defines the contract for embedding generation services.

Constitution Compliance:
- Article II (Hexagonal): Application layer port interface
- Article V (SOLID): Interface segregation - embedding generation only
"""

from abc import ABC, abstractmethod
from typing import List


class EmbeddingError(Exception):
    """Exception raised for embedding service errors."""

    def __init__(self, message: str, code: str = "EMBEDDING_ERROR"):
        """
        Initialize embedding error.

        Args:
            message: Human-readable error message
            code: Machine-readable error code for categorization
        """
        self.code = code
        super().__init__(message)


class IEmbeddingService(ABC):
    """
    Port interface for embedding generation services.

    Implementations provide vector embeddings for text content,
    enabling semantic search and retrieval-augmented generation.

    Constitution Compliance:
        - Article II (Hexagonal): Port interface for external services
        - Article V (SOLID): Single responsibility - embedding generation
    """

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """
        Generate vector embedding for a single text.

        Args:
            text: Text content to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
            ValueError: If text is empty or invalid

        Example:
            >>> service = IEmbeddingService()
            >>> embedding = await service.embed("The brave warrior fought")
            >>> len(embedding)
            1536
        """
        ...

    @abstractmethod
    async def embed_batch(
        self, texts: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.

        More efficient than calling embed() repeatedly as implementations
        can batch API calls.

        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process per batch (default: 100)

        Returns:
            List of embedding vectors, same order as input texts

        Raises:
            EmbeddingError: If embedding generation fails

        Example:
            >>> service = IEmbeddingService()
            >>> texts = ["text 1", "text 2", "text 3"]
            >>> embeddings = await service.embed_batch(texts)
            >>> len(embeddings) == len(texts)
            True
        """
        ...

    @abstractmethod
    def get_dimension(self) -> int:
        """
        Get the dimensionality of embeddings produced by this service.

        Returns:
            Number of dimensions in embedding vectors (e.g., 1536, 3072)
        """
        ...

    @abstractmethod
    def clear_cache(self) -> None:
        """
        Clear any internal caching.

        Implementations may cache embeddings to avoid redundant API calls.
        This method clears those caches.
        """
        ...
