#!/usr/bin/env python3
"""
Unit Tests for NarrativeContext Validation

Test suite covering NarrativeContext input validation,
boundary conditions, and constraint enforcement.
"""

from decimal import Decimal

import pytest

from src.contexts.narratives.domain.value_objects.narrative_context import (
    ContextScope,
    ContextType,
    NarrativeContext,
)

pytestmark = pytest.mark.unit


class TestNarrativeContextValidation:
    """Test suite for NarrativeContext validation logic."""

    @pytest.mark.unit
    def test_empty_context_id_validation(self):
        """Test validation fails with empty context ID."""
        with pytest.raises(ValueError, match="Context ID cannot be empty"):
            NarrativeContext(
                context_id="",
                context_type=ContextType.SETTING,
                scope=ContextScope.SCENE,
                name="Valid Name",
                description="Valid description",
            )

    @pytest.mark.unit
    def test_whitespace_only_context_id_validation(self):
        """Test validation fails with whitespace-only context ID."""
        with pytest.raises(ValueError, match="Context ID cannot be empty"):
            NarrativeContext(
                context_id="   ",
                context_type=ContextType.SETTING,
                scope=ContextScope.SCENE,
                name="Valid Name",
                description="Valid description",
            )

    @pytest.mark.unit
    def test_empty_name_validation(self):
        """Test validation fails with empty name."""
        with pytest.raises(ValueError, match="Context name cannot be empty"):
            NarrativeContext(
                context_id="valid-id",
                context_type=ContextType.HISTORICAL,
                scope=ContextScope.ARC,
                name="",
                description="Valid description",
            )

    @pytest.mark.unit
    def test_whitespace_only_name_validation(self):
        """Test validation fails with whitespace-only name."""
        with pytest.raises(ValueError, match="Context name cannot be empty"):
            NarrativeContext(
                context_id="valid-id",
                context_type=ContextType.HISTORICAL,
                scope=ContextScope.ARC,
                name="   ",
                description="Valid description",
            )

    @pytest.mark.unit
    def test_empty_description_validation(self):
        """Test validation fails with empty description."""
        with pytest.raises(ValueError, match="Context description cannot be empty"):
            NarrativeContext(
                context_id="valid-id",
                context_type=ContextType.SOCIAL,
                scope=ContextScope.GLOBAL,
                name="Valid Name",
                description="",
            )

    @pytest.mark.unit
    def test_whitespace_only_description_validation(self):
        """Test validation fails with whitespace-only description."""
        with pytest.raises(ValueError, match="Context description cannot be empty"):
            NarrativeContext(
                context_id="valid-id",
                context_type=ContextType.SOCIAL,
                scope=ContextScope.GLOBAL,
                name="Valid Name",
                description="   \t\n  ",
            )

    @pytest.mark.unit
    def test_invalid_sequence_range_validation(self):
        """Test validation fails when from sequence is after to sequence."""
        with pytest.raises(
            ValueError, match="From sequence must be before or equal to to sequence"
        ):
            NarrativeContext(
                context_id="invalid-range-test",
                context_type=ContextType.THEMATIC,
                scope=ContextScope.ARC,
                name="Invalid Range",
                description="Testing invalid sequence range",
                applies_from_sequence=50,
                applies_to_sequence=25,
            )

    @pytest.mark.unit
    def test_valid_sequence_range_equal_values(self):
        """Test that equal from and to sequence values are valid."""
        context = NarrativeContext(
            context_id="equal-sequence-test",
            context_type=ContextType.INTERPERSONAL,
            scope=ContextScope.SCENE,
            name="Equal Sequence",
            description="Testing equal sequence values",
            applies_from_sequence=30,
            applies_to_sequence=30,
        )

        assert context.applies_from_sequence == 30
        assert context.applies_to_sequence == 30

    @pytest.mark.unit
    def test_valid_sequence_range_proper_order(self):
        """Test that proper sequence order is valid."""
        context = NarrativeContext(
            context_id="valid-range-test",
            context_type=ContextType.ENVIRONMENTAL,
            scope=ContextScope.CHAPTER,
            name="Valid Range",
            description="Testing valid sequence range",
            applies_from_sequence=10,
            applies_to_sequence=20,
        )

        assert context.applies_from_sequence == 10
        assert context.applies_to_sequence == 20

    @pytest.mark.unit
    def test_narrative_importance_below_minimum_validation(self):
        """Test validation fails with narrative importance below 1."""
        with pytest.raises(
            ValueError, match="narrative_importance must be between 1 and 10"
        ):
            NarrativeContext(
                context_id="low-importance-test",
                context_type=ContextType.MAGICAL,
                scope=ContextScope.ARC,
                name="Low Importance",
                description="Testing low importance",
                narrative_importance=Decimal("0.5"),
            )

    @pytest.mark.unit
    def test_narrative_importance_above_maximum_validation(self):
        """Test validation fails with narrative importance above 10."""
        with pytest.raises(
            ValueError, match="narrative_importance must be between 1 and 10"
        ):
            NarrativeContext(
                context_id="high-importance-test",
                context_type=ContextType.MAGICAL,
                scope=ContextScope.ARC,
                name="High Importance",
                description="Testing high importance",
                narrative_importance=Decimal("11.0"),
            )

    @pytest.mark.unit
    def test_visibility_level_boundary_validation(self):
        """Test visibility level boundary validation."""
        with pytest.raises(
            ValueError, match="visibility_level must be between 1 and 10"
        ):
            NarrativeContext(
                context_id="low-visibility-test",
                context_type=ContextType.TECHNOLOGICAL,
                scope=ContextScope.GLOBAL,
                name="Low Visibility",
                description="Testing low visibility",
                visibility_level=Decimal("0.9"),
            )

        with pytest.raises(
            ValueError, match="visibility_level must be between 1 and 10"
        ):
            NarrativeContext(
                context_id="high-visibility-test",
                context_type=ContextType.TECHNOLOGICAL,
                scope=ContextScope.GLOBAL,
                name="High Visibility",
                description="Testing high visibility",
                visibility_level=Decimal("10.1"),
            )

    @pytest.mark.unit
    def test_complexity_level_boundary_validation(self):
        """Test complexity level boundary validation."""
        with pytest.raises(
            ValueError, match="complexity_level must be between 1 and 10"
        ):
            NarrativeContext(
                context_id="low-complexity-test",
                context_type=ContextType.ECONOMIC,
                scope=ContextScope.ARC,
                name="Low Complexity",
                description="Testing low complexity",
                complexity_level=Decimal("0.5"),
            )

        with pytest.raises(
            ValueError, match="complexity_level must be between 1 and 10"
        ):
            NarrativeContext(
                context_id="high-complexity-test",
                context_type=ContextType.ECONOMIC,
                scope=ContextScope.ARC,
                name="High Complexity",
                description="Testing high complexity",
                complexity_level=Decimal("15.0"),
            )

    @pytest.mark.unit
    def test_valid_decimal_boundary_values(self):
        """Test that boundary decimal values are valid."""
        context = NarrativeContext(
            context_id="boundary-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.GLOBAL,
            name="Boundary Test",
            description="Testing boundary values",
            narrative_importance=Decimal("1.0"),
            visibility_level=Decimal("10.0"),
            complexity_level=Decimal("5.5"),
        )

        assert context.narrative_importance == Decimal("1.0")
        assert context.visibility_level == Decimal("10.0")
        assert context.complexity_level == Decimal("5.5")

    @pytest.mark.unit
    def test_evolution_rate_below_minimum_validation(self):
        """Test validation fails with evolution rate below 0."""
        with pytest.raises(ValueError, match="evolution_rate must be between 0 and 1"):
            NarrativeContext(
                context_id="low-evolution-test",
                context_type=ContextType.CULTURAL,
                scope=ContextScope.ARC,
                name="Low Evolution",
                description="Testing low evolution rate",
                evolution_rate=Decimal("-0.1"),
            )

    @pytest.mark.unit
    def test_evolution_rate_above_maximum_validation(self):
        """Test validation fails with evolution rate above 1."""
        with pytest.raises(ValueError, match="evolution_rate must be between 0 and 1"):
            NarrativeContext(
                context_id="high-evolution-test",
                context_type=ContextType.CULTURAL,
                scope=ContextScope.ARC,
                name="High Evolution",
                description="Testing high evolution rate",
                evolution_rate=Decimal("1.1"),
            )

    @pytest.mark.unit
    def test_stability_boundary_validation(self):
        """Test stability boundary validation."""
        with pytest.raises(ValueError, match="stability must be between 0 and 1"):
            NarrativeContext(
                context_id="low-stability-test",
                context_type=ContextType.SOCIAL,
                scope=ContextScope.CHAPTER,
                name="Low Stability",
                description="Testing low stability",
                stability=Decimal("-0.2"),
            )

        with pytest.raises(ValueError, match="stability must be between 0 and 1"):
            NarrativeContext(
                context_id="high-stability-test",
                context_type=ContextType.SOCIAL,
                scope=ContextScope.CHAPTER,
                name="High Stability",
                description="Testing high stability",
                stability=Decimal("1.5"),
            )

    @pytest.mark.unit
    def test_valid_rate_boundary_values(self):
        """Test that boundary rate values (0 and 1) are valid."""
        context = NarrativeContext(
            context_id="boundary-rates-test",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Boundary Rates",
            description="Testing rate boundaries",
            evolution_rate=Decimal("0.0"),
            stability=Decimal("1.0"),
        )

        assert context.evolution_rate == Decimal("0.0")
        assert context.stability == Decimal("1.0")

    @pytest.mark.unit
    def test_influence_values_below_minimum_validation(self):
        """Test validation fails with influence values below -10."""
        with pytest.raises(
            ValueError, match="Influence values must be between -10 and 10"
        ):
            NarrativeContext(
                context_id="low-mood-influence-test",
                context_type=ContextType.EMOTIONAL,
                scope=ContextScope.SCENE,
                name="Low Mood Influence",
                description="Testing low mood influence",
                mood_influences={"fear": Decimal("-11.0")},
            )

    @pytest.mark.unit
    def test_influence_values_above_maximum_validation(self):
        """Test validation fails with influence values above 10."""
        with pytest.raises(
            ValueError, match="Influence values must be between -10 and 10"
        ):
            NarrativeContext(
                context_id="high-tension-modifier-test",
                context_type=ContextType.INTERPERSONAL,
                scope=ContextScope.SCENE,
                name="High Tension Modifier",
                description="Testing high tension modifier",
                tension_modifiers={"conflict": Decimal("15.0")},
            )

    @pytest.mark.unit
    def test_pacing_effects_boundary_validation(self):
        """Test pacing effects boundary validation."""
        with pytest.raises(
            ValueError, match="Influence values must be between -10 and 10"
        ):
            NarrativeContext(
                context_id="invalid-pacing-test",
                context_type=ContextType.THEMATIC,
                scope=ContextScope.ARC,
                name="Invalid Pacing",
                description="Testing invalid pacing effects",
                pacing_effects={"urgency": Decimal("-12.0")},
            )

    @pytest.mark.unit
    def test_valid_influence_boundary_values(self):
        """Test that boundary influence values (-10 and 10) are valid."""
        context = NarrativeContext(
            context_id="boundary-influences-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.GLOBAL,
            name="Boundary Influences",
            description="Testing influence boundaries",
            mood_influences={"wonder": Decimal("10.0"), "fear": Decimal("-10.0")},
            tension_modifiers={"magical": Decimal("5.0")},
            pacing_effects={"acceleration": Decimal("-8.5")},
        )

        assert context.mood_influences["wonder"] == Decimal("10.0")
        assert context.mood_influences["fear"] == Decimal("-10.0")
        assert context.tension_modifiers["magical"] == Decimal("5.0")
        assert context.pacing_effects["acceleration"] == Decimal("-8.5")

    @pytest.mark.unit
    def test_string_length_validations(self):
        """Test string length constraint validations."""
        # Context ID too long
        with pytest.raises(
            ValueError, match="Context ID too long \\(max 100 characters\\)"
        ):
            NarrativeContext(
                context_id="x" * 101,
                context_type=ContextType.SETTING,
                scope=ContextScope.SCENE,
                name="Valid Name",
                description="Valid description",
            )

        # Name too long
        with pytest.raises(
            ValueError, match="Context name too long \\(max 200 characters\\)"
        ):
            NarrativeContext(
                context_id="valid-id",
                context_type=ContextType.SETTING,
                scope=ContextScope.SCENE,
                name="x" * 201,
                description="Valid description",
            )

        # Description too long
        with pytest.raises(
            ValueError, match="Context description too long \\(max 2000 characters\\)"
        ):
            NarrativeContext(
                context_id="valid-id",
                context_type=ContextType.SETTING,
                scope=ContextScope.SCENE,
                name="Valid Name",
                description="x" * 2001,
            )

    @pytest.mark.unit
    def test_valid_string_length_boundaries(self):
        """Test that maximum string length boundaries are valid."""
        context = NarrativeContext(
            context_id="x" * 100,
            context_type=ContextType.ENVIRONMENTAL,
            scope=ContextScope.GLOBAL,
            name="x" * 200,
            description="x" * 2000,
        )

        assert len(context.context_id) == 100
        assert len(context.name) == 200
        assert len(context.description) == 2000
