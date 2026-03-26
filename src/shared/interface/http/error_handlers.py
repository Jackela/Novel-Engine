"""Shared HTTP error handling utilities."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar, cast

import structlog
from fastapi import HTTPException, status

from src.shared.application.result import Failure, Result

logger = structlog.get_logger(__name__)

# Standard error code to HTTP status mapping
ERROR_CODE_TO_HTTP_STATUS: dict[str, int] = {
    # Client errors (4xx)
    "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
    "BAD_REQUEST": status.HTTP_400_BAD_REQUEST,
    "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,
    "FORBIDDEN": status.HTTP_403_FORBIDDEN,
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "CONFLICT": status.HTTP_409_CONFLICT,
    "UNPROCESSABLE_ENTITY": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "TOO_MANY_REQUESTS": status.HTTP_429_TOO_MANY_REQUESTS,
    # Server errors (5xx)
    "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "NOT_IMPLEMENTED": status.HTTP_501_NOT_IMPLEMENTED,
    "SERVICE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
}

# Standard error messages
ERROR_CODE_TO_MESSAGE: dict[str, str] = {
    "VALIDATION_ERROR": "Validation failed",
    "BAD_REQUEST": "Bad request",
    "UNAUTHORIZED": "Unauthorized",
    "FORBIDDEN": "Forbidden",
    "NOT_FOUND": "Resource not found",
    "CONFLICT": "Conflict occurred",
    "UNPROCESSABLE_ENTITY": "Unprocessable entity",
    "TOO_MANY_REQUESTS": "Too many requests",
    "INTERNAL_ERROR": "Internal server error",
    "NOT_IMPLEMENTED": "Not implemented",
    "SERVICE_UNAVAILABLE": "Service unavailable",
}

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])


class ResultErrorHandler:
    """Handle Result-type errors and convert to HTTPException."""

    @staticmethod
    def handle(result: Result[T], operation: str | None = None) -> T:
        """Handle Result error.

        If result contains an error, raises appropriate HTTPException.
        Otherwise returns the success value.

        Args:
            result: The Result to handle
            operation: Optional operation name for logging

        Returns:
            The success value if result is successful

        Raises:
            HTTPException: If result contains an error
        """
        if isinstance(result, Failure):
            error = result
            status_code = ERROR_CODE_TO_HTTP_STATUS.get(
                error.code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            message = ERROR_CODE_TO_MESSAGE.get(error.code, error.error)

            if operation:
                logger.error(
                    "result_operation_failed",
                    operation=operation,
                    error_code=error.code,
                    error_message=error.error,
                )

            raise HTTPException(status_code=status_code, detail=message)

        return result.value

    @staticmethod
    def handle_or_return(
        result: Result[T], operation: str | None = None
    ) -> T | None:
        """Handle result or return None on error (for optional operations)."""
        if isinstance(result, Failure):
            return None
        return result.value


class BaseErrorConverter:
    """Base error converter. Extend this for context-specific conversions."""

    @staticmethod
    def convert(error: Exception) -> HTTPException:
        """Convert generic exception to HTTPException.

        Override this method in subclasses to add context-specific handling.
        """
        if isinstance(error, ValueError):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            )

        logger.error(f"Unhandled error: {error}", exc_info=True)
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


def handle_result_error(operation: str | None = None) -> Callable[[F], F]:
    """Decorator to handle Result errors in route handlers.

    Usage:
        @router.get("/items")
        @handle_result_error("list_items")
        async def list_items():
            result = await service.get_items()
            return ResultErrorHandler.handle(result, "list_items")
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error in {operation or func.__name__}",
                    error=str(e),
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error",
                ) from e

        return cast(F, wrapper)

    return decorator
