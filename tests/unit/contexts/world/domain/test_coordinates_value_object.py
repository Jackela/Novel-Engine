#!/usr/bin/env python3
"""
Unit tests for Coordinates Value Object

Comprehensive test suite for the Coordinates value object covering
spatial calculations, validation, immutability, and mathematical operations.
"""

import pytest
import math
from unittest.mock import MagicMock
import sys

# Mock problematic dependencies
sys.modules['aioredis'] = MagicMock()

# Import the value object we're testing
from contexts.world.domain.value_objects.coordinates import Coordinates


class TestCoordinatesValueObject:
    """Test suite for Coordinates value object."""

    # ==================== Basic Creation Tests ====================

    def test_coordinates_creation_success(self):
        """Test successful coordinates creation."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0, precision=6)
        
        assert coords.x == 10.0
        assert coords.y == 20.0
        assert coords.z == 5.0
        assert coords.precision == 6

    def test_coordinates_creation_default_z(self):
        """Test coordinates creation with default z value."""
        coords = Coordinates(x=10.0, y=20.0)
        
        assert coords.x == 10.0
        assert coords.y == 20.0
        assert coords.z == 0.0
        assert coords.precision == 6

    def test_coordinates_creation_default_precision(self):
        """Test coordinates creation with default precision."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        assert coords.precision == 6

    def test_coordinates_precision_rounding(self):
        """Test that coordinates are rounded to specified precision."""
        coords = Coordinates(x=10.123456789, y=20.987654321, z=5.555555555, precision=3)
        
        assert coords.x == 10.123
        assert coords.y == 20.988
        assert coords.z == 5.556

    # ==================== Validation Tests ====================

    def test_coordinates_validation_invalid_types(self):
        """Test validation fails for invalid coordinate types."""
        with pytest.raises(ValueError) as exc_info:
            Coordinates(x="invalid", y=20.0, z=5.0)
        assert "x coordinate must be numeric" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            Coordinates(x=10.0, y="invalid", z=5.0)
        assert "y coordinate must be numeric" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            Coordinates(x=10.0, y=20.0, z="invalid")
        assert "z coordinate must be numeric" in str(exc_info.value)

    def test_coordinates_validation_nan_values(self):
        """Test validation fails for NaN values."""
        with pytest.raises(ValueError) as exc_info:
            Coordinates(x=float('nan'), y=20.0, z=5.0)
        assert "x coordinate must be a finite number" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            Coordinates(x=10.0, y=float('nan'), z=5.0)
        assert "y coordinate must be a finite number" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            Coordinates(x=10.0, y=20.0, z=float('nan'))
        assert "z coordinate must be a finite number" in str(exc_info.value)

    def test_coordinates_validation_infinite_values(self):
        """Test validation fails for infinite values."""
        with pytest.raises(ValueError) as exc_info:
            Coordinates(x=float('inf'), y=20.0, z=5.0)
        assert "x coordinate must be a finite number" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            Coordinates(x=10.0, y=float('-inf'), z=5.0)
        assert "y coordinate must be a finite number" in str(exc_info.value)

    def test_coordinates_validation_precision_invalid_type(self):
        """Test validation fails for invalid precision type."""
        with pytest.raises(ValueError) as exc_info:
            Coordinates(x=10.0, y=20.0, z=5.0, precision="invalid")
        assert "Precision must be an integer between 0 and 15" in str(exc_info.value)

    def test_coordinates_validation_precision_out_of_range(self):
        """Test validation fails for precision out of valid range."""
        with pytest.raises(ValueError) as exc_info:
            Coordinates(x=10.0, y=20.0, z=5.0, precision=-1)
        assert "Precision must be an integer between 0 and 15" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            Coordinates(x=10.0, y=20.0, z=5.0, precision=16)
        assert "Precision must be an integer between 0 and 15" in str(exc_info.value)

    def test_coordinates_validation_extreme_values(self):
        """Test validation fails for extremely large coordinate values."""
        with pytest.raises(ValueError) as exc_info:
            Coordinates(x=1e11, y=20.0, z=5.0)  # Exceeds max_coord = 1e10
        assert "Coordinates must be within ±1e+10" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            Coordinates(x=10.0, y=-1e11, z=5.0)
        assert "Coordinates must be within ±1e+10" in str(exc_info.value)

    # ==================== Distance Calculation Tests ====================

    def test_distance_to_3d(self):
        """Test 3D Euclidean distance calculation."""
        coords1 = Coordinates(x=0.0, y=0.0, z=0.0)
        coords2 = Coordinates(x=3.0, y=4.0, z=0.0)
        
        distance = coords1.distance_to(coords2)
        expected_distance = math.sqrt(3*3 + 4*4 + 0*0)
        
        assert distance == pytest.approx(expected_distance)

    def test_distance_to_3d_with_z(self):
        """Test 3D distance calculation with z component."""
        coords1 = Coordinates(x=1.0, y=2.0, z=3.0)
        coords2 = Coordinates(x=4.0, y=6.0, z=15.0)
        
        distance = coords1.distance_to(coords2)
        expected_distance = math.sqrt((4-1)**2 + (6-2)**2 + (15-3)**2)
        
        assert distance == pytest.approx(expected_distance)

    def test_distance_to_same_point(self):
        """Test distance to same point is zero."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        distance = coords.distance_to(coords)
        
        assert distance == 0.0

    def test_distance_to_invalid_type(self):
        """Test distance calculation fails with invalid type."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        with pytest.raises(TypeError) as exc_info:
            coords.distance_to("invalid")
        assert "Can only calculate distance to another Coordinates object" in str(exc_info.value)

    def test_distance_to_2d(self):
        """Test 2D distance calculation ignoring z component."""
        coords1 = Coordinates(x=0.0, y=0.0, z=100.0)  # High z value
        coords2 = Coordinates(x=3.0, y=4.0, z=200.0)  # Different high z value
        
        distance = coords1.distance_to_2d(coords2)
        expected_distance = math.sqrt(3*3 + 4*4)  # Should ignore z difference
        
        assert distance == pytest.approx(expected_distance)

    def test_distance_to_2d_same_point(self):
        """Test 2D distance to same point is zero."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        distance = coords.distance_to_2d(coords)
        
        assert distance == 0.0

    def test_distance_to_2d_invalid_type(self):
        """Test 2D distance calculation fails with invalid type."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        with pytest.raises(TypeError) as exc_info:
            coords.distance_to_2d("invalid")
        assert "Can only calculate distance to another Coordinates object" in str(exc_info.value)

    def test_manhattan_distance_to(self):
        """Test Manhattan distance calculation."""
        coords1 = Coordinates(x=1.0, y=2.0, z=3.0)
        coords2 = Coordinates(x=4.0, y=6.0, z=15.0)
        
        distance = coords1.manhattan_distance_to(coords2)
        expected_distance = abs(4-1) + abs(6-2) + abs(15-3)  # 3 + 4 + 12 = 19
        
        assert distance == expected_distance

    def test_manhattan_distance_same_point(self):
        """Test Manhattan distance to same point is zero."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        distance = coords.manhattan_distance_to(coords)
        
        assert distance == 0.0

    def test_manhattan_distance_invalid_type(self):
        """Test Manhattan distance calculation fails with invalid type."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        with pytest.raises(TypeError) as exc_info:
            coords.manhattan_distance_to("invalid")
        assert "Can only calculate distance to another Coordinates object" in str(exc_info.value)

    # ==================== Range Check Tests ====================

    def test_is_within_range_true(self):
        """Test is_within_range returns True when within range."""
        center = Coordinates(x=0.0, y=0.0, z=0.0)
        nearby = Coordinates(x=3.0, y=4.0, z=0.0)  # Distance = 5
        
        assert center.is_within_range(nearby, max_distance=5.0) is True
        assert center.is_within_range(nearby, max_distance=6.0) is True

    def test_is_within_range_false(self):
        """Test is_within_range returns False when outside range."""
        center = Coordinates(x=0.0, y=0.0, z=0.0)
        distant = Coordinates(x=3.0, y=4.0, z=0.0)  # Distance = 5
        
        assert center.is_within_range(distant, max_distance=4.0) is False

    def test_is_within_range_exact_boundary(self):
        """Test is_within_range at exact boundary distance."""
        center = Coordinates(x=0.0, y=0.0, z=0.0)
        boundary = Coordinates(x=3.0, y=4.0, z=0.0)  # Distance = 5
        
        assert center.is_within_range(boundary, max_distance=5.0) is True

    def test_is_within_range_negative_distance_fails(self):
        """Test is_within_range fails with negative max_distance."""
        coords1 = Coordinates(x=0.0, y=0.0, z=0.0)
        coords2 = Coordinates(x=1.0, y=1.0, z=1.0)
        
        with pytest.raises(ValueError) as exc_info:
            coords1.is_within_range(coords2, max_distance=-1.0)
        assert "Maximum distance cannot be negative" in str(exc_info.value)

    # ==================== Coordinate Transformation Tests ====================

    def test_translate(self):
        """Test coordinate translation."""
        original = Coordinates(x=10.0, y=20.0, z=5.0, precision=3)
        translated = original.translate(dx=5.0, dy=-10.0, dz=2.0)
        
        assert translated.x == 15.0
        assert translated.y == 10.0
        assert translated.z == 7.0
        assert translated.precision == original.precision
        
        # Original should be unchanged (immutable)
        assert original.x == 10.0
        assert original.y == 20.0
        assert original.z == 5.0

    def test_translate_default_dz(self):
        """Test translation with default dz value."""
        original = Coordinates(x=10.0, y=20.0, z=5.0)
        translated = original.translate(dx=5.0, dy=-10.0)  # No dz provided
        
        assert translated.x == 15.0
        assert translated.y == 10.0
        assert translated.z == 5.0  # Should remain unchanged

    def test_midpoint(self):
        """Test midpoint calculation between two coordinates."""
        coords1 = Coordinates(x=0.0, y=0.0, z=0.0, precision=6)
        coords2 = Coordinates(x=10.0, y=20.0, z=6.0, precision=4)
        
        midpoint = coords1.midpoint(coords2)
        
        assert midpoint.x == 5.0
        assert midpoint.y == 10.0
        assert midpoint.z == 3.0
        assert midpoint.precision == 4  # Should use minimum precision

    def test_midpoint_same_point(self):
        """Test midpoint with same point."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        midpoint = coords.midpoint(coords)
        
        assert midpoint.x == coords.x
        assert midpoint.y == coords.y
        assert midpoint.z == coords.z

    def test_midpoint_invalid_type(self):
        """Test midpoint calculation fails with invalid type."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        with pytest.raises(TypeError) as exc_info:
            coords.midpoint("invalid")
        assert "Can only calculate midpoint with another Coordinates object" in str(exc_info.value)

    # ==================== Conversion Tests ====================

    def test_to_tuple(self):
        """Test conversion to tuple."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        tuple_result = coords.to_tuple()
        
        assert tuple_result == (10.0, 20.0, 5.0)
        assert isinstance(tuple_result, tuple)

    def test_to_tuple_2d(self):
        """Test conversion to 2D tuple."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        tuple_result = coords.to_tuple_2d()
        
        assert tuple_result == (10.0, 20.0)
        assert isinstance(tuple_result, tuple)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0, precision=6)
        
        dict_result = coords.to_dict()
        
        expected_dict = {
            'x': 10.0,
            'y': 20.0,
            'z': 5.0,
            'precision': 6
        }
        
        assert dict_result == expected_dict

    # ==================== Factory Method Tests ====================

    def test_from_tuple_2d(self):
        """Test creation from 2D tuple."""
        coords = Coordinates.from_tuple((10.0, 20.0), precision=3)
        
        assert coords.x == 10.0
        assert coords.y == 20.0
        assert coords.z == 0.0
        assert coords.precision == 3

    def test_from_tuple_3d(self):
        """Test creation from 3D tuple."""
        coords = Coordinates.from_tuple((10.0, 20.0, 5.0), precision=4)
        
        assert coords.x == 10.0
        assert coords.y == 20.0
        assert coords.z == 5.0
        assert coords.precision == 4

    def test_from_tuple_invalid_length(self):
        """Test creation from tuple with invalid length."""
        with pytest.raises(ValueError) as exc_info:
            Coordinates.from_tuple((10.0,))  # Only one element
        assert "Coordinate tuple must have 2 or 3 elements" in str(exc_info.value)
        
        with pytest.raises(ValueError) as exc_info:
            Coordinates.from_tuple((10.0, 20.0, 5.0, 15.0))  # Four elements
        assert "Coordinate tuple must have 2 or 3 elements" in str(exc_info.value)

    def test_from_dict_complete(self):
        """Test creation from complete dictionary."""
        data = {'x': 10.0, 'y': 20.0, 'z': 5.0, 'precision': 3}
        
        coords = Coordinates.from_dict(data)
        
        assert coords.x == 10.0
        assert coords.y == 20.0
        assert coords.z == 5.0
        assert coords.precision == 3

    def test_from_dict_minimal(self):
        """Test creation from minimal dictionary."""
        data = {'x': 10.0, 'y': 20.0}
        
        coords = Coordinates.from_dict(data)
        
        assert coords.x == 10.0
        assert coords.y == 20.0
        assert coords.z == 0.0  # Default value
        assert coords.precision == 6  # Default value

    def test_from_dict_missing_required(self):
        """Test creation from dictionary missing required keys."""
        with pytest.raises(KeyError):
            Coordinates.from_dict({'x': 10.0})  # Missing 'y'
        
        with pytest.raises(KeyError):
            Coordinates.from_dict({'y': 20.0})  # Missing 'x'

    def test_origin_factory(self):
        """Test origin factory method."""
        origin = Coordinates.origin(precision=4)
        
        assert origin.x == 0.0
        assert origin.y == 0.0
        assert origin.z == 0.0
        assert origin.precision == 4

    def test_origin_default_precision(self):
        """Test origin with default precision."""
        origin = Coordinates.origin()
        
        assert origin.x == 0.0
        assert origin.y == 0.0
        assert origin.z == 0.0
        assert origin.precision == 6

    # ==================== Mathematical Operations Tests ====================

    def test_addition(self):
        """Test vector addition."""
        coords1 = Coordinates(x=10.0, y=20.0, z=5.0, precision=6)
        coords2 = Coordinates(x=5.0, y=-10.0, z=15.0, precision=4)
        
        result = coords1 + coords2
        
        assert result.x == 15.0
        assert result.y == 10.0
        assert result.z == 20.0
        assert result.precision == 4  # Should use minimum precision

    def test_addition_invalid_type(self):
        """Test addition fails with invalid type."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        with pytest.raises(TypeError) as exc_info:
            coords + "invalid"
        assert "Can only add Coordinates to Coordinates" in str(exc_info.value)

    def test_subtraction(self):
        """Test vector subtraction."""
        coords1 = Coordinates(x=10.0, y=20.0, z=5.0, precision=6)
        coords2 = Coordinates(x=3.0, y=15.0, z=2.0, precision=4)
        
        result = coords1 - coords2
        
        assert result.x == 7.0
        assert result.y == 5.0
        assert result.z == 3.0
        assert result.precision == 4  # Should use minimum precision

    def test_subtraction_invalid_type(self):
        """Test subtraction fails with invalid type."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        with pytest.raises(TypeError) as exc_info:
            coords - "invalid"
        assert "Can only subtract Coordinates from Coordinates" in str(exc_info.value)

    def test_multiplication_by_scalar(self):
        """Test scalar multiplication."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0, precision=3)
        
        result = coords * 2.5
        
        assert result.x == 25.0
        assert result.y == 50.0
        assert result.z == 12.5
        assert result.precision == 3  # Should preserve original precision

    def test_multiplication_by_integer(self):
        """Test multiplication by integer."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        result = coords * 3
        
        assert result.x == 30.0
        assert result.y == 60.0
        assert result.z == 15.0

    def test_multiplication_invalid_type(self):
        """Test multiplication fails with invalid type."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        with pytest.raises(TypeError) as exc_info:
            coords * "invalid"
        assert "Can only multiply Coordinates by numeric values" in str(exc_info.value)

    def test_right_multiplication(self):
        """Test right multiplication (scalar * coordinates)."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        result = 2.0 * coords
        
        assert result.x == 20.0
        assert result.y == 40.0
        assert result.z == 10.0

    # ==================== String Representation Tests ====================

    def test_str_representation(self):
        """Test string representation."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        str_repr = str(coords)
        
        assert str_repr == "(10.0, 20.0, 5.0)"

    def test_repr_representation(self):
        """Test detailed string representation."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0, precision=3)
        
        repr_str = repr(coords)
        
        expected = "Coordinates(x=10.0, y=20.0, z=5.0, precision=3)"
        assert repr_str == expected

    # ==================== Immutability Tests ====================

    def test_immutability_frozen_dataclass(self):
        """Test that coordinates is immutable (frozen dataclass)."""
        coords = Coordinates(x=10.0, y=20.0, z=5.0)
        
        with pytest.raises(AttributeError):
            coords.x = 15.0  # Should fail due to frozen dataclass

    def test_operations_create_new_instances(self):
        """Test that operations create new instances instead of modifying original."""
        original = Coordinates(x=10.0, y=20.0, z=5.0)
        
        # Various operations
        translated = original.translate(5.0, -10.0, 2.0)
        added = original + Coordinates(1.0, 1.0, 1.0)
        multiplied = original * 2
        
        # Original should remain unchanged
        assert original.x == 10.0
        assert original.y == 20.0
        assert original.z == 5.0
        
        # New instances should be different objects
        assert translated is not original
        assert added is not original
        assert multiplied is not original

    # ==================== Equality and Hashing Tests ====================

    def test_equality(self):
        """Test coordinate equality."""
        coords1 = Coordinates(x=10.0, y=20.0, z=5.0, precision=6)
        coords2 = Coordinates(x=10.0, y=20.0, z=5.0, precision=6)
        coords3 = Coordinates(x=10.0, y=20.0, z=5.1, precision=6)
        
        assert coords1 == coords2
        assert coords1 != coords3
        assert coords2 != coords3

    def test_equality_different_precision(self):
        """Test equality with different precision."""
        coords1 = Coordinates(x=10.0, y=20.0, z=5.0, precision=6)
        coords2 = Coordinates(x=10.0, y=20.0, z=5.0, precision=3)
        
        # Should be equal because precision is not compared in equality
        assert coords1 == coords2

    def test_hash_consistency(self):
        """Test that equal coordinates have the same hash."""
        coords1 = Coordinates(x=10.0, y=20.0, z=5.0, precision=6)
        coords2 = Coordinates(x=10.0, y=20.0, z=5.0, precision=3)
        
        # Equal objects should have same hash
        if coords1 == coords2:
            assert hash(coords1) == hash(coords2)

    def test_hashable_in_set(self):
        """Test that coordinates can be used in sets."""
        coords1 = Coordinates(x=10.0, y=20.0, z=5.0)
        coords2 = Coordinates(x=10.0, y=20.0, z=5.0)
        coords3 = Coordinates(x=15.0, y=25.0, z=10.0)
        
        coord_set = {coords1, coords2, coords3}
        
        # coords1 and coords2 are equal, so set should have 2 elements
        assert len(coord_set) == 2

    # ==================== Edge Cases and Boundary Tests ====================

    def test_precision_zero(self):
        """Test coordinates with zero precision."""
        coords = Coordinates(x=10.123, y=20.456, z=5.789, precision=0)
        
        assert coords.x == 10.0
        assert coords.y == 20.0
        assert coords.z == 6.0  # Should round 5.789 to 6

    def test_precision_maximum(self):
        """Test coordinates with maximum precision."""
        coords = Coordinates(x=10.123456789012345, y=20.0, z=5.0, precision=15)
        
        # Should preserve high precision
        assert coords.x == 10.123456789012345

    def test_very_small_coordinates(self):
        """Test very small coordinate values."""
        coords = Coordinates(x=1e-10, y=-1e-10, z=1e-15, precision=15)
        
        assert coords.x == 1e-10
        assert coords.y == -1e-10
        assert coords.z == 1e-15

    def test_boundary_coordinate_values(self):
        """Test coordinates at boundary values."""
        max_coord = 1e10
        coords = Coordinates(x=max_coord, y=-max_coord, z=0.0)
        
        assert coords.x == max_coord
        assert coords.y == -max_coord
        assert coords.z == 0.0

    def test_distance_calculations_with_precision(self):
        """Test distance calculations respect precision."""
        coords1 = Coordinates(x=0.0, y=0.0, z=0.0, precision=2)
        coords2 = Coordinates(x=1.0, y=1.0, z=1.0, precision=2)
        
        distance = coords1.distance_to(coords2)
        expected = math.sqrt(3)  # sqrt(1^2 + 1^2 + 1^2)
        
        assert distance == pytest.approx(expected)

    def test_complex_mathematical_operations(self):
        """Test complex combinations of mathematical operations."""
        coords1 = Coordinates(x=10.0, y=20.0, z=5.0)
        coords2 = Coordinates(x=5.0, y=10.0, z=15.0)
        coords3 = Coordinates(x=2.0, y=3.0, z=1.0)
        
        # Complex operation: (coords1 + coords2) * 2 - coords3
        result = (coords1 + coords2) * 2 - coords3
        
        expected_x = (10.0 + 5.0) * 2 - 2.0  # 28.0
        expected_y = (20.0 + 10.0) * 2 - 3.0  # 57.0
        expected_z = (5.0 + 15.0) * 2 - 1.0   # 39.0
        
        assert result.x == expected_x
        assert result.y == expected_y
        assert result.z == expected_z