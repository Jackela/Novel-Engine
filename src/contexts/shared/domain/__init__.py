"""Shared domain components for cross-cutting concerns."""

from .errors import (
    ConfigError,
    OperationError,
    RepositoryError,
    ServiceError,
    StateError,
    ValidationError,
)

__all__ = [
    "ConfigError",
    "OperationError",
    "RepositoryError",
    "ServiceError",
    "StateError",
    "ValidationError",
]
