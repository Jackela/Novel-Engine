"""Unit tests for TimeAdvancedHandler."""

from unittest.mock import MagicMock, patch

import pytest

from src.contexts.world.application.handlers.time_handler import (
    TimeAdvancedHandler,
    handle_time_advanced,
)
from src.contexts.world.domain.events.time_events import TimeAdvancedEvent


@pytest.mark.unit
class TestTimeAdvancedHandler:
    """Tests for TimeAdvancedHandler."""

    @pytest.fixture
    def handler(self) -> TimeAdvancedHandler:
        """Create a TimeAdvancedHandler instance."""
        return TimeAdvancedHandler()

    @pytest.fixture
    def sample_event(self) -> TimeAdvancedEvent:
        """Create a sample TimeAdvancedEvent."""
        return TimeAdvancedEvent.create(
            previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 6, "era_name": "First Age"},
            days_advanced=5,
            world_id="test-world",
        )

    def test_handler_exists(self, handler: TimeAdvancedHandler) -> None:
        """Test that TimeAdvancedHandler can be instantiated."""
        assert handler is not None

    def test_handler_has_tick_service(self, handler: TimeAdvancedHandler) -> None:
        """Test that handler has a tick service."""
        assert hasattr(handler, "_tick_service")

    @pytest.mark.asyncio
    async def test_handle_time_advanced_event(
        self, handler: TimeAdvancedHandler, sample_event: TimeAdvancedEvent
    ) -> None:
        """Test handling a TimeAdvancedEvent."""
        result = await handler.handle(sample_event)

        assert result.success is True
        assert result.world_id == "test-world"
        assert result.days_advanced == 5

    @pytest.mark.asyncio
    async def test_handler_with_custom_tick_service(self) -> None:
        """Test handler with injected tick service."""
        from src.contexts.world.application.services.faction_tick_service import (
            FactionTickService,
            TickResult,
        )

        mock_service = MagicMock(spec=FactionTickService)
        mock_service.process_tick.return_value = TickResult(
            world_id="custom-world",
            days_advanced=10,
            success=True,
            resources_updated=5,
            diplomatic_changes=2,
        )

        handler = TimeAdvancedHandler(tick_service=mock_service)

        event = TimeAdvancedEvent.create(
            previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 11, "era_name": "First Age"},
            days_advanced=10,
            world_id="custom-world",
        )

        result = await handler.handle(event)

        assert result.success is True
        assert result.world_id == "custom-world"
        assert result.days_advanced == 10
        assert result.resources_updated == 5
        assert result.diplomatic_changes == 2
        mock_service.process_tick.assert_called_once_with(
            world_id="custom-world", days_advanced=10
        )

    @pytest.mark.asyncio
    async def test_handler_logs_event_processing(
        self, handler: TimeAdvancedHandler, sample_event: TimeAdvancedEvent
    ) -> None:
        """Test that handler logs event processing."""
        with patch(
            "src.contexts.world.application.handlers.time_handler.logger"
        ) as mock_logger:
            await handler.handle(sample_event)

            # Verify logging occurred
            assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_handler_catches_exceptions(
        self, sample_event: TimeAdvancedEvent
    ) -> None:
        """Test that handler catches exceptions and returns error result."""
        from src.contexts.world.application.services.faction_tick_service import (
            FactionTickService,
        )

        mock_service = MagicMock(spec=FactionTickService)
        mock_service.process_tick.side_effect = RuntimeError("Test error")

        handler = TimeAdvancedHandler(tick_service=mock_service)

        result = await handler.handle(sample_event)

        assert result.success is False
        assert "Test error" in result.errors

    def test_create_for_event_bus(self) -> None:
        """Test factory method creates handler."""
        handler = TimeAdvancedHandler.create_for_event_bus()

        assert handler is not None
        assert isinstance(handler, TimeAdvancedHandler)


@pytest.mark.unit
class TestHandleTimeAdvancedFunction:
    """Tests for handle_time_advanced sync wrapper function."""

    @pytest.fixture
    def sample_event(self) -> TimeAdvancedEvent:
        """Create a sample TimeAdvancedEvent."""
        return TimeAdvancedEvent.create(
            previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 2, "era_name": "First Age"},
            days_advanced=1,
            world_id="test-world",
        )

    def test_handle_time_advanced_exists(self) -> None:
        """Test that handle_time_advanced function exists."""
        assert callable(handle_time_advanced)

    def test_handle_time_advanced_runs_without_error(
        self, sample_event: TimeAdvancedEvent
    ) -> None:
        """Test that handle_time_advanced can be called without error."""
        # Should not raise an exception
        handle_time_advanced(sample_event)
