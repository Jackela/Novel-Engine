"""
Ingestion Processors

Content-specific processors for different source types.

Each processor defines chunking defaults and metadata enrichment
for its source type without implementing embedding or storage logic.

Constitution Compliance:
- Article II (Hexagonal): Application service implementing IIngestionProcessor
- Article V (SOLID): SRP - each processor handles one content type
"""

from __future__ import annotations

import re
from typing import Any

from ...application.ports.i_ingestion_processor import IIngestionProcessor
from ...domain.models.chunking_strategy import (
    ChunkingStrategy,
    ChunkStrategyType,
)
from ...domain.models.source_type import SourceType

# Patterns for content analysis
_WORD_PATTERN: re.Pattern[str] = re.compile(r"\S+")
_DIALOGUE_PATTERN: re.Pattern[str] = re.compile(r'"[^"]*"')


class GenericProcessor(IIngestionProcessor):
    """
    Generic processor for source types without specific handling.

    Uses default chunking strategy and minimal metadata enrichment.
    """

    @property
    def source_type(self) -> SourceType:
        """Return wildcard for generic processor."""
        return SourceType.LORE  # Lore as reasonable default

    def get_chunking_strategy(
        self,
        custom_strategy: ChunkingStrategy | None = None,
    ) -> ChunkingStrategy:
        """Get default chunking strategy."""
        return custom_strategy or ChunkingStrategy.default()

    def enrich_metadata(
        self,
        base_metadata: dict[str, Any],
        content: str,
    ) -> dict[str, Any]:
        """Add minimal metadata enrichment."""
        enriched = base_metadata.copy()
        enriched.setdefault("processor", "generic")
        return enriched


class LoreProcessor(IIngestionProcessor):
    """
    Processor for lore entries.

    Lore entries are factual world-building content that benefits
    from fixed-size chunking for consistent retrieval.
    """

    @property
    def source_type(self) -> SourceType:
        """Return LORE source type."""
        return SourceType.LORE

    def get_chunking_strategy(
        self,
        custom_strategy: ChunkingStrategy | None = None,
    ) -> ChunkingStrategy:
        """Get lore-optimized chunking strategy (400-word fixed chunks)."""
        if custom_strategy:
            return custom_strategy
        return ChunkingStrategy.for_lore()

    def enrich_metadata(
        self,
        base_metadata: dict[str, Any],
        content: str,
    ) -> dict[str, Any]:
        """Enrich metadata with lore-specific information."""
        enriched = base_metadata.copy()
        enriched["processor"] = "lore"

        # Detect lore categories from content
        content_lower = content.lower()

        # Category hints
        if any(
            word in content_lower
            for word in ["history", "historical", "ancient", "past"]
        ):
            enriched.setdefault("category", "history")
        elif any(
            word in content_lower for word in ["magic", "spell", "enchantment", "curse"]
        ):
            enriched.setdefault("category", "magic")
        elif any(
            word in content_lower for word in ["geography", "region", "land", "terrain"]
        ):
            enriched.setdefault("category", "geography")
        elif any(
            word in content_lower
            for word in ["culture", "society", "tradition", "custom"]
        ):
            enriched.setdefault("category", "culture")
        else:
            enriched.setdefault("category", "general")

        return enriched


class CharacterProcessor(IIngestionProcessor):
    """
    Processor for character profiles.

    Character profiles contain structured information (personality,
    appearance, background) that benefit from semantic chunking.
    """

    @property
    def source_type(self) -> SourceType:
        """Return CHARACTER source type."""
        return SourceType.CHARACTER

    def get_chunking_strategy(
        self,
        custom_strategy: ChunkingStrategy | None = None,
    ) -> ChunkingStrategy:
        """Get character-optimized chunking strategy (200-word semantic chunks)."""
        if custom_strategy:
            return custom_strategy
        return ChunkingStrategy.for_character()

    def enrich_metadata(
        self,
        base_metadata: dict[str, Any],
        content: str,
    ) -> dict[str, Any]:
        """Enrich metadata with character-specific information."""
        enriched = base_metadata.copy()
        enriched["processor"] = "character"

        # Extract character name if present (common pattern: "Name\n" or "Name -")
        first_line = content.strip().split("\n")[0].strip()
        if len(first_line) < 50 and not first_line.endswith("."):
            # Likely a name/title line
            enriched.setdefault("name_hint", first_line)

        # Detect character role
        content_lower = content.lower()

        role_keywords = {
            "protagonist": ["hero", "main character", "protagonist", "protagonist"],
            "antagonist": ["villain", "antagonist", "enemy", "opponent"],
            "mentor": ["mentor", "teacher", "guide", "master"],
            "ally": ["ally", "friend", "companion", "sidekick"],
            "neutral": ["neutral", "npc", "background"],
        }

        for role, keywords in role_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                enriched.setdefault("role_hint", role)
                break

        return enriched


class SceneProcessor(IIngestionProcessor):
    """
    Processor for scene content.

    Scenes contain narrative flow and dialogue that benefit
    from paragraph-aware chunking to preserve context.
    """

    @property
    def source_type(self) -> SourceType:
        """Return SCENE source type."""
        return SourceType.SCENE

    def get_chunking_strategy(
        self,
        custom_strategy: ChunkingStrategy | None = None,
    ) -> ChunkingStrategy:
        """Get scene-optimized chunking strategy (300-word paragraph chunks)."""
        if custom_strategy:
            return custom_strategy
        return ChunkingStrategy.for_scene()

    def enrich_metadata(
        self,
        base_metadata: dict[str, Any],
        content: str,
    ) -> dict[str, Any]:
        """Enrich metadata with scene-specific information."""
        enriched = base_metadata.copy()
        enriched["processor"] = "scene"

        # Count dialogue vs narration
        dialogue_matches = _DIALOGUE_PATTERN.findall(content)
        dialogue_words = sum(
            len(_WORD_PATTERN.findall(match)) for match in dialogue_matches
        )
        total_words = len(_WORD_PATTERN.findall(content))

        if total_words > 0:
            dialogue_ratio = dialogue_words / total_words
            enriched["dialogue_ratio"] = round(dialogue_ratio, 3)

            # Classify scene type
            if dialogue_ratio > 0.5:
                enriched.setdefault("scene_type", "dialogue_heavy")
            elif dialogue_ratio < 0.1:
                enriched.setdefault("scene_type", "narration_heavy")
            else:
                enriched.setdefault("scene_type", "balanced")

        # Detect setting hints
        content_lower = content.lower()

        setting_keywords = {
            "indoor": ["room", "hall", "chamber", "house", "castle", "building"],
            "outdoor": ["field", "forest", "mountain", "road", "path", "outside"],
            "urban": ["street", "city", "town", "market", "square", "alley"],
            "travel": ["journey", "travel", "riding", "walking", "march", "sailing"],
        }

        for setting, keywords in setting_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                enriched.setdefault("setting_hint", setting)
                break

        return enriched


class PlotlineProcessor(IIngestionProcessor):
    """
    Processor for plotline entries.

    Plotlines describe story arcs and events.
    """

    @property
    def source_type(self) -> SourceType:
        """Return PLOTLINE source type."""
        return SourceType.PLOTLINE

    def get_chunking_strategy(
        self,
        custom_strategy: ChunkingStrategy | None = None,
    ) -> ChunkingStrategy:
        """Get plotline-optimized chunking strategy."""
        if custom_strategy:
            return custom_strategy
        # Plotlines benefit from semantic chunking
        return ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=350,
            overlap=None,  # Auto-calculated as 10% = 35
        )

    def enrich_metadata(
        self,
        base_metadata: dict[str, Any],
        content: str,
    ) -> dict[str, Any]:
        """Enrich metadata with plotline-specific information."""
        enriched = base_metadata.copy()
        enriched["processor"] = "plotline"

        # Detect plot phase
        content_lower = content.lower()

        phase_keywords = {
            "setup": ["introduction", "beginning", "setup", "start", "initial"],
            "rising_action": ["conflict", "rising", "tension", "complication"],
            "climax": ["climax", "peak", "confrontation", "battle", "showdown"],
            "falling_action": ["aftermath", "falling", "resolution", "consequence"],
            "resolution": ["ending", "conclusion", "finale", "epilogue", "resolved"],
        }

        for phase, keywords in phase_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                enriched.setdefault("plot_phase", phase)
                break

        return enriched


class ItemProcessor(IIngestionProcessor):
    """
    Processor for item entries.

    Items include objects, equipment, and artifacts.
    """

    @property
    def source_type(self) -> SourceType:
        """Return ITEM source type."""
        return SourceType.ITEM

    def get_chunking_strategy(
        self,
        custom_strategy: ChunkingStrategy | None = None,
    ) -> ChunkingStrategy:
        """Get item-optimized chunking strategy (smaller chunks)."""
        if custom_strategy:
            return custom_strategy
        # Items are usually shorter, use smaller chunks
        return ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=150,
            overlap=None,  # Auto-calculated as 10% = 15
        )

    def enrich_metadata(
        self,
        base_metadata: dict[str, Any],
        content: str,
    ) -> dict[str, Any]:
        """Enrich metadata with item-specific information."""
        enriched = base_metadata.copy()
        enriched["processor"] = "item"

        # Detect item type
        content_lower = content.lower()

        type_keywords = {
            "weapon": ["sword", "axe", "bow", "dagger", "spear", "weapon"],
            "armor": ["armor", "shield", "helmet", "plate", "mail", "defense"],
            "consumable": ["potion", "elixir", "food", "drink", "scroll", "consumable"],
            "artifact": ["artifact", "relic", "ancient", "legendary", "cursed"],
            "tool": ["tool", "key", "lockpick", "rope", "torch", "instrument"],
        }

        for item_type, keywords in type_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                enriched.setdefault("item_type_hint", item_type)
                break

        return enriched


class LocationProcessor(IIngestionProcessor):
    """
    Processor for location entries.

    Locations describe places and geographical features.
    """

    @property
    def source_type(self) -> SourceType:
        """Return LOCATION source type."""
        return SourceType.LOCATION

    def get_chunking_strategy(
        self,
        custom_strategy: ChunkingStrategy | None = None,
    ) -> ChunkingStrategy:
        """Get location-optimized chunking strategy."""
        if custom_strategy:
            return custom_strategy
        return ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=300,
            overlap=None,  # Auto-calculated as 10% = 30
        )

    def enrich_metadata(
        self,
        base_metadata: dict[str, Any],
        content: str,
    ) -> dict[str, Any]:
        """Enrich metadata with location-specific information."""
        enriched = base_metadata.copy()
        enriched["processor"] = "location"

        # Detect location type
        content_lower = content.lower()

        type_keywords = {
            "settlement": ["city", "town", "village", "hamlet", "settlement"],
            "natural": ["forest", "mountain", "river", "lake", "ocean", "valley"],
            "structure": [
                "castle",
                "fortress",
                "temple",
                "ruins",
                "building",
                "dungeon",
            ],
            "region": ["kingdom", "realm", "territory", "province", "region", "land"],
        }

        for location_type, keywords in type_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                enriched.setdefault("location_type_hint", location_type)
                break

        return enriched


__all__ = [
    "IIngestionProcessor",
    "GenericProcessor",
    "LoreProcessor",
    "CharacterProcessor",
    "SceneProcessor",
    "PlotlineProcessor",
    "ItemProcessor",
    "LocationProcessor",
]
