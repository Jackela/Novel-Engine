"""Core result types for backward compatibility.

This module provides Result, Ok, Err, Error types that are compatible
with the existing codebase. It's a thin wrapper around src.shared.application.result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar

from src.shared.application.result import Failure, Success

T = TypeVar("T")
E = TypeVar("E")

# Re-export Success as Ok for compatibility
Ok = Success
Result = Success[T] | Failure


@dataclass(frozen=True)
class Error:
    """Error type for compatibility with existing code.

    Attributes:
        message: Error message
        code: Error code
        details: Additional error details
        recoverable: Whether the error is recoverable
    """

    message: str
    code: str = "ERROR"
    details: dict[str, Any] | None = None
    recoverable: bool = True

    def __str__(self) -> str:
        return self.message


class Err(Failure):
    """Err type for backward compatibility, extends Failure.

    Uses Failure's is_ok() method which returns False.
    Also provides is_ok and is_err properties for compatibility.
    """

    def __init__(
        self,
        error: Error | str,
        code: str = "ERROR",
        details: dict[str, Any] | None = None,
    ):
        if isinstance(error, Error):
            super().__init__(
                error=error.message,
                code=error.code,
                details=error.details or {},
            )
        else:
            super().__init__(
                error=error,
                code=code,
                details=details or {},
            )

    @property
    def is_ok(self) -> bool:
        """Property for compatibility with result.is_ok checks."""
        return False

    @property
    def is_err(self) -> bool:
        """Property for compatibility with result.is_err checks."""
        return True


# Add is_ok property to Success for consistency
Success.is_ok = property(lambda self: True)  # type: ignore
Success.is_err = property(lambda self: False)  # type: ignore

__all__ = ["Ok", "Err", "Error", "Result", "Success", "Failure"]
