"""World generation API router."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.contexts.world.application.ports.world_generator_port import (
    WorldGenerationInput,
)
from src.contexts.world.domain.entities import Era, Genre, ToneType
from src.api.error_handlers import ServiceUnavailableException
from src.contexts.world.infrastructure.generators.llm_world_generator import (
    LLMWorldGenerator,
)


router = APIRouter(tags=["world"])


# === Request/Response Models ===


class WorldGenerationRequest(BaseModel):
    """Request model for world generation."""

    genre: str = Field(default="fantasy", description="Primary genre (fantasy, sci-fi, etc.)")
    era: str = Field(default="medieval", description="Temporal era (medieval, modern, etc.)")
    tone: str = Field(default="heroic", description="Narrative tone (dark, heroic, etc.)")
    themes: List[str] = Field(
        default_factory=lambda: ["adventure", "heroism"],
        description="Thematic elements",
    )
    magic_level: int = Field(default=5, ge=0, le=10, description="Magic level (0-10)")
    technology_level: int = Field(default=3, ge=0, le=10, description="Technology level (0-10)")
    num_factions: int = Field(default=3, ge=1, le=10, description="Number of factions")
    num_locations: int = Field(default=5, ge=1, le=10, description="Number of locations")
    num_events: int = Field(default=3, ge=1, le=10, description="Number of history events")


class WorldSettingResponse(BaseModel):
    """Response model for world setting."""

    id: str
    name: str
    description: str
    genre: str
    era: str
    tone: str
    themes: List[str]
    magic_level: int
    technology_level: int


class FactionResponse(BaseModel):
    """Response model for faction."""

    id: str
    name: str
    description: str
    faction_type: str
    alignment: str
    values: List[str]
    goals: List[str]
    influence: int
    ally_count: int = 0
    enemy_count: int = 0


class LocationResponse(BaseModel):
    """Response model for location."""

    id: str
    name: str
    description: str
    location_type: str
    population: int
    controlling_faction_id: Optional[str] = None
    notable_features: List[str]
    danger_level: str


class HistoryEventResponse(BaseModel):
    """Response model for history event."""

    id: str
    name: str
    description: str
    event_type: str
    significance: int
    participants: List[str]


class WorldGenerationResponse(BaseModel):
    """Response model for world generation."""

    world_setting: WorldSettingResponse
    factions: List[FactionResponse]
    locations: List[LocationResponse]
    events: List[HistoryEventResponse]
    generation_summary: str


# === Helpers ===


def _safe_genre(value: str) -> Genre:
    """Convert string to Genre enum safely."""
    try:
        return Genre(value.lower().replace("-", "_").replace(" ", "_"))
    except ValueError:
        return Genre.FANTASY


def _safe_era(value: str) -> Era:
    """Convert string to Era enum safely."""
    try:
        return Era(value.lower().replace("-", "_").replace(" ", "_"))
    except ValueError:
        return Era.MEDIEVAL


def _safe_tone(value: str) -> ToneType:
    """Convert string to ToneType enum safely."""
    try:
        return ToneType(value.lower().replace("-", "_").replace(" ", "_"))
    except ValueError:
        return ToneType.HEROIC


# === Endpoint ===


@router.post("/world/generation", response_model=WorldGenerationResponse)
async def generate_world(request: WorldGenerationRequest) -> WorldGenerationResponse:
    """Generate a complete world with factions, locations, and history events."""
    generator = LLMWorldGenerator()

    input_data = WorldGenerationInput(
        genre=_safe_genre(request.genre),
        era=_safe_era(request.era),
        tone=_safe_tone(request.tone),
        themes=request.themes,
        magic_level=request.magic_level,
        technology_level=request.technology_level,
        num_factions=request.num_factions,
        num_locations=request.num_locations,
        num_events=request.num_events,
    )

    result = generator.generate(input_data)
    if result.world_setting.name == "Generation Failed" or result.generation_summary.startswith(
        "Error:"
    ):
        raise ServiceUnavailableException(
            service_name="World generation",
            detail=result.generation_summary,
        )

    # Convert domain entities to response models
    world_setting = WorldSettingResponse(
        id=result.world_setting.id,
        name=result.world_setting.name,
        description=result.world_setting.description,
        genre=result.world_setting.genre.value,
        era=result.world_setting.era.value,
        tone=result.world_setting.tone.value,
        themes=result.world_setting.themes,
        magic_level=result.world_setting.magic_level,
        technology_level=result.world_setting.technology_level,
    )

    factions = [
        FactionResponse(
            id=f.id,
            name=f.name,
            description=f.description,
            faction_type=f.faction_type.value,
            alignment=f.alignment.value,
            values=f.values,
            goals=f.goals,
            influence=f.influence,
            ally_count=len(f.get_allies()),
            enemy_count=len(f.get_enemies()),
        )
        for f in result.factions
    ]

    locations = [
        LocationResponse(
            id=loc.id,
            name=loc.name,
            description=loc.description,
            location_type=loc.location_type.value,
            population=loc.population,
            controlling_faction_id=loc.controlling_faction_id,
            notable_features=loc.notable_features,
            danger_level=loc.get_danger_level(),
        )
        for loc in result.locations
    ]

    events = [
        HistoryEventResponse(
            id=e.id,
            name=e.name,
            description=e.description,
            event_type=e.event_type.value,
            significance=e.significance,
            participants=list(e.participant_ids),
        )
        for e in result.events
    ]

    return WorldGenerationResponse(
        world_setting=world_setting,
        factions=factions,
        locations=locations,
        events=events,
        generation_summary=result.generation_summary,
    )
