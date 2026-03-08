"""Unit tests for FactionTickService."""

import pytest


pytestmark = pytest.mark.unit

from src.contexts.world.application.services.faction_tick_service import (
    FactionTickService,
    TickResult,
)


@pytest.mark.unit
class TestFactionTickService:
    """Tests for FactionTickService."""

    @pytest.fixture
    def service(self) -> FactionTickService:
        """Create a FactionTickService instance."""
        return FactionTickService()

    def test_service_exists(self, service: FactionTickService) -> None:
        """Test that FactionTickService can be instantiated."""
        assert service is not None

    def test_process_tick_returns_result(self, service: FactionTickService) -> None:
        """Test that process_tick returns a TickResult."""
        result = service.process_tick(world_id="test-world", days_advanced=1)

        assert result.is_ok
        tick_result = result.unwrap()
        assert isinstance(tick_result, TickResult)
        assert tick_result.world_id == "test-world"
        assert tick_result.days_advanced == 1
        assert tick_result.resources_updated == 0  # No factions yet
        assert tick_result.diplomatic_changes == 0

    def test_process_tick_with_factions(self, service: FactionTickService) -> None:
        """Test process_tick with mock faction data."""
        # This will be expanded when we integrate with actual faction data
        result = service.process_tick(world_id="test-world", days_advanced=5)

        assert result.is_ok
        tick_result = result.unwrap()
        assert tick_result.days_advanced == 5
        assert tick_result.success is True

    def test_tick_result_dataclass_fields(self) -> None:
        """Test that TickResult has all required fields with correct defaults."""
        result = TickResult(world_id="test", days_advanced=10)

        assert result.world_id == "test"
        assert result.days_advanced == 10
        assert result.success is True  # Default
        assert result.resources_updated == 0  # Default
        assert result.diplomatic_changes == 0  # Default
        assert result.errors == []  # Default

    def test_tick_result_with_errors(self) -> None:
        """Test that TickResult can capture errors."""
        result = TickResult(
            world_id="test",
            days_advanced=1,
            success=False,
            errors=["Something went wrong", "Another error"],
        )

        assert result.success is False
        assert len(result.errors) == 2
        assert "Something went wrong" in result.errors

    def test_service_has_calculate_resource_yields_method(
        self, service: FactionTickService
    ) -> None:
        """Test that service has _calculate_resource_yields placeholder method."""
        # This is a placeholder that returns 0 for now
        result = service._calculate_resource_yields("test-world", 5)
        assert result == 0

    def test_service_has_process_diplomatic_changes_method(
        self, service: FactionTickService
    ) -> None:
        """Test that service has _process_diplomatic_changes placeholder method."""
        # This is a placeholder that returns 0 for now
        result = service._process_diplomatic_changes("test-world", 5)
        assert result == 0
