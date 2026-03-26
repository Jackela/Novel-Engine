"""Canonical runtime re-export.

The in-memory guest/orchestration implementation lives under
``src.apps.api.services.runtime``. This module keeps a stable import path so the
application and tests share the same runtime store instance.
"""

from __future__ import annotations

from src.apps.api.services.runtime import (
    CanonicalRuntimeService,
    GuestSession,
    runtime_store,
)

__all__ = ["CanonicalRuntimeService", "GuestSession", "runtime_store"]
