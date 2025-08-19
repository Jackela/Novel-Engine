#!/usr/bin/env python3
"""
Advanced Memory Management and Optimization System for Novel Engine - Iteration 2.

This module implements sophisticated memory management including object pooling,
memory leak detection, garbage collection optimization, and efficient object lifecycle management.
"""

import gc
import sys
import weakref
import threading
import asyncio
import time
import psutil
import os
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic, Callable, Set
from collections import defaultdict, deque
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import logging
import pickle
import mmap
from pathlib import Path
import tracemalloc
import linecache

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class MemoryStats:
    """Memory usage statistics and metrics."""
    total_memory_mb: float = 0.0
    used_memory_mb: float = 0.0
    available_memory_mb: float = 0.0
    memory_percent: float = 0.0
    gc_collections: Dict[int, int] = field(default_factory=dict)
    object_counts: Dict[str, int] = field(default_factory=dict)
    pool_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    leaked_objects: List[Dict[str, Any]] = field(default_factory=list)

class ObjectPool(Generic[T]):
    """High-performance object pool for frequent allocations/deallocations."""
    
    def __init__(self, factory: Callable[[], T], max_size: int = 100, 
                 reset_func: Optional[Callable[[T], None]] = None):
        self.factory = factory
        self.reset_func = reset_func
        self.max_size = max_size
        self.pool = deque(maxlen=max_size)
        self.lock = threading.RLock()
        self.stats = {
            'created': 0,
            'reused': 0,
            'peak_size': 0,
            'current_size': 0,
            'total_acquisitions': 0,
            'total_releases': 0
        }
        
        # Pre-populate the pool
        self._populate_pool(min(max_size // 4, 10))
    
    def _populate_pool(self, count: int):
        """Pre-populate the pool with objects."""
        for _ in range(count):
            try:
                obj = self.factory()
                self.pool.append(obj)
                self.stats['created'] += 1
            except Exception as e:
                logger.error(f"Error pre-populating pool: {e}")
                break
    
    def acquire(self) -> T:
        """Acquire an object from the pool."""
        with self.lock:
            self.stats['total_acquisitions'] += 1
            
            if self.pool:
                obj = self.pool.popleft()
                self.stats['reused'] += 1
                self.stats['current_size'] = len(self.pool)
                return obj
            else:
                obj = self.factory()
                self.stats['created'] += 1
                return obj
    
    def release(self, obj: T) -> bool:
        """Release an object back to the pool."""
        with self.lock:
            self.stats['total_releases'] += 1
            
            if len(self.pool) >= self.max_size:
                return False  # Pool is full
            
            try:
                # Reset object state if reset function provided
                if self.reset_func:
                    self.reset_func(obj)
                
                self.pool.append(obj)
                self.stats['current_size'] = len(self.pool)
                self.stats['peak_size'] = max(self.stats['peak_size'], len(self.pool))
                return True
                
            except Exception as e:
                logger.error(f"Error resetting object for pool: {e}")
                return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self.lock:
            reuse_rate = (self.stats['reused'] / 
                         max(self.stats['total_acquisitions'], 1))
            
            return {
                **self.stats,
                'reuse_rate': reuse_rate,
                'efficiency': reuse_rate * 100,
                'pool_utilization': len(self.pool) / self.max_size * 100
            }
    
    def clear(self):
        """Clear the pool."""
        with self.lock:
            self.pool.clear()
            self.stats['current_size'] = 0

class AsyncObjectPool(ObjectPool[T]):
    """Async version of ObjectPool for coroutine-safe operations."""
    
    def __init__(self, factory: Callable[[], T], max_size: int = 100,
                 reset_func: Optional[Callable[[T], None]] = None):
        super().__init__(factory, max_size, reset_func)
        self.async_lock = asyncio.Lock()
    
    async def acquire_async(self) -> T:
        """Async acquire an object from the pool."""
        async with self.async_lock:
            return self.acquire()
    
    async def release_async(self, obj: T) -> bool:
        """Async release an object back to the pool."""
        async with self.async_lock:
            return self.release(obj)

class MemoryMappedBuffer:
    """Memory-mapped buffer for efficient large data handling."""
    
    def __init__(self, size: int, file_path: Optional[str] = None):
        self.size = size
        self.file_path = file_path or f"/tmp/mmap_buffer_{os.getpid()}_{id(self)}"
        self.file_handle = None
        self.mmap_obj = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the memory-mapped buffer."""
        try:
            # Create the file
            with open(self.file_path, 'wb') as f:
                f.write(b'\x00' * self.size)
            
            # Open for memory mapping
            self.file_handle = open(self.file_path, 'r+b')
            self.mmap_obj = mmap.mmap(self.file_handle.fileno(), self.size)
            
        except Exception as e:
            logger.error(f"Error initializing memory-mapped buffer: {e}")
            self.cleanup()
            raise
    
    def write(self, data: bytes, offset: int = 0) -> int:
        """Write data to the buffer."""
        if not self.mmap_obj:
            raise RuntimeError("Buffer not initialized")
        
        if offset + len(data) > self.size:
            raise ValueError("Data exceeds buffer size")
        
        self.mmap_obj.seek(offset)
        return self.mmap_obj.write(data)
    
    def read(self, length: int, offset: int = 0) -> bytes:
        """Read data from the buffer."""
        if not self.mmap_obj:
            raise RuntimeError("Buffer not initialized")
        
        if offset + length > self.size:
            raise ValueError("Read exceeds buffer size")
        
        self.mmap_obj.seek(offset)
        return self.mmap_obj.read(length)
    
    def flush(self):
        """Flush changes to disk."""
        if self.mmap_obj:
            self.mmap_obj.flush()
    
    def cleanup(self):
        """Clean up resources."""
        if self.mmap_obj:
            self.mmap_obj.close()
            self.mmap_obj = None
        
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None
        
        try:
            if os.path.exists(self.file_path):
                os.unlink(self.file_path)
        except:
            pass
    
    def __del__(self):
        self.cleanup()

class MemoryLeakDetector:
    """Advanced memory leak detection and monitoring."""
    
    def __init__(self, threshold_mb: float = 50.0, check_interval: int = 60):
        self.threshold_mb = threshold_mb
        self.check_interval = check_interval
        self.baseline_memory = 0.0
        self.memory_history = deque(maxlen=100)
        self.suspicious_objects = defaultdict(int)
        self.tracemalloc_active = False
        self.top_stats = []
        
    def start_monitoring(self):
        """Start memory leak monitoring."""
        # Start tracemalloc if available
        if not self.tracemalloc_active:
            tracemalloc.start()
            self.tracemalloc_active = True
        
        # Get baseline memory
        self.baseline_memory = self._get_memory_usage()
        logger.info(f"Memory leak detection started. Baseline: {self.baseline_memory:.2f}MB")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    def check_for_leaks(self) -> Dict[str, Any]:
        """Check for potential memory leaks."""
        current_memory = self._get_memory_usage()
        self.memory_history.append({
            'timestamp': time.time(),
            'memory_mb': current_memory
        })
        
        # Calculate memory growth
        memory_growth = current_memory - self.baseline_memory
        
        leak_report = {
            'current_memory_mb': current_memory,
            'baseline_memory_mb': self.baseline_memory,
            'memory_growth_mb': memory_growth,
            'leak_detected': memory_growth > self.threshold_mb,
            'object_counts': {},
            'top_allocations': []
        }
        
        # Analyze object counts
        for obj_type in [dict, list, str, int, float, tuple]:
            count = len(gc.get_objects())
            # This is a simplified count - in practice you'd track specific types
            leak_report['object_counts'][obj_type.__name__] = count
        
        # Get tracemalloc statistics if available
        if self.tracemalloc_active:
            try:
                snapshot = tracemalloc.take_snapshot()
                self.top_stats = snapshot.statistics('lineno')[:10]
                
                leak_report['top_allocations'] = [
                    {
                        'traceback': str(stat.traceback),
                        'size_mb': stat.size / 1024 / 1024,
                        'count': stat.count
                    }
                    for stat in self.top_stats[:5]
                ]
            except Exception as e:
                logger.error(f"Error getting tracemalloc stats: {e}")
        
        if leak_report['leak_detected']:
            logger.warning(f"Memory leak detected! Growth: {memory_growth:.2f}MB")
        
        return leak_report
    
    def analyze_memory_trend(self) -> Dict[str, Any]:
        """Analyze memory usage trend."""
        if len(self.memory_history) < 2:
            return {'trend': 'insufficient_data'}
        
        recent_points = list(self.memory_history)[-10:]
        memory_values = [point['memory_mb'] for point in recent_points]
        
        # Simple linear regression for trend
        n = len(memory_values)
        x_sum = sum(range(n))
        y_sum = sum(memory_values)
        xy_sum = sum(i * memory_values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        if n * x2_sum - x_sum * x_sum != 0:
            slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
        else:
            slope = 0
        
        trend_analysis = {
            'slope_mb_per_check': slope,
            'trend': 'increasing' if slope > 0.1 else 'decreasing' if slope < -0.1 else 'stable',
            'current_memory': memory_values[-1],
            'memory_range': {
                'min': min(memory_values),
                'max': max(memory_values),
                'avg': sum(memory_values) / len(memory_values)
            }
        }
        
        return trend_analysis

class GCOptimizer:
    """Garbage collection optimization and tuning."""
    
    def __init__(self):
        self.gc_stats = {
            'collections': defaultdict(int),
            'collection_times': defaultdict(list),
            'objects_collected': defaultdict(int)
        }
        self.tuning_applied = False
    
    def optimize_gc_settings(self):
        """Optimize garbage collection settings for performance."""
        if self.tuning_applied:
            return
        
        # Get current thresholds
        thresholds = gc.get_threshold()
        logger.info(f"Current GC thresholds: {thresholds}")
        
        # Apply optimized thresholds for server workloads
        # Increase gen0 threshold to reduce frequent collections
        # Adjust gen1/gen2 for better long-term memory management
        new_thresholds = (
            thresholds[0] * 2,    # Gen 0: double to reduce frequency
            thresholds[1] * 1.5,  # Gen 1: increase moderately
            thresholds[2] * 1.2   # Gen 2: slight increase
        )
        
        gc.set_threshold(*[int(t) for t in new_thresholds])
        logger.info(f"Applied optimized GC thresholds: {new_thresholds}")
        
        # Enable GC debugging in development
        if __debug__:
            gc.set_debug(gc.DEBUG_STATS)
        
        self.tuning_applied = True
    
    def force_collection(self, generation: Optional[int] = None) -> Dict[str, Any]:
        """Force garbage collection and return statistics."""
        start_time = time.time()
        
        if generation is not None:
            collected = gc.collect(generation)
        else:
            collected = gc.collect()
        
        collection_time = time.time() - start_time
        
        # Update statistics
        gen = generation if generation is not None else 'full'
        self.gc_stats['collections'][gen] += 1
        self.gc_stats['collection_times'][gen].append(collection_time)
        self.gc_stats['objects_collected'][gen] += collected
        
        return {
            'generation': gen,
            'objects_collected': collected,
            'collection_time': collection_time,
            'total_collections': self.gc_stats['collections'][gen]
        }
    
    def get_gc_statistics(self) -> Dict[str, Any]:
        """Get comprehensive garbage collection statistics."""
        stats = {
            'counts': dict(gc.get_count()),
            'thresholds': gc.get_threshold(),
            'collection_stats': dict(self.gc_stats['collections']),
            'avg_collection_times': {}
        }
        
        # Calculate average collection times
        for gen, times in self.gc_stats['collection_times'].items():
            if times:
                stats['avg_collection_times'][gen] = sum(times) / len(times)
        
        return stats

class MemoryManager:
    """Central memory management system coordinating all optimization features."""
    
    def __init__(self):
        self.pools = {}
        self.leak_detector = MemoryLeakDetector()
        self.gc_optimizer = GCOptimizer()
        self.memory_buffers = {}
        self.monitoring_active = False
        self.monitoring_task = None
        
    def create_object_pool(self, name: str, factory: Callable[[], T], 
                          max_size: int = 100, reset_func: Optional[Callable[[T], None]] = None,
                          async_pool: bool = False) -> ObjectPool[T]:
        """Create and register an object pool."""
        if async_pool:
            pool = AsyncObjectPool(factory, max_size, reset_func)
        else:
            pool = ObjectPool(factory, max_size, reset_func)
        
        self.pools[name] = pool
        logger.info(f"Created {'async ' if async_pool else ''}object pool '{name}' with max_size={max_size}")
        return pool
    
    def get_pool(self, name: str) -> Optional[ObjectPool]:
        """Get a registered object pool by name."""
        return self.pools.get(name)
    
    def create_memory_buffer(self, name: str, size: int, 
                           file_path: Optional[str] = None) -> MemoryMappedBuffer:
        """Create and register a memory-mapped buffer."""
        buffer = MemoryMappedBuffer(size, file_path)
        self.memory_buffers[name] = buffer
        logger.info(f"Created memory buffer '{name}' with size={size} bytes")
        return buffer
    
    def start_monitoring(self):
        """Start comprehensive memory monitoring."""
        if self.monitoring_active:
            return
        
        self.leak_detector.start_monitoring()
        self.gc_optimizer.optimize_gc_settings()
        self.monitoring_active = True
        
        # Start background monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Memory monitoring started")
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while self.monitoring_active:
            try:
                # Check for memory leaks
                leak_report = self.leak_detector.check_for_leaks()
                
                if leak_report['leak_detected']:
                    # Force garbage collection if leak detected
                    gc_stats = self.gc_optimizer.force_collection()
                    logger.warning(f"Forced GC due to leak: {gc_stats}")
                
                # Log memory statistics periodically
                if int(time.time()) % 300 == 0:  # Every 5 minutes
                    stats = await self.get_comprehensive_stats()
                    logger.info(f"Memory stats: {stats['memory_usage']['used_memory_mb']:.1f}MB used")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                await asyncio.sleep(60)
    
    def stop_monitoring(self):
        """Stop memory monitoring."""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
    
    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        # System memory info
        memory = psutil.virtual_memory()
        process = psutil.Process()
        process_memory = process.memory_info()
        
        stats = {
            'memory_usage': {
                'total_memory_mb': memory.total / 1024 / 1024,
                'available_memory_mb': memory.available / 1024 / 1024,
                'used_memory_mb': process_memory.rss / 1024 / 1024,
                'memory_percent': memory.percent
            },
            'garbage_collection': self.gc_optimizer.get_gc_statistics(),
            'object_pools': {
                name: pool.get_stats() for name, pool in self.pools.items()
            },
            'memory_buffers': {
                name: {'size': buf.size} for name, buf in self.memory_buffers.items()
            },
            'leak_detection': self.leak_detector.analyze_memory_trend()
        }
        
        return stats
    
    def cleanup(self):
        """Clean up all memory resources."""
        self.stop_monitoring()
        
        # Clear all pools
        for pool in self.pools.values():
            pool.clear()
        
        # Clean up memory buffers
        for buffer in self.memory_buffers.values():
            buffer.cleanup()
        
        self.pools.clear()
        self.memory_buffers.clear()
        
        logger.info("Memory manager cleanup completed")

# Global memory manager instance
memory_manager = MemoryManager()

# Common object pools for Novel Engine
def setup_novel_engine_pools():
    """Setup object pools commonly used in Novel Engine."""
    
    # Dictionary pool for frequent dict allocations
    memory_manager.create_object_pool(
        "dict_pool",
        factory=dict,
        max_size=200,
        reset_func=lambda d: d.clear()
    )
    
    # List pool for frequent list allocations
    memory_manager.create_object_pool(
        "list_pool", 
        factory=list,
        max_size=200,
        reset_func=lambda l: l.clear()
    )
    
    # String builder pool (using list for efficient string building)
    memory_manager.create_object_pool(
        "string_builder_pool",
        factory=list,
        max_size=50,
        reset_func=lambda l: l.clear()
    )
    
    # Async pools for coroutine environments
    memory_manager.create_object_pool(
        "async_dict_pool",
        factory=dict,
        max_size=100,
        reset_func=lambda d: d.clear(),
        async_pool=True
    )

# Context managers for efficient resource usage
class PooledObject:
    """Context manager for pooled object usage."""
    
    def __init__(self, pool: ObjectPool[T]):
        self.pool = pool
        self.obj = None
    
    def __enter__(self) -> T:
        self.obj = self.pool.acquire()
        return self.obj
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.obj is not None:
            self.pool.release(self.obj)
            self.obj = None

class AsyncPooledObject:
    """Async context manager for pooled object usage."""
    
    def __init__(self, pool: AsyncObjectPool[T]):
        self.pool = pool
        self.obj = None
    
    async def __aenter__(self) -> T:
        self.obj = await self.pool.acquire_async()
        return self.obj
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.obj is not None:
            await self.pool.release_async(self.obj)
            self.obj = None

# Memory optimization decorators
def memory_optimized(pool_name: str):
    """Decorator to use pooled objects in function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            pool = memory_manager.get_pool(pool_name)
            if pool:
                with PooledObject(pool) as obj:
                    return func(obj, *args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator

def async_memory_optimized(pool_name: str):
    """Async decorator to use pooled objects in function execution."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            pool = memory_manager.get_pool(pool_name)
            if pool and isinstance(pool, AsyncObjectPool):
                async with AsyncPooledObject(pool) as obj:
                    return await func(obj, *args, **kwargs)
            else:
                return await func(*args, **kwargs)
        return wrapper
    return decorator

if __name__ == "__main__":
    # Example usage and testing
    async def test_memory_optimization():
        """Test the memory optimization system."""
        # Setup pools
        setup_novel_engine_pools()
        
        # Start monitoring
        memory_manager.start_monitoring()
        
        # Test object pooling
        dict_pool = memory_manager.get_pool("dict_pool")
        
        # Performance test
        iterations = 10000
        
        # Test without pooling
        start_time = time.time()
        for _ in range(iterations):
            d = {}
            d['test'] = 'value'
            del d
        no_pool_time = time.time() - start_time
        
        # Test with pooling
        start_time = time.time()
        for _ in range(iterations):
            with PooledObject(dict_pool) as d:
                d['test'] = 'value'
        pool_time = time.time() - start_time
        
        print(f"Without pooling: {no_pool_time:.3f}s")
        print(f"With pooling: {pool_time:.3f}s")
        print(f"Speedup: {no_pool_time/pool_time:.1f}x")
        
        # Get statistics
        stats = await memory_manager.get_comprehensive_stats()
        print(f"Memory usage: {stats['memory_usage']['used_memory_mb']:.1f}MB")
        print(f"Pool stats: {stats['object_pools']}")
        
        # Test memory leak detection
        leak_report = memory_manager.leak_detector.check_for_leaks()
        print(f"Leak detection: {leak_report}")
        
        # Cleanup
        memory_manager.cleanup()
    
    # Run the test
    asyncio.run(test_memory_optimization())