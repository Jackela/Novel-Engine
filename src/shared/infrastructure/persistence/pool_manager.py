"""Shared connection-pool lifecycle helpers."""

from __future__ import annotations

from src.shared.infrastructure.config.settings import get_settings
from src.shared.infrastructure.persistence.connection_pool import (
    DatabaseConnectionPool,
)

_connection_pool: DatabaseConnectionPool | None = None


async def get_connection_pool() -> DatabaseConnectionPool:
    """Get or create the shared database connection pool."""
    global _connection_pool
    if _connection_pool is None:
        settings = get_settings()
        _connection_pool = DatabaseConnectionPool(
            database_url=settings.database.url,
            max_connections=settings.database.pool_size + settings.database.max_overflow,
        )
        await _connection_pool.initialize()
    return _connection_pool


async def close_connection_pool() -> None:
    """Close the shared database connection pool."""
    global _connection_pool
    if _connection_pool is not None:
        await _connection_pool.close()
        _connection_pool = None


def reset_connection_pool() -> None:
    """Drop the cached pool reference without touching an active connection."""
    global _connection_pool
    _connection_pool = None
