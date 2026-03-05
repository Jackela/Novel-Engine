"""Social API schemas for the Novel Engine.

This module contains schemas for social systems including:
- Relationship schemas (WORLD-003)
- Social Network Analysis schemas (CHAR-031)
- Item schemas (WORLD-008)
- Faction schemas (CHAR-035)

Created as part of PREP-002 (Operation Vanguard).
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

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
    romance: Optional[int] = Field(
        default=None, ge=0, le=100, description="Romance level"
    )


class InteractionLogSchema(BaseModel):
    """Schema for a single interaction log entry."""

    interaction_id: str = Field(..., description="Unique ID for this interaction")
    summary: str = Field(..., description="Description of the interaction")
    trust_change: int = Field(
        ..., ge=-100, le=100, description="Trust change (-100 to +100)"
    )
    romance_change: int = Field(
        ..., ge=-100, le=100, description="Romance change (-100 to +100)"
    )
    timestamp: str = Field(..., description="ISO 8601 timestamp of the interaction")


class LogInteractionRequest(BaseModel):
    """Request model for logging an interaction."""

    summary: str = Field(
        ..., min_length=1, max_length=500, description="Interaction description"
    )
    trust_change: int = Field(default=0, ge=-100, le=100, description="Trust change")
    romance_change: int = Field(
        default=0, ge=-100, le=100, description="Romance change"
    )


class RelationshipHistoryGenerationResponse(BaseModel):
    """Response model for generated relationship history.

    Contains a backstory explaining how two characters developed their current
    relationship dynamics based on trust/romance levels.
    """

    backstory: str = Field(
        ..., description="2-4 paragraph narrative explaining relationship history"
    )
    first_meeting: Optional[str] = Field(
        None, description="How the characters first met"
    )
    defining_moment: Optional[str] = Field(
        None, description="Pivotal event shaping current dynamic"
    )
    current_status: Optional[str] = Field(
        None, description="Summary of where they currently stand"
    )
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
    relationship_count: int = Field(
        default=0, ge=0, description="Total relationships (degree centrality)"
    )
    positive_count: int = Field(
        default=0, ge=0, description="Positive relationships (ally, family, romantic)"
    )
    negative_count: int = Field(
        default=0, ge=0, description="Negative relationships (enemy, rival)"
    )
    average_trust: float = Field(
        default=0.0, ge=0, le=100, description="Average trust across relationships"
    )
    average_romance: float = Field(
        default=0.0, ge=0, le=100, description="Average romance across relationships"
    )
    centrality_score: float = Field(
        default=0.0, ge=0, le=100, description="Normalized centrality (0-100)"
    )


class SocialAnalysisResponse(BaseModel):
    """Complete social network analysis result.

    Provides graph analytics for the character relationship network including
    centrality metrics, extreme characters, and network properties.
    """

    character_centralities: Dict[str, CharacterCentralitySchema] = Field(
        default_factory=dict,
        description="Mapping of character_id to their centrality metrics",
    )
    most_connected: Optional[str] = Field(
        None, description="Character ID with most relationships"
    )
    most_hated: Optional[str] = Field(
        None, description="Character ID with most negative relationships"
    )
    most_loved: Optional[str] = Field(
        None, description="Character ID with highest trust/romance average"
    )
    total_relationships: int = Field(
        default=0, ge=0, description="Total character-to-character relationships"
    )
    total_characters: int = Field(
        default=0, ge=0, description="Unique characters in the social graph"
    )
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
    effects: List[str] = Field(
        default_factory=list, description="List of effect descriptions"
    )
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
    is_leader: bool = Field(
        default=False, description="Whether this member is the faction leader"
    )


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
    members: List[FactionMemberSchema] = Field(
        default_factory=list, description="List of faction members"
    )
