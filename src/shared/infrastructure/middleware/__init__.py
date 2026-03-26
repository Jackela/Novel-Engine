"""Shared infrastructure middleware.

This package contains middleware components for the Novel Engine application
including logging, correlation ID tracking, and metrics collection.
"""

from src.shared.infrastructure.middleware.correlation_middleware import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    CorrelationIdMiddleware,
    get_correlation_id,
    get_correlation_id_from_context,
    get_request_id,
)
from src.shared.infrastructure.middleware.logging_middleware import LoggingMiddleware
from src.shared.infrastructure.middleware.metrics_middleware import (
    MetricsMiddleware,
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
    start_prometheus_server,
)

__all__ = [
    # Correlation ID middleware
    "CorrelationIdMiddleware",
    "CORRELATION_ID_HEADER",
    "REQUEST_ID_HEADER",
    "get_correlation_id",
    "get_request_id",
    "get_correlation_id_from_context",
    # Logging middleware
    "LoggingMiddleware",
    # Metrics middleware
    "MetricsMiddleware",
    "start_prometheus_server",
    "http_requests_total",
    "http_request_duration_seconds",
    "http_requests_in_progress",
]
