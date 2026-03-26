"""Honcho client exceptions and error handling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class HonchoErrorDetails:
    """Structured error details for Honcho operations.

    Attributes:
        operation: The operation being performed (e.g., "create_workspace").
        entity_id: The ID of the entity being operated on.
        error_code: Standardized error code (e.g., "CONNECTION_ERROR").
        original_exception: The original exception that was raised.
        context: Additional context information.
    """

    operation: str
    entity_id: str
    error_code: str
    original_exception: Optional[Exception] = None
    context: Optional[dict[str, Any]] = None


class HonchoClientError(Exception):
    """Exception raised by HonchoClient operations.

    Attributes:
        message: Human-readable error message.
        details: Structured error details.
        error_code: Standardized error code.
    """

    def __init__(
        self,
        message: str,
        details: Optional[HonchoErrorDetails] = None,
    ) -> None:
        super().__init__(message)
        self.details = details
        self.error_code = details.error_code if details else "UNKNOWN_ERROR"
