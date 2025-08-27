#!/usr/bin/env python3
"""
Narrative Identifier Value Object

This module defines the NarrativeId value object, which serves as the
unique identifier for narrative elements within the Narrative domain.
"""

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID, uuid4


@dataclass(frozen=True)
class NarrativeId:
    """
    Unique identifier for narrative elements.
    
    This immutable value object ensures that narrative elements can be
    uniquely identified across the system while maintaining type safety
    and preventing identifier confusion with other domain contexts.
    """
    
    value: UUID
    
    # Class-level metadata
    _context_name: ClassVar[str] = "narratives"
    _type_name: ClassVar[str] = "NarrativeId"
    
    def __post_init__(self):
        """Validate the UUID value after initialization."""
        if not isinstance(self.value, UUID):
            raise TypeError(f"NarrativeId value must be a UUID, got {type(self.value)}")
    
    @classmethod
    def generate(cls) -> 'NarrativeId':
        """
        Generate a new unique NarrativeId.
        
        Returns:
            New NarrativeId with a randomly generated UUID
        """
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, id_string: str) -> 'NarrativeId':
        """
        Create a NarrativeId from a string representation.
        
        Args:
            id_string: String representation of a UUID
            
        Returns:
            NarrativeId created from the string
            
        Raises:
            ValueError: If the string is not a valid UUID format
        """
        try:
            uuid_value = UUID(id_string)
            return cls(uuid_value)
        except ValueError as e:
            raise ValueError(f"Invalid UUID format for NarrativeId: {id_string}") from e
    
    def to_string(self) -> str:
        """
        Get the string representation of this identifier.
        
        Returns:
            String representation of the underlying UUID
        """
        return str(self.value)
    
    def __str__(self) -> str:
        """String representation for human-readable output."""
        return f"NarrativeId({self.value})"
    
    def __repr__(self) -> str:
        """Developer representation for debugging."""
        return f"NarrativeId(value={self.value!r})"