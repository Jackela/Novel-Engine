"""
Edge Cases Tests for Narratives Context

Tests boundary conditions, edge cases, and unusual scenarios.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID

from src.contexts.narratives.domain.aggregates.narrative_arc import NarrativeArc
from src.contexts.narratives.domain.entities.narrative_thread import NarrativeThread
from src.contexts.narratives.domain.entities.story_element import StoryElement
from src.contexts.narratives.domain.value_objects.narrative_id import NarrativeId
from src.contexts.narratives.domain.value_objects.plot_point import PlotPoint, PlotPointType, PlotPointImportance
from src.contexts.narratives.domain.value_objects.narrative_theme import NarrativeTheme, ThemeType, ThemeIntensity
from src.contexts.narratives.domain.value_objects.story_pacing import StoryPacing, PacingType
from src.contexts.narratives.domain.value_objects.causal_node import CausalNode
pytestmark = pytest.mark.unit



class TestNarrativeIdEdgeCases:
    """Edge case tests for NarrativeId."""

    def test_narrative_id_generation(self):
        """Test narrative ID generation."""
        id1 = NarrativeId.generate()
        id2 = NarrativeId.generate()
        
        assert id1 != id2
        assert isinstance(id1.value, UUID)

    def test_narrative_id_from_string_valid_uuid(self):
        """Test narrative ID from valid UUID string."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        nid = NarrativeId.from_string(uuid_str)
        
        assert str(nid.value) == uuid_str

    def test_narrative_id_from_string_without_dashes(self):
        """Test narrative ID from UUID string without dashes."""
        uuid_str = "550e8400e29b41d4a716446655440000"
        nid = NarrativeId.from_string(uuid_str)
        
        assert nid.value.hex == uuid_str

    def test_narrative_id_from_string_empty_raises(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            NarrativeId.from_string("")

    def test_narrative_id_from_string_invalid_raises(self):
        """Test that invalid UUID string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            NarrativeId.from_string("not-a-uuid")

    def test_narrative_id_from_string_whitespace_raises(self):
        """Test that whitespace in string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            NarrativeId.from_string(" 550e8400-e29b-41d4-a716-446655440000 ")

    def test_narrative_id_equality(self):
        """Test narrative ID equality."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        id1 = NarrativeId.from_string(uuid_str)
        id2 = NarrativeId.from_string(uuid_str)
        
        assert id1 == id2

    def test_narrative_id_hash(self):
        """Test narrative ID hashing."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        nid = NarrativeId.from_string(uuid_str)
        
        # Hash should be consistent
        assert hash(nid) == hash(nid)
        # Different NarrativeIds with same value should have same hash
        nid2 = NarrativeId.from_string(uuid_str)
        assert hash(nid) == hash(nid2)


class TestNarrativeArcEdgeCases:
    """Edge case tests for NarrativeArc."""

    def test_arc_creation_minimal(self):
        """Test arc creation with minimal required fields."""
        arc = NarrativeArc(
            arc_id=NarrativeId.generate(),
            arc_name="Test Arc",
            arc_type="main",
        )
        assert arc.arc_name == "Test Arc"
        assert arc.arc_type == "main"

    def test_arc_with_empty_description(self):
        """Test arc with empty description."""
        arc = NarrativeArc(
            arc_id=NarrativeId.generate(),
            arc_name="Test Arc",
            arc_type="main",
            description="",
        )
        assert arc.description == ""

    def test_arc_with_very_long_name(self):
        """Test arc with very long name."""
        long_name = "A" * 1000
        arc = NarrativeArc(
            arc_id=NarrativeId.generate(),
            arc_name=long_name,
            arc_type="main",
        )
        assert len(arc.arc_name) == 1000

    def test_arc_with_special_characters(self):
        """Test arc with special unicode characters."""
        special_name = "Arc: 日本語 🎭 Ñoño & More"
        arc = NarrativeArc(
            arc_id=NarrativeId.generate(),
            arc_name=special_name,
            arc_type="main",
        )
        assert arc.arc_name == special_name


class TestPlotPointEdgeCases:
    """Edge case tests for PlotPoint."""

    def test_plot_point_types_exist(self):
        """Test that all plot point types exist."""
        assert PlotPointType.CLIMAX is not None
        assert PlotPointType.RESOLUTION is not None
        assert PlotPointType.INCITING_INCIDENT is not None

    def test_plot_point_all_types(self):
        """Test all plot point types."""
        types = [
            PlotPointType.INCITING_INCIDENT,
            PlotPointType.RISING_ACTION,
            PlotPointType.CLIMAX,
            PlotPointType.FALLING_ACTION,
            PlotPointType.RESOLUTION,
            PlotPointType.TURNING_POINT,
            PlotPointType.REVELATION,
            PlotPointType.CRISIS,
            PlotPointType.SETBACK,
            PlotPointType.TRIUMPH,
            PlotPointType.COMPLICATION,
            PlotPointType.DISCOVERY,
            PlotPointType.CONFRONTATION,
            PlotPointType.RECONCILIATION,
            PlotPointType.SACRIFICE,
            PlotPointType.TRANSFORMATION,
        ]
        
        for pt_type in types:
            assert isinstance(pt_type, PlotPointType)

    def test_plot_point_all_importance_levels(self):
        """Test all importance levels."""
        levels = [
            PlotPointImportance.CRITICAL,
            PlotPointImportance.MAJOR,
            PlotPointImportance.MODERATE,
            PlotPointImportance.MINOR,
            PlotPointImportance.SUPPLEMENTAL,
        ]
        
        for level in levels:
            assert isinstance(level, PlotPointImportance)


class TestNarrativeThemeEdgeCases:
    """Edge case tests for NarrativeTheme."""

    def test_theme_creation(self):
        """Test theme creation."""
        theme = NarrativeTheme(
            theme_id="theme_001",
            theme_type=ThemeType.UNIVERSAL,
            intensity=ThemeIntensity.CENTRAL,
            name="Redemption",
            description="The journey of redemption",
        )
        assert theme.name == "Redemption"
        assert theme.theme_type == ThemeType.UNIVERSAL

    def test_theme_all_types(self):
        """Test all theme types."""
        types = [
            ThemeType.UNIVERSAL,
            ThemeType.SOCIAL,
            ThemeType.PHILOSOPHICAL,
            ThemeType.PSYCHOLOGICAL,
            ThemeType.CULTURAL,
            ThemeType.MORAL,
            ThemeType.POLITICAL,
            ThemeType.SPIRITUAL,
            ThemeType.ENVIRONMENTAL,
            ThemeType.TECHNOLOGICAL,
            ThemeType.FAMILY,
            ThemeType.COMING_OF_AGE,
        ]
        
        for t_type in types:
            assert isinstance(t_type, ThemeType)

    def test_theme_all_intensities(self):
        """Test all theme intensity levels."""
        intensities = [
            ThemeIntensity.SUBTLE,
            ThemeIntensity.MODERATE,
            ThemeIntensity.PROMINENT,
            ThemeIntensity.CENTRAL,
            ThemeIntensity.OVERWHELMING,
        ]
        
        for intensity in intensities:
            assert isinstance(intensity, ThemeIntensity)


class TestStoryPacingEdgeCases:
    """Edge case tests for StoryPacing."""

    def test_pacing_creation(self):
        """Test pacing creation."""
        from decimal import Decimal
        from src.contexts.narratives.domain.value_objects.story_pacing import PacingIntensity
        pacing = StoryPacing(
            pacing_id="pacing_001",
            pacing_type=PacingType.STEADY,
            base_intensity=PacingIntensity.MODERATE,
            start_sequence=0,
            end_sequence=10,
            dialogue_ratio=Decimal("0.3"),
            action_ratio=Decimal("0.4"),
            reflection_ratio=Decimal("0.3"),
        )
        assert pacing.pacing_id == "pacing_001"
        assert pacing.pacing_type == PacingType.STEADY

    def test_pacing_all_types(self):
        """Test all pacing types."""
        types = [
            PacingType.STEADY,
            PacingType.ACCELERATING,
            PacingType.DECELERATING,
            PacingType.EPISODIC,
            PacingType.CRESCENDO,
            PacingType.PLATEAU,
            PacingType.WAVE,
            PacingType.EXPLOSIVE_START,
            PacingType.SLOW_BURN,
            PacingType.STACCATO,
        ]
        
        for p_type in types:
            assert isinstance(p_type, PacingType)


class TestCausalNodeEdgeCases:
    """Edge case tests for CausalNode."""

    def test_causal_node_creation(self):
        """Test causal node creation."""
        node = CausalNode(
            node_id="node_001",
            description="An event",
        )
        assert node.node_id == "node_001"
        assert node.description == "An event"

    def test_causal_node_creation_variations(self):
        """Test causal node creation with various configurations."""
        # Test with just id and description
        node1 = CausalNode(
            node_id="node_001",
            description="Simple event",
        )
        assert node1.node_id == "node_001"
        
        # Test with additional fields if supported
        try:
            node2 = CausalNode(
                node_id="node_002",
                description="Event with related",
                related_events=["event_1", "event_2"],
            )
            assert len(node2.related_events) == 2
        except TypeError:
            # Field doesn't exist, which is fine
            pass


class TestStringHandlingEdgeCases:
    """Edge case tests for string handling."""

    def test_unicode_handling_in_arc(self):
        """Test handling of unicode characters in arc."""
        unicode_strings = [
            "日本語テスト",
            "العربية",
            "🎭🎬📚",
            "Café résumé naïve",
            "Καλημέρα κόσμε",
        ]
        
        for s in unicode_strings:
            arc = NarrativeArc(
                arc_id=NarrativeId.generate(),
                arc_name=s,
                arc_type="main",
            )
            assert arc.arc_name == s


class TestNarrativeIdValidation:
    """Validation tests for NarrativeId."""

    def test_narrative_id_with_non_uuid_type_raises(self):
        """Test that non-UUID type raises TypeError."""
        with pytest.raises(TypeError, match="must be a UUID"):
            NarrativeId(value="not-a-uuid")

    def test_narrative_id_with_none_raises(self):
        """Test that None raises ValueError in from_string."""
        with pytest.raises(ValueError, match="Invalid UUID format"):
            NarrativeId.from_string(None)

    def test_narrative_id_str_and_repr(self):
        """Test string representations."""
        nid = NarrativeId.generate()
        
        str_repr = str(nid)
        assert "NarrativeId" in str_repr
        
        repr_str = repr(nid)
        assert "NarrativeId" in repr_str
        assert "value" in repr_str


class TestPlotPointTypeAndImportance:
    """Tests for PlotPointType and PlotPointImportance."""

    def test_plot_point_type_values(self):
        """Test plot point type string values."""
        assert PlotPointType.CLIMAX.value == "climax"
        assert PlotPointType.RESOLUTION.value == "resolution"
        assert PlotPointType.INCITING_INCIDENT.value == "inciting_incident"

    def test_plot_point_importance_values(self):
        """Test plot point importance string values."""
        assert PlotPointImportance.CRITICAL.value == "critical"
        assert PlotPointImportance.MAJOR.value == "major"
        assert PlotPointImportance.MINOR.value == "minor"


class TestThemeTypeAndIntensity:
    """Tests for ThemeType and ThemeIntensity."""

    def test_theme_type_values(self):
        """Test theme type string values."""
        assert ThemeType.UNIVERSAL.value == "universal"
        assert ThemeType.MORAL.value == "moral"
        assert ThemeType.SOCIAL.value == "social"

    def test_theme_intensity_values(self):
        """Test theme intensity string values."""
        assert ThemeIntensity.CENTRAL.value == "central"
        assert ThemeIntensity.SUBTLE.value == "subtle"
        assert ThemeIntensity.OVERWHELMING.value == "overwhelming"


class TestPacingIntensity:
    """Tests for PacingIntensity."""
    
    def test_pacing_intensity_values(self):
        """Test pacing intensity string values."""
        from src.contexts.narratives.domain.value_objects.story_pacing import PacingIntensity
        assert PacingIntensity.GLACIAL.value == "glacial"
        assert PacingIntensity.SLOW.value == "slow"
        assert PacingIntensity.MODERATE.value == "moderate"
        assert PacingIntensity.BRISK.value == "brisk"
        assert PacingIntensity.FAST.value == "fast"
        assert PacingIntensity.BREAKNECK.value == "breakneck"
