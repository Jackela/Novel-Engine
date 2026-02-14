#!/usr/bin/env python3
"""World Domain Entities.

This module exports all domain entities for the World context.
"""

from .entity import Entity
from .faction import (
    Faction,
    FactionAlignment,
    FactionRelation,
    FactionStatus,
    FactionType,
)
from .history_event import (
    EventOutcome,
    EventSignificance,
    EventType,
    HistoryEvent,
)
from .item import (
    Item,
    ItemRarity,
    ItemType,
)
from .location import (
    ClimateType,
    Location,
    LocationStatus,
    LocationType,
)
from .lore_entry import (
    LoreCategory,
    LoreEntry,
)
from .relationship import (
    EntityType,
    InteractionLog,
    Relationship,
    RelationshipType,
)
from .world_rule import WorldRule
from .world_setting import (
    Era,
    Genre,
    ToneType,
    WorldSetting,
)

__all__ = [
    # Base Entity
    "Entity",
    # WorldSetting
    "WorldSetting",
    "Genre",
    "Era",
    "ToneType",
    # Faction
    "Faction",
    "FactionType",
    "FactionAlignment",
    "FactionStatus",
    "FactionRelation",
    # Location
    "Location",
    "LocationType",
    "ClimateType",
    "LocationStatus",
    # HistoryEvent
    "HistoryEvent",
    "EventType",
    "EventSignificance",
    "EventOutcome",
    # Relationship
    "Relationship",
    "RelationshipType",
    "EntityType",
    "InteractionLog",
    # Item
    "Item",
    "ItemType",
    "ItemRarity",
    # LoreEntry
    "LoreEntry",
    "LoreCategory",
    # WorldRule
    "WorldRule",
]
