"""Unit tests for GeopoliticsService."""

import pytest

pytestmark = pytest.mark.unit

from unittest.mock import patch

from src.contexts.world.application.services.geopolitics_service import (
    GeopoliticsService,
)
from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus


@pytest.mark.unit
class TestGeopoliticsService:
    """Tests for GeopoliticsService."""

    @pytest.fixture
    def service(self) -> GeopoliticsService:
        """Create a GeopoliticsService instance."""
        return GeopoliticsService()

    @pytest.fixture
    def diplomacy_matrix(self) -> DiplomacyMatrix:
        """Create a sample diplomacy matrix."""
        matrix = DiplomacyMatrix(world_id="world_1")
        matrix.register_faction("faction_a")
        matrix.register_faction("faction_b")
        return matrix

    def test_declare_war_success(self, service: GeopoliticsService) -> None:
        """Test declaring war between factions."""
        matrix = DiplomacyMatrix(world_id="world_1")
        matrix.register_faction("faction_a")
        matrix.register_faction("faction_b")

        result = service.declare_war(
            matrix=matrix,
            aggressor_id="faction_a",
            defender_id="faction_b",
            reason="Territorial dispute",
        )

        assert result.is_ok
        status = matrix.get_status("faction_a", "faction_b")
        assert status == DiplomaticStatus.AT_WAR

    def test_declare_war_emits_event(self, service: GeopoliticsService) -> None:
        """Test that declaring war emits a WarDeclaredEvent."""
        matrix = DiplomacyMatrix(world_id="world_1")
        matrix.register_faction("faction_a")
        matrix.register_faction("faction_b")

        with patch.object(service, "_emit_event") as mock_emit:
            service.declare_war(
                matrix=matrix,
                aggressor_id="faction_a",
                defender_id="faction_b",
                reason="Test war",
            )
            mock_emit.assert_called_once()
            event = mock_emit.call_args[0][0]
            assert event.event_type == "geopolitics.war_declared"

    def test_form_alliance_success(self, service: GeopoliticsService) -> None:
        """Test forming an alliance between factions."""
        matrix = DiplomacyMatrix(world_id="world_1")
        matrix.register_faction("faction_a")
        matrix.register_faction("faction_b")

        result = service.form_alliance(
            matrix=matrix,
            faction_a_id="faction_a",
            faction_b_id="faction_b",
        )

        assert result.is_ok
        status = matrix.get_status("faction_a", "faction_b")
        assert status == DiplomaticStatus.ALLIED

    def test_cannot_ally_while_at_war(self, service: GeopoliticsService) -> None:
        """Test that factions at war cannot form alliance directly."""
        matrix = DiplomacyMatrix(world_id="world_1")
        matrix.register_faction("faction_a")
        matrix.register_faction("faction_b")
        matrix.set_status("faction_a", "faction_b", DiplomaticStatus.AT_WAR)

        result = service.form_alliance(
            matrix=matrix,
            faction_a_id="faction_a",
            faction_b_id="faction_b",
        )

        assert result.is_error
        assert "at war" in str(result.error).lower()

    def test_transfer_territory(self, service: GeopoliticsService) -> None:
        """Test transferring territory between factions."""
        from src.contexts.world.domain.entities.location import Location

        location = Location(
            id="loc_1",
            name="Test Territory",
            description="A test territory",
            location_type="province",
            controlling_faction_id="faction_a",
        )

        result = service.transfer_territory(
            location=location,
            new_controller_id="faction_b",
            reason="Military conquest",
        )

        assert result.is_ok
        assert location.controlling_faction_id == "faction_b"

    def test_transfer_territory_emits_event(self, service: GeopoliticsService) -> None:
        """Test that territory transfer emits TerritoryChangedEvent."""
        from src.contexts.world.domain.entities.location import Location

        location = Location(
            id="loc_1",
            name="Test Territory",
            description="A test territory",
            location_type="province",
            controlling_faction_id="faction_a",
        )

        with patch.object(service, "_emit_event") as mock_emit:
            service.transfer_territory(
                location=location,
                new_controller_id="faction_b",
                reason="Test transfer",
            )
            mock_emit.assert_called_once()
            event = mock_emit.call_args[0][0]
            assert event.event_type == "geopolitics.territory_changed"
