"""Tests for Result Pattern module.

Tests cover:
- Ok creation and unwrap
- Err creation and unwrap_err
- is_ok / is_err properties
- map() on Ok and Err
- and_then() / or_else() chaining
- Error class functionality
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from src.core.result import (
    ConflictError,
    Err,
    Error,
    NotFoundError,
    Ok,
    PermissionError,
    Result,
    SaveError,
    ValidationError,
)


class TestOkCreation:
    """Test Ok Result creation and basic properties."""

    def test_ok_creation_with_value(self) -> None:
        """Test creating an Ok Result with a value."""
        result = Ok(42)
        
        assert result.is_ok is True
        assert result.is_error is False
        assert result.value == 42

    def test_ok_creation_with_string(self) -> None:
        """Test creating an Ok Result with a string."""
        result = Ok("success")
        
        assert result.value == "success"

    def test_ok_creation_with_object(self) -> None:
        """Test creating an Ok Result with an object."""
        obj = {"key": "value"}
        result = Ok(obj)
        
        assert result.value == obj

    def test_ok_unwrap_returns_value(self) -> None:
        """Test unwrap returns the success value."""
        result = Ok(42)
        
        assert result.unwrap() == 42

    def test_ok_error_property_raises(self) -> None:
        """Test accessing error property on Ok raises ValueError."""
        result = Ok(42)
        
        with pytest.raises(ValueError, match="Cannot get error from Ok Result"):
            _ = result.error


class TestErrCreation:
    """Test Err Result creation and basic properties."""

    def test_err_creation_with_error(self) -> None:
        """Test creating an Err Result with an error."""
        error = Error(code="TEST_ERROR", message="Test error message")
        result = Err(error)
        
        assert result.is_ok is False
        assert result.is_error is True
        assert result.error == error

    def test_err_value_property_raises(self) -> None:
        """Test accessing value property on Err raises ValueError."""
        error = Error(code="TEST_ERROR", message="Test error message")
        result = Err(error)
        
        with pytest.raises(ValueError, match="Cannot get value from Error Result"):
            _ = result.value

    def test_err_unwrap_returns_default(self) -> None:
        """Test unwrap on Err returns default value."""
        error = Error(code="TEST_ERROR", message="Test error message")
        result = Err(error)
        
        assert result.unwrap() is None
        assert result.unwrap(default="fallback") == "fallback"


class TestOkMap:
    """Test map() method on Ok Results."""

    def test_ok_map_transforms_value(self) -> None:
        """Test map transforms the success value."""
        result = Ok(5)
        mapped = result.map(lambda x: x * 2)
        
        assert mapped.is_ok is True
        assert mapped.value == 10

    def test_ok_map_chaining(self) -> None:
        """Test map can be chained."""
        result = Ok(5)
        mapped = result.map(lambda x: x * 2).map(lambda x: x + 1)
        
        assert mapped.value == 11

    def test_ok_map_with_string_transformation(self) -> None:
        """Test map with string transformation."""
        result = Ok("hello")
        mapped = result.map(lambda s: s.upper())
        
        assert mapped.value == "HELLO"

    def test_ok_map_exception_becomes_err(self) -> None:
        """Test that exceptions in map function become Err."""
        result = Ok(5)
        mapped = result.map(lambda x: x / 0)  # Division by zero
        
        assert mapped.is_error is True
        assert mapped.error.code == "MAP_FAILED"


class TestErrMap:
    """Test map() method on Err Results."""

    def test_err_map_is_no_op(self) -> None:
        """Test map on Err is a no-op and returns the same error."""
        error = Error(code="TEST_ERROR", message="Test error")
        result = Err(error)
        mapped = result.map(lambda x: x * 2)
        
        assert mapped.is_error is True
        assert mapped.error == error

    def test_err_map_does_not_call_function(self) -> None:
        """Test map function is not called on Err."""
        error = Error(code="TEST_ERROR", message="Test error")
        result = Err(error)
        
        function_called = False
        def transform(x: int) -> int:
            nonlocal function_called
            function_called = True
            return x * 2
        
        result.map(transform)
        
        assert not function_called


class TestAndThen:
    """Test and_then() method for chaining Results."""

    def test_ok_and_then_with_ok_result(self) -> None:
        """Test and_then on Ok with function returning Ok."""
        result = Ok(5)
        chained = result.and_then(lambda x: Ok(x * 2))
        
        assert chained.is_ok is True
        assert chained.value == 10

    def test_ok_and_then_with_err_result(self) -> None:
        """Test and_then on Ok with function returning Err."""
        result = Ok(5)
        error = Error(code="CHAIN_ERROR", message="Chain failed")
        chained = result.and_then(lambda x: Err(error))
        
        assert chained.is_error is True
        assert chained.error == error

    def test_err_and_then_is_no_op(self) -> None:
        """Test and_then on Err is a no-op."""
        error = Error(code="TEST_ERROR", message="Test error")
        result = Err(error)
        
        function_called = False
        def transform(x: int) -> Result[int, Error]:
            nonlocal function_called
            function_called = True
            return Ok(x * 2)
        
        chained = result.and_then(transform)
        
        assert not function_called
        assert chained.is_error is True
        assert chained.error == error


class TestOrElse:
    """Test or_else() method for error recovery."""

    def test_ok_or_else_is_no_op(self) -> None:
        """Test or_else on Ok is a no-op."""
        result = Ok(5)
        
        function_called = False
        def recover(e: Error) -> Result[int, Error]:
            nonlocal function_called
            function_called = True
            return Ok(0)
        
        recovered = result.or_else(recover)
        
        assert not function_called
        assert recovered.is_ok is True
        assert recovered.value == 5

    def test_err_or_else_with_recovery(self) -> None:
        """Test or_else on Err with recovery function."""
        error = Error(code="TEST_ERROR", message="Test error")
        result = Err(error)
        
        recovered = result.or_else(lambda e: Ok(42))
        
        assert recovered.is_ok is True
        assert recovered.value == 42

    def test_err_or_else_with_another_err(self) -> None:
        """Test or_else on Err with function returning another Err."""
        error1 = Error(code="ERROR_1", message="First error")
        error2 = Error(code="ERROR_2", message="Second error")
        result = Err(error1)
        
        recovered = result.or_else(lambda e: Err(error2))
        
        assert recovered.is_error is True
        assert recovered.error == error2


class TestOnSuccess:
    """Test on_success() callback."""

    def test_ok_on_success_calls_function(self) -> None:
        """Test on_success on Ok calls the function."""
        result = Ok(42)
        callback_value = None
        
        def callback(value: int) -> None:
            nonlocal callback_value
            callback_value = value
        
        returned = result.on_success(callback)
        
        assert callback_value == 42
        assert returned == result  # Returns self for chaining

    def test_err_on_success_is_no_op(self) -> None:
        """Test on_success on Err is a no-op."""
        error = Error(code="TEST_ERROR", message="Test error")
        result = Err(error)
        
        function_called = False
        def callback(value: int) -> None:
            nonlocal function_called
            function_called = True
        
        result.on_success(callback)
        
        assert not function_called


class TestOnError:
    """Test on_error() callback."""

    def test_ok_on_error_is_no_op(self) -> None:
        """Test on_error on Ok is a no-op."""
        result = Ok(42)
        
        function_called = False
        def callback(error: Error) -> None:
            nonlocal function_called
            function_called = True
        
        result.on_error(callback)
        
        assert not function_called

    def test_err_on_error_calls_function(self) -> None:
        """Test on_error on Err calls the function."""
        error = Error(code="TEST_ERROR", message="Test error")
        result = Err(error)
        callback_error = None
        
        def callback(e: Error) -> None:
            nonlocal callback_error
            callback_error = e
        
        returned = result.on_error(callback)
        
        assert callback_error == error
        assert returned == result  # Returns self for chaining


class TestErrorClass:
    """Test Error class."""

    def test_error_creation(self) -> None:
        """Test creating an Error."""
        error = Error(
            code="TEST_ERROR",
            message="Test message",
            recoverable=True,
            details={"key": "value"}
        )
        
        assert error.code == "TEST_ERROR"
        assert error.message == "Test message"
        assert error.recoverable is True
        assert error.details == {"key": "value"}

    def test_error_defaults(self) -> None:
        """Test Error with default values."""
        error = Error(code="TEST_ERROR", message="Test message")
        
        assert error.recoverable is True
        assert error.details is None

    def test_error_with_detail(self) -> None:
        """Test adding detail to error."""
        error = Error(code="TEST_ERROR", message="Test message")
        new_error = error.with_detail("user_id", "123")
        
        assert new_error.details == {"user_id": "123"}
        assert new_error.code == "TEST_ERROR"  # Original unchanged

    def test_error_str_representation(self) -> None:
        """Test string representation of Error."""
        error = Error(code="TEST_ERROR", message="Test message")
        
        assert str(error) == "TEST_ERROR: Test message"


class TestNotFoundError:
    """Test NotFoundError subclass."""

    def test_not_found_error_creation(self) -> None:
        """Test creating a NotFoundError."""
        error = NotFoundError("Entity not found")
        
        assert error.code == "NOT_FOUND"
        assert error.message == "Entity not found"
        assert error.recoverable is False

    def test_not_found_error_with_details(self) -> None:
        """Test NotFoundError with details."""
        error = NotFoundError("Entity not found", details={"entity_id": "123"})
        
        assert error.details == {"entity_id": "123"}


class TestValidationError:
    """Test ValidationError subclass."""

    def test_validation_error_creation(self) -> None:
        """Test creating a ValidationError."""
        error = ValidationError("Invalid input")
        
        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Invalid input"
        assert error.recoverable is True

    def test_validation_error_with_field(self) -> None:
        """Test ValidationError with field."""
        error = ValidationError("Invalid value", field="email")
        
        assert error.details == {"field": "email"}


class TestConflictError:
    """Test ConflictError subclass."""

    def test_conflict_error_creation(self) -> None:
        """Test creating a ConflictError."""
        error = ConflictError("Resource conflict")
        
        assert error.code == "CONFLICT"
        assert error.message == "Resource conflict"
        assert error.recoverable is True


class TestPermissionError:
    """Test PermissionError subclass."""

    def test_permission_error_creation(self) -> None:
        """Test creating a PermissionError."""
        error = PermissionError("Access denied")
        
        assert error.code == "PERMISSION_DENIED"
        assert error.message == "Access denied"
        assert error.recoverable is False


class TestSaveError:
    """Test SaveError subclass."""

    def test_save_error_creation(self) -> None:
        """Test creating a SaveError."""
        error = SaveError("Save failed")
        
        assert error.code == "SAVE_ERROR"
        assert error.message == "Save failed"
        assert error.recoverable is True

    def test_save_error_with_entity_type(self) -> None:
        """Test SaveError with entity type."""
        error = SaveError("Save failed", entity_type="Character")
        
        assert error.details == {"entity_type": "Character"}


class TestOkEquality:
    """Test equality comparison for Ok."""

    def test_ok_equal_same_value(self) -> None:
        """Test Ok with same value are equal."""
        ok1 = Ok(42)
        ok2 = Ok(42)
        
        assert ok1 == ok2

    def test_ok_not_equal_different_value(self) -> None:
        """Test Ok with different values are not equal."""
        ok1 = Ok(42)
        ok2 = Ok(43)
        
        assert ok1 != ok2

    def test_ok_not_equal_to_err(self) -> None:
        """Test Ok is not equal to Err."""
        ok = Ok(42)
        err = Err(Error(code="TEST", message="Test"))
        
        assert ok != err


class TestErrEquality:
    """Test equality comparison for Err."""

    def test_err_equal_same_error(self) -> None:
        """Test Err with same error are equal."""
        error = Error(code="TEST", message="Test")
        err1 = Err(error)
        err2 = Err(error)
        
        assert err1 == err2

    def test_err_not_equal_different_error(self) -> None:
        """Test Err with different errors are not equal."""
        err1 = Err(Error(code="TEST1", message="Test 1"))
        err2 = Err(Error(code="TEST2", message="Test 2"))
        
        assert err1 != err2


class TestOkRepr:
    """Test repr for Ok."""

    def test_ok_repr(self) -> None:
        """Test repr of Ok."""
        ok = Ok(42)
        
        assert repr(ok) == "Ok(42)"

    def test_ok_repr_with_string(self) -> None:
        """Test repr of Ok with string."""
        ok = Ok("hello")
        
        assert repr(ok) == "Ok('hello')"


class TestErrRepr:
    """Test repr for Err."""

    def test_err_repr(self) -> None:
        """Test repr of Err."""
        error = Error(code="TEST", message="Test error")
        err = Err(error)
        
        repr_str = repr(err)
        
        assert "Err" in repr_str
        assert "TEST" in repr_str
