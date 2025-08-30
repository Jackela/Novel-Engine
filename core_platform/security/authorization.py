"""
Role-Based Access Control (RBAC) Authorization System
====================================================

Comprehensive authorization framework with role and permission management,
access control decorators, and policy enforcement for Novel Engine platform.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..persistence.database import get_db_session
from .authentication import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Standard resource types for permission management."""

    CHARACTER = "character"
    STORY = "story"
    CAMPAIGN = "campaign"
    USER = "user"
    SYSTEM = "system"
    ANALYTICS = "analytics"


class ActionType(Enum):
    """Standard action types for permissions."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    ADMIN = "admin"
    EXECUTE = "execute"


class SystemRole(Enum):
    """Predefined system roles."""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"


class AuthorizationException(Exception):
    """Base exception for authorization errors."""

    pass


class InsufficientPermissionsException(AuthorizationException):
    """Raised when user lacks required permissions."""

    pass


class RoleNotFoundException(AuthorizationException):
    """Raised when role is not found."""

    pass


class PermissionNotFoundException(AuthorizationException):
    """Raised when permission is not found."""

    pass


class PermissionManager:
    """
    Manages permissions, roles, and access control policies.

    Features:
    - Dynamic permission creation and management
    - Role hierarchy and inheritance
    - Permission caching and optimization
    - Bulk permission operations
    - Audit trail for permission changes
    """

    def __init__(self):
        """Initialize permission manager."""
        self._permission_cache: Dict[str, Set[str]] = {}
        self._role_cache: Dict[str, Dict[str, Any]] = {}

    def create_permission(
        self,
        session: Session,
        name: str,
        resource: str,
        action: str,
        description: Optional[str] = None,
    ) -> Permission:
        """
        Create a new permission.

        Args:
            session: Database session
            name: Permission name (unique)
            resource: Resource type
            action: Action type
            description: Optional description

        Returns:
            Created Permission object
        """
        try:
            # Check if permission already exists
            existing = session.query(Permission).filter(Permission.name == name).first()
            if existing:
                return existing

            permission = Permission(
                name=name, resource=resource, action=action, description=description
            )

            session.add(permission)
            session.commit()

            logger.info(f"Created permission: {name}")
            return permission

        except Exception as e:
            logger.error(f"Failed to create permission {name}: {e}")
            session.rollback()
            raise

    def create_role(
        self,
        session: Session,
        name: str,
        description: Optional[str] = None,
        is_system_role: bool = False,
    ) -> Role:
        """
        Create a new role.

        Args:
            session: Database session
            name: Role name (unique)
            description: Optional description
            is_system_role: Whether this is a system role

        Returns:
            Created Role object
        """
        try:
            # Check if role already exists
            existing = session.query(Role).filter(Role.name == name).first()
            if existing:
                return existing

            role = Role(
                name=name, description=description, is_system_role=is_system_role
            )

            session.add(role)
            session.commit()

            logger.info(f"Created role: {name}")
            return role

        except Exception as e:
            logger.error(f"Failed to create role {name}: {e}")
            session.rollback()
            raise

    def assign_permission_to_role(
        self,
        session: Session,
        role_name: str,
        permission_name: str,
        granted_by_user_id: Optional[str] = None,
    ) -> None:
        """
        Assign a permission to a role.

        Args:
            session: Database session
            role_name: Role name
            permission_name: Permission name
            granted_by_user_id: User who granted the permission
        """
        try:
            # Find role and permission
            role = session.query(Role).filter(Role.name == role_name).first()
            if not role:
                raise RoleNotFoundException(f"Role {role_name} not found")

            permission = (
                session.query(Permission)
                .filter(Permission.name == permission_name)
                .first()
            )
            if not permission:
                raise PermissionNotFoundException(
                    f"Permission {permission_name} not found"
                )

            # Check if assignment already exists
            existing = (
                session.query(RolePermission)
                .filter(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
                .first()
            )

            if existing:
                logger.debug(
                    f"Permission {permission_name} already assigned to role {role_name}"
                )
                return

            # Create assignment
            role_permission = RolePermission(
                role_id=role.id,
                permission_id=permission.id,
                granted_by=granted_by_user_id,
            )

            session.add(role_permission)
            session.commit()

            # Clear cache
            self._clear_role_cache(role_name)

            logger.info(f"Assigned permission {permission_name} to role {role_name}")

        except Exception as e:
            logger.error(
                f"Failed to assign permission {permission_name} to role {role_name}: {e}"
            )
            session.rollback()
            raise

    def assign_role_to_user(
        self,
        session: Session,
        user_id: str,
        role_name: str,
        granted_by_user_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> None:
        """
        Assign a role to a user.

        Args:
            session: Database session
            user_id: User ID
            role_name: Role name
            granted_by_user_id: User who granted the role
            expires_at: Optional role expiration
        """
        try:
            # Find user and role
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                raise AuthorizationException(f"User {user_id} not found")

            role = session.query(Role).filter(Role.name == role_name).first()
            if not role:
                raise RoleNotFoundException(f"Role {role_name} not found")

            # Check if assignment already exists
            existing = (
                session.query(UserRole)
                .filter(
                    UserRole.user_id == user.id,
                    UserRole.role_id == role.id,
                    or_(
                        UserRole.expires_at.is_(None),
                        UserRole.expires_at > datetime.now(timezone.utc),
                    ),
                )
                .first()
            )

            if existing:
                logger.debug(f"Role {role_name} already assigned to user {user_id}")
                return

            # Create assignment
            user_role = UserRole(
                user_id=user.id,
                role_id=role.id,
                granted_by=granted_by_user_id,
                expires_at=expires_at,
            )

            session.add(user_role)
            session.commit()

            # Clear cache
            self._clear_user_cache(str(user.id))

            logger.info(f"Assigned role {role_name} to user {user_id}")

        except Exception as e:
            logger.error(f"Failed to assign role {role_name} to user {user_id}: {e}")
            session.rollback()
            raise

    def has_permission(
        self, user_id: str, permission_name: str, use_cache: bool = True
    ) -> bool:
        """
        Check if user has a specific permission.

        Args:
            user_id: User ID
            permission_name: Permission name to check
            use_cache: Whether to use cached permissions

        Returns:
            True if user has permission, False otherwise
        """
        try:
            # Check cache first
            if use_cache and user_id in self._permission_cache:
                return permission_name in self._permission_cache[user_id]

            with get_db_session() as session:
                # Get user permissions
                permissions = self._get_user_permissions(session, user_id)

                # Cache permissions
                if use_cache:
                    self._permission_cache[user_id] = permissions

                return permission_name in permissions

        except Exception as e:
            logger.error(
                f"Failed to check permission {permission_name} for user {user_id}: {e}"
            )
            return False

    def has_any_permission(
        self, user_id: str, permission_names: List[str], use_cache: bool = True
    ) -> bool:
        """
        Check if user has any of the specified permissions.

        Args:
            user_id: User ID
            permission_names: List of permission names
            use_cache: Whether to use cached permissions

        Returns:
            True if user has any permission, False otherwise
        """
        try:
            # Check cache first
            if use_cache and user_id in self._permission_cache:
                user_permissions = self._permission_cache[user_id]
                return any(perm in user_permissions for perm in permission_names)

            with get_db_session() as session:
                # Get user permissions
                permissions = self._get_user_permissions(session, user_id)

                # Cache permissions
                if use_cache:
                    self._permission_cache[user_id] = permissions

                return any(perm in permissions for perm in permission_names)

        except Exception as e:
            logger.error(
                f"Failed to check permissions {permission_names} for user {user_id}: {e}"
            )
            return False

    def has_role(self, user_id: str, role_name: str, use_cache: bool = True) -> bool:
        """
        Check if user has a specific role.

        Args:
            user_id: User ID
            role_name: Role name to check
            use_cache: Whether to use cached roles

        Returns:
            True if user has role, False otherwise
        """
        try:
            # Check cache first
            if use_cache and user_id in self._role_cache:
                user_roles = self._role_cache[user_id].get("roles", [])
                return role_name in user_roles

            with get_db_session() as session:
                # Get user roles
                user_roles = (
                    session.query(UserRole)
                    .filter(
                        UserRole.user_id == user_id,
                        or_(
                            UserRole.expires_at.is_(None),
                            UserRole.expires_at > datetime.now(timezone.utc),
                        ),
                    )
                    .all()
                )

                roles = [ur.role.name for ur in user_roles]

                # Cache roles
                if use_cache:
                    self._role_cache[user_id] = {"roles": roles}

                return role_name in roles

        except Exception as e:
            logger.error(f"Failed to check role {role_name} for user {user_id}: {e}")
            return False

    def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for a user."""
        try:
            with get_db_session() as session:
                return self._get_user_permissions(session, user_id)
        except Exception as e:
            logger.error(f"Failed to get permissions for user {user_id}: {e}")
            return set()

    def _get_user_permissions(self, session: Session, user_id: str) -> Set[str]:
        """Internal method to get user permissions from database."""
        permissions = set()

        # Get user roles
        user_roles = (
            session.query(UserRole)
            .filter(
                UserRole.user_id == user_id,
                or_(
                    UserRole.expires_at.is_(None),
                    UserRole.expires_at > datetime.now(timezone.utc),
                ),
            )
            .all()
        )

        # Get permissions for each role
        for user_role in user_roles:
            role_permissions = (
                session.query(RolePermission)
                .filter(RolePermission.role_id == user_role.role_id)
                .all()
            )

            for role_permission in role_permissions:
                permissions.add(role_permission.permission.name)

        return permissions

    def _clear_user_cache(self, user_id: str) -> None:
        """Clear cached data for a user."""
        self._permission_cache.pop(user_id, None)
        self._role_cache.pop(user_id, None)

    def _clear_role_cache(self, role_name: str) -> None:
        """Clear cached data affected by role changes."""
        # Clear all user caches since role permissions changed
        self._permission_cache.clear()
        self._role_cache.clear()

    def initialize_system_permissions(self) -> None:
        """Initialize default system permissions and roles."""
        try:
            with get_db_session() as session:
                # Create default permissions
                default_permissions = [
                    # Character permissions
                    (
                        "character.create",
                        ResourceType.CHARACTER.value,
                        ActionType.CREATE.value,
                        "Create characters",
                    ),
                    (
                        "character.read",
                        ResourceType.CHARACTER.value,
                        ActionType.READ.value,
                        "View characters",
                    ),
                    (
                        "character.update",
                        ResourceType.CHARACTER.value,
                        ActionType.UPDATE.value,
                        "Update characters",
                    ),
                    (
                        "character.delete",
                        ResourceType.CHARACTER.value,
                        ActionType.DELETE.value,
                        "Delete characters",
                    ),
                    (
                        "character.admin",
                        ResourceType.CHARACTER.value,
                        ActionType.ADMIN.value,
                        "Administer all characters",
                    ),
                    # Story permissions
                    (
                        "story.create",
                        ResourceType.STORY.value,
                        ActionType.CREATE.value,
                        "Create stories",
                    ),
                    (
                        "story.read",
                        ResourceType.STORY.value,
                        ActionType.READ.value,
                        "View stories",
                    ),
                    (
                        "story.update",
                        ResourceType.STORY.value,
                        ActionType.UPDATE.value,
                        "Update stories",
                    ),
                    (
                        "story.delete",
                        ResourceType.STORY.value,
                        ActionType.DELETE.value,
                        "Delete stories",
                    ),
                    (
                        "story.admin",
                        ResourceType.STORY.value,
                        ActionType.ADMIN.value,
                        "Administer all stories",
                    ),
                    # Campaign permissions
                    (
                        "campaign.create",
                        ResourceType.CAMPAIGN.value,
                        ActionType.CREATE.value,
                        "Create campaigns",
                    ),
                    (
                        "campaign.read",
                        ResourceType.CAMPAIGN.value,
                        ActionType.READ.value,
                        "View campaigns",
                    ),
                    (
                        "campaign.update",
                        ResourceType.CAMPAIGN.value,
                        ActionType.UPDATE.value,
                        "Update campaigns",
                    ),
                    (
                        "campaign.delete",
                        ResourceType.CAMPAIGN.value,
                        ActionType.DELETE.value,
                        "Delete campaigns",
                    ),
                    (
                        "campaign.admin",
                        ResourceType.CAMPAIGN.value,
                        ActionType.ADMIN.value,
                        "Administer all campaigns",
                    ),
                    # User management permissions
                    (
                        "user.create",
                        ResourceType.USER.value,
                        ActionType.CREATE.value,
                        "Create users",
                    ),
                    (
                        "user.read",
                        ResourceType.USER.value,
                        ActionType.READ.value,
                        "View users",
                    ),
                    (
                        "user.update",
                        ResourceType.USER.value,
                        ActionType.UPDATE.value,
                        "Update users",
                    ),
                    (
                        "user.delete",
                        ResourceType.USER.value,
                        ActionType.DELETE.value,
                        "Delete users",
                    ),
                    (
                        "user.admin",
                        ResourceType.USER.value,
                        ActionType.ADMIN.value,
                        "Administer all users",
                    ),
                    # System permissions
                    (
                        "system.admin",
                        ResourceType.SYSTEM.value,
                        ActionType.ADMIN.value,
                        "System administration",
                    ),
                    (
                        "system.monitor",
                        ResourceType.SYSTEM.value,
                        ActionType.READ.value,
                        "Monitor system health",
                    ),
                    (
                        "analytics.read",
                        ResourceType.ANALYTICS.value,
                        ActionType.READ.value,
                        "View analytics",
                    ),
                ]

                for name, resource, action, description in default_permissions:
                    self.create_permission(session, name, resource, action, description)

                # Create default roles
                default_roles = [
                    (
                        SystemRole.SUPER_ADMIN.value,
                        "Super Administrator with all permissions",
                        True,
                    ),
                    (
                        SystemRole.ADMIN.value,
                        "Administrator with most permissions",
                        True,
                    ),
                    (
                        SystemRole.MODERATOR.value,
                        "Moderator with content management permissions",
                        True,
                    ),
                    (
                        SystemRole.USER.value,
                        "Regular user with basic permissions",
                        True,
                    ),
                    (SystemRole.GUEST.value, "Guest with read-only permissions", True),
                ]

                for name, description, is_system in default_roles:
                    self.create_role(session, name, description, is_system)

                # Assign permissions to roles
                role_permissions = {
                    SystemRole.SUPER_ADMIN.value: [
                        "character.admin",
                        "story.admin",
                        "campaign.admin",
                        "user.admin",
                        "system.admin",
                        "analytics.read",
                    ],
                    SystemRole.ADMIN.value: [
                        "character.admin",
                        "story.admin",
                        "campaign.admin",
                        "user.read",
                        "user.update",
                        "system.monitor",
                        "analytics.read",
                    ],
                    SystemRole.MODERATOR.value: [
                        "character.create",
                        "character.read",
                        "character.update",
                        "story.create",
                        "story.read",
                        "story.update",
                        "campaign.create",
                        "campaign.read",
                        "campaign.update",
                        "user.read",
                    ],
                    SystemRole.USER.value: [
                        "character.create",
                        "character.read",
                        "character.update",
                        "story.create",
                        "story.read",
                        "story.update",
                        "campaign.create",
                        "campaign.read",
                        "campaign.update",
                    ],
                    SystemRole.GUEST.value: [
                        "character.read",
                        "story.read",
                        "campaign.read",
                    ],
                }

                for role_name, permissions in role_permissions.items():
                    for permission_name in permissions:
                        self.assign_permission_to_role(
                            session, role_name, permission_name
                        )

                logger.info("Initialized system permissions and roles")

        except Exception as e:
            logger.error(f"Failed to initialize system permissions: {e}")
            raise


class AuthorizationService:
    """
    Main authorization service for permission checks and enforcement.

    Features:
    - Permission-based access control
    - Role-based access control
    - Resource-level authorization
    - Caching and performance optimization
    - Audit logging for security events
    """

    def __init__(self):
        """Initialize authorization service."""
        self.permission_manager = PermissionManager()

    def require_permission(self, permission_name: str):
        """
        Decorator to require specific permission for a function.

        Args:
            permission_name: Required permission name

        Usage:
            @require_permission("story.create")
            async def create_story(...):
                pass
        """

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract user from request context
                user_id = self._get_current_user_id()
                if not user_id:
                    raise InsufficientPermissionsException("Authentication required")

                if not self.permission_manager.has_permission(user_id, permission_name):
                    raise InsufficientPermissionsException(
                        f"Permission '{permission_name}' required"
                    )

                return await func(*args, **kwargs)

            return wrapper

        return decorator

    def require_role(self, role_name: str):
        """
        Decorator to require specific role for a function.

        Args:
            role_name: Required role name

        Usage:
            @require_role("admin")
            async def admin_function(...):
                pass
        """

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract user from request context
                user_id = self._get_current_user_id()
                if not user_id:
                    raise InsufficientPermissionsException("Authentication required")

                if not self.permission_manager.has_role(user_id, role_name):
                    raise InsufficientPermissionsException(
                        f"Role '{role_name}' required"
                    )

                return await func(*args, **kwargs)

            return wrapper

        return decorator

    def require_any_permission(self, permission_names: List[str]):
        """
        Decorator to require any of the specified permissions.

        Args:
            permission_names: List of acceptable permission names

        Usage:
            @require_any_permission(["story.read", "story.admin"])
            async def view_story(...):
                pass
        """

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract user from request context
                user_id = self._get_current_user_id()
                if not user_id:
                    raise InsufficientPermissionsException("Authentication required")

                if not self.permission_manager.has_any_permission(
                    user_id, permission_names
                ):
                    raise InsufficientPermissionsException(
                        f"One of permissions {permission_names} required"
                    )

                return await func(*args, **kwargs)

            return wrapper

        return decorator

    def _get_current_user_id(self) -> Optional[str]:
        """
        Get current user ID from request context.

        This is a placeholder implementation - in a real application,
        this would extract the user ID from the request context,
        HTTP headers, or dependency injection.
        """
        # TODO: Implement based on your web framework
        # For FastAPI: from request context or dependency injection
        # For Django: from request.user
        # For Flask: from session or g object
        return None

    def check_resource_access(
        self, user_id: str, resource_type: str, resource_id: str, action: str
    ) -> bool:
        """
        Check if user can perform action on specific resource.

        Args:
            user_id: User ID
            resource_type: Type of resource (e.g., "story", "character")
            resource_id: Specific resource ID
            action: Action to perform (e.g., "read", "update")

        Returns:
            True if access is allowed, False otherwise
        """
        # Check general permission first
        permission_name = f"{resource_type}.{action}"
        if self.permission_manager.has_permission(user_id, permission_name):
            return True

        # Check admin permission
        admin_permission = f"{resource_type}.admin"
        if self.permission_manager.has_permission(user_id, admin_permission):
            return True

        # TODO: Implement resource-specific ownership checks
        # This would check if the user owns the specific resource

        return False

    def initialize_system_data(self) -> None:
        """Initialize system permissions and roles."""
        self.permission_manager.initialize_system_permissions()


# Global authorization service instance
_auth_service: Optional[AuthorizationService] = None


def get_authorization_service() -> AuthorizationService:
    """Get the global authorization service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthorizationService()
    return _auth_service


# Convenience decorators
def require_permission(permission_name: str):
    """Decorator to require specific permission."""
    service = get_authorization_service()
    return service.require_permission(permission_name)


def require_role(role_name: str):
    """Decorator to require specific role."""
    service = get_authorization_service()
    return service.require_role(role_name)


def require_any_permission(permission_names: List[str]):
    """Decorator to require any of the specified permissions."""
    service = get_authorization_service()
    return service.require_any_permission(permission_names)
