"""Honcho infrastructure package.

This package provides shared Honcho client and configuration for
memory management across all bounded contexts.
"""

from __future__ import annotations

from .client import HonchoClient, HonchoClientError, get_honcho_client
from .config import HonchoSettings

__all__ = [
    "HonchoClient",
    "HonchoClientError",
    "HonchoSettings",
    "get_honcho_client",
]
