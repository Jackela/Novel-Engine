#!/usr/bin/env python3
"""
Unit Tests for NarrativeTheme Edge Cases

Test suite covering edge cases, boundary conditions, and complex scenarios
for NarrativeTheme in the Narrative Context domain layer.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.contexts.narratives.domain.value_objects.narrative_theme import (
    NarrativeTheme,
    ThemeIntensity,
    ThemeType,
)

pytestmark = pytest.mark.unit


class TestNarrativeThemeEdgeCasesAndBoundaryConditions:
    """Test suite for edge cases and boundary conditions."""

    @pytest.mark.unit
    def test_creation_with_fixed_timestamp(self):
        """Test creation with explicitly set timestamp."""
        fixed_time = datetime(2024, 6, 15, 14, 30, 45, tzinfo=timezone.utc)

        theme = NarrativeTheme(
            theme_id="timestamp-test",
            theme_type=ThemeType.UNIVERSAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Eternal Love",
            description="Love that transcends time",
            creation_timestamp=fixed_time,
        )

        assert theme.creation_timestamp == fixed_time

    @pytest.mark.unit
    def test_large_collections_handling(self):
        """Test handling of large collections."""
        many_symbols = {f"symbol_{i}" for i in range(100)}
        many_motifs = {f"motif_{i}" for i in range(75)}
        many_archetypes = {f"archetype_{i}" for i in range(50)}
        many_conflicts = {f"conflict_theme_{i}" for i in range(25)}
        many_reinforces = {f"reinforce_theme_{i}" for i in range(30)}
        many_tags = {f"tag_{i}" for i in range(40)}
        large_audience_mapping = {
            f"audience_{i}": Decimal(str(i % 10 + 1)) for i in range(20)
        }

        theme = NarrativeTheme(
            theme_id="large-collections-test",
            theme_type=ThemeType.PHILOSOPHICAL,
            intensity=ThemeIntensity.OVERWHELMING,
            name="Complexity of Existence",
            description="A theme with many interconnected elements",
            symbolic_elements=many_symbols,
            related_motifs=many_motifs,
            character_archetypes=many_archetypes,
            conflicts_with_themes=many_conflicts,
            reinforces_themes=many_reinforces,
            target_audience_relevance=large_audience_mapping,
            tags=many_tags,
        )

        assert len(theme.symbolic_elements) == 100
        assert len(theme.related_motifs) == 75
        assert len(theme.character_archetypes) == 50
        assert len(theme.conflicts_with_themes) == 25
        assert len(theme.reinforces_themes) == 30
        assert len(theme.target_audience_relevance) == 20
        assert len(theme.tags) == 40
        assert theme.has_symbolic_representation is True
        assert theme.has_character_expression is True

    @pytest.mark.unit
    def test_decimal_precision_handling(self):
        """Test handling of decimal precision for score values."""
        theme = NarrativeTheme(
            theme_id="precision-test",
            theme_type=ThemeType.MORAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Ethical Dilemma",
            description="Complex moral choices",
            moral_complexity=Decimal("7.123456789"),
            emotional_resonance=Decimal("8.987654321"),
            universal_appeal=Decimal("9.555555555"),
        )

        # Values should maintain precision
        assert theme.moral_complexity == Decimal("7.123456789")
        assert theme.emotional_resonance == Decimal("8.987654321")
        assert theme.universal_appeal == Decimal("9.555555555")

        # Scores should use precise calculation
        complexity_score = theme.thematic_complexity_score
        impact_score = theme.narrative_impact_score
        assert isinstance(complexity_score, Decimal)
        assert isinstance(impact_score, Decimal)

    @pytest.mark.unit
    def test_unicode_text_handling(self):
        """Test handling of unicode characters in text fields."""
        theme = NarrativeTheme(
            theme_id="unicode-test-🎭",
            theme_type=ThemeType.CULTURAL,
            intensity=ThemeIntensity.PROMINENT,
            name="文化传承 Cultural Heritage 🏛️",
            description="Preserving traditions across generations: αβγ 中文 русский العربية 🌍",
            cultural_context="多元文化环境 Multicultural environment",
            development_trajectory="从传统到现代 From tradition to modernity ⚡",
        )

        assert "🎭" in theme.theme_id
        assert "文化传承" in theme.name
        assert "🏛️" in theme.name
        assert "中文" in theme.description
        assert "العربية" in theme.description
        assert "🌍" in theme.description
        assert "多元文化环境" in theme.cultural_context
        assert "⚡" in theme.development_trajectory

    @pytest.mark.unit
    def test_complex_metadata_handling(self):
        """Test handling of complex metadata structures."""
        complex_metadata = {
            "research_data": {
                "sources": ["Jung", "Campbell", "Vogler"],
                "analysis_depth": {
                    "psychological": 8.5,
                    "mythological": 9.0,
                    "cultural": 7.5,
                },
            },
            "adaptation_notes": [
                {"medium": "film", "effectiveness": 9.0},
                {"medium": "novel", "effectiveness": 8.5},
                {"medium": "theatre", "effectiveness": 7.0},
            ],
            "unicode_metadata_🔍": {
                "global_appeal": "универсальный",
                "cultural_variants": ["Western", "Eastern", "中式", "العربي"],
            },
        }

        theme = NarrativeTheme(
            theme_id="complex-metadata-test",
            theme_type=ThemeType.UNIVERSAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Hero's Journey",
            description="Universal pattern of adventure and transformation",
            metadata=complex_metadata,
        )

        # Should store complex metadata as-is
        assert theme.metadata == complex_metadata
        assert theme.metadata["research_data"]["sources"] == [
            "Jung",
            "Campbell",
            "Vogler",
        ]
        assert theme.metadata["unicode_metadata_🔍"]["global_appeal"] == "универсальный"
        assert "中式" in theme.metadata["unicode_metadata_🔍"]["cultural_variants"]
