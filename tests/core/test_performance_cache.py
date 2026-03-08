"""
Test suite for Performance Cache module.

Tests cache strategies, eviction policies, and memory management.
"""

import asyncio
import pytest

pytestmark = pytest.mark.unit

from unittest.mock import Mock, patch, AsyncMock

from src.core.performance_cache import (
    CacheBackend,
    CacheEntry,
    CacheLevel,
    MemoryCache,
    PerformanceCache,
    get_global_cache,
    close_global_cache,
)


class TestCacheLevel:
    """Test CacheLevel enum."""

    def test_cache_level_values(self):
        """Test that CacheLevel has expected values."""
        assert CacheLevel.CRITICAL.value == "critical"
        assert CacheLevel.HIGH.value == "high"
        assert CacheLevel.MEDIUM.value == "medium"
        assert CacheLevel.LOW.value == "low"


class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            ttl=3600.0,
            level=CacheLevel.HIGH,
        )
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.ttl == 3600.0
        assert entry.level == CacheLevel.HIGH
        assert entry.access_count == 0

    def test_is_expired_no_ttl(self):
        """Test that entry without TTL never expires."""
        entry = CacheEntry(key="test", value="value", ttl=None)
        assert not entry.is_expired()

    def test_is_expired_with_ttl(self):
        """Test entry expiration with TTL."""
        entry = CacheEntry(key="test", value="value", ttl=0.001)
        assert not entry.is_expired()
        import time
        time.sleep(0.002)
        assert entry.is_expired()

    def test_update_access(self):
        """Test access count update."""
        entry = CacheEntry(key="test", value="value")
        assert entry.access_count == 0
        entry.update_access()
        assert entry.access_count == 1
        entry.update_access()
        assert entry.access_count == 2


class TestMemoryCache:
    """Test MemoryCache implementation."""

    @pytest.fixture
    async def cache(self):
        """Create a fresh memory cache for each test."""
        cache = MemoryCache(max_size=100, max_memory_mb=10)
        yield cache
        await cache.clear()

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        cache = MemoryCache(max_size=100, max_memory_mb=10)
        result = await cache.get("nonexistent")
        assert result is None
        assert cache.miss_count == 1

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = MemoryCache(max_size=100, max_memory_mb=10)
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"
        assert cache.hit_count == 1

    @pytest.mark.asyncio
    async def test_set_with_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = MemoryCache(max_size=100, max_memory_mb=10)
        await cache.set("key1", "value1", ttl=0.001)
        result = await cache.get("key1")
        assert result == "value1"
        
        import time
        time.sleep(0.002)
        
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_existing_key(self):
        """Test deleting an existing key."""
        cache = MemoryCache(max_size=100, max_memory_mb=10)
        await cache.set("key1", "value1")
        result = await cache.delete("key1")
        assert result is True
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self):
        """Test deleting a key that doesn't exist."""
        cache = MemoryCache(max_size=100, max_memory_mb=10)
        result = await cache.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing all cache entries."""
        cache = MemoryCache(max_size=100, max_memory_mb=10)
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        result = await cache.clear()
        assert result is True
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = MemoryCache(max_size=3, max_memory_mb=100)
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        await cache.get("key1")
        
        # Add new entry, should evict key2 (least recently used)
        await cache.set("key4", "value4")
        
        assert await cache.get("key1") is not None  # Still exists
        assert await cache.get("key2") is None  # Evicted
        assert await cache.get("key3") is not None  # Still exists
        assert await cache.get("key4") is not None  # New entry

    @pytest.mark.asyncio
    async def test_critical_level_never_evicted(self):
        """Test that CRITICAL level entries are never evicted."""
        cache = MemoryCache(max_size=2, max_memory_mb=100)
        await cache.set("key1", "value1", level=CacheLevel.CRITICAL)
        await cache.set("key2", "value2", level=CacheLevel.LOW)
        await cache.set("key3", "value3", level=CacheLevel.LOW)
        
        # key1 should still exist because it's CRITICAL
        assert await cache.get("key1") is not None

    @pytest.mark.asyncio
    async def test_memory_size_calculation(self):
        """Test memory size calculation for different value types."""
        cache = MemoryCache(max_size=100, max_memory_mb=10)
        
        # Test string
        size1 = cache._calculate_memory_size("test string")
        assert size1 == len("test string")
        
        # Test dict
        size2 = cache._calculate_memory_size({"key": "value"})
        assert size2 > 0
        
        # Test list
        size3 = cache._calculate_memory_size([1, 2, 3])
        assert size3 > 0

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting cache statistics."""
        cache = MemoryCache(max_size=100, max_memory_mb=10)
        await cache.set("key1", "value1")
        await cache.get("key1")
        await cache.get("nonexistent")
        
        stats = await cache.get_stats()
        assert stats["entries"] == 1
        assert stats["hit_count"] == 1
        assert stats["miss_count"] == 1
        assert "hit_rate" in stats


class TestPerformanceCache:
    """Test PerformanceCache implementation."""

    @pytest.fixture
    async def perf_cache(self):
        """Create a fresh performance cache for each test."""
        cache = PerformanceCache(memory_cache_size=100, memory_limit_mb=10)
        yield cache
        await cache.memory_cache.clear()

    @pytest.mark.asyncio
    async def test_character_caching(self):
        """Test character data caching."""
        cache = PerformanceCache(memory_cache_size=100, memory_limit_mb=10)
        character_data = {"id": "char1", "name": "Test Character"}
        
        # Set character
        result = await cache.set_character("char1", character_data)
        assert result is True
        
        # Get character
        retrieved = await cache.get_character("char1")
        assert retrieved == character_data
        
        # Check stats
        assert cache.cache_stats["character_hits"] == 1

    @pytest.mark.asyncio
    async def test_story_generation_caching(self):
        """Test story generation caching."""
        cache = PerformanceCache(memory_cache_size=100, memory_limit_mb=10)
        story_data = {"id": "story1", "content": "Once upon a time..."}
        
        # Set story
        result = await cache.set_story_generation("story1", story_data)
        assert result is True
        
        # Get story
        retrieved = await cache.get_story_generation("story1")
        assert retrieved == story_data
        
        # Check stats
        assert cache.cache_stats["story_hits"] == 1

    @pytest.mark.asyncio
    async def test_template_caching(self):
        """Test template caching with critical level."""
        cache = PerformanceCache(memory_cache_size=100, memory_limit_mb=10)
        template = "Template content here"
        
        # Set template
        result = await cache.set_template("template1", template)
        assert result is True
        
        # Get template
        retrieved = await cache.get_template("template1")
        assert retrieved == template
        
        # Check stats
        assert cache.cache_stats["template_hits"] == 1

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self):
        """Test invalidating cache entries by pattern."""
        cache = PerformanceCache(memory_cache_size=100, memory_limit_mb=10)
        
        await cache.set_character("char1", {"name": "Character 1"})
        await cache.set_character("char2", {"name": "Character 2"})
        await cache.set_template("template1", "Template 1")
        
        await cache.invalidate_pattern("character:")
        
        assert await cache.get_character("char1") is None
        assert await cache.get_character("char2") is None
        assert await cache.get_template("template1") is not None

    @pytest.mark.asyncio
    async def test_get_comprehensive_stats(self):
        """Test getting comprehensive cache statistics."""
        cache = PerformanceCache(memory_cache_size=100, memory_limit_mb=10)
        
        await cache.set_character("char1", {"name": "Character 1"})
        await cache.get_character("char1")
        await cache.get_character("nonexistent")
        
        stats = await cache.get_comprehensive_stats()
        assert "memory_cache" in stats
        assert "domain_stats" in stats
        assert "character" in stats["domain_stats"]
        assert "story" in stats["domain_stats"]
        assert "template" in stats["domain_stats"]

    @pytest.mark.asyncio
    async def test_background_cleanup(self):
        """Test background cleanup task."""
        cache = PerformanceCache(memory_cache_size=100, memory_limit_mb=10)
        
        # Start background tasks
        await cache.start_background_tasks()
        assert cache.cleanup_task is not None
        
        # Stop background tasks
        await cache.stop_background_tasks()
        # Task should be cancelled (None or cancelled task is acceptable)
        assert cache.cleanup_task is None or cache.cleanup_task.cancelled()

    @pytest.mark.asyncio
    async def test_warm_cache(self):
        """Test cache warming functionality."""
        cache = PerformanceCache(memory_cache_size=100, memory_limit_mb=10)
        
        # Warm cache with character IDs
        await cache.warm_cache(character_ids=["char1", "char2"])
        
        # Should complete without error
        assert True


class TestGlobalCache:
    """Test global cache functions."""

    @pytest.mark.asyncio
    async def test_get_global_cache(self):
        """Test getting global cache instance."""
        # Close any existing global cache first
        await close_global_cache()
        
        cache1 = await get_global_cache()
        cache2 = await get_global_cache()
        
        # Should return same instance
        assert cache1 is cache2
        
        # Cleanup
        await close_global_cache()

    @pytest.mark.asyncio
    async def test_close_global_cache(self):
        """Test closing global cache."""
        # Get and close global cache
        cache = await get_global_cache()
        await close_global_cache()
        
        # Getting again should create new instance
        cache2 = await get_global_cache()
        assert cache is not cache2
        
        # Cleanup
        await close_global_cache()


class TestCacheBackend:
    """Test CacheBackend abstract class."""

    def test_cache_backend_is_abstract(self):
        """Test that CacheBackend cannot be instantiated."""
        with pytest.raises(TypeError):
            CacheBackend()


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_empty_string_key(self):
        """Test using empty string as key."""
        cache = MemoryCache(max_size=100, max_memory_mb=10)
        await cache.set("", "value")
        result = await cache.get("")
        assert result == "value"

    @pytest.mark.asyncio
    async def test_none_value(self):
        """Test storing None value."""
        cache = MemoryCache(max_size=100, max_memory_mb=10)
        await cache.set("key", None)
        result = await cache.get("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_large_value(self):
        """Test storing large values."""
        cache = MemoryCache(max_size=100, max_memory_mb=10)
        large_value = "x" * 1000000  # 1MB string
        await cache.set("large_key", large_value)
        result = await cache.get("large_key")
        assert result == large_value

    @pytest.mark.asyncio
    async def test_overwrite_existing_key(self):
        """Test overwriting an existing key."""
        cache = MemoryCache(max_size=100, max_memory_mb=10)
        await cache.set("key1", "value1")
        await cache.set("key1", "value2")
        result = await cache.get("key1")
        assert result == "value2"

    @pytest.mark.asyncio
    async def test_memory_limit_eviction(self):
        """Test eviction when memory limit is reached."""
        cache = MemoryCache(max_size=1000, max_memory_mb=1)  # 1MB limit
        
        # Add entries until memory limit
        for i in range(100):
            await cache.set(f"key{i}", "x" * 10000)  # ~10KB each
        
        # Cache should still be functional
        await cache.set("new_key", "new_value")
        result = await cache.get("new_key")
        assert result == "new_value"
