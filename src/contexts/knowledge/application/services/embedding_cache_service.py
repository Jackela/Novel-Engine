"""
Embedding Cache Service

LRU + TTL cache for embedding results to avoid redundant API calls.
Designed to support Redis-backed implementation in the future.

Constitution Compliance:
- Article II (Hexagonal): Application service for caching
- Article V (SOLID): SRP - cache operations only
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional

from structlog import get_logger

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
class CacheEntry:
    """Cached embedding with metadata."""

    embedding: List[float]
    created_ts: float
    ttl_seconds: Optional[int] = None

    def is_expired(self, now: float) -> bool:
        """Check if entry has expired."""
        if self.ttl_seconds is None:
            return False
        return (now - self.created_ts) >= self.ttl_seconds


@dataclass(slots=True)
class CacheStats:
    """Cache performance statistics."""

    hits: int = 0
    misses: int = 0
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
    ):
        """
        Initialize embedding cache.

        Args:
            max_size: Maximum number of entries before LRU eviction
            default_ttl_seconds: Default TTL in seconds (None = no expiration)
        """
        self._max_size = max_size
        self._default_ttl = default_ttl_seconds
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # Track LRU order
        self._stats = CacheStats()

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
        import time

        key = CacheKey.from_text(text, model)
        key_str = str(key)

        entry = self._cache.get(key_str)
        if entry is None:
            self._stats.misses += 1
            logger.debug(
                "embedding_cache_miss",
                key=str(key),
                model=model,
            )
            return None

        if entry.is_expired(time.time()):
            # Remove expired entry
            del self._cache[key_str]
            self._access_order.remove(key_str)
            self._stats.misses += 1
            self._stats.size -= 1
            logger.debug(
                "embedding_cache_expired",
                key=str(key),
                model=model,
            )
            return None

        # Update LRU order
        self._access_order.remove(key_str)
        self._access_order.append(key_str)

        self._stats.hits += 1
        logger.debug(
            "embedding_cache_hit",
            key=str(key),
            model=model,
        )
        return entry.embedding

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
            ttl_seconds: Custom TTL (None = use default)
        """
        import time

        key = CacheKey.from_text(text, model)
        key_str = str(key)

        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        entry = CacheEntry(
            embedding=embedding,
            created_ts=time.time(),
            ttl_seconds=ttl,
        )

        # Update or insert
        if key_str in self._cache:
            self._access_order.remove(key_str)
        else:
            self._stats.size += 1

        self._cache[key_str] = entry
        self._access_order.append(key_str)

        # Evict if needed
        self._evict_if_needed()

        logger.debug(
            "embedding_cache_put",
            key=str(key),
            model=model,
            ttl_seconds=ttl,
            cache_size=self._stats.size,
        )

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
            ttl_seconds: Custom TTL (None = use default)
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
        results = {}
        for text in texts:
            embedding = self.get(text, model)
            if embedding is not None:
                results[text] = embedding
        return results

    def invalidate(self, model: str | None = None) -> int:
        """
        Invalidate cache entries.

        Args:
            model: If specified, only invalidate entries for this model

        Returns:
            Number of entries invalidated
        """
        if model is None:
            count = len(self._cache)
            self._cache.clear()
            self._access_order.clear()
            self._stats.size = 0
            logger.info("embedding_cache_cleared", count=count)
            return count

        # Invalidate by model prefix
        to_remove = [
            key_str for key_str in self._cache.keys() if key_str.startswith(f"{model}:")
        ]
        for key_str in to_remove:
            del self._cache[key_str]
            self._access_order.remove(key_str)

        self._stats.size = len(self._cache)
        logger.info(
            "embedding_cache_invalidated",
            model=model,
            count=len(to_remove),
        )
        return len(to_remove)

    def get_stats(self) -> CacheStats:
        """
        Get cache performance statistics.

        Returns:
            CacheStats with current metrics
        """
        return CacheStats(
            hits=self._stats.hits,
            misses=self._stats.misses,
            size=self._stats.size,
        )

    def clear(self) -> None:
        """Clear all cache entries and reset stats."""
        self._cache.clear()
        self._access_order.clear()
        self._stats = CacheStats()
        logger.info("embedding_cache_reset")

    def _evict_if_needed(self) -> None:
        """Evict least recently used entries if over capacity."""
        while len(self._cache) > self._max_size:
            # Remove LRU entry
            lru_key = self._access_order.pop(0)
            del self._cache[lru_key]
            self._stats.size -= 1
            logger.debug(
                "embedding_cache_evicted",
                key=lru_key,
                cache_size=self._stats.size,
            )
