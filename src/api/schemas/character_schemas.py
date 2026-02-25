"""Character-related schemas for the Novel Engine API.

This module contains all schemas related to character management,
including psychology, memory, goals, dialogue generation, and profile generation.

Extracted from schemas.py as part of PREP-001 (Operation Vanguard).
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, JsonValue, field_validator


# === Character Psychology Schemas ===


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


# === Dialogue Generation Schemas ===


class DialogueGenerationRequest(BaseModel):
    """Request model for generating character dialogue.

    Uses character psychology, traits, and speaking style to generate
    authentic dialogue that sounds like the character would naturally speak.
    """

    character_id: str = Field(
        ..., description="ID of the character to generate dialogue for"
    )
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
        None,
        description="Optional psychology override if not using stored character data",
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


# === Character Memory Schemas ===


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
    importance: int = Field(..., ge=1, le=10, description="Importance score (1-10)")
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
    importance: int = Field(..., ge=1, le=10, description="Importance score (1-10)")
    tags: List[str] = Field(
        default_factory=list, description="Categorization tags for retrieval"
    )


class CharacterMemoryUpdateRequest(BaseModel):
    """Request to update a character memory (limited updates allowed)."""

    importance: Optional[int] = Field(
        None, ge=1, le=10, description="Updated importance score"
    )
    tags: Optional[List[str]] = Field(None, description="Updated tags")


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
    status: str = Field(..., description="Goal status: ACTIVE, COMPLETED, or FAILED")
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


# === Character Summary and List Schemas ===


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
    # SIM-020: Character location tracking
    current_location_id: Optional[str] = None
    # SIM-019: Character life cycle
    is_deceased: bool = False


class CharactersListResponse(BaseModel):
    characters: List[CharacterSummary]


# === Character Detail Schema ===


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


# === Character Generation Schemas ===


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


# === Character Profile Generation Schemas ===


class CharacterProfileGenerationRequest(BaseModel):
    """Request model for character profile generation.

    This generates a detailed character profile with aliases, archetype, traits,
    appearance, backstory, etc. using LLM or mock generator.
    """

    name: str = Field(
        ..., min_length=1, max_length=100, description="Character's primary name"
    )
    archetype: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Character archetype (e.g., Hero, Villain, Mentor)",
    )
    context: Optional[str] = Field(
        None,
        max_length=500,
        description="Additional context about the character's world or background",
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
