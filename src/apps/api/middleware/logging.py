"""
Logging Middleware

Structured logging middleware using structlog.
Captures request/response details and performance metrics.
"""

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging.

    Captures:
    - Request method, path, query params
    - Response status code
    - Processing time
    - Request ID for tracing
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Create request-specific logger
        request_logger = logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query=str(request.query_params),
            client_host=request.client.host if request.client else None,
        )

        # Start timing
        start_time = time.perf_counter()

        # Log request start
        await request_logger.ainfo("request_started")

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log successful response
            await request_logger.ainfo(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Calculate duration even for errors
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log error
            await request_logger.aerror(
                "request_failed",
                exception_type=type(exc).__name__,
                exception_message=str(exc),
                duration_ms=round(duration_ms, 2),
            )

            raise


# Convenience function for FastAPI middleware system
async def logging_middleware(request: Request, call_next: Callable) -> Response:
    """
    ASGI-style logging middleware function.

    Usage:
        app.middleware("http")(logging_middleware)

    Note: Prefer using LoggingMiddleware class for better structure.
    """
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    start_time = time.perf_counter()

    await logger.ainfo(
        "request_started",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )

    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        await logger.ainfo(
            "request_completed",
            request_id=request_id,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        response.headers["X-Request-ID"] = request_id
        return response

    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000

        await logger.aerror(
            "request_failed",
            request_id=request_id,
            exception_type=type(exc).__name__,
            duration_ms=round(duration_ms, 2),
        )

        raise


class RequestContext:
    """
    Context manager for request-specific logging context.

    Usage:
        with RequestContext(request_id="abc123"):
            # All logs in this block include request_id
            logger.info("processing")
    """

    def __init__(self, **context_vars):
        self.context_vars = context_vars
        self.bound_logger = None

    def __enter__(self):
        self.bound_logger = logger.bind(**self.context_vars)
        return self.bound_logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
