#!/usr/bin/env python3
"""
Unit tests for DiplomaticStatus Value Object

Comprehensive test suite for the DiplomaticStatus enum covering
strength mapping, colors, and labels.
"""

import sys
from unittest.mock import MagicMock

import pytest

# Mock problematic dependencies
pytestmark = pytest.mark.unit

sys.modules["aioredis"] = MagicMock()

# Import the value object we're testing
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus


class TestDiplomaticStatusEnum:
    """Test suite for DiplomaticStatus enum."""

    # ==================== Enum Value Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enum_values_exist(self):
        """Test that all expected enum values exist."""
        assert DiplomaticStatus.ALLIED.value == "allied"
        assert DiplomaticStatus.FRIENDLY.value == "friendly"
        assert DiplomaticStatus.NEUTRAL.value == "neutral"
        assert DiplomaticStatus.COLD.value == "cold"
        assert DiplomaticStatus.HOSTILE.value == "hostile"
        assert DiplomaticStatus.AT_WAR.value == "at_war"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_enum_count(self):
        """Test that we have exactly 6 status values."""
        assert len(DiplomaticStatus) == 6

    # ==================== from_relation_strength Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_allied_at_threshold(self):
        """Test that strength 50 maps to ALLIED."""
        status = DiplomaticStatus.from_relation_strength(50)
        assert status == DiplomaticStatus.ALLIED

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_allied_above_threshold(self):
        """Test that strength above 50 maps to ALLIED."""
        status = DiplomaticStatus.from_relation_strength(75)
        assert status == DiplomaticStatus.ALLIED

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_allied_at_max(self):
        """Test that strength 100 maps to ALLIED."""
        status = DiplomaticStatus.from_relation_strength(100)
        assert status == DiplomaticStatus.ALLIED

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_friendly_at_threshold(self):
        """Test that strength 20 maps to FRIENDLY."""
        status = DiplomaticStatus.from_relation_strength(20)
        assert status == DiplomaticStatus.FRIENDLY

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_friendly_middle(self):
        """Test that strength between 20-49 maps to FRIENDLY."""
        status = DiplomaticStatus.from_relation_strength(35)
        assert status == DiplomaticStatus.FRIENDLY

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_friendly_just_below_allied(self):
        """Test that strength 49 maps to FRIENDLY."""
        status = DiplomaticStatus.from_relation_strength(49)
        assert status == DiplomaticStatus.FRIENDLY

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_neutral_positive(self):
        """Test that positive strength < 20 maps to NEUTRAL."""
        status = DiplomaticStatus.from_relation_strength(19)
        assert status == DiplomaticStatus.NEUTRAL

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_neutral_zero(self):
        """Test that strength 0 maps to NEUTRAL."""
        status = DiplomaticStatus.from_relation_strength(0)
        assert status == DiplomaticStatus.NEUTRAL

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_neutral_negative(self):
        """Test that negative strength > -20 maps to NEUTRAL."""
        status = DiplomaticStatus.from_relation_strength(-19)
        assert status == DiplomaticStatus.NEUTRAL

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_cold_at_threshold(self):
        """Test that strength -20 maps to COLD."""
        status = DiplomaticStatus.from_relation_strength(-20)
        assert status == DiplomaticStatus.COLD

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_cold_middle(self):
        """Test that strength between -50 and -20 maps to COLD."""
        status = DiplomaticStatus.from_relation_strength(-35)
        assert status == DiplomaticStatus.COLD

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_cold_just_above_hostile(self):
        """Test that strength -49 maps to COLD."""
        status = DiplomaticStatus.from_relation_strength(-49)
        assert status == DiplomaticStatus.COLD

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_hostile_at_threshold(self):
        """Test that strength -50 maps to HOSTILE."""
        status = DiplomaticStatus.from_relation_strength(-50)
        assert status == DiplomaticStatus.HOSTILE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_hostile_middle(self):
        """Test that strength between -80 and -50 maps to HOSTILE."""
        status = DiplomaticStatus.from_relation_strength(-65)
        assert status == DiplomaticStatus.HOSTILE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_hostile_just_above_war(self):
        """Test that strength -79 maps to HOSTILE."""
        status = DiplomaticStatus.from_relation_strength(-79)
        assert status == DiplomaticStatus.HOSTILE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_at_war_at_threshold(self):
        """Test that strength -80 maps to AT_WAR."""
        status = DiplomaticStatus.from_relation_strength(-80)
        assert status == DiplomaticStatus.AT_WAR

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_at_war_below_threshold(self):
        """Test that strength below -80 maps to AT_WAR."""
        status = DiplomaticStatus.from_relation_strength(-90)
        assert status == DiplomaticStatus.AT_WAR

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_at_war_at_min(self):
        """Test that strength -100 maps to AT_WAR."""
        status = DiplomaticStatus.from_relation_strength(-100)
        assert status == DiplomaticStatus.AT_WAR

    # ==================== Clamping Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_clamps_high_values(self):
        """Test that strength above 100 is clamped to 100."""
        status = DiplomaticStatus.from_relation_strength(150)
        assert status == DiplomaticStatus.ALLIED

    @pytest.mark.unit
    @pytest.mark.fast
    def test_from_strength_clamps_low_values(self):
        """Test that strength below -100 is clamped to -100."""
        status = DiplomaticStatus.from_relation_strength(-150)
        assert status == DiplomaticStatus.AT_WAR

    # ==================== Color Property Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_color_allied_is_green(self):
        """Test ALLIED color is green."""
        assert DiplomaticStatus.ALLIED.color == "#22c55e"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_color_friendly_is_lime(self):
        """Test FRIENDLY color is lime."""
        assert DiplomaticStatus.FRIENDLY.color == "#84cc16"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_color_neutral_is_yellow(self):
        """Test NEUTRAL color is yellow."""
        assert DiplomaticStatus.NEUTRAL.color == "#eab308"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_color_cold_is_orange(self):
        """Test COLD color is orange."""
        assert DiplomaticStatus.COLD.color == "#f97316"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_color_hostile_is_red(self):
        """Test HOSTILE color is red."""
        assert DiplomaticStatus.HOSTILE.color == "#ef4444"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_color_at_war_is_dark_red(self):
        """Test AT_WAR color is darker red."""
        assert DiplomaticStatus.AT_WAR.color == "#dc2626"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_all_colors_are_hex_strings(self):
        """Test that all colors are valid hex color strings."""
        for status in DiplomaticStatus:
            color = status.color
            assert color.startswith("#")
            assert len(color) == 7

    # ==================== Label Property Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_label_allied(self):
        """Test ALLIED label."""
        assert DiplomaticStatus.ALLIED.label == "Allied"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_label_friendly(self):
        """Test FRIENDLY label."""
        assert DiplomaticStatus.FRIENDLY.label == "Friendly"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_label_neutral(self):
        """Test NEUTRAL label."""
        assert DiplomaticStatus.NEUTRAL.label == "Neutral"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_label_cold(self):
        """Test COLD label."""
        assert DiplomaticStatus.COLD.label == "Cold"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_label_hostile(self):
        """Test HOSTILE label."""
        assert DiplomaticStatus.HOSTILE.label == "Hostile"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_label_at_war(self):
        """Test AT_WAR label."""
        assert DiplomaticStatus.AT_WAR.label == "At War"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_all_labels_are_strings(self):
        """Test that all labels are non-empty strings."""
        for status in DiplomaticStatus:
            label = status.label
            assert isinstance(label, str)
            assert len(label) > 0

    # ==================== Boundary Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_boundary_between_allied_and_friendly(self):
        """Test boundary between ALLIED (50+) and FRIENDLY (20-49)."""
        assert DiplomaticStatus.from_relation_strength(50) == DiplomaticStatus.ALLIED
        assert DiplomaticStatus.from_relation_strength(49) == DiplomaticStatus.FRIENDLY

    @pytest.mark.unit
    @pytest.mark.fast
    def test_boundary_between_friendly_and_neutral(self):
        """Test boundary between FRIENDLY (20+) and NEUTRAL (-19 to 19)."""
        assert DiplomaticStatus.from_relation_strength(20) == DiplomaticStatus.FRIENDLY
        assert DiplomaticStatus.from_relation_strength(19) == DiplomaticStatus.NEUTRAL

    @pytest.mark.unit
    @pytest.mark.fast
    def test_boundary_between_neutral_and_cold(self):
        """Test boundary between NEUTRAL (above -20) and COLD (-20 and below)."""
        assert DiplomaticStatus.from_relation_strength(-19) == DiplomaticStatus.NEUTRAL
        assert DiplomaticStatus.from_relation_strength(-20) == DiplomaticStatus.COLD

    @pytest.mark.unit
    @pytest.mark.fast
    def test_boundary_between_cold_and_hostile(self):
        """Test boundary between COLD (above -50) and HOSTILE (-50 and below)."""
        assert DiplomaticStatus.from_relation_strength(-49) == DiplomaticStatus.COLD
        assert DiplomaticStatus.from_relation_strength(-50) == DiplomaticStatus.HOSTILE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_boundary_between_hostile_and_at_war(self):
        """Test boundary between HOSTILE (above -80) and AT_WAR (-80 and below)."""
        assert DiplomaticStatus.from_relation_strength(-79) == DiplomaticStatus.HOSTILE
        assert DiplomaticStatus.from_relation_strength(-80) == DiplomaticStatus.AT_WAR
