#!/usr/bin/env python3
"""
Unit tests for Rumor Entity

Comprehensive test suite for the Rumor entity covering
validation, spread mechanics, veracity labels, and serialization.
"""

import pytest

pytestmark = pytest.mark.unit

from src.contexts.world.domain.entities.rumor import (
    TRUTH_DECAY_PER_HOP,
    VERACITY_CONFIRMED,
    VERACITY_LIKELY_FALSE,
    VERACITY_LIKELY_TRUE,
    VERACITY_UNCERTAIN,
    Rumor,
    RumorOrigin,
)
from src.contexts.world.domain.value_objects.world_calendar import WorldCalendar


class TestRumorOriginEnum:
    """Test suite for RumorOrigin enum."""

    @pytest.mark.unit
    def test_rumor_origin_values(self):
        """Test all expected RumorOrigin values exist."""
        assert RumorOrigin.EVENT.value == "event"
        assert RumorOrigin.NPC.value == "npc"
        assert RumorOrigin.PLAYER.value == "player"
        assert RumorOrigin.UNKNOWN.value == "unknown"

    @pytest.mark.unit
    def test_rumor_origin_count(self):
        """Test that we have exactly 4 origin types."""
        assert len(RumorOrigin) == 4


class TestRumorCreation:
    """Test suite for Rumor creation."""

    @pytest.fixture
    def valid_calendar(self) -> WorldCalendar:
        """Create a valid calendar for testing."""
        return WorldCalendar(1042, 3, 15, "Third Age")

    @pytest.fixture
    def valid_rumor_data(self, valid_calendar: WorldCalendar) -> dict:
        """Create valid rumor data for testing."""
        return {
            "content": "Word spreads of a great battle in the north...",
            "truth_value": 90,
            "origin_type": RumorOrigin.EVENT,
            "origin_location_id": "loc-north-pass",
            "created_date": valid_calendar,
        }

    @pytest.mark.unit
    def test_create_rumor_with_all_fields(self, valid_rumor_data: dict):
        """Test creating a rumor with all fields specified."""
        rumor = Rumor(**valid_rumor_data)

        assert rumor.content == "Word spreads of a great battle in the north..."
        assert rumor.truth_value == 90
        assert rumor.origin_type == RumorOrigin.EVENT
        assert rumor.origin_location_id == "loc-north-pass"
        assert rumor.rumor_id is not None
        assert rumor.created_date is not None

    @pytest.mark.unit
    def test_create_rumor_with_defaults(self):
        """Test creating a rumor with minimal required fields."""
        rumor = Rumor(
            content="Something happened somewhere...",
            origin_location_id="loc-123",
        )

        assert rumor.content == "Something happened somewhere..."
        assert rumor.truth_value == 50  # Default
        assert rumor.origin_type == RumorOrigin.UNKNOWN  # Default
        assert rumor.origin_location_id == "loc-123"
        assert rumor.source_event_id is None  # Optional
        assert rumor.spread_count == 0  # Default
        assert rumor.current_locations == set()  # Empty set

    @pytest.mark.unit
    def test_auto_generated_rumor_id(self):
        """Test that rumor_id is auto-generated as UUID."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
        )

        # Should be a valid UUID string
        assert isinstance(rumor.rumor_id, str)
        assert len(rumor.rumor_id) == 36  # UUID format

    @pytest.mark.unit
    def test_create_rumor_with_current_locations(self):
        """Test creating a rumor with initial locations."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-origin",
            current_locations={"loc-origin", "loc-spread-1"},
        )

        assert "loc-origin" in rumor.current_locations
        assert "loc-spread-1" in rumor.current_locations
        assert len(rumor.current_locations) == 2


class TestRumorValidation:
    """Test suite for Rumor validation."""

    @pytest.mark.unit
    def test_validation_empty_content(self):
        """Test that empty content fails validation."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            Rumor(
                content="",
                origin_location_id="loc-123",
            )

    @pytest.mark.unit
    def test_validation_whitespace_content(self):
        """Test that whitespace-only content fails validation."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            Rumor(
                content="   ",
                origin_location_id="loc-123",
            )

    @pytest.mark.unit
    def test_validation_empty_origin_location(self):
        """Test that empty origin_location_id fails validation."""
        with pytest.raises(ValueError, match="Origin location ID cannot be empty"):
            Rumor(
                content="Test rumor",
                origin_location_id="",
            )

    @pytest.mark.unit
    def test_validation_truth_value_below_range(self):
        """Test that truth_value below 0 fails validation."""
        with pytest.raises(ValueError, match="Truth value must be between 0 and 100"):
            Rumor(
                content="Test rumor",
                origin_location_id="loc-123",
                truth_value=-1,
            )

    @pytest.mark.unit
    def test_validation_truth_value_above_range(self):
        """Test that truth_value above 100 fails validation."""
        with pytest.raises(ValueError, match="Truth value must be between 0 and 100"):
            Rumor(
                content="Test rumor",
                origin_location_id="loc-123",
                truth_value=101,
            )

    @pytest.mark.unit
    def test_valid_truth_value_boundaries(self):
        """Test that truth_value boundaries 0 and 100 are valid."""
        rumor_min = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=0,
        )
        rumor_max = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=100,
        )

        assert rumor_min.truth_value == 0
        assert rumor_max.truth_value == 100


class TestRumorSpread:
    """Test suite for Rumor spread mechanics."""

    @pytest.mark.unit
    def test_truth_after_spread_decreases(self):
        """Test that truth value decreases after spread."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-origin",
            truth_value=90,
        )

        new_truth = rumor.truth_after_spread()
        assert new_truth == 80  # 90 - 10

    @pytest.mark.unit
    def test_truth_after_spread_minimum_zero(self):
        """Test that truth value doesn't go below 0."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-origin",
            truth_value=5,
        )

        new_truth = rumor.truth_after_spread()
        assert new_truth == 0  # max(0, 5 - 10) = 0

    @pytest.mark.unit
    def test_truth_after_spread_at_zero(self):
        """Test truth after spread when already at 0."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-origin",
            truth_value=0,
        )

        new_truth = rumor.truth_after_spread()
        assert new_truth == 0

    @pytest.mark.unit
    def test_spread_to_creates_new_instance(self):
        """Test that spread_to creates a new Rumor instance."""
        original = Rumor(
            rumor_id="rumor-123",
            content="Test rumor",
            origin_location_id="loc-origin",
            truth_value=90,
            current_locations={"loc-origin"},
            spread_count=0,
        )

        spread = original.spread_to("loc-new")

        # Original unchanged
        assert original.truth_value == 90
        assert original.spread_count == 0
        assert "loc-new" not in original.current_locations

        # New instance has changes
        assert spread.rumor_id == "rumor-123"  # Same ID
        assert spread.truth_value == 80  # Decreased
        assert spread.spread_count == 1  # Incremented
        assert "loc-new" in spread.current_locations

    @pytest.mark.unit
    def test_spread_to_adds_location(self):
        """Test that spread_to adds the new location."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-origin",
            truth_value=70,
            current_locations={"loc-origin"},
        )

        spread = rumor.spread_to("loc-new")
        assert "loc-new" in spread.current_locations
        assert "loc-origin" in spread.current_locations  # Original preserved

    @pytest.mark.unit
    def test_spread_to_empty_location_raises(self):
        """Test that spread_to with empty location raises ValueError."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-origin",
            truth_value=70,
        )

        with pytest.raises(ValueError, match="Location ID cannot be empty"):
            rumor.spread_to("")

    @pytest.mark.unit
    def test_multiple_spreads(self):
        """Test multiple spreads accumulate correctly."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-origin",
            truth_value=100,
            current_locations={"loc-origin"},
            spread_count=0,
        )

        # First spread
        rumor = rumor.spread_to("loc-1")
        assert rumor.truth_value == 90
        assert rumor.spread_count == 1

        # Second spread
        rumor = rumor.spread_to("loc-2")
        assert rumor.truth_value == 80
        assert rumor.spread_count == 2

        # Third spread
        rumor = rumor.spread_to("loc-3")
        assert rumor.truth_value == 70
        assert rumor.spread_count == 3


class TestRumorVeracity:
    """Test suite for Rumor veracity label and properties."""

    @pytest.mark.unit
    def test_veracity_label_confirmed(self):
        """Test veracity label for truth_value >= 80."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=80,
        )
        assert rumor.veracity_label == "Confirmed"

        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=100,
        )
        assert rumor.veracity_label == "Confirmed"

    @pytest.mark.unit
    def test_veracity_label_likely_true(self):
        """Test veracity label for truth_value 60-79."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=60,
        )
        assert rumor.veracity_label == "Likely True"

        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=79,
        )
        assert rumor.veracity_label == "Likely True"

    @pytest.mark.unit
    def test_veracity_label_uncertain(self):
        """Test veracity label for truth_value 40-59."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=40,
        )
        assert rumor.veracity_label == "Uncertain"

        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=59,
        )
        assert rumor.veracity_label == "Uncertain"

    @pytest.mark.unit
    def test_veracity_label_likely_false(self):
        """Test veracity label for truth_value 20-39."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=20,
        )
        assert rumor.veracity_label == "Likely False"

        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=39,
        )
        assert rumor.veracity_label == "Likely False"

    @pytest.mark.unit
    def test_veracity_label_false(self):
        """Test veracity label for truth_value 0-19."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=0,
        )
        assert rumor.veracity_label == "False"

        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=19,
        )
        assert rumor.veracity_label == "False"

    @pytest.mark.unit
    def test_is_dead_property(self):
        """Test is_dead property."""
        living_rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=1,
        )
        assert living_rumor.is_dead is False

        dead_rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=0,
        )
        assert dead_rumor.is_dead is True

    @pytest.mark.unit
    def test_veracity_color_confirmed(self):
        """Test veracity color for Confirmed."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=90,
        )
        assert rumor.veracity_color == "#22c55e"  # green

    @pytest.mark.unit
    def test_veracity_color_likely_true(self):
        """Test veracity color for Likely True."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=65,
        )
        assert rumor.veracity_color == "#84cc16"  # lime

    @pytest.mark.unit
    def test_veracity_color_uncertain(self):
        """Test veracity color for Uncertain."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=50,
        )
        assert rumor.veracity_color == "#eab308"  # yellow

    @pytest.mark.unit
    def test_veracity_color_likely_false(self):
        """Test veracity color for Likely False."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=25,
        )
        assert rumor.veracity_color == "#f97316"  # orange

    @pytest.mark.unit
    def test_veracity_color_false(self):
        """Test veracity color for False."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=10,
        )
        assert rumor.veracity_color == "#6b7280"  # gray


class TestRumorSerialization:
    """Test suite for Rumor serialization."""

    @pytest.mark.unit
    def test_to_dict(self):
        """Test to_dict returns correct dictionary."""
        calendar = WorldCalendar(1042, 3, 15, "Third Age")
        rumor = Rumor(
            rumor_id="rumor-123",
            content="Test rumor content",
            truth_value=75,
            origin_type=RumorOrigin.EVENT,
            source_event_id="event-456",
            origin_location_id="loc-origin",
            current_locations={"loc-origin", "loc-spread"},
            created_date=calendar,
            spread_count=2,
        )

        result = rumor.to_dict()

        assert result["rumor_id"] == "rumor-123"
        assert result["content"] == "Test rumor content"
        assert result["truth_value"] == 75
        assert result["origin_type"] == "event"
        assert result["source_event_id"] == "event-456"
        assert result["origin_location_id"] == "loc-origin"
        assert set(result["current_locations"]) == {"loc-origin", "loc-spread"}
        assert result["spread_count"] == 2
        assert result["veracity_label"] == "Likely True"
        assert result["is_dead"] is False

    @pytest.mark.unit
    def test_to_dict_with_none_source_event(self):
        """Test to_dict handles None source_event_id."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
        )

        result = rumor.to_dict()
        assert result["source_event_id"] is None

    @pytest.mark.unit
    def test_from_dict_with_all_fields(self):
        """Test from_dict creates rumor from complete dictionary."""
        calendar_dict = {
            "year": 1042,
            "month": 3,
            "day": 15,
            "era_name": "Third Age",
        }
        data = {
            "rumor_id": "rumor-123",
            "content": "Test rumor content",
            "truth_value": 80,
            "origin_type": "event",
            "source_event_id": "event-456",
            "origin_location_id": "loc-origin",
            "current_locations": ["loc-origin", "loc-spread"],
            "created_date": calendar_dict,
            "spread_count": 3,
        }

        rumor = Rumor.from_dict(data)

        assert rumor.rumor_id == "rumor-123"
        assert rumor.content == "Test rumor content"
        assert rumor.truth_value == 80
        assert rumor.origin_type == RumorOrigin.EVENT
        assert rumor.source_event_id == "event-456"
        assert rumor.origin_location_id == "loc-origin"
        assert rumor.current_locations == {"loc-origin", "loc-spread"}
        assert rumor.spread_count == 3

    @pytest.mark.unit
    def test_from_dict_with_defaults(self):
        """Test from_dict uses defaults for missing fields."""
        data = {
            "content": "Test rumor",
            "origin_location_id": "loc-123",
        }

        rumor = Rumor.from_dict(data)

        assert rumor.content == "Test rumor"
        assert rumor.origin_location_id == "loc-123"
        assert rumor.truth_value == 50  # Default
        assert rumor.origin_type == RumorOrigin.UNKNOWN  # Default
        assert rumor.source_event_id is None
        assert rumor.current_locations == set()
        assert rumor.spread_count == 0

    @pytest.mark.unit
    def test_from_dict_case_insensitive_origin_type(self):
        """Test from_dict handles case-insensitive origin_type."""
        data = {
            "content": "Test rumor",
            "origin_type": "NPC",
            "origin_location_id": "loc-123",
        }

        rumor = Rumor.from_dict(data)
        assert rumor.origin_type == RumorOrigin.NPC

    @pytest.mark.unit
    def test_from_dict_with_origin_type_enum(self):
        """Test from_dict handles RumorOrigin enum directly."""
        data = {
            "content": "Test rumor",
            "origin_type": RumorOrigin.PLAYER,
            "origin_location_id": "loc-123",
        }

        rumor = Rumor.from_dict(data)
        assert rumor.origin_type == RumorOrigin.PLAYER

    @pytest.mark.unit
    def test_roundtrip_serialization(self):
        """Test that to_dict -> from_dict preserves key data."""
        calendar = WorldCalendar(1042, 3, 15, "Third Age")
        original = Rumor(
            rumor_id="rumor-123",
            content="Test rumor content",
            truth_value=85,
            origin_type=RumorOrigin.EVENT,
            source_event_id="event-456",
            origin_location_id="loc-origin",
            current_locations={"loc-origin"},
            created_date=calendar,
            spread_count=1,
        )

        data = original.to_dict()
        restored = Rumor.from_dict(data)

        assert restored.rumor_id == original.rumor_id
        assert restored.content == original.content
        assert restored.truth_value == original.truth_value
        assert restored.origin_type == original.origin_type
        assert restored.source_event_id == original.source_event_id
        assert restored.origin_location_id == original.origin_location_id
        assert restored.current_locations == original.current_locations
        assert restored.spread_count == original.spread_count


class TestRumorStringRepresentation:
    """Test suite for Rumor string representations."""

    @pytest.mark.unit
    def test_str_representation_short_content(self):
        """Test __str__ returns expected format for short content."""
        rumor = Rumor(
            rumor_id="rumor-12345678",
            content="Short rumor",
            origin_location_id="loc-123",
            truth_value=90,
        )

        result = str(rumor)

        assert "Rumor" in result
        assert "Short rumor" in result
        assert "90%" in result
        assert "Confirmed" in result

    @pytest.mark.unit
    def test_str_representation_long_content(self):
        """Test __str__ truncates long content."""
        long_content = "This is a very long rumor that should be truncated in the string representation"
        rumor = Rumor(
            rumor_id="rumor-12345678",
            content=long_content,
            origin_location_id="loc-123",
            truth_value=50,
        )

        result = str(rumor)

        assert "..." in result  # Truncated
        assert len(result) < len(long_content) + 50  # Much shorter than full content

    @pytest.mark.unit
    def test_repr_representation(self):
        """Test __repr__ returns expected format."""
        rumor = Rumor(
            rumor_id="rumor-12345678",
            content="Test rumor",
            origin_location_id="loc-123",
            origin_type=RumorOrigin.EVENT,
            truth_value=75,
            spread_count=3,
        )

        result = repr(rumor)

        assert "Rumor" in result
        assert "event" in result
        assert "75%" in result
        assert "spread_count=3" in result


class TestRumorEquality:
    """Test suite for Rumor equality and hashing."""

    @pytest.mark.unit
    def test_equality_same_id(self):
        """Test rumors with same ID are equal."""
        rumor1 = Rumor(
            rumor_id="rumor-123",
            content="Test rumor",
            origin_location_id="loc-123",
            truth_value=90,
        )

        rumor2 = Rumor(
            rumor_id="rumor-123",
            content="Different content",
            origin_location_id="loc-456",
            truth_value=50,
        )

        # Same ID = equal (even with different content)
        assert rumor1 == rumor2

    @pytest.mark.unit
    def test_inequality_different_id(self):
        """Test rumors with different IDs are not equal."""
        rumor1 = Rumor(
            rumor_id="rumor-123",
            content="Test rumor",
            origin_location_id="loc-123",
        )

        rumor2 = Rumor(
            rumor_id="rumor-456",
            content="Test rumor",
            origin_location_id="loc-123",
        )

        assert rumor1 != rumor2

    @pytest.mark.unit
    def test_equality_with_non_rumor(self):
        """Test equality with non-Rumor object returns False."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
        )

        assert rumor != "not a rumor"
        assert rumor != 123
        assert rumor is not None

    @pytest.mark.unit
    def test_hash_consistency(self):
        """Test that rumors with same ID have same hash."""
        rumor1 = Rumor(
            rumor_id="rumor-123",
            content="Test rumor 1",
            origin_location_id="loc-123",
        )

        rumor2 = Rumor(
            rumor_id="rumor-123",
            content="Test rumor 2",
            origin_location_id="loc-456",
        )

        assert hash(rumor1) == hash(rumor2)

    @pytest.mark.unit
    def test_can_be_used_in_set(self):
        """Test that rumors can be used in sets."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
        )

        # Should not raise TypeError
        rumor_set = {rumor}
        assert rumor in rumor_set

    @pytest.mark.unit
    def test_can_be_used_as_dict_key(self):
        """Test that rumors can be used as dict keys."""
        rumor = Rumor(
            content="Test rumor",
            origin_location_id="loc-123",
        )

        # Should not raise TypeError
        rumor_dict = {rumor: "value"}
        assert rumor_dict[rumor] == "value"

    @pytest.mark.unit
    def test_set_deduplication_by_id(self):
        """Test that set deduplicates rumors by ID."""
        rumor1 = Rumor(
            rumor_id="rumor-123",
            content="Content 1",
            origin_location_id="loc-123",
        )

        rumor2 = Rumor(
            rumor_id="rumor-123",
            content="Content 2",
            origin_location_id="loc-456",
        )

        rumor_set = {rumor1, rumor2}
        assert len(rumor_set) == 1  # Only one because same ID


class TestRumorConstants:
    """Test suite for module constants."""

    @pytest.mark.unit
    def test_truth_decay_per_hop(self):
        """Test TRUTH_DECAY_PER_HOP constant."""
        assert TRUTH_DECAY_PER_HOP == 10

    @pytest.mark.unit
    def test_veracity_thresholds(self):
        """Test veracity threshold constants."""
        assert VERACITY_CONFIRMED == 80
        assert VERACITY_LIKELY_TRUE == 60
        assert VERACITY_UNCERTAIN == 40
        assert VERACITY_LIKELY_FALSE == 20
