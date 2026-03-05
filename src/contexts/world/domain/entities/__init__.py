#!/usr/bin/env python3
"""World Domain Entities.

This module exports all domain entities for the World context.
"""

from .diplomatic_pact import (
    INCOMPATIBLE_PACTS,
    DiplomaticPact,
    PactType,
)
from .entity import Entity
from .faction import (
    Faction,
    FactionAlignment,
    FactionRelation,
    FactionStatus,
    FactionType,
)
from .faction_intent import (
    DEFENSIVE_ACTIONS,
    DEFENSIVE_INTENTS,  # Legacy alias
    OFFENSIVE_ACTIONS,
    OFFENSIVE_INTENTS,  # Legacy alias
    VALID_STATUS_TRANSITIONS,
    ActionType,
    FactionIntent,
    IntentStatus,
    IntentType,  # Backward compatibility alias for ActionType
    _normalize_action_type,
)
from .history_event import (
    EventOutcome,
    EventSignificance,
    EventType,
    HistoryEvent,
    ImpactScope,
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
from .resource import Resource
from .rumor import (
    Rumor,
    RumorOrigin,
)
from .world_rule import WorldRule
from .world_setting import (
    Era,
    Genre,
    ToneType,
    WorldSetting,
)
from .world_snapshot import WorldSnapshot

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
    "ImpactScope",
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
    # Resource
    "Resource",
    # DiplomaticPact
    "DiplomaticPact",
    "PactType",
    "INCOMPATIBLE_PACTS",
    # WorldRule
    "WorldRule",
    # FactionIntent
    "FactionIntent",
    "ActionType",
    "IntentStatus",
    "IntentType",  # Backward compatibility alias
    "OFFENSIVE_ACTIONS",
    "DEFENSIVE_ACTIONS",
    "OFFENSIVE_INTENTS",  # Legacy alias
    "DEFENSIVE_INTENTS",  # Legacy alias
    "VALID_STATUS_TRANSITIONS",
    "_normalize_action_type",
    # Rumor
    "Rumor",
    "RumorOrigin",
    # WorldSnapshot
    "WorldSnapshot",
]
