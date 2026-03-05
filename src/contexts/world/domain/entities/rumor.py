#!/usr/bin/env python3
"""Rumor Domain Entity.

This module defines the Rumor entity which represents a piece of information
that spreads through the world, decaying in truth value as it propagates.
Rumors can originate from events, NPCs, players, or unknown sources.

Typical usage example:
    >>> from src.contexts.world.domain.entities import Rumor, RumorOrigin
    >>> from src.contexts.world.domain.value_objects import WorldCalendar
    >>> calendar = WorldCalendar(1042, 3, 15, "Third Age")
    >>> rumor = Rumor(
    ...     content="Word spreads of a great battle in the north...",
    ...     truth_value=90,
    ...     origin_type=RumorOrigin.EVENT,
    ...     origin_location_id="loc-north-pass",
    ...     created_date=calendar
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# Use TYPE_CHECKING to avoid circular import
from typing import TYPE_CHECKING, Any, Dict, Optional, Set
from uuid import uuid4

if TYPE_CHECKING:
    from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar


class RumorOrigin(Enum):
    """Classification of rumor origin types.

    Categorizes where a rumor originated from, which affects
    its initial truth value and how it spreads.

    Attributes:
        EVENT: Originated from a historical event (high truth value).
        NPC: Originated from an NPC character (variable truth value).
        PLAYER: Originated from a player action (variable truth value).
        UNKNOWN: Origin is unknown or unclear (lower initial truth).
    """

    EVENT = "event"
    NPC = "npc"
    PLAYER = "player"
    UNKNOWN = "unknown"


# Truth decay per hop (spread)
TRUTH_DECAY_PER_HOP = 10

# Veracity thresholds
VERACITY_CONFIRMED = 80
VERACITY_LIKELY_TRUE = 60
VERACITY_UNCERTAIN = 40
VERACITY_LIKELY_FALSE = 20


@dataclass(frozen=True)
class Rumor:
    """Rumor Entity (Immutable).

    Represents a piece of information that spreads through the world.
    Truth value decays as the rumor spreads from location to location.

    Why frozen: Rumors are immutable records of information spreading.
    When a rumor spreads, a new Rumor instance is created with updated
    values (see spread_to() method).

    Attributes:
        rumor_id: Unique identifier for this rumor (UUID).
        content: The text content of the rumor.
        truth_value: Truth percentage (0-100, 100 = completely true).
        origin_type: Where the rumor originated from.
        source_event_id: ID of the source event if origin is EVENT.
        origin_location_id: ID of the location where rumor started.
        current_locations: Set of location IDs where rumor has spread.
        created_date: WorldCalendar when the rumor was created.
        spread_count: Number of times the rumor has spread.
    """

    rumor_id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    truth_value: int = 50
    origin_type: RumorOrigin = RumorOrigin.UNKNOWN
    source_event_id: Optional[str] = None
    origin_location_id: str = ""
    current_locations: Set[str] = field(default_factory=set)
    created_date: Optional["WorldCalendar"] = None
    spread_count: int = 0

    def __post_init__(self) -> None:
        """Validate rumor after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate the rumor's invariants.

        Raises:
            ValueError: If any validation rule is violated.
        """
        errors: list[Any] = []
        if not self.rumor_id:
            errors.append("Rumor ID cannot be empty")

        if not self.content or not self.content.strip():
            errors.append("Content cannot be empty")

        if not 0 <= self.truth_value <= 100:
            errors.append(
                f"Truth value must be between 0 and 100, got {self.truth_value}"
            )

        if not self.origin_location_id:
            errors.append("Origin location ID cannot be empty")

        if errors:
            raise ValueError(f"Rumor validation failed: {'; '.join(errors)}")

    def truth_after_spread(self) -> int:
        """Calculate truth value after one spread hop.

        Each spread reduces truth value by TRUTH_DECAY_PER_HOP (default 10),
        minimum 0.

        Returns:
            Truth value after spread (0-100).
        """
        return max(0, self.truth_value - TRUTH_DECAY_PER_HOP)

    def spread_to(self, location_id: str) -> "Rumor":
        """Create a new rumor spread to a new location.

        The new rumor has decreased truth value and updated spread count.
        The original rumor is not modified (immutability pattern).

        Args:
            location_id: ID of the location to spread to.

        Returns:
            A new Rumor instance with updated location and truth value.

        Raises:
            ValueError: If location_id is empty.
        """
        if not location_id or not location_id.strip():
            raise ValueError("Location ID cannot be empty")

        new_truth = self.truth_after_spread()
        new_locations = self.current_locations | {location_id}

        return Rumor(
            rumor_id=self.rumor_id,  # Same rumor, just spread
            content=self.content,
            truth_value=new_truth,
            origin_type=self.origin_type,
            source_event_id=self.source_event_id,
            origin_location_id=self.origin_location_id,
            current_locations=new_locations,
            created_date=self.created_date,
            spread_count=self.spread_count + 1,
        )

    @property
    def veracity_label(self) -> str:
        """Get human-readable veracity label based on truth value.

        Returns:
            Label string: 'Confirmed', 'Likely True', 'Uncertain',
            'Likely False', or 'False'.
        """
        if self.truth_value >= VERACITY_CONFIRMED:
            return "Confirmed"
        elif self.truth_value >= VERACITY_LIKELY_TRUE:
            return "Likely True"
        elif self.truth_value >= VERACITY_UNCERTAIN:
            return "Uncertain"
        elif self.truth_value >= VERACITY_LIKELY_FALSE:
            return "Likely False"
        else:
            return "False"

    @property
    def is_dead(self) -> bool:
        """Check if rumor has no truth value left.

        Returns:
            True if truth_value is 0, False otherwise.
        """
        return self.truth_value == 0

    @property
    def veracity_color(self) -> str:
        """Get color code for veracity display.

        Returns:
            Hex color code for UI display.
        """
        if self.truth_value >= VERACITY_CONFIRMED:
            return "#22c55e"  # green
        elif self.truth_value >= VERACITY_LIKELY_TRUE:
            return "#84cc16"  # lime
        elif self.truth_value >= VERACITY_UNCERTAIN:
            return "#eab308"  # yellow
        elif self.truth_value >= VERACITY_LIKELY_FALSE:
            return "#f97316"  # orange
        else:
            return "#6b7280"  # gray

    def to_dict(self) -> Dict[str, Any]:
        """Convert rumor to dictionary representation.

        Returns:
            Dictionary representation of the rumor.
        """
        created_date_dict = None
        if self.created_date is not None:
            if hasattr(self.created_date, "to_dict"):
                created_date_dict = self.created_date.to_dict()
            else:
                created_date_dict = str(self.created_date)

        return {
            "rumor_id": self.rumor_id,
            "content": self.content,
            "truth_value": self.truth_value,
            "origin_type": self.origin_type.value,
            "source_event_id": self.source_event_id,
            "origin_location_id": self.origin_location_id,
            "current_locations": list(self.current_locations),
            "created_date": created_date_dict,
            "spread_count": self.spread_count,
            "veracity_label": self.veracity_label,
            "is_dead": self.is_dead,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rumor":
        """Create a Rumor from a dictionary.

        Args:
            data: Dictionary containing rumor data.

        Returns:
            A new Rumor instance.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        # Handle origin_type parsing
        origin_type = data.get("origin_type")
        if isinstance(origin_type, str):
            origin_type = RumorOrigin(origin_type.lower())
        elif not isinstance(origin_type, RumorOrigin):
            origin_type = RumorOrigin.UNKNOWN

        # Handle current_locations parsing
        current_locations = data.get("current_locations", [])
        if isinstance(current_locations, list):
            current_locations = set(current_locations)
        elif not isinstance(current_locations, set):
            current_locations: set[Any] = set()
        # Handle created_date - keep as-is for now (could be dict or WorldCalendar)
        created_date = data.get("created_date")

        return cls(
            rumor_id=data.get("rumor_id", str(uuid4())),
            content=data.get("content", ""),
            truth_value=data.get("truth_value", 50),
            origin_type=origin_type,
            source_event_id=data.get("source_event_id"),
            origin_location_id=data.get("origin_location_id", ""),
            current_locations=current_locations,
            created_date=created_date,
            spread_count=data.get("spread_count", 0),
        )

    def __str__(self) -> str:
        """Return string representation of the rumor.

        Returns:
            String representation showing content preview and veracity.
        """
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"Rumor({preview}, truth={self.truth_value}%, {self.veracity_label})"

    def __repr__(self) -> str:
        """Return detailed string representation.

        Returns:
            Detailed string representation of the rumor.
        """
        return (
            f"Rumor(rumor_id={self.rumor_id[:8]}..., "
            f"origin={self.origin_type.value}, "
            f"truth={self.truth_value}%, spread_count={self.spread_count})"
        )

    def __hash__(self) -> int:
        """Make Rumor hashable for use in sets/dicts.

        Note: This uses rumor_id as the hash key, assuming same ID = same rumor.

        Returns:
            Hash value based on rumor_id.
        """
        return hash(self.rumor_id)

    def __eq__(self, other: object) -> bool:
        """Check equality based on rumor_id.

        Args:
            other: Another object to compare with.

        Returns:
            True if both have the same rumor_id, False otherwise.
        """
        if not isinstance(other, Rumor):
            return False
        return self.rumor_id == other.rumor_id
