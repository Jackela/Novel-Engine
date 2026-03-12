"""Unit tests for response envelope models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from src.api.response_envelopes import (
    APIError,
    APIErrorType,
    APIMetadata,
    APIResponse,
    ErrorResponse,
    HealthCheckData,
    HealthCheckResponse,
    ResponseStatus,
    SuccessResponse,
)
from src.api.response_envelopes import (
    ValidationError as APIValidationError,
)


@pytest.mark.unit
class TestResponseStatus:
    """Tests for ResponseStatus enum."""

    def test_response_status_values(self) -> None:
        """Test ResponseStatus enum values."""
        assert ResponseStatus.SUCCESS == "success"
        assert ResponseStatus.ERROR == "error"
        assert ResponseStatus.PARTIAL == "partial"
        assert ResponseStatus.PENDING == "pending"

    def test_response_status_str_type(self) -> None:
        """Test ResponseStatus is a string enum."""
        assert isinstance(ResponseStatus.SUCCESS, str)


@pytest.mark.unit
class TestAPIErrorType:
    """Tests for APIErrorType enum."""

    def test_error_type_values(self) -> None:
        """Test all APIErrorType enum values."""
        assert APIErrorType.VALIDATION_ERROR == "validation_error"
        assert APIErrorType.NOT_FOUND == "not_found"
        assert APIErrorType.UNAUTHORIZED == "unauthorized"
        assert APIErrorType.FORBIDDEN == "forbidden"
        assert APIErrorType.CONFLICT == "conflict"
        assert APIErrorType.RATE_LIMITED == "rate_limited"
        assert APIErrorType.INTERNAL_ERROR == "internal_error"
        assert APIErrorType.SERVICE_UNAVAILABLE == "service_unavailable"
        assert APIErrorType.TIMEOUT == "timeout"
        assert APIErrorType.BAD_REQUEST == "bad_request"


@pytest.mark.unit
class TestAPIError:
    """Tests for APIError model."""

    def test_api_error_creation(self) -> None:
        """Test creating APIError instance."""
        error = APIError(
            type=APIErrorType.NOT_FOUND,
            message="Resource not found",
            detail="The requested resource does not exist",
            code="RESOURCE_NOT_FOUND",
            field="user_id",
        )

        assert error.type == APIErrorType.NOT_FOUND
        assert error.message == "Resource not found"
        assert error.detail == "The requested resource does not exist"
        assert error.code == "RESOURCE_NOT_FOUND"
        assert error.field == "user_id"

    def test_api_error_minimal(self) -> None:
        """Test creating APIError with minimal fields."""
        error = APIError(
            type=APIErrorType.INTERNAL_ERROR,
            message="Something went wrong",
        )

        assert error.type == APIErrorType.INTERNAL_ERROR
        assert error.message == "Something went wrong"
        assert error.detail is None
        assert error.code is None
        assert error.field is None

    def test_api_error_serialization(self) -> None:
        """Test APIError JSON serialization."""
        error = APIError(
            type=APIErrorType.VALIDATION_ERROR,
            message="Invalid input",
            field="email",
        )

        data = error.model_dump()
        assert data["type"] == "validation_error"
        assert data["message"] == "Invalid input"
        assert data["field"] == "email"


@pytest.mark.unit
class TestValidationError:
    """Tests for ValidationError model."""

    def test_validation_error_creation(self) -> None:
        """Test creating ValidationError instance."""
        error = APIValidationError(
            field="email",
            message="Must be a valid email address",
            value="invalid-email",
        )

        assert error.field == "email"
        assert error.message == "Must be a valid email address"
        assert error.value == "invalid-email"

    def test_validation_error_without_value(self) -> None:
        """Test creating ValidationError without value field."""
        error = APIValidationError(
            field="password",
            message="Password is required",
        )

        assert error.field == "password"
        assert error.message == "Password is required"
        assert error.value is None


@pytest.mark.unit
class TestAPIMetadata:
    """Tests for APIMetadata model."""

    def test_api_metadata_creation(self) -> None:
        """Test creating APIMetadata instance."""
        now = datetime.now()
        metadata = APIMetadata(
            timestamp=now,
            request_id="req-123",
            api_version="2.0.0",
            server_time=0.125,
            rate_limit_remaining=99,
        )

        assert metadata.timestamp == now
        assert metadata.request_id == "req-123"
        assert metadata.api_version == "2.0.0"
        assert metadata.server_time == 0.125
        assert metadata.rate_limit_remaining == 99

    def test_api_metadata_defaults(self) -> None:
        """Test APIMetadata default values."""
        metadata = APIMetadata(server_time=0.1)

        assert isinstance(metadata.timestamp, datetime)
        assert metadata.api_version == "1.0.0"
        assert metadata.request_id is None
        assert metadata.rate_limit_remaining is None
        assert metadata.rate_limit_reset is None

    def test_api_metadata_timestamp_auto(self) -> None:
        """Test timestamp is auto-generated."""
        before = datetime.now()
        metadata = APIMetadata(server_time=0.1)
        after = datetime.now()

        assert before <= metadata.timestamp <= after


@pytest.mark.unit
class TestAPIResponse:
    """Tests for APIResponse model."""

    def test_api_response_creation(self) -> None:
        """Test creating APIResponse instance."""
        metadata = APIMetadata(server_time=0.1)
        response = APIResponse[dict[str, Any]](
            status=ResponseStatus.SUCCESS,
            data={"id": "123", "name": "Test"},
            metadata=metadata,
        )

        assert response.status == ResponseStatus.SUCCESS
        assert response.data == {"id": "123", "name": "Test"}
        assert response.error is None
        assert response.metadata == metadata

    def test_api_response_error(self) -> None:
        """Test APIResponse with error."""
        metadata = APIMetadata(server_time=0.1)
        error = APIError(
            type=APIErrorType.NOT_FOUND,
            message="Not found",
        )

        response = APIResponse[None](
            status=ResponseStatus.ERROR,
            error=error,
            metadata=metadata,
        )

        assert response.status == ResponseStatus.ERROR
        assert response.error == error
        assert response.data is None

    def test_api_response_json_serialization(self) -> None:
        """Test APIResponse JSON serialization with datetime."""
        metadata = APIMetadata(server_time=0.1)
        response = APIResponse[dict[str, Any]](
            status=ResponseStatus.SUCCESS,
            data={"items": [1, 2, 3]},
            metadata=metadata,
        )

        json_data = response.model_dump(mode="json")
        assert json_data["status"] == "success"
        assert json_data["data"] == {"items": [1, 2, 3]}
        assert "timestamp" in json_data["metadata"]


@pytest.mark.unit
class TestSuccessResponse:
    """Tests for SuccessResponse model."""

    def test_success_response_default_status(self) -> None:
        """Test SuccessResponse has default SUCCESS status."""
        metadata = APIMetadata(server_time=0.1)
        response = SuccessResponse[dict[str, Any]](
            data={"result": "ok"},
            metadata=metadata,
        )

        assert response.status == ResponseStatus.SUCCESS

    def test_success_response_override_status(self) -> None:
        """Test SuccessResponse status can be explicitly set."""
        metadata = APIMetadata(server_time=0.1)
        response = SuccessResponse[dict[str, Any]](
            status=ResponseStatus.PARTIAL,
            data={"result": "partial"},
            metadata=metadata,
        )

        assert response.status == ResponseStatus.PARTIAL


@pytest.mark.unit
class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_error_response_default_status(self) -> None:
        """Test ErrorResponse has default ERROR status."""
        metadata = APIMetadata(server_time=0.1)
        error = APIError(
            type=APIErrorType.INTERNAL_ERROR,
            message="Error occurred",
        )

        response = ErrorResponse(
            error=error,
            metadata=metadata,
        )

        assert response.status == ResponseStatus.ERROR


@pytest.mark.unit
class TestHealthCheckData:
    """Tests for HealthCheckData model."""

    def test_health_check_data_creation(self) -> None:
        """Test creating HealthCheckData instance."""
        data = HealthCheckData(
            service_status="healthy",
            database_status="connected",
            orchestrator_status="running",
            active_agents=5,
            uptime_seconds=3600.5,
            version="1.0.0",
            environment="production",
        )

        assert data.service_status == "healthy"
        assert data.database_status == "connected"
        assert data.orchestrator_status == "running"
        assert data.active_agents == 5
        assert data.uptime_seconds == 3600.5
        assert data.version == "1.0.0"
        assert data.environment == "production"

    def test_health_check_data_validation(self) -> None:
        """Test HealthCheckData validation constraints."""
        # Test negative active_agents (ge=0 constraint)
        with pytest.raises(ValidationError):
            HealthCheckData(
                service_status="healthy",
                database_status="connected",
                orchestrator_status="running",
                active_agents=-1,  # Invalid: must be >= 0
                uptime_seconds=3600,
                version="1.0.0",
                environment="test",
            )

        # Test negative uptime (ge=0 constraint)
        with pytest.raises(ValidationError):
            HealthCheckData(
                service_status="healthy",
                database_status="connected",
                orchestrator_status="running",
                active_agents=0,
                uptime_seconds=-1,  # Invalid: must be >= 0
                version="1.0.0",
                environment="test",
            )


@pytest.mark.unit
class TestHealthCheckResponse:
    """Tests for HealthCheckResponse model."""

    def test_health_check_response_creation(self) -> None:
        """Test creating HealthCheckResponse instance."""
        health_data = HealthCheckData(
            service_status="healthy",
            database_status="connected",
            orchestrator_status="running",
            active_agents=3,
            uptime_seconds=1800.0,
            version="1.0.0",
            environment="development",
        )

        metadata = APIMetadata(server_time=0.05)
        response = HealthCheckResponse(
            data=health_data,
            metadata=metadata,
        )

        assert response.status == ResponseStatus.SUCCESS
        assert response.data.service_status == "healthy"
        assert response.data.active_agents == 3

    def test_health_check_response_serialization(self) -> None:
        """Test HealthCheckResponse JSON serialization."""
        health_data = HealthCheckData(
            service_status="healthy",
            database_status="connected",
            orchestrator_status="running",
            active_agents=0,
            uptime_seconds=0.0,
            version="1.0.0",
            environment="test",
        )

        metadata = APIMetadata(server_time=0.01)
        response = HealthCheckResponse(
            data=health_data,
            metadata=metadata,
        )

        json_data = response.model_dump(mode="json")
        assert json_data["status"] == "success"
        assert json_data["data"]["service_status"] == "healthy"
        assert json_data["data"]["active_agents"] == 0


@pytest.mark.unit
class TestAllExports:
    """Tests for __all__ exports."""

    def test_all_exports_present(self) -> None:
        """Test that __all__ includes all expected exports."""
        from src.api.response_envelopes import __all__

        expected = [
            "ResponseStatus",
            "APIErrorType",
            "APIError",
            "ValidationError",
            "APIMetadata",
            "APIResponse",
            "SuccessResponse",
            "ErrorResponse",
            "HealthCheckData",
            "HealthCheckResponse",
        ]

        for item in expected:
            assert item in __all__, f"{item} should be in __all__"
