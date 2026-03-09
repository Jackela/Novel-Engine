"""Unit tests for geopolitics domain events."""

import pytest

pytestmark = pytest.mark.unit

from src.contexts.world.domain.events.geopolitics_events import (
    AllianceFormedEvent,
    PactType,
    TerritoryChangedEvent,
    WarDeclaredEvent,
)


@pytest.mark.unit
class TestWarDeclaredEvent:
    """Tests for WarDeclaredEvent."""

    def test_create_war_declared_event(self) -> None:
        """Test creating a war declared event."""
        event = WarDeclaredEvent.create(
            aggressor_id="faction_a",
            defender_id="faction_b",
            reason="Territorial dispute",
            world_id="world_1",
        )

        assert event.aggressor_id == "faction_a"
        assert event.defender_id == "faction_b"
        assert event.reason == "Territorial dispute"
        assert event.event_type == "geopolitics.war_declared"
        assert "world:world_1" in event.tags

    def test_war_event_has_high_priority(self) -> None:
        """War events should have high priority."""
        from src.events.event_bus import EventPriority

        event = WarDeclaredEvent.create(
            aggressor_id="f1", defender_id="f2", reason="test"
        )
        assert event.priority == EventPriority.HIGH


@pytest.mark.unit
class TestAllianceFormedEvent:
    """Tests for AllianceFormedEvent."""

    def test_create_alliance_event(self) -> None:
        """Test creating an alliance formed event."""
        event = AllianceFormedEvent.create(
            faction_a_id="faction_a",
            faction_b_id="faction_b",
            pact_type=PactType.DEFENSIVE_ALLIANCE,
            world_id="world_1",
        )

        assert event.faction_a_id == "faction_a"
        assert event.faction_b_id == "faction_b"
        assert event.pact_type == PactType.DEFENSIVE_ALLIANCE
        assert event.event_type == "geopolitics.alliance_formed"


@pytest.mark.unit
class TestTerritoryChangedEvent:
    """Tests for TerritoryChangedEvent."""

    def test_create_territory_changed_event(self) -> None:
        """Test creating a territory changed event."""
        event = TerritoryChangedEvent.create(
            location_id="loc_1",
            previous_controller_id="faction_a",
            new_controller_id="faction_b",
            world_id="world_1",
            reason="Military conquest",
        )

        assert event.location_id == "loc_1"
        assert event.previous_controller_id == "faction_a"
        assert event.new_controller_id == "faction_b"
        assert event.reason == "Military conquest"
        assert event.event_type == "geopolitics.territory_changed"

    def test_territory_event_with_none_previous_controller(self) -> None:
        """Territory can be claimed from uncontrolled state."""
        event = TerritoryChangedEvent.create(
            location_id="loc_1",
            previous_controller_id=None,
            new_controller_id="faction_a",
            world_id="world_1",
        )

        assert event.previous_controller_id is None
        assert event.new_controller_id == "faction_a"
