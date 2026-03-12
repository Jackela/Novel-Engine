#!/usr/bin/env python3
"""
Unit tests for response_builder module.

Tests the ResponseBuilder class for creating standardized response objects
with various configurations and edge cases.
"""

from typing import Any, Dict

import pytest

from src.core.data_models import ErrorInfo, StandardResponse

pytestmark = pytest.mark.unit
from src.core.utils.response_builder import ResponseBuilder


class TestResponseBuilderSuccess:
    """Test suite for ResponseBuilder.success method."""

    def test_success_with_data_only(self) -> None:
        """Test building success response with only data."""
        data = {"id": 1, "name": "test"}
        result = ResponseBuilder.success(data)

        assert isinstance(result, StandardResponse)
        assert result.success is True
        assert result.data == data
        assert result.error is None
        assert result.metadata == {}

    def test_success_with_message(self) -> None:
        """Test building success response with message."""
        data = {"id": 1}
        message = "Operation completed successfully"
        result = ResponseBuilder.success(data, message=message)

        assert result.success is True
        assert result.data == data
        assert result.metadata.get("message") == message

    def test_success_with_metadata(self) -> None:
        """Test building success response with custom metadata."""
        data = {"id": 1}
        metadata = {"page": 1, "total": 100}
        result = ResponseBuilder.success(data, metadata=metadata)

        assert result.success is True
        assert result.data == data
        assert result.metadata.get("page") == 1
        assert result.metadata.get("total") == 100

    def test_success_with_message_and_metadata(self) -> None:
        """Test building success response with both message and metadata."""
        data = {"items": [1, 2, 3]}
        message = "Items retrieved"
        metadata = {"count": 3, "page": 1}
        result = ResponseBuilder.success(data, message=message, metadata=metadata)

        assert result.success is True
        assert result.data == data
        assert result.metadata.get("message") == message
        assert result.metadata.get("count") == 3
        assert result.metadata.get("page") == 1

    def test_success_with_empty_data(self) -> None:
        """Test building success response with empty data."""
        result = ResponseBuilder.success({})

        assert result.success is True
        assert result.data == {}

    def test_success_with_nested_data(self) -> None:
        """Test building success response with nested data structure."""
        data = {
            "user": {"id": 1, "name": "John"},
            "roles": ["admin", "user"],
            "settings": {"theme": "dark"},
        }
        result = ResponseBuilder.success(data)

        assert result.success is True
        assert result.data == data

    @pytest.mark.parametrize("data", [
        {},
        {"key": "value"},
        [],
        [1, 2, 3],
        "string",
        123,
        None,
        True,
    ])
    def test_success_with_various_data_types(self, data: Any) -> None:
        """Test building success response with various data types."""
        result = ResponseBuilder.success(data)

        assert result.success is True
        assert result.data == data


class TestResponseBuilderError:
    """Test suite for ResponseBuilder.error method."""

    def test_error_with_minimal_params(self) -> None:
        """Test building error response with minimal parameters."""
        result = ResponseBuilder.error("ERROR_CODE", "Error message")

        assert isinstance(result, StandardResponse)
        assert result.success is False
        assert result.error is not None
        assert isinstance(result.error, ErrorInfo)
        assert result.error.code == "ERROR_CODE"
        assert result.error.message == "Error message"
        assert result.error.recoverable is True
        assert result.error.details == {}

    def test_error_with_recoverable_false(self) -> None:
        """Test building non-recoverable error response."""
        result = ResponseBuilder.error(
            "CRITICAL_ERROR", "Critical failure", recoverable=False
        )

        assert result.success is False
        assert result.error is not None
        assert result.error.recoverable is False

    def test_error_with_details(self) -> None:
        """Test building error response with details."""
        details = {"field": "email", "reason": "invalid_format"}
        result = ResponseBuilder.error(
            "VALIDATION_ERROR", "Validation failed", details=details
        )

        assert result.success is False
        assert result.error is not None
        assert result.error.details == details

    def test_error_with_all_params(self) -> None:
        """Test building error response with all parameters."""
        result = ResponseBuilder.error(
            code="CUSTOM_ERROR",
            message="Something went wrong",
            recoverable=False,
            details={"context": "test"},
        )

        assert result.success is False
        assert result.error is not None
        assert result.error.code == "CUSTOM_ERROR"
        assert result.error.message == "Something went wrong"
        assert result.error.recoverable is False
        assert result.error.details == {"context": "test"}

    @pytest.mark.parametrize("code,message", [
        ("E1", "Simple error"),
        ("VERY_LONG_ERROR_CODE_NAME", "Error with long code"),
        ("ERR-123", "Error with hyphen"),
        ("ERR_456", "Error with underscore"),
        ("", "Empty code"),
        ("CODE", ""),
    ])
    def test_error_with_various_codes_and_messages(self, code: str, message: str) -> None:
        """Test building error response with various code and message formats."""
        result = ResponseBuilder.error(code, message)

        assert result.success is False
        assert result.error is not None
        assert result.error.code == code
        assert result.error.message == message


class TestResponseBuilderNotFound:
    """Test suite for ResponseBuilder.not_found method."""

    def test_not_found_basic(self) -> None:
        """Test building not found response."""
        result = ResponseBuilder.not_found("user", "123")

        assert isinstance(result, StandardResponse)
        assert result.success is False
        assert result.error is not None
        assert result.error.code == "USER_NOT_FOUND"
        assert "User '123' not found" in result.error.message

    def test_not_found_different_entities(self) -> None:
        """Test not found with different entity types."""
        test_cases = [
            ("equipment", "sword_001", "EQUIPMENT_NOT_FOUND"),
            ("character", "char_123", "CHARACTER_NOT_FOUND"),
            ("item", "item_456", "ITEM_NOT_FOUND"),
            ("agent", "agent_789", "AGENT_NOT_FOUND"),
        ]

        for entity_type, entity_id, expected_code in test_cases:
            result = ResponseBuilder.not_found(entity_type, entity_id)
            assert result.error is not None
            assert result.error.code == expected_code
            assert entity_type.capitalize() in result.error.message
            assert entity_id in result.error.message

    def test_not_found_with_special_chars_in_id(self) -> None:
        """Test not found with special characters in entity ID."""
        result = ResponseBuilder.not_found("file", "path/to/file.txt")

        assert result.error is not None
        assert result.error.code == "FILE_NOT_FOUND"
        assert "path/to/file.txt" in result.error.message

    @pytest.mark.parametrize("entity_type,entity_id", [
        ("", ""),
        ("test", ""),
        ("", "123"),
        ("entity", "id-with-hyphens"),
        ("entity", "id_with_underscores"),
    ])
    def test_not_found_edge_cases(self, entity_type: str, entity_id: str) -> None:
        """Test not found with edge case inputs."""
        result = ResponseBuilder.not_found(entity_type, entity_id)

        assert result.success is False
        assert result.error is not None
        assert entity_type.upper() in result.error.code
        assert entity_id in result.error.message


class TestResponseBuilderValidationError:
    """Test suite for ResponseBuilder.validation_error method."""

    def test_validation_error_basic(self) -> None:
        """Test building validation error response."""
        result = ResponseBuilder.validation_error("Field is required")

        assert isinstance(result, StandardResponse)
        assert result.success is False
        assert result.error is not None
        assert result.error.code == "VALIDATION_ERROR"
        assert result.error.message == "Field is required"
        assert result.error.details == {}

    def test_validation_error_with_details(self) -> None:
        """Test building validation error with details."""
        details = {"field": "email", "constraint": "must_be_email"}
        result = ResponseBuilder.validation_error("Invalid email format", details)

        assert result.success is False
        assert result.error is not None
        assert result.error.message == "Invalid email format"
        assert result.error.details == details

    def test_validation_error_with_empty_details(self) -> None:
        """Test building validation error with empty details dict."""
        result = ResponseBuilder.validation_error("Error message", {})

        assert result.success is False
        assert result.error is not None
        assert result.error.details == {}

    def test_validation_error_with_complex_details(self) -> None:
        """Test building validation error with complex details structure."""
        details: Dict[str, Any] = {
            "fields": ["name", "email", "age"],
            "errors": {
                "name": "Too short",
                "email": "Invalid format",
            },
            "context": {"form_id": "user_registration"},
        }
        result = ResponseBuilder.validation_error("Multiple validation errors", details)

        assert result.success is False
        assert result.error is not None
        assert result.error.details == details

    @pytest.mark.parametrize("message", [
        "Simple message",
        "",
        "Very long message " * 100,
        "Message with special chars: <>&\"'",
        "Unicode: 你好世界 🌍",
    ])
    def test_validation_error_various_messages(self, message: str) -> None:
        """Test validation error with various message formats."""
        result = ResponseBuilder.validation_error(message)

        assert result.success is False
        assert result.error is not None
        assert result.error.message == message


class TestResponseBuilderOperationFailed:
    """Test suite for ResponseBuilder.operation_failed method."""

    def test_operation_failed_basic(self) -> None:
        """Test building operation failed response."""
        exception = ValueError("Something broke")
        result = ResponseBuilder.operation_failed("database_save", exception)

        assert isinstance(result, StandardResponse)
        assert result.success is False
        assert result.error is not None
        assert result.error.code == "DATABASE_SAVE_FAILED"
        assert "database_save failed" in result.error.message
        assert "Something broke" in result.error.message

    def test_operation_failed_with_recoverable_false(self) -> None:
        """Test building non-recoverable operation failed response."""
        exception = RuntimeError("Critical system error")
        result = ResponseBuilder.operation_failed(
            "system_init", exception, recoverable=False
        )

        assert result.success is False
        assert result.error is not None
        assert result.error.recoverable is False

    def test_operation_failed_with_different_exceptions(self) -> None:
        """Test operation failed with different exception types."""
        exceptions = [
            ValueError("Invalid value"),
            TypeError("Wrong type"),
            KeyError("Missing key"),
            RuntimeError("Runtime problem"),
            ConnectionError("Connection failed"),
        ]

        for exc in exceptions:
            result = ResponseBuilder.operation_failed("test_op", exc)
            assert result.error is not None
            assert "test_op failed" in result.error.message
            assert str(exc) in result.error.message

    def test_operation_failed_with_empty_exception_message(self) -> None:
        """Test operation failed with exception having empty message."""
        exception = ValueError()
        result = ResponseBuilder.operation_failed("operation", exception)

        assert result.success is False
        assert result.error is not None
        assert result.error.code == "OPERATION_FAILED"

    def test_operation_failed_preserves_exception_type_in_message(self) -> None:
        """Test that exception message is properly converted to string."""
        exception = ValueError(123)  # Non-string exception argument
        result = ResponseBuilder.operation_failed("test", exception)

        assert result.success is False
        assert result.error is not None
        assert "123" in result.error.message


class TestResponseBuilderIntegration:
    """Integration tests for ResponseBuilder methods."""

    def test_success_followed_by_error(self) -> None:
        """Test creating both success and error responses in sequence."""
        success_result = ResponseBuilder.success({"id": 1})
        error_result = ResponseBuilder.error("NOT_FOUND", "Item not found")

        assert success_result.success is True
        assert error_result.success is False
        assert success_result.data == {"id": 1}
        assert error_result.error is not None

    def test_all_static_methods_independent(self) -> None:
        """Test that all static methods create independent responses."""
        responses = [
            ResponseBuilder.success({"test": 1}),
            ResponseBuilder.error("ERR", "msg"),
            ResponseBuilder.not_found("user", "123"),
            ResponseBuilder.validation_error("validation failed"),
            ResponseBuilder.operation_failed("op", Exception("error")),
        ]

        # Verify all are StandardResponse instances
        for resp in responses:
            assert isinstance(resp, StandardResponse)
            assert resp.timestamp is not None

    def test_response_metadata_isolation(self) -> None:
        """Test that metadata is isolated between responses."""
        result1 = ResponseBuilder.success({}, metadata={"key": "value1"})
        result2 = ResponseBuilder.success({}, metadata={"key": "value2"})

        assert result1.metadata.get("key") == "value1"
        assert result2.metadata.get("key") == "value2"

    def test_error_details_isolation(self) -> None:
        """Test that error details are isolated between responses."""
        result1 = ResponseBuilder.error("ERR", "msg", details={"a": 1})
        result2 = ResponseBuilder.error("ERR", "msg", details={"a": 2})

        assert result1.error is not None
        assert result2.error is not None
        assert result1.error.details == {"a": 1}
        assert result2.error.details == {"a": 2}

    def test_default_metadata_mutation_not_affected(self) -> None:
        """Test that default empty metadata dict doesn't cause issues."""
        result1 = ResponseBuilder.success({})
        result2 = ResponseBuilder.success({})

        # Modify first result's metadata
        result1.metadata["custom"] = "value"

        # Second result should not be affected
        assert "custom" not in result2.metadata
