#!/usr/bin/env python3
"""
Geopolitics Domain Events

Domain events for geopolitical actions including war declarations,
alliance formations, and territory transfers.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from uuid import uuid4

import structlog

from src.events.event_bus import Event, EventPriority

logger = structlog.get_logger()


class PactType(Enum):
    """Types of diplomatic pacts."""

    DEFENSIVE_ALLIANCE = "defensive_alliance"
    OFFENSIVE_ALLIANCE = "offensive_alliance"
    NON_AGGRESSION = "non_aggression"
    TRADE_AGREEMENT = "trade_agreement"
    RESEARCH_AGREEMENT = "research_agreement"


@dataclass
class WarDeclaredEvent(Event):
    """Domain event emitted when war is declared between factions."""

    event_type: str = field(default="geopolitics.war_declared", init=False)
    source: str = field(default="geopolitics_service", init=False)
    priority: EventPriority = field(default=EventPriority.HIGH, init=False)

    aggressor_id: str = ""
    defender_id: str = ""
    reason: str = ""
    world_id: Optional[str] = None

    def __post_init__(self) -> None:
        # Note: timestamp is initialized by parent Event class default
        if not self.event_id:
            object.__setattr__(self, "event_id", str(uuid4()))

        self.tags.update(
            {
                "context:world",
                "event:war_declared",
                f"aggressor:{self.aggressor_id}",
                f"defender:{self.defender_id}",
            }
        )
        if self.world_id:
            self.tags.add(f"world:{self.world_id}")

        self.payload.update(
            {
                "aggressor_id": self.aggressor_id,
                "defender_id": self.defender_id,
                "reason": self.reason,
                "world_id": self.world_id,
            }
        )
        super().__post_init__()

    @classmethod
    def create(
        cls,
        aggressor_id: str,
        defender_id: str,
        reason: str,
        world_id: Optional[str] = None,
    ) -> "WarDeclaredEvent":
        return cls(
            aggressor_id=aggressor_id,
            defender_id=defender_id,
            reason=reason,
            world_id=world_id,
        )


@dataclass
class AllianceFormedEvent(Event):
    """Domain event emitted when an alliance is formed."""

    event_type: str = field(default="geopolitics.alliance_formed", init=False)
    source: str = field(default="geopolitics_service", init=False)
    priority: EventPriority = field(default=EventPriority.NORMAL, init=False)

    faction_a_id: str = ""
    faction_b_id: str = ""
    pact_type: PactType = PactType.DEFENSIVE_ALLIANCE
    world_id: Optional[str] = None

    def __post_init__(self) -> None:
        # Note: timestamp is initialized by parent Event class default
        if not self.event_id:
            object.__setattr__(self, "event_id", str(uuid4()))

        self.tags.update(
            {
                "context:world",
                "event:alliance_formed",
                f"faction_a:{self.faction_a_id}",
                f"faction_b:{self.faction_b_id}",
            }
        )
        if self.world_id:
            self.tags.add(f"world:{self.world_id}")

        self.payload.update(
            {
                "faction_a_id": self.faction_a_id,
                "faction_b_id": self.faction_b_id,
                "pact_type": self.pact_type.value,
                "world_id": self.world_id,
            }
        )
        super().__post_init__()

    @classmethod
    def create(
        cls,
        faction_a_id: str,
        faction_b_id: str,
        pact_type: PactType,
        world_id: Optional[str] = None,
    ) -> "AllianceFormedEvent":
        return cls(
            faction_a_id=faction_a_id,
            faction_b_id=faction_b_id,
            pact_type=pact_type,
            world_id=world_id,
        )


@dataclass
class TerritoryChangedEvent(Event):
    """Domain event emitted when territory control changes."""

    event_type: str = field(default="geopolitics.territory_changed", init=False)
    source: str = field(default="geopolitics_service", init=False)
    priority: EventPriority = field(default=EventPriority.NORMAL, init=False)

    location_id: str = ""
    previous_controller_id: Optional[str] = None
    new_controller_id: Optional[str] = None
    reason: str = ""
    world_id: Optional[str] = None

    def __post_init__(self) -> None:
        # Note: timestamp is initialized by parent Event class default
        if not self.event_id:
            object.__setattr__(self, "event_id", str(uuid4()))

        self.tags.update(
            {
                "context:world",
                "event:territory_changed",
                f"location:{self.location_id}",
            }
        )
        if self.world_id:
            self.tags.add(f"world:{self.world_id}")

        self.payload.update(
            {
                "location_id": self.location_id,
                "previous_controller_id": self.previous_controller_id,
                "new_controller_id": self.new_controller_id,
                "reason": self.reason,
                "world_id": self.world_id,
            }
        )
        super().__post_init__()

    @classmethod
    def create(
        cls,
        location_id: str,
        previous_controller_id: Optional[str],
        new_controller_id: Optional[str],
        world_id: Optional[str] = None,
        reason: str = "",
    ) -> "TerritoryChangedEvent":
        return cls(
            location_id=location_id,
            previous_controller_id=previous_controller_id,
            new_controller_id=new_controller_id,
            world_id=world_id,
            reason=reason,
        )
