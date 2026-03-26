"""Request/Response logging middleware.

This module provides middleware for logging all HTTP requests and responses
with detailed information including timing, status codes, and error details.
"""

import time
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.shared.infrastructure.logging.config import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all HTTP requests and responses.

    This middleware logs detailed information about each request including
    the path, method, query parameters, client information, response status,
    and processing duration. It also captures and logs any errors that occur.
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Process the request and log details.

        Args:
            request: The incoming FastAPI request.
            call_next: The next middleware or route handler in the chain.

        Returns:
            The response from the next handler in the chain.
        """
        start_time = time.time()

        # Log request start
        logger.info(
            "Request started",
            path=request.url.path,
            method=request.method,
            query_params=str(request.query_params) if request.query_params else None,
            client_host=request.client.host if request.client else None,
            client_port=request.client.port if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time
            duration_ms = round(duration * 1000, 2)

            # Log response
            logger.info(
                "Request completed",
                path=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
                content_length=response.headers.get("content-length"),
            )

            return response

        except Exception as e:
            # Calculate duration even for errors
            duration = time.time() - start_time
            duration_ms = round(duration * 1000, 2)

            # Log error
            logger.error(
                "Request failed",
                path=request.url.path,
                method=request.method,
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=duration_ms,
            )
            raise


__all__ = ["LoggingMiddleware"]
