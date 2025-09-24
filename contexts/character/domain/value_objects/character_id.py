#!/usr/bin/env python3
"""
Character ID Value Object

This module implements the CharacterID value object, providing a strongly-typed
identifier for Character aggregates with validation and immutability guarantees.

Follows P3 Sprint 3 patterns for type safety and validation.
"""

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from ...infrastructure.character_domain_types import ensure_uuid


@dataclass(frozen=True)
class CharacterID:
    """
    Value object representing a unique Character identifier.

    This value object ensures that character identifiers are:
    - Immutable once created
    - Always valid UUID format
    - Type-safe for domain operations
    - Comparable for equality

    Following DDD principles, this prevents primitive obsession by
    providing a domain-specific type instead of using raw strings.
    """

    value: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self):
        """Validate the character ID format with type safety."""
        if not self.value:
            raise ValueError("CharacterID cannot be empty")

        # Validate UUID format with type guard
        try:
            from ...infrastructure.character_domain_types import ensure_uuid

            # Ensure the value is a valid UUID
            ensure_uuid(self.value)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"CharacterID must be a valid UUID format: {self.value}"
            ) from e

    @classmethod
    def generate(cls) -> "CharacterID":
        """Generate a new random CharacterID."""
        return cls(str(uuid.uuid4()))

    @classmethod
    def from_string(cls, id_string: Union[str, uuid.UUID]) -> "CharacterID":
        """Create CharacterID from string or UUID, validating format."""
        from ...infrastructure.character_domain_types import (
            CharacterDomainTyping,
        )

        # Convert to string using type-safe conversion
        if isinstance(id_string, uuid.UUID):
            return cls(str(id_string))
        elif isinstance(id_string, str):
            # Validate format before creating
            try:
                uuid.UUID(id_string)  # Validate format
                return cls(id_string)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {id_string}")
        else:
            raise TypeError(
                f"Cannot create CharacterID from {type(id_string)}"
            )

    def __str__(self) -> str:
        """String representation of the character ID."""
        return self.value

    def __repr__(self) -> str:
        """Developer representation of the character ID."""
        return f"CharacterID('{self.value}')"

    def to_uuid(self) -> uuid.UUID:
        """Convert CharacterID to UUID object."""
        return uuid.UUID(self.value)

    def __eq__(self, other) -> bool:
        """Check equality with another CharacterID."""
        if not isinstance(other, CharacterID):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Hash for use in sets and dictionaries."""
        return hash(self.value)
