"""
Cached Embedding Service Adapter

Wraps an embedding service with caching layer to avoid redundant API calls.
Implements IEmbeddingService port interface.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter with caching
- Article V (SOLID): Decorator pattern - adds caching without changing delegate
"""

from __future__ import annotations

from typing import List, Optional

from structlog import get_logger

from src.contexts.knowledge.application.ports.i_embedding_service import (
    IEmbeddingService,
)
from src.contexts.knowledge.application.services.embedding_cache_service import (
    CacheStats,
    EmbeddingCacheService,
)

logger = get_logger()


class CachedEmbeddingService(IEmbeddingService):
    """
    Embedding service with LRU + TTL cache wrapper.

    Delegates to an underlying embedding service (e.g., OpenAI API)
    while caching results to avoid redundant API calls.

    On cache miss, calls delegate and caches the result.
    On delegate failure, propagates error without caching.

    Constitution Compliance:
        - Article II (Hexagonal): Adapter for embedding service
        - Article V (SOLID): SRP - caching logic only
    """

    def __init__(
        self,
        delegate: IEmbeddingService,
        cache_service: Optional[EmbeddingCacheService] = None,
        model: str = "text-embedding-ada-002",
    ):
        """
        Initialize cached embedding service.

        Args:
            delegate: Underlying embedding service to call on cache miss
            cache_service: Optional custom cache (creates default if None)
            model: Model identifier for cache keys
        """
        self._delegate = delegate
        self._cache = cache_service or EmbeddingCacheService()
        self._model = model

    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding with caching.

        Args:
            text: Text content to embed

        Returns:
            Embedding vector (cached or fresh)

        Raises:
            EmbeddingError: If delegate fails
            ValueError: If text is empty
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")

        # Check cache first
        cached = self._cache.get(text, self._model)
        if cached is not None:
            logger.debug(
                "cached_embedding_hit",
                text_length=len(text),
                model=self._model,
            )
            return cached

        # Cache miss - call delegate
        logger.debug(
            "cached_embedding_miss",
            text_length=len(text),
            model=self._model,
        )
        embedding = await self._delegate.embed(text)

        # Store in cache
        self._cache.put(text, embedding, self._model)

        return embedding

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 100,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with caching.

        Checks cache for all texts first, then calls delegate
        only for cache misses in batches.

        Args:
            texts: List of text strings to embed
            batch_size: Batch size for delegate calls

        Returns:
            List of embedding vectors, same order as input
        """
        if not texts:
            return []

        # Check cache for all texts
        cached_results = self._cache.get_batch(texts, self._model)

        # Separate cache hits from misses
        hit_indices = []
        miss_indices = []
        miss_texts = []

        for i, text in enumerate(texts):
            if text in cached_results:
                hit_indices.append(i)
            else:
                miss_indices.append(i)
                miss_texts.append(text)

        logger.debug(
            "cached_embedding_batch_stats",
            total=len(texts),
            hits=len(hit_indices),
            misses=len(miss_indices),
            model=self._model,
        )

        # Fetch misses from delegate
        miss_embeddings: List[List[float]] = []
        if miss_texts:
            miss_embeddings = await self._delegate.embed_batch(miss_texts, batch_size)

            # Cache the results
            self._cache.put_batch(
                list(zip(miss_texts, miss_embeddings, strict=True)),
                self._model,
            )

        # Combine results in original order
        results: List[List[float]] = []

        # Build result list in original order
        text_to_result: dict[str, List[float]] = {}

        # Add cache hits
        for text in cached_results:
            text_to_result[text] = cached_results[text]

        # Add cache misses
        for i, text in enumerate(miss_texts):
            text_to_result[text] = miss_embeddings[i]

        # Reconstruct in original order
        for text in texts:
            results.append(text_to_result[text])

        return results

    def get_dimension(self) -> int:
        """
        Get embedding dimensionality from delegate.

        Returns:
            Number of dimensions in embedding vectors
        """
        return self._delegate.get_dimension()

    def clear_cache(self) -> None:
        """
        Clear the embedding cache.

        Does not affect the delegate's internal state.
        """
        self._cache.clear()
        logger.info("cached_embedding_cache_cleared")

    def get_cache_stats(self) -> CacheStats:
        """
        Get cache performance statistics.

        Returns:
            CacheStats with hits, misses, size, and hit rate
        """
        return self._cache.get_stats()

    def invalidate_cache(self, model: str | None = None) -> int:
        """
        Invalidate cache entries.

        Args:
            model: If specified, only invalidate entries for this model

        Returns:
            Number of entries invalidated
        """
        target_model = model or self._model
        return self._cache.invalidate(target_model)
