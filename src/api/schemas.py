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


class CharacterPsychologySchema(BaseModel):
    """Schema for Big Five personality model.

    The Big Five (OCEAN) traits quantify personality:
    - Openness: Appreciation for art, emotion, adventure, unusual ideas
    - Conscientiousness: Self-discipline, act dutifully, aim for achievement
    - Extraversion: Energy, positive emotions, assertiveness, sociability
    - Agreeableness: Tendency to be compassionate and cooperative
    - Neuroticism: Tendency to experience unpleasant emotions easily

    All traits are scored 0-100 where:
    - 0-30: Low
    - 31-70: Average
    - 71-100: High
    """

    openness: int = Field(
        ..., ge=0, le=100, description="Openness to experience (0-100)"
    )
    conscientiousness: int = Field(
        ..., ge=0, le=100, description="Conscientiousness (0-100)"
    )
    extraversion: int = Field(..., ge=0, le=100, description="Extraversion (0-100)")
    agreeableness: int = Field(..., ge=0, le=100, description="Agreeableness (0-100)")
    neuroticism: int = Field(..., ge=0, le=100, description="Neuroticism (0-100)")


class DialogueGenerationRequest(BaseModel):
    """Request model for generating character dialogue.

    Uses character psychology, traits, and speaking style to generate
    authentic dialogue that sounds like the character would naturally speak.
    """

    character_id: str = Field(..., description="ID of the character to generate dialogue for")
    context: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The situation or prompt the character is responding to",
    )
    mood: Optional[str] = Field(
        None,
        max_length=50,
        description="Current emotional state (e.g., 'angry', 'excited', 'fearful')",
    )
    # Optional override fields for when character data isn't in the system
    psychology_override: Optional[CharacterPsychologySchema] = Field(
        None, description="Optional psychology override if not using stored character data"
    )
    traits_override: Optional[List[str]] = Field(
        None, description="Optional traits override"
    )
    speaking_style_override: Optional[str] = Field(
        None, max_length=200, description="Optional speaking style override"
    )


class DialogueGenerationResponse(BaseModel):
    """Response model for generated dialogue.

    Contains the character's spoken words along with metadata about
    their internal state and physical expression.
    """

    dialogue: str = Field(..., description="The character's spoken response")
    tone: str = Field(..., description="Emotional tone (e.g., 'defensive', 'excited')")
    internal_thought: Optional[str] = Field(
        None, description="What the character thinks but doesn't say"
    )
    body_language: Optional[str] = Field(
        None, description="Physical description (e.g., 'crosses arms')"
    )
    character_id: str = Field(..., description="ID of the character who spoke")
    error: Optional[str] = Field(None, description="Error message if generation failed")


class CharacterMemorySchema(BaseModel):
    """Schema for character memory.

    Memories are immutable records of experiences that shape character behavior.

    Importance scale (1-10):
    - 1-3: Minor memories (daily routines, passing encounters)
    - 4-6: Moderate memories (friendships, minor conflicts)
    - 7-8: Significant memories (major life events, turning points)
    - 9-10: Core memories (defining moments, traumas, transformations)
    """

    memory_id: str = Field(..., description="Unique identifier for this memory")
    content: str = Field(
        ..., min_length=1, description="The memory content (what happened)"
    )
    importance: int = Field(
        ..., ge=1, le=10, description="Importance score (1-10)"
    )
    tags: List[str] = Field(
        default_factory=list, description="Categorization tags for retrieval"
    )
    timestamp: str = Field(..., description="ISO 8601 timestamp of when memory formed")
    is_core_memory: bool = Field(
        False, description="Whether this is a core memory (importance > 8)"
    )
    importance_level: str = Field(
        "moderate", description="Qualitative level: minor, moderate, significant, core"
    )


class CharacterMemoryCreateRequest(BaseModel):
    """Request to create a new character memory."""

    content: str = Field(
        ..., min_length=1, description="The memory content (what happened)"
    )
    importance: int = Field(
        ..., ge=1, le=10, description="Importance score (1-10)"
    )
    tags: List[str] = Field(
        default_factory=list, description="Categorization tags for retrieval"
    )


class CharacterMemoryUpdateRequest(BaseModel):
    """Request to update a character memory (limited updates allowed)."""

    importance: Optional[int] = Field(
        None, ge=1, le=10, description="Updated importance score"
    )
    tags: Optional[List[str]] = Field(
        None, description="Updated tags"
    )


class CharacterMemoriesResponse(BaseModel):
    """Response containing a list of character memories."""

    character_id: str
    memories: List[CharacterMemorySchema]
    total_count: int
    core_memory_count: int


# === Character Goal Schemas (CHAR-029) ===


class CharacterGoalSchema(BaseModel):
    """Schema for character goal.

    Goals represent what a character wants to achieve, driving motivation
    and narrative arcs.

    Status values:
    - ACTIVE: Currently being pursued
    - COMPLETED: Successfully achieved
    - FAILED: Abandoned or became impossible

    Urgency levels:
    - LOW: Background ambition, no time pressure
    - MEDIUM: Important but not immediate
    - HIGH: Pressing concern that demands attention
    - CRITICAL: Must be addressed immediately
    """

    goal_id: str = Field(..., description="Unique identifier for this goal")
    description: str = Field(
        ..., min_length=1, description="What the character wants to achieve"
    )
    status: str = Field(
        ..., description="Goal status: ACTIVE, COMPLETED, or FAILED"
    )
    urgency: str = Field(
        ..., description="Urgency level: LOW, MEDIUM, HIGH, or CRITICAL"
    )
    created_at: str = Field(..., description="ISO 8601 timestamp when goal was created")
    completed_at: Optional[str] = Field(
        None, description="ISO 8601 timestamp when goal was completed/failed"
    )
    is_active: bool = Field(True, description="Whether the goal is still being pursued")
    is_urgent: bool = Field(
        False, description="Whether the goal requires immediate attention"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid_statuses = {"ACTIVE", "COMPLETED", "FAILED"}
        if v.upper() not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v.upper()

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: str) -> str:
        valid_urgencies = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        if v.upper() not in valid_urgencies:
            raise ValueError(f"Urgency must be one of: {valid_urgencies}")
        return v.upper()


class CharacterGoalCreateRequest(BaseModel):
    """Request to create a new character goal."""

    description: str = Field(
        ..., min_length=1, description="What the character wants to achieve"
    )
    urgency: str = Field(
        "MEDIUM", description="Urgency level: LOW, MEDIUM, HIGH, or CRITICAL"
    )

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: str) -> str:
        valid_urgencies = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        if v.upper() not in valid_urgencies:
            raise ValueError(f"Urgency must be one of: {valid_urgencies}")
        return v.upper()


class CharacterGoalUpdateRequest(BaseModel):
    """Request to update a character goal."""

    status: Optional[str] = Field(
        None, description="New status: ACTIVE, COMPLETED, or FAILED"
    )
    urgency: Optional[str] = Field(
        None, description="New urgency level: LOW, MEDIUM, HIGH, or CRITICAL"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid_statuses = {"ACTIVE", "COMPLETED", "FAILED"}
        if v.upper() not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v.upper()

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid_urgencies = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        if v.upper() not in valid_urgencies:
            raise ValueError(f"Urgency must be one of: {valid_urgencies}")
        return v.upper()


class CharacterGoalsResponse(BaseModel):
    """Response containing a list of character goals."""

    character_id: str
    goals: List[CharacterGoalSchema]
    total_count: int
    active_count: int
    completed_count: int
    failed_count: int


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
    psychology: Optional[CharacterPsychologySchema] = Field(
        None, description="Big Five personality traits (OCEAN model)"
    )
    memories: List[CharacterMemorySchema] = Field(
        default_factory=list, description="Character memories"
    )
    goals: List[CharacterGoalSchema] = Field(
        default_factory=list, description="Character goals"
    )


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


class CharacterProfileGenerationRequest(BaseModel):
    """Request model for character profile generation.

    This generates a detailed character profile with aliases, archetype, traits,
    appearance, backstory, etc. using LLM or mock generator.
    """

    name: str = Field(..., min_length=1, max_length=100, description="Character's primary name")
    archetype: str = Field(
        ..., min_length=1, max_length=50, description="Character archetype (e.g., Hero, Villain, Mentor)"
    )
    context: Optional[str] = Field(
        None, max_length=500, description="Additional context about the character's world or background"
    )


class CharacterProfileGenerationResponse(BaseModel):
    """Response model for character profile generation.

    Contains the generated profile fields matching the CharacterProfile
    value object's fields from WORLD-001.
    """

    name: str
    aliases: List[str]
    archetype: str
    traits: List[str]
    appearance: str
    backstory: str
    motivations: List[str]
    quirks: List[str]


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
    trust: int = Field(default=50, ge=0, le=100, description="Trust level (0-100)")
    romance: int = Field(default=0, ge=0, le=100, description="Romance level (0-100)")


class RelationshipUpdateRequest(BaseModel):
    """Request model for updating a relationship."""

    relationship_type: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None, max_length=1000)
    strength: Optional[int] = Field(default=None, ge=0, le=100)
    is_active: Optional[bool] = Field(default=None)
    trust: Optional[int] = Field(default=None, ge=0, le=100, description="Trust level")
    romance: Optional[int] = Field(default=None, ge=0, le=100, description="Romance level")


class InteractionLogSchema(BaseModel):
    """Schema for a single interaction log entry."""

    interaction_id: str = Field(..., description="Unique ID for this interaction")
    summary: str = Field(..., description="Description of the interaction")
    trust_change: int = Field(..., ge=-100, le=100, description="Trust change (-100 to +100)")
    romance_change: int = Field(
        ..., ge=-100, le=100, description="Romance change (-100 to +100)"
    )
    timestamp: str = Field(..., description="ISO 8601 timestamp of the interaction")


class LogInteractionRequest(BaseModel):
    """Request model for logging an interaction."""

    summary: str = Field(..., min_length=1, max_length=500, description="Interaction description")
    trust_change: int = Field(default=0, ge=-100, le=100, description="Trust change")
    romance_change: int = Field(default=0, ge=-100, le=100, description="Romance change")


class RelationshipHistoryGenerationResponse(BaseModel):
    """Response model for generated relationship history.

    Contains a backstory explaining how two characters developed their current
    relationship dynamics based on trust/romance levels.
    """

    backstory: str = Field(..., description="2-4 paragraph narrative explaining relationship history")
    first_meeting: Optional[str] = Field(None, description="How the characters first met")
    defining_moment: Optional[str] = Field(None, description="Pivotal event shaping current dynamic")
    current_status: Optional[str] = Field(None, description="Summary of where they currently stand")
    error: Optional[str] = Field(None, description="Error message if generation failed")


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
    trust: int = Field(default=50, description="Trust level (0-100)")
    romance: int = Field(default=0, description="Romance level (0-100)")
    interaction_history: List[InteractionLogSchema] = Field(
        default_factory=list, description="History of interactions"
    )
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class RelationshipListResponse(BaseModel):
    """Response model for listing relationships."""

    relationships: List[RelationshipResponse] = Field(default_factory=list)
    total: int = Field(default=0, description="Total count of matching relationships")


# === Social Network Analysis Schemas (CHAR-031) ===


class CharacterCentralitySchema(BaseModel):
    """Centrality metrics for a single character in the social network.

    Why centrality: In narrative design, understanding which characters are
    most connected helps identify protagonists, social hubs, and potential
    dramatic focal points.
    """

    character_id: str = Field(..., description="Character UUID")
    relationship_count: int = Field(default=0, ge=0, description="Total relationships (degree centrality)")
    positive_count: int = Field(default=0, ge=0, description="Positive relationships (ally, family, romantic)")
    negative_count: int = Field(default=0, ge=0, description="Negative relationships (enemy, rival)")
    average_trust: float = Field(default=0.0, ge=0, le=100, description="Average trust across relationships")
    average_romance: float = Field(default=0.0, ge=0, le=100, description="Average romance across relationships")
    centrality_score: float = Field(default=0.0, ge=0, le=100, description="Normalized centrality (0-100)")


class SocialAnalysisResponse(BaseModel):
    """Complete social network analysis result.

    Provides graph analytics for the character relationship network including
    centrality metrics, extreme characters, and network properties.
    """

    character_centralities: Dict[str, CharacterCentralitySchema] = Field(
        default_factory=dict,
        description="Mapping of character_id to their centrality metrics",
    )
    most_connected: Optional[str] = Field(None, description="Character ID with most relationships")
    most_hated: Optional[str] = Field(None, description="Character ID with most negative relationships")
    most_loved: Optional[str] = Field(None, description="Character ID with highest trust/romance average")
    total_relationships: int = Field(default=0, ge=0, description="Total character-to-character relationships")
    total_characters: int = Field(default=0, ge=0, description="Unique characters in the social graph")
    network_density: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Ratio of actual to possible relationships (0.0-1.0)",
    )


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


# === Lore Entry Schemas (WORLD-010) ===


class LoreEntryCreateRequest(BaseModel):
    """Request model for creating a lore entry."""

    title: str = Field(..., min_length=1, max_length=300, description="Entry title")
    content: str = Field(default="", description="Full content (markdown supported)")
    tags: List[str] = Field(
        default_factory=list, max_length=20, description="Searchable tags"
    )
    category: str = Field(
        default="history", description="Category: HISTORY, CULTURE, MAGIC, TECHNOLOGY"
    )
    summary: str = Field(default="", max_length=500, description="Short summary")


class LoreEntryUpdateRequest(BaseModel):
    """Request model for updating a lore entry."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    content: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None, max_length=20)
    category: Optional[str] = Field(default=None)
    summary: Optional[str] = Field(default=None, max_length=500)


class LoreEntryResponse(BaseModel):
    """Response model for a single lore entry."""

    id: str = Field(..., description="Entry UUID")
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    category: str
    summary: str
    related_entry_ids: List[str] = Field(default_factory=list)
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class LoreEntryListResponse(BaseModel):
    """Response model for listing lore entries."""

    entries: List[LoreEntryResponse] = Field(default_factory=list)
    total: int = Field(default=0, description="Total count of matching entries")


class LoreSearchRequest(BaseModel):
    """Request model for searching lore entries."""

    query: str = Field(default="", description="Search query (matches title)")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    category: Optional[str] = Field(default=None, description="Filter by category")


# ============ World Rule Schemas ============


class WorldRuleCreateRequest(BaseModel):
    """Request model for creating a world rule."""

    name: str = Field(..., min_length=1, max_length=200, description="Rule name")
    description: str = Field(default="", max_length=5000, description="Rule description")
    consequence: str = Field(default="", max_length=2000, description="What happens when rule is invoked/violated")
    exceptions: List[str] = Field(
        default_factory=list, max_length=20, description="Cases where rule doesn't apply"
    )
    category: str = Field(default="", max_length=50, description="Rule category (magic, physics, social, etc.)")
    severity: int = Field(default=50, ge=0, le=100, description="How strictly enforced (0-100)")


class WorldRuleUpdateRequest(BaseModel):
    """Request model for updating a world rule."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    consequence: Optional[str] = Field(default=None, max_length=2000)
    exceptions: Optional[List[str]] = Field(default=None, max_length=20)
    category: Optional[str] = Field(default=None, max_length=50)
    severity: Optional[int] = Field(default=None, ge=0, le=100)


class WorldRuleResponse(BaseModel):
    """Response model for a single world rule."""

    id: str = Field(..., description="Rule UUID")
    name: str
    description: str
    consequence: str
    exceptions: List[str] = Field(default_factory=list)
    category: str
    severity: int
    related_rule_ids: List[str] = Field(default_factory=list)
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class WorldRuleListResponse(BaseModel):
    """Response model for listing world rules."""

    rules: List[WorldRuleResponse] = Field(default_factory=list)
    total: int = Field(default=0, description="Total count of matching rules")


# === Faction Schemas (CHAR-035) ===


class FactionJoinRequest(BaseModel):
    """Request model for joining a faction.

    Why character_id is required: A character must be explicitly specified
    to join a faction. This enables scenarios like GMs assigning characters
    to factions or characters choosing to join.
    """

    character_id: str = Field(..., description="Character ID to join the faction")


class FactionJoinResponse(BaseModel):
    """Response model for successful faction join operation."""

    faction_id: str = Field(..., description="Faction UUID that was joined")
    character_id: str = Field(..., description="Character UUID that joined")
    faction_name: str = Field(..., description="Display name of the faction")
    message: str = Field(default="Successfully joined faction")


class FactionLeaveRequest(BaseModel):
    """Request model for leaving a faction."""

    character_id: str = Field(..., description="Character ID to leave the faction")


class FactionLeaveResponse(BaseModel):
    """Response model for successful faction leave operation."""

    faction_id: str = Field(..., description="Faction UUID that was left")
    character_id: str = Field(..., description="Character UUID that left")
    message: str = Field(default="Successfully left faction")


class FactionSetLeaderRequest(BaseModel):
    """Request model for setting a faction leader."""

    character_id: str = Field(..., description="Character ID to become the leader")
    leader_name: Optional[str] = Field(None, description="Display name for the leader")


class FactionSetLeaderResponse(BaseModel):
    """Response model for successful leader assignment."""

    faction_id: str = Field(..., description="Faction UUID")
    leader_id: str = Field(..., description="Character UUID of new leader")
    leader_name: Optional[str] = Field(None, description="Display name of new leader")
    message: str = Field(default="Successfully set faction leader")


class FactionMemberSchema(BaseModel):
    """Schema for a faction member."""

    character_id: str = Field(..., description="Character UUID")
    name: str = Field(default="", description="Character display name")
    is_leader: bool = Field(default=False, description="Whether this member is the faction leader")


class FactionDetailResponse(BaseModel):
    """Response model for faction details including members."""

    id: str = Field(..., description="Faction UUID")
    name: str = Field(..., description="Faction name")
    description: str = Field(default="", description="Faction description")
    faction_type: str = Field(..., description="Type of faction (KINGDOM, GUILD, etc.)")
    alignment: str = Field(..., description="Moral alignment")
    status: str = Field(..., description="Operational status")
    leader_id: Optional[str] = Field(None, description="Character ID of the leader")
    leader_name: Optional[str] = Field(None, description="Display name of the leader")
    influence: int = Field(default=50, ge=0, le=100, description="Faction influence")
    member_count: int = Field(default=0, ge=0, description="Number of members")
    members: List[FactionMemberSchema] = Field(default_factory=list, description="List of faction members")


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
    "CharacterPsychologySchema",
    "CharacterGoalSchema",
    "CharacterGoalCreateRequest",
    "CharacterGoalUpdateRequest",
    "CharacterGoalsResponse",
    "DialogueGenerationRequest",
    "DialogueGenerationResponse",
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
    "InteractionLogSchema",
    "LogInteractionRequest",
    "RelationshipHistoryGenerationResponse",
    # Social Network Analysis Schemas
    "CharacterCentralitySchema",
    "SocialAnalysisResponse",
    # Item Schemas
    "ItemCreateRequest",
    "ItemUpdateRequest",
    "ItemResponse",
    "ItemListResponse",
    "GiveItemRequest",
    "RemoveItemResponse",
    # Lore Entry Schemas
    "LoreEntryCreateRequest",
    "LoreEntryUpdateRequest",
    "LoreEntryResponse",
    "LoreEntryListResponse",
    "LoreSearchRequest",
    # World Rule Schemas
    "WorldRuleCreateRequest",
    "WorldRuleUpdateRequest",
    "WorldRuleResponse",
    "WorldRuleListResponse",
    # Faction Schemas
    "FactionJoinRequest",
    "FactionJoinResponse",
    "FactionLeaveRequest",
    "FactionLeaveResponse",
    "FactionSetLeaderRequest",
    "FactionSetLeaderResponse",
    "FactionMemberSchema",
    "FactionDetailResponse",
]

try:
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

    _OPTIONAL_SCHEMA_TYPES = (
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
        CausalGraphData,
        CausalGraphRequest,
        CausalLinkResponse,
        EmergentNarrativeData,
        EmergentNarrativeRequest,
        NarrativeBuildRequest,
        NarrativeEventResponse,
        NegotiationRequest,
        NegotiationResponse,
        InteractionRequest,
        InteractionResponse,
        CreateKnowledgeEntryRequest,
        CreateKnowledgeEntryResponse,
        KnowledgeEntryResponse,
        UpdateKnowledgeEntryRequest,
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
    ]
except ImportError:
    # Optional imports for extended API schemas - these modules may not exist in all environments
    pass
