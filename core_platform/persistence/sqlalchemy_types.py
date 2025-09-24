#!/usr/bin/env python3
"""
SQLAlchemy Type Safety Patterns
===============================

Type safety patterns and protocols for SQLAlchemy ORM operations.
Provides type-safe patterns for Column definitions, instance access,
and ORM-to-domain object mapping.
"""

from datetime import datetime
from typing import Any, Generic, Optional, Protocol, TypeVar, cast
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.sql.type_api import TypeEngine
from typing_extensions import Annotated

# Type Variables for Generic Patterns
T = TypeVar("T")
ModelT = TypeVar("ModelT", bound="SQLAlchemyModel")
DomainT = TypeVar("DomainT")


# SQLAlchemy Typed Column Pattern
class TypedColumn(Generic[T]):
    """
    Type-safe wrapper for SQLAlchemy Column that preserves type information.

    This addresses the fundamental issue where MyPy sees Column objects
    at class level but actual values at instance level.
    """

    def __init__(self, column: Column[T]) -> None:
        self._column = column

    def __get__(self, instance: Any, owner: Any) -> T:
        """Return the actual value when accessed on instance."""
        if instance is None:
            return cast(T, self._column)
        return cast(T, getattr(instance, self._column.key))

    def __set__(self, instance: Any, value: T) -> None:
        """Set the actual value when assigned on instance."""
        setattr(instance, self._column.key, value)


# Type-Safe SQLAlchemy Model Base Protocol
class SQLAlchemyModel(Protocol):
    """Protocol for type-safe SQLAlchemy models."""

    id: UUID
    created_at: datetime
    updated_at: datetime


# Domain Mapper Protocol
class DomainMapper(Protocol[ModelT, DomainT]):
    """Protocol for mapping between ORM models and domain objects."""

    def to_domain(self, model: ModelT) -> DomainT:
        """Convert ORM model to domain object."""
        ...

    def to_orm(self, domain: DomainT) -> ModelT:
        """Convert domain object to ORM model."""
        ...

    def update_orm(self, model: ModelT, domain: DomainT) -> None:
        """Update existing ORM model from domain object."""
        ...


# Repository Protocol
class Repository(Protocol[DomainT]):
    """Generic repository protocol for domain objects."""

    async def find_by_id(self, entity_id: str) -> Optional[DomainT]:
        """Find domain object by ID."""
        ...

    async def save(self, entity: DomainT) -> DomainT:
        """Save domain object."""
        ...

    async def delete(self, entity_id: str) -> bool:
        """Delete domain object by ID."""
        ...


# Type Guards for SQLAlchemy Operations
def ensure_not_none(value: Optional[T]) -> T:
    """Type guard to ensure value is not None."""
    if value is None:
        raise ValueError("Expected non-None value")
    return value


def safe_column_access(
    instance: Any, column_name: str, expected_type: type[T]
) -> T:
    """Type-safe access to SQLAlchemy model attributes."""
    value = getattr(instance, column_name)
    if not isinstance(value, expected_type):
        raise TypeError(f"Expected {expected_type}, got {type(value)}")
    return value


# Authentication Model Type Safety Patterns
class AuthenticationTypes:
    """Type definitions for authentication models."""

    # User model field types
    UserId = Annotated[UUID, "User unique identifier"]
    Email = Annotated[str, "User email address"]
    Username = Annotated[str, "User username"]
    PasswordHash = Annotated[str, "Hashed password"]
    Salt = Annotated[str, "Password salt"]
    FailedAttempts = Annotated[int, "Failed login attempt count"]
    LockedUntil = Annotated[Optional[datetime], "Account lock expiration"]
    LastLogin = Annotated[Optional[datetime], "Last login timestamp"]
    IPAddress = Annotated[Optional[str], "IP address"]

    # Token types
    AccessToken = Annotated[str, "JWT access token"]
    RefreshToken = Annotated[str, "JWT refresh token"]
    ResetToken = Annotated[Optional[str], "Password reset token"]
    VerificationToken = Annotated[Optional[str], "Email verification token"]


# Character Model Type Safety Patterns
class CharacterTypes:
    """Type definitions for character models."""

    # Character field types
    CharacterId = Annotated[UUID, "Character unique identifier"]
    CharacterName = Annotated[str, "Character name"]
    Age = Annotated[int, "Character age"]
    Level = Annotated[int, "Character level"]
    IsAlive = Annotated[bool, "Character alive status"]
    Version = Annotated[int, "Character version for optimistic locking"]

    # Profile types
    Gender = Annotated[str, "Character gender"]
    Race = Annotated[str, "Character race"]
    CharacterClass = Annotated[str, "Character class"]


# SQLAlchemy Typing Utilities
class SQLAlchemyTyping:
    """Utilities for SQLAlchemy type safety."""

    @staticmethod
    def safe_datetime_comparison(
        column_value: Optional[datetime], compare_value: datetime
    ) -> bool:
        """Type-safe datetime comparison for SQLAlchemy columns."""
        if column_value is None:
            return False
        # At runtime, column_value will be a datetime, not a Column
        return cast(datetime, column_value) < compare_value

    @staticmethod
    def safe_int_increment(column_value: int) -> int:
        """Type-safe integer increment for SQLAlchemy columns."""
        # At runtime, column_value will be an int, not a Column
        return cast(int, column_value) + 1

    @staticmethod
    def safe_string_assignment(value: str) -> str:
        """Type-safe string assignment for SQLAlchemy columns."""
        return cast(str, value)

    @staticmethod
    def safe_optional_assignment(value: Optional[T]) -> Optional[T]:
        """Type-safe optional value assignment for SQLAlchemy columns."""
        return cast(Optional[T], value)


# Repository Implementation Helpers
class RepositoryHelpers:
    """Helper functions for repository implementations."""

    @staticmethod
    def handle_sqlalchemy_session_commit(session: Any) -> None:
        """Handle SQLAlchemy session commit with proper error handling."""
        try:
            session.commit()
        except Exception:
            session.rollback()
            raise

    @staticmethod
    def create_query_filter(
        query: Any, filter_field: str, filter_value: Any
    ) -> Any:
        """Create type-safe query filter."""
        return query.filter(
            getattr(query.column_descriptions[0]["type"], filter_field)
            == filter_value
        )


# Type-Safe Model Mixins
class TimestampMixin:
    """Mixin for timestamp fields with proper typing."""

    created_at: datetime
    updated_at: datetime

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()


class VersionMixin:
    """Mixin for optimistic locking with proper typing."""

    version: int

    def increment_version(self) -> None:
        """Increment version for optimistic locking."""
        self.version = SQLAlchemyTyping.safe_int_increment(self.version)


# Validation Patterns
class ModelValidation:
    """Validation patterns for SQLAlchemy models."""

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        return "@" in email and "." in email

    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format."""
        return len(username) >= 3 and username.isalnum()

    @staticmethod
    def validate_character_name(name: str) -> bool:
        """Validate character name."""
        return 1 <= len(name) <= 50 and name.strip() == name


# Error Handling for Type Safety
class TypeSafetyError(Exception):
    """Base exception for type safety violations."""

    pass


class ColumnTypeMismatchError(TypeSafetyError):
    """Raised when column type doesn't match expected type."""

    def __init__(
        self, column_name: str, expected_type: type, actual_type: type
    ):
        super().__init__(
            f"Column '{column_name}' expected type {expected_type}, got {actual_type}"
        )


class DomainMappingError(TypeSafetyError):
    """Raised when domain-to-ORM mapping fails."""

    pass


__all__ = [
    "TypedColumn",
    "SQLAlchemyModel",
    "DomainMapper",
    "Repository",
    "ensure_not_none",
    "safe_column_access",
    "AuthenticationTypes",
    "CharacterTypes",
    "SQLAlchemyTyping",
    "RepositoryHelpers",
    "TimestampMixin",
    "VersionMixin",
    "ModelValidation",
    "TypeSafetyError",
    "ColumnTypeMismatchError",
    "DomainMappingError",
]
