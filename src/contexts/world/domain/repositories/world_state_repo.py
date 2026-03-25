"""World state repository implementation."""

from abc import ABC
from typing import TYPE_CHECKING

from src.contexts.world.domain.ports.world_state_repository_port import (
    WorldStateRepositoryPort,
)

if TYPE_CHECKING:
    pass


class RepositoryException(Exception):
    """Base repository exception."""

    pass


class ConcurrencyException(RepositoryException):
    """Concurrency conflict exception."""

    def __init__(
        self,
        message: str,
        expected_version: int | None = None,
        actual_version: int | None = None,
    ) -> None:
        super().__init__(message)
        self.expected_version = expected_version
        self.actual_version = actual_version


class EntityNotFoundException(RepositoryException):
    """Entity not found exception."""

    pass


class WorldStateRepository(WorldStateRepositoryPort, ABC):
    """Abstract implementation of WorldStateRepositoryPort."""

    pass
