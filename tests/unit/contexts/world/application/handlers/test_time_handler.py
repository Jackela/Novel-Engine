"""Unit tests for TimeAdvancedHandler."""

from unittest.mock import MagicMock, patch

import pytest

from src.core.result import Ok

pytestmark = pytest.mark.unit

from src.contexts.world.application.handlers.time_handler import TimeAdvancedHandler
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

    def test_handler_implements_event_handler_interface(
        self, handler: TimeAdvancedHandler
    ) -> None:
        """Test that handler implements EventHandler interface."""
        from src.events.event_bus import EventHandler

        assert isinstance(handler, EventHandler)

    def test_handled_event_types(self, handler: TimeAdvancedHandler) -> None:
        """Test that handler declares correct event types."""
        assert "world.time_advanced" in handler.handled_event_types

    def test_handler_has_tick_service(self, handler: TimeAdvancedHandler) -> None:
        """Test that handler has a tick service."""
        assert hasattr(handler, "_tick_service")

    @pytest.mark.asyncio
    async def test_handle_time_advanced_event(
        self, handler: TimeAdvancedHandler, sample_event: TimeAdvancedEvent
    ) -> None:
        """Test handling a TimeAdvancedEvent returns bool."""
        result = await handler.handle(sample_event)

        # EventHandler interface returns bool
        assert result is True

    @pytest.mark.asyncio
    async def test_handler_with_custom_tick_service(self) -> None:
        """Test handler with injected tick service."""
        from src.contexts.world.application.services.faction_tick_service import (
            FactionTickService,
            TickResult,
        )

        mock_service = MagicMock(spec=FactionTickService)
        mock_service.process_tick.return_value = Ok(
            TickResult(
                world_id="custom-world",
                days_advanced=10,
                success=True,
                resources_updated=5,
                diplomatic_changes=2,
            )
        )

        handler = TimeAdvancedHandler(tick_service=mock_service)

        event = TimeAdvancedEvent.create(
            previous_date={"year": 1, "month": 1, "day": 1, "era_name": "First Age"},
            new_date={"year": 1, "month": 1, "day": 11, "era_name": "First Age"},
            days_advanced=10,
            world_id="custom-world",
        )

        result = await handler.handle(event)

        assert result is True
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
        """Test that handler catches exceptions and returns False."""
        from src.contexts.world.application.services.faction_tick_service import (
            FactionTickService,
        )

        mock_service = MagicMock(spec=FactionTickService)
        mock_service.process_tick.side_effect = RuntimeError("Test error")

        handler = TimeAdvancedHandler(tick_service=mock_service)

        result = await handler.handle(sample_event)

        # EventHandler interface returns False on failure
        assert result is False

    def test_create_for_event_bus(self) -> None:
        """Test factory method creates handler."""
        handler = TimeAdvancedHandler.create_for_event_bus()

        assert handler is not None
        assert isinstance(handler, TimeAdvancedHandler)
