#!/usr/bin/env python3
"""
Comprehensive Unit Tests for SubjectiveId Value Object

Test suite covering unique identification, UUID validation, factory methods,
and identity management in the Subjective Context domain layer.
"""

import pytest
from uuid import UUID, uuid4
from typing import Any

from contexts.subjective.domain.value_objects.subjective_id import SubjectiveId


class TestSubjectiveIdCreation:
    """Test suite for SubjectiveId creation and basic functionality."""
    
    def test_create_with_uuid(self):
        """Test creating SubjectiveId with valid UUID."""
        uuid_value = uuid4()
        subjective_id = SubjectiveId(uuid_value)
        
        assert subjective_id.value == uuid_value
        assert isinstance(subjective_id.value, UUID)
    
    def test_create_with_specific_uuid(self):
        """Test creating SubjectiveId with specific UUID."""
        specific_uuid = UUID('12345678-1234-5678-9abc-123456789abc')
        subjective_id = SubjectiveId(specific_uuid)
        
        assert subjective_id.value == specific_uuid
        assert str(subjective_id.value) == '12345678-1234-5678-9abc-123456789abc'
    
    def test_frozen_dataclass_immutability(self):
        """Test that SubjectiveId is immutable (frozen dataclass)."""
        uuid_value = uuid4()
        subjective_id = SubjectiveId(uuid_value)
        
        # Should not be able to modify the value
        with pytest.raises(AttributeError):
            subjective_id.value = uuid4()


class TestSubjectiveIdValidation:
    """Test suite for SubjectiveId validation logic."""
    
    def test_invalid_uuid_type_string(self):
        """Test validation fails with string instead of UUID."""
        with pytest.raises(ValueError, match="SubjectiveId must be a UUID, got"):
            SubjectiveId("not-a-uuid-object")
    
    def test_invalid_uuid_type_integer(self):
        """Test validation fails with integer instead of UUID."""
        with pytest.raises(ValueError, match="SubjectiveId must be a UUID, got"):
            SubjectiveId(12345)
    
    def test_invalid_uuid_type_none(self):
        """Test validation fails with None instead of UUID."""
        with pytest.raises(ValueError, match="SubjectiveId must be a UUID, got"):
            SubjectiveId(None)
    
    def test_invalid_uuid_type_dict(self):
        """Test validation fails with dict instead of UUID."""
        with pytest.raises(ValueError, match="SubjectiveId must be a UUID, got"):
            SubjectiveId({"uuid": "12345678-1234-5678-9abc-123456789abc"})
    
    def test_invalid_uuid_type_list(self):
        """Test validation fails with list instead of UUID."""
        with pytest.raises(ValueError, match="SubjectiveId must be a UUID, got"):
            SubjectiveId([1, 2, 3, 4])


class TestSubjectiveIdFactoryMethods:
    """Test suite for SubjectiveId factory methods."""
    
    def test_generate_creates_unique_ids(self):
        """Test that generate() creates unique IDs each time."""
        id1 = SubjectiveId.generate()
        id2 = SubjectiveId.generate()
        id3 = SubjectiveId.generate()
        
        # All should be different
        assert id1 != id2
        assert id1 != id3
        assert id2 != id3
        
        # All should be valid SubjectiveId instances
        assert isinstance(id1, SubjectiveId)
        assert isinstance(id2, SubjectiveId)
        assert isinstance(id3, SubjectiveId)
        
        # All should have UUID values
        assert isinstance(id1.value, UUID)
        assert isinstance(id2.value, UUID)
        assert isinstance(id3.value, UUID)
    
    def test_from_string_valid_uuid(self):
        """Test creating SubjectiveId from valid UUID string."""
        uuid_string = "12345678-1234-5678-9abc-123456789abc"
        subjective_id = SubjectiveId.from_string(uuid_string)
        
        assert isinstance(subjective_id, SubjectiveId)
        assert str(subjective_id.value) == uuid_string.lower()  # UUID strings are normalized to lowercase
    
    def test_from_string_uppercase_uuid(self):
        """Test creating SubjectiveId from uppercase UUID string."""
        uuid_string = "12345678-1234-5678-9ABC-123456789ABC"
        subjective_id = SubjectiveId.from_string(uuid_string)
        
        assert isinstance(subjective_id, SubjectiveId)
        assert str(subjective_id.value) == uuid_string.lower()
    
    def test_from_string_without_dashes(self):
        """Test creating SubjectiveId from UUID string without dashes."""
        uuid_string = "123456781234567890ab123456789abc"
        subjective_id = SubjectiveId.from_string(uuid_string)
        
        assert isinstance(subjective_id, SubjectiveId)
        # UUID constructor should handle this and add dashes
        assert len(str(subjective_id.value)) == 36  # Standard UUID format with dashes
    
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
            with pytest.raises(ValueError, match="Invalid UUID string"):
                SubjectiveId.from_string(invalid_string)
    
    def test_from_string_none(self):
        """Test from_string fails with None."""
        with pytest.raises(ValueError, match="Invalid UUID string"):
            SubjectiveId.from_string(None)
    
    def test_from_string_non_string_type(self):
        """Test from_string fails with non-string types."""
        with pytest.raises(ValueError, match="Invalid UUID string"):
            SubjectiveId.from_string(12345)
        
        with pytest.raises(ValueError, match="Invalid UUID string"):
            SubjectiveId.from_string(uuid4())  # UUID object, not string


class TestSubjectiveIdStringRepresentation:
    """Test suite for SubjectiveId string representation."""
    
    def test_str_representation(self):
        """Test string representation of SubjectiveId."""
        uuid_value = UUID('12345678-1234-5678-9abc-123456789abc')
        subjective_id = SubjectiveId(uuid_value)
        
        str_repr = str(subjective_id)
        assert str_repr == '12345678-1234-5678-9abc-123456789abc'
        assert isinstance(str_repr, str)
    
    def test_str_representation_generated(self):
        """Test string representation of generated SubjectiveId."""
        subjective_id = SubjectiveId.generate()
        str_repr = str(subjective_id)
        
        # Should be a valid UUID string format
        assert len(str_repr) == 36
        assert str_repr.count('-') == 4
        
        # Should be able to create UUID from the string
        UUID(str_repr)  # Should not raise exception
    
    def test_repr_not_implemented(self):
        """Test that repr uses default dataclass representation."""
        uuid_value = UUID('12345678-1234-5678-9abc-123456789abc')
        subjective_id = SubjectiveId(uuid_value)
        
        repr_str = repr(subjective_id)
        # Should contain class name and value
        assert 'SubjectiveId' in repr_str
        assert '12345678-1234-5678-9abc-123456789abc' in repr_str


class TestSubjectiveIdEquality:
    """Test suite for SubjectiveId equality comparison."""
    
    def test_equality_same_uuid(self):
        """Test equality with same UUID value."""
        uuid_value = uuid4()
        id1 = SubjectiveId(uuid_value)
        id2 = SubjectiveId(uuid_value)
        
        assert id1 == id2
        assert not (id1 != id2)
    
    def test_equality_different_uuids(self):
        """Test inequality with different UUID values."""
        uuid1 = uuid4()
        uuid2 = uuid4()
        
        id1 = SubjectiveId(uuid1)
        id2 = SubjectiveId(uuid2)
        
        assert id1 != id2
        assert not (id1 == id2)
    
    def test_equality_with_non_subjective_id(self):
        """Test equality comparison with non-SubjectiveId objects."""
        uuid_value = uuid4()
        subjective_id = SubjectiveId(uuid_value)
        
        # Should not be equal to UUID directly
        assert subjective_id != uuid_value
        assert not (subjective_id == uuid_value)
        
        # Should not be equal to string representation
        assert subjective_id != str(uuid_value)
        assert not (subjective_id == str(uuid_value))
        
        # Should not be equal to other types
        assert subjective_id != 123
        assert subjective_id != "string"
        assert subjective_id != None
        assert subjective_id != {}
        assert subjective_id != []
    
    def test_equality_reflexive(self):
        """Test that equality is reflexive (a == a)."""
        subjective_id = SubjectiveId.generate()
        assert subjective_id == subjective_id
    
    def test_equality_symmetric(self):
        """Test that equality is symmetric (a == b implies b == a)."""
        uuid_value = uuid4()
        id1 = SubjectiveId(uuid_value)
        id2 = SubjectiveId(uuid_value)
        
        assert id1 == id2
        assert id2 == id1
    
    def test_equality_transitive(self):
        """Test that equality is transitive (a == b and b == c implies a == c)."""
        uuid_value = uuid4()
        id1 = SubjectiveId(uuid_value)
        id2 = SubjectiveId(uuid_value)
        id3 = SubjectiveId(uuid_value)
        
        assert id1 == id2
        assert id2 == id3
        assert id1 == id3


class TestSubjectiveIdHashing:
    """Test suite for SubjectiveId hashing behavior."""
    
    def test_hash_consistency(self):
        """Test that hash is consistent for same object."""
        subjective_id = SubjectiveId.generate()
        hash1 = hash(subjective_id)
        hash2 = hash(subjective_id)
        
        assert hash1 == hash2
    
    def test_hash_equality_implies_same_hash(self):
        """Test that equal objects have the same hash."""
        uuid_value = uuid4()
        id1 = SubjectiveId(uuid_value)
        id2 = SubjectiveId(uuid_value)
        
        assert id1 == id2
        assert hash(id1) == hash(id2)
    
    def test_hash_different_for_different_uuids(self):
        """Test that different UUIDs produce different hashes."""
        id1 = SubjectiveId.generate()
        id2 = SubjectiveId.generate()
        
        # While theoretically possible for different objects to have same hash,
        # it's extremely unlikely with UUIDs
        assert hash(id1) != hash(id2)
    
    def test_usable_as_dict_key(self):
        """Test that SubjectiveId can be used as dictionary key."""
        id1 = SubjectiveId.generate()
        id2 = SubjectiveId.generate()
        
        test_dict = {
            id1: "value1",
            id2: "value2"
        }
        
        assert test_dict[id1] == "value1"
        assert test_dict[id2] == "value2"
        
        # Test with equivalent ID
        uuid_value = id1.value
        equivalent_id = SubjectiveId(uuid_value)
        assert test_dict[equivalent_id] == "value1"  # Should find the same entry
    
    def test_usable_in_set(self):
        """Test that SubjectiveId can be used in sets."""
        id1 = SubjectiveId.generate()
        id2 = SubjectiveId.generate()
        uuid_value = id1.value
        equivalent_id = SubjectiveId(uuid_value)
        
        test_set = {id1, id2}
        
        assert id1 in test_set
        assert id2 in test_set
        assert equivalent_id in test_set  # Equivalent ID should be found
        assert len(test_set) == 2  # Should only have two unique elements
        
        # Adding equivalent ID should not increase set size
        test_set.add(equivalent_id)
        assert len(test_set) == 2


class TestSubjectiveIdRoundTripConversion:
    """Test suite for round-trip conversion between different representations."""
    
    def test_generate_to_string_to_from_string(self):
        """Test round-trip: generate -> string -> from_string."""
        original = SubjectiveId.generate()
        string_repr = str(original)
        reconstructed = SubjectiveId.from_string(string_repr)
        
        assert original == reconstructed
        assert original.value == reconstructed.value
    
    def test_from_string_to_string_consistency(self):
        """Test that from_string -> string produces consistent results."""
        uuid_string = "12345678-1234-5678-9abc-123456789abc"
        subjective_id = SubjectiveId.from_string(uuid_string)
        result_string = str(subjective_id)
        
        assert result_string == uuid_string.lower()
    
    def test_uuid_to_subjective_id_to_string(self):
        """Test round-trip: UUID -> SubjectiveId -> string."""
        original_uuid = uuid4()
        subjective_id = SubjectiveId(original_uuid)
        string_repr = str(subjective_id)
        
        assert string_repr == str(original_uuid)
    
    def test_multiple_round_trips(self):
        """Test multiple round-trip conversions maintain equality."""
        original = SubjectiveId.generate()
        
        # Multiple round trips
        string1 = str(original)
        reconstructed1 = SubjectiveId.from_string(string1)
        string2 = str(reconstructed1)
        reconstructed2 = SubjectiveId.from_string(string2)
        
        assert original == reconstructed1
        assert reconstructed1 == reconstructed2
        assert original == reconstructed2
        assert string1 == string2


class TestSubjectiveIdEdgeCases:
    """Test suite for edge cases and boundary conditions."""
    
    def test_nil_uuid(self):
        """Test with nil/zero UUID."""
        nil_uuid = UUID('00000000-0000-0000-0000-000000000000')
        subjective_id = SubjectiveId(nil_uuid)
        
        assert subjective_id.value == nil_uuid
        assert str(subjective_id) == '00000000-0000-0000-0000-000000000000'
    
    def test_max_uuid(self):
        """Test with maximum UUID value."""
        max_uuid = UUID('ffffffff-ffff-ffff-ffff-ffffffffffff')
        subjective_id = SubjectiveId(max_uuid)
        
        assert subjective_id.value == max_uuid
        assert str(subjective_id) == 'ffffffff-ffff-ffff-ffff-ffffffffffff'
    
    def test_uuid_versions(self):
        """Test with different UUID versions."""
        # UUID version 1 (time-based)
        uuid1 = UUID('550e8400-e29b-11d4-a716-446655440000')
        id1 = SubjectiveId(uuid1)
        assert id1.value == uuid1
        
        # UUID version 4 (random) - most common
        uuid4_val = uuid4()
        id4 = SubjectiveId(uuid4_val)
        assert id4.value == uuid4_val
        
        # Different versions should create different IDs
        assert id1 != id4
    
    def test_case_insensitive_from_string(self):
        """Test that from_string handles case variations correctly."""
        uuid_lower = "12345678-1234-5678-9abc-123456789def"
        uuid_upper = "12345678-1234-5678-9ABC-123456789DEF"
        uuid_mixed = "12345678-1234-5678-9AbC-123456789DeF"
        
        id_lower = SubjectiveId.from_string(uuid_lower)
        id_upper = SubjectiveId.from_string(uuid_upper)
        id_mixed = SubjectiveId.from_string(uuid_mixed)
        
        # All should be equal since UUID is case-insensitive
        assert id_lower == id_upper
        assert id_upper == id_mixed
        assert id_lower == id_mixed
        
        # String representation should be lowercase
        assert str(id_lower) == uuid_lower
        assert str(id_upper) == uuid_lower
        assert str(id_mixed) == uuid_lower
    
    def test_compact_uuid_string(self):
        """Test from_string with compact (no dashes) UUID format."""
        compact_uuid = "123456781234567890ab123456789def"
        subjective_id = SubjectiveId.from_string(compact_uuid)
        
        # Should produce standard format with dashes
        expected_standard = "12345678-1234-5678-90ab-123456789def"
        assert str(subjective_id) == expected_standard
    
    def test_memory_efficiency(self):
        """Test that multiple SubjectiveIds with same UUID value are memory efficient."""
        uuid_value = uuid4()
        id1 = SubjectiveId(uuid_value)
        id2 = SubjectiveId(uuid_value)
        
        # Should be equal but different objects
        assert id1 == id2
        assert id1 is not id2
        
        # Should have same hash
        assert hash(id1) == hash(id2)
        
        # Both should reference the same UUID object (UUID objects are typically interned)
        assert id1.value is uuid_value
        assert id2.value is uuid_value


class TestSubjectiveIdCollections:
    """Test suite for SubjectiveId behavior in collections."""
    
    def test_list_operations(self):
        """Test SubjectiveId in list operations."""
        id1 = SubjectiveId.generate()
        id2 = SubjectiveId.generate()
        id3 = SubjectiveId.generate()
        
        id_list = [id1, id2, id3]
        
        assert len(id_list) == 3
        assert id1 in id_list
        assert id2 in id_list
        assert id3 in id_list
        
        # Test finding by equivalent ID
        equivalent_id1 = SubjectiveId(id1.value)
        assert equivalent_id1 in id_list
    
    def test_set_operations(self):
        """Test SubjectiveId in set operations."""
        id1 = SubjectiveId.generate()
        id2 = SubjectiveId.generate()
        equivalent_id1 = SubjectiveId(id1.value)
        
        id_set = {id1, id2, equivalent_id1}
        
        # Should only have 2 unique elements (id1 and equivalent_id1 are equal)
        assert len(id_set) == 2
        assert id1 in id_set
        assert id2 in id_set
        assert equivalent_id1 in id_set
    
    def test_dict_key_operations(self):
        """Test SubjectiveId as dictionary keys."""
        id1 = SubjectiveId.generate()
        id2 = SubjectiveId.generate()
        
        id_dict = {id1: "data1", id2: "data2"}
        
        # Test access
        assert id_dict[id1] == "data1"
        assert id_dict[id2] == "data2"
        
        # Test with equivalent ID
        equivalent_id1 = SubjectiveId(id1.value)
        assert id_dict[equivalent_id1] == "data1"
        
        # Test update with equivalent key
        id_dict[equivalent_id1] = "updated_data1"
        assert len(id_dict) == 2  # Should still have 2 keys
        assert id_dict[id1] == "updated_data1"  # Original key should have updated value
    
    def test_sorting(self):
        """Test that SubjectiveIds can be sorted (by UUID string representation)."""
        # Create IDs with known UUID values for predictable sorting
        uuid1 = UUID('11111111-1111-1111-1111-111111111111')
        uuid2 = UUID('22222222-2222-2222-2222-222222222222')
        uuid3 = UUID('33333333-3333-3333-3333-333333333333')
        
        id1 = SubjectiveId(uuid1)
        id2 = SubjectiveId(uuid2)
        id3 = SubjectiveId(uuid3)
        
        unsorted_list = [id3, id1, id2]
        sorted_list = sorted(unsorted_list, key=lambda x: str(x.value))
        
        assert sorted_list == [id1, id2, id3]