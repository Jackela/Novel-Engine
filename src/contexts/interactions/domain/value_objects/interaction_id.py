#!/usr/bin/env python3
"""
Interaction ID Value Object

This module implements the InteractionId value object, which provides
unique identification for interaction entities in the system.
"""

from dataclasses import dataclass
import re
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
        if not isinstance(uuid_string, str):
            raise ValueError(f"Invalid UUID string: {uuid_string}")

        normalized_value = uuid_string.strip()
        if not normalized_value:
            raise ValueError("Invalid UUID string: value cannot be empty")

        if UUID_COMPACT_PATTERN.fullmatch(normalized_value):
            normalized_value = (
                f"{normalized_value[0:8]}-{normalized_value[8:12]}-"
                f"{normalized_value[12:16]}-{normalized_value[16:20]}-{normalized_value[20:]}"
            )
        elif not UUID_PATTERN.fullmatch(normalized_value):
            raise ValueError(f"Invalid UUID string: {uuid_string}")

        try:
            uuid_value = UUID(normalized_value)
            return cls(uuid_value)
        except (ValueError, TypeError, AttributeError) as e:
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


UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
UUID_COMPACT_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")
