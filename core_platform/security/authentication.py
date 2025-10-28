"""
Authentication and JWT Token Management
======================================

Comprehensive authentication system with JWT tokens, password hashing,
session management, and security validation for Novel Engine platform.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import bcrypt
import jwt
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, or_
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from ..config.settings import get_security_settings
from ..persistence.models import BaseModel as DBModel
from ..persistence.models import TimestampMixin

logger = logging.getLogger(__name__)


class AuthenticationException(Exception):
    """Base exception for authentication errors."""

    pass


class InvalidCredentialsException(AuthenticationException):
    """Raised when credentials are invalid."""

    pass


class TokenExpiredException(AuthenticationException):
    """Raised when JWT token has expired."""

    pass


class InsufficientPermissionsException(AuthenticationException):
    """Raised when user lacks required permissions."""

    pass


# Database Models
class User(DBModel, TimestampMixin):
    """User account model."""

    __tablename__ = "users"

    # Basic user information
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)

    # Authentication
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(255), nullable=False)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Security tracking
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # IPv6 compatible

    # Password management
    password_changed_at = Column(DateTime(timezone=True), nullable=True)
    password_reset_token = Column(String(255), nullable=True, unique=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)

    # Email verification
    email_verification_token = Column(String(255), nullable=True, unique=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    user_sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """Set user password with proper hashing."""
        self.salt = secrets.token_hex(32)
        self.password_hash = self._hash_password(password, self.salt)
        self.password_changed_at = datetime.now(timezone.utc)

    def verify_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        return self._hash_password(password, self.salt) == self.password_hash

    def is_locked(self) -> bool:
        """Check if account is locked due to failed login attempts."""
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def lock_account(self, duration_minutes: int = 15) -> None:
        """Lock account for specified duration."""
        self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)

    def unlock_account(self) -> None:
        """Unlock account and reset failed attempts."""
        self.failed_login_attempts = 0
        self.locked_until = None

    def increment_failed_attempts(self, max_attempts: int = 5) -> None:
        """Increment failed login attempts and lock if necessary."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.lock_account()

    def generate_password_reset_token(self, expires_hours: int = 24) -> str:
        """Generate password reset token."""
        token = secrets.token_urlsafe(32)
        self.password_reset_token = token
        self.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
        return token

    def generate_email_verification_token(self, expires_hours: int = 24) -> str:
        """Generate email verification token."""
        token = secrets.token_urlsafe(32)
        self.email_verification_token = token
        self.email_verification_expires = datetime.now(timezone.utc) + timedelta(
            hours=expires_hours
        )
        return token

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Hash password with salt using bcrypt."""
        return bcrypt.hashpw(
            password.encode("utf-8") + salt.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")


class Role(DBModel, TimestampMixin):
    """Role model for RBAC system."""

    __tablename__ = "roles"

    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_system_role = Column(Boolean, default=False, nullable=False)

    # Relationships
    user_roles = relationship("UserRole", back_populates="role")
    role_permissions = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )


class Permission(DBModel, TimestampMixin):
    """Permission model for RBAC system."""

    __tablename__ = "permissions"

    name = Column(String(100), unique=True, nullable=False, index=True)
    resource = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)

    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission")


class UserRole(DBModel, TimestampMixin):
    """Many-to-many relationship between users and roles."""

    __tablename__ = "user_roles"

    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(PGUUID(as_uuid=True), ForeignKey("roles.id"), nullable=False, index=True)
    granted_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="user_roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_roles")
    granted_by_user = relationship("User", foreign_keys=[granted_by])


class RolePermission(DBModel, TimestampMixin):
    """Many-to-many relationship between roles and permissions."""

    __tablename__ = "role_permissions"

    role_id = Column(PGUUID(as_uuid=True), ForeignKey("roles.id"), nullable=False, index=True)
    permission_id = Column(
        PGUUID(as_uuid=True), ForeignKey("permissions.id"), nullable=False, index=True
    )
    granted_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")
    granted_by_user = relationship("User", foreign_keys=[granted_by])


class UserSession(DBModel, TimestampMixin):
    """User session tracking."""

    __tablename__ = "user_sessions"

    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=False, index=True)

    # Session metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Session lifecycle
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Security
    login_method = Column(String(50), nullable=True)  # password, oauth, etc.

    # Relationships
    user = relationship("User", back_populates="user_sessions")


# Pydantic Models for API
class LoginRequest(BaseModel):
    """Login request model."""

    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(default=False, description="Extended session")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        """Basic email validation."""
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email format")
        return v.lower().strip()


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")

    user: Dict[str, Any] = Field(..., description="User information")


class UserInfo(BaseModel):
    """User information model."""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="Username")
    full_name: str = Field(..., description="Full name")
    is_active: bool = Field(..., description="Account active status")
    is_verified: bool = Field(..., description="Email verified status")
    roles: List[str] = Field(..., description="User roles")
    permissions: List[str] = Field(..., description="User permissions")


class AuthenticationService:
    """
    Authentication service for user login, token management, and session handling.

    Features:
    - Password-based authentication with security controls
    - JWT token generation and validation
    - Session management and tracking
    - Account lockout and security monitoring
    - Password reset and email verification
    """

    def __init__(self):
        """Initialize authentication service."""
        self.config = get_security_settings()
        self._secret_key = self.config["jwt_secret_key"]
        self._algorithm = self.config["jwt_algorithm"]
        self._access_token_expires = self.config["jwt_access_token_expires"]
        self._refresh_token_expires = self.config["jwt_refresh_token_expires"]

    async def authenticate_user(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        """
        Authenticate user and return tokens.

        Args:
            email: User email
            password: User password
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            TokenResponse with access and refresh tokens

        Raises:
            InvalidCredentialsException: If credentials are invalid
            AuthenticationException: If account is locked or inactive
        """
        from ..persistence.database import get_db_session

        try:
            with get_db_session() as session:
                # Find user by email
                user = session.query(User).filter(User.email == email.lower()).first()

                if not user:
                    raise InvalidCredentialsException("Invalid email or password")

                # Check account status
                if not user.is_active:
                    raise AuthenticationException("Account is deactivated")

                if user.is_locked():
                    raise AuthenticationException("Account is temporarily locked")

                # Verify password
                if not user.verify_password(password):
                    user.increment_failed_attempts()
                    session.commit()
                    raise InvalidCredentialsException("Invalid email or password")

                # Reset failed attempts on successful login
                user.failed_login_attempts = 0
                user.locked_until = None
                user.last_login_at = datetime.now(timezone.utc)
                user.last_login_ip = ip_address

                # Generate tokens
                access_token = self._generate_access_token(user)
                refresh_token = self._generate_refresh_token(user)

                # Create session record
                session_record = UserSession(
                    user_id=user.id,
                    session_token=access_token,
                    refresh_token=refresh_token,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    expires_at=datetime.now(timezone.utc)
                    + timedelta(seconds=self._access_token_expires),
                    login_method="password",
                )

                session.add(session_record)
                session.commit()

                # Get user info
                user_info = await self._get_user_info(user, session)

                return TokenResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=self._access_token_expires,
                    user=user_info,
                )

        except (InvalidCredentialsException, AuthenticationException):
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise AuthenticationException("Authentication failed")

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New TokenResponse with refreshed tokens

        Raises:
            TokenExpiredException: If refresh token is expired or invalid
        """
        try:
            # Decode refresh token
            payload = jwt.decode(refresh_token, self._secret_key, algorithms=[self._algorithm])

            user_id = payload.get("user_id")
            if not user_id:
                raise TokenExpiredException("Invalid refresh token")

            from ..persistence.database import get_db_session

            with get_db_session() as session:
                # Find user and session
                user = session.query(User).filter(User.id == user_id).first()
                if not user or not user.is_active:
                    raise TokenExpiredException("Invalid refresh token")

                session_record = (
                    session.query(UserSession)
                    .filter(
                        UserSession.refresh_token == refresh_token,
                        UserSession.is_active is True,
                    )
                    .first()
                )

                if not session_record:
                    raise TokenExpiredException("Invalid refresh token")

                # Generate new tokens
                access_token = self._generate_access_token(user)
                new_refresh_token = self._generate_refresh_token(user)

                # Update session
                session_record.session_token = access_token
                session_record.refresh_token = new_refresh_token
                session_record.expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=self._access_token_expires
                )
                session_record.last_activity_at = datetime.now(timezone.utc)

                session.commit()

                # Get user info
                user_info = await self._get_user_info(user, session)

                return TokenResponse(
                    access_token=access_token,
                    refresh_token=new_refresh_token,
                    expires_in=self._access_token_expires,
                    user=user_info,
                )

        except jwt.ExpiredSignatureError:
            raise TokenExpiredException("Refresh token has expired")
        except jwt.InvalidTokenError:
            raise TokenExpiredException("Invalid refresh token")
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise TokenExpiredException("Failed to refresh token")

    async def validate_token(self, token: str) -> UserInfo:
        """
        Validate access token and return user information.

        Args:
            token: JWT access token

        Returns:
            UserInfo object

        Raises:
            TokenExpiredException: If token is expired or invalid
        """
        try:
            # Decode token
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])

            user_id = payload.get("user_id")
            if not user_id:
                raise TokenExpiredException("Invalid access token")

            from ..persistence.database import get_db_session

            with get_db_session() as session:
                # Find user
                user = session.query(User).filter(User.id == user_id).first()
                if not user or not user.is_active:
                    raise TokenExpiredException("Invalid access token")

                # Update session activity
                session_record = (
                    session.query(UserSession)
                    .filter(
                        UserSession.session_token == token,
                        UserSession.is_active is True,
                    )
                    .first()
                )

                if session_record:
                    session_record.last_activity_at = datetime.now(timezone.utc)
                    session.commit()

                # Get user info
                user_info = await self._get_user_info(user, session)

                return UserInfo(
                    id=str(user.id),
                    email=user.email,
                    username=user.username,
                    full_name=user.full_name,
                    is_active=user.is_active,
                    is_verified=user.is_verified,
                    roles=user_info.get("roles", []),
                    permissions=user_info.get("permissions", []),
                )

        except jwt.ExpiredSignatureError:
            raise TokenExpiredException("Access token has expired")
        except jwt.InvalidTokenError:
            raise TokenExpiredException("Invalid access token")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise TokenExpiredException("Failed to validate token")

    async def logout(self, token: str) -> None:
        """
        Logout user by invalidating session.

        Args:
            token: Access token to invalidate
        """
        try:
            from ..persistence.database import get_db_session

            with get_db_session() as session:
                # Find and deactivate session
                session_record = (
                    session.query(UserSession)
                    .filter(
                        UserSession.session_token == token,
                        UserSession.is_active is True,
                    )
                    .first()
                )

                if session_record:
                    session_record.is_active = False
                    session.commit()

        except Exception as e:
            logger.error(f"Logout error: {e}")
            # Don't raise exception for logout failures

    def _generate_access_token(self, user: User) -> str:
        """Generate JWT access token for user."""
        payload = {
            "user_id": str(user.id),
            "email": user.email,
            "username": user.username,
            "exp": datetime.now(timezone.utc) + timedelta(seconds=self._access_token_expires),
            "iat": datetime.now(timezone.utc),
            "type": "access",
        }

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def _generate_refresh_token(self, user: User) -> str:
        """Generate JWT refresh token for user."""
        payload = {
            "user_id": str(user.id),
            "exp": datetime.now(timezone.utc) + timedelta(seconds=self._refresh_token_expires),
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
        }

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    async def _get_user_info(self, user: User, session) -> Dict[str, Any]:
        """Get comprehensive user information including roles and permissions."""
        # Get user roles
        user_roles = (
            session.query(UserRole)
            .filter(
                UserRole.user_id == user.id,
                or_(
                    UserRole.expires_at.is_(None),
                    UserRole.expires_at > datetime.now(timezone.utc),
                ),
            )
            .all()
        )

        roles = []
        permissions = set()

        for user_role in user_roles:
            roles.append(user_role.role.name)

            # Get role permissions
            role_permissions = (
                session.query(RolePermission)
                .filter(RolePermission.role_id == user_role.role_id)
                .all()
            )

            for role_permission in role_permissions:
                permissions.add(role_permission.permission.name)

        return {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "roles": roles,
            "permissions": list(permissions),
        }


# Global authentication service instance
_auth_service: Optional[AuthenticationService] = None


def get_auth_service() -> AuthenticationService:
    """Get the global authentication service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthenticationService()
    return _auth_service
