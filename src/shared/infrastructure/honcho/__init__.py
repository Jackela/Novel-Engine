"""Honcho infrastructure package.

This package provides shared Honcho client and configuration for
memory management across all bounded contexts.
"""

from __future__ import annotations

from .client import HonchoClient, create_honcho_client
from .config import HonchoSettings
from .errors import HonchoClientError, HonchoErrorDetails

__all__ = [
    "HonchoClient",
    "HonchoClientError",
    "HonchoErrorDetails",
    "HonchoSettings",
    "create_honcho_client",
]
