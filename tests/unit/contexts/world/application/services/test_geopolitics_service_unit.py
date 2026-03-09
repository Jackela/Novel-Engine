#!/usr/bin/env python3
"""Tests for GeopoliticsService.

Unit tests covering:
- War declarations between factions
- Alliance formation
- Territory transfers
- Diplomacy summary retrieval
- Event emission
"""

from unittest.mock import MagicMock, patch

import pytest

from src.contexts.world.application.services.geopolitics_service import (
    GeopoliticsService,
)
from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.entities.location import Location, LocationType
from src.contexts.world.domain.events.geopolitics_events import (
    AllianceFormedEvent,
    PactType,
    TerritoryChangedEvent,
    WarDeclaredEvent,
)
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus

pytestmark = pytest.mark.unit


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_event_bus() -> MagicMock:
    """Create a mock event bus."""
    bus = MagicMock()
    bus.publish = MagicMock()
    return bus


@pytest.fixture
def service(mock_event_bus: MagicMock) -> GeopoliticsService:
    """Create a GeopoliticsService with a mock event bus."""
    return GeopoliticsService(event_bus=mock_event_bus)


@pytest.fixture
def diplomacy_matrix() -> DiplomacyMatrix:
    """Create a test diplomacy matrix with two factions."""
    matrix = DiplomacyMatrix(world_id="world-123")
    matrix.register_faction("faction-a")
    matrix.register_faction("faction-b")
    matrix.register_faction("faction-c")
    return matrix


@pytest.fixture
def location() -> Location:
    """Create a test location."""
    return Location(
        name="Thornhaven",
        location_type=LocationType.CITY,
        controlling_faction_id="faction-a",
    )


# ============================================================================
# Test declare_war
# ============================================================================


class TestDeclareWar:
    """Tests for declare_war method."""

    def test_declare_war_success(
        self,
        service: GeopoliticsService,
        diplomacy_matrix: DiplomacyMatrix,
        mock_event_bus: MagicMock,
    ) -> None:
        """Should successfully declare war between two factions."""
        result = service.declare_war(
            matrix=diplomacy_matrix,
            aggressor_id="faction-a",
            defender_id="faction-b",
            reason="Territorial dispute",
        )

        assert result.is_ok
        assert diplomacy_matrix.get_status("faction-a", "faction-b") == DiplomaticStatus.AT_WAR
        mock_event_bus.publish.assert_called_once()

        # Verify event type
        event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(event, WarDeclaredEvent)
        assert event.aggressor_id == "faction-a"
        assert event.defender_id == "faction-b"
        assert event.reason == "Territorial dispute"

    def test_declare_war_with_world_id(
        self,
        service: GeopoliticsService,
        diplomacy_matrix: DiplomacyMatrix,
        mock_event_bus: MagicMock,
    ) -> None:
        """Should include world_id in the event."""
        result = service.declare_war(
            matrix=diplomacy_matrix,
            aggressor_id="faction-a",
            defender_id="faction-b",
            reason="Test war",
            world_id="custom-world",
        )

        assert result.is_ok
        event = mock_event_bus.publish.call_args[0][0]
        assert event.world_id == "custom-world"

    def test_declare_war_same_faction(
        self,
        service: GeopoliticsService,
        diplomacy_matrix: DiplomacyMatrix,
        mock_event_bus: MagicMock,
    ) -> None:
        """Should fail when trying to declare war on self."""
        result = service.declare_war(
            matrix=diplomacy_matrix,
            aggressor_id="faction-a",
            defender_id="faction-a",
            reason="Self conflict",
        )

        assert result.is_error
        mock_event_bus.publish.assert_not_called()

    def test_declare_war_updates_matrix(
        self,
        service: GeopoliticsService,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """Should update diplomatic status to AT_WAR."""
        service.declare_war(
            matrix=diplomacy_matrix,
            aggressor_id="faction-a",
            defender_id="faction-b",
            reason="Test",
        )

        status = diplomacy_matrix.get_status("faction-a", "faction-b")
        assert status == DiplomaticStatus.AT_WAR


# ============================================================================
# Test form_alliance
# ============================================================================


class TestFormAlliance:
    """Tests for form_alliance method."""

    def test_form_alliance_success(
        self,
        service: GeopoliticsService,
        diplomacy_matrix: DiplomacyMatrix,
        mock_event_bus: MagicMock,
    ) -> None:
        """Should successfully form an alliance between two factions."""
        result = service.form_alliance(
            matrix=diplomacy_matrix,
            faction_a_id="faction-a",
            faction_b_id="faction-b",
        )

        assert result.is_ok
        assert diplomacy_matrix.get_status("faction-a", "faction-b") == DiplomaticStatus.ALLIED
        mock_event_bus.publish.assert_called_once()

        event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(event, AllianceFormedEvent)
        assert event.faction_a_id == "faction-a"
        assert event.faction_b_id == "faction-b"

    def test_form_alliance_default_pact_type(
        self,
        service: GeopoliticsService,
        diplomacy_matrix: DiplomacyMatrix,
        mock_event_bus: MagicMock,
    ) -> None:
        """Should use DEFENSIVE_ALLIANCE as default pact type."""
        result = service.form_alliance(
            matrix=diplomacy_matrix,
            faction_a_id="faction-a",
            faction_b_id="faction-b",
        )

        assert result.is_ok
        event = mock_event_bus.publish.call_args[0][0]
        assert event.pact_type == PactType.DEFENSIVE_ALLIANCE

    def test_form_alliance_custom_pact_type(
        self,
        service: GeopoliticsService,
        diplomacy_matrix: DiplomacyMatrix,
        mock_event_bus: MagicMock,
    ) -> None:
        """Should allow specifying pact type."""
        result = service.form_alliance(
            matrix=diplomacy_matrix,
            faction_a_id="faction-a",
            faction_b_id="faction-b",
            pact_type=PactType.OFFENSIVE_ALLIANCE,
        )

        assert result.is_ok
        event = mock_event_bus.publish.call_args[0][0]
        assert event.pact_type == PactType.OFFENSIVE_ALLIANCE

    def test_form_alliance_while_at_war(
        self,
        service: GeopoliticsService,
        diplomacy_matrix: DiplomacyMatrix,
        mock_event_bus: MagicMock,
    ) -> None:
        """Should fail to form alliance between warring factions."""
        # First set them at war
        diplomacy_matrix.set_status("faction-a", "faction-b", DiplomaticStatus.AT_WAR)

        result = service.form_alliance(
            matrix=diplomacy_matrix,
            faction_a_id="faction-a",
            faction_b_id="faction-b",
        )

        assert result.is_error
        assert "at war" in str(result.error).lower()
        mock_event_bus.publish.assert_not_called()

    def test_form_alliance_same_faction(
        self,
        service: GeopoliticsService,
        diplomacy_matrix: DiplomacyMatrix,
        mock_event_bus: MagicMock,
    ) -> None:
        """Should fail when trying to form alliance with self."""
        result = service.form_alliance(
            matrix=diplomacy_matrix,
            faction_a_id="faction-a",
            faction_b_id="faction-a",
        )

        assert result.is_error
        mock_event_bus.publish.assert_not_called()


# ============================================================================
# Test transfer_territory
# ============================================================================


class TestTransferTerritory:
    """Tests for transfer_territory method."""

    def test_transfer_territory_success(
        self,
        service: GeopoliticsService,
        location: Location,
        mock_event_bus: MagicMock,
    ) -> None:
        """Should successfully transfer territory control."""
        result = service.transfer_territory(
            location=location,
            new_controller_id="faction-b",
            reason="Conquest",
        )

        assert result.is_ok
        assert location.controlling_faction_id == "faction-b"
        mock_event_bus.publish.assert_called_once()

        event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(event, TerritoryChangedEvent)
        assert event.location_id == location.id
        assert event.previous_controller_id == "faction-a"
        assert event.new_controller_id == "faction-b"
        assert event.reason == "Conquest"

    def test_transfer_territory_to_none(
        self,
        service: GeopoliticsService,
        location: Location,
        mock_event_bus: MagicMock,
    ) -> None:
        """Should raise ValueError when new_controller_id is None."""
        # The service validates that new_controller_id is not empty/None
        with pytest.raises(ValueError, match="cannot be empty"):
            service.transfer_territory(
                location=location,
                new_controller_id=None,
                reason="Abandoned",
            )

        # No event should be published when validation fails
        mock_event_bus.publish.assert_not_called()

    def test_transfer_territory_with_world_id(
        self,
        service: GeopoliticsService,
        location: Location,
        mock_event_bus: MagicMock,
    ) -> None:
        """Should include world_id in event."""
        result = service.transfer_territory(
            location=location,
            new_controller_id="faction-b",
            world_id="world-456",
        )

        assert result.is_ok
        event = mock_event_bus.publish.call_args[0][0]
        assert event.world_id == "world-456"

    def test_transfer_territory_uses_transfer_control(
        self,
        service: GeopoliticsService,
        mock_event_bus: MagicMock,
    ) -> None:
        """Should use transfer_control method when available."""
        location = Location(
            name="Test City",
            location_type=LocationType.CITY,
            controlling_faction_id="faction-a",
        )

        # transfer_control is available on Location
        result = service.transfer_territory(
            location=location,
            new_controller_id="faction-b",
        )

        assert result.is_ok
        assert location.controlling_faction_id == "faction-b"
        # contested_by should be cleared by transfer_control
        assert len(location.contested_by) == 0


# ============================================================================
# Test get_diplomacy_summary
# ============================================================================


class TestGetDiplomacySummary:
    """Tests for get_diplomacy_summary method."""

    def test_get_diplomacy_summary_basic(
        self,
        service: GeopoliticsService,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """Should return a summary with allies, enemies, and neutral."""
        # Set up relations
        diplomacy_matrix.set_status("faction-a", "faction-b", DiplomaticStatus.ALLIED)
        diplomacy_matrix.set_status("faction-a", "faction-c", DiplomaticStatus.AT_WAR)

        summary = service.get_diplomacy_summary(diplomacy_matrix, "faction-a")

        assert summary.unwrap()["faction_id"] == "faction-a"
        assert "faction-b" in summary.unwrap()["allies"]
        assert "faction-c" in summary.unwrap()["enemies"]

    def test_get_diplomacy_summary_no_relations(
        self,
        service: GeopoliticsService,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """Should return empty lists when no relations exist."""
        summary = service.get_diplomacy_summary(diplomacy_matrix, "faction-a")

        assert summary.unwrap()["faction_id"] == "faction-a"
        assert summary.unwrap()["allies"] == []
        assert summary.unwrap()["enemies"] == []
        assert summary.unwrap()["neutral"] == []

    def test_get_diplomacy_summary_neutral_factions(
        self,
        service: GeopoliticsService,
        diplomacy_matrix: DiplomacyMatrix,
    ) -> None:
        """Should include neutral factions in summary."""
        diplomacy_matrix.set_status("faction-a", "faction-b", DiplomaticStatus.NEUTRAL)

        summary = service.get_diplomacy_summary(diplomacy_matrix, "faction-a")

        assert "faction-b" in summary.unwrap()["neutral"]


# ============================================================================
# Test Event Bus Initialization
# ============================================================================


class TestEventBusInitialization:
    """Tests for event bus initialization."""

    def test_default_event_bus(self) -> None:
        """Should create default EventBus if none provided."""
        with patch(
            "src.contexts.world.application.services.geopolitics_service.EventBus"
        ) as mock_bus_class:
            mock_instance = MagicMock()
            mock_bus_class.return_value = mock_instance

            service = GeopoliticsService()

            mock_bus_class.assert_called_once()
            assert service._event_bus == mock_instance

    def test_custom_event_bus(self, mock_event_bus: MagicMock) -> None:
        """Should use provided EventBus."""
        service = GeopoliticsService(event_bus=mock_event_bus)
        assert service._event_bus == mock_event_bus
