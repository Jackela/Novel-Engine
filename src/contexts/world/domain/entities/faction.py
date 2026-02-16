#!/usr/bin/env python3
"""Faction Domain Entity.

This module defines the Faction entity which represents organizations, groups,
or power structures within the world. Factions have goals, values, territories,
and complex relationships with other factions.

Typical usage example:
    >>> from src.contexts.world.domain.entities import Faction, FactionType
    >>> kingdom = Faction.create_kingdom(
    ...     name="Kingdom of Valdris",
    ...     description="A prosperous realm known for its academies."
    ... )
    >>> guild = Faction.create_guild(name="Merchants' Alliance", guild_focus="trade")
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from .entity import Entity


class FactionType(Enum):
    """Classification of faction types.

    Determines the organizational structure, typical behaviors, and
    default characteristics of a faction.

    Attributes:
        KINGDOM: A sovereign nation with monarchy.
        EMPIRE: A large multi-nation territory under imperial rule.
        GUILD: Professional organization of craftsmen or merchants.
        CULT: Religious or ideological extremist group.
        CORPORATION: Business entity with economic focus.
        MILITARY: Armed forces or mercenary organization.
        RELIGIOUS: Mainstream religious institution.
        CRIMINAL: Organized crime syndicate.
        ACADEMIC: Educational or research institution.
        MERCHANT: Trading company or merchant collective.
        TRIBAL: Indigenous or nomadic clan structure.
        REVOLUTIONARY: Movement seeking political change.
        SECRET_SOCIETY: Clandestine organization with hidden agenda.
        ADVENTURER_GROUP: Band of heroes or mercenaries.
        NOBLE_HOUSE: Aristocratic family lineage.
    """

    KINGDOM = "kingdom"
    EMPIRE = "empire"
    GUILD = "guild"
    CULT = "cult"
    CORPORATION = "corporation"
    MILITARY = "military"
    RELIGIOUS = "religious"
    CRIMINAL = "criminal"
    ACADEMIC = "academic"
    MERCHANT = "merchant"
    TRIBAL = "tribal"
    REVOLUTIONARY = "revolutionary"
    SECRET_SOCIETY = "secret_society"
    ADVENTURER_GROUP = "adventurer_group"
    NOBLE_HOUSE = "noble_house"


class FactionAlignment(Enum):
    """Moral alignment of the faction.

    Based on the classic D&D alignment system, representing both
    ethical (lawful/chaotic) and moral (good/evil) dimensions.

    Attributes:
        LAWFUL_GOOD: Follows rules, does right. Paladins, just kings.
        NEUTRAL_GOOD: Does right regardless of rules. Healers, helpers.
        CHAOTIC_GOOD: Values freedom, fights oppression. Rebels, vigilantes.
        LAWFUL_NEUTRAL: Values order above all. Judges, bureaucrats.
        TRUE_NEUTRAL: Balanced, pragmatic. Druids, merchants.
        CHAOTIC_NEUTRAL: Values personal freedom. Rogues, wanderers.
        LAWFUL_EVIL: Uses rules for selfish ends. Tyrants, corrupt officials.
        NEUTRAL_EVIL: Self-serving without loyalty. Mercenaries, assassins.
        CHAOTIC_EVIL: Destruction and cruelty. Raiders, demons.
    """

    LAWFUL_GOOD = "lawful_good"
    NEUTRAL_GOOD = "neutral_good"
    CHAOTIC_GOOD = "chaotic_good"
    LAWFUL_NEUTRAL = "lawful_neutral"
    TRUE_NEUTRAL = "true_neutral"
    CHAOTIC_NEUTRAL = "chaotic_neutral"
    LAWFUL_EVIL = "lawful_evil"
    NEUTRAL_EVIL = "neutral_evil"
    CHAOTIC_EVIL = "chaotic_evil"


class FactionStatus(Enum):
    """Current status of the faction.

    Represents the operational state of the faction, affecting its
    ability to act and interact with other entities.

    Attributes:
        ACTIVE: Fully operational and influential.
        DORMANT: Inactive but not disbanded, may reactivate.
        DISBANDED: No longer exists as an organization.
        EMERGING: Newly formed, building influence.
        DECLINING: Losing power and members.
        CONQUERED: Subjugated by another faction.
        HIDDEN: Operating in secret, existence unknown to most.
    """

    ACTIVE = "active"
    DORMANT = "dormant"
    DISBANDED = "disbanded"
    EMERGING = "emerging"
    DECLINING = "declining"
    CONQUERED = "conquered"
    HIDDEN = "hidden"


@dataclass
class FactionRelation:
    """Represents the relationship between two factions.

    Encapsulates the diplomatic or social connection between factions,
    including the nature and strength of their relationship.

    Attributes:
        target_faction_id: UUID of the related faction.
        relation_type: Type of relationship (alliance, enemy, neutral,
            vassal, overlord, rival, trading).
        strength: Relationship strength from -100 (hostile) to 100 (allied).
        description: Optional narrative description of the relationship.

    Example:
        >>> relation = FactionRelation(
        ...     target_faction_id="uuid-here",
        ...     relation_type="alliance",
        ...     strength=75,
        ...     description="Forged during the Great War"
        ... )
        >>> relation.is_friendly()
        True
    """

    target_faction_id: str
    relation_type: str
    strength: int
    description: Optional[str] = None

    def is_hostile(self) -> bool:
        """Check if relationship is hostile (strength < -30)."""
        return self.strength < -30

    def is_friendly(self) -> bool:
        """Check if relationship is friendly (strength > 30)."""
        return self.strength > 30

    def is_neutral(self) -> bool:
        """Check if relationship is neutral (-30 <= strength <= 30)."""
        return -30 <= self.strength <= 30


@dataclass(eq=False)
class Faction(Entity):
    """Faction Entity.

    Represents an organization, group, or power within the world. Contains
    domain logic for managing faction relationships, influence, and internal
    consistency.

    Attributes:
        name: The faction's name
        description: Detailed description of the faction
        faction_type: Classification of the faction
        alignment: Moral alignment
        status: Current operational status
        headquarters_id: ID of primary location (optional)
        leader_name: Name of current leader (optional)
        founding_date: When the faction was founded (narrative date)
        values: Core values/beliefs of the faction
        goals: Current objectives
        resources: Types of resources controlled
        influence: Level of influence (0-100)
        military_strength: Military power (0-100)
        economic_power: Economic strength (0-100)
        relations: Relationships with other factions
        member_count: Approximate number of members
        territories: IDs of controlled locations
        secrets: Hidden information about the faction
    """

    name: str = ""
    description: str = ""
    faction_type: FactionType = FactionType.GUILD
    alignment: FactionAlignment = FactionAlignment.TRUE_NEUTRAL
    status: FactionStatus = FactionStatus.ACTIVE
    headquarters_id: Optional[str] = None
    leader_name: Optional[str] = None
    leader_id: Optional[str] = None  # Character ID of the faction leader
    founding_date: Optional[str] = None
    values: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    influence: int = 50
    military_strength: int = 50
    economic_power: int = 50
    relations: List[FactionRelation] = field(default_factory=list)
    member_count: int = 100
    territories: List[str] = field(default_factory=list)
    secrets: List[str] = field(default_factory=list)

    def __eq__(self, other: object) -> bool:
        """Compare factions by identity, not by mutable attributes.

        Why: Preserve Entity equality semantics (type + id) while explicitly
        documenting the intent for CodeQL and reviewers.
        """
        return super().__eq__(other)

    def _validate_business_rules(self) -> List[str]:
        """Validate Faction-specific business rules."""
        errors = []

        if not self.name or not self.name.strip():
            errors.append("Faction name cannot be empty")

        if len(self.name) > 200:
            errors.append("Faction name cannot exceed 200 characters")

        if not 0 <= self.influence <= 100:
            errors.append("Influence must be between 0 and 100")

        if not 0 <= self.military_strength <= 100:
            errors.append("Military strength must be between 0 and 100")

        if not 0 <= self.economic_power <= 100:
            errors.append("Economic power must be between 0 and 100")

        if self.member_count < 0:
            errors.append("Member count cannot be negative")

        if len(self.values) > 10:
            errors.append("Cannot have more than 10 values")

        if len(self.goals) > 10:
            errors.append("Cannot have more than 10 goals")

        # Validate alignment consistency with type
        errors.extend(self._validate_type_alignment_consistency())

        # Validate relations
        errors.extend(self._validate_relations())

        return errors

    def _validate_type_alignment_consistency(self) -> List[str]:
        """Validate that faction type and alignment are consistent."""
        errors: List[str] = []

        # Religious factions typically aren't chaotic evil
        if (
            self.faction_type == FactionType.RELIGIOUS
            and self.alignment == FactionAlignment.CHAOTIC_EVIL
        ):
            # Warning but allowed - could be a dark cult
            pass

        # Guilds are typically lawful
        lawful_alignments = {
            FactionAlignment.LAWFUL_GOOD,
            FactionAlignment.LAWFUL_NEUTRAL,
            FactionAlignment.LAWFUL_EVIL,
        }
        if (
            self.faction_type == FactionType.GUILD
            and self.alignment not in lawful_alignments
        ):
            # This is allowed but noted
            pass

        return errors

    def _validate_relations(self) -> List[str]:
        """Validate faction relationships."""
        errors = []

        seen_targets: Set[str] = set()
        for relation in self.relations:
            if relation.target_faction_id in seen_targets:
                errors.append(
                    f"Duplicate relation with faction {relation.target_faction_id}"
                )
            seen_targets.add(relation.target_faction_id)

            if not -100 <= relation.strength <= 100:
                errors.append(
                    f"Relation strength with {relation.target_faction_id} must be -100 to 100"
                )

        return errors

    def add_relation(self, relation: FactionRelation) -> None:
        """
        Add or update a relationship with another faction.

        Args:
            relation: The relationship to add/update
        """
        # Remove existing relation if present
        self.relations = [
            r
            for r in self.relations
            if r.target_faction_id != relation.target_faction_id
        ]
        self.relations.append(relation)
        self.touch()

    def remove_relation(self, target_faction_id: str) -> bool:
        """
        Remove a relationship with another faction.

        Args:
            target_faction_id: ID of the faction to remove relation with

        Returns:
            True if relation was removed, False if not found
        """
        original_count = len(self.relations)
        self.relations = [
            r for r in self.relations if r.target_faction_id != target_faction_id
        ]
        if len(self.relations) < original_count:
            self.touch()
            return True
        return False

    def get_relation(self, target_faction_id: str) -> Optional[FactionRelation]:
        """
        Get the relationship with a specific faction.

        Args:
            target_faction_id: ID of the target faction

        Returns:
            The FactionRelation if found, None otherwise
        """
        for relation in self.relations:
            if relation.target_faction_id == target_faction_id:
                return relation
        return None

    def get_allies(self) -> List[FactionRelation]:
        """Get all allied factions."""
        return [r for r in self.relations if r.is_friendly()]

    def get_enemies(self) -> List[FactionRelation]:
        """Get all enemy factions."""
        return [r for r in self.relations if r.is_hostile()]

    def add_goal(self, goal: str) -> None:
        """
        Add a goal to the faction.

        Args:
            goal: The goal to add

        Raises:
            ValueError: If goal limit exceeded
        """
        if not goal or not goal.strip():
            raise ValueError("Goal cannot be empty")

        goal = goal.strip()
        if goal in self.goals:
            return

        if len(self.goals) >= 10:
            raise ValueError("Cannot have more than 10 goals")

        self.goals.append(goal)
        self.touch()

    def remove_goal(self, goal: str) -> bool:
        """
        Remove a goal from the faction.

        Args:
            goal: The goal to remove

        Returns:
            True if removed, False if not found
        """
        goal = goal.strip()
        if goal in self.goals:
            self.goals.remove(goal)
            self.touch()
            return True
        return False

    def add_territory(self, location_id: str) -> None:
        """
        Add a territory to the faction's control.

        Args:
            location_id: ID of the location to add
        """
        if location_id not in self.territories:
            self.territories.append(location_id)
            self.touch()

    def remove_territory(self, location_id: str) -> bool:
        """
        Remove a territory from the faction's control.

        Args:
            location_id: ID of the location to remove

        Returns:
            True if removed, False if not found
        """
        if location_id in self.territories:
            self.territories.remove(location_id)
            self.touch()
            return True
        return False

    def update_influence(self, delta: int) -> None:
        """
        Update the faction's influence level.

        Args:
            delta: Amount to change influence by (positive or negative)
        """
        new_influence = max(0, min(100, self.influence + delta))
        if new_influence != self.influence:
            self.influence = new_influence
            self.touch()

    def update_status(self, new_status: FactionStatus) -> None:
        """
        Update the faction's status.

        Args:
            new_status: New status for the faction
        """
        if new_status != self.status:
            self.status = new_status
            self.touch()

    def get_power_rating(self) -> float:
        """
        Calculate overall power rating of the faction.

        Returns:
            Power rating from 0 to 100
        """
        return (
            self.influence * 0.4
            + self.military_strength * 0.35
            + self.economic_power * 0.25
        )

    def is_major_power(self) -> bool:
        """Check if faction is a major power (power rating >= 70)."""
        return self.get_power_rating() >= 70

    def is_minor_faction(self) -> bool:
        """Check if faction is a minor faction (power rating < 30)."""
        return self.get_power_rating() < 30

    def set_leader(self, character_id: str, leader_name: Optional[str] = None) -> None:
        """Set the faction leader.

        Why track both ID and name: ID enables system lookups and cross-references,
        while name provides human-readable display without requiring a lookup.

        Args:
            character_id: The unique identifier of the character becoming leader
            leader_name: Optional display name for the leader
        """
        if not character_id or not character_id.strip():
            raise ValueError("Leader character ID cannot be empty")

        self.leader_id = character_id
        if leader_name:
            self.leader_name = leader_name
        self.touch()

    def remove_leader(self) -> bool:
        """Remove the current faction leader.

        Returns:
            True if a leader was removed, False if there was no leader
        """
        if self.leader_id is None:
            return False

        self.leader_id = None
        self.leader_name = None
        self.touch()
        return True

    def get_leader_id(self) -> Optional[str]:
        """Get the leader's character ID.

        Returns:
            The leader's character ID or None if no leader is set
        """
        return self.leader_id

    def has_leader(self) -> bool:
        """Check if the faction has a leader."""
        return self.leader_id is not None

    def _to_dict_specific(self) -> Dict[str, Any]:
        """Convert Faction-specific data to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "faction_type": self.faction_type.value,
            "alignment": self.alignment.value,
            "status": self.status.value,
            "headquarters_id": self.headquarters_id,
            "leader_name": self.leader_name,
            "leader_id": self.leader_id,
            "founding_date": self.founding_date,
            "values": self.values,
            "goals": self.goals,
            "resources": self.resources,
            "influence": self.influence,
            "military_strength": self.military_strength,
            "economic_power": self.economic_power,
            "relations": [
                {
                    "target_faction_id": r.target_faction_id,
                    "relation_type": r.relation_type,
                    "strength": r.strength,
                    "description": r.description,
                }
                for r in self.relations
            ],
            "member_count": self.member_count,
            "territories": self.territories,
        }

    @classmethod
    def create_kingdom(
        cls,
        name: str,
        description: str = "",
        alignment: FactionAlignment = FactionAlignment.LAWFUL_NEUTRAL,
    ) -> "Faction":
        """Create a kingdom faction with typical royal attributes.

        Factory method that creates a pre-configured Faction representing
        a sovereign nation with high influence and large population.

        Args:
            name: The kingdom's name.
            description: Optional detailed description.
            alignment: Moral alignment. Defaults to LAWFUL_NEUTRAL.

        Returns:
            A new Faction configured as a kingdom.

        Example:
            >>> kingdom = Faction.create_kingdom(
            ...     name="Valdris",
            ...     description="A realm of scholars and warriors."
            ... )
        """
        return cls(
            name=name,
            description=description,
            faction_type=FactionType.KINGDOM,
            alignment=alignment,
            influence=70,
            military_strength=60,
            economic_power=65,
            member_count=100000,
        )

    @classmethod
    def create_guild(
        cls,
        name: str,
        description: str = "",
        guild_focus: str = "trade",
    ) -> "Faction":
        """Create a guild faction with typical professional organization attributes.

        Factory method that creates a pre-configured Faction representing
        a professional guild with high economic power and lawful alignment.

        Args:
            name: The guild's name.
            description: Optional detailed description.
            guild_focus: Primary focus area (e.g., "trade", "crafting", "magic").
                Defaults to "trade".

        Returns:
            A new Faction configured as a guild.

        Example:
            >>> guild = Faction.create_guild(
            ...     name="Blacksmiths' Union",
            ...     guild_focus="crafting"
            ... )
        """
        return cls(
            name=name,
            description=description,
            faction_type=FactionType.GUILD,
            alignment=FactionAlignment.LAWFUL_NEUTRAL,
            influence=40,
            military_strength=20,
            economic_power=70,
            member_count=500,
            values=[guild_focus, "profit", "expertise"],
        )

    @classmethod
    def create_cult(
        cls,
        name: str,
        description: str = "",
        alignment: FactionAlignment = FactionAlignment.CHAOTIC_EVIL,
    ) -> "Faction":
        """Create a cult faction with typical secretive organization attributes.

        Factory method that creates a pre-configured Faction representing
        a cult with hidden status, moderate military strength, and small membership.

        Args:
            name: The cult's name.
            description: Optional detailed description.
            alignment: Moral alignment. Defaults to CHAOTIC_EVIL.

        Returns:
            A new Faction configured as a cult.

        Example:
            >>> cult = Faction.create_cult(
            ...     name="Followers of the Void",
            ...     alignment=FactionAlignment.NEUTRAL_EVIL
            ... )
        """
        return cls(
            name=name,
            description=description,
            faction_type=FactionType.CULT,
            alignment=alignment,
            status=FactionStatus.HIDDEN,
            influence=20,
            military_strength=30,
            economic_power=15,
            member_count=50,
        )
