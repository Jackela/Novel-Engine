"""Character domain ports package.

This package contains port interfaces (abstract contracts) that the
domain layer defines and infrastructure implements.
"""

from __future__ import annotations

from .memory_port import (
    CharacterMemoryPort,
    MemoryEntry,
    MemoryQueryError,
    MemoryQueryPort,
    MemoryQueryResult,
    MemoryReasoningPort,
    MemoryStorageError,
    MemoryStoragePort,
    ScopeManagementPort,
)

__all__ = [
    "CharacterMemoryPort",
    "MemoryEntry",
    "MemoryQueryPort",
    "MemoryQueryResult",
    "MemoryReasoningPort",
    "MemoryStorageError",
    "MemoryStoragePort",
    "MemoryQueryError",
    "ScopeManagementPort",
]
