"""Identity Application Service

Application service for identity and authentication operations.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.shared.application.result import Failure, Result, Success
from src.contexts.identity.domain.aggregates.user import User
from src.contexts.identity.domain.repositories.user_repository import (
    UserRepository,
    AuthenticationService,
)


class IdentityApplicationService:
    """
    Application service for identity management.

    Handles user registration, authentication, and account management.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        auth_service: AuthenticationService,
    ):
        self.user_repo = user_repo
        self.auth_service = auth_service

    async def register_user(
        self,
        email: str,
        username: str,
        password: str,
    ) -> Result[User]:
        """
        Register a new user.

        Args:
            email: User email address
            username: Unique username
            password: Plain text password (will be hashed)

        Returns:
            Result containing the created user or error
        """
        try:
            # Check if email already exists
            if await self.user_repo.exists_by_email(email):
                return Failure("Email already registered", "CONFLICT")

            # Check if username already exists
            if await self.user_repo.exists_by_username(username):
                return Failure("Username already taken", "CONFLICT")

            # Hash password
            hashed_password = await self.auth_service.hash_password(password)

            # Create user
            user = User(
                email=email,
                username=username,
                hashed_password=hashed_password,
            )

            await self.user_repo.save(user)

            return Success(user)

        except ValueError as e:
            return Failure(str(e), "VALIDATION_ERROR")
        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def authenticate_user(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Result[Dict[str, Any]]:
        """
        Authenticate a user with email and password.

        Args:
            email: User email
            password: Plain text password
            ip_address: Optional client IP
            user_agent: Optional client user agent

        Returns:
            Result containing user data and tokens or error
        """
        try:
            # Find user by email
            user = await self.user_repo.get_by_email(email)

            if not user:
                return Failure("Invalid credentials", "INVALID_CREDENTIALS")

            # Check if account is locked
            if user.is_locked:
                return Failure("Account is temporarily locked", "ACCOUNT_LOCKED")

            # Verify password
            password_valid = await self.auth_service.verify_password(
                password, user.hashed_password
            )

            if not password_valid:
                user.record_login(success=False)
                await self.user_repo.save(user)
                return Failure("Invalid credentials", "INVALID_CREDENTIALS")

            # Record successful login
            user.record_login(success=True)
            await self.user_repo.save(user)

            # Generate tokens
            access_token = await self.auth_service.generate_token(
                str(user.id), "access"
            )
            refresh_token = await self.auth_service.generate_token(
                str(user.id), "refresh"
            )

            return Success(
                {
                    "user": user.to_dict(),
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
            )

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def get_user(self, user_id: str) -> Result[User]:
        """Get a user by ID."""
        try:
            from uuid import UUID

            user = await self.user_repo.get_by_id(UUID(user_id))

            if not user:
                return Failure("User not found", "NOT_FOUND")

            return Success(user)

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> Result[User]:
        """
        Change a user's password.

        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password

        Returns:
            Result containing updated user or error
        """
        try:
            from uuid import UUID

            user = await self.user_repo.get_by_id(UUID(user_id))

            if not user:
                return Failure("User not found", "NOT_FOUND")

            # Verify old password
            if not await self.auth_service.verify_password(
                old_password, user.hashed_password
            ):
                return Failure("Current password is incorrect", "INVALID_CREDENTIALS")

            # Hash and set new password
            new_hashed = await self.auth_service.hash_password(new_password)
            user.change_password(new_hashed)

            await self.user_repo.save(user)

            return Success(user)

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def assign_role(self, user_id: str, role: str) -> Result[User]:
        """Assign a role to a user."""
        try:
            from uuid import UUID

            user = await self.user_repo.get_by_id(UUID(user_id))

            if not user:
                return Failure("User not found", "NOT_FOUND")

            user.add_role(role)
            await self.user_repo.save(user)

            return Success(user)

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")

    async def verify_email(self, user_id: str) -> Result[User]:
        """Mark a user's email as verified."""
        try:
            from uuid import UUID

            user = await self.user_repo.get_by_id(UUID(user_id))

            if not user:
                return Failure("User not found", "NOT_FOUND")

            user.verify_email()
            await self.user_repo.save(user)

            return Success(user)

        except Exception as e:
            return Failure(str(e), "INTERNAL_ERROR")
