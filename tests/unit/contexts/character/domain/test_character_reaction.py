#!/usr/bin/env python3
"""
Tests for CharacterReaction Value Object

This module tests the CharacterReaction value object which represents
a character's emotional or behavioral response to a world event.
"""

import pytest
from datetime import datetime
from unittest.mock import patch

from src.contexts.character.domain.value_objects.character_reaction import (
    CharacterReaction,
    ReactionType,
)

pytestmark = pytest.mark.unit


class TestReactionTypeEnum:
    """Tests for ReactionType enum."""

    def test_all_reaction_types_exist(self):
        """Test that all required reaction types are defined."""
        assert ReactionType.OBSERVE == "OBSERVE"
        assert ReactionType.FLEE == "FLEE"
        assert ReactionType.INVESTIGATE == "INVESTIGATE"
        assert ReactionType.IGNORE == "IGNORE"
        assert ReactionType.CELEBRATE == "CELEBRATE"
        assert ReactionType.MOURN == "MOURN"
        assert ReactionType.PROTEST == "PROTEST"

    def test_count_of_reaction_types(self):
        """Test that there are exactly 7 reaction types."""
        assert len(ReactionType) == 7

    def test_is_active_property(self):
        """Test is_active property returns correct values."""
        # Active reactions involve doing something
        assert ReactionType.FLEE.is_active is True
        assert ReactionType.INVESTIGATE.is_active is True
        assert ReactionType.CELEBRATE.is_active is True
        assert ReactionType.PROTEST.is_active is True

        # Non-active reactions
        assert ReactionType.OBSERVE.is_active is False
        assert ReactionType.IGNORE.is_active is False
        assert ReactionType.MOURN.is_active is False

    def test_is_emotional_property(self):
        """Test is_emotional property returns correct values."""
        # Emotional reactions
        assert ReactionType.CELEBRATE.is_emotional is True
        assert ReactionType.MOURN.is_emotional is True
        assert ReactionType.PROTEST.is_emotional is True

        # Non-emotional reactions
        assert ReactionType.OBSERVE.is_emotional is False
        assert ReactionType.FLEE.is_emotional is False
        assert ReactionType.INVESTIGATE.is_emotional is False
        assert ReactionType.IGNORE.is_emotional is False

    def test_creates_memory_property(self):
        """Test creates_memory property returns correct values."""
        # IGNORE does not create memory
        assert ReactionType.IGNORE.creates_memory is False

        # All other types create memory
        assert ReactionType.OBSERVE.creates_memory is True
        assert ReactionType.FLEE.creates_memory is True
        assert ReactionType.INVESTIGATE.creates_memory is True
        assert ReactionType.CELEBRATE.creates_memory is True
        assert ReactionType.MOURN.creates_memory is True
        assert ReactionType.PROTEST.creates_memory is True

    def test_reaction_type_from_string(self):
        """Test creating ReactionType from string value."""
        assert ReactionType("OBSERVE") == ReactionType.OBSERVE
        assert ReactionType("FLEE") == ReactionType.FLEE
        assert ReactionType("IGNORE") == ReactionType.IGNORE

    def test_reaction_type_invalid_string_raises(self):
        """Test that invalid string raises ValueError."""
        with pytest.raises(ValueError):
            ReactionType("INVALID_TYPE")


class TestCharacterReactionCreation:
    """Tests for CharacterReaction creation and validation."""

    def test_create_basic_reaction(self):
        """Test creating a basic reaction with required fields."""
        reaction = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=5,
            narrative="Test character observed the event.",
        )

        assert reaction.character_id == "char-1"
        assert reaction.event_id == "event-1"
        assert reaction.reaction_type == ReactionType.OBSERVE
        assert reaction.intensity == 5
        assert reaction.narrative == "Test character observed the event."
        assert reaction.memory_created is False
        assert isinstance(reaction.reaction_id, str)
        assert isinstance(reaction.created_at, datetime)

    def test_create_reaction_with_all_fields(self):
        """Test creating a reaction with all fields specified."""
        fixed_time = datetime(2024, 1, 15, 10, 30, 0)

        reaction = CharacterReaction(
            reaction_id="reaction-123",
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.CELEBRATE,
            intensity=8,
            narrative="Celebrating the victory!",
            memory_created=True,
            created_at=fixed_time,
        )

        assert reaction.reaction_id == "reaction-123"
        assert reaction.character_id == "char-1"
        assert reaction.event_id == "event-1"
        assert reaction.reaction_type == ReactionType.CELEBRATE
        assert reaction.intensity == 8
        assert reaction.narrative == "Celebrating the victory!"
        assert reaction.memory_created is True
        assert reaction.created_at == fixed_time

    def test_create_with_string_reaction_type(self):
        """Test creating reaction with string reaction_type that gets converted."""
        reaction = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type="FLEE",  # String instead of enum
            intensity=7,
            narrative="Running away!",
        )

        assert reaction.reaction_type == ReactionType.FLEE

    def test_create_with_lowercase_reaction_type(self):
        """Test that lowercase string reaction_type raises error."""
        with pytest.raises(ValueError, match="Invalid reaction_type"):
            CharacterReaction(
                character_id="char-1",
                event_id="event-1",
                reaction_type="flee",  # lowercase
                intensity=7,
                narrative="Running away!",
            )

    def test_create_with_invalid_reaction_type(self):
        """Test that invalid reaction_type string raises error."""
        with pytest.raises(ValueError, match="Invalid reaction_type"):
            CharacterReaction(
                character_id="char-1",
                event_id="event-1",
                reaction_type="DANCE",
                intensity=5,
                narrative="Dancing!",
            )

    def test_factory_method_create(self):
        """Test the create factory method."""
        reaction = CharacterReaction.create(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.MOURN,
            intensity=9,
            narrative="Mourning the loss of a friend.",
            memory_created=True,
        )

        assert reaction.character_id == "char-1"
        assert reaction.event_id == "event-1"
        assert reaction.reaction_type == ReactionType.MOURN
        assert reaction.intensity == 9
        assert reaction.narrative == "Mourning the loss of a friend."
        assert reaction.memory_created is True


class TestCharacterReactionValidation:
    """Tests for CharacterReaction validation."""

    def test_empty_reaction_id_raises(self):
        """Test that empty reaction_id raises ValueError."""
        with pytest.raises(ValueError, match="reaction_id cannot be empty"):
            CharacterReaction(
                reaction_id="",
                character_id="char-1",
                event_id="event-1",
                reaction_type=ReactionType.OBSERVE,
                intensity=5,
                narrative="Test narrative",
            )

    def test_empty_character_id_raises(self):
        """Test that empty character_id raises ValueError."""
        with pytest.raises(ValueError, match="character_id cannot be empty"):
            CharacterReaction(
                character_id="",
                event_id="event-1",
                reaction_type=ReactionType.OBSERVE,
                intensity=5,
                narrative="Test narrative",
            )

    def test_empty_event_id_raises(self):
        """Test that empty event_id raises ValueError."""
        with pytest.raises(ValueError, match="event_id cannot be empty"):
            CharacterReaction(
                character_id="char-1",
                event_id="",
                reaction_type=ReactionType.OBSERVE,
                intensity=5,
                narrative="Test narrative",
            )

    def test_empty_narrative_raises(self):
        """Test that empty narrative raises ValueError."""
        with pytest.raises(ValueError, match="narrative cannot be empty"):
            CharacterReaction(
                character_id="char-1",
                event_id="event-1",
                reaction_type=ReactionType.OBSERVE,
                intensity=5,
                narrative="",
            )

    def test_whitespace_narrative_raises(self):
        """Test that whitespace-only narrative raises ValueError."""
        with pytest.raises(ValueError, match="narrative cannot be empty"):
            CharacterReaction(
                character_id="char-1",
                event_id="event-1",
                reaction_type=ReactionType.OBSERVE,
                intensity=5,
                narrative="   ",
            )

    def test_intensity_below_minimum_raises(self):
        """Test that intensity below 1 raises ValueError."""
        with pytest.raises(ValueError, match="intensity must be between 1 and 10"):
            CharacterReaction(
                character_id="char-1",
                event_id="event-1",
                reaction_type=ReactionType.OBSERVE,
                intensity=0,
                narrative="Test narrative",
            )

    def test_intensity_above_maximum_raises(self):
        """Test that intensity above 10 raises ValueError."""
        with pytest.raises(ValueError, match="intensity must be between 1 and 10"):
            CharacterReaction(
                character_id="char-1",
                event_id="event-1",
                reaction_type=ReactionType.OBSERVE,
                intensity=11,
                narrative="Test narrative",
            )

    def test_negative_intensity_raises(self):
        """Test that negative intensity raises ValueError."""
        with pytest.raises(ValueError, match="intensity must be between 1 and 10"):
            CharacterReaction(
                character_id="char-1",
                event_id="event-1",
                reaction_type=ReactionType.OBSERVE,
                intensity=-5,
                narrative="Test narrative",
            )

    def test_intensity_boundary_values(self):
        """Test intensity at boundary values (1 and 10)."""
        # Min boundary
        reaction_min = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=1,
            narrative="Minimal reaction",
        )
        assert reaction_min.intensity == 1

        # Max boundary
        reaction_max = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=10,
            narrative="Maximum reaction",
        )
        assert reaction_max.intensity == 10

    def test_invalid_reaction_id_type_raises(self):
        """Test that non-string reaction_id raises TypeError."""
        with pytest.raises(TypeError, match="reaction_id must be a string"):
            CharacterReaction(
                reaction_id=123,
                character_id="char-1",
                event_id="event-1",
                reaction_type=ReactionType.OBSERVE,
                intensity=5,
                narrative="Test narrative",
            )

    def test_invalid_character_id_type_raises(self):
        """Test that non-string character_id raises TypeError."""
        with pytest.raises(TypeError, match="character_id must be a string"):
            CharacterReaction(
                character_id=123,
                event_id="event-1",
                reaction_type=ReactionType.OBSERVE,
                intensity=5,
                narrative="Test narrative",
            )

    def test_invalid_event_id_type_raises(self):
        """Test that non-string event_id raises TypeError."""
        with pytest.raises(TypeError, match="event_id must be a string"):
            CharacterReaction(
                character_id="char-1",
                event_id=123,
                reaction_type=ReactionType.OBSERVE,
                intensity=5,
                narrative="Test narrative",
            )

    def test_invalid_intensity_type_raises(self):
        """Test that non-int intensity raises TypeError."""
        with pytest.raises(TypeError, match="intensity must be an int"):
            CharacterReaction(
                character_id="char-1",
                event_id="event-1",
                reaction_type=ReactionType.OBSERVE,
                intensity="high",
                narrative="Test narrative",
            )

    def test_invalid_narrative_type_raises(self):
        """Test that non-string narrative raises TypeError."""
        with pytest.raises(TypeError, match="narrative must be a string"):
            CharacterReaction(
                character_id="char-1",
                event_id="event-1",
                reaction_type=ReactionType.OBSERVE,
                intensity=5,
                narrative=123,
            )

    def test_invalid_memory_created_type_raises(self):
        """Test that non-bool memory_created raises TypeError."""
        with pytest.raises(TypeError, match="memory_created must be a bool"):
            CharacterReaction(
                character_id="char-1",
                event_id="event-1",
                reaction_type=ReactionType.OBSERVE,
                intensity=5,
                narrative="Test narrative",
                memory_created="yes",
            )

    def test_invalid_created_at_type_raises(self):
        """Test that non-datetime created_at raises TypeError."""
        with pytest.raises(TypeError, match="created_at must be a datetime"):
            CharacterReaction(
                character_id="char-1",
                event_id="event-1",
                reaction_type=ReactionType.OBSERVE,
                intensity=5,
                narrative="Test narrative",
                created_at="2024-01-15",
            )


class TestCharacterReactionMethods:
    """Tests for CharacterReaction methods."""

    def test_is_intense_default_threshold(self):
        """Test is_intense with default threshold (7)."""
        intense_reaction = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.FLEE,
            intensity=8,
            narrative="Running for life!",
        )
        assert intense_reaction.is_intense() is True

        mild_reaction = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=5,
            narrative="Just watching.",
        )
        assert mild_reaction.is_intense() is False

    def test_is_intense_custom_threshold(self):
        """Test is_intense with custom threshold."""
        reaction = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=5,
            narrative="Test narrative",
        )

        assert reaction.is_intense(threshold=3) is True
        assert reaction.is_intense(threshold=5) is True
        assert reaction.is_intense(threshold=6) is False

    def test_is_mild(self):
        """Test is_mild method (intensity <= 3)."""
        mild_reaction = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.IGNORE,
            intensity=2,
            narrative="Barely noticed.",
        )
        assert mild_reaction.is_mild() is True

        not_mild_reaction = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=4,
            narrative="Noticing more.",
        )
        assert not_mild_reaction.is_mild() is False

    def test_should_create_memory_ignore_type(self):
        """Test should_create_memory returns False for IGNORE type."""
        reaction = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.IGNORE,
            intensity=8,  # High intensity but IGNORE type
            narrative="Not interested.",
        )
        assert reaction.should_create_memory() is False

    def test_should_create_memory_low_intensity(self):
        """Test should_create_memory returns False for low intensity (< 4)."""
        reaction = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=3,  # Low intensity
            narrative="Barely noticed.",
        )
        assert reaction.should_create_memory() is False

    def test_should_create_memory_true(self):
        """Test should_create_memory returns True for non-IGNORE with intensity >= 4."""
        reaction = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=4,  # At threshold
            narrative="Noticed.",
        )
        assert reaction.should_create_memory() is True

        high_intensity = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.CELEBRATE,
            intensity=9,
            narrative="Celebrating!",
        )
        assert high_intensity.should_create_memory() is True

    def test_with_memory_created(self):
        """Test with_memory_created returns new instance with memory_created=True."""
        original = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.CELEBRATE,
            intensity=7,
            narrative="Celebrating!",
            memory_created=False,
        )

        updated = original.with_memory_created()

        # Original unchanged
        assert original.memory_created is False

        # Updated has memory_created=True
        assert updated.memory_created is True
        assert updated.reaction_id == original.reaction_id
        assert updated.character_id == original.character_id
        assert updated.event_id == original.event_id
        assert updated.reaction_type == original.reaction_type
        assert updated.intensity == original.intensity
        assert updated.narrative == original.narrative
        assert updated.created_at == original.created_at

    def test_to_dict(self):
        """Test to_dict serialization."""
        fixed_time = datetime(2024, 1, 15, 10, 30, 0)

        reaction = CharacterReaction(
            reaction_id="reaction-123",
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.CELEBRATE,
            intensity=8,
            narrative="Celebrating the victory!",
            memory_created=True,
            created_at=fixed_time,
        )

        result = reaction.to_dict()

        assert result["reaction_id"] == "reaction-123"
        assert result["character_id"] == "char-1"
        assert result["event_id"] == "event-1"
        assert result["reaction_type"] == "CELEBRATE"
        assert result["intensity"] == 8
        assert result["narrative"] == "Celebrating the victory!"
        assert result["memory_created"] is True
        assert result["created_at"] == "2024-01-15T10:30:00"
        assert result["is_intense"] is True
        assert result["is_mild"] is False

    def test_from_dict(self):
        """Test from_dict deserialization."""
        data = {
            "reaction_id": "reaction-456",
            "character_id": "char-2",
            "event_id": "event-2",
            "reaction_type": "MOURN",
            "intensity": 9,
            "narrative": "Saddened by the news.",
            "memory_created": True,
            "created_at": "2024-02-20T14:00:00",
        }

        reaction = CharacterReaction.from_dict(data)

        assert reaction.reaction_id == "reaction-456"
        assert reaction.character_id == "char-2"
        assert reaction.event_id == "event-2"
        assert reaction.reaction_type == ReactionType.MOURN
        assert reaction.intensity == 9
        assert reaction.narrative == "Saddened by the news."
        assert reaction.memory_created is True
        assert reaction.created_at == datetime(2024, 2, 20, 14, 0, 0)

    def test_from_dict_with_enum_type(self):
        """Test from_dict with ReactionType enum instead of string."""
        data = {
            "reaction_id": "reaction-789",
            "character_id": "char-3",
            "event_id": "event-3",
            "reaction_type": ReactionType.INVESTIGATE,
            "intensity": 6,
            "narrative": "Looking into it.",
        }

        reaction = CharacterReaction.from_dict(data)

        assert reaction.reaction_type == ReactionType.INVESTIGATE

    def test_from_dict_defaults(self):
        """Test from_dict with missing optional fields uses defaults."""
        data = {
            "character_id": "char-1",
            "event_id": "event-1",
            "reaction_type": "OBSERVE",
            "intensity": 5,
            "narrative": "Test narrative",
        }

        reaction = CharacterReaction.from_dict(data)

        assert reaction.memory_created is False
        assert isinstance(reaction.reaction_id, str)
        assert isinstance(reaction.created_at, datetime)

    def test_roundtrip_serialization(self):
        """Test that to_dict -> from_dict preserves all data."""
        original = CharacterReaction(
            reaction_id="reaction-rt",
            character_id="char-rt",
            event_id="event-rt",
            reaction_type=ReactionType.PROTEST,
            intensity=7,
            narrative="Protesting the decision!",
            memory_created=True,
            created_at=datetime(2024, 3, 15, 9, 30, 0),
        )

        data = original.to_dict()
        restored = CharacterReaction.from_dict(data)

        assert restored.reaction_id == original.reaction_id
        assert restored.character_id == original.character_id
        assert restored.event_id == original.event_id
        assert restored.reaction_type == original.reaction_type
        assert restored.intensity == original.intensity
        assert restored.narrative == original.narrative
        assert restored.memory_created == original.memory_created
        assert restored.created_at == original.created_at


class TestCharacterReactionImmutability:
    """Tests for CharacterReaction immutability (frozen dataclass)."""

    def test_cannot_modify_reaction_id(self):
        """Test that reaction_id cannot be modified after creation."""
        reaction = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=5,
            narrative="Test narrative",
        )

        with pytest.raises(AttributeError):
            reaction.reaction_id = "new-id"

    def test_cannot_modify_intensity(self):
        """Test that intensity cannot be modified after creation."""
        reaction = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=5,
            narrative="Test narrative",
        )

        with pytest.raises(AttributeError):
            reaction.intensity = 10

    def test_cannot_modify_reaction_type(self):
        """Test that reaction_type cannot be modified after creation."""
        reaction = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=5,
            narrative="Test narrative",
        )

        with pytest.raises(AttributeError):
            reaction.reaction_type = ReactionType.FLEE


class TestCharacterReactionEquality:
    """Tests for CharacterReaction equality and hashing."""

    def test_equality_same_values(self):
        """Test that two reactions with same values are equal."""
        fixed_time = datetime(2024, 1, 15, 10, 30, 0)

        reaction1 = CharacterReaction(
            reaction_id="reaction-1",
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=5,
            narrative="Test narrative",
            memory_created=False,
            created_at=fixed_time,
        )

        reaction2 = CharacterReaction(
            reaction_id="reaction-1",
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=5,
            narrative="Test narrative",
            memory_created=False,
            created_at=fixed_time,
        )

        assert reaction1 == reaction2

    def test_equality_different_reaction_id(self):
        """Test that reactions with different reaction_ids are not equal."""
        reaction1 = CharacterReaction(
            reaction_id="reaction-1",
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=5,
            narrative="Test narrative",
        )

        reaction2 = CharacterReaction(
            reaction_id="reaction-2",
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=5,
            narrative="Test narrative",
        )

        assert reaction1 != reaction2

    def test_hash_consistency(self):
        """Test that hash is consistent for same values."""
        fixed_time = datetime(2024, 1, 15, 10, 30, 0)

        reaction1 = CharacterReaction(
            reaction_id="reaction-1",
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=5,
            narrative="Test narrative",
            created_at=fixed_time,
        )

        reaction2 = CharacterReaction(
            reaction_id="reaction-1",
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=5,
            narrative="Test narrative",
            created_at=fixed_time,
        )

        assert hash(reaction1) == hash(reaction2)

    def test_can_use_in_set(self):
        """Test that reactions can be used in a set."""
        fixed_time = datetime(2024, 1, 15, 10, 30, 0)

        reaction = CharacterReaction(
            reaction_id="reaction-1",
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=5,
            narrative="Test narrative",
            created_at=fixed_time,
        )

        reaction_set = {reaction}
        assert reaction in reaction_set


class TestAllReactionTypes:
    """Tests for all reaction types to ensure they work correctly."""

    @pytest.mark.parametrize("reaction_type", list(ReactionType))
    def test_create_with_each_reaction_type(self, reaction_type):
        """Test creating reactions with each reaction type."""
        reaction = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=reaction_type,
            intensity=5,
            narrative=f"Reaction of type {reaction_type.value}",
        )

        assert reaction.reaction_type == reaction_type
        assert reaction.reaction_type.value == reaction_type.value

    @pytest.mark.parametrize("intensity", range(1, 11))
    def test_create_with_each_intensity(self, intensity):
        """Test creating reactions with each valid intensity."""
        reaction = CharacterReaction(
            character_id="char-1",
            event_id="event-1",
            reaction_type=ReactionType.OBSERVE,
            intensity=intensity,
            narrative=f"Intensity {intensity} reaction",
        )

        assert reaction.intensity == intensity
