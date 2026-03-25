"""Type definitions for the character context domain.

This module defines type aliases and constants used throughout
the character context domain layer.
"""

from typing import Dict, Literal, NewType
from uuid import UUID

# ID Types
CharacterId = NewType("CharacterId", UUID)

# Attribute Types
AttributeName = Literal[
    "strength",
    "intelligence",
    "charisma",
    "dexterity",
    "constitution",
    "wisdom",
    "luck",
]

Attributes = Dict[str, int]

# Status Types
CharacterStatus = Literal[
    "active",
    "inactive",
    "dead",
    "retired",
]

# Item Types
ItemType = Literal[
    "weapon",
    "armor",
    "consumable",
    "material",
    "key",
    "misc",
]

# Relationship Types
RelationshipType = Literal[
    "friend",
    "enemy",
    "ally",
    "rival",
    "neutral",
    "family",
    "romantic",
]

# Skill Categories
SkillCategory = Literal[
    "combat",
    "magic",
    "social",
    "crafting",
    "survival",
    "knowledge",
    "stealth",
]
