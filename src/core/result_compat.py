#!/usr/bin/env python3
"""
Result Pattern Compatibility Layer
==================================

Provides backward-compatible integration between Result pattern and StandardResponse.
This enables gradual migration of core services to Result[T,E] pattern while
maintaining compatibility with existing code.

Migration Path:
1. Add Result-based methods alongside existing methods
2. Update internal implementations to use Result pattern
3. Have old methods wrap Result-based methods for backward compatibility
4. Eventually deprecate StandardResponse-based methods
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar, cast

from .data_models import ErrorInfo, StandardResponse
from .result import Error, Err, Ok, Result

T = TypeVar("T")


def result_to_standard_response(result: Result[T, Error]) -> StandardResponse:
    """
    Convert a Result[T, Error] to StandardResponse for backward compatibility.

    Args:
        result: The Result to convert

    Returns:
        StandardResponse with success/error information
    """
    if result.is_ok:
        return StandardResponse(success=True, data=result.value)
    else:
        error = result.error
        return StandardResponse(
            success=False,
            error=ErrorInfo(
                code=error.code,
                message=error.message,
                details=error.details or {},
            ),
        )


def standard_response_to_result(
    response: StandardResponse,
) -> Result[Any, Error]:
    """
    Convert a StandardResponse to Result[Any, Error].

    Args:
        response: The StandardResponse to convert

    Returns:
        Result containing data or error
    """
    if response.success:
        return Ok(response.data)
    else:
        error_info = response.error
        return Err(
            Error(
                code=error_info.code if error_info else "UNKNOWN_ERROR",
                message=error_info.message if error_info else "Unknown error",
                details=error_info.details if error_info else None,
            )
        )


def result_from_optional(
    value: T | None, error_code: str, error_message: str
) -> Result[T, Error]:
    """
    Create a Result from an optional value.

    Args:
        value: The optional value
        error_code: Error code if value is None
        error_message: Error message if value is None

    Returns:
        Ok(value) if value is not None, Err(Error) otherwise
    """
    if value is not None:
        return Ok(value)
    return Err(Error(code=error_code, message=error_message))


def result_from_bool(
    success: bool,
    success_value: T,
    error_code: str = "OPERATION_FAILED",
    error_message: str = "Operation failed",
) -> Result[T, Error]:
    """
    Create a Result from a boolean success indicator.

    Args:
        success: Whether the operation succeeded
        success_value: Value to return on success
        error_code: Error code if success is False
        error_message: Error message if success is False

    Returns:
        Ok(success_value) if success is True, Err(Error) otherwise
    """
    if success:
        return Ok(success_value)
    return Err(Error(code=error_code, message=error_message))


def catch_to_result(
    fn: Callable[..., T],
    *args: Any,
    error_code: str = "OPERATION_FAILED",
    **kwargs: Any,
) -> Result[T, Error]:
    """
    Execute a function and wrap the result in a Result type.

    Args:
        fn: Function to execute
        *args: Positional arguments for the function
        error_code: Error code if function raises an exception
        **kwargs: Keyword arguments for the function

    Returns:
        Ok(result) if function succeeds, Err(Error) otherwise
    """
    try:
        result = fn(*args, **kwargs)
        return Ok(result)
    except Exception as e:
        return Err(
            Error(
                code=error_code,
                message=str(e),
                recoverable=False,
                details={"exception_type": type(e).__name__},
            )
        )


def map_result_list(results: list[Result[T, Error]]) -> Result[list[T], Error]:
    """
    Convert a list of Results to a Result containing a list of values.
    Returns the first error encountered, if any.

    Args:
        results: List of Results to combine

    Returns:
        Ok(list of values) if all results are Ok, first Err otherwise
    """
    values: list[T] = []
    for result in results:
        if result.is_error:
            return cast(Result[list[T], Error], result)
        values.append(result.value)
    return Ok(values)


def wrap_with_fallback(
    result: Result[T, Error],
    fallback: T,
    log_fallback: bool = True,
) -> T:
    """
    Unwrap a Result with a fallback value.

    Args:
        result: The Result to unwrap
        fallback: Value to return if Result is an error
        log_fallback: Whether to log fallback usage

    Returns:
        The value from Result or fallback
    """
    if result.is_ok:
        return result.value
    else:
        if log_fallback:
            import structlog

            logger = structlog.get_logger(__name__)
            logger.warning(
                "result_fallback_used",
                error_code=result.error.code,
                error_message=result.error.message,
            )
        return fallback


class ResultMixin:
    """
    Mixin class to add Result pattern methods to existing classes.

    Provides backward-compatible Result-based versions of common operations.
    """

    def _ok(self, value: T) -> Result[T, Error]:
        """Create an Ok result."""
        return Ok(value)

    def _err(
        self,
        code: str,
        message: str,
        recoverable: bool = True,
        details: dict[str, Any] | None = None,
    ) -> Result[Any, Error]:
        """Create an Err result."""
        return Err(Error(code=code, message=message, recoverable=recoverable, details=details))

    def _to_standard_response(self, result: Result[T, Error]) -> StandardResponse:
        """Convert Result to StandardResponse for backward compatibility."""
        return result_to_standard_response(result)


__all__ = [
    "ResultMixin",
    "catch_to_result",
    "map_result_list",
    "result_from_bool",
    "result_from_optional",
    "result_to_standard_response",
    "standard_response_to_result",
    "wrap_with_fallback",
]
