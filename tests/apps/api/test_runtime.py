"""Tests for workspace-scoped canonical runtime behavior."""

# mypy: disable-error-code=misc

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.apps.api.services.runtime import CanonicalRuntimeService
from src.shared.infrastructure.config import settings as settings_module


def _build_runtime_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> CanonicalRuntimeService:
    monkeypatch.setenv("APP_ENVIRONMENT", "testing")
    monkeypatch.setenv(
        "SECURITY_SECRET_KEY",
        "test-secret-key-for-runtime-scoping-1234567890",
    )
    monkeypatch.setenv("MONITORING_METRICS_ENABLED", "false")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    settings_module.reset_settings()
    return CanonicalRuntimeService(base_dir=tmp_path)


@pytest.mark.asyncio
async def test_dashboard_status_reports_only_workspace_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _build_runtime_service(tmp_path, monkeypatch)

    await runtime.create_or_resume_guest_session("workspace-a")
    await runtime.start_orchestration(["aria"], total_turns=1, workspace_id="workspace-a")

    workspace_a_status = await runtime.get_dashboard_status("workspace-a")
    workspace_b_status = await runtime.get_dashboard_status("workspace-b")

    assert workspace_a_status["workspaceId"] == "workspace-a"
    assert workspace_a_status["activeSignals"] == len(workspace_a_status["recent_events"])
    assert workspace_a_status["activeSignals"] >= 1
    assert {event["workspace_id"] for event in workspace_a_status["recent_events"]} == {
        "workspace-a"
    }

    assert workspace_b_status["workspaceId"] == "workspace-b"
    assert workspace_b_status["activeSignals"] == 0
    assert workspace_b_status["recent_events"] == []

    await runtime.shutdown()


@pytest.mark.asyncio
async def test_subscribers_receive_only_their_workspace_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _build_runtime_service(tmp_path, monkeypatch)

    subscriber_a = await runtime.register_subscriber("workspace-a")
    subscriber_b = await runtime.register_subscriber("workspace-b")

    await runtime.start_orchestration(["aria"], total_turns=1, workspace_id="workspace-a")

    event_a = await asyncio.wait_for(subscriber_a.get(), timeout=1)
    assert event_a["workspace_id"] == "workspace-a"

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(subscriber_b.get(), timeout=0.1)

    runtime.unregister_subscriber("workspace-a", subscriber_a)
    runtime.unregister_subscriber("workspace-b", subscriber_b)
    await runtime.shutdown()


@pytest.mark.asyncio
async def test_runtime_events_use_unique_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _build_runtime_service(tmp_path, monkeypatch)

    event_a = runtime._build_event(
        workspace_id="workspace-a",
        event_type="system",
        title="Heartbeat",
        description="Dashboard connection is alive",
        data={},
    )
    event_b = runtime._build_event(
        workspace_id="workspace-a",
        event_type="system",
        title="Heartbeat",
        description="Dashboard connection is alive",
        data={},
    )

    assert event_a["id"].startswith("event-")
    assert event_a["id"] != event_b["id"]

    await runtime.shutdown()
