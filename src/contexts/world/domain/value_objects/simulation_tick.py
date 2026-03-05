#!/usr/bin/env python3
"""
SimulationTick Value Object

This module provides value objects for recording simulation step results.
These value objects capture the state changes that occur during a single
simulation tick, including resource changes, diplomacy changes, and events.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar


@dataclass(frozen=True)
class ResourceChanges:
    """Resource changes for a faction during a simulation tick.

    Records the delta changes to a faction's resources (wealth, military,
    influence) resulting from intent resolution during a simulation tick.

    Attributes:
        wealth_delta: Change in economic power (-100 to 100).
        military_delta: Change in military strength (-100 to 100).
        influence_delta: Change in influence (-100 to 100).
    """

    wealth_delta: int = 0
    military_delta: int = 0
    influence_delta: int = 0

    def __post_init__(self) -> None:
        """Validate resource change values."""
        errors = []

        if not -100 <= self.wealth_delta <= 100:
            errors.append(f"Wealth delta must be -100 to 100, got {self.wealth_delta}")

        if not -100 <= self.military_delta <= 100:
            errors.append(
                f"Military delta must be -100 to 100, got {self.military_delta}"
            )

        if not -100 <= self.influence_delta <= 100:
            errors.append(
                f"Influence delta must be -100 to 100, got {self.influence_delta}"
            )

        if errors:
            raise ValueError(f"Invalid ResourceChanges: {'; '.join(errors)}")

    @property
    def has_changes(self) -> bool:
        """Check if any resource changes occurred.

        Returns:
            True if any delta is non-zero, False otherwise.
        """
        return (
            self.wealth_delta != 0
            or self.military_delta != 0
            or self.influence_delta != 0
        )

    @property
    def total_change(self) -> int:
        """Get the sum of all absolute changes.

        Returns:
            Sum of absolute values of all deltas.
        """
        return (
            abs(self.wealth_delta)
            + abs(self.military_delta)
            + abs(self.influence_delta)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with resource delta values.
        """
        return {
            "wealth_delta": self.wealth_delta,
            "military_delta": self.military_delta,
            "influence_delta": self.influence_delta,
            "has_changes": self.has_changes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceChanges":
        """Create ResourceChanges from dictionary.

        Args:
            data: Dictionary containing resource change data.

        Returns:
            New ResourceChanges instance.
        """
        return cls(
            wealth_delta=data.get("wealth_delta", 0),
            military_delta=data.get("military_delta", 0),
            influence_delta=data.get("influence_delta", 0),
        )


@dataclass(frozen=True)
class DiplomacyChange:
    """Diplomacy status change between two factions.

    Records a change in diplomatic status between two factions during
    a simulation tick.

    Attributes:
        faction_a: ID of the first faction.
        faction_b: ID of the second faction.
        status_before: Diplomatic status before the change.
        status_after: Diplomatic status after the change.
    """

    faction_a: str
    faction_b: str
    status_before: DiplomaticStatus
    status_after: DiplomaticStatus

    def __post_init__(self) -> None:
        """Validate diplomacy change values."""
        errors = []

        if not self.faction_a or not self.faction_a.strip():
            errors.append("Faction A ID cannot be empty")

        if not self.faction_b or not self.faction_b.strip():
            errors.append("Faction B ID cannot be empty")

        if self.faction_a == self.faction_b:
            errors.append("Faction A and B cannot be the same")

        if errors:
            raise ValueError(f"Invalid DiplomacyChange: {'; '.join(errors)}")

    @property
    def is_significant(self) -> bool:
        """Check if the change is significant.

        A significant change is one that crosses a major boundary
        (e.g., neutral to hostile, allied to at_war).

        Returns:
            True if the change crosses a major boundary.
        """
        # Significant changes involve crossing between positive/neutral/negative
        positive = {DiplomaticStatus.ALLIED, DiplomaticStatus.FRIENDLY}
        negative = {DiplomaticStatus.HOSTILE, DiplomaticStatus.AT_WAR}

        before_positive = self.status_before in positive
        before_negative = self.status_before in negative
        after_positive = self.status_after in positive
        after_negative = self.status_after in negative

        # Significant if crossing from positive to negative or vice versa
        return (before_positive and after_negative) or (
            before_negative and after_positive
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with diplomacy change data.
        """
        return {
            "faction_a": self.faction_a,
            "faction_b": self.faction_b,
            "status_before": self.status_before.value,
            "status_after": self.status_after.value,
            "is_significant": self.is_significant,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiplomacyChange":
        """Create DiplomacyChange from dictionary.

        Args:
            data: Dictionary containing diplomacy change data.

        Returns:
            New DiplomacyChange instance.
        """
        return cls(
            faction_a=data["faction_a"],
            faction_b=data["faction_b"],
            status_before=DiplomaticStatus(data["status_before"]),
            status_after=DiplomaticStatus(data["status_after"]),
        )


@dataclass(frozen=True)
class SimulationTick:
    """Value object recording simulation step results.

    Captures all state changes that occurred during a single simulation tick,
    including calendar advancement, events generated, resource changes,
    diplomacy changes, and character reactions.

    This value object is immutable and serves as a historical record of
    what happened during a specific simulation step.

    Attributes:
        tick_id: Unique identifier for this tick (UUID).
        world_id: ID of the world this tick belongs to.
        calendar_before: Calendar state before the tick.
        calendar_after: Calendar state after the tick.
        days_advanced: Number of days advanced in this tick.
        events_generated: List of event IDs generated during this tick.
        resource_changes: Dict mapping faction_id to ResourceChanges.
        diplomacy_changes: List of DiplomacyChange records.
        character_reactions: List of character IDs that reacted to events.
        rumors_created: Number of rumors created during this tick.
        created_at: Timestamp when this tick record was created.
    """

    tick_id: str = field(default_factory=lambda: str(uuid4()))
    world_id: str = ""
    calendar_before: Optional[WorldCalendar] = None
    calendar_after: Optional[WorldCalendar] = None
    days_advanced: int = 0
    events_generated: List[str] = field(default_factory=list)
    resource_changes: Dict[str, ResourceChanges] = field(default_factory=dict)
    diplomacy_changes: List[DiplomacyChange] = field(default_factory=list)
    character_reactions: List[str] = field(default_factory=list)
    rumors_created: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate simulation tick values."""
        errors = []

        if not self.tick_id:
            errors.append("Tick ID cannot be empty")

        if not self.world_id:
            errors.append("World ID cannot be empty")

        if self.days_advanced < 0:
            errors.append(f"Days advanced must be >= 0, got {self.days_advanced}")

        if self.rumors_created < 0:
            errors.append(f"Rumors created must be >= 0, got {self.rumors_created}")

        if errors:
            raise ValueError(f"Invalid SimulationTick: {'; '.join(errors)}")

    @property
    def has_changes(self) -> bool:
        """Check if any changes occurred during this tick.

        Returns:
            True if any events, resource changes, diplomacy changes,
            character reactions, or rumors occurred.
        """
        return bool(
            self.events_generated
            or self.resource_changes
            or self.diplomacy_changes
            or self.character_reactions
            or self.rumors_created > 0
            or self.days_advanced > 0
        )

    @property
    def total_resource_changes(self) -> int:
        """Get total number of factions with resource changes.

        Returns:
            Number of factions with non-zero resource changes.
        """
        return sum(
            1 for changes in self.resource_changes.values() if changes.has_changes
        )

    @property
    def total_diplomacy_changes(self) -> int:
        """Get total number of diplomacy changes.

        Returns:
            Number of diplomacy changes.
        """
        return len(self.diplomacy_changes)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all tick data.
        """
        return {
            "tick_id": self.tick_id,
            "world_id": self.world_id,
            "calendar_before": (
                self.calendar_before.to_dict() if self.calendar_before else None
            ),
            "calendar_after": (
                self.calendar_after.to_dict() if self.calendar_after else None
            ),
            "days_advanced": self.days_advanced,
            "events_generated": self.events_generated,
            "resource_changes": {
                k: v.to_dict() for k, v in self.resource_changes.items()
            },
            "diplomacy_changes": [dc.to_dict() for dc in self.diplomacy_changes],
            "character_reactions": self.character_reactions,
            "rumors_created": self.rumors_created,
            "created_at": self.created_at.isoformat(),
            "has_changes": self.has_changes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulationTick":
        """Create SimulationTick from dictionary.

        Args:
            data: Dictionary containing tick data.

        Returns:
            New SimulationTick instance.
        """
        # Parse calendar objects
        calendar_before = None
        if data.get("calendar_before"):
            calendar_before = WorldCalendar.from_dict(data["calendar_before"])

        calendar_after = None
        if data.get("calendar_after"):
            calendar_after = WorldCalendar.from_dict(data["calendar_after"])

        # Parse resource changes
        resource_changes: Dict[str, ResourceChanges] = {}
        for faction_id, changes_data in data.get("resource_changes", {}).items():
            resource_changes[faction_id] = ResourceChanges.from_dict(changes_data)

        # Parse diplomacy changes
        diplomacy_changes = [
            DiplomacyChange.from_dict(dc) for dc in data.get("diplomacy_changes", [])
        ]

        # Parse created_at
        created_at = datetime.now()
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])

        return cls(
            tick_id=data.get("tick_id", str(uuid4())),
            world_id=data.get("world_id", ""),
            calendar_before=calendar_before,
            calendar_after=calendar_after,
            days_advanced=data.get("days_advanced", 0),
            events_generated=data.get("events_generated", []),
            resource_changes=resource_changes,
            diplomacy_changes=diplomacy_changes,
            character_reactions=data.get("character_reactions", []),
            rumors_created=data.get("rumors_created", 0),
            created_at=created_at,
        )
