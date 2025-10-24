#!/usr/bin/env python3
"""
Response Builder Utilities

Centralized utilities for building StandardResponse objects with consistent patterns.
"""

from typing import Any, Dict, Optional

from src.core.data_models import ErrorInfo, StandardResponse


class ResponseBuilder:
    """Utility class for building standardized responses."""

    @staticmethod
    def success(
        data: Dict[str, Any],
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StandardResponse:
        """
        Build successful response.

        Args:
            data: Response data payload
            message: Optional success message
            metadata: Optional metadata

        Returns:
            StandardResponse with success=True
        """
        return StandardResponse(
            success=True,
            message=message,
            data=data,
            metadata=metadata or {},
        )

    @staticmethod
    def error(
        code: str,
        message: str,
        recoverable: bool = True,
        details: Optional[Dict[str, Any]] = None,
    ) -> StandardResponse:
        """
        Build error response.

        Args:
            code: Error code
            message: Error message
            recoverable: Whether error is recoverable
            details: Optional error details

        Returns:
            StandardResponse with success=False
        """
        return StandardResponse(
            success=False,
            error=ErrorInfo(
                code=code,
                message=message,
                recoverable=recoverable,
                details=details or {},
            ),
        )

    @staticmethod
    def not_found(entity_type: str, entity_id: str) -> StandardResponse:
        """
        Build not found error response.

        Args:
            entity_type: Type of entity (e.g., "equipment", "agent")
            entity_id: ID of entity that was not found

        Returns:
            StandardResponse with NOT_FOUND error
        """
        return StandardResponse(
            success=False,
            error=ErrorInfo(
                code=f"{entity_type.upper()}_NOT_FOUND",
                message=f"{entity_type.capitalize()} '{entity_id}' not found",
            ),
        )

    @staticmethod
    def validation_error(
        message: str, details: Optional[Dict[str, Any]] = None
    ) -> StandardResponse:
        """
        Build validation error response.

        Args:
            message: Validation error message
            details: Optional validation details

        Returns:
            StandardResponse with VALIDATION_ERROR
        """
        return StandardResponse(
            success=False,
            error=ErrorInfo(
                code="VALIDATION_ERROR",
                message=message,
                details=details or {},
            ),
        )

    @staticmethod
    def operation_failed(
        operation_name: str, exception: Exception, recoverable: bool = True
    ) -> StandardResponse:
        """
        Build operation failed error response.

        Args:
            operation_name: Name of failed operation
            exception: Exception that caused failure
            recoverable: Whether operation is recoverable

        Returns:
            StandardResponse with operation failure error
        """
        return StandardResponse(
            success=False,
            error=ErrorInfo(
                code=f"{operation_name.upper()}_FAILED",
                message=f"{operation_name} failed: {str(exception)}",
                recoverable=recoverable,
            ),
        )


__all__ = ["ResponseBuilder"]
