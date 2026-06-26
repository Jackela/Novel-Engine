from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.apps.api.runtime import create_runtime
from src.contexts.ai.infrastructure.providers.dashscope_text_generation_provider import (
    DashScopeTextGenerationProvider,
)
from src.shared.infrastructure.config.settings import (
    DatabaseSettings,
    LLMSettings,
    NovelEngineSettings,
    reset_settings,
)


def test_web_import_uses_app_owned_data_dir_after_global_settings_change(
    canonical_app: FastAPI,
    canonical_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    canonical_client.post(
        "/api/setup",
        json={"username": "owner", "password": "owner-password-123"},
    )
    canonical_client.post(
        "/api/session/login",
        json={"username": "owner", "password": "owner-password-123"},
    )
    app_settings = canonical_app.state.settings
    workspace = app_settings.data_dir / "imports" / "app-owned-workspace"
    workspace.mkdir(parents=True)
    (workspace / "story.yaml").write_text("title: App-owned import\n", encoding="utf-8")
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path / "global-data"))
    reset_settings()

    preview = canonical_client.post(
        "/api/imports/preview",
        json={"source": workspace.name},
    )

    assert preview.status_code == 200
    assert preview.json()["title"] == "App-owned import"


def test_runtime_provider_factory_uses_explicit_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    reset_settings()
    settings = NovelEngineSettings(
        environment="testing",
        data_dir=tmp_path,
        database=DatabaseSettings(url=f"sqlite:///{tmp_path / 'studio.sqlite3'}"),
        llm=LLMSettings(
            provider="dashscope",
            DASHSCOPE_API_KEY="explicit-dashscope-key",
            DASHSCOPE_MODEL="explicit-model",
        ),
    )
    runtime = create_runtime(settings)

    try:
        provider = runtime.store.ai_service._ai_provider_factory(
            "dashscope", "explicit-model"
        )
    finally:
        runtime.database.dispose()

    assert isinstance(provider, DashScopeTextGenerationProvider)


def test_ai_proposal_route_uses_app_owned_model_after_global_settings_change(
    canonical_app: FastAPI,
    canonical_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    canonical_client.post("/api/session/guest")
    project = canonical_client.post(
        "/api/projects", json={"title": "Settings-owned AI"}
    ).json()
    document = project["documents"][0]
    app_model = canonical_app.state.settings.llm.resolved_model("mock")
    monkeypatch.setenv("LLM_MODEL", "global-model-after-app-start")
    reset_settings()

    proposal = canonical_client.post(
        f"/api/projects/{project['id']}/documents/{document['id']}/ai-proposals",
        json={
            "operation": "continue",
            "instruction": "Continue from here.",
            "provider": "mock",
        },
    )

    assert proposal.status_code == 200
    assert proposal.json()["model"] == app_model

    providers = canonical_client.get("/api/providers")
    assert providers.status_code == 200
    mock_provider = next(
        item for item in providers.json()["providers"] if item["provider"] == "mock"
    )
    assert mock_provider["model"] == app_model
