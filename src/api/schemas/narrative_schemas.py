"""Narrative-related schemas for the Novel Engine API.

This module contains all schemas related to narrative generation, structure,
and content management including stories, chapters, scenes, beats, plotlines,
conflicts, pacing analysis, foreshadowing, and critique.

Extracted from schemas.py as part of PREP-001 (Operation Vanguard).
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, JsonValue

# Import for forward reference in SceneGenerationRequest
from src.api.schemas.character_schemas import CharacterGenerationResponse


# === Narrative Data Schemas ===


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


# === Scene Generation Schemas ===


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
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Flexible metadata including smart tags"
    )
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

    content: str = Field(
        default="", max_length=10000, description="Beat narrative text"
    )
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
    rationale: Optional[str] = Field(
        None, description="AI's explanation for this suggestion"
    )


class BeatSuggestionResponse(BaseModel):
    """Response model for AI beat suggestions.

    Contains 3 AI-generated beat suggestions that could follow
    the current sequence.
    """

    scene_id: str = Field(..., description="Scene UUID")
    suggestions: List[BeatSuggestion] = Field(
        default_factory=list,
        min_length=0,
        max_length=3,
        description="3 suggested beats",
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

    issue_type: str = Field(
        ..., description="Category: monotonous_tension, tension_spike, etc."
    )
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
    tension_range: List[int] = Field(
        ..., min_length=2, max_length=2, description="[min, max] tension"
    )
    energy_range: List[int] = Field(
        ..., min_length=2, max_length=2, description="[min, max] energy"
    )


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
    description: Optional[str] = Field(default=None, min_length=1, max_length=2000)
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
    color: str = Field(
        ...,
        pattern=r"^#[0-9a-fA-F]{3,6}$",
        description="Hex color code (e.g., #ff5733)",
    )
    description: str = Field(
        default="", max_length=2000, description="Plotline description"
    )
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
    scene_count: int = Field(
        default=0, description="Number of scenes linked to this plotline"
    )
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
    plotline_ids: List[str] = Field(
        default_factory=list, description="Associated plotline UUIDs"
    )


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
    inciting_incident: int = Field(
        ..., description="Number of scenes in INCITING_INCIDENT phase"
    )
    rising_action: int = Field(
        ..., description="Number of scenes in RISING_ACTION phase"
    )
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
    severity: str = Field(
        ..., description="Issue severity (low, medium, high, critical)"
    )
    affected_scenes: List[str] = Field(
        default_factory=list, description="Scene UUIDs involved"
    )
    recommendation: str = Field(
        ..., description="Actionable suggestion for fixing the issue"
    )


class TensionArcShapeResponse(BaseModel):
    """Analysis of the tension arc shape."""

    shape_type: str = Field(..., description="Descriptive name of the arc shape")
    starts_at: int = Field(..., description="Opening tension level")
    peaks_at: int = Field(..., description="Maximum tension level")
    ends_at: int = Field(..., description="Closing tension level")
    has_clear_climax: bool = Field(
        ..., description="Whether there's a distinct tension peak"
    )
    is_monotonic: bool = Field(..., description="Whether tension stays flat throughout")


class ChapterHealthReportResponse(BaseModel):
    """Complete structural health analysis for a chapter."""

    chapter_id: str = Field(..., description="Chapter UUID")
    health_score: str = Field(..., description="Overall health classification")
    phase_distribution: PhaseDistributionResponse = Field(
        ..., description="Scene counts per story phase"
    )
    word_count: WordCountEstimateResponse = Field(
        ..., description="Estimated word count metrics"
    )
    total_scenes: int = Field(..., description="Number of scenes in the chapter")
    total_beats: int = Field(..., description="Total number of beats across all scenes")
    tension_arc: TensionArcShapeResponse = Field(
        ..., description="Analysis of tension arc shape"
    )
    warnings: List[HealthWarningResponse] = Field(
        default_factory=list, description="Detected structural issues"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Improvement suggestions"
    )


# ============ Scene Critique Schemas (DIR-057/DIR-058) ============


class CritiqueCategoryScoreResponse(BaseModel):
    """Category-specific critique score with issues and suggestions."""

    category: str = Field(
        ..., description="Quality dimension: pacing, voice, showing, dialogue"
    )
    score: int = Field(
        ..., ge=1, le=10, description="Score from 1-10 for this category"
    )
    issues: List[str] = Field(
        default_factory=list, description="Specific problems identified"
    )
    suggestions: List[str] = Field(
        default_factory=list, description="Actionable improvements"
    )


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

    overall_score: int = Field(
        ..., ge=1, le=10, description="Overall quality score (1-10)"
    )
    category_scores: List[CritiqueCategoryScoreResponse] = Field(
        default_factory=list, description="Evaluations by category"
    )
    highlights: List[str] = Field(
        default_factory=list, description="What works well in the scene"
    )
    summary: str = Field(..., description="Brief 2-3 sentence assessment")
    error: Optional[str] = Field(None, description="Error message if critique failed")


# ============ Foreshadowing Schemas (DIR-052) ============


class ForeshadowingCreateRequest(BaseModel):
    """Request model for creating a new foreshadowing.

    Foreshadowing represents a narrative setup that will be paid off later.
    This enforces Chekhov's Gun: every setup must have a payoff.
    """

    setup_scene_id: str = Field(..., description="Scene UUID where setup occurs")
    description: str = Field(
        ..., min_length=1, max_length=2000, description="Description of the setup"
    )
    status: str = Field(
        default="planted",
        description="Status: 'planted', 'paid_off', 'abandoned'",
    )


class ForeshadowingUpdateRequest(BaseModel):
    """Request model for updating a foreshadowing."""

    description: str = Field(
        default="", max_length=2000, description="Updated description"
    )
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
    payoff_scene_id: Optional[str] = Field(
        None, description="Payoff scene UUID (if paid off)"
    )
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
