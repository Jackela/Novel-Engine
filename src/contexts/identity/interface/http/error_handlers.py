"""HTTP Error Handlers for Identity Context

Provides conversion from Result errors to HTTPException, and error handling decorators.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable, Coroutine, Dict, Optional, TypeVar

from fastapi import HTTPException, status

from src.contexts.identity.application.exceptions import (
    AccountLockedError,
    AuthenticationError,
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
from src.shared.application.result import Result

# Configure logging
logger = logging.getLogger(__name__)

# Error code to HTTP status code mapping
ERROR_CODE_TO_HTTP_STATUS: Dict[str, int] = {
    # Client errors (4xx)
    "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
    "BAD_REQUEST": status.HTTP_400_BAD_REQUEST,
    "PASSWORD_TOO_WEAK": status.HTTP_400_BAD_REQUEST,
    "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,
    "AUTHENTICATION_ERROR": status.HTTP_401_UNAUTHORIZED,
    "INVALID_CREDENTIALS": status.HTTP_401_UNAUTHORIZED,
    "TOKEN_EXPIRED": status.HTTP_401_UNAUTHORIZED,
    "INVALID_TOKEN": status.HTTP_401_UNAUTHORIZED,
    "FORBIDDEN": status.HTTP_403_FORBIDDEN,
    "ACCOUNT_LOCKED": status.HTTP_403_FORBIDDEN,
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "CONFLICT": status.HTTP_409_CONFLICT,
    "UNPROCESSABLE_ENTITY": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "TOO_MANY_REQUESTS": status.HTTP_429_TOO_MANY_REQUESTS,
    # Server errors (5xx)
    "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "NOT_IMPLEMENTED": status.HTTP_501_NOT_IMPLEMENTED,
    "SERVICE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
    # Default
    "IDENTITY_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
}

# Error code to default message mapping
ERROR_CODE_TO_MESSAGE: Dict[str, str] = {
    "VALIDATION_ERROR": "Validation failed",
    "BAD_REQUEST": "Bad request",
    "PASSWORD_TOO_WEAK": "Password is too weak",
    "UNAUTHORIZED": "Unauthorized",
    "AUTHENTICATION_ERROR": "Authentication failed",
    "INVALID_CREDENTIALS": "Invalid username or password",
    "TOKEN_EXPIRED": "Token has expired",
    "INVALID_TOKEN": "Invalid token",
    "FORBIDDEN": "Forbidden",
    "ACCOUNT_LOCKED": "Account is locked",
    "NOT_FOUND": "Resource not found",
    "CONFLICT": "Conflict occurred",
    "UNPROCESSABLE_ENTITY": "Unprocessable entity",
    "TOO_MANY_REQUESTS": "Too many requests",
    "INTERNAL_ERROR": "Internal server error",
    "NOT_IMPLEMENTED": "Not implemented",
    "SERVICE_UNAVAILABLE": "Service unavailable",
    "IDENTITY_ERROR": "An error occurred",
}

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])


class ResultErrorHandler:
    """Result error handler.

    Converts Result-type errors to HTTPException.

    Usage:
        result = await service.authenticate_user(...)
        ResultErrorHandler.handle(result)  # Automatically converts error
        return result.value
    """

    @classmethod
    def handle(cls, result: Result[Any], operation: Optional[str] = None) -> None:
        """Handle Result error.

        If result contains an error, raises appropriate HTTPException.

        Args:
            result: Result object to handle
            operation: Operation name (for logging)

        Raises:
            HTTPException: When result contains error
        """
        if not result.is_error:
            return

        # result is Failure type
        failure = result  # type: ignore
        error_code = failure.code
        error_message = failure.error
        error_details = failure.details if hasattr(failure, "details") else None

        # Get HTTP status code
        status_code = ERROR_CODE_TO_HTTP_STATUS.get(
            error_code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        # Get default message (if error message is empty)
        detail = error_message or ERROR_CODE_TO_MESSAGE.get(
            error_code, "An error occurred"
        )

        # Log
        operation_str = f" in {operation}" if operation else ""
        if status_code >= 500:
            logger.error(
                f"Server error{operation_str}: [{error_code}] {detail}",
                extra={"error_code": error_code, "details": error_details},
            )
        elif status_code >= 400:
            logger.warning(
                f"Client error{operation_str}: [{error_code}] {detail}",
                extra={"error_code": error_code, "details": error_details},
            )

        # Raise HTTPException
        raise HTTPException(
            status_code=status_code,
            detail=detail,
            headers={"X-Error-Code": error_code} if error_details else None,
        )

    @classmethod
    def handle_or_return(cls, result: Result[T], operation: Optional[str] = None) -> T:
        """Handle Result error or return value.

        If result contains error, raises HTTPException.
        Otherwise returns value from result.

        Args:
            result: Result object to handle
            operation: Operation name (for logging)

        Returns:
            Value from Result

        Raises:
            HTTPException: When result contains error
        """
        cls.handle(result, operation)
        # At this point result must be Success
        return result.value  # type: ignore


class ErrorConverter:
    """Error converter.

    Converts IdentityError exceptions to HTTPException.
    """

    @staticmethod
    def convert(error: IdentityError) -> HTTPException:
        """Convert IdentityError to HTTPException.

        Args:
            error: IdentityError exception

        Returns:
            Corresponding HTTPException
        """
        status_code = ERROR_CODE_TO_HTTP_STATUS.get(
            error.code, status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        # Log
        if status_code >= 500:
            logger.error(
                f"Server error: [{error.code}] {error.message}",
                extra={"error_code": error.code, "details": error.details},
                exc_info=True,
            )
        else:
            logger.warning(
                f"Client error: [{error.code}] {error.message}",
                extra={"error_code": error.code, "details": error.details},
            )

        return HTTPException(
            status_code=status_code,
            detail=error.message,
            headers={"X-Error-Code": error.code} if error.details else None,
        )


def handle_identity_errors(func: F) -> F:
    """Identity error handling decorator.

    Automatically catches IdentityError exceptions and converts to HTTPException.
    Recommended for Router endpoint functions.

    Usage:
        @router.post("/")
        @handle_identity_errors
        async def login(...):
            result = await service.authenticate_user(...)
            ResultErrorHandler.handle(result)
            return result.value
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except IdentityValidationError as e:
            logger.warning(f"Validation error: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
            ) from e
        except UserNotFoundError as e:
            logger.warning(
                f"Not found: {e.message}",
                extra={"code": e.code, "user_id": getattr(e, "user_id", None)},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=e.message
            ) from e
        except UserAlreadyExistsError as e:
            logger.warning(f"Conflict: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=e.message
            ) from e
        except InvalidCredentialsError as e:
            logger.warning(f"Invalid credentials: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=e.message,
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
        except TokenExpiredError as e:
            logger.warning(f"Token expired: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=e.message,
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
        except InvalidTokenError as e:
            logger.warning(f"Invalid token: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=e.message,
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
        except AccountLockedError as e:
            logger.warning(f"Account locked: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=e.message
            ) from e
        except IdentityUnauthorizedError as e:
            logger.warning(f"Unauthorized: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=e.message,
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
        except IdentityForbiddenError as e:
            logger.warning(f"Forbidden: {e.message}", extra={"code": e.code})
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=e.message
            ) from e
        except IdentityInternalError as e:
            logger.error(
                f"Internal error: {e.message}", extra={"code": e.code}, exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred",
            ) from e
        except IdentityError as e:
            # Other IdentityError
            logger.error(
                f"Identity error: {e.message}", extra={"code": e.code}, exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message
            ) from e

    return wrapper  # type: ignore


def handle_result_error(operation: Optional[str] = None) -> Callable[[F], F]:
    """Result error handling decorator (with operation name).

    Automatically handles Result-type errors, converting to HTTPException.

    Usage:
        @router.post("/")
        @handle_result_error("authenticate_user")
        async def login(...):
            result = await service.authenticate_user(...)
            return ResultErrorHandler.handle_or_return(result, "authenticate_user")
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # If already HTTPException, re-raise directly
                raise
            except Exception as e:
                # Catch other exceptions
                op_str = f" in {operation}" if operation else ""
                logger.exception(f"Unexpected error{op_str}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An unexpected error occurred",
                ) from e

        return wrapper  # type: ignore

    return decorator
