"""JWT token utilities for authentication.

This module provides JWT token management for the Novel Engine authentication system.
"""

from datetime import datetime, timedelta
from typing import Any, Optional, cast

import jwt
from jwt import PyJWTError


class AuthenticationError(Exception):
    """Base exception for authentication errors."""

    pass


class TokenExpiredError(AuthenticationError):
    """Exception raised when token has expired."""

    pass


class InvalidTokenError(AuthenticationError):
    """Exception raised when token is invalid."""

    pass


class JWTManager:
    """JWT token manager for authentication.

    This class handles the creation and verification of JWT tokens
    for user authentication in the Novel Engine system.

    Attributes:
        _secret_key: Secret key for signing tokens.
        _algorithm: JWT algorithm to use.
        _access_token_expire_minutes: Expiration time for access tokens.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        """Initialize JWT manager.

        Args:
            secret_key: Secret key for signing tokens. Must be at least 32 characters.
            algorithm: JWT algorithm to use. Defaults to "HS256".
            access_token_expire_minutes: Access token expiration in minutes.
            refresh_token_expire_days: Refresh token expiration in days.

        Raises:
            ValueError: If secret_key is too short.
        """
        if len(secret_key) < 32:
            raise ValueError("Secret key must be at least 32 characters long")

        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_token_expire_minutes = access_token_expire_minutes
        self._refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        user_id: str,
        username: str,
        email: str,
        roles: Optional[list[str]] = None,
        additional_claims: Optional[dict[str, Any]] = None,
    ) -> str:
        """Create an access token for a user.

        Args:
            user_id: User ID (UUID as string).
            username: User's username.
            email: User's email address.
            roles: Optional list of user roles.
            additional_claims: Optional additional claims to include.

        Returns:
            Encoded JWT access token.
        """
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self._access_token_expire_minutes)

        to_encode = {
            "sub": user_id,
            "username": username,
            "email": email,
            "iat": now,
            "exp": expire,
            "type": "access",
        }

        if roles:
            to_encode["roles"] = roles

        if additional_claims:
            to_encode.update(additional_claims)

        return jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(
        self,
        user_id: str,
        additional_claims: Optional[dict[str, Any]] = None,
    ) -> str:
        """Create a refresh token for a user.

        Args:
            user_id: User ID (UUID as string).
            additional_claims: Optional additional claims to include.

        Returns:
            Encoded JWT refresh token.
        """
        now = datetime.utcnow()
        expire = now + timedelta(days=self._refresh_token_expire_days)

        to_encode = {
            "sub": user_id,
            "iat": now,
            "exp": expire,
            "type": "refresh",
        }

        if additional_claims:
            to_encode.update(additional_claims)

        return jwt.encode(to_encode, self._secret_key, algorithm=self._algorithm)

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify and decode a JWT token.

        Args:
            token: JWT token string.

        Returns:
            Decoded token payload.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid.
        """
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                options={"verify_exp": True},
            )
            return payload
        except jwt.ExpiredSignatureError as e:
            raise TokenExpiredError("Token has expired") from e
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}") from e
        except PyJWTError as e:
            raise InvalidTokenError(f"Token verification failed: {str(e)}") from e

    def verify_access_token(self, token: str) -> dict[str, Any]:
        """Verify an access token.

        Args:
            token: Access token string.

        Returns:
            Decoded token payload.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid or not an access token.
        """
        payload = self.verify_token(token)

        if payload.get("type") != "access":
            raise InvalidTokenError("Token is not an access token")

        return payload

    def verify_refresh_token(self, token: str) -> dict[str, Any]:
        """Verify a refresh token.

        Args:
            token: Refresh token string.

        Returns:
            Decoded token payload.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid or not a refresh token.
        """
        payload = self.verify_token(token)

        if payload.get("type") != "refresh":
            raise InvalidTokenError("Token is not a refresh token")

        return payload

    def get_token_expiry(self, token: str) -> datetime:
        """Get token expiration time without full verification.

        Args:
            token: JWT token string.

        Returns:
            Token expiration datetime (UTC).

        Raises:
            InvalidTokenError: If the token cannot be decoded.
        """
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=[self._algorithm],
            )
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.utcfromtimestamp(exp_timestamp)
            raise InvalidTokenError("Token has no expiration")
        except jwt.PyJWTError as e:
            raise InvalidTokenError(f"Cannot decode token: {str(e)}") from e

    def refresh_access_token(
        self,
        refresh_token: str,
        username: str,
        email: str,
        roles: Optional[list[str]] = None,
    ) -> str:
        """Create a new access token from a refresh token.

        Args:
            refresh_token: Valid refresh token.
            username: User's username.
            email: User's email address.
            roles: Optional list of user roles.

        Returns:
            New access token.

        Raises:
            TokenExpiredError: If the refresh token has expired.
            InvalidTokenError: If the refresh token is invalid.
        """
        payload = self.verify_refresh_token(refresh_token)
        user_id = cast(str, payload["sub"])

        return self.create_access_token(
            user_id=user_id,
            username=username,
            email=email,
            roles=roles,
        )
