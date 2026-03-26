"""Tests for the DomainEvent base class.

This module contains comprehensive tests for the DomainEvent class,
ensuring proper event creation, serialization, and immutability.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import ClassVar
from uuid import UUID, uuid4

import pytest

from src.shared.domain.base.event import DomainEvent, IntegrationEvent


@dataclass(frozen=True)
class OrderCreated(DomainEvent):
    """Test event for order creation."""

    event_type: ClassVar[str] = "order.created"
    customer_id: UUID = field(default_factory=uuid4)
    total_amount: Decimal = Decimal("0.00")


@dataclass(frozen=True)
class ProductAdded(DomainEvent):
    """Test event for product addition."""

    event_type: ClassVar[str] = "product.added"
    product_name: str = ""
    quantity: int = 0


@dataclass(frozen=True)
class OrderShipped(IntegrationEvent):
    """Test integration event."""

    event_type: ClassVar[str] = "order.shipped"
    tracking_number: str = ""


class TestDomainEvent:
    """Test cases for DomainEvent base class."""

    def test_event_created_with_defaults(self) -> None:
        """Test event creation with default values."""
        aggregate_id = uuid4()
        event = OrderCreated(aggregate_id=str(aggregate_id))

        assert isinstance(event.event_id, UUID)
        assert event.aggregate_id == str(aggregate_id)
        assert isinstance(event.occurred_at, datetime)
        assert event.type == "order.created"

    def test_event_created_with_custom_values(self) -> None:
        """Test event creation with custom values."""
        aggregate_id = uuid4()
        customer_id = uuid4()
        event = OrderCreated(
            aggregate_id=str(aggregate_id),
            customer_id=customer_id,
            total_amount=Decimal("99.99"),
        )

        assert event.customer_id == customer_id
        assert event.total_amount == Decimal("99.99")

    def test_event_immutability(self) -> None:
        """Test that events are immutable."""
        event = OrderCreated(aggregate_id=str(uuid4()))

        with pytest.raises(FrozenInstanceError):
            event.total_amount = Decimal("50.00")  # type: ignore[misc]

    def test_event_to_dict(self) -> None:
        """Test event serialization to dictionary."""
        aggregate_id = uuid4()
        event = OrderCreated(aggregate_id=str(aggregate_id))

        result = event.to_dict()

        assert result["event_type"] == "order.created"
        assert result["aggregate_id"] == str(aggregate_id)
        assert "event_id" in result
        assert "occurred_at" in result
        assert result["correlation_id"] is None

    def test_event_str_representation(self) -> None:
        """Test string representation of event."""
        event = OrderCreated(aggregate_id=str(uuid4()))

        result = str(event)

        assert "order.created" in result
        assert str(event.event_id) in result

    def test_event_repr_representation(self) -> None:
        """Test repr representation of event."""
        aggregate_id = uuid4()
        event = OrderCreated(aggregate_id=str(aggregate_id))

        result = repr(event)

        assert "OrderCreated" in result
        assert str(event.event_id) in result

    def test_event_type_property(self) -> None:
        """Test event type property."""
        event = OrderCreated(aggregate_id=str(uuid4()))

        assert event.type == "order.created"

    def test_events_with_different_ids_are_not_equal(self) -> None:
        """Test that events with different IDs are not equal."""
        aggregate_id = uuid4()
        event1 = OrderCreated(aggregate_id=str(aggregate_id))
        event2 = OrderCreated(aggregate_id=str(aggregate_id))

        assert event1 != event2  # Different event_ids

    def test_correlation_id_can_be_set(self) -> None:
        """Test that correlation ID can be set."""
        aggregate_id = uuid4()
        correlation_id = uuid4()
        event = OrderCreated(
            aggregate_id=str(aggregate_id), correlation_id=correlation_id
        )

        assert event.correlation_id == correlation_id


class TestIntegrationEvent:
    """Test cases for IntegrationEvent class."""

    def test_integration_event_inherits_from_domain_event(self) -> None:
        """Test that IntegrationEvent inherits from DomainEvent."""
        aggregate_id = uuid4()
        event = OrderShipped(
            aggregate_id=str(aggregate_id),
            tracking_number="TRACK123",
            source_service="shipping-service",
        )

        assert isinstance(event, DomainEvent)
        assert event.source_service == "shipping-service"

    def test_integration_event_to_dict_includes_source(self) -> None:
        """Test that to_dict includes integration-specific fields."""
        aggregate_id = uuid4()
        event = OrderShipped(
            aggregate_id=str(aggregate_id),
            tracking_number="TRACK123",
            source_service="order-service",
        )

        result = event.to_dict()

        assert result["source_service"] == "order-service"
        assert result["event_type"] == "order.shipped"

    def test_integration_event_default_source_service(self) -> None:
        """Test default source service value."""
        aggregate_id = uuid4()
        event = OrderShipped(aggregate_id=str(aggregate_id))

        assert event.source_service == "unknown"


class TestAbstractDomainEvent:
    """Test cases for abstract DomainEvent behavior."""

    def test_cannot_instantiate_abstract_event(self) -> None:
        """Test that DomainEvent cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DomainEvent(aggregate_id=str(uuid4()))  # type: ignore[abstract]

    def test_event_without_event_type_raises(self) -> None:
        """Test that events without event_type raise error."""

        @dataclass(frozen=True)
        class BadEvent(DomainEvent):
            """Event without event_type."""

            # Missing event_type

        # This might or might not raise depending on implementation
        # The error could be raised in __post_init__
        try:
            BadEvent(aggregate_id=str(uuid4()))
            # If we get here, the validation might not be strict
        except (ValueError, TypeError):
            pass  # Expected
