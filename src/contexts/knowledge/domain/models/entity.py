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

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


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


class RelationshipType(str, Enum):
    """
    Types of relationships between entities in the knowledge graph.

    Why enum:
        Provides type safety and enables semantic querying of relationships.

    Relationship Types:
        KNOWS: Entities are acquainted or aware of each other
        KILLED: One entity caused the death of another
        LOVES: Romantic or familial affection
        HATES: Strong dislike or enmity
        PARENT_OF: Familial parent-child relationship
        CHILD_OF: Familial child-parent relationship (inverse of PARENT_OF)
        MEMBER_OF: Entity belongs to an organization or group
        LEADS: Entity leads or commands another
        SERVES: Entity serves or follows another
        OWNS: Entity possesses another
        LOCATED_AT: Entity is found at a location
        OCCURRED_AT: Event took place at a location
        PARTICIPATED_IN: Entity took part in an event
        ALLIED_WITH: Entities are allies or partners
        ENEMY_OF: Entities are opposed or at war
        MENTORED: One entity taught or guided another
        OTHER: Catch-all for unspecified relationships
    """

    KNOWS = "knows"
    KILLED = "killed"
    LOVES = "loves"
    HATES = "hates"
    PARENT_OF = "parent_of"
    CHILD_OF = "child_of"
    MEMBER_OF = "member_of"
    LEADS = "leads"
    SERVES = "serves"
    OWNS = "owns"
    LOCATED_AT = "located_at"
    OCCURRED_AT = "occurred_at"
    PARTICIPATED_IN = "participated_in"
    ALLIED_WITH = "allied_with"
    ENEMY_OF = "enemy_of"
    MENTORED = "mentored"
    OTHER = "other"


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


@dataclass(frozen=True, slots=True)
class Relationship:
    """
    A relationship between two entities in the knowledge graph.

    Represents a directed relationship from a source entity to a target entity,
    with context about where this relationship was established.

    Why frozen:
        Immutable snapshot ensures relationship data doesn't change during processing.

    Attributes:
        source: Name of the source entity (the subject of the relationship)
        target: Name of the target entity (the object of the relationship)
        relationship_type: Type of relationship from RelationshipType enum
        context: Text snippet providing context for this relationship
        strength: Confidence score 0.0-1.0, or 1.0 if explicitly stated
        bidirectional: Whether the relationship naturally works both ways (e.g., KNOWS)
        temporal_marker: Optional time reference (e.g., "during chapter 1", "before the battle")
        metadata: Additional attributes about the relationship
    """

    source: str
    target: str
    relationship_type: RelationshipType
    context: str = ""
    strength: float = 1.0
    bidirectional: bool = False
    temporal_marker: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate relationship data."""
        if not self.source or not self.source.strip():
            raise ValueError("Source entity name must not be empty")
        if not self.target or not self.target.strip():
            raise ValueError("Target entity name must not be empty")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("Strength must be between 0.0 and 1.0")

    @property
    def is_self_relationship(self) -> bool:
        """Check if this is a self-referential relationship."""
        return self.source.lower().strip() == self.target.lower().strip()

    def invert(self) -> Relationship:
        """
        Create an inverted version of this relationship.

        Swaps source and target, and adjusts the relationship type
        to its inverse if one exists (e.g., PARENT_OF -> CHILD_OF).

        Returns:
            New Relationship with inverted direction
        """
        inverted_type = _INVERSE_RELATIONSHIP_MAP.get(self.relationship_type)

        if inverted_type:
            return Relationship(
                source=self.target,
                target=self.source,
                relationship_type=inverted_type,
                context=self.context,
                strength=self.strength,
                bidirectional=self.bidirectional,
                temporal_marker=self.temporal_marker,
                metadata=self.metadata.copy(),
            )
        else:
            # No inverse type, just swap directions
            return Relationship(
                source=self.target,
                target=self.source,
                relationship_type=self.relationship_type,
                context=self.context,
                strength=self.strength,
                bidirectional=self.bidirectional,
                temporal_marker=self.temporal_marker,
                metadata=self.metadata.copy(),
            )


@dataclass(frozen=True, slots=True)
class ExtractionResultWithRelationships(ExtractionResult):
    """
    Extended extraction result that includes relationships between entities.

    Attributes:
        relationships: All relationships extracted between entities
    """

    relationships: tuple[Relationship, ...] = field(default_factory=tuple)

    def get_relationships_for_entity(
        self, entity_name: str
    ) -> tuple[Relationship, ...]:
        """
        Get all relationships involving a specific entity.

        Args:
            entity_name: Name of the entity (case-insensitive)

        Returns:
            Tuple of relationships where the entity is source or target
        """
        name_lower = entity_name.lower()
        return tuple(
            r for r in self.relationships
            if r.source.lower() == name_lower or r.target.lower() == name_lower
        )

    def get_relationships_by_type(
        self, relationship_type: RelationshipType
    ) -> tuple[Relationship, ...]:
        """
        Get all relationships of a specific type.

        Args:
            relationship_type: The type of relationships to filter

        Returns:
            Tuple of relationships matching the type
        """
        return tuple(
            r for r in self.relationships
            if r.relationship_type == relationship_type
        )

    def find_relationship(
        self,
        source: str,
        target: str,
        relationship_type: RelationshipType | None = None,
    ) -> tuple[Relationship, ...]:
        """
        Find relationships between two specific entities.

        Args:
            source: Source entity name (case-insensitive)
            target: Target entity name (case-insensitive)
            relationship_type: Optional filter by relationship type

        Returns:
            Tuple of matching relationships
        """
        source_lower = source.lower()
        target_lower = target.lower()

        matches = (
            r for r in self.relationships
            if r.source.lower() == source_lower and r.target.lower() == target_lower
        )

        if relationship_type:
            matches = (r for r in matches if r.relationship_type == relationship_type)

        return tuple(matches)

    @property
    def relationship_count(self) -> int:
        """Total number of relationships extracted."""
        return len(self.relationships)

    def normalize_bidirectional(self) -> "ExtractionResultWithRelationships":
        """
        Normalize bidirectional relationships by adding inverse relationships.

        For relationships marked as bidirectional or of inherently symmetric types,
        ensures that both directions exist in the result. If a bidirectional
        relationship exists A->B but not B->A, the inverse is added.

        Returns:
            New ExtractionResultWithRelationships with normalized relationships
        """
        existing_pairs: set[tuple[str, str, RelationshipType]] = set()
        normalized: list[Relationship] = list(self.relationships)

        # Track existing relationships (source, target, type)
        for rel in self.relationships:
            key = (rel.source.lower(), rel.target.lower(), rel.relationship_type)
            existing_pairs.add(key)

        # Add missing inverse relationships for bidirectional ones
        for rel in self.relationships:
            should_add_inverse = rel.bidirectional or is_naturally_bidirectional(
                rel.relationship_type
            )

            if should_add_inverse:
                inverse_key = (
                    rel.target.lower(),
                    rel.source.lower(),
                    rel.relationship_type,
                )

                # For symmetric types, check both directions
                # For non-symmetric with bidirectional=True, check for inverse type
                if is_naturally_bidirectional(rel.relationship_type):
                    # Symmetric relationship - both directions should exist
                    if inverse_key not in existing_pairs:
                        inverted = rel.invert()
                        normalized.append(inverted)
                        existing_pairs.add(inverse_key)
                elif rel.bidirectional:
                    # Check if inverse relationship exists (with inverse type)
                    inverse_type = _INVERSE_RELATIONSHIP_MAP.get(rel.relationship_type)
                    if inverse_type:
                        inverse_with_type_key = (
                            rel.target.lower(),
                            rel.source.lower(),
                            inverse_type,
                        )
                        if inverse_with_type_key not in existing_pairs:
                            inverted = rel.invert()
                            normalized.append(inverted)
                            existing_pairs.add(inverse_with_type_key)

        return dataclasses.replace(
            self,
            relationships=tuple(normalized),
        )

    def filter_by_temporal(
        self,
        temporal_marker: str | None = None,
        contains_marker: str | None = None,
    ) -> "ExtractionResultWithRelationships":
        """
        Filter relationships by temporal marker.

        Args:
            temporal_marker: Exact temporal marker to match (e.g., "during chapter 1")
            contains_marker: Substring to match in temporal markers (e.g., "chapter")

        Returns:
            New ExtractionResultWithRelationships with filtered relationships

        Examples:
            >>> # Get relationships during chapter 1
            >>> result.filter_by_temporal(temporal_marker="during chapter 1")
            >>> # Get all relationships mentioning "chapter"
            >>> result.filter_by_temporal(contains_marker="chapter")
            >>> # Get relationships without temporal info
            >>> result.filter_by_temporal(temporal_marker="")
        """
        if temporal_marker is not None:
            # Exact match (empty string matches relationships without temporal info)
            filtered = tuple(
                r for r in self.relationships
                if r.temporal_marker == temporal_marker
            )
        elif contains_marker is not None:
            # Substring match
            marker_lower = contains_marker.lower()
            filtered = tuple(
                r for r in self.relationships
                if marker_lower in r.temporal_marker.lower()
            )
        else:
            # No filter
            filtered = self.relationships

        return dataclasses.replace(
            self,
            relationships=filtered,
        )

    def get_temporal_markers(self) -> tuple[str, ...]:
        """
        Get all unique temporal markers from relationships.

        Returns:
            Tuple of unique temporal markers
        """
        markers = {r.temporal_marker for r in self.relationships if r.temporal_marker}
        return tuple(sorted(markers))

    def get_relationships_at_time(
        self,
        time_reference: str,
    ) -> tuple[Relationship, ...]:
        """
        Get relationships valid at a specific time reference.

        Matches relationships whose temporal_marker contains the time reference,
        or relationships without temporal information (assumed always valid).

        Args:
            time_reference: Time reference to match (e.g., "chapter 1", "before the battle")

        Returns:
            Tuple of relationships valid at the specified time
        """
        time_lower = time_reference.lower()
        return tuple(
            r for r in self.relationships
            if not r.temporal_marker or time_lower in r.temporal_marker.lower()
        )

    def has_temporal_relationship(self, entity_name: str) -> bool:
        """
        Check if an entity has any relationships with temporal information.

        Args:
            entity_name: Name of the entity (case-insensitive)

        Returns:
            True if the entity has relationships with temporal markers
        """
        name_lower = entity_name.lower()
        return any(
            (r.source.lower() == name_lower or r.target.lower() == name_lower)
            and r.temporal_marker
            for r in self.relationships
        )


# Mapping of relationship types to their inverses
_INVERSE_RELATIONSHIP_MAP: dict[RelationshipType, RelationshipType] = {
    RelationshipType.PARENT_OF: RelationshipType.CHILD_OF,
    RelationshipType.CHILD_OF: RelationshipType.PARENT_OF,
    RelationshipType.LEADS: RelationshipType.SERVES,
    RelationshipType.SERVES: RelationshipType.LEADS,
    RelationshipType.MENTORED: RelationshipType.CHILD_OF,  # Approximation
    RelationshipType.LOCATED_AT: RelationshipType.LOCATED_AT,  # Symmetric
    RelationshipType.KNOWS: RelationshipType.KNOWS,  # Symmetric
    RelationshipType.LOVES: RelationshipType.LOVES,  # Potentially symmetric
    RelationshipType.HATES: RelationshipType.HATES,  # Potentially symmetric
    RelationshipType.ALLIED_WITH: RelationshipType.ALLIED_WITH,  # Symmetric
    RelationshipType.ENEMY_OF: RelationshipType.ENEMY_OF,  # Symmetric
}

# Relationship types that are inherently bidirectional (symmetric)
_BIDIRECTIONAL_RELATIONSHIP_TYPES: frozenset[RelationshipType] = frozenset([
    RelationshipType.KNOWS,
    RelationshipType.LOVES,
    RelationshipType.HATES,
    RelationshipType.ALLIED_WITH,
    RelationshipType.ENEMY_OF,
    RelationshipType.LOCATED_AT,
])


def is_naturally_bidirectional(relationship_type: RelationshipType) -> bool:
    """
    Check if a relationship type is naturally bidirectional.

    Args:
        relationship_type: The relationship type to check

    Returns:
        True if the relationship type is inherently symmetric/bidirectional
    """
    return relationship_type in _BIDIRECTIONAL_RELATIONSHIP_TYPES

# Constants for entity extraction
DEFAULT_EXTRACTION_CONFIDENCE_THRESHOLD = 0.5
DEFAULT_MAX_ENTITIES = 50
PRONOUNS = {
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "it", "its", "itself",
    "they", "them", "their", "theirs", "themselves",
}
