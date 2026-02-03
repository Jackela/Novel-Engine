#!/usr/bin/env python3
"""
Unit Tests for NarrativeContext Edge Cases

Test suite covering edge cases, boundary conditions,
decimal precision, unicode handling, and complex metadata.
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


class TestNarrativeContextEdgeCasesAndBoundaryConditions:
    """Test suite for edge cases and boundary conditions."""

    @pytest.mark.unit
    def test_creation_with_fixed_timestamp(self):
        """Test creation with explicitly set timestamp."""
        fixed_time = datetime(2024, 9, 15, 16, 45, 30, tzinfo=timezone.utc)

        context = NarrativeContext(
            context_id="timestamp-test",
            context_type=ContextType.SETTING,
            scope=ContextScope.SCENE,
            name="Fixed Timestamp Context",
            description="Testing fixed timestamp",
            creation_timestamp=fixed_time,
        )

        assert context.creation_timestamp == fixed_time

    @pytest.mark.unit
    def test_large_collections_handling(self):
        """Test handling of large collections."""
        many_locations = {f"location_{i}" for i in range(100)}
        many_regions = {f"region_{i}" for i in range(50)}
        many_characters = {uuid4() for _ in range(75)}
        many_knowledge_chars = {uuid4() for _ in range(25)}
        many_reactions = {uuid4(): f"reaction_{i}" for i in range(30)}
        many_facts = [f"fact_{i}" for i in range(80)]
        many_implicit = [f"implicit_{i}" for i in range(40)]
        many_hidden = [f"hidden_{i}" for i in range(20)]
        many_constraints = [f"constraint_{i}" for i in range(35)]
        many_behaviors = [f"behavior_{i}" for i in range(45)]
        many_implications = [f"implication_{i}" for i in range(25)]
        many_moods = {f"mood_{i}": Decimal(str(i % 10)) for i in range(15)}
        many_tensions = {f"tension_{i}": Decimal(str((i % 20) - 10)) for i in range(12)}
        many_pacing = {f"pacing_{i}": Decimal(str((i % 15) - 5)) for i in range(18)}
        many_prerequisites = {f"prereq_{i}" for i in range(8)}
        many_conflicts = {f"conflict_{i}" for i in range(10)}
        many_reinforces = {f"reinforce_{i}" for i in range(12)}
        many_tags = {f"tag_{i}" for i in range(30)}

        context = NarrativeContext(
            context_id="large-collections-test",
            context_type=ContextType.MAGICAL,
            scope=ContextScope.GLOBAL,
            name="Complex Magic World",
            description="A world with incredibly complex magical systems and interactions",
            locations=many_locations,
            affected_regions=many_regions,
            affected_characters=many_characters,
            character_knowledge_required=many_knowledge_chars,
            character_reactions=many_reactions,
            key_facts=many_facts,
            implicit_knowledge=many_implicit,
            hidden_information=many_hidden,
            narrative_constraints=many_constraints,
            behavioral_influences=many_behaviors,
            plot_implications=many_implications,
            mood_influences=many_moods,
            tension_modifiers=many_tensions,
            pacing_effects=many_pacing,
            prerequisite_contexts=many_prerequisites,
            conflicting_contexts=many_conflicts,
            reinforcing_contexts=many_reinforces,
            tags=many_tags,
        )

        assert len(context.locations) == 100
        assert len(context.affected_regions) == 50
        assert len(context.affected_characters) == 75
        assert len(context.character_knowledge_required) == 25
        assert len(context.character_reactions) == 30
        assert len(context.key_facts) == 80
        assert len(context.implicit_knowledge) == 40
        assert len(context.hidden_information) == 20
        assert len(context.narrative_constraints) == 35
        assert len(context.behavioral_influences) == 45
        assert len(context.plot_implications) == 25
        assert len(context.mood_influences) == 15
        assert len(context.tension_modifiers) == 12
        assert len(context.pacing_effects) == 18
        assert len(context.prerequisite_contexts) == 8
        assert len(context.conflicting_contexts) == 10
        assert len(context.reinforcing_contexts) == 12
        assert len(context.tags) == 30
        assert context.affects_characters is True
        assert context.has_hidden_information is True
        assert context.has_narrative_constraints is True
        assert context.influences_mood is True
        assert context.influences_pacing is True
        assert context.has_prerequisites is True
        assert context.has_conflicts is True

    @pytest.mark.unit
    def test_decimal_precision_handling(self):
        """Test handling of decimal precision for influence and score values."""
        context = NarrativeContext(
            context_id="precision-test",
            context_type=ContextType.INTERPERSONAL,
            scope=ContextScope.SCENE,
            name="Precision Test",
            description="Testing decimal precision",
            narrative_importance=Decimal("7.123456789"),
            visibility_level=Decimal("8.987654321"),
            complexity_level=Decimal("6.555555555"),
            evolution_rate=Decimal("0.123456789"),
            stability=Decimal("0.987654321"),
            mood_influences={"precise_mood": Decimal("5.123456789")},
            tension_modifiers={"precise_tension": Decimal("-3.987654321")},
            pacing_effects={"precise_pacing": Decimal("2.555555555")},
        )

        # Values should maintain precision
        assert context.narrative_importance == Decimal("7.123456789")
        assert context.visibility_level == Decimal("8.987654321")
        assert context.complexity_level == Decimal("6.555555555")
        assert context.evolution_rate == Decimal("0.123456789")
        assert context.stability == Decimal("0.987654321")
        assert context.mood_influences["precise_mood"] == Decimal("5.123456789")
        assert context.tension_modifiers["precise_tension"] == Decimal("-3.987654321")
        assert context.pacing_effects["precise_pacing"] == Decimal("2.555555555")

        # Scores should use precise calculation
        influence_score = context.overall_influence_strength
        complexity_score = context.contextual_complexity_score
        assert isinstance(influence_score, Decimal)
        assert isinstance(complexity_score, Decimal)

    @pytest.mark.unit
    def test_unicode_text_handling(self):
        """Test handling of unicode characters in text fields."""
        context = NarrativeContext(
            context_id="unicode-test-🌍",
            context_type=ContextType.CULTURAL,
            scope=ContextScope.GLOBAL,
            name="世界文化 World Culture 🏛️",
            description="A rich tapestry of cultures: αβγ 中文 العربية русский हिन्दी 🌟",
            geographical_scope="全球范围 Global scope",
            source_material="多文化研究 Multicultural research",
            research_notes="Sources include: 文献、books, كتب, книги, पुस्तकें 📚",
        )

        assert "🌍" in context.context_id
        assert "世界文化" in context.name
        assert "🏛️" in context.name
        assert "αβγ" in context.description
        assert "العربية" in context.description
        assert "हिन्दी" in context.description
        assert "🌟" in context.description
        assert "全球范围" in context.geographical_scope
        assert "多文化研究" in context.source_material
        assert "📚" in context.research_notes

    @pytest.mark.unit
    def test_complex_metadata_handling(self):
        """Test handling of complex metadata structures."""
        complex_metadata = {
            "world_building": {
                "inspiration_sources": ["Tolkien", "Martin", "Sanderson"],
                "cultural_influences": {
                    "european": ["medieval", "renaissance"],
                    "asian": ["feudal_japan", "ancient_china"],
                    "fantasy": ["high_fantasy", "dark_fantasy"],
                },
            },
            "narrative_analysis": {
                "themes_explored": ["power", "corruption", "redemption"],
                "character_archetypes": [
                    {"type": "hero", "count": 3},
                    {"type": "mentor", "count": 2},
                    {"type": "shadow", "count": 1},
                ],
            },
            "unicode_research_🔬": {
                "multilingual_sources": {
                    "english": "Primary language",
                    "中文": "Chinese historical records",
                    "日本語": "Japanese cultural studies",
                    "العربية": "Arabic philosophical texts",
                }
            },
        }

        context = NarrativeContext(
            context_id="complex-metadata-test",
            context_type=ContextType.HISTORICAL,
            scope=ContextScope.GLOBAL,
            name="Complex World Context",
            description="A richly detailed world with complex cultural interactions",
            metadata=complex_metadata,
        )

        # Should store complex metadata as-is
        assert context.metadata == complex_metadata
        assert context.metadata["world_building"]["inspiration_sources"] == [
            "Tolkien",
            "Martin",
            "Sanderson",
        ]
        assert (
            context.metadata["unicode_research_🔬"]["multilingual_sources"]["中文"]
            == "Chinese historical records"
        )
        assert (
            "العربية" in context.metadata["unicode_research_🔬"]["multilingual_sources"]
        )
