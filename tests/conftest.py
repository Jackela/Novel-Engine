"""Shared pytest setup for source-backed tests."""

# mypy: disable-error-code=misc

from __future__ import annotations

import importlib
import os
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip opt-in external integration tests unless explicitly enabled."""
    del config

    enabled_markers = {
        "requires_dashscope": os.getenv("ENABLE_DASHSCOPE_TESTS") == "1",
    }
    skip_messages = {
        "requires_dashscope": (
            "DashScope integration tests are opt-in; set ENABLE_DASHSCOPE_TESTS=1 to run them."
        ),
    }

    for item in items:
        for marker_name, enabled in enabled_markers.items():
            if not enabled and marker_name in item.keywords:
                item.add_marker(pytest.mark.skip(reason=skip_messages[marker_name]))


def build_canonical_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    monkeypatch.setenv(
        "APP_DATA_DIR",
        tempfile.mkdtemp(prefix="novel-engine-api-tests-"),
    )
    monkeypatch.setenv(
        "SECURITY_SECRET_KEY",
        "test-secret-key-for-contract-checks-1234567890",
    )
    monkeypatch.setenv("MONITORING_METRICS_ENABLED", "false")
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    from src.contexts.studio.application import services as services_module
    from src.contexts.studio.infrastructure.database import StudioDatabase
    from src.shared.infrastructure.config import settings as settings_module

    settings_module.reset_settings()
    database = StudioDatabase(
        f"sqlite:///{Path(os.environ['APP_DATA_DIR']) / 'test.sqlite3'}"
    )
    database.initialize(create_backup=False)
    services_module.studio_store.database = database

    for module_name in ("src.apps.api.router",):
        sys.modules.pop(module_name, None)

    main_module = importlib.import_module("src.apps.api.main")
    return cast(FastAPI, main_module.create_application())


@pytest.fixture
def canonical_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    try:
        return build_canonical_app(monkeypatch)
    except Exception as exc:
        pytest.fail(f"canonical app failed to build: {exc}")


@pytest.fixture
def canonical_client(canonical_app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(canonical_app, raise_server_exceptions=False) as client:
        yield client
