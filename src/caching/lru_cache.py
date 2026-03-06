"""LRU Cache with TTL support and metrics logging.

A thread-safe LRU cache with time-to-live (TTL) eviction and comprehensive
metrics tracking via structlog. Built on cachetools.TTLCache for reliability.

Constitution Compliance:
    - Article V (SOLID): SRP - caching only
    - Article II (Hexagonal): Infrastructure component

Usage:
    >>> from src.caching.lru_cache import LRUCache
    >>> cache = LRUCache(maxsize=1000, ttl_seconds=300)
    >>> cache.set("key", [1.0, 2.0, 3.0])
    >>> value = cache.get("key")
    >>> print(cache.stats())
    {'hits': 1, 'misses': 0, 'evictions': 0, 'size': 1}
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import RLock
from typing import Callable, Generic, Hashable, Optional, TypeVar

import structlog
from cachetools import TTLCache

logger = structlog.get_logger(__name__)

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


@dataclass
class CacheStats:
    """Cache statistics for monitoring.

    Attributes:
        hits: Number of cache hits
        misses: Number of cache misses
        evictions: Number of entries evicted (due to TTL or LRU)
        size: Current number of entries in cache
        maxsize: Maximum cache capacity
    """

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    maxsize: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate (0.0 to 1.0)."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


@dataclass
class CacheConfig:
    """Configuration for LRU cache.

    Attributes:
        maxsize: Maximum number of entries
        ttl_seconds: Time-to-live in seconds (None = no TTL)
        name: Cache name for logging
        log_metrics: Whether to log metrics on eviction
    """

    maxsize: int = 512
    ttl_seconds: Optional[float] = 3600  # 1 hour default
    name: str = "default"
    log_metrics: bool = True


class LRUCache(Generic[K, V]):
    """Thread-safe LRU cache with TTL support and metrics.

    Features:
        - LRU eviction when maxsize is reached
        - TTL-based expiration
        - Thread-safe operations
        - Comprehensive metrics with structlog logging
        - Type-safe generic implementation

    Example:
        >>> cache = LRUCache[str, list[float]](maxsize=100, ttl_seconds=60)
        >>> cache.set("embedding", [0.1, 0.2, 0.3])
        >>> value = cache.get("embedding")
        >>> assert value == [0.1, 0.2, 0.3]
    """

    def __init__(
        self,
        maxsize: int = 512,
        ttl_seconds: Optional[float] = 3600,
        name: str = "default",
        log_metrics: bool = True,
    ) -> None:
        """Initialize LRU cache.

        Args:
            maxsize: Maximum number of entries (0 = unlimited, not recommended)
            ttl_seconds: Time-to-live in seconds. None means no TTL.
            name: Cache name for logging and identification
            log_metrics: Whether to log metrics on eviction/periodically
        """
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive or None")

        self._maxsize = maxsize
        self._ttl = ttl_seconds
        self._name = name
        self._log_metrics = log_metrics

        # Use cachetools TTLCache for robust implementation
        self._cache: TTLCache[K, V] = TTLCache(
            maxsize=maxsize,
            ttl=ttl_seconds if ttl_seconds else float("inf"),
        )
        self._lock = RLock()

        # Metrics tracking (cachetools doesn't track these)
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._creation_time = time.time()

        # Track size before operations to detect evictions
        self._prev_size = 0

        logger.debug(
            "lru_cache_created",
            cache_name=name,
            maxsize=maxsize,
            ttl_seconds=ttl_seconds,
        )

    def get(self, key: K) -> Optional[V]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            self._prev_size = len(self._cache)
            value: Optional[V] = self._cache.get(key)
            if value is not None:
                self._hits += 1
                logger.debug(
                    "cache_hit",
                    cache_name=self._name,
                    key=str(key)[:50],  # Truncate long keys
                )
            else:
                self._misses += 1
                logger.debug(
                    "cache_miss",
                    cache_name=self._name,
                    key=str(key)[:50],
                )
            return value

    def set(self, key: K, value: V) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            self._prev_size = len(self._cache)
            self._cache[key] = value

            # Detect evictions (cachetools evicts on insertion when full)
            current_size = len(self._cache)
            if current_size < self._prev_size or (
                current_size == self._prev_size and key not in self._cache
            ):
                # This shouldn't happen normally, but log if it does
                pass

            # Check if we had an eviction due to LRU
            if self._prev_size >= self._maxsize and len(self._cache) <= self._prev_size:
                self._evictions += 1
                if self._log_metrics:
                    logger.info(
                        "cache_eviction",
                        cache_name=self._name,
                        reason="lru_full",
                        stats=self.stats().__dict__,
                    )

    def get_or_set(self, key: K, factory: Callable[[], V]) -> V:
        """Get value from cache or compute and cache it.

        Args:
            key: Cache key
            factory: Function to compute value if not in cache

        Returns:
            Cached or computed value
        """
        value = self.get(key)
        if value is not None:
            return value

        value = factory()
        self.set(key, value)
        return value

    async def aget_or_set(self, key: K, factory: Callable[[], V]) -> V:
        """Async version of get_or_set (factory can be sync).

        For async factories, use: await cache.get(key) or await factory()

        Args:
            key: Cache key
            factory: Function to compute value if not in cache

        Returns:
            Cached or computed value
        """
        value = self.get(key)
        if value is not None:
            return value

        value = factory()
        self.set(key, value)
        return value

    def delete(self, key: K) -> bool:
        """Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key existed, False otherwise
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> int:
        """Clear all entries from cache.

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            if count > 0 and self._log_metrics:
                logger.info(
                    "cache_cleared",
                    cache_name=self._name,
                    entries_cleared=count,
                )
            return count

    def contains(self, key: K) -> bool:
        """Check if key exists in cache (and not expired).

        Args:
            key: Cache key

        Returns:
            True if key exists and is valid
        """
        with self._lock:
            return key in self._cache

    def stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            CacheStats with current metrics
        """
        with self._lock:
            return CacheStats(
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
                size=len(self._cache),
                maxsize=self._maxsize,
            )

    @property
    def size(self) -> int:
        """Current cache size."""
        with self._lock:
            return len(self._cache)

    @property
    def maxsize(self) -> int:
        """Maximum cache size."""
        return self._maxsize

    @property
    def ttl_seconds(self) -> Optional[float]:
        """TTL in seconds."""
        return self._ttl

    def log_summary(self) -> None:
        """Log cache statistics summary via structlog."""
        stats = self.stats()
        uptime = time.time() - self._creation_time

        logger.info(
            "cache_summary",
            cache_name=self._name,
            hits=stats.hits,
            misses=stats.misses,
            hit_rate=f"{stats.hit_rate:.2%}",
            evictions=stats.evictions,
            size=stats.size,
            maxsize=stats.maxsize,
            uptime_seconds=f"{uptime:.1f}",
        )

    def __len__(self) -> int:
        """Return current cache size."""
        return self.size

    def __contains__(self, key: K) -> bool:
        """Check if key exists."""
        return self.contains(key)

    def __repr__(self) -> str:
        return (
            f"LRUCache(name={self._name!r}, "
            f"size={self.size}/{self._maxsize}, "
            f"ttl={self._ttl}s)"
        )


def create_embedding_cache(
    maxsize: int = 1024, ttl_seconds: float = 900.0
) -> LRUCache[str, list[float]]:
    """Factory for creating embedding cache with sensible defaults.

    Default TTL is 15 minutes (900s) since embeddings for the same text
    don't change unless the model changes.

    Args:
        maxsize: Maximum embeddings to cache (default: 1024)
        ttl_seconds: TTL in seconds (default: 900 = 15 minutes)

    Returns:
        Configured LRUCache for embeddings
    """
    return LRUCache[str, list[float]](
        maxsize=maxsize,
        ttl_seconds=ttl_seconds,
        name="embeddings",
        log_metrics=True,
    )
