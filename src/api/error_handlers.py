#!/usr/bin/env python3
"""
Centralized Error Handling System.

Provides consistent error handling, logging, and response formatting
across all API endpoints with proper HTTP status codes and error classification.
"""

import logging
import time
import traceback
from datetime import datetime
from typing import List, Optional, Union

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .response_envelopes import (
    APIError,
    APIErrorType,
    APIMetadata,
    ErrorResponse,
    ResponseStatus,
    ValidationError,
)

logger = logging.getLogger(__name__)


class NovelEngineException(Exception):
    """Base exception for Novel Engine API."""

    def __init__(
        self,
        message: str,
        error_type: APIErrorType = APIErrorType.INTERNAL_ERROR,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Optional[str] = None,
        code: Optional[str] = None,
    ):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(message)


class ValidationException(NovelEngineException):
    """Validation error exception."""

    def __init__(
        self, message: str, field: Optional[str] = None, detail: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_type=APIErrorType.VALIDATION_ERROR,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
        )
        self.field = field


class ResourceNotFoundException(NovelEngineException):
    """Resource not found exception."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} '{resource_id}' not found",
            error_type=APIErrorType.NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The requested {resource_type.lower()} does not exist",
        )


class ServiceUnavailableException(NovelEngineException):
    """Service unavailable exception."""

    def __init__(self, service_name: str, detail: Optional[str] = None):
        super().__init__(
            message=f"{service_name} service is currently unavailable",
            error_type=APIErrorType.SERVICE_UNAVAILABLE,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail or "Please try again later",
        )


class ConflictException(NovelEngineException):
    """Resource conflict exception."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            message=message,
            error_type=APIErrorType.CONFLICT,
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class RateLimitException(NovelEngineException):
    """Rate limit exceeded exception."""

    def __init__(self, retry_after: Optional[int] = None):
        super().__init__(
            message="Rate limit exceeded",
            error_type=APIErrorType.RATE_LIMITED,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Retry after {retry_after} seconds"
                if retry_after
                else "Please slow down your requests"
            ),
        )


class ErrorHandler:
    """Centralized error handling system."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.error_count = 0
        self.start_time = time.time()

    def create_error_response(
        self,
        error: Union[NovelEngineException, Exception],
        request: Optional[Request] = None,
        request_id: Optional[str] = None,
        processing_time: Optional[float] = None,
    ) -> ErrorResponse:
        """Create standardized error response."""

        # Increment error counter
        self.error_count += 1

        # Determine error details
        if isinstance(error, NovelEngineException):
            api_error = APIError(
                type=error.error_type,
                message=error.message,
                detail=error.detail,
                code=error.code,
            )
            status_code = error.status_code
        elif isinstance(error, HTTPException):
            api_error = APIError(
                type=self._map_http_status_to_error_type(error.status_code),
                message=str(error.detail),
                detail=None,
            )
            status_code = error.status_code
        else:
            # Generic exception
            api_error = APIError(
                type=APIErrorType.INTERNAL_ERROR,
                message=(
                    "An unexpected error occurred" if not self.debug else str(error)
                ),
                detail=traceback.format_exc() if self.debug else None,
            )
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        # Create metadata
        metadata = APIMetadata(
            timestamp=datetime.now(),
            request_id=request_id,
            server_time=processing_time or 0.0,
            api_version="1.0.0",
        )

        # Log error
        self._log_error(error, request, api_error, status_code)

        return ErrorResponse(
            status=ResponseStatus.ERROR, error=api_error, metadata=metadata
        )

    def create_validation_error_response(
        self,
        validation_errors: List[ValidationError],
        request_id: Optional[str] = None,
        processing_time: Optional[float] = None,
    ) -> ErrorResponse:
        """Create validation error response."""

        metadata = APIMetadata(
            timestamp=datetime.now(),
            request_id=request_id,
            server_time=processing_time or 0.0,
            api_version="1.0.0",
        )

        # Main error
        main_error = APIError(
            type=APIErrorType.VALIDATION_ERROR,
            message=f"Validation failed for {len(validation_errors)} field(s)",
            detail="Please check the errors array for detailed field-level validation issues",
        )

        return ErrorResponse(
            status=ResponseStatus.ERROR,
            error=main_error,
            errors=validation_errors,
            metadata=metadata,
        )

    def _map_http_status_to_error_type(self, status_code: int) -> APIErrorType:
        """Map HTTP status codes to API error types."""
        mapping = {
            400: APIErrorType.BAD_REQUEST,
            401: APIErrorType.UNAUTHORIZED,
            403: APIErrorType.FORBIDDEN,
            404: APIErrorType.NOT_FOUND,
            409: APIErrorType.CONFLICT,
            422: APIErrorType.VALIDATION_ERROR,
            429: APIErrorType.RATE_LIMITED,
            500: APIErrorType.INTERNAL_ERROR,
            503: APIErrorType.SERVICE_UNAVAILABLE,
            504: APIErrorType.TIMEOUT,
        }
        return mapping.get(status_code, APIErrorType.INTERNAL_ERROR)

    def _log_error(
        self,
        error: Exception,
        request: Optional[Request],
        api_error: APIError,
        status_code: int,
    ):
        """Log error with appropriate level and context."""

        # Determine log level
        if status_code >= 500:
            log_level = logging.ERROR
        elif status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        # Create log message
        error_context = {
            "error_type": api_error.type.value,
            "status_code": status_code,
            "message": api_error.message,
            "error_count": self.error_count,
        }

        if request:
            error_context.update(
                {
                    "method": request.method,
                    "url": str(request.url),
                    "client_ip": request.client.host if request.client else "unknown",
                }
            )

        if isinstance(error, NovelEngineException):
            error_context["detail"] = error.detail
            error_context["code"] = error.code

        logger.log(
            log_level,
            f"API Error: {api_error.message}",
            extra=error_context,
            exc_info=status_code >= 500,
        )


def setup_error_handlers(app, debug: bool = False):
    """Setup error handlers for FastAPI application."""

    error_handler = ErrorHandler(debug=debug)

    @app.exception_handler(NovelEngineException)
    async def novel_engine_exception_handler(
        request: Request, exc: NovelEngineException
    ):
        """Handle Novel Engine specific exceptions."""
        processing_time = getattr(request.state, "processing_time", 0.0)
        request_id = getattr(request.state, "request_id", None)

        error_response = error_handler.create_error_response(
            error=exc,
            request=request,
            request_id=request_id,
            processing_time=processing_time,
        )

        return JSONResponse(
            status_code=exc.status_code, content=error_response.model_dump()
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTP exceptions."""
        processing_time = getattr(request.state, "processing_time", 0.0)
        request_id = getattr(request.state, "request_id", None)

        error_response = error_handler.create_error_response(
            error=exc,
            request=request,
            request_id=request_id,
            processing_time=processing_time,
        )

        return JSONResponse(
            status_code=exc.status_code, content=error_response.model_dump()
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle Pydantic validation errors."""
        processing_time = getattr(request.state, "processing_time", 0.0)
        request_id = getattr(request.state, "request_id", None)

        # Convert Pydantic errors to our validation error format
        validation_errors = []
        for error in exc.errors():
            field_path = ".".join(str(loc) for loc in error["loc"])
            validation_errors.append(
                ValidationError(
                    field=field_path, message=error["msg"], value=error.get("input")
                )
            )

        error_response = error_handler.create_validation_error_response(
            validation_errors=validation_errors,
            request_id=request_id,
            processing_time=processing_time,
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=error_response.model_dump(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions."""
        processing_time = getattr(request.state, "processing_time", 0.0)
        request_id = getattr(request.state, "request_id", None)

        error_response = error_handler.create_error_response(
            error=exc,
            request=request,
            request_id=request_id,
            processing_time=processing_time,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.model_dump(),
        )

    return error_handler


__all__ = [
    "NovelEngineException",
    "ValidationException",
    "ResourceNotFoundException",
    "ServiceUnavailableException",
    "ConflictException",
    "RateLimitException",
    "ErrorHandler",
    "setup_error_handlers",
]
