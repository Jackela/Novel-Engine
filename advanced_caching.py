#!/usr/bin/env python3
"""
Advanced Multi-Layer Caching System for Novel Engine - Iteration 2.

This module implements a sophisticated caching infrastructure with Redis compatibility,
intelligent cache warming, performance monitoring, and adaptive invalidation strategies.
"""

import asyncio
import json
import time
import hashlib
import weakref
import threading
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, OrderedDict
from functools import wraps
import logging
import os
from pathlib import Path
import pickle
import sqlite3
import aiosqlite
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Represents a cached item with metadata."""
    value: Any
    timestamp: float
    access_count: int = 0
    ttl: float = 3600.0  # 1 hour default
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)
    priority: int = 1  # 1=low, 2=medium, 3=high
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() - self.timestamp > self.ttl
    
    def touch(self):
        """Update access count and timestamp."""
        self.access_count += 1
        # Don't update timestamp on access to preserve TTL

@dataclass
class CacheStats:
    """Cache statistics for monitoring and optimization."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    avg_access_time: float = 0.0
    hit_rate: float = 0.0
    
    def update_hit_rate(self):
        """Update the hit rate based on hits and misses."""
        total = self.hits + self.misses
        self.hit_rate = self.hits / total if total > 0 else 0.0

class CacheWarmer:
    """Intelligent cache warming system for frequently accessed data."""
    
    def __init__(self, cache_instance):
        self.cache = weakref.ref(cache_instance)
        self.warming_strategies = {}
        self.warm_patterns = []
        self.executor = ThreadPoolExecutor(max_workers=2)
        
    def register_warming_strategy(self, pattern: str, strategy: Callable):
        """Register a cache warming strategy for a specific pattern."""
        self.warming_strategies[pattern] = strategy
        
    def add_warm_pattern(self, pattern: str, ttl: float = 7200.0):
        """Add a pattern to be warmed on startup."""
        self.warm_patterns.append((pattern, ttl))
        
    async def warm_cache(self):
        """Execute all registered warming strategies."""
        cache = self.cache()
        if not cache:
            return
            
        logger.info("Starting intelligent cache warming...")
        start_time = time.time()
        warmed_count = 0
        
        for pattern, ttl in self.warm_patterns:
            if pattern in self.warming_strategies:
                try:
                    strategy = self.warming_strategies[pattern]
                    loop = asyncio.get_event_loop()
                    
                    # Execute warming strategy in thread pool
                    data = await loop.run_in_executor(self.executor, strategy)
                    
                    if isinstance(data, dict):
                        for key, value in data.items():
                            await cache.set(key, value, ttl=ttl, priority=3)
                            warmed_count += 1
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, tuple) and len(item) == 2:
                                key, value = item
                                await cache.set(key, value, ttl=ttl, priority=3)
                                warmed_count += 1
                                
                    logger.debug(f"Warmed cache pattern '{pattern}' with {len(data) if data else 0} entries")
                    
                except Exception as e:
                    logger.error(f"Error warming cache pattern '{pattern}': {e}")
        
        duration = time.time() - start_time
        logger.info(f"Cache warming completed: {warmed_count} entries in {duration:.2f}s")
        
    def shutdown(self):
        """Shutdown the cache warmer."""
        self.executor.shutdown(wait=True)

class RedisCompatibleCache:
    """Redis-compatible caching interface with local implementation."""
    
    def __init__(self, max_size: int = 10000, max_memory_mb: int = 512):
        self.data = OrderedDict()
        self.stats = CacheStats()
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.lock = asyncio.Lock()
        self.warmer = CacheWarmer(self)
        self.invalidation_patterns = {}
        self.access_log = []
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (Redis GET compatible)."""
        async with self.lock:
            if key in self.data:
                entry = self.data[key]
                if entry.is_expired():
                    await self._remove_entry(key)
                    self.stats.misses += 1
                    return None
                
                # Move to end (LRU)
                self.data.move_to_end(key)
                entry.touch()
                self.stats.hits += 1
                self._log_access(key, 'hit')
                return entry.value
            
            self.stats.misses += 1
            self._log_access(key, 'miss')
            return None
    
    async def set(self, key: str, value: Any, ttl: float = 3600.0, priority: int = 1) -> bool:
        """Set value in cache (Redis SET compatible)."""
        async with self.lock:
            # Serialize value to calculate size
            try:
                serialized = pickle.dumps(value)
                size_bytes = len(serialized)
            except:
                # Fallback size estimation
                size_bytes = len(str(value)) * 2
            
            entry = CacheEntry(
                value=value,
                timestamp=time.time(),
                ttl=ttl,
                size_bytes=size_bytes,
                priority=priority
            )
            
            # Check if we need to evict
            await self._ensure_capacity(size_bytes)
            
            if key in self.data:
                old_entry = self.data[key]
                self.stats.size_bytes -= old_entry.size_bytes
            
            self.data[key] = entry
            self.data.move_to_end(key)
            
            self.stats.size_bytes += size_bytes
            self.stats.entry_count = len(self.data)
            self._log_access(key, 'set')
            
            return True
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache (Redis DEL compatible)."""
        async with self.lock:
            if key in self.data:
                await self._remove_entry(key)
                return True
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists (Redis EXISTS compatible)."""
        async with self.lock:
            if key in self.data:
                entry = self.data[key]
                if entry.is_expired():
                    await self._remove_entry(key)
                    return False
                return True
            return False
    
    async def ttl(self, key: str) -> float:
        """Get TTL for key (Redis TTL compatible)."""
        async with self.lock:
            if key in self.data:
                entry = self.data[key]
                if entry.is_expired():
                    await self._remove_entry(key)
                    return -2
                remaining = entry.ttl - (time.time() - entry.timestamp)
                return max(0, remaining)
            return -2
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern (Redis KEYS compatible)."""
        async with self.lock:
            if pattern == "*":
                return list(self.data.keys())
            
            # Simple pattern matching (could be enhanced)
            import fnmatch
            return [key for key in self.data.keys() if fnmatch.fnmatch(key, pattern)]
    
    async def flushall(self) -> bool:
        """Clear all cache entries (Redis FLUSHALL compatible)."""
        async with self.lock:
            self.data.clear()
            self.stats = CacheStats()
            return True
    
    async def info(self) -> Dict[str, Any]:
        """Get cache information (Redis INFO compatible)."""
        async with self.lock:
            self.stats.entry_count = len(self.data)
            self.stats.update_hit_rate()
            
            return {
                'entries': self.stats.entry_count,
                'memory_usage': self.stats.size_bytes,
                'memory_limit': self.max_memory_bytes,
                'hits': self.stats.hits,
                'misses': self.stats.misses,
                'hit_rate': self.stats.hit_rate,
                'evictions': self.stats.evictions,
                'avg_access_time': self.stats.avg_access_time
            }
    
    async def _remove_entry(self, key: str):
        """Remove an entry and update statistics."""
        if key in self.data:
            entry = self.data[key]
            self.stats.size_bytes -= entry.size_bytes
            del self.data[key]
            self.stats.entry_count = len(self.data)
    
    async def _ensure_capacity(self, new_size: int):
        """Ensure cache has capacity for new entry."""
        # Check memory limit
        while (self.stats.size_bytes + new_size > self.max_memory_bytes and self.data):
            await self._evict_lru()
        
        # Check entry count limit
        while (len(self.data) >= self.max_size and self.data):
            await self._evict_lru()
    
    async def _evict_lru(self):
        """Evict least recently used entry with priority consideration."""
        if not self.data:
            return
        
        # Find entries with lowest priority first
        min_priority = min(entry.priority for entry in self.data.values())
        lru_candidates = [
            key for key, entry in self.data.items() 
            if entry.priority == min_priority
        ]
        
        # Among lowest priority, evict least recently used
        lru_key = lru_candidates[0]
        await self._remove_entry(lru_key)
        self.stats.evictions += 1
        logger.debug(f"Evicted LRU entry: {lru_key}")
    
    def _log_access(self, key: str, action: str):
        """Log cache access for analysis."""
        self.access_log.append({
            'key': key,
            'action': action,
            'timestamp': time.time()
        })
        
        # Keep only last 1000 entries
        if len(self.access_log) > 1000:
            self.access_log = self.access_log[-1000:]

class HierarchicalCache:
    """Multi-level hierarchical cache with L1 (memory), L2 (disk), and L3 (database)."""
    
    def __init__(self, l1_size: int = 1000, l2_size: int = 5000, db_path: str = "cache.db"):
        self.l1 = RedisCompatibleCache(max_size=l1_size, max_memory_mb=128)
        self.l2 = RedisCompatibleCache(max_size=l2_size, max_memory_mb=256)
        self.db_path = db_path
        self.stats = {
            'l1_hits': 0, 'l1_misses': 0,
            'l2_hits': 0, 'l2_misses': 0,
            'l3_hits': 0, 'l3_misses': 0,
            'promotions': 0, 'demotions': 0
        }
        self._init_database()
    
    def _init_database(self):
        """Initialize L3 database cache."""
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else '.', exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_l3 (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    timestamp REAL,
                    ttl REAL,
                    access_count INTEGER DEFAULT 0,
                    priority INTEGER DEFAULT 1
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON cache_l3(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_priority ON cache_l3(priority)")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from hierarchical cache."""
        # Try L1 first
        value = await self.l1.get(key)
        if value is not None:
            self.stats['l1_hits'] += 1
            return value
        self.stats['l1_misses'] += 1
        
        # Try L2
        value = await self.l2.get(key)
        if value is not None:
            self.stats['l2_hits'] += 1
            # Promote to L1
            await self.l1.set(key, value, priority=2)
            self.stats['promotions'] += 1
            return value
        self.stats['l2_misses'] += 1
        
        # Try L3 (database)
        value = await self._get_l3(key)
        if value is not None:
            self.stats['l3_hits'] += 1
            # Promote to L2
            await self.l2.set(key, value, priority=2)
            self.stats['promotions'] += 1
            return value
        self.stats['l3_misses'] += 1
        
        return None
    
    async def set(self, key: str, value: Any, ttl: float = 3600.0, priority: int = 1):
        """Set value in hierarchical cache."""
        # Always set in L1
        await self.l1.set(key, value, ttl=ttl, priority=priority)
        
        # Set in L2 for medium/high priority items
        if priority >= 2:
            await self.l2.set(key, value, ttl=ttl, priority=priority)
        
        # Set in L3 for high priority items
        if priority >= 3:
            await self._set_l3(key, value, ttl, priority)
    
    async def _get_l3(self, key: str) -> Optional[Any]:
        """Get value from L3 database cache."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute(
                    "SELECT value, timestamp, ttl FROM cache_l3 WHERE key = ?", 
                    (key,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        value_blob, timestamp, ttl = row
                        if time.time() - timestamp < ttl:
                            # Update access count
                            await conn.execute(
                                "UPDATE cache_l3 SET access_count = access_count + 1 WHERE key = ?",
                                (key,)
                            )
                            await conn.commit()
                            return pickle.loads(value_blob)
                        else:
                            # Expired, remove
                            await conn.execute("DELETE FROM cache_l3 WHERE key = ?", (key,))
                            await conn.commit()
            return None
        except Exception as e:
            logger.error(f"L3 cache get error: {e}")
            return None
    
    async def _set_l3(self, key: str, value: Any, ttl: float, priority: int):
        """Set value in L3 database cache."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                value_blob = pickle.dumps(value)
                await conn.execute("""
                    INSERT OR REPLACE INTO cache_l3 
                    (key, value, timestamp, ttl, access_count, priority)
                    VALUES (?, ?, ?, ?, 0, ?)
                """, (key, value_blob, time.time(), ttl, priority))
                await conn.commit()
        except Exception as e:
            logger.error(f"L3 cache set error: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        l1_info = await self.l1.info()
        l2_info = await self.l2.info()
        
        # L3 stats
        l3_count = 0
        l3_size = 0
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute("SELECT COUNT(*), SUM(LENGTH(value)) FROM cache_l3") as cursor:
                    row = await cursor.fetchone()
                    if row:
                        l3_count, l3_size = row[0], row[1] or 0
        except:
            pass
        
        return {
            'hierarchical_stats': self.stats,
            'l1': l1_info,
            'l2': l2_info,
            'l3': {
                'entries': l3_count,
                'size_bytes': l3_size
            }
        }

class CacheDecorator:
    """Decorator for automatic function result caching."""
    
    def __init__(self, cache: Union[RedisCompatibleCache, HierarchicalCache], 
                 ttl: float = 3600.0, key_prefix: str = ""):
        self.cache = cache
        self.ttl = ttl
        self.key_prefix = key_prefix
    
    def __call__(self, func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            key_data = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = f"{self.key_prefix}:{hashlib.md5(key_data.encode()).hexdigest()}"
            
            # Try cache first
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, func, *args, **kwargs)
            
            # Cache result
            await self.cache.set(cache_key, result, ttl=self.ttl)
            return result
            
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions, use asyncio.run
            async def async_inner():
                return await async_wrapper(*args, **kwargs)
            
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(async_inner())
            except RuntimeError:
                # No event loop running
                return asyncio.run(async_inner())
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

# Global cache instances for the application
app_cache = HierarchicalCache(
    l1_size=1000,
    l2_size=5000,
    db_path="data/app_cache.db"
)

# Specialized cache instances
character_cache = RedisCompatibleCache(max_size=500, max_memory_mb=64)
simulation_cache = RedisCompatibleCache(max_size=1000, max_memory_mb=128)
api_response_cache = RedisCompatibleCache(max_size=2000, max_memory_mb=256)

# Cache decorators for common use cases
@CacheDecorator(character_cache, ttl=7200.0, key_prefix="character")
async def cached_character_load(character_name: str):
    """Cached character loading function."""
    pass  # Implementation would be added by the application

@CacheDecorator(simulation_cache, ttl=3600.0, key_prefix="simulation")
async def cached_simulation_run(character_names: List[str], turns: int):
    """Cached simulation execution function."""
    pass  # Implementation would be added by the application

async def setup_cache_warming():
    """Setup intelligent cache warming strategies."""
    # Character cache warming
    def warm_characters():
        """Warm character cache with frequently accessed characters."""
        characters_dir = Path("characters")
        if characters_dir.exists():
            characters = {}
            for char_dir in characters_dir.iterdir():
                if char_dir.is_dir():
                    char_file = char_dir / f"character_{char_dir.name}.md"
                    if char_file.exists():
                        with open(char_file, 'r', encoding='utf-8') as f:
                            characters[char_dir.name] = f.read()
            return characters
        return {}
    
    # Register warming strategies
    character_cache.warmer.register_warming_strategy("characters", warm_characters)
    character_cache.warmer.add_warm_pattern("characters", ttl=7200.0)
    
    # Start warming
    await character_cache.warmer.warm_cache()

async def cleanup_expired_entries():
    """Background task to clean up expired cache entries."""
    while True:
        try:
            # Clean up expired entries from all caches
            for cache in [character_cache, simulation_cache, api_response_cache]:
                expired_keys = []
                async with cache.lock:
                    for key, entry in cache.data.items():
                        if entry.is_expired():
                            expired_keys.append(key)
                
                for key in expired_keys:
                    await cache.delete(key)
                
                if expired_keys:
                    logger.debug(f"Cleaned up {len(expired_keys)} expired entries")
            
            # Sleep for 5 minutes
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"Cache cleanup error: {e}")
            await asyncio.sleep(60)

# Cache monitoring and analytics
class CacheAnalytics:
    """Advanced cache analytics and optimization recommendations."""
    
    def __init__(self):
        self.access_patterns = defaultdict(list)
        self.performance_history = []
    
    async def analyze_access_patterns(self, cache: RedisCompatibleCache) -> Dict[str, Any]:
        """Analyze cache access patterns for optimization."""
        analysis = {
            'hot_keys': [],
            'cold_keys': [],
            'temporal_patterns': {},
            'recommendations': []
        }
        
        # Analyze access frequency
        key_access_count = defaultdict(int)
        for access in cache.access_log:
            if access['action'] in ['hit', 'miss']:
                key_access_count[access['key']] += 1
        
        # Identify hot and cold keys
        if key_access_count:
            access_counts = list(key_access_count.values())
            avg_access = sum(access_counts) / len(access_counts)
            
            for key, count in key_access_count.items():
                if count > avg_access * 2:
                    analysis['hot_keys'].append({'key': key, 'access_count': count})
                elif count < avg_access * 0.5:
                    analysis['cold_keys'].append({'key': key, 'access_count': count})
        
        # Generate recommendations
        cache_info = await cache.info()
        hit_rate = cache_info['hit_rate']
        
        if hit_rate < 0.7:
            analysis['recommendations'].append("Consider increasing cache size or TTL")
        if len(analysis['hot_keys']) > cache.max_size * 0.1:
            analysis['recommendations'].append("Consider implementing cache warming for hot keys")
        if cache_info['evictions'] > cache_info['hits'] * 0.1:
            analysis['recommendations'].append("High eviction rate - consider increasing memory limit")
        
        return analysis

analytics = CacheAnalytics()

if __name__ == "__main__":
    # Example usage and testing
    async def test_caching_system():
        """Test the caching system functionality."""
        # Test Redis-compatible cache
        cache = RedisCompatibleCache()
        
        # Basic operations
        await cache.set("test_key", "test_value", ttl=60.0)
        value = await cache.get("test_key")
        print(f"Retrieved value: {value}")
        
        # Test hierarchical cache
        h_cache = HierarchicalCache()
        await h_cache.set("hierarchical_test", {"data": "complex_object"}, priority=3)
        result = await h_cache.get("hierarchical_test")
        print(f"Hierarchical result: {result}")
        
        # Test cache decorator
        @CacheDecorator(cache, ttl=30.0)
        async def expensive_operation(x: int) -> int:
            await asyncio.sleep(0.1)  # Simulate work
            return x * x
        
        # First call - miss
        start = time.time()
        result1 = await expensive_operation(5)
        time1 = time.time() - start
        
        # Second call - hit
        start = time.time()
        result2 = await expensive_operation(5)
        time2 = time.time() - start
        
        print(f"First call: {result1} in {time1:.3f}s")
        print(f"Second call: {result2} in {time2:.3f}s")
        print(f"Speedup: {time1/time2:.1f}x")
        
        # Print statistics
        stats = await cache.info()
        print(f"Cache stats: {stats}")
    
    # Run the test
    asyncio.run(test_caching_system())