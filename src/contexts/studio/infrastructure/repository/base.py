from __future__ import annotations

from src.contexts.studio.infrastructure.repository.common import (
    StudioDatabase,
)

__all__ = ["RepositoryBase"]


class RepositoryBase:
    def __init__(self, database: StudioDatabase) -> None:
        self.database = database
