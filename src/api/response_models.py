#!/usr/bin/env python3
"""
Standardized API Response Models.

This module provides consistent response formats across all API endpoints,
following REST API best practices and ensuring reliable client integration.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, ConfigDict, Field

# Generic type for data payload
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


class PaginationInfo(BaseModel):
    """Pagination information for list responses."""

    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total_items: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=1, description="Total number of pages")
    has_next: bool = Field(..., description="Whether next page exists")
    has_previous: bool = Field(..., description="Whether previous page exists")


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
    pagination: Optional[PaginationInfo] = Field(
        None, description="Pagination info for list responses"
    )

    model_config = ConfigDict(json_encoders={datetime: lambda dt: dt.isoformat()})


class SuccessResponse(APIResponse[T]):
    """Successful API response."""

    status: ResponseStatus = ResponseStatus.SUCCESS


class ErrorResponse(APIResponse[None]):
    """Error API response."""

    status: ResponseStatus = ResponseStatus.ERROR
    data: None = None


class ListResponse(APIResponse[List[T]]):
    """List API response with pagination."""

    data: List[T] = Field(..., description="List of items")
    pagination: PaginationInfo = Field(..., description="Pagination information")


# Common response types for the Novel Engine API


class HealthCheckData(BaseModel):
    """Health check response data."""

    service_status: str = Field(..., description="Overall service status")
    database_status: str = Field(..., description="Database connection status")
    orchestrator_status: str = Field(..., description="System orchestrator status")
    active_agents: int = Field(..., ge=0, description="Number of active agents")
    uptime_seconds: float = Field(..., ge=0, description="Service uptime in seconds")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Environment (development/production)")


class CharacterSummary(BaseModel):
    """Character summary for list responses."""

    agent_id: str = Field(..., description="Unique character identifier")
    name: str = Field(..., description="Character display name")
    status: str = Field(..., description="Current character status")
    created_at: datetime = Field(..., description="Character creation timestamp")
    last_activity: datetime = Field(..., description="Last activity timestamp")


class CharacterDetail(CharacterSummary):
    """Detailed character information."""

    background_summary: str = Field("", description="Character background")
    personality_traits: str = Field("", description="Character personality")
    skills: Dict[str, float] = Field(
        default_factory=dict, description="Character skills"
    )
    relationships: Dict[str, float] = Field(
        default_factory=dict, description="Character relationships"
    )
    current_location: str = Field("", description="Current character location")
    inventory: List[str] = Field(
        default_factory=list, description="Character inventory"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class StoryGenerationSummary(BaseModel):
    """Story generation summary."""

    generation_id: str = Field(..., description="Unique generation identifier")
    status: str = Field(..., description="Generation status")
    progress: float = Field(
        ..., ge=0, le=100, description="Generation progress percentage"
    )
    characters: List[str] = Field(..., description="Participating characters")
    created_at: datetime = Field(..., description="Generation start timestamp")
    estimated_completion: Optional[datetime] = Field(
        None, description="Estimated completion time"
    )


class InteractionSummary(BaseModel):
    """Interaction summary."""

    interaction_id: str = Field(..., description="Unique interaction identifier")
    participants: List[str] = Field(..., description="Interaction participants")
    interaction_type: str = Field(..., description="Type of interaction")
    status: str = Field(..., description="Interaction status")
    created_at: datetime = Field(..., description="Interaction creation timestamp")
    topic: Optional[str] = Field(None, description="Interaction topic")


# Common response type aliases
HealthCheckResponse = SuccessResponse[HealthCheckData]
CharacterListResponse = ListResponse[CharacterSummary]
CharacterResponse = SuccessResponse[CharacterDetail]
StoryGenerationResponse = SuccessResponse[StoryGenerationSummary]
InteractionListResponse = ListResponse[InteractionSummary]

__all__ = [
    "ResponseStatus",
    "APIErrorType",
    "APIError",
    "ValidationError",
    "APIMetadata",
    "PaginationInfo",
    "APIResponse",
    "SuccessResponse",
    "ErrorResponse",
    "ListResponse",
    "HealthCheckData",
    "CharacterSummary",
    "CharacterDetail",
    "StoryGenerationSummary",
    "InteractionSummary",
    "HealthCheckResponse",
    "CharacterListResponse",
    "CharacterResponse",
    "StoryGenerationResponse",
    "InteractionListResponse",
]
