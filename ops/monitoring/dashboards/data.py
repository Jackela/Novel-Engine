#!/usr/bin/env python3
"""
Dashboard Data Collector for Novel Engine Monitoring

Provides data collection and aggregation for comprehensive monitoring dashboards:
- Executive dashboards for business metrics
- Operational dashboards for system health
- Performance dashboards for optimization
- Security dashboards for threat monitoring
"""

import asyncio
import json
import logging
import os
import statistics
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class MetricData:
    """Individual metric data point"""

    name: str
    value: Union[float, int]
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""
    description: str = ""


@dataclass
class TimeSeriesData:
    """Time series data for a metric"""

    metric_name: str
    data_points: List[MetricData]
    aggregation_window: str = "1m"  # 1m, 5m, 1h, 1d

    def get_latest_value(self) -> Optional[float]:
        """Get the latest metric value"""
        if not self.data_points:
            return None
        return self.data_points[-1].value

    def get_average(self, minutes: int = 60) -> Optional[float]:
        """Get average value over specified time period"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        recent_points = [
            point.value for point in self.data_points if point.timestamp >= cutoff_time
        ]

        if not recent_points:
            return None

        return statistics.mean(recent_points)

    def get_percentile(self, percentile: int, minutes: int = 60) -> Optional[float]:
        """Get percentile value over specified time period"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        recent_points = [
            point.value for point in self.data_points if point.timestamp >= cutoff_time
        ]

        if not recent_points:
            return None

        if percentile == 50:
            return statistics.median(recent_points)

        sorted_points = sorted(recent_points)
        index = int((percentile / 100.0) * (len(sorted_points) - 1))
        return sorted_points[index]


@dataclass
class DashboardWidget:
    """Dashboard widget configuration"""

    id: str
    title: str
    widget_type: str  # "metric", "chart", "table", "status", "gauge"
    metric_queries: List[str]
    time_range: str = "1h"
    refresh_interval: int = 30  # seconds
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Dashboard:
    """Dashboard configuration"""

    id: str
    title: str
    description: str
    category: str  # "executive", "operational", "performance", "security"
    widgets: List[DashboardWidget]
    tags: List[str] = field(default_factory=list)
    auto_refresh: bool = True


@dataclass
class DashboardConfig:
    """Configuration for dashboard system"""

    data_retention_hours: int = 168  # 7 days
    aggregation_intervals: List[str] = field(
        default_factory=lambda: ["1m", "5m", "1h", "1d"]
    )
    max_data_points_per_series: int = 1440  # 24 hours of minute data
    enable_real_time: bool = True
    export_enabled: bool = False
    export_path: str = "data/dashboard_exports"


class DashboardDataCollector:
    """Collects and manages data for monitoring dashboards"""

    def __init__(self, config: DashboardConfig):
        self.config = config

        # Data storage
        self.time_series_data: Dict[str, TimeSeriesData] = {}
        self.aggregated_data: Dict[
            str, Dict[str, TimeSeriesData]
        ] = {}  # interval -> metric -> data

        # Dashboard definitions
        self.dashboards: Dict[str, Dashboard] = {}

        # Background tasks
        self.running = False
        self.aggregation_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None

        # Initialize default dashboards
        self._create_default_dashboards()

        logger.info("Dashboard data collector initialized")

    def add_metric_data(self, metric_data: MetricData):
        """Add a metric data point"""
        metric_name = metric_data.name

        if metric_name not in self.time_series_data:
            self.time_series_data[metric_name] = TimeSeriesData(
                metric_name=metric_name,
                data_points=deque(maxlen=self.config.max_data_points_per_series),
            )

        self.time_series_data[metric_name].data_points.append(metric_data)

    def get_metric_data(
        self, metric_name: str, time_range: str = "1h"
    ) -> Optional[TimeSeriesData]:
        """Get metric data for specified time range"""
        if metric_name not in self.time_series_data:
            return None

        # Parse time range
        duration_minutes = self._parse_time_range(time_range)
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=duration_minutes)

        # Filter data points
        series = self.time_series_data[metric_name]
        filtered_points = [
            point for point in series.data_points if point.timestamp >= cutoff_time
        ]

        return TimeSeriesData(
            metric_name=metric_name,
            data_points=filtered_points,
            aggregation_window=time_range,
        )

    def _parse_time_range(self, time_range: str) -> int:
        """Parse time range string to minutes"""
        time_range = time_range.lower()

        if time_range.endswith("m"):
            return int(time_range[:-1])
        elif time_range.endswith("h"):
            return int(time_range[:-1]) * 60
        elif time_range.endswith("d"):
            return int(time_range[:-1]) * 24 * 60
        else:
            return 60  # Default to 1 hour

    async def start(self):
        """Start background data processing"""
        if self.running:
            return

        self.running = True

        # Start background tasks
        self.aggregation_task = asyncio.create_task(self._aggregation_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("Dashboard data collector started")

    async def stop(self):
        """Stop background data processing"""
        self.running = False

        if self.aggregation_task:
            self.aggregation_task.cancel()
            try:
                await self.aggregation_task
            except asyncio.CancelledError:
                logger.debug("Aggregation task cancelled", exc_info=True)

        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                logger.debug("Cleanup task cancelled", exc_info=True)

        logger.info("Dashboard data collector stopped")

    async def _aggregation_loop(self):
        """Background task for data aggregation"""
        while self.running:
            try:
                await self._aggregate_data()
                await asyncio.sleep(60)  # Aggregate every minute
            except Exception as e:
                logger.error(f"Error in aggregation loop: {e}")
                await asyncio.sleep(60)

    async def _cleanup_loop(self):
        """Background task for data cleanup"""
        while self.running:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Cleanup every hour
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)

    async def _aggregate_data(self):
        """Aggregate raw data into different time intervals"""
        current_time = datetime.now(timezone.utc)

        for interval in self.config.aggregation_intervals:
            if interval not in self.aggregated_data:
                self.aggregated_data[interval] = {}

            for metric_name, series in self.time_series_data.items():
                if metric_name not in self.aggregated_data[interval]:
                    self.aggregated_data[interval][metric_name] = TimeSeriesData(
                        metric_name=metric_name,
                        data_points=deque(
                            maxlen=self.config.max_data_points_per_series
                        ),
                        aggregation_window=interval,
                    )

                # Aggregate data for this interval
                aggregated_series = self.aggregated_data[interval][metric_name]
                await self._aggregate_metric_for_interval(
                    series, aggregated_series, interval, current_time
                )

    async def _aggregate_metric_for_interval(
        self,
        raw_series: TimeSeriesData,
        aggregated_series: TimeSeriesData,
        interval: str,
        current_time: datetime,
    ):
        """Aggregate a metric for a specific interval"""
        interval_minutes = self._parse_time_range(interval)

        # Check if we need a new aggregated data point
        if aggregated_series.data_points:
            last_point = aggregated_series.data_points[-1]
            time_since_last = (current_time - last_point.timestamp).total_seconds() / 60

            if time_since_last < interval_minutes:
                return  # Not time for new aggregation yet

        # Aggregate data from the interval
        start_time = current_time - timedelta(minutes=interval_minutes)
        relevant_points = [
            point
            for point in raw_series.data_points
            if start_time <= point.timestamp <= current_time
        ]

        if not relevant_points:
            return

        # Calculate aggregated value (average for now)
        values = [point.value for point in relevant_points]
        aggregated_value = statistics.mean(values)

        # Create aggregated data point
        aggregated_point = MetricData(
            name=raw_series.metric_name,
            value=aggregated_value,
            timestamp=current_time,
            labels=relevant_points[0].labels if relevant_points else {},
            unit=relevant_points[0].unit if relevant_points else "",
            description=relevant_points[0].description if relevant_points else "",
        )

        aggregated_series.data_points.append(aggregated_point)

    async def _cleanup_old_data(self):
        """Clean up old data beyond retention period"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            hours=self.config.data_retention_hours
        )

        # Clean raw data
        for series in self.time_series_data.values():
            while series.data_points and series.data_points[0].timestamp < cutoff_time:
                series.data_points.popleft()

        # Clean aggregated data
        for interval_data in self.aggregated_data.values():
            for series in interval_data.values():
                while (
                    series.data_points and series.data_points[0].timestamp < cutoff_time
                ):
                    series.data_points.popleft()

    def _create_default_dashboards(self):
        """Create default monitoring dashboards"""

        # Executive Dashboard
        executive_dashboard = Dashboard(
            id="executive",
            title="Executive Dashboard",
            description="High-level business metrics and system overview",
            category="executive",
            widgets=[
                DashboardWidget(
                    id="system_health",
                    title="System Health",
                    widget_type="status",
                    metric_queries=["system_health_score"],
                    config={"thresholds": {"good": 80, "warning": 60}},
                ),
                DashboardWidget(
                    id="active_users",
                    title="Active Users",
                    widget_type="metric",
                    metric_queries=["active_sessions"],
                    config={"format": "number"},
                ),
                DashboardWidget(
                    id="request_rate",
                    title="Request Rate",
                    widget_type="chart",
                    metric_queries=["http_requests_total"],
                    time_range="24h",
                    config={"chart_type": "line"},
                ),
                DashboardWidget(
                    id="error_rate",
                    title="Error Rate",
                    widget_type="gauge",
                    metric_queries=["http_error_rate_percent"],
                    config={"max_value": 5, "thresholds": {"good": 1, "warning": 3}},
                ),
                DashboardWidget(
                    id="story_generation_stats",
                    title="Story Generation",
                    widget_type="table",
                    metric_queries=[
                        "story_generation_requests_total",
                        "story_generation_success_rate",
                    ],
                    time_range="24h",
                ),
            ],
        )

        # Operational Dashboard
        operational_dashboard = Dashboard(
            id="operational",
            title="Operational Dashboard",
            description="System health and infrastructure monitoring",
            category="operational",
            widgets=[
                DashboardWidget(
                    id="cpu_usage",
                    title="CPU Usage",
                    widget_type="chart",
                    metric_queries=["system_cpu_usage_percent"],
                    time_range="1h",
                    config={
                        "chart_type": "area",
                        "thresholds": {"warning": 70, "critical": 90},
                    },
                ),
                DashboardWidget(
                    id="memory_usage",
                    title="Memory Usage",
                    widget_type="chart",
                    metric_queries=["system_memory_usage_percent"],
                    time_range="1h",
                    config={
                        "chart_type": "area",
                        "thresholds": {"warning": 80, "critical": 95},
                    },
                ),
                DashboardWidget(
                    id="disk_usage",
                    title="Disk Usage",
                    widget_type="gauge",
                    metric_queries=["system_disk_usage_percent"],
                    config={
                        "max_value": 100,
                        "thresholds": {"warning": 85, "critical": 95},
                    },
                ),
                DashboardWidget(
                    id="network_io",
                    title="Network I/O",
                    widget_type="chart",
                    metric_queries=["network_bytes_sent", "network_bytes_recv"],
                    time_range="1h",
                    config={"chart_type": "line"},
                ),
                DashboardWidget(
                    id="database_connections",
                    title="Database Connections",
                    widget_type="metric",
                    metric_queries=["database_connections_active"],
                    config={"format": "number"},
                ),
                DashboardWidget(
                    id="active_alerts",
                    title="Active Alerts",
                    widget_type="table",
                    metric_queries=["active_alerts_count"],
                    time_range="1h",
                ),
            ],
        )

        # Performance Dashboard
        performance_dashboard = Dashboard(
            id="performance",
            title="Performance Dashboard",
            description="Application performance metrics and optimization data",
            category="performance",
            widgets=[
                DashboardWidget(
                    id="response_times",
                    title="Response Times",
                    widget_type="chart",
                    metric_queries=["http_request_duration_seconds"],
                    time_range="1h",
                    config={
                        "chart_type": "line",
                        "aggregation": "percentile",
                        "percentiles": [50, 95, 99],
                    },
                ),
                DashboardWidget(
                    id="throughput",
                    title="Throughput (req/s)",
                    widget_type="chart",
                    metric_queries=["http_requests_per_second"],
                    time_range="1h",
                    config={"chart_type": "area"},
                ),
                DashboardWidget(
                    id="database_performance",
                    title="Database Query Time",
                    widget_type="chart",
                    metric_queries=["database_query_duration_seconds"],
                    time_range="1h",
                    config={
                        "chart_type": "line",
                        "aggregation": "percentile",
                        "percentiles": [50, 95],
                    },
                ),
                DashboardWidget(
                    id="cache_hit_rate",
                    title="Cache Hit Rate",
                    widget_type="gauge",
                    metric_queries=["cache_hit_rate_percent"],
                    config={
                        "max_value": 100,
                        "thresholds": {"good": 80, "warning": 60},
                    },
                ),
                DashboardWidget(
                    id="story_generation_performance",
                    title="Story Generation Performance",
                    widget_type="chart",
                    metric_queries=["story_generation_duration_seconds"],
                    time_range="1h",
                    config={
                        "chart_type": "line",
                        "aggregation": "percentile",
                        "percentiles": [50, 95],
                    },
                ),
                DashboardWidget(
                    id="agent_coordination_time",
                    title="Agent Coordination Time",
                    widget_type="metric",
                    metric_queries=["agent_coordination_duration_seconds"],
                    config={"format": "duration", "aggregation": "average"},
                ),
            ],
        )

        # Security Dashboard
        security_dashboard = Dashboard(
            id="security",
            title="Security Dashboard",
            description="Security monitoring and threat detection",
            category="security",
            widgets=[
                DashboardWidget(
                    id="failed_authentications",
                    title="Failed Authentications",
                    widget_type="chart",
                    metric_queries=["authentication_failures_total"],
                    time_range="24h",
                    config={"chart_type": "bar"},
                ),
                DashboardWidget(
                    id="suspicious_requests",
                    title="Suspicious Requests",
                    widget_type="metric",
                    metric_queries=["suspicious_requests_total"],
                    time_range="1h",
                    config={"format": "number"},
                ),
                DashboardWidget(
                    id="security_alerts",
                    title="Security Alerts",
                    widget_type="table",
                    metric_queries=["security_alerts"],
                    time_range="24h",
                ),
                DashboardWidget(
                    id="request_rate_by_ip",
                    title="Request Rate by IP",
                    widget_type="table",
                    metric_queries=["http_requests_by_ip"],
                    time_range="1h",
                    config={"sort_by": "request_count", "limit": 10},
                ),
                DashboardWidget(
                    id="error_4xx_rate",
                    title="4xx Error Rate",
                    widget_type="chart",
                    metric_queries=["http_4xx_errors_total"],
                    time_range="24h",
                    config={"chart_type": "line"},
                ),
            ],
        )

        # Store dashboards
        self.dashboards[executive_dashboard.id] = executive_dashboard
        self.dashboards[operational_dashboard.id] = operational_dashboard
        self.dashboards[performance_dashboard.id] = performance_dashboard
        self.dashboards[security_dashboard.id] = security_dashboard

        logger.info(f"Created {len(self.dashboards)} default dashboards")

    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get dashboard configuration"""
        return self.dashboards.get(dashboard_id)

    def list_dashboards(self) -> List[Dashboard]:
        """List all available dashboards"""
        return list(self.dashboards.values())

    def get_dashboard_data(self, dashboard_id: str) -> Dict[str, Any]:
        """Get complete dashboard data"""
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            return {}

        dashboard_data = {
            "dashboard": asdict(dashboard),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "widgets": {},
        }

        # Get data for each widget
        for widget in dashboard.widgets:
            widget_data = self._get_widget_data(widget)
            dashboard_data["widgets"][widget.id] = widget_data

        return dashboard_data

    def _get_widget_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for a specific widget"""
        widget_data = {"widget": asdict(widget), "data": {}, "status": "ok"}

        try:
            # Get data for each metric query
            for metric_query in widget.metric_queries:
                metric_data = self.get_metric_data(metric_query, widget.time_range)

                if metric_data:
                    widget_data["data"][metric_query] = {
                        "latest_value": metric_data.get_latest_value(),
                        "average": metric_data.get_average(),
                        "p50": metric_data.get_percentile(50),
                        "p95": metric_data.get_percentile(95),
                        "p99": metric_data.get_percentile(99),
                        "data_points": [
                            {
                                "timestamp": point.timestamp.isoformat(),
                                "value": point.value,
                                "labels": point.labels,
                            }
                            for point in metric_data.data_points
                        ],
                    }
                else:
                    widget_data["data"][metric_query] = {
                        "latest_value": None,
                        "average": None,
                        "p50": None,
                        "p95": None,
                        "p99": None,
                        "data_points": [],
                    }
                    widget_data["status"] = "no_data"

        except Exception as e:
            logger.error(f"Error getting widget data for {widget.id}: {e}")
            widget_data["status"] = "error"
            widget_data["error"] = str(e)

        return widget_data

    def add_dashboard(self, dashboard: Dashboard):
        """Add a custom dashboard"""
        self.dashboards[dashboard.id] = dashboard
        logger.info(f"Added dashboard: {dashboard.id}")

    def remove_dashboard(self, dashboard_id: str):
        """Remove a dashboard"""
        if dashboard_id in self.dashboards:
            del self.dashboards[dashboard_id]
            logger.info(f"Removed dashboard: {dashboard_id}")

    def export_dashboard_data(
        self, dashboard_id: str, format: str = "json"
    ) -> Optional[str]:
        """Export dashboard data"""
        if not self.config.export_enabled:
            return None

        dashboard_data = self.get_dashboard_data(dashboard_id)
        if not dashboard_data:
            return None

        # Ensure export directory exists
        os.makedirs(self.config.export_path, exist_ok=True)

        # Generate filename
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{dashboard_id}_{timestamp}.{format}"
        filepath = os.path.join(self.config.export_path, filename)

        try:
            if format == "json":
                with open(filepath, "w") as f:
                    json.dump(dashboard_data, f, indent=2, default=str)
            else:
                logger.error(f"Unsupported export format: {format}")
                return None

            logger.info(f"Exported dashboard data to: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error exporting dashboard data: {e}")
            return None

    def get_system_overview(self) -> Dict[str, Any]:
        """Get system overview data for quick status check"""
        current_time = datetime.now(timezone.utc)

        # Key metrics for overview
        key_metrics = [
            "system_cpu_usage_percent",
            "system_memory_usage_percent",
            "system_disk_usage_percent",
            "http_requests_total",
            "http_error_rate_percent",
            "active_sessions",
            "database_connections_active",
        ]

        overview = {
            "timestamp": current_time.isoformat(),
            "metrics": {},
            "status": "healthy",
        }

        for metric_name in key_metrics:
            metric_data = self.get_metric_data(metric_name, "5m")
            if metric_data:
                latest_value = metric_data.get_latest_value()
                average_value = metric_data.get_average(5)  # 5 minute average

                overview["metrics"][metric_name] = {
                    "current": latest_value,
                    "average_5m": average_value,
                }

                # Simple health assessment
                if metric_name.endswith("_percent") and latest_value:
                    if latest_value > 95:
                        overview["status"] = "critical"
                    elif latest_value > 85 and overview["status"] != "critical":
                        overview["status"] = "warning"

        return overview


# Global dashboard data collector
dashboard_collector: Optional[DashboardDataCollector] = None


def initialize_dashboard_collector(
    config: Optional[DashboardConfig] = None,
) -> DashboardDataCollector:
    """Initialize the dashboard data collector"""
    global dashboard_collector

    if config is None:
        config = DashboardConfig()

    dashboard_collector = DashboardDataCollector(config)
    return dashboard_collector


def get_dashboard_collector() -> Optional[DashboardDataCollector]:
    """Get the global dashboard data collector"""
    return dashboard_collector


__all__ = [
    "MetricData",
    "TimeSeriesData",
    "DashboardWidget",
    "Dashboard",
    "DashboardConfig",
    "DashboardDataCollector",
    "initialize_dashboard_collector",
    "get_dashboard_collector",
]
