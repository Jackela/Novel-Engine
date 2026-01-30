#!/usr/bin/env python3
"""Domain Entity Base Class.

This module provides the base Entity class for the World context following
Domain-Driven Design principles. All domain entities should inherit from this base class.
"""

import uuid
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from src.events.event_bus import Event


@dataclass
class Entity(ABC):
    """
    Base class for all domain entities in the World context.

    Follows Domain-Driven Design principles:
    - Has a unique identity that persists across changes
    - Encapsulates business logic and invariants
    - Can raise domain events
    - Provides validation and equality based on identity

    Attributes:
        id: Unique identifier for the entity
        created_at: Timestamp when the entity was created
        updated_at: Timestamp when the entity was last updated
        version: Version number for optimistic concurrency control
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = field(default=1)

    # Private field to store domain events
    _domain_events: List[Event] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        """
        Validate entity after initialization.

        Subclasses can override this method to add specific validation logic.
        """
        self.validate()

    def validate(self) -> List[str]:
        """
        Validate the entity's invariants.

        Returns:
            List of validation error messages. Empty list means valid.
        """
        errors = []

        if not self.id:
            errors.append("Entity ID cannot be empty")

        if self.version < 1:
            errors.append("Entity version must be positive")

        if self.created_at > datetime.now():
            errors.append("Created timestamp cannot be in the future")

        if self.updated_at < self.created_at:
            errors.append("Updated timestamp cannot be before created timestamp")

        # Allow subclasses to add their own validation
        errors.extend(self._validate_business_rules())

        if errors:
            raise ValueError(f"Entity validation failed: {'; '.join(errors)}")

        return errors

    def _validate_business_rules(self) -> List[str]:
        """
        Validate entity-specific business rules.

        Subclasses should override this method to implement their specific
        business rule validations.

        Returns:
            List of validation error messages.
        """
        return []

    def touch(self) -> None:
        """
        Update the entity's timestamp and increment version.

        Call this method when the entity is modified to track changes.
        """
        self.updated_at = datetime.now()
        self.version += 1

    def raise_domain_event(self, event: Event) -> None:
        """
        Raise a domain event related to this entity.

        Args:
            event: The domain event to raise
        """
        # Ensure event has proper correlation with this entity
        if not event.correlation_id:
            event.correlation_id = self.id

        if not event.source:
            event.source = f"{self.__class__.__name__}:{self.id}"

        self._domain_events.append(event)

    def get_domain_events(self) -> List[Event]:
        """
        Get all domain events raised by this entity.

        Returns:
            List of domain events
        """
        return self._domain_events.copy()

    def clear_domain_events(self) -> None:
        """
        Clear all domain events from this entity.

        Usually called after events have been published to the event bus.
        """
        self._domain_events.clear()

    def has_domain_events(self) -> bool:
        """
        Check if this entity has any pending domain events.

        Returns:
            True if there are pending domain events
        """
        return len(self._domain_events) > 0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert entity to dictionary representation.

        Returns:
            Dictionary representation of the entity
        """
        result = {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "entity_type": self.__class__.__name__,
        }

        # Add entity-specific data
        entity_data = self._to_dict_specific()
        result.update(entity_data)

        return result

    def _to_dict_specific(self) -> Dict[str, Any]:
        """
        Convert entity-specific data to dictionary.

        Subclasses should override this method to include their specific fields.

        Returns:
            Dictionary with entity-specific data
        """
        return {}

    def __eq__(self, other: object) -> bool:
        """
        Equality comparison based on entity identity.

        Two entities are equal if they are of the same type and have the same ID.

        Args:
            other: Object to compare with

        Returns:
            True if entities are equal
        """
        if not isinstance(other, Entity):
            return False

        return self.__class__ == other.__class__ and self.id == other.id

    def __hash__(self) -> int:
        """
        Hash based on entity type and ID.

        Returns:
            Hash value for the entity
        """
        return hash((self.__class__.__name__, self.id))

    def __str__(self) -> str:
        """Return string representation of the entity.

        Returns:
            String representation showing entity type and ID
        """
        return f"{self.__class__.__name__}(id={self.id})"

    def __repr__(self) -> str:
        """
        Detailed string representation of the entity.

        Returns:
            Detailed string representation
        """
        return (
            f"{self.__class__.__name__}(id={self.id}, "
            f"version={self.version}, created_at={self.created_at})"
        )
