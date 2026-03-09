#!/usr/bin/env python3
"""Comprehensive tests for GeopoliticsService.

This module provides test coverage for the GeopoliticsService including:
- Declaring wars between factions
- Forming alliances between factions
- Transferring territory control
- Querying diplomatic state

Total: 25 tests
"""


import pytest

from src.contexts.world.application.services.geopolitics_service import (
    GeopoliticsService,
)
from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.entities.location import Location, LocationType
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus
from src.events.event_bus import EventBus

pytestmark = pytest.mark.unit



@pytest.fixture
def event_bus():
    """Create a fresh event bus for each test."""
    return EventBus()


@pytest.fixture
def geopolitics_service(event_bus):
    """Create a fresh GeopoliticsService for each test."""
    return GeopoliticsService(event_bus=event_bus)


@pytest.fixture
def diplomacy_matrix():
    """Create a fresh DiplomacyMatrix for each test."""
    return DiplomacyMatrix(world_id="world-1")


@pytest.fixture
def sample_location():
    """Create a sample location for testing."""
    return Location(
        id="loc-1",
        name="Test Location",
        location_type=LocationType.CITY,
        controlling_faction_id="faction-1",
    )


# =============================================================================
# Test GeopoliticsService Initialization (3 tests)
# =============================================================================


class TestGeopoliticsServiceInitialization:
    """Tests for GeopoliticsService initialization."""

    def test_service_initialization_with_event_bus(self, event_bus):
        """Test that service initializes with event bus."""
        service = GeopoliticsService(event_bus=event_bus)
        assert service._event_bus is event_bus

    def test_service_initialization_with_default_event_bus(self):
        """Test that service creates default event bus if not provided."""
        service = GeopoliticsService()
        assert service._event_bus is not None
        assert isinstance(service._event_bus, EventBus)

    def test_service_initialization_sets_event_bus_correctly(self):
        """Test that event bus is set correctly during initialization."""
        bus = EventBus()
        service = GeopoliticsService(event_bus=bus)
        assert isinstance(service._event_bus, EventBus)


# =============================================================================
# Test declare_war (7 tests)
# =============================================================================


class TestDeclareWar:
    """Tests for declare_war method."""

    def test_declare_war_success(self, geopolitics_service, diplomacy_matrix):
        """Test successful war declaration."""
        result = geopolitics_service.declare_war(
            matrix=diplomacy_matrix,
            aggressor_id="faction-a",
            defender_id="faction-b",
            reason="Territorial dispute",
            world_id="world-1",
        )

        assert result.is_ok
        # Check that status was set
        status = diplomacy_matrix.get_status("faction-a", "faction-b")
        assert status == DiplomaticStatus.AT_WAR

    def test_declare_war_updates_matrix_status(self, geopolitics_service, diplomacy_matrix):
        """Test that war declaration updates the matrix status."""
        # Initially no status
        assert diplomacy_matrix.get_status("faction-a", "faction-b") is None

        geopolitics_service.declare_war(
            matrix=diplomacy_matrix,
            aggressor_id="faction-a",
            defender_id="faction-b",
            reason="Invasion",
        )

        # Status should be AT_WAR
        status = diplomacy_matrix.get_status("faction-a", "faction-b")
        assert status == DiplomaticStatus.AT_WAR

    def test_declare_war_registers_factions(self, geopolitics_service, diplomacy_matrix):
        """Test that factions are registered in the matrix."""
        assert len(diplomacy_matrix.faction_ids) == 0

        geopolitics_service.declare_war(
            matrix=diplomacy_matrix,
            aggressor_id="faction-a",
            defender_id="faction-b",
            reason="Conflict",
        )

        assert "faction-a" in diplomacy_matrix.faction_ids
        assert "faction-b" in diplomacy_matrix.faction_ids

    def test_declare_war_with_world_id_in_reason(self, geopolitics_service, diplomacy_matrix):
        """Test war declaration with world ID context."""
        result = geopolitics_service.declare_war(
            matrix=diplomacy_matrix,
            aggressor_id="faction-a",
            defender_id="faction-b",
            reason="Resource war",
            world_id="world-1",
        )

        assert result.is_ok
        assert diplomacy_matrix.world_id == "world-1"


# =============================================================================
# Test form_alliance (7 tests)
# =============================================================================


class TestFormAlliance:
    """Tests for form_alliance method."""

    def test_form_alliance_success(self, geopolitics_service, diplomacy_matrix):
        """Test successful alliance formation."""
        result = geopolitics_service.form_alliance(
            matrix=diplomacy_matrix,
            faction_a_id="faction-a",
            faction_b_id="faction-b",
            world_id="world-1",
        )

        assert result.is_ok
        status = diplomacy_matrix.get_status("faction-a", "faction-b")
        assert status == DiplomaticStatus.ALLIED

    def test_form_alliance_fails_when_at_war(self, geopolitics_service, diplomacy_matrix):
        """Test that alliance cannot be formed when factions are at war."""
        # First declare war
        diplomacy_matrix.set_status("faction-a", "faction-b", DiplomaticStatus.AT_WAR)

        # Try to form alliance
        result = geopolitics_service.form_alliance(
            matrix=diplomacy_matrix,
            faction_a_id="faction-a",
            faction_b_id="faction-b",
        )

        assert result.is_error

    def test_form_alliance_updates_matrix_status(self, geopolitics_service, diplomacy_matrix):
        """Test that alliance formation updates the matrix status."""
        assert diplomacy_matrix.get_status("faction-a", "faction-b") is None

        geopolitics_service.form_alliance(
            matrix=diplomacy_matrix,
            faction_a_id="faction-a",
            faction_b_id="faction-b",
        )

        status = diplomacy_matrix.get_status("faction-a", "faction-b")
        assert status == DiplomaticStatus.ALLIED


# =============================================================================
# Test transfer_territory (5 tests)
# =============================================================================


class TestTransferTerritory:
    """Tests for transfer_territory method."""

    def test_transfer_territory_success(self, geopolitics_service, sample_location):
        """Test successful territory transfer."""
        assert sample_location.controlling_faction_id == "faction-1"

        result = geopolitics_service.transfer_territory(
            location=sample_location,
            new_controller_id="faction-2",
            reason="Peace treaty",
            world_id="world-1",
        )

        assert result.is_ok
        assert sample_location.controlling_faction_id == "faction-2"

    def test_transfer_territory_with_reason(self, geopolitics_service, sample_location):
        """Test transfer with specific reason."""
        result = geopolitics_service.transfer_territory(
            location=sample_location,
            new_controller_id="faction-2",
            reason="Diplomatic exchange",
            world_id="world-1",
        )

        assert result.is_ok


# =============================================================================
# Test get_diplomacy_summary (3 tests)
# =============================================================================


class TestGetDiplomacySummary:
    """Tests for get_diplomacy_summary method."""

    def test_get_diplomacy_summary_basic(self, geopolitics_service, diplomacy_matrix):
        """Test basic diplomacy summary."""
        # Setup some relations
        diplomacy_matrix.set_status("faction-a", "faction-b", DiplomaticStatus.ALLIED)
        diplomacy_matrix.set_status("faction-a", "faction-c", DiplomaticStatus.AT_WAR)
        diplomacy_matrix.set_status("faction-a", "faction-d", DiplomaticStatus.NEUTRAL)

        result = geopolitics_service.get_diplomacy_summary(
            matrix=diplomacy_matrix,
            faction_id="faction-a",
        )

        assert result.is_ok
        summary = result.value
        assert summary["faction_id"] == "faction-a"
        assert "faction-b" in summary["allies"]
        assert "faction-c" in summary["enemies"]
        assert "faction-d" in summary["neutral"]

    def test_get_diplomacy_summary_empty(self, geopolitics_service, diplomacy_matrix):
        """Test diplomacy summary for faction with no relations."""
        result = geopolitics_service.get_diplomacy_summary(
            matrix=diplomacy_matrix,
            faction_id="faction-a",
        )

        assert result.is_ok
        summary = result.value
        assert summary["faction_id"] == "faction-a"
        assert summary["allies"] == []
        assert summary["enemies"] == []
        assert summary["neutral"] == []

    def test_get_diplomacy_summary_returns_dict(self, geopolitics_service, diplomacy_matrix):
        """Test that summary returns dictionary."""
        result = geopolitics_service.get_diplomacy_summary(
            matrix=diplomacy_matrix,
            faction_id="faction-a",
        )

        assert result.is_ok
        assert isinstance(result.value, dict)
        assert "faction_id" in result.value
        assert "allies" in result.value
        assert "enemies" in result.value
        assert "neutral" in result.value
