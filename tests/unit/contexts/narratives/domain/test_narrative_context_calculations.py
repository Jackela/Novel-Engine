#!/usr/bin/env python3
"""
Unit Tests for NarrativeContext Calculations

Test suite covering NarrativeContext calculated metrics:
overall influence strength and contextual complexity score.
"""

from decimal import Decimal

import pytest

from src.contexts.narratives.domain.value_objects.narrative_context import (
    ContextScope,
    ContextType,
    NarrativeContext,
)

pytestmark = pytest.mark.unit


class TestOverallInfluenceStrength:
    """Test suite for overall influence strength calculation."""

    @pytest.mark.unit
    def test_influence_strength_base_calculation(self):
        """Test influence strength with base values only."""
        context = NarrativeContext(
            context_id="base-strength-test",
            context_type=ContextType.SETTING,
            scope=ContextScope.SCENE,
            name="Base Strength Test",
            description="Testing base influence strength",
            narrative_importance=Decimal("6.0"),
            visibility_level=Decimal("8.0"),
        )

        # Expected: (6.0 * 8.0) / 10.0 + 0 = 4.8
        assert context.overall_influence_strength == Decimal("4.8")

    @pytest.mark.unit
    def test_influence_strength_with_influences(self):
        """Test influence strength with various influences."""
        context = NarrativeContext(
            context_id="influences-strength-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.ARC,
            name="Influences Strength Test",
            description="Testing influence strength with influences",
            narrative_importance=Decimal("8.0"),
            visibility_level=Decimal("7.0"),
            mood_influences={"tension": Decimal("5.0"), "fear": Decimal("3.0")},
            tension_modifiers={"political": Decimal("6.0")},
            pacing_effects={"urgency": Decimal("4.0"), "deliberation": Decimal("-2.0")},
            behavioral_influences=["increased_caution", "group_solidarity"],
            narrative_constraints=[
                "limited_travel",
                "monitored_communication",
                "resource_scarcity",
            ],
        )

        # Base: (8.0 * 7.0) / 10.0 = 5.6
        # Influences: 2 mood + 1 tension + 2 pacing + 2 behavioral + 3 constraints = 10 total
        # Bonus: min(3, 10 * 0.2) = min(3, 2.0) = 2.0
        # Total: min(10, 5.6 + 2.0) = min(10, 7.6) = 7.6
        assert context.overall_influence_strength == Decimal("7.6")

    @pytest.mark.unit
    def test_influence_strength_capped_at_ten(self):
        """Test that influence strength is capped at 10."""
        context = NarrativeContext(
            context_id="max-strength-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.GLOBAL,
            name="Maximum Strength Test",
            description="Testing maximum influence strength",
            narrative_importance=Decimal("10.0"),
            visibility_level=Decimal("10.0"),
            mood_influences={f"mood_{i}": Decimal("5.0") for i in range(10)},
            tension_modifiers={f"tension_{i}": Decimal("3.0") for i in range(10)},
            pacing_effects={f"pacing_{i}": Decimal("2.0") for i in range(10)},
            behavioral_influences=[f"behavior_{i}" for i in range(20)],
            narrative_constraints=[f"constraint_{i}" for i in range(20)],
        )

        # Base: (10.0 * 10.0) / 10.0 = 10.0
        # Influences: 10 + 10 + 10 + 20 + 20 = 70 total
        # Bonus: min(3, 70 * 0.2) = min(3, 14.0) = 3.0
        # Total: min(10, 10.0 + 3.0) = 10.0 (capped)
        assert context.overall_influence_strength == Decimal("10.0")

    @pytest.mark.unit
    def test_influence_strength_bonus_capped(self):
        """Test that influence bonus is capped at 3."""
        context = NarrativeContext(
            context_id="bonus-cap-test",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.ARC,
            name="Bonus Cap Test",
            description="Testing bonus cap",
            narrative_importance=Decimal("5.0"),
            visibility_level=Decimal("4.0"),
            behavioral_influences=[f"influence_{i}" for i in range(20)],
        )

        # Base: (5.0 * 4.0) / 10.0 = 2.0
        # Influences: 20 total
        # Bonus: min(3, 20 * 0.2) = min(3, 4.0) = 3.0 (capped)
        # Total: min(10, 2.0 + 3.0) = 5.0
        assert context.overall_influence_strength == Decimal("5.0")


class TestContextualComplexityScore:
    """Test suite for contextual complexity score calculation."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_complexity_score_base_only(self):
        """Test complexity score with only base complexity level."""
        context = NarrativeContext(
            context_id="base-complexity-test",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Base Complexity Test",
            description="Testing base complexity",
            complexity_level=Decimal("6.0"),
        )

        # Expected: 6.0 + 0 + 0 = 6.0
        assert context.contextual_complexity_score == Decimal("6.0")

    @pytest.mark.unit
    def test_complexity_score_with_relationships(self):
        """Test complexity score with context relationships."""
        context = NarrativeContext(
            context_id="relationships-complexity-test",
            context_type=ContextType.SOCIAL,
            scope=ContextScope.ARC,
            name="Relationships Complexity Test",
            description="Testing relationship complexity",
            complexity_level=Decimal("4.0"),
            prerequisite_contexts={"context1", "context2"},
            conflicting_contexts={"context3"},
            reinforcing_contexts={"context4", "context5", "context6"},
        )

        # Base: 4.0
        # Relationships: (2 + 1 + 3) * 0.3 = 6 * 0.3 = 1.8
        # Information: 0
        # Total: 4.0 + 1.8 + 0 = 5.8
        assert context.contextual_complexity_score == Decimal("5.8")

    @pytest.mark.unit
    def test_complexity_score_with_information_layers(self):
        """Test complexity score with information layer complexity."""
        context = NarrativeContext(
            context_id="information-complexity-test",
            context_type=ContextType.THEMATIC,
            scope=ContextScope.CHAPTER,
            name="Information Complexity Test",
            description="Testing information complexity",
            complexity_level=Decimal("5.0"),
            key_facts=["fact1", "fact2", "fact3", "fact4"],
            implicit_knowledge=["implicit1", "implicit2"],
            hidden_information=["hidden1", "hidden2", "hidden3"],
        )

        # Base: 5.0
        # Relationships: 0
        # Information: (4 + 2 + 3) * 0.1 = 9 * 0.1 = 0.9
        # Total: 5.0 + 0 + 0.9 = 5.9
        assert context.contextual_complexity_score == Decimal("5.9")

    @pytest.mark.unit
    def test_complexity_score_comprehensive(self):
        """Test complexity score with all components."""
        context = NarrativeContext(
            context_id="comprehensive-complexity-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.GLOBAL,
            name="Comprehensive Complexity Test",
            description="Testing comprehensive complexity",
            complexity_level=Decimal("7.0"),
            prerequisite_contexts={"prereq1", "prereq2"},
            conflicting_contexts={"conflict1", "conflict2", "conflict3"},
            reinforcing_contexts={"reinforce1"},
            key_facts=["fact1", "fact2", "fact3"],
            implicit_knowledge=["implicit1", "implicit2", "implicit3", "implicit4"],
            hidden_information=["hidden1", "hidden2"],
        )

        # Base: 7.0
        # Relationships: (2 + 3 + 1) * 0.3 = 6 * 0.3 = 1.8
        # Information: (3 + 4 + 2) * 0.1 = 9 * 0.1 = 0.9
        # Total: 7.0 + 1.8 + 0.9 = 9.7
        assert context.contextual_complexity_score == Decimal("9.7")

    @pytest.mark.unit
    def test_complexity_score_capped_at_ten(self):
        """Test that complexity score is capped at 10."""
        context = NarrativeContext(
            context_id="max-complexity-test",
            context_type=ContextType.INTERPERSONAL,
            scope=ContextScope.ARC,
            name="Maximum Complexity Test",
            description="Testing maximum complexity",
            complexity_level=Decimal("9.0"),
            prerequisite_contexts={f"prereq_{i}" for i in range(10)},
            conflicting_contexts={f"conflict_{i}" for i in range(10)},
            reinforcing_contexts={f"reinforce_{i}" for i in range(10)},
            key_facts=[f"fact_{i}" for i in range(20)],
            implicit_knowledge=[f"implicit_{i}" for i in range(20)],
            hidden_information=[f"hidden_{i}" for i in range(20)],
        )

        # Base: 9.0
        # Relationships: (10 + 10 + 10) * 0.3 = 30 * 0.3 = 9.0
        # Information: (20 + 20 + 20) * 0.1 = 60 * 0.1 = 6.0
        # Total: min(10, 9.0 + 9.0 + 6.0) = min(10, 24.0) = 10.0
        assert context.contextual_complexity_score == Decimal("10.0")
