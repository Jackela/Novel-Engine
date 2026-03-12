"""Unit tests for error_handlers module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException

pytestmark = pytest.mark.unit

from src.api.error_handlers import (
    ConflictException,
    ErrorHandler,
    NovelEngineException,
    RateLimitException,
    ResourceNotFoundException,
    ServiceUnavailableException,
    ValidationException,
    setup_error_handlers,
)
from src.api.response_envelopes import APIErrorType, ResponseStatus


@pytest.mark.unit
class TestNovelEngineException:
    """Tests for NovelEngineException base class."""

    def test_basic_exception(self) -> None:
        """Test creating basic NovelEngineException."""
        exc = NovelEngineException(
            message="Test error",
            error_type=APIErrorType.INTERNAL_ERROR,
            status_code=500,
        )

        assert exc.message == "Test error"
        assert exc.error_type == APIErrorType.INTERNAL_ERROR
        assert exc.status_code == 500
        assert exc.detail is None
        assert exc.code is None
        assert str(exc) == "Test error"

    def test_exception_with_detail_and_code(self) -> None:
        """Test NovelEngineException with detail and code."""
        exc = NovelEngineException(
            message="Error occurred",
            error_type=APIErrorType.NOT_FOUND,
            status_code=404,
            detail="The resource was not found",
            code="RESOURCE_NOT_FOUND",
        )

        assert exc.detail == "The resource was not found"
        assert exc.code == "RESOURCE_NOT_FOUND"

    def test_default_values(self) -> None:
        """Test NovelEngineException default values."""
        exc = NovelEngineException(message="Test")

        assert exc.error_type == APIErrorType.INTERNAL_ERROR
        assert exc.status_code == 500


@pytest.mark.unit
class TestValidationException:
    """Tests for ValidationException."""

    def test_basic_validation_exception(self) -> None:
        """Test creating ValidationException."""
        exc = ValidationException(
            message="Validation failed",
            field="email",
            detail="Must be a valid email",
        )

        assert exc.message == "Validation failed"
        assert exc.field == "email"
        assert exc.detail == "Must be a valid email"
        assert exc.error_type == APIErrorType.VALIDATION_ERROR
        assert exc.status_code == 422

    def test_validation_exception_without_field(self) -> None:
        """Test ValidationException without field."""
        exc = ValidationException(message="Validation failed")

        assert exc.field is None
        assert exc.status_code == 422


@pytest.mark.unit
class TestResourceNotFoundException:
    """Tests for ResourceNotFoundException."""

    def test_resource_not_found(self) -> None:
        """Test creating ResourceNotFoundException."""
        exc = ResourceNotFoundException(
            resource_type="Character", resource_id="char-123"
        )

        assert exc.message == "Character 'char-123' not found"
        assert exc.error_type == APIErrorType.NOT_FOUND
        assert exc.status_code == 404
        assert "does not exist" in exc.detail

    def test_resource_not_found_different_types(self) -> None:
        """Test ResourceNotFoundException with different resource types."""
        exc_user = ResourceNotFoundException(
            resource_type="User", resource_id="user-456"
        )
        assert "User 'user-456'" in exc_user.message

        exc_item = ResourceNotFoundException(
            resource_type="Item", resource_id="item-789"
        )
        assert "Item 'item-789'" in exc_item.message


@pytest.mark.unit
class TestServiceUnavailableException:
    """Tests for ServiceUnavailableException."""

    def test_service_unavailable(self) -> None:
        """Test creating ServiceUnavailableException."""
        exc = ServiceUnavailableException(service_name="Database")

        assert "Database service is currently unavailable" in exc.message
        assert exc.error_type == APIErrorType.SERVICE_UNAVAILABLE
        assert exc.status_code == 503
        assert "try again later" in exc.detail.lower()

    def test_service_unavailable_with_detail(self) -> None:
        """Test ServiceUnavailableException with custom detail."""
        exc = ServiceUnavailableException(
            service_name="Redis",
            detail="Connection timeout after 30 seconds",
        )

        assert "Redis service" in exc.message
        assert exc.detail == "Connection timeout after 30 seconds"


@pytest.mark.unit
class TestConflictException:
    """Tests for ConflictException."""

    def test_conflict_exception(self) -> None:
        """Test creating ConflictException."""
        exc = ConflictException(message="Resource already exists")

        assert exc.message == "Resource already exists"
        assert exc.error_type == APIErrorType.CONFLICT
        assert exc.status_code == 409

    def test_conflict_with_detail(self) -> None:
        """Test ConflictException with detail."""
        exc = ConflictException(
            message="Duplicate entry",
            detail="A user with this email already exists",
        )

        assert exc.detail == "A user with this email already exists"


@pytest.mark.unit
class TestRateLimitException:
    """Tests for RateLimitException."""

    def test_rate_limit_with_retry_after(self) -> None:
        """Test RateLimitException with retry_after."""
        exc = RateLimitException(retry_after=60)

        assert "Rate limit exceeded" in exc.message
        assert exc.error_type == APIErrorType.RATE_LIMITED
        assert exc.status_code == 429
        assert "60 seconds" in exc.detail

    def test_rate_limit_without_retry_after(self) -> None:
        """Test RateLimitException without retry_after."""
        exc = RateLimitException()

        assert "slow down" in exc.detail.lower()


@pytest.mark.unit
class TestErrorHandler:
    """Tests for ErrorHandler class."""

    def test_error_handler_initialization(self) -> None:
        """Test ErrorHandler initialization."""
        handler = ErrorHandler(debug=False)

        assert handler.debug is False
        assert handler.error_count == 0

    def test_error_handler_debug_mode(self) -> None:
        """Test ErrorHandler with debug mode."""
        handler = ErrorHandler(debug=True)

        assert handler.debug is True

    def test_create_error_response_novelengine_exception(self) -> None:
        """Test creating error response from NovelEngineException."""
        handler = ErrorHandler()
        exc = ResourceNotFoundException(resource_type="Character", resource_id="123")

        response = handler.create_error_response(error=exc)

        assert response.status == ResponseStatus.ERROR
        assert response.error.type == APIErrorType.NOT_FOUND
        assert "Character '123'" in response.error.message
        assert handler.error_count == 1

    def test_create_error_response_http_exception(self) -> None:
        """Test creating error response from HTTPException."""
        handler = ErrorHandler()
        exc = HTTPException(status_code=403, detail="Access denied")

        response = handler.create_error_response(error=exc)

        assert response.error.type == APIErrorType.FORBIDDEN
        assert response.error.message == "Access denied"

    def test_create_error_response_generic_exception(self) -> None:
        """Test creating error response from generic Exception."""
        handler = ErrorHandler(debug=False)
        exc = ValueError("Something went wrong")

        response = handler.create_error_response(error=exc)

        assert response.error.type == APIErrorType.INTERNAL_ERROR
        assert "unexpected error occurred" in response.error.message.lower()
        assert response.error.detail is None  # No stack trace in production

    def test_create_error_response_generic_exception_debug_mode(self) -> None:
        """Test creating error response in debug mode."""
        handler = ErrorHandler(debug=True)
        exc = ValueError("Debug error details")

        response = handler.create_error_response(error=exc)

        assert "Debug error details" in response.error.message

    def test_create_error_response_with_request(self) -> None:
        """Test creating error response with request context."""
        handler = ErrorHandler()
        exc = NovelEngineException(message="Test error")

        request = MagicMock()
        request.method = "POST"
        request.url = "http://test.com/api/test"
        request.client.host = "192.168.1.1"

        response = handler.create_error_response(error=exc, request=request)

        assert response.status == ResponseStatus.ERROR

    def test_create_error_response_with_request_id(self) -> None:
        """Test creating error response with request ID."""
        handler = ErrorHandler()
        exc = NovelEngineException(message="Test error")

        response = handler.create_error_response(error=exc, request_id="req-abc-123")

        assert response.metadata.request_id == "req-abc-123"

    def test_create_error_response_with_processing_time(self) -> None:
        """Test creating error response with processing time."""
        handler = ErrorHandler()
        exc = NovelEngineException(message="Test error")

        response = handler.create_error_response(error=exc, processing_time=0.123)

        assert response.metadata.server_time == 0.123

    def test_create_validation_error_response(self) -> None:
        """Test creating validation error response."""
        handler = ErrorHandler()

        from src.api.response_envelopes import ValidationError

        validation_errors = [
            ValidationError(field="email", message="Invalid email"),
            ValidationError(field="age", message="Must be positive"),
        ]

        response = handler.create_validation_error_response(
            validation_errors=validation_errors,
            request_id="req-123",
            processing_time=0.1,
        )

        assert response.status == ResponseStatus.ERROR
        assert response.error.type == APIErrorType.VALIDATION_ERROR
        assert "2 field(s)" in response.error.message
        assert len(response.errors) == 2
        assert response.metadata.request_id == "req-123"

    def test_map_http_status_to_error_type(self) -> None:
        """Test HTTP status to error type mapping."""
        handler = ErrorHandler()

        assert handler._map_http_status_to_error_type(400) == APIErrorType.BAD_REQUEST
        assert handler._map_http_status_to_error_type(401) == APIErrorType.UNAUTHORIZED
        assert handler._map_http_status_to_error_type(403) == APIErrorType.FORBIDDEN
        assert handler._map_http_status_to_error_type(404) == APIErrorType.NOT_FOUND
        assert handler._map_http_status_to_error_type(409) == APIErrorType.CONFLICT
        assert (
            handler._map_http_status_to_error_type(422) == APIErrorType.VALIDATION_ERROR
        )
        assert handler._map_http_status_to_error_type(429) == APIErrorType.RATE_LIMITED
        assert (
            handler._map_http_status_to_error_type(500) == APIErrorType.INTERNAL_ERROR
        )
        assert (
            handler._map_http_status_to_error_type(503)
            == APIErrorType.SERVICE_UNAVAILABLE
        )
        assert handler._map_http_status_to_error_type(504) == APIErrorType.TIMEOUT
        assert (
            handler._map_http_status_to_error_type(999) == APIErrorType.INTERNAL_ERROR
        )

    def test_error_count_increment(self) -> None:
        """Test that error_count increments correctly."""
        handler = ErrorHandler()

        assert handler.error_count == 0

        handler.create_error_response(error=Exception("Test 1"))
        assert handler.error_count == 1

        handler.create_error_response(error=Exception("Test 2"))
        assert handler.error_count == 2


@pytest.mark.unit
class TestSetupErrorHandlers:
    """Tests for setup_error_handlers function."""

    def test_setup_error_handlers_returns_handler(self) -> None:
        """Test that setup_error_handlers returns ErrorHandler instance."""
        app = FastAPI()

        handler = setup_error_handlers(app, debug=False)

        assert isinstance(handler, ErrorHandler)
        assert handler.debug is False

    @pytest.mark.asyncio
    async def test_setup_error_handlers_handlers_registered(self) -> None:
        """Test that exception handlers are registered."""
        app = FastAPI()
        setup_error_handlers(app)

        # Test NovelEngineException handler
        @app.get("/novel-exception")
        async def novel_exception():
            raise NovelEngineException(
                message="Test",
                status_code=418,
            )

        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/novel-exception")

        assert response.status_code == 418
        assert response.json()["error"]["type"] == "internal_error"

    @pytest.mark.asyncio
    async def test_setup_validation_error_handler(self) -> None:
        """Test validation error handler with setup_error_handlers."""
        app = FastAPI()
        setup_error_handlers(app)

        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str

        @app.post("/validate")
        async def validate(data: TestModel):
            return data

        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.post("/validate", json={"name": 123})

        assert response.status_code == 422
        data = response.json()
        assert data["status"] == "error"
        assert "errors" in data


@pytest.mark.unit
class TestAllExports:
    """Tests for __all__ exports."""

    def test_all_exports_present(self) -> None:
        """Test that __all__ includes all expected exports."""
        from src.api.error_handlers import __all__

        expected = [
            "NovelEngineException",
            "ValidationException",
            "ResourceNotFoundException",
            "ServiceUnavailableException",
            "ConflictException",
            "RateLimitException",
            "ErrorHandler",
            "setup_error_handlers",
        ]

        for item in expected:
            assert item in __all__, f"{item} should be in __all__"
