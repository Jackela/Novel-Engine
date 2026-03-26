"""Error Bubbling Middleware for HTTP interface.

Implements the Error Bubbling pattern from DDD, allowing domain exceptions
to propagate from Domain > Application > Interface layers with proper
context preservation and HTTP response conversion.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from src.shared.domain.exceptions import (
    BusinessRuleException,
    DomainException,
    EntityNotFoundException,
    ValidationException,
)

logger = logging.getLogger(__name__)


class ErrorBubblingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle error bubbling from Domain to HTTP.

    This middleware catches domain exceptions and converts them to
    appropriate HTTP responses while preserving error context.

    Example:
        >>> app.add_middleware(ErrorBubblingMiddleware)
        >>> # Domain exceptions are automatically converted to HTTP responses
    """

    # Mapping of exception codes to HTTP status codes
    STATUS_MAP: dict[str, int] = {
        "VALIDATION_ERROR": 400,
        "ENTITY_NOT_FOUND": 404,
        "BUSINESS_RULE_VIOLATION": 422,
        "DUPLICATE_ENTITY": 409,
        "CONCURRENCY_CONFLICT": 409,
    }

    def __init__(
        self,
        app: ASGIApp,
        status_map: dict[str, int] | None = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            status_map: Optional custom mapping of error codes to HTTP status codes.
        """
        super().__init__(app)
        if status_map:
            self.STATUS_MAP.update(status_map)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        """Process the request and handle exceptions.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware/handler in the chain.

        Returns:
            HTTP response, either from the handler or an error response.
        """
        try:
            response = await call_next(request)
            if isinstance(response, Response):
                return response
            raise TypeError(f"Expected Response, got {type(response).__name__}")
        except ValidationException as e:
            return self._convert_domain_exception(e)
        except EntityNotFoundException as e:
            return self._convert_domain_exception(e)
        except BusinessRuleException as e:
            return self._convert_domain_exception(e)
        except DomainException as e:
            return self._convert_domain_exception(e)
        except Exception as e:
            return self._handle_unexpected_error(e)

    def _convert_domain_exception(self, exc: DomainException) -> JSONResponse:
        """Convert a domain exception to an HTTP response.

        Args:
            exc: The domain exception to convert.

        Returns:
            JSONResponse with appropriate status code and error details.
        """
        status_code = self.STATUS_MAP.get(exc.code, 500)

        logger.debug(
            "Domain exception converted to HTTP response: %s (status: %s)",
            exc.code,
            status_code,
        )

        return JSONResponse(
            status_code=status_code,
            content=exc.to_dict(),
        )

    def _handle_unexpected_error(self, exc: Exception) -> JSONResponse:
        """Handle unexpected errors that are not domain exceptions.

        Args:
            exc: The unexpected exception.

        Returns:
            JSONResponse with 500 status code and generic error message.
        """
        logger.exception("Unhandled error occurred")

        return JSONResponse(
            status_code=500,
            content={
                "message": "Internal server error",
                "code": "INTERNAL_ERROR",
                "context": {},
                "exception_type": exc.__class__.__name__,
            },
        )
