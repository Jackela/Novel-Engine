"""Tests for the Result pattern implementation.

This module contains comprehensive tests for the Result[T] pattern,
ensuring proper success/failure handling and monadic operations.
"""

from __future__ import annotations

import pytest

from src.shared.application.result import (
    Failure,
    Result,
    Success,
    UnwrapError,
    get_error,
    get_value,
    is_failure,
    is_success,
)


class TestSuccess:
    """Test cases for Success result."""

    def test_success_creation(self) -> None:
        """Test Success result creation."""
        result: Success[int] = Success(42)

        assert result.value == 42

    def test_success_is_ok(self) -> None:
        """Test Success.is_ok returns True."""
        result: Success[int] = Success(42)

        assert result.is_ok() is True

    def test_success_is_err(self) -> None:
        """Test Success.is_err returns False."""
        result: Success[int] = Success(42)

        assert result.is_err() is False

    def test_success_unwrap(self) -> None:
        """Test Success.unwrap returns value."""
        result: Success[int] = Success(42)

        assert result.unwrap() == 42

    def test_success_unwrap_or(self) -> None:
        """Test Success.unwrap_or returns original value."""
        result: Success[int] = Success(42)

        assert result.unwrap_or(0) == 42

    def test_success_map(self) -> None:
        """Test Success.map transforms value."""
        result: Success[int] = Success(42)

        mapped = result.map(lambda x: x * 2)

        assert mapped.unwrap() == 84

    def test_success_map_err_noop(self) -> None:
        """Test Success.map_err is no-op."""
        result: Success[int] = Success(42)

        mapped = result.map_err(lambda e: f"error: {e}")

        assert mapped.unwrap() == 42

    def test_success_bind(self) -> None:
        """Test Success.bind chains operations."""
        result: Success[int] = Success(10)

        chained = result.bind(lambda x: Success(x * 2))

        assert chained.unwrap() == 20

    def test_success_bind_can_return_failure(self) -> None:
        """Test Success.bind can return Failure."""
        result: Success[int] = Success(10)

        chained: Result[int] = result.bind(lambda x: Failure("error", "ERR_001"))

        assert chained.is_err()

    def test_success_repr(self) -> None:
        """Test Success repr."""
        result: Success[int] = Success(42)

        assert "Success" in repr(result)
        assert "42" in repr(result)


class TestFailure:
    """Test cases for Failure result."""

    def test_failure_creation(self) -> None:
        """Test Failure result creation."""
        result: Failure = Failure("Something went wrong", "ERR_001")

        assert result.error == "Something went wrong"
        assert result.code == "ERR_001"
        assert result.details is None

    def test_failure_creation_with_details(self) -> None:
        """Test Failure creation with details."""
        details = {"field": "name", "reason": "too long"}
        result: Failure = Failure("Validation failed", "VAL_001", details)

        assert result.details == details

    def test_failure_is_ok(self) -> None:
        """Test Failure.is_ok returns False."""
        result: Failure = Failure("error", "ERR_001")

        assert result.is_ok() is False

    def test_failure_is_err(self) -> None:
        """Test Failure.is_err returns True."""
        result: Failure = Failure("error", "ERR_001")

        assert result.is_err() is True

    def test_failure_unwrap_raises(self) -> None:
        """Test Failure.unwrap raises UnwrapError."""
        result: Failure = Failure("Something went wrong", "ERR_001")

        with pytest.raises(UnwrapError, match="Something went wrong"):
            result.unwrap()

    def test_failure_unwrap_or_returns_default(self) -> None:
        """Test Failure.unwrap_or returns default."""
        result: Failure = Failure("error", "ERR_001")

        assert result.unwrap_or(42) == 42

    def test_failure_map_noop(self) -> None:
        """Test Failure.map is no-op."""
        result: Failure = Failure("error", "ERR_001")

        mapped = result.map(lambda x: x * 2)

        assert isinstance(mapped, Failure)
        assert mapped.is_err()
        assert mapped.error == "error"

    def test_failure_map_err_transforms_error(self) -> None:
        """Test Failure.map_err transforms error."""
        result: Failure = Failure("error", "ERR_001")

        mapped = result.map_err(lambda e: f"transformed: {e}")

        assert isinstance(mapped, Failure)
        assert "transformed" in mapped.error

    def test_failure_bind_noop(self) -> None:
        """Test Failure.bind is no-op."""
        result: Failure = Failure("error", "ERR_001")

        chained = result.bind(lambda x: Success(100))

        assert chained.is_err()

    def test_failure_repr(self) -> None:
        """Test Failure repr."""
        result: Failure = Failure("error", "ERR_001")

        assert "Failure" in repr(result)
        assert "error" in repr(result)
        assert "ERR_001" in repr(result)


class TestResultTypeAlias:
    """Test cases for Result type alias."""

    def test_result_can_be_success(self) -> None:
        """Test Result type can be Success."""
        result: Result[int] = Success(42)

        assert is_success(result)

    def test_result_can_be_failure(self) -> None:
        """Test Result type can be Failure."""
        result: Result[int] = Failure("error", "ERR_001")

        assert is_failure(result)


class TestHelperFunctions:
    """Test cases for helper functions."""

    def test_is_success_with_success(self) -> None:
        """Test is_success returns True for Success."""
        result: Result[int] = Success(42)

        assert is_success(result) is True

    def test_is_success_with_failure(self) -> None:
        """Test is_success returns False for Failure."""
        result: Result[int] = Failure("error", "ERR_001")

        assert is_success(result) is False

    def test_is_failure_with_success(self) -> None:
        """Test is_failure returns False for Success."""
        result: Result[int] = Success(42)

        assert is_failure(result) is False

    def test_is_failure_with_failure(self) -> None:
        """Test is_failure returns True for Failure."""
        result: Result[int] = Failure("error", "ERR_001")

        assert is_failure(result) is True

    def test_get_value_from_success(self) -> None:
        """Test get_value extracts value from Success."""
        success: Success[int] = Success(42)

        assert get_value(success) == 42

    def test_get_error_from_failure(self) -> None:
        """Test get_error extracts error from Failure."""
        failure: Failure = Failure("Something wrong", "ERR_001")

        assert get_error(failure) == "Something wrong"


class TestUnwrapError:
    """Test cases for UnwrapError exception."""

    def test_unwrap_error_message(self) -> None:
        """Test UnwrapError message."""
        error = UnwrapError("Test message")

        assert "Test message" in str(error)
        assert error.message == "Test message"

    def test_unwrap_error_is_exception(self) -> None:
        """Test UnwrapError is an Exception."""
        error = UnwrapError("Test")

        assert isinstance(error, Exception)


class TestResultChaining:
    """Test cases for Result chaining operations."""

    def test_success_chaining(self) -> None:
        """Test chaining multiple Success operations."""
        result: Result[int] = Success(5)

        final = (
            result.bind(lambda x: Success(x + 5))
            .bind(lambda x: Success(x * 2))
            .bind(lambda x: Success(x - 3))
        )

        assert final.unwrap() == 17  # (5 + 5) * 2 - 3

    def test_chaining_stops_at_first_failure(self) -> None:
        """Test that chaining stops at first Failure."""
        result: Result[int] = Success(5)
        call_count = 0

        def count_and_fail(x: int) -> Result[int]:
            nonlocal call_count
            call_count += 1
            return Failure("Failed", "ERR_001")

        def should_not_be_called(x: int) -> Result[int]:
            raise AssertionError("Should not be called")

        final = result.bind(count_and_fail).bind(should_not_be_called)

        assert final.is_err()
        assert call_count == 1

    def test_mixed_chaining_with_failure_in_middle(self) -> None:
        """Test chaining with failure in the middle."""
        result: Result[int] = Success(5)

        final = (
            result.bind(lambda x: Success(x + 5))  # 10
            .bind(lambda x: Failure("Middle error", "ERR_002"))
            .bind(lambda x: Success(x * 2))  # Should not execute
        )

        assert final.is_err()
        assert isinstance(final, Failure)
        assert "Middle error" in final.error
