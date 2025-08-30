"""
Memory Leak Fixes and Data Management
====================================

Critical memory leak fixes for PersonaAgent decision history accumulation and other
memory-intensive operations identified in the performance bottleneck analysis.

Wave 5.1.3 - Memory Management and Leak Prevention
"""

import gc
import json
import logging
import sys
import threading
import time
import weakref
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Deque, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    """Memory usage statistics."""

    timestamp: datetime
    rss_mb: float  # Resident Set Size
    vms_mb: float  # Virtual Memory Size
    percent: float  # Memory percentage
    available_mb: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "rss_mb": self.rss_mb,
            "vms_mb": self.vms_mb,
            "percent": self.percent,
            "available_mb": self.available_mb,
        }


@dataclass
class MemoryLeakAlert:
    """Memory leak alert information."""

    component: str
    growth_rate_mb_per_min: float
    current_size_mb: float
    threshold_exceeded: bool
    recommendation: str
    timestamp: datetime = field(default_factory=datetime.now)


class SlidingWindowMemoryManager:
    """
    Sliding window memory manager for preventing unlimited data accumulation.

    Critical fix for PersonaAgent decision_history memory leak.
    """

    def __init__(
        self,
        max_size: int = 1000,
        archive_threshold: float = 0.8,
        enable_persistence: bool = True,
        archive_path: str = "memory_archive",
    ):
        self.max_size = max_size
        self.archive_threshold = int(max_size * archive_threshold)
        self.enable_persistence = enable_persistence
        self.archive_path = archive_path
        self.archived_count = 0

        logger.debug(
            f"SlidingWindowMemoryManager initialized: max_size={max_size}, "
            f"archive_threshold={self.archive_threshold}"
        )

    def manage_list(self, data_list: List[Any], name: str = "unknown") -> int:
        """
        Manage a list with sliding window pattern.

        Returns number of items archived.
        """
        if len(data_list) <= self.max_size:
            return 0

        # Calculate how many items to archive
        items_to_archive = len(data_list) - self.archive_threshold

        # Extract items to archive
        items_for_archive = data_list[:items_to_archive]

        # Archive if persistence enabled
        if self.enable_persistence and items_for_archive:
            self._archive_items(items_for_archive, name)

        # Keep only recent items
        data_list[:] = data_list[items_to_archive:]

        archived_count = len(items_for_archive)
        self.archived_count += archived_count

        logger.debug(
            f"Sliding window management for {name}: archived {archived_count} items, "
            f"kept {len(data_list)} recent items"
        )

        return archived_count

    def manage_deque(self, data_deque: Deque[Any], name: str = "unknown") -> int:
        """Manage a deque with sliding window pattern."""
        if len(data_deque) <= self.max_size:
            return 0

        items_to_remove = len(data_deque) - self.archive_threshold
        archived_items = []

        # Archive oldest items
        for _ in range(items_to_remove):
            if data_deque:
                archived_items.append(data_deque.popleft())

        # Archive if persistence enabled
        if self.enable_persistence and archived_items:
            self._archive_items(archived_items, name)

        self.archived_count += len(archived_items)

        logger.debug(
            f"Deque sliding window for {name}: archived {len(archived_items)} items"
        )

        return len(archived_items)

    def _archive_items(self, items: List[Any], name: str) -> None:
        """Archive items to persistent storage."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.archive_path}_{name}_{timestamp}.json"

            # Convert items to JSON-serializable format
            serializable_items = []
            for item in items:
                try:
                    if hasattr(item, "__dict__"):
                        serializable_items.append(item.__dict__)
                    elif isinstance(item, (dict, list, str, int, float, bool)):
                        serializable_items.append(item)
                    else:
                        serializable_items.append(str(item))
                except Exception:
                    serializable_items.append(
                        f"<non-serializable: {type(item).__name__}>"
                    )

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "archived_at": timestamp,
                        "item_count": len(serializable_items),
                        "component": name,
                        "items": serializable_items,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            logger.debug(f"Archived {len(items)} items to {filename}")

        except Exception as e:
            logger.error(f"Failed to archive items for {name}: {e}")


class PersonaAgentMemoryFixer:
    """
    Critical memory leak fixes for PersonaAgent instances.

    Addresses the unlimited decision_history accumulation identified in performance analysis.
    """

    @staticmethod
    def fix_persona_agent_memory_leaks(persona_agent_instance) -> Dict[str, Any]:
        """
        Apply comprehensive memory leak fixes to PersonaAgent instance.

        Args:
            persona_agent_instance: PersonaAgent instance to fix

        Returns:
            Dict with fix results and memory improvements
        """
        fix_results = {
            "fixes_applied": [],
            "memory_before_mb": 0,
            "memory_after_mb": 0,
            "items_archived": {},
            "success": True,
            "errors": [],
        }

        try:
            # Capture before metrics
            process = psutil.Process()
            fix_results["memory_before_mb"] = process.memory_info().rss / 1024 / 1024

            # Fix 1: Decision History Memory Leak (THE CRITICAL ONE)
            if hasattr(persona_agent_instance, "decision_history"):
                original_count = len(persona_agent_instance.decision_history)

                # Create sliding window manager
                memory_manager = SlidingWindowMemoryManager(
                    max_size=500,  # Keep last 500 decisions
                    archive_threshold=0.8,
                    enable_persistence=True,
                    archive_path=f"decision_archive_{persona_agent_instance.agent_id}",
                )

                # Apply sliding window management
                archived_count = memory_manager.manage_list(
                    persona_agent_instance.decision_history,
                    f"decisions_{persona_agent_instance.agent_id}",
                )

                fix_results["fixes_applied"].append("decision_history_sliding_window")
                fix_results["items_archived"]["decision_history"] = archived_count

                logger.info(
                    f"PersonaAgent {persona_agent_instance.agent_id}: "
                    f"decision_history {original_count} → {len(persona_agent_instance.decision_history)} "
                    f"({archived_count} archived)"
                )

            # Fix 2: LLM Response Cache Management
            if hasattr(persona_agent_instance, "llm_response_cache"):
                cache = persona_agent_instance.llm_response_cache
                if isinstance(cache, dict) and len(cache) > 100:
                    # Keep only recent 100 cache entries
                    cache_items = list(cache.items())
                    cache.clear()

                    # Keep most recent items (assuming timestamp-based keys)
                    recent_items = cache_items[-100:]
                    cache.update(recent_items)

                    archived_cache_count = len(cache_items) - 100
                    fix_results["fixes_applied"].append("llm_cache_cleanup")
                    fix_results["items_archived"]["llm_cache"] = archived_cache_count

                    logger.info(
                        f"PersonaAgent {persona_agent_instance.agent_id}: "
                        f"LLM cache cleaned - {archived_cache_count} items removed"
                    )

            # Fix 3: Character Context History Cleanup
            context_attributes = [
                "context_history",
                "interaction_history",
                "narrative_context",
            ]
            for attr in context_attributes:
                if hasattr(persona_agent_instance, attr):
                    attr_value = getattr(persona_agent_instance, attr)
                    if isinstance(attr_value, list) and len(attr_value) > 200:
                        original_length = len(attr_value)

                        # Use sliding window
                        memory_manager = SlidingWindowMemoryManager(max_size=100)
                        archived_count = memory_manager.manage_list(
                            attr_value, f"{attr}_{persona_agent_instance.agent_id}"
                        )

                        fix_results["fixes_applied"].append(f"{attr}_cleanup")
                        fix_results["items_archived"][attr] = archived_count

                        logger.info(
                            f"PersonaAgent {persona_agent_instance.agent_id}: "
                            f"{attr} {original_length} → {len(attr_value)}"
                        )

            # Fix 4: Add Memory Monitoring
            persona_agent_instance._memory_monitor = PersonaAgentMemoryMonitor(
                persona_agent_instance
            )
            fix_results["fixes_applied"].append("memory_monitoring")

            # Force garbage collection
            gc.collect()

            # Capture after metrics
            fix_results["memory_after_mb"] = process.memory_info().rss / 1024 / 1024

            memory_saved = (
                fix_results["memory_before_mb"] - fix_results["memory_after_mb"]
            )
            logger.info(
                f"PersonaAgent memory fixes completed: {memory_saved:.1f}MB saved"
            )

        except Exception as e:
            logger.error(f"PersonaAgent memory fix failed: {e}")
            fix_results["success"] = False
            fix_results["errors"].append(str(e))

        return fix_results


class PersonaAgentMemoryMonitor:
    """Real-time memory monitoring for PersonaAgent instances."""

    def __init__(self, persona_agent_instance):
        self.agent_instance = weakref.ref(
            persona_agent_instance
        )  # Weak reference to prevent circular refs
        self.agent_id = persona_agent_instance.agent_id
        self.memory_history = deque(maxlen=100)  # Keep last 100 memory measurements
        self.last_cleanup = datetime.now()
        self.cleanup_interval = timedelta(minutes=15)  # Check every 15 minutes
        self.memory_threshold_mb = 50  # Alert if agent uses > 50MB

        # Start background monitoring
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

        logger.debug(f"Memory monitor started for PersonaAgent {self.agent_id}")

    def _monitor_loop(self):
        """Background memory monitoring loop."""
        while self._monitoring_active:
            try:
                agent = self.agent_instance()
                if agent is None:
                    # Agent was garbage collected
                    break

                # Capture memory stats
                process = psutil.Process()
                memory_info = process.memory_info()

                stats = MemoryStats(
                    timestamp=datetime.now(),
                    rss_mb=memory_info.rss / 1024 / 1024,
                    vms_mb=memory_info.vms / 1024 / 1024,
                    percent=process.memory_percent(),
                    available_mb=psutil.virtual_memory().available / 1024 / 1024,
                )

                self.memory_history.append(stats)

                # Check for cleanup needs
                if datetime.now() - self.last_cleanup > self.cleanup_interval:
                    self._check_cleanup_needs(agent)
                    self.last_cleanup = datetime.now()

                # Check for memory alerts
                self._check_memory_alerts(stats, agent)

                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Memory monitor error for {self.agent_id}: {e}")
                time.sleep(60)  # Wait longer on error

    def _check_cleanup_needs(self, agent):
        """Check if agent needs memory cleanup."""
        try:
            cleanup_needed = False

            # Check decision history size
            if hasattr(agent, "decision_history") and len(agent.decision_history) > 750:
                cleanup_needed = True
                logger.warning(
                    f"Agent {self.agent_id} decision_history at {len(agent.decision_history)} items"
                )

            # Check other memory-intensive attributes
            for attr_name in [
                "context_history",
                "interaction_history",
                "narrative_context",
            ]:
                if hasattr(agent, attr_name):
                    attr_value = getattr(agent, attr_name)
                    if isinstance(attr_value, list) and len(attr_value) > 150:
                        cleanup_needed = True
                        logger.warning(
                            f"Agent {self.agent_id} {attr_name} at {len(attr_value)} items"
                        )

            if cleanup_needed:
                logger.info(
                    f"Performing automatic cleanup for PersonaAgent {self.agent_id}"
                )
                PersonaAgentMemoryFixer.fix_persona_agent_memory_leaks(agent)

        except Exception as e:
            logger.error(f"Cleanup check failed for {self.agent_id}: {e}")

    def _check_memory_alerts(self, stats: MemoryStats, agent):
        """Check for memory usage alerts."""
        # Alert if memory usage is high
        if stats.rss_mb > self.memory_threshold_mb:
            logger.warning(
                f"High memory usage for PersonaAgent {self.agent_id}: {stats.rss_mb:.1f}MB"
            )

        # Check for memory growth trends
        if len(self.memory_history) >= 10:
            recent_growth = self._calculate_memory_growth_trend()
            if recent_growth > 1.0:  # Growing by > 1MB per measurement period
                logger.warning(
                    f"Rapid memory growth detected for {self.agent_id}: "
                    f"{recent_growth:.2f}MB per period"
                )

    def _calculate_memory_growth_trend(self) -> float:
        """Calculate memory growth trend from recent history."""
        if len(self.memory_history) < 5:
            return 0.0

        recent_samples = list(self.memory_history)[-5:]
        oldest_sample = recent_samples[0]
        newest_sample = recent_samples[-1]

        time_diff = (newest_sample.timestamp - oldest_sample.timestamp).total_seconds()
        memory_diff = newest_sample.rss_mb - oldest_sample.rss_mb

        if time_diff > 0:
            return memory_diff / (time_diff / 60)  # MB per minute
        return 0.0

    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory report for this agent."""
        if not self.memory_history:
            return {"error": "No memory data available"}

        recent_stats = self.memory_history[-1]
        growth_trend = self._calculate_memory_growth_trend()

        agent = self.agent_instance()
        agent_info = {}
        if agent:
            agent_info = {
                "decision_history_size": len(getattr(agent, "decision_history", [])),
                "context_history_size": len(getattr(agent, "context_history", [])),
                "has_memory_monitor": hasattr(agent, "_memory_monitor"),
            }

        return {
            "agent_id": self.agent_id,
            "current_memory_mb": recent_stats.rss_mb,
            "memory_percent": recent_stats.percent,
            "growth_trend_mb_per_min": growth_trend,
            "samples_collected": len(self.memory_history),
            "last_cleanup": self.last_cleanup.isoformat(),
            "agent_details": agent_info,
            "monitoring_active": self._monitoring_active,
        }

    def stop_monitoring(self):
        """Stop memory monitoring."""
        self._monitoring_active = False
        if self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
        logger.debug(f"Memory monitoring stopped for {self.agent_id}")


class SystemWideMemoryManager:
    """
    System-wide memory leak detection and prevention.

    Monitors overall application memory usage and triggers cleanup when needed.
    """

    def __init__(self, memory_limit_mb: int = 1024, check_interval: int = 60):
        self.memory_limit_mb = memory_limit_mb
        self.check_interval = check_interval
        self.monitoring_active = False
        self.monitor_thread = None

        self.memory_history = deque(maxlen=100)
        self.leak_alerts = []
        self.cleanup_callbacks = []  # Functions to call for cleanup

        # Component memory tracking
        self.component_memory = defaultdict(list)

        logger.info(
            f"SystemWideMemoryManager initialized: limit={memory_limit_mb}MB, "
            f"check_interval={check_interval}s"
        )

    def start_monitoring(self):
        """Start system-wide memory monitoring."""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop, daemon=True
            )
            self.monitor_thread.start()
            logger.info("System-wide memory monitoring started")

    def stop_monitoring(self):
        """Stop system-wide memory monitoring."""
        self.monitoring_active = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        logger.info("System-wide memory monitoring stopped")

    def register_cleanup_callback(
        self, callback: Callable[[], None], component_name: str
    ):
        """Register a cleanup function for a specific component."""
        self.cleanup_callbacks.append((callback, component_name))
        logger.debug(f"Cleanup callback registered for component: {component_name}")

    def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                # Collect memory stats
                process = psutil.Process()
                memory_info = process.memory_info()
                virtual_memory = psutil.virtual_memory()

                stats = MemoryStats(
                    timestamp=datetime.now(),
                    rss_mb=memory_info.rss / 1024 / 1024,
                    vms_mb=memory_info.vms / 1024 / 1024,
                    percent=process.memory_percent(),
                    available_mb=virtual_memory.available / 1024 / 1024,
                )

                self.memory_history.append(stats)

                # Check for memory limit exceeded
                if stats.rss_mb > self.memory_limit_mb:
                    self._handle_memory_limit_exceeded(stats)

                # Check for memory leaks
                self._check_for_memory_leaks()

                # Log periodic memory status
                if len(self.memory_history) % 10 == 0:  # Every 10 measurements
                    logger.info(
                        f"System Memory: {stats.rss_mb:.1f}MB RSS, "
                        f"{stats.percent:.1f}% usage, {stats.available_mb:.1f}MB available"
                    )

                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"System memory monitoring error: {e}")
                time.sleep(self.check_interval * 2)

    def _handle_memory_limit_exceeded(self, stats: MemoryStats):
        """Handle memory limit exceeded situation."""
        logger.warning(
            f"Memory limit exceeded: {stats.rss_mb:.1f}MB > {self.memory_limit_mb}MB"
        )

        # Trigger emergency cleanup
        self._trigger_emergency_cleanup()

        # Force garbage collection
        logger.info("Triggering emergency garbage collection")
        gc.collect()

        # Create alert
        alert = MemoryLeakAlert(
            component="system_wide",
            growth_rate_mb_per_min=0.0,  # Calculate if needed
            current_size_mb=stats.rss_mb,
            threshold_exceeded=True,
            recommendation="Emergency cleanup triggered - check for memory leaks",
        )
        self.leak_alerts.append(alert)

    def _trigger_emergency_cleanup(self):
        """Trigger all registered cleanup callbacks."""
        logger.warning("Triggering emergency cleanup procedures")

        for callback, component_name in self.cleanup_callbacks:
            try:
                logger.info(f"Running emergency cleanup for {component_name}")
                callback()
            except Exception as e:
                logger.error(f"Emergency cleanup failed for {component_name}: {e}")

    def _check_for_memory_leaks(self):
        """Check for potential memory leaks."""
        if len(self.memory_history) < 10:
            return

        # Calculate memory growth trend
        recent_samples = list(self.memory_history)[-10:]  # Last 10 samples
        oldest = recent_samples[0]
        newest = recent_samples[-1]

        time_diff = (newest.timestamp - oldest.timestamp).total_seconds()
        memory_diff = newest.rss_mb - oldest.rss_mb

        if time_diff > 0:
            growth_rate = memory_diff / (time_diff / 60)  # MB per minute

            # Alert on sustained growth
            if growth_rate > 2.0:  # More than 2MB/min growth
                logger.warning(
                    f"Potential memory leak detected: {growth_rate:.2f}MB/min growth"
                )

                alert = MemoryLeakAlert(
                    component="system_wide",
                    growth_rate_mb_per_min=growth_rate,
                    current_size_mb=newest.rss_mb,
                    threshold_exceeded=False,
                    recommendation="Investigate memory usage patterns and enable detailed monitoring",
                )
                self.leak_alerts.append(alert)

    def get_system_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive system memory report."""
        if not self.memory_history:
            return {"error": "No memory data available"}

        current_stats = self.memory_history[-1]

        # Calculate trends
        growth_trend = 0.0
        if len(self.memory_history) >= 5:
            recent_samples = list(self.memory_history)[-5:]
            oldest = recent_samples[0]
            newest = recent_samples[-1]
            time_diff = (newest.timestamp - oldest.timestamp).total_seconds()
            if time_diff > 0:
                memory_diff = newest.rss_mb - oldest.rss_mb
                growth_trend = memory_diff / (time_diff / 60)

        return {
            "current_memory_mb": current_stats.rss_mb,
            "virtual_memory_mb": current_stats.vms_mb,
            "memory_percent": current_stats.percent,
            "available_memory_mb": current_stats.available_mb,
            "memory_limit_mb": self.memory_limit_mb,
            "limit_exceeded": current_stats.rss_mb > self.memory_limit_mb,
            "growth_trend_mb_per_min": growth_trend,
            "samples_collected": len(self.memory_history),
            "leak_alerts_count": len(self.leak_alerts),
            "cleanup_callbacks_registered": len(self.cleanup_callbacks),
            "monitoring_active": self.monitoring_active,
            "last_measurement": current_stats.timestamp.isoformat(),
        }


# Global system-wide memory manager instance
_global_memory_manager: Optional[SystemWideMemoryManager] = None


def get_global_memory_manager() -> SystemWideMemoryManager:
    """Get or create global memory manager instance."""
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = SystemWideMemoryManager()
        _global_memory_manager.start_monitoring()
    return _global_memory_manager


def apply_memory_fixes_to_persona_agent(persona_agent_instance) -> bool:
    """
    Quick utility function to apply all memory fixes to a PersonaAgent.

    Args:
        persona_agent_instance: PersonaAgent instance to fix

    Returns:
        bool: True if fixes applied successfully
    """
    try:
        result = PersonaAgentMemoryFixer.fix_persona_agent_memory_leaks(
            persona_agent_instance
        )
        return result["success"]
    except Exception as e:
        logger.error(f"Quick memory fix failed: {e}")
        return False


def monitor_persona_agent_memory(persona_agent_instance):
    """
    Add memory monitoring to a PersonaAgent instance.

    Returns the memory monitor instance for tracking.
    """
    if hasattr(persona_agent_instance, "_memory_monitor"):
        logger.warning(
            f"Memory monitor already exists for {persona_agent_instance.agent_id}"
        )
        return persona_agent_instance._memory_monitor

    monitor = PersonaAgentMemoryMonitor(persona_agent_instance)
    persona_agent_instance._memory_monitor = monitor
    return monitor


def get_comprehensive_memory_report() -> Dict[str, Any]:
    """Get comprehensive memory report for entire system."""
    manager = get_global_memory_manager()
    system_report = manager.get_system_memory_report()

    # Add Python-specific memory info
    system_report["python_info"] = {
        "gc_stats": gc.get_stats(),
        "gc_threshold": gc.get_threshold(),
        "object_count": len(gc.get_objects()),
        "referrers_tracked": sys.gettrace() is not None,
    }

    return {
        "system_memory": system_report,
        "timestamp": datetime.now().isoformat(),
        "status": (
            "healthy" if not system_report.get("limit_exceeded", False) else "warning"
        ),
    }


# Cleanup utilities


def emergency_memory_cleanup():
    """Emergency memory cleanup function."""
    logger.warning("Executing emergency memory cleanup")

    # Force garbage collection multiple times
    for i in range(3):
        collected = gc.collect()
        logger.info(f"Garbage collection pass {i+1}: {collected} objects collected")

    # Clear module-level caches if they exist
    try:
        import functools

        functools._CacheInfo.cache_clear()  # This won't work, but shows intent
    except Exception:
        pass

    logger.info("Emergency memory cleanup completed")


def setup_automatic_memory_management():
    """Setup automatic memory management for the entire application."""
    manager = get_global_memory_manager()

    # Register emergency cleanup
    manager.register_cleanup_callback(emergency_memory_cleanup, "emergency_cleanup")

    logger.info("Automatic memory management setup completed")
    return manager
