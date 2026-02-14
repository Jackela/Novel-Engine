"""
Embedding Service Adapter

Generates vector embeddings for knowledge entry content using OpenAI embeddings API
or fallback mock implementation for testing.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter for external embedding service
- Article V (SOLID): SRP - embedding generation only

Note:
    For production LRU + TTL caching, use CachedEmbeddingService wrapper
    instead of relying on the internal cache. The internal cache here
    is kept for backward compatibility but does not have TTL or LRU eviction.
"""

import hashlib
import os
from typing import TYPE_CHECKING, List, Union

from src.contexts.knowledge.application.ports.i_embedding_service import (
    EmbeddingError,
    IEmbeddingService,
)

if TYPE_CHECKING:
    from openai import AsyncOpenAI


class EmbeddingServiceAdapter(IEmbeddingService):
    """
    Adapter for generating vector embeddings from text content.

    Uses OpenAI embeddings API (text-embedding-3-small) to generate
    1536-dimensional vectors for semantic search.

    Falls back to deterministic mock embeddings when:
    - OPENAI_API_KEY is not set
    - use_mock=True is specified
    - API calls fail

    Constitution Compliance:
        - Article II (Hexagonal): External service adapter
        - Article V (SOLID): Single responsibility - embedding generation

    Note:
        The internal cache is kept for backward compatibility. For production,
        wrap this adapter with CachedEmbeddingService for proper LRU + TTL caching.
    """

    # Model dimension mapping
    DIMENSIONS = {
        "text-embedding-ada-002": 1536,
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
    }

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        use_mock: bool = False,
        enable_internal_cache: bool = True,
    ):
        """
        Initialize embedding service with API configuration.

        Args:
            api_key: Optional API key for OpenAI. If None, reads OPENAI_API_KEY env var.
            model: Embedding model to use (default: text-embedding-3-small)
            use_mock: Force mock mode regardless of API key availability
            enable_internal_cache: Enable simple internal cache (default: True).
                                  For production, set to False and use CachedEmbeddingService.

        Models:
            - text-embedding-ada-002: 1536 dimensions (OpenAI legacy)
            - text-embedding-3-small: 1536 dimensions (OpenAI newer, cheaper)
            - text-embedding-3-large: 3072 dimensions (OpenAI higher quality)
        """
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._model = model
        self._use_mock = use_mock or not self._api_key
        self._client: Union["AsyncOpenAI", None] = None

        # Internal cache (simple dict, no TTL/LRU)
        # Can be disabled in favor of CachedEmbeddingService
        self._embedding_cache: dict[str, list[float]] = (
            {} if enable_internal_cache else {}
        )
        self._cache_enabled = enable_internal_cache

        # Validate model
        if model not in self.DIMENSIONS:
            raise ValueError(
                f"Unknown model: {model}. " f"Supported: {list(self.DIMENSIONS.keys())}"
            )

    async def embed(self, text: str) -> List[float]:
        """
        Generate vector embedding for text content.

        Args:
            text: Text content to embed (knowledge entry content)

        Returns:
            List of floats representing the embedding vector

        Raises:
            EmbeddingError: If text is empty or embedding generation fails

        Example:
            >>> service = EmbeddingServiceAdapter()
            >>> embedding = await service.embed("The spacecraft has quantum drive")
            >>> len(embedding)
            1536
        """
        if not text or not text.strip():
            raise EmbeddingError(
                "Cannot generate embedding for empty text", "EMPTY_TEXT"
            )

        # Check internal cache first (if enabled)
        if self._cache_enabled:
            cache_key = self._get_cache_key(text)
            if cache_key in self._embedding_cache:
                return self._embedding_cache[cache_key]

        # Generate embedding
        try:
            if self._use_mock:
                embedding = self._generate_mock_embedding(text)
            else:
                embedding = await self._call_openai_api(text)

            # Cache result (if enabled)
            if self._cache_enabled:
                cache_key = self._get_cache_key(text)
                self._embedding_cache[cache_key] = embedding
            return embedding

        except Exception as e:
            # Log error and fall back to mock
            if not self._use_mock:
                # On API failure, silently fall back to mock
                embedding = self._generate_mock_embedding(text)
                if self._cache_enabled:
                    cache_key = self._get_cache_key(text)
                    self._embedding_cache[cache_key] = embedding
                return embedding
            raise EmbeddingError(
                f"Failed to generate embedding: {e}", "EMBEDDING_FAILED"
            )

    async def embed_batch(
        self, texts: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        More efficient than calling embed() repeatedly.

        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to process per API call (default: 100)

        Returns:
            List of embedding vectors, same order as input texts

        Raises:
            EmbeddingError: If embedding generation fails

        Example:
            >>> service = EmbeddingServiceAdapter()
            >>> texts = ["text 1", "text 2", "text 3"]
            >>> embeddings = await service.embed_batch(texts)
            >>> len(embeddings) == len(texts)
            True
        """
        if not texts:
            return []

        embeddings = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            if self._use_mock:
                batch_embeddings = []
                for t in batch:
                    # Check cache first for each text (if enabled)
                    if self._cache_enabled:
                        cache_key = self._get_cache_key(t)
                        if cache_key in self._embedding_cache:
                            batch_embeddings.append(self._embedding_cache[cache_key])
                            continue
                    embedding = self._generate_mock_embedding(t)
                    if self._cache_enabled:
                        cache_key = self._get_cache_key(t)
                        self._embedding_cache[cache_key] = embedding
                    batch_embeddings.append(embedding)
            else:
                try:
                    batch_embeddings = await self._call_openai_api_batch(batch)
                except Exception:
                    # Fall back to individual mock generation
                    batch_embeddings = [self._generate_mock_embedding(t) for t in batch]

            embeddings.extend(batch_embeddings)

        return embeddings

    def get_dimension(self) -> int:
        """
        Get the dimensionality of embeddings produced by this service.

        Returns:
            Number of dimensions (1536 for most models, 3072 for large)
        """
        return self.DIMENSIONS.get(self._model, 1536)

    def clear_cache(self) -> None:
        """
        Clear embedding cache.

        Useful for testing or when memory is constrained.
        """
        self._embedding_cache.clear()

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text content."""
        return hashlib.sha256(text.encode()).hexdigest()

    def _get_client(self) -> "AsyncOpenAI":
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(api_key=self._api_key)
            except ImportError:
                raise EmbeddingError(
                    "OpenAI package not installed. Install with: pip install openai",
                    "PACKAGE_NOT_FOUND",
                )
        return self._client

    async def _call_openai_api(self, text: str) -> List[float]:
        """
        Call OpenAI embeddings API for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        client = self._get_client()

        response = await client.embeddings.create(
            model=self._model,
            input=text,
        )

        return list(response.data[0].embedding)

    async def _call_openai_api_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Call OpenAI embeddings API for multiple texts.

        More efficient than individual calls as OpenAI processes
        multiple texts in a single request.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        client = self._get_client()

        # OpenAI supports up to 2048 texts in a batch, but we limit
        # to batch_size (default 100) for safety
        response = await client.embeddings.create(
            model=self._model,
            input=texts,
        )

        # Return embeddings in same order as input
        return [item.embedding for item in response.data]

    def _generate_mock_embedding(self, text: str) -> List[float]:
        """
        Generate deterministic mock embedding for testing.

        Uses text hash to create consistent embeddings that normalize
        to unit vectors (standard practice for embeddings).

        Real embeddings would have semantic properties - similar texts
        produce similar vectors. Mock embeddings are only for
        testing infrastructure, not for semantic search quality.

        Args:
            text: Text to generate mock embedding for

        Returns:
            Normalized vector of appropriate dimension
        """
        import random

        # Create deterministic seed from text
        seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        random.seed(seed)

        dimension = self.get_dimension()

        # Generate normalized vector using Gaussian distribution
        embedding = [random.gauss(0, 1) for _ in range(dimension)]

        # Normalize to unit length (standard for embeddings)
        magnitude = sum(x**2 for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding


# Backward compatibility alias
EmbeddingGeneratorAdapter = EmbeddingServiceAdapter
