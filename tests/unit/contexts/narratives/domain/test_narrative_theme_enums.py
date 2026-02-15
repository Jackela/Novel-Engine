#!/usr/bin/env python3
"""
Unit Tests for NarrativeTheme Enum Types

Test suite covering ThemeType and ThemeIntensity enums
in the Narrative Context domain layer.
"""

import pytest

from src.contexts.narratives.domain.value_objects.narrative_theme import (
    ThemeIntensity,
    ThemeType,
)

pytestmark = pytest.mark.unit


class TestThemeTypeEnum:
    """Test suite for ThemeType enum."""

    @pytest.mark.unit
    def test_all_theme_types_exist(self):
        """Test that all expected theme types are defined."""
        expected_types = {
            "UNIVERSAL",
            "SOCIAL",
            "PHILOSOPHICAL",
            "PSYCHOLOGICAL",
            "CULTURAL",
            "MORAL",
            "POLITICAL",
            "SPIRITUAL",
            "ENVIRONMENTAL",
            "TECHNOLOGICAL",
            "FAMILY",
            "COMING_OF_AGE",
        }

        actual_types = {item.name for item in ThemeType}
        assert actual_types == expected_types

    @pytest.mark.unit
    def test_theme_type_string_values(self):
        """Test that theme type enum values have correct string representations."""
        assert ThemeType.UNIVERSAL.value == "universal"
        assert ThemeType.SOCIAL.value == "social"
        assert ThemeType.PHILOSOPHICAL.value == "philosophical"
        assert ThemeType.PSYCHOLOGICAL.value == "psychological"
        assert ThemeType.CULTURAL.value == "cultural"
        assert ThemeType.MORAL.value == "moral"
        assert ThemeType.POLITICAL.value == "political"
        assert ThemeType.SPIRITUAL.value == "spiritual"
        assert ThemeType.ENVIRONMENTAL.value == "environmental"
        assert ThemeType.TECHNOLOGICAL.value == "technological"
        assert ThemeType.FAMILY.value == "family"
        assert ThemeType.COMING_OF_AGE.value == "coming_of_age"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_theme_type_uniqueness(self):
        """Test that all theme type values are unique."""
        values = [item.value for item in ThemeType]
        assert len(values) == len(set(values))

    @pytest.mark.unit
    @pytest.mark.fast
    def test_theme_type_membership(self):
        """Test theme type membership operations."""
        assert ThemeType.MORAL in ThemeType
        assert "moral" == ThemeType.MORAL.value
        assert ThemeType.MORAL == ThemeType("moral")


class TestThemeIntensityEnum:
    """Test suite for ThemeIntensity enum."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_all_intensity_levels_exist(self):
        """Test that all expected intensity levels are defined."""
        expected_levels = {"SUBTLE", "MODERATE", "PROMINENT", "CENTRAL", "OVERWHELMING"}
        actual_levels = {item.name for item in ThemeIntensity}
        assert actual_levels == expected_levels

    @pytest.mark.unit
    @pytest.mark.fast
    def test_intensity_string_values(self):
        """Test that intensity enum values have correct string representations."""
        assert ThemeIntensity.SUBTLE.value == "subtle"
        assert ThemeIntensity.MODERATE.value == "moderate"
        assert ThemeIntensity.PROMINENT.value == "prominent"
        assert ThemeIntensity.CENTRAL.value == "central"
        assert ThemeIntensity.OVERWHELMING.value == "overwhelming"

    @pytest.mark.unit
    def test_intensity_logical_ordering(self):
        """Test that intensity levels represent logical progression."""
        intensity_order = {
            ThemeIntensity.SUBTLE: 1,
            ThemeIntensity.MODERATE: 2,
            ThemeIntensity.PROMINENT: 3,
            ThemeIntensity.CENTRAL: 4,
            ThemeIntensity.OVERWHELMING: 5,
        }

        assert (
            intensity_order[ThemeIntensity.OVERWHELMING]
            > intensity_order[ThemeIntensity.CENTRAL]
        )
        assert (
            intensity_order[ThemeIntensity.CENTRAL]
            > intensity_order[ThemeIntensity.PROMINENT]
        )
        assert (
            intensity_order[ThemeIntensity.PROMINENT]
            > intensity_order[ThemeIntensity.MODERATE]
        )
        assert (
            intensity_order[ThemeIntensity.MODERATE]
            > intensity_order[ThemeIntensity.SUBTLE]
        )
