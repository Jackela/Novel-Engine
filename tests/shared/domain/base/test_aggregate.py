"""Tests for the AggregateRoot base class.

This module contains comprehensive tests for the AggregateRoot class,
ensuring proper event sourcing, version management, and invariant validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import override
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from src.shared.domain.base.aggregate import AggregateRoot
from src.shared.domain.base.event import DomainEvent
from src.shared.domain.exceptions import BusinessRuleException


@dataclass(frozen=True)
class ItemAddedEvent(DomainEvent):
    """Test event for item added."""

    event_type: str = "item.added"
    item_name: str = ""


@dataclass(frozen=True)
class OrderCreatedEvent(DomainEvent):
    """Test event for order created."""

    event_type: str = "order.created"
    customer_name: str = ""


@dataclass
class Order(AggregateRoot):
    """Test aggregate implementation."""

    customer_name: str = ""
    items: list[str] = field(default_factory=list)
    _event_handlers_called: list[str] = field(default_factory=list, repr=False)

    @override
    def validate_invariants(self) -> None:
        """Validate order invariants."""
        if len(self.customer_name) > 100:
            raise ValueError("Customer name too long")

    def add_item(self, item_name: str) -> None:
        """Add an item to the order."""
        self.check_rule(len(item_name) > 0, "Item name cannot be empty")
        self.items.append(item_name)
        self.add_event(ItemAddedEvent(aggregate_id=str(self.id), item_name=item_name))

    def _on_itemaddedevent(self, event: ItemAddedEvent) -> None:
        """Handle ItemAddedEvent for event sourcing."""
        self._event_handlers_called.append(f"item_added:{event.item_name}")

    def _on_ordercreatedevent(self, event: OrderCreatedEvent) -> None:
        """Handle OrderCreatedEvent for event sourcing."""
        self._event_handlers_called.append(f"order_created:{event.customer_name}")


class TestAggregateRoot:
    """Test cases for AggregateRoot base class."""

    def test_aggregate_inherits_from_entity(self) -> None:
        """Test that AggregateRoot is an Entity."""
        order = Order(customer_name="John")

        assert hasattr(order, "id")
        assert hasattr(order, "created_at")
        assert hasattr(order, "updated_at")
        assert hasattr(order, "_domain_events")

    def test_version_starts_at_zero(self) -> None:
        """Test that version starts at 0."""
        order = Order(customer_name="John")

        assert order.version == 0

    def test_increment_version(self) -> None:
        """Test version increment."""
        order = Order(customer_name="John")

        order.increment_version()

        assert order.version == 1

    def test_apply_event_increments_version(self) -> None:
        """Test that applying event increments version."""
        order = Order(customer_name="John")
        event = ItemAddedEvent(aggregate_id=str(order.id), item_name="Book")

        order.apply_event(event)

        assert order.version == 1

    def test_apply_event_calls_handler(self) -> None:
        """Test that applying event calls the correct handler."""
        order = Order(customer_name="John")
        event = ItemAddedEvent(aggregate_id=str(order.id), item_name="Book")

        order.apply_event(event)

        assert "item_added:Book" in order._event_handlers_called

    def test_apply_event_without_handler_still_increments_version(self) -> None:
        """Test that events without handlers still increment version."""

        @dataclass(frozen=True)
        class UnknownEvent(DomainEvent):
            """Event without handler."""

            event_type: str = "unknown"

        order = Order(customer_name="John")
        event = UnknownEvent(aggregate_id=str(order.id))

        order.apply_event(event)

        assert order.version == 1

    def test_validate_invariants_called(self) -> None:
        """Test that validate_invariants is called during creation."""
        with pytest.raises(ValueError, match="Customer name too long"):
            Order(customer_name="x" * 101)

    def test_check_rule_raises_on_false_condition(self) -> None:
        """Test that check_rule raises BusinessRuleException."""
        order = Order(customer_name="John")

        with pytest.raises(BusinessRuleException, match="Business rule violated"):
            order.check_rule(False, "Business rule violated")

    def test_check_rule_passes_on_true_condition(self) -> None:
        """Test that check_rule passes on true condition."""
        order = Order(customer_name="John")

        # Should not raise
        order.check_rule(True, "This should not be raised")

    def test_validate_delegates_to_validate_invariants(self) -> None:
        """Test that validate calls validate_invariants."""
        order = Order(customer_name="John")

        # Should not raise
        order.validate()

    def test_add_item_business_rule(self) -> None:
        """Test business rule enforcement in domain method."""
        order = Order(customer_name="John")

        with pytest.raises(BusinessRuleException, match="Item name cannot be empty"):
            order.add_item("")

    def test_add_item_succeeds_with_valid_input(self) -> None:
        """Test that add_item works with valid input."""
        order = Order(customer_name="John")

        order.add_item("Book")

        assert "Book" in order.items
        assert len(order.get_events()) == 1

    def test_event_sourcing_replay(self) -> None:
        """Test event sourcing replay functionality."""
        order = Order(customer_name="John")
        events = [
            OrderCreatedEvent(aggregate_id=str(order.id), customer_name="Jane"),
            ItemAddedEvent(aggregate_id=str(order.id), item_name="Book"),
            ItemAddedEvent(aggregate_id=str(order.id), item_name="Pen"),
        ]

        for event in events:
            order.apply_event(event)

        assert order.version == 3
        assert len(order._event_handlers_called) == 3


class TestAbstractAggregateRoot:
    """Test cases for abstract AggregateRoot behavior.

    Note: In Python, AggregateRoot cannot be truly abstract because
    validate_invariants has a default implementation. These tests
    verify the actual behavior rather than的理想化的期望。
    """

    def test_aggregate_root_can_be_instantiated(self) -> None:
        """Test that AggregateRoot can be instantiated (has default validate)."""
        # AggregateRoot has a default validate_invariants that does nothing
        # so it can be instantiated, though this is not typical usage
        root = AggregateRoot()
        assert root.id is not None
        assert root.version == 0

    def test_validate_invariants_default_does_nothing(self) -> None:
        """Test that default validate_invariants does not raise."""

        @dataclass
        class ConcreteAggregate(AggregateRoot):
            value: str = ""

        # Should not raise - default validate_invariants is a no-op
        agg = ConcreteAggregate()
        agg.validate()  # Should not raise

    def test_inherits_entity_validate(self) -> None:
        """Test that validate method from Entity is inherited."""
        order = Order(customer_name="Test")

        # Should call validate_invariants
        order.validate()
