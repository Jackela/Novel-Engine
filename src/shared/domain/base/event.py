"""Domain event base class for Novel Engine.

This module defines the abstract base class for all domain events.
Domain events represent significant occurrences in the domain that
other parts of the system may need to react to.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, final
from uuid import UUID, uuid4


@dataclass(frozen=True, kw_only=True)
class DomainEvent(ABC):
    """Abstract base class for all domain events.

    Domain events capture occurrences in the domain that are relevant
    to domain experts. They are immutable, have a unique identity,
    and contain a timestamp of when they occurred.

    Attributes:
        event_id: Unique identifier for this event instance.
        event_type: Type identifier for the event.
        aggregate_id: ID of the aggregate that raised this event.
        occurred_at: Timestamp when the event occurred.
        correlation_id: Optional correlation ID for tracing.

    Example:
        >>> @dataclass(frozen=True)
        ... class OrderCreated(DomainEvent):
        ...     event_type: ClassVar[str] = "order.created"
        ...     customer_id: UUID
        ...     total_amount: Decimal
        ...
        >>> event = OrderCreated(aggregate_id=order_id, customer_id=cid, total_amount=amt)
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls is DomainEvent:
            raise TypeError("Cannot instantiate abstract class DomainEvent")
        return super().__new__(cls)

    event_id: UUID = field(default_factory=uuid4)
    event_type: str = field(default="DomainEvent")
    aggregate_id: str = field(default="")
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    correlation_id: UUID | None = field(default=None)

    def __post_init__(self) -> None:
        """Validate that event_type is defined by concrete classes."""
        if (
            not self.event_type
            and self.__class__ is not DomainEvent
            and "DomainEvent" not in self.__class__.__name__
        ):
            raise ValueError(f"{self.__class__.__name__} must define event_type")

    @final
    @property
    def type(self) -> str:
        """Get the event type.

        Returns:
            The event type string.
        """
        return self.event_type

    def to_dict(self) -> dict[str, Any]:
        """Convert the event to a dictionary for serialization.

        Returns:
            Dictionary representation suitable for serialization.
        """
        return {
            "event_id": str(self.event_id),
            "event_type": self.type,
            "aggregate_id": str(self.aggregate_id),
            "occurred_at": self.occurred_at.isoformat(),
            "correlation_id": str(self.correlation_id) if self.correlation_id else None,
        }

    def __str__(self) -> str:
        """Return string representation of the event.

        Returns:
            Human-readable string with event type and ID.
        """
        return f"{self.type}({self.event_id})"

    def __repr__(self) -> str:
        """Return detailed representation of the event.

        Returns:
            Detailed string representation.
        """
        return (
            f"{self.__class__.__name__}("
            f"event_id={self.event_id}, "
            f"aggregate_id={self.aggregate_id}, "
            f"occurred_at={self.occurred_at.isoformat()}"
            f")"
        )


@dataclass(frozen=True, kw_only=True)
class IntegrationEvent(DomainEvent):
    """Base class for integration events between bounded contexts.

    Integration events are published for other bounded contexts
    to consume. They should be stable and versioned carefully.

    Attributes:
        source_service: Name of the service that published the event.
    """

    source_service: str = field(default="unknown")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with integration-specific fields.

        Returns:
            Dictionary with additional integration fields.
        """
        base = super().to_dict()
        base.update(
            {
                "source_service": self.source_service,
            }
        )
        return base
