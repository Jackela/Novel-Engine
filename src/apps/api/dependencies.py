"""API Dependencies

Dependency injection container for FastAPI endpoints.
Implements Clean Architecture dependency management.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.contexts.identity.application.services.authentication_service import (
    AuthenticationService,
)
from src.contexts.identity.application.services.identity_service import (
    IdentityApplicationService,
)
from src.contexts.identity.domain.repositories.user_repository import UserRepository
from src.contexts.identity.infrastructure.repositories.postgres_user_repository import (
    PostgresUserRepository,
)
from src.shared.infrastructure.auth.jwt_utils import JWTManager
from src.shared.infrastructure.config.settings import get_settings
from src.shared.infrastructure.persistence.connection_pool import (
    DatabaseConnectionPool,
)

# Security scheme
security = HTTPBearer(auto_error=False)

# Global connection pool instance (singleton)
_connection_pool: DatabaseConnectionPool | None = None

# Global JWT manager instance (singleton)
_jwt_manager: JWTManager | None = None

# Global service instances (singletons)
_user_repository: UserRepository | None = None
_authentication_service: AuthenticationService | None = None
_identity_service: IdentityApplicationService | None = None


def get_jwt_manager() -> JWTManager:
    """Get or create the global JWT manager.

    Returns:
        JWTManager: The global JWT manager instance.
    """
    global _jwt_manager
    if _jwt_manager is None:
        settings = get_settings()
        _jwt_manager = JWTManager(
            secret_key=settings.security.secret_key,
            algorithm=settings.security.algorithm,
            access_token_expire_minutes=settings.security.access_token_expire_minutes,
            refresh_token_expire_days=settings.security.refresh_token_expire_days,
        )
    return _jwt_manager


def reset_jwt_manager() -> None:
    """Reset the global JWT manager instance.

    This is useful for testing to ensure a fresh JWT manager is created.
    """
    global _jwt_manager
    _jwt_manager = None


async def get_connection_pool() -> DatabaseConnectionPool:
    """Get or create the global connection pool.

    Returns:
        DatabaseConnectionPool: The global connection pool instance.
    """
    global _connection_pool
    if _connection_pool is None:
        settings = get_settings()
        _connection_pool = DatabaseConnectionPool(
            database_url=settings.database.url,
            max_connections=settings.database.pool_size
            + settings.database.max_overflow,
        )
        await _connection_pool.initialize()
    return _connection_pool


async def close_connection_pool() -> None:
    """Close the global connection pool.

    This should be called during application shutdown.
    """
    global _connection_pool
    if _connection_pool is not None:
        await _connection_pool.close()
        _connection_pool = None


@asynccontextmanager
async def get_database_session() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get database session as async context manager.

    Yields:
        asyncpg.Connection: A database connection from the pool.

    Example:
        async with get_database_session() as conn:
            result = await conn.fetch("SELECT * FROM users")
    """
    pool = await get_connection_pool()
    conn = await pool.acquire()
    transaction = conn.transaction()
    await transaction.start()

    try:
        yield conn
        await transaction.commit()
    except Exception:
        await transaction.rollback()
        raise
    finally:
        await pool.release(conn)


async def get_database(
    request: Request,
) -> AsyncGenerator[asyncpg.Connection, None]:
    """Dependency for database session injection.

    Usage:
        @app.get("/items")
        async def get_items(db: asyncpg.Connection = Depends(get_database)):
            results = await db.fetch("SELECT * FROM items")
            ...

    Args:
        request: FastAPI request object.

    Yields:
        asyncpg.Connection: A database connection.
    """
    async with get_database_session() as session:
        yield session


class CurrentUser:
    """Current authenticated user data."""

    def __init__(
        self,
        user_id: str,
        username: str,
        email: str,
        roles: list[str],
        permissions: list[str],
    ):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.roles = roles
        self.permissions = permissions

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return role in self.roles


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Optional[CurrentUser]:
    """
    Get current user from JWT token (optional).

    Returns None if no valid credentials provided.
    """
    if not credentials:
        return None

    token = credentials.credentials
    jwt_manager = get_jwt_manager()

    try:
        payload = jwt_manager.verify_access_token(token)

        return CurrentUser(
            user_id=payload.get("sub"),
            username=payload.get("username", ""),
            email=payload.get("email", ""),
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
        )
    except Exception:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CurrentUser:
    """
    Get current authenticated user (required).

    Raises:
        HTTPException: If authentication fails.
    """
    user = await get_current_user_optional(credentials)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_permissions(*permissions: str):
    """
    Dependency factory for permission-based access control.

    Usage:
        @app.delete("/items/{id}")
        async def delete_item(
            user: CurrentUser = Depends(require_permissions("items:delete"))
        ):
            ...
    """

    async def check_permissions(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        for permission in permissions:
            if not user.has_permission(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission}",
                )
        return user

    return check_permissions


async def require_roles(*roles: str):
    """
    Dependency factory for role-based access control.

    Usage:
        @app.get("/admin")
        async def admin_only(
            user: CurrentUser = Depends(require_roles("admin"))
        ):
            ...
    """

    async def check_roles(
        user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        for role in roles:
            if not user.has_role(role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role required: {role}",
                )
        return user

    return check_roles


class PaginationParams:
    """Pagination query parameters."""

    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ):
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), 100)  # Cap at 100
        self.sort_by = sort_by
        self.sort_order = sort_order.lower() if sort_order in ("asc", "desc") else "asc"
        self.offset = (self.page - 1) * self.page_size


def get_pagination(
    page: int = 1,
    page_size: int = 20,
    sort_by: Optional[str] = None,
    sort_order: str = "asc",
) -> PaginationParams:
    """Dependency for pagination parameters."""
    return PaginationParams(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


async def get_user_repository() -> UserRepository:
    """Get or create the user repository.

    Returns:
        UserRepository: PostgreSQL user repository instance.
    """
    global _user_repository
    if _user_repository is None:
        pool = await get_connection_pool()
        _user_repository = PostgresUserRepository(pool.pool)
    return _user_repository


async def get_authentication_service() -> AuthenticationService:
    """Get or create the authentication service.

    Returns:
        AuthenticationService: Authentication service instance.
    """
    global _authentication_service
    if _authentication_service is None:
        user_repo = await get_user_repository()
        jwt_manager = get_jwt_manager()
        _authentication_service = AuthenticationService(user_repo, jwt_manager)
    return _authentication_service


async def get_identity_service() -> IdentityApplicationService:
    """Get or create the identity service.

    Returns:
        IdentityApplicationService: Identity service instance.
    """
    global _identity_service
    if _identity_service is None:
        user_repo = await get_user_repository()
        auth_service = await get_authentication_service()
        _identity_service = IdentityApplicationService(user_repo, auth_service)
    return _identity_service
