"""Domain exceptions for Novel Engine.

This module defines the exception hierarchy for the domain layer.
All domain exceptions inherit from DomainException to allow
catching all domain-specific errors.

Implements Error Bubbling pattern from DDD - exceptions carry context
for propagation from Domain to Application to Interface layers.
"""

from __future__ import annotations

from typing import Any


class DomainException(Exception):
    """Base exception for all domain-related errors.

    Attributes:
        message: Human-readable error message.
        code: Error code for programmatic handling.
        context: Additional context for error bubbling.

    Example:
        >>> raise DomainException("Invalid operation", code="DOMAIN_001")

        >>> try:
        ...     process_entity(entity)
        ... except DomainException as e:
        ...     logger.error(f"Domain error {e.code}: {e.message}")
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        **context: Any,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Human-readable error message.
            code: Error code for programmatic handling. Defaults to None.
            **context: Additional context for error bubbling.
        """
        self.message = message
        self.code = code if code is not None else "DOMAIN_ERROR"
        self.context = context
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            String with message and code if explicitly provided.
        """
        if self.code and self.code != "DOMAIN_ERROR":
            return f"[{self.code}] {self.message}"
        return self.message

    def __repr__(self) -> str:
        """Return detailed representation.

        Returns:
            Detailed string with class name and attributes.
        """
        return (
            f"{self.__class__.__name__}(message={self.message!r}, code={self.code!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for serialization.

        Returns:
            Dictionary with error details for JSON serialization.
        """
        return {
            "message": self.message,
            "code": self.code,
            "context": self.context,
            "exception_type": self.__class__.__name__,
        }


class ValidationException(DomainException):
    """Exception raised when domain validation fails.

    This is used for invariant violations, invalid state transitions,
    and other validation errors in the domain.

    Attributes:
        field: Optional field name that failed validation.

    Example:
        >>> raise ValidationException(
        ...     "Title cannot be empty",
        ...     field="title",
        ...     code="VAL_001"
        ... )
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        code: str = "VALIDATION_ERROR",
        **context: Any,
    ) -> None:
        """Initialize the validation exception.

        Args:
            message: Human-readable error message.
            field: Optional field name that failed validation.
            code: Error code for programmatic handling.
            **context: Additional context for error bubbling.
        """
        self.field = field
        super().__init__(message, code, **context)

    def __str__(self) -> str:
        """Return string representation with field if present."""
        base = super().__str__()
        if self.field:
            return f"{base} (field: {self.field})"
        return base


class BusinessRuleException(DomainException):
    """Exception raised when a business rule is violated.

    Business rules are domain constraints that go beyond simple
    validation, such as "a novel cannot be published without chapters".

    Attributes:
        rule_name: Optional name of the violated business rule.

    Example:
        >>> raise BusinessRuleException(
        ...     "Cannot publish novel without chapters",
        ...     rule_name="PUBLISH_REQUIREMENT",
        ...     code="RULE_001"
        ... )
    """

    def __init__(
        self,
        message: str,
        rule_name: str | None = None,
        code: str = "BUSINESS_RULE_VIOLATION",
        **context: Any,
    ) -> None:
        """Initialize the business rule exception.

        Args:
            message: Human-readable error message.
            rule_name: Optional name of the violated rule.
            code: Error code for programmatic handling.
            **context: Additional context for error bubbling.
        """
        self.rule_name = rule_name
        super().__init__(message, code, **context)

    def __str__(self) -> str:
        """Return string representation with rule name if present."""
        base = super().__str__()
        if self.rule_name:
            return f"{base} (rule: {self.rule_name})"
        return base


class EntityNotFoundException(DomainException):
    """Exception raised when a requested entity cannot be found.

    Attributes:
        entity_type: Type name of entity that was not found.
        entity_id: ID of the entity that was not found.

    Example:
        >>> raise EntityNotFoundException(
        ...     entity_type="Novel",
        ...     entity_id="123",
        ...     code="NOT_FOUND_001"
        ... )
    """

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        code: str = "ENTITY_NOT_FOUND",
        **context: Any,
    ) -> None:
        """Initialize the not found exception.

        Args:
            entity_type: Type name of entity that was not found.
            entity_id: ID of the entity that was not found.
            code: Error code for programmatic handling.
            **context: Additional context for error bubbling.
        """
        self.entity_type = entity_type
        self.entity_id = entity_id
        message = f"{entity_type} with id {entity_id} not found"
        super().__init__(message, code, **context)


class ConcurrencyException(DomainException):
    """Exception raised when optimistic concurrency check fails.

    This occurs when attempting to update an entity that has been
    modified by another process since it was read.

    Attributes:
        entity_type: Type name of entity with conflict.
        entity_id: ID of the entity with conflict.
        expected_version: Version that was expected.
        actual_version: Actual version in the database.

    Example:
        >>> raise ConcurrencyException(
        ...     entity_type="Novel",
        ...     entity_id="123",
        ...     expected_version=5,
        ...     actual_version=6,
        ...     code="CONCURRENT_UPDATE"
        ... )
    """

    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        expected_version: int,
        actual_version: int,
        code: str = "CONCURRENCY_CONFLICT",
        **context: Any,
    ) -> None:
        """Initialize the concurrency exception.

        Args:
            entity_type: Type name of entity with conflict.
            entity_id: ID of the entity with conflict.
            expected_version: Version that was expected.
            actual_version: Actual version in the database.
            code: Error code for programmatic handling.
            **context: Additional context for error bubbling.
        """
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.expected_version = expected_version
        self.actual_version = actual_version
        message = (
            f"{entity_type} with id {entity_id} was modified. "
            f"Expected version {expected_version}, but found {actual_version}"
        )
        super().__init__(message, code, **context)


class DuplicateEntityException(DomainException):
    """Exception raised when attempting to create a duplicate entity.

    Attributes:
        entity_type: Type name of entity that already exists.
        identifier: The unique identifier that caused the conflict.

    Example:
        >>> raise DuplicateEntityException(
        ...     entity_type="User",
        ...     identifier="user@example.com",
        ...     code="DUPLICATE_USER"
        ... )
    """

    def __init__(
        self,
        entity_type: str,
        identifier: str,
        code: str = "DUPLICATE_ENTITY",
        **context: Any,
    ) -> None:
        """Initialize the duplicate entity exception.

        Args:
            entity_type: Type name of entity that already exists.
            identifier: The unique identifier causing conflict.
            code: Error code for programmatic handling.
            **context: Additional context for error bubbling.
        """
        self.entity_type = entity_type
        self.identifier = identifier
        message = f"{entity_type} with identifier '{identifier}' already exists"
        super().__init__(message, code, **context)
