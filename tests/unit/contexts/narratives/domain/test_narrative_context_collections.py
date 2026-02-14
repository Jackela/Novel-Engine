#!/usr/bin/env python3
"""
Unit Tests for NarrativeContext Collections and Comparison

Test suite covering NarrativeContext behavior in collections
(lists, sets, dicts), sorting, equality, and hashing.
"""

from decimal import Decimal

import pytest

from src.contexts.narratives.domain.value_objects.narrative_context import (
    ContextScope,
    ContextType,
    NarrativeContext,
)

pytestmark = pytest.mark.unit


class TestNarrativeContextCollectionsAndComparison:
    """Test suite for NarrativeContext behavior in collections and comparisons."""

    @pytest.mark.unit
    def test_contexts_in_list(self):
        """Test NarrativeContext objects in list operations."""
        context1 = NarrativeContext(
            context_id="list-test-1",
            context_type=ContextType.SETTING,
            scope=ContextScope.SCENE,
            name="First Context",
            description="First test context",
        )

        context2 = NarrativeContext(
            context_id="list-test-2",
            context_type=ContextType.EMOTIONAL,
            scope=ContextScope.CHAPTER,
            name="Second Context",
            description="Second test context",
        )

        context_list = [context1, context2]

        assert len(context_list) == 2
        assert context1 in context_list
        assert context2 in context_list

    @pytest.mark.unit
    def test_contexts_sorting_by_influence_strength(self):
        """Test sorting NarrativeContext objects by overall influence strength."""
        contexts = [
            NarrativeContext(
                context_id=f"sort-test-{i}",
                context_type=ContextType.THEMATIC,
                scope=scope,
                name=f"Context {i}",
                description=f"Context number {i}",
                narrative_importance=importance,
                visibility_level=visibility,
                mood_influences={
                    f"mood_{j}": Decimal("5.0") for j in range(mood_count)
                },
            )
            for i, (scope, importance, visibility, mood_count) in enumerate(
                [
                    (ContextScope.MOMENT, Decimal("3.0"), Decimal("4.0"), 1),
                    (ContextScope.GLOBAL, Decimal("9.0"), Decimal("8.0"), 5),
                    (ContextScope.SCENE, Decimal("5.0"), Decimal("6.0"), 2),
                    (ContextScope.ARC, Decimal("8.0"), Decimal("9.0"), 3),
                ]
            )
        ]

        sorted_contexts = sorted(
            contexts, key=lambda c: c.overall_influence_strength, reverse=True
        )

        # Highest influence should be first
        assert (
            sorted_contexts[0].overall_influence_strength
            >= sorted_contexts[1].overall_influence_strength
        )
        assert (
            sorted_contexts[1].overall_influence_strength
            >= sorted_contexts[2].overall_influence_strength
        )
        assert (
            sorted_contexts[2].overall_influence_strength
            >= sorted_contexts[3].overall_influence_strength
        )

    @pytest.mark.unit
    def test_context_equality_identity(self):
        """Test that identical NarrativeContext objects are considered equal."""
        context1 = NarrativeContext(
            context_id="equality-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.ARC,
            name="Equal Context",
            description="Testing equality",
        )

        context2 = NarrativeContext(
            context_id="equality-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.ARC,
            name="Equal Context",
            description="Testing equality",
        )

        # Frozen dataclasses with same values should be equal
        assert context1 == context2
        # But they should be different objects
        assert context1 is not context2

    @pytest.mark.unit
    def test_context_inequality(self):
        """Test that different NarrativeContext objects are not equal."""
        context1 = NarrativeContext(
            context_id="different-1",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.GLOBAL,
            name="First Context",
            description="First context description",
        )

        context2 = NarrativeContext(
            context_id="different-2",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.GLOBAL,
            name="Second Context",
            description="Second context description",
        )

        assert context1 != context2

    @pytest.mark.unit
    def test_context_hashing_consistency(self):
        """Test that equal NarrativeContext objects have same hash."""
        context1 = NarrativeContext(
            context_id="hash-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.CHAPTER,
            name="Hash Test Context",
            description="Testing hash consistency",
        )

        context2 = NarrativeContext(
            context_id="hash-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.CHAPTER,
            name="Hash Test Context",
            description="Testing hash consistency",
        )

        # Equal objects should have equal hashes
        assert context1 == context2
        assert hash(context1) == hash(context2)

    @pytest.mark.unit
    def test_contexts_in_set(self):
        """Test NarrativeContext objects in set operations."""
        context1 = NarrativeContext(
            context_id="set-test-1",
            context_type=ContextType.TECHNOLOGICAL,
            scope=ContextScope.ARC,
            name="Tech Context",
            description="Technology context",
        )

        context2 = NarrativeContext(
            context_id="set-test-2",
            context_type=ContextType.ENVIRONMENTAL,
            scope=ContextScope.GLOBAL,
            name="Environment Context",
            description="Environmental context",
        )

        # Identical context
        context1_duplicate = NarrativeContext(
            context_id="set-test-1",
            context_type=ContextType.TECHNOLOGICAL,
            scope=ContextScope.ARC,
            name="Tech Context",
            description="Technology context",
        )

        context_set = {context1, context2, context1_duplicate}

        # Set should deduplicate identical objects
        assert len(context_set) == 2  # context1 and context1_duplicate are the same
        assert context1 in context_set
        assert context2 in context_set
        assert context1_duplicate in context_set  # Should find context1

    @pytest.mark.unit
    def test_contexts_as_dict_keys(self):
        """Test using NarrativeContext objects as dictionary keys."""
        context1 = NarrativeContext(
            context_id="dict-key-1",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Historical Context",
            description="Important historical period",
        )

        context2 = NarrativeContext(
            context_id="dict-key-2",
            context_type=ContextType.SOCIAL,
            scope=ContextScope.ARC,
            name="Social Context",
            description="Social dynamics and relationships",
        )

        context_dict = {context1: "historical_data", context2: "social_data"}

        assert context_dict[context1] == "historical_data"
        assert context_dict[context2] == "social_data"

        # Test with equivalent context
        equivalent_context1 = NarrativeContext(
            context_id="dict-key-1",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Historical Context",
            description="Important historical period",
        )

        # Should find the same entry
        assert context_dict[equivalent_context1] == "historical_data"
