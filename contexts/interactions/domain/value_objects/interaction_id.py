#!/usr/bin/env python3
"""
Interaction ID Value Object

This module implements the InteractionId value object, which provides
unique identification for interaction entities in the system.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True)
class InteractionId:
    """
    Value object representing unique identification for interaction entities.

    This immutable value object ensures consistent identity handling across
    the Interaction bounded context, following DDD principles for identity
    management in domain objects.
    """

    value: UUID

    def __post_init__(self):
        """Validate the UUID value."""
        if not isinstance(self.value, UUID):
            raise ValueError(f"InteractionId must be a UUID, got {type(self.value)}")

    @classmethod
    def generate(cls) -> "InteractionId":
        """Generate a new unique InteractionId."""
        return cls(uuid4())

    @classmethod
    def from_string(cls, uuid_string: str) -> "InteractionId":
        """Create InteractionId from string representation."""
        try:
            uuid_value = UUID(uuid_string)
            return cls(uuid_value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid UUID string: {uuid_string}") from e

    def __str__(self) -> str:
        """Return string representation of the ID."""
        return str(self.value)

    def __eq__(self, other: Any) -> bool:
        """Compare InteractionId instances for equality."""
        if not isinstance(other, InteractionId):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Return hash of the UUID value."""
        return hash(self.value)
