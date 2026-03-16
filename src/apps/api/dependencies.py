"""
API Dependencies

Dependency injection container for FastAPI endpoints.
Implements Clean Architecture dependency management.
"""

from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Security scheme
security = HTTPBearer(auto_error=False)


class DatabaseSession:
    """Database session dependency."""

    def __init__(self):
        self._session = None

    async def __aenter__(self):
        # TODO: Implement actual database session creation
        # from src.infrastructure.database import get_session
        # self._session = await get_session()
        return self._session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            # await self._session.close()
            pass


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[Optional[object], None]:
    """
    Get database session as async context manager.

    Yields:
        Database session object or None if not configured.
    """
    async with DatabaseSession() as session:
        yield session


async def get_database(request: Request) -> AsyncGenerator[Optional[object], None]:
    """
    Dependency for database session injection.

    Usage:
        @app.get("/items")
        async def get_items(db = Depends(get_database)):
            ...
    """
    async with get_db_session() as session:
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

    # TODO: Implement JWT token validation
    # For now, return a mock user
    return CurrentUser(
        user_id="mock-user-id",
        username="mockuser",
        email="mock@example.com",
        roles=["user"],
        permissions=["read"],
    )


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
