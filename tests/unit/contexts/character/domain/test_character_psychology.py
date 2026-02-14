#!/usr/bin/env python3
"""
Unit Tests for CharacterPsychology Value Object

These tests verify the Big Five personality model implementation,
including validation, trait level categorization, and helper methods.
"""

import pytest

from src.contexts.character.domain.value_objects.character_psychology import (
    CharacterPsychology,
)

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestCharacterPsychologyCreation:
    """Tests for CharacterPsychology instantiation and validation."""

    def test_create_valid_psychology(self):
        """Test creating a valid CharacterPsychology instance."""
        psychology = CharacterPsychology(
            openness=75,
            conscientiousness=60,
            extraversion=45,
            agreeableness=80,
            neuroticism=30,
        )

        assert psychology.openness == 75
        assert psychology.conscientiousness == 60
        assert psychology.extraversion == 45
        assert psychology.agreeableness == 80
        assert psychology.neuroticism == 30

    def test_create_balanced_psychology(self):
        """Test factory method for balanced personality."""
        psychology = CharacterPsychology.create_balanced()

        assert psychology.openness == 50
        assert psychology.conscientiousness == 50
        assert psychology.extraversion == 50
        assert psychology.agreeableness == 50
        assert psychology.neuroticism == 50

    def test_create_with_boundary_values(self):
        """Test creating psychology with minimum and maximum values."""
        min_psychology = CharacterPsychology(
            openness=0,
            conscientiousness=0,
            extraversion=0,
            agreeableness=0,
            neuroticism=0,
        )
        assert min_psychology.openness == 0

        max_psychology = CharacterPsychology(
            openness=100,
            conscientiousness=100,
            extraversion=100,
            agreeableness=100,
            neuroticism=100,
        )
        assert max_psychology.openness == 100

    def test_reject_negative_values(self):
        """Test that negative trait values are rejected."""
        with pytest.raises(ValueError, match="openness must be between 0 and 100"):
            CharacterPsychology(
                openness=-1,
                conscientiousness=50,
                extraversion=50,
                agreeableness=50,
                neuroticism=50,
            )

    def test_reject_values_over_100(self):
        """Test that trait values over 100 are rejected."""
        with pytest.raises(
            ValueError, match="conscientiousness must be between 0 and 100"
        ):
            CharacterPsychology(
                openness=50,
                conscientiousness=101,
                extraversion=50,
                agreeableness=50,
                neuroticism=50,
            )

    def test_reject_non_integer_values(self):
        """Test that non-integer trait values are rejected."""
        with pytest.raises(TypeError, match="openness must be an integer"):
            CharacterPsychology(
                openness=50.5,  # type: ignore
                conscientiousness=50,
                extraversion=50,
                agreeableness=50,
                neuroticism=50,
            )

    def test_psychology_is_frozen(self):
        """Test that CharacterPsychology is immutable."""
        psychology = CharacterPsychology.create_balanced()

        with pytest.raises(Exception):  # FrozenInstanceError
            psychology.openness = 75  # type: ignore


@pytest.mark.unit
class TestCharacterPsychologyTraitLevels:
    """Tests for trait level categorization."""

    def test_get_low_trait_level(self):
        """Test that scores 0-30 return 'low'."""
        psychology = CharacterPsychology(
            openness=0,
            conscientiousness=15,
            extraversion=30,
            agreeableness=50,
            neuroticism=50,
        )

        assert psychology.get_trait_level("openness") == "low"
        assert psychology.get_trait_level("conscientiousness") == "low"
        assert psychology.get_trait_level("extraversion") == "low"

    def test_get_average_trait_level(self):
        """Test that scores 31-70 return 'average'."""
        psychology = CharacterPsychology(
            openness=31,
            conscientiousness=50,
            extraversion=70,
            agreeableness=50,
            neuroticism=50,
        )

        assert psychology.get_trait_level("openness") == "average"
        assert psychology.get_trait_level("conscientiousness") == "average"
        assert psychology.get_trait_level("extraversion") == "average"

    def test_get_high_trait_level(self):
        """Test that scores 71-100 return 'high'."""
        psychology = CharacterPsychology(
            openness=71,
            conscientiousness=85,
            extraversion=100,
            agreeableness=50,
            neuroticism=50,
        )

        assert psychology.get_trait_level("openness") == "high"
        assert psychology.get_trait_level("conscientiousness") == "high"
        assert psychology.get_trait_level("extraversion") == "high"

    def test_get_invalid_trait_level(self):
        """Test that invalid trait names raise ValueError."""
        psychology = CharacterPsychology.create_balanced()

        with pytest.raises(ValueError, match="Invalid trait name"):
            psychology.get_trait_level("invalid_trait")


@pytest.mark.unit
class TestCharacterPsychologyDominantAndWeakTraits:
    """Tests for dominant and weak trait identification."""

    def test_get_dominant_traits(self):
        """Test identifying traits above the threshold."""
        psychology = CharacterPsychology(
            openness=80,
            conscientiousness=75,
            extraversion=50,
            agreeableness=90,
            neuroticism=20,
        )

        dominant = psychology.get_dominant_traits()

        assert "openness" in dominant
        assert "conscientiousness" in dominant
        assert "agreeableness" in dominant
        assert "extraversion" not in dominant
        assert "neuroticism" not in dominant

    def test_get_dominant_traits_custom_threshold(self):
        """Test dominant traits with custom threshold."""
        psychology = CharacterPsychology(
            openness=60,
            conscientiousness=55,
            extraversion=50,
            agreeableness=45,
            neuroticism=40,
        )

        dominant = psychology.get_dominant_traits(threshold=50)

        assert "openness" in dominant
        assert "conscientiousness" in dominant
        assert len(dominant) == 2

    def test_get_weak_traits(self):
        """Test identifying traits below the threshold."""
        psychology = CharacterPsychology(
            openness=80,
            conscientiousness=75,
            extraversion=25,
            agreeableness=90,
            neuroticism=10,
        )

        weak = psychology.get_weak_traits()

        assert "extraversion" in weak
        assert "neuroticism" in weak
        assert "openness" not in weak
        assert len(weak) == 2

    def test_get_weak_traits_custom_threshold(self):
        """Test weak traits with custom threshold."""
        psychology = CharacterPsychology(
            openness=45,
            conscientiousness=40,
            extraversion=50,
            agreeableness=55,
            neuroticism=60,
        )

        weak = psychology.get_weak_traits(threshold=50)

        assert "openness" in weak
        assert "conscientiousness" in weak
        assert len(weak) == 2


@pytest.mark.unit
class TestCharacterPsychologyConversion:
    """Tests for conversion and summary methods."""

    def test_to_dict(self):
        """Test converting psychology to dictionary."""
        psychology = CharacterPsychology(
            openness=75,
            conscientiousness=60,
            extraversion=45,
            agreeableness=80,
            neuroticism=30,
        )

        result = psychology.to_dict()

        assert result == {
            "openness": 75,
            "conscientiousness": 60,
            "extraversion": 45,
            "agreeableness": 80,
            "neuroticism": 30,
        }

    def test_get_personality_summary_with_dominant_and_weak(self):
        """Test summary with both dominant and weak traits."""
        psychology = CharacterPsychology(
            openness=80,
            conscientiousness=75,
            extraversion=20,
            agreeableness=50,
            neuroticism=10,
        )

        summary = psychology.get_personality_summary()

        assert "High in:" in summary
        assert "Low in:" in summary
        assert "openness" in summary
        assert "extraversion" in summary

    def test_get_personality_summary_balanced(self):
        """Test summary for balanced personality."""
        psychology = CharacterPsychology.create_balanced()

        summary = psychology.get_personality_summary()

        assert "Balanced personality" in summary
