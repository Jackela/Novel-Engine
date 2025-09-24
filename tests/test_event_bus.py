import unittest
from unittest.mock import Mock

from src.event_bus import EventBus


class TestEventBus(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()

    def test_subscribe_and_emit(self):
        """Test that a subscribed callback is called when an event is emitted."""
        mock_callback = Mock()
        self.event_bus.subscribe("test_event", mock_callback)
        self.event_bus.emit("test_event", "arg1", kwarg1="value1")
        mock_callback.assert_called_once_with("arg1", kwarg1="value1")

    def test_multiple_subscribers(self):
        """Test that multiple subscribers are called for a single event."""
        mock_callback1 = Mock()
        mock_callback2 = Mock()
        self.event_bus.subscribe("test_event", mock_callback1)
        self.event_bus.subscribe("test_event", mock_callback2)
        self.event_bus.emit("test_event")
        mock_callback1.assert_called_once()
        mock_callback2.assert_called_once()

    def test_emit_to_unsubscribed_event(self):
        """Test that emitting an event with no subscribers does not raise an error."""
        try:
            self.event_bus.emit("unsubscribed_event")
        except Exception as e:
            self.fail(
                f"Emitting to an unsubscribed event raised an exception: {e}"
            )

    def test_callback_exception_handling(self):
        """Test that the event bus handles exceptions in callbacks gracefully."""
        mock_callback1 = Mock(side_effect=ValueError("Test Error"))
        mock_callback2 = Mock()
        self.event_bus.subscribe("test_event", mock_callback1)
        self.event_bus.subscribe("test_event", mock_callback2)

        # We expect the event bus to log an error but not to crash.
        # The second callback should still be called.
        self.event_bus.emit("test_event")

        mock_callback1.assert_called_once()
        mock_callback2.assert_called_once()


if __name__ == "__main__":
    unittest.main()
