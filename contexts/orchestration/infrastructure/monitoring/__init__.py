#!/usr/bin/env python3
"""
Turn Orchestration Monitoring Infrastructure

Comprehensive observability infrastructure for the M10 Observability & Security system.

This package provides:
- Prometheus metrics collection and export
- OpenTelemetry distributed tracing integration
- Performance monitoring and alerting
- Business KPI tracking and analysis

The monitoring infrastructure integrates with the existing PerformanceTracker
domain service to provide enterprise-grade observability capabilities.
"""

import logging

from .metrics_middleware import PrometheusMiddleware
from .prometheus_collector import PrometheusMetricsCollector

try:
    from .tracing import NovelEngineTracingConfig, initialize_tracing
    from .tracing_middleware import setup_fastapi_tracing
except ImportError as tracing_error:  # pragma: no cover - fallback when otel missing
    logging.getLogger(__name__).warning(
        "OpenTelemetry dependencies unavailable (%s); tracing will be disabled.",
        tracing_error,
    )

    class NovelEngineTracingConfig:  # type: ignore[override]
        def __init__(self, *_, **__):
            pass

    def initialize_tracing(*_, **__):
        return None

    def setup_fastapi_tracing(app, *_args, **_kwargs):
        return app


__all__ = [
    "PrometheusMetricsCollector",
    "PrometheusMiddleware",
    "NovelEngineTracingConfig",
    "initialize_tracing",
    "setup_fastapi_tracing",
]
