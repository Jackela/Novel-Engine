"""
Unit tests for Result pattern implementation.

Tests cover:
- Ok/Error creation
- is_ok/is_error properties
- value/error properties
- unwrap method
- map/and_then/or_else chain operations
- on_error/on_success callbacks
- Error details and error types
"""

import pytest

from src.core.result import (
    ConflictError,
    Err,
    Error,
    NotFoundError,
    Ok,
    PermissionError,
    Result,
    SaveError,
    Unwrap,
    ValidationError,
)

pytestmark = pytest.mark.unit


class TestOkResult:
    """Tests for Ok Result."""

    def test_ok_creation(self) -> None:
        """Test creating Ok Result."""
        result = Ok(42)
        assert result.is_ok is True
        assert result.is_error is False

    def test_ok_value_access(self) -> None:
        """Test accessing value from Ok Result."""
        result = Ok(42)
        assert result.value == 42

    def test_ok_error_access_raises(self) -> None:
        """Test that accessing error from Ok raises."""
        result = Ok(42)
        with pytest.raises(ValueError, match="Cannot get error from Ok Result"):
            _ = result.error

    def test_ok_unwrap(self) -> None:
        """Test unwrap on Ok Result."""
        result = Ok(42)
        assert result.unwrap() == 42

    def test_ok_unwrap_different_signature(self) -> None:
        """Test unwrap on Ok Result (Ok.unwrap doesn't take default)."""
        result = Ok(42)
        # Ok.unwrap() doesn't accept default parameter - it always returns value
        assert result.unwrap() == 42


class TestErrorResult:
    """Tests for Error Result."""

    def test_error_creation(self) -> None:
        """Test creating Error Result."""
        error = Error(code="TEST", message="Test error")
        result = Err(error)
        assert result.is_ok is False
        assert result.is_error is True

    def test_error_error_access(self) -> None:
        """Test accessing error from Error Result."""
        error = Error(code="TEST", message="Test error")
        result = Err(error)
        assert result.error == error

    def test_error_value_access_raises(self) -> None:
        """Test that accessing value from Error raises."""
        error = Error(code="TEST", message="Test error")
        result = Err(error)
        with pytest.raises(ValueError, match="Cannot get value from Error Result"):
            _ = result.value

    def test_error_unwrap_returns_none(self) -> None:
        """Test unwrap on Error Result returns None."""
        error = Error(code="TEST", message="Test error")
        result = Err(error)
        assert result.unwrap() is None

    def test_error_unwrap_with_default(self) -> None:
        """Test unwrap with default on Error Result."""
        error = Error(code="TEST", message="Test error")
        result = Err(error)
        assert result.unwrap(default="fallback") == "fallback"


class TestResultMap:
    """Tests for Result.map method."""

    def test_ok_map(self) -> None:
        """Test map on Ok Result."""
        result = Ok(5)
        mapped = result.map(lambda x: x * 2)
        assert mapped.is_ok
        assert mapped.value == 10

    def test_ok_map_chain(self) -> None:
        """Test chaining map operations."""
        result = Ok(5)
        mapped = result.map(lambda x: x * 2).map(lambda x: x + 1)
        assert mapped.value == 11

    def test_ok_map_with_exception(self) -> None:
        """Test map when transform raises exception."""
        result = Ok(5)
        mapped = result.map(lambda x: 1 / 0)
        assert mapped.is_error
        assert mapped.error.code == "MAP_FAILED"

    def test_error_map(self) -> None:
        """Test map on Error Result (should pass through)."""
        error = Error(code="TEST", message="Test error")
        result = Err(error)
        mapped = result.map(lambda x: x * 2)
        assert mapped.is_error
        assert mapped.error == error


class TestResultAndThen:
    """Tests for Result.and_then method."""

    def test_ok_and_then(self) -> None:
        """Test and_then on Ok Result."""
        result = Ok(5)
        chained = result.and_then(lambda x: Ok(x * 2))
        assert chained.is_ok
        assert chained.value == 10

    def test_ok_and_then_to_error(self) -> None:
        """Test and_then returning Error from Ok."""
        result = Ok(5)
        error = Error(code="LIMIT", message="Limit exceeded")
        chained = result.and_then(lambda x: Err(error))
        assert chained.is_error
        assert chained.error == error

    def test_error_and_then(self) -> None:
        """Test and_then on Error Result (should pass through)."""
        error = Error(code="TEST", message="Test error")
        result = Err(error)
        chained = result.and_then(lambda x: Ok(100))
        assert chained.is_error
        assert chained.error == error


class TestResultOrElse:
    """Tests for Result.or_else method."""

    def test_ok_or_else(self) -> None:
        """Test or_else on Ok Result (should pass through)."""
        result = Ok(42)
        recovered = result.or_else(lambda e: Ok(100))
        assert recovered.is_ok
        assert recovered.value == 42

    def test_error_or_else(self) -> None:
        """Test or_else on Error Result."""
        error = Error(code="TEST", message="Test error")
        result = Err(error)
        recovered = result.or_else(lambda e: Ok(100))
        assert recovered.is_ok
        assert recovered.value == 100

    def test_error_or_else_chain(self) -> None:
        """Test or_else chain recovery."""
        error = Error(code="TEST", message="Test error")
        result = Err(error)
        recovered = result.or_else(lambda e: Ok(100)).map(lambda x: x + 1)
        assert recovered.value == 101


class TestResultOnCallbacks:
    """Tests for on_error and on_success callbacks."""

    def test_ok_on_success_callback(self) -> None:
        """Test on_success callback on Ok Result."""
        result = Ok(42)
        callback_called = []
        result.on_success(lambda v: callback_called.append(v))
        assert callback_called == [42]

    def test_ok_on_error_callback(self) -> None:
        """Test on_error callback on Ok Result (should not call)."""
        result = Ok(42)
        callback_called = []
        result.on_error(lambda e: callback_called.append(e))
        assert callback_called == []

    def test_error_on_error_callback(self) -> None:
        """Test on_error callback on Error Result."""
        error = Error(code="TEST", message="Test error")
        result = Err(error)
        callback_called = []
        result.on_error(lambda e: callback_called.append(e))
        assert callback_called == [error]

    def test_error_on_success_callback(self) -> None:
        """Test on_success callback on Error Result (should not call)."""
        error = Error(code="TEST", message="Test error")
        result = Err(error)
        callback_called = []
        result.on_success(lambda v: callback_called.append(v))
        assert callback_called == []


class TestResultRepr:
    """Tests for Result string representation."""

    def test_ok_repr(self) -> None:
        """Test repr of Ok Result."""
        result = Ok(42)
        assert repr(result) == "Ok(42)"

    def test_error_repr(self) -> None:
        """Test repr of Error Result."""
        error = Error(code="TEST", message="Test")
        result = Err(error)
        assert "Err" in repr(result)


class TestResultEquality:
    """Tests for Result equality."""

    def test_ok_equality(self) -> None:
        """Test equality of Ok Results."""
        assert Ok(42) == Ok(42)
        assert Ok(42) != Ok(43)
        assert Ok(42) != Err(Error(code="TEST", message="Test"))

    def test_error_equality(self) -> None:
        """Test equality of Error Results."""
        error1 = Error(code="TEST", message="Test")
        error2 = Error(code="TEST", message="Test")
        error3 = Error(code="OTHER", message="Other")
        assert Err(error1) == Err(error2)
        assert Err(error1) != Err(error3)

    def test_ok_error_inequality(self) -> None:
        """Test Ok and Error are never equal."""
        assert Ok(42) != Err(Error(code="TEST", message="Test"))


class TestResultHash:
    """Tests for Result hashing."""

    def test_ok_hash(self) -> None:
        """Test hash of Ok Results."""
        assert hash(Ok(42)) == hash(Ok(42))
        assert hash(Ok(42)) != hash(Ok(43))

    def test_error_hash(self) -> None:
        """Test hash of Error Results."""
        error = Error(code="TEST", message="Test")
        assert hash(Err(error)) == hash(Err(error))


class TestErrorClass:
    """Tests for Error dataclass."""

    def test_error_str(self) -> None:
        """Test string representation of Error."""
        error = Error(code="NOT_FOUND", message="Not found")
        assert str(error) == "NOT_FOUND: Not found"

    def test_error_with_detail(self) -> None:
        """Test adding details to Error."""
        error = Error(code="VALIDATION", message="Invalid input")
        error_with_id = error.with_detail("id", "123")
        assert error_with_id.details == {"id": "123"}
        # Original error unchanged
        assert error.details is None

    def test_error_multiple_details(self) -> None:
        """Test adding multiple details."""
        error = Error(code="VALIDATION", message="Invalid input", details={"field": "name"})
        error_full = error.with_detail("value", "test")
        assert error_full.details == {"field": "name", "value": "test"}

    def test_error_default_values(self) -> None:
        """Test Error default values."""
        error = Error(code="TEST", message="Test")
        assert error.recoverable is True
        assert error.details is None


class TestNotFoundError:
    """Tests for NotFoundError."""

    def test_not_found_error(self) -> None:
        """Test NotFoundError creation."""
        error = NotFoundError("Character not found", details={"id": "123"})
        assert error.code == "NOT_FOUND"
        assert error.message == "Character not found"
        assert error.recoverable is False
        assert error.details == {"id": "123"}


class TestValidationError:
    """Tests for ValidationError."""

    def test_validation_error_basic(self) -> None:
        """Test ValidationError creation."""
        error = ValidationError("Invalid input")
        assert error.code == "VALIDATION_ERROR"
        assert error.recoverable is True

    def test_validation_error_with_field(self) -> None:
        """Test ValidationError with field."""
        error = ValidationError("Invalid input", field="email")
        assert error.details == {"field": "email"}

    def test_validation_error_with_details(self) -> None:
        """Test ValidationError with custom details."""
        error = ValidationError("Invalid input", details={"constraint": "required"})
        assert error.details == {"constraint": "required"}


class TestConflictError:
    """Tests for ConflictError."""

    def test_conflict_error(self) -> None:
        """Test ConflictError creation."""
        error = ConflictError("Name already exists")
        assert error.code == "CONFLICT"
        assert error.message == "Name already exists"
        assert error.recoverable is True


class TestPermissionError:
    """Tests for PermissionError."""

    def test_permission_error(self) -> None:
        """Test PermissionError creation."""
        error = PermissionError("Access denied", details={"resource": "admin"})
        assert error.code == "PERMISSION_DENIED"
        assert error.message == "Access denied"
        assert error.recoverable is False


class TestSaveError:
    """Tests for SaveError."""

    def test_save_error_basic(self) -> None:
        """Test SaveError creation."""
        error = SaveError("Save failed")
        assert error.code == "SAVE_ERROR"
        assert error.recoverable is True

    def test_save_error_with_entity_type(self) -> None:
        """Test SaveError with entity type."""
        error = SaveError("Save failed", entity_type="Character")
        assert error.details == {"entity_type": "Character"}


class TestUnwrapAlias:
    """Tests for Unwrap alias."""

    def test_unwrap_alias(self) -> None:
        """Test that Unwrap is an alias for Err."""
        error = Error(code="TEST", message="Test")
        result = Unwrap(error)
        assert result.is_error
        assert result.error == error
