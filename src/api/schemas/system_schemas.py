"""System API schemas for the Novel Engine.

This module contains schemas for system-level functionality including:
- Health/Meta schemas (error handling, health checks)
- Events/Analytics schemas (SSE, metrics)
- Campaign schemas (story campaigns)
- Authentication schemas (login, tokens)
- Workspace schemas (character workspace management)

Created as part of PREP-002 (Operation Vanguard).
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, JsonValue, field_validator


# === Health/Meta Schemas ===


class ErrorDetail(BaseModel):
    """Standard error response schema.

    Used for consistent error reporting across all API endpoints.
    Example: {"code": "NOT_FOUND", "message": "Resource not found"}
    """

    code: str = Field(..., description="Error code identifying the type of error")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error context and metadata"
    )


class ValidationError(ErrorDetail):
    """Validation error response with field-level error details.

    Extends ErrorDetail with structured field-level validation errors.
    Example:
        {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "field_errors": {
                "email": ["Invalid email format"],
                "age": ["Must be a positive integer"]
            }
        }
    """

    field_errors: Optional[Dict[str, List[str]]] = Field(
        None, description="Mapping of field names to their validation error messages"
    )


class HealthResponse(BaseModel):
    message: str
    status: Optional[str] = None
    timestamp: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Detailed health check response."""

    status: str
    api: str
    timestamp: str
    version: str
    config: str
    uptime: float


class SystemStatusResponse(BaseModel):
    """System status response."""

    status: str
    uptime: float
    version: str
    components: Dict[str, str]


class PolicyInfoResponse(BaseModel):
    """Policy information response."""

    brand_status: str
    compliance: Dict[str, str]
    last_reviewed: str


# === Events/Analytics Schemas ===


class SSEEventData(BaseModel):
    """SSE event data structure."""

    id: str
    type: str
    title: str
    description: str
    timestamp: int
    severity: str
    characterName: Optional[str] = None


class SSEStatsResponse(BaseModel):
    """SSE connection statistics."""

    connected_clients: int
    total_events_sent: int
    active_queues: int


class AnalyticsMetricsData(BaseModel):
    """Analytics metrics data."""

    story_quality: float
    engagement: float
    coherence: float
    complexity: float
    data_points: int
    metrics_tracked: int
    status: str
    last_updated: str


class AnalyticsMetricsResponse(BaseModel):
    """Analytics metrics response."""

    success: bool
    data: AnalyticsMetricsData


# === Simulation Schemas (CHAR-029) ===


class SimulationRequest(BaseModel):
    character_names: List[str] = Field(..., min_length=2, max_length=6)
    turns: Optional[int] = Field(None, ge=1, le=10)
    setting: Optional[str] = None
    scenario: Optional[str] = None


class SimulationResponse(BaseModel):
    story: str
    participants: List[str]
    turns_executed: int
    duration_seconds: float


# === Campaign Schemas ===


class FileCount(BaseModel):
    """Response model for file count information."""

    count: int
    file_type: str


class CampaignsListResponse(BaseModel):
    """Response model for campaigns list."""

    campaigns: List[str]


class CampaignCreationRequest(BaseModel):
    """Request model for campaign creation."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    participants: List[str] = Field(..., min_length=1)


class CampaignCreationResponse(BaseModel):
    """Response model for campaign creation."""

    campaign_id: str
    name: str
    status: str
    created_at: str


class CampaignDetailResponse(BaseModel):
    """Response model for campaign detail."""

    id: str
    name: str
    description: str
    status: str
    created_at: str
    updated_at: str
    current_turn: int = 0


# === Authentication Schemas ===


class LoginRequest(BaseModel):
    """Request model for user login."""

    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(
        default=False, description="Whether to extend session duration"
    )


class AuthResponse(BaseModel):
    """Response model for authentication endpoints."""

    access_token: str = Field(
        ..., description="JWT access token (for backward compatibility)"
    )
    refresh_token: str = Field(
        ..., description="JWT refresh token (for backward compatibility)"
    )
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry time in seconds")
    user: Dict[str, JsonValue] = Field(..., description="User information")


class LogoutRequest(BaseModel):
    access_token: Optional[str] = Field(
        None, description="Optional access token to invalidate"
    )


class LogoutResponse(BaseModel):
    success: bool
    message: str


class TokenValidationResponse(BaseModel):
    valid: bool
    expires_at: Optional[int] = Field(
        None, description="Token expiry timestamp in milliseconds"
    )
    user_id: Optional[str] = None
    error: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""

    refresh_token: str = Field(..., description="Refresh token")


class CSRFTokenResponse(BaseModel):
    """Response model for CSRF token endpoint."""

    csrf_token: str = Field(..., description="CSRF token for state-changing requests")


class InvalidationRequest(BaseModel):
    all_of: List[str]


class ChunkInRequest(BaseModel):
    seq: int
    data: str


class GuestSessionResponse(BaseModel):
    workspace_id: str
    created: bool


# === Workspace Schemas ===


class WorkspaceCharacterCreateRequest(BaseModel):
    agent_id: str = Field(
        ...,
        description="Stable identifier for the character.",
    )
    name: str = Field(..., min_length=2, max_length=100)
    background_summary: str = Field("", max_length=1000)
    personality_traits: str = Field("", max_length=500)
    skills: Dict[str, float] = Field(default_factory=dict)
    relationships: Dict[str, float] = Field(default_factory=dict)
    current_location: Optional[str] = Field(default=None, max_length=200)
    inventory: List[str] = Field(default_factory=list)
    metadata: Dict[str, JsonValue] = Field(default_factory=dict)
    structured_data: Dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("agent_id is required")
        cleaned = value.strip()
        if not cleaned.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Agent ID must be alphanumeric with hyphens or underscores."
            )
        return cleaned.lower()

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, values: Dict[str, float]) -> Dict[str, float]:
        for skill, value in (values or {}).items():
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"Skill {skill} must be between 0.0 and 1.0.")
        return values


class WorkspaceCharacterUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    background_summary: Optional[str] = Field(default=None, max_length=1000)
    personality_traits: Optional[str] = Field(default=None, max_length=500)
    skills: Optional[Dict[str, float]] = None
    relationships: Optional[Dict[str, float]] = None
    current_location: Optional[str] = Field(default=None, max_length=200)
    inventory: Optional[List[str]] = None
    metadata: Optional[Dict[str, JsonValue]] = None
    structured_data: Optional[Dict[str, JsonValue]] = None
