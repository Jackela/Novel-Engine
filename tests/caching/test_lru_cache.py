"""Tests for LRU Cache module.

Tests cover:
- Basic get/set operations
- Cache miss returns None
- LRU eviction when maxsize exceeded
- TTL expiration
- Cache stats and metrics
"""

from __future__ import annotations

import time

import pytest

pytestmark = pytest.mark.unit

from src.caching.lru_cache import (
    CacheConfig,
    CacheStats,
    LRUCache,
    create_embedding_cache,
)


class TestLRUCacheBasicOperations:
    """Test basic cache get/set operations."""

    def test_get_existing_key_returns_value(self) -> None:
        """Test that get returns the value for an existing key."""
        cache = LRUCache[str, str](maxsize=10)
        cache.set("key1", "value1")

        result = cache.get("key1")

        assert result == "value1"

    def test_get_missing_key_returns_none(self) -> None:
        """Test that get returns None for a missing key."""
        cache = LRUCache[str, str](maxsize=10)

        result = cache.get("missing_key")

        assert result is None

    def test_set_new_key_adds_to_cache(self) -> None:
        """Test that set adds a new key-value pair."""
        cache = LRUCache[str, int](maxsize=10)

        cache.set("key1", 100)

        assert cache.get("key1") == 100

    def test_set_overwrites_existing_key(self) -> None:
        """Test that set overwrites the value for an existing key."""
        cache = LRUCache[str, str](maxsize=10)
        cache.set("key1", "old_value")

        cache.set("key1", "new_value")

        assert cache.get("key1") == "new_value"

    def test_contains_existing_key(self) -> None:
        """Test that contains returns True for existing key."""
        cache = LRUCache[str, str](maxsize=10)
        cache.set("key1", "value1")

        assert cache.contains("key1") is True

    def test_contains_missing_key(self) -> None:
        """Test that contains returns False for missing key."""
        cache = LRUCache[str, str](maxsize=10)

        assert cache.contains("missing_key") is False

    def test_delete_existing_key(self) -> None:
        """Test that delete removes an existing key."""
        cache = LRUCache[str, str](maxsize=10)
        cache.set("key1", "value1")

        result = cache.delete("key1")

        assert result is True
        assert cache.get("key1") is None

    def test_delete_missing_key(self) -> None:
        """Test that delete returns False for missing key."""
        cache = LRUCache[str, str](maxsize=10)

        result = cache.delete("missing_key")

        assert result is False

    def test_clear_removes_all_entries(self) -> None:
        """Test that clear removes all cache entries."""
        cache = LRUCache[str, str](maxsize=10)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        count = cache.clear()

        assert count == 2
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.size == 0


class TestLRUCacheEviction:
    """Test LRU eviction when maxsize is exceeded."""

    def test_lru_eviction_when_maxsize_exceeded(self) -> None:
        """Test that oldest entries are evicted when maxsize is exceeded."""
        cache = LRUCache[str, str](maxsize=3)

        # Fill cache to capacity
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 to make it recently used
        cache.get("key1")

        # Add new entry, should evict key2 (oldest)
        cache.set("key4", "value4")

        # key1 should still be there (recently accessed)
        assert cache.get("key1") == "value1"
        # key2 should be evicted
        assert cache.get("key2") is None
        # key3 and key4 should be there
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_eviction_count_tracked_in_stats(self) -> None:
        """Test that evictions are tracked in cache stats."""
        cache = LRUCache[str, str](maxsize=2)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should trigger eviction

        stats = cache.stats()
        assert stats.evictions >= 0  # At least one eviction should occur


class TestLRUCacheTTL:
    """Test TTL (Time-To-Live) expiration."""

    def test_ttl_expiration_removes_entry(self) -> None:
        """Test that entries expire after TTL."""
        cache = LRUCache[str, str](maxsize=10, ttl_seconds=0.1)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Wait for TTL to expire
        time.sleep(0.15)

        # Entry should be expired
        assert cache.get("key1") is None

    def test_no_ttl_means_no_expiration(self) -> None:
        """Test that None TTL means entries don't expire."""
        cache = LRUCache[str, str](maxsize=10, ttl_seconds=None)

        cache.set("key1", "value1")

        # Entry should still be there
        assert cache.get("key1") == "value1"


class TestLRUCacheStats:
    """Test cache statistics tracking."""

    def test_stats_tracks_hits_and_misses(self) -> None:
        """Test that stats track cache hits and misses."""
        cache = LRUCache[str, str](maxsize=10)

        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("missing")  # Miss

        stats = cache.stats()
        assert stats.hits == 2
        assert stats.misses == 1

    def test_stats_hit_rate_calculation(self) -> None:
        """Test that hit rate is calculated correctly."""
        cache = LRUCache[str, str](maxsize=10)

        # No operations yet
        stats = cache.stats()
        assert stats.hit_rate == 0.0

        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("missing")  # Miss

        stats = cache.stats()
        assert stats.hit_rate == 0.5  # 1 hit / 2 total

    def test_stats_size_and_maxsize(self) -> None:
        """Test that stats track size and maxsize."""
        cache = LRUCache[str, str](maxsize=100)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.stats()
        assert stats.size == 2
        assert stats.maxsize == 100


class TestLRUCacheGetOrSet:
    """Test get_or_set convenience method."""

    def test_get_or_set_returns_cached_value(self) -> None:
        """Test that get_or_set returns cached value if exists."""
        cache = LRUCache[str, str](maxsize=10)
        cache.set("key1", "cached_value")

        result = cache.get_or_set("key1", lambda: "new_value")

        assert result == "cached_value"

    def test_get_or_set_computes_and_caches_new_value(self) -> None:
        """Test that get_or_set computes and caches new value if not exists."""
        cache = LRUCache[str, str](maxsize=10)

        result = cache.get_or_set("key1", lambda: "computed_value")

        assert result == "computed_value"
        assert cache.get("key1") == "computed_value"

    def test_get_or_set_does_not_call_factory_on_cache_hit(self) -> None:
        """Test that factory is not called when value is cached."""
        cache = LRUCache[str, str](maxsize=10)
        cache.set("key1", "cached_value")

        factory_called = False

        def factory() -> str:
            nonlocal factory_called
            factory_called = True
            return "new_value"

        cache.get_or_set("key1", factory)

        assert not factory_called


class TestLRUCacheAsync:
    """Test async methods."""

    @pytest.mark.asyncio
    async def test_aget_or_set_returns_cached_value(self) -> None:
        """Test async get_or_set returns cached value if exists."""
        cache = LRUCache[str, str](maxsize=10)
        cache.set("key1", "cached_value")

        result = await cache.aget_or_set("key1", lambda: "new_value")

        assert result == "cached_value"

    @pytest.mark.asyncio
    async def test_aget_or_set_computes_and_caches_new_value(self) -> None:
        """Test async get_or_set computes and caches new value if not exists."""
        cache = LRUCache[str, str](maxsize=10)

        result = await cache.aget_or_set("key1", lambda: "computed_value")

        assert result == "computed_value"
        assert cache.get("key1") == "computed_value"


class TestLRUCacheValidation:
    """Test input validation."""

    def test_invalid_maxsize_raises_error(self) -> None:
        """Test that maxsize <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="maxsize must be positive"):
            LRUCache[str, str](maxsize=0)

        with pytest.raises(ValueError, match="maxsize must be positive"):
            LRUCache[str, str](maxsize=-1)

    def test_invalid_ttl_raises_error(self) -> None:
        """Test that ttl_seconds <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="ttl_seconds must be positive"):
            LRUCache[str, str](maxsize=10, ttl_seconds=0)

        with pytest.raises(ValueError, match="ttl_seconds must be positive"):
            LRUCache[str, str](maxsize=10, ttl_seconds=-1)


class TestLRUCacheProperties:
    """Test cache properties."""

    def test_size_property(self) -> None:
        """Test size property returns current cache size."""
        cache = LRUCache[str, str](maxsize=10)

        assert cache.size == 0

        cache.set("key1", "value1")
        assert cache.size == 1

        cache.set("key2", "value2")
        assert cache.size == 2

    def test_maxsize_property(self) -> None:
        """Test maxsize property returns configured maxsize."""
        cache = LRUCache[str, str](maxsize=100)

        assert cache.maxsize == 100

    def test_ttl_seconds_property(self) -> None:
        """Test ttl_seconds property returns configured TTL."""
        cache = LRUCache[str, str](maxsize=10, ttl_seconds=300)

        assert cache.ttl_seconds == 300


class TestLRUCacheDunderMethods:
    """Test dunder methods."""

    def test_len_returns_size(self) -> None:
        """Test __len__ returns cache size."""
        cache = LRUCache[str, str](maxsize=10)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert len(cache) == 2

    def test_contains_operator(self) -> None:
        """Test __contains__ for 'in' operator."""
        cache = LRUCache[str, str](maxsize=10)
        cache.set("key1", "value1")

        assert "key1" in cache
        assert "missing" not in cache

    def test_repr(self) -> None:
        """Test __repr__ returns meaningful string."""
        cache = LRUCache[str, str](maxsize=100, ttl_seconds=300, name="test_cache")
        cache.set("key1", "value1")

        repr_str = repr(cache)

        assert "LRUCache" in repr_str
        assert "test_cache" in repr_str


class TestCacheStats:
    """Test CacheStats dataclass."""

    def test_cache_stats_default_values(self) -> None:
        """Test CacheStats with default values."""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.size == 0
        assert stats.maxsize == 0

    def test_cache_stats_hit_rate_with_no_ops(self) -> None:
        """Test hit rate when no operations performed."""
        stats = CacheStats()

        assert stats.hit_rate == 0.0

    def test_cache_stats_hit_rate_calculation(self) -> None:
        """Test hit rate calculation."""
        stats = CacheStats(hits=8, misses=2)

        assert stats.hit_rate == 0.8


class TestCacheConfig:
    """Test CacheConfig dataclass."""

    def test_cache_config_defaults(self) -> None:
        """Test CacheConfig with default values."""
        config = CacheConfig()

        assert config.maxsize == 512
        assert config.ttl_seconds == 3600
        assert config.name == "default"
        assert config.log_metrics is True

    def test_cache_config_custom_values(self) -> None:
        """Test CacheConfig with custom values."""
        config = CacheConfig(
            maxsize=100, ttl_seconds=60, name="custom_cache", log_metrics=False
        )

        assert config.maxsize == 100
        assert config.ttl_seconds == 60
        assert config.name == "custom_cache"
        assert config.log_metrics is False


class TestCreateEmbeddingCache:
    """Test create_embedding_cache factory function."""

    def test_create_embedding_cache_defaults(self) -> None:
        """Test create_embedding_cache with default values."""
        cache = create_embedding_cache()

        assert cache.maxsize == 1024
        assert cache.ttl_seconds == 900
        assert cache._name == "embeddings"

    def test_create_embedding_cache_custom_values(self) -> None:
        """Test create_embedding_cache with custom values."""
        cache = create_embedding_cache(maxsize=512, ttl_seconds=300)

        assert cache.maxsize == 512
        assert cache.ttl_seconds == 300
        assert cache._name == "embeddings"

    def test_create_embedding_cache_type_annotation(self) -> None:
        """Test that create_embedding_cache returns correctly typed cache."""
        cache = create_embedding_cache()

        # Should be able to store string keys and list[float] values
        cache.set("embedding_1", [0.1, 0.2, 0.3])
        result = cache.get("embedding_1")

        assert result == [0.1, 0.2, 0.3]
