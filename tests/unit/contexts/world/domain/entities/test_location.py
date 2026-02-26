"""Unit tests for Location entity territory control features.

Tests cover the new territory control fields and methods added for PREP-006.
"""

import pytest

from src.contexts.world.domain.entities import (
    ClimateType,
    Location,
    LocationStatus,
    LocationType,
)
from src.contexts.world.domain.value_objects import ResourceType, ResourceYield


pytestmark = pytest.mark.unit


class TestLocationTerritoryControl:
    """Tests for territory control functionality."""

    def test_location_with_territory_fields(self) -> None:
        """Test creating a location with territory control fields."""
        location = Location(
            name="Strategic Fortress",
            location_type=LocationType.FORTRESS,
            controlling_faction_id="faction-123",
            territory_value=80,
            infrastructure_level=60,
        )
        assert location.controlling_faction_id == "faction-123"
        assert location.territory_value == 80
        assert location.infrastructure_level == 60
        assert location.contested_by == []

    def test_transfer_control(self) -> None:
        """Test transferring control between factions."""
        location = Location(
            name="Border Town",
            controlling_faction_id="faction-123",
            contested_by=["faction-456", "faction-789"],
        )

        location.transfer_control("faction-456")

        assert location.controlling_faction_id == "faction-456"
        assert location.contested_by == []  # Should be cleared on transfer

    def test_transfer_control_empty_faction_raises_error(self) -> None:
        """Test that transferring to empty faction raises error."""
        location = Location(name="Town", controlling_faction_id="faction-123")

        with pytest.raises(ValueError, match="New faction ID cannot be empty"):
            location.transfer_control("")

    def test_add_contender(self) -> None:
        """Test adding a contender for control."""
        location = Location(
            name="Disputed Territory",
            controlling_faction_id="faction-123",
        )

        location.add_contender("faction-456")
        location.add_contender("faction-789")

        assert "faction-456" in location.contested_by
        assert "faction-789" in location.contested_by

    def test_add_contender_already_controller_raises_error(self) -> None:
        """Test that adding the controller as contender raises error."""
        location = Location(
            name="Territory",
            controlling_faction_id="faction-123",
        )

        with pytest.raises(ValueError, match="Cannot add controlling faction as contender"):
            location.add_contender("faction-123")

    def test_remove_contender(self) -> None:
        """Test removing a contender."""
        location = Location(
            name="Territory",
            controlling_faction_id="faction-123",
            contested_by=["faction-456", "faction-789"],
        )

        result = location.remove_contender("faction-456")

        assert result is True
        assert "faction-456" not in location.contested_by
        assert "faction-789" in location.contested_by

    def test_remove_contender_not_found(self) -> None:
        """Test removing a contender that doesn't exist."""
        location = Location(
            name="Territory",
            controlling_faction_id="faction-123",
        )

        result = location.remove_contender("faction-999")

        assert result is False

    def test_is_contested(self) -> None:
        """Test is_contested check."""
        contested = Location(
            name="Territory",
            controlling_faction_id="faction-123",
            contested_by=["faction-456"],
        )
        assert contested.is_contested() is True

        uncontested = Location(
            name="Territory",
            controlling_faction_id="faction-123",
        )
        assert uncontested.is_contested() is False

    def test_set_controlling_faction_removes_from_contested(self) -> None:
        """Test that setting controller removes it from contested list if present."""
        # Create location with controller and contested (different factions)
        location = Location(
            name="Territory",
            controlling_faction_id="faction-123",
            contested_by=["faction-456", "faction-789"],
        )

        # When we set a new controller that was in contested, it should be removed
        location.contested_by.append("faction-abc")  # Add new controller manually (bypassing validation)
        location.set_controlling_faction("faction-abc")

        assert location.controlling_faction_id == "faction-abc"
        assert "faction-abc" not in location.contested_by


class TestLocationResourceYields:
    """Tests for resource yield functionality."""

    def test_add_resource_yield(self) -> None:
        """Test adding a resource yield to a location."""
        location = Location(name="Mining Town")
        gold_yield = ResourceYield(
            resource_type=ResourceType.GOLD,
            base_amount=100,
            modifier=1.5,
        )

        location.add_resource_yield(gold_yield)

        assert len(location.resource_yields) == 1
        assert location.resource_yields[0].resource_type == ResourceType.GOLD

    def test_add_resource_yield_replaces_same_type(self) -> None:
        """Test that adding a yield replaces existing yield of same type."""
        location = Location(name="Mining Town")

        old_yield = ResourceYield(
            resource_type=ResourceType.GOLD,
            base_amount=50,
        )
        location.add_resource_yield(old_yield)

        new_yield = ResourceYield(
            resource_type=ResourceType.GOLD,
            base_amount=100,
        )
        location.add_resource_yield(new_yield)

        assert len(location.resource_yields) == 1
        assert location.resource_yields[0].base_amount == 100

    def test_get_resource_yield(self) -> None:
        """Test getting a specific resource yield."""
        location = Location(
            name="Town",
            resource_yields=[
                ResourceYield(resource_type=ResourceType.GOLD, base_amount=100),
                ResourceYield(resource_type=ResourceType.FOOD, base_amount=50),
            ],
        )

        gold_yield = location.get_resource_yield(ResourceType.GOLD)
        assert gold_yield is not None
        assert gold_yield.base_amount == 100

        iron_yield = location.get_resource_yield(ResourceType.IRON)
        assert iron_yield is None

    def test_collect_resources(self) -> None:
        """Test collecting all resource yields."""
        location = Location(
            name="Town",
            resource_yields=[
                ResourceYield(resource_type=ResourceType.GOLD, base_amount=100, modifier=1.0),
                ResourceYield(resource_type=ResourceType.FOOD, base_amount=50, modifier=2.0),
            ],
        )

        collected = location.collect_resources()

        assert collected["gold"] == 100
        assert collected["food"] == 100  # 50 * 2.0


class TestLocationInfrastructure:
    """Tests for infrastructure functionality."""

    def test_upgrade_infrastructure(self) -> None:
        """Test upgrading infrastructure level."""
        location = Location(
            name="Town",
            infrastructure_level=10,
        )

        location.upgrade_infrastructure(5)

        assert location.infrastructure_level == 15

    def test_upgrade_infrastructure_exceeds_max_raises_error(self) -> None:
        """Test that upgrading past 100 raises error."""
        location = Location(
            name="Town",
            infrastructure_level=98,
        )

        with pytest.raises(ValueError, match="Infrastructure level cannot exceed 100"):
            location.upgrade_infrastructure(5)

    def test_set_territory_value(self) -> None:
        """Test setting territory value."""
        location = Location(name="Strategic Point")

        location.set_territory_value(75)

        assert location.territory_value == 75

    def test_set_territory_value_out_of_range_raises_error(self) -> None:
        """Test that invalid territory value raises error."""
        location = Location(name="Point")

        with pytest.raises(ValueError, match="Territory value must be between 0 and 100"):
            location.set_territory_value(150)

        with pytest.raises(ValueError, match="Territory value must be between 0 and 100"):
            location.set_territory_value(-10)


class TestLocationValidation:
    """Tests for territory control validation."""

    def test_invalid_territory_value_raises_error(self) -> None:
        """Test that invalid territory value raises validation error."""
        with pytest.raises(ValueError, match="Territory value must be between 0 and 100"):
            Location(
                name="Test",
                territory_value=150,
            )

    def test_invalid_infrastructure_level_raises_error(self) -> None:
        """Test that invalid infrastructure level raises validation error."""
        with pytest.raises(ValueError, match="Infrastructure level must be between 0 and 100"):
            Location(
                name="Test",
                infrastructure_level=-5,
            )

    def test_controller_in_contested_raises_error(self) -> None:
        """Test that having controller in contested list raises validation error."""
        with pytest.raises(ValueError, match="should not be in contested_by list"):
            Location(
                name="Test",
                controlling_faction_id="faction-123",
                contested_by=["faction-123"],
            )
