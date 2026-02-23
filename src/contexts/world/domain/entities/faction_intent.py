#!/usr/bin/env python3
"""FactionIntent Domain Entity.

This module defines the FactionIntent entity which represents a faction's
intended action within the world simulation. Intents are generated based
on world state and faction characteristics, then resolved during simulation.

Typical usage example:
    >>> from src.contexts.world.domain.entities import FactionIntent, IntentType
    >>> intent = FactionIntent(
    ...     faction_id="faction-uuid",
    ...     intent_type=IntentType.EXPAND,
    ...     target_id="location-uuid",
    ...     priority=5,
    ...     narrative="Expand territory into the eastern plains"
    ... )
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4


class IntentType(Enum):
    """Classification of faction intent types.

    Categorizes the different strategic actions a faction can intend
    to take during simulation ticks.

    Attributes:
        EXPAND: Grow territory by claiming new locations.
        ATTACK: Initiate conflict with an enemy faction.
        DEFEND: Fortify against potential threats.
        ALLY: Seek alliance with another faction.
        TRADE: Establish trade relationships.
        RECOVER: Rebuild resources and stability.
        CONSOLIDATE: Focus on internal affairs and consolidation.
    """

    EXPAND = "expand"
    ATTACK = "attack"
    DEFEND = "defend"
    ALLY = "ally"
    TRADE = "trade"
    RECOVER = "recover"
    CONSOLIDATE = "consolidate"


# Define offensive and defensive intent sets
OFFENSIVE_INTENTS = {IntentType.ATTACK, IntentType.EXPAND}
DEFENSIVE_INTENTS = {IntentType.DEFEND, IntentType.CONSOLIDATE}


@dataclass(frozen=True)
class FactionIntent:
    """FactionIntent Entity.

    Represents a faction's intended action within the simulation.
    Uses frozen=True for immutability - intents are created, not modified.

    Attributes:
        intent_id: Unique identifier for this intent (UUID).
        faction_id: ID of the faction that has this intent.
        intent_type: Classification of the intent (EXPAND, ATTACK, etc.).
        target_id: ID of target (faction_id or location_id), optional.
        priority: Importance level (1-10, higher = more important).
        narrative: Human-readable description of the intent.
        created_at: Timestamp when the intent was created.
    """

    intent_id: str = field(default_factory=lambda: str(uuid4()))
    faction_id: str = ""
    intent_type: IntentType = IntentType.CONSOLIDATE
    target_id: Optional[str] = None
    priority: int = 1
    narrative: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate intent after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate the intent's invariants.

        Raises:
            ValueError: If any validation rule is violated.
        """
        errors = []

        if not self.intent_id:
            errors.append("Intent ID cannot be empty")

        if not self.faction_id:
            errors.append("Faction ID cannot be empty")

        # Note: intent_type is already typed as IntentType, so no runtime check needed

        if not 1 <= self.priority <= 10:
            errors.append(f"Priority must be between 1 and 10, got {self.priority}")

        if not self.narrative or not self.narrative.strip():
            errors.append("Narrative cannot be empty")

        if errors:
            raise ValueError(f"FactionIntent validation failed: {'; '.join(errors)}")

    @property
    def is_offensive(self) -> bool:
        """Check if this intent is offensive in nature.

        Offensive intents include ATTACK and EXPAND.

        Returns:
            True if the intent is offensive, False otherwise.
        """
        return self.intent_type in OFFENSIVE_INTENTS

    @property
    def is_defensive(self) -> bool:
        """Check if this intent is defensive in nature.

        Defensive intents include DEFEND and CONSOLIDATE.

        Returns:
            True if the intent is defensive, False otherwise.
        """
        return self.intent_type in DEFENSIVE_INTENTS

    def to_dict(self) -> Dict[str, Any]:
        """Convert intent to dictionary representation.

        Returns:
            Dictionary representation of the intent.
        """
        return {
            "intent_id": self.intent_id,
            "faction_id": self.faction_id,
            "intent_type": self.intent_type.value,
            "target_id": self.target_id,
            "priority": self.priority,
            "narrative": self.narrative,
            "created_at": self.created_at.isoformat(),
            "is_offensive": self.is_offensive,
            "is_defensive": self.is_defensive,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactionIntent":
        """Create a FactionIntent from a dictionary.

        Args:
            data: Dictionary containing intent data.

        Returns:
            A new FactionIntent instance.

        Raises:
            ValueError: If required fields are missing or invalid.
        """
        # Handle created_at parsing
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        # Handle intent_type parsing
        intent_type = data.get("intent_type")
        if isinstance(intent_type, str):
            intent_type = IntentType(intent_type.lower())
        elif not isinstance(intent_type, IntentType):
            intent_type = IntentType.CONSOLIDATE

        return cls(
            intent_id=data.get("intent_id", str(uuid4())),
            faction_id=data.get("faction_id", ""),
            intent_type=intent_type,
            target_id=data.get("target_id"),
            priority=data.get("priority", 1),
            narrative=data.get("narrative", ""),
            created_at=created_at,
        )

    def __str__(self) -> str:
        """Return string representation of the intent.

        Returns:
            String representation showing intent type and faction.
        """
        return f"FactionIntent({self.faction_id[:8]}... -> {self.intent_type.value}, priority={self.priority})"

    def __repr__(self) -> str:
        """Return detailed string representation.

        Returns:
            Detailed string representation of the intent.
        """
        return (
            f"FactionIntent(intent_id={self.intent_id[:8]}..., "
            f"faction_id={self.faction_id[:8]}..., "
            f"type={self.intent_type.value}, priority={self.priority})"
        )
