"""World Simulation API schemas for the Novel Engine.

This module contains schemas for world simulation including:
- History Event schemas (SIM-006)
- Calendar schemas
- Diplomacy schemas
- Simulation schemas
- Snapshot schemas
- Rumor schemas

Created as part of PREP-002 (Operation Vanguard).
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# === History Event Schemas (SIM-006) ===


class HistoryEventResponse(BaseModel):
    """Response model for a historical event."""

    id: str = Field(..., description="Unique identifier for the event")
    name: str = Field(..., description="Short name/title of the event")
    description: str = Field(..., description="Detailed description of what happened")
    event_type: str = Field(..., description="Classification of the event type")
    significance: str = Field(..., description="Level of historical significance")
    outcome: str = Field(..., description="General outcome of the event")
    date_description: str = Field(..., description="Narrative date description")
    duration_description: Optional[str] = Field(
        None, description="How long the event lasted"
    )
    location_ids: List[str] = Field(
        default_factory=list, description="IDs of locations where event occurred"
    )
    faction_ids: List[str] = Field(
        default_factory=list, description="IDs of factions involved"
    )
    key_figures: List[str] = Field(
        default_factory=list, description="Names of key individuals involved"
    )
    causes: List[str] = Field(default_factory=list, description="What led to this event")
    consequences: List[str] = Field(
        default_factory=list, description="What resulted from this event"
    )
    preceding_event_ids: List[str] = Field(
        default_factory=list, description="IDs of events that directly preceded this one"
    )
    following_event_ids: List[str] = Field(
        default_factory=list, description="IDs of events that directly followed this one"
    )
    related_event_ids: List[str] = Field(
        default_factory=list, description="IDs of related but not directly connected events"
    )
    is_secret: bool = Field(False, description="Whether this event is hidden from common knowledge")
    sources: List[str] = Field(
        default_factory=list, description="Where knowledge of this event comes from"
    )
    narrative_importance: int = Field(
        50, ge=0, le=100, description="How important this is to the story (0-100)"
    )
    impact_scope: Optional[str] = Field(
        None, description="Geographic scope of the event's impact (local, regional, global)"
    )
    affected_faction_ids: Optional[List[str]] = Field(
        None, description="IDs of factions directly affected (distinct from involved)"
    )
    affected_location_ids: Optional[List[str]] = Field(
        None, description="IDs of locations directly affected (distinct from where occurred)"
    )
    structured_date: Optional[Dict[str, Any]] = Field(
        None, description="Structured calendar date for simulation events"
    )
    created_at: Optional[str] = Field(None, description="ISO 8601 timestamp when event was created")
    updated_at: Optional[str] = Field(None, description="ISO 8601 timestamp when event was last updated")


class CreateEventRequest(BaseModel):
    """Request model for creating a new historical event."""

    name: str = Field(..., min_length=1, max_length=300, description="Short name/title of the event")
    description: str = Field(..., min_length=1, description="Detailed description of what happened")
    event_type: str = Field(
        default="political",
        description="Classification of the event type (e.g., war, battle, treaty, discovery)",
    )
    significance: str = Field(
        default="moderate",
        description="Level of historical significance (trivial, minor, moderate, major, world_changing, legendary)",
    )
    outcome: str = Field(
        default="neutral",
        description="General outcome of the event (positive, negative, neutral, mixed, unknown)",
    )
    date_description: str = Field(..., min_length=1, description="Narrative date description")
    duration_description: Optional[str] = Field(None, description="How long the event lasted")
    location_ids: Optional[List[str]] = Field(None, description="IDs of locations where event occurred")
    faction_ids: Optional[List[str]] = Field(None, description="IDs of factions involved")
    key_figures: Optional[List[str]] = Field(None, description="Names of key individuals involved")
    causes: Optional[List[str]] = Field(None, description="What led to this event")
    consequences: Optional[List[str]] = Field(None, description="What resulted from this event")
    preceding_event_ids: Optional[List[str]] = Field(
        None, description="IDs of events that directly preceded this one"
    )
    following_event_ids: Optional[List[str]] = Field(
        None, description="IDs of events that directly followed this one"
    )
    related_event_ids: Optional[List[str]] = Field(
        None, description="IDs of related but not directly connected events"
    )
    is_secret: bool = Field(False, description="Whether this event is hidden from common knowledge")
    sources: Optional[List[str]] = Field(
        None, description="Where knowledge of this event comes from"
    )
    narrative_importance: int = Field(
        default=50, ge=0, le=100, description="How important this is to the story (0-100)"
    )
    impact_scope: Optional[str] = Field(
        None, description="Geographic scope of the event's impact (local, regional, global)"
    )
    affected_faction_ids: Optional[List[str]] = Field(
        None, description="IDs of factions directly affected (distinct from involved)"
    )
    affected_location_ids: Optional[List[str]] = Field(
        None, description="IDs of locations directly affected (distinct from where occurred)"
    )
    structured_date: Optional[Dict[str, Any]] = Field(
        None, description="Structured calendar date for simulation events"
    )


class EventFilterParams(BaseModel):
    """Query parameters for filtering historical events."""

    event_type: Optional[str] = Field(None, description="Filter by event type")
    impact_scope: Optional[str] = Field(None, description="Filter by impact scope (local, regional, global)")
    from_date: Optional[str] = Field(None, description="Filter events from this date (ISO format or narrative)")
    to_date: Optional[str] = Field(None, description="Filter events to this date (ISO format or narrative)")
    faction_id: Optional[str] = Field(None, description="Filter by faction ID involved")
    location_id: Optional[str] = Field(None, description="Filter by location ID")
    is_secret: Optional[bool] = Field(None, description="Filter by secret status")
    page: int = Field(default=1, ge=1, description="Page number for pagination")
    page_size: int = Field(
        default=20, ge=1, le=100, description="Number of items per page (1-100)"
    )


class EventListResponse(BaseModel):
    """Response model for paginated list of historical events."""

    events: List[HistoryEventResponse] = Field(
        default_factory=list, description="List of historical events"
    )
    total_count: int = Field(..., description="Total number of events matching the filter")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


# === Calendar Schemas ===


class CalendarResponse(BaseModel):
    """Response model for calendar state.

    Used by both calendar router and simulation router for consistent
    calendar data representation.
    """

    year: int = Field(description="Current year in the world calendar")
    month: int = Field(description="Current month (1 to months_per_year)")
    day: int = Field(description="Current day (1 to days_per_month)")
    era_name: str = Field(description="Name of the current era")
    formatted_date: str = Field(description="Human-readable formatted date string")
    days_per_month: int = Field(default=30, description="Number of days per month")
    months_per_year: int = Field(default=12, description="Number of months per year")


class AdvanceCalendarRequest(BaseModel):
    """Request model for advancing the calendar."""

    days: int = Field(
        default=1, ge=1, le=365, description="Number of days to advance (1-365)"
    )


class WorldTimeResponse(BaseModel):
    """Response model for world time state."""

    year: int = Field(description="Current year in the world calendar")
    month: int = Field(description="Current month (1-12)")
    day: int = Field(description="Current day (1-30)")
    era_name: str = Field(description="Name of the current era")
    display_string: str = Field(description="Human-readable formatted date string")


class AdvanceTimeRequest(BaseModel):
    """Request model for advancing world time."""

    days: int = Field(default=1, ge=1, le=365, description="Number of days to advance (1-365)")


class CalendarData(BaseModel):
    """Calendar data embedded in other responses.

    Lightweight calendar representation for nested use in snapshots,
    rumors, and other entities.
    """

    year: int
    month: int
    day: int
    era_name: str
    formatted: str


# === Diplomacy Schemas ===


class DiplomacyMatrixResponse(BaseModel):
    """Response model for full diplomacy matrix."""

    world_id: str = Field(description="World ID for this diplomacy matrix")
    matrix: Dict[str, Dict[str, str]] = Field(
        description="2D matrix of faction relationships"
    )
    factions: List[str] = Field(description="List of all faction IDs in the matrix")


class FactionDiplomacyResponse(BaseModel):
    """Response model for a single faction's diplomatic relations."""

    faction_id: str = Field(description="The faction's ID")
    allies: List[str] = Field(description="List of allied faction IDs")
    enemies: List[str] = Field(description="List of hostile/at war faction IDs")
    neutral: List[str] = Field(description="List of neutral faction IDs")


class SetRelationRequest(BaseModel):
    """Request model for setting a diplomatic relation."""

    status: str = Field(
        description="Diplomatic status to set (allied, friendly, neutral, cold, hostile, at_war)"
    )


# === Simulation Schemas ===


class SimulateRequest(BaseModel):
    """Request model for simulation operations."""

    days: int = Field(
        default=1,
        ge=1,
        le=365,
        description="Number of days to simulate (1-365)",
    )


class ResourceChangesResponse(BaseModel):
    """Response model for resource changes during simulation."""

    wealth_delta: int
    military_delta: int
    influence_delta: int
    has_changes: bool


class DiplomacyChangeResponse(BaseModel):
    """Response model for diplomacy changes during simulation."""

    faction_a: str
    faction_b: str
    status_before: str
    status_after: str
    is_significant: bool


class SimulationTickSummary(BaseModel):
    """Summary model for simulation tick history."""

    tick_id: str
    days_advanced: int
    events_count: int
    created_at: str


class SimulationTickResponse(BaseModel):
    """Response model for a complete simulation tick."""

    tick_id: str
    world_id: str
    calendar_before: Optional[CalendarResponse]
    calendar_after: Optional[CalendarResponse]
    days_advanced: int
    events_generated: List[str]
    resource_changes: Dict[str, ResourceChangesResponse]
    diplomacy_changes: List[DiplomacyChangeResponse]
    created_at: str


class SimulationHistoryResponse(BaseModel):
    """Response model for simulation history."""

    ticks: List[SimulationTickSummary]
    total: int


class SimulationStatusResponse(BaseModel):
    """Response model for async simulation status."""

    tick_id: str
    status: str
    status_url: str
    message: str


# === Snapshot Schemas ===


class CreateSnapshotRequest(BaseModel):
    """Request model for creating a snapshot."""

    description: Optional[str] = Field(
        None, max_length=200, description="Optional description for the snapshot"
    )
    tick_number: int = Field(
        default=0, ge=0, description="Sequential tick number for the snapshot"
    )
    state_json: str = Field(
        default="{}", description="JSON-serialized world state data"
    )


class SnapshotSummary(BaseModel):
    """Summary model for snapshot list."""

    snapshot_id: str
    tick_number: int
    description: str
    created_at: str


class SnapshotResponse(BaseModel):
    """Response model for a snapshot."""

    snapshot_id: str
    world_id: str
    calendar: Optional[CalendarData]
    tick_number: int
    description: str
    created_at: str
    size_bytes: int


class SnapshotListResponse(BaseModel):
    """Response model for list of snapshots."""

    snapshots: List[SnapshotSummary]
    total: int


class RestoreSnapshotResponse(BaseModel):
    """Response model for snapshot restoration."""

    snapshot_id: str
    world_id: str
    restored: bool
    message: str


# === Rumor Schemas ===


class SortByEnum(str, Enum):
    """Sort options for rumors."""

    RECENT = "recent"
    RELIABLE = "reliable"
    SPREAD = "spread"


class RumorResponse(BaseModel):
    """Response model for a single rumor."""

    rumor_id: str
    content: str
    truth_value: int = Field(ge=0, le=100)
    origin_type: str
    source_event_id: Optional[str] = None
    origin_location_id: str
    current_locations: List[str]
    created_date: Optional[CalendarData]
    spread_count: int
    veracity_label: str


class RumorListResponse(BaseModel):
    """Response model for list of rumors."""

    rumors: List[RumorResponse]
    total: int


# === World State Schemas (PREP-010) ===


class TerritorySummary(BaseModel):
    """Summary of a territory with control information."""

    location_id: str = Field(description="Unique identifier for the location")
    name: str = Field(description="Name of the location/territory")
    location_type: str = Field(description="Type of location (kingdom, city, fortress, etc.)")
    controlling_faction_id: Optional[str] = Field(
        None, description="ID of faction controlling this territory"
    )
    contested_by: List[str] = Field(
        default_factory=list, description="Factions contesting control"
    )
    territory_value: int = Field(
        default=0, ge=0, le=100, description="Strategic importance (0-100)"
    )
    infrastructure_level: int = Field(
        default=0, ge=0, le=100, description="Development level (0-100)"
    )
    population: int = Field(default=0, description="Population count")
    resource_types: List[str] = Field(
        default_factory=list, description="Types of resources produced"
    )


class TerritoriesResponse(BaseModel):
    """Response model for world territories."""

    world_id: str = Field(description="World ID")
    territories: List[TerritorySummary] = Field(description="List of territories")
    total_count: int = Field(description="Total number of territories")
    controlled_count: int = Field(description="Number of controlled territories")
    contested_count: int = Field(description="Number of contested territories")


class FactionResourceSummary(BaseModel):
    """Summary of a faction's resources."""

    faction_id: str = Field(description="Faction ID")
    faction_name: str = Field(description="Faction name")
    resources: Dict[str, int] = Field(
        default_factory=dict, description="Resource type -> amount"
    )
    total_territories: int = Field(description="Number of controlled territories")
    total_population: int = Field(description="Total population across territories")


class WorldResourcesResponse(BaseModel):
    """Response model for world resources summary."""

    world_id: str = Field(description="World ID")
    factions: List[FactionResourceSummary] = Field(
        description="Resource summary per faction"
    )
    total_resources: Dict[str, int] = Field(
        default_factory=dict, description="Total resources in world"
    )
    timestamp: str = Field(description="ISO 8601 timestamp of snapshot")


class PactSummary(BaseModel):
    """Summary of a diplomatic pact."""

    pact_id: str = Field(description="Pact ID")
    faction_a_id: str = Field(description="First faction ID")
    faction_b_id: str = Field(description="Second faction ID")
    pact_type: str = Field(description="Type of pact (alliance, trade, etc.)")
    signed_date: Optional[str] = Field(None, description="When pact was signed")
    expires_date: Optional[str] = Field(None, description="When pact expires")
    is_active: bool = Field(description="Whether pact is currently active")


class DiplomacyMatrixDetailResponse(BaseModel):
    """Detailed response model for diplomacy matrix with pacts."""

    world_id: str = Field(description="World ID for this diplomacy matrix")
    matrix: Dict[str, Dict[str, str]] = Field(
        description="2D matrix of faction relationships"
    )
    factions: List[str] = Field(description="List of all faction IDs in the matrix")
    active_pacts: List[PactSummary] = Field(
        default_factory=list, description="List of active diplomatic pacts"
    )
