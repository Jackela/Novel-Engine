#!/usr/bin/env python3
"""
Prometheus Metrics Collection Infrastructure for Novel Engine

Implements comprehensive Prometheus metrics collection with:
- Application performance metrics (response times, throughput, errors)
- Infrastructure metrics (CPU, memory, disk, network)
- Business metrics (active users, operations, feature usage)
- Custom metrics for Novel Engine operations (agent coordination, story generation)
"""

import asyncio
import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Union

import psutil
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Prometheus metric types"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

@dataclass
class PrometheusMetric:
    """Prometheus metric definition"""
    name: str
    metric_type: MetricType
    help_text: str
    labels: Dict[str, str]
    value: Union[float, int]
    timestamp: float

class PrometheusMetricsCollector:
    """Prometheus metrics collection system"""
    
    def __init__(self):
        self.metrics: Dict[str, PrometheusMetric] = {}
        self.counters: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.gauge_values: Dict[str, float] = {}
        
        # Track system resources
        self.process = psutil.Process()
        self.start_time = time.time()
        
        # Application-specific metrics
        self.http_requests_total = 0
        self.http_request_duration_sum = 0.0
        self.http_request_duration_count = 0
        self.http_errors_total = 0
        
        # Novel Engine specific metrics
        self.story_generation_requests = 0
        self.story_generation_duration_sum = 0.0
        self.agent_coordination_events = 0
        self.active_sessions = 0
        self.character_interactions = 0
        self.narrative_quality_score = 0.0
        
        # Database metrics
        self.database_queries_total = 0
        self.database_query_duration_sum = 0.0
        self.database_connections_active = 0
        
        # Cache metrics
        self.cache_hits = 0
        self.cache_misses = 0
        self.cache_operations_total = 0
        
        logger.info("Prometheus metrics collector initialized")
    
    def increment_counter(self, name: str, labels: Dict[str, str] = None, value: float = 1.0):
        """Increment a counter metric"""
        metric_key = self._build_metric_key(name, labels)
        self.counters[metric_key] += value
        
        metric = PrometheusMetric(
            name=name,
            metric_type=MetricType.COUNTER,
            help_text=f"Counter metric: {name}",
            labels=labels or {},
            value=self.counters[metric_key],
            timestamp=time.time()
        )
        self.metrics[metric_key] = metric
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge metric value"""
        metric_key = self._build_metric_key(name, labels)
        self.gauge_values[metric_key] = value
        
        metric = PrometheusMetric(
            name=name,
            metric_type=MetricType.GAUGE,
            help_text=f"Gauge metric: {name}",
            labels=labels or {},
            value=value,
            timestamp=time.time()
        )
        self.metrics[metric_key] = metric
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe a value for histogram metric"""
        metric_key = self._build_metric_key(name, labels)
        self.histograms[metric_key].append(value)
        
        # Keep only last 1000 observations to manage memory
        if len(self.histograms[metric_key]) > 1000:
            self.histograms[metric_key] = self.histograms[metric_key][-1000:]
        
        metric = PrometheusMetric(
            name=name,
            metric_type=MetricType.HISTOGRAM,
            help_text=f"Histogram metric: {name}",
            labels=labels or {},
            value=value,
            timestamp=time.time()
        )
        self.metrics[metric_key] = metric
    
    def _build_metric_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Build unique metric key from name and labels"""
        if not labels:
            return name
        
        label_parts = [f"{k}={v}" for k, v in sorted(labels.items())]
        return f"{name}{{{','.join(label_parts)}}}"
    
    # Application Performance Metrics
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration_seconds: float):
        """Record HTTP request metrics"""
        labels = {
            "method": method,
            "endpoint": endpoint,
            "status_code": str(status_code)
        }
        
        # Increment request counter
        self.increment_counter("http_requests_total", labels)
        
        # Record request duration
        self.observe_histogram("http_request_duration_seconds", duration_seconds, labels)
        
        # Track errors
        if status_code >= 400:
            self.increment_counter("http_errors_total", labels)
        
        # Update internal counters for summary metrics
        self.http_requests_total += 1
        self.http_request_duration_sum += duration_seconds
        self.http_request_duration_count += 1
        
        if status_code >= 400:
            self.http_errors_total += 1
    
    def record_database_query(self, query_type: str, table: str, duration_seconds: float, success: bool = True):
        """Record database query metrics"""
        labels = {
            "query_type": query_type,
            "table": table,
            "success": str(success).lower()
        }
        
        self.increment_counter("database_queries_total", labels)
        self.observe_histogram("database_query_duration_seconds", duration_seconds, labels)
        
        # Update internal counters
        self.database_queries_total += 1
        self.database_query_duration_sum += duration_seconds
    
    def record_cache_operation(self, operation: str, hit: bool, duration_seconds: float = 0.0):
        """Record cache operation metrics"""
        labels = {
            "operation": operation,
            "result": "hit" if hit else "miss"
        }
        
        self.increment_counter("cache_operations_total", labels)
        
        if duration_seconds > 0:
            self.observe_histogram("cache_operation_duration_seconds", duration_seconds, labels)
        
        # Update internal counters
        self.cache_operations_total += 1
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    # Novel Engine Specific Metrics
    def record_story_generation(self, story_type: str, duration_seconds: float, success: bool = True, quality_score: float = 0.0):
        """Record story generation metrics"""
        labels = {
            "story_type": story_type,
            "success": str(success).lower()
        }
        
        self.increment_counter("story_generation_requests_total", labels)
        self.observe_histogram("story_generation_duration_seconds", duration_seconds, labels)
        
        if quality_score > 0:
            self.set_gauge("story_generation_quality_score", quality_score, labels)
        
        # Update internal counters
        self.story_generation_requests += 1
        self.story_generation_duration_sum += duration_seconds
        
        if quality_score > 0:
            self.narrative_quality_score = quality_score
    
    def record_agent_coordination(self, event_type: str, agent_count: int, duration_seconds: float):
        """Record agent coordination metrics"""
        labels = {
            "event_type": event_type,
            "agent_count": str(agent_count)
        }
        
        self.increment_counter("agent_coordination_events_total", labels)
        self.observe_histogram("agent_coordination_duration_seconds", duration_seconds, labels)
        
        # Update internal counter
        self.agent_coordination_events += 1
    
    def record_character_interaction(self, interaction_type: str, character_count: int, success: bool = True):
        """Record character interaction metrics"""
        labels = {
            "interaction_type": interaction_type,
            "character_count": str(character_count),
            "success": str(success).lower()
        }
        
        self.increment_counter("character_interactions_total", labels)
        
        # Update internal counter
        self.character_interactions += 1
    
    def set_active_sessions(self, count: int):
        """Set number of active sessions"""
        self.set_gauge("active_sessions", count)
        self.active_sessions = count
    
    def set_database_connections(self, count: int):
        """Set number of active database connections"""
        self.set_gauge("database_connections_active", count)
        self.database_connections_active = count
    
    # System Resource Metrics
    def collect_system_metrics(self):
        """Collect system resource metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            self.set_gauge("system_cpu_usage_percent", cpu_percent)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            self.set_gauge("system_memory_total_bytes", memory.total)
            self.set_gauge("system_memory_available_bytes", memory.available)
            self.set_gauge("system_memory_used_bytes", memory.used)
            self.set_gauge("system_memory_usage_percent", memory.percent)
            
            # Process memory
            process_memory = self.process.memory_info()
            self.set_gauge("process_memory_rss_bytes", process_memory.rss)
            self.set_gauge("process_memory_vms_bytes", process_memory.vms)
            
            # Process CPU
            process_cpu = self.process.cpu_percent()
            self.set_gauge("process_cpu_usage_percent", process_cpu)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            self.set_gauge("system_disk_total_bytes", disk.total)
            self.set_gauge("system_disk_used_bytes", disk.used)
            self.set_gauge("system_disk_free_bytes", disk.free)
            self.set_gauge("system_disk_usage_percent", (disk.used / disk.total) * 100)
            
            # Process uptime
            uptime = time.time() - self.start_time
            self.set_gauge("process_uptime_seconds", uptime)
            
            # File descriptors (Linux/macOS)
            if hasattr(self.process, 'num_fds'):
                fds = self.process.num_fds()
                self.set_gauge("process_open_fds", fds)
            
            # Thread count
            threads = self.process.num_threads()
            self.set_gauge("process_threads", threads)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    # Business Metrics
    def record_user_action(self, action_type: str, user_id: str = None, success: bool = True):
        """Record user action metrics"""
        labels = {
            "action_type": action_type,
            "success": str(success).lower()
        }
        
        if user_id:
            labels["user_id"] = user_id
        
        self.increment_counter("user_actions_total", labels)
    
    def record_feature_usage(self, feature_name: str, user_count: int = 1):
        """Record feature usage metrics"""
        labels = {"feature": feature_name}
        self.increment_counter("feature_usage_total", labels, user_count)
    
    def set_business_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Set business metric value"""
        self.set_gauge(f"business_{metric_name}", value, labels)
    
    # Metrics Export
    def get_metrics_text(self) -> str:
        """Generate Prometheus metrics text format"""
        lines = []
        
        # Group metrics by name
        metrics_by_name = defaultdict(list)
        for metric in self.metrics.values():
            metrics_by_name[metric.name].append(metric)
        
        for metric_name, metric_list in metrics_by_name.items():
            if not metric_list:
                continue
            
            # Add help and type comments
            metric_type = metric_list[0].metric_type
            lines.append(f"# HELP {metric_name} {metric_list[0].help_text}")
            lines.append(f"# TYPE {metric_name} {metric_type.value}")
            
            # Add metric values
            for metric in metric_list:
                if metric.labels:
                    label_parts = [f'{k}="{v}"' for k, v in metric.labels.items()]
                    label_str = "{" + ",".join(label_parts) + "}"
                    lines.append(f"{metric_name}{label_str} {metric.value}")
                else:
                    lines.append(f"{metric_name} {metric.value}")
        
        # Add summary metrics for histograms
        for metric_name, values in self.histograms.items():
            if values:
                base_name = metric_name.split("{")[0]  # Remove labels for base name
                count = len(values)
                total = sum(values)
                
                lines.append(f"# HELP {base_name}_sum Total sum of {base_name}")
                lines.append(f"# TYPE {base_name}_sum counter")
                lines.append(f"{base_name}_sum {total}")
                
                lines.append(f"# HELP {base_name}_count Total count of {base_name}")
                lines.append(f"# TYPE {base_name}_count counter")
                lines.append(f"{base_name}_count {count}")
                
                # Add percentiles
                if count > 0:
                    sorted(values)
                    int(0.5 * (count - 1))
                    int(0.95 * (count - 1))
                    int(0.99 * (count - 1))
                    
                    lines.append(f"# HELP {base_name}_bucket Cumulative counters for {base_name}")
                    lines.append(f"# TYPE {base_name}_bucket counter")
                    
                    # Simple bucket implementation
                    buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, "+Inf"]
                    for bucket in buckets:
                        if bucket == "+Inf":
                            bucket_count = count
                        else:
                            bucket_count = sum(1 for v in values if v <= bucket)
                        lines.append(f'{base_name}_bucket{{le="{bucket}"}} {bucket_count}')
        
        return "\n".join(lines) + "\n"
    
    def get_metrics_dict(self) -> Dict[str, Any]:
        """Get metrics as dictionary for JSON export"""
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {},
            "summary": {
                "total_http_requests": self.http_requests_total,
                "total_http_errors": self.http_errors_total,
                "avg_response_time": (
                    self.http_request_duration_sum / self.http_request_duration_count 
                    if self.http_request_duration_count > 0 else 0
                ),
                "total_database_queries": self.database_queries_total,
                "avg_query_time": (
                    self.database_query_duration_sum / self.database_queries_total 
                    if self.database_queries_total > 0 else 0
                ),
                "cache_hit_rate": (
                    self.cache_hits / self.cache_operations_total 
                    if self.cache_operations_total > 0 else 0
                ),
                "active_sessions": self.active_sessions,
                "story_generation_requests": self.story_generation_requests,
                "agent_coordination_events": self.agent_coordination_events,
                "character_interactions": self.character_interactions,
                "narrative_quality_score": self.narrative_quality_score
            }
        }
        
        for metric in self.metrics.values():
            metric_data = {
                "type": metric.metric_type.value,
                "value": metric.value,
                "labels": metric.labels,
                "timestamp": metric.timestamp
            }
            
            if metric.name not in result["metrics"]:
                result["metrics"][metric.name] = []
            result["metrics"][metric.name].append(metric_data)
        
        return result

# Global metrics collector instance
metrics_collector = PrometheusMetricsCollector()

# Context manager for request timing
@asynccontextmanager
async def time_request(method: str, endpoint: str):
    """Context manager for timing HTTP requests"""
    start_time = time.time()
    status_code = 200
    
    try:
        yield
    except Exception:
        status_code = 500
        raise
    finally:
        duration = time.time() - start_time
        metrics_collector.record_http_request(method, endpoint, status_code, duration)

# Decorator for timing functions
def time_operation(operation_name: str, labels: Dict[str, str] = None):
    """Decorator for timing operations"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return result
            except Exception:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                operation_labels = (labels or {}).copy()
                operation_labels["success"] = str(success).lower()
                metrics_collector.observe_histogram(f"{operation_name}_duration_seconds", duration, operation_labels)
                metrics_collector.increment_counter(f"{operation_name}_total", operation_labels)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else lambda *args, **kwargs: asyncio.run(async_wrapper(*args, **kwargs))
    return decorator

# FastAPI integration
def setup_prometheus_endpoint(app: FastAPI):
    """Setup Prometheus metrics endpoint in FastAPI app"""
    
    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics_endpoint():
        """Prometheus metrics endpoint"""
        # Collect current system metrics
        metrics_collector.collect_system_metrics()
        
        # Return metrics in Prometheus format
        return metrics_collector.get_metrics_text()
    
    @app.get("/metrics/json")
    async def metrics_json_endpoint():
        """JSON metrics endpoint for debugging"""
        metrics_collector.collect_system_metrics()
        return metrics_collector.get_metrics_dict()
    
    # Middleware to automatically track HTTP requests
    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        metrics_collector.record_http_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration_seconds=duration
        )
        
        return response
    
    logger.info("Prometheus metrics endpoint configured at /metrics")

# Background metrics collection
async def start_background_collection(interval_seconds: int = 15):
    """Start background metrics collection"""
    async def collection_loop():
        while True:
            try:
                metrics_collector.collect_system_metrics()
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(interval_seconds)
    
    # Start the collection task
    task = asyncio.create_task(collection_loop())
    logger.info(f"Started background metrics collection (interval: {interval_seconds}s)")
    return task

# Helper functions for specific Novel Engine metrics
def record_story_generation_success(story_type: str, duration_seconds: float, quality_score: float):
    """Record successful story generation"""
    metrics_collector.record_story_generation(story_type, duration_seconds, True, quality_score)

def record_story_generation_failure(story_type: str, duration_seconds: float):
    """Record failed story generation"""
    metrics_collector.record_story_generation(story_type, duration_seconds, False)

def record_agent_coordination_event(event_type: str, agent_count: int, duration_seconds: float):
    """Record agent coordination event"""
    metrics_collector.record_agent_coordination(event_type, agent_count, duration_seconds)

def record_character_interaction_success(interaction_type: str, character_count: int):
    """Record successful character interaction"""
    metrics_collector.record_character_interaction(interaction_type, character_count, True)

def record_character_interaction_failure(interaction_type: str, character_count: int):
    """Record failed character interaction"""
    metrics_collector.record_character_interaction(interaction_type, character_count, False)

def update_active_sessions(count: int):
    """Update active sessions count"""
    metrics_collector.set_active_sessions(count)

def update_database_connections(count: int):
    """Update database connections count"""
    metrics_collector.set_database_connections(count)

__all__ = [
    'PrometheusMetricsCollector',
    'metrics_collector',
    'time_request',
    'time_operation',
    'setup_prometheus_endpoint',
    'start_background_collection',
    'record_story_generation_success',
    'record_story_generation_failure',
    'record_agent_coordination_event',
    'record_character_interaction_success',
    'record_character_interaction_failure',
    'update_active_sessions',
    'update_database_connections'
]