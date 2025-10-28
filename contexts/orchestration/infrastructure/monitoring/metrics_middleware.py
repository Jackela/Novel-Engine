#!/usr/bin/env python3
"""
Prometheus Metrics Middleware

FastAPI middleware for automatic HTTP metrics collection and request monitoring.
Integrates with the PrometheusMetricsCollector to provide comprehensive API observability.
"""

import logging
import time
from typing import Callable, Optional

from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram, Info
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .prometheus_collector import PrometheusMetricsCollector

logger = logging.getLogger(__name__)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic Prometheus metrics collection.

    Collects comprehensive HTTP request metrics including:
    - Request count by endpoint, method, and status code
    - Request duration histograms
    - Active request tracking
    - Error rate monitoring
    - Response size tracking

    Integrates with PrometheusMetricsCollector for unified metrics collection.
    """

    def __init__(
        self,
        app: ASGIApp,
        app_name: str = "novel_engine_orchestration",
        group_paths: bool = True,
        ignored_paths: Optional[list] = None,
        metrics_collector: Optional[PrometheusMetricsCollector] = None,
    ):
        """
        Initialize Prometheus middleware.

        Args:
            app: FastAPI application
            app_name: Application name for metrics
            group_paths: Whether to group similar paths (e.g., /turns/{id})
            ignored_paths: List of paths to ignore in metrics
            metrics_collector: Optional existing metrics collector
        """
        super().__init__(app)
        self.app_name = app_name
        self.group_paths = group_paths
        self.ignored_paths = ignored_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/favicon.ico",
        ]

        # Use provided collector or create new one
        self.metrics_collector = metrics_collector or PrometheusMetricsCollector()

        # Initialize HTTP-specific metrics
        self._initialize_http_metrics()

        logger.info(f"PrometheusMiddleware initialized for {app_name}")

    def _initialize_http_metrics(self) -> None:
        """Initialize HTTP-specific Prometheus metrics."""

        # HTTP request metrics
        self.http_requests_total = Counter(
            f"{self.app_name}_http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status_code"],
            registry=self.metrics_collector.registry,
        )

        self.http_request_duration_seconds = Histogram(
            f"{self.app_name}_http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint", "status_code"],
            buckets=[
                0.001,
                0.005,
                0.01,
                0.025,
                0.05,
                0.1,
                0.25,
                0.5,
                1.0,
                2.5,
                5.0,
                10.0,
                float("inf"),
            ],
            registry=self.metrics_collector.registry,
        )

        self.http_requests_in_progress = Gauge(
            f"{self.app_name}_http_requests_in_progress",
            "Number of HTTP requests currently being processed",
            ["method", "endpoint"],
            registry=self.metrics_collector.registry,
        )

        self.http_request_size_bytes = Histogram(
            f"{self.app_name}_http_request_size_bytes",
            "HTTP request size in bytes",
            ["method", "endpoint"],
            buckets=[64, 256, 1024, 4096, 16384, 65536, 262144, 1048576, float("inf")],
            registry=self.metrics_collector.registry,
        )

        self.http_response_size_bytes = Histogram(
            f"{self.app_name}_http_response_size_bytes",
            "HTTP response size in bytes",
            ["method", "endpoint", "status_code"],
            buckets=[64, 256, 1024, 4096, 16384, 65536, 262144, 1048576, float("inf")],
            registry=self.metrics_collector.registry,
        )

        # API-specific metrics
        self.api_errors_total = Counter(
            f"{self.app_name}_api_errors_total",
            "Total API errors",
            ["endpoint", "error_type", "status_code"],
            registry=self.metrics_collector.registry,
        )

        self.api_response_time_percentiles = Gauge(
            f"{self.app_name}_api_response_time_percentiles_seconds",
            "API response time percentiles",
            ["endpoint", "percentile"],
            registry=self.metrics_collector.registry,
        )

        # Application info
        self.app_info = Info(
            f"{self.app_name}_application_info",
            "Application information",
            registry=self.metrics_collector.registry,
        )

        # Set application info
        self.app_info.info(
            {
                "version": "2.0.0",
                "component": "turn_orchestration",
                "environment": "production",  # Could be from config
            }
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process HTTP request and collect metrics.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response with metrics collected
        """
        # Skip metrics collection for ignored paths
        if request.url.path in self.ignored_paths:
            return await call_next(request)

        # Extract request information
        method = request.method
        path = (
            self._get_grouped_path(request.url.path)
            if self.group_paths
            else request.url.path
        )

        # Get request size
        request_size = 0
        if hasattr(request, "headers") and "content-length" in request.headers:
            try:
                request_size = int(request.headers["content-length"])
            except (ValueError, TypeError):
                request_size = 0

        # Start timing
        start_time = time.time()

        # Increment in-progress requests
        self.http_requests_in_progress.labels(method=method, endpoint=path).inc()

        try:
            # Process request
            response = await call_next(request)

            # Calculate metrics
            duration = time.time() - start_time
            status_code = str(response.status_code)

            # Get response size
            response_size = 0
            if hasattr(response, "headers") and "content-length" in response.headers:
                try:
                    response_size = int(response.headers["content-length"])
                except (ValueError, TypeError):
                    # Estimate size for chunked responses
                    response_size = (
                        len(str(response.__dict__))
                        if hasattr(response, "__dict__")
                        else 0
                    )

            # Record metrics
            self._record_request_metrics(
                method=method,
                path=path,
                status_code=status_code,
                duration=duration,
                request_size=request_size,
                response_size=response_size,
                error_occurred=response.status_code >= 400,
            )

            return response

        except Exception as e:
            # Handle exceptions during request processing
            duration = time.time() - start_time

            # Record error metrics
            self._record_request_metrics(
                method=method,
                path=path,
                status_code="500",
                duration=duration,
                request_size=request_size,
                response_size=0,
                error_occurred=True,
                exception=e,
            )

            # Re-raise the exception
            raise

        finally:
            # Decrement in-progress requests
            self.http_requests_in_progress.labels(method=method, endpoint=path).dec()

    def _record_request_metrics(
        self,
        method: str,
        path: str,
        status_code: str,
        duration: float,
        request_size: int,
        response_size: int,
        error_occurred: bool,
        exception: Optional[Exception] = None,
    ) -> None:
        """
        Record metrics for HTTP request.

        Args:
            method: HTTP method
            path: Request path
            status_code: HTTP status code
            duration: Request duration in seconds
            request_size: Request size in bytes
            response_size: Response size in bytes
            error_occurred: Whether an error occurred
            exception: Exception if one occurred
        """
        # Basic HTTP metrics
        self.http_requests_total.labels(
            method=method, endpoint=path, status_code=status_code
        ).inc()

        self.http_request_duration_seconds.labels(
            method=method, endpoint=path, status_code=status_code
        ).observe(duration)

        if request_size > 0:
            self.http_request_size_bytes.labels(method=method, endpoint=path).observe(
                request_size
            )

        if response_size > 0:
            self.http_response_size_bytes.labels(
                method=method, endpoint=path, status_code=status_code
            ).observe(response_size)

        # Error tracking
        if error_occurred:
            error_type = (
                "client_error" if status_code.startswith("4") else "server_error"
            )
            if exception:
                error_type = f"{error_type}_{type(exception).__name__}"

            self.api_errors_total.labels(
                endpoint=path, error_type=error_type, status_code=status_code
            ).inc()

            # Record error in main metrics collector
            self.metrics_collector.record_error(
                error_type=error_type,
                severity="high" if status_code.startswith("5") else "medium",
                component="http_api",
                recovery_attempted=False,
            )

        # Log significant events
        if duration > 10.0:  # Slow requests
            logger.warning(f"Slow request: {method} {path} took {duration:.2f}s")
        elif error_occurred:
            logger.error(f"Request error: {method} {path} -> {status_code}")
        elif duration > 1.0:  # Moderately slow requests
            logger.info(f"Request: {method} {path} took {duration:.3f}s")

    def _get_grouped_path(self, path: str) -> str:
        """
        Group similar paths for metrics labeling.

        Converts paths like /v1/turns/123 to /v1/turns/{id}
        to prevent high cardinality in metrics labels.

        Args:
            path: Original request path

        Returns:
            Grouped path for metrics
        """
        import re

        # Common patterns to group
        patterns = [
            # UUIDs and IDs
            (
                r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                "/{uuid}",
            ),
            (r"/\d+", "/{id}"),
            # Turn-specific patterns
            (r"/turns/[^/]+/status", "/turns/{turn_id}/status"),
            (r"/turns/[^/]+/cancel", "/turns/{turn_id}/cancel"),
            (r"/turns/[^/]+", "/turns/{turn_id}"),
        ]

        grouped_path = path
        for pattern, replacement in patterns:
            grouped_path = re.sub(pattern, replacement, grouped_path)

        return grouped_path


class MetricsRegistry:
    """
    Singleton registry for managing Prometheus metrics collectors.

    Ensures consistent metrics collection across the application
    and provides easy access to metrics collectors.
    """

    _instance = None
    _collectors = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_collector(self, name: str = "default") -> PrometheusMetricsCollector:
        """
        Get or create a metrics collector.

        Args:
            name: Collector name

        Returns:
            Prometheus metrics collector
        """
        if name not in self._collectors:
            self._collectors[name] = PrometheusMetricsCollector()
        return self._collectors[name]

    def register_collector(
        self, name: str, collector: PrometheusMetricsCollector
    ) -> None:
        """
        Register a metrics collector.

        Args:
            name: Collector name
            collector: Metrics collector instance
        """
        self._collectors[name] = collector

    def get_all_metrics_data(self) -> str:
        """
        Get metrics data from all registered collectors.

        Returns:
            Combined metrics data
        """
        all_data = []
        for name, collector in self._collectors.items():
            try:
                data = collector.get_metrics_data()
                if data.strip():  # Only add non-empty data
                    all_data.append(data)
            except Exception as e:
                logger.error(f"Error getting metrics from collector {name}: {e}")

        return "\n".join(all_data)


# Global registry instance
metrics_registry = MetricsRegistry()
