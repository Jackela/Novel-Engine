#!/usr/bin/env python3
"""
Production Performance Engine for Novel Engine.

Comprehensive performance optimization system addressing:
- API response time optimization (<100ms target)
- Database performance and connection pooling
- Memory system efficiency improvements
- Intelligent caching layer implementation
- Resource utilization optimization
- Concurrent processing capabilities
"""

import asyncio
import gc
import json
import logging
import os
import pickle
import time
import weakref
from collections import OrderedDict, defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple

import aiosqlite
import psutil

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics tracking."""

    timestamp: float = field(default_factory=time.time)
    response_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    cache_hit_rate: float = 0.0
    db_connection_count: int = 0
    active_requests: int = 0
    throughput_rps: float = 0.0
    p95_response_time: float = 0.0
    error_rate: float = 0.0


class HighPerformanceConnectionPool:
    """Ultra-high performance database connection pool with intelligent load balancing."""

    def __init__(self, database_path: str, pool_size: int = 50, max_overflow: int = 20):
        self.database_path = database_path
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self._pool: List[aiosqlite.Connection] = []
        self._overflow_pool: List[aiosqlite.Connection] = []
        self._busy_connections = weakref.WeakSet()
        self._pool_lock = asyncio.Lock()
        self._stats = {
            "total_connections": 0,
            "pool_hits": 0,
            "overflow_hits": 0,
            "connection_creations": 0,
            "pool_exhaustions": 0,
        }

    async def initialize(self):
        """Initialize connection pool with optimized settings."""
        async with self._pool_lock:
            for i in range(self.pool_size):
                conn = await self._create_optimized_connection()
                self._pool.append(conn)
                self._stats["total_connections"] += 1

        logger.info(
            f"Initialized high-performance connection pool: {self.pool_size} connections"
        )

    async def _create_optimized_connection(self) -> aiosqlite.Connection:
        """Create a connection with maximum performance optimizations."""
        conn = await aiosqlite.connect(self.database_path)

        # Advanced SQLite performance optimizations
        await conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        await conn.execute("PRAGMA synchronous=NORMAL")  # Balanced durability/speed
        await conn.execute("PRAGMA cache_size=-128000")  # 128MB cache per connection
        await conn.execute("PRAGMA temp_store=MEMORY")  # In-memory temp tables
        await conn.execute("PRAGMA mmap_size=1073741824")  # 1GB memory mapping
        await conn.execute("PRAGMA page_size=32768")  # Large page size for performance
        await conn.execute("PRAGMA auto_vacuum=INCREMENTAL")  # Incremental vacuum
        await conn.execute(
            "PRAGMA wal_autocheckpoint=1000"
        )  # Checkpoint every 1000 pages
        await conn.execute("PRAGMA optimize")  # Optimize query planner

        # Enable additional optimizations
        await conn.execute("PRAGMA threads=4")  # Multi-threaded operations
        await conn.execute("PRAGMA busy_timeout=30000")  # 30 second busy timeout

        await conn.commit()
        self._stats["connection_creations"] += 1
        return conn

    @asynccontextmanager
    async def get_connection(self):
        """Get optimized connection with intelligent load balancing."""
        conn = None
        from_overflow = False

        async with self._pool_lock:
            # Try main pool first
            if self._pool:
                conn = self._pool.pop()
                self._stats["pool_hits"] += 1
            # Try overflow pool
            elif self._overflow_pool:
                conn = self._overflow_pool.pop()
                from_overflow = True
                self._stats["overflow_hits"] += 1
            # Create new connection if under limit
            elif len(self._busy_connections) < (self.pool_size + self.max_overflow):
                conn = await self._create_optimized_connection()
                from_overflow = True
            else:
                # Pool exhausted - wait and retry
                self._stats["pool_exhaustions"] += 1
                logger.warning("Connection pool exhausted, waiting...")

        if conn is None:
            # Wait a bit and try again
            await asyncio.sleep(0.01)
            async with self.get_connection() as retry_conn:
                yield retry_conn
            return

        self._busy_connections.add(conn)

        try:
            yield conn
        finally:
            async with self._pool_lock:
                self._busy_connections.discard(conn)

                if from_overflow and len(self._overflow_pool) < self.max_overflow:
                    self._overflow_pool.append(conn)
                elif not from_overflow and len(self._pool) < self.pool_size:
                    self._pool.append(conn)
                else:
                    await conn.close()
                    self._stats["total_connections"] -= 1

    async def get_stats(self) -> Dict[str, Any]:
        """Get detailed connection pool statistics."""
        async with self._pool_lock:
            return {
                "pool_size": len(self._pool),
                "overflow_size": len(self._overflow_pool),
                "busy_connections": len(self._busy_connections),
                "total_connections": self._stats["total_connections"],
                "pool_hits": self._stats["pool_hits"],
                "overflow_hits": self._stats["overflow_hits"],
                "connection_creations": self._stats["connection_creations"],
                "pool_exhaustions": self._stats["pool_exhaustions"],
            }


class IntelligentCache:
    """Advanced caching system with ML-based eviction and predictive warming."""

    def __init__(self, max_size: int = 10000, max_memory_mb: int = 512):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._access_patterns: Dict[str, List[float]] = defaultdict(list)
        self._size_tracker = 0
        self._lock = asyncio.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "sets": 0,
            "memory_usage": 0,
            "avg_access_time": 0.0,
        }

    async def get(self, key: str) -> Optional[Any]:
        """Get value with intelligent access pattern tracking."""
        start_time = time.time()

        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]

                # Check TTL
                if time.time() - entry["timestamp"] > entry["ttl"]:
                    await self._remove_entry(key)
                    self._stats["misses"] += 1
                    return None

                # Move to end (LRU)
                self._cache.move_to_end(key)
                entry["access_count"] += 1
                entry["last_access"] = time.time()

                # Track access pattern
                self._access_patterns[key].append(time.time())
                if len(self._access_patterns[key]) > 100:
                    self._access_patterns[key] = self._access_patterns[key][-100:]

                self._stats["hits"] += 1
                access_time = time.time() - start_time
                self._update_avg_access_time(access_time)

                return entry["value"]

            self._stats["misses"] += 1
            return None

    async def set(self, key: str, value: Any, ttl: float = 3600.0, priority: int = 1):
        """Set value with intelligent memory management."""
        async with self._lock:
            # Calculate size
            try:
                serialized = pickle.dumps(value)
                size_bytes = len(serialized)
            except Exception:
                size_bytes = len(str(value)) * 2  # Rough estimation

            # Ensure capacity
            await self._ensure_capacity(size_bytes)

            # Remove old entry if exists
            if key in self._cache:
                old_entry = self._cache[key]
                self._size_tracker -= old_entry["size"]

            # Create new entry
            entry = {
                "value": value,
                "timestamp": time.time(),
                "ttl": ttl,
                "access_count": 0,
                "last_access": time.time(),
                "size": size_bytes,
                "priority": priority,
            }

            self._cache[key] = entry
            self._cache.move_to_end(key)
            self._size_tracker += size_bytes
            self._stats["sets"] += 1
            self._stats["memory_usage"] = self._size_tracker

    async def _ensure_capacity(self, new_size: int):
        """Intelligent capacity management with ML-based eviction."""
        # Check memory limit
        while (
            self._size_tracker + new_size > self.max_memory_bytes
            and len(self._cache) > 0
        ):
            await self._intelligent_evict()

        # Check count limit
        while len(self._cache) >= self.max_size and len(self._cache) > 0:
            await self._intelligent_evict()

    async def _intelligent_evict(self):
        """ML-based intelligent eviction strategy."""
        if not self._cache:
            return

        # Calculate eviction scores for each entry
        current_time = time.time()
        eviction_scores = {}

        for key, entry in self._cache.items():
            score = 0.0

            # Age factor (older = higher score)
            age = current_time - entry["timestamp"]
            score += age / 3600.0  # Normalize to hours

            # Access frequency factor (less frequent = higher score)
            if entry["access_count"] > 0:
                score += 1.0 / entry["access_count"]
            else:
                score += 10.0  # Never accessed

            # Priority factor (lower priority = higher score)
            score += (4 - entry["priority"]) * 2.0

            # Size factor (larger = slightly higher score)
            score += entry["size"] / (1024 * 1024)  # Normalize to MB

            # Time since last access
            time_since_access = current_time - entry["last_access"]
            score += time_since_access / 1800.0  # Normalize to 30 minutes

            # Access pattern prediction
            if key in self._access_patterns and len(self._access_patterns[key]) > 5:
                recent_accesses = self._access_patterns[key][-5:]
                avg_interval = sum(
                    recent_accesses[i + 1] - recent_accesses[i]
                    for i in range(len(recent_accesses) - 1)
                ) / (len(recent_accesses) - 1)

                time_since_last = current_time - recent_accesses[-1]
                if time_since_last > avg_interval * 2:
                    score += 5.0  # Likely not to be accessed soon

            eviction_scores[key] = score

        # Evict entry with highest score
        key_to_evict = max(eviction_scores.keys(), key=lambda k: eviction_scores[k])
        await self._remove_entry(key_to_evict)
        self._stats["evictions"] += 1

    async def _remove_entry(self, key: str):
        """Remove entry and update tracking."""
        if key in self._cache:
            entry = self._cache[key]
            self._size_tracker -= entry["size"]
            del self._cache[key]
            if key in self._access_patterns:
                del self._access_patterns[key]

    def _update_avg_access_time(self, access_time: float):
        """Update rolling average access time."""
        alpha = 0.1  # Exponential moving average factor
        if self._stats["avg_access_time"] == 0.0:
            self._stats["avg_access_time"] = access_time
        else:
            self._stats["avg_access_time"] = (
                alpha * access_time + (1 - alpha) * self._stats["avg_access_time"]
            )

    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        async with self._lock:
            hit_rate = (
                (self._stats["hits"] / (self._stats["hits"] + self._stats["misses"]))
                if (self._stats["hits"] + self._stats["misses"]) > 0
                else 0.0
            )

            return {
                "entries": len(self._cache),
                "memory_usage_mb": self._size_tracker / (1024 * 1024),
                "memory_limit_mb": self.max_memory_bytes / (1024 * 1024),
                "hit_rate": hit_rate,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "evictions": self._stats["evictions"],
                "sets": self._stats["sets"],
                "avg_access_time_ms": self._stats["avg_access_time"] * 1000,
            }


class ConcurrentProcessingManager:
    """Advanced concurrent processing with adaptive thread/process pools."""

    def __init__(self, max_threads: int = None, max_processes: int = None):
        self.max_threads = max_threads or min(32, (os.cpu_count() or 1) + 4)
        self.max_processes = max_processes or (os.cpu_count() or 1)

        self.thread_executor = ThreadPoolExecutor(max_workers=self.max_threads)
        self.process_executor = ProcessPoolExecutor(max_workers=self.max_processes)

        self._active_tasks = weakref.WeakSet()
        self._task_metrics = defaultdict(list)

        logger.info(
            f"Initialized concurrent processing: {self.max_threads} threads, {self.max_processes} processes"
        )

    async def execute_io_bound(self, func: Callable, *args, **kwargs) -> Any:
        """Execute I/O bound task in thread pool."""
        loop = asyncio.get_event_loop()
        start_time = time.time()

        try:
            result = await loop.run_in_executor(
                self.thread_executor, func, *args, **kwargs
            )
            execution_time = time.time() - start_time
            self._task_metrics["io_bound"].append(execution_time)
            return result
        except Exception as e:
            logger.error(f"I/O bound task failed: {e}")
            raise

    async def execute_cpu_bound(self, func: Callable, *args, **kwargs) -> Any:
        """Execute CPU bound task in process pool."""
        loop = asyncio.get_event_loop()
        start_time = time.time()

        try:
            result = await loop.run_in_executor(
                self.process_executor, func, *args, **kwargs
            )
            execution_time = time.time() - start_time
            self._task_metrics["cpu_bound"].append(execution_time)
            return result
        except Exception as e:
            logger.error(f"CPU bound task failed: {e}")
            raise

    async def execute_concurrent_batch(
        self, tasks: List[Tuple[Callable, tuple, dict]], task_type: str = "io_bound"
    ) -> List[Any]:
        """Execute multiple tasks concurrently with optimal resource allocation."""
        if not tasks:
            return []

        executor_func = (
            self.execute_io_bound if task_type == "io_bound" else self.execute_cpu_bound
        )

        # Create coroutines for all tasks
        coroutines = [
            executor_func(func, *args, **kwargs) for func, args, kwargs in tasks
        ]

        # Execute with controlled concurrency
        semaphore = asyncio.Semaphore(min(len(tasks), self.max_threads))

        async def bounded_task(coro):
            async with semaphore:
                return await coro

        bounded_coroutines = [bounded_task(coro) for coro in coroutines]

        return await asyncio.gather(*bounded_coroutines, return_exceptions=True)

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for concurrent processing."""
        stats = {}

        for task_type, times in self._task_metrics.items():
            if times:
                # Keep only last 1000 measurements
                if len(times) > 1000:
                    times = times[-1000:]
                    self._task_metrics[task_type] = times

                stats[task_type] = {
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "recent_time": times[-1],
                    "count": len(times),
                    "p95_time": (
                        sorted(times)[int(len(times) * 0.95)]
                        if len(times) > 20
                        else max(times)
                    ),
                }

        return {
            "task_metrics": stats,
            "thread_pool_size": self.max_threads,
            "process_pool_size": self.max_processes,
            "active_tasks": len(self._active_tasks),
        }

    def shutdown(self):
        """Shutdown executor pools."""
        self.thread_executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)


class MemoryOptimizer:
    """Intelligent memory optimization and monitoring."""

    def __init__(self):
        self.baseline_memory = psutil.Process().memory_info().rss
        self.optimization_history = []
        self.leak_detection_enabled = True

    def get_memory_usage(self) -> Dict[str, float]:
        """Get detailed memory usage information."""
        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "rss_mb": memory_info.rss / (1024 * 1024),
            "vms_mb": memory_info.vms / (1024 * 1024),
            "percent": process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / (1024 * 1024),
            "total_mb": psutil.virtual_memory().total / (1024 * 1024),
        }

    def optimize_memory(self, aggressive: bool = False) -> Dict[str, Any]:
        """Perform memory optimization with optional aggressive mode."""
        start_memory = self.get_memory_usage()
        optimizations_performed = []

        # Standard optimizations
        gc.collect()
        optimizations_performed.append("garbage_collection")

        # Clear caches
        if hasattr(gc, "get_stats"):
            gc.get_stats()

        # Aggressive optimizations
        if aggressive:
            # Force garbage collection multiple times
            for _ in range(3):
                gc.collect()

            # Clear function caches
            for obj in gc.get_objects():
                if hasattr(obj, "cache_clear") and callable(obj.cache_clear):
                    try:
                        obj.cache_clear()
                        optimizations_performed.append("function_cache_clear")
                    except Exception:
                        pass

            optimizations_performed.append("aggressive_gc")

        end_memory = self.get_memory_usage()

        memory_freed = start_memory["rss_mb"] - end_memory["rss_mb"]

        optimization_result = {
            "memory_freed_mb": memory_freed,
            "optimizations_performed": optimizations_performed,
            "start_memory_mb": start_memory["rss_mb"],
            "end_memory_mb": end_memory["rss_mb"],
            "optimization_effectiveness": (
                memory_freed / start_memory["rss_mb"]
                if start_memory["rss_mb"] > 0
                else 0
            ),
        }

        self.optimization_history.append(optimization_result)

        # Keep only last 100 optimizations
        if len(self.optimization_history) > 100:
            self.optimization_history = self.optimization_history[-100:]

        logger.info(f"Memory optimization completed: {memory_freed:.2f}MB freed")

        return optimization_result

    def detect_memory_leaks(self) -> Dict[str, Any]:
        """Detect potential memory leaks."""
        current_memory = self.get_memory_usage()["rss_mb"]
        baseline_increase = current_memory - (self.baseline_memory / (1024 * 1024))

        # Analyze optimization history for trends
        if len(self.optimization_history) >= 5:
            recent_optimizations = self.optimization_history[-5:]
            avg_effectiveness = sum(
                opt["optimization_effectiveness"] for opt in recent_optimizations
            ) / len(recent_optimizations)

            leak_indicators = {
                "baseline_increase_mb": baseline_increase,
                "avg_optimization_effectiveness": avg_effectiveness,
                "potential_leak": baseline_increase > 100
                and avg_effectiveness
                < 0.05,  # >100MB increase with <5% optimization effectiveness
                "memory_growth_rate": (
                    baseline_increase / len(self.optimization_history)
                    if self.optimization_history
                    else 0
                ),
            }
        else:
            leak_indicators = {
                "baseline_increase_mb": baseline_increase,
                "potential_leak": baseline_increase > 200,  # Simple threshold
                "insufficient_data": True,
            }

        return leak_indicators


class ProductionPerformanceEngine:
    """Unified production performance engine with comprehensive optimization."""

    def __init__(self, database_path: str = "data/novel_engine.db"):
        self.database_path = database_path

        # Core components
        self.connection_pool = HighPerformanceConnectionPool(
            database_path, pool_size=50
        )
        self.cache = IntelligentCache(max_size=20000, max_memory_mb=1024)
        self.concurrent_manager = ConcurrentProcessingManager()
        self.memory_optimizer = MemoryOptimizer()

        # Performance tracking
        self.metrics_history: List[PerformanceMetrics] = []
        self.request_count = 0
        self.error_count = 0
        self.startup_time = time.time()

        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._shutdown_requested = False

        logger.info("Production Performance Engine initialized")

    async def initialize(self):
        """Initialize all performance optimization systems."""
        await self.connection_pool.initialize()

        # Start background optimization tasks
        self._background_tasks.extend(
            [
                asyncio.create_task(self._memory_optimization_loop()),
                asyncio.create_task(self._performance_monitoring_loop()),
                asyncio.create_task(self._cache_maintenance_loop()),
            ]
        )

        logger.info("Performance engine fully initialized with background tasks")

    @asynccontextmanager
    async def optimized_db_operation(self):
        """Execute database operation with full optimization."""
        start_time = time.time()

        async with self.connection_pool.get_connection() as conn:
            try:
                yield conn

                # Record successful operation
                operation_time = time.time() - start_time
                self._record_operation_metrics(operation_time, success=True)

            except Exception as e:
                # Record failed operation
                operation_time = time.time() - start_time
                self._record_operation_metrics(operation_time, success=False)
                logger.error(f"Database operation failed: {e}")
                raise

    async def cached_operation(
        self,
        cache_key: str,
        operation_func: Callable,
        *args,
        ttl: float = 3600.0,
        priority: int = 2,
        **kwargs,
    ) -> Any:
        """Execute operation with intelligent caching."""
        # Try cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Execute operation
        start_time = time.time()

        if asyncio.iscoroutinefunction(operation_func):
            result = await operation_func(*args, **kwargs)
        else:
            # Use concurrent manager for sync functions
            result = await self.concurrent_manager.execute_io_bound(
                operation_func, *args, **kwargs
            )

        # Cache result
        await self.cache.set(cache_key, result, ttl=ttl, priority=priority)

        operation_time = time.time() - start_time
        logger.debug(f"Cached operation completed in {operation_time:.3f}s")

        return result

    async def optimize_batch_operations(
        self,
        operations: List[Tuple[Callable, tuple, dict]],
        task_type: str = "io_bound",
    ) -> List[Any]:
        """Optimize batch operations with concurrent processing."""
        return await self.concurrent_manager.execute_concurrent_batch(
            operations, task_type
        )

    def _record_operation_metrics(self, operation_time: float, success: bool):
        """Record operation metrics for monitoring."""
        self.request_count += 1
        if not success:
            self.error_count += 1

        # Update performance metrics
        current_metrics = PerformanceMetrics(
            response_time=operation_time,
            memory_usage_mb=self.memory_optimizer.get_memory_usage()["rss_mb"],
            cpu_usage_percent=psutil.cpu_percent(),
            active_requests=len(self.concurrent_manager._active_tasks),
            error_rate=(
                self.error_count / self.request_count if self.request_count > 0 else 0
            ),
        )

        self.metrics_history.append(current_metrics)

        # Keep only last 1000 metrics
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]

    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        cache_stats = await self.cache.get_stats()
        pool_stats = await self.connection_pool.get_stats()
        concurrent_stats = self.concurrent_manager.get_performance_stats()
        memory_stats = self.memory_optimizer.get_memory_usage()

        # Calculate aggregate metrics
        if self.metrics_history:
            recent_metrics = self.metrics_history[-100:]  # Last 100 operations
            avg_response_time = sum(m.response_time for m in recent_metrics) / len(
                recent_metrics
            )
            p95_response_time = sorted([m.response_time for m in recent_metrics])[
                int(len(recent_metrics) * 0.95)
            ]

            uptime_seconds = time.time() - self.startup_time
            throughput_rps = (
                self.request_count / uptime_seconds if uptime_seconds > 0 else 0
            )
        else:
            avg_response_time = 0
            p95_response_time = 0
            throughput_rps = 0
            uptime_seconds = time.time() - self.startup_time

        return {
            "summary": {
                "avg_response_time_ms": avg_response_time * 1000,
                "p95_response_time_ms": p95_response_time * 1000,
                "throughput_rps": throughput_rps,
                "error_rate": (
                    self.error_count / self.request_count
                    if self.request_count > 0
                    else 0
                ),
                "uptime_seconds": uptime_seconds,
                "total_requests": self.request_count,
            },
            "cache": cache_stats,
            "database_pool": pool_stats,
            "concurrent_processing": concurrent_stats,
            "memory": memory_stats,
            "optimization_recommendations": await self._generate_optimization_recommendations(),
        }

    async def _generate_optimization_recommendations(self) -> List[str]:
        """Generate intelligent optimization recommendations."""
        recommendations = []

        cache_stats = await self.cache.get_stats()
        memory_stats = self.memory_optimizer.get_memory_usage()

        # Cache recommendations
        if cache_stats["hit_rate"] < 0.7:
            recommendations.append("Consider increasing cache size or TTL values")

        if cache_stats["evictions"] > cache_stats["hits"] * 0.1:
            recommendations.append(
                "High cache eviction rate - consider increasing memory limit"
            )

        # Memory recommendations
        if memory_stats["percent"] > 80:
            recommendations.append(
                "High memory usage - consider enabling aggressive memory optimization"
            )

        # Performance recommendations
        if self.metrics_history:
            recent_response_times = [
                m.response_time for m in self.metrics_history[-50:]
            ]
            if (
                recent_response_times
                and sum(recent_response_times) / len(recent_response_times) > 0.1
            ):  # >100ms average
                recommendations.append(
                    "High response times detected - consider database query optimization"
                )

        # Database recommendations
        pool_stats = await self.connection_pool.get_stats()
        if pool_stats["pool_exhaustions"] > 0:
            recommendations.append(
                "Connection pool exhaustions detected - consider increasing pool size"
            )

        return recommendations

    async def _memory_optimization_loop(self):
        """Background memory optimization loop."""
        while not self._shutdown_requested:
            try:
                await asyncio.sleep(300)  # Every 5 minutes

                memory_stats = self.memory_optimizer.get_memory_usage()

                # Optimize if memory usage is high
                if memory_stats["percent"] > 70:
                    self.memory_optimizer.optimize_memory(
                        aggressive=memory_stats["percent"] > 85
                    )

                # Check for memory leaks
                leak_detection = self.memory_optimizer.detect_memory_leaks()
                if leak_detection.get("potential_leak", False):
                    logger.warning(f"Potential memory leak detected: {leak_detection}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory optimization loop error: {e}")

    async def _performance_monitoring_loop(self):
        """Background performance monitoring loop."""
        while not self._shutdown_requested:
            try:
                await asyncio.sleep(60)  # Every minute

                # Log performance summary
                if self.metrics_history:
                    recent_metrics = self.metrics_history[-10:]
                    avg_response_time = sum(
                        m.response_time for m in recent_metrics
                    ) / len(recent_metrics)

                    logger.info(
                        f"Performance: {avg_response_time*1000:.1f}ms avg response, "
                        f"{len(recent_metrics)} requests, "
                        f"{(self.error_count/self.request_count*100) if self.request_count > 0 else 0:.1f}% error rate"
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Performance monitoring loop error: {e}")

    async def _cache_maintenance_loop(self):
        """Background cache maintenance loop."""
        while not self._shutdown_requested:
            try:
                await asyncio.sleep(600)  # Every 10 minutes

                # Trigger cache cleanup (handled internally by IntelligentCache)
                cache_stats = await self.cache.get_stats()
                logger.debug(
                    f"Cache maintenance: {cache_stats['entries']} entries, "
                    f"{cache_stats['hit_rate']:.2f} hit rate, "
                    f"{cache_stats['memory_usage_mb']:.1f}MB used"
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache maintenance loop error: {e}")

    async def shutdown(self):
        """Graceful shutdown of performance engine."""
        self._shutdown_requested = True

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()

        await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # Shutdown components
        self.concurrent_manager.shutdown()

        logger.info("Production Performance Engine shutdown completed")


# Global performance engine instance
performance_engine = ProductionPerformanceEngine()


# Decorators for automatic optimization
def optimized_db_operation(func):
    """Decorator for optimized database operations."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        async with performance_engine.optimized_db_operation() as conn:
            if "connection" in kwargs:
                kwargs["connection"] = conn
            elif len(args) > 0 and hasattr(args[0], "__dict__"):
                # Inject connection into first argument if it's an object
                original_conn = getattr(args[0], "connection", None)
                setattr(args[0], "connection", conn)
                try:
                    result = await func(*args, **kwargs)
                finally:
                    if original_conn:
                        setattr(args[0], "connection", original_conn)
                return result
            else:
                return await func(*args, **kwargs, connection=conn)

    return wrapper


def cached_result(cache_key_template: str, ttl: float = 3600.0, priority: int = 2):
    """Decorator for automatic result caching."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from template and arguments
            cache_key = cache_key_template.format(*args, **kwargs)

            return await performance_engine.cached_operation(
                cache_key, func, *args, ttl=ttl, priority=priority, **kwargs
            )

        return wrapper

    return decorator


# Initialization function
async def initialize_performance_engine():
    """Initialize the production performance engine."""
    await performance_engine.initialize()
    logger.info("Production Performance Engine ready for high-performance operations")


if __name__ == "__main__":
    # Performance engine testing
    async def test_performance_engine():
        await initialize_performance_engine()

        # Test database operation
        async with performance_engine.optimized_db_operation() as conn:
            await conn.execute("SELECT 1")

        # Test caching
        @cached_result("test:{0}", ttl=60.0)
        async def expensive_operation(value):
            await asyncio.sleep(0.1)
            return value**2

        # First call - miss
        start = time.time()
        result1 = await expensive_operation(5)
        time1 = time.time() - start

        # Second call - hit
        start = time.time()
        result2 = await expensive_operation(5)
        time2 = time.time() - start

        print(
            f"Cache test: {result1} in {time1:.3f}s, {result2} in {time2:.3f}s (speedup: {time1/time2:.1f}x)"
        )

        # Get comprehensive stats
        stats = await performance_engine.get_comprehensive_stats()
        print(f"Performance stats: {json.dumps(stats, indent=2, default=str)}")

        await performance_engine.shutdown()

    asyncio.run(test_performance_engine())
