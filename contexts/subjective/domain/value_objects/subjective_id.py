#!/usr/bin/env python3
"""
Subjective ID Value Object

This module implements the SubjectiveId value object, which provides
unique identification for subjective perception entities in the system.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True)
class SubjectiveId:
    """
    Value object representing unique identification for subjective entities.

    This immutable value object ensures consistent identity handling across
    the Subjective bounded context, following DDD principles for identity
    management in domain objects.
    """

    value: UUID

    def __post_init__(self):
        """Validate the UUID value."""
        if not isinstance(self.value, UUID):
            raise ValueError(
                f"SubjectiveId must be a UUID, got {type(self.value)}"
            )

    @classmethod
    def generate(cls) -> "SubjectiveId":
        """Generate a new unique SubjectiveId."""
        return cls(uuid4())

    @classmethod
    def from_string(cls, uuid_string: str) -> "SubjectiveId":
        """Create SubjectiveId from string representation."""
        # Type validation first
        if not isinstance(uuid_string, str):
            raise ValueError(f"Invalid UUID string: {uuid_string}")

        # Empty or whitespace validation
        if not uuid_string or not uuid_string.strip():
            raise ValueError(f"Invalid UUID string: {uuid_string}")

        uuid_str = uuid_string.strip()

        # Strict format validation for properly formatted UUID strings
        import re

        # Standard UUID pattern: 8-4-4-4-12 hexadecimal digits separated by hyphens
        uuid_pattern = re.compile(
            r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        )
        # Also allow compact format without hyphens (32 hex digits)
        compact_pattern = re.compile(r"^[0-9a-fA-F]{32}$")

        if not (
            uuid_pattern.match(uuid_str) or compact_pattern.match(uuid_str)
        ):
            raise ValueError(f"Invalid UUID string: {uuid_string}")

        try:
            uuid_value = UUID(uuid_str)
            return cls(uuid_value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid UUID string: {uuid_string}") from e

    def __str__(self) -> str:
        """Return string representation of the ID."""
        return str(self.value)

    def __eq__(self, other: Any) -> bool:
        """Compare SubjectiveId instances for equality."""
        if not isinstance(other, SubjectiveId):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Return hash of the UUID value."""
        return hash(self.value)
