#!/usr/bin/env python3
"""
Character Domain Events

This package contains domain events for the Character context.
Domain events represent something interesting that happened in the
domain that other parts of the system might care about.

Events included:
- CharacterCreated: Raised when a new character is created
- CharacterUpdated: Raised when character data is modified
- CharacterStatsChanged: Raised when health/mana/stats change
- CharacterLeveledUp: Raised when a character gains levels
- CharacterDeleted: Raised when a character is removed
"""

from .character_events import (
    CharacterCreated,
    CharacterDeleted,
    CharacterEvent,
    CharacterLeveledUp,
    CharacterStatsChanged,
    CharacterUpdated,
)

__all__ = [
    "CharacterEvent",
    "CharacterCreated",
    "CharacterUpdated",
    "CharacterStatsChanged",
    "CharacterLeveledUp",
    "CharacterDeleted",
]
