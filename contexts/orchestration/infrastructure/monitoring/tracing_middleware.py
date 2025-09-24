#!/usr/bin/env python3
"""
OpenTelemetry FastAPI Middleware

Automatic HTTP request instrumentation and trace context management for FastAPI applications.
Integrates with Novel Engine distributed tracing system.
"""

import logging
import time
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

from fastapi import Request, Response
from opentelemetry import propagate, trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.util.http import get_excluded_urls
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .tracing import NovelEngineTracer, get_tracer

logger = logging.getLogger(__name__)


class OpenTelemetryMiddleware(BaseHTTPMiddleware):
    """
    Custom OpenTelemetry middleware for Novel Engine turn orchestration API.

    Provides enhanced HTTP request tracing with:
    - Automatic span creation for all HTTP requests
    - Trace context propagation from incoming headers
    - Integration with Novel Engine business context
    - Enhanced span attributes for monitoring and debugging
    """

    def __init__(
        self,
        app: ASGIApp,
        tracer: Optional[NovelEngineTracer] = None,
        excluded_urls: Optional[list] = None,
        trace_request_payload: bool = False,
        trace_response_payload: bool = False,
    ):
        """
        Initialize OpenTelemetry middleware.

        Args:
            app: FastAPI application
            tracer: Optional Novel Engine tracer instance
            excluded_urls: URLs to exclude from tracing
            trace_request_payload: Whether to trace request payload
            trace_response_payload: Whether to trace response payload
        """
        super().__init__(app)
        self.tracer = tracer or get_tracer()

        # Default excluded URLs for observability endpoints
        self.excluded_urls = excluded_urls or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        ]

        self.trace_request_payload = trace_request_payload
        self.trace_response_payload = trace_response_payload

        logger.info(
            "OpenTelemetryMiddleware initialized with Novel Engine tracer integration"
        )

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process HTTP request with distributed tracing.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            HTTP response with trace context
        """
        # Skip tracing for excluded URLs
        if self._should_exclude_url(request.url.path):
            return await call_next(request)

        # Extract trace context from incoming headers
        carrier = dict(request.headers)
        propagate.extract(carrier)

        # Start HTTP span
        if self.tracer:
            otel_tracer = self.tracer.tracer
        else:
            otel_tracer = trace.get_tracer(__name__)

        span_name = f"{request.method} {self._get_route_pattern(request)}"

        if otel_tracer is None:
            # If tracer is not available, continue without tracing
            response = await call_next(request)
            return response

        with otel_tracer.start_as_current_span(
            name=span_name, kind=trace.SpanKind.SERVER
        ) as span:
            # Set HTTP attributes
            self._set_http_attributes(span, request)

            # Add trace context to request scope for use by handlers
            request.scope["trace_context"] = span

            try:
                # Process request
                start_time = time.time()
                response = await call_next(request)
                duration_seconds = time.time() - start_time

                # Set response attributes
                self._set_response_attributes(span, response, duration_seconds)

                # Set span status based on HTTP status code
                if response.status_code >= 400:
                    span.set_status(
                        Status(
                            StatusCode.ERROR, f"HTTP {response.status_code}"
                        )
                    )
                else:
                    span.set_status(Status(StatusCode.OK))

                # Inject trace context into response headers for downstream services
                response_carrier: Dict[str, str] = {}
                propagate.inject(response_carrier)

                for key, value in response_carrier.items():
                    response.headers[key] = value

                return response

            except Exception as e:
                # Record exception in span
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))

                # Add error attributes
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))

                logger.error(f"Exception in HTTP request: {e}")
                raise

    def _should_exclude_url(self, url_path: str) -> bool:
        """
        Check if URL should be excluded from tracing.

        Args:
            url_path: URL path

        Returns:
            True if URL should be excluded
        """
        return any(excluded in url_path for excluded in self.excluded_urls)

    def _get_route_pattern(self, request: Request) -> str:
        """
        Get route pattern for span naming.

        Args:
            request: HTTP request

        Returns:
            Route pattern or path
        """
        # Try to get the route pattern if available
        if hasattr(request, "scope") and "route" in request.scope:
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path

        # Fallback to request path with parameter substitution
        path = request.url.path

        # Common patterns for turn orchestration API
        import re

        patterns = [
            (r"/v1/turns/[^/]+/status", "/v1/turns/{turn_id}/status"),
            (r"/v1/turns/[^/]+/cancel", "/v1/turns/{turn_id}/cancel"),
            (r"/v1/turns/[^/]+", "/v1/turns/{turn_id}"),
        ]

        for pattern, replacement in patterns:
            path = re.sub(pattern, replacement, path)

        return path

    def _set_http_attributes(self, span: trace.Span, request: Request) -> None:
        """
        Set HTTP request attributes on span.

        Args:
            span: Current span
            request: HTTP request
        """
        # Standard HTTP attributes
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))
        span.set_attribute("http.scheme", request.url.scheme)
        span.set_attribute("http.host", request.url.hostname or "unknown")
        span.set_attribute("http.target", request.url.path)

        # User agent if available
        user_agent = request.headers.get("user-agent")
        if user_agent:
            span.set_attribute("http.user_agent", user_agent)

        # Request ID for correlation
        request_id = request.headers.get("x-request-id") or str(uuid4())
        span.set_attribute("http.request_id", request_id)

        # Content length if available
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                span.set_attribute(
                    "http.request_content_length", int(content_length)
                )
            except (ValueError, TypeError):
                pass

        # Trace request payload if configured
        if self.trace_request_payload:
            # This would require reading the request body
            # For now, just log that it's enabled
            span.set_attribute("http.request_payload_traced", True)

    def _set_response_attributes(
        self, span: trace.Span, response: Response, duration_seconds: float
    ) -> None:
        """
        Set HTTP response attributes on span.

        Args:
            span: Current span
            response: HTTP response
            duration_seconds: Request duration
        """
        # Response attributes
        span.set_attribute("http.status_code", response.status_code)
        span.set_attribute("http.response_time_seconds", duration_seconds)

        # Content length if available
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                span.set_attribute(
                    "http.response_content_length", int(content_length)
                )
            except (ValueError, TypeError):
                pass

        # Response content type
        content_type = response.headers.get("content-type")
        if content_type:
            span.set_attribute("http.response_content_type", content_type)


def get_trace_context(request: Request) -> Optional[trace.Span]:
    """
    Get trace context from FastAPI request.

    Args:
        request: FastAPI request

    Returns:
        Current span if available
    """
    return request.scope.get("trace_context")


def add_trace_attributes(request: Request, **attributes: Any) -> None:
    """
    Add attributes to current trace span.

    Args:
        request: FastAPI request
        **attributes: Attributes to add
    """
    span = get_trace_context(request)
    if span:
        for key, value in attributes.items():
            span.set_attribute(key, value)


class TracingDependency:
    """
    FastAPI dependency for accessing trace context in route handlers.

    Usage:
        @app.post("/v1/turns:run")
        async def execute_turn(
            request: TurnExecutionRequest,
            trace_span: Span = Depends(TracingDependency())
        ):
            trace_span.set_attribute("turn.participants_count", len(request.participants))
            # ... rest of handler
    """

    def __call__(self, request: Request) -> Optional[trace.Span]:
        """
        Get current trace span from request.

        Args:
            request: FastAPI request

        Returns:
            Current trace span if available
        """
        return get_trace_context(request)


def setup_fastapi_tracing(
    app,
    tracer: Optional[NovelEngineTracer] = None,
    excluded_urls: Optional[list] = None,
    enable_automatic_instrumentation: bool = True,
) -> None:
    """
    Setup comprehensive FastAPI tracing.

    Args:
        app: FastAPI application
        tracer: Optional Novel Engine tracer
        excluded_urls: URLs to exclude from tracing
        enable_automatic_instrumentation: Whether to enable automatic instrumentation
    """
    # Add custom middleware
    app.add_middleware(
        OpenTelemetryMiddleware, tracer=tracer, excluded_urls=excluded_urls
    )

    # Enable automatic instrumentation if requested
    if enable_automatic_instrumentation:
        try:
            # Convert list to comma-separated string for FastAPI instrumentation
            excluded_urls_str = None
            if excluded_urls is not None:
                excluded_urls_str = ",".join(excluded_urls)

            FastAPIInstrumentor.instrument_app(
                app,
                excluded_urls=excluded_urls_str,
            )
            logger.info("FastAPI automatic instrumentation enabled")
        except Exception as e:
            logger.warning(f"Could not enable automatic instrumentation: {e}")

    logger.info("FastAPI tracing setup completed")
