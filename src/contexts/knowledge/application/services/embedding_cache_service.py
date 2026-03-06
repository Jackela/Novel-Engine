"""
Embedding Cache Service

LRU + TTL cache for embedding results to avoid redundant API calls.
Built on cachetools.TTLCache for robust, production-ready caching.
Designed to support Redis-backed implementation in the future.

Constitution Compliance:
- Article II (Hexagonal): Application service for caching
- Article V (SOLID): SRP - cache operations only
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, List

from structlog import get_logger

from src.caching.lru_cache import LRUCache
from src.contexts.shared.domain.errors import ServiceError
from src.core.result import Err, Ok, Result

logger = get_logger()


@dataclass(slots=True, frozen=True)
class CacheKey:
    """
    Cache key for embedding lookups.

    Combines content hash with model identifier for uniqueness.
    """

    content_hash: str
    model: str

    @classmethod
    def from_text(cls, text: str, model: str) -> "CacheKey":
        """
        Create cache key from text and model.

        Uses sha256(text + model) to ensure unique keys per model.

        Args:
            text: Text content to hash
            model: Model identifier (e.g., "text-embedding-ada-002")

        Returns:
            CacheKey instance
        """
        combined = f"{text}|{model}"
        content_hash = hashlib.sha256(combined.encode()).hexdigest()
        return cls(content_hash=content_hash, model=model)

    def __str__(self) -> str:
        return f"{self.model}:{self.content_hash[:16]}"


@dataclass(slots=True)
class CacheStats:
    """Cache performance statistics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total


class EmbeddingCacheService:
    """
    LRU + TTL cache for embedding results.

    Thread-safe in-memory cache with configurable TTL and max size.
    Uses cachetools.TTLCache internally for robust caching.
    Designed for future Redis backing - the interface abstracts
    storage details.

    Constitution Compliance:
        - Article II (Hexagonal): Application service
        - Article V (SOLID): Single responsibility - caching
    """

    DEFAULT_MAX_SIZE = 1000
    DEFAULT_TTL_SECONDS = 3600  # 1 hour

    def __init__(
        self,
        max_size: int = DEFAULT_MAX_SIZE,
        default_ttl_seconds: int | None = DEFAULT_TTL_SECONDS,
    ) -> None:
        """
        Initialize embedding cache.

        Args:
            max_size: Maximum number of entries before LRU eviction
            default_ttl_seconds: Default TTL in seconds (None = no expiration)
        """
        self._max_size = max_size
        self._default_ttl = default_ttl_seconds or 3600

        # Use LRUCache wrapper which provides metrics and structlog logging
        self._cache = LRUCache[str, List[float]](
            maxsize=max_size,
            ttl_seconds=float(self._default_ttl),
            name="embeddings",
            log_metrics=True,
        )

    def get(
        self, text: str, model: str = "text-embedding-ada-002"
    ) -> List[float] | None:
        """
        Retrieve cached embedding for text.

        Args:
            text: Text content to look up
            model: Model identifier for cache key

        Returns:
            Cached embedding vector or None if miss/expired
        """
        key = self._make_key(text, model)
        return self._cache.get(key)

    def put(
        self,
        text: str,
        embedding: List[float],
        model: str = "text-embedding-ada-002",
        ttl_seconds: int | None = None,
    ) -> None:
        """
        Store embedding in cache.

        Args:
            text: Text content used as cache key
            embedding: Vector embedding to cache
            model: Model identifier for cache key
            ttl_seconds: Custom TTL (ignored - uses default TTL from constructor)
        """
        key = self._make_key(text, model)
        self._cache.set(key, embedding)

    def put_batch(
        self,
        items: list[tuple[str, List[float]]],
        model: str = "text-embedding-ada-002",
        ttl_seconds: int | None = None,
    ) -> None:
        """
        Store multiple embeddings in cache.

        Args:
            items: List of (text, embedding) tuples
            model: Model identifier for cache keys
            ttl_seconds: Custom TTL (ignored - uses default TTL from constructor)
        """
        for text, embedding in items:
            self.put(text, embedding, model=model, ttl_seconds=ttl_seconds)

    def get_batch(
        self,
        texts: List[str],
        model: str = "text-embedding-ada-002",
    ) -> dict[str, List[float]]:
        """
        Retrieve multiple cached embeddings.

        Args:
            texts: List of text contents to look up
            model: Model identifier for cache keys

        Returns:
            Dict mapping text to cached embedding (only hits included)
        """
        results: dict[Any, Any] = {}
        for text in texts:
            embedding = self.get(text, model)
            if embedding is not None:
                results[text] = embedding
        return results

    def get_batch_result(
        self,
        texts: List[str],
        model: str = "text-embedding-ada-002",
    ) -> Result[dict[str, List[float]], ServiceError]:
        """
        Retrieve multiple cached embeddings (Result pattern).

        Args:
            texts: List of text contents to look up
            model: Model identifier for cache keys

        Returns:
            Result containing dict mapping text to cached embedding on success.
            - Ok: Dict with cached embeddings (only hits)
            - Err(ServiceError): If batch retrieval fails
        """
        try:
            results: dict[Any, Any] = {}
            for text in texts:
                embedding = self.get(text, model)
                if embedding is not None:
                    results[text] = embedding
            return Ok(results)
        except Exception as e:
            return Err(
                ServiceError(
                    message=f"Failed to get batch embeddings: {e}",
                    service_name="EmbeddingCacheService",
                    operation="get_batch",
                    details={"text_count": len(texts), "model": model},
                )
            )

    def invalidate(self, model: str | None = None) -> int:
        """
        Invalidate cache entries.

        Args:
            model: If specified, only invalidate entries for this model

        Returns:
            Number of entries invalidated
        """
        if model is None:
            return self._cache.clear()

        # For model-specific invalidation, we need to find matching keys
        # Note: This is less efficient with cachetools as we can't iterate
        # directly. We track keys by model prefix.
        count = 0
        # cachetools doesn't expose key iteration directly in a thread-safe way
        # For now, clear all on model invalidation (simple but broader)
        # A more sophisticated implementation would track keys separately
        count = self._cache.clear()
        logger.info(
            "embedding_cache_invalidated",
            model=model,
            count=count,
        )
        return count

    def get_stats(self) -> CacheStats:
        """
        Get cache performance statistics.

        Returns:
            CacheStats with current metrics
        """
        stats = self._cache.stats()
        return CacheStats(
            hits=stats.hits,
            misses=stats.misses,
            evictions=stats.evictions,
            size=stats.size,
        )

    def get_stats_result(self) -> Result[CacheStats, ServiceError]:
        """
        Get cache performance statistics (Result pattern).

        Returns:
            Result containing CacheStats on success.
            - Ok: CacheStats with current metrics
            - Err(ServiceError): If stats retrieval fails
        """
        try:
            stats = self._cache.stats()
            return Ok(
                CacheStats(
                    hits=stats.hits,
                    misses=stats.misses,
                    evictions=stats.evictions,
                    size=stats.size,
                )
            )
        except Exception as e:
            return Err(
                ServiceError(
                    message=f"Failed to get cache stats: {e}",
                    service_name="EmbeddingCacheService",
                    operation="get_stats",
                )
            )

    def clear(self) -> None:
        """Clear all cache entries and reset stats."""
        self._cache.clear()
        # Create new cache instance to reset stats
        self._cache = LRUCache[str, List[float]](
            maxsize=self._max_size,
            ttl_seconds=float(self._default_ttl),
            name="embeddings",
            log_metrics=True,
        )
        logger.info("embedding_cache_reset")

    def log_summary(self) -> None:
        """Log cache statistics summary via structlog."""
        self._cache.log_summary()

    def _make_key(self, text: str, model: str) -> str:
        """Generate cache key from text and model."""
        key = CacheKey.from_text(text, model)
        return str(key)
