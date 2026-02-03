#!/usr/bin/env python3
"""
Unit Tests for NarrativeTheme Validation

Test suite covering input validation and constraint enforcement
for NarrativeTheme in the Narrative Context domain layer.
"""

from decimal import Decimal

import pytest

from src.contexts.narratives.domain.value_objects.narrative_theme import (
    NarrativeTheme,
    ThemeIntensity,
    ThemeType,
)


class TestNarrativeThemeValidation:
    """Test suite for NarrativeTheme validation logic."""

    @pytest.mark.unit
    def test_empty_name_validation(self):
        """Test validation fails with empty name."""
        with pytest.raises(ValueError, match="Theme name cannot be empty"):
            NarrativeTheme(
                theme_id="empty-name-test",
                theme_type=ThemeType.FAMILY,
                intensity=ThemeIntensity.MODERATE,
                name="",
                description="Valid description",
            )

    @pytest.mark.unit
    def test_whitespace_only_name_validation(self):
        """Test validation fails with whitespace-only name."""
        with pytest.raises(ValueError, match="Theme name cannot be empty"):
            NarrativeTheme(
                theme_id="whitespace-name-test",
                theme_type=ThemeType.FAMILY,
                intensity=ThemeIntensity.MODERATE,
                name="   ",
                description="Valid description",
            )

    @pytest.mark.unit
    def test_empty_description_validation(self):
        """Test validation fails with empty description."""
        with pytest.raises(ValueError, match="Theme description cannot be empty"):
            NarrativeTheme(
                theme_id="empty-desc-test",
                theme_type=ThemeType.ENVIRONMENTAL,
                intensity=ThemeIntensity.SUBTLE,
                name="Valid Name",
                description="",
            )

    @pytest.mark.unit
    def test_whitespace_only_description_validation(self):
        """Test validation fails with whitespace-only description."""
        with pytest.raises(ValueError, match="Theme description cannot be empty"):
            NarrativeTheme(
                theme_id="whitespace-desc-test",
                theme_type=ThemeType.ENVIRONMENTAL,
                intensity=ThemeIntensity.SUBTLE,
                name="Valid Name",
                description="   \t\n  ",
            )

    @pytest.mark.unit
    def test_negative_sequence_validation(self):
        """Test validation fails with negative sequence numbers."""
        with pytest.raises(
            ValueError, match="introduction_sequence must be non-negative"
        ):
            NarrativeTheme(
                theme_id="negative-intro-test",
                theme_type=ThemeType.COMING_OF_AGE,
                intensity=ThemeIntensity.CENTRAL,
                name="Growing Up",
                description="The journey to maturity",
                introduction_sequence=-1,
            )

        with pytest.raises(
            ValueError, match="resolution_sequence must be non-negative"
        ):
            NarrativeTheme(
                theme_id="negative-resolution-test",
                theme_type=ThemeType.COMING_OF_AGE,
                intensity=ThemeIntensity.CENTRAL,
                name="Growing Up",
                description="The journey to maturity",
                resolution_sequence=-5,
            )

        with pytest.raises(
            ValueError, match="peak_intensity_sequence must be non-negative"
        ):
            NarrativeTheme(
                theme_id="negative-peak-test",
                theme_type=ThemeType.COMING_OF_AGE,
                intensity=ThemeIntensity.CENTRAL,
                name="Growing Up",
                description="The journey to maturity",
                peak_intensity_sequence=-10,
            )

    @pytest.mark.unit
    def test_zero_sequence_allowed(self):
        """Test that zero sequence numbers are allowed."""
        theme = NarrativeTheme(
            theme_id="zero-seq-test",
            theme_type=ThemeType.TECHNOLOGICAL,
            intensity=ThemeIntensity.OVERWHELMING,
            name="AI Dominance",
            description="Technology overtaking humanity",
            introduction_sequence=0,
            resolution_sequence=0,
            peak_intensity_sequence=0,
        )

        assert theme.introduction_sequence == 0
        assert theme.resolution_sequence == 0
        assert theme.peak_intensity_sequence == 0

    @pytest.mark.unit
    def test_moral_complexity_below_minimum_validation(self):
        """Test validation fails with moral complexity below 1."""
        with pytest.raises(
            ValueError, match="moral_complexity must be between 1 and 10"
        ):
            NarrativeTheme(
                theme_id="low-complexity-test",
                theme_type=ThemeType.SPIRITUAL,
                intensity=ThemeIntensity.MODERATE,
                name="Faith",
                description="Spiritual journey",
                moral_complexity=Decimal("0.5"),
            )

    @pytest.mark.unit
    def test_moral_complexity_above_maximum_validation(self):
        """Test validation fails with moral complexity above 10."""
        with pytest.raises(
            ValueError, match="moral_complexity must be between 1 and 10"
        ):
            NarrativeTheme(
                theme_id="high-complexity-test",
                theme_type=ThemeType.SPIRITUAL,
                intensity=ThemeIntensity.MODERATE,
                name="Faith",
                description="Spiritual journey",
                moral_complexity=Decimal("11.0"),
            )

    @pytest.mark.unit
    def test_emotional_resonance_boundary_validation(self):
        """Test emotional resonance boundary validation."""
        with pytest.raises(
            ValueError, match="emotional_resonance must be between 1 and 10"
        ):
            NarrativeTheme(
                theme_id="low-resonance-test",
                theme_type=ThemeType.POLITICAL,
                intensity=ThemeIntensity.PROMINENT,
                name="Revolution",
                description="Fight for freedom",
                emotional_resonance=Decimal("0.9"),
            )

        with pytest.raises(
            ValueError, match="emotional_resonance must be between 1 and 10"
        ):
            NarrativeTheme(
                theme_id="high-resonance-test",
                theme_type=ThemeType.POLITICAL,
                intensity=ThemeIntensity.PROMINENT,
                name="Revolution",
                description="Fight for freedom",
                emotional_resonance=Decimal("10.1"),
            )

    @pytest.mark.unit
    def test_universal_appeal_boundary_validation(self):
        """Test universal appeal boundary validation."""
        with pytest.raises(
            ValueError, match="universal_appeal must be between 1 and 10"
        ):
            NarrativeTheme(
                theme_id="low-appeal-test",
                theme_type=ThemeType.CULTURAL,
                intensity=ThemeIntensity.SUBTLE,
                name="Heritage",
                description="Cultural traditions",
                universal_appeal=Decimal("0.5"),
            )

        with pytest.raises(
            ValueError, match="universal_appeal must be between 1 and 10"
        ):
            NarrativeTheme(
                theme_id="high-appeal-test",
                theme_type=ThemeType.CULTURAL,
                intensity=ThemeIntensity.SUBTLE,
                name="Heritage",
                description="Cultural traditions",
                universal_appeal=Decimal("15.0"),
            )

    @pytest.mark.unit
    def test_valid_decimal_boundary_values(self):
        """Test that boundary decimal values (1 and 10) are valid."""
        theme = NarrativeTheme(
            theme_id="boundary-test",
            theme_type=ThemeType.PHILOSOPHICAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Existential Crisis",
            description="Questions about meaning and existence",
            moral_complexity=Decimal("1.0"),
            emotional_resonance=Decimal("10.0"),
            universal_appeal=Decimal("5.5"),
        )

        assert theme.moral_complexity == Decimal("1.0")
        assert theme.emotional_resonance == Decimal("10.0")
        assert theme.universal_appeal == Decimal("5.5")

    @pytest.mark.unit
    def test_audience_relevance_boundary_validation(self):
        """Test audience relevance value validation."""
        with pytest.raises(
            ValueError, match="Audience relevance for 'teens' must be between 0 and 10"
        ):
            NarrativeTheme(
                theme_id="invalid-audience-test",
                theme_type=ThemeType.COMING_OF_AGE,
                intensity=ThemeIntensity.PROMINENT,
                name="Growing Up",
                description="Teenage struggles",
                target_audience_relevance={"teens": Decimal("-1.0")},
            )

        with pytest.raises(
            ValueError, match="Audience relevance for 'adults' must be between 0 and 10"
        ):
            NarrativeTheme(
                theme_id="invalid-audience-high-test",
                theme_type=ThemeType.COMING_OF_AGE,
                intensity=ThemeIntensity.PROMINENT,
                name="Growing Up",
                description="Teenage struggles",
                target_audience_relevance={"adults": Decimal("11.5")},
            )

    @pytest.mark.unit
    def test_valid_audience_relevance_boundaries(self):
        """Test that audience relevance boundaries (0 and 10) are valid."""
        theme = NarrativeTheme(
            theme_id="valid-audience-test",
            theme_type=ThemeType.TECHNOLOGICAL,
            intensity=ThemeIntensity.OVERWHELMING,
            name="Digital Dystopia",
            description="Technology controlling society",
            target_audience_relevance={
                "children": Decimal("0.0"),
                "tech_workers": Decimal("10.0"),
                "elderly": Decimal("3.5"),
            },
        )

        assert theme.target_audience_relevance["children"] == Decimal("0.0")
        assert theme.target_audience_relevance["tech_workers"] == Decimal("10.0")
        assert theme.target_audience_relevance["elderly"] == Decimal("3.5")

    @pytest.mark.unit
    def test_string_length_validations(self):
        """Test string length constraint validations."""
        # Theme ID too long
        with pytest.raises(
            ValueError, match="Theme ID too long \\(max 100 characters\\)"
        ):
            NarrativeTheme(
                theme_id="x" * 101,
                theme_type=ThemeType.UNIVERSAL,
                intensity=ThemeIntensity.MODERATE,
                name="Valid Name",
                description="Valid description",
            )

        # Name too long
        with pytest.raises(
            ValueError, match="Theme name too long \\(max 200 characters\\)"
        ):
            NarrativeTheme(
                theme_id="valid-id",
                theme_type=ThemeType.UNIVERSAL,
                intensity=ThemeIntensity.MODERATE,
                name="x" * 201,
                description="Valid description",
            )

        # Description too long
        with pytest.raises(
            ValueError, match="Theme description too long \\(max 1000 characters\\)"
        ):
            NarrativeTheme(
                theme_id="valid-id",
                theme_type=ThemeType.UNIVERSAL,
                intensity=ThemeIntensity.MODERATE,
                name="Valid Name",
                description="x" * 1001,
            )

    @pytest.mark.unit
    def test_valid_string_length_boundaries(self):
        """Test that maximum string length boundaries are valid."""
        theme = NarrativeTheme(
            theme_id="x" * 100,
            theme_type=ThemeType.MORAL,
            intensity=ThemeIntensity.CENTRAL,
            name="x" * 200,
            description="x" * 1000,
        )

        assert len(theme.theme_id) == 100
        assert len(theme.name) == 200
        assert len(theme.description) == 1000
