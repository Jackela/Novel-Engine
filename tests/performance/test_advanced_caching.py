"""
Tests for Advanced Caching Module

Coverage targets:
- LRU eviction
- TTL expiration
- Cache serialization (pickle)
- Memory limits
"""

import asyncio
import gzip
import pickle
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

pytestmark = pytest.mark.unit

from src.performance.advanced_caching import (
    CacheConfig,
    CacheEntry,
    CacheEvent,
    CacheLevel,
    CacheStats,
    CacheStrategy,
    IntelligentCacheManager,
    cached,
    get_cache_manager,
    initialize_cache_manager,
)


class TestCacheLevel:
    """Tests for CacheLevel enum."""

    def test_cache_levels(self):
        """Test all cache levels are defined."""
        assert CacheLevel.MEMORY.value == "memory"
        assert CacheLevel.REDIS.value == "redis"
        assert CacheLevel.DISK.value == "disk"
        assert CacheLevel.DATABASE.value == "database"


class TestCacheStrategy:
    """Tests for CacheStrategy enum."""

    def test_cache_strategies(self):
        """Test all cache strategies are defined."""
        assert CacheStrategy.LRU.value == "lru"
        assert CacheStrategy.LFU.value == "lfu"
        assert CacheStrategy.TTL.value == "ttl"
        assert CacheStrategy.FIFO.value == "fifo"
        assert CacheStrategy.ADAPTIVE.value == "adaptive"


class TestCacheEvent:
    """Tests for CacheEvent enum."""

    def test_cache_events(self):
        """Test all cache events are defined."""
        assert CacheEvent.HIT.value == "hit"
        assert CacheEvent.MISS.value == "miss"
        assert CacheEvent.SET.value == "set"
        assert CacheEvent.DELETE.value == "delete"
        assert CacheEvent.EXPIRE.value == "expire"
        assert CacheEvent.EVICT.value == "evict"


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_entry_creation(self):
        """Test cache entry creation."""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=datetime.now().timestamp(),
            accessed_at=datetime.now().timestamp(),
            ttl=3600,
        )

        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.ttl == 3600
        assert entry.access_count == 0

    def test_entry_is_expired_with_ttl(self):
        """Test entry expiration with TTL."""
        entry = CacheEntry(
            key="test",
            value="value",
            created_at=datetime.now().timestamp() - 7200,  # 2 hours ago
            accessed_at=datetime.now().timestamp(),
            ttl=3600,  # 1 hour TTL
        )

        assert entry.is_expired() is True

    def test_entry_is_not_expired(self):
        """Test entry not expired."""
        entry = CacheEntry(
            key="test",
            value="value",
            created_at=datetime.now().timestamp(),
            accessed_at=datetime.now().timestamp(),
            ttl=3600,
        )

        assert entry.is_expired() is False

    def test_entry_no_ttl_never_expires(self):
        """Test entry without TTL never expires."""
        entry = CacheEntry(
            key="test",
            value="value",
            created_at=0,  # Very old
            accessed_at=0,
            ttl=None,
        )

        assert entry.is_expired() is False

    def test_entry_touch(self):
        """Test entry touch updates access info."""
        entry = CacheEntry(
            key="test",
            value="value",
            created_at=datetime.now().timestamp(),
            accessed_at=0,
            access_count=0,
        )

        entry.touch()

        assert entry.access_count == 1
        assert entry.accessed_at > 0


class TestCacheStats:
    """Tests for CacheStats dataclass."""

    def test_stats_initialization(self):
        """Test stats initialization."""
        stats = CacheStats()

        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0
        assert stats.deletes == 0
        assert stats.evictions == 0
        assert stats.hit_rate == 0.0

    def test_update_hit_rate(self):
        """Test hit rate calculation."""
        stats = CacheStats()
        stats.hits = 80
        stats.misses = 20

        stats.update_hit_rate()

        assert stats.hit_rate == 80.0

    def test_update_hit_rate_no_requests(self):
        """Test hit rate with no requests."""
        stats = CacheStats()

        stats.update_hit_rate()

        assert stats.hit_rate == 0.0


class TestCacheConfig:
    """Tests for CacheConfig dataclass."""

    def test_default_config(self):
        """Test default config values."""
        config = CacheConfig()

        assert config.max_size == 1000
        assert config.max_memory_mb == 100
        assert config.default_ttl == 3600
        assert config.strategy == CacheStrategy.ADAPTIVE
        assert config.persist_to_disk is False

    def test_custom_config(self):
        """Test custom config values."""
        config = CacheConfig(
            max_size=500,
            max_memory_mb=50,
            default_ttl=7200,
            strategy=CacheStrategy.LRU,
            persist_to_disk=True,
        )

        assert config.max_size == 500
        assert config.max_memory_mb == 50
        assert config.default_ttl == 7200
        assert config.strategy == CacheStrategy.LRU
        assert config.persist_to_disk is True


@pytest.mark.asyncio
class TestIntelligentCacheManager:
    """Tests for IntelligentCacheManager class."""

    @pytest_asyncio.fixture
    async def cache_manager(self):
        """Create a cache manager instance."""
        config = CacheConfig(
            max_size=10,
            max_memory_mb=10,
            default_ttl=3600,
            strategy=CacheStrategy.LRU,
            persist_to_disk=False,
            background_cleanup=False,
        )
        manager = IntelligentCacheManager(config)
        return manager

    def test_initialization(self):
        """Test cache manager initialization."""
        config = CacheConfig()
        manager = IntelligentCacheManager(config)

        assert manager.config == config
        assert len(manager.cache) == 0
        assert isinstance(manager.stats, CacheStats)

    async def test_set_and_get(self, cache_manager):
        """Test setting and getting cache values."""
        await cache_manager.set("key1", "value1")

        result = await cache_manager.get("key1")

        assert result == "value1"
        assert cache_manager.stats.sets == 1
        assert cache_manager.stats.hits == 1

    async def test_get_not_found(self, cache_manager):
        """Test getting non-existent key."""
        result = await cache_manager.get("nonexistent")

        assert result is None
        assert cache_manager.stats.misses == 1

    async def test_get_with_default(self, cache_manager):
        """Test getting with default value."""
        result = await cache_manager.get("nonexistent", default="default_value")

        assert result == "default_value"

    async def test_set_with_ttl(self, cache_manager):
        """Test setting value with custom TTL."""
        await cache_manager.set("key1", "value1", ttl=1)  # 1 second TTL

        # Should be available immediately
        result = await cache_manager.get("key1")
        assert result == "value1"

    async def test_expired_entry_removed(self, cache_manager):
        """Test that expired entries are removed."""
        await cache_manager.set("key1", "value1", ttl=0.001)  # Very short TTL

        # Wait for expiration
        await asyncio.sleep(0.1)

        result = await cache_manager.get("key1")
        assert result is None
        assert "key1" not in cache_manager.cache

    async def test_delete(self, cache_manager):
        """Test deleting cache entry."""
        await cache_manager.set("key1", "value1")

        result = await cache_manager.delete("key1")

        assert result is True
        assert "key1" not in cache_manager.cache
        assert cache_manager.stats.deletes == 1

    async def test_delete_not_found(self, cache_manager):
        """Test deleting non-existent key."""
        result = await cache_manager.delete("nonexistent")

        assert result is False

    async def test_invalidate_pattern(self, cache_manager):
        """Test invalidating keys by pattern."""
        await cache_manager.set("user:1:name", "Alice")
        await cache_manager.set("user:1:email", "alice@example.com")
        await cache_manager.set("user:2:name", "Bob")
        await cache_manager.set("product:1", "Widget")

        count = await cache_manager.invalidate_pattern("user:1")

        assert count == 2
        assert "user:1:name" not in cache_manager.cache
        assert "user:1:email" not in cache_manager.cache
        assert "user:2:name" in cache_manager.cache

    async def test_lru_eviction(self, cache_manager):
        """Test LRU eviction when max size reached."""
        cache_manager.config.max_size = 3
        cache_manager.config.strategy = CacheStrategy.LRU

        await cache_manager.set("key1", "value1")
        await cache_manager.set("key2", "value2")
        await cache_manager.set("key3", "value3")

        # Access key1 to make it most recently used
        await cache_manager.get("key1")

        # Add key4, should evict key2 (least recently used)
        await cache_manager.set("key4", "value4")

        assert "key1" in cache_manager.cache
        assert "key2" not in cache_manager.cache  # Evicted
        assert "key3" in cache_manager.cache
        assert "key4" in cache_manager.cache
        assert cache_manager.stats.evictions >= 1

    async def test_warm_cache(self, cache_manager):
        """Test warming cache with multiple values."""
        data = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3",
        }

        await cache_manager.warm_cache(data)

        assert await cache_manager.get("key1") == "value1"
        assert await cache_manager.get("key2") == "value2"
        assert await cache_manager.get("key3") == "value3"

    def test_generate_key_hash(self, cache_manager):
        """Test key hash generation."""
        hash1 = cache_manager._generate_key_hash("test_key")
        hash2 = cache_manager._generate_key_hash("test_key")
        hash3 = cache_manager._generate_key_hash("different_key")

        assert hash1 == hash2  # Same input = same hash
        assert hash1 != hash3  # Different input = different hash
        assert len(hash1) == 16  # 16 characters

    def test_calculate_entry_size_string(self, cache_manager):
        """Test size calculation for string."""
        size = cache_manager._calculate_entry_size("test string")

        assert size == 11  # Length of string

    def test_calculate_entry_size_object(self, cache_manager):
        """Test size calculation for object."""
        obj = {"key": "value", "number": 123}
        size = cache_manager._calculate_entry_size(obj)

        assert size > 0
        assert size == len(pickle.dumps(obj))

    def test_compress_value(self, cache_manager):
        """Test value compression."""
        cache_manager.config.compression_threshold = 10
        large_value = "x" * 1000

        compressed = cache_manager._compress_value(large_value)

        assert isinstance(compressed, bytes)
        assert len(compressed) < len(large_value)

    def test_decompress_value(self, cache_manager):
        """Test value decompression."""
        original = "test value"
        compressed = gzip.compress(pickle.dumps(original))

        result = cache_manager._decompress_value(compressed, compressed=True)

        assert result == original

    def test_select_eviction_key_lru(self, cache_manager):
        """Test LRU eviction key selection."""
        cache_manager.config.strategy = CacheStrategy.LRU
        cache_manager.cache["key1"] = Mock()
        cache_manager.cache["key2"] = Mock()

        key = cache_manager._select_eviction_key()

        assert key == "key1"  # First key in OrderedDict

    def test_select_eviction_key_lfu(self, cache_manager):
        """Test LFU eviction key selection."""
        cache_manager.config.strategy = CacheStrategy.LFU

        entry1 = Mock()
        entry1.access_count = 5
        entry2 = Mock()
        entry2.access_count = 2

        cache_manager.cache["key1"] = entry1
        cache_manager.cache["key2"] = entry2

        key = cache_manager._select_eviction_key()

        assert key == "key2"  # Lower access count

    async def test_get_stats(self, cache_manager):
        """Test getting cache statistics."""
        await cache_manager.set("key1", "value1")
        await cache_manager.get("key1")

        stats = cache_manager.get_stats()

        assert "cache_stats" in stats
        assert stats["cache_size"] == 1
        assert stats["cache_stats"]["hits"] == 1
        assert stats["cache_stats"]["sets"] == 1

    async def test_shutdown(self, cache_manager):
        """Test cache shutdown."""
        # Setup background tasks
        cache_manager._cleanup_task = AsyncMock()
        cache_manager._cleanup_task.cancel = Mock()
        cache_manager._cleanup_task.done = Mock(return_value=True)

        await cache_manager.shutdown()

        # Should cancel tasks and cleanup
        assert len(cache_manager.cache) == 0


class TestCachedDecorator:
    """Tests for @cached decorator."""

    @pytest.mark.asyncio
    async def test_cached_async_function(self):
        """Test caching async function."""
        call_count = 0

        @cached(ttl=3600, key_prefix="test")
        async def async_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # Mock cache manager
        with patch("src.performance.advanced_caching.get_cache_manager") as mock_get:
            mock_cache = AsyncMock()
            mock_cache.get = AsyncMock(return_value=None)  # First call - cache miss
            mock_cache.set = AsyncMock()
            mock_get.return_value = mock_cache

            result1 = await async_func(5)
            assert result1 == 10
            assert call_count == 1

            # Second call should use cache
            mock_cache.get = AsyncMock(return_value=10)  # Cache hit
            result2 = await async_func(5)
            assert result2 == 10
            assert call_count == 1  # Not incremented


class TestGlobalInstances:
    """Tests for global instances."""

    def test_get_cache_manager_singleton(self):
        """Test cache manager is singleton."""
        import src.performance.advanced_caching as cache_module

        original = cache_module.cache_manager
        cache_module.cache_manager = None

        try:
            manager1 = get_cache_manager()
            manager2 = get_cache_manager()
            assert manager1 is manager2
        finally:
            cache_module.cache_manager = original

    def test_initialize_cache_manager(self):
        """Test cache manager initialization."""
        import src.performance.advanced_caching as cache_module

        original = cache_module.cache_manager
        cache_module.cache_manager = None

        try:
            config = CacheConfig(max_size=500)
            manager = initialize_cache_manager(config)

            assert manager is not None
            assert manager.config.max_size == 500
        finally:
            cache_module.cache_manager = original
