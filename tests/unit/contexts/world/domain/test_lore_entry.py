#!/usr/bin/env python3
"""Unit tests for the LoreEntry domain entity.

Tests cover:
- LoreEntry creation and validation
- LoreCategory enum
- Business rule enforcement
- Factory methods
- Tag management operations
"""

import pytest

from src.contexts.world.domain.entities.lore_entry import (
    LoreCategory,
    LoreEntry,
)


class TestLoreCategory:
    """Tests for LoreCategory enum behavior."""

    def test_category_values(self):
        """Verify all categories have correct string values."""
        assert LoreCategory.HISTORY.value == "history"
        assert LoreCategory.CULTURE.value == "culture"
        assert LoreCategory.MAGIC.value == "magic"
        assert LoreCategory.TECHNOLOGY.value == "technology"

    def test_category_count(self):
        """Verify we have the expected number of categories."""
        assert len(LoreCategory) == 4


class TestLoreEntryCreation:
    """Tests for LoreEntry entity creation."""

    def test_create_basic_entry(self):
        """Test creating a basic lore entry."""
        entry = LoreEntry(
            title="The Great War",
            content="A thousand years ago...",
            category=LoreCategory.HISTORY,
        )

        assert entry.title == "The Great War"
        assert entry.content == "A thousand years ago..."
        assert entry.category == LoreCategory.HISTORY
        assert entry.tags == []
        assert entry.summary == ""

    def test_create_entry_with_defaults(self):
        """Test entry creation with default values."""
        entry = LoreEntry(title="Test Entry")

        assert entry.title == "Test Entry"
        assert entry.category == LoreCategory.HISTORY  # Default
        assert entry.content == ""
        assert entry.tags == []
        assert entry.summary == ""
        assert entry.related_entry_ids == []

    def test_create_entry_with_all_fields(self):
        """Test entry creation with all optional fields."""
        entry = LoreEntry(
            title="The Binding Laws",
            content="All magic requires a sacrifice of energy...",
            category=LoreCategory.MAGIC,
            tags=["magic", "rules", "cost"],
            summary="The fundamental laws governing all magic.",
            related_entry_ids=["entry-001", "entry-002"],
        )

        assert entry.title == "The Binding Laws"
        assert entry.content == "All magic requires a sacrifice of energy..."
        assert entry.category == LoreCategory.MAGIC
        assert entry.tags == ["magic", "rules", "cost"]
        assert entry.summary == "The fundamental laws governing all magic."
        assert entry.related_entry_ids == ["entry-001", "entry-002"]

    def test_entry_has_entity_fields(self):
        """Test that entry inherits Entity fields."""
        entry = LoreEntry(title="Test")

        assert entry.id is not None
        assert entry.created_at is not None
        assert entry.updated_at is not None
        assert entry.version == 1


class TestLoreEntryValidation:
    """Tests for LoreEntry validation rules."""

    def test_empty_title_fails(self):
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            LoreEntry(title="")

    def test_whitespace_only_title_fails(self):
        """Test that whitespace-only title raises ValueError."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            LoreEntry(title="   ")

    def test_title_too_long_fails(self):
        """Test that title exceeding 300 chars raises ValueError."""
        long_title = "x" * 301
        with pytest.raises(ValueError, match="cannot exceed 300 characters"):
            LoreEntry(title=long_title)

    def test_title_at_limit_succeeds(self):
        """Test that title at exactly 300 chars succeeds."""
        title = "x" * 300
        entry = LoreEntry(title=title)
        assert len(entry.title) == 300

    def test_too_many_tags_fails(self):
        """Test that more than 20 tags raises ValueError."""
        tags = [f"tag{i}" for i in range(21)]
        with pytest.raises(ValueError, match="more than 20 tags"):
            LoreEntry(title="Test", tags=tags)

    def test_max_tags_succeeds(self):
        """Test that exactly 20 tags succeeds."""
        tags = [f"tag{i}" for i in range(20)]
        entry = LoreEntry(title="Test", tags=tags)
        assert len(entry.tags) == 20


class TestLoreEntryTagOperations:
    """Tests for tag management operations."""

    def test_add_tag(self):
        """Test adding a tag."""
        entry = LoreEntry(title="Test")
        result = entry.add_tag("magic")

        assert result is True
        assert "magic" in entry.tags
        assert entry.version > 1  # Version incremented

    def test_add_tag_normalizes_case(self):
        """Test that tags are lowercased."""
        entry = LoreEntry(title="Test")
        entry.add_tag("MAGIC")

        assert "magic" in entry.tags
        assert "MAGIC" not in entry.tags

    def test_add_duplicate_tag_fails(self):
        """Test that adding duplicate tag returns False."""
        entry = LoreEntry(title="Test", tags=["magic"])
        result = entry.add_tag("magic")

        assert result is False
        assert entry.tags.count("magic") == 1

    def test_add_duplicate_tag_case_insensitive(self):
        """Test that duplicate detection is case-insensitive."""
        entry = LoreEntry(title="Test", tags=["magic"])
        result = entry.add_tag("MAGIC")

        assert result is False

    def test_add_empty_tag_fails(self):
        """Test that adding empty tag returns False."""
        entry = LoreEntry(title="Test")
        result = entry.add_tag("")

        assert result is False
        assert len(entry.tags) == 0

    def test_add_tag_exceeds_limit_raises(self):
        """Test that adding tag beyond 20 limit raises ValueError."""
        tags = [f"tag{i}" for i in range(20)]
        entry = LoreEntry(title="Test", tags=tags)

        with pytest.raises(ValueError, match="Cannot add more than 20 tags"):
            entry.add_tag("tag20")

    def test_add_tag_too_long_raises(self):
        """Test that tag over 50 chars raises ValueError."""
        entry = LoreEntry(title="Test")
        long_tag = "x" * 51

        with pytest.raises(ValueError, match="cannot exceed 50 characters"):
            entry.add_tag(long_tag)

    def test_remove_tag(self):
        """Test removing a tag."""
        entry = LoreEntry(title="Test", tags=["magic", "rules"])
        result = entry.remove_tag("magic")

        assert result is True
        assert "magic" not in entry.tags
        assert "rules" in entry.tags

    def test_remove_tag_case_insensitive(self):
        """Test that tag removal is case-insensitive."""
        entry = LoreEntry(title="Test", tags=["magic"])
        result = entry.remove_tag("MAGIC")

        assert result is True
        assert len(entry.tags) == 0

    def test_remove_nonexistent_tag_fails(self):
        """Test that removing nonexistent tag returns False."""
        entry = LoreEntry(title="Test", tags=["magic"])
        result = entry.remove_tag("rules")

        assert result is False
        assert "magic" in entry.tags

    def test_has_tag(self):
        """Test checking for tag existence."""
        entry = LoreEntry(title="Test", tags=["magic", "rules"])

        assert entry.has_tag("magic") is True
        assert entry.has_tag("MAGIC") is True  # Case-insensitive
        assert entry.has_tag("nonexistent") is False


class TestLoreEntryUpdateOperations:
    """Tests for update operations."""

    def test_update_title(self):
        """Test updating title."""
        entry = LoreEntry(title="Old Title")
        entry.update_title("New Title")

        assert entry.title == "New Title"
        assert entry.version > 1

    def test_update_title_strips_whitespace(self):
        """Test that title update strips whitespace."""
        entry = LoreEntry(title="Old")
        entry.update_title("  New  ")

        assert entry.title == "New"

    def test_update_title_empty_fails(self):
        """Test that empty title update raises ValueError."""
        entry = LoreEntry(title="Test")

        with pytest.raises(ValueError, match="cannot be empty"):
            entry.update_title("")

    def test_update_content(self):
        """Test updating content."""
        entry = LoreEntry(title="Test", content="Old content")
        entry.update_content("New content")

        assert entry.content == "New content"
        assert entry.version > 1

    def test_update_summary(self):
        """Test updating summary."""
        entry = LoreEntry(title="Test", summary="Old summary")
        entry.update_summary("New summary")

        assert entry.summary == "New summary"
        assert entry.version > 1

    def test_set_category(self):
        """Test changing category."""
        entry = LoreEntry(title="Test", category=LoreCategory.HISTORY)
        entry.set_category(LoreCategory.MAGIC)

        assert entry.category == LoreCategory.MAGIC
        assert entry.version > 1


class TestLoreEntryRelatedEntries:
    """Tests for related entry management."""

    def test_add_related_entry(self):
        """Test adding a related entry reference."""
        entry = LoreEntry(title="Test")
        result = entry.add_related_entry("related-001")

        assert result is True
        assert "related-001" in entry.related_entry_ids

    def test_add_duplicate_related_entry_fails(self):
        """Test that adding duplicate related entry returns False."""
        entry = LoreEntry(title="Test", related_entry_ids=["related-001"])
        result = entry.add_related_entry("related-001")

        assert result is False
        assert entry.related_entry_ids.count("related-001") == 1

    def test_add_self_reference_fails(self):
        """Test that self-reference returns False."""
        entry = LoreEntry(title="Test")
        result = entry.add_related_entry(entry.id)

        assert result is False

    def test_remove_related_entry(self):
        """Test removing a related entry reference."""
        entry = LoreEntry(title="Test", related_entry_ids=["related-001"])
        result = entry.remove_related_entry("related-001")

        assert result is True
        assert "related-001" not in entry.related_entry_ids


class TestLoreEntryCategoryHelpers:
    """Tests for category helper methods."""

    def test_is_history(self):
        """Test is_history helper."""
        entry = LoreEntry(title="Test", category=LoreCategory.HISTORY)
        assert entry.is_history() is True
        assert entry.is_culture() is False

    def test_is_culture(self):
        """Test is_culture helper."""
        entry = LoreEntry(title="Test", category=LoreCategory.CULTURE)
        assert entry.is_culture() is True
        assert entry.is_history() is False

    def test_is_magic(self):
        """Test is_magic helper."""
        entry = LoreEntry(title="Test", category=LoreCategory.MAGIC)
        assert entry.is_magic() is True
        assert entry.is_technology() is False

    def test_is_technology(self):
        """Test is_technology helper."""
        entry = LoreEntry(title="Test", category=LoreCategory.TECHNOLOGY)
        assert entry.is_technology() is True
        assert entry.is_magic() is False


class TestLoreEntryFactoryMethods:
    """Tests for factory methods."""

    def test_create_history_entry(self):
        """Test factory for history entries."""
        entry = LoreEntry.create_history_entry(
            title="The Great War",
            content="A thousand years ago...",
            tags=["war", "ancient"],
        )

        assert entry.title == "The Great War"
        assert entry.category == LoreCategory.HISTORY
        assert entry.tags == ["war", "ancient"]

    def test_create_culture_entry(self):
        """Test factory for culture entries."""
        entry = LoreEntry.create_culture_entry(
            title="Festival of Lights",
            content="Every autumn...",
        )

        assert entry.title == "Festival of Lights"
        assert entry.category == LoreCategory.CULTURE

    def test_create_magic_entry(self):
        """Test factory for magic entries."""
        entry = LoreEntry.create_magic_entry(
            title="The Binding Laws",
            content="All magic requires sacrifice...",
        )

        assert entry.title == "The Binding Laws"
        assert entry.category == LoreCategory.MAGIC

    def test_create_technology_entry(self):
        """Test factory for technology entries."""
        entry = LoreEntry.create_technology_entry(
            title="Steam Engines",
            content="The invention that changed everything...",
        )

        assert entry.title == "Steam Engines"
        assert entry.category == LoreCategory.TECHNOLOGY


class TestLoreEntrySerialization:
    """Tests for serialization methods."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        entry = LoreEntry(
            title="The Binding Laws",
            content="All magic requires sacrifice...",
            category=LoreCategory.MAGIC,
            tags=["magic", "rules"],
            summary="Magic rules summary",
        )

        data = entry.to_dict()

        assert data["title"] == "The Binding Laws"
        assert data["content"] == "All magic requires sacrifice..."
        assert data["category"] == "magic"
        assert data["tags"] == ["magic", "rules"]
        assert data["summary"] == "Magic rules summary"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "version" in data
