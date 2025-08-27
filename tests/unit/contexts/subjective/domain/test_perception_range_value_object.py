#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Perception Range Value Objects

Test suite covering perception ranges, visibility calculations, perception capabilities,
and awareness zone management in the Subjective Context domain layer.
"""

import pytest
import math
from typing import Dict
from unittest.mock import Mock, patch

from contexts.subjective.domain.value_objects.perception_range import (
    PerceptionType,
    VisibilityLevel,
    PerceptionRange,
    PerceptionCapabilities
)


class TestPerceptionRangeCreation:
    """Test suite for PerceptionRange value object creation and validation."""
    
    def test_minimal_perception_range_creation(self):
        """Test creating perception range with minimal required fields."""
        perception_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=80.0,
            accuracy_modifier=0.8,
            environmental_modifiers={}
        )
        
        assert perception_range.perception_type == PerceptionType.VISUAL
        assert perception_range.base_range == 100.0
        assert perception_range.effective_range == 80.0
        assert perception_range.accuracy_modifier == 0.8
        assert perception_range.environmental_modifiers == {}
    
    def test_full_perception_range_creation(self):
        """Test creating perception range with environmental modifiers."""
        env_modifiers = {
            "fog": 0.5,
            "darkness": 0.3,
            "rain": 0.8
        }
        
        perception_range = PerceptionRange(
            perception_type=PerceptionType.AUDITORY,
            base_range=150.0,
            effective_range=120.0,
            accuracy_modifier=0.9,
            environmental_modifiers=env_modifiers
        )
        
        assert perception_range.perception_type == PerceptionType.AUDITORY
        assert perception_range.base_range == 150.0
        assert perception_range.effective_range == 120.0
        assert perception_range.accuracy_modifier == 0.9
        assert perception_range.environmental_modifiers == env_modifiers
    
    def test_zero_ranges_allowed(self):
        """Test that zero ranges are allowed (but negative are not)."""
        perception_range = PerceptionRange(
            perception_type=PerceptionType.TACTILE,
            base_range=0.0,
            effective_range=0.0,
            accuracy_modifier=1.0,
            environmental_modifiers={}
        )
        
        assert perception_range.base_range == 0.0
        assert perception_range.effective_range == 0.0


class TestPerceptionRangeValidation:
    """Test suite for PerceptionRange validation logic."""
    
    def test_negative_base_range_validation(self):
        """Test validation fails with negative base range."""
        with pytest.raises(ValueError, match="Base range cannot be negative"):
            PerceptionRange(
                perception_type=PerceptionType.VISUAL,
                base_range=-10.0,
                effective_range=80.0,
                accuracy_modifier=0.8,
                environmental_modifiers={}
            )
    
    def test_negative_effective_range_validation(self):
        """Test validation fails with negative effective range."""
        with pytest.raises(ValueError, match="Effective range cannot be negative"):
            PerceptionRange(
                perception_type=PerceptionType.VISUAL,
                base_range=100.0,
                effective_range=-10.0,
                accuracy_modifier=0.8,
                environmental_modifiers={}
            )
    
    def test_accuracy_modifier_below_zero(self):
        """Test validation fails with accuracy modifier below 0.0."""
        with pytest.raises(ValueError, match="Accuracy modifier must be between 0.0 and 1.0"):
            PerceptionRange(
                perception_type=PerceptionType.VISUAL,
                base_range=100.0,
                effective_range=80.0,
                accuracy_modifier=-0.1,
                environmental_modifiers={}
            )
    
    def test_accuracy_modifier_above_one(self):
        """Test validation fails with accuracy modifier above 1.0."""
        with pytest.raises(ValueError, match="Accuracy modifier must be between 0.0 and 1.0"):
            PerceptionRange(
                perception_type=PerceptionType.VISUAL,
                base_range=100.0,
                effective_range=80.0,
                accuracy_modifier=1.1,
                environmental_modifiers={}
            )
    
    def test_empty_environmental_modifier_name(self):
        """Test validation fails with empty environmental modifier name."""
        with pytest.raises(ValueError, match="Environmental modifier names must be non-empty strings"):
            PerceptionRange(
                perception_type=PerceptionType.VISUAL,
                base_range=100.0,
                effective_range=80.0,
                accuracy_modifier=0.8,
                environmental_modifiers={"": 0.5}
            )
    
    def test_whitespace_environmental_modifier_name(self):
        """Test validation fails with whitespace-only environmental modifier name."""
        with pytest.raises(ValueError, match="Environmental modifier names must be non-empty strings"):
            PerceptionRange(
                perception_type=PerceptionType.VISUAL,
                base_range=100.0,
                effective_range=80.0,
                accuracy_modifier=0.8,
                environmental_modifiers={"   \t\n  ": 0.5}
            )
    
    def test_non_string_environmental_modifier_name(self):
        """Test validation fails with non-string environmental modifier name."""
        with pytest.raises(ValueError, match="Environmental modifier names must be non-empty strings"):
            PerceptionRange(
                perception_type=PerceptionType.VISUAL,
                base_range=100.0,
                effective_range=80.0,
                accuracy_modifier=0.8,
                environmental_modifiers={123: 0.5}
            )
    
    def test_non_numeric_environmental_modifier_value(self):
        """Test validation fails with non-numeric environmental modifier value."""
        with pytest.raises(ValueError, match="Environmental modifier 'fog' must be numeric"):
            PerceptionRange(
                perception_type=PerceptionType.VISUAL,
                base_range=100.0,
                effective_range=80.0,
                accuracy_modifier=0.8,
                environmental_modifiers={"fog": "heavy"}
            )
    
    def test_boundary_accuracy_modifier_values(self):
        """Test that boundary accuracy modifier values (0.0 and 1.0) are valid."""
        # Test 0.0
        perception_range_zero = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=80.0,
            accuracy_modifier=0.0,
            environmental_modifiers={}
        )
        assert perception_range_zero.accuracy_modifier == 0.0
        
        # Test 1.0
        perception_range_one = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=80.0,
            accuracy_modifier=1.0,
            environmental_modifiers={}
        )
        assert perception_range_one.accuracy_modifier == 1.0


class TestVisibilityCalculation:
    """Test suite for visibility calculation at different distances."""
    
    def test_visibility_at_zero_distance(self):
        """Test visibility at zero distance is always clear."""
        perception_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=0.5,  # Even with low accuracy
            environmental_modifiers={"fog": 0.1}  # And bad conditions
        )
        
        visibility = perception_range.calculate_visibility_at_distance(0.0)
        assert visibility == VisibilityLevel.CLEAR
    
    def test_visibility_beyond_effective_range(self):
        """Test visibility beyond effective range is invisible."""
        perception_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=50.0,
            accuracy_modifier=1.0,
            environmental_modifiers={}
        )
        
        # At effective range boundary
        visibility_at_range = perception_range.calculate_visibility_at_distance(50.0)
        assert visibility_at_range == VisibilityLevel.INVISIBLE
        
        # Beyond effective range
        visibility_beyond = perception_range.calculate_visibility_at_distance(60.0)
        assert visibility_beyond == VisibilityLevel.INVISIBLE
    
    def test_visibility_within_range_perfect_conditions(self):
        """Test visibility calculation within range with perfect conditions."""
        perception_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={}
        )
        
        # Very close - should be clear
        visibility_close = perception_range.calculate_visibility_at_distance(10.0)
        assert visibility_close == VisibilityLevel.CLEAR
        
        # Medium distance - should still be clear or partial
        visibility_medium = perception_range.calculate_visibility_at_distance(50.0)
        assert visibility_medium in [VisibilityLevel.CLEAR, VisibilityLevel.PARTIAL]
        
        # Near maximum range - visibility degrades but still visible
        visibility_far = perception_range.calculate_visibility_at_distance(90.0)
        assert visibility_far in [VisibilityLevel.PARTIAL, VisibilityLevel.OBSCURED, VisibilityLevel.HIDDEN]
    
    def test_visibility_with_environmental_degradation(self):
        """Test visibility degradation due to environmental conditions."""
        # Perfect conditions
        perfect_perception = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={}
        )
        
        # Poor conditions
        degraded_perception = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={"fog": 0.3, "rain": 0.7}  # Combined modifier: 0.3 * 0.7 = 0.21
        )
        
        distance = 30.0
        perfect_visibility = perfect_perception.calculate_visibility_at_distance(distance)
        degraded_visibility = degraded_perception.calculate_visibility_at_distance(distance)
        
        # Degraded conditions should result in worse or equal visibility
        visibility_order = [VisibilityLevel.CLEAR, VisibilityLevel.PARTIAL, 
                           VisibilityLevel.OBSCURED, VisibilityLevel.HIDDEN, 
                           VisibilityLevel.INVISIBLE]
        
        perfect_index = visibility_order.index(perfect_visibility)
        degraded_index = visibility_order.index(degraded_visibility)
        
        # Degraded should be worse (higher index) or equal
        assert degraded_index >= perfect_index
    
    def test_visibility_with_low_accuracy(self):
        """Test visibility with low accuracy modifier."""
        low_accuracy_perception = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=0.2,  # Very low accuracy
            environmental_modifiers={}
        )
        
        # Even at close distance, low accuracy should affect visibility
        visibility_close = low_accuracy_perception.calculate_visibility_at_distance(20.0)
        
        # Should not be clear due to low accuracy
        assert visibility_close in [VisibilityLevel.PARTIAL, VisibilityLevel.OBSCURED, 
                                   VisibilityLevel.HIDDEN, VisibilityLevel.INVISIBLE]
    
    def test_visibility_level_thresholds(self):
        """Test specific visibility level threshold calculations."""
        # Create perception with known parameters to test specific thresholds
        perception_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={}
        )
        
        # Test different distances to hit different visibility thresholds
        test_distances = [10.0, 30.0, 50.0, 70.0, 90.0, 95.0]
        
        for distance in test_distances:
            visibility = perception_range.calculate_visibility_at_distance(distance)
            assert isinstance(visibility, VisibilityLevel)
            
            # Verify visibility degrades with distance
            if distance < 20.0:
                assert visibility in [VisibilityLevel.CLEAR, VisibilityLevel.PARTIAL]


class TestPerceptionRangeUtilityMethods:
    """Test suite for PerceptionRange utility methods."""
    
    def test_is_within_range_true(self):
        """Test is_within_range returns True for distances within effective range."""
        perception_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=80.0,
            accuracy_modifier=0.8,
            environmental_modifiers={}
        )
        
        assert perception_range.is_within_range(0.0)
        assert perception_range.is_within_range(40.0)
        assert perception_range.is_within_range(80.0)  # Exactly at effective range
    
    def test_is_within_range_false(self):
        """Test is_within_range returns False for distances beyond effective range."""
        perception_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=80.0,
            accuracy_modifier=0.8,
            environmental_modifiers={}
        )
        
        assert not perception_range.is_within_range(80.1)
        assert not perception_range.is_within_range(100.0)
        assert not perception_range.is_within_range(150.0)
    
    def test_apply_environmental_modifier_creates_new_instance(self):
        """Test apply_environmental_modifier creates new instance with additional modifier."""
        original = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=80.0,
            accuracy_modifier=0.8,
            environmental_modifiers={"fog": 0.5}
        )
        
        modified = original.apply_environmental_modifier("rain", 0.7)
        
        # Original unchanged
        assert original.environmental_modifiers == {"fog": 0.5}
        
        # New instance has additional modifier
        expected_modifiers = {"fog": 0.5, "rain": 0.7}
        assert modified.environmental_modifiers == expected_modifiers
        
        # Other properties unchanged
        assert modified.perception_type == original.perception_type
        assert modified.base_range == original.base_range
        assert modified.effective_range == original.effective_range
        assert modified.accuracy_modifier == original.accuracy_modifier
        
        # Different objects
        assert original is not modified
    
    def test_apply_environmental_modifier_overwrites_existing(self):
        """Test apply_environmental_modifier overwrites existing modifier with same name."""
        original = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=80.0,
            accuracy_modifier=0.8,
            environmental_modifiers={"fog": 0.5}
        )
        
        modified = original.apply_environmental_modifier("fog", 0.3)
        
        # Should overwrite the existing fog modifier
        assert modified.environmental_modifiers == {"fog": 0.3}


class TestPerceptionCapabilitiesCreation:
    """Test suite for PerceptionCapabilities creation and validation."""
    
    def test_minimal_perception_capabilities_creation(self):
        """Test creating perception capabilities with minimal fields."""
        visual_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=80.0,
            accuracy_modifier=0.8,
            environmental_modifiers={}
        )
        
        capabilities = PerceptionCapabilities(
            perception_ranges={PerceptionType.VISUAL: visual_range}
        )
        
        assert len(capabilities.perception_ranges) == 1
        assert PerceptionType.VISUAL in capabilities.perception_ranges
        assert capabilities.passive_awareness_bonus == 0.0
        assert capabilities.focused_perception_multiplier == 1.5
    
    def test_full_perception_capabilities_creation(self):
        """Test creating perception capabilities with all fields."""
        visual_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=80.0,
            accuracy_modifier=0.8,
            environmental_modifiers={}
        )
        
        auditory_range = PerceptionRange(
            perception_type=PerceptionType.AUDITORY,
            base_range=150.0,
            effective_range=120.0,
            accuracy_modifier=0.9,
            environmental_modifiers={}
        )
        
        capabilities = PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: visual_range,
                PerceptionType.AUDITORY: auditory_range
            },
            passive_awareness_bonus=0.3,
            focused_perception_multiplier=2.0
        )
        
        assert len(capabilities.perception_ranges) == 2
        assert PerceptionType.VISUAL in capabilities.perception_ranges
        assert PerceptionType.AUDITORY in capabilities.perception_ranges
        assert capabilities.passive_awareness_bonus == 0.3
        assert capabilities.focused_perception_multiplier == 2.0


class TestPerceptionCapabilitiesValidation:
    """Test suite for PerceptionCapabilities validation logic."""
    
    def test_empty_perception_ranges_validation(self):
        """Test validation fails with empty perception ranges."""
        with pytest.raises(ValueError, match="Entity must have at least one perception range"):
            PerceptionCapabilities(perception_ranges={})
    
    def test_invalid_perception_type_key(self):
        """Test validation fails with invalid perception type key."""
        visual_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=80.0,
            accuracy_modifier=0.8,
            environmental_modifiers={}
        )
        
        with pytest.raises(ValueError, match="Invalid perception type"):
            PerceptionCapabilities(
                perception_ranges={"invalid_key": visual_range}
            )
    
    def test_invalid_perception_range_value(self):
        """Test validation fails with invalid perception range value."""
        with pytest.raises(ValueError, match="Invalid perception range for"):
            PerceptionCapabilities(
                perception_ranges={PerceptionType.VISUAL: "invalid_range"}
            )
    
    def test_perception_type_mismatch(self):
        """Test validation fails when perception range type doesn't match dictionary key."""
        auditory_range = PerceptionRange(
            perception_type=PerceptionType.AUDITORY,  # Auditory type
            base_range=150.0,
            effective_range=120.0,
            accuracy_modifier=0.9,
            environmental_modifiers={}
        )
        
        with pytest.raises(ValueError, match="Perception range type mismatch"):
            PerceptionCapabilities(
                perception_ranges={PerceptionType.VISUAL: auditory_range}  # But mapped to visual
            )
    
    def test_negative_passive_awareness_bonus(self):
        """Test validation fails with negative passive awareness bonus."""
        visual_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=80.0,
            accuracy_modifier=0.8,
            environmental_modifiers={}
        )
        
        with pytest.raises(ValueError, match="Passive awareness bonus cannot be negative"):
            PerceptionCapabilities(
                perception_ranges={PerceptionType.VISUAL: visual_range},
                passive_awareness_bonus=-0.1
            )
    
    def test_zero_focused_perception_multiplier(self):
        """Test validation fails with zero focused perception multiplier."""
        visual_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=80.0,
            accuracy_modifier=0.8,
            environmental_modifiers={}
        )
        
        with pytest.raises(ValueError, match="Focused perception multiplier must be positive"):
            PerceptionCapabilities(
                perception_ranges={PerceptionType.VISUAL: visual_range},
                focused_perception_multiplier=0.0
            )
    
    def test_negative_focused_perception_multiplier(self):
        """Test validation fails with negative focused perception multiplier."""
        visual_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=80.0,
            accuracy_modifier=0.8,
            environmental_modifiers={}
        )
        
        with pytest.raises(ValueError, match="Focused perception multiplier must be positive"):
            PerceptionCapabilities(
                perception_ranges={PerceptionType.VISUAL: visual_range},
                focused_perception_multiplier=-1.0
            )


class TestPerceptionCapabilitiesBusinessLogic:
    """Test suite for PerceptionCapabilities business logic methods."""
    
    @pytest.fixture
    def multi_sense_capabilities(self):
        """Create perception capabilities with multiple senses for testing."""
        visual_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=80.0,
            accuracy_modifier=0.8,
            environmental_modifiers={}
        )
        
        auditory_range = PerceptionRange(
            perception_type=PerceptionType.AUDITORY,
            base_range=150.0,
            effective_range=120.0,
            accuracy_modifier=0.9,
            environmental_modifiers={}
        )
        
        magical_range = PerceptionRange(
            perception_type=PerceptionType.MAGICAL,
            base_range=200.0,
            effective_range=180.0,
            accuracy_modifier=0.7,
            environmental_modifiers={}
        )
        
        return PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: visual_range,
                PerceptionType.AUDITORY: auditory_range,
                PerceptionType.MAGICAL: magical_range
            },
            passive_awareness_bonus=0.2,
            focused_perception_multiplier=2.0
        )
    
    def test_get_best_visibility_no_focus(self, multi_sense_capabilities):
        """Test getting best visibility without focused perception."""
        distance = 50.0
        
        # Should use the best available sense at this distance
        visibility = multi_sense_capabilities.get_best_visibility_at_distance(distance)
        
        assert isinstance(visibility, VisibilityLevel)
        # Should not be invisible since all senses can reach this distance
        assert visibility != VisibilityLevel.INVISIBLE
    
    def test_get_best_visibility_with_focus(self, multi_sense_capabilities):
        """Test getting best visibility with focused perception."""
        distance = 50.0
        
        # Test focusing on visual perception
        focused_visibility = multi_sense_capabilities.get_best_visibility_at_distance(
            distance, 
            focused_perception=PerceptionType.VISUAL
        )
        
        # Test without focus for comparison
        unfocused_visibility = multi_sense_capabilities.get_best_visibility_at_distance(distance)
        
        # Both should be valid visibility levels
        assert isinstance(focused_visibility, VisibilityLevel)
        assert isinstance(unfocused_visibility, VisibilityLevel)
        
        # Focused perception might be better or equal, but should never be worse
        visibility_order = [VisibilityLevel.CLEAR, VisibilityLevel.PARTIAL, 
                           VisibilityLevel.OBSCURED, VisibilityLevel.HIDDEN, 
                           VisibilityLevel.INVISIBLE]
        
        focused_index = visibility_order.index(focused_visibility)
        unfocused_index = visibility_order.index(unfocused_visibility)
        
        # Focused should be better (lower index) or equal
        assert focused_index <= unfocused_index
    
    def test_get_best_visibility_beyond_all_ranges(self, multi_sense_capabilities):
        """Test visibility beyond all perception ranges."""
        distance = 1000.0  # Beyond all ranges
        
        visibility = multi_sense_capabilities.get_best_visibility_at_distance(distance)
        assert visibility == VisibilityLevel.INVISIBLE
    
    def test_get_maximum_range(self, multi_sense_capabilities):
        """Test getting maximum perception range."""
        max_range = multi_sense_capabilities.get_maximum_range()
        
        # Should be the magical range (180.0) as it has the highest effective range
        assert max_range == 180.0
    
    def test_get_maximum_range_empty_ranges(self):
        """Test getting maximum range with no perception ranges (edge case)."""
        # This shouldn't happen due to validation, but test the method directly
        visual_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=80.0,
            accuracy_modifier=0.8,
            environmental_modifiers={}
        )
        
        # Create capabilities normally, then test empty case directly
        capabilities = PerceptionCapabilities(
            perception_ranges={PerceptionType.VISUAL: visual_range}
        )
        
        # Temporarily clear ranges to test the method
        empty_capabilities = PerceptionCapabilities.__new__(PerceptionCapabilities)
        object.__setattr__(empty_capabilities, 'perception_ranges', {})
        object.__setattr__(empty_capabilities, 'passive_awareness_bonus', 0.0)
        object.__setattr__(empty_capabilities, 'focused_perception_multiplier', 1.5)
        
        max_range = empty_capabilities.get_maximum_range()
        assert max_range == 0.0
    
    def test_has_perception_type(self, multi_sense_capabilities):
        """Test checking for specific perception types."""
        assert multi_sense_capabilities.has_perception_type(PerceptionType.VISUAL)
        assert multi_sense_capabilities.has_perception_type(PerceptionType.AUDITORY)
        assert multi_sense_capabilities.has_perception_type(PerceptionType.MAGICAL)
        
        assert not multi_sense_capabilities.has_perception_type(PerceptionType.THERMAL)
        assert not multi_sense_capabilities.has_perception_type(PerceptionType.PSYCHIC)
    
    def test_get_perception_types(self, multi_sense_capabilities):
        """Test getting all available perception types."""
        perception_types = multi_sense_capabilities.get_perception_types()
        
        assert len(perception_types) == 3
        assert PerceptionType.VISUAL in perception_types
        assert PerceptionType.AUDITORY in perception_types
        assert PerceptionType.MAGICAL in perception_types
        
        # Should not contain types not in capabilities
        assert PerceptionType.THERMAL not in perception_types


class TestComplexPerceptionScenarios:
    """Test suite for complex perception scenarios."""
    
    def test_stealth_detection_scenario(self):
        """Test a complex stealth detection scenario with multiple perception types."""
        # Visual perception affected by darkness
        visual_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=0.8,
            environmental_modifiers={"darkness": 0.2}  # Heavy penalty for darkness
        )
        
        # Auditory perception less affected by darkness
        auditory_range = PerceptionRange(
            perception_type=PerceptionType.AUDITORY,
            base_range=80.0,
            effective_range=80.0,
            accuracy_modifier=0.9,
            environmental_modifiers={"darkness": 0.9}  # Minimal penalty
        )
        
        # Thermal perception unaffected by darkness
        thermal_range = PerceptionRange(
            perception_type=PerceptionType.THERMAL,
            base_range=60.0,
            effective_range=60.0,
            accuracy_modifier=0.7,
            environmental_modifiers={}  # No environmental penalties
        )
        
        guard_capabilities = PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: visual_range,
                PerceptionType.AUDITORY: auditory_range,
                PerceptionType.THERMAL: thermal_range
            },
            focused_perception_multiplier=1.5
        )
        
        # Test detection at various distances in dark conditions
        close_distance = 20.0
        medium_distance = 50.0
        far_distance = 90.0
        
        # At close distance, thermal should provide good visibility
        close_visibility = guard_capabilities.get_best_visibility_at_distance(close_distance)
        assert close_visibility in [VisibilityLevel.CLEAR, VisibilityLevel.PARTIAL, VisibilityLevel.OBSCURED]
        
        # At medium distance, auditory might be best due to less darkness penalty
        medium_visibility = guard_capabilities.get_best_visibility_at_distance(medium_distance)
        assert medium_visibility != VisibilityLevel.INVISIBLE  # Should still detect something
        
        # At far distance, might struggle to detect
        far_visibility = guard_capabilities.get_best_visibility_at_distance(far_distance)
        # Could be any level depending on the exact calculations
        assert isinstance(far_visibility, VisibilityLevel)
        
        # Focusing on auditory perception should help at medium distance
        focused_auditory = guard_capabilities.get_best_visibility_at_distance(
            medium_distance, 
            PerceptionType.AUDITORY
        )
        
        # Should be equal or better than unfocused
        visibility_order = [VisibilityLevel.CLEAR, VisibilityLevel.PARTIAL, 
                           VisibilityLevel.OBSCURED, VisibilityLevel.HIDDEN, 
                           VisibilityLevel.INVISIBLE]
        
        focused_index = visibility_order.index(focused_auditory)
        unfocused_index = visibility_order.index(medium_visibility)
        assert focused_index <= unfocused_index
    
    def test_environmental_adaptation_scenario(self):
        """Test perception adaptation to changing environmental conditions."""
        base_visual_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=0.9,
            environmental_modifiers={}
        )
        
        # Apply fog condition
        foggy_range = base_visual_range.apply_environmental_modifier("fog", 0.4)
        
        # Apply additional rain condition
        foggy_rainy_range = foggy_range.apply_environmental_modifier("rain", 0.7)
        
        # Test visibility degradation with worsening conditions
        test_distance = 40.0
        
        clear_visibility = base_visual_range.calculate_visibility_at_distance(test_distance)
        foggy_visibility = foggy_range.calculate_visibility_at_distance(test_distance)
        stormy_visibility = foggy_rainy_range.calculate_visibility_at_distance(test_distance)
        
        # Visibility should generally degrade with worse conditions
        visibility_order = [VisibilityLevel.CLEAR, VisibilityLevel.PARTIAL, 
                           VisibilityLevel.OBSCURED, VisibilityLevel.HIDDEN, 
                           VisibilityLevel.INVISIBLE]
        
        clear_index = visibility_order.index(clear_visibility)
        foggy_index = visibility_order.index(foggy_visibility)
        stormy_index = visibility_order.index(stormy_visibility)
        
        # Each condition should be worse or equal to the previous
        assert foggy_index >= clear_index
        assert stormy_index >= foggy_index
        
        # Verify environmental modifiers are correctly applied
        assert len(base_visual_range.environmental_modifiers) == 0
        assert foggy_range.environmental_modifiers == {"fog": 0.4}
        assert foggy_rainy_range.environmental_modifiers == {"fog": 0.4, "rain": 0.7}
    
    def test_focused_perception_effectiveness(self):
        """Test effectiveness of focused perception in different scenarios."""
        # Create a perception with limited range for testing focus effects
        limited_visual = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=50.0,
            effective_range=50.0,
            accuracy_modifier=0.8,
            environmental_modifiers={}
        )
        
        capabilities = PerceptionCapabilities(
            perception_ranges={PerceptionType.VISUAL: limited_visual},
            focused_perception_multiplier=2.0  # Strong focus multiplier
        )
        
        # Test distances near the normal effective range limit
        edge_distance = 50.0  # At normal effective range
        beyond_distance = 75.0  # Beyond normal but within focused range
        far_beyond_distance = 120.0  # Beyond even focused range
        
        # Without focus, should be invisible at edge distance
        unfocused_edge = capabilities.get_best_visibility_at_distance(edge_distance)
        assert unfocused_edge == VisibilityLevel.INVISIBLE
        
        # With focus, might be visible at edge distance due to extended range
        focused_edge = capabilities.get_best_visibility_at_distance(
            edge_distance, 
            PerceptionType.VISUAL
        )
        # Focus extends range to 50.0 * 2.0 = 100.0, so should be visible
        assert focused_edge != VisibilityLevel.INVISIBLE
        
        # Beyond normal range but within focused range
        focused_beyond = capabilities.get_best_visibility_at_distance(
            beyond_distance, 
            PerceptionType.VISUAL
        )
        assert focused_beyond != VisibilityLevel.INVISIBLE
        
        # Far beyond even focused range should still be invisible
        focused_far_beyond = capabilities.get_best_visibility_at_distance(
            far_beyond_distance, 
            PerceptionType.VISUAL
        )
        assert focused_far_beyond == VisibilityLevel.INVISIBLE
    
    def test_multi_sense_compensation_scenario(self):
        """Test how multiple senses can compensate for each other's weaknesses."""
        # Visual perception with fog penalty
        impaired_visual = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=0.9,
            environmental_modifiers={"fog": 0.2}  # Heavy fog penalty
        )
        
        # Auditory perception unaffected by fog
        clear_auditory = PerceptionRange(
            perception_type=PerceptionType.AUDITORY,
            base_range=80.0,
            effective_range=80.0,
            accuracy_modifier=0.8,
            environmental_modifiers={}  # No fog effect on hearing
        )
        
        # Test single-sense vs multi-sense capabilities
        visual_only = PerceptionCapabilities(
            perception_ranges={PerceptionType.VISUAL: impaired_visual}
        )
        
        multi_sense = PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: impaired_visual,
                PerceptionType.AUDITORY: clear_auditory
            }
        )
        
        # Test at distance where visual is impaired but auditory works
        test_distance = 60.0
        
        visual_only_visibility = visual_only.get_best_visibility_at_distance(test_distance)
        multi_sense_visibility = multi_sense.get_best_visibility_at_distance(test_distance)
        
        # Multi-sense should be better or equal to visual-only
        visibility_order = [VisibilityLevel.CLEAR, VisibilityLevel.PARTIAL, 
                           VisibilityLevel.OBSCURED, VisibilityLevel.HIDDEN, 
                           VisibilityLevel.INVISIBLE]
        
        visual_index = visibility_order.index(visual_only_visibility)
        multi_index = visibility_order.index(multi_sense_visibility)
        
        # Multi-sense should be better (lower index) or equal
        assert multi_index <= visual_index


class TestEdgeCasesAndBoundaryConditions:
    """Test suite for edge cases and boundary conditions."""
    
    def test_zero_effective_range_perception(self):
        """Test perception with zero effective range."""
        zero_range = PerceptionRange(
            perception_type=PerceptionType.TACTILE,
            base_range=0.0,
            effective_range=0.0,
            accuracy_modifier=1.0,
            environmental_modifiers={}
        )
        
        # Only at zero distance should be clear
        assert zero_range.calculate_visibility_at_distance(0.0) == VisibilityLevel.CLEAR
        assert zero_range.calculate_visibility_at_distance(0.1) == VisibilityLevel.INVISIBLE
        
        assert zero_range.is_within_range(0.0)
        assert not zero_range.is_within_range(0.1)
    
    def test_zero_accuracy_perception(self):
        """Test perception with zero accuracy modifier."""
        zero_accuracy = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=0.0,  # Zero accuracy
            environmental_modifiers={}
        )
        
        # Even at close distance, should have poor visibility due to zero accuracy
        visibility = zero_accuracy.calculate_visibility_at_distance(10.0)
        assert visibility == VisibilityLevel.INVISIBLE  # Zero accuracy results in zero visibility score
    
    def test_extreme_environmental_modifiers(self):
        """Test behavior with extreme environmental modifiers."""
        extreme_perception = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={
                "blizzard": 0.01,  # Extreme penalty
                "magical_enhancement": 100.0  # Extreme bonus (though capped by other factors)
            }
        )
        
        # The extreme penalty should dominate
        visibility = extreme_perception.calculate_visibility_at_distance(10.0)
        # Combined modifier: 0.01 * 100.0 = 1.0, but distance factor and other elements affect final score
        assert isinstance(visibility, VisibilityLevel)
    
    def test_very_large_distances(self):
        """Test behavior with very large distances."""
        normal_perception = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={}
        )
        
        # Test with extremely large distance
        huge_distance = 1000000.0
        visibility = normal_perception.calculate_visibility_at_distance(huge_distance)
        assert visibility == VisibilityLevel.INVISIBLE
        assert not normal_perception.is_within_range(huge_distance)
    
    def test_negative_distances(self):
        """Test behavior with negative distances (should be treated as positive)."""
        perception_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={}
        )
        
        # Negative distances should be treated as zero (clear visibility)
        visibility_negative = perception_range.calculate_visibility_at_distance(-10.0)
        visibility_zero = perception_range.calculate_visibility_at_distance(0.0)
        
        # Both should be clear since negative distance is treated as zero
        assert visibility_negative == VisibilityLevel.CLEAR
        assert visibility_zero == VisibilityLevel.CLEAR
    
    def test_focused_perception_on_nonexistent_type(self):
        """Test focused perception on a perception type that doesn't exist."""
        visual_range = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={}
        )
        
        capabilities = PerceptionCapabilities(
            perception_ranges={PerceptionType.VISUAL: visual_range}
        )
        
        # Try to focus on a non-existent perception type
        visibility = capabilities.get_best_visibility_at_distance(
            50.0, 
            focused_perception=PerceptionType.THERMAL  # Not in capabilities
        )
        
        # Should still work using available perceptions (visual)
        assert isinstance(visibility, VisibilityLevel)
        # Since thermal doesn't exist, should use visual without focus bonus
        assert visibility != VisibilityLevel.INVISIBLE  # Visual should still work at this distance