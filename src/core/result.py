#!/usr/bin/env python3
"""
Result Pattern: Functional Error Handling

Why Result[T, E]:
    Explicit error handling without exceptions. Services return Results
    instead of raising, making control flow visible and forcing callers
    to handle both success and failure cases.

Design Principles:
    - Result[T, E] is either Ok(value: T) or Error(error: E)
    - Immutable: once created, a Result's state never changes
    - Generic: works with any success (T) and error (E) types
    - Chainable: supports map, and_then, or_else for functional composition

Migration Path:
    1. Replace service methods that raise with methods returning Result
    2. Update routers to unwrap Results and return appropriate HTTP status
    3. Use .map() to transform values, .and_then() to chain Results

Example:
    def get_character(id: str) -> Result[Character, NotFoundError]:
        if char := repo.get(id):
            return Ok(char)
        return Error(NotFoundError(f"Character {id} not found"))

    # Usage:
    result = service.get_character("123")
    if result.is_ok:
        character = result.value
    else:
        return handle_error(result.error)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar, Union, overload

T = TypeVar("T")  # Success type
E = TypeVar("E")  # Error type
U = TypeVar("U")  # Mapped success type
F = TypeVar("F")  # Mapped error type


@dataclass(frozen=True)
class Error:
    """
    Represents an error in the Result pattern.

    Why frozen:
        Errors are immutable snapshots of what went wrong. Modifying
        an error would be misleading - the original failure state
        should be preserved.

    Attributes:
        code: Machine-readable error identifier (e.g., "CHARACTER_NOT_FOUND")
        message: Human-readable error description
        recoverable: Whether the operation can be retried
        details: Optional additional context (validation errors, IDs, etc.)
    """

    code: str
    message: str
    recoverable: bool = True
    details: dict[str, Any] | None = None

    def with_detail(self, key: str, value: Any) -> Error:
        """Add a detail to this error, returning a new Error."""
        current_details = self.details or {}
        return Error(
            code=self.code,
            message=self.message,
            recoverable=self.recoverable,
            details={**current_details, key: value},
        )

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class _Ok(Generic[T]):
    """
    Internal class representing a successful Result.

    Why separate classes:
        Using separate _Ok and _Error classes instead of a single Result
        class with a flag provides better type safety and prevents
        accessing the wrong property (value vs error).
    """

    __match_args__ = ("value",)

    def __init__(self, value: T):
        self._value = value

    @property
    def is_ok(self) -> bool:
        return True

    @property
    def is_error(self) -> bool:
        return False

    @property
    def value(self) -> T:
        return self._value

    @property
    def error(self) -> None:
        raise ValueError("Cannot get error from Ok Result")

    def unwrap(self) -> T:
        return self._value

    def map(self, fn: Callable[[T], U]) -> Result[U, Any]:
        try:
            return _Ok(fn(self._value))
        except Exception as e:
            return _Error(
                Error(
                    code="MAP_FAILED",
                    message=f"Transform function failed: {e}",
                    recoverable=False,
                )
            )

    def and_then(self, fn: Callable[[T], Result[U, Any]]) -> Result[U, Any]:
        return fn(self._value)

    def or_else(self, fn: Callable[[Any], Result[T, Any]]) -> Result[T, Any]:
        return self

    def on_error(self, fn: Callable[[Any], None]) -> Result[T, Any]:
        return self

    def on_success(self, fn: Callable[[T], None]) -> Result[T, Any]:
        fn(self._value)
        return self

    def __repr__(self) -> str:
        return f"Ok({self._value!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Ok) and self._value == other._value

    def __hash__(self) -> int:
        return hash((True, self._value))


class _Error(Generic[E]):
    """
    Internal class representing a failed Result.

    Why separate classes:
        Using separate _Ok and _Error classes instead of a single Result
        class with a flag provides better type safety and prevents
        accessing the wrong property (value vs error).
    """

    __match_args__ = ("error",)

    def __init__(self, error: E):
        self._error = error

    @property
    def is_ok(self) -> bool:
        return False

    @property
    def is_error(self) -> bool:
        return True

    @property
    def value(self) -> None:
        raise ValueError(f"Cannot get value from Error Result: {self._error}")

    @property
    def error(self) -> E:
        return self._error

    def unwrap(self, default: T | None = None) -> T | None:
        return default

    def map(self, fn: Callable[[Any], Any]) -> Result[Any, E]:
        return self

    def and_then(self, fn: Callable[[Any], Result[Any, E]]) -> Result[Any, E]:
        return self

    def or_else(self, fn: Callable[[E], Result[T, F]]) -> Result[T, F]:
        return fn(self._error)

    def on_error(self, fn: Callable[[E], None]) -> Result[T, E]:
        fn(self._error)
        return self

    def on_success(self, fn: Callable[[Any], None]) -> Result[T, E]:
        return self

    def __repr__(self) -> str:
        return f"Err({self._error!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Error) and self._error == other._error

    def __hash__(self) -> int:
        return hash((False, self._error))


# Type alias for the union of Ok and Error results
Result = Union[_Ok[T], _Error[E]]


def Ok(value: T) -> Result[T, Any]:
    """
    Create an Ok Result.

    Why factory function:
        More concise than _Ok(value) and makes the intent explicit in code.

    Args:
        value: The success value

    Returns:
        An Ok Result containing the value

    Example:
        return Ok(character)
    """
    return _Ok(value)


def Err(error: E) -> Result[Any, E]:
    """
    Create an Error Result.

    Why factory function:
        More concise than _Error(error) and makes the intent explicit in code.

    Args:
        error: The error value

    Returns:
        An Error Result containing the error

    Example:
        return Err(Error(code="NOT_FOUND", message="Character not found"))
    """
    return _Error(error)


# Alias for backward compatibility
Unwrap = Err


class NotFoundError(Error):
    """Error raised when a requested entity is not found."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="NOT_FOUND",
            message=message,
            recoverable=False,
            details=details,
        )


class ValidationError(Error):
    """Error raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        full_details = details or {}
        if field:
            full_details["field"] = field
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


class ConflictError(Error):
    """Error raised when an operation conflicts with existing state."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="CONFLICT",
            message=message,
            recoverable=True,
            details=details,
        )


class PermissionError(Error):
    """Error raised when a user lacks permission for an operation."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="PERMISSION_DENIED",
            message=message,
            recoverable=False,
            details=details,
        )


__all__ = [
    "Result",
    "Ok",
    "Err",
    "Unwrap",
    "Error",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "PermissionError",
]
