#!/usr/bin/env python3
"""
Unit Tests for NarrativeContext Properties

Test suite covering NarrativeContext computed properties,
state checks, and boolean accessor methods.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from src.contexts.narratives.domain.value_objects.narrative_context import (
    ContextScope,
    ContextType,
    NarrativeContext,
)

pytestmark = pytest.mark.unit


class TestNarrativeContextProperties:
    """Test suite for NarrativeContext property methods."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_sequence_range_with_from_sequence(self):
        """Test has_sequence_range returns True when from sequence is set."""
        context = NarrativeContext(
            context_id="from-seq-test",
            context_type=ContextType.THEMATIC,
            scope=ContextScope.ARC,
            name="From Sequence Test",
            description="Testing from sequence",
            applies_from_sequence=10,
        )

        assert context.has_sequence_range is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_sequence_range_with_to_sequence(self):
        """Test has_sequence_range returns True when to sequence is set."""
        context = NarrativeContext(
            context_id="to-seq-test",
            context_type=ContextType.INTERPERSONAL,
            scope=ContextScope.CHAPTER,
            name="To Sequence Test",
            description="Testing to sequence",
            applies_to_sequence=50,
        )

        assert context.has_sequence_range is True

    @pytest.mark.unit
    def test_has_sequence_range_with_both_sequences(self):
        """Test has_sequence_range returns True when both sequences are set."""
        context = NarrativeContext(
            context_id="both-seq-test",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.ARC,
            name="Both Sequences Test",
            description="Testing both sequences",
            applies_from_sequence=15,
            applies_to_sequence=45,
        )

        assert context.has_sequence_range is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_sequence_range_false(self):
        """Test has_sequence_range returns False when no sequences are set."""
        context = NarrativeContext(
            context_id="no-seq-test",
            context_type=ContextType.SETTING,
            scope=ContextScope.GLOBAL,
            name="No Sequence Test",
            description="Testing no sequences",
        )

        assert context.has_sequence_range is False

    @pytest.mark.unit
    def test_is_temporal_context_true(self):
        """Test is_temporal_context returns True when not persistent and has sequence range."""
        context = NarrativeContext(
            context_id="temporal-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.CHAPTER,
            name="Temporal Context",
            description="Testing temporal context",
            is_persistent=False,
            applies_from_sequence=20,
            applies_to_sequence=30,
        )

        assert context.is_temporal_context is True

    @pytest.mark.unit
    def test_is_temporal_context_false_persistent(self):
        """Test is_temporal_context returns False when persistent even with sequence range."""
        context = NarrativeContext(
            context_id="persistent-test",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Persistent Context",
            description="Testing persistent context",
            is_persistent=True,
            applies_from_sequence=5,
            applies_to_sequence=100,
        )

        assert context.is_temporal_context is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_temporal_context_false_no_range(self):
        """Test is_temporal_context returns False when no sequence range."""
        context = NarrativeContext(
            context_id="no-range-test",
            context_type=ContextType.SOCIAL,
            scope=ContextScope.ARC,
            name="No Range Context",
            description="Testing no range context",
            is_persistent=False,
        )

        assert context.is_temporal_context is False

    @pytest.mark.unit
    def test_affects_characters_true(self):
        """Test affects_characters returns True when characters are affected."""
        char_id = uuid4()

        context = NarrativeContext(
            context_id="char-affects-test",
            context_type=ContextType.EMOTIONAL,
            scope=ContextScope.SCENE,
            name="Character Affects Test",
            description="Testing character affects",
            affected_characters={char_id},
        )

        assert context.affects_characters is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_affects_characters_false(self):
        """Test affects_characters returns False when no characters are affected."""
        context = NarrativeContext(
            context_id="no-char-affects-test",
            context_type=ContextType.ENVIRONMENTAL,
            scope=ContextScope.GLOBAL,
            name="No Character Affects Test",
            description="Testing no character affects",
        )

        assert context.affects_characters is False

    @pytest.mark.unit
    def test_has_hidden_information_true(self):
        """Test has_hidden_information returns True when hidden information exists."""
        context = NarrativeContext(
            context_id="hidden-info-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.ARC,
            name="Hidden Info Test",
            description="Testing hidden information",
            hidden_information=[
                "Secret magical ward protects the castle",
                "Ancient curse affects the land",
            ],
        )

        assert context.has_hidden_information is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_hidden_information_false(self):
        """Test has_hidden_information returns False when no hidden information exists."""
        context = NarrativeContext(
            context_id="no-hidden-info-test",
            context_type=ContextType.TECHNOLOGICAL,
            scope=ContextScope.CHAPTER,
            name="No Hidden Info Test",
            description="Testing no hidden information",
        )

        assert context.has_hidden_information is False

    @pytest.mark.unit
    def test_has_narrative_constraints_true(self):
        """Test has_narrative_constraints returns True when constraints exist."""
        context = NarrativeContext(
            context_id="constraints-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.ARC,
            name="Constraints Test",
            description="Testing narrative constraints",
            narrative_constraints=[
                "No magic can be used",
                "Characters must remain in city",
            ],
        )

        assert context.has_narrative_constraints is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_narrative_constraints_false(self):
        """Test has_narrative_constraints returns False when no constraints exist."""
        context = NarrativeContext(
            context_id="no-constraints-test",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.SCENE,
            name="No Constraints Test",
            description="Testing no constraints",
        )

        assert context.has_narrative_constraints is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_influences_mood_true(self):
        """Test influences_mood returns True when mood influences exist."""
        context = NarrativeContext(
            context_id="mood-influence-test",
            context_type=ContextType.EMOTIONAL,
            scope=ContextScope.SCENE,
            name="Mood Influence Test",
            description="Testing mood influence",
            mood_influences={"melancholy": Decimal("6.0"), "hope": Decimal("-3.0")},
        )

        assert context.influences_mood is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_influences_mood_false(self):
        """Test influences_mood returns False when no mood influences exist."""
        context = NarrativeContext(
            context_id="no-mood-influence-test",
            context_type=ContextType.ECONOMIC,
            scope=ContextScope.GLOBAL,
            name="No Mood Influence Test",
            description="Testing no mood influence",
        )

        assert context.influences_mood is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_influences_pacing_true(self):
        """Test influences_pacing returns True when pacing effects exist."""
        context = NarrativeContext(
            context_id="pacing-influence-test",
            context_type=ContextType.THEMATIC,
            scope=ContextScope.ARC,
            name="Pacing Influence Test",
            description="Testing pacing influence",
            pacing_effects={"urgency": Decimal("4.5"), "contemplation": Decimal("2.0")},
        )

        assert context.influences_pacing is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_influences_pacing_false(self):
        """Test influences_pacing returns False when no pacing effects exist."""
        context = NarrativeContext(
            context_id="no-pacing-influence-test",
            context_type=ContextType.SETTING,
            scope=ContextScope.SCENE,
            name="No Pacing Influence Test",
            description="Testing no pacing influence",
        )

        assert context.influences_pacing is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_prerequisites_true(self):
        """Test has_prerequisites returns True when prerequisite contexts exist."""
        context = NarrativeContext(
            context_id="prerequisites-test",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.ARC,
            name="Prerequisites Test",
            description="Testing prerequisites",
            prerequisite_contexts={"ancient_prophecy", "hero_training"},
        )

        assert context.has_prerequisites is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_prerequisites_false(self):
        """Test has_prerequisites returns False when no prerequisite contexts exist."""
        context = NarrativeContext(
            context_id="no-prerequisites-test",
            context_type=ContextType.INTERPERSONAL,
            scope=ContextScope.SCENE,
            name="No Prerequisites Test",
            description="Testing no prerequisites",
        )

        assert context.has_prerequisites is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_conflicts_true(self):
        """Test has_conflicts returns True when conflicting contexts exist."""
        context = NarrativeContext(
            context_id="conflicts-test",
            context_type=ContextType.SOCIAL,
            scope=ContextScope.CHAPTER,
            name="Conflicts Test",
            description="Testing conflicts",
            conflicting_contexts={"peaceful_times", "celebration_mood"},
        )

        assert context.has_conflicts is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_conflicts_false(self):
        """Test has_conflicts returns False when no conflicting contexts exist."""
        context = NarrativeContext(
            context_id="no-conflicts-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.MOMENT,
            name="No Conflicts Test",
            description="Testing no conflicts",
        )

        assert context.has_conflicts is False
