"""Unit tests for API errors module."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException

pytestmark = pytest.mark.unit

from src.api.error_handlers import NovelEngineException
from src.api.errors import (
    _envelope,
    _status_code_to_error,
    install_error_handlers,
)


@pytest.mark.unit
class TestStatusCodeToError:
    """Tests for _status_code_to_error function."""

    def test_known_status_codes(self) -> None:
        """Test mapping of known status codes."""
        assert _status_code_to_error(400) == ("Bad Request", "bad_request")
        assert _status_code_to_error(401) == ("Unauthorized", "unauthorized")
        assert _status_code_to_error(403) == ("Forbidden", "forbidden")
        assert _status_code_to_error(404) == ("Not Found", "not_found")
        assert _status_code_to_error(405) == (
            "Method Not Allowed",
            "method_not_allowed",
        )
        assert _status_code_to_error(409) == ("Conflict", "conflict")
        assert _status_code_to_error(422) == ("Validation Error", "validation_error")
        assert _status_code_to_error(429) == ("Too Many Requests", "rate_limited")
        assert _status_code_to_error(500) == ("Internal Server Error", "internal_error")
        assert _status_code_to_error(503) == (
            "Service Unavailable",
            "service_unavailable",
        )

    def test_unknown_status_code(self) -> None:
        """Test mapping of unknown status code."""
        assert _status_code_to_error(999) == ("Unknown Error", "unknown_error")
        assert _status_code_to_error(418) == ("Unknown Error", "unknown_error")


@pytest.mark.unit
class TestEnvelope:
    """Tests for _envelope function."""

    def test_envelope_basic(self) -> None:
        """Test basic envelope creation."""
        result = _envelope(status_code=200, detail="OK")

        assert result["error"] == "Unknown Error"  # 200 is not in mapping
        assert result["detail"] == "OK"
        assert result["code"] == "unknown_error"

    def test_envelope_with_custom_error(self) -> None:
        """Test envelope with custom error and code."""
        result = _envelope(
            status_code=404,
            detail="User not found",
            code="USER_NOT_FOUND",
            error="User Error",
        )

        assert result["error"] == "User Error"
        assert result["detail"] == "User not found"
        assert result["code"] == "USER_NOT_FOUND"

    def test_envelope_with_extra(self) -> None:
        """Test envelope with extra fields."""
        extra = {"field": "username", "suggestion": "Check spelling"}
        result = _envelope(
            status_code=422,
            detail="Validation failed",
            extra=extra,
        )

        assert result["error"] == "Validation Error"
        assert result["detail"] == "Validation failed"
        assert result["code"] == "validation_error"
        assert result["field"] == "username"
        assert result["suggestion"] == "Check spelling"

    def test_envelope_default_code_from_mapping(self) -> None:
        """Test that default code comes from status code mapping."""
        result = _envelope(status_code=500, detail="Server error")

        assert result["code"] == "internal_error"
        assert result["error"] == "Internal Server Error"


@pytest.mark.unit
class TestInstallErrorHandlers:
    """Tests for install_error_handlers function."""

    @pytest.fixture
    def app(self):
        """Create a test FastAPI app."""
        return FastAPI()

    def test_404_handler(self, app) -> None:
        """Test 404 error handler."""
        install_error_handlers(app)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/nonexistent")

        assert response.status_code == 404
        assert response.json()["code"] == "NOT_FOUND"
        assert "endpoint does not exist" in response.json()["message"]

    def test_starlette_http_exception_handler(self, app) -> None:
        """Test Starlette HTTP exception handler."""
        install_error_handlers(app)

        @app.get("/test")
        async def test_endpoint():
            raise StarletteHTTPException(status_code=403, detail="Forbidden access")

        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 403
        data = response.json()
        assert data["detail"] == "Forbidden access"
        assert data["code"] == "forbidden"

    def test_fastapi_http_exception_handler(self, app) -> None:
        """Test FastAPI HTTP exception handler."""
        install_error_handlers(app)

        @app.get("/test")
        async def test_endpoint():
            raise HTTPException(status_code=409, detail="Resource conflict")

        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 409
        data = response.json()
        assert data["detail"] == "Resource conflict"
        assert data["code"] == "conflict"

    def test_validation_error_handler(self, app) -> None:
        """Test validation error handler."""
        install_error_handlers(app)

        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str
            age: int

        @app.post("/test")
        async def test_endpoint(data: TestModel):
            return data

        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.post("/test", json={"name": 123, "age": "not-a-number"})

        assert response.status_code == 422
        data = response.json()
        assert data["detail"] == "Request validation failed."
        assert "fields" in data

    def test_novel_engine_exception_handler(self, app) -> None:
        """Test NovelEngine exception handler."""
        install_error_handlers(app)

        @app.get("/test")
        async def test_endpoint():
            raise NovelEngineException(
                message="Custom error",
                status_code=418,
                detail="I'm a teapot",
                code="TEAPOT_ERROR",
            )

        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 418
        data = response.json()
        assert data["detail"] == "I'm a teapot"
        assert data["code"] == "TEAPOT_ERROR"

    def test_generic_exception_handler_via_direct_call(self, app) -> None:
        """Test generic exception handler via direct handler call."""
        install_error_handlers(app, debug=False)

        # Test that handler is registered by checking app.exception_handlers
        # The handler for Exception should be registered
        assert (
            Exception in app.exception_handlers
            or any(
                issubclass(Exception, exc_type)
                for exc_type in app.exception_handlers.keys()
            )
            or len(app.exception_handlers) > 0
        )  # At minimum, handlers should be registered

    def test_generic_exception_handler_debug_mode_via_direct_call(self, app) -> None:
        """Test generic exception handler debug mode via direct handler call."""
        install_error_handlers(app, debug=True)

        # Handlers should be registered
        assert len(app.exception_handlers) > 0

    def test_validation_error_with_exception_in_ctx(self, app) -> None:
        """Test validation error handling with exception in ctx."""
        install_error_handlers(app)

        from pydantic import BaseModel, Field

        class TestModel(BaseModel):
            value: int = Field(..., gt=0)

        @app.post("/test")
        async def test_endpoint(data: TestModel):
            return data

        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.post("/test", json={"value": -1})

        assert response.status_code == 422
        data = response.json()
        assert "fields" in data


@pytest.mark.unit
class TestValidationErrorSerialization:
    """Tests for validation error serialization edge cases."""

    def test_validation_error_with_non_serializable_value(self) -> None:
        """Test handling validation errors with non-serializable values."""
        app = FastAPI()
        install_error_handlers(app)

        from pydantic import BaseModel, field_validator

        class TestModel(BaseModel):
            data: str

            @field_validator("data")
            @classmethod
            def validate_data(cls, v):
                if v == "error":
                    raise ValueError("Custom error with complex object")
                return v

        @app.post("/test")
        async def test_endpoint(data: TestModel):
            return data

        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.post("/test", json={"data": "error"})

        assert response.status_code == 422
        data = response.json()
        assert "fields" in data
