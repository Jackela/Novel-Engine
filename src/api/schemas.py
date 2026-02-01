from typing import Dict, List, Optional

from pydantic import BaseModel, Field, JsonValue, field_validator


# === Orchestration Schemas (aligned with frontend/src/types/schemas.ts) ===


class OrchestrationStep(BaseModel):
    """Step within orchestration progress."""

    id: str = Field(..., description="Unique identifier for this step")
    name: str = Field(..., description="Human-readable name of the step")
    status: str = Field(..., description="Current status: pending, running, completed, failed")
    progress: float = Field(ge=0, le=100, description="Completion percentage (0-100)")


class OrchestrationStatusData(BaseModel):
    """Orchestration status data structure."""

    status: str = Field(..., description="Overall orchestration status: idle, running, paused, completed")
    current_turn: int = Field(0, description="Current turn number being processed")
    total_turns: int = Field(0, description="Total number of turns to process")
    queue_length: int = Field(0, description="Number of pending operations in the queue")
    average_processing_time: float = Field(0.0, description="Average time per turn in seconds")
    steps: List[OrchestrationStep] = Field(default_factory=list, description="Detailed step breakdown")
    last_updated: Optional[str] = Field(None, description="ISO 8601 timestamp of last status update")


class OrchestrationStatusResponse(BaseModel):
    """Response for orchestration status endpoint."""

    success: bool
    data: OrchestrationStatusData
    message: Optional[str] = None


class OrchestrationStartRequest(BaseModel):
    """Request to start orchestration."""

    character_names: Optional[List[str]] = Field(
        None,
        min_length=2,
        max_length=6,
        description="List of character names to include (2-6 characters)"
    )
    total_turns: Optional[int] = Field(
        3,
        ge=1,
        le=10,
        description="Number of narrative turns to generate (1-10)"
    )
    setting: Optional[str] = Field(None, description="World setting name or ID")
    scenario: Optional[str] = Field(None, description="Initial scenario description")


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
    # New fields for WORLD-001: Enhanced character profiles
    aliases: List[str] = Field(default_factory=list)
    archetype: Optional[str] = None
    traits: List[str] = Field(default_factory=list)
    appearance: Optional[str] = None


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


class CharacterGenerationRequest(BaseModel):
    """Request model for character generation."""

    concept: str
    archetype: str
    tone: Optional[str] = None


class CharacterGenerationResponse(BaseModel):
    """Response model for character generation."""

    name: str
    tagline: str
    bio: str
    visual_prompt: str
    traits: List[str]


class SceneGenerationRequest(BaseModel):
    """Request model for scene generation."""

    character_context: CharacterGenerationResponse
    scene_type: str  # 'opening', 'action', 'dialogue', 'climax', 'resolution'
    tone: Optional[str] = None


class SceneGenerationResponse(BaseModel):
    """Response model for scene generation."""

    title: str
    content: str  # Markdown story text
    summary: str  # Short text for node display
    visual_prompt: str


# === Narrative Streaming Schemas ===


class WorldContextEntity(BaseModel):
    """Entity within the world context."""

    id: str
    name: str
    type: str  # 'character', 'location', 'item', 'event'
    description: str = ""
    attributes: Dict[str, str] = Field(default_factory=dict)


class WorldContext(BaseModel):
    """World context for narrative generation."""

    characters: List[WorldContextEntity] = Field(default_factory=list)
    locations: List[WorldContextEntity] = Field(default_factory=list)
    entities: List[WorldContextEntity] = Field(default_factory=list)
    current_scene: Optional[str] = None
    narrative_style: Optional[str] = None


class NarrativeStreamRequest(BaseModel):
    """Request model for streaming narrative generation."""

    prompt: str = Field(..., min_length=1, max_length=5000)
    world_context: WorldContext
    chapter_title: Optional[str] = None
    tone: Optional[str] = None
    max_tokens: int = Field(default=2000, ge=100, le=8000)


class NarrativeStreamChunk(BaseModel):
    """A single chunk from the narrative stream."""

    type: str  # 'chunk', 'done', 'error'
    content: str
    sequence: int = 0


class NarrativeStreamMetadata(BaseModel):
    """Metadata about a completed narrative stream."""

    total_chunks: int
    total_characters: int
    generation_time_ms: int
    model_used: str = "deterministic-fallback"


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


# === Narrative Structure Schemas (Story Outline CRUD) ===


class StoryCreateRequest(BaseModel):
    """Request model for creating a new story."""

    title: str = Field(..., min_length=1, max_length=200, description="Story title")
    summary: str = Field(default="", max_length=2000, description="Story synopsis")


class StoryUpdateRequest(BaseModel):
    """Request model for updating a story."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    summary: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[str] = Field(
        default=None, description="Story status: 'draft' or 'published'"
    )


class StoryResponse(BaseModel):
    """Response model for a single story."""

    id: str = Field(..., description="Story UUID")
    title: str = Field(..., description="Story title")
    summary: str = Field(default="", description="Story synopsis")
    status: str = Field(..., description="Publication status")
    chapter_count: int = Field(default=0, description="Number of chapters")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class StoryListResponse(BaseModel):
    """Response model for listing stories."""

    stories: List["StoryResponse"] = Field(default_factory=list)


class ChapterCreateRequest(BaseModel):
    """Request model for creating a new chapter."""

    title: str = Field(..., min_length=1, max_length=200, description="Chapter title")
    summary: str = Field(default="", max_length=2000, description="Chapter synopsis")
    order_index: Optional[int] = Field(
        default=None, ge=0, description="Position in story (0-based)"
    )


class ChapterUpdateRequest(BaseModel):
    """Request model for updating a chapter."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    summary: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[str] = Field(
        default=None, description="Chapter status: 'draft' or 'published'"
    )


class ChapterResponse(BaseModel):
    """Response model for a single chapter."""

    id: str = Field(..., description="Chapter UUID")
    story_id: str = Field(..., description="Parent story UUID")
    title: str = Field(..., description="Chapter title")
    summary: str = Field(default="", description="Chapter synopsis")
    order_index: int = Field(..., description="Position in story")
    status: str = Field(..., description="Publication status")
    scene_count: int = Field(default=0, description="Number of scenes")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class ChapterListResponse(BaseModel):
    """Response model for listing chapters."""

    story_id: str = Field(..., description="Parent story UUID")
    chapters: List["ChapterResponse"] = Field(default_factory=list)


class SceneCreateRequest(BaseModel):
    """Request model for creating a new scene."""

    title: str = Field(..., min_length=1, max_length=200, description="Scene title")
    summary: str = Field(default="", max_length=2000, description="Scene synopsis")
    location: str = Field(default="", max_length=500, description="Scene setting")
    order_index: Optional[int] = Field(
        default=None, ge=0, description="Position in chapter (0-based)"
    )


class SceneUpdateRequest(BaseModel):
    """Request model for updating a scene."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    summary: Optional[str] = Field(default=None, max_length=2000)
    location: Optional[str] = Field(default=None, max_length=500)
    status: Optional[str] = Field(
        default=None,
        description="Scene status: 'draft', 'generating', 'review', 'published'",
    )


class SceneResponse(BaseModel):
    """Response model for a single scene."""

    id: str = Field(..., description="Scene UUID")
    chapter_id: str = Field(..., description="Parent chapter UUID")
    title: str = Field(..., description="Scene title")
    summary: str = Field(default="", description="Scene synopsis")
    location: str = Field(default="", description="Scene setting")
    order_index: int = Field(..., description="Position in chapter")
    status: str = Field(..., description="Workflow status")
    beat_count: int = Field(default=0, description="Number of beats")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class SceneListResponse(BaseModel):
    """Response model for listing scenes."""

    chapter_id: str = Field(..., description="Parent chapter UUID")
    scenes: List["SceneResponse"] = Field(default_factory=list)


class MoveChapterRequest(BaseModel):
    """Request model for moving a chapter to a new position."""

    new_order_index: int = Field(..., ge=0, description="New position in story")


class MoveSceneRequest(BaseModel):
    """Request model for moving a scene."""

    target_chapter_id: Optional[str] = Field(
        default=None, description="Target chapter UUID (for cross-chapter moves)"
    )
    new_order_index: int = Field(..., ge=0, description="New position in chapter")


class StructureErrorResponse(BaseModel):
    """Standard error response for structure operations."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(default=None, description="Additional details")


# === Relationship Schemas (WORLD-003) ===


class RelationshipCreateRequest(BaseModel):
    """Request model for creating a relationship."""

    source_id: str = Field(..., description="ID of the source entity")
    source_type: str = Field(
        ..., description="Type of source: CHARACTER, FACTION, LOCATION, ITEM, EVENT"
    )
    target_id: str = Field(..., description="ID of the target entity")
    target_type: str = Field(
        ..., description="Type of target: CHARACTER, FACTION, LOCATION, ITEM, EVENT"
    )
    relationship_type: str = Field(
        ...,
        description="Relationship type: FAMILY, ENEMY, ALLY, MENTOR, ROMANTIC, RIVAL, "
        "MEMBER_OF, LOCATED_IN, OWNS, CREATED, HISTORICAL, NEUTRAL",
    )
    description: str = Field(default="", max_length=1000)
    strength: int = Field(default=50, ge=0, le=100, description="Relationship strength")


class RelationshipUpdateRequest(BaseModel):
    """Request model for updating a relationship."""

    relationship_type: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None, max_length=1000)
    strength: Optional[int] = Field(default=None, ge=0, le=100)
    is_active: Optional[bool] = Field(default=None)


class RelationshipResponse(BaseModel):
    """Response model for a single relationship."""

    id: str = Field(..., description="Relationship UUID")
    source_id: str
    source_type: str
    target_id: str
    target_type: str
    relationship_type: str
    description: str
    strength: int
    is_active: bool
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class RelationshipListResponse(BaseModel):
    """Response model for listing relationships."""

    relationships: List[RelationshipResponse] = Field(default_factory=list)
    total: int = Field(default=0, description="Total count of matching relationships")


# === Item Schemas (WORLD-008) ===


class ItemCreateRequest(BaseModel):
    """Request model for creating an item."""

    name: str = Field(..., min_length=1, max_length=200, description="Item name")
    item_type: str = Field(
        ..., description="Type: WEAPON, ARMOR, CONSUMABLE, KEY_ITEM, MISC"
    )
    description: str = Field(default="", max_length=2000)
    rarity: str = Field(
        default="common", description="Rarity: COMMON, UNCOMMON, RARE, LEGENDARY"
    )
    weight: Optional[float] = Field(default=None, ge=0, description="Weight in kg")
    value: Optional[int] = Field(default=None, ge=0, description="Monetary value")
    is_equippable: bool = Field(default=False)
    is_consumable: bool = Field(default=False)
    effects: List[str] = Field(default_factory=list, description="List of effect descriptions")
    lore: str = Field(default="", max_length=5000, description="Extended backstory")


class ItemUpdateRequest(BaseModel):
    """Request model for updating an item."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    rarity: Optional[str] = Field(default=None)
    weight: Optional[float] = Field(default=None, ge=0)
    value: Optional[int] = Field(default=None, ge=0)
    effects: Optional[List[str]] = Field(default=None)
    lore: Optional[str] = Field(default=None, max_length=5000)


class ItemResponse(BaseModel):
    """Response model for a single item."""

    id: str = Field(..., description="Item UUID")
    name: str
    item_type: str
    description: str
    rarity: str
    weight: Optional[float] = None
    value: Optional[int] = None
    is_equippable: bool
    is_consumable: bool
    effects: List[str] = Field(default_factory=list)
    lore: str
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class ItemListResponse(BaseModel):
    """Response model for listing items."""

    items: List[ItemResponse] = Field(default_factory=list)
    total: int = Field(default=0, description="Total count of matching items")


class GiveItemRequest(BaseModel):
    """Request model for giving an item to a character."""

    item_id: str = Field(..., description="ID of the item to give")


class RemoveItemResponse(BaseModel):
    """Response model for removing an item from a character."""

    success: bool = Field(..., description="Whether removal was successful")
    message: str = Field(default="", description="Status message")


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
    "CharacterGenerationRequest",
    "CharacterGenerationResponse",
    "SceneGenerationRequest",
    "SceneGenerationResponse",
    # Narrative Streaming Schemas
    "WorldContextEntity",
    "WorldContext",
    "NarrativeStreamRequest",
    "NarrativeStreamChunk",
    "NarrativeStreamMetadata",
    "FileCount",
    "CampaignsListResponse",
    "CampaignCreationRequest",
    "CampaignCreationResponse",
    "CampaignDetailResponse",
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
    # Structure (Outline) Schemas
    "StoryCreateRequest",
    "StoryUpdateRequest",
    "StoryResponse",
    "StoryListResponse",
    "ChapterCreateRequest",
    "ChapterUpdateRequest",
    "ChapterResponse",
    "ChapterListResponse",
    "SceneCreateRequest",
    "SceneUpdateRequest",
    "SceneResponse",
    "SceneListResponse",
    "MoveChapterRequest",
    "MoveSceneRequest",
    "StructureErrorResponse",
    # Relationship Schemas
    "RelationshipCreateRequest",
    "RelationshipUpdateRequest",
    "RelationshipResponse",
    "RelationshipListResponse",
    # Item Schemas
    "ItemCreateRequest",
    "ItemUpdateRequest",
    "ItemResponse",
    "ItemListResponse",
    "GiveItemRequest",
    "RemoveItemResponse",
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
    ]
except ImportError:
    pass
