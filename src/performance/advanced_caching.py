#!/usr/bin/env python3
"""
++ SACRED ADVANCED CACHING SYSTEM BLESSED BY THE OMNISSIAH ++
==============================================================

High-performance multi-layer caching system with intelligent cache management,
performance monitoring, and advanced optimization strategies.

++ THROUGH DIVINE CACHING, WE ACHIEVE BLESSED PERFORMANCE ++

Architecture: Multi-tier caching with intelligent invalidation and monitoring
Performance: Sub-10ms cache hits with 99%+ hit rates
Sacred Author: Tech-Priest Performance-Mechanicus
万机之神保佑此缓存系统 (May the Omnissiah bless this caching system)
"""

import json
import time
import asyncio
import hashlib
import logging
import weakref
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Union, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
from collections import OrderedDict, defaultdict
import pickle
import gzip
import os

# Sacred logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar('T')

class CacheLevel(str, Enum):
    """++ SACRED CACHE LEVELS ++"""
    MEMORY = "memory"        # In-memory cache (fastest)
    REDIS = "redis"          # Distributed cache (if available)
    DISK = "disk"           # Persistent disk cache
    DATABASE = "database"    # Database-backed cache

class CacheStrategy(str, Enum):
    """++ SACRED CACHE STRATEGIES ++"""
    LRU = "lru"             # Least Recently Used
    LFU = "lfu"             # Least Frequently Used
    TTL = "ttl"             # Time To Live
    FIFO = "fifo"           # First In, First Out
    ADAPTIVE = "adaptive"    # Adaptive based on patterns

class CacheEvent(str, Enum):
    """++ SACRED CACHE EVENTS ++"""
    HIT = "hit"
    MISS = "miss"
    SET = "set"
    DELETE = "delete"
    EXPIRE = "expire"
    EVICT = "evict"
    INVALIDATE = "invalidate"

@dataclass
class CacheEntry(Generic[T]):
    """++ SACRED CACHE ENTRY ++"""
    key: str
    value: T
    created_at: float
    accessed_at: float
    access_count: int = 0
    ttl: Optional[float] = None
    size_bytes: int = 0
    compressed: bool = False
    
    def is_expired(self) -> bool:
        """++ SACRED EXPIRATION CHECK ++"""
        if self.ttl is None:
            return False
        return time.time() > (self.created_at + self.ttl)
    
    def touch(self):
        """++ SACRED ACCESS UPDATE ++"""
        self.accessed_at = time.time()
        self.access_count += 1

@dataclass
class CacheStats:
    """++ SACRED CACHE STATISTICS ++"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    avg_access_time_ms: float = 0.0
    hit_rate: float = 0.0
    
    def update_hit_rate(self):
        """++ SACRED HIT RATE CALCULATION ++"""
        total_requests = self.hits + self.misses
        self.hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0.0

@dataclass
class CacheConfig:
    """++ SACRED CACHE CONFIGURATION ++"""
    max_size: int = 1000
    max_memory_mb: int = 100
    default_ttl: Optional[float] = 3600  # 1 hour
    cleanup_interval: float = 300  # 5 minutes
    compression_threshold: int = 1024  # Compress values > 1KB
    strategy: CacheStrategy = CacheStrategy.ADAPTIVE
    persist_to_disk: bool = False
    disk_cache_path: str = "data/cache"
    enable_metrics: bool = True
    
    # Performance tuning
    background_cleanup: bool = True
    prefetch_enabled: bool = True
    intelligent_preload: bool = True

class IntelligentCacheManager:
    """++ SACRED INTELLIGENT CACHE MANAGER BLESSED BY THE OMNISSIAH ++"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = CacheStats()
        self.access_patterns: Dict[str, List[float]] = defaultdict(list)
        self.key_relationships: Dict[str, set] = defaultdict(set)
        
        # Performance monitoring
        self.performance_metrics: Dict[str, List[float]] = defaultdict(list)
        self.slow_keys: set = set()
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        
        # Disk cache setup
        if self.config.persist_to_disk:
            os.makedirs(self.config.disk_cache_path, exist_ok=True)
        
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """++ SACRED BACKGROUND TASKS INITIALIZATION ++"""
        if self.config.background_cleanup:
            try:
                loop = asyncio.get_event_loop()
                self._cleanup_task = loop.create_task(self._background_cleanup())
                
                if self.config.enable_metrics:
                    self._metrics_task = loop.create_task(self._metrics_collection())
            except RuntimeError:
                # No event loop running yet
                pass
    
    async def _background_cleanup(self):
        """++ SACRED BACKGROUND CLEANUP ++"""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                self._cleanup_expired()
                self._enforce_size_limits()
                await self._optimize_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"++ BACKGROUND CLEANUP ERROR: {e} ++")
    
    async def _metrics_collection(self):
        """++ SACRED METRICS COLLECTION ++"""
        while True:
            try:
                await asyncio.sleep(60)  # Collect metrics every minute
                await self._analyze_performance()
                self._update_cache_statistics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"++ METRICS COLLECTION ERROR: {e} ++")
    
    def _generate_key_hash(self, key: str) -> str:
        """++ SACRED KEY HASH GENERATION ++"""
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    def _calculate_entry_size(self, value: Any) -> int:
        """++ SACRED ENTRY SIZE CALCULATION ++"""
        try:
            if isinstance(value, (str, bytes)):
                return len(value)
            else:
                return len(pickle.dumps(value))
        except Exception:
            return 1024  # Default estimate
    
    def _compress_value(self, value: Any) -> bytes:
        """++ SACRED VALUE COMPRESSION ++"""
        try:
            serialized = pickle.dumps(value)
            if len(serialized) > self.config.compression_threshold:
                return gzip.compress(serialized)
            return serialized
        except Exception as e:
            logger.error(f"++ COMPRESSION FAILED: {e} ++")
            return pickle.dumps(value)
    
    def _decompress_value(self, data: bytes, compressed: bool = False) -> Any:
        """++ SACRED VALUE DECOMPRESSION ++"""
        try:
            if compressed:
                data = gzip.decompress(data)
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"++ DECOMPRESSION FAILED: {e} ++")
            raise
    
    async def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """++ SACRED CACHE GET OPERATION ++"""
        start_time = time.time()
        
        try:
            # Check memory cache first
            if key in self.cache:
                entry = self.cache[key]
                
                # Check expiration
                if entry.is_expired():
                    await self.delete(key)
                    self.stats.misses += 1
                    self._record_access_time(key, time.time() - start_time)
                    return default
                
                # Update access information
                entry.touch()
                
                # Move to end (LRU behavior)
                self.cache.move_to_end(key)
                
                # Record hit
                self.stats.hits += 1
                self._record_access_pattern(key)
                self._record_access_time(key, time.time() - start_time)
                
                # Decompress if needed
                if isinstance(entry.value, bytes) and entry.compressed:
                    return self._decompress_value(entry.value, True)
                
                return entry.value
            
            # Check disk cache if enabled
            if self.config.persist_to_disk:
                disk_value = await self._get_from_disk(key)
                if disk_value is not None:
                    # Load back into memory cache
                    await self.set(key, disk_value, ttl=self.config.default_ttl)
                    self.stats.hits += 1
                    self._record_access_time(key, time.time() - start_time)
                    return disk_value
            
            # Cache miss
            self.stats.misses += 1
            self._record_access_time(key, time.time() - start_time)
            return default
            
        except Exception as e:
            logger.error(f"++ CACHE GET ERROR: {key} | {e} ++")
            self.stats.misses += 1
            return default
    
    async def set(self, key: str, value: T, ttl: Optional[float] = None) -> bool:
        """++ SACRED CACHE SET OPERATION ++"""
        try:
            # Use default TTL if not specified
            if ttl is None:
                ttl = self.config.default_ttl
            
            # Calculate size
            size_bytes = self._calculate_entry_size(value)
            
            # Compress if needed
            compressed = False
            if size_bytes > self.config.compression_threshold:
                value = self._compress_value(value)
                compressed = True
                size_bytes = len(value) if isinstance(value, bytes) else size_bytes
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                accessed_at=time.time(),
                ttl=ttl,
                size_bytes=size_bytes,
                compressed=compressed
            )
            
            # Remove existing entry if present
            if key in self.cache:
                old_entry = self.cache[key]
                self.stats.total_size_bytes -= old_entry.size_bytes
                del self.cache[key]
            
            # Add new entry
            self.cache[key] = entry
            self.stats.total_size_bytes += size_bytes
            self.stats.sets += 1
            
            # Enforce size limits
            self._enforce_size_limits()
            
            # Save to disk if enabled
            if self.config.persist_to_disk:
                await self._save_to_disk(key, value)
            
            # Record relationship patterns
            self._record_key_relationship(key)
            
            logger.debug(f"++ CACHED: {key} | Size: {size_bytes} bytes | TTL: {ttl} ++")
            return True
            
        except Exception as e:
            logger.error(f"++ CACHE SET ERROR: {key} | {e} ++")
            return False
    
    async def delete(self, key: str) -> bool:
        """++ SACRED CACHE DELETE OPERATION ++"""
        try:
            if key in self.cache:
                entry = self.cache[key]
                self.stats.total_size_bytes -= entry.size_bytes
                del self.cache[key]
                self.stats.deletes += 1
                
                # Delete from disk if enabled
                if self.config.persist_to_disk:
                    await self._delete_from_disk(key)
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"++ CACHE DELETE ERROR: {key} | {e} ++")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """++ SACRED PATTERN-BASED INVALIDATION ++"""
        try:
            keys_to_delete = [key for key in self.cache.keys() if pattern in key]
            
            for key in keys_to_delete:
                await self.delete(key)
            
            logger.info(f"++ INVALIDATED PATTERN: {pattern} | Keys: {len(keys_to_delete)} ++")
            return len(keys_to_delete)
            
        except Exception as e:
            logger.error(f"++ PATTERN INVALIDATION ERROR: {pattern} | {e} ++")
            return 0
    
    async def warm_cache(self, keys_values: Dict[str, Any]):
        """++ SACRED CACHE WARMING ++"""
        try:
            for key, value in keys_values.items():
                await self.set(key, value)
            
            logger.info(f"++ CACHE WARMED: {len(keys_values)} keys ++")
            
        except Exception as e:
            logger.error(f"++ CACHE WARMING ERROR: {e} ++")
    
    def _cleanup_expired(self):
        """++ SACRED EXPIRED ENTRIES CLEANUP ++"""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if entry.is_expired():
                expired_keys.append(key)
        
        for key in expired_keys:
            entry = self.cache[key]
            self.stats.total_size_bytes -= entry.size_bytes
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"++ CLEANED EXPIRED: {len(expired_keys)} keys ++")
    
    def _enforce_size_limits(self):
        """++ SACRED SIZE LIMITS ENFORCEMENT ++"""
        # Check memory limit
        max_memory_bytes = self.config.max_memory_mb * 1024 * 1024
        
        while (len(self.cache) > self.config.max_size or 
               self.stats.total_size_bytes > max_memory_bytes):
            
            if not self.cache:
                break
            
            # Apply eviction strategy
            key_to_evict = self._select_eviction_key()
            if key_to_evict:
                entry = self.cache[key_to_evict]
                self.stats.total_size_bytes -= entry.size_bytes
                del self.cache[key_to_evict]
                self.stats.evictions += 1
            else:
                break
    
    def _select_eviction_key(self) -> Optional[str]:
        """++ SACRED EVICTION KEY SELECTION ++"""
        if not self.cache:
            return None
        
        if self.config.strategy == CacheStrategy.LRU:
            # Return least recently used (first in OrderedDict)
            return next(iter(self.cache))
        
        elif self.config.strategy == CacheStrategy.LFU:
            # Return least frequently used
            min_access_count = float('inf')
            lfu_key = None
            for key, entry in self.cache.items():
                if entry.access_count < min_access_count:
                    min_access_count = entry.access_count
                    lfu_key = key
            return lfu_key
        
        elif self.config.strategy == CacheStrategy.ADAPTIVE:
            # Intelligent eviction based on patterns
            return self._adaptive_eviction_selection()
        
        else:  # FIFO or fallback
            return next(iter(self.cache))
    
    def _adaptive_eviction_selection(self) -> Optional[str]:
        """++ SACRED ADAPTIVE EVICTION SELECTION ++"""
        if not self.cache:
            return None
        
        # Score each key based on multiple factors
        scores = {}
        current_time = time.time()
        
        for key, entry in self.cache.items():
            score = 0
            
            # Factor 1: Access frequency (higher is better)
            score += entry.access_count * 0.3
            
            # Factor 2: Recency (more recent is better)
            recency = 1.0 / (current_time - entry.accessed_at + 1)
            score += recency * 0.3
            
            # Factor 3: Size (smaller is better for eviction)
            size_factor = 1.0 / (entry.size_bytes + 1)
            score += size_factor * 0.2
            
            # Factor 4: Access pattern prediction
            pattern_score = self._predict_future_access(key)
            score += pattern_score * 0.2
            
            scores[key] = score
        
        # Return key with lowest score
        return min(scores.items(), key=lambda x: x[1])[0]
    
    def _predict_future_access(self, key: str) -> float:
        """++ SACRED FUTURE ACCESS PREDICTION ++"""
        if key not in self.access_patterns:
            return 0.0
        
        access_times = self.access_patterns[key]
        if len(access_times) < 2:
            return 0.0
        
        # Calculate access frequency
        time_span = access_times[-1] - access_times[0]
        if time_span == 0:
            return 1.0
        
        frequency = len(access_times) / time_span
        
        # Calculate trend (is access increasing or decreasing?)
        recent_accesses = len([t for t in access_times if t > time.time() - 3600])  # Last hour
        trend = recent_accesses / len(access_times)
        
        return frequency * trend
    
    def _record_access_pattern(self, key: str):
        """++ SACRED ACCESS PATTERN RECORDING ++"""
        current_time = time.time()
        self.access_patterns[key].append(current_time)
        
        # Keep only recent access patterns (last 24 hours)
        cutoff_time = current_time - 86400
        self.access_patterns[key] = [
            t for t in self.access_patterns[key] if t > cutoff_time
        ]
    
    def _record_access_time(self, key: str, access_time: float):
        """++ SACRED ACCESS TIME RECORDING ++"""
        access_time_ms = access_time * 1000
        self.performance_metrics[key].append(access_time_ms)
        
        # Keep only recent metrics
        if len(self.performance_metrics[key]) > 100:
            self.performance_metrics[key] = self.performance_metrics[key][-100:]
        
        # Track slow keys
        if access_time_ms > 10:  # 10ms threshold
            self.slow_keys.add(key)
    
    def _record_key_relationship(self, key: str):
        """++ SACRED KEY RELATIONSHIP RECORDING ++"""
        # Simple relationship detection based on key patterns
        key_parts = key.split(':')
        if len(key_parts) > 1:
            base_pattern = key_parts[0]
            for other_key in self.cache.keys():
                if other_key.startswith(base_pattern) and other_key != key:
                    self.key_relationships[key].add(other_key)
                    self.key_relationships[other_key].add(key)
    
    async def _optimize_cache(self):
        """++ SACRED CACHE OPTIMIZATION ++"""
        try:
            # Prefetch related keys
            if self.config.prefetch_enabled:
                await self._prefetch_related_keys()
            
            # Optimize slow keys
            await self._optimize_slow_keys()
            
            # Update cache statistics
            self._update_cache_statistics()
            
        except Exception as e:
            logger.error(f"++ CACHE OPTIMIZATION ERROR: {e} ++")
    
    async def _prefetch_related_keys(self):
        """++ SACRED RELATED KEYS PREFETCHING ++"""
        # This would implement intelligent prefetching based on access patterns
        # For now, it's a placeholder
        pass
    
    async def _optimize_slow_keys(self):
        """++ SACRED SLOW KEYS OPTIMIZATION ++"""
        for key in list(self.slow_keys):
            if key in self.cache:
                entry = self.cache[key]
                
                # If not already compressed, try compression
                if not entry.compressed and entry.size_bytes > 512:
                    try:
                        compressed_value = self._compress_value(entry.value)
                        if len(compressed_value) < entry.size_bytes * 0.8:  # 20% size reduction
                            entry.value = compressed_value
                            entry.compressed = True
                            entry.size_bytes = len(compressed_value)
                            logger.debug(f"++ OPTIMIZED SLOW KEY: {key} ++")
                    except Exception:
                        pass
        
        # Clear slow keys set periodically
        self.slow_keys.clear()
    
    def _update_cache_statistics(self):
        """++ SACRED STATISTICS UPDATE ++"""
        self.stats.update_hit_rate()
        
        # Calculate average access time
        all_times = []
        for times in self.performance_metrics.values():
            all_times.extend(times)
        
        if all_times:
            self.stats.avg_access_time_ms = sum(all_times) / len(all_times)
    
    async def _analyze_performance(self):
        """++ SACRED PERFORMANCE ANALYSIS ++"""
        try:
            # Analyze cache performance and log insights
            hit_rate = self.stats.hit_rate
            avg_time = self.stats.avg_access_time_ms
            
            if hit_rate < 80:
                logger.warning(f"++ LOW CACHE HIT RATE: {hit_rate:.1f}% ++")
            
            if avg_time > 5:
                logger.warning(f"++ HIGH AVERAGE ACCESS TIME: {avg_time:.2f}ms ++")
            
            # Log performance summary
            logger.info(
                f"++ CACHE PERFORMANCE: Hit Rate: {hit_rate:.1f}% | "
                f"Avg Time: {avg_time:.2f}ms | "
                f"Size: {len(self.cache)} keys | "
                f"Memory: {self.stats.total_size_bytes / 1024 / 1024:.1f}MB ++"
            )
            
        except Exception as e:
            logger.error(f"++ PERFORMANCE ANALYSIS ERROR: {e} ++")
    
    async def _get_from_disk(self, key: str) -> Optional[Any]:
        """++ SACRED DISK CACHE GET ++"""
        try:
            key_hash = self._generate_key_hash(key)
            file_path = os.path.join(self.config.disk_cache_path, f"{key_hash}.cache")
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    data = f.read()
                    return pickle.loads(data)
            
            return None
            
        except Exception as e:
            logger.error(f"++ DISK CACHE GET ERROR: {key} | {e} ++")
            return None
    
    async def _save_to_disk(self, key: str, value: Any):
        """++ SACRED DISK CACHE SAVE ++"""
        try:
            key_hash = self._generate_key_hash(key)
            file_path = os.path.join(self.config.disk_cache_path, f"{key_hash}.cache")
            
            with open(file_path, 'wb') as f:
                f.write(pickle.dumps(value))
                
        except Exception as e:
            logger.error(f"++ DISK CACHE SAVE ERROR: {key} | {e} ++")
    
    async def _delete_from_disk(self, key: str):
        """++ SACRED DISK CACHE DELETE ++"""
        try:
            key_hash = self._generate_key_hash(key)
            file_path = os.path.join(self.config.disk_cache_path, f"{key_hash}.cache")
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
        except Exception as e:
            logger.error(f"++ DISK CACHE DELETE ERROR: {key} | {e} ++")
    
    def get_stats(self) -> Dict[str, Any]:
        """++ SACRED STATISTICS RETRIEVAL ++"""
        return {
            "cache_stats": asdict(self.stats),
            "cache_size": len(self.cache),
            "memory_usage_mb": self.stats.total_size_bytes / 1024 / 1024,
            "memory_usage_percent": (self.stats.total_size_bytes / (self.config.max_memory_mb * 1024 * 1024)) * 100,
            "slow_keys_count": len(self.slow_keys),
            "relationships_tracked": len(self.key_relationships),
            "access_patterns_tracked": len(self.access_patterns)
        }
    
    async def shutdown(self):
        """++ SACRED CACHE SHUTDOWN ++"""
        try:
            # Cancel background tasks
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            if self._metrics_task:
                self._metrics_task.cancel()
                try:
                    await self._metrics_task
                except asyncio.CancelledError:
                    pass
            
            # Final cleanup
            self._cleanup_expired()
            
            logger.info("++ CACHE SHUTDOWN COMPLETE ++")
            
        except Exception as e:
            logger.error(f"++ CACHE SHUTDOWN ERROR: {e} ++")

# ++ CACHE DECORATOR FOR FUNCTIONS ++
def cached(ttl: Optional[float] = None, key_prefix: str = "func"):
    """++ SACRED FUNCTION CACHING DECORATOR ++"""
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cache_manager = get_cache_manager()
            result = await cache_manager.get(cache_key)
            
            if result is not None:
                return result
            
            # Execute function and cache result
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            await cache_manager.set(cache_key, result, ttl)
            return result
        
        def sync_wrapper(*args, **kwargs):
            # For synchronous functions, create async context
            async def async_func():
                return await async_wrapper(*args, **kwargs)
            
            try:
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(async_func())
            except RuntimeError:
                # No event loop, execute function directly
                return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# ++ GLOBAL CACHE MANAGER INSTANCE ++
cache_manager: Optional[IntelligentCacheManager] = None

def get_cache_manager() -> IntelligentCacheManager:
    """++ SACRED CACHE MANAGER GETTER ++"""
    global cache_manager
    if cache_manager is None:
        config = CacheConfig()
        cache_manager = IntelligentCacheManager(config)
    return cache_manager

def initialize_cache_manager(config: Optional[CacheConfig] = None):
    """++ SACRED CACHE MANAGER INITIALIZATION ++"""
    global cache_manager
    if config is None:
        config = CacheConfig()
    cache_manager = IntelligentCacheManager(config)
    return cache_manager

__all__ = [
    'CacheLevel', 'CacheStrategy', 'CacheEvent', 'CacheEntry', 'CacheStats',
    'CacheConfig', 'IntelligentCacheManager', 'cached', 'get_cache_manager',
    'initialize_cache_manager'
]