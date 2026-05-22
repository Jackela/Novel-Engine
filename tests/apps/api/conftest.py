"""Shared fixtures and environment for canonical API tests."""

# mypy: disable-error-code=misc

from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.apps.api.dependencies import reset_identity_dependencies, reset_jwt_manager
from src.apps.api.health import reset_health_state
from src.apps.api.routes.workspaces import reset_workspace_jobs
from src.apps.api.runtime import runtime_store
from src.shared.infrastructure.config.settings import reset_settings


@pytest.fixture(autouse=True)
def reset_canonical_api_state() -> Generator[None, None, None]:
    """Reset process-local state before and after each test."""
    reset_settings()
    reset_jwt_manager()
    reset_identity_dependencies()
    reset_health_state()
    reset_workspace_jobs()
    runtime_store.reset()
    yield
    runtime_store.reset()
    reset_workspace_jobs()
    reset_health_state()
    reset_identity_dependencies()
    reset_jwt_manager()
    reset_settings()
