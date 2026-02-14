"""
Unit tests for EmbeddingCacheService.

Tests LRU eviction, TTL expiration, batch operations, and statistics tracking.
"""

import time

import pytest

from src.contexts.knowledge.application.services.embedding_cache_service import (
    CacheEntry,
    CacheKey,
    CacheStats,
    EmbeddingCacheService,
)

pytestmark = pytest.mark.unit


class TestCacheKey:
    """Test CacheKey generation and uniqueness."""

    def test_cache_key_from_text(self):
        """Test generating cache key from text and model."""
        key = CacheKey.from_text("hello world", "text-embedding-ada-002")
        assert key.model == "text-embedding-ada-002"
        assert len(key.content_hash) == 64  # SHA256 hex length
        assert isinstance(key.content_hash, str)

    def test_cache_key_uniqueness_by_text(self):
        """Test that different texts produce different keys."""
        key1 = CacheKey.from_text("text one", "model")
        key2 = CacheKey.from_text("text two", "model")
        assert key1.content_hash != key2.content_hash

    def test_cache_key_uniqueness_by_model(self):
        """Test that different models produce different keys for same text."""
        key1 = CacheKey.from_text("same text", "model-a")
        key2 = CacheKey.from_text("same text", "model-b")
        assert key1.content_hash != key2.content_hash

    def test_cache_key_deterministic(self):
        """Test that same input produces same key."""
        key1 = CacheKey.from_text("same text", "same model")
        key2 = CacheKey.from_text("same text", "same model")
        assert key1.content_hash == key2.content_hash

    def test_cache_key_string_repr(self):
        """Test string representation includes model and hash prefix."""
        key = CacheKey.from_text("test", "model-123")
        key_str = str(key)
        assert "model-123:" in key_str
        assert len(key_str.split(":")[1]) == 16  # First 16 chars of hash


class TestCacheEntry:
    """Test CacheEntry expiration logic."""

    def test_entry_not_expired_without_ttl(self):
        """Test that entry without TTL never expires."""
        entry = CacheEntry(
            embedding=[0.1, 0.2, 0.3],
            created_ts=time.time() - 1000,  # 1000 seconds ago
            ttl_seconds=None,
        )
        assert not entry.is_expired(time.time())

    def test_entry_not_expired_within_ttl(self):
        """Test that entry within TTL is not expired."""
        entry = CacheEntry(
            embedding=[0.1, 0.2, 0.3],
            created_ts=time.time() - 50,  # 50 seconds ago
            ttl_seconds=100,  # 100 second TTL
        )
        assert not entry.is_expired(time.time())

    def test_entry_expired_after_ttl(self):
        """Test that entry past TTL is expired."""
        entry = CacheEntry(
            embedding=[0.1, 0.2, 0.3],
            created_ts=time.time() - 150,  # 150 seconds ago
            ttl_seconds=100,  # 100 second TTL
        )
        assert entry.is_expired(time.time())

    def test_entry_expires_at_ttl_boundary(self):
        """Test expiration exactly at TTL boundary."""
        entry = CacheEntry(
            embedding=[0.1, 0.2, 0.3],
            created_ts=100.0,
            ttl_seconds=100,
        )
        # At exactly boundary, should be expired
        assert entry.is_expired(200.0)
        # Just before boundary, should not be expired
        assert not entry.is_expired(199.9)


class TestEmbeddingCacheService:
    """Test EmbeddingCacheService caching behavior."""

    def test_init_default_values(self):
        """Test default initialization values."""
        cache = EmbeddingCacheService()
        assert cache._max_size == EmbeddingCacheService.DEFAULT_MAX_SIZE
        assert cache._default_ttl == EmbeddingCacheService.DEFAULT_TTL_SECONDS
        assert cache.get_stats().size == 0

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        cache = EmbeddingCacheService(max_size=100, default_ttl_seconds=600)
        assert cache._max_size == 100
        assert cache._default_ttl == 600

    def test_put_and_get(self):
        """Test basic put and get operations."""
        cache = EmbeddingCacheService()
        embedding = [0.1, 0.2, 0.3, 0.4]

        cache.put("test text", embedding, "model")
        result = cache.get("test text", "model")

        assert result == embedding

    def test_get_missing_returns_none(self):
        """Test that getting missing key returns None."""
        cache = EmbeddingCacheService()
        result = cache.get("nonexistent", "model")
        assert result is None

    def test_cache_hit_increments_stats(self):
        """Test that cache hit increments hit counter."""
        cache = EmbeddingCacheService()
        embedding = [0.1, 0.2]

        cache.put("test", embedding, "model")
        cache.get("test", "model")  # Hit

        stats = cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 0

    def test_cache_miss_increments_stats(self):
        """Test that cache miss increments miss counter."""
        cache = EmbeddingCacheService()
        cache.get("nonexistent", "model")  # Miss

        stats = cache.get_stats()
        assert stats.hits == 0
        assert stats.misses == 1

    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = EmbeddingCacheService(default_ttl_seconds=1)  # 1 second TTL
        embedding = [0.1, 0.2]

        cache.put("test", embedding, "model")
        # Should be cached immediately
        assert cache.get("test", "model") == embedding

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        result = cache.get("test", "model")
        assert result is None

        stats = cache.get_stats()
        assert stats.misses == 1  # The final get was a miss
        assert stats.size == 0

    def test_custom_ttl_per_entry(self):
        """Test custom TTL for individual entries."""
        cache = EmbeddingCacheService(default_ttl_seconds=3600)
        embedding = [0.1, 0.2]

        # Entry with short TTL
        cache.put("short", embedding, "model", ttl_seconds=1)
        # Entry with long TTL
        cache.put("long", embedding, "model", ttl_seconds=10)

        time.sleep(1.1)

        assert cache.get("short", "model") is None  # Expired
        assert cache.get("long", "model") == embedding  # Still cached

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = EmbeddingCacheService(max_size=3)

        cache.put("first", [0.1], "model")
        cache.put("second", [0.2], "model")
        cache.put("third", [0.3], "model")

        # Cache is full
        assert cache.get_stats().size == 3

        # Access first to make it more recent than second
        cache.get("first", "model")

        # Add fourth entry - should evict second (least recently used)
        cache.put("fourth", [0.4], "model")

        assert cache.get_stats().size == 3
        assert cache.get("first", "model") == [0.1]  # Still there
        assert cache.get("second", "model") is None  # Evicted
        assert cache.get("third", "model") == [0.3]  # Still there
        assert cache.get("fourth", "model") == [0.4]  # New entry

    def test_put_batch(self):
        """Test batch put operation."""
        cache = EmbeddingCacheService()
        items = [
            ("text1", [0.1, 0.2]),
            ("text2", [0.3, 0.4]),
            ("text3", [0.5, 0.6]),
        ]

        cache.put_batch(items, "model")

        assert cache.get("text1", "model") == [0.1, 0.2]
        assert cache.get("text2", "model") == [0.3, 0.4]
        assert cache.get("text3", "model") == [0.5, 0.6]
        assert cache.get_stats().size == 3

    def test_get_batch(self):
        """Test batch get operation."""
        cache = EmbeddingCacheService()
        cache.put("hit1", [0.1], "model")
        cache.put("hit2", [0.2], "model")

        results = cache.get_batch(["hit1", "miss1", "hit2", "miss2"], "model")

        assert results == {"hit1": [0.1], "hit2": [0.2]}
        assert "miss1" not in results
        assert "miss2" not in results

    def test_invalidate_all(self):
        """Test invalidating all cache entries."""
        cache = EmbeddingCacheService()
        cache.put("test1", [0.1], "model-a")
        cache.put("test2", [0.2], "model-b")

        count = cache.invalidate()  # No model filter

        assert count == 2
        assert cache.get_stats().size == 0

    def test_invalidate_by_model(self):
        """Test invalidating entries for specific model."""
        cache = EmbeddingCacheService()
        cache.put("test1", [0.1], "model-a")
        cache.put("test2", [0.2], "model-b")
        cache.put("test3", [0.3], "model-a")

        count = cache.invalidate(model="model-a")

        assert count == 2
        assert cache.get("test1", "model-a") is None
        assert cache.get("test2", "model-b") == [0.2]  # Still cached
        assert cache.get("test3", "model-a") is None
        assert cache.get_stats().size == 1

    def test_clear(self):
        """Test clearing cache and resetting stats."""
        cache = EmbeddingCacheService()
        cache.put("test", [0.1], "model")
        cache.get("test", "model")
        cache.get("miss", "model")  # Force a miss

        assert cache.get_stats().size == 1
        assert cache.get_stats().hits == 1
        assert cache.get_stats().misses == 1

        cache.clear()

        stats = cache.get_stats()
        assert stats.size == 0
        assert stats.hits == 0
        assert stats.misses == 0

    def test_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        cache = EmbeddingCacheService()
        cache.put("test", [0.1], "model")

        # 1 hit, 0 misses
        cache.get("test", "model")
        stats = cache.get_stats()
        assert stats.hit_rate == 1.0

        # 1 hit, 1 miss
        cache.get("miss", "model")
        stats = cache.get_stats()
        assert stats.hit_rate == 0.5

        # 1 hit, 3 misses
        cache.get("miss1", "model")
        cache.get("miss2", "model")
        stats = cache.get_stats()
        assert stats.hit_rate == 0.25

    def test_hit_rate_empty_cache(self):
        """Test hit rate with empty cache."""
        cache = EmbeddingCacheService()
        assert cache.get_stats().hit_rate == 0.0

    def test_update_existing_entry(self):
        """Test that putting existing entry updates it."""
        cache = EmbeddingCacheService()
        cache.put("test", [0.1, 0.2], "model")
        cache.put("test", [0.3, 0.4], "model")  # Update

        assert cache.get("test", "model") == [0.3, 0.4]
        assert cache.get_stats().size == 1  # No duplicate entry

    def test_different_models_separate_entries(self):
        """Test that same text with different models creates separate entries."""
        cache = EmbeddingCacheService()
        cache.put("text", [0.1], "model-a")
        cache.put("text", [0.2], "model-b")

        assert cache.get("text", "model-a") == [0.1]
        assert cache.get("text", "model-b") == [0.2]
        assert cache.get_stats().size == 2


class TestCacheStats:
    """Test CacheStats dataclass."""

    def test_default_values(self):
        """Test default stat values."""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.size == 0
        assert stats.hit_rate == 0.0

    def test_custom_values(self):
        """Test stats with custom values."""
        stats = CacheStats(hits=80, misses=20, size=100)
        assert stats.hits == 80
        assert stats.misses == 20
        assert stats.size == 100
        assert stats.hit_rate == 0.8
