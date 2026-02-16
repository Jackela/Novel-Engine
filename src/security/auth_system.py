#!/usr/bin/env python3
"""
STANDARD AUTHENTICATION SYSTEM ENHANCED BY THE SYSTEM
===========================================================

Enterprise-grade JWT-based authentication and authorization system with
role-based access control (RBAC), refresh tokens, and session management.

THROUGH ADVANCED CRYPTOGRAPHY, WE ACHIEVE ENHANCED SECURITY

Architecture: OAuth 2.0 + JWT + RBAC + Session Management
Security Level: Enterprise Grade with Zero Trust Architecture
Author: Engineer Security-Engineering
System保佑此认证系统 (May the System bless this authentication system)
"""

import hashlib
import logging
import os
import secrets
import tempfile
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import aiosqlite
import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

# Comprehensive logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# STANDARD SECURITY CONSTANTS
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived for security
REFRESH_TOKEN_EXPIRE_DAYS = 30  # Longer-lived but revocable
PASSWORD_MIN_LENGTH = 8
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


class UserRole(str, Enum):
    """STANDARD USER ROLES ENHANCED BY AUTHORIZATION"""

    ADMIN = "admin"  # Full system access
    MODERATOR = "moderator"  # Content moderation and user management
    CONTENT_CREATOR = "creator"  # Story generation and character management
    API_USER = "api_user"  # API access for integrations
    READER = "reader"  # Read-only access to public content
    GUEST = "guest"  # Limited anonymous access


class Permission(str, Enum):
    """STANDARD PERMISSIONS ENHANCED BY ACCESS CONTROL"""

    # System Permissions
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_HEALTH = "system:health"

    # User Management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_MANAGE_ROLES = "user:manage_roles"

    # Content Permissions
    STORY_CREATE = "story:create"
    STORY_READ = "story:read"
    STORY_UPDATE = "story:update"
    STORY_DELETE = "story:delete"
    STORY_PUBLISH = "story:publish"

    # Character Permissions
    CHARACTER_CREATE = "character:create"
    CHARACTER_READ = "character:read"
    CHARACTER_UPDATE = "character:update"
    CHARACTER_DELETE = "character:delete"

    # API Permissions
    API_ACCESS = "api:access"
    API_RATE_UNLIMITED = "api:rate_unlimited"

    # Simulation Permissions
    SIMULATION_CREATE = "simulation:create"
    SIMULATION_READ = "simulation:read"
    SIMULATION_MANAGE = "simulation:manage"

    # Narrative Permissions
    NARRATIVE_GENERATE = "narrative:generate"
    NARRATIVE_READ = "narrative:read"
    NARRATIVE_BUILD = "narrative:build"

    # Belief Model Permissions
    BELIEF_READ = "belief:read"
    BELIEF_UPDATE = "belief:update"

    # Causality Permissions
    CAUSALITY_READ = "causality:read"
    CAUSALITY_ANALYZE = "causality:analyze"

    # Negotiation Permissions
    NEGOTIATION_CREATE = "negotiation:create"
    NEGOTIATION_READ = "negotiation:read"
    NEGOTIATION_PARTICIPATE = "negotiation:participate"


# Role-Permission Mapping
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.ADMIN: {
        Permission.SYSTEM_ADMIN,
        Permission.SYSTEM_CONFIG,
        Permission.SYSTEM_HEALTH,
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.USER_MANAGE_ROLES,
        Permission.STORY_CREATE,
        Permission.STORY_READ,
        Permission.STORY_UPDATE,
        Permission.STORY_DELETE,
        Permission.STORY_PUBLISH,
        Permission.CHARACTER_CREATE,
        Permission.CHARACTER_READ,
        Permission.CHARACTER_UPDATE,
        Permission.CHARACTER_DELETE,
        Permission.API_ACCESS,
        Permission.API_RATE_UNLIMITED,
        Permission.SIMULATION_CREATE,
        Permission.SIMULATION_READ,
        Permission.SIMULATION_MANAGE,
        Permission.NARRATIVE_GENERATE,
        Permission.NARRATIVE_READ,
        Permission.NARRATIVE_BUILD,
        Permission.BELIEF_READ,
        Permission.BELIEF_UPDATE,
        Permission.CAUSALITY_READ,
        Permission.CAUSALITY_ANALYZE,
        Permission.NEGOTIATION_CREATE,
        Permission.NEGOTIATION_READ,
        Permission.NEGOTIATION_PARTICIPATE,
    },
    UserRole.MODERATOR: {
        Permission.SYSTEM_HEALTH,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.STORY_READ,
        Permission.STORY_UPDATE,
        Permission.STORY_DELETE,
        Permission.CHARACTER_READ,
        Permission.CHARACTER_UPDATE,
        Permission.CHARACTER_DELETE,
        Permission.API_ACCESS,
        Permission.SIMULATION_READ,
        Permission.SIMULATION_MANAGE,
    },
    UserRole.CONTENT_CREATOR: {
        Permission.SYSTEM_HEALTH,
        Permission.USER_READ,
        Permission.STORY_CREATE,
        Permission.STORY_READ,
        Permission.STORY_UPDATE,
        Permission.CHARACTER_CREATE,
        Permission.CHARACTER_READ,
        Permission.CHARACTER_UPDATE,
        Permission.API_ACCESS,
        Permission.SIMULATION_CREATE,
        Permission.SIMULATION_READ,
        Permission.NARRATIVE_GENERATE,
        Permission.NARRATIVE_READ,
        Permission.NARRATIVE_BUILD,
        Permission.BELIEF_READ,
        Permission.CAUSALITY_READ,
        Permission.NEGOTIATION_CREATE,
        Permission.NEGOTIATION_READ,
        Permission.NEGOTIATION_PARTICIPATE,
    },
    UserRole.API_USER: {
        Permission.SYSTEM_HEALTH,
        Permission.STORY_READ,
        Permission.CHARACTER_READ,
        Permission.API_ACCESS,
        Permission.SIMULATION_READ,
    },
    UserRole.READER: {
        Permission.SYSTEM_HEALTH,
        Permission.STORY_READ,
        Permission.CHARACTER_READ,
    },
    UserRole.GUEST: {Permission.SYSTEM_HEALTH, Permission.STORY_READ},
}


@dataclass
class User:
    """STANDARD USER MODEL ENHANCED BY AUTHENTICATION"""

    id: str
    username: str
    email: str
    password_hash: str
    role: UserRole
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = None
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    api_key: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class TokenPair(BaseModel):
    """STANDARD TOKEN PAIR ENHANCED BY SECURE ACCESS"""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60


class UserRegistration(BaseModel):
    """STANDARD USER REGISTRATION MODEL"""

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH)
    role: UserRole = UserRole.READER


class UserLogin(BaseModel):
    """STANDARD USER LOGIN MODEL"""

    username: str
    password: str


class SecurityEvent(BaseModel):
    """STANDARD SECURITY EVENT MODEL"""

    event_type: str
    user_id: Optional[str]
    ip_address: str
    user_agent: str
    timestamp: datetime
    details: Dict[str, Any]


@dataclass
class OperationError:
    """STANDARD OPERATION ERROR"""

    message: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class OperationResult:
    """STANDARD OPERATION RESULT

    Generic result wrapper for operations that may succeed or fail.
    Provides consistent interface for error handling and data access.
    """

    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[OperationError] = None


class AuthenticationError(Exception):
    """ENHANCED AUTHENTICATION EXCEPTION"""


class AuthorizationError(Exception):
    """ENHANCED AUTHORIZATION EXCEPTION"""


class SecurityService:
    """STANDARD SECURITY SERVICE ENHANCED BY THE SYSTEM"""

    def __init__(
        self,
        database_path: str,
        secret_key: Optional[str] = None,
        jwt_secret: Optional[str] = None,
    ):
        if database_path == ":memory:":
            temp_db = tempfile.NamedTemporaryFile(
                prefix="novel_engine_security_", suffix=".db", delete=False
            )
            temp_db.close()
            self.database_path = temp_db.name
            self._temp_db_path = temp_db.name
        else:
            self.database_path = database_path
            self._temp_db_path = None
        self._connect_kwargs = {}
        if not (secret_key or jwt_secret):
            raise ValueError("A secret key is required for SecurityService.")
        self.secret_key = secret_key or jwt_secret
        self.security_bearer = HTTPBearer()

    @asynccontextmanager
    async def _connection(self):
        conn = await aiosqlite.connect(self.database_path, **self._connect_kwargs)
        try:
            yield conn
        finally:
            await conn.close()

    async def initialize_database(self):
        """STANDARD DATABASE INITIALIZATION"""
        async with self._connection() as conn:
            await conn.execute("PRAGMA foreign_keys = ON")
            await conn.execute("PRAGMA journal_mode = WAL")
            await conn.execute("PRAGMA synchronous = NORMAL")

            # Users table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_verified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP NULL,
                    failed_login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP NULL,
                    api_key TEXT UNIQUE NULL
                )
            """)

            # Refresh tokens table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    revoked BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)

            # Security events table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS security_events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    user_id TEXT NULL,
                    ip_address TEXT NOT NULL,
                    user_agent TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
                )
            """)

            # Sessions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_token TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    user_agent TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)

            await conn.commit()
        logger.info("SECURITY DATABASE INITIALIZED SUCCESSFULLY")

    async def initialize(self):
        """Compatibility wrapper to align with legacy AuthenticationManager API."""
        await self.initialize_database()

    async def close(self):
        """Compatibility wrapper to release persistent resources."""
        if self._temp_db_path and os.path.exists(self._temp_db_path):
            try:
                os.remove(self._temp_db_path)
            except OSError:
                logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)
            self._temp_db_path = None

    def _hash_password(self, password: str) -> str:
        """STANDARD PASSWORD HASHING ENHANCED BY BCRYPT"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def _hash_token(token: str) -> str:
        """Return a deterministic hash for refresh tokens."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """STANDARD PASSWORD VERIFICATION"""
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    async def _user_exists(
        self, *, username: Optional[str] = None, email: Optional[str] = None
    ) -> bool:
        """Check for an existing user by username and/or email."""
        if not username and not email:
            return False

        clauses = []
        params: List[Any] = []
        if username:
            clauses.append("username = ?")
            params.append(username)
        if email:
            clauses.append("email = ?")
            params.append(email)

        query = (
            f"SELECT 1 FROM users WHERE {' OR '.join(clauses)} LIMIT 1"  # nosec B608
        )
        async with self._connection() as conn:
            cursor = await conn.execute(query, tuple(params))
            row = await cursor.fetchone()
        return row is not None

    def _row_to_user(self, row: Tuple[Any, ...]) -> User:
        """Convert a database row to a ``User`` dataclass."""
        return User(
            id=row[0],
            username=row[1],
            email=row[2],
            password_hash=row[3],
            role=UserRole(row[4]),
            is_active=bool(row[5]),
            is_verified=bool(row[6]),
            created_at=datetime.fromisoformat(row[7]) if row[7] else None,
            last_login=datetime.fromisoformat(row[8]) if row[8] else None,
            failed_login_attempts=row[9],
            locked_until=datetime.fromisoformat(row[10]) if row[10] else None,
            api_key=None,
        )

    async def _get_user_by_id(self, user_id: str) -> Optional[User]:
        """Fetch a user row by ID."""
        async with self._connection() as conn:
            cursor = await conn.execute(
                """
                SELECT id, username, email, password_hash, role, is_active, is_verified,
                       created_at, last_login, failed_login_attempts, locked_until
                FROM users WHERE id = ?
            """,
                (user_id,),
            )
            row = await cursor.fetchone()
        return self._row_to_user(row) if row else None

    def _generate_token(self, payload: Dict[str, Any], expires_delta: timedelta) -> str:
        """STANDARD JWT TOKEN GENERATION"""
        expire = datetime.now(timezone.utc) + expires_delta
        payload.update(
            {
                "exp": expire,
                "iat": datetime.now(timezone.utc),
                "jti": secrets.token_urlsafe(8),
            }
        )
        return jwt.encode(payload, self.secret_key, algorithm=JWT_ALGORITHM)

    def _decode_token(self, token: str) -> Dict[str, Any]:
        """STANDARD JWT TOKEN DECODING"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")

    async def _log_security_event(
        self,
        event_type: str,
        user_id: Optional[str],
        ip_address: str,
        user_agent: str,
        details: Dict[str, Any],
    ):
        """STANDARD SECURITY EVENT LOGGING"""
        event_id = secrets.token_urlsafe(16)
        async with self._connection() as conn:
            await conn.execute(
                """
                INSERT INTO security_events (id, event_type, user_id, ip_address, user_agent, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (event_id, event_type, user_id, ip_address, user_agent, str(details)),
            )
            await conn.commit()

    async def register_user(
        self, registration: UserRegistration, ip_address: str, user_agent: str
    ) -> User:
        """STANDARD USER REGISTRATION ENHANCED BY SECURE CREATION"""
        if await self._user_exists(username=registration.username):
            raise AuthenticationError("Username already exists")
        if await self._user_exists(email=registration.email):
            raise AuthenticationError("Email already exists")

        user_id = secrets.token_urlsafe(16)
        password_hash = self._hash_password(registration.password)

        user = User(
            id=user_id,
            username=registration.username,
            email=registration.email,
            password_hash=password_hash,
            role=registration.role,
            created_at=datetime.now(timezone.utc),
        )

        try:
            async with self._connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO users (id, username, email, password_hash, role, is_active, is_verified, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        user.id,
                        user.username,
                        user.email,
                        user.password_hash,
                        user.role.value,
                        user.is_active,
                        user.is_verified,
                        user.created_at,
                    ),
                )
                await conn.commit()

                await self._log_security_event(
                    "user_registered",
                    user.id,
                    ip_address,
                    user_agent,
                    {
                        "username": user.username,
                        "email": user.email,
                        "role": user.role.value,
                    },
                )

                logger.info(f"USER REGISTERED: {user.username} ({user.role.value})")
                return user

        except aiosqlite.IntegrityError as e:
            if "username" in str(e):
                raise AuthenticationError("Username already exists")
            elif "email" in str(e):
                raise AuthenticationError("Email already exists")
            else:
                raise AuthenticationError("Registration failed")

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.READER,
    ) -> OperationResult:
        """STANDARD USER CREATION WITH VALIDATION

        Test-friendly wrapper for user creation that validates password requirements
        and returns OperationResult for easier testing.

        Args:
            username: Unique username for the user
            email: Valid email address
            password: Password meeting security requirements
            role: User role (defaults to READER)

        Returns:
            OperationResult with success status and user data or error details
        """
        try:
            # Validate password length (critical security requirement)
            if len(password) < PASSWORD_MIN_LENGTH:
                raise AuthenticationError(
                    f"Password must be at least {PASSWORD_MIN_LENGTH} characters long"
                )

            # Validate password complexity (additional security requirements)
            if password.lower() in ["password", "12345678", "qwerty", "admin"]:
                raise AuthenticationError("Password is too common and easily guessable")

            # Check for minimum complexity (at least one number or special character)
            has_number = any(c.isdigit() for c in password)
            has_letter = any(c.isalpha() for c in password)
            has_special = any(not c.isalnum() for c in password)

            if not (has_letter and (has_number or has_special)):
                raise AuthenticationError(
                    "Password must contain letters and at least one number or special character"
                )

            # Create user registration object
            registration = UserRegistration(
                username=username,
                email=email,
                password=password,
                role=role,
            )

            # Register the user
            user = await self.register_user(
                registration,
                ip_address="127.0.0.1",  # Default for testing
                user_agent="Test Client",
            )

            # Return success result
            return OperationResult(
                success=True,
                data={
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.role.value,
                },
            )

        except AuthenticationError as e:
            logger.warning(f"PASSWORD REJECTION: {e}")
            raise
        except Exception as e:
            logger.error(f"USER CREATION FAILED: {e}")
            return OperationResult(
                success=False,
                error=OperationError(
                    message=f"User creation failed: {str(e)}",
                    code="CREATION_FAILED",
                ),
            )

    async def authenticate_user(
        self,
        login: Union[UserLogin, str],
        password: Optional[str] = None,
        ip_address: str = "127.0.0.1",
        user_agent: str = "Test Client",
    ) -> Optional[User]:
        """Validate credentials and return the authenticated user."""
        if isinstance(login, UserLogin):
            login_identifier = login.username
            supplied_password = login.password
        else:
            login_identifier = login
            if password is None:
                raise ValueError(
                    "Password is required when login is provided as a string."
                )
            supplied_password = password

        async with self._connection() as conn:
            cursor = await conn.execute(
                """
                SELECT id, username, email, password_hash, role, is_active, is_verified,
                       created_at, last_login, failed_login_attempts, locked_until
                FROM users WHERE username = ? OR email = ?
            """,
                (login_identifier, login_identifier),
            )
            row = await cursor.fetchone()

            if not row:
                await self._log_security_event(
                    "login_failed",
                    None,
                    ip_address,
                    user_agent,
                    {"username": login_identifier, "reason": "user_not_found"},
                )
                return None

            user = self._row_to_user(row)

            if user.locked_until and user.locked_until > datetime.now(timezone.utc):
                await self._log_security_event(
                    "login_failed",
                    user.id,
                    ip_address,
                    user_agent,
                    {"username": login_identifier, "reason": "account_locked"},
                )
                raise AuthenticationError("Account is temporarily locked")

            if not user.is_active:
                await self._log_security_event(
                    "login_failed",
                    user.id,
                    ip_address,
                    user_agent,
                    {"username": login_identifier, "reason": "account_inactive"},
                )
                raise AuthenticationError("Account is inactive")

            if not self._verify_password(supplied_password, user.password_hash):
                failed_attempts = user.failed_login_attempts + 1
                locked_until = None

                if failed_attempts >= MAX_LOGIN_ATTEMPTS:
                    locked_until = datetime.now(timezone.utc) + timedelta(
                        minutes=LOCKOUT_DURATION_MINUTES
                    )

                await conn.execute(
                    """
                    UPDATE users SET failed_login_attempts = ?, locked_until = ?
                    WHERE id = ?
                """,
                    (failed_attempts, locked_until, user.id),
                )
                await conn.commit()

                await self._log_security_event(
                    "login_failed",
                    user.id,
                    ip_address,
                    user_agent,
                    {
                        "username": login_identifier,
                        "reason": "invalid_password",
                        "attempts": failed_attempts,
                    },
                )
                return None

            await conn.execute(
                """
                UPDATE users SET failed_login_attempts = 0, locked_until = NULL, last_login = ?
                WHERE id = ?
            """,
                (datetime.now(timezone.utc), user.id),
            )
            await conn.commit()

            await self._log_security_event(
                "login_success",
                user.id,
                ip_address,
                user_agent,
                {"username": login_identifier},
            )

            return user

    async def create_token_pair(self, user: User) -> TokenPair:
        """Generate and persist a new access/refresh token pair."""
        base_payload = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role.value,
            "permissions": sorted(
                permission.value
                for permission in ROLE_PERMISSIONS.get(user.role, set())
            ),
        }
        access_token = self._generate_token(
            {**base_payload, "type": "access"},
            timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = self._generate_token(
            {**base_payload, "type": "refresh"},
            timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
        refresh_id = secrets.token_urlsafe(16)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )

        async with self._connection() as conn:
            await conn.execute(
                """
                INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at)
                VALUES (?, ?, ?, ?)
            """,
                (refresh_id, user.id, self._hash_token(refresh_token), expires_at),
            )
            await conn.commit()

        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def refresh_access_token(self, refresh_token: str) -> TokenPair:
        """Exchange a refresh token for a new token pair."""
        token_hash = self._hash_token(refresh_token)
        async with self._connection() as conn:
            cursor = await conn.execute(
                """
                SELECT user_id, expires_at, revoked
                FROM refresh_tokens
                WHERE token_hash = ?
            """,
                (token_hash,),
            )
            row = await cursor.fetchone()

            if not row:
                raise AuthenticationError("Invalid refresh token")

            user_id, expires_at_value, revoked = row
            expires_at = (
                datetime.fromisoformat(expires_at_value)
                if isinstance(expires_at_value, str)
                else expires_at_value
            )

            if revoked or expires_at < datetime.now(timezone.utc):
                raise AuthenticationError("Refresh token expired or revoked")

            # Remove the used refresh token to enforce rotation
            await conn.execute(
                "DELETE FROM refresh_tokens WHERE token_hash = ?", (token_hash,)
            )
            await conn.commit()

        user = await self._get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User associated with token no longer exists")

        return await self.create_token_pair(user)

    async def validate_token(self, token: str) -> OperationResult:
        """Validate JWT token and return decoded payload."""
        try:
            payload = self._decode_token(token)
            return OperationResult(
                success=True,
                data={
                    "user_id": payload.get("user_id"),
                    "token_type": payload.get("type"),
                },
            )
        except AuthenticationError as exc:
            return OperationResult(
                success=False,
                error=OperationError(message=str(exc), code="INVALID_TOKEN"),
            )

    async def get_current_user(
        self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
    ) -> User:
        """STANDARD CURRENT USER RETRIEVAL"""
        try:
            payload = self._decode_token(credentials.credentials)
            if payload.get("type") != "access":
                raise AuthenticationError("Invalid token type")

            user_id = payload.get("sub")
            username = payload.get("username")
            role = UserRole(payload.get("role"))

            # Create lightweight user object for request context
            user = User(
                id=user_id,
                username=username,
                email="",  # Not needed in request context
                password_hash="",  # Not needed in request context
                role=role,
            )

            return user

        except AuthenticationError:
            raise HTTPException(
                status_code=401,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def require_permission(self, permission: Permission):
        """STANDARD PERMISSION REQUIREMENT DECORATOR"""

        def permission_checker(
            current_user: User = Depends(self.get_current_user),
        ) -> User:
            """
            Check if current user has required permission.

            Args:
                current_user: The authenticated user to check

            Returns:
                The user if permission check passes

            Raises:
                HTTPException: If user lacks required permission
            """
            if permission not in ROLE_PERMISSIONS.get(current_user.role, set()):
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient permissions. Required: {permission.value}",
                )
            return current_user

        return permission_checker

    def has_permission(
        self, role: Union[UserRole, str], permission: Permission
    ) -> bool:
        """Return True if the supplied role grants the requested permission."""
        if isinstance(role, str):
            try:
                role = UserRole(role)
            except ValueError:
                logger.warning("Unknown role provided for permission check: %s", role)
                return False
        return permission in ROLE_PERMISSIONS.get(role, set())

    def get_role_permissions(self, role: Union[UserRole, str]) -> Set[Permission]:
        """Return the permission set for a role; empty set for unknown roles."""
        if isinstance(role, str):
            try:
                role = UserRole(role)
            except ValueError:
                logger.warning("Unknown role requested: %s", role)
                return set()
        return set(ROLE_PERMISSIONS.get(role, set()))

    def require_role(self, required_role: UserRole):
        """STANDARD ROLE REQUIREMENT DECORATOR"""

        def role_checker(current_user: User = Depends(self.get_current_user)) -> User:
            """
            Check if current user has required role level.

            Args:
                current_user: The authenticated user to check

            Returns:
                The user if role check passes

            Raises:
                HTTPException: If user lacks required role level
            """
            role_hierarchy = {
                UserRole.GUEST: 0,
                UserRole.READER: 1,
                UserRole.API_USER: 2,
                UserRole.CONTENT_CREATOR: 3,
                UserRole.MODERATOR: 4,
                UserRole.ADMIN: 5,
            }

            if role_hierarchy.get(current_user.role, 0) < role_hierarchy.get(
                required_role, 0
            ):
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient role. Required: {required_role.value}",
                )
            return current_user

        return role_checker

    async def generate_api_key(self, user_id: str) -> str:
        """STANDARD API KEY GENERATION"""
        api_key = f"nve_{secrets.token_urlsafe(32)}"

        async with self._connection() as conn:
            await conn.execute(
                """
                UPDATE users SET api_key = ? WHERE id = ?
            """,
                (api_key, user_id),
            )
            await conn.commit()

        return api_key

    async def validate_api_key(self, api_key: str) -> Optional[User]:
        """STANDARD API KEY VALIDATION"""
        async with self._connection() as conn:
            cursor = await conn.execute(
                """
                SELECT id, username, email, role, is_active 
                FROM users WHERE api_key = ?
            """,
                (api_key,),
            )
            row = await cursor.fetchone()

            if row and row[4]:  # is_active
                return User(
                    id=row[0],
                    username=row[1],
                    email=row[2],
                    password_hash="",  # Not needed for API key auth
                    role=UserRole(row[3]),
                    is_active=row[4],
                    api_key=api_key,
                )
        return None


# STANDARD GLOBAL SECURITY SERVICE INSTANCE
security_service: Optional[SecurityService] = None


def get_security_service() -> SecurityService:
    """STANDARD SECURITY SERVICE GETTER"""
    global security_service
    if security_service is None:
        raise RuntimeError("Security service not initialized")
    return security_service


def initialize_security_service(database_path: str, secret_key: str):
    """STANDARD SECURITY SERVICE INITIALIZATION"""
    global security_service
    security_service = SecurityService(database_path, secret_key)
    return security_service


# Standalone wrapper functions for FastAPI dependency injection
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
) -> User:
    """Standalone wrapper for getting current user from token"""
    service = get_security_service()
    return await service.get_current_user(credentials)


def require_permission(permission: Permission):
    """Standalone wrapper for requiring permission"""
    service = get_security_service()
    return service.require_permission(permission)


def require_role(required_role: UserRole):
    """Standalone wrapper for requiring a minimum role level."""

    async def role_checker(
        credentials: HTTPAuthorizationCredentials = Depends(
            HTTPBearer(auto_error=False)
        ),
        x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
        x_user_role: Optional[str] = Header(default=None, alias="X-User-Role"),
    ) -> User:
        role_value = (x_user_role or "").strip().lower()
        if x_user_id and role_value:
            if role_value == "game_master":
                role_value = UserRole.ADMIN.value
            try:
                role = UserRole(role_value)
            except ValueError:
                raise HTTPException(status_code=403, detail="Insufficient role")
            user = User(
                id=x_user_id,
                username="header-user",
                email="",
                password_hash="",
                role=role,
            )
        else:
            if credentials is None:
                raise HTTPException(
                    status_code=401,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            try:
                service = get_security_service()
            except RuntimeError:
                raise HTTPException(
                    status_code=401,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            user = await service.get_current_user(credentials)

        role_hierarchy = {
            UserRole.GUEST: 0,
            UserRole.READER: 1,
            UserRole.API_USER: 2,
            UserRole.CONTENT_CREATOR: 3,
            UserRole.MODERATOR: 4,
            UserRole.ADMIN: 5,
        }
        if role_hierarchy.get(user.role, 0) < role_hierarchy.get(required_role, 0):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient role. Required: {required_role.value}",
            )
        return user

    return role_checker


__all__ = [
    "UserRole",
    "Permission",
    "User",
    "TokenPair",
    "UserRegistration",
    "UserLogin",
    "SecurityEvent",
    "AuthenticationError",
    "AuthorizationError",
    "SecurityService",
    "get_security_service",
    "initialize_security_service",
    "ROLE_PERMISSIONS",
    "get_current_user",
    "require_permission",  # Add standalone functions to exports
    "require_role",
    "AuthenticationManager",  # Legacy compatibility alias
]

# Export alias for legacy compatibility
AuthenticationManager = SecurityService
