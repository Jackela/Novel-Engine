from enum import Enum
from typing import Any, Dict, List, Optional

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
    story_phase: Optional[str] = Field(
        default="setup",
        description="Story phase: 'setup', 'inciting_incident', 'rising_action', 'climax', 'resolution'",
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
    story_phase: Optional[str] = Field(
        default=None,
        description="Story phase: 'setup', 'inciting_incident', 'rising_action', 'climax', 'resolution'",
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
    story_phase: str = Field(default="setup", description="Story structure phase")
    beat_count: int = Field(default=0, description="Number of beats")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class SceneListResponse(BaseModel):
    """Response model for listing scenes."""

    chapter_id: str = Field(..., description="Parent chapter UUID")
    scenes: List["SceneResponse"] = Field(default_factory=list)


# === Beat Schemas (DIR-042) ===


class BeatCreateRequest(BaseModel):
    """Request model for creating a new beat.

    Beats are atomic narrative units within a scene. Each beat
    represents a single action, dialogue, or reaction moment.
    """

    content: str = Field(default="", max_length=10000, description="Beat narrative text")
    beat_type: str = Field(
        default="action",
        description="Beat type: 'action', 'dialogue', 'reaction', 'revelation', 'transition', 'description'",
    )
    mood_shift: int = Field(
        default=0, ge=-5, le=5, description="Emotional impact (-5 to +5)"
    )
    order_index: Optional[int] = Field(
        default=None, ge=0, description="Position in scene (0-based)"
    )


class BeatUpdateRequest(BaseModel):
    """Request model for updating a beat."""

    content: Optional[str] = Field(default=None, max_length=10000)
    beat_type: Optional[str] = Field(
        default=None,
        description="Beat type: 'action', 'dialogue', 'reaction', 'revelation', 'transition', 'description'",
    )
    mood_shift: Optional[int] = Field(default=None, ge=-5, le=5)


class BeatResponse(BaseModel):
    """Response model for a single beat."""

    id: str = Field(..., description="Beat UUID")
    scene_id: str = Field(..., description="Parent scene UUID")
    content: str = Field(default="", description="Beat narrative text")
    beat_type: str = Field(..., description="Beat classification")
    mood_shift: int = Field(default=0, description="Emotional impact (-5 to +5)")
    order_index: int = Field(..., description="Position in scene")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class BeatListResponse(BaseModel):
    """Response model for listing beats."""

    scene_id: str = Field(..., description="Parent scene UUID")
    beats: List["BeatResponse"] = Field(default_factory=list)


class ReorderBeatsRequest(BaseModel):
    """Request model for reordering beats within a scene."""

    beat_ids: List[str] = Field(..., description="Beat UUIDs in desired order")


# === Beat Suggestion Schemas (DIR-047/DIR-048) ===


class BeatSuggestionRequest(BaseModel):
    """Request model for AI beat suggestions.

    Asks the AI to suggest 3 possible next beats based on the current
    beat sequence and scene context.
    """

    scene_id: str = Field(..., description="Scene UUID")
    current_beats: List[Dict[str, JsonValue]] = Field(
        default_factory=list,
        description="Current beats in scene with 'beat_type', 'content', 'mood_shift'",
    )
    scene_context: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Scene context: setting, characters, situation/goals",
    )
    mood_target: Optional[int] = Field(
        None,
        ge=-5,
        le=5,
        description="Optional target mood direction (-5 to +5)",
    )


class BeatSuggestion(BaseModel):
    """A single AI-generated beat suggestion."""

    beat_type: str = Field(..., description="Suggested beat type")
    content: str = Field(..., description="Suggested narrative text (1-3 sentences)")
    mood_shift: int = Field(default=0, ge=-5, le=5, description="Emotional impact")
    rationale: Optional[str] = Field(None, description="AI's explanation for this suggestion")


class BeatSuggestionResponse(BaseModel):
    """Response model for AI beat suggestions.

    Contains 3 AI-generated beat suggestions that could follow
    the current sequence.
    """

    scene_id: str = Field(..., description="Scene UUID")
    suggestions: List[BeatSuggestion] = Field(
        default_factory=list, min_length=0, max_length=3, description="3 suggested beats"
    )
    error: Optional[str] = Field(None, description="Error message if generation failed")


# === Pacing Schemas (DIR-043/DIR-044) ===


class ScenePacingMetricsResponse(BaseModel):
    """Pacing metrics for a single scene.

    Why frozen on backend:
        Metrics are immutable snapshots. Modifications should go through
        the Scene entity and generate new metrics.
    """

    scene_id: str = Field(..., description="Scene UUID")
    scene_title: str = Field(..., description="Scene title for display")
    order_index: int = Field(..., description="Position in chapter")
    tension_level: int = Field(..., ge=1, le=10, description="Dramatic tension (1-10)")
    energy_level: int = Field(..., ge=1, le=10, description="Narrative momentum (1-10)")


class PacingIssueResponse(BaseModel):
    """A detected pacing problem in the chapter."""

    issue_type: str = Field(..., description="Category: monotonous_tension, tension_spike, etc.")
    description: str = Field(..., description="Human-readable description")
    affected_scenes: List[str] = Field(..., description="Scene UUIDs involved")
    severity: str = Field(..., description="low, medium, or high")
    suggestion: str = Field(..., description="Recommendation for addressing the issue")


class ChapterPacingResponse(BaseModel):
    """Complete pacing analysis for a chapter.

    Why this structure:
        Provides the frontend with all data needed to render the PacingGraph:
        - scene_metrics: ordered list for the X-axis (scene sequence)
        - average/range values: for reference lines and scaling
        - issues: for displaying warnings in the UI
    """

    chapter_id: str = Field(..., description="Chapter UUID")
    scene_metrics: List[ScenePacingMetricsResponse] = Field(
        default_factory=list, description="Per-scene metrics in order"
    )
    issues: List[PacingIssueResponse] = Field(
        default_factory=list, description="Detected pacing problems"
    )
    average_tension: float = Field(..., ge=0, le=10, description="Mean tension")
    average_energy: float = Field(..., ge=0, le=10, description="Mean energy")
    tension_range: List[int] = Field(..., min_length=2, max_length=2, description="[min, max] tension")
    energy_range: List[int] = Field(..., min_length=2, max_length=2, description="[min, max] energy")


# === Conflict Schemas (DIR-045) ===


class ConflictCreateRequest(BaseModel):
    """Request model for creating a new conflict.

    Conflicts represent sources of dramatic tension in a scene.
    Every compelling scene should have at least one conflict.
    """

    conflict_type: str = Field(
        ...,
        description="Conflict type: 'internal', 'external', 'interpersonal'",
    )
    stakes: str = Field(
        default="medium",
        description="Stakes level: 'low', 'medium', 'high', 'critical'",
    )
    description: str = Field(
        ..., min_length=1, max_length=2000, description="Description of the conflict"
    )
    resolution_status: str = Field(
        default="unresolved",
        description="Resolution status: 'unresolved', 'escalating', 'resolved'",
    )


class ConflictUpdateRequest(BaseModel):
    """Request model for updating a conflict."""

    conflict_type: Optional[str] = Field(
        default=None,
        description="Conflict type: 'internal', 'external', 'interpersonal'",
    )
    stakes: Optional[str] = Field(
        default=None,
        description="Stakes level: 'low', 'medium', 'high', 'critical'",
    )
    description: Optional[str] = Field(
        default=None, min_length=1, max_length=2000
    )
    resolution_status: Optional[str] = Field(
        default=None,
        description="Resolution status: 'unresolved', 'escalating', 'resolved'",
    )


class ConflictResponse(BaseModel):
    """Response model for a single conflict."""

    id: str = Field(..., description="Conflict UUID")
    scene_id: str = Field(..., description="Parent scene UUID")
    conflict_type: str = Field(..., description="Conflict classification")
    stakes: str = Field(..., description="Stakes level")
    description: str = Field(..., description="Conflict description")
    resolution_status: str = Field(..., description="Current resolution state")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class ConflictListResponse(BaseModel):
    """Response model for listing conflicts."""

    scene_id: str = Field(..., description="Parent scene UUID")
    conflicts: List["ConflictResponse"] = Field(default_factory=list)


# ============ Plotline Schemas (DIR-049) ============


class PlotlineCreateRequest(BaseModel):
    """Request model for creating a new plotline.

    Plotlines represent narrative threads that weave through multiple scenes.
    A scene can belong to multiple plotlines simultaneously.
    """

    name: str = Field(..., min_length=1, max_length=200, description="Plotline name")
    color: str = Field(..., pattern=r"^#[0-9a-fA-F]{3,6}$", description="Hex color code (e.g., #ff5733)")
    description: str = Field(default="", max_length=2000, description="Plotline description")
    status: str = Field(
        default="active",
        description="Plotline status: 'active', 'resolved', 'abandoned'",
    )


class PlotlineUpdateRequest(BaseModel):
    """Request model for updating a plotline."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9a-fA-F]{3,6}$")
    description: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[str] = Field(
        default=None,
        description="Plotline status: 'active', 'resolved', 'abandoned'",
    )


class PlotlineResponse(BaseModel):
    """Response model for a single plotline."""

    id: str = Field(..., description="Plotline UUID")
    name: str = Field(..., description="Plotline name")
    color: str = Field(..., description="Hex color code")
    description: str = Field(..., description="Plotline description")
    status: str = Field(..., description="Current status")
    scene_count: int = Field(default=0, description="Number of scenes linked to this plotline")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class PlotlineListResponse(BaseModel):
    """Response model for listing plotlines."""

    plotlines: List["PlotlineResponse"] = Field(default_factory=list)


class LinkSceneToPlotlineRequest(BaseModel):
    """Request model for linking a scene to a plotline."""

    plotline_id: str = Field(..., description="Plotline UUID to link")


class UnlinkSceneFromPlotlineRequest(BaseModel):
    """Request model for unlinking a scene from a plotline."""

    plotline_id: str = Field(..., description="Plotline UUID to unlink")


class SetScenePlotlinesRequest(BaseModel):
    """Request model for setting all plotlines for a scene."""

    plotline_ids: List[str] = Field(
        default_factory=list,
        description="List of plotline UUIDs to associate with the scene",
    )


class ScenePlotlinesResponse(BaseModel):
    """Response model for listing a scene's plotlines."""

    scene_id: str = Field(..., description="Scene UUID")
    plotline_ids: List[str] = Field(default_factory=list, description="Associated plotline UUIDs")


# ============ Foreshadowing Schemas (DIR-052) ============


# ============ Chapter Analysis Schemas (DIR-055/DIR-056) ============


class HealthScoreEnum(str, Enum):
    """Overall health classification for a chapter."""

    CRITICAL = "critical"  # Major structural issues
    POOR = "poor"  # Multiple significant issues
    FAIR = "fair"  # Some issues but functional
    GOOD = "good"  # Minor issues or well-balanced
    EXCELLENT = "excellent"  # No issues detected


class WarningCategoryEnum(str, Enum):
    """Categories of structural warnings."""

    PACING = "pacing"  # Tension/energy issues
    STRUCTURE = "structure"  # Phase distribution issues
    CONFLICT = "conflict"  # Missing or unresolved conflicts
    BALANCE = "balance"  # Word count and beat count issues
    ARC = "arc"  # Tension arc shape issues


class PhaseDistributionResponse(BaseModel):
    """Distribution of scenes across story phases."""

    setup: int = Field(..., description="Number of scenes in SETUP phase")
    inciting_incident: int = Field(..., description="Number of scenes in INCITING_INCIDENT phase")
    rising_action: int = Field(..., description="Number of scenes in RISING_ACTION phase")
    climax: int = Field(..., description="Number of scenes in CLIMAX phase")
    resolution: int = Field(..., description="Number of scenes in RESOLUTION phase")


class WordCountEstimateResponse(BaseModel):
    """Estimated word count metrics for a chapter."""

    total_words: int = Field(..., description="Estimated total word count")
    min_words: int = Field(..., description="Minimum estimated word count")
    max_words: int = Field(..., description="Maximum estimated word count")
    per_scene_average: float = Field(..., description="Average words per scene")


class HealthWarningResponse(BaseModel):
    """A detected structural issue in the chapter."""

    category: str = Field(..., description="The type of issue")
    title: str = Field(..., description="Short, human-readable title")
    description: str = Field(..., description="Detailed explanation of the issue")
    severity: str = Field(..., description="Issue severity (low, medium, high, critical)")
    affected_scenes: List[str] = Field(default_factory=list, description="Scene UUIDs involved")
    recommendation: str = Field(..., description="Actionable suggestion for fixing the issue")


class TensionArcShapeResponse(BaseModel):
    """Analysis of the tension arc shape."""

    shape_type: str = Field(..., description="Descriptive name of the arc shape")
    starts_at: int = Field(..., description="Opening tension level")
    peaks_at: int = Field(..., description="Maximum tension level")
    ends_at: int = Field(..., description="Closing tension level")
    has_clear_climax: bool = Field(..., description="Whether there's a distinct tension peak")
    is_monotonic: bool = Field(..., description="Whether tension stays flat throughout")


class ChapterHealthReportResponse(BaseModel):
    """Complete structural health analysis for a chapter."""

    chapter_id: str = Field(..., description="Chapter UUID")
    health_score: str = Field(..., description="Overall health classification")
    phase_distribution: PhaseDistributionResponse = Field(..., description="Scene counts per story phase")
    word_count: WordCountEstimateResponse = Field(..., description="Estimated word count metrics")
    total_scenes: int = Field(..., description="Number of scenes in the chapter")
    total_beats: int = Field(..., description="Total number of beats across all scenes")
    tension_arc: TensionArcShapeResponse = Field(..., description="Analysis of tension arc shape")
    warnings: List[HealthWarningResponse] = Field(default_factory=list, description="Detected structural issues")
    recommendations: List[str] = Field(default_factory=list, description="Improvement suggestions")


# ============ Scene Critique Schemas (DIR-057/DIR-058) ============


class CritiqueCategoryScoreResponse(BaseModel):
    """Category-specific critique score with issues and suggestions."""

    category: str = Field(..., description="Quality dimension: pacing, voice, showing, dialogue")
    score: int = Field(..., ge=1, le=10, description="Score from 1-10 for this category")
    issues: List[str] = Field(default_factory=list, description="Specific problems identified")
    suggestions: List[str] = Field(default_factory=list, description="Actionable improvements")


class CritiqueSceneRequest(BaseModel):
    """Request model for AI scene critique.

    Asks the AI to analyze scene writing quality across multiple craft dimensions.
    """

    scene_text: str = Field(
        ...,
        min_length=50,
        max_length=12000,
        description="Full text content of the scene to analyze",
    )
    scene_goals: Optional[List[str]] = Field(
        None,
        description="Optional list of writer's goals for the scene (e.g., reveal motivation, build tension)",
    )


class CritiqueSceneResponse(BaseModel):
    """Response model for AI scene critique.

    Contains AI-generated feedback on scene quality including overall score,
    category-specific evaluations, highlights, and actionable suggestions.
    """

    overall_score: int = Field(..., ge=1, le=10, description="Overall quality score (1-10)")
    category_scores: List[CritiqueCategoryScoreResponse] = Field(
        default_factory=list, description="Evaluations by category"
    )
    highlights: List[str] = Field(default_factory=list, description="What works well in the scene")
    summary: str = Field(..., description="Brief 2-3 sentence assessment")
    error: Optional[str] = Field(None, description="Error message if critique failed")


# ============ Foreshadowing Schemas (DIR-052) ============


class ForeshadowingCreateRequest(BaseModel):
    """Request model for creating a new foreshadowing.

    Foreshadowing represents a narrative setup that will be paid off later.
    This enforces Chekhov's Gun: every setup must have a payoff.
    """

    setup_scene_id: str = Field(..., description="Scene UUID where setup occurs")
    description: str = Field(..., min_length=1, max_length=2000, description="Description of the setup")
    status: str = Field(
        default="planted",
        description="Status: 'planted', 'paid_off', 'abandoned'",
    )


class ForeshadowingUpdateRequest(BaseModel):
    """Request model for updating a foreshadowing."""

    description: str = Field(default="", max_length=2000, description="Updated description")
    status: str = Field(default="", description="Updated status")
    payoff_scene_id: Optional[str] = Field(
        default=None, description="Scene UUID where payoff occurs (for paid_off status)"
    )


class LinkPayoffRequest(BaseModel):
    """Request model for linking a payoff scene to foreshadowing.

    This validates that the payoff scene comes after the setup scene.
    """

    payoff_scene_id: str = Field(..., description="Scene UUID where payoff occurs")


class ForeshadowingResponse(BaseModel):
    """Response model for a single foreshadowing."""

    id: str = Field(..., description="Foreshadowing UUID")
    setup_scene_id: str = Field(..., description="Setup scene UUID")
    payoff_scene_id: Optional[str] = Field(None, description="Payoff scene UUID (if paid off)")
    description: str = Field(..., description="Foreshadowing description")
    status: str = Field(..., description="Current status")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class ForeshadowingListResponse(BaseModel):
    """Response model for listing foreshadowing."""

    foreshadowings: List["ForeshadowingResponse"] = Field(default_factory=list)


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


# === Prompt Management Schemas (BRAIN-015) ===


class PromptVariableDefinition(BaseModel):
    """Schema for a prompt variable definition."""

    name: str = Field(..., min_length=1, max_length=100, description="Variable name (must match {{var}} in template)")
    type: str = Field(..., description="Variable type: string, integer, float, boolean, list, dict")
    default_value: Optional[JsonValue] = Field(None, description="Default value if not provided")
    description: str = Field(default="", max_length=500, description="Human-readable description")
    required: bool = Field(default=True, description="Whether this variable must be provided")


class PromptVariableValue(BaseModel):
    """Schema for a prompt variable value during rendering."""

    name: str = Field(..., min_length=1, description="Variable name")
    value: JsonValue = Field(..., description="Variable value")


class PromptSummary(BaseModel):
    """Schema for a prompt template summary (list view)."""

    id: str = Field(..., description="Prompt template UUID")
    name: str = Field(..., description="Prompt name")
    description: str = Field(default="", description="Prompt description")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    version: int = Field(default=1, description="Version number")
    model_provider: str = Field(default="openai", description="LLM provider")
    model_name: str = Field(default="gpt-4", description="Model name")
    variable_count: int = Field(default=0, description="Number of variables")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class PromptModelConfig(BaseModel):
    """Schema for prompt model configuration."""

    provider: str = Field(default="openai", description="LLM provider")
    model_name: str = Field(default="gpt-4", description="Model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=1000, ge=1, description="Maximum tokens to generate")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Nucleus sampling")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")


class PromptDetailResponse(BaseModel):
    """Schema for a full prompt template detail."""

    id: str = Field(..., description="Prompt template UUID")
    name: str = Field(..., description="Prompt name")
    description: str = Field(default="", description="Prompt description")
    content: str = Field(..., description="Template content with {{variable}} placeholders")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    extends: List[str] = Field(default_factory=list, description="Parent template IDs/names this template extends")
    version: int = Field(default=1, description="Version number")
    parent_version_id: Optional[str] = Field(None, description="Parent version ID")
    llm_config: PromptModelConfig = Field(..., description="Model configuration", alias="model_config")
    variables: List[PromptVariableDefinition] = Field(default_factory=list, description="Variable definitions")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")

    model_config = {"populate_by_name": True}


class PromptListResponse(BaseModel):
    """Response model for listing prompts."""

    prompts: List[PromptSummary] = Field(default_factory=list, description="List of prompt summaries")
    total: int = Field(default=0, description="Total count of prompts")
    limit: int = Field(default=100, description="Page size limit")
    offset: int = Field(default=0, description="Pagination offset")


class PromptCreateRequest(BaseModel):
    """Request model for creating a new prompt template."""

    name: str = Field(..., min_length=1, max_length=200, description="Prompt name")
    content: str = Field(..., min_length=1, description="Template content with {{variable}} placeholders")
    description: str = Field(default="", max_length=1000, description="Prompt description")
    tags: List[str] = Field(default_factory=list, max_length=20, description="Tags for categorization")
    extends: List[str] = Field(default_factory=list, max_length=10, description="Parent template IDs/names to extend")
    variables: List[PromptVariableDefinition] = Field(default_factory=list, description="Variable definitions")
    model_provider: str = Field(default="openai", description="LLM provider")
    model_name: str = Field(default="gpt-4", description="Model name")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Maximum tokens to generate")
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Nucleus sampling")
    frequency_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0, description="Presence penalty")


class PromptUpdateRequest(BaseModel):
    """Request model for updating a prompt template (creates new version)."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200, description="Prompt name")
    content: Optional[str] = Field(default=None, min_length=1, description="Template content")
    description: Optional[str] = Field(default=None, max_length=1000, description="Prompt description")
    tags: Optional[List[str]] = Field(default=None, max_length=20, description="Tags for categorization")
    extends: Optional[List[str]] = Field(default=None, max_length=10, description="Parent template IDs/names to extend")
    variables: Optional[List[PromptVariableDefinition]] = Field(default=None, description="Variable definitions")
    model_provider: Optional[str] = Field(default=None, description="LLM provider")
    model_name: Optional[str] = Field(default=None, description="Model name")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="Maximum tokens to generate")
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Nucleus sampling")
    frequency_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0, description="Presence penalty")


class PromptRenderRequest(BaseModel):
    """Request model for rendering a prompt template."""

    variables: List[PromptVariableValue] = Field(default_factory=list, description="Variable values for rendering")
    strict: bool = Field(default=True, description="Raise errors for missing required variables")


class PromptRenderResponse(BaseModel):
    """Response model for a rendered prompt."""

    rendered: str = Field(..., description="Rendered prompt content")
    variables_used: List[str] = Field(default_factory=list, description="Variable names that were used")
    variables_missing: List[str] = Field(default_factory=list, description="Required variables that were missing")
    template_id: str = Field(..., description="Template ID that was rendered")
    template_name: str = Field(..., description="Template name")
    token_count: Optional[int] = Field(None, description="Estimated token count")
    llm_config: Optional[Dict[str, Any]] = Field(None, description="Model configuration used", alias="model_config")

    model_config = {"populate_by_name": True}


class PromptGenerateRequest(BaseModel):
    """Request model for generating output using a prompt template.

    BRAIN-020B: Frontend: Prompt Playground - Integration
    Combines rendering and LLM generation in a single request.
    """

    variables: List[PromptVariableValue] = Field(
        default_factory=list,
        description="Variable values for rendering the prompt"
    )
    # Override model config from the prompt template
    provider: Optional[str] = Field(
        None,
        description="Override LLM provider (uses prompt config if not specified)"
    )
    model_name: Optional[str] = Field(
        None,
        description="Override model name (uses prompt config if not specified)"
    )
    temperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=2.0,
        description="Override sampling temperature"
    )
    max_tokens: Optional[int] = Field(
        None,
        ge=1,
        description="Override max tokens to generate"
    )
    top_p: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Override nucleus sampling"
    )
    frequency_penalty: Optional[float] = Field(
        None,
        ge=-2.0,
        le=2.0,
        description="Override frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        None,
        ge=-2.0,
        le=2.0,
        description="Override presence penalty"
    )
    strict: bool = Field(
        default=True,
        description="Raise errors for missing required variables"
    )


class PromptGenerateResponse(BaseModel):
    """Response model for prompt generation output.

    BRAIN-020B: Frontend: Prompt Playground - Integration
    Contains both the rendered prompt and the LLM-generated output.
    """

    rendered: str = Field(..., description="The rendered prompt content")
    output: str = Field(..., description="The LLM-generated output")
    template_id: str = Field(..., description="Template ID that was used")
    template_name: str = Field(..., description="Template name")
    prompt_tokens: int = Field(..., description="Estimated input token count")
    output_tokens: Optional[int] = Field(None, description="Output token count if available")
    total_tokens: int = Field(..., description="Total token count")
    latency_ms: float = Field(..., description="Generation time in milliseconds")
    model_used: str = Field(..., description="Model that was used for generation")
    error: Optional[str] = Field(None, description="Error message if generation failed")


# === Prompt Analytics Schemas (BRAIN-022B) ===


class PromptAnalyticsTimePeriod(str, Enum):
    """Time period for analytics aggregation."""

    day = "day"
    week = "week"
    month = "month"
    all = "all"


class PromptTimeSeriesDataPoint(BaseModel):
    """Single data point in time series analytics."""

    period: str = Field(..., description="Time period identifier (ISO date or week number)")
    total_uses: int = Field(default=0, ge=0, description="Total uses in this period")
    successful_uses: int = Field(default=0, ge=0, description="Successful uses in this period")
    failed_uses: int = Field(default=0, ge=0, description="Failed uses in this period")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens consumed")
    avg_latency_ms: float = Field(default=0.0, ge=0, description="Average latency")
    avg_rating: float = Field(default=0.0, ge=0, le=5, description="Average rating")


class PromptRatingDistribution(BaseModel):
    """Distribution of user ratings."""

    one_star: int = Field(default=0, ge=0, description="Count of 1-star ratings")
    two_star: int = Field(default=0, ge=0, description="Count of 2-star ratings")
    three_star: int = Field(default=0, ge=0, description="Count of 3-star ratings")
    four_star: int = Field(default=0, ge=0, description="Count of 4-star ratings")
    five_star: int = Field(default=0, ge=0, description="Count of 5-star ratings")


class PromptAnalyticsResponse(BaseModel):
    """Response model for prompt analytics.

    BRAIN-022B: Backend: Prompt Analytics - API
    Provides usage statistics and metrics over time.
    """

    prompt_id: str = Field(..., description="Prompt template ID")
    prompt_name: str = Field(..., description="Prompt name")
    period: PromptAnalyticsTimePeriod = Field(
        default=PromptAnalyticsTimePeriod.all,
        description="Time period for aggregation"
    )

    # Overall metrics
    total_uses: int = Field(default=0, ge=0, description="Total number of uses")
    successful_uses: int = Field(default=0, ge=0, description="Successful generations")
    failed_uses: int = Field(default=0, ge=0, description="Failed generations")
    success_rate: float = Field(default=0.0, ge=0, le=100, description="Success rate percentage")

    # Token metrics
    total_tokens: int = Field(default=0, ge=0, description="Total tokens consumed")
    total_input_tokens: int = Field(default=0, ge=0, description="Total input tokens")
    total_output_tokens: int = Field(default=0, ge=0, description="Total output tokens")
    avg_tokens_per_use: float = Field(default=0.0, ge=0, description="Average tokens per use")
    avg_input_tokens: float = Field(default=0.0, ge=0, description="Average input tokens")
    avg_output_tokens: float = Field(default=0.0, ge=0, description="Average output tokens")

    # Latency metrics
    total_latency_ms: float = Field(default=0.0, ge=0, description="Total latency")
    avg_latency_ms: float = Field(default=0.0, ge=0, description="Average latency in ms")
    min_latency_ms: float = Field(default=0.0, ge=0, description="Minimum latency")
    max_latency_ms: float = Field(default=0.0, ge=0, description="Maximum latency")

    # Rating metrics
    rating_sum: float = Field(default=0.0, description="Sum of ratings")
    rating_count: int = Field(default=0, ge=0, description="Number of ratings")
    avg_rating: float = Field(default=0.0, ge=0, le=5, description="Average rating")
    rating_distribution: PromptRatingDistribution = Field(
        default_factory=PromptRatingDistribution,
        description="Distribution of ratings"
    )

    # Time series data
    time_series: List[PromptTimeSeriesDataPoint] = Field(
        default_factory=list,
        description="Usage over time grouped by period"
    )

    # Metadata
    first_used: Optional[str] = Field(None, description="First use timestamp")
    last_used: Optional[str] = Field(None, description="Last use timestamp")
    generated_at: str = Field(..., description="When analytics were generated")


class PromptAnalyticsRequest(BaseModel):
    """Request parameters for analytics query."""

    period: PromptAnalyticsTimePeriod = Field(
        default=PromptAnalyticsTimePeriod.all,
        description="Time period for aggregation (day, week, month, all)"
    )
    start_date: Optional[str] = Field(
        None,
        description="ISO 8601 start date for filtering (exclusive of period)"
    )
    end_date: Optional[str] = Field(
        None,
        description="ISO 8601 end date for filtering (exclusive of period)"
    )
    workspace_id: Optional[str] = Field(
        None,
        description="Filter by workspace ID"
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum time series data points"
    )


# === Prompt Experiment Schemas (BRAIN-018B) ===


class ExperimentMetricsResponse(BaseModel):
    """Schema for experiment metrics."""

    total_runs: int = Field(default=0, ge=0, description="Total number of runs")
    success_count: int = Field(default=0, ge=0, description="Number of successful runs")
    failure_count: int = Field(default=0, ge=0, description="Number of failed runs")
    success_rate: float = Field(default=0.0, ge=0, le=100, description="Success rate percentage")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens consumed")
    avg_tokens_per_run: float = Field(default=0.0, ge=0, description="Average tokens per run")
    token_efficiency: float = Field(default=0.0, ge=0, description="Tokens per successful generation")
    total_latency_ms: float = Field(default=0.0, ge=0, description="Total latency in milliseconds")
    avg_latency_ms: float = Field(default=0.0, ge=0, description="Average latency in milliseconds")
    rating_sum: float = Field(default=0.0, description="Sum of all ratings")
    rating_count: int = Field(default=0, ge=0, description="Number of ratings")
    avg_rating: float = Field(default=0.0, ge=0, le=5, description="Average user rating")


class ConfidenceIntervalResponse(BaseModel):
    """Schema for confidence interval of a metric."""

    lower: float = Field(..., ge=0, le=100, description="Lower bound of confidence interval")
    upper: float = Field(..., ge=0, le=100, description="Upper bound of confidence interval")


class ExperimentVariantResponse(BaseModel):
    """Schema for an experiment variant with metrics."""

    prompt_id: str = Field(..., description="Prompt template ID")
    total_runs: int = Field(default=0, ge=0, description="Total number of runs")
    success_count: int = Field(default=0, ge=0, description="Number of successful runs")
    failure_count: int = Field(default=0, ge=0, description="Number of failed runs")
    success_rate: float = Field(default=0.0, ge=0, le=100, description="Success rate percentage")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens consumed")
    avg_tokens_per_run: float = Field(default=0.0, ge=0, description="Average tokens per run")
    token_efficiency: float = Field(default=0.0, ge=0, description="Tokens per successful generation")
    total_latency_ms: float = Field(default=0.0, ge=0, description="Total latency in milliseconds")
    avg_latency_ms: float = Field(default=0.0, ge=0, description="Average latency in milliseconds")
    rating_sum: float = Field(default=0.0, description="Sum of all ratings")
    rating_count: int = Field(default=0, ge=0, description="Number of ratings")
    avg_rating: float = Field(default=0.0, ge=0, le=5, description="Average user rating")
    confidence_interval: Optional[ConfidenceIntervalResponse] = Field(
        default=None, description="Confidence interval for success rate"
    )


class ExperimentComparisonResponse(BaseModel):
    """Schema for variant comparison."""

    success_rate_diff: float = Field(default=0.0, description="Difference in success rate (A - B)")
    success_rate_rel_diff: float = Field(default=0.0, description="Relative difference in success rate (%)")
    avg_rating_diff: float = Field(default=0.0, description="Difference in average rating (A - B)")
    avg_rating_rel_diff: float = Field(default=0.0, description="Relative difference in rating (%)")
    token_efficiency_diff: float = Field(default=0.0, description="Difference in token efficiency (A - B)")
    avg_latency_diff: float = Field(default=0.0, description="Difference in latency (A - B)")
    avg_latency_rel_diff: float = Field(default=0.0, description="Relative difference in latency (%)")


class ExperimentTimelineResponse(BaseModel):
    """Schema for experiment timeline."""

    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    started_at: Optional[str] = Field(None, description="ISO 8601 start timestamp")
    ended_at: Optional[str] = Field(None, description="ISO 8601 end timestamp")


class ExperimentResultsResponse(BaseModel):
    """Schema for experiment results."""

    experiment_id: str = Field(..., description="Experiment ID")
    name: str = Field(..., description="Experiment name")
    status: str = Field(..., description="Experiment status")
    metric: str = Field(..., description="Primary metric for comparison")
    winner: Optional[str] = Field(None, description="Winning variant (A or B)")
    min_sample_size: int = Field(default=100, ge=1, description="Minimum sample size")
    traffic_split: Dict[str, int] = Field(default_factory=dict, description="Traffic split percentage")
    variant_a: ExperimentVariantResponse = Field(..., description="Variant A metrics")
    variant_b: ExperimentVariantResponse = Field(..., description="Variant B metrics")
    comparison: ExperimentComparisonResponse = Field(..., description="Variant comparison")
    timeline: ExperimentTimelineResponse = Field(..., description="Experiment timeline")
    statistical_significance: Optional[Dict[str, Any]] = Field(
        None, description="Statistical significance analysis"
    )


class ExperimentSummaryResponse(BaseModel):
    """Schema for experiment summary (list view)."""

    id: str = Field(..., description="Experiment ID")
    name: str = Field(..., description="Experiment name")
    description: str = Field(default="", description="Experiment description")
    status: str = Field(..., description="Experiment status")
    metric: str = Field(..., description="Primary metric for comparison")
    prompt_a_id: str = Field(..., description="Variant A prompt ID")
    prompt_b_id: str = Field(..., description="Variant B prompt ID")
    traffic_split: int = Field(default=50, description="Traffic split for variant A")
    winner: Optional[str] = Field(None, description="Winning variant (A or B)")
    total_runs: int = Field(default=0, ge=0, description="Total runs across both variants")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    started_at: Optional[str] = Field(None, description="ISO 8601 start timestamp")
    ended_at: Optional[str] = Field(None, description="ISO 8601 end timestamp")


class ExperimentListResponse(BaseModel):
    """Response model for listing experiments."""

    experiments: List[ExperimentSummaryResponse] = Field(default_factory=list)
    total: int = Field(default=0, description="Total count of experiments")
    limit: int = Field(default=100, description="Page size limit")
    offset: int = Field(default=0, description="Pagination offset")


class ExperimentCreateRequest(BaseModel):
    """Request model for creating an experiment."""

    name: str = Field(..., min_length=1, max_length=200, description="Experiment name")
    description: str = Field(default="", max_length=1000, description="Experiment description")
    prompt_a_id: str = Field(..., description="Variant A prompt template ID")
    prompt_b_id: str = Field(..., description="Variant B prompt template ID")
    metric: str = Field(
        ...,
        description="Primary metric: success_rate, user_rating, token_efficiency, latency",
    )
    traffic_split: int = Field(default=50, ge=0, le=100, description="Traffic split for variant A (0-100)")
    min_sample_size: int = Field(default=100, ge=10, description="Minimum sample size per variant")
    confidence_threshold: float = Field(default=0.95, ge=0.5, le=0.99, description="Confidence threshold")

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, v: str) -> str:
        valid_metrics = {"success_rate", "user_rating", "token_efficiency", "latency"}
        if v not in valid_metrics:
            raise ValueError(f"Metric must be one of: {valid_metrics}")
        return v


class ExperimentUpdateRequest(BaseModel):
    """Request model for updating an experiment."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[str] = Field(default=None, description="New status: draft, running, paused, completed")
    min_sample_size: Optional[int] = Field(default=None, ge=10)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid_statuses = {"draft", "running", "paused", "completed", "archived"}
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v


class ExperimentRecordRequest(BaseModel):
    """Request model for recording a run result."""

    variant_id: str = Field(..., description="The variant that was used (prompt_a_id or prompt_b_id)")
    success: bool = Field(..., description="Whether the generation was successful")
    tokens: int = Field(default=0, ge=0, description="Number of tokens consumed")
    latency_ms: float = Field(default=0.0, ge=0, description="Response time in milliseconds")
    rating: Optional[float] = Field(None, ge=1.0, le=5.0, description="User rating (1-5)")


class ExperimentActionRequest(BaseModel):
    """Request model for experiment actions (start, pause, resume, complete)."""

    winner: Optional[str] = Field(None, description="Winning variant (for complete action)")


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
    # Conflict Schemas (DIR-045)
    "ConflictCreateRequest",
    "ConflictUpdateRequest",
    "ConflictResponse",
    "ConflictListResponse",
    # Plotline Schemas (DIR-049)
    "PlotlineCreateRequest",
    "PlotlineUpdateRequest",
    "PlotlineResponse",
    "PlotlineListResponse",
    "LinkSceneToPlotlineRequest",
    "UnlinkSceneFromPlotlineRequest",
    "SetScenePlotlinesRequest",
    "ScenePlotlinesResponse",
    # Foreshadowing Schemas (DIR-052)
    "ForeshadowingCreateRequest",
    "ForeshadowingUpdateRequest",
    "LinkPayoffRequest",
    "ForeshadowingResponse",
    "ForeshadowingListResponse",
    # Chapter Analysis Schemas (DIR-055/DIR-056)
    "HealthScoreEnum",
    "WarningCategoryEnum",
    "PhaseDistributionResponse",
    "WordCountEstimateResponse",
    "HealthWarningResponse",
    "TensionArcShapeResponse",
    "ChapterHealthReportResponse",
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
    # Prompt Management Schemas (BRAIN-015)
    "PromptVariableDefinition",
    "PromptVariableValue",
    "PromptSummary",
    "PromptModelConfig",
    "PromptDetailResponse",
    "PromptListResponse",
    "PromptCreateRequest",
    "PromptUpdateRequest",
    "PromptRenderRequest",
    "PromptRenderResponse",
    "PromptGenerateRequest",
    "PromptGenerateResponse",
    # Prompt Analytics Schemas (BRAIN-022B)
    "PromptAnalyticsTimePeriod",
    "PromptTimeSeriesDataPoint",
    "PromptRatingDistribution",
    "PromptAnalyticsResponse",
    "PromptAnalyticsRequest",
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
    # Prompt Experiment Schemas (BRAIN-018B)
    "ExperimentMetricsResponse",
    "ExperimentVariantResponse",
    "ExperimentComparisonResponse",
    "ExperimentTimelineResponse",
    "ExperimentResultsResponse",
    "ExperimentSummaryResponse",
    "ExperimentListResponse",
    "ExperimentCreateRequest",
    "ExperimentUpdateRequest",
    "ExperimentRecordRequest",
    "ExperimentActionRequest",
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


# === Routing Configuration Schemas ===
# BRAIN-028B: Model Routing Configuration


class TaskRoutingRuleSchema(BaseModel):
    """Routing rule for a specific task type."""

    task_type: str = Field(..., description="Task type: creative, logical, fast, cheap")
    provider: str = Field(..., description="LLM provider: openai, anthropic, gemini, ollama, mock")
    model_name: str = Field("", description="Model name (empty for provider default)")
    temperature: Optional[float] = Field(None, ge=0, le=2, description="Temperature override")
    max_tokens: Optional[int] = Field(None, ge=1, le=1000000, description="Max tokens override")
    priority: int = Field(0, ge=0, description="Rule priority (higher = more important)")
    enabled: bool = Field(True, description="Whether this rule is active")


class RoutingConstraintsSchema(BaseModel):
    """Constraints for model routing decisions."""

    max_cost_per_1m_tokens: Optional[float] = Field(None, ge=0, description="Maximum cost per 1M tokens (USD)")
    max_latency_ms: Optional[int] = Field(None, ge=0, description="Maximum acceptable latency (ms)")
    preferred_providers: List[str] = Field(default_factory=list, description="Provider preference order")
    blocked_providers: List[str] = Field(default_factory=list, description="Providers to never use")
    require_capabilities: List[str] = Field(default_factory=list, description="Required capabilities")


class CircuitBreakerRuleSchema(BaseModel):
    """Circuit breaker configuration for a specific model."""

    model_key: str = Field(..., description="Model identifier (provider:model)")
    failure_threshold: int = Field(5, ge=1, le=100, description="Failures before opening circuit")
    timeout_seconds: int = Field(60, ge=1, le=3600, description="Seconds before half-open state")
    enabled: bool = Field(True, description="Whether circuit breaker is enabled")


class RoutingConfigResponse(BaseModel):
    """Response model for routing configuration."""

    workspace_id: str = Field(..., description="Workspace identifier (empty for global)")
    scope: str = Field(..., description="Configuration scope: global or workspace")
    task_rules: List[TaskRoutingRuleSchema] = Field(default_factory=list, description="Task routing rules")
    constraints: Optional[RoutingConstraintsSchema] = Field(None, description="Routing constraints")
    circuit_breaker_rules: List[CircuitBreakerRuleSchema] = Field(default_factory=list, description="Circuit breaker rules")
    enable_circuit_breaker: bool = Field(True, description="Whether circuit breaker is enabled")
    enable_fallback: bool = Field(True, description="Whether fallback chain is enabled")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 update timestamp")
    version: int = Field(..., ge=1, description="Configuration version")


class RoutingConfigUpdateRequest(BaseModel):
    """Request model for updating routing configuration."""

    task_rules: Optional[List[TaskRoutingRuleSchema]] = Field(None, description="New task rules")
    constraints: Optional[RoutingConstraintsSchema] = Field(None, description="New constraints")
    circuit_breaker_rules: Optional[List[CircuitBreakerRuleSchema]] = Field(None, description="New circuit breaker rules")
    enable_circuit_breaker: Optional[bool] = Field(None, description="Circuit breaker setting")
    enable_fallback: Optional[bool] = Field(None, description="Fallback setting")


class RoutingConfigResetRequest(BaseModel):
    """Request model for resetting routing configuration."""

    workspace_id: str = Field(..., description="Workspace identifier (empty for global)")


class RoutingStatsResponse(BaseModel):
    """Response model for routing statistics."""

    total_decisions: int = Field(..., ge=0, description="Total routing decisions made")
    fallback_count: int = Field(..., ge=0, description="Number of times fallback was used")
    fallback_rate: float = Field(..., ge=0, le=1, description="Rate of fallback usage (0-1)")
    reason_counts: Dict[str, int] = Field(default_factory=dict, description="Count by routing reason")
    provider_counts: Dict[str, int] = Field(default_factory=dict, description="Count by provider")
    avg_routing_time_ms: float = Field(..., ge=0, description="Average routing decision time")
    open_circuits: List[Dict[str, Any]] = Field(default_factory=list, description="Currently open circuits")
    total_circuits: int = Field(..., ge=0, description="Total circuit breakers tracked")


# === Brain Settings Schemas ===
# BRAIN-033: Frontend Brain Settings


class APIKeysRequest(BaseModel):
    """Request model for updating API keys."""

    openai_key: Optional[str] = Field(None, description="OpenAI API key")
    anthropic_key: Optional[str] = Field(None, description="Anthropic API key")
    gemini_key: Optional[str] = Field(None, description="Google Gemini API key")
    ollama_base_url: Optional[str] = Field(None, description="Ollama base URL")


class APIKeysResponse(BaseModel):
    """Response model for API keys (values masked)."""

    openai_key: str = Field(..., description="Masked OpenAI API key")
    anthropic_key: str = Field(..., description="Masked Anthropic API key")
    gemini_key: str = Field(..., description="Masked Gemini API key")
    ollama_base_url: Optional[str] = Field(None, description="Ollama base URL")
    has_openai: bool = Field(default=False, description="Whether OpenAI key is set")
    has_anthropic: bool = Field(default=False, description="Whether Anthropic key is set")
    has_gemini: bool = Field(default=False, description="Whether Gemini key is set")


class RAGConfigRequest(BaseModel):
    """Request model for updating RAG configuration."""

    enabled: Optional[bool] = Field(None, description="Whether RAG is enabled")
    max_chunks: Optional[int] = Field(None, ge=1, le=50, description="Maximum chunks to retrieve")
    score_threshold: Optional[float] = Field(None, ge=0, le=1, description="Minimum relevance score")
    context_token_limit: Optional[int] = Field(None, ge=100, le=100000, description="Max tokens for context")
    include_sources: Optional[bool] = Field(None, description="Whether to include source citations")
    chunk_size: Optional[int] = Field(None, ge=100, le=10000, description="Default chunk size for ingestion")
    chunk_overlap: Optional[int] = Field(None, ge=0, le=1000, description="Chunk overlap for ingestion")
    hybrid_search_weight: Optional[float] = Field(
        None, ge=0, le=1, description="Vector search weight (1-BM25 weight)"
    )


class RAGConfigResponse(BaseModel):
    """Response model for RAG configuration."""

    enabled: bool = Field(..., description="Whether RAG is enabled")
    max_chunks: int = Field(..., description="Maximum chunks to retrieve")
    score_threshold: float = Field(..., description="Minimum relevance score")
    context_token_limit: int = Field(..., description="Max tokens for context")
    include_sources: bool = Field(..., description="Whether to include source citations")
    chunk_size: int = Field(..., description="Default chunk size for ingestion")
    chunk_overlap: int = Field(..., description="Chunk overlap for ingestion")
    hybrid_search_weight: float = Field(..., description="Vector search weight (1-BM25 weight)")


class KnowledgeBaseStatusResponse(BaseModel):
    """Response model for knowledge base status."""

    total_entries: int = Field(..., ge=0, description="Total entries in knowledge base")
    characters_count: int = Field(..., ge=0, description="Number of character entries")
    lore_count: int = Field(..., ge=0, description="Number of lore entries")
    scenes_count: int = Field(..., ge=0, description="Number of scene entries")
    plotlines_count: int = Field(..., ge=0, description="Number of plotline entries")
    last_sync: Optional[str] = Field(None, description="ISO 8601 timestamp of last sync")
    is_healthy: bool = Field(..., description="Whether the vector store is healthy")


class BrainSettingsResponse(BaseModel):
    """Combined response for all brain settings."""

    api_keys: APIKeysResponse
    rag_config: RAGConfigResponse
    knowledge_base: KnowledgeBaseStatusResponse


# BRAIN-036-02: Context Inspector Schemas


class RetrievedChunkResponse(BaseModel):
    """A retrieved chunk from the knowledge base."""

    chunk_id: str = Field(..., description="ID of the chunk")
    source_id: str = Field(..., description="ID of the source entity")
    source_type: str = Field(..., description="Type of source (CHARACTER, LORE, SCENE, etc.)")
    content: str = Field(..., description="Chunk content text")
    score: float = Field(..., ge=0, le=1, description="Relevance score (0-1)")
    token_count: int = Field(..., ge=0, description="Estimated token count")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RAGContextResponse(BaseModel):
    """Response model for RAG context retrieval."""

    query: str = Field(..., description="The query used for retrieval")
    chunks: List[RetrievedChunkResponse] = Field(..., description="Retrieved chunks")
    total_tokens: int = Field(..., ge=0, description="Total tokens in retrieved context")
    chunk_count: int = Field(..., ge=0, description="Number of chunks retrieved")
    sources: List[str] = Field(default_factory=list, description="Source references")

