#!/usr/bin/env python3
"""
Unit tests for CharacterID Value Object

Comprehensive test suite for the CharacterID value object including:
- Creation and validation
- Factory methods
- String representation
- Immutability
"""

import sys
import uuid
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()
from src.contexts.character.domain.value_objects.character_id import CharacterID


class TestCharacterID:
    """Test suite for CharacterID value object."""

    @pytest.fixture
    def valid_uuid(self):
        """Create a valid UUID string."""
        return str(uuid.uuid4())

    def test_character_id_creation_success(self, valid_uuid):
        """Test successful CharacterID creation."""
        character_id = CharacterID(valid_uuid)

        assert character_id.value == valid_uuid

    def test_character_id_creation_with_uuid_object(self):
        """Test creation with UUID object converted to string."""
        uuid_obj = uuid.uuid4()
        character_id = CharacterID(str(uuid_obj))

        assert character_id.value == str(uuid_obj)

    def test_character_id_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterID("")
        assert "CharacterID cannot be empty" in str(exc_info.value)

    def test_character_id_whitespace_string_raises_error(self):
        """Test that whitespace-only string raises ValueError (UUID format)."""
        with pytest.raises(ValueError) as exc_info:
            CharacterID("   ")
        # Whitespace-only strings fail UUID validation
        assert "must be a valid UUID format" in str(exc_info.value)

    def test_character_id_invalid_uuid_raises_error(self):
        """Test that invalid UUID format raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterID("not-a-valid-uuid")
        assert "must be a valid UUID format" in str(exc_info.value)

    def test_character_id_invalid_uuid_special_chars(self):
        """Test that UUID with special characters raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CharacterID("12345-!@#$%-abcd-efgh-ijkl")
        assert "must be a valid UUID format" in str(exc_info.value)

    def test_character_id_generate_creates_valid_uuid(self):
        """Test that generate() creates a valid UUID."""
        character_id = CharacterID.generate()

        assert isinstance(character_id, CharacterID)
        # Should be a valid UUID
        uuid.UUID(character_id.value)

    def test_character_id_generate_unique(self):
        """Test that generate() creates unique IDs."""
        id1 = CharacterID.generate()
        id2 = CharacterID.generate()

        assert id1.value != id2.value

    def test_character_id_from_string_success(self, valid_uuid):
        """Test from_string factory method."""
        character_id = CharacterID.from_string(valid_uuid)

        assert character_id.value == valid_uuid

    def test_character_id_from_string_invalid(self):
        """Test from_string with invalid UUID."""
        with pytest.raises(ValueError) as exc_info:
            CharacterID.from_string("invalid")
        assert "must be a valid UUID format" in str(exc_info.value)

    def test_character_id_str_representation(self, valid_uuid):
        """Test __str__ returns the value."""
        character_id = CharacterID(valid_uuid)

        assert str(character_id) == valid_uuid

    def test_character_id_repr_representation(self, valid_uuid):
        """Test __repr__ returns formatted string."""
        character_id = CharacterID(valid_uuid)
        result = repr(character_id)

        assert "CharacterID" in result
        assert valid_uuid in result

    def test_character_id_immutable(self, valid_uuid):
        """Test that CharacterID is immutable (frozen dataclass)."""
        character_id = CharacterID(valid_uuid)

        # Attempt to modify should raise error
        with pytest.raises(AttributeError):
            character_id.value = str(uuid.uuid4())

    def test_character_id_equality_same_value(self, valid_uuid):
        """Test equality with same value."""
        id1 = CharacterID(valid_uuid)
        id2 = CharacterID(valid_uuid)

        assert id1 == id2

    def test_character_id_equality_different_values(self):
        """Test equality with different values."""
        id1 = CharacterID.generate()
        id2 = CharacterID.generate()

        assert id1 != id2

    def test_character_id_hashable(self, valid_uuid):
        """Test that CharacterID can be used as dict key."""
        character_id = CharacterID(valid_uuid)

        # Should be hashable
        d = {character_id: "value"}
        assert d[character_id] == "value"

    def test_character_id_can_be_used_in_set(self, valid_uuid):
        """Test that CharacterID can be used in a set."""
        character_id = CharacterID(valid_uuid)

        s = {character_id}
        assert character_id in s

    def test_character_id_case_insensitive_uuid_validation(self):
        """Test that UUID validation is case-insensitive."""
        # UUIDs can be uppercase or lowercase
        upper_uuid = str(uuid.uuid4()).upper()
        lower_uuid = upper_uuid.lower()

        id_upper = CharacterID(upper_uuid)
        id_lower = CharacterID(lower_uuid)

        assert id_upper.value.upper() == id_lower.value.upper()
