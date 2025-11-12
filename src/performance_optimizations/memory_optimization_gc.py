"""
Memory Optimization and Garbage Collection Management
====================================================

Advanced memory optimization system with intelligent garbage collection
and memory usage monitoring for Novel Engine performance optimization.

Wave 5.4 - Memory Management & Garbage Collection Enhancement
"""

import asyncio
import gc
import logging
import threading
import weakref
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


class MemoryPressureLevel(Enum):
    """Memory pressure levels for optimization decisions."""

    LOW = "low"  # < 60% memory usage
    MODERATE = "moderate"  # 60-75% memory usage
    HIGH = "high"  # 75-85% memory usage
    CRITICAL = "critical"  # > 85% memory usage


@dataclass
class MemoryMetrics:
    """Memory usage metrics and statistics."""

    timestamp: datetime
    total_memory_mb: float
    available_memory_mb: float
    used_memory_mb: float
    memory_percent: float
    process_memory_mb: float
    gc_collections: Dict[int, int]
    gc_objects_count: int
    memory_pressure: MemoryPressureLevel

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_memory_mb": self.total_memory_mb,
            "available_memory_mb": self.available_memory_mb,
            "used_memory_mb": self.used_memory_mb,
            "memory_percent": self.memory_percent,
            "process_memory_mb": self.process_memory_mb,
            "gc_collections": self.gc_collections,
            "gc_objects_count": self.gc_objects_count,
            "memory_pressure": self.memory_pressure.value,
        }


class ObjectPool:
    """
    Object pool for reusing expensive-to-create objects.

    Reduces garbage collection pressure by reusing objects instead of
    constantly creating and destroying them.
    """

    def __init__(self, factory: Callable[[], Any], max_size: int = 100):
        self.factory = factory
        self.max_size = max_size
        self.pool = deque(maxlen=max_size)
        self.created_count = 0
        self.reused_count = 0
        self._lock = threading.Lock()

    def acquire(self) -> Any:
        """Acquire object from pool or create new one."""
        with self._lock:
            if self.pool:
                obj = self.pool.popleft()
                self.reused_count += 1
                return obj
            else:
                obj = self.factory()
                self.created_count += 1
                return obj

    def release(self, obj: Any) -> bool:
        """Return object to pool for reuse."""
        with self._lock:
            if len(self.pool) < self.max_size:
                # Reset object state if it has a reset method
                if hasattr(obj, "reset"):
                    obj.reset()
                self.pool.append(obj)
                return True
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return {
                "pool_size": len(self.pool),
                "max_size": self.max_size,
                "created_count": self.created_count,
                "reused_count": self.reused_count,
                "reuse_rate_percent": (
                    self.reused_count / max(1, self.created_count + self.reused_count)
                )
                * 100,
            }


class WeakReferenceManager:
    """
    Manages weak references to break circular references and prevent memory leaks.
    """

    def __init__(self):
        self.weak_refs: Dict[str, weakref.ref] = {}
        self.cleanup_callbacks: Dict[str, Callable] = {}
        self._lock = threading.Lock()

    def register(self, key: str, obj: Any, cleanup_callback: Optional[Callable] = None):
        """Register object with weak reference."""
        with self._lock:
            if cleanup_callback:
                self.cleanup_callbacks[key] = cleanup_callback
                weak_ref = weakref.ref(obj, lambda ref: self._cleanup_callback(key))
            else:
                weak_ref = weakref.ref(obj)

            self.weak_refs[key] = weak_ref

    def get(self, key: str) -> Optional[Any]:
        """Get object if it still exists."""
        with self._lock:
            weak_ref = self.weak_refs.get(key)
            if weak_ref:
                obj = weak_ref()
                if obj is None:
                    # Object was garbage collected, clean up reference
                    del self.weak_refs[key]
                    if key in self.cleanup_callbacks:
                        del self.cleanup_callbacks[key]
                return obj
            return None

    def _cleanup_callback(self, key: str):
        """Handle object cleanup when it's garbage collected."""
        if key in self.cleanup_callbacks:
            try:
                self.cleanup_callbacks[key]()
            except Exception as e:
                logger.error(f"Cleanup callback failed for {key}: {e}")
            finally:
                with self._lock:
                    if key in self.cleanup_callbacks:
                        del self.cleanup_callbacks[key]

    def cleanup_dead_references(self) -> int:
        """Remove dead weak references."""
        dead_refs = []
        with self._lock:
            for key, weak_ref in list(self.weak_refs.items()):
                if weak_ref() is None:
                    dead_refs.append(key)

            for key in dead_refs:
                del self.weak_refs[key]
                if key in self.cleanup_callbacks:
                    del self.cleanup_callbacks[key]

        return len(dead_refs)

    def get_stats(self) -> Dict[str, Any]:
        """Get weak reference manager statistics."""
        with self._lock:
            alive_refs = sum(1 for ref in self.weak_refs.values() if ref() is not None)
            return {
                "total_references": len(self.weak_refs),
                "alive_references": alive_refs,
                "dead_references": len(self.weak_refs) - alive_refs,
                "cleanup_callbacks": len(self.cleanup_callbacks),
            }


class MemoryOptimizer:
    """
    Intelligent memory optimizer with adaptive garbage collection.

    Features:
    - Adaptive GC tuning based on memory pressure
    - Object pooling for expensive objects
    - Weak reference management
    - Memory pressure monitoring
    - Automatic memory cleanup
    """

    def __init__(
        self,
        target_memory_percent: float = 70.0,
        gc_threshold_multiplier: float = 1.5,
        monitoring_interval: float = 30.0,
    ):

        self.target_memory_percent = target_memory_percent
        self.gc_threshold_multiplier = gc_threshold_multiplier
        self.monitoring_interval = monitoring_interval

        # Memory monitoring
        self.memory_history: deque = deque(maxlen=100)
        self.memory_alerts: List[Dict[str, Any]] = []

        # Object management
        self.object_pools: Dict[str, ObjectPool] = {}
        self.weak_ref_manager = WeakReferenceManager()

        # GC tuning
        self.original_gc_thresholds = gc.get_threshold()
        self.gc_stats = defaultdict(int)

        # Monitoring control
        self.monitoring_active = True
        self.monitoring_task = None

        # Performance tracking
        self.optimization_stats = {
            "memory_cleanups": 0,
            "gc_optimizations": 0,
            "object_pool_saves": 0,
            "weak_ref_cleanups": 0,
        }

        logger.info(f"MemoryOptimizer initialized: target={target_memory_percent}%")

    async def start_monitoring(self):
        """Start memory monitoring and optimization."""
        if self.monitoring_task is None:
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Memory optimization monitoring started")

    async def stop_monitoring(self):
        """Stop memory monitoring."""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None

        # Restore original GC thresholds
        gc.set_threshold(*self.original_gc_thresholds)
        logger.info("Memory optimization monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                # Collect memory metrics
                metrics = self._collect_memory_metrics()
                self.memory_history.append(metrics)

                # Determine memory pressure and optimize accordingly
                await self._optimize_based_on_pressure(metrics)

                # Periodic maintenance
                await self._periodic_maintenance()

                await asyncio.sleep(self.monitoring_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                await asyncio.sleep(5.0)

    def _collect_memory_metrics(self) -> MemoryMetrics:
        """Collect comprehensive memory metrics."""
        # System memory info
        memory = psutil.virtual_memory()
        process = psutil.Process()
        process_memory = process.memory_info()

        # GC statistics
        gc_stats = {i: gc.get_count()[i] for i in range(3)}
        gc_objects = len(gc.get_objects())

        # Determine memory pressure level
        memory_percent = memory.percent
        if memory_percent < 60:
            pressure = MemoryPressureLevel.LOW
        elif memory_percent < 75:
            pressure = MemoryPressureLevel.MODERATE
        elif memory_percent < 85:
            pressure = MemoryPressureLevel.HIGH
        else:
            pressure = MemoryPressureLevel.CRITICAL

        return MemoryMetrics(
            timestamp=datetime.now(),
            total_memory_mb=memory.total / 1024 / 1024,
            available_memory_mb=memory.available / 1024 / 1024,
            used_memory_mb=memory.used / 1024 / 1024,
            memory_percent=memory_percent,
            process_memory_mb=process_memory.rss / 1024 / 1024,
            gc_collections=gc_stats,
            gc_objects_count=gc_objects,
            memory_pressure=pressure,
        )

    async def _optimize_based_on_pressure(self, metrics: MemoryMetrics):
        """Optimize memory based on current pressure level."""
        if metrics.memory_pressure == MemoryPressureLevel.CRITICAL:
            # Aggressive optimization
            await self._aggressive_memory_cleanup()
            self._tune_gc_for_pressure(aggressive=True)

        elif metrics.memory_pressure == MemoryPressureLevel.HIGH:
            # Moderate optimization
            await self._moderate_memory_cleanup()
            self._tune_gc_for_pressure(aggressive=False)

        elif metrics.memory_pressure == MemoryPressureLevel.MODERATE:
            # Light optimization
            self._light_memory_cleanup()

        # Always perform weak reference cleanup
        self.weak_ref_manager.cleanup_dead_references()

    async def _aggressive_memory_cleanup(self):
        """Aggressive memory cleanup for critical pressure."""
        logger.warning("Critical memory pressure - performing aggressive cleanup")

        # Force garbage collection multiple times
        for generation in [2, 1, 0]:  # Reverse order for efficiency
            collected = gc.collect(generation)
            self.gc_stats[f"aggressive_gen{generation}"] += collected

        # Clear object pools to release pooled objects
        for pool_name, pool in self.object_pools.items():
            with pool._lock:
                released = len(pool.pool)
                pool.pool.clear()
                self.optimization_stats["object_pool_saves"] += released

        # Clean up weak references
        cleaned_refs = self.weak_ref_manager.cleanup_dead_references()
        self.optimization_stats["weak_ref_cleanups"] += cleaned_refs

        self.optimization_stats["memory_cleanups"] += 1

        # Log memory alert
        self.memory_alerts.append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": "aggressive_cleanup",
                "details": f"Cleaned {cleaned_refs} refs, cleared object pools",
            }
        )

    async def _moderate_memory_cleanup(self):
        """Moderate memory cleanup for high pressure."""
        logger.info("High memory pressure - performing moderate cleanup")

        # Selective garbage collection
        collected = gc.collect()
        self.gc_stats["moderate_collection"] += collected

        # Trim object pools to 50% capacity
        for pool in self.object_pools.values():
            with pool._lock:
                if len(pool.pool) > pool.max_size // 2:
                    excess = len(pool.pool) - (pool.max_size // 2)
                    for _ in range(excess):
                        pool.pool.pop()
                    self.optimization_stats["object_pool_saves"] += excess

        self.optimization_stats["memory_cleanups"] += 1

    def _light_memory_cleanup(self):
        """Light memory cleanup for moderate pressure."""
        # Just collect generation 0 garbage
        collected = gc.collect(0)
        self.gc_stats["light_collection"] += collected

    def _tune_gc_for_pressure(self, aggressive: bool = False):
        """Tune garbage collection thresholds based on memory pressure."""
        if aggressive:
            # More aggressive GC - lower thresholds
            new_thresholds = tuple(
                int(t / self.gc_threshold_multiplier)
                for t in self.original_gc_thresholds
            )
        else:
            # Moderate GC tuning
            multiplier = (self.gc_threshold_multiplier + 1.0) / 2.0
            new_thresholds = tuple(
                int(t / multiplier) for t in self.original_gc_thresholds
            )

        gc.set_threshold(*new_thresholds)
        self.optimization_stats["gc_optimizations"] += 1

        logger.debug(
            f"GC thresholds adjusted: {self.original_gc_thresholds} -> {new_thresholds}"
        )

    async def _periodic_maintenance(self):
        """Perform periodic maintenance tasks."""
        # Trim memory alerts list
        if len(self.memory_alerts) > 50:
            self.memory_alerts = self.memory_alerts[-25:]

        # Clean up weak references periodically
        if len(self.memory_history) % 10 == 0:  # Every 10 monitoring cycles
            self.weak_ref_manager.cleanup_dead_references()

    def create_object_pool(
        self, name: str, factory: Callable[[], Any], max_size: int = 100
    ) -> ObjectPool:
        """Create and register an object pool."""
        pool = ObjectPool(factory, max_size)
        self.object_pools[name] = pool
        logger.debug(f"Object pool '{name}' created with max_size={max_size}")
        return pool

    def get_object_pool(self, name: str) -> Optional[ObjectPool]:
        """Get existing object pool."""
        return self.object_pools.get(name)

    def register_weak_reference(
        self, key: str, obj: Any, cleanup_callback: Optional[Callable] = None
    ):
        """Register object with weak reference management."""
        self.weak_ref_manager.register(key, obj, cleanup_callback)

    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory optimization report."""
        if not self.memory_history:
            return {"status": "no_data"}

        latest_metrics = self.memory_history[-1]

        # Calculate memory trends
        if len(self.memory_history) >= 2:
            previous_metrics = self.memory_history[-2]
            memory_trend = (
                latest_metrics.memory_percent - previous_metrics.memory_percent
            )
        else:
            memory_trend = 0.0

        # Object pool statistics
        pool_stats = {}
        for name, pool in self.object_pools.items():
            pool_stats[name] = pool.get_stats()

        return {
            "timestamp": latest_metrics.timestamp.isoformat(),
            "current_memory": latest_metrics.to_dict(),
            "memory_trend_percent": memory_trend,
            "memory_pressure": latest_metrics.memory_pressure.value,
            "optimization_stats": self.optimization_stats.copy(),
            "object_pools": pool_stats,
            "weak_references": self.weak_ref_manager.get_stats(),
            "gc_stats": dict(self.gc_stats),
            "memory_alerts": self.memory_alerts[-10:],  # Last 10 alerts
            "monitoring_active": self.monitoring_active,
        }

    def force_memory_optimization(self) -> Dict[str, Any]:
        """Force immediate memory optimization."""
        logger.info("Forcing immediate memory optimization")

        # Get current metrics
        metrics = self._collect_memory_metrics()

        # Perform cleanup based on current pressure
        if metrics.memory_pressure in [
            MemoryPressureLevel.CRITICAL,
            MemoryPressureLevel.HIGH,
        ]:
            # Synchronous aggressive cleanup
            for generation in [2, 1, 0]:
                collected = gc.collect(generation)
                self.gc_stats[f"forced_gen{generation}"] += collected

            # Clear object pools
            total_released = 0
            for pool in self.object_pools.values():
                with pool._lock:
                    released = len(pool.pool)
                    pool.pool.clear()
                    total_released += released

            # Clean weak references
            cleaned_refs = self.weak_ref_manager.cleanup_dead_references()

            self.optimization_stats["memory_cleanups"] += 1

            return {
                "optimization_performed": True,
                "objects_released": total_released,
                "weak_refs_cleaned": cleaned_refs,
                "memory_before": metrics.to_dict(),
            }
        else:
            return {
                "optimization_performed": False,
                "reason": f"Memory pressure is {metrics.memory_pressure.value}, no optimization needed",
            }


# Specialized optimizers for Novel Engine components


class PersonaAgentMemoryOptimizer:
    """
    Specialized memory optimizer for PersonaAgent instances.

    Focuses on optimizing decision history, context caching, and LLM response storage.
    """

    def __init__(self, memory_optimizer: MemoryOptimizer):
        self.memory_optimizer = memory_optimizer

        # Create specialized object pools
        self.decision_pool = memory_optimizer.create_object_pool(
            "persona_decisions",
            lambda: {"turn": 0, "action": "", "reasoning": "", "context": {}},
            max_size=200,
        )

        self.context_pool = memory_optimizer.create_object_pool(
            "persona_contexts",
            lambda: {"agent_id": "", "turn": 0, "state": {}, "history": []},
            max_size=100,
        )

        logger.info("PersonaAgentMemoryOptimizer initialized")

    def optimize_persona_agent(self, agent: Any) -> Dict[str, Any]:
        """Optimize memory usage for a specific PersonaAgent."""
        optimization_results = {
            "agent_id": getattr(agent, "agent_id", "unknown"),
            "optimizations_applied": [],
            "memory_saved_estimate": 0,
        }

        try:
            # Optimize decision history using object pooling
            if hasattr(agent, "decision_history") and len(agent.decision_history) > 100:
                # Keep only recent decisions, pool the rest
                recent_decisions = agent.decision_history[-50:]
                old_decisions = agent.decision_history[:-50]

                # Return old decisions to pool
                for decision in old_decisions:
                    if isinstance(decision, dict):
                        # Reset and return to pool
                        decision.clear()
                        self.decision_pool.release(decision)

                agent.decision_history = recent_decisions
                optimization_results["optimizations_applied"].append(
                    "decision_history_pooling"
                )
                optimization_results["memory_saved_estimate"] += (
                    len(old_decisions) * 1024
                )  # Rough estimate

            # Optimize context history
            if hasattr(agent, "context_history") and len(agent.context_history) > 50:
                old_contexts = agent.context_history[:-25]
                agent.context_history = agent.context_history[-25:]

                for context in old_contexts:
                    if isinstance(context, dict):
                        context.clear()
                        self.context_pool.release(context)

                optimization_results["optimizations_applied"].append(
                    "context_history_pooling"
                )
                optimization_results["memory_saved_estimate"] += len(old_contexts) * 512

            # Register agent with weak reference for lifecycle management
            agent_key = f"persona_agent_{optimization_results['agent_id']}"
            self.memory_optimizer.register_weak_reference(
                agent_key,
                agent,
                lambda: logger.debug(
                    f"PersonaAgent {optimization_results['agent_id']} garbage collected"
                ),
            )
            optimization_results["optimizations_applied"].append(
                "weak_reference_registration"
            )

        except Exception as e:
            logger.error(f"PersonaAgent optimization failed: {e}")
            optimization_results["error"] = str(e)

        return optimization_results


class DirectorAgentMemoryOptimizer:
    """
    Specialized memory optimizer for DirectorAgent instances.

    Focuses on world state caching, agent coordination data, and turn management.
    """

    def __init__(self, memory_optimizer: MemoryOptimizer):
        self.memory_optimizer = memory_optimizer

        # Create specialized object pools
        self.world_state_pool = memory_optimizer.create_object_pool(
            "world_states",
            lambda: {"turn": 0, "agents": {}, "discoveries": {}, "interactions": {}},
            max_size=50,
        )

        self.coordination_pool = memory_optimizer.create_object_pool(
            "coordination_data",
            lambda: {
                "requesting_agent": "",
                "target_agents": [],
                "coordination_type": "",
                "data": {},
            },
            max_size=100,
        )

        logger.info("DirectorAgentMemoryOptimizer initialized")

    def optimize_director_agent(self, director: Any) -> Dict[str, Any]:
        """Optimize memory usage for DirectorAgent."""
        optimization_results = {"optimizations_applied": [], "memory_saved_estimate": 0}

        try:
            # Optimize world state history
            if hasattr(director, "world_state_history"):
                world_states = getattr(director, "world_state_history", {})
                if isinstance(world_states, dict) and len(world_states) > 20:
                    # Keep only recent world states
                    sorted_turns = sorted(world_states.keys())
                    old_turns = sorted_turns[:-10]  # Keep last 10 turns

                    for turn in old_turns:
                        old_state = world_states.pop(turn, None)
                        if isinstance(old_state, dict):
                            old_state.clear()
                            self.world_state_pool.release(old_state)

                    optimization_results["optimizations_applied"].append(
                        "world_state_pooling"
                    )
                    optimization_results["memory_saved_estimate"] += (
                        len(old_turns) * 2048
                    )

            # Optimize agent coordination data
            if hasattr(director, "coordination_cache"):
                coord_cache = getattr(director, "coordination_cache", {})
                if isinstance(coord_cache, dict) and len(coord_cache) > 50:
                    # Clear old coordination data
                    items_to_remove = list(coord_cache.keys())[:-25]  # Keep last 25
                    for key in items_to_remove:
                        old_coord = coord_cache.pop(key, None)
                        if isinstance(old_coord, dict):
                            old_coord.clear()
                            self.coordination_pool.release(old_coord)

                    optimization_results["optimizations_applied"].append(
                        "coordination_cache_pooling"
                    )
                    optimization_results["memory_saved_estimate"] += (
                        len(items_to_remove) * 1024
                    )

        except Exception as e:
            logger.error(f"DirectorAgent optimization failed: {e}")
            optimization_results["error"] = str(e)

        return optimization_results


# Global memory optimizer instance
_global_memory_optimizer: Optional[MemoryOptimizer] = None
_persona_optimizer: Optional[PersonaAgentMemoryOptimizer] = None
_director_optimizer: Optional[DirectorAgentMemoryOptimizer] = None


async def get_memory_optimizer() -> MemoryOptimizer:
    """Get or create global memory optimizer."""
    global _global_memory_optimizer
    if _global_memory_optimizer is None:
        _global_memory_optimizer = MemoryOptimizer()
        await _global_memory_optimizer.start_monitoring()
    return _global_memory_optimizer


def get_persona_agent_optimizer() -> PersonaAgentMemoryOptimizer:
    """Get or create PersonaAgent memory optimizer."""
    global _persona_optimizer, _global_memory_optimizer
    if _persona_optimizer is None:
        if _global_memory_optimizer is None:
            # Create synchronously for backward compatibility
            _global_memory_optimizer = MemoryOptimizer()
        _persona_optimizer = PersonaAgentMemoryOptimizer(_global_memory_optimizer)
    return _persona_optimizer


def get_director_agent_optimizer() -> DirectorAgentMemoryOptimizer:
    """Get or create DirectorAgent memory optimizer."""
    global _director_optimizer, _global_memory_optimizer
    if _director_optimizer is None:
        if _global_memory_optimizer is None:
            _global_memory_optimizer = MemoryOptimizer()
        _director_optimizer = DirectorAgentMemoryOptimizer(_global_memory_optimizer)
    return _director_optimizer


async def setup_memory_optimization() -> Dict[str, Any]:
    """Setup comprehensive memory optimization system."""
    memory_optimizer = await get_memory_optimizer()
    persona_optimizer = get_persona_agent_optimizer()
    director_optimizer = get_director_agent_optimizer()

    logger.info("Memory optimization system setup completed")

    return {
        "memory_optimizer": memory_optimizer,
        "persona_optimizer": persona_optimizer,
        "director_optimizer": director_optimizer,
        "status": "active",
    }


async def get_comprehensive_memory_optimization_report() -> Dict[str, Any]:
    """Get comprehensive memory optimization report."""
    report = {"timestamp": datetime.now().isoformat(), "status": "active"}

    if _global_memory_optimizer:
        report["memory_optimizer"] = _global_memory_optimizer.get_memory_report()

    # System-wide memory info
    memory = psutil.virtual_memory()
    process = psutil.Process()
    process_memory = process.memory_info()

    report["system_memory"] = {
        "total_gb": memory.total / 1024 / 1024 / 1024,
        "available_gb": memory.available / 1024 / 1024 / 1024,
        "used_percent": memory.percent,
        "process_memory_mb": process_memory.rss / 1024 / 1024,
    }

    # GC statistics
    report["garbage_collection"] = {
        "counts": gc.get_count(),
        "thresholds": gc.get_threshold(),
        "total_objects": len(gc.get_objects()),
    }

    return report


async def cleanup_memory_optimization():
    """Cleanup memory optimization system."""
    global _global_memory_optimizer, _persona_optimizer, _director_optimizer

    if _global_memory_optimizer:
        await _global_memory_optimizer.stop_monitoring()
        _global_memory_optimizer = None

    _persona_optimizer = None
    _director_optimizer = None

    logger.info("Memory optimization cleanup completed")


@asynccontextmanager
async def memory_optimization_context():
    """Context manager for memory optimization setup and cleanup."""
    try:
        setup_result = await setup_memory_optimization()
        yield setup_result
    finally:
        await cleanup_memory_optimization()
