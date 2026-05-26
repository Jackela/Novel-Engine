"""Identity infrastructure repositories package.

PostgreSQL support is an optional integration. Keep this package importable in
core CLI/API environments where the postgres extra is not installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.contexts.identity.infrastructure.repositories.postgres_user_repository import (
        PostgresUserRepository,
    )

__all__ = ["PostgresUserRepository"]


def __getattr__(name: str) -> Any:
    """Lazily resolve optional repository implementations."""
    if name == "PostgresUserRepository":
        from src.contexts.identity.infrastructure.repositories.postgres_user_repository import (
            PostgresUserRepository,
        )

        return PostgresUserRepository
    raise AttributeError(name)
