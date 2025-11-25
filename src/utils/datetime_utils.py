"""Timezone-aware datetime utilities.

This module provides utilities for working with timezone-aware datetime objects,
replacing deprecated datetime methods like datetime.utcnow().

Python 3.12+ deprecates naive datetime methods in favor of timezone-aware alternatives.
"""

from datetime import datetime, timezone


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
