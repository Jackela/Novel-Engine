"""
Shared Domain Errors

Common error types used across multiple contexts for Result pattern migration.
These errors represent generic failure modes that don't belong to a specific domain.

Why shared errors:
    - Avoid duplication of common error types
    - Consistent error handling across contexts
    - Reduced coupling between contexts
"""

from __future__ import annotations

from typing import Any

from src.core.result import Error


class ServiceError(Error):
    """Error raised when a service operation fails."""

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if service_name:
            full_details["service_name"] = service_name
        if operation:
            full_details["operation"] = operation
        super().__init__(
            code="SERVICE_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


class RepositoryError(Error):
    """Error raised when a repository operation fails."""

    def __init__(
        self,
        message: str,
        entity_type: str | None = None,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if entity_type:
            full_details["entity_type"] = entity_type
        if operation:
            full_details["operation"] = operation
        super().__init__(
            code="REPOSITORY_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


class ConfigError(Error):
    """Error raised when configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if config_key:
            full_details["config_key"] = config_key
        super().__init__(
            code="CONFIG_ERROR",
            message=message,
            recoverable=False,
            details=full_details,
        )


class StateError(Error):
    """Error raised when entity state is invalid."""

    def __init__(
        self,
        message: str,
        entity_id: str | None = None,
        expected_state: str | None = None,
        actual_state: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if entity_id:
            full_details["entity_id"] = entity_id
        if expected_state:
            full_details["expected_state"] = expected_state
        if actual_state:
            full_details["actual_state"] = actual_state
        super().__init__(
            code="STATE_ERROR",
            message=message,
            recoverable=False,
            details=full_details,
        )


class ValidationError(Error):
    """Error raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: Any = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if field:
            full_details["field"] = field
        if value is not None:
            full_details["value"] = str(value)
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


class OperationError(Error):
    """Error raised when a general operation fails."""

    def __init__(
        self,
        message: str,
        operation: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        full_details = details or {}
        if operation:
            full_details["operation"] = operation
        super().__init__(
            code="OPERATION_ERROR",
            message=message,
            recoverable=True,
            details=full_details,
        )


__all__ = [
    "ConfigError",
    "OperationError",
    "RepositoryError",
    "ServiceError",
    "StateError",
    "ValidationError",
]
