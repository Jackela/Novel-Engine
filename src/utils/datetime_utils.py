"""Timezone-aware datetime utilities.

This module provides utilities for working with timezone-aware datetime objects,
replacing deprecated datetime methods like datetime.utcnow().

Python 3.12+ deprecates naive datetime methods in favor of timezone-aware alternatives.
"""

from datetime import datetime, timezone

from src.contexts.shared.domain.errors import OperationError
from src.core.result import Err, Ok, Result


def utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime.

    Replacement for deprecated datetime.utcnow().

    Returns:
        datetime: Current UTC time with timezone info.

    Example:
        >>> now = utc_now()
        >>> now.tzinfo == timezone.utc
        True
    """
    return datetime.now(timezone.utc)


def utc_now_result() -> Result[datetime, OperationError]:
    """
    Get current UTC time as timezone-aware datetime (Result pattern).

    Replacement for deprecated datetime.utcnow() with explicit error handling.

    Returns:
        Result containing current UTC datetime on success.
        - Ok: Current UTC time with timezone info
        - Err(OperationError): If time retrieval fails

    Example:
        >>> result = utc_now_result()
        >>> if result.is_ok:
        ...     now = result.value
        ...     assert now.tzinfo == timezone.utc
    """
    try:
        return Ok(datetime.now(timezone.utc))
    except Exception as e:
        return Err(
            OperationError(
                message=f"Failed to get current UTC time: {e}",
                operation="utc_now",
            )
        )


def from_timestamp(ts: float) -> datetime:
    """Convert Unix timestamp to timezone-aware UTC datetime.

    Replacement for deprecated datetime.utcfromtimestamp().

    Args:
        ts: Unix timestamp (seconds since epoch).

    Returns:
        datetime: UTC datetime with timezone info.

    Example:
        >>> dt = from_timestamp(1234567890)
        >>> dt.tzinfo == timezone.utc
        True
    """
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def from_timestamp_result(ts: float) -> Result[datetime, OperationError]:
    """
    Convert Unix timestamp to timezone-aware UTC datetime (Result pattern).

    Replacement for deprecated datetime.utcfromtimestamp() with explicit error handling.

    Args:
        ts: Unix timestamp (seconds since epoch).

    Returns:
        Result containing UTC datetime on success.
        - Ok: UTC datetime with timezone info
        - Err(OperationError): If conversion fails

    Example:
        >>> result = from_timestamp_result(1234567890)
        >>> if result.is_ok:
        ...     dt = result.value
        ...     assert dt.tzinfo == timezone.utc
    """
    try:
        if ts < 0:
            return Err(
                OperationError(
                    message=f"Timestamp cannot be negative, got {ts}",
                    operation="from_timestamp",
                    details={"timestamp": ts},
                )
            )
        return Ok(datetime.fromtimestamp(ts, tz=timezone.utc))
    except Exception as e:
        return Err(
            OperationError(
                message=f"Failed to convert timestamp: {e}",
                operation="from_timestamp",
                details={"timestamp": ts},
            )
        )


__all__ = [
    "from_timestamp",
    "from_timestamp_result",
    "utc_now",
    "utc_now_result",
]
