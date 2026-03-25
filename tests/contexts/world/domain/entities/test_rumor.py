"""Tests for the Rumor entity.

This module contains comprehensive tests for the Rumor domain entity,
covering rumor creation, spreading, and truth value decay.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest

from src.contexts.world.domain.entities.rumor import Rumor, RumorOrigin


@pytest.fixture
def valid_rumor() -> Rumor:
    """Create a valid rumor for testing."""
    return Rumor(
        content="The king is secretly ill",
        truth_value=80,
        origin_type=RumorOrigin.NPC,
        origin_location_id="loc-castle",
        current_locations={"loc-castle"},
    )


class TestRumor:
    """Test cases for Rumor entity."""

    def test_create_rumor_with_valid_data(self) -> None:
        """Test rumor creation with valid data."""
        rumor = Rumor(
            content="A dragon was spotted in the mountains",
            truth_value=60,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc-mountains",
            current_locations={"loc-mountains", "loc-village"},
            created_date=datetime(2024, 1, 1),
            spread_count=5,
            source_event_id="event-123",
        )

        assert rumor.content == "A dragon was spotted in the mountains"
        assert rumor.truth_value == 60
        assert rumor.origin_type == RumorOrigin.EVENT
        assert rumor.origin_location_id == "loc-mountains"
        assert rumor.current_locations == {"loc-mountains", "loc-village"}
        assert rumor.created_date == datetime(2024, 1, 1)
        assert rumor.spread_count == 5
        assert rumor.source_event_id == "event-123"
        assert isinstance(rumor.rumor_id, str)

    def test_create_rumor_with_minimal_data(self) -> None:
        """Test rumor creation with minimal data."""
        rumor = Rumor(
            content="Simple rumor",
            truth_value=50,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="loc-town",
        )

        assert rumor.current_locations == set()  # Default
        assert rumor.created_date is None
        assert rumor.spread_count == 0
        assert rumor.source_event_id is None

    def test_create_rumor_generates_id(self) -> None:
        """Test that rumor auto-generates ID."""
        rumor1 = Rumor(
            content="Rumor 1",
            truth_value=50,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="loc-1",
        )
        rumor2 = Rumor(
            content="Rumor 2",
            truth_value=50,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="loc-2",
        )

        assert rumor1.rumor_id is not None
        assert rumor2.rumor_id is not None
        assert rumor1.rumor_id != rumor2.rumor_id

        # Should be valid UUID string
        assert UUID(rumor1.rumor_id)
        assert UUID(rumor2.rumor_id)


class TestRumorOrigins:
    """Test cases for rumor origins."""

    def test_origin_types(self) -> None:
        """Test all origin types can be used."""
        origins = [
            (RumorOrigin.EVENT, "event"),
            (RumorOrigin.NPC, "npc"),
            (RumorOrigin.PLAYER, "player"),
            (RumorOrigin.UNKNOWN, "unknown"),
        ]

        for origin, _ in origins:
            rumor = Rumor(
                content=f"Rumor from {origin}",
                truth_value=50,
                origin_type=origin,
                origin_location_id="loc-test",
            )
            assert rumor.origin_type == origin


class TestRumorSpreading:
    """Test cases for rumor spreading."""

    def test_spread_to_new_location(self, valid_rumor: Rumor) -> None:
        """Test spreading rumor to a new location."""
        original_truth = valid_rumor.truth_value
        original_locations = valid_rumor.current_locations.copy()

        spread_rumor = valid_rumor.spread_to("loc-tavern")

        # Should create new rumor instance
        assert spread_rumor is not valid_rumor

        # Should preserve content and ID
        assert spread_rumor.content == valid_rumor.content
        assert spread_rumor.rumor_id == valid_rumor.rumor_id

        # Should add new location
        assert "loc-tavern" in spread_rumor.current_locations
        assert original_locations.issubset(spread_rumor.current_locations)

        # Truth should decay
        assert spread_rumor.truth_value == original_truth - 10

        # Spread count should increment
        assert spread_rumor.spread_count == valid_rumor.spread_count + 1

    def test_spread_to_existing_location_returns_same(self, valid_rumor: Rumor) -> None:
        """Test spreading to already reached location returns same rumor."""
        # Add location first
        valid_rumor.current_locations.add("loc-tavern")

        # Try to spread to same location
        result = valid_rumor.spread_to("loc-tavern")

        # Should return same instance (no change)
        assert result is valid_rumor
        assert result.truth_value == valid_rumor.truth_value
        assert result.spread_count == valid_rumor.spread_count

    def test_spread_multiple_times(self, valid_rumor: Rumor) -> None:
        """Test spreading rumor multiple times."""
        rumor = valid_rumor

        # Spread to multiple locations
        locations = ["loc-tavern", "loc-market", "loc-dock", "loc-temple"]
        for location in locations:
            rumor = rumor.spread_to(location)

        assert len(rumor.current_locations) == 5  # Original + 4 new
        assert rumor.spread_count == 4
        assert rumor.truth_value == 40  # 80 - (4 * 10)

    def test_spread_until_dead(self, valid_rumor: Rumor) -> None:
        """Test spreading rumor until it dies (truth value reaches 0)."""
        # Start with truth_value of 10
        rumor = Rumor(
            content="Weak rumor",
            truth_value=10,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="loc-start",
            current_locations={"loc-start"},
        )

        # Spread once - should become 0
        rumor = rumor.spread_to("loc-tavern")

        assert rumor.truth_value == 0
        assert rumor.is_dead is True

    def test_spread_preserves_all_fields(self, valid_rumor: Rumor) -> None:
        """Test that spreading preserves all relevant fields."""
        spread_rumor = valid_rumor.spread_to("loc-tavern")

        assert spread_rumor.origin_type == valid_rumor.origin_type
        assert spread_rumor.origin_location_id == valid_rumor.origin_location_id
        assert spread_rumor.source_event_id == valid_rumor.source_event_id
        assert spread_rumor.created_date == valid_rumor.created_date


class TestRumorTruthValue:
    """Test cases for truth value management."""

    def test_is_dead_property_when_alive(self, valid_rumor: Rumor) -> None:
        """Test is_dead property when rumor is alive."""
        assert valid_rumor.truth_value > 0
        assert valid_rumor.is_dead is False

    def test_is_dead_property_when_dead(self, valid_rumor: Rumor) -> None:
        """Test is_dead property when rumor is dead."""
        valid_rumor.truth_value = 0
        assert valid_rumor.is_dead is True

    def test_is_dead_property_when_negative(self, valid_rumor: Rumor) -> None:
        """Test is_dead property with negative truth value."""
        valid_rumor.truth_value = -10
        assert valid_rumor.is_dead is True

    def test_truth_value_bounds(self) -> None:
        """Test truth value at boundaries."""
        # Maximum truth value
        high_truth = Rumor(
            content="Very true",
            truth_value=100,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc-1",
        )
        assert high_truth.truth_value == 100
        assert high_truth.is_dead is False

        # Minimum truth value before death
        low_truth = Rumor(
            content="Barely alive",
            truth_value=1,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="loc-1",
        )
        assert low_truth.truth_value == 1
        assert low_truth.is_dead is False

        # Dead rumor
        dead = Rumor(
            content="Dead",
            truth_value=0,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="loc-1",
        )
        assert dead.truth_value == 0
        assert dead.is_dead is True


class TestRumorLocations:
    """Test cases for location tracking."""

    def test_current_locations_is_set(self, valid_rumor: Rumor) -> None:
        """Test that current_locations is a set."""
        assert isinstance(valid_rumor.current_locations, set)

    def test_multiple_locations(self) -> None:
        """Test rumor with multiple current locations."""
        rumor = Rumor(
            content="Widespread rumor",
            truth_value=70,
            origin_type=RumorOrigin.EVENT,
            origin_location_id="loc-origin",
            current_locations={"loc-a", "loc-b", "loc-c", "loc-d"},
        )

        assert len(rumor.current_locations) == 4
        assert "loc-a" in rumor.current_locations
        assert "loc-b" in rumor.current_locations

    def test_locations_independence(self) -> None:
        """Test that location sets are independent between rumors."""
        rumor1 = Rumor(
            content="Rumor 1",
            truth_value=50,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="loc-1",
            current_locations={"loc-a"},
        )
        rumor2 = Rumor(
            content="Rumor 2",
            truth_value=50,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="loc-2",
            current_locations={"loc-b"},
        )

        assert rumor1.current_locations != rumor2.current_locations
        assert "loc-a" not in rumor2.current_locations
        assert "loc-b" not in rumor1.current_locations


class TestRumorInvariants:
    """Test cases for invariant validation."""

    def test_rumor_always_has_id(self) -> None:
        """Test that rumor always has an ID."""
        rumor = Rumor(
            content="Test",
            truth_value=50,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="loc-1",
        )

        assert rumor.rumor_id is not None
        assert len(rumor.rumor_id) > 0

    def test_rumor_always_has_content(self) -> None:
        """Test that rumor always has content."""
        rumor = Rumor(
            content="Must have content",
            truth_value=50,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="loc-1",
        )

        assert rumor.content
        assert len(rumor.content) > 0

    def test_rumor_always_has_origin_location(self) -> None:
        """Test that rumor always has origin location."""
        rumor = Rumor(
            content="Test",
            truth_value=50,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="origin-loc",
        )

        assert rumor.origin_location_id == "origin-loc"

    def test_rumor_spread_count_non_negative(self) -> None:
        """Test that spread_count is never negative."""
        rumor = Rumor(
            content="Test",
            truth_value=50,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="loc-1",
        )

        assert rumor.spread_count >= 0

    def test_rumor_equality(self) -> None:
        """Test rumor equality (default dataclass equality)."""
        rumor1 = Rumor(
            content="Same content",
            truth_value=50,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="loc-1",
        )
        rumor2 = Rumor(
            content="Same content",
            truth_value=50,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="loc-1",
        )

        # Should not be equal because IDs are different
        assert rumor1 != rumor2

    def test_rumor_hash(self) -> None:
        """Test rumor can be hashed (default dataclass behavior)."""
        rumor = Rumor(
            content="Test",
            truth_value=50,
            origin_type=RumorOrigin.UNKNOWN,
            origin_location_id="loc-1",
        )
        # Should be hashable (can be added to set)
        rumor_set = {rumor}
        assert len(rumor_set) == 1
        assert rumor in rumor_set

    def test_truth_decay_constant(self) -> None:
        """Test truth decay per hop constant."""
        from src.contexts.world.domain.entities.rumor import TRUTH_DECAY_PER_HOP

        assert TRUTH_DECAY_PER_HOP == 10
