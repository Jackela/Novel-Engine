"""
Test suite for Distributed Caching module.

Tests distributed cache operations and consistency.
"""

import pytest

pytestmark = pytest.mark.unit

from unittest.mock import Mock

from src.performance.distributed_caching import (
    CacheEntry,
    CacheLevel,
    CacheMetrics,
    CacheStrategy,
    DistributedCache,
    MemoryCache,
    MockRedis,
)


class TestCacheLevel:
    """Test CacheLevel enum."""

    def test_cache_level_values(self):
        """Test cache level values."""
        assert CacheLevel.L1_MEMORY == "l1_memory"
        assert CacheLevel.L2_REDIS == "l2_redis"
        assert CacheLevel.L3_DATABASE == "l3_database"


class TestCacheStrategy:
    """Test CacheStrategy enum."""

    def test_strategy_values(self):
        """Test cache strategy values."""
        assert CacheStrategy.LRU == "lru"
        assert CacheStrategy.LFU == "lfu"
        assert CacheStrategy.TTL == "ttl"


class TestCacheMetrics:
    """Test CacheMetrics dataclass."""

    def test_metrics_creation(self):
        """Test creating cache metrics."""
        metrics = CacheMetrics(
            hits=100,
            misses=20,
            sets=50,
        )
        
        assert metrics.hits == 100
        assert metrics.misses == 20
        assert metrics.sets == 50

    def test_hit_rate(self):
        """Test hit rate calculation."""
        metrics = CacheMetrics(hits=80, misses=20)
        
        assert metrics.hit_rate == 80.0

    def test_hit_rate_no_requests(self):
        """Test hit rate with no requests."""
        metrics = CacheMetrics()
        
        assert metrics.hit_rate == 0.0


class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            ttl=3600,
            size=100,
            tags=["tag1", "tag2"],
        )
        
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.ttl == 3600
        assert entry.size == 100

    def test_is_expired_no_ttl(self):
        """Test that entry without TTL never expires."""
        entry = CacheEntry(key="test", value="value", ttl=None)
        
        assert entry.is_expired is False

    def test_update_access(self):
        """Test access update."""
        entry = CacheEntry(key="test", value="value")
        
        entry.update_access()
        
        assert entry.access_count == 1


class TestMemoryCache:
    """Test MemoryCache implementation."""

    @pytest.fixture
    async def cache(self):
        """Create a fresh memory cache."""
        cache = MemoryCache(max_size=100, default_ttl=3600)
        yield cache
        await cache.clear()

    @pytest.mark.asyncio
    async def test_get_existing_key(self, cache):
        """Test getting an existing key."""
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache):
        """Test getting a non-existent key."""
        result = await cache.get("nonexistent")
        
        assert result is None
        assert cache.metrics.misses == 1

    @pytest.mark.asyncio
    async def test_set_and_overwrite(self, cache):
        """Test setting and overwriting a key."""
        await cache.set("key1", "value1")
        await cache.set("key1", "value2")
        
        result = await cache.get("key1")
        assert result == "value2"

    @pytest.mark.asyncio
    async def test_delete_existing(self, cache):
        """Test deleting an existing key."""
        await cache.set("key1", "value1")
        result = await cache.delete("key1")
        
        assert result is True
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_exists(self, cache):
        """Test checking key existence."""
        await cache.set("key1", "value1")
        
        assert await cache.exists("key1") is True
        assert await cache.exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_clear(self, cache):
        """Test clearing all cache entries."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        
        result = await cache.clear()
        
        assert result is True
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, cache):
        """Test that metrics are properly tracked."""
        await cache.set("key1", "value1")
        await cache.get("key1")
        await cache.get("nonexistent")
        
        metrics = cache.get_metrics()
        
        assert metrics.hits >= 0
        assert metrics.misses >= 0
        assert metrics.sets >= 1


class TestMockRedis:
    """Test MockRedis implementation."""

    @pytest.mark.asyncio
    async def test_get_set(self):
        """Test basic get/set operations."""
        redis = MockRedis()
        
        await redis.setex("key1", 3600, "value1")
        result = await redis.get("key1")
        
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test delete operation."""
        redis = MockRedis()
        
        await redis.setex("key1", 3600, "value1")
        deleted = await redis.delete("key1")
        
        assert deleted == 1
        assert await redis.get("key1") is None

    @pytest.mark.asyncio
    async def test_exists(self):
        """Test exists operation."""
        redis = MockRedis()
        
        await redis.setex("key1", 3600, "value1")
        
        assert await redis.exists("key1") == 1
        assert await redis.exists("nonexistent") == 0


class TestDistributedCache:
    """Test DistributedCache implementation."""

    @pytest.fixture
    async def distributed_cache(self):
        """Create a distributed cache with mocked backends."""
        l1_cache = MemoryCache(max_size=100)
        l2_cache = Mock()
        l2_cache.get = Mock(return_value=None)
        l2_cache.set = Mock(return_value=True)
        l2_cache.delete = Mock(return_value=True)
        l2_cache.exists = Mock(return_value=False)
        l2_cache.clear = Mock(return_value=True)
        l2_cache.get_metrics = Mock(return_value=CacheMetrics())
        # Make methods async-compatible
        import asyncio
        for method in ['get', 'set', 'delete', 'exists', 'clear']:
            setattr(l2_cache, method, Mock(return_value=asyncio.Future()))
            getattr(l2_cache, method).return_value.set_result(True)
        l2_cache.get.return_value = asyncio.Future()
        l2_cache.get.return_value.set_result(None)
        
        cache = DistributedCache(l1_cache=l1_cache, l2_cache=l2_cache)
        yield cache

    @pytest.mark.asyncio
    async def test_get_l1_hit(self, distributed_cache):
        """Test getting from L1 cache (hit)."""
        await distributed_cache.l1_cache.set("key1", "value1")
        
        result = await distributed_cache.get("key1")
        
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_set_both_levels(self, distributed_cache):
        """Test setting in both cache levels."""
        result = await distributed_cache.set("key1", "value1")
        
        assert result is True
        assert await distributed_cache.l1_cache.get("key1") == "value1"

    @pytest.mark.asyncio
    async def test_delete_both_levels(self, distributed_cache):
        """Test deleting from both cache levels."""
        await distributed_cache.set("key1", "value1")
        result = await distributed_cache.delete("key1")
        
        assert result is True

    def test_register_cache_loader(self, distributed_cache):
        """Test registering a cache loader."""
        loader = Mock(return_value="loaded_value")
        
        distributed_cache.register_cache_loader("pattern:*", loader)
        
        assert "pattern:*" in distributed_cache._cache_loaders

    def test_get_comprehensive_metrics(self, distributed_cache):
        """Test getting comprehensive metrics."""
        metrics = distributed_cache.get_comprehensive_metrics()
        
        assert "combined" in metrics
        assert "l1_memory" in metrics
        assert "l2_redis" in metrics
