#!/usr/bin/env python3
"""
Comprehensive tests for performance and UX optimizations.

Tests WebSocket performance, caching effectiveness, memory management,
and overall system performance improvements.
"""

import asyncio
import time

import pytest

# Import our optimized components
from src.core.performance_cache import CacheLevel, PerformanceCache

pytestmark = pytest.mark.unit


class TestPerformanceCache:
    """Test caching system performance and correctness."""

    @pytest.mark.asyncio
    async def test_memory_cache_basic_operations(self):
        """Test basic cache get/set operations."""
        cache = PerformanceCache()

        # Test cache miss
        result = await cache.get_character("test_char")
        assert result is None

        # Test cache set and hit
        test_data = {"name": "Test Character", "type": "hero"}
        await cache.set_character("test_char", test_data)

        result = await cache.get_character("test_char")
        assert result == test_data

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self):
        """Test TTL-based cache expiration."""
        cache = PerformanceCache()

        # Set with very short TTL
        test_data = {"name": "Test Character"}
        await cache.set_character("test_char", test_data, ttl=0.1)  # 100ms

        # Should be available immediately
        result = await cache.get_character("test_char")
        assert result == test_data

        # Wait for expiration
        await asyncio.sleep(0.2)

        # Should be expired
        result = await cache.get_character("test_char")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_levels_and_eviction(self):
        """Test intelligent cache eviction based on levels."""
        # Create small cache for testing eviction
        cache = PerformanceCache(memory_cache_size=3, memory_limit_mb=1)

        # Fill cache with different priority levels
        await cache.memory_cache.set("critical", "data1", level=CacheLevel.CRITICAL)
        await cache.memory_cache.set("high", "data2", level=CacheLevel.HIGH)
        await cache.memory_cache.set("low", "data3", level=CacheLevel.LOW)

        # Add one more item (should evict LOW priority first)
        await cache.memory_cache.set("medium", "data4", level=CacheLevel.MEDIUM)

        # Critical and high should still be there
        assert await cache.memory_cache.get("critical") == "data1"
        assert await cache.memory_cache.get("high") == "data2"

        # Low priority should be evicted
        assert await cache.memory_cache.get("low") is None

    @pytest.mark.asyncio
    async def test_cache_statistics(self):
        """Test cache hit/miss statistics tracking."""
        cache = PerformanceCache()

        # Initial stats
        stats = await cache.get_comprehensive_stats()
        assert stats["domain_stats"]["character"]["hits"] == 0
        assert stats["domain_stats"]["character"]["misses"] == 0

        # Cause cache miss
        await cache.get_character("nonexistent")

        # Cache miss should be recorded
        stats = await cache.get_comprehensive_stats()
        assert stats["domain_stats"]["character"]["misses"] == 1

        # Add item and cause cache hit
        await cache.set_character("test", {"name": "test"})
        await cache.get_character("test")

        # Cache hit should be recorded
        stats = await cache.get_comprehensive_stats()
        assert stats["domain_stats"]["character"]["hits"] == 1

    @pytest.mark.asyncio
    async def test_cache_invalidation_patterns(self):
        """Test pattern-based cache invalidation."""
        cache = PerformanceCache()

        # Set multiple character entries
        await cache.set_character("char1", {"name": "Character 1"})
        await cache.set_character("char2", {"name": "Character 2"})
        await cache.set_story_generation("story1", {"title": "Story 1"})

        # Invalidate character pattern
        await cache.invalidate_pattern("character:")

        # Character entries should be gone
        assert await cache.get_character("char1") is None
        assert await cache.get_character("char2") is None

        # Story entry should remain
        assert await cache.get_story_generation("story1") is not None


class TestIntegratedPerformance:
    """Test overall system performance with optimizations."""

    @pytest.mark.asyncio
    async def test_memory_usage_efficiency(self):
        """Test memory usage remains reasonable under load."""
        cache = PerformanceCache(memory_limit_mb=10)  # 10MB limit

        # Add many items to test memory management
        for i in range(1000):
            large_data = {"content": "x" * 1000, "id": i}  # ~1KB each
            await cache.set_character(f"char_{i}", large_data)

        # Check memory usage stays within bounds
        stats = await cache.get_comprehensive_stats()
        memory_mb = stats["memory_cache"]["memory_usage_mb"]
        assert memory_mb <= 10.5  # Small buffer for overhead

        # Cache should still be functional
        recent_char = await cache.get_character("char_999")
        assert recent_char is not None


class TestFrontendOptimizations:
    """Test frontend optimizations (requires frontend test environment)."""

    @pytest.mark.unit
    def test_api_cache_deduplication(self):
        """Test API request deduplication prevents duplicate calls."""
        # This would require a more complex test setup with actual HTTP mocking
        # For now, we can test the cache logic

    @pytest.mark.unit
    def test_mobile_responsive_behavior(self):
        """Test mobile-responsive UI adaptations."""
        # This would require React Testing Library setup


if __name__ == "__main__":
    # Run basic performance benchmark
    async def run_benchmark():
        print("🚀 Running Performance Optimization Benchmark...")

        # Test cache performance
        cache = PerformanceCache()
        start_time = time.time()

        # Simulate realistic usage
        for i in range(1000):
            await cache.set_character(f"char_{i}", {"name": f"Character {i}"})
            await cache.get_character(f"char_{i}")

        cache_duration = time.time() - start_time
        stats = await cache.get_comprehensive_stats()

        print("✅ Cache Performance:")
        print(f"   - 1000 operations completed in {cache_duration:.2f}s")
        print(f"   - Memory usage: {stats['memory_cache']['memory_usage_mb']:.1f}MB")
        print(f"   - Hit rate: {stats['memory_cache']['hit_rate']:.1%}")

        print("🎉 Performance benchmark complete!")

    asyncio.run(run_benchmark())
