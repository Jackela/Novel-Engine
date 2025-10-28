#!/usr/bin/env python3
"""
Error Handling Decorators and Utilities

Centralized error handling patterns for consistent error responses.
"""

import functools
import logging
from typing import Callable, Optional

from src.core.data_models import ErrorInfo, StandardResponse

logger = logging.getLogger(__name__)


def handle_standard_errors(
    operation_name: str,
    error_code: Optional[str] = None,
    recoverable: bool = True,
    log_level: str = "error",
) -> Callable:
    """
    Decorator for standardized error handling.

    Args:
        operation_name: Name of the operation (for logging and error messages)
        error_code: Error code to use (defaults to OPERATION_NAME_FAILED)
        recoverable: Whether errors are recoverable
        log_level: Logging level for errors (error, warning, info)

    Returns:
        Decorated function with automatic error handling

    Example:
        @handle_standard_errors("equipment_registration", "REGISTRATION_FAILED")
        async def register_equipment(self, equipment_item):
            # ... implementation
            return StandardResponse(success=True, data={...})
    """
    if error_code is None:
        error_code = f"{operation_name.upper().replace(' ', '_')}_FAILED"

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except (AttributeError, KeyError, TypeError) as e:
                # Invalid data structure errors in async operation
                log_func = getattr(logger, log_level, logger.error)
                log_func(
                    f"{operation_name.upper()} FAILED (invalid data): {e}",
                    extra={"error_type": type(e).__name__},
                )
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code=error_code,
                        message=f"{operation_name} failed: {str(e)}",
                        recoverable=recoverable,
                    ),
                )
            except (ValueError, RuntimeError) as e:
                # Processing errors in async operation
                log_func = getattr(logger, log_level, logger.error)
                log_func(
                    f"{operation_name.upper()} FAILED: {e}",
                    extra={"error_type": type(e).__name__},
                )
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code=error_code,
                        message=f"{operation_name} failed: {str(e)}",
                        recoverable=recoverable,
                    ),
                )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (AttributeError, KeyError, TypeError) as e:
                # Invalid data structure errors in sync operation
                log_func = getattr(logger, log_level, logger.error)
                log_func(
                    f"{operation_name.upper()} FAILED (invalid data): {e}",
                    extra={"error_type": type(e).__name__},
                )
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code=error_code,
                        message=f"{operation_name} failed: {str(e)}",
                        recoverable=recoverable,
                    ),
                )
            except (ValueError, RuntimeError) as e:
                # Processing errors in sync operation
                log_func = getattr(logger, log_level, logger.error)
                log_func(
                    f"{operation_name.upper()} FAILED: {e}",
                    extra={"error_type": type(e).__name__},
                )
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code=error_code,
                        message=f"{operation_name} failed: {str(e)}",
                        recoverable=recoverable,
                    ),
                )

        # Return appropriate wrapper based on function type
        if functools.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


__all__ = ["handle_standard_errors"]
