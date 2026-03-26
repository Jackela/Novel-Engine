"""Result pattern implementation for Novel Engine application layer.

This module implements the Result monad pattern for handling operations
that can succeed or fail without throwing exceptions. It provides a
functional approach to error handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")
"""Type variable for successful result value."""

E = TypeVar("E")
"""Type variable for error value."""

U = TypeVar("U")
"""Type variable for transformed value in map operations."""


@dataclass(frozen=True)
class Success(Generic[T]):
    """Represents a successful result with a value.

    Attributes:
        value: The successful result value.

    Example:
        >>> result: Result[int, str] = Success(42)
        >>> is_success(result)
        True
        >>> get_value(result)
        42
    """

    value: T

    @property
    def is_ok(self) -> bool:
        """Check if result is success.

        Returns:
            Always True for Success.
        """
        return True

    @property
    def is_err(self) -> bool:
        """Check if result is error.

        Returns:
            Always False for Success.
        """
        return False

    @property
    def is_error(self) -> bool:
        """Property alias for is_err().

        Returns:
            Always False for Success.
        """
        return False

    def unwrap(self) -> T:
        """Get the success value.

        Returns:
            The success value.
        """
        return self.value

    def unwrap_or(self, default: U) -> T:
        """Get the success value or a default.

        Args:
            default: Ignored for Success.

        Returns:
            The success value.
        """
        return self.value

    def map(self, f: Callable[[T], U]) -> Success[U]:
        """Transform the success value.

        Args:
            f: Function to apply to the success value.

        Returns:
            New Success with transformed value.
        """
        return Success(f(self.value))

    def map_err(self, f: Callable[[Any], Any]) -> Success[T]:
        """Transform the error value (no-op for Success).

        Args:
            f: Ignored for Success.

        Returns:
            Self unchanged.
        """
        return self

    def bind(self, f: Callable[[T], Success[U] | Failure]) -> Success[U] | Failure:
        """Chain another result-producing operation.

        Args:
            f: Function that takes success value and returns new Result.

        Returns:
            Result of applying f to the success value.
        """
        return f(self.value)

    def __repr__(self) -> str:
        """String representation.

        Returns:
            String showing the success value.
        """
        return f"Success({self.value!r})"


@dataclass(frozen=True)
class Failure:
    """Represents a failed result with an error.

    Attributes:
        error: The error message.
        code: Error code for programmatic handling.
        details: Optional dictionary with additional error details.

    Example:
        >>> result: Result[int, str] = Failure("something went wrong", "ERR_001")
        >>> is_failure(result)
        True
        >>> get_error(result)
        'something went wrong'
    """

    error: str
    code: str = "ERROR"
    details: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Prevent nested Failure objects."""
        if isinstance(self.error, Failure):
            raise ValueError("Cannot nest Failure objects")

    @staticmethod
    def from_exception(exc: Exception, code: str | None = None) -> "Failure":
        """Create Failure from an exception.

        Args:
            exc: The exception to convert.
            code: Optional error code. Defaults to exception class name.

        Returns:
            Failure instance with error details from exception.

        Example:
            >>> try:
            ...     1 / 0
            ... except Exception as e:
            ...     failure = Failure.from_exception(e)
        """
        return Failure(
            error=str(exc),
            code=code or exc.__class__.__name__.upper(),
            details={"exception_type": exc.__class__.__name__},
        )

    @staticmethod
    def from_message(message: str, code: str = "ERROR", **details: Any) -> "Failure":
        """Create Failure from a message.

        Args:
            message: The error message.
            code: Error code for programmatic handling.
            **details: Additional error details as keyword arguments.

        Returns:
            Failure instance with the given message and details.

        Example:
            >>> failure = Failure.from_message("Invalid input", "VALIDATION_ERROR", field="name")
        """
        return Failure(error=message, code=code, details=details or None)

    @property
    def value(self) -> Any:
        """Property to access error details (for compatibility).

        Returns:
            The error message as 'value' for uniform access pattern.
        """
        return {"error": self.error, "code": self.code, "details": self.details}

    @property
    def is_ok(self) -> bool:
        """Check if result is success.

        Returns:
            Always False for Failure.
        """
        return False

    @property
    def is_err(self) -> bool:
        """Check if result is error.

        Returns:
            Always True for Failure.
        """
        return True

    @property
    def is_error(self) -> bool:
        """Property alias for is_err().

        Returns:
            Always True for Failure.
        """
        return True

    def unwrap(self) -> Any:
        """Get the success value.

        Raises:
            UnwrapError: Always raises for Failure.
        """
        raise UnwrapError(f"Called unwrap on Failure: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Get the success value or a default.

        Args:
            default: Value to return since this is Failure.

        Returns:
            The default value.
        """
        return default

    def map(self, f: Callable[[Any], Any]) -> Failure:
        """Transform the success value (no-op for Failure).

        Args:
            f: Ignored for Failure.

        Returns:
            Self unchanged.
        """
        return self

    def map_err(self, f: Callable[[str], U]) -> Failure:
        """Transform the error value.

        Args:
            f: Function to apply to the error value.

        Returns:
            New Failure with transformed error.
        """
        return Failure(error=str(f(self.error)), code=self.code, details=self.details)

    def bind(self, f: Callable[[Any], Success[Any] | Failure]) -> Failure:
        """Chain another result-producing operation (no-op for Failure).

        Args:
            f: Ignored for Failure.

        Returns:
            Self unchanged.
        """
        return self

    def __repr__(self) -> str:
        """String representation.

        Returns:
            String showing the error details.
        """
        return f"Failure(error={self.error!r}, code={self.code!r})"


# Type alias for Result - represents either success or failure
Result = Success[T] | Failure
# Note: Result type alias only takes one type parameter T for the success value.
# For proper typing of functions that can fail, use explicit return types like:
# -> Success[int] | Failure or use a more specific Result type.
"""Type alias representing either success (Success) or failure (Failure).

Type Parameters:
    T: Type of the success value.
    
Example:
    >>> def divide(a: float, b: float) -> Result[float]:
    ...     if b == 0:
    ...         return Failure("division by zero", "MATH_001")
    ...     return Success(a / b)
    >>>
    >>> result = divide(10, 2)
    >>> if is_success(result):
    ...     print(f"Result: {get_value(result)}")
    ... else:
    ...     print(f"Error: {get_error(result)}")
"""


class UnwrapError(Exception):
    """Exception raised when unwrapping a Failure result.

    Attributes:
        message: Description of the error.
    """

    def __init__(self, message: str) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
        """
        self.message = message
        super().__init__(self.message)


def is_success(result: Result[T]) -> bool:
    """Check if result is success.

    Args:
        result: The result to check.

    Returns:
        True if result is Success, False otherwise.
    """
    return isinstance(result, Success)


def is_failure(result: Result[T]) -> bool:
    """Check if result is failure.

    Args:
        result: The result to check.

    Returns:
        True if result is Failure, False otherwise.
    """
    return isinstance(result, Failure)


def get_value(result: Success[T]) -> T:
    """Get value from success result.

    Args:
        result: A Success result.

    Returns:
        The success value.
    """
    return result.value


def get_error(result: Failure) -> str:
    """Get error from failure result.

    Args:
        result: A Failure result.

    Returns:
        The error message.
    """
    return result.error
