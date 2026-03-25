"""FastAPI dependency providers using DI container.

This module provides FastAPI-compatible dependency functions
that resolve services from the DI container.
"""

from __future__ import annotations

from typing import Any, AsyncGenerator

import asyncpg
from fastapi import Depends, Request

from src.contexts.identity.application.services.authentication_service import (
    AuthenticationService,
)
from src.contexts.identity.domain.repositories.user_repository import UserRepository
from src.shared.infrastructure.auth.jwt_utils import JWTManager
from src.shared.infrastructure.di.container import ApplicationContainer

# Global container instance (initialized lazily)
_container: ApplicationContainer | None = None


def get_container() -> ApplicationContainer:
    """Get or create the global application container.

    This function returns a singleton container instance.
    The first call will initialize the container from configuration.

    Returns:
        ApplicationContainer: The global container instance.

    Example:
        >>> container = get_container()
        >>> auth_service = container.identity.authentication_service()
    """
    global _container
    if _container is None:
        _container = ApplicationContainer()
        # Load configuration from settings
        from src.shared.infrastructure.config.settings import get_settings

        settings = get_settings()
        _container.config.from_dict(
            {
                "database": {
                    "url": settings.database.url,
                    "max_connections": settings.database.pool_size,
                },
                "security": {
                    "secret_key": settings.security.secret_key,
                    "algorithm": settings.security.algorithm,
                    "access_token_expire_minutes": settings.security.access_token_expire_minutes,
                    "refresh_token_expire_days": settings.security.refresh_token_expire_days,
                },
                "honcho": {
                    "base_url": "https://api.honcho.dev",  # Default Honcho cloud URL
                    "api_key": None,  # Will be loaded from environment
                },
            }
        )
    return _container


def reset_container() -> None:
    """Reset the global container instance.

    This is useful for testing to ensure fresh container state.
    """
    global _container
    _container = None


async def get_database_pool(request: Request) -> Any:
    """FastAPI dependency for database connection pool.

    Args:
        request: FastAPI request object.

    Returns:
        Database connection pool instance.
    """
    container = get_container()
    return container.core.db_pool()


async def get_database_connection(
    request: Request,
) -> AsyncGenerator[asyncpg.Connection, None]:
    """FastAPI dependency for database connection.

    This dependency acquires a connection from the pool and
    automatically releases it when the request is complete.

    Args:
        request: FastAPI request object.

    Yields:
        Database connection from the pool.

    Example:
        @router.get("/items")
        async def get_items(conn: asyncpg.Connection = Depends(get_database_connection)):
            rows = await conn.fetch("SELECT * FROM items")
            return rows
    """
    container = get_container()
    pool = container.core.db_pool()

    async with pool.pool.acquire() as connection:
        yield connection


async def get_jwt_manager(request: Request) -> JWTManager:
    """FastAPI dependency for JWT manager.

    Args:
        request: FastAPI request object.

    Returns:
        JWT manager instance.
    """
    container = get_container()
    return container.core.jwt_manager()


async def get_user_repository(request: Request) -> UserRepository:
    """FastAPI dependency for user repository.

    Args:
        request: FastAPI request object.

    Returns:
        User repository instance.
    """
    container = get_container()
    return container.identity.user_repository()


async def get_authentication_service(request: Request) -> AuthenticationService:
    """FastAPI dependency for authentication service.

    Args:
        request: FastAPI request object.

    Returns:
        Authentication service instance.
    """
    container = get_container()
    return container.identity.authentication_service()


async def get_current_user(
    request: Request,
    jwt_manager: JWTManager = Depends(get_jwt_manager),
) -> dict[str, Any] | None:
    """Get current user from JWT token in request headers.

    Args:
        request: FastAPI request object.
        jwt_manager: JWT manager dependency.

    Returns:
        User dictionary if token is valid, None otherwise.

    Example:
        @router.get("/profile")
        async def get_profile(user: dict = Depends(get_current_user)):
            if user is None:
                raise HTTPException(status_code=401)
            return user
    """
    auth_header = request.headers.get("authorization")
    if not auth_header:
        return None

    # Extract token from "Bearer <token>" format
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]

    try:
        payload = jwt_manager.verify_access_token(token)
        return {
            "id": payload.get("sub"),
            "username": payload.get("username"),
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
        }
    except Exception:
        return None


async def get_honcho_client(request: Request) -> Any:
    """FastAPI dependency for Honcho client.

    Args:
        request: FastAPI request object.

    Returns:
        Honcho client instance.
    """
    container = get_container()
    return container.core.honcho_client()


# Re-export container for direct access
__all__ = [
    "get_container",
    "reset_container",
    "get_database_pool",
    "get_database_connection",
    "get_jwt_manager",
    "get_user_repository",
    "get_authentication_service",
    "get_current_user",
    "get_honcho_client",
]
