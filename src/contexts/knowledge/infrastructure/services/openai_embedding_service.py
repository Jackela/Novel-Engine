"""OpenAI embedding service implementation.

This module provides an OpenAI-based implementation of the embedding
service port interface for text vectorization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.contexts.knowledge.application.ports.i_embedding_service import (
    EmbeddingError,
    IEmbeddingService,
)

if TYPE_CHECKING:
    import openai


class OpenAIEmbeddingService(IEmbeddingService):
    """OpenAI embedding service implementation.

    Uses OpenAI API to generate text embeddings.

    Example:
        >>> service = OpenAIEmbeddingService(api_key="sk-...")
        >>> embedding = await service.embed("Hello world")
        >>> print(len(embedding))  # 1536 for text-embedding-3-small
    """

    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        """Initialize OpenAI embedding service.

        Args:
            api_key: OpenAI API key
            model: Embedding model name (default: text-embedding-3-small)

        Raises:
            ImportError: If openai package is not installed
            ValueError: If api_key is empty
        """
        if not api_key:
            raise ValueError("API key cannot be empty")

        self._api_key = api_key
        self._model = model
        self._client: openai.AsyncOpenAI | None = None
        self._dimension: int | None = None

    def _get_client(self) -> "openai.AsyncOpenAI":
        """Get or create OpenAI client.

        Returns:
            OpenAI async client instance

        Raises:
            ImportError: If openai is not installed
        """
        if self._client is None:
            try:
                import openai

                self._client = openai.AsyncOpenAI(api_key=self._api_key)
            except ImportError as e:
                raise ImportError(
                    "openai is required for OpenAIEmbeddingService. "
                    "Install it with: pip install openai"
                ) from e
        return self._client

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
            ValueError: If text is empty
        """
        if not text:
            raise ValueError("Text cannot be empty")

        try:
            client = self._get_client()
            response = await client.embeddings.create(
                model=self._model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embedding: {e}") from e

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails
            ValueError: If texts list is empty
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")

        # Filter out empty strings
        valid_texts = [t for t in texts if t]
        if not valid_texts:
            raise ValueError("All texts are empty")

        try:
            client = self._get_client()
            response = await client.embeddings.create(
                model=self._model,
                input=valid_texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            raise EmbeddingError(f"Failed to generate batch embeddings: {e}") from e

    def get_dimension(self) -> int:
        """Get the dimension of the embeddings.

        Returns:
            Embedding dimension based on model

        Note:
            Returns cached dimension if already queried.
        """
        # Cache dimensions for known models
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

        if self._dimension is None:
            self._dimension = model_dimensions.get(self._model, 1536)

        return self._dimension
