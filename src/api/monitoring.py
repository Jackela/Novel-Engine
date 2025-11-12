#!/usr/bin/env python3
"""
Comprehensive Monitoring and Metrics Collection System.

Provides performance monitoring, metrics collection, and observability
for production API operations with detailed analytics and alerting.
"""

import json
import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics collected."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """Individual metric data point."""

    name: str
    type: MetricType
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary format."""
        return {
            "name": self.name,
            "type": self.type.value,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
        }


@dataclass
class RequestMetrics:
    """Metrics for individual request."""

    request_id: str
    method: str
    path: str
    status_code: int
    duration_ms: float
    timestamp: datetime
    user_agent: Optional[str] = None
    client_ip: Optional[str] = None
    api_version: Optional[str] = None
    error_type: Optional[str] = None


@dataclass
class AlertRule:
    """Alert rule configuration."""

    name: str
    metric_name: str
    threshold: float
    comparison: str  # ">", "<", ">=", "<=", "==", "!="
    level: AlertLevel
    window_minutes: int = 5
    min_samples: int = 1
    enabled: bool = True


class MetricsCollector:
    """Thread-safe metrics collection system."""

    def __init__(self, max_metrics_history: int = 10000):
        self.metrics: deque = deque(maxlen=max_metrics_history)
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        # Use a re-entrant lock to avoid deadlocks when helper methods that also
        # acquire the lock (e.g., record_metric via record_timer) are called
        # from within other locked sections like end_request_timer.
        self._lock = threading.RLock()

        # Request tracking
        self.requests: deque = deque(maxlen=1000)
        self.active_requests: Dict[str, float] = {}

        # Performance tracking
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "count": 0,
                "total_time": 0.0,
                "avg_time": 0.0,
                "min_time": float("inf"),
                "max_time": 0.0,
                "error_count": 0,
                "error_rate": 0.0,
            }
        )

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType,
        labels: Optional[Dict[str, str]] = None,
    ):
        """Record a metric with thread safety."""
        labels = labels or {}
        metric = Metric(
            name=name,
            type=metric_type,
            value=value,
            timestamp=datetime.now(),
            labels=labels,
        )

        with self._lock:
            self.metrics.append(metric)

            if metric_type == MetricType.COUNTER:
                key = f"{name}_{json.dumps(labels, sort_keys=True)}"
                self.counters[key] += value
            elif metric_type == MetricType.GAUGE:
                key = f"{name}_{json.dumps(labels, sort_keys=True)}"
                self.gauges[key] = value
            elif metric_type == MetricType.HISTOGRAM:
                self.histograms[name].append(value)
                # Keep only recent values
                if len(self.histograms[name]) > 1000:
                    self.histograms[name] = self.histograms[name][-1000:]
            elif metric_type == MetricType.TIMER:
                self.timers[name].append(value)
                # Keep only recent values
                if len(self.timers[name]) > 1000:
                    self.timers[name] = self.timers[name][-1000:]

    def increment_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ):
        """Increment a counter metric."""
        self.record_metric(name, value, MetricType.COUNTER, labels)

    def set_gauge(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ):
        """Set a gauge metric."""
        self.record_metric(name, value, MetricType.GAUGE, labels)

    def record_histogram(
        self, name: str, value: float, labels: Optional[Dict[str, str]] = None
    ):
        """Record a histogram value."""
        self.record_metric(name, value, MetricType.HISTOGRAM, labels)

    def record_timer(
        self, name: str, duration_ms: float, labels: Optional[Dict[str, str]] = None
    ):
        """Record a timer value."""
        self.record_metric(name, duration_ms, MetricType.TIMER, labels)

    def start_request_timer(self, request_id: str):
        """Start timing a request."""
        with self._lock:
            self.active_requests[request_id] = time.time()

    def end_request_timer(self, request_id: str, request_metrics: RequestMetrics):
        """End timing a request and record metrics."""
        with self._lock:
            if request_id in self.active_requests:
                del self.active_requests[request_id]

            # Store request metrics
            self.requests.append(request_metrics)

            # Update endpoint statistics
            endpoint_key = f"{request_metrics.method} {request_metrics.path}"
            stats = self.endpoint_stats[endpoint_key]
            stats["count"] += 1
            stats["total_time"] += request_metrics.duration_ms
            stats["avg_time"] = stats["total_time"] / stats["count"]
            stats["min_time"] = min(stats["min_time"], request_metrics.duration_ms)
            stats["max_time"] = max(stats["max_time"], request_metrics.duration_ms)

            if request_metrics.status_code >= 400:
                stats["error_count"] += 1
            stats["error_rate"] = (stats["error_count"] / stats["count"]) * 100

            # Record metrics
            self.record_timer(
                "request_duration",
                request_metrics.duration_ms,
                {
                    "method": request_metrics.method,
                    "endpoint": request_metrics.path,
                    "status_code": str(request_metrics.status_code),
                },
            )

            self.increment_counter(
                "requests_total",
                1.0,
                {
                    "method": request_metrics.method,
                    "endpoint": request_metrics.path,
                    "status_code": str(request_metrics.status_code),
                },
            )

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all collected metrics."""
        with self._lock:
            current_time = datetime.now()
            recent_requests = [
                r
                for r in self.requests
                if (current_time - r.timestamp).total_seconds() < 300  # Last 5 minutes
            ]

            return {
                "timestamp": current_time.isoformat(),
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {
                    name: {
                        "count": len(values),
                        "min": min(values) if values else 0,
                        "max": max(values) if values else 0,
                        "avg": sum(values) / len(values) if values else 0,
                    }
                    for name, values in self.histograms.items()
                },
                "timers": {
                    name: {
                        "count": len(values),
                        "min": min(values) if values else 0,
                        "max": max(values) if values else 0,
                        "avg": sum(values) / len(values) if values else 0,
                        "p95": self._percentile(values, 95) if values else 0,
                        "p99": self._percentile(values, 99) if values else 0,
                    }
                    for name, values in self.timers.items()
                },
                "recent_requests": {
                    "total": len(recent_requests),
                    "avg_duration": (
                        sum(r.duration_ms for r in recent_requests)
                        / len(recent_requests)
                        if recent_requests
                        else 0
                    ),
                    "error_rate": (
                        (
                            len([r for r in recent_requests if r.status_code >= 400])
                            / len(recent_requests)
                            * 100
                        )
                        if recent_requests
                        else 0
                    ),
                },
                "endpoint_stats": dict(self.endpoint_stats),
                "active_requests": len(self.active_requests),
            }

    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * percentile / 100
        f = int(k)
        c = k - f
        if f == len(sorted_values) - 1:
            return sorted_values[f]
        return sorted_values[f] * (1 - c) + sorted_values[f + 1] * c


class AlertManager:
    """Alert management system."""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self.alert_rules: List[AlertRule] = []
        self.active_alerts: Dict[str, datetime] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self._setup_default_alerts()

    def _setup_default_alerts(self):
        """Setup default alert rules."""
        default_rules = [
            AlertRule(
                name="High Error Rate",
                metric_name="error_rate",
                threshold=10.0,
                comparison=">",
                level=AlertLevel.WARNING,
                window_minutes=5,
            ),
            AlertRule(
                name="Critical Error Rate",
                metric_name="error_rate",
                threshold=25.0,
                comparison=">",
                level=AlertLevel.CRITICAL,
                window_minutes=5,
            ),
            AlertRule(
                name="High Response Time",
                metric_name="avg_response_time",
                threshold=2000.0,  # 2 seconds
                comparison=">",
                level=AlertLevel.WARNING,
                window_minutes=5,
            ),
            AlertRule(
                name="Very High Response Time",
                metric_name="avg_response_time",
                threshold=5000.0,  # 5 seconds
                comparison=">",
                level=AlertLevel.ERROR,
                window_minutes=5,
            ),
        ]

        self.alert_rules.extend(default_rules)

    def add_alert_rule(self, rule: AlertRule):
        """Add a new alert rule."""
        self.alert_rules.append(rule)
        logger.info(f"Added alert rule: {rule.name}")

    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check all alert rules and return triggered alerts."""
        triggered_alerts = []
        current_time = datetime.now()

        # Get recent metrics for analysis
        summary = self.metrics_collector.get_metrics_summary()
        recent_requests = [
            r
            for r in self.metrics_collector.requests
            if (current_time - r.timestamp).total_seconds() < 300
        ]

        for rule in self.alert_rules:
            if not rule.enabled:
                continue

            try:
                # Calculate metric value based on rule
                metric_value = self._calculate_metric_value(
                    rule, summary, recent_requests
                )

                # Check if alert should trigger
                if self._should_trigger_alert(rule, metric_value):
                    alert_key = f"{rule.name}_{rule.metric_name}"

                    # Check if this is a new alert (not already active)
                    if alert_key not in self.active_alerts:
                        alert = {
                            "rule_name": rule.name,
                            "metric_name": rule.metric_name,
                            "current_value": metric_value,
                            "threshold": rule.threshold,
                            "level": rule.level.value,
                            "timestamp": current_time.isoformat(),
                            "message": f"{rule.name}: {rule.metric_name} is {metric_value} (threshold: {rule.threshold})",
                        }

                        triggered_alerts.append(alert)
                        self.active_alerts[alert_key] = current_time
                        self.alert_history.append(alert)

                        logger.log(
                            (
                                logging.WARNING
                                if rule.level == AlertLevel.WARNING
                                else logging.ERROR
                            ),
                            f"ALERT: {alert['message']}",
                        )
                else:
                    # Remove from active alerts if no longer triggering
                    alert_key = f"{rule.name}_{rule.metric_name}"
                    if alert_key in self.active_alerts:
                        del self.active_alerts[alert_key]

            except Exception as e:
                logger.error(f"Error checking alert rule {rule.name}: {e}")

        return triggered_alerts

    def _calculate_metric_value(
        self,
        rule: AlertRule,
        summary: Dict[str, Any],
        recent_requests: List[RequestMetrics],
    ) -> float:
        """Calculate the current value for a metric."""
        if rule.metric_name == "error_rate":
            if not recent_requests:
                return 0.0
            error_count = len([r for r in recent_requests if r.status_code >= 400])
            return (error_count / len(recent_requests)) * 100

        elif rule.metric_name == "avg_response_time":
            if not recent_requests:
                return 0.0
            return sum(r.duration_ms for r in recent_requests) / len(recent_requests)

        elif rule.metric_name in summary.get("gauges", {}):
            return summary["gauges"][rule.metric_name]

        elif rule.metric_name in summary.get("counters", {}):
            return summary["counters"][rule.metric_name]

        return 0.0

    def _should_trigger_alert(self, rule: AlertRule, value: float) -> bool:
        """Check if an alert should trigger based on rule conditions."""
        if rule.comparison == ">":
            return value > rule.threshold
        elif rule.comparison == "<":
            return value < rule.threshold
        elif rule.comparison == ">=":
            return value >= rule.threshold
        elif rule.comparison == "<=":
            return value <= rule.threshold
        elif rule.comparison == "==":
            return value == rule.threshold
        elif rule.comparison == "!=":
            return value != rule.threshold

        return False


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for request monitoring and metrics collection."""

    def __init__(self, app, metrics_collector: MetricsCollector):
        super().__init__(app)
        self.metrics_collector = metrics_collector

    async def dispatch(self, request: Request, call_next):
        """Process request with monitoring."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()
        self.metrics_collector.start_request_timer(request_id)
        request.state.processing_time = start_time

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Create request metrics
            request_metrics = RequestMetrics(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                user_agent=request.headers.get("user-agent"),
                client_ip=request.client.host if request.client else None,
                api_version=getattr(request.state, "api_version", None),
            )

            # Record metrics
            self.metrics_collector.end_request_timer(request_id, request_metrics)

            # Add monitoring headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            return response

        except Exception as e:
            # Record error metrics
            duration_ms = (time.time() - start_time) * 1000

            request_metrics = RequestMetrics(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
                timestamp=datetime.now(),
                user_agent=request.headers.get("user-agent"),
                client_ip=request.client.host if request.client else None,
                api_version=getattr(request.state, "api_version", None),
                error_type=type(e).__name__,
            )

            self.metrics_collector.end_request_timer(request_id, request_metrics)
            raise


def setup_monitoring(app, enable_alerts: bool = True):
    """Setup monitoring middleware and endpoints."""

    # Create metrics collector and alert manager
    metrics_collector = MetricsCollector()
    alert_manager = AlertManager(metrics_collector) if enable_alerts else None

    # Add monitoring middleware
    app.add_middleware(MonitoringMiddleware, metrics_collector=metrics_collector)

    # Add metrics endpoint
    @app.get("/api/v1/metrics", tags=["Monitoring"])
    async def get_metrics():
        """Get system metrics and statistics."""
        summary = metrics_collector.get_metrics_summary()

        # Add alert information if available
        if alert_manager:
            active_alerts = alert_manager.check_alerts()
            summary["alerts"] = {
                "active": len(alert_manager.active_alerts),
                "recent": active_alerts[-10:] if active_alerts else [],
                "rules_count": len(alert_manager.alert_rules),
            }

        return summary

    # Add performance endpoint
    @app.get("/api/v1/metrics/performance", tags=["Monitoring"])
    async def get_performance_metrics():
        """Get detailed performance metrics."""
        summary = metrics_collector.get_metrics_summary()

        return {
            "endpoint_performance": summary.get("endpoint_stats", {}),
            "response_times": summary.get("timers", {}),
            "request_rates": summary.get("counters", {}),
            "active_requests": summary.get("active_requests", 0),
            "timestamp": summary.get("timestamp"),
        }

    logger.info("Monitoring system initialized")

    return {"metrics_collector": metrics_collector, "alert_manager": alert_manager}


__all__ = [
    "MetricType",
    "AlertLevel",
    "Metric",
    "RequestMetrics",
    "AlertRule",
    "MetricsCollector",
    "AlertManager",
    "MonitoringMiddleware",
    "setup_monitoring",
]
