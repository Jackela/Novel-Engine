"""Port definition for world generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Protocol

from src.contexts.world.domain.entities import (
    Era,
    Faction,
    Genre,
    HistoryEvent,
    Location,
    ToneType,
    WorldSetting,
)


@dataclass(frozen=True)
class WorldGenerationInput:
    """Input data for world generation.

    Attributes:
        genre: Primary genre for the world (fantasy, sci-fi, etc.)
        era: Temporal era setting (medieval, modern, etc.)
        tone: Narrative tone (dark, heroic, etc.)
        themes: List of thematic elements to incorporate
        magic_level: Level of magic/supernatural (0-10)
        technology_level: Level of technology (0-10)
        num_factions: Target number of factions to generate (1-10)
        num_locations: Target number of locations to generate (1-10)
        num_events: Target number of history events to generate (1-10)
        custom_constraints: Additional constraints or requirements
    """

    genre: Genre = Genre.FANTASY
    era: Era = Era.MEDIEVAL
    tone: ToneType = ToneType.HEROIC
    themes: List[str] = field(default_factory=lambda: ["adventure", "heroism"])
    magic_level: int = 5
    technology_level: int = 3
    num_factions: int = 3
    num_locations: int = 5
    num_events: int = 3
    custom_constraints: str | None = None

    def __post_init__(self) -> None:
        """Validate input parameters."""
        if not 0 <= self.magic_level <= 10:
            raise ValueError("magic_level must be between 0 and 10")
        if not 0 <= self.technology_level <= 10:
            raise ValueError("technology_level must be between 0 and 10")
        if not 1 <= self.num_factions <= 10:
            raise ValueError("num_factions must be between 1 and 10")
        if not 1 <= self.num_locations <= 10:
            raise ValueError("num_locations must be between 1 and 10")
        if not 1 <= self.num_events <= 10:
            raise ValueError("num_events must be between 1 and 10")


@dataclass(frozen=True)
class WorldGenerationResult:
    """Result of world generation.

    Contains the complete generated world lore including the world setting,
    factions, locations, and historical events. All entities are fully
    instantiated domain entities with relationships established.

    Attributes:
        world_setting: The generated world setting entity
        factions: List of generated faction entities
        locations: List of generated location entities
        events: List of generated history event entities
        generation_summary: Brief summary of what was generated
    """

    world_setting: WorldSetting
    factions: List[Faction] = field(default_factory=list)
    locations: List[Location] = field(default_factory=list)
    events: List[HistoryEvent] = field(default_factory=list)
    generation_summary: str = ""

    @property
    def total_entities(self) -> int:
        """Get total number of entities generated."""
        return 1 + len(self.factions) + len(self.locations) + len(self.events)


class WorldGeneratorPort(Protocol):
    """Protocol for world generators.

    Defines the interface for generating complete world lore including
    setting, factions, locations, and historical events. Implementations
    may use LLM-based generation or other approaches.
    """

    def generate(self, request: WorldGenerationInput) -> WorldGenerationResult:
        """Generate a complete world from structured input.

        Args:
            request: Input parameters for world generation

        Returns:
            WorldGenerationResult containing all generated entities
        """
        ...
