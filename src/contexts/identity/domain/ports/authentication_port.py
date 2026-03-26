"""Authentication port (interface).

This module defines the abstract interface for authentication operations,
following the Ports and Adapters pattern (Hexagonal Architecture).

The domain layer depends on this port, while infrastructure provides
concrete implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AuthToken:
    """Value object representing authentication tokens.

    Attributes:
        access_token: The JWT access token.
        refresh_token: The JWT refresh token.
        token_type: The type of token (e.g., "bearer").
        expires_in: Access token expiration time in seconds.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int | None = None

    def to_dict(self) -> dict[str, str | int | None]:
        """Convert token to dictionary."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
        }


class AuthenticationPort(Protocol):
    """Port interface for authentication operations.

    This protocol defines the contract for authentication-related operations.
    It abstracts away the underlying authentication mechanism from the domain layer.

    Implementations:
        - JWTAuthenticationService: Uses JWT tokens for authentication
    """

    async def authenticate(self, username: str, password: str) -> AuthToken:
        """Authenticate a user with username and password.

        Args:
            username: The user's username or email.
            password: The user's plain text password.

        Returns:
            AuthToken containing access and refresh tokens.

        Raises:
            AuthenticationError: If authentication fails.
            InvalidCredentialsError: If credentials are invalid.
            UserNotFoundError: If user is not found.
        """
        ...

    async def verify_token(self, token: str) -> dict:
        """Verify a token and return its payload.

        Args:
            token: The JWT token to verify.

        Returns:
            Decoded token payload as dictionary.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid.
        """
        ...

    async def refresh_token(self, refresh_token: str) -> AuthToken:
        """Refresh access token using a refresh token.

        Args:
            refresh_token: The valid refresh token.

        Returns:
            New AuthToken with fresh access token.

        Raises:
            TokenExpiredError: If the refresh token has expired.
            InvalidTokenError: If the refresh token is invalid.
            UserNotFoundError: If user associated with token is not found.
        """
        ...

    async def logout(self, token: str) -> None:
        """Logout a user (invalidate token).

        Note: In JWT-based authentication, this is typically client-side only.
        Token blacklisting would require additional infrastructure.

        Args:
            token: The token to invalidate.

        Raises:
            InvalidTokenError: If the token is invalid.
        """
        ...

    async def hash_password(self, plain_password: str) -> str:
        """Hash a plain text password.

        Args:
            plain_password: Plain text password to hash.

        Returns:
            Hashed password string.
        """
        ...

    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain text password against a hash.

        Args:
            plain_password: Plain text password to verify.
            hashed_password: Hashed password to verify against.

        Returns:
            True if password matches, False otherwise.
        """
        ...
