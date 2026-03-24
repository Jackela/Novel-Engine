"""Identity application layer exceptions.

These exceptions are used in the application layer and are caught
by the router layer to be converted into appropriate HTTPExceptions.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class IdentityError(Exception):
    """Base exception for identity context.

    All identity-related exceptions inherit from this class.
    """

    def __init__(
        self,
        message: str,
        code: str = "IDENTITY_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class IdentityValidationError(IdentityError):
    """Validation error for identity operations.

    Raised when input data validation fails.
    Corresponds to HTTP 400 Bad Request.
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="VALIDATION_ERROR", details=details)


class UserNotFoundError(IdentityError):
    """User not found error.

    Raised when the requested user does not exist.
    Corresponds to HTTP 404 Not Found.
    """

    def __init__(self, user_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"User with ID '{user_id}' not found",
            code="NOT_FOUND",
            details=details or {"user_id": user_id},
        )
        self.user_id = user_id


class UserAlreadyExistsError(IdentityError):
    """User already exists error.

    Raised when attempting to create a user that already exists.
    Corresponds to HTTP 409 Conflict.
    """

    def __init__(
        self,
        message: str = "User already exists",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="CONFLICT", details=details)


class AuthenticationError(IdentityError):
    """Authentication failed error.

    Raised when authentication fails for any reason.
    Corresponds to HTTP 401 Unauthorized.
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="AUTHENTICATION_ERROR", details=details)


class InvalidCredentialsError(IdentityError):
    """Invalid credentials error.

    Raised when username or password is incorrect.
    Corresponds to HTTP 401 Unauthorized.
    """

    def __init__(
        self,
        message: str = "Invalid username or password",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="INVALID_CREDENTIALS", details=details)


class TokenExpiredError(IdentityError):
    """Token has expired error.

    Raised when a token has expired.
    Corresponds to HTTP 401 Unauthorized.
    """

    def __init__(
        self,
        message: str = "Token has expired",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="TOKEN_EXPIRED", details=details)


class InvalidTokenError(IdentityError):
    """Invalid token error.

    Raised when a token is invalid or malformed.
    Corresponds to HTTP 401 Unauthorized.
    """

    def __init__(
        self,
        message: str = "Invalid token",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="INVALID_TOKEN", details=details)


class AccountLockedError(IdentityError):
    """Account locked error.

    Raised when a user account is temporarily locked.
    Corresponds to HTTP 403 Forbidden.
    """

    def __init__(
        self,
        message: str = "Account is temporarily locked due to too many failed attempts",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="ACCOUNT_LOCKED", details=details)


class IdentityUnauthorizedError(IdentityError):
    """Unauthorized error.

    Raised when user is not authorized to perform an action.
    Corresponds to HTTP 401 Unauthorized.
    """

    def __init__(
        self,
        message: str = "Unauthorized to perform this action",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="UNAUTHORIZED", details=details)


class IdentityForbiddenError(IdentityError):
    """Forbidden error.

    Raised when user is forbidden from accessing a resource.
    Corresponds to HTTP 403 Forbidden.
    """

    def __init__(
        self,
        message: str = "Access to this resource is forbidden",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="FORBIDDEN", details=details)


class IdentityInternalError(IdentityError):
    """Internal error.

    Raised when an unexpected internal error occurs.
    Corresponds to HTTP 500 Internal Server Error.
    """

    def __init__(
        self,
        message: str = "An internal error occurred",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="INTERNAL_ERROR", details=details)


class PasswordTooWeakError(IdentityError):
    """Password too weak error.

    Raised when password does not meet strength requirements.
    Corresponds to HTTP 400 Bad Request.
    """

    def __init__(
        self,
        message: str = "Password is too weak",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message=message, code="PASSWORD_TOO_WEAK", details=details)
