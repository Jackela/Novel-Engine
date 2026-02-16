#!/usr/bin/env python3
"""Lore Entry Domain Entity.

This module defines the LoreEntry entity which represents wiki-style
knowledge base entries for world-building. Lore entries capture
historical, cultural, magical, and technological aspects of the setting.

Why Lore matters: A rich lore foundation provides consistency for
narrative generation. Characters can reference historical events,
cultural norms, and technological constraints that make the world
feel lived-in and coherent.

Typical usage example:
    >>> from src.contexts.world.domain.entities import LoreEntry, LoreCategory
    >>> magic_system = LoreEntry(
    ...     title="The Binding Laws",
    ...     content="All magic requires a sacrifice...",
    ...     category=LoreCategory.MAGIC,
    ...     tags=["magic", "rules", "cost"]
    ... )
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

from .entity import Entity


class LoreCategory(Enum):
    """Classification of lore entry categories.

    Defines the thematic category of a lore entry, which helps
    organize knowledge and enables category-based filtering.

    Attributes:
        HISTORY: Past events, wars, dynasties, and timelines.
        CULTURE: Customs, traditions, religions, and social norms.
        MAGIC: Supernatural systems, spells, and mystical rules.
        TECHNOLOGY: Tools, inventions, and scientific knowledge.
    """

    HISTORY = "history"
    CULTURE = "culture"
    MAGIC = "magic"
    TECHNOLOGY = "technology"


@dataclass(eq=False)
class LoreEntry(Entity):
    """Lore Entry Entity.

    Represents a knowledge base entry containing world-building
    information. Lore entries form the backbone of the world's
    wiki and can be referenced by characters, locations, and events.

    Why track lore: Lore entries enable consistent world-building
    across narratives:
    - Historical context for character backstories
    - Cultural rules that constrain character behavior
    - Magic/tech systems that define what's possible
    - Reference material for AI narrative generation

    Attributes:
        title: Display title for the lore entry.
        content: Full text content (supports markdown).
        tags: Searchable tags for categorization and discovery.
        category: Thematic category (HISTORY, CULTURE, MAGIC, TECHNOLOGY).
        summary: Optional short summary for previews.
        related_entry_ids: IDs of related lore entries for cross-referencing.
        metadata: Additional flexible data for specific use cases.
    """

    title: str = ""
    content: str = ""
    tags: List[str] = field(default_factory=list)
    category: LoreCategory = LoreCategory.HISTORY
    summary: str = ""
    related_entry_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __eq__(self, other: object) -> bool:
        """Equality comparison based on entity identity (inherited from Entity)."""
        return super().__eq__(other)

    def _validate_business_rules(self) -> List[str]:
        """Validate LoreEntry-specific business rules."""
        errors = []

        if not self.title or not self.title.strip():
            errors.append("Lore entry title cannot be empty")

        if len(self.title) > 300:
            errors.append("Lore entry title cannot exceed 300 characters")

        if len(self.tags) > 20:
            errors.append("Lore entry cannot have more than 20 tags")

        # Validate individual tags
        for tag in self.tags:
            if not tag or not tag.strip():
                errors.append("Tags cannot be empty strings")
                break
            if len(tag) > 50:
                errors.append(f"Tag '{tag[:20]}...' exceeds 50 character limit")

        return errors

    def update_title(self, title: str) -> None:
        """Update the entry's title.

        Args:
            title: New title for the entry.

        Raises:
            ValueError: If title is empty or too long.
        """
        if not title or not title.strip():
            raise ValueError("Lore entry title cannot be empty")
        if len(title) > 300:
            raise ValueError("Lore entry title cannot exceed 300 characters")

        self.title = title.strip()
        self.touch()

    def update_content(self, content: str) -> None:
        """Update the entry's content.

        Args:
            content: New content text (markdown supported).
        """
        self.content = content.strip() if content else ""
        self.touch()

    def update_summary(self, summary: str) -> None:
        """Update the entry's summary.

        Args:
            summary: Short summary text.
        """
        self.summary = summary.strip() if summary else ""
        self.touch()

    def set_category(self, category: LoreCategory) -> None:
        """Change the entry's category.

        Args:
            category: New category classification.
        """
        self.category = category
        self.touch()

    def add_tag(self, tag: str) -> bool:
        """Add a tag to the entry.

        Args:
            tag: Tag to add.

        Returns:
            True if tag was added, False if duplicate or invalid.

        Raises:
            ValueError: If tag limit would be exceeded.
        """
        if not tag or not tag.strip():
            return False

        tag_normalized = tag.strip().lower()
        if len(tag_normalized) > 50:
            raise ValueError("Tag cannot exceed 50 characters")

        if len(self.tags) >= 20:
            raise ValueError("Cannot add more than 20 tags")

        if tag_normalized not in [t.lower() for t in self.tags]:
            self.tags.append(tag_normalized)
            self.touch()
            return True
        return False

    def remove_tag(self, tag: str) -> bool:
        """Remove a tag from the entry.

        Args:
            tag: Tag to remove.

        Returns:
            True if tag was found and removed.
        """
        tag_normalized = tag.strip().lower()
        for existing_tag in self.tags:
            if existing_tag.lower() == tag_normalized:
                self.tags.remove(existing_tag)
                self.touch()
                return True
        return False

    def has_tag(self, tag: str) -> bool:
        """Check if entry has a specific tag (case-insensitive).

        Args:
            tag: Tag to check for.

        Returns:
            True if tag exists.
        """
        tag_normalized = tag.strip().lower()
        return tag_normalized in [t.lower() for t in self.tags]

    def add_related_entry(self, entry_id: str) -> bool:
        """Add a related lore entry reference.

        Args:
            entry_id: ID of the related entry.

        Returns:
            True if added, False if already linked or self-reference.
        """
        if not entry_id or entry_id == self.id:
            return False

        if entry_id not in self.related_entry_ids:
            self.related_entry_ids.append(entry_id)
            self.touch()
            return True
        return False

    def remove_related_entry(self, entry_id: str) -> bool:
        """Remove a related entry reference.

        Args:
            entry_id: ID of the entry to unlink.

        Returns:
            True if removed.
        """
        if entry_id in self.related_entry_ids:
            self.related_entry_ids.remove(entry_id)
            self.touch()
            return True
        return False

    def is_history(self) -> bool:
        """Check if this is a historical lore entry."""
        return self.category == LoreCategory.HISTORY

    def is_culture(self) -> bool:
        """Check if this is a cultural lore entry."""
        return self.category == LoreCategory.CULTURE

    def is_magic(self) -> bool:
        """Check if this is a magic-related lore entry."""
        return self.category == LoreCategory.MAGIC

    def is_technology(self) -> bool:
        """Check if this is a technology-related lore entry."""
        return self.category == LoreCategory.TECHNOLOGY

    # ==================== Metadata / Smart Tags Operations ====================

    def set_smart_tags(self, tags: Dict[str, List[str]]) -> None:
        """Store smart tags in metadata.

        Args:
            tags: Dictionary mapping category names to tag lists.

        Why this method:
            Provides a consistent interface for storing smart tags
            generated by the AI tagging system. Smart tags are
            stored separately from manual tags to allow for
            automatic updating without overwriting user edits.
        """
        self.metadata["smart_tags"] = tags
        self.touch()

    def get_smart_tags(self) -> Dict[str, List[str]]:
        """Get smart tags from metadata.

        Returns:
            Dictionary mapping category names to tag lists, or empty dict if none.
        """
        return self.metadata.get("smart_tags", {})

    def has_smart_tag(self, category: str, tag: str) -> bool:
        """Check if the lore entry has a specific smart tag.

        Args:
            category: The tag category (e.g., "genre", "mood", "themes").
            tag: The tag value to check.

        Returns:
            True if the tag exists in the specified category.
        """
        smart_tags = self.get_smart_tags()
        category_tags = smart_tags.get(category, [])
        return tag.lower() in [t.lower() for t in category_tags]

    def get_all_tags_combined(self) -> List[str]:
        """Get all tags (manual + smart) combined.

        Returns:
            List of all tags without duplicates.
        """
        all_tags = self.tags.copy()
        smart_tags = self.get_smart_tags()
        for category_tags in smart_tags.values():
            for tag in category_tags:
                tag_normalized = tag.lower()
                if tag_normalized not in [t.lower() for t in all_tags]:
                    all_tags.append(tag_normalized)
        return all_tags

    # ==================== Manual Smart Tags Override ====================

    def set_manual_smart_tags(self, category: str, tags: List[str]) -> None:
        """Set manual tags for a specific category.

        These tags are marked as manual-only and will never be overridden
        by auto-tagging. They are stored under a separate key in metadata.

        Args:
            category: The tag category (e.g., "genre", "mood", "themes")
            tags: List of manual tags for this category
        """
        if "manual_smart_tags" not in self.metadata:
            self.metadata["manual_smart_tags"] = {}

        self.metadata["manual_smart_tags"][category] = [
            t.strip().lower() for t in tags if t.strip()
        ]
        self.touch()

    def get_manual_smart_tags(self) -> Dict[str, List[str]]:
        """Get manual-only smart tags.

        Returns:
            Dictionary mapping category names to manual tag lists.
        """
        return self.metadata.get("manual_smart_tags", {})

    def get_manual_smart_tags_for_category(self, category: str) -> List[str]:
        """Get manual tags for a specific category.

        Args:
            category: The tag category

        Returns:
            List of manual tags for this category
        """
        manual_tags = self.get_manual_smart_tags()
        return manual_tags.get(category, [])

    def remove_manual_smart_tag(self, category: str, tag: str) -> bool:
        """Remove a manual smart tag.

        Args:
            category: The tag category
            tag: The tag to remove

        Returns:
            True if tag was found and removed
        """
        manual_tags = self.get_manual_smart_tags()
        if category in manual_tags:
            tag_normalized = tag.strip().lower()
            if tag_normalized in [t.lower() for t in manual_tags[category]]:
                manual_tags[category] = [
                    t for t in manual_tags[category] if t.lower() != tag_normalized
                ]
                self.metadata["manual_smart_tags"] = manual_tags
                self.touch()
                return True
        return False

    def clear_manual_smart_tags(self, category: str | None = None) -> None:
        """Clear manual smart tags.

        Args:
            category: If provided, only clear this category.
                     If None, clear all manual tags.
        """
        if "manual_smart_tags" not in self.metadata:
            return

        if category:
            self.metadata["manual_smart_tags"].pop(category, None)
        else:
            self.metadata["manual_smart_tags"] = {}

        self.touch()

    def get_effective_smart_tags(self) -> Dict[str, List[str]]:
        """Get all smart tags (auto + manual) combined.

        Returns:
            Dictionary with all tags by category, merging auto-generated
            and manual tags. Manual tags take precedence.
        """
        auto_tags = self.get_smart_tags()
        manual_tags = self.get_manual_smart_tags()

        effective: Dict[str, List[str]] = {}

        # All categories
        all_categories = set(auto_tags.keys()) | set(manual_tags.keys())

        for category in all_categories:
            auto = set(auto_tags.get(category, []))
            manual = set(manual_tags.get(category, []))
            # Union gives us all tags, manual doesn't need special handling
            # since they're already included in the combined set
            effective[category] = list(auto | manual)

        return effective

    def _to_dict_specific(self) -> Dict[str, Any]:
        """Convert LoreEntry-specific data to dictionary."""
        return {
            "title": self.title,
            "content": self.content,
            "tags": self.tags.copy(),
            "category": self.category.value,
            "summary": self.summary,
            "related_entry_ids": self.related_entry_ids.copy(),
            "metadata": self.metadata.copy(),
        }

    @classmethod
    def create_history_entry(
        cls,
        title: str,
        content: str = "",
        tags: List[str] | None = None,
    ) -> "LoreEntry":
        """Factory method for creating history entries.

        Args:
            title: Entry title.
            content: Entry content.
            tags: Optional tags.

        Returns:
            A new history LoreEntry.
        """
        return cls(
            title=title,
            content=content,
            category=LoreCategory.HISTORY,
            tags=tags or [],
        )

    @classmethod
    def create_culture_entry(
        cls,
        title: str,
        content: str = "",
        tags: List[str] | None = None,
    ) -> "LoreEntry":
        """Factory method for creating culture entries.

        Args:
            title: Entry title.
            content: Entry content.
            tags: Optional tags.

        Returns:
            A new culture LoreEntry.
        """
        return cls(
            title=title,
            content=content,
            category=LoreCategory.CULTURE,
            tags=tags or [],
        )

    @classmethod
    def create_magic_entry(
        cls,
        title: str,
        content: str = "",
        tags: List[str] | None = None,
    ) -> "LoreEntry":
        """Factory method for creating magic entries.

        Args:
            title: Entry title.
            content: Entry content.
            tags: Optional tags.

        Returns:
            A new magic LoreEntry.
        """
        return cls(
            title=title,
            content=content,
            category=LoreCategory.MAGIC,
            tags=tags or [],
        )

    @classmethod
    def create_technology_entry(
        cls,
        title: str,
        content: str = "",
        tags: List[str] | None = None,
    ) -> "LoreEntry":
        """Factory method for creating technology entries.

        Args:
            title: Entry title.
            content: Entry content.
            tags: Optional tags.

        Returns:
            A new technology LoreEntry.
        """
        return cls(
            title=title,
            content=content,
            category=LoreCategory.TECHNOLOGY,
            tags=tags or [],
        )
