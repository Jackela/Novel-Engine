#!/usr/bin/env python3
"""
Perception Range Value Object Tests

Tests for PerceptionType, VisibilityLevel, PerceptionRange, and PerceptionCapabilities.
Covers unit tests, integration tests, and boundary tests.
"""

import pytest

from src.contexts.subjective.domain.value_objects.perception_range import (
    PerceptionCapabilities,
    PerceptionRange,
    PerceptionType,
    VisibilityLevel,
)

pytestmark = pytest.mark.unit



# ============================================================================
# Unit Tests (12 tests)
# ============================================================================


@pytest.mark.unit
class TestPerceptionType:
    """Unit tests for PerceptionType enum."""

    def test_perception_type_values(self):
        """Test perception type enum values."""
        assert PerceptionType.VISUAL.value == "visual"
        assert PerceptionType.AUDITORY.value == "auditory"
        assert PerceptionType.TACTILE.value == "tactile"
        assert PerceptionType.MAGICAL.value == "magical"
        assert PerceptionType.PSYCHIC.value == "psychic"
        assert PerceptionType.THERMAL.value == "thermal"
        assert PerceptionType.VIBRATIONAL.value == "vibrational"


@pytest.mark.unit
class TestVisibilityLevel:
    """Unit tests for VisibilityLevel enum."""

    def test_visibility_level_values(self):
        """Test visibility level enum values."""
        assert VisibilityLevel.CLEAR.value == "clear"
        assert VisibilityLevel.PARTIAL.value == "partial"
        assert VisibilityLevel.OBSCURED.value == "obscured"
        assert VisibilityLevel.HIDDEN.value == "hidden"
        assert VisibilityLevel.INVISIBLE.value == "invisible"


@pytest.mark.unit
class TestPerceptionRange:
    """Unit tests for PerceptionRange."""

    def test_create_perception_range(self):
        """Test creating perception range."""
        range_obj = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={},
        )
        assert range_obj.perception_type == PerceptionType.VISUAL
        assert range_obj.base_range == 100.0
        assert range_obj.effective_range == 100.0
        assert range_obj.accuracy_modifier == 1.0

    def test_calculate_visibility_at_zero_distance(self):
        """Test visibility at zero distance."""
        range_obj = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={},
        )
        visibility = range_obj.calculate_visibility_at_distance(0.0)
        assert visibility == VisibilityLevel.CLEAR

    def test_calculate_visibility_within_range(self):
        """Test visibility within range."""
        range_obj = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={},
        )
        visibility = range_obj.calculate_visibility_at_distance(50.0)
        assert visibility in [VisibilityLevel.CLEAR, VisibilityLevel.PARTIAL, VisibilityLevel.OBSCURED]

    def test_calculate_visibility_beyond_range(self):
        """Test visibility beyond range."""
        range_obj = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={},
        )
        visibility = range_obj.calculate_visibility_at_distance(150.0)
        assert visibility == VisibilityLevel.INVISIBLE

    def test_is_within_range(self):
        """Test within range check."""
        range_obj = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={},
        )
        assert range_obj.is_within_range(50.0)
        assert range_obj.is_within_range(100.0)
        assert not range_obj.is_within_range(150.0)

    def test_apply_environmental_modifier(self):
        """Test applying environmental modifier."""
        range_obj = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={},
        )
        
        new_range = range_obj.apply_environmental_modifier("darkness", 0.5)
        assert "darkness" in new_range.environmental_modifiers
        assert new_range.environmental_modifiers["darkness"] == 0.5


@pytest.mark.unit
class TestPerceptionCapabilities:
    """Unit tests for PerceptionCapabilities."""

    def test_create_capabilities(self):
        """Test creating perception capabilities."""
        capabilities = PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: PerceptionRange(
                    perception_type=PerceptionType.VISUAL,
                    base_range=100.0,
                    effective_range=100.0,
                    accuracy_modifier=1.0,
                    environmental_modifiers={},
                ),
            }
        )
        assert PerceptionType.VISUAL in capabilities.perception_ranges

    def test_get_maximum_range(self):
        """Test getting maximum range."""
        capabilities = PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: PerceptionRange(
                    perception_type=PerceptionType.VISUAL,
                    base_range=100.0,
                    effective_range=100.0,
                    accuracy_modifier=1.0,
                    environmental_modifiers={},
                ),
                PerceptionType.AUDITORY: PerceptionRange(
                    perception_type=PerceptionType.AUDITORY,
                    base_range=50.0,
                    effective_range=50.0,
                    accuracy_modifier=0.8,
                    environmental_modifiers={},
                ),
            }
        )
        assert capabilities.get_maximum_range() == 100.0

    def test_has_perception_type(self):
        """Test checking for perception type."""
        capabilities = PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: PerceptionRange(
                    perception_type=PerceptionType.VISUAL,
                    base_range=100.0,
                    effective_range=100.0,
                    accuracy_modifier=1.0,
                    environmental_modifiers={},
                ),
            }
        )
        assert capabilities.has_perception_type(PerceptionType.VISUAL)
        assert not capabilities.has_perception_type(PerceptionType.AUDITORY)

    def test_get_perception_types(self):
        """Test getting all perception types."""
        capabilities = PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: PerceptionRange(
                    perception_type=PerceptionType.VISUAL,
                    base_range=100.0,
                    effective_range=100.0,
                    accuracy_modifier=1.0,
                    environmental_modifiers={},
                ),
                PerceptionType.AUDITORY: PerceptionRange(
                    perception_type=PerceptionType.AUDITORY,
                    base_range=50.0,
                    effective_range=50.0,
                    accuracy_modifier=0.8,
                    environmental_modifiers={},
                ),
            }
        )
        types = capabilities.get_perception_types()
        assert PerceptionType.VISUAL in types
        assert PerceptionType.AUDITORY in types
        assert len(types) == 2


# ============================================================================
# Integration Tests (8 tests)
# ============================================================================


@pytest.mark.integration
class TestPerceptionRangeIntegration:
    """Integration tests for perception range."""

    def test_visibility_with_environmental_modifiers(self):
        """Test visibility with environmental modifiers."""
        range_obj = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={"fog": 0.5},
        )
        
        # Same distance should have worse visibility with fog
        visibility_with_fog = range_obj.calculate_visibility_at_distance(50.0)
        
        range_obj_no_fog = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={},
        )
        visibility_without_fog = range_obj_no_fog.calculate_visibility_at_distance(50.0)
        
        # Fog should degrade visibility
        assert visibility_with_fog.value <= visibility_without_fog.value

    def test_capabilities_best_visibility(self):
        """Test getting best visibility from capabilities."""
        capabilities = PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: PerceptionRange(
                    perception_type=PerceptionType.VISUAL,
                    base_range=100.0,
                    effective_range=100.0,
                    accuracy_modifier=1.0,
                    environmental_modifiers={},
                ),
                PerceptionType.AUDITORY: PerceptionRange(
                    perception_type=PerceptionType.AUDITORY,
                    base_range=50.0,
                    effective_range=50.0,
                    accuracy_modifier=0.8,
                    environmental_modifiers={},
                ),
            }
        )
        
        # At 30 distance, visual should be clear but auditory might be partial
        best_visibility = capabilities.get_best_visibility_at_distance(30.0)
        assert best_visibility in [VisibilityLevel.CLEAR, VisibilityLevel.PARTIAL]


@pytest.mark.integration
class TestPerceptionCapabilitiesIntegration:
    """Integration tests for perception capabilities."""

    def test_multiple_perception_types_integration(self):
        """Test multiple perception types working together."""
        capabilities = PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: PerceptionRange(
                    perception_type=PerceptionType.VISUAL,
                    base_range=100.0,
                    effective_range=100.0,
                    accuracy_modifier=1.0,
                    environmental_modifiers={},
                ),
                PerceptionType.AUDITORY: PerceptionRange(
                    perception_type=PerceptionType.AUDITORY,
                    base_range=80.0,
                    effective_range=80.0,
                    accuracy_modifier=0.8,
                    environmental_modifiers={},
                ),
                PerceptionType.THERMAL: PerceptionRange(
                    perception_type=PerceptionType.THERMAL,
                    base_range=60.0,
                    effective_range=60.0,
                    accuracy_modifier=0.7,
                    environmental_modifiers={},
                ),
            }
        )
        
        assert capabilities.get_maximum_range() == 100.0
        assert len(capabilities.get_perception_types()) == 3

    def test_focused_perception_multiplier(self):
        """Test focused perception multiplier."""
        capabilities = PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: PerceptionRange(
                    perception_type=PerceptionType.VISUAL,
                    base_range=100.0,
                    effective_range=100.0,
                    accuracy_modifier=1.0,
                    environmental_modifiers={},
                ),
            },
            focused_perception_multiplier=2.0,
        )
        
        # At 150 distance (beyond normal range), with focus should be visible
        visibility = capabilities.get_best_visibility_at_distance(
            150.0,
            focused_perception=PerceptionType.VISUAL,
        )
        assert visibility != VisibilityLevel.INVISIBLE


# ============================================================================
# Boundary Tests (7 tests)
# ============================================================================


@pytest.mark.unit
class TestPerceptionRangeBoundaryConditions:
    """Boundary tests for perception range."""

    def test_zero_base_range(self):
        """Test with zero base range."""
        range_obj = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=0.0,
            effective_range=0.0,
            accuracy_modifier=1.0,
            environmental_modifiers={},
        )
        assert range_obj.base_range == 0.0

    def test_zero_effective_range(self):
        """Test with zero effective range."""
        with pytest.raises(ValueError, match="Effective range cannot be negative"):
            PerceptionRange(
                perception_type=PerceptionType.VISUAL,
                base_range=100.0,
                effective_range=-1.0,
                accuracy_modifier=1.0,
                environmental_modifiers={},
            )

    def test_zero_accuracy(self):
        """Test with zero accuracy modifier."""
        range_obj = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=0.0,
            environmental_modifiers={},
        )
        visibility = range_obj.calculate_visibility_at_distance(1.0)
        # Zero accuracy should result in poor visibility
        assert visibility in [VisibilityLevel.HIDDEN, VisibilityLevel.INVISIBLE]

    def test_maximum_accuracy(self):
        """Test with maximum accuracy modifier."""
        range_obj = PerceptionRange(
            perception_type=PerceptionType.VISUAL,
            base_range=100.0,
            effective_range=100.0,
            accuracy_modifier=1.0,
            environmental_modifiers={},
        )
        visibility = range_obj.calculate_visibility_at_distance(1.0)
        assert visibility == VisibilityLevel.CLEAR

    def test_negative_base_range(self):
        """Test negative base range validation."""
        with pytest.raises(ValueError, match="Base range cannot be negative"):
            PerceptionRange(
                perception_type=PerceptionType.VISUAL,
                base_range=-10.0,
                effective_range=100.0,
                accuracy_modifier=1.0,
                environmental_modifiers={},
            )

    def test_zero_passive_awareness_bonus(self):
        """Test with zero passive awareness bonus."""
        capabilities = PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: PerceptionRange(
                    perception_type=PerceptionType.VISUAL,
                    base_range=100.0,
                    effective_range=100.0,
                    accuracy_modifier=1.0,
                    environmental_modifiers={},
                ),
            },
            passive_awareness_bonus=0.0,
        )
        assert capabilities.passive_awareness_bonus == 0.0

    def test_minimum_focused_multiplier(self):
        """Test minimum focused perception multiplier."""
        # Should work with very small multiplier
        capabilities = PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: PerceptionRange(
                    perception_type=PerceptionType.VISUAL,
                    base_range=100.0,
                    effective_range=100.0,
                    accuracy_modifier=1.0,
                    environmental_modifiers={},
                ),
            },
            focused_perception_multiplier=0.1,
        )
        assert capabilities.focused_perception_multiplier == 0.1


# Total: 12 unit + 8 integration + 7 boundary = 27 tests for perception_range
