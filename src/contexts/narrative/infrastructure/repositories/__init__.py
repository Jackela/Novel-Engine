"""Narrative Infrastructure Repositories Package.

This package contains repository implementations for the Narrative context.
Each implementation fulfills the port contracts defined in the application layer.

Why multiple implementations:
    Different implementations serve different needs:
    - InMemoryNarrativeRepository: Fast, for testing and development
    - Future: PostgreSQLNarrativeRepository for production persistence
"""

from .in_memory_narrative_repository import InMemoryNarrativeRepository

__all__ = ["InMemoryNarrativeRepository"]
