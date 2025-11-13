#!/usr/bin/env python3
"""
Performance Optimization Implementation for Novel Engine.

Addresses the critical performance gaps identified in production readiness assessment:
- Response time: 2,075ms → <200ms target (90% improvement needed)
- Throughput: 157 req/s → 1000+ req/s target (500% improvement needed)
- Concurrent users: 0 → 200+ concurrent users (∞ improvement needed)
"""

import asyncio
import gc
import logging
import time
import weakref
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any, Dict, List, Optional

import aiosqlite

logger = logging.getLogger(__name__)


class AsyncDatabasePool:
    """High-performance async database connection pool."""

    def __init__(self, database_path: str, max_connections: int = 10):
        self.database_path = database_path
        self.max_connections = max_connections
        self._pool: List[aiosqlite.Connection] = []
        self._busy_connections: weakref.WeakSet = weakref.WeakSet()
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize the connection pool."""
        async with self._lock:
            for _ in range(self.max_connections):
                conn = await aiosqlite.connect(self.database_path)
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
                await conn.execute("PRAGMA temp_store=memory")
                await conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
                await conn.execute("PRAGMA synchronous=NORMAL")
                await conn.commit()
                self._pool.append(conn)
        logger.info(
            f"Initialized database pool with {self.max_connections} connections"
        )

    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool."""
        async with self._lock:
            if not self._pool:
                # Create temporary connection if pool exhausted
                conn = await aiosqlite.connect(self.database_path)
                await conn.execute("PRAGMA journal_mode=WAL")
                await conn.execute("PRAGMA cache_size=-32000")
                await conn.execute("PRAGMA temp_store=memory")
            else:
                conn = self._pool.pop()

            self._busy_connections.add(conn)

        try:
            yield conn
        finally:
            async with self._lock:
                if conn not in self._busy_connections:
                    return
                self._busy_connections.discard(conn)
                if len(self._pool) < self.max_connections:
                    self._pool.append(conn)
                else:
                    await conn.close()


class AdvancedCache:
    """High-performance caching system with intelligent eviction."""

    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with LRU tracking."""
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if time.time() - entry["timestamp"] > self.ttl:
                del self._cache[key]
                del self._access_times[key]
                return None

            self._access_times[key] = time.time()
            return entry["value"]

    async def set(self, key: str, value: Any) -> None:
        """Set value in cache with automatic eviction."""
        async with self._lock:
            current_time = time.time()

            # Evict old entries
            if len(self._cache) >= self.max_size:
                await self._evict_lru()

            self._cache[key] = {"value": value, "timestamp": current_time}
            self._access_times[key] = current_time

    async def _evict_lru(self):
        """Evict least recently used entries."""
        if not self._access_times:
            return

        # Remove 25% of cache when full
        to_remove = max(1, len(self._cache) // 4)
        sorted_keys = sorted(self._access_times.items(), key=lambda x: x[1])

        for key, _ in sorted_keys[:to_remove]:
            self._cache.pop(key, None)
            self._access_times.pop(key, None)


class AsyncEventBus:
    """High-performance async event bus."""

    def __init__(self):
        self._subscribers: Dict[str, List[callable]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, event_type: str, callback: callable):
        """Subscribe to an event type."""
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    async def emit(self, event_type: str, data: Any):
        """Emit an event to all subscribers."""
        subscribers = []
        async with self._lock:
            subscribers = self._subscribers.get(event_type, []).copy()

        if subscribers:
            # Process events concurrently
            tasks = []
            for callback in subscribers:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(data))
                else:
                    # Run sync callbacks in thread pool
                    tasks.append(
                        asyncio.get_event_loop().run_in_executor(None, callback, data)
                    )

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)


class PerformanceOptimizer:
    """Central performance optimization coordinator."""

    def __init__(self):
        self.db_pool: Optional[AsyncDatabasePool] = None
        self.cache = AdvancedCache(max_size=2000, ttl=600)
        self.event_bus = AsyncEventBus()
        self._metrics: Dict[str, List[float]] = {}

    async def initialize(self, database_path: str = "data/novel_engine.db"):
        """Initialize performance optimization systems."""
        self.db_pool = AsyncDatabasePool(database_path, max_connections=20)
        await self.db_pool.initialize()
        logger.info("Performance optimization systems initialized")

    @asynccontextmanager
    async def get_db_connection(self):
        """Get optimized database connection."""
        if not self.db_pool:
            raise RuntimeError("Database pool not initialized")
        async with self.db_pool.get_connection() as conn:
            yield conn

    async def cached_operation(
        self, cache_key: str, operation: callable, *args, **kwargs
    ):
        """Execute operation with caching."""
        # Try cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Execute operation
        if asyncio.iscoroutinefunction(operation):
            result = await operation(*args, **kwargs)
        else:
            result = operation(*args, **kwargs)

        # Cache result
        await self.cache.set(cache_key, result)
        return result

    async def measure_performance(
        self, operation_name: str, operation: callable, *args, **kwargs
    ):
        """Measure and record operation performance."""
        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(operation):
                result = await operation(*args, **kwargs)
            else:
                result = operation(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            if operation_name not in self._metrics:
                self._metrics[operation_name] = []
            self._metrics[operation_name].append(duration)

            # Keep only last 100 measurements
            if len(self._metrics[operation_name]) > 100:
                self._metrics[operation_name] = self._metrics[operation_name][-100:]

    def get_performance_stats(self) -> Dict[str, Dict[str, float]]:
        """Get performance statistics."""
        stats = {}
        for operation, times in self._metrics.items():
            if times:
                stats[operation] = {
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "recent_time": times[-1] if times else 0,
                    "count": len(times),
                }
        return stats


# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()


async def optimize_character_loading(character_factory, character_name: str):
    """Optimized character loading with caching."""
    cache_key = f"character:{character_name}"

    async def load_character():
        # Use event bus for async coordination
        await performance_optimizer.event_bus.emit(
            "character_loading_start", character_name
        )

        # Load character (this would be the original synchronous operation)
        agent = character_factory.create_character(character_name)

        await performance_optimizer.event_bus.emit(
            "character_loading_complete", character_name
        )
        return agent

    return await performance_optimizer.cached_operation(cache_key, load_character)


async def optimize_simulation_execution(director, turns: int):
    """Optimized simulation execution with async coordination."""

    async def execute_turn_async(turn_number: int):
        """Execute a single turn asynchronously."""
        await performance_optimizer.event_bus.emit("turn_start", turn_number)

        # Execute turn (wrap synchronous operation)
        await asyncio.get_event_loop().run_in_executor(None, director.run_turn)

        await performance_optimizer.event_bus.emit("turn_complete", turn_number)

    # Execute turns with controlled concurrency
    semaphore = asyncio.Semaphore(3)  # Limit concurrent turns

    async def bounded_turn(turn_num):
        async with semaphore:
            return await execute_turn_async(turn_num)

    # Run turns with performance measurement
    tasks = [
        performance_optimizer.measure_performance(f"turn_{i}", bounded_turn, i)
        for i in range(turns)
    ]

    await asyncio.gather(*tasks, return_exceptions=True)


@lru_cache(maxsize=128)
def cached_config_loader():
    """Cached configuration loading."""
    from config_loader import get_config

    return get_config()


class AsyncSimulationManager:
    """High-performance simulation manager."""

    def __init__(self):
        self.active_simulations: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def start_simulation(
        self, simulation_id: str, character_names: List[str], turns: int
    ):
        """Start an async simulation."""
        async with self._lock:
            if simulation_id in self.active_simulations:
                raise ValueError(f"Simulation {simulation_id} already active")

            self.active_simulations[simulation_id] = {
                "character_names": character_names,
                "turns": turns,
                "status": "starting",
                "start_time": time.time(),
            }

        try:
            # Initialize components asynchronously
            from src.agents.director_agent import DirectorAgent
            from src.config.character_factory import CharacterFactory
            from src.event_bus import EventBus

            event_bus = EventBus()
            character_factory = CharacterFactory(event_bus)

            # Load characters concurrently
            character_tasks = [
                optimize_character_loading(character_factory, name)
                for name in character_names
            ]
            agents = await asyncio.gather(*character_tasks)

            # Set up director
            log_path = f"logs/async_simulation_{simulation_id}.md"
            director = DirectorAgent(event_bus, campaign_log_path=log_path)
            for agent in agents:
                director.register_agent(agent)

            # Update status
            async with self._lock:
                self.active_simulations[simulation_id]["status"] = "running"

            # Execute simulation
            await optimize_simulation_execution(director, turns)

            # Generate story
            from src.agents.chronicler_agent import ChroniclerAgent

            chronicler = ChroniclerAgent(event_bus, character_names=character_names)
            story = chronicler.transcribe_log(log_path)

            # Clean up
            import os

            if os.path.exists(log_path):
                os.remove(log_path)

            result = {
                "story": story,
                "participants": character_names,
                "turns_executed": turns,
                "duration_seconds": time.time()
                - self.active_simulations[simulation_id]["start_time"],
            }

            async with self._lock:
                self.active_simulations[simulation_id]["status"] = "completed"
                self.active_simulations[simulation_id]["result"] = result

            return result

        except Exception as e:
            async with self._lock:
                self.active_simulations[simulation_id]["status"] = "failed"
                self.active_simulations[simulation_id]["error"] = str(e)
            raise

    async def get_simulation_status(
        self, simulation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get simulation status."""
        async with self._lock:
            return self.active_simulations.get(simulation_id)

    async def cleanup_completed_simulations(self):
        """Clean up old completed simulations."""
        current_time = time.time()
        async with self._lock:
            to_remove = []
            for sim_id, sim_data in self.active_simulations.items():
                if (
                    sim_data["status"] in ["completed", "failed"]
                    and current_time - sim_data["start_time"] > 3600
                ):  # 1 hour
                    to_remove.append(sim_id)

            for sim_id in to_remove:
                del self.active_simulations[sim_id]


# Global simulation manager
simulation_manager = AsyncSimulationManager()


# Memory optimization utilities
def optimize_memory():
    """Optimize memory usage."""
    # Force garbage collection
    gc.collect()

    # Clear internal caches
    cached_config_loader.cache_clear()

    logger.info("Memory optimization completed")


async def initialize_performance_systems():
    """Initialize all performance optimization systems."""
    await performance_optimizer.initialize()
    logger.info("All performance systems initialized")


if __name__ == "__main__":
    # Test performance optimization
    async def test_performance():
        await initialize_performance_systems()

        # Test database operations
        async with performance_optimizer.get_db_connection() as conn:
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS test (id INTEGER, data TEXT)"
            )
            await conn.commit()

        logger.info("Performance optimization systems tested successfully")

    asyncio.run(test_performance())
