"""Shared pytest setup for source-backed tests."""

# mypy: disable-error-code=misc

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import types
from collections.abc import Generator
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _install_asyncpg_stub() -> None:
    if importlib.util.find_spec("asyncpg") is not None or "asyncpg" in sys.modules:
        return

    asyncpg_stub = types.ModuleType("asyncpg")

    class Connection:  # pragma: no cover - import-only fallback
        pass

    class Pool:  # pragma: no cover - import-only fallback
        pass

    class Record(dict):  # pragma: no cover - import-only fallback
        pass

    class PostgresError(Exception):  # pragma: no cover - import-only fallback
        pass

    async def create_pool(
        *args: Any, **kwargs: Any
    ) -> Any:  # pragma: no cover - import-only fallback
        raise RuntimeError("asyncpg is not installed in this test environment")

    setattr(asyncpg_stub, "Connection", Connection)
    setattr(asyncpg_stub, "Pool", Pool)
    setattr(asyncpg_stub, "Record", Record)
    setattr(asyncpg_stub, "PostgresError", PostgresError)
    setattr(asyncpg_stub, "create_pool", create_pool)
    sys.modules["asyncpg"] = asyncpg_stub


_install_asyncpg_stub()

collect_ignore_glob: list[str] = []
if importlib.util.find_spec("dependency_injector") is None:
    collect_ignore_glob.append("shared/infrastructure/di/*.py")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip opt-in external integration tests unless explicitly enabled."""
    del config

    enabled_markers = {
        "requires_dashscope": os.getenv("ENABLE_DASHSCOPE_TESTS") == "1",
        "requires_honcho": os.getenv("ENABLE_HONCHO_TESTS") == "1",
        "requires_chroma": os.getenv("ENABLE_CHROMA_TESTS") == "1",
        "postgres_integration": os.getenv("ENABLE_POSTGRES_TESTS") == "1",
    }
    skip_messages = {
        "requires_dashscope": (
            "DashScope integration tests are opt-in; set ENABLE_DASHSCOPE_TESTS=1 to run them."
        ),
        "requires_honcho": (
            "Honcho integration tests are opt-in; set ENABLE_HONCHO_TESTS=1 to run them."
        ),
        "requires_chroma": (
            "Chroma integration tests are opt-in; set ENABLE_CHROMA_TESTS=1 to run them."
        ),
        "postgres_integration": (
            "PostgreSQL integration tests are opt-in; set ENABLE_POSTGRES_TESTS=1 to run them."
        ),
    }

    for item in items:
        nodeid = item.nodeid.replace("\\", "/")
        if (
            ("postgres_" in nodeid or "/postgres/" in nodeid)
            and not enabled_markers["postgres_integration"]
        ):
            item.add_marker(pytest.mark.skip(reason=skip_messages["postgres_integration"]))
            continue

        for marker_name, enabled in enabled_markers.items():
            if not enabled and marker_name in item.keywords:
                item.add_marker(pytest.mark.skip(reason=skip_messages[marker_name]))


def build_canonical_app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    monkeypatch.setenv(
        "SECURITY_SECRET_KEY",
        "test-secret-key-for-contract-checks-1234567890",
    )
    monkeypatch.setenv("MONITORING_METRICS_ENABLED", "false")
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    from src.apps.api.dependencies import reset_knowledge_service
    from src.apps.api.health import reset_health_state
    from src.contexts.narrative.infrastructure.runtime import (
        reset_story_workflow_service,
    )
    from src.shared.infrastructure.config import settings as settings_module

    settings_module.reset_settings()
    reset_knowledge_service()
    reset_health_state()
    reset_story_workflow_service()

    for module_name in ("src.apps.api.router", "src.apps.api.main"):
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
