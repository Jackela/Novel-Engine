"""Tests for event bus abstraction."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from src.shared.infrastructure.messaging.event_bus import (
    DomainEvent,
    EventBus,
    EventBusError,
    EventBusNotStartedError,
    EventPublishError,
    EventSubscribeError,
)


class TestDomainEvent:
    """Tests for DomainEvent dataclass."""

    def test_create_domain_event_with_required_fields(self) -> None:
        """Test creating a domain event with required fields only."""
        event = DomainEvent(
            event_type="test.event",
            payload={"key": "value"},
        )

        assert event.event_type == "test.event"
        assert event.payload == {"key": "value"}
        assert isinstance(event.event_id, UUID)
        assert event.aggregate_id is None
        assert event.correlation_id is None
        assert event.causation_id is None
        assert isinstance(event.occurred_on, datetime)
        assert event.metadata == {}

    def test_create_domain_event_with_all_fields(self) -> None:
        """Test creating a domain event with all fields."""
        event_id = uuid4()
        occurred_on = datetime(2024, 1, 1, 12, 0, 0)

        event = DomainEvent(
            event_type="test.event",
            aggregate_id="agg-123",
            payload={"data": "value"},
            event_id=event_id,
            correlation_id="corr-456",
            causation_id="cause-789",
            occurred_on=occurred_on,
            metadata={"source": "test"},
        )

        assert event.event_type == "test.event"
        assert event.aggregate_id == "agg-123"
        assert event.payload == {"data": "value"}
        assert event.event_id == event_id
        assert event.correlation_id == "corr-456"
        assert event.causation_id == "cause-789"
        assert event.occurred_on == occurred_on
        assert event.metadata == {"source": "test"}

    def test_create_domain_event_with_generic_payload(self) -> None:
        """Test creating domain event with different payload types."""
        str_event = DomainEvent[str](event_type="test.string", payload="hello")
        assert str_event.payload == "hello"

        int_event = DomainEvent[int](event_type="test.int", payload=42)
        assert int_event.payload == 42

        list_event = DomainEvent[list](event_type="test.list", payload=[1, 2, 3])
        assert list_event.payload == [1, 2, 3]

    def test_event_immutability(self) -> None:
        """Test that events are immutable (frozen dataclass)."""
        event = DomainEvent(
            event_type="test.event",
            payload={"key": "value"},
        )

        with pytest.raises(AttributeError):
            event.event_type = "new.type"

        with pytest.raises(AttributeError):
            event.payload = {"new": "data"}

    def test_empty_event_type_raises_error(self) -> None:
        """Test that empty event type raises ValueError."""
        with pytest.raises(ValueError, match="event_type cannot be empty"):
            DomainEvent(event_type="", payload={})

    def test_default_event_id_is_unique(self) -> None:
        """Test that default event IDs are unique."""
        event1 = DomainEvent(event_type="test", payload={})
        event2 = DomainEvent(event_type="test", payload={})

        assert event1.event_id != event2.event_id

    def test_default_occurred_on_is_recent(self) -> None:
        """Test that default occurred_on is close to current time."""
        before = datetime.utcnow()
        event = DomainEvent(event_type="test", payload={})
        after = datetime.utcnow()

        assert before <= event.occurred_on <= after


class TestEventBusAbstract:
    """Tests for EventBus abstract base class."""

    def test_event_bus_is_abstract(self) -> None:
        """Test that EventBus cannot be instantiated directly."""
        with pytest.raises(TypeError):
            EventBus()

    def test_event_bus_subclass_must_implement_methods(self) -> None:
        """Test that subclasses must implement abstract methods."""

        class IncompleteBus(EventBus):
            pass

        with pytest.raises(TypeError):
            IncompleteBus()


class TestEventBusExceptions:
    """Tests for EventBus exceptions."""

    def test_event_bus_error_inheritance(self) -> None:
        """Test that all exceptions inherit from EventBusError."""
        assert issubclass(EventPublishError, EventBusError)
        assert issubclass(EventSubscribeError, EventBusError)
        assert issubclass(EventBusNotStartedError, EventBusError)

    def test_event_bus_error_can_be_caught(self) -> None:
        """Test that base exception can catch all sub-exceptions."""
        errors = [
            EventPublishError("publish failed"),
            EventSubscribeError("subscribe failed"),
            EventBusNotStartedError("not started"),
        ]

        for error in errors:
            with pytest.raises(EventBusError):
                raise error

    def test_exceptions_have_messages(self) -> None:
        """Test that exceptions preserve error messages."""
        msg = "custom error message"

        assert str(EventPublishError(msg)) == msg
        assert str(EventSubscribeError(msg)) == msg
        assert str(EventBusNotStartedError(msg)) == msg

    def test_exceptions_with_cause(self) -> None:
        """Test that exceptions can chain with causes."""
        cause = ValueError("original error")

        with pytest.raises(EventPublishError) as exc_info:
            raise EventPublishError("publish failed") from cause

        assert exc_info.value.__cause__ is cause
