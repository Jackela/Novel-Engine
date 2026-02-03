"""
SourceType Enumeration

Defines the types of content sources for RAG knowledge entries.

Warzone 4: AI Brain - BRAIN-003
Classifies content sources for filtering and retrieval.

Constitution Compliance:
- Article I (DDD): Enumeration represents domain concept
"""

from __future__ import annotations

from enum import Enum


class SourceType(str, Enum):
    """
    Type of content source for a knowledge entry.

    Used to filter retrieval by source type and track content provenance.

    Values:
        CHARACTER: Character profiles and descriptions
        LORE: World-building and setting information
        SCENE: Scene content and narrative
        PLOTLINE: Plot events and story arcs
        ITEM: Items, objects, and equipment
        LOCATION: Places and geographical information
    """

    CHARACTER = "CHARACTER"
    LORE = "LORE"
    SCENE = "SCENE"
    PLOTLINE = "PLOTLINE"
    ITEM = "ITEM"
    LOCATION = "LOCATION"

    @classmethod
    def from_string(cls, value: str) -> SourceType:
        """
        Convert string to SourceType, case-insensitive.

        Args:
            value: String representation of source type

        Returns:
            Matching SourceType enum value

        Raises:
            ValueError: If value doesn't match any source type
        """
        normalized = value.strip().upper()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(
            f"Unknown SourceType: {value}. "
            f"Valid values: {[s.value for s in cls]}"
        )


__all__ = ["SourceType"]
