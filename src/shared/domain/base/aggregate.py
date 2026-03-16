"""Domain aggregate base class for Novel Engine.

This module defines the abstract base class for all domain aggregates.
Aggregates are clusters of associated objects treated as a single unit
for data changes, with one entity designated as the aggregate root.
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, TypeVar, final
from uuid import UUID

from src.shared.domain.base.entity import Entity
from src.shared.domain.base.event import DomainEvent

T = TypeVar("T")


@dataclass
class AggregateRoot(Entity[Any]):
    """Abstract base class for all domain aggregate roots.

    Aggregates are consistency boundaries that encapsulate a cluster
    of domain objects. They ensure that all changes to the cluster
    maintain invariants. External references should only point to
    the aggregate root.

    Attributes:
        id: The unique identifier of the aggregate root.
        _domain_events: Internal list of domain events raised by this aggregate.
        _version: Optimistic concurrency control version number.

    Example:
        >>> class Order(AggregateRoot):
        ...     customer_id: UUID
        ...     items: list[OrderItem] = field(default_factory=list)
        ...
        ...     def add_item(self, item: OrderItem) -> None:
        ...         self.items.append(item)
        ...         self.add_event(ItemAddedEvent(order_id=self.id, item=item))
    """

    _version: int = field(default=0, init=False, repr=False)

    @abstractmethod
    def validate_invariants(self) -> None:
        """Validate the aggregate's invariants across all contained objects.

        This method must be implemented by concrete aggregate classes
        to ensure all objects within the aggregate maintain valid state
        and that aggregate-wide invariants are satisfied.

        Raises:
            DomainException: If any invariant is violated.
        """
        ...

    def validate(self) -> None:
        """Validate the aggregate root entity.

        This calls validate_invariants by default. Override if you need
        separate root validation from aggregate-wide validation.

        Raises:
            DomainException: If the aggregate is in an invalid state.
        """
        self.validate_invariants()

    @final
    def increment_version(self) -> None:
        """Increment the aggregate's version for optimistic concurrency.

        This should be called whenever the aggregate is modified.
        The version is used to prevent concurrent modification conflicts.
        """
        self._version += 1

    @final
    @property
    def version(self) -> int:
        """Get the current version of the aggregate.

        Returns:
            The current optimistic concurrency control version.
        """
        return self._version

    @final
    def apply_event(self, event: DomainEvent) -> None:
        """Apply a domain event to the aggregate state.

        This method is used for event sourcing or applying events
        from the event store to reconstruct aggregate state.

        Args:
            event: The domain event to apply.

        Example:
            >>> order.apply_event(OrderCreatedEvent(order_id=id, customer_id=cid))
        """
        handler_name = f"_on_{event.__class__.__name__.lower()}"
        handler = getattr(self, handler_name, None)
        if handler and callable(handler):
            handler(event)
        self.increment_version()

    @final
    def check_rule(self, condition: bool, message: str) -> None:
        """Check a business rule and raise exception if violated.

        This is a helper method for validating business rules within
        the aggregate's methods.

        Args:
            condition: The condition to check.
            message: Error message if the condition is False.

        Raises:
            BusinessRuleException: If the condition is False.
        """
        if not condition:
            from src.shared.domain.exceptions import BusinessRuleException

            raise BusinessRuleException(message)
