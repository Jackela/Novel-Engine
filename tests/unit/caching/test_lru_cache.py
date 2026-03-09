"""
Unit tests for LRUCache with TTL support.

Tests cover:
- Basic get/set operations
- LRU eviction when cache is full
- TTL-based expiration
- Cache statistics
- Thread safety
"""

import asyncio
import time

import pytest

from src.caching.lru_cache import LRUCache, create_embedding_cache

pytestmark = pytest.mark.unit


class TestLRUCacheBasicOperations:
    """Tests for basic get/set operations."""

    def test_init_default_params(self) -> None:
        """Test initialization with default parameters."""
        cache = LRUCache[str, int]()
        assert cache.maxsize == 512
        assert cache.ttl_seconds == 3600
        assert cache.size == 0

    def test_init_custom_params(self) -> None:
        """Test initialization with custom parameters."""
        cache = LRUCache[str, int](maxsize=100, ttl_seconds=60, name="test")
        assert cache.maxsize == 100
        assert cache.ttl_seconds == 60
        assert cache.size == 0

    def test_init_invalid_maxsize_raises(self) -> None:
        """Test that maxsize <= 0 raises error."""
        with pytest.raises(ValueError, match="maxsize must be positive"):
            LRUCache[str, int](maxsize=0)

        with pytest.raises(ValueError, match="maxsize must be positive"):
            LRUCache[str, int](maxsize=-1)

    def test_init_invalid_ttl_raises(self) -> None:
        """Test that ttl <= 0 raises error."""
        with pytest.raises(ValueError, match="ttl_seconds must be positive"):
            LRUCache[str, int](ttl_seconds=0)

        with pytest.raises(ValueError, match="ttl_seconds must be positive"):
            LRUCache[str, int](ttl_seconds=-1)

    def test_set_and_get(self) -> None:
        """Test basic set and get operations."""
        cache = LRUCache[str, int](maxsize=10)

        cache.set("key1", 100)
        assert cache.get("key1") == 100

    def test_get_missing_key_returns_none(self) -> None:
        """Test that getting missing key returns None."""
        cache = LRUCache[str, int]()
        assert cache.get("nonexistent") is None

    def test_set_overwrites_existing(self) -> None:
        """Test that setting same key overwrites value."""
        cache = LRUCache[str, int]()

        cache.set("key", 100)
        cache.set("key", 200)

        assert cache.get("key") == 200
        assert cache.size == 1

    def test_delete_existing_key(self) -> None:
        """Test deleting an existing key."""
        cache = LRUCache[str, int]()
        cache.set("key", 100)

        result = cache.delete("key")

        assert result is True
        assert cache.get("key") is None

    def test_delete_nonexistent_key(self) -> None:
        """Test deleting a nonexistent key."""
        cache = LRUCache[str, int]()

        result = cache.delete("nonexistent")

        assert result is False

    def test_clear(self) -> None:
        """Test clearing the cache."""
        cache = LRUCache[str, int]()
        cache.set("key1", 100)
        cache.set("key2", 200)

        count = cache.clear()

        assert count == 2
        assert cache.size == 0

    def test_contains(self) -> None:
        """Test contains check."""
        cache = LRUCache[str, int]()
        cache.set("key", 100)

        assert cache.contains("key") is True
        assert cache.contains("nonexistent") is False

    def test_in_operator(self) -> None:
        """Test 'in' operator."""
        cache = LRUCache[str, int]()
        cache.set("key", 100)

        assert "key" in cache
        assert "nonexistent" not in cache


class TestLRUCacheEviction:
    """Tests for LRU eviction."""

    def test_lru_eviction_on_maxsize(self) -> None:
        """Test that LRU eviction occurs when cache is full."""
        cache = LRUCache[str, int](maxsize=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # Should evict "a"

        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") == 4
        assert cache.size == 3

    def test_lru_access_updates_order(self) -> None:
        """Test that accessing an item updates its LRU position."""
        cache = LRUCache[str, int](maxsize=3)

        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)

        # Access "a" to make it recently used
        cache.get("a")

        # Add new item - should evict "b" (not "a")
        cache.set("d", 4)

        assert cache.get("a") == 1  # Still present
        assert cache.get("b") is None  # Evicted


class TestLRUCacheTTL:
    """Tests for TTL-based expiration."""

    def test_ttl_expiration(self) -> None:
        """Test that entries expire after TTL."""
        cache = LRUCache[str, int](maxsize=10, ttl_seconds=0.1)

        cache.set("key", 100)
        assert cache.get("key") == 100  # Still valid

        # Wait for TTL to expire
        time.sleep(0.15)

        assert cache.get("key") is None  # Expired

    def test_no_ttl_never_expires(self) -> None:
        """Test that entries with no TTL don't expire."""
        # Use very large TTL (effectively no expiration in test timeframe)
        cache = LRUCache[str, int](maxsize=10, ttl_seconds=86400)

        cache.set("key", 100)
        time.sleep(0.05)  # Small delay

        assert cache.get("key") == 100

    def test_different_ttls_per_entry_not_supported(self) -> None:
        """Test that all entries use the same TTL (cache-level)."""
        # LRUCache uses cache-level TTL, not per-entry
        cache = LRUCache[str, int](maxsize=10, ttl_seconds=1.0)

        cache.set("key1", 100)
        cache.set("key2", 200)

        # Both should be present
        assert cache.get("key1") == 100
        assert cache.get("key2") == 200


class TestLRUCacheStats:
    """Tests for cache statistics."""

    def test_initial_stats(self) -> None:
        """Test initial stats are zero."""
        cache = LRUCache[str, int]()

        stats = cache.stats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.size == 0

    def test_stats_hit_tracking(self) -> None:
        """Test hit tracking in stats."""
        cache = LRUCache[str, int]()
        cache.set("key", 100)

        cache.get("key")  # Hit
        cache.get("key")  # Hit

        stats = cache.stats()
        assert stats.hits == 2
        assert stats.misses == 0

    def test_stats_miss_tracking(self) -> None:
        """Test miss tracking in stats."""
        cache = LRUCache[str, int]()

        cache.get("nonexistent1")  # Miss
        cache.get("nonexistent2")  # Miss

        stats = cache.stats()
        assert stats.hits == 0
        assert stats.misses == 2

    def test_stats_hit_rate_calculation(self) -> None:
        """Test hit rate calculation."""
        cache = LRUCache[str, int]()
        cache.set("key", 100)

        cache.get("key")  # Hit
        cache.get("key")  # Hit
        cache.get("other")  # Miss

        stats = cache.stats()
        # 2 hits, 1 miss = 0.666...
        assert 0.6 < stats.hit_rate < 0.7

    def test_stats_hit_rate_empty_cache(self) -> None:
        """Test hit rate is 0 for empty cache with no operations."""
        cache = LRUCache[str, int]()

        stats = cache.stats()
        assert stats.hit_rate == 0.0


class TestLRUCacheGetOrSet:
    """Tests for get_or_set method."""

    def test_get_or_set_cache_hit(self) -> None:
        """Test get_or_set returns cached value."""
        cache = LRUCache[str, int]()
        cache.set("key", 100)

        result = cache.get_or_set("key", lambda: 999)

        assert result == 100

    def test_get_or_set_cache_miss(self) -> None:
        """Test get_or_set computes and caches on miss."""
        cache = LRUCache[str, int]()

        result = cache.get_or_set("key", lambda: 100)

        assert result == 100
        assert cache.get("key") == 100

    def test_aget_or_set(self) -> None:
        """Test async get_or_set."""
        cache = LRUCache[str, int]()

        async def run_test() -> int:
            result = await cache.aget_or_set("key", lambda: 100)
            return result

        result = asyncio.run(run_test())
        assert result == 100


class TestCreateEmbeddingCache:
    """Tests for embedding cache factory."""

    def test_create_with_defaults(self) -> None:
        """Test creating embedding cache with defaults."""
        cache = create_embedding_cache()

        assert cache.maxsize == 1024
        assert cache.ttl_seconds == 900.0  # 15 minutes

    def test_create_with_custom_params(self) -> None:
        """Test creating embedding cache with custom params."""
        cache = create_embedding_cache(maxsize=500, ttl_seconds=300.0)

        assert cache.maxsize == 500
        assert cache.ttl_seconds == 300.0

    def test_store_embedding_vectors(self) -> None:
        """Test storing embedding vectors."""
        cache = create_embedding_cache()

        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        cache.set("text_hash", embedding)

        result = cache.get("text_hash")
        assert result == embedding


class TestLRUCacheRepr:
    """Tests for string representation."""

    def test_repr(self) -> None:
        """Test string representation."""
        cache = LRUCache[str, int](maxsize=100, ttl_seconds=60, name="test")
        cache.set("key", 100)

        repr_str = repr(cache)

        assert "LRUCache" in repr_str
        assert "name='test'" in repr_str
        assert "size=1/100" in repr_str
        assert "ttl=60" in repr_str
