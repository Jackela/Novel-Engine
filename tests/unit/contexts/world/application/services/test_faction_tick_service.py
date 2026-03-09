#!/usr/bin/env python3
"""Tests for FactionTickService.

Unit tests covering:
- Tick processing logic
- Resource yield calculations
- Diplomatic change processing
- TickResult dataclass
- Logging behavior
"""

from unittest.mock import patch

import pytest

from src.contexts.world.application.services.faction_tick_service import (
    FactionTickService,
    TickResult,
)

pytestmark = pytest.mark.unit


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def service() -> FactionTickService:
    """Create a FactionTickService instance."""
    return FactionTickService()


# ============================================================================
# Test TickResult Dataclass
# ============================================================================


class TestTickResult:
    """Tests for TickResult dataclass."""

    def test_default_values(self) -> None:
        """Should have sensible default values."""
        result = TickResult(world_id="world-123", days_advanced=5)

        assert result.world_id == "world-123"
        assert result.days_advanced == 5
        assert result.success is True
        assert result.resources_updated == 0
        assert result.diplomatic_changes == 0
        assert result.errors == []

    def test_custom_values(self) -> None:
        """Should accept custom values."""
        result = TickResult(
            world_id="world-456",
            days_advanced=10,
            success=False,
            resources_updated=5,
            diplomatic_changes=3,
            errors=["Error 1", "Error 2"],
        )

        assert result.world_id == "world-456"
        assert result.days_advanced == 10
        assert result.success is False
        assert result.resources_updated == 5
        assert result.diplomatic_changes == 3
        assert len(result.errors) == 2

    def test_success_with_errors(self) -> None:
        """Should allow setting success independently of errors."""
        result = TickResult(
            world_id="world-123",
            days_advanced=5,
            success=True,
            errors=["Warning: minor issue"],
        )

        # Success is explicitly set, regardless of errors
        assert result.success is True
        assert len(result.errors) == 1


# ============================================================================
# Test FactionTickService Initialization
# ============================================================================


class TestFactionTickServiceInit:
    """Tests for FactionTickService initialization."""

    def test_init_logs_debug(self) -> None:
        """Should log debug message on initialization."""
        with patch(
            "src.contexts.world.application.services.faction_tick_service.logger"
        ) as mock_logger:
            FactionTickService()
            mock_logger.debug.assert_called_once_with(
                "faction_tick_service_initialized"
            )


# ============================================================================
# Test process_tick
# ============================================================================


class TestProcessTick:
    """Tests for process_tick method."""

    def test_process_tick_returns_result(self, service: FactionTickService) -> None:
        """Should return a Result containing TickResult."""
        result = service.process_tick(world_id="world-123", days_advanced=5)

        assert result.is_ok
        assert isinstance(result.value, TickResult)
        assert result.value.world_id == "world-123"
        assert result.value.days_advanced == 5

    def test_process_tick_success_no_errors(
        self, service: FactionTickService
    ) -> None:
        """Should return success=True when no errors."""
        result = service.process_tick(world_id="world-123", days_advanced=1)

        assert result.is_ok
        assert result.value.success is True
        assert result.value.errors == []

    def test_process_tick_calls_resource_calculation(
        self, service: FactionTickService
    ) -> None:
        """Should call _calculate_resource_yields."""
        with patch.object(
            service, "_calculate_resource_yields", return_value=10
        ) as mock_calc:
            result = service.process_tick(world_id="world-123", days_advanced=5)

            mock_calc.assert_called_once_with("world-123", 5)
            assert result.is_ok
            assert result.value.resources_updated == 10

    def test_process_tick_calls_diplomatic_changes(
        self, service: FactionTickService
    ) -> None:
        """Should call _process_diplomatic_changes."""
        with patch.object(
            service, "_process_diplomatic_changes", return_value=3
        ) as mock_diplo:
            result = service.process_tick(world_id="world-123", days_advanced=5)

            mock_diplo.assert_called_once_with("world-123", 5)
            assert result.is_ok
            assert result.value.diplomatic_changes == 3

    def test_process_tick_logs_start_and_completion(
        self, service: FactionTickService
    ) -> None:
        """Should log tick start and completion."""
        with patch(
            "src.contexts.world.application.services.faction_tick_service.logger"
        ) as mock_logger:
            service.process_tick(world_id="world-123", days_advanced=7)

            # Check start log
            mock_logger.info.assert_any_call(
                "faction_tick_started",
                world_id="world-123",
                days_advanced=7,
            )

            # Check completion log
            mock_logger.info.assert_any_call(
                "faction_tick_completed",
                world_id="world-123",
                days_advanced=7,
                resources_updated=0,
                diplomatic_changes=0,
                success=True,
            )

    def test_process_tick_zero_days(self, service: FactionTickService) -> None:
        """Should handle zero days advanced."""
        result = service.process_tick(world_id="world-123", days_advanced=0)

        assert result.is_ok
        assert result.value.days_advanced == 0
        assert result.value.success is True

    def test_process_tick_large_days_value(self, service: FactionTickService) -> None:
        """Should handle large days values."""
        result = service.process_tick(world_id="world-123", days_advanced=365)

        assert result.is_ok
        assert result.value.days_advanced == 365
        assert result.value.success is True

    def test_process_tick_multiple_worlds(
        self, service: FactionTickService
    ) -> None:
        """Should process different worlds independently."""
        result1 = service.process_tick(world_id="world-1", days_advanced=5)
        result2 = service.process_tick(world_id="world-2", days_advanced=10)

        assert result1.is_ok
        assert result2.is_ok
        assert result1.value.world_id == "world-1"
        assert result1.value.days_advanced == 5
        assert result2.value.world_id == "world-2"
        assert result2.value.days_advanced == 10


# ============================================================================
# Test _calculate_resource_yields
# ============================================================================


class TestCalculateResourceYields:
    """Tests for _calculate_resource_yields method."""

    def test_returns_zero_placeholder(self, service: FactionTickService) -> None:
        """Should return 0 as placeholder implementation."""
        result = service._calculate_resource_yields("world-123", 5)

        assert result == 0

    def test_logs_debug(self, service: FactionTickService) -> None:
        """Should log debug message."""
        with patch(
            "src.contexts.world.application.services.faction_tick_service.logger"
        ) as mock_logger:
            service._calculate_resource_yields("world-123", 5)

            mock_logger.debug.assert_called_once_with(
                "resource_yield_calculation_placeholder",
                world_id="world-123",
            )


# ============================================================================
# Test _process_diplomatic_changes
# ============================================================================


class TestProcessDiplomaticChanges:
    """Tests for _process_diplomatic_changes method."""

    def test_returns_zero_placeholder(self, service: FactionTickService) -> None:
        """Should return 0 as placeholder implementation."""
        result = service._process_diplomatic_changes("world-123", 5)

        assert result == 0

    def test_logs_debug(self, service: FactionTickService) -> None:
        """Should log debug message."""
        with patch(
            "src.contexts.world.application.services.faction_tick_service.logger"
        ) as mock_logger:
            service._process_diplomatic_changes("world-123", 5)

            mock_logger.debug.assert_called_once_with(
                "diplomatic_changes_placeholder",
                world_id="world-123",
            )


# ============================================================================
# Integration-style Tests
# ============================================================================


class TestFactionTickServiceIntegration:
    """Integration-style tests for FactionTickService."""

    def test_full_tick_workflow(self, service: FactionTickService) -> None:
        """Should execute full tick workflow."""
        # Process a tick
        result = service.process_tick(
            world_id="test-world",
            days_advanced=30,
        )

        # Verify result structure
        assert result.is_ok
        assert result.value.world_id == "test-world"
        assert result.value.days_advanced == 30
        assert isinstance(result.value.success, bool)
        assert isinstance(result.value.resources_updated, int)
        assert isinstance(result.value.diplomatic_changes, int)
        assert isinstance(result.value.errors, list)

    def test_service_is_stateless(self) -> None:
        """Service should not maintain state between calls."""
        service1 = FactionTickService()
        service2 = FactionTickService()

        result1 = service1.process_tick("world-1", 5)
        result2 = service2.process_tick("world-2", 10)

        # Results should be independent
        assert result1.is_ok
        assert result2.is_ok
        assert result1.value.world_id == "world-1"
        assert result2.value.world_id == "world-2"

    def test_concurrent_ticks_simulated(self, service: FactionTickService) -> None:
        """Should handle sequential ticks on same world."""
        # Simulate multiple ticks
        results = []
        for days in [1, 7, 30, 365]:
            result = service.process_tick("world-123", days)
            results.append(result)

        # All should succeed
        assert all(r.is_ok for r in results)
        assert all(r.value.success for r in results)

        # Days should match what was passed
        assert results[0].value.days_advanced == 1
        assert results[1].value.days_advanced == 7
        assert results[2].value.days_advanced == 30
        assert results[3].value.days_advanced == 365
