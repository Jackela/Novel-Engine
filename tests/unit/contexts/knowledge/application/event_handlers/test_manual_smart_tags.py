"""
Tests for manual smart tags override functionality.

BRAIN-038-05: Smart Tagging Manual Override
Tests that manual tags persist and are not overridden by auto-tagging.
"""

import pytest

from src.contexts.character.domain.aggregates.character import Character
from src.contexts.character.domain.value_objects.character_id import CharacterID
from src.contexts.character.domain.value_objects.character_profile import (
    Background,
    CharacterClass,
    CharacterProfile,
    CharacterRace,
    Gender,
    PersonalityTraits,
    PhysicalTraits,
)
from src.contexts.character.domain.value_objects.character_stats import (
    CharacterStats,
    CombatStats,
    CoreAbilities,
    VitalStats,
)
from src.contexts.narrative.domain.entities.scene import Scene, StoryPhase
from src.contexts.world.domain.entities.lore_entry import LoreCategory, LoreEntry

pytestmark = pytest.mark.unit


class TestLoreEntryManualSmartTags:
    """Test manual smart tags on LoreEntry entities."""

    def test_set_manual_smart_tags(self):
        """Test setting manual smart tags."""
        entry = LoreEntry.create_history_entry("Test Entry", "Test content")

        entry.set_manual_smart_tags("genre", ["fantasy", "epic"])

        assert entry.get_manual_smart_tags() == {"genre": ["fantasy", "epic"]}
        assert entry.metadata["manual_smart_tags"] == {"genre": ["fantasy", "epic"]}

    def test_get_manual_smart_tags_for_category(self):
        """Test getting manual tags for a specific category."""
        entry = LoreEntry.create_history_entry("Test Entry", "Test content")

        entry.set_manual_smart_tags("genre", ["fantasy"])
        entry.set_manual_smart_tags("mood", ["dark"])

        assert entry.get_manual_smart_tags_for_category("genre") == ["fantasy"]
        assert entry.get_manual_smart_tags_for_category("mood") == ["dark"]
        assert entry.get_manual_smart_tags_for_category("themes") == []

    def test_remove_manual_smart_tag(self):
        """Test removing a specific manual tag."""
        entry = LoreEntry.create_history_entry("Test Entry", "Test content")

        entry.set_manual_smart_tags("genre", ["fantasy", "epic", "adventure"])
        result = entry.remove_manual_smart_tag("genre", "epic")

        assert result is True
        assert entry.get_manual_smart_tags_for_category("genre") == [
            "fantasy",
            "adventure",
        ]

    def test_remove_nonexistent_manual_tag(self):
        """Test removing a tag that doesn't exist."""
        entry = LoreEntry.create_history_entry("Test Entry", "Test content")

        entry.set_manual_smart_tags("genre", ["fantasy"])
        result = entry.remove_manual_smart_tag("genre", "epic")

        assert result is False
        assert entry.get_manual_smart_tags_for_category("genre") == ["fantasy"]

    def test_clear_manual_smart_tags_category(self):
        """Test clearing manual tags for a specific category."""
        entry = LoreEntry.create_history_entry("Test Entry", "Test content")

        entry.set_manual_smart_tags("genre", ["fantasy"])
        entry.set_manual_smart_tags("mood", ["dark"])

        entry.clear_manual_smart_tags("genre")

        assert entry.get_manual_smart_tags_for_category("genre") == []
        assert entry.get_manual_smart_tags_for_category("mood") == ["dark"]

    def test_clear_all_manual_smart_tags(self):
        """Test clearing all manual tags."""
        entry = LoreEntry.create_history_entry("Test Entry", "Test content")

        entry.set_manual_smart_tags("genre", ["fantasy"])
        entry.set_manual_smart_tags("mood", ["dark"])

        entry.clear_manual_smart_tags()

        assert entry.get_manual_smart_tags() == {}

    def test_get_effective_smart_tags(self):
        """Test getting combined auto and manual tags."""
        entry = LoreEntry.create_history_entry("Test Entry", "Test content")

        # Set auto-generated tags
        entry.set_smart_tags({"genre": ["fantasy"], "mood": ["dark"]})

        # Set manual tags (one overlapping, one new)
        entry.set_manual_smart_tags("genre", ["epic"])  # Different from auto
        entry.set_manual_smart_tags("themes", ["redemption"])  # New category

        effective = entry.get_effective_smart_tags()

        # Genre should have both auto and manual
        assert set(effective["genre"]) == {"fantasy", "epic"}
        # Mood should only have auto
        assert effective["mood"] == ["dark"]
        # Themes should only have manual
        assert effective["themes"] == ["redemption"]

    def test_manual_tags_persist_after_auto_update(self):
        """Test that manual tags are preserved when auto tags are updated."""
        entry = LoreEntry.create_history_entry("Test Entry", "Test content")

        # Set initial manual tags
        entry.set_manual_smart_tags("genre", ["custom-genre"])
        entry.set_smart_tags({"genre": ["fantasy"]})

        # Simulate auto-tagging updating the smart tags
        entry.set_smart_tags({"genre": ["adventure"], "mood": ["dark"]})

        # Manual tags should still be accessible separately
        assert entry.get_manual_smart_tags_for_category("genre") == ["custom-genre"]

        # Effective tags should include both
        effective = entry.get_effective_smart_tags()
        assert set(effective["genre"]) == {"adventure", "custom-genre"}

    def test_set_manual_tags_normalizes_values(self):
        """Test that manual tags are normalized (lowercase, stripped)."""
        entry = LoreEntry.create_history_entry("Test Entry", "Test content")

        entry.set_manual_smart_tags("genre", ["  Fantasy  ", "EPIC", "adventure "])

        assert entry.get_manual_smart_tags() == {
            "genre": ["fantasy", "epic", "adventure"]
        }


class TestSceneManualSmartTags:
    """Test manual smart tags on Scene entities."""

    def test_set_manual_smart_tags(self):
        """Test setting manual smart tags on a scene."""
        from uuid import uuid4

        scene = Scene(
            title="Test Scene",
            chapter_id=uuid4(),
        )

        scene.set_manual_smart_tags("mood", ["tense", "suspenseful"])

        assert scene.get_manual_smart_tags() == {"mood": ["tense", "suspenseful"]}
        assert scene.metadata["manual_smart_tags"] == {"mood": ["tense", "suspenseful"]}

    def test_get_effective_smart_tags_scene(self):
        """Test getting combined auto and manual tags for scenes."""
        from uuid import uuid4

        scene = Scene(
            title="Test Scene",
            chapter_id=uuid4(),
        )

        # Set auto-generated and manual tags
        scene.set_smart_tags({"mood": ["tense"]})
        scene.set_manual_smart_tags("mood", ["dramatic"])

        effective = scene.get_effective_smart_tags()

        assert set(effective["mood"]) == {"tense", "dramatic"}

    def test_remove_manual_smart_tag_scene(self):
        """Test removing a manual tag from a scene."""
        from uuid import uuid4

        scene = Scene(
            title="Test Scene",
            chapter_id=uuid4(),
        )

        scene.set_manual_smart_tags("themes", ["betrayal", "loyalty"])
        result = scene.remove_manual_smart_tag("themes", "betrayal")

        assert result is True
        assert scene.get_manual_smart_tags_for_category("themes") == ["loyalty"]


class TestCharacterManualSmartTags:
    """Test manual smart tags on Character aggregates."""

    def test_set_manual_smart_tags(self):
        """Test setting manual smart tags on a character."""
        character = Character.create_new_character(
            name="Test Character",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=25,
            core_abilities=CoreAbilities(
                strength=10,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
            ),
        )

        character.set_manual_smart_tags("themes", ["redemption", "honor"])

        assert character.get_manual_smart_tags() == {"themes": ["redemption", "honor"]}
        assert character.version == 2  # Version should increment

    def test_get_effective_smart_tags_character(self):
        """Test getting combined auto and manual tags for characters."""
        character = Character.create_new_character(
            name="Test Character",
            gender=Gender.FEMALE,
            race=CharacterRace.ELF,
            character_class=CharacterClass.WIZARD,
            age=120,
            core_abilities=CoreAbilities(
                strength=8,
                dexterity=14,
                constitution=10,
                intelligence=16,
                wisdom=12,
                charisma=10,
            ),
        )

        character.set_smart_tags({"characters_present": ["protagonist"]})
        character.set_manual_smart_tags("themes", ["knowledge"])

        effective = character.get_effective_smart_tags()

        assert effective["characters_present"] == ["protagonist"]
        assert effective["themes"] == ["knowledge"]

    def test_clear_manual_smart_tags_character(self):
        """Test clearing manual tags from a character."""
        character = Character.create_new_character(
            name="Test Character",
            gender=Gender.MALE,
            race=CharacterRace.DWARF,
            character_class=CharacterClass.CLERIC,
            age=50,
            core_abilities=CoreAbilities(
                strength=14,
                dexterity=10,
                constitution=16,
                intelligence=10,
                wisdom=16,
                charisma=10,
            ),
        )

        character.set_manual_smart_tags("mood", ["stoic"])
        character.clear_manual_smart_tags("mood")

        assert character.get_manual_smart_tags() == {}
        assert character.version == 3  # Incremented twice (set + clear)
