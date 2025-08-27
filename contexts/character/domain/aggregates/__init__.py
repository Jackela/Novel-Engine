#!/usr/bin/env python3
"""
Character Domain Aggregates

This package contains the aggregate roots for the Character domain.
Aggregates are clusters of domain objects that can be treated as
a single unit for the purpose of data changes.

The Character aggregate is the main aggregate root that:
- Maintains consistency across all character-related data
- Enforces business rules and invariants  
- Raises domain events for state changes
- Provides the only entry point for character operations
"""

from .character import Character

__all__ = [
    "Character",
]