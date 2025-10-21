#!/usr/bin/env python3
"""
Observability Infrastructure
==========================

Milestone 4 Implementation: API Hardening + Metrics + Logging + Monitoring

核心设计：
- Prometheus metrics collection and export
- Structured logging with correlation IDs
- Distributed tracing with OpenTelemetry
- Health checks and monitoring endpoints
- Performance monitoring and alerting
- Security audit logging

Features:
- MetricsCollector: Prometheus-compatible metrics
- StructuredLogger: JSON structured logging
- TracingManager: Distributed request tracing
- HealthMonitor: System health monitoring
- SecurityAuditor: Security event logging
- PerformanceProfiler: Real-time performance analytics
"""

import asyncio
import json
import logging
import os
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

import psutil

# External dependencies - graceful degradation if not available
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

try:
    from opentelemetry import trace
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

# FastAPI for metrics endpoint
try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse, PlainTextResponse

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class MetricRecord:
    """Individual metric record"""

    name: str
    metric_type: str  # counter, histogram, gauge, info
    value: Union[float, int, str]
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    help_text: str = ""


@dataclass
class TraceSpan:
    """Trace span data"""

    span_id: str
    trace_id: str
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    labels: Dict[str, str] = field(default_factory=dict)
    status: str = "OK"
    error: Optional[str] = None


@dataclass
class LogRecord:
    """Structured log record"""

    timestamp: datetime
    level: str
    message: str
    logger_name: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    component: Optional[str] = None
    labels: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "logger": self.logger_name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "user_id": self.user_id,
            "request_id": self.request_id,
            "component": self.component,
            "labels": self.labels,
        }


class MetricsCollector:
    """Prometheus-compatible metrics collector"""

    def __init__(self, namespace: str = "novel_engine"):
        self.namespace = namespace
        self.registry = CollectorRegistry() if PROMETHEUS_AVAILABLE else None
        self.metrics: Dict[str, Any] = {}
        self.fallback_metrics: Dict[str, MetricRecord] = {}

        if PROMETHEUS_AVAILABLE:
            self._initialize_prometheus_metrics()

        logger.info(f"Metrics collector initialized with namespace: {namespace}")

    def _initialize_prometheus_metrics(self):
        """Initialize common Prometheus metrics"""
        if not PROMETHEUS_AVAILABLE:
            return

        # HTTP request metrics
        self.metrics["http_requests_total"] = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
            registry=self.registry,
        )

        self.metrics["http_request_duration"] = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration",
            ["method", "endpoint"],
            registry=self.registry,
        )

        # System metrics
        self.metrics["memory_usage_bytes"] = Gauge(
            "memory_usage_bytes",
            "Memory usage in bytes",
            ["type"],
            registry=self.registry,
        )

        self.metrics["cpu_usage_percent"] = Gauge(
            "cpu_usage_percent", "CPU usage percentage", registry=self.registry
        )

        # Application metrics
        self.metrics["active_agents"] = Gauge(
            "active_agents_total", "Number of active agents", registry=self.registry
        )

        self.metrics["simulation_turns_total"] = Counter(
            "simulation_turns_total",
            "Total simulation turns executed",
            ["agent_id"],
            registry=self.registry,
        )

        self.metrics["llm_requests_total"] = Counter(
            "llm_requests_total",
            "Total LLM requests",
            ["model", "status"],
            registry=self.registry,
        )

        self.metrics["llm_request_duration"] = Histogram(
            "llm_request_duration_seconds",
            "LLM request duration",
            ["model"],
            registry=self.registry,
        )

        self.metrics["narrative_events_total"] = Counter(
            "narrative_events_total",
            "Total narrative events generated",
            ["event_type"],
            registry=self.registry,
        )

        self.metrics["state_store_operations"] = Counter(
            "state_store_operations_total",
            "State store operations",
            ["store_type", "operation", "status"],
            registry=self.registry,
        )

        self.metrics["negotiation_sessions"] = Gauge(
            "negotiation_sessions_active",
            "Active negotiation sessions",
            registry=self.registry,
        )

    def increment_counter(
        self, name: str, labels: Dict[str, str] = None, value: float = 1.0
    ):
        """Increment a counter metric"""
        labels = labels or {}

        if PROMETHEUS_AVAILABLE and name in self.metrics:
            if labels:
                self.metrics[name].labels(**labels).inc(value)
            else:
                self.metrics[name].inc(value)
        else:
            # Fallback storage
            key = f"{name}:{json.dumps(labels, sort_keys=True)}"
            if key in self.fallback_metrics:
                self.fallback_metrics[key].value += value
            else:
                self.fallback_metrics[key] = MetricRecord(
                    name=name, metric_type="counter", value=value, labels=labels
                )

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric"""
        labels = labels or {}

        if PROMETHEUS_AVAILABLE and name in self.metrics:
            if labels:
                self.metrics[name].labels(**labels).set(value)
            else:
                self.metrics[name].set(value)
        else:
            # Fallback storage
            key = f"{name}:{json.dumps(labels, sort_keys=True)}"
            self.fallback_metrics[key] = MetricRecord(
                name=name, metric_type="gauge", value=value, labels=labels
            )

    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe a histogram metric"""
        labels = labels or {}

        if PROMETHEUS_AVAILABLE and name in self.metrics:
            if labels:
                self.metrics[name].labels(**labels).observe(value)
            else:
                self.metrics[name].observe(value)
        else:
            # Fallback - store as gauge for simplicity
            key = f"{name}:{json.dumps(labels, sort_keys=True)}"
            self.fallback_metrics[key] = MetricRecord(
                name=name, metric_type="histogram", value=value, labels=labels
            )

    def record_http_request(
        self, method: str, endpoint: str, status: int, duration: float
    ):
        """Record HTTP request metrics"""
        self.increment_counter(
            "http_requests_total",
            {"method": method, "endpoint": endpoint, "status": str(status)},
        )

        self.observe_histogram(
            "http_request_duration", duration, {"method": method, "endpoint": endpoint}
        )

    def update_system_metrics(self):
        """Update system resource metrics"""
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            self.set_gauge("memory_usage_bytes", memory.used, {"type": "used"})
            self.set_gauge(
                "memory_usage_bytes", memory.available, {"type": "available"}
            )

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=None)
            self.set_gauge("cpu_usage_percent", cpu_percent)

        except Exception as e:
            logger.warning(f"Failed to update system metrics: {e}")

    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format"""
        if PROMETHEUS_AVAILABLE and self.registry:
            return generate_latest(self.registry).decode("utf-8")
        else:
            # Generate simple text format for fallback metrics
            lines = []
            for key, record in self.fallback_metrics.items():
                labels_str = ""
                if record.labels:
                    label_pairs = [f'{k}="{v}"' for k, v in record.labels.items()]
                    labels_str = "{" + ",".join(label_pairs) + "}"

                lines.append(f"{record.name}{labels_str} {record.value}")

            return "\n".join(lines)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary as JSON"""
        summary = {"timestamp": datetime.now().isoformat(), "metrics": {}}

        if PROMETHEUS_AVAILABLE:
            # Convert Prometheus metrics to JSON
            for name, metric in self.metrics.items():
                summary["metrics"][name] = {
                    "type": metric._type,
                    "help": getattr(metric, "_documentation", ""),
                    "samples": [],
                }
        else:
            # Use fallback metrics
            grouped_metrics = defaultdict(list)
            for record in self.fallback_metrics.values():
                grouped_metrics[record.name].append(
                    {
                        "value": record.value,
                        "labels": record.labels,
                        "timestamp": record.timestamp.isoformat(),
                    }
                )

            summary["metrics"] = dict(grouped_metrics)

        return summary


class StructuredLogger:
    """Structured JSON logger with correlation support"""

    def __init__(self, name: str, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self._setup_handler()
        self._context_vars = threading.local()

    def _setup_handler(self):
        """Setup JSON formatter"""
        handler = logging.StreamHandler()
        formatter = StructuredFormatter()
        handler.setFormatter(formatter)

        # Remove existing handlers to avoid duplication
        self.logger.handlers.clear()
        self.logger.addHandler(handler)
        self.logger.propagate = False

    def set_context(self, **kwargs):
        """Set context variables for this thread"""
        if not hasattr(self._context_vars, "context"):
            self._context_vars.context = {}

        self._context_vars.context.update(kwargs)

    def clear_context(self):
        """Clear context variables"""
        if hasattr(self._context_vars, "context"):
            self._context_vars.context.clear()

    def _get_context(self) -> Dict[str, Any]:
        """Get current context"""
        if hasattr(self._context_vars, "context"):
            return self._context_vars.context.copy()
        return {}

    def _log(self, level: str, message: str, **kwargs):
        """Internal logging method"""
        context = self._get_context()
        context.update(kwargs)

        record = LogRecord(
            timestamp=datetime.now(),
            level=level,
            message=message,
            logger_name=self.logger.name,
            **context,
        )

        # Log as JSON
        self.logger.log(
            getattr(logging, level.upper()), json.dumps(record.to_dict(), default=str)
        )

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log("CRITICAL", message, **kwargs)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""

    def format(self, record):
        # If the message is already JSON, return as-is
        if record.getMessage().startswith("{"):
            return record.getMessage()

        # Otherwise, create structured log
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


class TracingManager:
    """Distributed tracing manager"""

    def __init__(self, service_name: str = "novel-engine", jaeger_endpoint: str = None):
        self.service_name = service_name
        self.active_spans: Dict[str, TraceSpan] = {}
        self.span_history = deque(maxlen=1000)  # Keep recent spans

        if OTEL_AVAILABLE and jaeger_endpoint:
            self._setup_jaeger(jaeger_endpoint)

        logger.info(f"Tracing manager initialized for service: {service_name}")

    def _setup_jaeger(self, endpoint: str):
        """Setup Jaeger tracing"""
        try:
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=14268,
                collector_endpoint=endpoint,
            )

            provider = TracerProvider()
            processor = BatchSpanProcessor(jaeger_exporter)
            provider.add_span_processor(processor)
            trace.set_tracer_provider(provider)

            self.tracer = trace.get_tracer(self.service_name)
            logger.info("Jaeger tracing configured")

        except Exception as e:
            logger.warning(f"Failed to setup Jaeger tracing: {e}")
            self.tracer = None

    def start_span(
        self, operation_name: str, parent_span_id: str = None, **labels
    ) -> str:
        """Start a new trace span"""
        span_id = str(uuid.uuid4())
        trace_id = parent_span_id or str(uuid.uuid4())

        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            operation_name=operation_name,
            start_time=datetime.now(),
            labels=labels,
        )

        self.active_spans[span_id] = span

        # Start OpenTelemetry span if available
        if hasattr(self, "tracer") and self.tracer:
            otel_span = self.tracer.start_span(operation_name)
            for key, value in labels.items():
                otel_span.set_attribute(key, str(value))

        return span_id

    def finish_span(self, span_id: str, status: str = "OK", error: str = None):
        """Finish a trace span"""
        if span_id not in self.active_spans:
            logger.warning(f"Attempted to finish unknown span: {span_id}")
            return

        span = self.active_spans[span_id]
        span.end_time = datetime.now()
        span.duration_ms = (span.end_time - span.start_time).total_seconds() * 1000
        span.status = status
        span.error = error

        # Move to history
        self.span_history.append(span)
        del self.active_spans[span_id]

        logger.debug(f"Finished span {span.operation_name}: {span.duration_ms:.2f}ms")

    @contextmanager
    def trace_operation(self, operation_name: str, **labels):
        """Context manager for tracing operations"""
        span_id = self.start_span(operation_name, **labels)
        try:
            yield span_id
            self.finish_span(span_id, "OK")
        except Exception as e:
            self.finish_span(span_id, "ERROR", str(e))
            raise

    def get_trace_summary(self, trace_id: str) -> List[Dict[str, Any]]:
        """Get trace summary for a trace ID"""
        spans = []

        # Check active spans
        for span in self.active_spans.values():
            if span.trace_id == trace_id:
                spans.append(asdict(span))

        # Check span history
        for span in self.span_history:
            if span.trace_id == trace_id:
                spans.append(asdict(span))

        return sorted(spans, key=lambda x: x["start_time"])


class PerformanceProfiler:
    """Real-time performance profiling and analytics"""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.operation_times = defaultdict(lambda: deque(maxlen=window_size))
        self.operation_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.start_times: Dict[str, datetime] = {}

    def start_operation(self, operation_id: str):
        """Start timing an operation"""
        self.start_times[operation_id] = datetime.now()

    def finish_operation(
        self, operation_id: str, operation_name: str, success: bool = True
    ):
        """Finish timing an operation"""
        if operation_id not in self.start_times:
            logger.warning(f"Attempted to finish unknown operation: {operation_id}")
            return

        duration = (datetime.now() - self.start_times[operation_id]).total_seconds()

        self.operation_times[operation_name].append(duration)
        self.operation_counts[operation_name] += 1

        if not success:
            self.error_counts[operation_name] += 1

        del self.start_times[operation_id]

        return duration

    @contextmanager
    def profile_operation(self, operation_name: str):
        """Context manager for profiling operations"""
        operation_id = str(uuid.uuid4())
        self.start_operation(operation_id)

        try:
            yield
            self.finish_operation(operation_id, operation_name, success=True)
        except Exception:
            self.finish_operation(operation_id, operation_name, success=False)
            raise

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = {}

        for operation_name, times in self.operation_times.items():
            if times:
                times_list = list(times)
                stats[operation_name] = {
                    "count": self.operation_counts[operation_name],
                    "error_count": self.error_counts[operation_name],
                    "error_rate": self.error_counts[operation_name]
                    / max(1, self.operation_counts[operation_name]),
                    "avg_duration_ms": sum(times_list) * 1000 / len(times_list),
                    "min_duration_ms": min(times_list) * 1000,
                    "max_duration_ms": max(times_list) * 1000,
                    "p95_duration_ms": (
                        sorted(times_list)[int(len(times_list) * 0.95)] * 1000
                        if times_list
                        else 0
                    ),
                    "p99_duration_ms": (
                        sorted(times_list)[int(len(times_list) * 0.99)] * 1000
                        if times_list
                        else 0
                    ),
                }

        return stats


class SecurityAuditor:
    """Security event auditing and logging"""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self.security_events = deque(maxlen=1000)
        self.threat_counts = defaultdict(int)

    def log_authentication_event(
        self,
        user_id: str,
        event_type: str,
        success: bool,
        details: Dict[str, Any] = None,
    ):
        """Log authentication event"""
        event_data = {
            "event_category": "authentication",
            "user_id": user_id,
            "event_type": event_type,
            "success": success,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
            "source_ip": details.get("source_ip") if details else None,
        }

        self.security_events.append(event_data)

        if success:
            self.logger.info(f"Authentication {event_type} successful", **event_data)
        else:
            self.logger.warning(f"Authentication {event_type} failed", **event_data)
            self.threat_counts[f"auth_failure_{event_type}"] += 1

    def log_authorization_event(
        self,
        user_id: str,
        resource: str,
        action: str,
        granted: bool,
        details: Dict[str, Any] = None,
    ):
        """Log authorization event"""
        event_data = {
            "event_category": "authorization",
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "granted": granted,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
        }

        self.security_events.append(event_data)

        if granted:
            self.logger.debug(f"Access granted to {resource}", **event_data)
        else:
            self.logger.warning(f"Access denied to {resource}", **event_data)
            self.threat_counts[f"access_denied_{action}"] += 1

    def log_security_threat(
        self, threat_type: str, severity: str, details: Dict[str, Any]
    ):
        """Log security threat"""
        event_data = {
            "event_category": "security_threat",
            "threat_type": threat_type,
            "severity": severity,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }

        self.security_events.append(event_data)
        self.threat_counts[threat_type] += 1

        if severity in ["HIGH", "CRITICAL"]:
            self.logger.critical(
                f"Security threat detected: {threat_type}", **event_data
            )
        else:
            self.logger.warning(
                f"Security threat detected: {threat_type}", **event_data
            )

    def get_security_summary(self) -> Dict[str, Any]:
        """Get security event summary"""
        recent_events = list(self.security_events)[-50:]  # Last 50 events

        return {
            "total_events": len(self.security_events),
            "threat_counts": dict(self.threat_counts),
            "recent_events": recent_events,
            "summary_generated_at": datetime.now().isoformat(),
        }


class HealthMonitor:
    """System health monitoring"""

    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.health_checks: Dict[str, Callable] = {}
        self.last_check_results: Dict[str, Dict[str, Any]] = {}
        self.health_history = deque(maxlen=100)

    def register_health_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.health_checks[name] = check_func
        logger.info(f"Registered health check: {name}")

    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        overall_healthy = True

        for name, check_func in self.health_checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()

                if isinstance(result, bool):
                    result = {
                        "healthy": result,
                        "message": "OK" if result else "Failed",
                    }
                elif not isinstance(result, dict):
                    result = {"healthy": bool(result), "message": str(result)}

                results[name] = result

                if not result.get("healthy", False):
                    overall_healthy = False

            except Exception as e:
                results[name] = {
                    "healthy": False,
                    "message": f"Health check failed: {str(e)}",
                    "error": str(e),
                }
                overall_healthy = False
                logger.error(f"Health check {name} failed: {e}")

        # Add system metrics
        self.metrics.update_system_metrics()

        health_summary = {
            "timestamp": datetime.now().isoformat(),
            "overall_healthy": overall_healthy,
            "checks": results,
            "system": self._get_system_health(),
        }

        self.last_check_results = health_summary
        self.health_history.append(health_summary)

        return health_summary

    def _get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "memory": {
                    "used_percent": memory.percent,
                    "available_gb": memory.available / (1024**3),
                    "used_gb": memory.used / (1024**3),
                },
                "disk": {
                    "used_percent": disk.percent,
                    "free_gb": disk.free / (1024**3),
                    "used_gb": disk.used / (1024**3),
                },
                "cpu_percent": psutil.cpu_percent(interval=None),
                "load_average": os.getloadavg() if hasattr(os, "getloadavg") else None,
                "uptime_seconds": time.time() - psutil.boot_time(),
            }

        except Exception as e:
            logger.warning(f"Failed to get system health: {e}")
            return {"error": str(e)}

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return self.last_check_results or {"status": "No health checks run yet"}

    def is_healthy(self) -> bool:
        """Check if system is currently healthy"""
        return self.last_check_results.get("overall_healthy", False)


class ObservabilityManager:
    """Main observability manager orchestrating all components"""

    def __init__(
        self, service_name: str = "novel-engine", config: Dict[str, Any] = None
    ):
        self.service_name = service_name
        self.config = config or {}

        # Initialize components
        self.metrics = MetricsCollector(namespace=service_name.replace("-", "_"))
        self.logger = StructuredLogger(
            service_name, level=self.config.get("log_level", "INFO")
        )
        self.tracer = TracingManager(service_name, self.config.get("jaeger_endpoint"))
        self.profiler = PerformanceProfiler()
        self.auditor = SecurityAuditor(self.logger)
        self.health_monitor = HealthMonitor(self.metrics)

        # Register default health checks
        self._register_default_health_checks()

        # Start background tasks
        self._start_background_tasks()

        self.logger.info("Observability manager initialized", service=service_name)

    def _register_default_health_checks(self):
        """Register default health checks"""

        def memory_check():
            memory = psutil.virtual_memory()
            return {
                "healthy": memory.percent < 90,
                "message": f"Memory usage: {memory.percent:.1f}%",
                "details": {
                    "usage_percent": memory.percent,
                    "available_gb": memory.available / (1024**3),
                },
            }

        def cpu_check():
            cpu_percent = psutil.cpu_percent(interval=1)
            return {
                "healthy": cpu_percent < 80,
                "message": f"CPU usage: {cpu_percent:.1f}%",
                "details": {"usage_percent": cpu_percent},
            }

        def disk_check():
            disk = psutil.disk_usage("/")
            return {
                "healthy": disk.percent < 85,
                "message": f"Disk usage: {disk.percent:.1f}%",
                "details": {
                    "usage_percent": disk.percent,
                    "free_gb": disk.free / (1024**3),
                },
            }

        self.health_monitor.register_health_check("memory", memory_check)
        self.health_monitor.register_health_check("cpu", cpu_check)
        self.health_monitor.register_health_check("disk", disk_check)

    def _start_background_tasks(self):
        """Start background monitoring tasks"""

        def update_metrics():
            while True:
                try:
                    self.metrics.update_system_metrics()
                    time.sleep(30)  # Update every 30 seconds
                except Exception as e:
                    self.logger.error("Failed to update system metrics", error=str(e))
                    time.sleep(30)

        # Start metrics update thread
        metrics_thread = threading.Thread(target=update_metrics, daemon=True)
        metrics_thread.start()

    def create_request_middleware(self):
        """Create FastAPI middleware for request tracking"""
        if not FASTAPI_AVAILABLE:
            return None

        async def observability_middleware(request: Request, call_next):
            # Generate request ID
            request_id = str(uuid.uuid4())
            request.state.request_id = request_id

            # Set context for logging
            self.logger.set_context(
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                user_agent=request.headers.get("user-agent"),
            )

            # Start tracing
            span_id = self.tracer.start_span(
                f"{request.method} {request.url.path}",
                method=request.method,
                endpoint=request.url.path,
                request_id=request_id,
            )

            # Start profiling
            operation_name = f"{request.method}:{request.url.path}"
            with self.profiler.profile_operation(operation_name):
                start_time = time.time()

                try:
                    response = await call_next(request)
                    duration = time.time() - start_time

                    # Record metrics
                    self.metrics.record_http_request(
                        request.method, request.url.path, response.status_code, duration
                    )

                    # Log request
                    self.logger.info(
                        f"{request.method} {request.url.path} -> {response.status_code}",
                        status_code=response.status_code,
                        duration_ms=duration * 1000,
                    )

                    # Finish tracing
                    self.tracer.finish_span(span_id, "OK")

                    return response

                except Exception as e:
                    duration = time.time() - start_time

                    # Record error metrics
                    self.metrics.record_http_request(
                        request.method, request.url.path, 500, duration
                    )

                    # Log error
                    self.logger.error(
                        f"{request.method} {request.url.path} -> ERROR",
                        error=str(e),
                        duration_ms=duration * 1000,
                    )

                    # Finish tracing with error
                    self.tracer.finish_span(span_id, "ERROR", str(e))

                    raise

                finally:
                    # Clear context
                    self.logger.clear_context()

        return observability_middleware

    def create_monitoring_routes(self):
        """Create monitoring endpoints for FastAPI"""
        if not FASTAPI_AVAILABLE:
            return None

        router = FastAPI()

        @router.get("/metrics")
        async def get_metrics():
            """Prometheus metrics endpoint"""
            content = self.metrics.get_prometheus_metrics()
            return PlainTextResponse(
                content=content,
                media_type=(
                    CONTENT_TYPE_LATEST if PROMETHEUS_AVAILABLE else "text/plain"
                ),
            )

        @router.get("/metrics/json")
        async def get_metrics_json():
            """JSON metrics endpoint"""
            return JSONResponse(content=self.metrics.get_metrics_summary())

        @router.get("/health")
        async def health_check():
            """Health check endpoint"""
            health = await self.health_monitor.run_health_checks()
            status_code = 200 if health["overall_healthy"] else 503
            return JSONResponse(content=health, status_code=status_code)

        @router.get("/ready")
        async def readiness_check():
            """Readiness check (lighter than health)"""
            return JSONResponse(
                content={
                    "ready": self.health_monitor.is_healthy(),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        @router.get("/performance")
        async def get_performance_stats():
            """Performance statistics endpoint"""
            return JSONResponse(content=self.profiler.get_performance_stats())

        @router.get("/security/summary")
        async def get_security_summary():
            """Security audit summary"""
            return JSONResponse(content=self.auditor.get_security_summary())

        @router.get("/traces/{trace_id}")
        async def get_trace(trace_id: str):
            """Get trace information"""
            trace_data = self.tracer.get_trace_summary(trace_id)
            if not trace_data:
                raise HTTPException(status_code=404, detail="Trace not found")
            return JSONResponse(content=trace_data)

        return router

    def instrument_function(self, operation_name: str = None):
        """Decorator to instrument functions with observability"""

        def decorator(func):
            func_name = operation_name or f"{func.__module__}.{func.__name__}"

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.tracer.trace_operation(func_name):
                    with self.profiler.profile_operation(func_name):
                        try:
                            result = await func(*args, **kwargs)
                            self.logger.debug(
                                f"Function {func_name} completed successfully"
                            )
                            return result
                        except Exception as e:
                            self.logger.error(
                                f"Function {func_name} failed", error=str(e)
                            )
                            raise

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.tracer.trace_operation(func_name):
                    with self.profiler.profile_operation(func_name):
                        try:
                            result = func(*args, **kwargs)
                            self.logger.debug(
                                f"Function {func_name} completed successfully"
                            )
                            return result
                        except Exception as e:
                            self.logger.error(
                                f"Function {func_name} failed", error=str(e)
                            )
                            raise

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def get_observability_summary(self) -> Dict[str, Any]:
        """Get overall observability summary"""
        return {
            "service": self.service_name,
            "timestamp": datetime.now().isoformat(),
            "health": self.health_monitor.get_health_status(),
            "metrics_available": PROMETHEUS_AVAILABLE,
            "tracing_available": OTEL_AVAILABLE,
            "performance": {
                "active_operations": len(self.profiler.start_times),
                "tracked_operations": len(self.profiler.operation_times),
            },
            "security": {
                "recent_events": len(self.auditor.security_events),
                "threat_types": len(self.auditor.threat_counts),
            },
        }


# Factory function
def create_observability_manager(
    service_name: str = "novel-engine", config: Dict[str, Any] = None
) -> ObservabilityManager:
    """Create observability manager instance"""
    return ObservabilityManager(service_name, config)


# Example usage
if __name__ == "__main__":

    async def example_usage():
        # Create observability manager
        obs_manager = create_observability_manager("novel-engine-example")

        # Example function instrumentation
        @obs_manager.instrument_function("example_operation")
        async def example_operation(name: str):
            obs_manager.logger.info(f"Processing {name}")
            await asyncio.sleep(0.1)  # Simulate work
            return f"Processed {name}"

        # Run some operations
        results = []
        for i in range(5):
            result = await example_operation(f"item_{i}")
            results.append(result)

        # Check health
        health = await obs_manager.health_monitor.run_health_checks()
        print(f"System healthy: {health['overall_healthy']}")

        # Get performance stats
        perf_stats = obs_manager.profiler.get_performance_stats()
        print(f"Performance stats: {perf_stats}")

        # Get metrics
        metrics_summary = obs_manager.metrics.get_metrics_summary()
        print(f"Metrics available: {len(metrics_summary['metrics'])}")

        # Log security event
        obs_manager.auditor.log_authentication_event(
            user_id="test_user",
            event_type="login",
            success=True,
            details={"source_ip": "192.168.1.1"},
        )

        print("Example completed successfully")

    # Run example
    asyncio.run(example_usage())
