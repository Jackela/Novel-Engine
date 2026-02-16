#!/usr/bin/env python3
"""
Unit tests for Character Faction Membership (CHAR-035)

Tests the faction_id field on Character aggregate and the join_faction,
leave_faction, and related methods.
"""

import sys
from unittest.mock import MagicMock, Mock

import pytest

# Mock problematic dependencies

pytestmark = pytest.mark.unit

sys.modules["aioredis"] = MagicMock()
event_bus_mock = MagicMock()
event_mock = MagicMock()
event_mock.return_value = Mock()
event_bus_mock.Event = event_mock

# Save original module if it exists
_original_event_bus = sys.modules.get("src.events.event_bus")

sys.modules["src.events.event_bus"] = event_bus_mock

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
from src.contexts.character.domain.value_objects.skills import Skills

# Restore original module to avoid polluting other tests
if _original_event_bus is not None:
    sys.modules["src.events.event_bus"] = _original_event_bus
else:
    del sys.modules["src.events.event_bus"]


def _create_test_character(faction_id: str | None = None) -> Character:
    """Helper to create a valid character for testing."""
    profile = CharacterProfile(
        name="Test Character",
        gender=Gender.MALE,
        race=CharacterRace.HUMAN,
        character_class=CharacterClass.FIGHTER,
        age=25,
        level=1,
        physical_traits=PhysicalTraits(),
        personality_traits=PersonalityTraits(
            traits={
                "courage": 0.7,
                "intelligence": 0.5,
                "charisma": 0.5,
                "loyalty": 0.5,
            }
        ),
        background=Background(),
    )

    core_abilities = CoreAbilities(
        strength=14,
        dexterity=12,
        constitution=13,
        intelligence=10,
        wisdom=10,
        charisma=8,
    )

    vital_stats = VitalStats(
        max_health=30,
        current_health=30,
        max_mana=5,
        current_mana=5,
        max_stamina=28,
        current_stamina=28,
        armor_class=11,
        speed=30,
    )

    combat_stats = CombatStats(
        base_attack_bonus=0,
        initiative_modifier=1,
        damage_reduction=0,
        spell_resistance=0,
        critical_hit_chance=0.05,
        critical_damage_multiplier=2.0,
    )

    stats = CharacterStats(
        core_abilities=core_abilities,
        vital_stats=vital_stats,
        combat_stats=combat_stats,
        experience_points=0,
        skill_points=5,
    )

    skills = Skills.create_basic_skills()

    return Character(
        character_id=CharacterID.generate(),
        profile=profile,
        stats=stats,
        skills=skills,
        faction_id=faction_id,
    )


class TestCharacterFactionMembership:
    """Test suite for faction membership on Character aggregate."""

    # ==================== Initial State Tests ====================

    @pytest.mark.unit
    def test_character_default_no_faction(self):
        """Test that a new character has no faction by default."""
        character = _create_test_character()

        assert character.faction_id is None
        assert character.get_faction_id() is None
        assert character.is_in_faction() is False

    @pytest.mark.unit
    def test_character_created_with_faction(self):
        """Test character can be created with an initial faction."""
        faction_id = "faction-123"
        character = _create_test_character(faction_id=faction_id)

        assert character.faction_id == faction_id
        assert character.get_faction_id() == faction_id
        assert character.is_in_faction() is True
        assert character.is_in_faction(faction_id) is True

    # ==================== join_faction Tests ====================

    @pytest.mark.unit
    def test_join_faction_success(self):
        """Test successfully joining a faction."""
        character = _create_test_character()
        faction_id = "guild-of-merchants"
        initial_version = character.version

        character.join_faction(faction_id)

        assert character.faction_id == faction_id
        assert character.get_faction_id() == faction_id
        assert character.is_in_faction(faction_id) is True
        assert character.version == initial_version + 1

    @pytest.mark.unit
    def test_join_faction_emits_event(self):
        """Test that joining a faction records a domain event."""
        character = _create_test_character()
        character.clear_events()  # Clear creation event

        character.join_faction("test-faction")

        events = character.get_events()
        assert len(events) == 1
        assert events[0].get_event_type() == "character.updated"
        assert "faction_join" in events[0].updated_fields

    @pytest.mark.unit
    def test_join_faction_updates_timestamp(self):
        """Test that joining a faction updates the updated_at timestamp."""
        character = _create_test_character()
        old_updated_at = character.updated_at

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.01)

        character.join_faction("test-faction")

        assert character.updated_at > old_updated_at

    @pytest.mark.unit
    def test_join_faction_empty_id_raises(self):
        """Test that joining with empty faction ID raises ValueError."""
        character = _create_test_character()

        with pytest.raises(ValueError, match="cannot be empty"):
            character.join_faction("")

    @pytest.mark.unit
    def test_join_faction_whitespace_id_raises(self):
        """Test that joining with whitespace-only faction ID raises ValueError."""
        character = _create_test_character()

        with pytest.raises(ValueError, match="cannot be empty"):
            character.join_faction("   ")

    @pytest.mark.unit
    def test_join_same_faction_raises(self):
        """Test that joining the same faction again raises ValueError."""
        character = _create_test_character(faction_id="my-faction")

        with pytest.raises(ValueError, match="Already a member"):
            character.join_faction("my-faction")

    @pytest.mark.unit
    def test_join_different_faction_succeeds(self):
        """Test that a character can switch factions."""
        character = _create_test_character(faction_id="old-faction")

        # First leave, then join new (as per the method design requiring explicit leave)
        character.leave_faction()
        character.join_faction("new-faction")

        assert character.faction_id == "new-faction"

    # ==================== leave_faction Tests ====================

    @pytest.mark.unit
    def test_leave_faction_success(self):
        """Test successfully leaving a faction."""
        character = _create_test_character(faction_id="test-faction")
        initial_version = character.version

        result = character.leave_faction()

        assert result is True
        assert character.faction_id is None
        assert character.is_in_faction() is False
        assert character.version == initial_version + 1

    @pytest.mark.unit
    def test_leave_faction_when_not_member(self):
        """Test leaving a faction when not a member returns False."""
        character = _create_test_character()
        initial_version = character.version

        result = character.leave_faction()

        assert result is False
        assert character.faction_id is None
        assert character.version == initial_version  # No version change

    @pytest.mark.unit
    def test_leave_faction_emits_event(self):
        """Test that leaving a faction records a domain event."""
        character = _create_test_character(faction_id="test-faction")
        character.clear_events()

        character.leave_faction()

        events = character.get_events()
        assert len(events) == 1
        assert events[0].get_event_type() == "character.updated"
        assert "faction_leave" in events[0].updated_fields

    @pytest.mark.unit
    def test_leave_faction_updates_timestamp(self):
        """Test that leaving a faction updates the updated_at timestamp."""
        character = _create_test_character(faction_id="test-faction")
        old_updated_at = character.updated_at

        import time

        time.sleep(0.01)

        character.leave_faction()

        assert character.updated_at > old_updated_at

    # ==================== is_in_faction Tests ====================

    @pytest.mark.unit
    def test_is_in_faction_with_no_arg_when_member(self):
        """Test is_in_faction() returns True when in any faction."""
        character = _create_test_character(faction_id="any-faction")

        assert character.is_in_faction() is True

    @pytest.mark.unit
    def test_is_in_faction_with_no_arg_when_not_member(self):
        """Test is_in_faction() returns False when not in any faction."""
        character = _create_test_character()

        assert character.is_in_faction() is False

    @pytest.mark.unit
    def test_is_in_faction_specific_match(self):
        """Test is_in_faction(id) returns True for matching faction."""
        faction_id = "specific-faction"
        character = _create_test_character(faction_id=faction_id)

        assert character.is_in_faction(faction_id) is True

    @pytest.mark.unit
    def test_is_in_faction_specific_no_match(self):
        """Test is_in_faction(id) returns False for non-matching faction."""
        character = _create_test_character(faction_id="faction-a")

        assert character.is_in_faction("faction-b") is False

    @pytest.mark.unit
    def test_is_in_faction_specific_when_no_faction(self):
        """Test is_in_faction(id) returns False when not in any faction."""
        character = _create_test_character()

        assert character.is_in_faction("any-faction") is False

    # ==================== get_character_summary Tests ====================

    @pytest.mark.unit
    def test_summary_includes_faction_when_present(self):
        """Test that character summary includes faction_id when set."""
        faction_id = "warriors-guild"
        character = _create_test_character(faction_id=faction_id)

        summary = character.get_character_summary()

        assert "faction_id" in summary
        assert summary["faction_id"] == faction_id

    @pytest.mark.unit
    def test_summary_excludes_faction_when_absent(self):
        """Test that character summary excludes faction_id when not set."""
        character = _create_test_character()

        summary = character.get_character_summary()

        assert "faction_id" not in summary

    # ==================== Workflow Tests ====================

    @pytest.mark.unit
    def test_join_leave_join_workflow(self):
        """Test a complete join-leave-join workflow."""
        character = _create_test_character()

        # Join first faction
        character.join_faction("faction-1")
        assert character.is_in_faction("faction-1") is True

        # Leave faction
        character.leave_faction()
        assert character.is_in_faction() is False

        # Join new faction
        character.join_faction("faction-2")
        assert character.is_in_faction("faction-2") is True
        assert character.is_in_faction("faction-1") is False

    @pytest.mark.unit
    def test_multiple_faction_switches(self):
        """Test multiple faction switches maintain version consistency."""
        character = _create_test_character()
        initial_version = character.version

        # Multiple switches
        character.join_faction("faction-1")
        character.leave_faction()
        character.join_faction("faction-2")
        character.leave_faction()
        character.join_faction("faction-3")

        # 5 operations: join, leave, join, leave, join
        assert character.version == initial_version + 5
        assert character.faction_id == "faction-3"
