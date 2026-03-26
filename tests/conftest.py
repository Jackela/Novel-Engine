"""Shared pytest setup for source-backed tests."""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import types
import typing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from typing_extensions import override as _override
except ImportError:  # pragma: no cover - fallback for minimal envs
    def _override(func):
        return func

if not hasattr(typing, "override"):
    typing.override = _override


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

    async def create_pool(*args, **kwargs):  # pragma: no cover - import-only fallback
        raise RuntimeError("asyncpg is not installed in this test environment")

    asyncpg_stub.Connection = Connection
    asyncpg_stub.Pool = Pool
    asyncpg_stub.Record = Record
    asyncpg_stub.PostgresError = PostgresError
    asyncpg_stub.create_pool = create_pool
    sys.modules["asyncpg"] = asyncpg_stub


_install_asyncpg_stub()

collect_ignore_glob: list[str] = []
if importlib.util.find_spec("dependency_injector") is None:
    collect_ignore_glob.append("shared/infrastructure/di/*.py")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip opt-in external integration tests unless explicitly enabled."""
    del config

    enabled_markers = {
        "requires_openai": os.getenv("ENABLE_OPENAI_TESTS") == "1",
        "requires_chroma": os.getenv("ENABLE_CHROMA_TESTS") == "1",
        "postgres_integration": os.getenv("ENABLE_POSTGRES_TESTS") == "1",
        "evaluation": os.getenv("ENABLE_EVALUATION_TESTS") == "1",
    }
    skip_messages = {
        "requires_openai": (
            "OpenAI integration tests are opt-in; set ENABLE_OPENAI_TESTS=1 to run them."
        ),
        "requires_chroma": (
            "Chroma integration tests are opt-in; set ENABLE_CHROMA_TESTS=1 to run them."
        ),
        "postgres_integration": (
            "PostgreSQL integration tests are opt-in; set ENABLE_POSTGRES_TESTS=1 to run them."
        ),
        "evaluation": (
            "Evaluation tests are opt-in; set ENABLE_EVALUATION_TESTS=1 to run them."
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

        if "/evaluation/" in nodeid and not enabled_markers["evaluation"]:
            item.add_marker(pytest.mark.skip(reason=skip_messages["evaluation"]))
            continue

        for marker_name, enabled in enabled_markers.items():
            if not enabled and marker_name in item.keywords:
                item.add_marker(pytest.mark.skip(reason=skip_messages[marker_name]))


def build_canonical_app(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    monkeypatch.setenv(
        "SECURITY_SECRET_KEY",
        "test-secret-key-for-contract-checks-1234567890",
    )
    monkeypatch.setenv("MONITORING_METRICS_ENABLED", "false")

    from src.apps.api.dependencies import reset_knowledge_service
    from src.apps.api.health import reset_health_state
    from src.shared.infrastructure.config import settings as settings_module

    settings_module.reset_settings()
    reset_knowledge_service()
    reset_health_state()

    for module_name in ("src.apps.api.router", "src.apps.api.main"):
        sys.modules.pop(module_name, None)

    main_module = importlib.import_module("src.apps.api.main")
    return main_module.create_application()


@pytest.fixture
def canonical_app(monkeypatch: pytest.MonkeyPatch):
    try:
        return build_canonical_app(monkeypatch)
    except Exception as exc:
        pytest.fail(f"canonical app failed to build: {exc}")


@pytest.fixture
def canonical_client(canonical_app):
    with TestClient(canonical_app, raise_server_exceptions=False) as client:
        yield client
