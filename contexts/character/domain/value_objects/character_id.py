#!/usr/bin/env python3
"""
Character ID Value Object

This module implements the CharacterID value object, providing a strongly-typed
identifier for Character aggregates with validation and immutability guarantees.
"""

import uuid
from dataclasses import dataclass
from typing import Union


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
    
    value: str
    
    def __post_init__(self):
        """Validate the character ID format."""
        if not self.value:
            raise ValueError("CharacterID cannot be empty")
        
        # Validate UUID format
        try:
            uuid.UUID(self.value)
        except ValueError:
            raise ValueError(f"CharacterID must be a valid UUID format: {self.value}")
    
    @classmethod
    def generate(cls) -> 'CharacterID':
        """Generate a new random CharacterID."""
        return cls(str(uuid.uuid4()))
    
    @classmethod
    def from_string(cls, id_string: str) -> 'CharacterID':
        """Create CharacterID from string, validating format."""
        return cls(id_string)
    
    def __str__(self) -> str:
        """String representation of the character ID."""
        return self.value
    
    def __repr__(self) -> str:
        """Developer representation of the character ID."""
        return f"CharacterID('{self.value}')"