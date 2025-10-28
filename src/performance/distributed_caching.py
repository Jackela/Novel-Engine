#!/usr/bin/env python3
"""
DISTRIBUTED CACHING SYSTEM FOR NOVEL ENGINE
================================================

Advanced multi-tier caching system with Redis integration and intelligent
cache strategies for high-performance distributed operations.

Features:
- Multi-tier caching (L1: Memory, L2: Redis, L3: Database)
- Intelligent cache invalidation and refresh
- Cache warming and preloading strategies
- Distributed cache coordination
- Performance monitoring and optimization
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheLevel(str, Enum):
    """Cache tier enumeration"""

    L1_MEMORY = "l1_memory"  # In-process memory cache
    L2_REDIS = "l2_redis"  # Redis distributed cache
    L3_DATABASE = "l3_database"  # Database cache layer


class CacheStrategy(str, Enum):
    """Cache strategy enumeration"""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    READ_THROUGH = "read_through"


@dataclass
class CacheMetrics:
    """Cache performance metrics"""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    total_requests: int = 0
    average_response_time: float = 0.0
    memory_usage: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate percentage"""
        total = self.hits + self.misses
        return (self.hits / max(total, 1)) * 100

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate percentage"""
        return 100.0 - self.hit_rate


@dataclass
class CacheEntry:
    """Cache entry with metadata"""

    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl: Optional[int] = None  # TTL in seconds
    size: int = 0
    tags: List[str] = field(default_factory=list)

    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        if self.ttl is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl

    @property
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds"""
        return (datetime.now() - self.created_at).total_seconds()

    def update_access(self):
        """Update access metadata"""
        self.last_accessed = datetime.now()
        self.access_count += 1


class CacheInterface(ABC):
    """Abstract interface for cache implementations"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries"""
        pass

    @abstractmethod
    def get_metrics(self) -> CacheMetrics:
        """Get cache performance metrics"""
        pass


class MemoryCache(CacheInterface):
    """
    L1 Memory Cache Implementation
    High-speed in-process cache with intelligent eviction
    """

    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU tracking
        self._frequency: Dict[str, int] = defaultdict(int)  # For LFU tracking
        self._lock = asyncio.Lock()
        self.metrics = CacheMetrics()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache"""
        start_time = time.time()

        async with self._lock:
            self.metrics.total_requests += 1

            if key not in self._cache:
                self.metrics.misses += 1
                return None

            entry = self._cache[key]

            # Check expiration
            if entry.is_expired:
                await self._delete_entry(key)
                self.metrics.misses += 1
                return None

            # Update access metadata
            entry.update_access()
            self._update_access_order(key)
            self._frequency[key] += 1

            self.metrics.hits += 1
            response_time = time.time() - start_time
            self._update_response_time(response_time)

            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in memory cache"""
        async with self._lock:
            # Calculate entry size (rough estimation)
            entry_size = len(str(value))

            # Check if we need to evict entries
            if len(self._cache) >= self.max_size and key not in self._cache:
                await self._evict_entries()

            # Create cache entry
            entry = CacheEntry(
                key=key, value=value, ttl=ttl or self.default_ttl, size=entry_size
            )

            self._cache[key] = entry
            self._update_access_order(key)
            self.metrics.sets += 1
            self.metrics.memory_usage += entry_size

            return True

    async def delete(self, key: str) -> bool:
        """Delete value from memory cache"""
        async with self._lock:
            return await self._delete_entry(key)

    async def _delete_entry(self, key: str) -> bool:
        """Internal delete entry method"""
        if key in self._cache:
            entry = self._cache[key]
            del self._cache[key]

            if key in self._access_order:
                self._access_order.remove(key)

            if key in self._frequency:
                del self._frequency[key]

            self.metrics.deletes += 1
            self.metrics.memory_usage -= entry.size
            return True
        return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        async with self._lock:
            return key in self._cache and not self._cache[key].is_expired

    async def clear(self) -> bool:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._frequency.clear()
            self.metrics.memory_usage = 0
            return True

    def get_metrics(self) -> CacheMetrics:
        """Get cache performance metrics"""
        self.metrics.last_updated = datetime.now()
        return self.metrics

    def _update_access_order(self, key: str):
        """Update LRU access order"""
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def _update_response_time(self, response_time: float):
        """Update average response time"""
        total_requests = self.metrics.hits + self.metrics.misses
        if total_requests > 0:
            self.metrics.average_response_time = (
                self.metrics.average_response_time * (total_requests - 1)
                + response_time
            ) / total_requests

    async def _evict_entries(self, count: int = 1):
        """Evict cache entries using LRU strategy"""
        evicted = 0
        while evicted < count and self._access_order:
            # Get least recently used key
            lru_key = self._access_order[0]
            await self._delete_entry(lru_key)
            self.metrics.evictions += 1
            evicted += 1


class RedisCache(CacheInterface):
    """
    L2 Redis Cache Implementation
    Distributed cache for multi-instance coordination
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        prefix: str = "novel_engine:",
        default_ttl: int = 3600,
    ):
        self.redis_url = redis_url
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.metrics = CacheMetrics()
        self._redis = None

    async def _get_redis(self):
        """Get Redis connection (lazy initialization)"""
        if self._redis is None:
            try:
                import aioredis

                self._redis = aioredis.from_url(self.redis_url)
            except ImportError:
                logger.warning("aioredis not available, using mock Redis")
                self._redis = MockRedis()
        return self._redis

    def _make_key(self, key: str) -> str:
        """Create prefixed Redis key"""
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        start_time = time.time()

        try:
            redis = await self._get_redis()
            redis_key = self._make_key(key)

            value = await redis.get(redis_key)

            self.metrics.total_requests += 1
            response_time = time.time() - start_time

            if value is None:
                self.metrics.misses += 1
                return None

            # Deserialize value
            deserialized = json.loads(value)
            self.metrics.hits += 1
            self._update_response_time(response_time)

            return deserialized

        except Exception as e:
            logger.error(f"Redis get error: {e}")
            self.metrics.misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache"""
        try:
            redis = await self._get_redis()
            redis_key = self._make_key(key)

            # Serialize value
            serialized = json.dumps(value, default=str)

            # Set with TTL
            expire_time = ttl or self.default_ttl
            result = await redis.setex(redis_key, expire_time, serialized)

            self.metrics.sets += 1
            return bool(result)

        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from Redis cache"""
        try:
            redis = await self._get_redis()
            redis_key = self._make_key(key)

            result = await redis.delete(redis_key)
            self.metrics.deletes += 1
            return bool(result)

        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache"""
        try:
            redis = await self._get_redis()
            redis_key = self._make_key(key)

            result = await redis.exists(redis_key)
            return bool(result)

        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False

    async def clear(self) -> bool:
        """Clear all cache entries with prefix"""
        try:
            redis = await self._get_redis()

            # Find keys with prefix
            keys = await redis.keys(f"{self.prefix}*")

            if keys:
                await redis.delete(*keys)

            return True

        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return False

    def get_metrics(self) -> CacheMetrics:
        """Get cache performance metrics"""
        self.metrics.last_updated = datetime.now()
        return self.metrics

    def _update_response_time(self, response_time: float):
        """Update average response time"""
        total_requests = self.metrics.hits + self.metrics.misses
        if total_requests > 0:
            self.metrics.average_response_time = (
                self.metrics.average_response_time * (total_requests - 1)
                + response_time
            ) / total_requests


class MockRedis:
    """Mock Redis implementation for testing without Redis server"""

    def __init__(self):
        self._data = {}
        self._expiry = {}

    async def get(self, key: str) -> Optional[str]:
        if key in self._expiry and datetime.now() > self._expiry[key]:
            del self._data[key]
            del self._expiry[key]
            return None
        return self._data.get(key)

    async def setex(self, key: str, seconds: int, value: str) -> bool:
        self._data[key] = value
        self._expiry[key] = datetime.now() + timedelta(seconds=seconds)
        return True

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                if key in self._expiry:
                    del self._expiry[key]
                deleted += 1
        return deleted

    async def exists(self, key: str) -> int:
        if key in self._expiry and datetime.now() > self._expiry[key]:
            del self._data[key]
            del self._expiry[key]
            return 0
        return 1 if key in self._data else 0

    async def keys(self, pattern: str) -> List[str]:
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [key for key in self._data.keys() if key.startswith(prefix)]
        return list(self._data.keys())


class DistributedCache:
    """
    Multi-tier distributed cache system
    Coordinates L1 (Memory), L2 (Redis), and L3 (Database) caches
    """

    def __init__(
        self,
        l1_cache: Optional[MemoryCache] = None,
        l2_cache: Optional[RedisCache] = None,
        enable_write_through: bool = True,
        enable_read_through: bool = True,
    ):

        self.l1_cache = l1_cache or MemoryCache()
        self.l2_cache = l2_cache or RedisCache()
        self.enable_write_through = enable_write_through
        self.enable_read_through = enable_read_through

        self.combined_metrics = CacheMetrics()
        self._cache_loaders: Dict[str, Callable] = {}

    def register_cache_loader(self, key_pattern: str, loader: Callable):
        """Register a cache loader for specific key patterns"""
        self._cache_loaders[key_pattern] = loader

    async def get(self, key: str) -> Optional[Any]:
        """Get value from multi-tier cache"""
        start_time = time.time()

        # Try L1 cache first
        value = await self.l1_cache.get(key)
        if value is not None:
            logger.debug(f"Cache hit L1: {key}")
            self._update_combined_metrics("l1_hit", time.time() - start_time)
            return value

        # Try L2 cache
        value = await self.l2_cache.get(key)
        if value is not None:
            logger.debug(f"Cache hit L2: {key}")
            # Write back to L1
            await self.l1_cache.set(key, value)
            self._update_combined_metrics("l2_hit", time.time() - start_time)
            return value

        # Try cache loader (read-through)
        if self.enable_read_through:
            value = await self._load_from_source(key)
            if value is not None:
                logger.debug(f"Cache loaded from source: {key}")
                # Populate both caches
                await self.l1_cache.set(key, value)
                await self.l2_cache.set(key, value)
                self._update_combined_metrics("source_hit", time.time() - start_time)
                return value

        self._update_combined_metrics("miss", time.time() - start_time)
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in multi-tier cache"""
        results = []

        # Set in L1 cache
        result_l1 = await self.l1_cache.set(key, value, ttl)
        results.append(result_l1)

        # Set in L2 cache
        result_l2 = await self.l2_cache.set(key, value, ttl)
        results.append(result_l2)

        # Write-through to database if enabled
        if self.enable_write_through:
            await self._write_to_source(key, value)

        self.combined_metrics.sets += 1
        return all(results)

    async def delete(self, key: str) -> bool:
        """Delete value from all cache tiers"""
        results = []

        # Delete from L1
        result_l1 = await self.l1_cache.delete(key)
        results.append(result_l1)

        # Delete from L2
        result_l2 = await self.l2_cache.delete(key)
        results.append(result_l2)

        self.combined_metrics.deletes += 1
        return any(results)

    async def exists(self, key: str) -> bool:
        """Check if key exists in any cache tier"""
        # Check L1 first
        if await self.l1_cache.exists(key):
            return True

        # Check L2
        return await self.l2_cache.exists(key)

    async def clear(self, level: Optional[CacheLevel] = None) -> bool:
        """Clear cache tiers"""
        if level == CacheLevel.L1_MEMORY:
            return await self.l1_cache.clear()
        elif level == CacheLevel.L2_REDIS:
            return await self.l2_cache.clear()
        else:
            # Clear all levels
            result_l1 = await self.l1_cache.clear()
            result_l2 = await self.l2_cache.clear()
            return result_l1 and result_l2

    async def warm_cache(self, keys: List[str]):
        """Warm cache by preloading data"""
        logger.info(f"Warming cache with {len(keys)} keys")

        tasks = []
        for key in keys:
            task = asyncio.create_task(self.get(key))
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info("Cache warming completed")

    async def _load_from_source(self, key: str) -> Optional[Any]:
        """Load data from source using registered loaders"""
        for pattern, loader in self._cache_loaders.items():
            if pattern in key or pattern == "*":
                try:
                    if asyncio.iscoroutinefunction(loader):
                        return await loader(key)
                    else:
                        return loader(key)
                except Exception as e:
                    logger.error(f"Cache loader error for {key}: {e}")
        return None

    async def _write_to_source(self, key: str, value: Any):
        """Write data to source (write-through)"""
        # This would integrate with your database layer
        logger.debug(f"Write-through to source: {key}")

    def _update_combined_metrics(self, hit_type: str, response_time: float):
        """Update combined cache metrics"""
        self.combined_metrics.total_requests += 1

        if hit_type in ["l1_hit", "l2_hit", "source_hit"]:
            self.combined_metrics.hits += 1
        else:
            self.combined_metrics.misses += 1

        # Update response time
        total = self.combined_metrics.hits + self.combined_metrics.misses
        self.combined_metrics.average_response_time = (
            self.combined_metrics.average_response_time * (total - 1) + response_time
        ) / total

    def get_comprehensive_metrics(self) -> Dict[str, CacheMetrics]:
        """Get metrics from all cache tiers"""
        return {
            "combined": self.combined_metrics,
            "l1_memory": self.l1_cache.get_metrics(),
            "l2_redis": self.l2_cache.get_metrics(),
        }


# Novel Engine specific cache implementations


class CharacterCache:
    """Specialized cache for character data"""

    def __init__(self, distributed_cache: DistributedCache):
        self.cache = distributed_cache

        # Register cache loaders
        self.cache.register_cache_loader("character:", self._load_character)
        self.cache.register_cache_loader("character_list", self._load_character_list)

    async def get_character(self, character_id: str) -> Optional[Dict]:
        """Get character data with caching"""
        key = f"character:{character_id}"
        return await self.cache.get(key)

    async def set_character(
        self, character_id: str, character_data: Dict, ttl: int = 3600
    ) -> bool:
        """Set character data in cache"""
        key = f"character:{character_id}"
        return await self.cache.set(key, character_data, ttl)

    async def get_character_list(self) -> Optional[List[Dict]]:
        """Get character list with caching"""
        return await self.cache.get("character_list")

    async def invalidate_character(self, character_id: str):
        """Invalidate character cache"""
        await self.cache.delete(f"character:{character_id}")
        await self.cache.delete("character_list")  # Invalidate list cache too

    async def _load_character(self, key: str) -> Optional[Dict]:
        """Load character from database"""
        character_id = key.replace("character:", "")
        # This would integrate with your database
        logger.debug(f"Loading character from database: {character_id}")
        return {
            "id": character_id,
            "name": f"Character {character_id}",
            "loaded_from_db": True,
        }

    async def _load_character_list(self, key: str) -> Optional[List[Dict]]:
        """Load character list from database"""
        logger.debug("Loading character list from database")
        return [{"id": "1", "name": "Character 1"}, {"id": "2", "name": "Character 2"}]


# Example usage and testing
async def main():
    """Demonstrate distributed caching system"""
    logger.info("Starting Novel Engine Distributed Caching Demo")

    # Initialize caches
    memory_cache = MemoryCache(max_size=1000)
    redis_cache = RedisCache()
    distributed_cache = DistributedCache(memory_cache, redis_cache)

    # Initialize specialized caches
    character_cache = CharacterCache(distributed_cache)

    # Demo operations
    logger.info("Testing character caching...")

    # First access - should load from source
    character = await character_cache.get_character("test_char_1")
    logger.info(f"First access: {character}")

    # Second access - should hit cache
    character = await character_cache.get_character("test_char_1")
    logger.info(f"Second access (cached): {character}")

    # Set custom character
    custom_character = {
        "id": "custom_1",
        "name": "Custom Character",
        "faction": "Imperial",
    }
    await character_cache.set_character("custom_1", custom_character)

    # Retrieve custom character
    retrieved = await character_cache.get_character("custom_1")
    logger.info(f"Custom character: {retrieved}")

    # Test cache warming
    await distributed_cache.warm_cache(
        ["character:warm_1", "character:warm_2", "character:warm_3"]
    )

    # Display comprehensive metrics
    metrics = distributed_cache.get_comprehensive_metrics()
    for level, metric in metrics.items():
        logger.info(
            f"{level} cache - Hit rate: {metric.hit_rate:.1f}%, "
            f"Requests: {metric.total_requests}, "
            f"Avg response: {metric.average_response_time*1000:.1f}ms"
        )

    logger.info("Distributed caching demonstration complete")


if __name__ == "__main__":
    asyncio.run(main())
