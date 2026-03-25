"""HTTP Error Handlers for Identity Context.

Extends shared error handlers with identity-specific exception mappings.
"""

from functools import wraps
from typing import Any, Callable, TypeVar

from fastapi import HTTPException, status

from src.contexts.identity.application.exceptions import (
    AccountLockedError,
    IdentityError,
    IdentityForbiddenError,
    IdentityInternalError,
    IdentityUnauthorizedError,
    IdentityValidationError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from src.shared.interface.http.error_handlers import (
    BaseErrorConverter,
)
from src.shared.interface.http.error_handlers import (
    ResultErrorHandler as BaseResultErrorHandler,
)
from src.shared.interface.http.error_handlers import (
    handle_result_error as base_handle_result_error,
)

F = TypeVar("F", bound=Callable[..., Any])


class ResultErrorHandler(BaseResultErrorHandler):
    """Identity-specific result error handler."""

    pass


class ErrorConverter(BaseErrorConverter):
    """Convert IdentityError exceptions to HTTPException."""

    @staticmethod
    def convert(error: Exception) -> HTTPException:
        """Convert IdentityError to HTTPException."""
        if isinstance(error, UserNotFoundError):
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        elif isinstance(error, UserAlreadyExistsError):
            return HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User already exists"
            )
        elif isinstance(error, InvalidCredentialsError):
            return HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif isinstance(error, (TokenExpiredError, InvalidTokenError)):
            return HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif isinstance(error, AccountLockedError):
            return HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account is locked"
            )
        elif isinstance(error, (IdentityUnauthorizedError, IdentityForbiddenError)):
            return HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )
        elif isinstance(error, IdentityValidationError):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
            )
        elif isinstance(error, IdentityInternalError):
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )
        elif isinstance(error, IdentityError):
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)
            )

        return BaseErrorConverter.convert(error)


def handle_identity_errors(func: F) -> F:
    """Identity error handling decorator."""

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except IdentityError as e:
            raise ErrorConverter.convert(e) from e
        except Exception:
            raise

    return wrapper  # type: ignore


def handle_result_error(operation: str | None = None) -> Callable[[F], F]:
    """Result error handling decorator with operation name."""
    return base_handle_result_error(operation)
