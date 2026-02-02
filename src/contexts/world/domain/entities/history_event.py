#!/usr/bin/env python3
"""HistoryEvent Domain Entity.

This module defines the HistoryEvent entity which represents significant
historical events in the world's timeline, including wars, discoveries,
political changes, and other occurrences that shape the world's lore.

Typical usage example:
    >>> from src.contexts.world.domain.entities import (
    ...     HistoryEvent, EventType, EventSignificance
    ... )
    >>> war = HistoryEvent.create_war(
    ...     name="The Sundering",
    ...     description="A cataclysmic war that split the continent.",
    ...     date_description="Year 1042 of the Third Age",
    ...     faction_ids=["uuid1", "uuid2"]
    ... )
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .entity import Entity


class EventType(Enum):
    """Classification of historical event types.

    Categorizes events to enable consistent narrative treatment and
    establish relationships between events and other entities.

    Attributes:
        WAR: Extended military conflict between factions.
        BATTLE: Single military engagement.
        TREATY: Formal agreement between factions.
        FOUNDING: Creation of a new faction or settlement.
        DESTRUCTION: Annihilation of a location or faction.
        DISCOVERY: Finding of new knowledge, lands, or artifacts.
        INVENTION: Creation of new technology or magic.
        CORONATION: Ascension of a new ruler.
        DEATH: Passing of a significant figure.
        BIRTH: Arrival of a significant figure.
        MARRIAGE: Union between important individuals.
        REVOLUTION: Uprising against established order.
        MIGRATION: Large-scale population movement.
        DISASTER: Natural or magical catastrophe.
        MIRACLE: Divine intervention or unexplained wonder.
        PROPHECY: Revelation of future events.
        CONQUEST: Takeover of territory.
        LIBERATION: Freedom from occupation or oppression.
        ALLIANCE: Formation of faction partnership.
        BETRAYAL: Breaking of trust or agreement.
        RELIGIOUS: Faith-related occurrence.
        CULTURAL: Artistic or social development.
        ECONOMIC: Trade or financial change.
        SCIENTIFIC: Knowledge or research advancement.
        MAGICAL: Arcane phenomenon.
        POLITICAL: Governance or diplomacy event.
    """

    WAR = "war"
    BATTLE = "battle"
    TREATY = "treaty"
    FOUNDING = "founding"
    DESTRUCTION = "destruction"
    DISCOVERY = "discovery"
    INVENTION = "invention"
    CORONATION = "coronation"
    DEATH = "death"
    BIRTH = "birth"
    MARRIAGE = "marriage"
    REVOLUTION = "revolution"
    MIGRATION = "migration"
    DISASTER = "disaster"
    MIRACLE = "miracle"
    PROPHECY = "prophecy"
    CONQUEST = "conquest"
    LIBERATION = "liberation"
    ALLIANCE = "alliance"
    BETRAYAL = "betrayal"
    RELIGIOUS = "religious"
    CULTURAL = "cultural"
    ECONOMIC = "economic"
    SCIENTIFIC = "scientific"
    MAGICAL = "magical"
    POLITICAL = "political"


class EventSignificance(Enum):
    """Level of historical significance.

    Determines how much impact an event has on world history and
    affects narrative importance calculations.

    Attributes:
        TRIVIAL: Forgotten by most, local impact only.
        MINOR: Remembered locally, limited lasting effects.
        MODERATE: Regional impact, taught in schools.
        MAJOR: National impact, changes political landscape.
        WORLD_CHANGING: Global impact, reshapes civilization.
        LEGENDARY: Mythic status, defines eras.
    """

    TRIVIAL = "trivial"
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    WORLD_CHANGING = "world_changing"
    LEGENDARY = "legendary"


class EventOutcome(Enum):
    """General outcome of the event.

    Categorizes the net effect of the event on the world and affected parties.

    Attributes:
        POSITIVE: Beneficial results for most involved.
        NEGATIVE: Harmful results for most involved.
        NEUTRAL: No clear positive or negative impact.
        MIXED: Both positive and negative consequences.
        UNKNOWN: Outcome not yet determined or understood.
    """

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"
    UNKNOWN = "unknown"


@dataclass(eq=False)
class HistoryEvent(Entity):
    """HistoryEvent Entity.

    Represents a significant historical event in the world's timeline.
    Contains domain logic for managing event relationships, causality,
    and narrative impact.

    Attributes:
        name: Short name/title of the event
        description: Detailed description of what happened
        event_type: Classification of the event
        significance: Level of historical significance
        outcome: General outcome of the event
        date_description: Narrative date description (e.g., "Year 1042 of the Third Age")
        duration_description: How long the event lasted (e.g., "Three months")
        location_ids: IDs of locations where event occurred
        faction_ids: IDs of factions involved
        key_figures: Names of key individuals involved
        causes: What led to this event
        consequences: What resulted from this event
        preceding_event_ids: IDs of events that directly preceded this one
        following_event_ids: IDs of events that directly followed this one
        related_event_ids: IDs of related but not directly connected events
        is_secret: Whether this event is hidden from common knowledge
        sources: Where knowledge of this event comes from
        narrative_importance: How important this is to the story (0-100)
    """

    name: str = ""
    description: str = ""
    event_type: EventType = EventType.POLITICAL
    significance: EventSignificance = EventSignificance.MODERATE
    outcome: EventOutcome = EventOutcome.NEUTRAL
    date_description: str = ""
    duration_description: Optional[str] = None
    location_ids: List[str] = field(default_factory=list)
    faction_ids: List[str] = field(default_factory=list)
    key_figures: List[str] = field(default_factory=list)
    causes: List[str] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)
    preceding_event_ids: List[str] = field(default_factory=list)
    following_event_ids: List[str] = field(default_factory=list)
    related_event_ids: List[str] = field(default_factory=list)
    is_secret: bool = False
    sources: List[str] = field(default_factory=list)
    narrative_importance: int = 50

    def _validate_business_rules(self) -> List[str]:
        """Validate HistoryEvent-specific business rules."""
        errors = []

        if not self.name or not self.name.strip():
            errors.append("Event name cannot be empty")

        if len(self.name) > 300:
            errors.append("Event name cannot exceed 300 characters")

        if not self.date_description:
            errors.append("Event must have a date description")

        if not 0 <= self.narrative_importance <= 100:
            errors.append("Narrative importance must be between 0 and 100")

        # Validate event relationships
        errors.extend(self._validate_event_relationships())

        # Validate type-specific rules
        errors.extend(self._validate_type_specific_rules())

        return errors

    def _validate_event_relationships(self) -> List[str]:
        """Validate event relationship consistency."""
        errors = []

        # Can't be own predecessor/successor
        if self.id in self.preceding_event_ids:
            errors.append("Event cannot precede itself")

        if self.id in self.following_event_ids:
            errors.append("Event cannot follow itself")

        if self.id in self.related_event_ids:
            errors.append("Event cannot be related to itself")

        # Check for circular relationships (basic check)
        common_events = set(self.preceding_event_ids) & set(self.following_event_ids)
        if common_events:
            errors.append(
                f"Events cannot be both preceding and following: {common_events}"
            )

        return errors

    def _validate_type_specific_rules(self) -> List[str]:
        """Validate rules specific to event type."""
        errors = []

        # Wars and battles should have factions
        conflict_types = {EventType.WAR, EventType.BATTLE, EventType.CONQUEST}
        if self.event_type in conflict_types and len(self.faction_ids) < 2:
            # Warning but allowed - could be civil war within one faction
            pass

        # World-changing events should have consequences
        if (
            self.significance == EventSignificance.WORLD_CHANGING
            and not self.consequences
        ):
            # This is a warning but not an error
            pass

        # Legendary events should be moderately important to narrative
        if (
            self.significance == EventSignificance.LEGENDARY
            and self.narrative_importance < 30
        ):
            errors.append(
                "Legendary events should have narrative importance of at least 30"
            )

        return errors

    def add_cause(self, cause: str) -> None:
        """
        Add a cause for this event.

        Args:
            cause: Description of what caused this event
        """
        if not cause or not cause.strip():
            raise ValueError("Cause cannot be empty")

        cause = cause.strip()
        if cause not in self.causes:
            self.causes.append(cause)
            self.touch()

    def add_consequence(self, consequence: str) -> None:
        """
        Add a consequence of this event.

        Args:
            consequence: Description of what resulted from this event
        """
        if not consequence or not consequence.strip():
            raise ValueError("Consequence cannot be empty")

        consequence = consequence.strip()
        if consequence not in self.consequences:
            self.consequences.append(consequence)
            self.touch()

    def add_key_figure(self, figure: str) -> None:
        """
        Add a key figure involved in this event.

        Args:
            figure: Name of the key figure
        """
        if not figure or not figure.strip():
            raise ValueError("Figure name cannot be empty")

        figure = figure.strip()
        if figure not in self.key_figures:
            self.key_figures.append(figure)
            self.touch()

    def add_location(self, location_id: str) -> None:
        """
        Add a location where this event occurred.

        Args:
            location_id: ID of the location
        """
        if location_id not in self.location_ids:
            self.location_ids.append(location_id)
            self.touch()

    def add_faction(self, faction_id: str) -> None:
        """
        Add a faction involved in this event.

        Args:
            faction_id: ID of the faction
        """
        if faction_id not in self.faction_ids:
            self.faction_ids.append(faction_id)
            self.touch()

    def add_preceding_event(self, event_id: str) -> None:
        """
        Add an event that preceded this one.

        Args:
            event_id: ID of the preceding event

        Raises:
            ValueError: If trying to add self or create circular reference
        """
        if event_id == self.id:
            raise ValueError("Event cannot precede itself")

        if event_id in self.following_event_ids:
            raise ValueError("Event cannot be both preceding and following")

        if event_id not in self.preceding_event_ids:
            self.preceding_event_ids.append(event_id)
            self.touch()

    def add_following_event(self, event_id: str) -> None:
        """
        Add an event that followed this one.

        Args:
            event_id: ID of the following event

        Raises:
            ValueError: If trying to add self or create circular reference
        """
        if event_id == self.id:
            raise ValueError("Event cannot follow itself")

        if event_id in self.preceding_event_ids:
            raise ValueError("Event cannot be both preceding and following")

        if event_id not in self.following_event_ids:
            self.following_event_ids.append(event_id)
            self.touch()

    def add_related_event(self, event_id: str) -> None:
        """
        Add a related event.

        Args:
            event_id: ID of the related event
        """
        if event_id == self.id:
            raise ValueError("Event cannot be related to itself")

        if event_id not in self.related_event_ids:
            self.related_event_ids.append(event_id)
            self.touch()

    def mark_as_secret(self) -> None:
        """Mark this event as secret/hidden knowledge."""
        if not self.is_secret:
            self.is_secret = True
            self.touch()

    def reveal_secret(self) -> None:
        """Make this event common knowledge."""
        if self.is_secret:
            self.is_secret = False
            self.touch()

    def update_significance(self, significance: EventSignificance) -> None:
        """
        Update the event's significance level.

        Args:
            significance: New significance level
        """
        if significance != self.significance:
            self.significance = significance
            self.touch()
            self.validate()

    def update_narrative_importance(self, importance: int) -> None:
        """
        Update the narrative importance.

        Args:
            importance: New importance level (0-100)

        Raises:
            ValueError: If importance is out of range
        """
        if not 0 <= importance <= 100:
            raise ValueError("Narrative importance must be between 0 and 100")

        if importance != self.narrative_importance:
            self.narrative_importance = importance
            self.touch()
            self.validate()

    def is_conflict(self) -> bool:
        """Check if this event is a conflict (war, battle, etc.)."""
        return self.event_type in {
            EventType.WAR,
            EventType.BATTLE,
            EventType.CONQUEST,
            EventType.REVOLUTION,
        }

    def is_positive(self) -> bool:
        """Check if this event had a positive outcome."""
        return self.outcome == EventOutcome.POSITIVE

    def is_negative(self) -> bool:
        """Check if this event had a negative outcome."""
        return self.outcome == EventOutcome.NEGATIVE

    def is_world_changing(self) -> bool:
        """Check if this is a world-changing event."""
        return self.significance in {
            EventSignificance.WORLD_CHANGING,
            EventSignificance.LEGENDARY,
        }

    def has_known_causes(self) -> bool:
        """Check if this event has documented causes."""
        return len(self.causes) > 0

    def has_known_consequences(self) -> bool:
        """Check if this event has documented consequences."""
        return len(self.consequences) > 0

    def get_causality_chain_depth(self) -> int:
        """
        Get the depth of the causality chain (preceding events).

        Note: This only counts direct predecessors, not full chain.
        Full chain computation would require access to other events.

        Returns:
            Number of direct preceding events
        """
        return len(self.preceding_event_ids)

    def get_impact_breadth(self) -> int:
        """
        Get the breadth of impact (following + related events).

        Returns:
            Number of events directly impacted by this one
        """
        return len(self.following_event_ids) + len(self.related_event_ids)

    def _to_dict_specific(self) -> Dict[str, Any]:
        """Convert HistoryEvent-specific data to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "event_type": self.event_type.value,
            "significance": self.significance.value,
            "outcome": self.outcome.value,
            "date_description": self.date_description,
            "duration_description": self.duration_description,
            "location_ids": self.location_ids,
            "faction_ids": self.faction_ids,
            "key_figures": self.key_figures,
            "causes": self.causes,
            "consequences": self.consequences,
            "preceding_event_ids": self.preceding_event_ids,
            "following_event_ids": self.following_event_ids,
            "related_event_ids": self.related_event_ids,
            "is_secret": self.is_secret,
            "sources": self.sources,
            "narrative_importance": self.narrative_importance,
        }

    @classmethod
    def create_war(
        cls,
        name: str,
        description: str,
        date_description: str,
        faction_ids: List[str],
        outcome: EventOutcome = EventOutcome.MIXED,
    ) -> "HistoryEvent":
        """Create a war event with typical military conflict attributes.

        Factory method that creates a pre-configured HistoryEvent representing
        an extended military conflict with major significance and high
        narrative importance.

        Args:
            name: The war's name.
            description: Detailed description of the conflict.
            date_description: When the war occurred (narrative format).
            faction_ids: UUIDs of factions involved in the conflict.
            outcome: Result of the war. Defaults to MIXED.

        Returns:
            A new HistoryEvent configured as a war.

        Example:
            >>> war = HistoryEvent.create_war(
            ...     name="The Sundering",
            ...     description="A devastating conflict over ancient artifacts.",
            ...     date_description="Year 1042 of the Third Age",
            ...     faction_ids=["kingdom-uuid", "empire-uuid"]
            ... )
        """
        return cls(
            name=name,
            description=description,
            event_type=EventType.WAR,
            significance=EventSignificance.MAJOR,
            outcome=outcome,
            date_description=date_description,
            faction_ids=faction_ids,
            narrative_importance=70,
        )

    @classmethod
    def create_founding(
        cls,
        name: str,
        description: str,
        date_description: str,
        location_ids: List[str] | None = None,
        faction_ids: List[str] | None = None,
    ) -> "HistoryEvent":
        """Create a founding event for settlements or organizations.

        Factory method that creates a pre-configured HistoryEvent representing
        the establishment of a new faction or location with positive outcome
        and moderate significance.

        Args:
            name: The event's name.
            description: Detailed description of the founding.
            date_description: When the founding occurred (narrative format).
            location_ids: UUIDs of locations where the founding occurred.
            faction_ids: UUIDs of factions involved in the founding.

        Returns:
            A new HistoryEvent configured as a founding event.

        Example:
            >>> founding = HistoryEvent.create_founding(
            ...     name="Founding of Thornhaven",
            ...     description="Refugees established a new city.",
            ...     date_description="After the Great Migration",
            ...     location_ids=["city-uuid"]
            ... )
        """
        return cls(
            name=name,
            description=description,
            event_type=EventType.FOUNDING,
            significance=EventSignificance.MODERATE,
            outcome=EventOutcome.POSITIVE,
            date_description=date_description,
            location_ids=location_ids or [],
            faction_ids=faction_ids or [],
            narrative_importance=50,
        )

    @classmethod
    def create_disaster(
        cls,
        name: str,
        description: str,
        date_description: str,
        location_ids: List[str],
        significance: EventSignificance = EventSignificance.MAJOR,
    ) -> "HistoryEvent":
        """Create a disaster event representing a catastrophe.

        Factory method that creates a pre-configured HistoryEvent representing
        a natural or magical disaster with negative outcome and configurable
        significance.

        Args:
            name: The disaster's name.
            description: Detailed description of the catastrophe.
            date_description: When the disaster occurred (narrative format).
            location_ids: UUIDs of locations affected by the disaster.
            significance: Level of historical impact. Defaults to MAJOR.

        Returns:
            A new HistoryEvent configured as a disaster.

        Example:
            >>> disaster = HistoryEvent.create_disaster(
            ...     name="The Great Flood",
            ...     description="Rising seas swallowed the coastal cities.",
            ...     date_description="The Year of Drowned Bells",
            ...     location_ids=["coast-uuid", "port-uuid"],
            ...     significance=EventSignificance.WORLD_CHANGING
            ... )
        """
        return cls(
            name=name,
            description=description,
            event_type=EventType.DISASTER,
            significance=significance,
            outcome=EventOutcome.NEGATIVE,
            date_description=date_description,
            location_ids=location_ids,
            narrative_importance=60,
        )
