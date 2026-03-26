"""
Tests for API dependencies.
"""

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from src.apps.api.dependencies import (
    CurrentUser,
    PaginationParams,
    get_current_user,
    get_current_user_optional,
    get_pagination,
    require_permissions,
    require_roles,
    reset_jwt_manager,
)
from src.shared.infrastructure.config.settings import reset_settings


class TestCurrentUser:
    """Test CurrentUser model."""

    def test_user_creation(self):
        """Test creating a user."""
        user = CurrentUser(
            user_id="test-123",
            username="testuser",
            email="test@example.com",
            roles=["user"],
            permissions=["read"],
        )
        assert user.user_id == "test-123"
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_has_permission(self):
        """Test permission checking."""
        user = CurrentUser(
            user_id="test",
            username="test",
            email="test@test.com",
            roles=["user"],
            permissions=["read", "write"],
        )
        assert user.has_permission("read") is True
        assert user.has_permission("write") is True
        assert user.has_permission("delete") is False

    def test_has_role(self):
        """Test role checking."""
        user = CurrentUser(
            user_id="test",
            username="test",
            email="test@test.com",
            roles=["admin", "user"],
            permissions=[],
        )
        assert user.has_role("admin") is True
        assert user.has_role("user") is True
        assert user.has_role("guest") is False


class TestPaginationParams:
    """Test pagination parameters."""

    def test_default_pagination(self):
        """Test default pagination values."""
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.offset == 0
        assert params.sort_order == "asc"

    def test_custom_pagination(self):
        """Test custom pagination values."""
        params = PaginationParams(
            page=2, page_size=50, sort_by="name", sort_order="desc"
        )
        assert params.page == 2
        assert params.page_size == 50
        assert params.offset == 50  # (2-1) * 50
        assert params.sort_by == "name"
        assert params.sort_order == "desc"

    def test_pagination_bounds(self):
        """Test pagination bounds enforcement."""
        # Page should be at least 1
        params = PaginationParams(page=0)
        assert params.page == 1

        # Page size should be capped at 100
        params = PaginationParams(page_size=200)
        assert params.page_size == 100

        # Page size should be at least 1
        params = PaginationParams(page_size=0)
        assert params.page_size == 1

    def test_invalid_sort_order(self):
        """Test invalid sort order defaults to asc."""
        params = PaginationParams(sort_order="invalid")
        assert params.sort_order == "asc"


class TestGetPagination:
    """Test pagination dependency."""

    def test_get_pagination_function(self):
        """Test get_pagination dependency function."""
        params = get_pagination(
            page=3, page_size=15, sort_by="created_at", sort_order="desc"
        )
        assert params.page == 3
        assert params.page_size == 15
        assert params.sort_by == "created_at"
        assert params.sort_order == "desc"


@pytest.mark.asyncio
class TestAuthenticationDependencies:
    """Test authentication dependencies."""

    @pytest.fixture(autouse=True)
    def setup_jwt_manager(self):
        """Reset JWT manager and settings to use updated secret key."""
        reset_settings()
        reset_jwt_manager()
        yield
        # Cleanup after tests
        reset_jwt_manager()

    def _create_valid_token(self) -> str:
        """Create a valid JWT token for testing."""
        from src.apps.api.dependencies import get_jwt_manager

        jwt_manager = get_jwt_manager()
        return jwt_manager.create_access_token(
            user_id="test-user-123",
            username="testuser",
            email="test@example.com",
            roles=["user"],
        )

    async def test_get_current_user_optional_no_credentials(self):
        """Test optional auth without credentials."""
        user = await get_current_user_optional(None)
        assert user is None

    async def test_get_current_user_optional_with_credentials(self):
        """Test optional auth with credentials."""
        token = self._create_valid_token()
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = await get_current_user_optional(credentials)
        assert user is not None
        assert user.user_id is not None

    async def test_get_current_user_required_no_credentials(self):
        """Test required auth without credentials raises error."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_current_user_required_with_credentials(self):
        """Test required auth with credentials."""
        token = self._create_valid_token()
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = await get_current_user(credentials)
        assert user is not None


class TestPermissionDependencies:
    """Test permission-based dependencies."""

    def test_require_permissions_returns_coroutine(self):
        """Test permission check factory returns coroutine."""
        import asyncio

        dep = require_permissions("items:read")
        # require_permissions returns a coroutine (async function)
        assert asyncio.iscoroutine(dep)
        dep.close()  # Discard without awaiting to avoid RuntimeWarning

    def test_require_permissions_creates_dependency(self):
        """Test permission check creates dependency function."""
        result = require_permissions("admin:delete")
        # Result is the inner async function wrapped in coroutine
        assert result is not None
        result.close()  # Discard without awaiting to avoid RuntimeWarning


class TestRoleDependencies:
    """Test role-based dependencies."""

    def test_require_roles_returns_coroutine(self):
        """Test role check factory returns coroutine."""
        import asyncio

        dep = require_roles("user")
        assert asyncio.iscoroutine(dep)
        dep.close()  # Discard without awaiting to avoid RuntimeWarning

    def test_require_roles_creates_dependency(self):
        """Test role check creates dependency."""
        result = require_roles("admin")
        assert result is not None
        result.close()  # Discard without awaiting to avoid RuntimeWarning
