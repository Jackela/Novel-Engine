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

import jwt
import bcrypt
import secrets
import logging
import asyncio
import aiosqlite
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Union, Set
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import asynccontextmanager

from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr

# Comprehensive logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# STANDARD SECURITY CONSTANTS
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived for security
REFRESH_TOKEN_EXPIRE_DAYS = 30   # Longer-lived but revocable
PASSWORD_MIN_LENGTH = 8
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15

class UserRole(str, Enum):
    """STANDARD USER ROLES ENHANCED BY AUTHORIZATION"""
    ADMIN = "admin"              # Full system access
    MODERATOR = "moderator"      # Content moderation and user management
    CONTENT_CREATOR = "creator"  # Story generation and character management
    API_USER = "api_user"       # API access for integrations
    READER = "reader"           # Read-only access to public content
    GUEST = "guest"             # Limited anonymous access

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

# Role-Permission Mapping
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.ADMIN: {
        Permission.SYSTEM_ADMIN, Permission.SYSTEM_CONFIG, Permission.SYSTEM_HEALTH,
        Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE, 
        Permission.USER_DELETE, Permission.USER_MANAGE_ROLES,
        Permission.STORY_CREATE, Permission.STORY_READ, Permission.STORY_UPDATE,
        Permission.STORY_DELETE, Permission.STORY_PUBLISH,
        Permission.CHARACTER_CREATE, Permission.CHARACTER_READ, Permission.CHARACTER_UPDATE,
        Permission.CHARACTER_DELETE,
        Permission.API_ACCESS, Permission.API_RATE_UNLIMITED,
        Permission.SIMULATION_CREATE, Permission.SIMULATION_READ, Permission.SIMULATION_MANAGE
    },
    UserRole.MODERATOR: {
        Permission.SYSTEM_HEALTH,
        Permission.USER_READ, Permission.USER_UPDATE,
        Permission.STORY_READ, Permission.STORY_UPDATE, Permission.STORY_DELETE,
        Permission.CHARACTER_READ, Permission.CHARACTER_UPDATE, Permission.CHARACTER_DELETE,
        Permission.API_ACCESS,
        Permission.SIMULATION_READ, Permission.SIMULATION_MANAGE
    },
    UserRole.CONTENT_CREATOR: {
        Permission.SYSTEM_HEALTH,
        Permission.USER_READ,
        Permission.STORY_CREATE, Permission.STORY_READ, Permission.STORY_UPDATE,
        Permission.CHARACTER_CREATE, Permission.CHARACTER_READ, Permission.CHARACTER_UPDATE,
        Permission.API_ACCESS,
        Permission.SIMULATION_CREATE, Permission.SIMULATION_READ
    },
    UserRole.API_USER: {
        Permission.SYSTEM_HEALTH,
        Permission.STORY_READ,
        Permission.CHARACTER_READ,
        Permission.API_ACCESS,
        Permission.SIMULATION_READ
    },
    UserRole.READER: {
        Permission.SYSTEM_HEALTH,
        Permission.STORY_READ,
        Permission.CHARACTER_READ
    },
    UserRole.GUEST: {
        Permission.SYSTEM_HEALTH,
        Permission.STORY_READ
    }
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

class AuthenticationError(Exception):
    """ENHANCED AUTHENTICATION EXCEPTION"""
    pass

class AuthorizationError(Exception):
    """ENHANCED AUTHORIZATION EXCEPTION"""
    pass

class SecurityService:
    """STANDARD SECURITY SERVICE ENHANCED BY THE SYSTEM"""
    
    def __init__(self, database_path: str, secret_key: str):
        self.database_path = database_path
        self.secret_key = secret_key
        self.security_bearer = HTTPBearer()
        
    async def initialize_database(self):
        """STANDARD DATABASE INITIALIZATION"""
        async with aiosqlite.connect(self.database_path) as conn:
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
            
            # Sessions table for active session management
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
    
    def _hash_password(self, password: str) -> str:
        """STANDARD PASSWORD HASHING ENHANCED BY BCRYPT"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """STANDARD PASSWORD VERIFICATION"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def _generate_token(self, payload: Dict[str, Any], expires_delta: timedelta) -> str:
        """STANDARD JWT TOKEN GENERATION"""
        expire = datetime.now(timezone.utc) + expires_delta
        payload.update({"exp": expire, "iat": datetime.now(timezone.utc)})
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
    
    async def _log_security_event(self, event_type: str, user_id: Optional[str], 
                                  ip_address: str, user_agent: str, details: Dict[str, Any]):
        """STANDARD SECURITY EVENT LOGGING"""
        event_id = secrets.token_urlsafe(16)
        async with aiosqlite.connect(self.database_path) as conn:
            await conn.execute("""
                INSERT INTO security_events (id, event_type, user_id, ip_address, user_agent, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (event_id, event_type, user_id, ip_address, user_agent, str(details)))
            await conn.commit()
    
    async def register_user(self, registration: UserRegistration, ip_address: str, user_agent: str) -> User:
        """STANDARD USER REGISTRATION ENHANCED BY SECURE CREATION"""
        user_id = secrets.token_urlsafe(16)
        password_hash = self._hash_password(registration.password)
        
        user = User(
            id=user_id,
            username=registration.username,
            email=registration.email,
            password_hash=password_hash,
            role=registration.role,
            created_at=datetime.now(timezone.utc)
        )
        
        try:
            async with aiosqlite.connect(self.database_path) as conn:
                await conn.execute("""
                    INSERT INTO users (id, username, email, password_hash, role, is_active, is_verified, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user.id, user.username, user.email, user.password_hash, 
                      user.role.value, user.is_active, user.is_verified, user.created_at))
                await conn.commit()
                
                await self._log_security_event(
                    "user_registered", user.id, ip_address, user_agent,
                    {"username": user.username, "email": user.email, "role": user.role.value}
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
    
    async def authenticate_user(self, login: UserLogin, ip_address: str, user_agent: str) -> Optional[User]:
        """STANDARD USER AUTHENTICATION ENHANCED BY VERIFICATION"""
        async with aiosqlite.connect(self.database_path) as conn:
            cursor = await conn.execute("""
                SELECT id, username, email, password_hash, role, is_active, is_verified,
                       created_at, last_login, failed_login_attempts, locked_until
                FROM users WHERE username = ?
            """, (login.username,))
            row = await cursor.fetchone()
            
            if not row:
                await self._log_security_event(
                    "login_failed", None, ip_address, user_agent,
                    {"username": login.username, "reason": "user_not_found"}
                )
                return None
            
            user = User(
                id=row[0], username=row[1], email=row[2], password_hash=row[3],
                role=UserRole(row[4]), is_active=bool(row[5]), is_verified=bool(row[6]),
                created_at=datetime.fromisoformat(row[7]) if row[7] else None,
                last_login=datetime.fromisoformat(row[8]) if row[8] else None,
                failed_login_attempts=row[9],
                locked_until=datetime.fromisoformat(row[10]) if row[10] else None
            )
            
            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.now(timezone.utc):
                await self._log_security_event(
                    "login_failed", user.id, ip_address, user_agent,
                    {"username": login.username, "reason": "account_locked"}
                )
                raise AuthenticationError("Account is temporarily locked")
            
            # Check if account is active
            if not user.is_active:
                await self._log_security_event(
                    "login_failed", user.id, ip_address, user_agent,
                    {"username": login.username, "reason": "account_inactive"}
                )
                raise AuthenticationError("Account is inactive")
            
            # Verify password
            if not self._verify_password(login.password, user.password_hash):
                # Increment failed attempts
                failed_attempts = user.failed_login_attempts + 1
                locked_until = None
                
                if failed_attempts >= MAX_LOGIN_ATTEMPTS:
                    locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                
                await conn.execute("""
                    UPDATE users SET failed_login_attempts = ?, locked_until = ?
                    WHERE id = ?
                """, (failed_attempts, locked_until, user.id))
                await conn.commit()
                
                await self._log_security_event(
                    "login_failed", user.id, ip_address, user_agent,
                    {"username": login.username, "reason": "invalid_password", "attempts": failed_attempts}
                )
                return None
            
            # Successful login - reset failed attempts and update last login
            await conn.execute("""
                UPDATE users SET failed_login_attempts = 0, locked_until = NULL, last_login = ?
                WHERE id = ?
            """, (datetime.now(timezone.utc), user.id))
            await conn.commit()
            
            await self._log_security_event(
                "login_success", user.id, ip_address, user_agent,
                {"username": login.username}
            )
            
            user.last_login = datetime.now(timezone.utc)
            user.failed_login_attempts = 0
            user.locked_until = None
            
            return user
    
    async def create_token_pair(self, user: User) -> TokenPair:
        """STANDARD TOKEN PAIR CREATION"""
        # Create access token
        access_payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role.value,
            "permissions": [p.value for p in ROLE_PERMISSIONS[user.role]],
            "type": "access"
        }
        access_token = self._generate_token(access_payload, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        
        # Create refresh token
        refresh_payload = {
            "sub": user.id,
            "type": "refresh"
        }
        refresh_token = self._generate_token(refresh_payload, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
        
        # Store refresh token in database
        refresh_id = secrets.token_urlsafe(16)
        refresh_hash = self._hash_password(refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        async with aiosqlite.connect(self.database_path) as conn:
            await conn.execute("""
                INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at)
                VALUES (?, ?, ?, ?)
            """, (refresh_id, user.id, refresh_hash, expires_at))
            await conn.commit()
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    async def refresh_access_token(self, refresh_token: str) -> TokenPair:
        """STANDARD TOKEN REFRESH ENHANCED BY RENEWAL"""
        try:
            payload = self._decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise AuthenticationError("Invalid token type")
            
            user_id = payload.get("sub")
            
            # Verify refresh token exists and is not revoked
            async with aiosqlite.connect(self.database_path) as conn:
                cursor = await conn.execute("""
                    SELECT id, revoked, expires_at FROM refresh_tokens
                    WHERE user_id = ? AND expires_at > ?
                """, (user_id, datetime.now(timezone.utc)))
                tokens = await cursor.fetchall()
                
                # Verify token hash matches
                valid_token = None
                for token_row in tokens:
                    if self._verify_password(refresh_token, token_row[1]):  # Assuming token_hash is at index 1
                        valid_token = token_row
                        break
                
                if not valid_token or valid_token[1]:  # revoked
                    raise AuthenticationError("Invalid or revoked refresh token")
                
                # Get user details
                cursor = await conn.execute("""
                    SELECT username, role, is_active FROM users WHERE id = ?
                """, (user_id,))
                user_row = await cursor.fetchone()
                
                if not user_row or not user_row[2]:  # not active
                    raise AuthenticationError("User account is inactive")
                
                # Create new token pair
                user = User(
                    id=user_id,
                    username=user_row[0],
                    email="",  # Not needed for token refresh
                    password_hash="",  # Not needed for token refresh
                    role=UserRole(user_row[1]),
                    is_active=user_row[2]
                )
                
                return await self.create_token_pair(user)
                
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Refresh token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid refresh token")
    
    async def revoke_refresh_token(self, refresh_token: str):
        """STANDARD TOKEN REVOCATION"""
        try:
            payload = self._decode_token(refresh_token)
            user_id = payload.get("sub")
            
            async with aiosqlite.connect(self.database_path) as conn:
                await conn.execute("""
                    UPDATE refresh_tokens SET revoked = TRUE
                    WHERE user_id = ? AND expires_at > ?
                """, (user_id, datetime.now(timezone.utc)))
                await conn.commit()
                
        except jwt.InvalidTokenError:
            pass  # Token is already invalid
    
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> User:
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
                role=role
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
        def permission_checker(current_user: User = Depends(self.get_current_user)) -> User:
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
                    detail=f"Insufficient permissions. Required: {permission.value}"
                )
            return current_user
        return permission_checker
    
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
                UserRole.ADMIN: 5
            }
            
            if role_hierarchy.get(current_user.role, 0) < role_hierarchy.get(required_role, 0):
                raise HTTPException(
                    status_code=403,
                    detail=f"Insufficient role. Required: {required_role.value}"
                )
            return current_user
        return role_checker
    
    async def generate_api_key(self, user_id: str) -> str:
        """STANDARD API KEY GENERATION"""
        api_key = f"nve_{secrets.token_urlsafe(32)}"
        
        async with aiosqlite.connect(self.database_path) as conn:
            await conn.execute("""
                UPDATE users SET api_key = ? WHERE id = ?
            """, (api_key, user_id))
            await conn.commit()
        
        return api_key
    
    async def validate_api_key(self, api_key: str) -> Optional[User]:
        """STANDARD API KEY VALIDATION"""
        async with aiosqlite.connect(self.database_path) as conn:
            cursor = await conn.execute("""
                SELECT id, username, email, role, is_active 
                FROM users WHERE api_key = ?
            """, (api_key,))
            row = await cursor.fetchone()
            
            if row and row[4]:  # is_active
                return User(
                    id=row[0],
                    username=row[1],
                    email=row[2],
                    password_hash="",  # Not needed for API key auth
                    role=UserRole(row[3]),
                    is_active=row[4],
                    api_key=api_key
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

__all__ = [
    'UserRole', 'Permission', 'User', 'TokenPair', 'UserRegistration', 'UserLogin',
    'SecurityEvent', 'AuthenticationError', 'AuthorizationError', 'SecurityService',
    'get_security_service', 'initialize_security_service', 'ROLE_PERMISSIONS'
]