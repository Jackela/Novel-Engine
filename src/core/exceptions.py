#!/usr/bin/env python3
"""
Core Exception Hierarchy for Novel Engine

Provides structured exception types with rich context for better debugging
and error handling throughout the application.
"""

from typing import Any, Dict, Optional


class NovelEngineException(Exception):
    """
    Base exception for all Novel Engine errors.

    Provides structured error information with error codes, context data,
    and recoverability flags for sophisticated error handling.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
    ):
        """
        Initialize Novel Engine exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code for categorization
            context: Additional context data for debugging
            recoverable: Whether the error can be recovered from
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.context = context or {}
        self.recoverable = recoverable

    def __str__(self) -> str:
        """Return string representation of the exception."""
        return self.message


class ValidationException(NovelEngineException):
    """
    Validation error exception.

    Raised when input validation fails, providing detailed field-level
    error information.
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        constraint: Optional[str] = None,
    ):
        """
        Initialize validation exception.

        Args:
            message: Error message
            field: Field name that failed validation
            value: Invalid value that was provided
            constraint: Validation constraint that was violated
        """
        super().__init__(
            message=message, error_code="VALIDATION_ERROR", recoverable=True
        )
        self.field = field
        self.value = value
        self.constraint = constraint

    def __str__(self) -> str:
        """Return detailed validation error message."""
        parts = [self.message]
        if self.field:
            parts.append(f"field='{self.field}'")
        if self.constraint:
            parts.append(f"constraint='{self.constraint}'")
        return " | ".join(parts)


class ResourceNotFoundException(NovelEngineException):
    """
    Resource not found exception.

    Raised when a requested resource (character, scene, etc.) cannot be found.
    """

    def __init__(self, resource_type: str, resource_id: str):
        """
        Initialize resource not found exception.

        Args:
            resource_type: Type of resource (e.g., "Character", "Scene")
            resource_id: Identifier of the missing resource
        """
        message = f"{resource_type} with ID '{resource_id}' not found"
        super().__init__(
            message=message, error_code="RESOURCE_NOT_FOUND", recoverable=False
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class StateInconsistencyException(NovelEngineException):
    """
    State inconsistency exception.

    Raised when system state is inconsistent or corrupted, indicating
    a serious internal error.
    """

    def __init__(
        self,
        component: str,
        expected_state: str,
        actual_state: str,
        action: Optional[str] = None,
    ):
        """
        Initialize state inconsistency exception.

        Args:
            component: Component with inconsistent state
            expected_state: Expected state description
            actual_state: Actual state found
            action: Action that revealed the inconsistency
        """
        message = (
            f"State inconsistency in {component}: "
            f"expected '{expected_state}', found '{actual_state}'"
        )
        if action:
            message += f" during '{action}'"

        super().__init__(
            message=message, error_code="STATE_INCONSISTENCY", recoverable=False
        )
        self.component = component
        self.expected_state = expected_state
        self.actual_state = actual_state
        self.action = action


class LLMException(NovelEngineException):
    """
    LLM integration exception.

    Raised when LLM API calls fail or return unexpected results.
    """

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        retry_count: int = 0,
        error_details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize LLM exception.

        Args:
            message: Error message
            provider: LLM provider name (e.g., "gemini", "openai")
            retry_count: Number of retries attempted
            error_details: Additional error details from provider
        """
        super().__init__(
            message=message,
            error_code="LLM_ERROR",
            context=error_details or {},
            recoverable=True,
        )
        self.provider = provider
        self.retry_count = retry_count


class MemoryException(NovelEngineException):
    """
    Memory system exception.

    Raised when memory storage, retrieval, or consistency operations fail.
    """

    def __init__(
        self,
        message: str,
        memory_type: Optional[str] = None,
        agent_id: Optional[str] = None,
        operation: Optional[str] = None,
    ):
        """
        Initialize memory exception.

        Args:
            message: Error message
            memory_type: Type of memory (e.g., "episodic", "semantic")
            agent_id: Agent whose memory operation failed
            operation: Memory operation that failed (e.g., "store", "retrieve")
        """
        super().__init__(message=message, error_code="MEMORY_ERROR", recoverable=True)
        self.memory_type = memory_type
        self.agent_id = agent_id
        self.operation = operation


__all__ = [
    "NovelEngineException",
    "ValidationException",
    "ResourceNotFoundException",
    "StateInconsistencyException",
    "LLMException",
    "MemoryException",
]
