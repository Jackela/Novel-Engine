#!/usr/bin/env python3
"""Relationship Domain Entity.

This module defines the Relationship entity which represents connections
between world entities (characters, factions, locations). Relationships
form the basis of the World Knowledge Graph, enabling rich narrative
interconnections.

Typical usage example:
    >>> from src.contexts.world.domain.entities import Relationship, EntityType, RelationshipType
    >>> friendship = Relationship(
    ...     source_id="char-001",
    ...     source_type=EntityType.CHARACTER,
    ...     target_id="char-002",
    ...     target_type=EntityType.CHARACTER,
    ...     relationship_type=RelationshipType.ALLY,
    ...     description="Childhood friends who grew up together",
    ...     strength=80
    ... )
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .entity import Entity


@dataclass(frozen=True)
class InteractionLog:
    """Record of a single interaction that affected the relationship.

    Why frozen: Interactions are historical records that should never
    be modified once created. This ensures data integrity for the
    relationship evolution timeline.

    Attributes:
        summary: Brief description of what happened in the interaction.
        trust_change: How much trust changed (-100 to +100).
        romance_change: How much romance changed (-100 to +100).
        timestamp: When the interaction occurred.
        interaction_id: Unique identifier for this interaction.
    """

    summary: str
    trust_change: int
    romance_change: int
    timestamp: datetime = field(default_factory=datetime.now)
    interaction_id: str = field(default_factory=lambda: str(__import__("uuid").uuid4()))

    def __post_init__(self) -> None:
        """Validate interaction log constraints."""
        if not self.summary or not self.summary.strip():
            raise ValueError("Interaction summary cannot be empty")
        if not -100 <= self.trust_change <= 100:
            raise ValueError("Trust change must be between -100 and +100")
        if not -100 <= self.romance_change <= 100:
            raise ValueError("Romance change must be between -100 and +100")


class EntityType(Enum):
    """Classification of entity types that can participate in relationships.

    Used to specify the source and target types in a relationship,
    enabling type-aware queries and validation.

    Attributes:
        CHARACTER: A character/persona in the narrative.
        FACTION: An organization, group, or political entity.
        LOCATION: A place, region, or geographical feature.
        ITEM: An object, artifact, or possession.
        EVENT: A historical or narrative event.
    """

    CHARACTER = "character"
    FACTION = "faction"
    LOCATION = "location"
    ITEM = "item"
    EVENT = "event"


class RelationshipType(Enum):
    """Classification of relationship types between entities.

    Defines the nature of the connection between two entities.
    Each type has an implicit bidirectional awareness - for example,
    if A is ENEMY of B, then B is also ENEMY of A.

    Attributes:
        FAMILY: Blood or adoptive family relationship.
        ENEMY: Hostile or adversarial relationship.
        ALLY: Friendly, cooperative relationship.
        MENTOR: Teacher/student or guide relationship.
        ROMANTIC: Romantic or intimate relationship.
        RIVAL: Competitive but not necessarily hostile.
        MEMBER_OF: Membership in a group or organization.
        LOCATED_IN: Physical presence or residence.
        OWNS: Ownership or possession.
        CREATED: Creator/creation relationship.
        HISTORICAL: Past relationship that has ended.
        NEUTRAL: Known to each other but no strong ties.
    """

    FAMILY = "family"
    ENEMY = "enemy"
    ALLY = "ally"
    MENTOR = "mentor"
    ROMANTIC = "romantic"
    RIVAL = "rival"
    MEMBER_OF = "member_of"
    LOCATED_IN = "located_in"
    OWNS = "owns"
    CREATED = "created"
    HISTORICAL = "historical"
    NEUTRAL = "neutral"

    def is_bidirectional(self) -> bool:
        """Check if this relationship type is inherently bidirectional.

        Returns:
            True if the relationship implies mutual recognition.
        """
        bidirectional_types = {
            RelationshipType.FAMILY,
            RelationshipType.ENEMY,
            RelationshipType.ALLY,
            RelationshipType.ROMANTIC,
            RelationshipType.RIVAL,
            RelationshipType.HISTORICAL,
            RelationshipType.NEUTRAL,
        }
        return self in bidirectional_types

    def get_inverse(self) -> "RelationshipType":
        """Get the inverse relationship type.

        For bidirectional relationships, returns the same type.
        For directional relationships, returns the logical inverse.

        Returns:
            The inverse RelationshipType.
        """
        inverses = {
            RelationshipType.MENTOR: RelationshipType.MENTOR,  # Mentor implies mentee
            RelationshipType.MEMBER_OF: RelationshipType.MEMBER_OF,
            RelationshipType.LOCATED_IN: RelationshipType.LOCATED_IN,
            RelationshipType.OWNS: RelationshipType.OWNS,
            RelationshipType.CREATED: RelationshipType.CREATED,
        }
        return inverses.get(self, self)


@dataclass
class Relationship(Entity):
    """Relationship Entity.

    Represents a connection between two entities in the world. Relationships
    form edges in the World Knowledge Graph, enabling rich narrative
    interconnections and queries.

    Why use strength instead of boolean existence: Relationships in
    narratives are nuanced. A character might be a weak ally or a bitter
    enemy. The strength value (0-100) captures this nuance.

    Attributes:
        source_id: ID of the entity initiating the relationship.
        source_type: Type of the source entity (CHARACTER, FACTION, etc.).
        target_id: ID of the entity being related to.
        target_type: Type of the target entity.
        relationship_type: Nature of the relationship (FAMILY, ENEMY, etc.).
        description: Human-readable description of the relationship.
        strength: Intensity of the relationship (0-100).
        is_active: Whether the relationship is currently active.
        metadata: Additional flexible data for specific use cases.
    """

    source_id: str = ""
    source_type: EntityType = EntityType.CHARACTER
    target_id: str = ""
    target_type: EntityType = EntityType.CHARACTER
    relationship_type: RelationshipType = RelationshipType.NEUTRAL
    description: str = ""
    strength: int = 50
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Dynamic relationship evolution metrics (CHAR-025)
    trust: int = 50
    romance: int = 0
    _interaction_history: Tuple[InteractionLog, ...] = field(default_factory=tuple)

    def _validate_business_rules(self) -> List[str]:
        """Validate Relationship-specific business rules."""
        errors = []

        if not self.source_id or not self.source_id.strip():
            errors.append("Source ID cannot be empty")

        if not self.target_id or not self.target_id.strip():
            errors.append("Target ID cannot be empty")

        if self.source_id == self.target_id:
            errors.append("Source and target cannot be the same entity")

        if not 0 <= self.strength <= 100:
            errors.append("Strength must be between 0 and 100")

        if not 0 <= self.trust <= 100:
            errors.append("Trust must be between 0 and 100")

        if not 0 <= self.romance <= 100:
            errors.append("Romance must be between 0 and 100")

        # Validate relationship type compatibility with entity types
        errors.extend(self._validate_type_compatibility())

        return errors

    def _validate_type_compatibility(self) -> List[str]:
        """Validate that relationship type is compatible with entity types."""
        errors = []

        # FAMILY relationships should primarily be between characters
        if self.relationship_type == RelationshipType.FAMILY:
            if self.source_type != EntityType.CHARACTER:
                errors.append("FAMILY relationships should have CHARACTER as source")
            if self.target_type != EntityType.CHARACTER:
                errors.append("FAMILY relationships should have CHARACTER as target")

        # ROMANTIC relationships must be between characters
        if self.relationship_type == RelationshipType.ROMANTIC:
            if self.source_type != EntityType.CHARACTER:
                errors.append("ROMANTIC relationships require CHARACTER source")
            if self.target_type != EntityType.CHARACTER:
                errors.append("ROMANTIC relationships require CHARACTER target")

        # MEMBER_OF typically connects character/faction to faction
        if self.relationship_type == RelationshipType.MEMBER_OF:
            if self.target_type not in (EntityType.FACTION, EntityType.LOCATION):
                errors.append("MEMBER_OF target should be FACTION or LOCATION")

        # LOCATED_IN connects entities to locations
        if self.relationship_type == RelationshipType.LOCATED_IN:
            if self.target_type != EntityType.LOCATION:
                errors.append("LOCATED_IN target must be LOCATION")

        # OWNS connects characters/factions to items/locations
        if self.relationship_type == RelationshipType.OWNS:
            if self.source_type not in (EntityType.CHARACTER, EntityType.FACTION):
                errors.append("OWNS source should be CHARACTER or FACTION")
            if self.target_type not in (EntityType.ITEM, EntityType.LOCATION):
                errors.append("OWNS target should be ITEM or LOCATION")

        return errors

    def update_strength(self, new_strength: int) -> None:
        """Update the relationship strength.

        Args:
            new_strength: New strength value (0-100).

        Raises:
            ValueError: If strength is out of valid range.
        """
        if not 0 <= new_strength <= 100:
            raise ValueError("Strength must be between 0 and 100")

        self.strength = new_strength
        self.touch()

    def deactivate(self) -> None:
        """Mark the relationship as inactive (historical)."""
        self.is_active = False
        self.touch()

    def activate(self) -> None:
        """Mark the relationship as active."""
        self.is_active = True
        self.touch()

    def update_description(self, description: str) -> None:
        """Update the relationship description.

        Args:
            description: New description text.
        """
        self.description = description.strip()
        self.touch()

    def change_type(self, new_type: RelationshipType) -> None:
        """Change the relationship type.

        Why allow type changes: Narratives evolve. Friends become enemies,
        mentors become equals, rivals become allies. This method enables
        such narrative arcs.

        Args:
            new_type: New relationship type.
        """
        self.relationship_type = new_type
        self.touch()
        # Re-validate after type change
        self.validate()

    def log_interaction(
        self,
        summary: str,
        trust_change: int = 0,
        romance_change: int = 0,
    ) -> InteractionLog:
        """Record an interaction that affects the relationship.

        Why log interactions: Relationships evolve through specific events.
        Logging each interaction provides a history that explains how the
        relationship reached its current state, enabling rich narrative
        backstories and character development arcs.

        Args:
            summary: Description of what happened in the interaction.
            trust_change: How much trust changed (-100 to +100).
            romance_change: How much romance changed (-100 to +100).

        Returns:
            The created InteractionLog record.

        Raises:
            ValueError: If changes are out of valid range or summary is empty.
        """
        interaction = InteractionLog(
            summary=summary,
            trust_change=trust_change,
            romance_change=romance_change,
        )

        # Apply changes with clamping to valid range
        new_trust = max(0, min(100, self.trust + trust_change))
        new_romance = max(0, min(100, self.romance + romance_change))

        self.trust = new_trust
        self.romance = new_romance

        # Append to immutable history (create new tuple)
        self._interaction_history = self._interaction_history + (interaction,)
        self.touch()

        return interaction

    def update_trust(self, new_trust: int) -> None:
        """Directly update trust level.

        Args:
            new_trust: New trust value (0-100).

        Raises:
            ValueError: If trust is out of valid range.
        """
        if not 0 <= new_trust <= 100:
            raise ValueError("Trust must be between 0 and 100")

        self.trust = new_trust
        self.touch()

    def update_romance(self, new_romance: int) -> None:
        """Directly update romance level.

        Args:
            new_romance: New romance value (0-100).

        Raises:
            ValueError: If romance is out of valid range.
        """
        if not 0 <= new_romance <= 100:
            raise ValueError("Romance must be between 0 and 100")

        self.romance = new_romance
        self.touch()

    def get_interaction_history(self) -> Tuple[InteractionLog, ...]:
        """Get the full interaction history.

        Returns:
            Tuple of all logged interactions, ordered chronologically.
        """
        return self._interaction_history

    def get_recent_interactions(self, limit: int = 10) -> Tuple[InteractionLog, ...]:
        """Get the most recent interactions.

        Args:
            limit: Maximum number of interactions to return.

        Returns:
            Tuple of recent interactions, most recent first.
        """
        return tuple(reversed(self._interaction_history[-limit:]))

    def is_positive(self) -> bool:
        """Check if this is a positive/friendly relationship."""
        positive_types = {
            RelationshipType.FAMILY,
            RelationshipType.ALLY,
            RelationshipType.MENTOR,
            RelationshipType.ROMANTIC,
        }
        return self.relationship_type in positive_types

    def is_negative(self) -> bool:
        """Check if this is a negative/hostile relationship."""
        negative_types = {
            RelationshipType.ENEMY,
            RelationshipType.RIVAL,
        }
        return self.relationship_type in negative_types

    def is_structural(self) -> bool:
        """Check if this is a structural relationship (membership, location, ownership)."""
        structural_types = {
            RelationshipType.MEMBER_OF,
            RelationshipType.LOCATED_IN,
            RelationshipType.OWNS,
            RelationshipType.CREATED,
        }
        return self.relationship_type in structural_types

    def involves_entity(self, entity_id: str) -> bool:
        """Check if this relationship involves a specific entity.

        Args:
            entity_id: Entity ID to check.

        Returns:
            True if the entity is either source or target.
        """
        return entity_id in (self.source_id, self.target_id)

    def get_other_entity(self, entity_id: str) -> Optional[str]:
        """Get the other entity in this relationship.

        Args:
            entity_id: One of the entity IDs in the relationship.

        Returns:
            The other entity ID, or None if entity_id is not part of this relationship.
        """
        if entity_id == self.source_id:
            return self.target_id
        elif entity_id == self.target_id:
            return self.source_id
        return None

    def _to_dict_specific(self) -> Dict[str, Any]:
        """Convert Relationship-specific data to dictionary."""
        return {
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "target_id": self.target_id,
            "target_type": self.target_type.value,
            "relationship_type": self.relationship_type.value,
            "description": self.description,
            "strength": self.strength,
            "is_active": self.is_active,
            "metadata": self.metadata,
            "trust": self.trust,
            "romance": self.romance,
            "interaction_history": [
                {
                    "interaction_id": log.interaction_id,
                    "summary": log.summary,
                    "trust_change": log.trust_change,
                    "romance_change": log.romance_change,
                    "timestamp": log.timestamp.isoformat(),
                }
                for log in self._interaction_history
            ],
        }

    @classmethod
    def create_character_relationship(
        cls,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        description: str = "",
        strength: int = 50,
    ) -> "Relationship":
        """Factory method for character-to-character relationships.

        Args:
            source_id: ID of the first character.
            target_id: ID of the second character.
            relationship_type: Type of relationship.
            description: Optional description.
            strength: Relationship intensity (0-100).

        Returns:
            A new Relationship between characters.
        """
        return cls(
            source_id=source_id,
            source_type=EntityType.CHARACTER,
            target_id=target_id,
            target_type=EntityType.CHARACTER,
            relationship_type=relationship_type,
            description=description,
            strength=strength,
        )

    @classmethod
    def create_membership(
        cls,
        member_id: str,
        member_type: EntityType,
        faction_id: str,
        description: str = "",
        strength: int = 70,
    ) -> "Relationship":
        """Factory method for membership relationships.

        Args:
            member_id: ID of the member entity.
            member_type: Type of the member (CHARACTER or FACTION).
            faction_id: ID of the faction.
            description: Optional description of membership role.
            strength: Commitment level (0-100).

        Returns:
            A new MEMBER_OF Relationship.
        """
        return cls(
            source_id=member_id,
            source_type=member_type,
            target_id=faction_id,
            target_type=EntityType.FACTION,
            relationship_type=RelationshipType.MEMBER_OF,
            description=description,
            strength=strength,
        )

    @classmethod
    def create_location_relationship(
        cls,
        entity_id: str,
        entity_type: EntityType,
        location_id: str,
        description: str = "",
    ) -> "Relationship":
        """Factory method for LOCATED_IN relationships.

        Args:
            entity_id: ID of the entity at the location.
            entity_type: Type of the entity.
            location_id: ID of the location.
            description: Optional description.

        Returns:
            A new LOCATED_IN Relationship.
        """
        return cls(
            source_id=entity_id,
            source_type=entity_type,
            target_id=location_id,
            target_type=EntityType.LOCATION,
            relationship_type=RelationshipType.LOCATED_IN,
            description=description,
            strength=100,  # Location relationships are typically binary
        )
