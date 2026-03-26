"""Authentication service implementation.

This module provides the concrete implementation of authentication operations
including password hashing and JWT token management.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

import bcrypt

from src.contexts.identity.domain.repositories.user_repository import (
    AuthenticationService as AuthenticationServicePort,
)
from src.contexts.identity.domain.repositories.user_repository import (
    UserRepository,
)
from src.shared.application.result import Failure, Result, Success
from src.shared.infrastructure.auth.jwt_utils import JWTManager


class AuthenticationService(AuthenticationServicePort):
    """Concrete implementation of authentication service.

    This service handles password hashing, verification, and JWT token
    generation for the identity context.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        jwt_manager: JWTManager,
    ):
        """Initialize authentication service.

        Args:
            user_repository: Repository for user data access.
            jwt_manager: JWT manager for token operations.
        """
        self._user_repository = user_repository
        self._jwt_manager = jwt_manager

    async def hash_password(self, plain_password: str) -> str:
        """Hash a plain text password.

        Args:
            plain_password: Plain text password to hash.

        Returns:
            Hashed password string.
        """
        # bcrypt has a maximum password length of 72 bytes
        password_bytes = plain_password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")

    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain text password against a hash.

        Args:
            plain_password: Plain text password to verify.
            hashed_password: Hashed password to verify against.

        Returns:
            True if password matches, False otherwise.
        """
        password_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)

    async def generate_token(self, user_id: str, token_type: str = "access") -> str:
        """Generate an authentication token.

        Args:
            user_id: User ID as string.
            token_type: Type of token ("access" or "refresh").

        Returns:
            Encoded JWT token.

        Raises:
            ValueError: If user not found or invalid token type.
        """
        user = await self._user_repository.get_by_id(UUID(user_id))

        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        if token_type == "access":
            return self._jwt_manager.create_access_token(
                user_id=str(user.id),
                username=user.username,
                email=user.email,
                roles=user.roles,
            )
        elif token_type == "refresh":
            return self._jwt_manager.create_refresh_token(user_id=str(user.id))
        else:
            raise ValueError(f"Invalid token type: {token_type}")

    async def verify_token(self, token: str) -> Optional[str]:
        """Verify a token and return the user_id if valid.

        Args:
            token: JWT token string.

        Returns:
            User ID if token is valid, None otherwise.
        """
        try:
            payload = self._jwt_manager.verify_token(token)
            return payload.get("sub")
        except Exception:
            return None

    async def authenticate_user(self, username: str, password: str) -> Result[dict]:
        """Authenticate a user with username and password.

        Args:
            username: User's username.
            password: Plain text password.

        Returns:
            Result containing tokens on success, or Failure with error details.
        """
        # Try to find user by username
        user = await self._user_repository.get_by_username(username)

        if not user:
            return Failure(
                error="Invalid username or password",
                code="INVALID_CREDENTIALS",
            )

        # Check if account is locked
        if user.is_locked:
            return Failure(
                error="Account is temporarily locked due to too many failed attempts",
                code="ACCOUNT_LOCKED",
            )

        # Verify password
        if not await self.verify_password(password, user.hashed_password):
            # Record failed login
            user.record_login(success=False)
            await self._user_repository.save(user)

            return Failure(
                error="Invalid username or password",
                code="INVALID_CREDENTIALS",
            )

        # Record successful login
        user.record_login(success=True)
        await self._user_repository.save(user)

        # Generate tokens
        access_token = await self.generate_token(str(user.id), "access")
        refresh_token = await self.generate_token(str(user.id), "refresh")

        return Success(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "roles": user.roles,
                },
            }
        )

    async def refresh_access_token(self, refresh_token: str) -> Result[dict]:
        """Refresh access token using a refresh token.

        Args:
            refresh_token: Valid refresh token.

        Returns:
            Result containing new access token on success, or Failure.
        """
        try:
            payload = self._jwt_manager.verify_refresh_token(refresh_token)
            user_id = payload["sub"]

            user = await self._user_repository.get_by_id(UUID(user_id))

            if not user:
                return Failure(
                    error="User not found",
                    code="NOT_FOUND",
                )

            new_access_token = self._jwt_manager.create_access_token(
                user_id=str(user.id),
                username=user.username,
                email=user.email,
                roles=user.roles,
            )

            return Success(
                {
                    "access_token": new_access_token,
                    "token_type": "bearer",
                }
            )

        except Exception as e:
            return Failure(
                error=str(e),
                code="INVALID_TOKEN",
            )
