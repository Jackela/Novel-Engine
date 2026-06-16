from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.contexts.studio.infrastructure.repository.common import (
    StudioDatabase,
)

__all__ = ["RepositoryBase"]


class RepositoryBase:
    def __init__(self, database: StudioDatabase) -> None:
        self.database = database

    def health_check(self) -> bool:
        """Verify the persistence backend is reachable."""
        try:
            with self.database.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except (RuntimeError, SQLAlchemyError):
            return False
