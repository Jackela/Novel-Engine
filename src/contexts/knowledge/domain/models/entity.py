"""
Entity Models for Knowledge Graph

Defines the domain entities for the Knowledge Graph system.
These entities represent extracted information from narrative text
that will be stored and queried to build relationships.

Constitution Compliance:
- Article II (Hexagonal): Domain models independent of infrastructure
- Article IV (Domain-Driven): Rich models with behavior, not anemic

Warzone 4: AI Brain - BRAIN-029A
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class EntityType(str, Enum):
    """
    Types of entities that can be extracted from narrative text.

    Why enum:
        Provides type safety and prevents invalid entity types.

    Entity Types:
        CHARACTER: People, sentient beings, protagonists/antagonists
        LOCATION: Places, buildings, geographical areas, worlds
        ITEM: Objects, weapons, artifacts, items of significance
        EVENT: Incidents, battles, meetings, plot points
        ORGANIZATION: Groups, factions, guilds, governments
    """

    CHARACTER = "character"
    LOCATION = "location"
    ITEM = "item"
    EVENT = "event"
    ORGANIZATION = "organization"


@dataclass(frozen=True, slots=True)
class ExtractedEntity:
    """
    An entity extracted from narrative text.

    Why frozen:
        Immutable snapshot ensures extracted data doesn't change
        unexpectedly during processing.

    Attributes:
        name: Primary name of the entity
        entity_type: Type of entity (character, location, etc.)
        aliases: Alternative names or references (e.g., "The Dark Lord", "He-Who-Must-Not-Be-Named")
        description: Brief description or context about the entity
        first_appearance: Position in text where entity first appears (character offset)
        confidence: Confidence score from extraction (0.0 to 1.0)
        metadata: Additional extracted attributes (role, traits, etc.)
    """

    name: str
    entity_type: EntityType
    aliases: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""
    first_appearance: int = 0
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate entity data."""
        if not self.name or not self.name.strip():
            raise ValueError("Entity name must not be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        if self.first_appearance < 0:
            raise ValueError("first_appearance must be non-negative")

    def has_alias(self, alias: str) -> bool:
        """
        Check if the given string is an alias of this entity.

        Args:
            alias: The alias to check (case-insensitive)

        Returns:
            True if the alias matches the entity name or any alias
        """
        alias_lower = alias.lower().strip()
        return alias_lower == self.name.lower() or any(
            a.lower() == alias_lower for a in self.aliases
        )


@dataclass(frozen=True, slots=True)
class EntityMention:
    """
    A specific mention of an entity within text.

    Used for tracking co-reference resolution and building entity maps.

    Attributes:
        entity_name: The resolved entity name this mention refers to
        mention_text: The actual text as it appears in the source
        start_pos: Character position where mention starts
        end_pos: Character position where mention ends
        is_pronoun: Whether this is a pronoun reference (he, she, it, they)
    """

    entity_name: str
    mention_text: str
    start_pos: int
    end_pos: int
    is_pronoun: bool = False

    def __post_init__(self) -> None:
        """Validate mention data."""
        if not self.mention_text or not self.mention_text.strip():
            raise ValueError("Mention text must not be empty")
        if self.start_pos < 0:
            raise ValueError("start_pos must be non-negative")
        if self.end_pos < self.start_pos:
            raise ValueError("end_pos must be >= start_pos")

    @property
    def length(self) -> int:
        """Length of the mention in characters."""
        return self.end_pos - self.start_pos


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """
    Result of entity extraction from a text.

    Attributes:
        entities: All extracted entities with their metadata
        mentions: All entity mentions found in the text
        source_length: Length of the source text in characters
        timestamp: When the extraction was performed
        model_used: Which LLM model performed the extraction
        tokens_used: Tokens consumed during extraction (if available)
    """

    entities: tuple[ExtractedEntity, ...]
    mentions: tuple[EntityMention, ...]
    source_length: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    model_used: str = ""
    tokens_used: int | None = None

    def get_entities_by_type(self, entity_type: EntityType) -> tuple[ExtractedEntity, ...]:
        """
        Get all entities of a specific type.

        Args:
            entity_type: The type of entities to filter

        Returns:
            Tuple of entities matching the type
        """
        return tuple(e for e in self.entities if e.entity_type == entity_type)

    def get_entity_mentions(self, entity_name: str) -> tuple[EntityMention, ...]:
        """
        Get all mentions of a specific entity.

        Args:
            entity_name: Name of the entity (case-insensitive)

        Returns:
            Tuple of mentions for the entity
        """
        name_lower = entity_name.lower()
        return tuple(
            m for m in self.mentions if m.entity_name.lower() == name_lower
        )

    @property
    def entity_count(self) -> int:
        """Total number of unique entities extracted."""
        return len(self.entities)

    @property
    def mention_count(self) -> int:
        """Total number of entity mentions found."""
        return len(self.mentions)


# Constants for entity extraction
DEFAULT_EXTRACTION_CONFIDENCE_THRESHOLD = 0.5
DEFAULT_MAX_ENTITIES = 50
PRONOUNS = {
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "it", "its", "itself",
    "they", "them", "their", "theirs", "themselves",
}
