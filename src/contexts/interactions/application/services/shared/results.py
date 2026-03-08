#!/usr/bin/env python3
"""
Interaction-specific Result type alias.

Provides a specialized Result type for interaction operations with
InteractionError as the default error type.
"""

from typing import Any, TypeVar

from ......core.result import Err, Ok, Result
from .errors import InteractionError

T = TypeVar("T")

# Type alias for interaction results - uses InteractionError as default error type
InteractionResult = Result[T, InteractionError]


# Helper functions for creating interaction results
def interaction_ok(value: T) -> InteractionResult[T]:
    """Create a successful interaction result."""
    return Ok(value)


def interaction_err(error: InteractionError) -> InteractionResult[Any]:
    """Create a failed interaction result."""
    return Err(error)
