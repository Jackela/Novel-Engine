#!/usr/bin/env python3
"""
Unit Tests for NarrativeContext Instance Methods

Test suite covering NarrativeContext behavioral methods
including sequence applicability, character interactions,
context relationships, and influence retrieval.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from src.contexts.narratives.domain.value_objects.narrative_context import (
    ContextScope,
    ContextType,
    NarrativeContext,
)


class TestNarrativeContextInstanceMethods:
    """Test suite for NarrativeContext instance methods."""

    @pytest.mark.unit
    def test_applies_at_sequence_persistent_no_range(self):
        """Test applies_at_sequence for persistent context with no range."""
        context = NarrativeContext(
            context_id="persistent-no-range-test",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.GLOBAL,
            name="Persistent No Range",
            description="Testing persistent context without range",
            is_persistent=True,
        )

        # Should apply at any sequence for persistent contexts without range
        assert context.applies_at_sequence(1) is True
        assert context.applies_at_sequence(50) is True
        assert context.applies_at_sequence(100) is True

    @pytest.mark.unit
    def test_applies_at_sequence_non_persistent_no_range(self):
        """Test applies_at_sequence for non-persistent context with no range."""
        context = NarrativeContext(
            context_id="non-persistent-no-range-test",
            context_type=ContextType.EMOTIONAL,
            scope=ContextScope.SCENE,
            name="Non-Persistent No Range",
            description="Testing non-persistent context without range",
            is_persistent=False,
        )

        # Should not apply at any sequence for non-persistent contexts without range
        assert context.applies_at_sequence(1) is False
        assert context.applies_at_sequence(25) is False
        assert context.applies_at_sequence(100) is False

    @pytest.mark.unit
    def test_applies_at_sequence_with_range(self):
        """Test applies_at_sequence with defined sequence range."""
        context = NarrativeContext(
            context_id="range-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.ARC,
            name="Range Test",
            description="Testing sequence range",
            applies_from_sequence=20,
            applies_to_sequence=40,
        )

        # Should not apply before range
        assert context.applies_at_sequence(10) is False
        assert context.applies_at_sequence(19) is False

        # Should apply within range
        assert context.applies_at_sequence(20) is True
        assert context.applies_at_sequence(30) is True
        assert context.applies_at_sequence(40) is True

        # Should not apply after range
        assert context.applies_at_sequence(41) is False
        assert context.applies_at_sequence(50) is False

    @pytest.mark.unit
    def test_applies_at_sequence_from_only(self):
        """Test applies_at_sequence with only from sequence defined."""
        context = NarrativeContext(
            context_id="from-only-test",
            context_type=ContextType.TECHNOLOGICAL,
            scope=ContextScope.ARC,
            name="From Only Test",
            description="Testing from sequence only",
            applies_from_sequence=30,
        )

        # Should not apply before from sequence
        assert context.applies_at_sequence(20) is False
        assert context.applies_at_sequence(29) is False

        # Should apply from sequence onwards
        assert context.applies_at_sequence(30) is True
        assert context.applies_at_sequence(50) is True
        assert context.applies_at_sequence(100) is True

    @pytest.mark.unit
    def test_applies_at_sequence_to_only(self):
        """Test applies_at_sequence with only to sequence defined."""
        context = NarrativeContext(
            context_id="to-only-test",
            context_type=ContextType.ENVIRONMENTAL,
            scope=ContextScope.CHAPTER,
            name="To Only Test",
            description="Testing to sequence only",
            applies_to_sequence=50,
        )

        # Should apply up to and including to sequence
        assert context.applies_at_sequence(1) is True
        assert context.applies_at_sequence(25) is True
        assert context.applies_at_sequence(50) is True

        # Should not apply after to sequence
        assert context.applies_at_sequence(51) is False
        assert context.applies_at_sequence(75) is False

    @pytest.mark.unit
    def test_affects_character_true(self):
        """Test affects_character returns True for affected character."""
        char_id1 = uuid4()
        char_id2 = uuid4()
        char_id3 = uuid4()

        context = NarrativeContext(
            context_id="char-affects-test",
            context_type=ContextType.INTERPERSONAL,
            scope=ContextScope.SCENE,
            name="Character Affects Test",
            description="Testing character affects",
            affected_characters={char_id1, char_id2},
        )

        assert context.affects_character(char_id1) is True
        assert context.affects_character(char_id2) is True
        assert context.affects_character(char_id3) is False

    @pytest.mark.unit
    def test_character_knows_context_true(self):
        """Test character_knows_context returns True for required character."""
        char_id1 = uuid4()
        char_id2 = uuid4()
        char_id3 = uuid4()

        context = NarrativeContext(
            context_id="char-knowledge-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.ARC,
            name="Character Knowledge Test",
            description="Testing character knowledge",
            character_knowledge_required={char_id1, char_id2},
        )

        assert context.character_knows_context(char_id1) is True
        assert context.character_knows_context(char_id2) is True
        assert context.character_knows_context(char_id3) is False

    @pytest.mark.unit
    def test_get_character_reaction_existing(self):
        """Test get_character_reaction returns reaction for existing character."""
        char_id1 = uuid4()
        char_id2 = uuid4()
        char_id3 = uuid4()

        context = NarrativeContext(
            context_id="char-reaction-test",
            context_type=ContextType.SOCIAL,
            scope=ContextScope.CHAPTER,
            name="Character Reaction Test",
            description="Testing character reactions",
            character_reactions={
                char_id1: "excited_and_hopeful",
                char_id2: "worried_and_cautious",
            },
        )

        assert context.get_character_reaction(char_id1) == "excited_and_hopeful"
        assert context.get_character_reaction(char_id2) == "worried_and_cautious"
        assert context.get_character_reaction(char_id3) is None

    @pytest.mark.unit
    def test_conflicts_with_context_true(self):
        """Test conflicts_with_context returns True for conflicting context."""
        context = NarrativeContext(
            context_id="conflicts-test",
            context_type=ContextType.THEMATIC,
            scope=ContextScope.ARC,
            name="Conflicts Test",
            description="Testing context conflicts",
            conflicting_contexts={
                "peaceful_times",
                "celebration_mood",
                "naive_optimism",
            },
        )

        assert context.conflicts_with_context("peaceful_times") is True
        assert context.conflicts_with_context("celebration_mood") is True
        assert context.conflicts_with_context("war_preparation") is False

    @pytest.mark.unit
    def test_reinforces_context_true(self):
        """Test reinforces_context returns True for reinforcing context."""
        context = NarrativeContext(
            context_id="reinforces-test",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Reinforces Test",
            description="Testing context reinforcement",
            reinforcing_contexts={
                "ancient_prophecy",
                "divine_mandate",
                "destiny_theme",
            },
        )

        assert context.reinforces_context("ancient_prophecy") is True
        assert context.reinforces_context("divine_mandate") is True
        assert context.reinforces_context("random_chance") is False

    @pytest.mark.unit
    def test_requires_context_true(self):
        """Test requires_context returns True for prerequisite context."""
        context = NarrativeContext(
            context_id="requires-test",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.ARC,
            name="Requires Test",
            description="Testing context requirements",
            prerequisite_contexts={
                "royal_death",
                "succession_crisis",
                "political_instability",
            },
        )

        assert context.requires_context("royal_death") is True
        assert context.requires_context("succession_crisis") is True
        assert context.requires_context("economic_boom") is False

    @pytest.mark.unit
    def test_get_mood_influence_existing(self):
        """Test get_mood_influence returns correct value for existing mood."""
        context = NarrativeContext(
            context_id="mood-influence-test",
            context_type=ContextType.EMOTIONAL,
            scope=ContextScope.SCENE,
            name="Mood Influence Test",
            description="Testing mood influences",
            mood_influences={
                "melancholy": Decimal("6.5"),
                "hope": Decimal("-2.0"),
                "tension": Decimal("8.0"),
            },
        )

        assert context.get_mood_influence("melancholy") == Decimal("6.5")
        assert context.get_mood_influence("hope") == Decimal("-2.0")
        assert context.get_mood_influence("tension") == Decimal("8.0")

    @pytest.mark.unit
    def test_get_mood_influence_default(self):
        """Test get_mood_influence returns default value for non-existing mood."""
        context = NarrativeContext(
            context_id="mood-default-test",
            context_type=ContextType.SETTING,
            scope=ContextScope.SCENE,
            name="Mood Default Test",
            description="Testing mood default",
            mood_influences={"gloom": Decimal("4.0")},
        )

        # Should return 0 for non-existing mood types
        assert context.get_mood_influence("joy") == Decimal("0")
        assert context.get_mood_influence("fear") == Decimal("0")
        # Should return actual value for existing mood
        assert context.get_mood_influence("gloom") == Decimal("4.0")

    @pytest.mark.unit
    def test_get_tension_modifier_existing(self):
        """Test get_tension_modifier returns correct value for existing tension type."""
        context = NarrativeContext(
            context_id="tension-modifier-test",
            context_type=ContextType.INTERPERSONAL,
            scope=ContextScope.CHAPTER,
            name="Tension Modifier Test",
            description="Testing tension modifiers",
            tension_modifiers={
                "romantic": Decimal("5.5"),
                "conflict": Decimal("7.0"),
                "mystery": Decimal("-1.5"),
            },
        )

        assert context.get_tension_modifier("romantic") == Decimal("5.5")
        assert context.get_tension_modifier("conflict") == Decimal("7.0")
        assert context.get_tension_modifier("mystery") == Decimal("-1.5")
        assert context.get_tension_modifier("comic") == Decimal("0")

    @pytest.mark.unit
    def test_get_pacing_effect_existing(self):
        """Test get_pacing_effect returns correct value for existing pacing aspect."""
        context = NarrativeContext(
            context_id="pacing-effect-test",
            context_type=ContextType.THEMATIC,
            scope=ContextScope.ARC,
            name="Pacing Effect Test",
            description="Testing pacing effects",
            pacing_effects={
                "urgency": Decimal("6.0"),
                "contemplation": Decimal("-3.0"),
                "action_frequency": Decimal("4.5"),
            },
        )

        assert context.get_pacing_effect("urgency") == Decimal("6.0")
        assert context.get_pacing_effect("contemplation") == Decimal("-3.0")
        assert context.get_pacing_effect("action_frequency") == Decimal("4.5")
        assert context.get_pacing_effect("dialogue_focus") == Decimal("0")

    @pytest.mark.unit
    def test_get_contextual_summary(self):
        """Test get_contextual_summary returns comprehensive summary dict."""
        char_id = uuid4()

        context = NarrativeContext(
            context_id="summary-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.ARC,
            name="Magic System Context",
            description="The underlying magical laws and constraints",
            is_persistent=True,
            applies_from_sequence=5,
            applies_to_sequence=95,
            affected_characters={char_id},
            locations={"magic_academy", "enchanted_forest"},
            hidden_information=["Secret about magic origins", "Origins are forgotten"],
            narrative_constraints=["Magic requires sacrifice", "Limited spell uses"],
            mood_influences={"wonder": Decimal("7.0")},
            pacing_effects={"mystery": Decimal("5.0")},
            prerequisite_contexts={"magic_discovery"},
            conflicting_contexts={"anti_magic_era"},
            reinforcing_contexts={"ancient_prophecy", "magical_awakening"},
            key_facts=["Magic is real", "It has rules"],
            implicit_knowledge=["Everyone knows magic exists"],
        )

        summary = context.get_contextual_summary()

        assert summary["context_id"] == "summary-test"
        assert summary["type"] == "magical"
        assert summary["scope"] == "arc"
        assert summary["name"] == "Magic System Context"
        assert summary["is_persistent"] is True
        assert summary["has_sequence_range"] is True
        assert summary["sequence_range"] == [5, 95]
        assert summary["affects_characters"] is True
        assert summary["character_count"] == 1
        assert summary["location_count"] == 2
        assert isinstance(summary["influence_strength"], float)
        assert isinstance(summary["complexity_score"], float)
        assert summary["has_hidden_information"] is True
        assert summary["has_constraints"] is True
        assert summary["influences_mood"] is True
        assert summary["influences_pacing"] is True
        assert summary["relationship_counts"]["prerequisites"] == 1
        assert summary["relationship_counts"]["conflicts"] == 1
        assert summary["relationship_counts"]["reinforces"] == 2
        assert summary["information_layers"]["key_facts"] == 2
        assert summary["information_layers"]["implicit_knowledge"] == 1
        assert summary["information_layers"]["hidden_information"] == 2
