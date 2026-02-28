"""Unit tests for API startup initialization."""

import pytest
from unittest.mock import MagicMock, patch

from src.api.startup import initialize_app_state


@pytest.mark.unit
class TestEventBusInitialization:
    """Tests for EventBus initialization."""

    @pytest.mark.asyncio
    async def test_uses_enterprise_event_bus(self) -> None:
        """Test that startup uses Enterprise EventBus from src.events."""
        from src.events.event_bus import EventBus as EnterpriseEventBus

        app = MagicMock()
        app.state = MagicMock()

        with patch("src.api.startup.get_service_container") as mock_container:
            mock_container.return_value = MagicMock()

            await initialize_app_state(app)

            # Verify the event bus is Enterprise version
            assert hasattr(app.state, "event_bus")
            assert isinstance(app.state.event_bus, EnterpriseEventBus)
