#!/usr/bin/env python3
"""
Standardized API response envelopes used by the main API server and error handlers.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ResponseStatus(str, Enum):
    """Standard response status enumeration."""

    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    PENDING = "pending"


class APIErrorType(str, Enum):
    """API error type classification."""

    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    CONFLICT = "conflict"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"
    BAD_REQUEST = "bad_request"


class APIError(BaseModel):
    """Standardized error information."""

    type: APIErrorType = Field(..., description="Error type classification")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    code: Optional[str] = Field(None, description="Internal error code")
    field: Optional[str] = Field(None, description="Field that caused validation error")


class ValidationError(BaseModel):
    """Validation error details."""

    field: str = Field(..., description="Field name that failed validation")
    message: str = Field(..., description="Validation error message")
    value: Optional[Any] = Field(None, description="Invalid value provided")


class APIMetadata(BaseModel):
    """Response metadata information."""

    timestamp: datetime = Field(
        default_factory=datetime.now, description="Response timestamp"
    )
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    api_version: str = Field("1.0.0", description="API version")
    server_time: float = Field(..., description="Server processing time in seconds")
    rate_limit_remaining: Optional[int] = Field(
        None, description="Remaining rate limit"
    )
    rate_limit_reset: Optional[datetime] = Field(
        None, description="Rate limit reset time"
    )


class APIResponse(BaseModel, Generic[T]):
    """Base standardized API response format."""

    status: ResponseStatus = Field(..., description="Response status")
    data: Optional[T] = Field(None, description="Response data payload")
    error: Optional[APIError] = Field(
        None, description="Error information if status is error"
    )
    errors: Optional[List[Union[APIError, ValidationError]]] = Field(
        None, description="Multiple errors for validation"
    )
    metadata: APIMetadata = Field(..., description="Response metadata")

    model_config = ConfigDict(json_encoders={datetime: lambda dt: dt.isoformat()})


class SuccessResponse(APIResponse[T]):
    """Successful API response."""

    status: ResponseStatus = ResponseStatus.SUCCESS


class ErrorResponse(APIResponse[None]):
    """Error API response."""

    status: ResponseStatus = ResponseStatus.ERROR


class HealthCheckData(BaseModel):
    """Health check response data."""

    service_status: str = Field(..., description="Overall service status")
    database_status: str = Field(..., description="Database connection status")
    orchestrator_status: str = Field(..., description="System orchestrator status")
    active_agents: int = Field(..., ge=0, description="Number of active agents")
    uptime_seconds: float = Field(..., ge=0, description="Service uptime in seconds")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Environment (development/production)")


class HealthCheckResponse(SuccessResponse[HealthCheckData]):
    """Typed response for health checks."""


__all__ = [
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
