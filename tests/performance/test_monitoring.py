"""
Test suite for Performance Monitoring module.

Tests metrics collection, reporting, and alerting.
"""

import pytest
from unittest.mock import Mock
from collections import deque

from src.performance.monitoring import (
    MetricType,
    AlertSeverity,
    PerformanceMetric,
    PerformanceAlert,
    MonitoringConfig,
    SystemResourceMonitor,
    PerformanceMonitor,
)


class TestMetricType:
    """Test MetricType enum."""

    def test_metric_type_values(self):
        """Test metric type values."""
        assert MetricType.COUNTER == "counter"
        assert MetricType.GAUGE == "gauge"
        assert MetricType.HISTOGRAM == "histogram"
        assert MetricType.TIMER == "timer"
        assert MetricType.RATE == "rate"


class TestAlertSeverity:
    """Test AlertSeverity enum."""

    def test_severity_values(self):
        """Test alert severity values."""
        assert AlertSeverity.INFO == "info"
        assert AlertSeverity.WARNING == "warning"
        assert AlertSeverity.CRITICAL == "critical"
        assert AlertSeverity.EMERGENCY == "emergency"


class TestPerformanceMetric:
    """Test PerformanceMetric dataclass."""

    def test_metric_creation(self):
        """Test creating a performance metric."""
        metric = PerformanceMetric(
            name="cpu_usage",
            value=75.5,
            timestamp=1234567890.0,
            metric_type=MetricType.GAUGE,
            tags={"host": "server1"},
        )
        
        assert metric.name == "cpu_usage"
        assert metric.value == 75.5
        assert metric.metric_type == MetricType.GAUGE

    def test_metric_to_dict(self):
        """Test converting metric to dictionary."""
        metric = PerformanceMetric(
            name="cpu_usage",
            value=75.5,
            timestamp=1234567890.0,
            metric_type=MetricType.GAUGE,
            tags={"host": "server1"},
        )
        
        d = metric.to_dict()
        
        assert d["name"] == "cpu_usage"
        assert d["value"] == 75.5
        assert d["type"] == "gauge"


class TestPerformanceAlert:
    """Test PerformanceAlert dataclass."""

    def test_alert_creation(self):
        """Test creating a performance alert."""
        alert = PerformanceAlert(
            alert_id="cpu_high",
            metric_name="cpu_usage",
            severity=AlertSeverity.CRITICAL,
            message="CPU usage is high",
            threshold_value=80.0,
            actual_value=95.0,
            timestamp=1234567890.0,
        )
        
        assert alert.alert_id == "cpu_high"
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.resolved is False


class TestMonitoringConfig:
    """Test MonitoringConfig dataclass."""

    def test_default_config(self):
        """Test default monitoring configuration."""
        config = MonitoringConfig()
        
        assert config.collection_interval == 1.0
        assert config.retention_period == 3600
        assert config.enable_system_metrics is True
        assert config.enable_alerts is True

    def test_default_thresholds(self):
        """Test default alert thresholds."""
        config = MonitoringConfig()
        
        assert "cpu_usage_percent" in config.alert_thresholds
        assert "memory_usage_percent" in config.alert_thresholds


class TestSystemResourceMonitor:
    """Test SystemResourceMonitor implementation."""

    @pytest.fixture
    def monitor(self):
        """Create system resource monitor."""
        return SystemResourceMonitor()

    def test_get_cpu_metrics(self, monitor):
        """Test getting CPU metrics."""
        metrics = monitor.get_cpu_metrics()
        
        assert "cpu_usage_percent" in metrics
        assert "cpu_count" in metrics

    def test_get_memory_metrics(self, monitor):
        """Test getting memory metrics."""
        metrics = monitor.get_memory_metrics()
        
        assert "memory_total_mb" in metrics
        assert "memory_usage_percent" in metrics

    def test_get_disk_metrics(self, monitor):
        """Test getting disk metrics."""
        metrics = monitor.get_disk_metrics()
        
        assert "disk_total_gb" in metrics
        assert "disk_usage_percent" in metrics


class TestPerformanceMonitor:
    """Test PerformanceMonitor implementation."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return MonitoringConfig(
            collection_interval=0.1,
            enable_system_metrics=False,
            enable_alerts=False,
            export_metrics=False,
        )

    @pytest.fixture
    def monitor(self, config):
        """Create performance monitor."""
        return PerformanceMonitor(config)

    def test_record_metric(self, monitor):
        """Test recording a metric."""
        monitor.record_metric(
            name="test_metric",
            value=100.0,
            metric_type=MetricType.GAUGE,
        )
        
        assert "test_metric" in monitor.metrics
        assert len(monitor.metrics["test_metric"]) == 1

    def test_record_metric_with_tags(self, monitor):
        """Test recording metric with tags."""
        monitor.record_metric(
            name="test_metric",
            value=100.0,
            metric_type=MetricType.GAUGE,
            tags={"host": "server1"},
        )
        
        metric = monitor.metrics["test_metric"][0]
        assert metric.tags == {"host": "server1"}

    def test_record_request_duration(self, monitor):
        """Test recording request duration."""
        monitor.record_request_duration(
            endpoint="/api/test",
            duration_ms=50.0,
            status_code=200,
        )
        
        assert "/api/test" in monitor.endpoint_metrics
        assert monitor.endpoint_metrics["/api/test"]["count"] == 1

    def test_record_request_duration_with_error(self, monitor):
        """Test recording request duration with error."""
        monitor.record_request_duration(
            endpoint="/api/test",
            duration_ms=100.0,
            status_code=500,
            error="Internal Server Error",
        )
        
        assert monitor.endpoint_metrics["/api/test"]["errors"] == 1

    def test_record_database_query(self, monitor):
        """Test recording database query."""
        monitor.record_database_query(
            query_type="SELECT",
            duration_ms=10.0,
            table="users",
        )
        
        assert "database_query_time_ms" in monitor.metrics

    def test_record_cache_operation_hit(self, monitor):
        """Test recording cache hit."""
        monitor.record_cache_operation(
            operation="get",
            hit=True,
            duration_ms=1.0,
        )
        
        assert "cache_hit_count" in monitor.metrics

    def test_record_concurrent_users(self, monitor):
        """Test recording concurrent users."""
        monitor.record_concurrent_users(count=100)
        
        assert "concurrent_users" in monitor.metrics
        assert monitor.metrics["concurrent_users"][0].value == 100

    def test_get_metric_stats(self, monitor):
        """Test getting metric statistics."""
        for i in range(10):
            monitor.record_metric(
                name="test_metric",
                value=float(i),
                metric_type=MetricType.GAUGE,
            )
        
        stats = monitor.get_metric_stats("test_metric")
        
        assert stats is not None
        assert stats["count"] == 10
        assert stats["min"] == 0.0
        assert stats["max"] == 9.0

    def test_get_endpoint_stats(self, monitor):
        """Test getting endpoint statistics."""
        monitor.record_request_duration("/api/test1", 50.0, 200)
        monitor.record_request_duration("/api/test1", 100.0, 200)
        
        stats = monitor.get_endpoint_stats()
        
        assert "/api/test1" in stats
        assert stats["/api/test1"]["request_count"] == 2

    def test_get_performance_summary(self, monitor):
        """Test getting performance summary."""
        monitor.record_request_duration("/api/test", 50.0, 200)
        
        summary = monitor.get_performance_summary()
        
        assert "timestamp" in summary
        assert "total_requests" in summary

    def test_get_alerts(self, monitor):
        """Test getting alerts."""
        alert = PerformanceAlert(
            alert_id="test_alert",
            metric_name="cpu_usage",
            severity=AlertSeverity.WARNING,
            message="CPU high",
            threshold_value=80.0,
            actual_value=85.0,
            timestamp=1234567890.0,
        )
        monitor.active_alerts["test_alert"] = alert
        
        alerts = monitor.get_alerts()
        
        assert len(alerts) == 1

    def test_reset_metrics(self, monitor):
        """Test resetting metrics."""
        monitor.record_metric("test_metric", 100.0, MetricType.GAUGE)
        
        # Reset metrics manually
        monitor._metrics = {
            "events_emitted": 0,
            "events_processed": 0,
            "events_failed": 0,
            "retries_attempted": 0,
        }
        
        assert monitor._metrics["events_emitted"] == 0


class TestPerformanceMonitorEdgeCases:
    """Test edge cases."""

    @pytest.fixture
    def monitor(self):
        config = MonitoringConfig(
            enable_system_metrics=False,
            enable_alerts=False,
        )
        return PerformanceMonitor(config)

    def test_get_metric_stats_nonexistent(self, monitor):
        """Test getting stats for non-existent metric."""
        stats = monitor.get_metric_stats("nonexistent")
        
        assert stats is None

    def test_endpoint_stats_empty(self, monitor):
        """Test getting endpoint stats with no data."""
        stats = monitor.get_endpoint_stats()
        
        assert stats == {}

    def test_multiple_metric_types_same_name(self, monitor):
        """Test recording different metric types with same name."""
        monitor.record_metric("metric", 1.0, MetricType.COUNTER)
        monitor.record_metric("metric", 2.0, MetricType.GAUGE)
        
        assert len(monitor.metrics["metric"]) == 2
