#!/usr/bin/env python3
"""
Performance Cache System for Novel Engine.

Intelligent caching layer with memory management, TTL support,
and performance optimization for character data and story generation.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache level priorities for intelligent memory management."""

    CRITICAL = "critical"  # Essential data - never evict
    HIGH = "high"  # Frequently accessed - evict last
    MEDIUM = "medium"  # Standard caching - normal eviction
    LOW = "low"  # Temporary data - evict first


@dataclass
class CacheEntry:
    """Individual cache entry with metadata."""

    key: str
    value: Any
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: Optional[float] = None
    level: CacheLevel = CacheLevel.MEDIUM
    memory_size: int = 0

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def update_access(self):
        """Update access statistics."""
        self.last_accessed = time.time()
        self.access_count += 1


class CacheBackend(ABC):
    """Abstract cache backend interface."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache by key.

        Args:
            key: The cache key to retrieve

        Returns:
            The cached value if found, None otherwise
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """
        Store a value in the cache with optional TTL.

        Args:
            key: The cache key to store under
            value: The value to cache
            ttl: Time to live in seconds, None for no expiration

        Returns:
            True if successfully stored, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Remove a value from the cache.

        Args:
            key: The cache key to remove

        Returns:
            True if key was found and removed, False otherwise
        """
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """
        Clear all entries from the cache.

        Returns:
            True if cache was successfully cleared
        """
        pass


class MemoryCache(CacheBackend):
    """High-performance in-memory cache with intelligent eviction."""

    def __init__(self, max_size: int = 10000, max_memory_mb: int = 500):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self.memory_usage = 0
        self.hit_count = 0
        self.miss_count = 0
        self.lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with LRU tracking."""
        async with self.lock:
            entry = self.entries.get(key)
            if entry is None:
                self.miss_count += 1
                return None

            if entry.is_expired():
                await self._remove_entry(key)
                self.miss_count += 1
                return None

            # Update access stats and move to end (most recent)
            entry.update_access()
            self.entries.move_to_end(key)
            self.hit_count += 1

            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        level: CacheLevel = CacheLevel.MEDIUM,
    ) -> bool:
        """Set value in cache with intelligent eviction."""
        async with self.lock:
            # Calculate memory size
            memory_size = self._calculate_memory_size(value)

            # Remove existing entry if present
            if key in self.entries:
                await self._remove_entry(key)

            # Check if we need to make space
            await self._ensure_space(memory_size, level)

            # Create and store entry
            entry = CacheEntry(
                key=key, value=value, ttl=ttl, level=level, memory_size=memory_size
            )

            self.entries[key] = entry
            self.memory_usage += memory_size

            return True

    async def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        async with self.lock:
            if key in self.entries:
                await self._remove_entry(key)
                return True
            return False

    async def clear(self) -> bool:
        """Clear all cache entries."""
        async with self.lock:
            self.entries.clear()
            self.memory_usage = 0
            return True

    async def _remove_entry(self, key: str):
        """Remove entry and update memory tracking."""
        entry = self.entries.pop(key, None)
        if entry:
            self.memory_usage -= entry.memory_size

    async def _ensure_space(self, required_memory: int, level: CacheLevel):
        """Ensure sufficient space using intelligent eviction."""
        # Check memory limit
        while (
            self.memory_usage + required_memory > self.max_memory_bytes
            or len(self.entries) >= self.max_size
        ):
            if not self.entries:
                break

            # Find best candidate for eviction
            eviction_key = self._find_eviction_candidate(level)
            if eviction_key:
                await self._remove_entry(eviction_key)
            else:
                # Can't evict anything - reject new entry
                raise MemoryError("Cache full and no evictable entries")

    def _find_eviction_candidate(self, new_level: CacheLevel) -> Optional[str]:
        """Find best entry to evict using intelligent strategy."""
        candidates = []
        current_time = time.time()

        for key, entry in self.entries.items():
            # Never evict critical entries
            if entry.level == CacheLevel.CRITICAL:
                continue

            # Calculate eviction score (higher = better candidate)
            score = 0

            # Age factor (older = higher score)
            age = current_time - entry.created_at
            score += age / 3600  # Age in hours

            # Access frequency (less frequent = higher score)
            frequency = entry.access_count / max(age / 3600, 0.1)
            score += 10 / max(frequency, 0.1)

            # Last access time (longer ago = higher score)
            last_access = current_time - entry.last_accessed
            score += last_access / 1800  # 30 minutes

            # Level priority (lower level = higher score)
            level_scores = {
                CacheLevel.LOW: 4,
                CacheLevel.MEDIUM: 2,
                CacheLevel.HIGH: 1,
                CacheLevel.CRITICAL: 0,
            }
            score += level_scores.get(entry.level, 2)

            # Memory size (larger = higher score for space efficiency)
            score += entry.memory_size / (1024 * 1024)  # MB

            candidates.append((key, score))

        if not candidates:
            return None

        # Return key with highest eviction score
        return max(candidates, key=lambda x: x[1])[0]

    def _calculate_memory_size(self, value: Any) -> int:
        """Estimate memory size of value."""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            elif isinstance(value, (dict, list)):
                return len(json.dumps(value, default=str).encode("utf-8"))
            else:
                return len(str(value).encode("utf-8"))
        except Exception:
            return 1024  # Default 1KB estimate

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests) if total_requests > 0 else 0

        return {
            "entries": len(self.entries),
            "memory_usage_mb": self.memory_usage / (1024 * 1024),
            "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
            "memory_utilization": self.memory_usage / self.max_memory_bytes,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": hit_rate,
            "max_size": self.max_size,
        }


class PerformanceCache:
    """Main performance cache system with multiple backends and intelligent routing."""

    def __init__(self, memory_cache_size: int = 10000, memory_limit_mb: int = 500):
        self.memory_cache = MemoryCache(memory_cache_size, memory_limit_mb)
        self.cache_stats = {
            "character_hits": 0,
            "character_misses": 0,
            "story_hits": 0,
            "story_misses": 0,
            "template_hits": 0,
            "template_misses": 0,
        }
        self.cleanup_task = None

    async def start_background_tasks(self):
        """Start background cache maintenance."""
        if not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop_background_tasks(self):
        """Stop background cache maintenance."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self):
        """Background cleanup for expired entries."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")

    async def _cleanup_expired(self):
        """Remove expired entries from cache."""
        expired_keys = []
        async with self.memory_cache.lock:
            for key, entry in self.memory_cache.entries.items():
                if entry.is_expired():
                    expired_keys.append(key)

        for key in expired_keys:
            await self.memory_cache.delete(key)

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

    # Character Caching Methods
    async def get_character(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Get character data from cache."""
        key = f"character:{character_id}"
        result = await self.memory_cache.get(key)

        if result:
            self.cache_stats["character_hits"] += 1
        else:
            self.cache_stats["character_misses"] += 1

        return result

    async def set_character(
        self,
        character_id: str,
        character_data: Dict[str, Any],
        ttl: Optional[float] = 3600,
    ) -> bool:
        """Cache character data with 1-hour TTL."""
        key = f"character:{character_id}"
        return await self.memory_cache.set(
            key, character_data, ttl=ttl, level=CacheLevel.HIGH
        )

    # Story Generation Caching
    async def get_story_generation(
        self, generation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get story generation data from cache."""
        key = f"story_gen:{generation_id}"
        result = await self.memory_cache.get(key)

        if result:
            self.cache_stats["story_hits"] += 1
        else:
            self.cache_stats["story_misses"] += 1

        return result

    async def set_story_generation(
        self,
        generation_id: str,
        generation_data: Dict[str, Any],
        ttl: Optional[float] = 7200,
    ) -> bool:
        """Cache story generation data with 2-hour TTL."""
        key = f"story_gen:{generation_id}"
        return await self.memory_cache.set(
            key, generation_data, ttl=ttl, level=CacheLevel.MEDIUM
        )

    # Template Caching
    async def get_template(self, template_key: str) -> Optional[str]:
        """Get template from cache."""
        key = f"template:{template_key}"
        result = await self.memory_cache.get(key)

        if result:
            self.cache_stats["template_hits"] += 1
        else:
            self.cache_stats["template_misses"] += 1

        return result

    async def set_template(
        self, template_key: str, template_content: str, ttl: Optional[float] = None
    ) -> bool:
        """Cache template with no expiration (templates rarely change)."""
        key = f"template:{template_key}"
        return await self.memory_cache.set(
            key, template_content, ttl=ttl, level=CacheLevel.CRITICAL
        )

    # Utility Methods
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern."""
        keys_to_delete = []
        async with self.memory_cache.lock:
            for key in self.memory_cache.entries.keys():
                if pattern in key:
                    keys_to_delete.append(key)

        for key in keys_to_delete:
            await self.memory_cache.delete(key)

        logger.debug(
            f"Invalidated {len(keys_to_delete)} cache entries matching '{pattern}'"
        )

    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        memory_stats = await self.memory_cache.get_stats()

        # Calculate domain-specific hit rates
        char_total = (
            self.cache_stats["character_hits"] + self.cache_stats["character_misses"]
        )
        story_total = self.cache_stats["story_hits"] + self.cache_stats["story_misses"]
        template_total = (
            self.cache_stats["template_hits"] + self.cache_stats["template_misses"]
        )

        return {
            "memory_cache": memory_stats,
            "domain_stats": {
                "character": {
                    "hits": self.cache_stats["character_hits"],
                    "misses": self.cache_stats["character_misses"],
                    "hit_rate": self.cache_stats["character_hits"] / max(char_total, 1),
                },
                "story": {
                    "hits": self.cache_stats["story_hits"],
                    "misses": self.cache_stats["story_misses"],
                    "hit_rate": self.cache_stats["story_hits"] / max(story_total, 1),
                },
                "template": {
                    "hits": self.cache_stats["template_hits"],
                    "misses": self.cache_stats["template_misses"],
                    "hit_rate": self.cache_stats["template_hits"]
                    / max(template_total, 1),
                },
            },
        }

    async def warm_cache(self, character_ids: List[str] = None):
        """Pre-warm cache with frequently accessed data."""
        # This would integrate with the actual data layer to pre-load
        # frequently accessed characters, templates, etc.
        logger.info("Cache warming initiated")

        if character_ids:
            logger.info(f"Pre-warming cache for {len(character_ids)} characters")
            # Would load character data here

        # Pre-load critical templates
        logger.info("Pre-warming template cache")
        # Would load templates here


# Global cache instance
_global_cache: Optional[PerformanceCache] = None


async def get_global_cache() -> PerformanceCache:
    """Get or create global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = PerformanceCache()
        await _global_cache.start_background_tasks()
    return _global_cache


async def close_global_cache():
    """Close global cache and cleanup resources."""
    global _global_cache
    if _global_cache:
        await _global_cache.stop_background_tasks()
        await _global_cache.memory_cache.clear()
        _global_cache = None


__all__ = [
    "PerformanceCache",
    "CacheLevel",
    "CacheEntry",
    "MemoryCache",
    "get_global_cache",
    "close_global_cache",
]
