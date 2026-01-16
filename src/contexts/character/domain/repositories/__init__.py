#!/usr/bin/env python3
"""
Character Domain Repository Interfaces

This package contains repository interfaces for the Character domain.
Following DDD principles, repository interfaces are defined in the
domain layer while implementations reside in the infrastructure layer.

The repository provides:
- Collection-like interface for Character aggregates
- Abstraction over persistence concerns
- Query capabilities for finding characters
- Optimistic concurrency control support
"""

from .character_repository import (
    ConcurrencyException,
    ICharacterRepository,
    NotSupportedException,
    RepositoryException,
)

__all__ = [
    "ICharacterRepository",
    "RepositoryException",
    "ConcurrencyException",
    "NotSupportedException",
]
