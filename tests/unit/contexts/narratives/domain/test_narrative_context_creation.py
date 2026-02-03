#!/usr/bin/env python3
"""
Unit Tests for NarrativeContext Creation

Test suite covering NarrativeContext object creation,
initialization, default values, and immutability.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from src.contexts.narratives.domain.value_objects.narrative_context import (
    ContextScope,
    ContextType,
    NarrativeContext,
)


class TestNarrativeContextCreation:
    """Test suite for NarrativeContext creation and initialization."""

    @pytest.mark.unit
    def test_create_minimal_narrative_context(self):
        """Test creating narrative context with minimal required fields."""
        context = NarrativeContext(
            context_id="minimal-context-1",
            context_type=ContextType.SETTING,
            scope=ContextScope.SCENE,
            name="Castle Throne Room",
            description="The formal throne room where important court business is conducted",
        )

        assert context.context_id == "minimal-context-1"
        assert context.context_type == ContextType.SETTING
        assert context.scope == ContextScope.SCENE
        assert context.name == "Castle Throne Room"
        assert (
            context.description
            == "The formal throne room where important court business is conducted"
        )

    @pytest.mark.unit
    def test_create_comprehensive_narrative_context(self):
        """Test creating narrative context with all fields specified."""
        char_id1 = uuid4()
        char_id2 = uuid4()
        char_id3 = uuid4()
        creation_time = datetime.now(timezone.utc)

        context = NarrativeContext(
            context_id="comprehensive-context",
            context_type=ContextType.POLITICAL,
            scope=ContextScope.ARC,
            name="Civil War Era",
            description="A time of political upheaval and division within the kingdom",
            applies_from_sequence=10,
            applies_to_sequence=75,
            is_persistent=False,
            locations={"capital_city", "northern_provinces", "border_towns"},
            affected_regions={"north", "central", "eastern_march"},
            geographical_scope="kingdom_wide",
            affected_characters={char_id1, char_id2, char_id3},
            character_knowledge_required={char_id1, char_id2},
            character_reactions={
                char_id1: "suspicious_and_cautious",
                char_id2: "opportunistic",
                char_id3: "fearful",
            },
            key_facts=[
                "King's authority is weakened",
                "Noble houses are taking sides",
                "Trade routes are disrupted",
            ],
            implicit_knowledge=[
                "Everyone knows war is coming",
                "Loyalty is questioned everywhere",
            ],
            hidden_information=[
                "The queen is secretly funding rebels",
                "Foreign powers are involved",
            ],
            narrative_constraints=[
                "Characters cannot travel freely",
                "Communication is monitored",
                "Resources are scarce",
            ],
            behavioral_influences=[
                "Increased paranoia among characters",
                "Stronger group loyalties",
                "Reduced trust in institutions",
            ],
            plot_implications=[
                "Forces characters to choose sides",
                "Creates opportunities for betrayal",
                "Sets up major confrontations",
            ],
            mood_influences={
                "tension": Decimal("8.0"),
                "fear": Decimal("6.5"),
                "uncertainty": Decimal("9.0"),
            },
            tension_modifiers={
                "political": Decimal("7.5"),
                "social": Decimal("5.0"),
                "military": Decimal("8.5"),
            },
            pacing_effects={
                "urgency": Decimal("6.0"),
                "deliberation": Decimal("-3.0"),
                "action_frequency": Decimal("4.0"),
            },
            prerequisite_contexts={"peaceful_kingdom", "economic_prosperity"},
            conflicting_contexts={"time_of_peace", "royal_wedding_celebration"},
            reinforcing_contexts={"economic_hardship", "foreign_threat"},
            narrative_importance=Decimal("9.0"),
            visibility_level=Decimal("8.5"),
            complexity_level=Decimal("7.5"),
            evolution_rate=Decimal("0.6"),
            stability=Decimal("0.3"),
            tags={"major_arc", "political", "conflict"},
            source_material="Historical research on civil wars",
            research_notes="Based on War of the Roses and similar conflicts",
            creation_timestamp=creation_time,
            metadata={
                "inspiration": "Real historical events",
                "complexity_rating": "high",
                "audience_impact": "significant",
            },
        )

        assert context.context_id == "comprehensive-context"
        assert context.context_type == ContextType.POLITICAL
        assert context.scope == ContextScope.ARC
        assert context.applies_from_sequence == 10
        assert context.applies_to_sequence == 75
        assert context.is_persistent is False
        assert context.locations == {
            "capital_city",
            "northern_provinces",
            "border_towns",
        }
        assert context.affected_regions == {"north", "central", "eastern_march"}
        assert context.geographical_scope == "kingdom_wide"
        assert context.affected_characters == {char_id1, char_id2, char_id3}
        assert context.character_knowledge_required == {char_id1, char_id2}
        assert context.character_reactions[char_id1] == "suspicious_and_cautious"
        assert len(context.key_facts) == 3
        assert len(context.implicit_knowledge) == 2
        assert len(context.hidden_information) == 2
        assert len(context.narrative_constraints) == 3
        assert len(context.behavioral_influences) == 3
        assert len(context.plot_implications) == 3
        assert context.mood_influences["tension"] == Decimal("8.0")
        assert context.tension_modifiers["political"] == Decimal("7.5")
        assert context.pacing_effects["urgency"] == Decimal("6.0")
        assert context.prerequisite_contexts == {
            "peaceful_kingdom",
            "economic_prosperity",
        }
        assert context.conflicting_contexts == {
            "time_of_peace",
            "royal_wedding_celebration",
        }
        assert context.reinforcing_contexts == {"economic_hardship", "foreign_threat"}
        assert context.narrative_importance == Decimal("9.0")
        assert context.visibility_level == Decimal("8.5")
        assert context.complexity_level == Decimal("7.5")
        assert context.evolution_rate == Decimal("0.6")
        assert context.stability == Decimal("0.3")
        assert context.tags == {"major_arc", "political", "conflict"}
        assert context.source_material == "Historical research on civil wars"
        assert (
            context.research_notes == "Based on War of the Roses and similar conflicts"
        )
        assert context.creation_timestamp == creation_time
        assert context.metadata["inspiration"] == "Real historical events"

    @pytest.mark.unit
    def test_default_values_initialization(self):
        """Test that default values are properly initialized."""
        context = NarrativeContext(
            context_id="default-test",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.GLOBAL,
            name="Default Culture",
            description="Testing default value initialization",
        )

        # Test default collections are empty
        assert context.locations == set()
        assert context.affected_regions == set()
        assert context.affected_characters == set()
        assert context.character_knowledge_required == set()
        assert context.character_reactions == {}
        assert context.key_facts == []
        assert context.implicit_knowledge == []
        assert context.hidden_information == []
        assert context.narrative_constraints == []
        assert context.behavioral_influences == []
        assert context.plot_implications == []
        assert context.mood_influences == {}
        assert context.tension_modifiers == {}
        assert context.pacing_effects == {}
        assert context.prerequisite_contexts == set()
        assert context.conflicting_contexts == set()
        assert context.reinforcing_contexts == set()
        assert context.tags == set()
        assert context.metadata == {}

        # Test default values
        assert context.applies_from_sequence is None
        assert context.applies_to_sequence is None
        assert context.is_persistent is True
        assert context.geographical_scope is None
        assert context.narrative_importance == Decimal("5.0")
        assert context.visibility_level == Decimal("5.0")
        assert context.complexity_level == Decimal("5.0")
        assert context.evolution_rate == Decimal("0.0")
        assert context.stability == Decimal("1.0")
        assert context.source_material is None
        assert context.research_notes == ""

        # Test that creation timestamp was set
        assert context.creation_timestamp is not None
        assert isinstance(context.creation_timestamp, datetime)

    @pytest.mark.unit
    def test_frozen_dataclass_immutability(self):
        """Test that NarrativeContext is immutable (frozen dataclass)."""
        context = NarrativeContext(
            context_id="immutable-test",
            context_type=ContextType.EMOTIONAL,
            scope=ContextScope.CHAPTER,
            name="Immutable Test",
            description="Testing immutability",
        )

        # Should not be able to modify fields
        with pytest.raises(AttributeError):
            context.name = "Modified Name"

        with pytest.raises(AttributeError):
            context.scope = ContextScope.GLOBAL

        with pytest.raises(AttributeError):
            context.narrative_importance = Decimal("8.0")
