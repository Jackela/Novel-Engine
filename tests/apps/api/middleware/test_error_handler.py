"""
Tests for error handler middleware.
"""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.apps.api.middleware.error_handler import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationAPIError,
    error_handler_middleware,
    format_validation_errors,
    general_exception_handler,
    setup_exception_handlers,
)


class TestAPIErrorClasses:
    """Test custom API error classes."""

    def test_base_api_error(self):
        """Test base APIError."""
        error = APIError("Test error", 400, "TEST_ERROR", {"detail": "test"})
        assert error.message == "Test error"
        assert error.status_code == 400
        assert error.error_code == "TEST_ERROR"
        assert error.details == {"detail": "test"}

    def test_not_found_error(self):
        """Test NotFoundError."""
        error = NotFoundError("User", "123")
        assert error.status_code == 404
        assert error.error_code == "NOT_FOUND"
        assert "User with id '123' not found" in error.message

    def test_not_found_error_without_id(self):
        """Test NotFoundError without ID."""
        error = NotFoundError("Resource")
        assert "Resource not found" in error.message

    def test_conflict_error(self):
        """Test ConflictError."""
        error = ConflictError("Resource already exists")
        assert error.status_code == 409
        assert error.error_code == "CONFLICT"

    def test_validation_api_error(self):
        """Test ValidationAPIError."""
        error = ValidationAPIError("Invalid input", {"field": "name"})
        assert error.status_code == 422
        assert error.error_code == "VALIDATION_ERROR"
        assert error.details == {"field": "name"}

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError()
        assert error.status_code == 401
        assert error.error_code == "UNAUTHORIZED"

    def test_authentication_error_custom(self):
        """Test AuthenticationError with custom message."""
        error = AuthenticationError("Token expired")
        assert error.message == "Token expired"

    def test_authorization_error(self):
        """Test AuthorizationError."""
        error = AuthorizationError()
        assert error.status_code == 403
        assert error.error_code == "FORBIDDEN"

    def test_authorization_error_custom(self):
        """Test AuthorizationError with custom message."""
        error = AuthorizationError("Insufficient permissions")
        assert error.message == "Insufficient permissions"


class TestFormatValidationErrors:
    """Test validation error formatting."""

    def test_format_validation_errors(self):
        """Test formatting of validation errors."""
        errors = [
            {"loc": ["body", "name"], "msg": "Field required", "type": "missing"},
            {"loc": ["body", "age"], "msg": "Must be positive", "type": "value_error"},
        ]
        formatted = format_validation_errors(errors)
        assert len(formatted) == 2
        assert formatted[0]["field"] == ".body.name"
        assert formatted[0]["message"] == "Field required"
        assert formatted[1]["field"] == ".body.age"

    def test_format_empty_errors(self):
        """Test formatting empty errors."""
        formatted = format_validation_errors([])
        assert formatted == []


@pytest.mark.asyncio
class TestExceptionHandlers:
    """Test exception handler functions."""

    async def test_api_error_handler(self):
        """Test API error handler."""
        app = FastAPI()

        @app.get("/error")
        def raise_error():
            raise APIError("Test error", 400, "TEST_ERROR")

        setup_exception_handlers(app)
        client = TestClient(app)

        response = client.get("/error")
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "TEST_ERROR"
        assert data["error"]["message"] == "Test error"

    async def test_http_exception_handler(self):
        """Test HTTP exception handler."""
        app = FastAPI()

        @app.get("/not-found")
        def raise_not_found():
            raise HTTPException(404, "Not found")

        setup_exception_handlers(app)
        client = TestClient(app)

        response = client.get("/not-found")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    async def test_validation_exception_handler(self):
        """Test validation exception handler."""
        app = FastAPI()

        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str
            age: int

        @app.post("/validate")
        def validate(data: TestModel):
            return data

        setup_exception_handlers(app)
        client = TestClient(app)

        response = client.post("/validate", json={"age": "not-a-number"})
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_general_exception_handler(self):
        """Test general exception handler."""
        import json

        class MockRequest:
            url = type("URL", (), {"path": "/test"})()
            method = "GET"

        exc = ValueError("Unexpected error")
        response = await general_exception_handler(MockRequest(), exc)

        assert response.status_code == 500
        data = json.loads(response.body)
        assert data["error"]["code"] == "INTERNAL_ERROR"
        assert "error_id" in data["error"]


class TestSetupExceptionHandlers:
    """Test exception handler setup."""

    def test_setup_exception_handlers(self):
        """Test that exception handlers are registered."""
        app = FastAPI()
        setup_exception_handlers(app)

        # Handlers are registered - app should work
        assert len(app.exception_handlers) > 0


class TestErrorHandlerMiddleware:
    """Test error handler middleware."""

    @pytest.mark.asyncio
    async def test_error_handler_middleware_success(self):
        """Test middleware with successful request."""

        class MockRequest:
            url = type("URL", (), {"path": "/test"})()
            method = "GET"

        async def mock_next(request):
            return type("Response", (), {"status_code": 200})()

        response = await error_handler_middleware(MockRequest(), mock_next)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_error_handler_middleware_error(self):
        """Test middleware with error."""

        class MockRequest:
            url = type("URL", (), {"path": "/test"})()
            method = "GET"

        async def mock_next(request):
            raise ValueError("Test error")

        response = await error_handler_middleware(MockRequest(), mock_next)
        assert response.status_code == 500
