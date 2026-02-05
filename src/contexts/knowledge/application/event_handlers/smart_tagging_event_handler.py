"""
Smart Tagging Event Handler

Automatically generates and stores tags for entities when they are created or updated.
Integrates with the event system to provide real-time smart tagging.

Constitution Compliance:
- Article II (Hexagonal): Application layer event handler
- Article V (SOLID): SRP - handles tagging events only
- Article VI (EDA): Event-driven tagging

Warzone 4: AI Brain - BRAIN-038-03
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from ..services.smart_tagging_service import (
    GeneratedTag,
    SmartTaggingService,
    TagCategory,
    TaggingResult,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


logger = structlog.get_logger()


class SmartTaggingEventHandler:
    """
    Event handler that automatically generates tags for content.

    Listens for content creation/update events and uses SmartTaggingService
    to generate relevant tags. Tags are returned to be stored in entity metadata.

    Example:
        >>> handler = SmartTaggingEventHandler(tagging_service)
        >>> tags = await handler.generate_tags_for_lore(
        ...     lore_id="lore-123",
        ...     title="The Ancient Sword",
        ...     content="A legendary weapon forged...",
        ...     category="artifact"
        ... )
        >>> # Store tags in entity metadata
    """

    def __init__(
        self,
        tagging_service: SmartTaggingService,
        enabled: bool = True,
    ):
        """
        Initialize the smart tagging event handler.

        Args:
            tagging_service: Service for generating tags
            enabled: Whether auto-tagging is enabled
        """
        self._tagging_service = tagging_service
        self._enabled = enabled
        self._logger = logger.bind(handler="smart_tagging")

    def is_enabled(self) -> bool:
        """Check if auto-tagging is enabled."""
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable auto-tagging."""
        self._enabled = enabled
        self._logger.info("smart_tagging_enabled_changed", enabled=enabled)

    async def generate_tags_for_lore(
        self,
        lore_id: str,
        title: str,
        content: str,
        category: str | None = None,
        existing_tags: dict[str, list[str]] | None = None,
        manual_only_tags: dict[str, list[str]] | None = None,
    ) -> dict[str, list[str]]:
        """
        Generate tags for a lore entry.

        Args:
            lore_id: Lore entry ID
            title: Lore title
            content: Lore content
            category: Lore category (optional)
            existing_tags: Existing tags to preserve
            manual_only_tags: Manual tags that should never be overridden

        Returns:
            Dictionary mapping category names to tag lists
        """
        if not self._enabled:
            return existing_tags or {}

        # Build content for tagging
        tag_content = self._build_lore_content(title, content, category)

        try:
            result = await self._tagging_service.generate_tags(
                content=tag_content,
                content_type="lore",
            )

            tags_dict = self._result_to_dict(result)

            # Preserve existing manual tags if provided
            if existing_tags:
                tags_dict = self._merge_tags(tags_dict, existing_tags, manual_only_tags)

            self._logger.info(
                "smart_tags_generated_for_lore",
                lore_id=lore_id,
                tag_count=len(result.tags),
                tags=tags_dict,
            )

            return tags_dict

        except Exception as e:
            self._logger.error(
                "smart_tagging_failed_for_lore",
                lore_id=lore_id,
                error=str(e),
            )
            return existing_tags or {}

    async def generate_tags_for_scene(
        self,
        scene_id: str,
        title: str,
        summary: str | None = None,
        location: str | None = None,
        beats: list[str] | None = None,
        existing_tags: dict[str, list[str]] | None = None,
        manual_only_tags: dict[str, list[str]] | None = None,
    ) -> dict[str, list[str]]:
        """
        Generate tags for a scene.

        Args:
            scene_id: Scene ID
            title: Scene title
            summary: Scene summary
            location: Scene location
            beats: Scene beat contents
            existing_tags: Existing tags to preserve
            manual_only_tags: Manual tags that should never be overridden

        Returns:
            Dictionary mapping category names to tag lists
        """
        if not self._enabled:
            return existing_tags or {}

        # Build content for tagging
        tag_content = self._build_scene_content(title, summary, location, beats)

        try:
            result = await self._tagging_service.generate_tags(
                content=tag_content,
                content_type="scene",
            )

            tags_dict = self._result_to_dict(result)

            # Preserve existing manual tags if provided
            if existing_tags:
                tags_dict = self._merge_tags(tags_dict, existing_tags, manual_only_tags)

            self._logger.info(
                "smart_tags_generated_for_scene",
                scene_id=scene_id,
                tag_count=len(result.tags),
                tags=tags_dict,
            )

            return tags_dict

        except Exception as e:
            self._logger.error(
                "smart_tagging_failed_for_scene",
                scene_id=scene_id,
                error=str(e),
            )
            return existing_tags or {}

    async def generate_tags_for_character(
        self,
        character_id: str,
        name: str,
        description: str | None = None,
        backstory: str | None = None,
        traits: list[str] | None = None,
        existing_tags: dict[str, list[str]] | None = None,
        manual_only_tags: dict[str, list[str]] | None = None,
    ) -> dict[str, list[str]]:
        """
        Generate tags for a character.

        Args:
            character_id: Character ID
            name: Character name
            description: Character description
            backstory: Character backstory
            traits: Character traits
            existing_tags: Existing tags to preserve
            manual_only_tags: Manual tags that should never be overridden

        Returns:
            Dictionary mapping category names to tag lists
        """
        if not self._enabled:
            return existing_tags or {}

        # Build content for tagging
        tag_content = self._build_character_content(
            name, description, backstory, traits
        )

        try:
            result = await self._tagging_service.generate_tags(
                content=tag_content,
                content_type="character",
            )

            tags_dict = self._result_to_dict(result)

            # Preserve existing manual tags if provided
            if existing_tags:
                tags_dict = self._merge_tags(tags_dict, existing_tags, manual_only_tags)

            self._logger.info(
                "smart_tags_generated_for_character",
                character_id=character_id,
                tag_count=len(result.tags),
                tags=tags_dict,
            )

            return tags_dict

        except Exception as e:
            self._logger.error(
                "smart_tagging_failed_for_character",
                character_id=character_id,
                error=str(e),
            )
            return existing_tags or {}

    def _build_lore_content(
        self, title: str, content: str, category: str | None = None
    ) -> str:
        """Build formatted content for lore tagging."""
        parts = [f"# {title}"]

        if category:
            parts.append(f"Category: {category}")

        parts.append(f"\n{content}")

        return "\n".join(parts)

    def _build_scene_content(
        self,
        title: str,
        summary: str | None = None,
        location: str | None = None,
        beats: list[str] | None = None,
    ) -> str:
        """Build formatted content for scene tagging."""
        parts = [f"# {title}"]

        if location:
            parts.append(f"Location: {location}")

        if summary:
            parts.append(f"\nSummary: {summary}")

        if beats:
            parts.append("\nBeats:")
            parts.extend(beats)

        return "\n".join(parts)

    def _build_character_content(
        self,
        name: str,
        description: str | None = None,
        backstory: str | None = None,
        traits: list[str] | None = None,
    ) -> str:
        """Build formatted content for character tagging."""
        parts = [f"# {name}"]

        if traits:
            parts.append(f"Traits: {', '.join(traits)}")

        if description:
            parts.append(f"\nDescription: {description}")

        if backstory:
            parts.append(f"\nBackstory: {backstory}")

        return "\n".join(parts)

    def _result_to_dict(self, result: TaggingResult) -> dict[str, list[str]]:
        """Convert TaggingResult to dictionary format for storage."""
        tags_dict: dict[str, list[str]] = {}

        for tag in result.tags:
            category_name = tag.category.value
            if category_name not in tags_dict:
                tags_dict[category_name] = []
            tags_dict[category_name].append(tag.value)

        return tags_dict

    def _merge_tags(
        self,
        generated_tags: dict[str, list[str]],
        existing_tags: dict[str, list[str]],
        manual_only_tags: dict[str, list[str]] | None = None,
    ) -> dict[str, list[str]]:
        """
        Merge generated tags with existing tags, preserving manual edits.

        Tags from existing_tags that aren't in generated_tags are preserved
        as manual edits. Duplicates are removed.

        Manual-only tags (user-added tags that should never be overridden)
        are always preserved.

        Args:
            generated_tags: Newly generated tags
            existing_tags: Existing tags (may include manual edits)
            manual_only_tags: Tags that are purely manual (never overridden)

        Returns:
            Merged tags dictionary
        """
        merged: dict[str, list[str]] = {}

        # All categories
        all_categories = set(generated_tags.keys()) | set(existing_tags.keys())
        if manual_only_tags:
            all_categories |= set(manual_only_tags.keys())

        for category in all_categories:
            gen = set(generated_tags.get(category, []))
            exi = set(existing_tags.get(category, []))
            manual = set(manual_only_tags.get(category, [])) if manual_only_tags else set()

            # Union of all sets: generated + existing + manual-only
            # Manual-only tags are always preserved even if not in generated
            merged[category] = list(gen | exi | manual)

        return merged


__all__ = ["SmartTaggingEventHandler"]
