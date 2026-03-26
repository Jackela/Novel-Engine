"""World state persistence layer.

This package provides PostgreSQL-based persistence for WorldState aggregates.
The implementation is organized into specialized classes, each handling
a specific category of operations.

Classes:
    PostgresWorldStateRepository: Main facade providing unified access to all operations.
    PostgresWorldStateCrud: Basic create, read, update, delete operations.
    PostgresWorldStateQueries: Complex queries, searching, and filtering.
    PostgresWorldStateVersioning: Version history, rollback, and event sourcing.
    PostgresWorldStateSnapshots: Snapshot creation, restoration, and management.
    PostgresWorldStateBatch: Bulk operations for efficient batch processing.

Example:
    >>> from src.contexts.world.infrastructure.persistence import PostgresWorldStateRepository
    >>> repo = PostgresWorldStateRepository()
    >>> world_state = await repo.get_by_id("world-123")
    >>> await repo.save(world_state)
"""

from .postgres_world_state_batch import PostgresWorldStateBatch
from .postgres_world_state_crud import PostgresWorldStateCrud
from .postgres_world_state_queries import PostgresWorldStateQueries
from .postgres_world_state_repo import PostgresWorldStateRepository
from .postgres_world_state_snapshots import PostgresWorldStateSnapshots
from .postgres_world_state_versioning import PostgresWorldStateVersioning

__all__ = [
    "PostgresWorldStateRepository",
    "PostgresWorldStateCrud",
    "PostgresWorldStateQueries",
    "PostgresWorldStateVersioning",
    "PostgresWorldStateSnapshots",
    "PostgresWorldStateBatch",
]
