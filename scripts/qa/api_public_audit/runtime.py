"""Runtime helpers for the public API audit."""

from __future__ import annotations

import importlib
import os
import sys
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from .models import RouteKey

PUBLIC_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def truncate_text(value: str, max_length: int = 400) -> str:
    clean = value.replace("\n", "\\n").replace("\r", "")
    if len(clean) <= max_length:
        return clean
    return f"{clean[: max_length - 3]}..."


def prepare_environment() -> None:
    os.environ.setdefault("APP_ENVIRONMENT", "testing")
    os.environ.setdefault(
        "SECURITY_SECRET_KEY",
        "test-secret-key-for-api-public-audit-1234567890",
    )
    os.environ.setdefault("MONITORING_METRICS_ENABLED", "false")
    os.environ.setdefault("LLM_PROVIDER", "mock")
    os.environ.setdefault("LOG_LEVEL", "WARNING")
    os.environ.setdefault("LOG_STRUCTURED", "false")


def reset_runtime_singletons() -> None:
    from src.apps.api.dependencies import (
        reset_identity_dependencies,
        reset_jwt_manager,
        reset_knowledge_service,
    )
    from src.apps.api.health import reset_health_state
    from src.apps.api.routes.workspaces import reset_workspace_jobs
    from src.apps.api.runtime import runtime_store
    from src.shared.infrastructure.config.settings import reset_settings

    reset_jwt_manager()
    reset_identity_dependencies()
    reset_knowledge_service()
    reset_health_state()
    reset_workspace_jobs()
    runtime_store.reset()
    reset_settings()


def build_canonical_client() -> tuple[TestClient, Any]:
    prepare_environment()
    reset_runtime_singletons()

    for module_name in ("src.apps.api.router", "src.apps.api.main"):
        sys.modules.pop(module_name, None)

    main_module = importlib.import_module("src.apps.api.main")
    app = main_module.create_application()
    return TestClient(app, raise_server_exceptions=False), app


def discover_public_routes(app: Any) -> list[RouteKey]:
    discovered: set[RouteKey] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not path or not methods:
            continue
        for method in methods:
            if method in PUBLIC_METHODS:
                discovered.add(RouteKey(method=method, path=path))
    return sorted(discovered, key=lambda item: (item.path, item.method))
