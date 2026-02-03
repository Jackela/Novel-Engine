#!/usr/bin/env python3
"""
Unit Tests for NarrativeContext String Representation

Test suite covering __str__ and __repr__ methods
for NarrativeContext objects.
"""

import pytest

from src.contexts.narratives.domain.value_objects.narrative_context import (
    ContextScope,
    ContextType,
    NarrativeContext,
)


class TestNarrativeContextStringRepresentation:
    """Test suite for NarrativeContext string representation methods."""

    @pytest.mark.unit
    def test_str_representation(self):
        """Test human-readable string representation."""
        context = NarrativeContext(
            context_id="str-test",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Renaissance Period",
            description="A time of cultural and intellectual flowering",
        )

        str_repr = str(context)
        expected = "NarrativeContext('Renaissance Period', historical, global)"
        assert str_repr == expected

    @pytest.mark.unit
    def test_repr_representation(self):
        """Test developer representation for debugging."""
        context = NarrativeContext(
            context_id="repr-test-id",
            context_type=ContextType.TECHNOLOGICAL,
            scope=ContextScope.ARC,
            name="Steampunk Era",
            description="Age of steam-powered technology",
        )

        repr_str = repr(context)
        expected = (
            "NarrativeContext(id='repr-test-id', "
            "type=technological, "
            "scope=arc, "
            "name='Steampunk Era')"
        )
        assert repr_str == expected

    @pytest.mark.unit
    def test_string_representations_different(self):
        """Test that str and repr provide different information."""
        context = NarrativeContext(
            context_id="different-repr-test",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.CHAPTER,
            name="Festival Season",
            description="Time of celebration and cultural expression",
        )

        str_repr = str(context)
        repr_str = repr(context)

        # They should be different
        assert str_repr != repr_str
        # str should be more human-readable
        assert "Festival Season" in str_repr
        # repr should include more technical details
        assert "different-repr-test" in repr_str
        assert "cultural" in repr_str
