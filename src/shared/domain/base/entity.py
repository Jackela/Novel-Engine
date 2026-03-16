"""Domain entity base class for Novel Engine.

This module defines the abstract base class for all domain entities.
Entities are objects that have a distinct identity that runs through time
and different representations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar, final
from uuid import UUID, uuid4

from src.shared.domain.base.event import DomainEvent

T = TypeVar("T")
E = TypeVar("E", bound="Entity[Any]")


@dataclass
class Entity(ABC, Generic[T]):
    """Abstract base class for all domain entities.

    Entities are defined by their identity, not by their attributes.
    Two entities with the same ID are considered the same entity,
    even if their other attributes differ.

    Type Parameters:
        T: The type of the entity's identifier (typically UUID or int).

    Attributes:
        id: The unique identifier of the entity.
        created_at: Timestamp when the entity was created.
        updated_at: Timestamp when the entity was last updated.
        _domain_events: Internal list of domain events raised by this entity.

    Example:
        >>> class User(Entity[UUID]):
        ...     name: str
        ...     email: str
        ...
        >>> user = User(id=uuid4(), name="John", email="john@example.com")
    """

    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    _domain_events: list[DomainEvent] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        """Post-initialization hook - currently a no-op since field has default_factory."""
        # Note: _domain_events is always initialized by dataclass with default_factory
        pass

    @abstractmethod
    def validate(self) -> None:
        """Validate the entity's invariants.

        This method must be implemented by concrete entity classes
        to ensure the entity maintains valid state.

        Raises:
            DomainException: If the entity is in an invalid state.
        """
        ...

    @final
    def __eq__(self, other: object) -> bool:
        """Check equality based on entity identity.

        Two entities are equal if they have the same type and ID.

        Args:
            other: The object to compare with.

        Returns:
            True if the entities are equal, False otherwise.
        """
        if not isinstance(other, self.__class__):
            return False
        return self.id == other.id

    @final
    def __hash__(self) -> int:
        """Return hash based on entity type and ID.

        Returns:
            Hash value for the entity.
        """
        return hash((self.__class__, self.id))

    @final
    def add_event(self, event: DomainEvent) -> None:
        """Add a domain event to this entity's event list.

        Domain events represent significant occurrences in the domain
        and are used for eventual consistency and side effects.

        Args:
            event: The domain event to add.

        Example:
            >>> user.add_event(UserCreatedEvent(user_id=user.id))
        """
        self._domain_events.append(event)

    @final
    def clear_events(self) -> None:
        """Clear all domain events.

        This method removes all pending domain events from this entity.
        Typically called after events have been dispatched.
        """
        self._domain_events.clear()

    @final
    def get_events(self) -> list[DomainEvent]:
        """Get all domain events.

        Returns:
            Copy of the list of domain events raised by this entity.
        """
        return self._domain_events.copy()

    @classmethod
    def next_id(cls) -> UUID:
        """Generate a new unique identifier.

        Returns:
            A new UUID v4.

        Note:
            This is a convenience method for generating UUIDs.
            Entities using other ID types should override this.
        """
        return uuid4()
