#!/usr/bin/env python3
"""
Comprehensive Performance Monitoring and Metrics System for Novel Engine - Iteration 2.

This module implements advanced performance monitoring, real-time metrics collection,
dashboard capabilities, alerting system, and performance regression detection.
"""

import asyncio
import gc
import json
import logging
import os
import sqlite3
import statistics
import threading
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import aiosqlite
import psutil

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics collected."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """A single metric data point."""

    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class PerformanceThreshold:
    """Performance threshold for alerting."""

    metric_name: str
    operator: str  # '>', '<', '>=', '<=', '==', '!='
    threshold_value: float
    alert_level: AlertLevel
    enabled: bool = True
    consecutive_violations: int = 1
    description: str = ""


@dataclass
class PerformanceAlert:
    """Performance alert notification."""

    id: str
    metric_name: str
    current_value: float
    threshold: PerformanceThreshold
    timestamp: float
    level: AlertLevel
    message: str
    acknowledged: bool = False


class MetricsCollector:
    """Collects and aggregates performance metrics."""

    def __init__(self, max_points: int = 10000):
        self.max_points = max_points
        self.metrics = defaultdict(lambda: deque(maxlen=max_points))
        self.counters = defaultdict(float)
        self.histograms = defaultdict(list)
        self.lock = threading.RLock()

    def record_counter(
        self, name: str, value: float = 1.0, tags: Dict[str, str] = None
    ):
        """Record a counter metric."""
        with self.lock:
            self.counters[name] += value
            self._add_metric_point(name, self.counters[name], MetricType.COUNTER, tags)

    def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a gauge metric."""
        with self.lock:
            self._add_metric_point(name, value, MetricType.GAUGE, tags)

    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a histogram metric."""
        with self.lock:
            self.histograms[name].append(value)
            # Keep only last 1000 values for memory efficiency
            if len(self.histograms[name]) > 1000:
                self.histograms[name] = self.histograms[name][-1000:]

            self._add_metric_point(name, value, MetricType.HISTOGRAM, tags)

    def record_timer(self, name: str, duration: float, tags: Dict[str, str] = None):
        """Record a timer metric."""
        with self.lock:
            self._add_metric_point(name, duration, MetricType.TIMER, tags)

    def _add_metric_point(
        self, name: str, value: float, metric_type: MetricType, tags: Dict[str, str]
    ):
        """Add a metric point to the collection."""
        point = MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags or {},
            metric_type=metric_type,
        )
        self.metrics[name].append(point)

    def get_metric_history(
        self, name: str, duration_seconds: int = 3600
    ) -> List[MetricPoint]:
        """Get metric history for the specified duration."""
        with self.lock:
            if name not in self.metrics:
                return []

            cutoff_time = time.time() - duration_seconds
            return [
                point for point in self.metrics[name] if point.timestamp >= cutoff_time
            ]

    def get_current_value(self, name: str) -> Optional[float]:
        """Get the current value of a metric."""
        with self.lock:
            if name not in self.metrics or not self.metrics[name]:
                return None
            return self.metrics[name][-1].value

    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """Get histogram statistics."""
        with self.lock:
            if name not in self.histograms or not self.histograms[name]:
                return {}

            values = self.histograms[name]
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "p95": self._percentile(values, 95),
                "p99": self._percentile(values, 99),
                "stddev": statistics.stdev(values) if len(values) > 1 else 0.0,
            }

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int((percentile / 100.0) * (len(sorted_values) - 1))
        return sorted_values[index]

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all current metrics."""
        with self.lock:
            result = {}
            for name in self.metrics.keys():
                current_value = self.get_current_value(name)
                if current_value is not None:
                    result[name] = current_value

                # Add histogram stats if available
                if name in self.histograms:
                    result[f"{name}_stats"] = self.get_histogram_stats(name)

            return result


class SystemMetricsCollector:
    """Collects system-level performance metrics."""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.process = psutil.Process()
        self.last_cpu_times = None
        self.last_io_counters = None

    def collect_system_metrics(self):
        """Collect comprehensive system metrics."""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            self.collector.record_gauge("system.cpu.usage_percent", cpu_percent)

            # Memory metrics
            memory = psutil.virtual_memory()
            self.collector.record_gauge(
                "system.memory.total_mb", memory.total / 1024 / 1024
            )
            self.collector.record_gauge(
                "system.memory.available_mb", memory.available / 1024 / 1024
            )
            self.collector.record_gauge("system.memory.used_percent", memory.percent)

            # Process-specific metrics
            process_memory = self.process.memory_info()
            self.collector.record_gauge(
                "process.memory.rss_mb", process_memory.rss / 1024 / 1024
            )
            self.collector.record_gauge(
                "process.memory.vms_mb", process_memory.vms / 1024 / 1024
            )

            # Process CPU
            process_cpu = self.process.cpu_percent()
            self.collector.record_gauge("process.cpu.usage_percent", process_cpu)

            # Disk I/O
            io_counters = self.process.io_counters()
            if self.last_io_counters:
                read_rate = (
                    (io_counters.read_bytes - self.last_io_counters.read_bytes)
                    / 1024
                    / 1024
                )
                write_rate = (
                    (io_counters.write_bytes - self.last_io_counters.write_bytes)
                    / 1024
                    / 1024
                )
                self.collector.record_gauge("process.io.read_mb_per_sec", read_rate)
                self.collector.record_gauge("process.io.write_mb_per_sec", write_rate)
            self.last_io_counters = io_counters

            # File descriptors
            num_fds = self.process.num_fds() if hasattr(self.process, "num_fds") else 0
            self.collector.record_gauge("process.file_descriptors", num_fds)

            # Threads
            num_threads = self.process.num_threads()
            self.collector.record_gauge("process.threads", num_threads)

            # Garbage collection
            gc_stats = gc.get_stats()
            for i, stats in enumerate(gc_stats):
                self.collector.record_gauge(
                    f"gc.generation_{i}.collections", stats["collections"]
                )
                self.collector.record_gauge(
                    f"gc.generation_{i}.collected", stats["collected"]
                )
                self.collector.record_gauge(
                    f"gc.generation_{i}.uncollectable", stats["uncollectable"]
                )

        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")


class ApplicationMetricsCollector:
    """Collects application-specific performance metrics."""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.request_start_times = {}

    def start_request(self, request_id: str):
        """Start tracking a request."""
        self.request_start_times[request_id] = time.time()

    def end_request(
        self, request_id: str, status_code: int = 200, endpoint: str = "unknown"
    ):
        """End tracking a request."""
        start_time = self.request_start_times.pop(request_id, None)
        if start_time:
            duration = time.time() - start_time
            self.collector.record_timer(
                "http.request.duration",
                duration,
                {"endpoint": endpoint, "status_code": str(status_code)},
            )
            self.collector.record_counter(
                "http.requests.total",
                1.0,
                {"endpoint": endpoint, "status_code": str(status_code)},
            )

    def record_database_query(
        self, query_type: str, duration: float, success: bool = True
    ):
        """Record database query metrics."""
        self.collector.record_timer(
            "database.query.duration",
            duration,
            {"query_type": query_type, "success": str(success)},
        )
        self.collector.record_counter(
            "database.queries.total",
            1.0,
            {"query_type": query_type, "success": str(success)},
        )

    def record_cache_operation(self, operation: str, hit: bool = True):
        """Record cache operation metrics."""
        self.collector.record_counter(
            "cache.operations.total",
            1.0,
            {"operation": operation, "result": "hit" if hit else "miss"},
        )

    def record_task_execution(
        self, task_type: str, duration: float, success: bool = True
    ):
        """Record task execution metrics."""
        self.collector.record_timer(
            "task.execution.duration",
            duration,
            {"task_type": task_type, "success": str(success)},
        )
        self.collector.record_counter(
            "task.executions.total",
            1.0,
            {"task_type": task_type, "success": str(success)},
        )


class AlertManager:
    """Manages performance alerts and notifications."""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self.thresholds = {}
        self.alerts = {}
        self.violation_counts = defaultdict(int)
        self.alert_callbacks = []

    def add_threshold(self, threshold: PerformanceThreshold):
        """Add a performance threshold."""
        self.thresholds[threshold.metric_name] = threshold
        logger.info(
            f"Added performance threshold: {threshold.metric_name} {threshold.operator} {threshold.threshold_value}"
        )

    def remove_threshold(self, metric_name: str):
        """Remove a performance threshold."""
        self.thresholds.pop(metric_name, None)
        self.violation_counts.pop(metric_name, 0)

    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]):
        """Add a callback for alert notifications."""
        self.alert_callbacks.append(callback)

    def check_thresholds(self):
        """Check all thresholds and generate alerts."""
        for metric_name, threshold in self.thresholds.items():
            if not threshold.enabled:
                continue

            current_value = self.collector.get_current_value(metric_name)
            if current_value is None:
                continue

            violated = self._check_threshold_violation(current_value, threshold)

            if violated:
                self.violation_counts[metric_name] += 1

                if (
                    self.violation_counts[metric_name]
                    >= threshold.consecutive_violations
                ):
                    self._generate_alert(metric_name, current_value, threshold)
            else:
                self.violation_counts[metric_name] = 0

    def _check_threshold_violation(
        self, value: float, threshold: PerformanceThreshold
    ) -> bool:
        """Check if a value violates a threshold."""
        operators = {
            ">": lambda x, y: x > y,
            "<": lambda x, y: x < y,
            ">=": lambda x, y: x >= y,
            "<=": lambda x, y: x <= y,
            "==": lambda x, y: x == y,
            "!=": lambda x, y: x != y,
        }

        op_func = operators.get(threshold.operator)
        if not op_func:
            logger.error(f"Invalid operator: {threshold.operator}")
            return False

        return op_func(value, threshold.threshold_value)

    def _generate_alert(
        self, metric_name: str, current_value: float, threshold: PerformanceThreshold
    ):
        """Generate a performance alert."""
        alert_id = f"{metric_name}_{int(time.time())}"

        alert = PerformanceAlert(
            id=alert_id,
            metric_name=metric_name,
            current_value=current_value,
            threshold=threshold,
            timestamp=time.time(),
            level=threshold.alert_level,
            message=f"{threshold.description or metric_name} violated: {current_value} {threshold.operator} {threshold.threshold_value}",
        )

        self.alerts[alert_id] = alert

        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

        logger.warning(f"Performance alert: {alert.message}")

    def acknowledge_alert(self, alert_id: str):
        """Acknowledge an alert."""
        if alert_id in self.alerts:
            self.alerts[alert_id].acknowledged = True

    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get all active (unacknowledged) alerts."""
        return [alert for alert in self.alerts.values() if not alert.acknowledged]

    def get_alert_history(self, hours: int = 24) -> List[PerformanceAlert]:
        """Get alert history for the specified period."""
        cutoff_time = time.time() - (hours * 3600)
        return [
            alert for alert in self.alerts.values() if alert.timestamp >= cutoff_time
        ]


class PerformanceRegression:
    """Detects performance regressions using statistical analysis."""

    def __init__(self, collector: MetricsCollector, sensitivity: float = 2.0):
        self.collector = collector
        self.sensitivity = sensitivity  # Standard deviations for regression detection
        self.baselines = {}

    def establish_baseline(self, metric_name: str, duration_hours: int = 24):
        """Establish a performance baseline for a metric."""
        history = self.collector.get_metric_history(metric_name, duration_hours * 3600)
        if len(history) < 10:
            logger.warning(f"Insufficient data to establish baseline for {metric_name}")
            return

        values = [point.value for point in history]
        baseline = {
            "mean": statistics.mean(values),
            "stddev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "median": statistics.median(values),
            "p95": self._percentile(values, 95),
            "established_at": time.time(),
            "sample_count": len(values),
        }

        self.baselines[metric_name] = baseline
        logger.info(
            f"Established baseline for {metric_name}: mean={baseline['mean']:.2f}, stddev={baseline['stddev']:.2f}"
        )

    def check_regression(
        self, metric_name: str, current_value: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Check if current metric value indicates a regression."""
        if metric_name not in self.baselines:
            return None

        if current_value is None:
            current_value = self.collector.get_current_value(metric_name)
            if current_value is None:
                return None

        baseline = self.baselines[metric_name]

        # Calculate Z-score
        if baseline["stddev"] > 0:
            z_score = abs(current_value - baseline["mean"]) / baseline["stddev"]
        else:
            z_score = 0.0

        # Check for regression
        is_regression = z_score > self.sensitivity

        # Determine direction
        direction = "increase" if current_value > baseline["mean"] else "decrease"

        return {
            "metric_name": metric_name,
            "current_value": current_value,
            "baseline_mean": baseline["mean"],
            "baseline_stddev": baseline["stddev"],
            "z_score": z_score,
            "is_regression": is_regression,
            "direction": direction,
            "severity": (
                "high"
                if z_score > self.sensitivity * 1.5
                else "medium" if is_regression else "low"
            ),
        }

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int((percentile / 100.0) * (len(sorted_values) - 1))
        return sorted_values[index]


class PerformanceMonitor:
    """Main performance monitoring system."""

    def __init__(self, db_path: str = "data/performance_metrics.db"):
        self.db_path = db_path
        self.collector = MetricsCollector()
        self.system_collector = SystemMetricsCollector(self.collector)
        self.app_collector = ApplicationMetricsCollector(self.collector)
        self.alert_manager = AlertManager(self.collector)
        self.regression_detector = PerformanceRegression(self.collector)

        self.monitoring_active = False
        self.monitoring_task = None
        self.collection_interval = 10  # seconds

        self._init_database()
        self._setup_default_thresholds()

    def _init_database(self):
        """Initialize metrics database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp REAL NOT NULL,
                    tags TEXT,
                    metric_type TEXT
                )
            """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_name_timestamp ON metrics(name, timestamp)"
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    metric_name TEXT NOT NULL,
                    current_value REAL NOT NULL,
                    threshold_value REAL NOT NULL,
                    operator TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    acknowledged BOOLEAN DEFAULT FALSE
                )
            """
            )

    def _setup_default_thresholds(self):
        """Setup default performance thresholds."""
        default_thresholds = [
            PerformanceThreshold(
                metric_name="system.memory.used_percent",
                operator=">",
                threshold_value=90.0,
                alert_level=AlertLevel.WARNING,
                description="System memory usage high",
            ),
            PerformanceThreshold(
                metric_name="process.memory.rss_mb",
                operator=">",
                threshold_value=1000.0,
                alert_level=AlertLevel.WARNING,
                description="Process memory usage high",
            ),
            PerformanceThreshold(
                metric_name="system.cpu.usage_percent",
                operator=">",
                threshold_value=80.0,
                alert_level=AlertLevel.WARNING,
                consecutive_violations=3,
                description="CPU usage consistently high",
            ),
            PerformanceThreshold(
                metric_name="http.request.duration",
                operator=">",
                threshold_value=5.0,
                alert_level=AlertLevel.WARNING,
                description="HTTP request duration high",
            ),
        ]

        for threshold in default_thresholds:
            self.alert_manager.add_threshold(threshold)

    async def start_monitoring(self):
        """Start performance monitoring."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        # Establish baselines for key metrics
        await asyncio.sleep(1)  # Allow initial collection
        key_metrics = [
            "http.request.duration",
            "database.query.duration",
            "process.memory.rss_mb",
            "system.cpu.usage_percent",
        ]

        for metric in key_metrics:
            self.regression_detector.establish_baseline(metric, duration_hours=1)

        logger.info("Performance monitoring started")

    async def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Performance monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                # Collect system metrics
                self.system_collector.collect_system_metrics()

                # Check thresholds
                self.alert_manager.check_thresholds()

                # Check for regressions
                self._check_regressions()

                # Persist metrics to database
                await self._persist_metrics()

                await asyncio.sleep(self.collection_interval)

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(self.collection_interval)

    def _check_regressions(self):
        """Check for performance regressions."""
        for metric_name in self.regression_detector.baselines.keys():
            regression_info = self.regression_detector.check_regression(metric_name)
            if regression_info and regression_info["is_regression"]:
                logger.warning(f"Performance regression detected: {regression_info}")

    async def _persist_metrics(self):
        """Persist current metrics to database."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                # Get recent metrics (last collection interval)
                cutoff_time = time.time() - self.collection_interval

                for metric_name, points in self.collector.metrics.items():
                    recent_points = [p for p in points if p.timestamp >= cutoff_time]

                    for point in recent_points:
                        await conn.execute(
                            """
                            INSERT INTO metrics (name, value, timestamp, tags, metric_type)
                            VALUES (?, ?, ?, ?, ?)
                        """,
                            (
                                point.name,
                                point.value,
                                point.timestamp,
                                json.dumps(point.tags),
                                point.metric_type.value,
                            ),
                        )

                await conn.commit()

        except Exception as e:
            logger.error(f"Error persisting metrics: {e}")

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for performance dashboard."""
        current_metrics = self.collector.get_all_metrics()
        active_alerts = self.alert_manager.get_active_alerts()

        # Get recent performance trends
        trends = {}
        key_metrics = [
            "process.memory.rss_mb",
            "system.cpu.usage_percent",
            "http.request.duration",
        ]

        for metric in key_metrics:
            history = self.collector.get_metric_history(metric, 3600)  # Last hour
            if len(history) >= 2:
                values = [p.value for p in history[-10:]]  # Last 10 points
                trend = (
                    "up"
                    if values[-1] > values[0]
                    else "down" if values[-1] < values[0] else "stable"
                )
                trends[metric] = {
                    "trend": trend,
                    "current": values[-1],
                    "change_percent": (
                        ((values[-1] - values[0]) / values[0] * 100)
                        if values[0] != 0
                        else 0
                    ),
                }

        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": current_metrics,
            "trends": trends,
            "alerts": [asdict(alert) for alert in active_alerts],
            "system_health": self._calculate_system_health(),
        }

    def _calculate_system_health(self) -> Dict[str, Any]:
        """Calculate overall system health score."""
        health_factors = {
            "memory": self.collector.get_current_value("system.memory.used_percent")
            or 0,
            "cpu": self.collector.get_current_value("system.cpu.usage_percent") or 0,
            "process_memory": self.collector.get_current_value("process.memory.rss_mb")
            or 0,
        }

        # Calculate health score (0-100)
        memory_score = max(0, 100 - health_factors["memory"])
        cpu_score = max(0, 100 - health_factors["cpu"])
        process_memory_score = max(
            0, 100 - min(health_factors["process_memory"] / 10, 100)
        )  # Scale by 10MB

        overall_score = (memory_score + cpu_score + process_memory_score) / 3

        if overall_score >= 80:
            status = "healthy"
        elif overall_score >= 60:
            status = "warning"
        else:
            status = "critical"

        return {"score": overall_score, "status": status, "factors": health_factors}


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Context managers and decorators for easy monitoring
class TimerContext:
    """Context manager for timing operations."""

    def __init__(self, metric_name: str, tags: Dict[str, str] = None):
        self.metric_name = metric_name
        self.tags = tags or {}
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            performance_monitor.collector.record_timer(
                self.metric_name, duration, self.tags
            )


def monitor_performance(metric_name: str, tags: Dict[str, str] = None):
    """Decorator for monitoring function performance."""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with TimerContext(metric_name, tags):
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with TimerContext(metric_name, tags):
                return func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


# Setup and initialization functions
async def setup_performance_monitoring():
    """Setup performance monitoring system."""
    await performance_monitor.start_monitoring()
    logger.info("Performance monitoring system initialized")


async def shutdown_performance_monitoring():
    """Shutdown performance monitoring system."""
    await performance_monitor.stop_monitoring()
    logger.info("Performance monitoring system shutdown")


if __name__ == "__main__":
    # Example usage and testing
    async def test_performance_monitoring():
        """Test the performance monitoring system."""
        await setup_performance_monitoring()

        # Simulate some application activity
        for i in range(20):
            # Simulate HTTP requests
            request_id = f"req_{i}"
            performance_monitor.app_collector.start_request(request_id)

            # Simulate some work
            await asyncio.sleep(0.1)

            performance_monitor.app_collector.end_request(request_id, 200, "/api/test")

            # Simulate database queries
            performance_monitor.app_collector.record_database_query("SELECT", 0.05)

            # Simulate cache operations
            performance_monitor.app_collector.record_cache_operation(
                "GET", hit=(i % 3 != 0)
            )

        # Wait for monitoring to collect data
        await asyncio.sleep(15)

        # Get dashboard data
        dashboard = performance_monitor.get_dashboard_data()
        print(f"Dashboard data: {json.dumps(dashboard, indent=2, default=str)}")

        # Test alert functionality
        print("\nActive alerts:")
        for alert in performance_monitor.alert_manager.get_active_alerts():
            print(f"- {alert.level.name}: {alert.message}")

        await shutdown_performance_monitoring()

    # Run the test
    asyncio.run(test_performance_monitoring())
