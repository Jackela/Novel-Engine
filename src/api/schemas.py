from typing import Dict, List, Optional

from pydantic import BaseModel, Field, JsonValue, field_validator


# === Orchestration Schemas (aligned with frontend/src/types/schemas.ts) ===


class OrchestrationStep(BaseModel):
    """Step within orchestration progress."""

    id: str
    name: str
    status: str
    progress: float = Field(ge=0, le=100)


class OrchestrationStatusData(BaseModel):
    """Orchestration status data structure."""

    status: str
    current_turn: int = 0
    total_turns: int = 0
    queue_length: int = 0
    average_processing_time: float = 0.0
    steps: List[OrchestrationStep] = Field(default_factory=list)
    last_updated: Optional[str] = None


class OrchestrationStatusResponse(BaseModel):
    """Response for orchestration status endpoint."""

    success: bool
    data: OrchestrationStatusData
    message: Optional[str] = None


class OrchestrationStartRequest(BaseModel):
    """Request to start orchestration."""

    character_names: Optional[List[str]] = Field(None, min_length=2, max_length=6)
    total_turns: Optional[int] = Field(3, ge=1, le=10)
    setting: Optional[str] = None
    scenario: Optional[str] = None


class OrchestrationStartResponse(BaseModel):
    """Response after starting orchestration."""

    success: bool
    status: str
    task_id: Optional[str] = None
    message: Optional[str] = None


class OrchestrationStopResponse(BaseModel):
    """Response after stopping orchestration."""

    success: bool
    message: Optional[str] = None


class NarrativeData(BaseModel):
    """Narrative content data."""

    story: str
    participants: List[str]
    turns_completed: int
    last_generated: Optional[str] = None
    has_content: bool


class NarrativeResponse(BaseModel):
    """Response for narrative endpoint."""

    success: bool
    data: NarrativeData


# === Health/Meta Schemas ===


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


# === Character Schemas ===


class CharacterSummary(BaseModel):
    id: str
    agent_id: str
    name: str
    status: str
    type: str
    updated_at: str
    workspace_id: Optional[str] = None


class CharactersListResponse(BaseModel):
    characters: List[CharacterSummary]


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


class CharacterDetailResponse(BaseModel):
    """Response model for detailed character information."""

    agent_id: str
    character_id: str
    character_name: str
    name: str
    background_summary: str
    personality_traits: str
    current_status: str
    narrative_context: str
    skills: Dict[str, float] = Field(default_factory=dict)
    relationships: Dict[str, float] = Field(default_factory=dict)
    current_location: str = ""
    inventory: List[str] = Field(default_factory=list)
    metadata: Dict[str, JsonValue] = Field(default_factory=dict)
    structured_data: Dict[str, JsonValue] = Field(default_factory=dict)


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


# Authentication Models
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


__all__ = [
    # Orchestration Schemas
    "OrchestrationStep",
    "OrchestrationStatusData",
    "OrchestrationStatusResponse",
    "OrchestrationStartRequest",
    "OrchestrationStartResponse",
    "OrchestrationStopResponse",
    "NarrativeData",
    "NarrativeResponse",
    # Health/Meta Schemas
    "HealthResponse",
    "HealthCheckResponse",
    "SystemStatusResponse",
    "PolicyInfoResponse",
    # Events/Analytics Schemas
    "SSEEventData",
    "SSEStatsResponse",
    "AnalyticsMetricsData",
    "AnalyticsMetricsResponse",
    # Character Schemas
    "CharacterSummary",
    "CharactersListResponse",
    "SimulationRequest",
    "SimulationResponse",
    "CharacterDetailResponse",
    "FileCount",
    "CampaignsListResponse",
    "CampaignCreationRequest",
    "CampaignCreationResponse",
    # Auth Schemas
    "LoginRequest",
    "AuthResponse",
    "LogoutRequest",
    "LogoutResponse",
    "TokenValidationResponse",
    "RefreshTokenRequest",
    "CSRFTokenResponse",
    "InvalidationRequest",
    "ChunkInRequest",
    "GuestSessionResponse",
    "WorkspaceCharacterCreateRequest",
    "WorkspaceCharacterUpdateRequest",
]

try:
    from .character_api import (
        CharacterCreationRequest,
        CharacterListResponse,
        CharacterResponse,
        CharacterUpdateRequest,
    )
    from .context7_integration_api import (
        BestPracticeItem,
        BestPracticeRequest,
        BestPracticesResponse,
        CodeExampleRequest,
        CodeExampleResponse,
        DocumentationRequest,
        DocumentationSection,
        EnhancedDocumentationResponse,
        PatternValidationRequest,
        ValidationIssue,
        PatternValidationResponse,
    )
    from .emergent_narrative_api import (
        CausalGraphData,
        CausalGraphRequest,
        CausalLinkResponse,
        EmergentNarrativeData,
        EmergentNarrativeRequest,
        NarrativeBuildRequest,
        NarrativeEventResponse,
        NegotiationRequest,
        NegotiationResponse,
    )
    from .interaction_api import InteractionRequest, InteractionResponse
    from .knowledge_api import (
        CreateKnowledgeEntryRequest,
        CreateKnowledgeEntryResponse,
        KnowledgeEntryResponse,
        UpdateKnowledgeEntryRequest,
    )
    from .prompts_router import (
        AnalyzeRequest,
        AnalyzeResponse,
        ApplySuggestionRequest,
        ApplySuggestionResponse,
        OptimizeRequest,
        OptimizeResponse,
        TemplateDetailResponse,
        TemplateInfo,
        TemplatesListResponse,
        UserPromptCreate,
        UserPromptResponse,
        UserPromptsListResponse,
        UserPromptUpdate,
    )
    from .secure_main_api import (
        ApiKeyResponse,
        CharacterCreateRequest,
        CharacterRecord,
        SecureSimulationRequest,
        SecureSimulationResponse,
        SystemHealthResponse,
        UserLoginRequest,
        UserRegistrationRequest,
    )
    from .story_generation_api import (
        ProgressUpdate,
        StoryGenerationRequest,
        StoryGenerationResponse,
    )
    from .subjective_reality_api import (
        BeliefModelData,
        BeliefModelRequest,
        BeliefUpdateRequest,
        InformationFragmentResponse,
        MultiBriefData,
        MultiBriefRequest,
        TurnBriefData,
        TurnBriefGenerationRequest,
        TurnBriefRequest,
    )

    __all__ += [
        "CharacterCreationRequest",
        "CharacterUpdateRequest",
        "CharacterResponse",
        "CharacterListResponse",
        "StoryGenerationRequest",
        "StoryGenerationResponse",
        "ProgressUpdate",
        "InteractionRequest",
        "InteractionResponse",
        "EmergentNarrativeRequest",
        "CausalLinkResponse",
        "NarrativeEventResponse",
        "EmergentNarrativeData",
        "NarrativeBuildRequest",
        "CausalGraphRequest",
        "CausalGraphData",
        "NegotiationRequest",
        "NegotiationResponse",
        "TurnBriefRequest",
        "InformationFragmentResponse",
        "TurnBriefData",
        "MultiBriefRequest",
        "MultiBriefData",
        "TurnBriefGenerationRequest",
        "BeliefModelRequest",
        "BeliefModelData",
        "BeliefUpdateRequest",
        "CreateKnowledgeEntryRequest",
        "CreateKnowledgeEntryResponse",
        "UpdateKnowledgeEntryRequest",
        "KnowledgeEntryResponse",
        "CodeExampleRequest",
        "CodeExampleResponse",
        "PatternValidationRequest",
        "ValidationIssue",
        "PatternValidationResponse",
        "DocumentationRequest",
        "DocumentationSection",
        "EnhancedDocumentationResponse",
        "BestPracticeRequest",
        "BestPracticeItem",
        "BestPracticesResponse",
        "TemplateInfo",
        "TemplateDetailResponse",
        "TemplatesListResponse",
        "AnalyzeRequest",
        "AnalyzeResponse",
        "OptimizeRequest",
        "OptimizeResponse",
        "ApplySuggestionRequest",
        "ApplySuggestionResponse",
        "UserPromptCreate",
        "UserPromptUpdate",
        "UserPromptResponse",
        "UserPromptsListResponse",
        "UserLoginRequest",
        "UserRegistrationRequest",
        "ApiKeyResponse",
        "SystemHealthResponse",
        "SecureSimulationRequest",
        "SecureSimulationResponse",
        "CharacterCreateRequest",
        "CharacterRecord",
    ]
except ImportError:
    pass
