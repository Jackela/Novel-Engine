"""Correlation ID middleware for distributed tracing.

This module provides middleware for managing correlation IDs across requests,
enabling distributed tracing and request tracking across services.
"""

import uuid
from typing import Awaitable, Callable

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

CORRELATION_ID_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware for adding correlation ID to all requests.

    This middleware ensures that every request has a correlation ID for
    distributed tracing. It either uses the ID from the incoming request
    header or generates a new one. The correlation ID is added to both
    the logging context and the response headers.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process the request and add correlation ID.

        Args:
            request: The incoming FastAPI request.
            call_next: The next middleware or route handler in the chain.

        Returns:
            The response with correlation ID headers added.
        """
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get(CORRELATION_ID_HEADER)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Generate request ID for this specific request
        request_id = str(uuid.uuid4())[:8]

        # Store in request state for later access
        request.state.correlation_id = correlation_id
        request.state.request_id = request_id

        # Clear any existing context and bind new values
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            request_id=request_id,
            request_path=request.url.path,
            request_method=request.method,
        )

        # Process request
        response = await call_next(request)

        # Add IDs to response headers
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        response.headers[REQUEST_ID_HEADER] = request_id

        return response


def get_correlation_id(request: Request) -> str:
    """Get the correlation ID from a request.

    Args:
        request: The FastAPI request object.

    Returns:
        The correlation ID string. If not found, generates a new one.
    """
    return getattr(request.state, "correlation_id", str(uuid.uuid4()))


def get_request_id(request: Request) -> str:
    """Get the request ID from a request.

    Args:
        request: The FastAPI request object.

    Returns:
        The request ID string. If not found, generates a new one.
    """
    return getattr(request.state, "request_id", str(uuid.uuid4())[:8])


def get_correlation_id_from_context() -> str | None:
    """Get correlation ID from the current logging context.

    Returns:
        The correlation ID if bound in context, None otherwise.
    """
    ctx = structlog.contextvars.get_contextvars()
    return ctx.get("correlation_id")


__all__ = [
    "CorrelationIdMiddleware",
    "CORRELATION_ID_HEADER",
    "REQUEST_ID_HEADER",
    "get_correlation_id",
    "get_request_id",
    "get_correlation_id_from_context",
]
