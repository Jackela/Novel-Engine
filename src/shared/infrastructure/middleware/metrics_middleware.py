"""Prometheus metrics middleware.

This module provides middleware for collecting Prometheus metrics
for all HTTP requests including request counts and duration histograms.
"""

from typing import Awaitable, Callable

from fastapi import Request
from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Prometheus metrics
# Note: Metrics server should be started separately, not in middleware
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting Prometheus metrics.

    This middleware collects metrics for all HTTP requests including:
    - Total request count by method, endpoint, and status code
    - Request duration histogram by method and endpoint
    - Requests currently in progress

    Note: The Prometheus metrics server should be started separately
    using start_prometheus_server() function.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process the request and collect metrics.

        Args:
            request: The incoming FastAPI request.
            call_next: The next middleware or route handler in the chain.

        Returns:
            The response from the next handler in the chain.
        """
        method = request.method
        # Normalize endpoint path for metrics (remove query params)
        endpoint = request.url.path

        # Track request in progress
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        try:
            # Time the request
            with http_request_duration_seconds.labels(
                method=method, endpoint=endpoint
            ).time():
                response = await call_next(request)

            # Record request count with status code
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(response.status_code),
            ).inc()

            return response

        except Exception:
            # Record failed request with 500 status
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code="500",
            ).inc()
            raise

        finally:
            # Decrement in-progress counter
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()


def start_prometheus_server(port: int = 9090) -> None:
    """Start the Prometheus metrics HTTP server.

    This function starts a separate HTTP server that exposes Prometheus
    metrics at /metrics endpoint. It should be called once during application
    startup, not within the middleware itself.

    Args:
        port: The port number for the metrics server. Defaults to 9090.

    Example:
        ```python
        from src.shared.infrastructure.middleware.metrics_middleware import (
            start_prometheus_server
        )

        # In application startup
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            start_prometheus_server(port=9090)
            yield
        ```
    """
    from prometheus_client import start_http_server

    start_http_server(port)


__all__ = [
    "MetricsMiddleware",
    "start_prometheus_server",
    "http_requests_total",
    "http_request_duration_seconds",
    "http_requests_in_progress",
]
