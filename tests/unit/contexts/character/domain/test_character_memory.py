#!/usr/bin/env python3
"""
Unit tests for Character Memory Value Object and Aggregate Integration

Comprehensive test suite for the CharacterMemory value object and its
integration with the Character aggregate.
"""

import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock

import pytest

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()
event_bus_mock = MagicMock()
event_mock = MagicMock()
event_mock.return_value = Mock()
event_bus_mock.Event = event_mock
sys.modules["src.events.event_bus"] = event_bus_mock

from src.contexts.character.domain.value_objects.character_memory import (
    CharacterMemory,
)


class TestCharacterMemoryValueObject:
    """Test suite for CharacterMemory value object."""

    @pytest.mark.unit
    def test_memory_creation_success(self):
        """Test successful memory creation with all fields."""
        memory = CharacterMemory(
            content="I saw the castle burn",
            importance=8,
            tags=("trauma", "fire"),
        )

        assert memory.content == "I saw the castle burn"
        assert memory.importance == 8
        assert memory.tags == ("trauma", "fire")
        assert isinstance(memory.timestamp, datetime)
        assert isinstance(memory.memory_id, str)
        assert len(memory.memory_id) > 0

    @pytest.mark.unit
    def test_memory_creation_with_factory(self):
        """Test memory creation using factory method."""
        timestamp = datetime(2025, 1, 1, 12, 0, 0)
        memory = CharacterMemory.create(
            content="Met a stranger in the woods",
            importance=5,
            tags=["encounter", "woods"],
            timestamp=timestamp,
        )

        assert memory.content == "Met a stranger in the woods"
        assert memory.importance == 5
        assert memory.tags == ("encounter", "woods")
        assert memory.timestamp == timestamp

    @pytest.mark.unit
    def test_memory_creation_minimal(self):
        """Test memory creation with minimal required fields."""
        memory = CharacterMemory(
            content="A simple memory",
            importance=1,
            tags=(),
        )

        assert memory.content == "A simple memory"
        assert memory.importance == 1
        assert memory.tags == ()

    # ==================== Validation Tests ====================

    @pytest.mark.unit
    def test_memory_invalid_empty_content(self):
        """Test that empty content raises ValueError."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            CharacterMemory(
                content="   ",
                importance=5,
                tags=(),
            )

    @pytest.mark.unit
    def test_memory_invalid_content_type(self):
        """Test that non-string content raises TypeError."""
        with pytest.raises(TypeError, match="content must be a string"):
            CharacterMemory(
                content=123,
                importance=5,
                tags=(),
            )

    @pytest.mark.unit
    def test_memory_invalid_importance_too_low(self):
        """Test that importance below 1 raises ValueError."""
        with pytest.raises(ValueError, match="importance must be between 1 and 10"):
            CharacterMemory(
                content="A memory",
                importance=0,
                tags=(),
            )

    @pytest.mark.unit
    def test_memory_invalid_importance_too_high(self):
        """Test that importance above 10 raises ValueError."""
        with pytest.raises(ValueError, match="importance must be between 1 and 10"):
            CharacterMemory(
                content="A memory",
                importance=11,
                tags=(),
            )

    @pytest.mark.unit
    def test_memory_invalid_importance_type(self):
        """Test that non-integer importance raises TypeError."""
        with pytest.raises(TypeError, match="importance must be an integer"):
            CharacterMemory(
                content="A memory",
                importance=5.5,
                tags=(),
            )

    @pytest.mark.unit
    def test_memory_invalid_tag_type(self):
        """Test that non-string tags raise TypeError."""
        with pytest.raises(TypeError, match="each tag must be a string"):
            CharacterMemory(
                content="A memory",
                importance=5,
                tags=(123, "valid"),
            )

    @pytest.mark.unit
    def test_memory_invalid_empty_tag(self):
        """Test that empty tags raise ValueError."""
        with pytest.raises(ValueError, match="tags cannot contain empty strings"):
            CharacterMemory(
                content="A memory",
                importance=5,
                tags=("valid", "   "),
            )

    @pytest.mark.unit
    def test_memory_tags_list_converted_to_tuple(self):
        """Test that tags list is converted to tuple for immutability."""
        memory = CharacterMemory(
            content="A memory",
            importance=5,
            tags=["tag1", "tag2"],
        )
        assert isinstance(memory.tags, tuple)
        assert memory.tags == ("tag1", "tag2")

    # ==================== Business Logic Tests ====================

    @pytest.mark.unit
    def test_is_core_memory_true(self):
        """Test that memories with importance > 8 are core memories."""
        memory = CharacterMemory(
            content="Defining moment",
            importance=9,
            tags=(),
        )
        assert memory.is_core_memory() is True

    @pytest.mark.unit
    def test_is_core_memory_false(self):
        """Test that memories with importance <= 8 are not core memories."""
        memory = CharacterMemory(
            content="Regular memory",
            importance=8,
            tags=(),
        )
        assert memory.is_core_memory() is False

    @pytest.mark.unit
    def test_has_tag_case_insensitive(self):
        """Test that tag matching is case-insensitive."""
        memory = CharacterMemory(
            content="A memory",
            importance=5,
            tags=("Trauma", "FIRE"),
        )
        assert memory.has_tag("trauma") is True
        assert memory.has_tag("TRAUMA") is True
        assert memory.has_tag("fire") is True
        assert memory.has_tag("water") is False

    @pytest.mark.unit
    def test_get_importance_level_minor(self):
        """Test importance level 'minor' for 1-3."""
        for importance in [1, 2, 3]:
            memory = CharacterMemory(
                content="Memory",
                importance=importance,
                tags=(),
            )
            assert memory.get_importance_level() == "minor"

    @pytest.mark.unit
    def test_get_importance_level_moderate(self):
        """Test importance level 'moderate' for 4-6."""
        for importance in [4, 5, 6]:
            memory = CharacterMemory(
                content="Memory",
                importance=importance,
                tags=(),
            )
            assert memory.get_importance_level() == "moderate"

    @pytest.mark.unit
    def test_get_importance_level_significant(self):
        """Test importance level 'significant' for 7-8."""
        for importance in [7, 8]:
            memory = CharacterMemory(
                content="Memory",
                importance=importance,
                tags=(),
            )
            assert memory.get_importance_level() == "significant"

    @pytest.mark.unit
    def test_get_importance_level_core(self):
        """Test importance level 'core' for 9-10."""
        for importance in [9, 10]:
            memory = CharacterMemory(
                content="Memory",
                importance=importance,
                tags=(),
            )
            assert memory.get_importance_level() == "core"

    # ==================== Serialization Tests ====================

    @pytest.mark.unit
    def test_to_dict(self):
        """Test conversion to dictionary."""
        timestamp = datetime(2025, 1, 1, 12, 0, 0)
        memory = CharacterMemory(
            content="Important event",
            importance=9,
            tags=("defining", "growth"),
            timestamp=timestamp,
            memory_id="test-id-123",
        )

        result = memory.to_dict()

        assert result["memory_id"] == "test-id-123"
        assert result["content"] == "Important event"
        assert result["importance"] == 9
        assert result["tags"] == ["defining", "growth"]
        assert result["timestamp"] == "2025-01-01T12:00:00"
        assert result["is_core_memory"] is True
        assert result["importance_level"] == "core"

    @pytest.mark.unit
    def test_get_summary_short_content(self):
        """Test summary generation for short content."""
        memory = CharacterMemory(
            content="Short memory",
            importance=5,
            tags=(),
        )

        summary = memory.get_summary()
        assert "[MODERATE]" in summary
        assert "Short memory" in summary

    @pytest.mark.unit
    def test_get_summary_long_content(self):
        """Test summary generation truncates long content."""
        long_content = "A" * 100
        memory = CharacterMemory(
            content=long_content,
            importance=10,
            tags=(),
        )

        summary = memory.get_summary()
        assert "[CORE]" in summary
        assert "..." in summary
        assert len(summary) < len(long_content) + 20

    # ==================== Immutability Tests ====================

    @pytest.mark.unit
    def test_memory_is_frozen(self):
        """Test that CharacterMemory is immutable."""
        memory = CharacterMemory(
            content="Immutable memory",
            importance=5,
            tags=(),
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            memory.content = "New content"


class TestCharacterMemoryAggregateIntegration:
    """Test suite for CharacterMemory integration with Character aggregate."""

    @pytest.fixture
    def sample_character(self):
        """Create a test Character instance."""
        from src.contexts.character.domain.aggregates.character import Character
        from src.contexts.character.domain.value_objects.character_id import (
            CharacterID,
        )
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

        profile = CharacterProfile(
            name="Test Character",
            gender=Gender.FEMALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=25,
            level=1,
            physical_traits=PhysicalTraits(),
            personality_traits=PersonalityTraits(
                traits={"courage": 0.8, "intelligence": 0.6, "charisma": 0.5, "loyalty": 0.9}
            ),
            background=Background(),
        )

        core_abilities = CoreAbilities(
            strength=15, dexterity=14, constitution=16,
            intelligence=12, wisdom=13, charisma=11,
        )
        vital_stats = VitalStats(
            max_health=36, current_health=36,
            max_mana=15, current_mana=15,
            max_stamina=31, current_stamina=31,
            armor_class=12, speed=30,
        )
        combat_stats = CombatStats(
            base_attack_bonus=0, initiative_modifier=2,
            damage_reduction=0, spell_resistance=0,
            critical_hit_chance=0.05, critical_damage_multiplier=2.0,
        )
        stats = CharacterStats(
            core_abilities=core_abilities,
            vital_stats=vital_stats,
            combat_stats=combat_stats,
            experience_points=0, skill_points=5,
        )

        # Create mock skills
        from src.contexts.character.domain.value_objects.skills import (
            ProficiencyLevel, Skill, SkillCategory,
        )
        combat_skill = Skill(
            name="Melee Combat", category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.NOVICE, modifier=0,
        )
        physical_skill = Skill(
            name="Athletics", category=SkillCategory.PHYSICAL,
            proficiency_level=ProficiencyLevel.APPRENTICE, modifier=1,
        )
        skills = Mock()
        skills.skill_groups = {
            SkillCategory.COMBAT: [combat_skill],
            SkillCategory.PHYSICAL: [physical_skill],
        }
        skills.get_skills_by_category = Mock(
            side_effect=lambda cat: skills.skill_groups.get(cat, [])
        )
        skills.get_skill_summary = Mock(
            return_value={"total_skills": 2, "trained_skills": 2}
        )

        return Character(
            character_id=CharacterID.generate(),
            profile=profile,
            stats=stats,
            skills=skills,
        )

    @pytest.mark.unit
    def test_add_memory_success(self, sample_character):
        """Test successfully adding a memory to character."""
        initial_version = sample_character.version

        memory = CharacterMemory(
            content="First memory",
            importance=5,
            tags=("test",),
        )

        sample_character.add_memory(memory)

        assert len(sample_character.memories) == 1
        assert sample_character.memories[0] == memory
        assert sample_character.version == initial_version + 1

    @pytest.mark.unit
    def test_add_memory_invalid_type(self, sample_character):
        """Test that adding non-CharacterMemory raises TypeError."""
        with pytest.raises(TypeError, match="Expected CharacterMemory"):
            sample_character.add_memory("not a memory")

    @pytest.mark.unit
    def test_add_multiple_memories(self, sample_character):
        """Test adding multiple memories."""
        memories = [
            CharacterMemory(content=f"Memory {i}", importance=i, tags=())
            for i in range(1, 4)
        ]

        for memory in memories:
            sample_character.add_memory(memory)

        assert len(sample_character.memories) == 3

    @pytest.mark.unit
    def test_get_memories_returns_copy(self, sample_character):
        """Test that get_memories returns a copy, not original list."""
        memory = CharacterMemory(content="Test", importance=5, tags=())
        sample_character.add_memory(memory)

        memories = sample_character.get_memories()
        memories.clear()

        assert len(sample_character.memories) == 1

    @pytest.mark.unit
    def test_get_core_memories(self, sample_character):
        """Test filtering for core memories only."""
        memories = [
            CharacterMemory(content="Regular", importance=5, tags=()),
            CharacterMemory(content="Core 1", importance=9, tags=()),
            CharacterMemory(content="Significant", importance=8, tags=()),
            CharacterMemory(content="Core 2", importance=10, tags=()),
        ]

        for memory in memories:
            sample_character.add_memory(memory)

        core = sample_character.get_core_memories()
        assert len(core) == 2
        assert all(m.is_core_memory() for m in core)

    @pytest.mark.unit
    def test_get_memories_by_tag(self, sample_character):
        """Test filtering memories by tag."""
        memories = [
            CharacterMemory(content="Family event", importance=7, tags=("family",)),
            CharacterMemory(content="Work memory", importance=5, tags=("work",)),
            CharacterMemory(content="Family trauma", importance=9, tags=("family", "trauma")),
        ]

        for memory in memories:
            sample_character.add_memory(memory)

        family_memories = sample_character.get_memories_by_tag("family")
        assert len(family_memories) == 2

    @pytest.mark.unit
    def test_get_recent_memories(self, sample_character):
        """Test getting most recent memories."""
        base_time = datetime(2025, 1, 1)
        memories = [
            CharacterMemory(
                content=f"Memory {i}",
                importance=5,
                tags=(),
                timestamp=base_time + timedelta(days=i),
            )
            for i in range(10)
        ]

        for memory in memories:
            sample_character.add_memory(memory)

        recent = sample_character.get_recent_memories(count=3)
        assert len(recent) == 3
        # Most recent should be first
        assert recent[0].content == "Memory 9"
        assert recent[1].content == "Memory 8"
        assert recent[2].content == "Memory 7"

    @pytest.mark.unit
    def test_character_summary_includes_memories(self, sample_character):
        """Test that character summary includes memory information."""
        memories = [
            CharacterMemory(content="Regular", importance=5, tags=()),
            CharacterMemory(content="Core", importance=10, tags=()),
        ]

        for memory in memories:
            sample_character.add_memory(memory)

        summary = sample_character.get_character_summary()

        assert "memories" in summary
        assert "memory_count" in summary
        assert summary["memory_count"] == 2
        assert "core_memory_count" in summary
        assert summary["core_memory_count"] == 1

    @pytest.mark.unit
    def test_add_memory_raises_event(self, sample_character):
        """Test that adding memory raises CharacterUpdated event."""
        initial_events = len(sample_character.get_events())

        memory = CharacterMemory(content="Event test", importance=5, tags=())
        sample_character.add_memory(memory)

        events = sample_character.get_events()
        assert len(events) > initial_events

        # The latest event should be about memory update
        latest_event = events[-1]
        assert "memories" in latest_event.updated_fields
