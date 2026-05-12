"""Compatibility exports for canonical shared logging middleware."""

from __future__ import annotations

import time
import uuid
from typing import Any, Awaitable, Callable

from fastapi import Request
from starlette.responses import Response

from src.shared.infrastructure.logging.config import get_logger
from src.shared.infrastructure.middleware.logging_middleware import LoggingMiddleware

logger = get_logger(__name__)

__all__ = ["LoggingMiddleware", "RequestContext", "logging_middleware"]


async def logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """ASGI-style wrapper kept for older imports.

    The canonical implementation is ``LoggingMiddleware`` from
    ``src.shared.infrastructure.middleware``.
    """
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    start_time = time.time()

    logger.info(
        "Request started",
        path=request.url.path,
        method=request.method,
        query_params=str(request.query_params) if request.query_params else None,
        client_host=request.client.host if request.client else None,
        client_port=request.client.port if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    try:
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(
            "Request completed",
            path=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            content_length=response.headers.get("content-length"),
        )
        response.headers.setdefault("X-Request-ID", request_id)
        return response
    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(
            "Request failed",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            error_type=type(exc).__name__,
            duration_ms=duration_ms,
        )
        raise


class RequestContext:
    """Context manager for request-specific logging context."""

    def __init__(self, **context_vars: Any) -> None:
        self.context_vars = context_vars
        self.bound_logger: Any = None

    def __enter__(self) -> Any:
        self.bound_logger = logger.bind(**self.context_vars)
        return self.bound_logger

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        return None
