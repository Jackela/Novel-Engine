#!/usr/bin/env python3
"""
Comprehensive Unit Tests for NarrativeId Value Object

Test suite covering unique identification, UUID validation, factory methods,
and identity management in the Narrative Context domain layer.
"""

from uuid import UUID, uuid4

import pytest

from src.contexts.narratives.domain.value_objects.narrative_id import NarrativeId


class TestNarrativeIdCreation:
    """Test suite for NarrativeId creation and basic functionality."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_create_with_uuid(self):
        """Test creating NarrativeId with valid UUID."""
        uuid_value = uuid4()
        narrative_id = NarrativeId(uuid_value)

        assert narrative_id.value == uuid_value
        assert isinstance(narrative_id.value, UUID)

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_create_with_specific_uuid(self):
        """Test creating NarrativeId with specific UUID."""
        specific_uuid = UUID("12345678-1234-5678-9abc-123456789abc")
        narrative_id = NarrativeId(specific_uuid)

        assert narrative_id.value == specific_uuid
        assert str(narrative_id.value) == "12345678-1234-5678-9abc-123456789abc"

    @pytest.mark.unit
    @pytest.mark.unit
    def test_frozen_dataclass_immutability(self):
        """Test that NarrativeId is immutable (frozen dataclass)."""
        uuid_value = uuid4()
        narrative_id = NarrativeId(uuid_value)

        # Should not be able to modify the value
        with pytest.raises(AttributeError):
            narrative_id.value = uuid4()

    @pytest.mark.unit
    @pytest.mark.fast
    def test_class_metadata(self):
        """Test that class-level metadata is correctly set."""
        assert NarrativeId._context_name == "narratives"
        assert NarrativeId._type_name == "NarrativeId"


class TestNarrativeIdValidation:
    """Test suite for NarrativeId validation logic."""

    @pytest.mark.unit
    def test_invalid_uuid_type_string(self):
        """Test validation fails with string instead of UUID."""
        with pytest.raises(TypeError, match="NarrativeId value must be a UUID, got"):
            NarrativeId("not-a-uuid-object")

    @pytest.mark.unit
    def test_invalid_uuid_type_integer(self):
        """Test validation fails with integer instead of UUID."""
        with pytest.raises(TypeError, match="NarrativeId value must be a UUID, got"):
            NarrativeId(12345)

    @pytest.mark.unit
    def test_invalid_uuid_type_none(self):
        """Test validation fails with None instead of UUID."""
        with pytest.raises(TypeError, match="NarrativeId value must be a UUID, got"):
            NarrativeId(None)

    @pytest.mark.unit
    def test_invalid_uuid_type_dict(self):
        """Test validation fails with dict instead of UUID."""
        with pytest.raises(TypeError, match="NarrativeId value must be a UUID, got"):
            NarrativeId({"uuid": "12345678-1234-5678-9abc-123456789abc"})

    @pytest.mark.unit
    def test_invalid_uuid_type_list(self):
        """Test validation fails with list instead of UUID."""
        with pytest.raises(TypeError, match="NarrativeId value must be a UUID, got"):
            NarrativeId([1, 2, 3, 4])


class TestNarrativeIdFactoryMethods:
    """Test suite for NarrativeId factory methods."""

    @pytest.mark.unit
    def test_generate_creates_unique_ids(self):
        """Test that generate() creates unique IDs each time."""
        id1 = NarrativeId.generate()
        id2 = NarrativeId.generate()
        id3 = NarrativeId.generate()

        # All should be different
        assert id1 != id2
        assert id1 != id3
        assert id2 != id3

        # All should be valid NarrativeId instances
        assert isinstance(id1, NarrativeId)
        assert isinstance(id2, NarrativeId)
        assert isinstance(id3, NarrativeId)

        # All should have UUID values
        assert isinstance(id1.value, UUID)
        assert isinstance(id2.value, UUID)
        assert isinstance(id3.value, UUID)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_string_valid_uuid(self):
        """Test creating NarrativeId from valid UUID string."""
        uuid_string = "12345678-1234-5678-9abc-123456789abc"
        narrative_id = NarrativeId.from_string(uuid_string)

        assert isinstance(narrative_id, NarrativeId)
        assert (
            str(narrative_id.value) == uuid_string.lower()
        )  # UUID strings are normalized to lowercase

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_string_uppercase_uuid(self):
        """Test creating NarrativeId from uppercase UUID string."""
        uuid_string = "12345678-1234-5678-9ABC-123456789ABC"
        narrative_id = NarrativeId.from_string(uuid_string)

        assert isinstance(narrative_id, NarrativeId)
        assert str(narrative_id.value) == uuid_string.lower()

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_string_without_dashes(self):
        """Test creating NarrativeId from UUID string without dashes."""
        uuid_string = "123456781234567890ab123456789abc"
        narrative_id = NarrativeId.from_string(uuid_string)

        assert isinstance(narrative_id, NarrativeId)
        # UUID constructor should handle this and add dashes
        assert len(str(narrative_id.value)) == 36  # Standard UUID format with dashes

    @pytest.mark.unit
    def test_from_string_invalid_format(self):
        """Test from_string fails with invalid UUID format."""
        invalid_strings = [
            "not-a-uuid",
            "12345678-1234-5678-9abc",  # Too short
            "12345678-1234-5678-9abc-123456789abc-extra",  # Too long
            "12345678-1234-5678-xyz-123456789abc",  # Invalid characters
            "12345678-1234-56789abc-123456789abc",  # Wrong dash placement
            "",
            "   ",
        ]

        for invalid_string in invalid_strings:
            with pytest.raises(ValueError, match="Invalid UUID format for NarrativeId"):
                NarrativeId.from_string(invalid_string)

    @pytest.mark.unit
    def test_from_string_none(self):
        """Test from_string fails with None."""
        with pytest.raises(ValueError, match="Invalid UUID format for NarrativeId"):
            NarrativeId.from_string(None)

    @pytest.mark.unit
    def test_from_string_non_string_type(self):
        """Test from_string fails with non-string types."""
        with pytest.raises(ValueError, match="Invalid UUID format for NarrativeId"):
            NarrativeId.from_string(12345)

        with pytest.raises(ValueError, match="Invalid UUID format for NarrativeId"):
            NarrativeId.from_string(uuid4())  # UUID object, not string


class TestNarrativeIdStringRepresentation:
    """Test suite for NarrativeId string representation."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation(self):
        """Test string representation of NarrativeId."""
        uuid_value = UUID("12345678-1234-5678-9abc-123456789abc")
        narrative_id = NarrativeId(uuid_value)

        str_repr = str(narrative_id)
        assert str_repr == f"NarrativeId({uuid_value})"
        assert isinstance(str_repr, str)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation_generated(self):
        """Test string representation of generated NarrativeId."""
        narrative_id = NarrativeId.generate()
        str_repr = str(narrative_id)

        # Should contain class name and UUID
        assert "NarrativeId(" in str_repr
        assert ")" in str_repr

        # Extract UUID part and validate format
        uuid_part = str_repr.replace("NarrativeId(", "").replace(")", "")
        UUID(uuid_part)  # Should not raise exception

    @pytest.mark.unit
    @pytest.mark.fast
    def test_repr_representation(self):
        """Test repr representation of NarrativeId."""
        uuid_value = UUID("12345678-1234-5678-9abc-123456789abc")
        narrative_id = NarrativeId(uuid_value)

        repr_str = repr(narrative_id)
        assert "NarrativeId" in repr_str
        assert "12345678-1234-5678-9abc-123456789abc" in repr_str
        assert "value=" in repr_str

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_string_method(self):
        """Test to_string method returns UUID string."""
        uuid_value = UUID("12345678-1234-5678-9abc-123456789abc")
        narrative_id = NarrativeId(uuid_value)

        string_repr = narrative_id.to_string()
        assert string_repr == "12345678-1234-5678-9abc-123456789abc"
        assert isinstance(string_repr, str)


class TestNarrativeIdEquality:
    """Test suite for NarrativeId equality comparison."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_equality_same_uuid(self):
        """Test equality with same UUID value."""
        uuid_value = uuid4()
        id1 = NarrativeId(uuid_value)
        id2 = NarrativeId(uuid_value)

        assert id1 == id2

    @pytest.mark.unit
    @pytest.mark.fast
    def test_equality_different_uuids(self):
        """Test inequality with different UUID values."""
        uuid1 = uuid4()
        uuid2 = uuid4()

        id1 = NarrativeId(uuid1)
        id2 = NarrativeId(uuid2)

        assert id1 != id2

    @pytest.mark.unit
    def test_equality_with_non_narrative_id(self):
        """Test equality comparison with non-NarrativeId objects."""
        uuid_value = uuid4()
        narrative_id = NarrativeId(uuid_value)

        # Should not be equal to UUID directly
        assert narrative_id != uuid_value

        # Should not be equal to string representation
        assert narrative_id != str(uuid_value)

        # Should not be equal to other types
        assert narrative_id != 123
        assert narrative_id != "string"
        assert narrative_id is not None
        assert narrative_id != {}
        assert narrative_id != []

    @pytest.mark.unit
    @pytest.mark.fast
    def test_equality_reflexive(self):
        """Test that equality is reflexive (a == a)."""
        narrative_id = NarrativeId.generate()
        assert narrative_id == NarrativeId(narrative_id.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_equality_symmetric(self):
        """Test that equality is symmetric (a == b implies b == a)."""
        uuid_value = uuid4()
        id1 = NarrativeId(uuid_value)
        id2 = NarrativeId(uuid_value)

        assert id1 == id2
        assert id2 == id1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_equality_transitive(self):
        """Test that equality is transitive (a == b and b == c implies a == c)."""
        uuid_value = uuid4()
        id1 = NarrativeId(uuid_value)
        id2 = NarrativeId(uuid_value)
        id3 = NarrativeId(uuid_value)

        assert id1 == id2
        assert id2 == id3
        assert id1 == id3


class TestNarrativeIdHashing:
    """Test suite for NarrativeId hashing behavior."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_hash_consistency(self):
        """Test that hash is consistent for same object."""
        narrative_id = NarrativeId.generate()
        hash1 = hash(narrative_id)
        hash2 = hash(narrative_id)

        assert hash1 == hash2

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_hash_equality_implies_same_hash(self):
        """Test that equal objects have the same hash."""
        uuid_value = uuid4()
        id1 = NarrativeId(uuid_value)
        id2 = NarrativeId(uuid_value)

        assert id1 == id2
        assert hash(id1) == hash(id2)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_hash_different_for_different_uuids(self):
        """Test that different UUIDs produce different hashes."""
        id1 = NarrativeId.generate()
        id2 = NarrativeId.generate()

        # While theoretically possible for different objects to have same hash,
        # it's extremely unlikely with UUIDs
        assert hash(id1) != hash(id2)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_usable_as_dict_key(self):
        """Test that NarrativeId can be used as dictionary key."""
        id1 = NarrativeId.generate()
        id2 = NarrativeId.generate()

        test_dict = {id1: "value1", id2: "value2"}

        assert test_dict[id1] == "value1"
        assert test_dict[id2] == "value2"

        # Test with equivalent ID
        uuid_value = id1.value
        equivalent_id = NarrativeId(uuid_value)
        assert test_dict[equivalent_id] == "value1"  # Should find the same entry

    @pytest.mark.unit
    def test_usable_in_set(self):
        """Test that NarrativeId can be used in sets."""
        id1 = NarrativeId.generate()
        id2 = NarrativeId.generate()
        uuid_value = id1.value
        equivalent_id = NarrativeId(uuid_value)

        test_set = {id1, id2}

        assert id1 in test_set
        assert id2 in test_set
        assert equivalent_id in test_set  # Equivalent ID should be found
        assert len(test_set) == 2  # Should only have two unique elements

        # Adding equivalent ID should not increase set size
        test_set.add(equivalent_id)
        assert len(test_set) == 2


class TestNarrativeIdRoundTripConversion:
    """Test suite for round-trip conversion between different representations."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_generate_to_string_to_from_string(self):
        """Test round-trip: generate -> to_string -> from_string."""
        original = NarrativeId.generate()
        string_repr = original.to_string()
        reconstructed = NarrativeId.from_string(string_repr)

        assert original == reconstructed
        assert original.value == reconstructed.value

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_string_to_string_consistency(self):
        """Test that from_string -> to_string produces consistent results."""
        uuid_string = "12345678-1234-5678-9abc-123456789abc"
        narrative_id = NarrativeId.from_string(uuid_string)
        result_string = narrative_id.to_string()

        assert result_string == uuid_string.lower()

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_uuid_to_narrative_id_to_string(self):
        """Test round-trip: UUID -> NarrativeId -> to_string."""
        original_uuid = uuid4()
        narrative_id = NarrativeId(original_uuid)
        string_repr = narrative_id.to_string()

        assert string_repr == str(original_uuid)

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_multiple_round_trips(self):
        """Test multiple round-trip conversions maintain equality."""
        original = NarrativeId.generate()

        # Multiple round trips
        string1 = original.to_string()
        reconstructed1 = NarrativeId.from_string(string1)
        string2 = reconstructed1.to_string()
        reconstructed2 = NarrativeId.from_string(string2)

        assert original == reconstructed1
        assert reconstructed1 == reconstructed2
        assert original == reconstructed2
        assert string1 == string2


class TestNarrativeIdEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_nil_uuid(self):
        """Test with nil/zero UUID."""
        nil_uuid = UUID("00000000-0000-0000-0000-000000000000")
        narrative_id = NarrativeId(nil_uuid)

        assert narrative_id.value == nil_uuid
        assert narrative_id.to_string() == "00000000-0000-0000-0000-000000000000"

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_max_uuid(self):
        """Test with maximum UUID value."""
        max_uuid = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
        narrative_id = NarrativeId(max_uuid)

        assert narrative_id.value == max_uuid
        assert narrative_id.to_string() == "ffffffff-ffff-ffff-ffff-ffffffffffff"

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_uuid_versions(self):
        """Test with different UUID versions."""
        # UUID version 1 (time-based)
        uuid1 = UUID("550e8400-e29b-11d4-a716-446655440000")
        id1 = NarrativeId(uuid1)
        assert id1.value == uuid1

        # UUID version 4 (random) - most common
        uuid4_val = uuid4()
        id4 = NarrativeId(uuid4_val)
        assert id4.value == uuid4_val

        # Different versions should create different IDs
        assert id1 != id4

    @pytest.mark.unit
    def test_case_insensitive_from_string(self):
        """Test that from_string handles case variations correctly."""
        uuid_lower = "12345678-1234-5678-9abc-123456789def"
        uuid_upper = "12345678-1234-5678-9ABC-123456789DEF"
        uuid_mixed = "12345678-1234-5678-9AbC-123456789DeF"

        id_lower = NarrativeId.from_string(uuid_lower)
        id_upper = NarrativeId.from_string(uuid_upper)
        id_mixed = NarrativeId.from_string(uuid_mixed)

        # All should be equal since UUID is case-insensitive
        assert id_lower == id_upper
        assert id_upper == id_mixed
        assert id_lower == id_mixed

        # String representation should be lowercase
        assert id_lower.to_string() == uuid_lower
        assert id_upper.to_string() == uuid_lower
        assert id_mixed.to_string() == uuid_lower

    @pytest.mark.unit
    @pytest.mark.fast
    def test_compact_uuid_string(self):
        """Test from_string with compact (no dashes) UUID format."""
        compact_uuid = "123456781234567890ab123456789def"
        narrative_id = NarrativeId.from_string(compact_uuid)

        # Should produce standard format with dashes
        expected_standard = "12345678-1234-5678-90ab-123456789def"
        assert narrative_id.to_string() == expected_standard

    @pytest.mark.unit
    @pytest.mark.fast
    def test_memory_efficiency(self):
        """Test that multiple NarrativeIds with same UUID value are memory efficient."""
        uuid_value = uuid4()
        id1 = NarrativeId(uuid_value)
        id2 = NarrativeId(uuid_value)

        # Should be equal but different objects
        assert id1 == id2
        assert id1 is not id2

        # Should have same hash
        assert hash(id1) == hash(id2)

        # Both should reference the same UUID object (UUID objects are typically interned)
        assert id1.value is uuid_value
        assert id2.value is uuid_value


class TestNarrativeIdCollections:
    """Test suite for NarrativeId behavior in collections."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_list_operations(self):
        """Test NarrativeId in list operations."""
        id1 = NarrativeId.generate()
        id2 = NarrativeId.generate()
        id3 = NarrativeId.generate()

        id_list = [id1, id2, id3]

        assert len(id_list) == 3
        assert id1 in id_list
        assert id2 in id_list
        assert id3 in id_list

        # Test finding by equivalent ID
        equivalent_id1 = NarrativeId(id1.value)
        assert equivalent_id1 in id_list

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_operations(self):
        """Test NarrativeId in set operations."""
        id1 = NarrativeId.generate()
        id2 = NarrativeId.generate()
        equivalent_id1 = NarrativeId(id1.value)

        id_set = {id1, id2, equivalent_id1}

        # Should only have 2 unique elements (id1 and equivalent_id1 are equal)
        assert len(id_set) == 2
        assert id1 in id_set
        assert id2 in id_set
        assert equivalent_id1 in id_set

    @pytest.mark.unit
    def test_dict_key_operations(self):
        """Test NarrativeId as dictionary keys."""
        id1 = NarrativeId.generate()
        id2 = NarrativeId.generate()

        id_dict = {id1: "data1", id2: "data2"}

        # Test access
        assert id_dict[id1] == "data1"
        assert id_dict[id2] == "data2"

        # Test with equivalent ID
        equivalent_id1 = NarrativeId(id1.value)
        assert id_dict[equivalent_id1] == "data1"

        # Test update with equivalent key
        id_dict[equivalent_id1] = "updated_data1"
        assert len(id_dict) == 2  # Should still have 2 keys
        assert id_dict[id1] == "updated_data1"  # Original key should have updated value

    @pytest.mark.unit
    @pytest.mark.fast
    def test_sorting(self):
        """Test that NarrativeIds can be sorted (by UUID string representation)."""
        # Create IDs with known UUID values for predictable sorting
        uuid1 = UUID("11111111-1111-1111-1111-111111111111")
        uuid2 = UUID("22222222-2222-2222-2222-222222222222")
        uuid3 = UUID("33333333-3333-3333-3333-333333333333")

        id1 = NarrativeId(uuid1)
        id2 = NarrativeId(uuid2)
        id3 = NarrativeId(uuid3)

        unsorted_list = [id3, id1, id2]
        sorted_list = sorted(unsorted_list, key=lambda x: str(x.value))

        assert sorted_list == [id1, id2, id3]


class TestNarrativeIdContextMetadata:
    """Test suite for context-specific metadata and features."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_context_name_metadata(self):
        """Test context name class variable."""
        assert hasattr(NarrativeId, "_context_name")
        assert NarrativeId._context_name == "narratives"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_type_name_metadata(self):
        """Test type name class variable."""
        assert hasattr(NarrativeId, "_type_name")
        assert NarrativeId._type_name == "NarrativeId"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_metadata_is_class_variable(self):
        """Test that metadata are class variables, not instance variables."""
        id1 = NarrativeId.generate()
        id2 = NarrativeId.generate()

        # Both instances should share the same class metadata
        assert id1._context_name is id2._context_name
        assert id1._type_name is id2._type_name
        assert id1._context_name is NarrativeId._context_name
        assert id1._type_name is NarrativeId._type_name

    @pytest.mark.unit
    def test_metadata_immutability(self):
        """Test that metadata cannot be changed on instances."""
        narrative_id = NarrativeId.generate()

        # Should not be able to modify metadata on instances
        with pytest.raises(AttributeError):
            narrative_id._context_name = "different"

        with pytest.raises(AttributeError):
            narrative_id._type_name = "different"
