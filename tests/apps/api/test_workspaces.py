"""Tests for the local-first workspace API."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, cast

from src.shared.infrastructure.config.settings import get_settings

TERMINAL_JOB_STATUSES = {"completed", "failed", "interrupted"}


def _start_guest(canonical_client: Any, workspace_id: str | None = None) -> str:
    payload = {"workspace_id": workspace_id} if workspace_id else None
    response = canonical_client.post("/api/guest/session", json=payload)
    assert response.status_code == 200
    return str(response.json()["workspace_id"])


def _workspace_root(guest_workspace_id: str, workspace_id: str) -> Path:
    return (
        get_settings().data_dir
        / "novel-workspaces"
        / guest_workspace_id
        / workspace_id
    ).resolve()


def _create_workspace(
    canonical_client: Any,
    workspace_id: str = "salt-ledger",
    *,
    force: bool = False,
    title: str = "The Salt Ledger",
) -> dict[str, Any]:
    response = canonical_client.post(
        "/api/workspaces",
        json={
            "workspace_id": workspace_id,
            "title": title,
            "genre": "mystery",
            "premise": "A courier receives a page that names debts before they happen.",
            "target_chapters": 3,
            "tone": "sharp, atmospheric serial fiction",
            "force": force,
        },
    )
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def _wait_for_job(
    canonical_client: Any,
    workspace_id: str,
    job_id: str,
) -> dict[str, Any]:
    for _ in range(100):
        response = canonical_client.get(
            f"/api/workspaces/{workspace_id}/jobs/{job_id}"
        )
        assert response.status_code == 200
        job = cast(dict[str, Any], response.json())
        if job["status"] in TERMINAL_JOB_STATUSES:
            return job
        time.sleep(0.01)
    raise AssertionError(f"job {job_id} did not reach a terminal status")


def _assert_no_private_payload(
    payload: object,
    *,
    forbidden_strings: tuple[str, ...] = (),
) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert key not in {"raw_model_output", "chapter_markdown", "chapter_file"}
            _assert_no_private_payload(value, forbidden_strings=forbidden_strings)
        return
    if isinstance(payload, list):
        for item in payload:
            _assert_no_private_payload(item, forbidden_strings=forbidden_strings)
        return
    if isinstance(payload, str):
        normalized_payload = payload.replace("\\", "/")
        for forbidden in forbidden_strings:
            assert forbidden.replace("\\", "/") not in normalized_payload


def test_workspace_create_list_and_status(canonical_client: Any) -> None:
    _start_guest(canonical_client)
    created = _create_workspace(canonical_client)

    assert created["workspace_id"] == "salt-ledger"
    assert "root" not in created
    assert created["story"]["title"] == "The Salt Ledger"
    assert created["chapters"] == []

    list_response = canonical_client.get("/api/workspaces")
    assert list_response.status_code == 200
    workspaces = list_response.json()["workspaces"]
    assert [workspace["workspace_id"] for workspace in workspaces] == ["salt-ledger"]
    assert "root" not in workspaces[0]

    status_response = canonical_client.get("/api/workspaces/salt-ledger")
    assert status_response.status_code == 200
    assert status_response.json()["workspace_id"] == created["workspace_id"]


def test_provider_discovery_defaults_to_mock_when_unconfigured(
    canonical_client: Any,
) -> None:
    response = canonical_client.get("/api/providers")

    assert response.status_code == 200
    payload = response.json()
    assert payload["default_provider"] in {"mock", "dashscope", "openai_compatible"}
    providers = {item["provider"]: item for item in payload["providers"]}
    assert providers["mock"]["configured"] is True
    assert providers["mock"]["label"] == "mock offline demo"
    assert providers[payload["default_provider"]]["configured"] is True


def test_run_job_drafts_reviews_and_can_be_polled(canonical_client: Any) -> None:
    guest_workspace_id = _start_guest(canonical_client)
    _create_workspace(canonical_client)
    workspace_root = _workspace_root(guest_workspace_id, "salt-ledger")

    job_response = canonical_client.post(
        "/api/workspaces/salt-ledger/jobs",
        json={"operation": "run", "target_chapters": 3, "provider": "mock"},
    )
    assert job_response.status_code == 202
    job = job_response.json()
    assert job["status"] in {"queued", "running", "completed"}
    assert job["provider"] == "mock"

    completed = _wait_for_job(canonical_client, "salt-ledger", str(job["job_id"]))
    assert completed["status"] == "completed"
    assert completed["result"]["result_type"] == "run"
    assert completed["result"]["review"]["export_blocked"] is False
    _assert_no_private_payload(
        completed,
        forbidden_strings=(str(workspace_root), str(get_settings().data_dir)),
    )

    status_response = canonical_client.get("/api/workspaces/salt-ledger")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    _assert_no_private_payload(
        status_payload,
        forbidden_strings=(str(workspace_root), str(get_settings().data_dir)),
    )
    assert len(status_payload["chapters"]) == 3
    for chapter in status_payload["chapters"]:
        assert "path" not in chapter
        assert chapter["relative_path"].startswith("manuscript/chapters/")
        assert chapter["artifact_id"] == chapter["filename"]
    assert status_payload["latest_review"]["export_blocked"] is False
    assert status_payload["runs"][0]["last_event"]["operation"] == "run"
    assert "path" not in status_payload["runs"][0]
    first_run_event_details = status_payload["runs"][0]["events"][1]["details"]
    assert "chapter_relative_path" in first_run_event_details
    assert "chapter_file" not in first_run_event_details
    suggestion_details = status_payload["latest_review"]["suggestions"][0]["details"]
    assert suggestion_details["evidence"]


def test_draft_job_result_uses_safe_artifact_reference(canonical_client: Any) -> None:
    guest_workspace_id = _start_guest(canonical_client)
    _create_workspace(canonical_client)
    workspace_root = _workspace_root(guest_workspace_id, "salt-ledger")

    response = canonical_client.post(
        "/api/workspaces/salt-ledger/jobs",
        json={"operation": "draft", "chapter": 1, "provider": "mock"},
    )

    assert response.status_code == 202
    job = _wait_for_job(canonical_client, "salt-ledger", str(response.json()["job_id"]))
    assert job["status"] == "completed"
    assert job["result"]["result_type"] == "artifact"
    assert job["result"]["chapter_number"] == 1
    assert job["result"]["artifact"]["relative_path"].startswith("artifacts/runs/")
    assert job["result"]["sidecar"]["summary"]
    _assert_no_private_payload(
        job,
        forbidden_strings=(str(workspace_root), str(get_settings().data_dir)),
    )


def test_review_warning_does_not_block_export(canonical_client: Any) -> None:
    guest_workspace_id = _start_guest(canonical_client)
    _create_workspace(canonical_client)
    chapter_dir = _workspace_root(guest_workspace_id, "salt-ledger") / "manuscript" / "chapters"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "chapter-001.md").write_text(
        "# Chapter 1: A Thin Opening\n\nA debt arrives early.",
        encoding="utf-8",
    )

    export_response = canonical_client.post(
        "/api/workspaces/salt-ledger/jobs",
        json={"operation": "export"},
    )
    assert export_response.status_code == 202
    queued = export_response.json()
    job = _wait_for_job(canonical_client, "salt-ledger", str(queued["job_id"]))
    assert job["status"] == "completed"
    assert job["result"]["result_type"] == "export"
    assert job["result"]["export"]["filename"] == "manuscript.md"
    assert "path" not in job["result"]["export"]

    status_response = canonical_client.get("/api/workspaces/salt-ledger")
    assert status_response.status_code == 200
    payload = status_response.json()
    review = payload["latest_review"]
    assert review["export_blocked"] is False
    assert [issue["code"] for issue in review["warnings"]] == ["thin_chapter"]
    assert payload["exports"][0]["relative_path"] == "exports/manuscript.md"


def test_empty_chapter_blocks_export(canonical_client: Any) -> None:
    guest_workspace_id = _start_guest(canonical_client)
    _create_workspace(canonical_client)
    chapter_dir = _workspace_root(guest_workspace_id, "salt-ledger") / "manuscript" / "chapters"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "chapter-001.md").write_text("", encoding="utf-8")

    export_response = canonical_client.post(
        "/api/workspaces/salt-ledger/jobs",
        json={"operation": "export"},
    )
    assert export_response.status_code == 202
    queued = export_response.json()
    job = _wait_for_job(canonical_client, "salt-ledger", str(queued["job_id"]))
    assert job["status"] == "failed"
    assert "empty_chapter" in job["error"]


def test_force_workspace_create_clears_existing_contents(canonical_client: Any) -> None:
    guest_workspace_id = _start_guest(canonical_client)
    _create_workspace(canonical_client)
    workspace_root = _workspace_root(guest_workspace_id, "salt-ledger")
    stale_chapter = workspace_root / "manuscript" / "chapters" / "chapter-001.md"
    stale_chapter.parent.mkdir(parents=True, exist_ok=True)
    stale_chapter.write_text("stale chapter", encoding="utf-8")
    stale_unknown = workspace_root / "unexpected.txt"
    stale_unknown.write_text("stale unknown file", encoding="utf-8")

    recreated = _create_workspace(
        canonical_client,
        force=True,
        title="The Fresh Ledger",
    )

    assert recreated["story"]["title"] == "The Fresh Ledger"
    assert not stale_chapter.exists()
    assert not stale_unknown.exists()


def test_jobs_are_scoped_to_active_guest_principal(
    canonical_app: Any,
    canonical_client: Any,
) -> None:
    guest_a = _start_guest(canonical_client)
    _create_workspace(canonical_client)
    job_response = canonical_client.post(
        "/api/workspaces/salt-ledger/jobs",
        json={"operation": "review"},
    )
    assert job_response.status_code == 202
    job_id = str(job_response.json()["job_id"])
    _wait_for_job(canonical_client, "salt-ledger", job_id)

    from fastapi.testclient import TestClient

    with TestClient(canonical_app, raise_server_exceptions=False) as second_client:
        guest_b = _start_guest(second_client)
        assert guest_b != guest_a
        _create_workspace(second_client)
        foreign_poll = second_client.get(
            f"/api/workspaces/salt-ledger/jobs/{job_id}"
        )
        assert foreign_poll.status_code == 404


def test_restart_marks_unfinished_job_interrupted(canonical_client: Any) -> None:
    guest_workspace_id = _start_guest(canonical_client)
    _create_workspace(canonical_client)
    workspace_root = _workspace_root(guest_workspace_id, "salt-ledger")
    jobs_dir = workspace_root / "artifacts" / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    job_path = jobs_dir / "job-stale.json"
    job_path.write_text(
        json.dumps(
            {
                "job_id": "job-stale",
                "principal_key": f"guest:{guest_workspace_id}",
                "workspace_id": "salt-ledger",
                "operation": "run",
                "status": "running",
                "created_at": "2026-05-19T00:00:00+00:00",
                "updated_at": "2026-05-19T00:00:00+00:00",
                "provider": "mock",
                "result": None,
                "error": None,
                "events": [
                    {
                        "timestamp": "2026-05-19T00:00:00+00:00",
                        "status": "running",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    status_response = canonical_client.get("/api/workspaces/salt-ledger")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    stale_jobs = [
        job for job in status_payload["jobs"] if job["job_id"] == "job-stale"
    ]
    assert stale_jobs
    assert stale_jobs[0]["status"] == "interrupted"

    persisted = json.loads(job_path.read_text(encoding="utf-8"))
    assert persisted["status"] == "interrupted"
    assert persisted["events"][-1]["status"] == "interrupted"
    assert persisted["events"][-1]["details"]["reason"] == "process_restart"

    poll_response = canonical_client.get(
        "/api/workspaces/salt-ledger/jobs/job-stale"
    )

    assert poll_response.status_code == 200
    payload = poll_response.json()
    assert payload["status"] == "interrupted"
    assert payload["error"] == "Job was interrupted before completion."


def test_explicit_unconfigured_real_provider_is_rejected(
    canonical_client: Any,
    monkeypatch: Any,
) -> None:
    guest_workspace_id = _start_guest(canonical_client)
    _create_workspace(canonical_client)
    chapter_dir = _workspace_root(guest_workspace_id, "salt-ledger") / "manuscript" / "chapters"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "chapter-001.md").write_text(
        "# Chapter 1: A Reviewable Opening\n\n"
        "Mira kept the page because the debt named her brother before the city did. "
        "Tomas watched the rain gather in the rail grooves and chose not to warn "
        "the clerk waiting at the end of the platform.",
        encoding="utf-8",
    )

    import src.apps.api.routes.workspaces as workspace_routes

    monkeypatch.setattr(workspace_routes, "_provider_is_configured", lambda _: False)

    response = canonical_client.post(
        "/api/workspaces/salt-ledger/jobs",
        json={"operation": "review", "provider": "dashscope"},
    )
    assert response.status_code == 422
    assert "Provider is not configured" in response.json()["error"]["message"]


def test_configured_real_provider_review_failure_fails_job(
    canonical_client: Any,
    monkeypatch: Any,
) -> None:
    guest_workspace_id = _start_guest(canonical_client)
    _create_workspace(canonical_client)
    chapter_dir = _workspace_root(guest_workspace_id, "salt-ledger") / "manuscript" / "chapters"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "chapter-001.md").write_text(
        "# Chapter 1: A Reviewable Opening\n\n"
        "Mira kept the page because the debt named her brother before the city did. "
        "Tomas watched the rain gather in the rail grooves and chose not to warn "
        "the clerk waiting at the end of the platform.",
        encoding="utf-8",
    )

    import src.apps.api.routes.workspaces as workspace_routes

    class BrokenReviewProvider:
        async def generate_structured(self, task: object) -> object:
            del task
            raise RuntimeError(f"judge failed under {get_settings().data_dir}")

    monkeypatch.setattr(
        workspace_routes,
        "_provider_is_configured",
        lambda provider: provider in {"mock", "dashscope"},
    )
    monkeypatch.setattr(
        workspace_routes,
        "_build_review_provider",
        lambda provider: BrokenReviewProvider(),
    )

    response = canonical_client.post(
        "/api/workspaces/salt-ledger/jobs",
        json={"operation": "review", "provider": "dashscope"},
    )

    assert response.status_code == 202
    job = _wait_for_job(canonical_client, "salt-ledger", str(response.json()["job_id"]))
    assert job["status"] == "failed"
    assert "judge failed under" in job["error"]
    assert str(get_settings().data_dir).replace("\\", "/") not in job["error"].replace("\\", "/")
    assert job["failure_artifact"]["relative_path"].startswith("artifacts/jobs/")


def test_export_preserves_existing_editorial_review(canonical_client: Any) -> None:
    guest_workspace_id = _start_guest(canonical_client)
    _create_workspace(canonical_client)
    chapter_dir = _workspace_root(guest_workspace_id, "salt-ledger") / "manuscript" / "chapters"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    (chapter_dir / "chapter-001.md").write_text(
        "# Chapter 1: A Reviewable Opening\n\n"
        "Mira kept the page because the debt named her brother before the city did. "
        "Tomas watched the rain gather in the rail grooves and chose not to warn "
        "the clerk waiting at the end of the platform.",
        encoding="utf-8",
    )

    review_response = canonical_client.post(
        "/api/workspaces/salt-ledger/jobs",
        json={"operation": "review", "provider": "mock"},
    )
    assert review_response.status_code == 202
    review_job = _wait_for_job(
        canonical_client,
        "salt-ledger",
        str(review_response.json()["job_id"]),
    )
    assert review_job["status"] == "completed"
    assert review_job["result"]["result_type"] == "review"

    review_path = (
        _workspace_root(guest_workspace_id, "salt-ledger")
        / "artifacts"
        / "reviews"
        / "latest.json"
    )
    before_export = review_path.read_text(encoding="utf-8")

    export_response = canonical_client.post(
        "/api/workspaces/salt-ledger/jobs",
        json={"operation": "export"},
    )
    assert export_response.status_code == 202
    export_job = _wait_for_job(
        canonical_client,
        "salt-ledger",
        str(export_response.json()["job_id"]),
    )

    assert export_job["status"] == "completed"
    assert export_job["result"]["result_type"] == "export"
    assert review_path.read_text(encoding="utf-8") == before_export


def test_failed_job_records_failure_artifact(canonical_client: Any) -> None:
    guest_workspace_id = _start_guest(canonical_client)
    _create_workspace(canonical_client)

    response = canonical_client.post(
        "/api/workspaces/salt-ledger/jobs",
        json={"operation": "export"},
    )
    assert response.status_code == 202
    job = _wait_for_job(canonical_client, "salt-ledger", str(response.json()["job_id"]))

    assert job["status"] == "failed"
    assert "missing_manuscript" in job["error"]
    failure = job["failure_artifact"]
    assert failure["relative_path"].startswith("artifacts/jobs/")
    assert "path" not in failure
    failure_path = _workspace_root(guest_workspace_id, "salt-ledger") / failure["relative_path"]
    payload = json.loads(failure_path.read_text(encoding="utf-8"))
    assert payload["operation"] == "export"
    assert payload["provider"] == job["provider"]
    assert payload["traceback"]


def test_workspace_id_rejects_path_traversal(canonical_client: Any) -> None:
    _start_guest(canonical_client)
    response = canonical_client.post(
        "/api/workspaces",
        json={
            "workspace_id": "../escape",
            "title": "Bad Path",
            "genre": "mystery",
            "premise": "A writer tries to escape the workspace root.",
        },
    )

    assert response.status_code == 422
