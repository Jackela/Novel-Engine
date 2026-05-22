from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

import scripts.uat.run_dashscope_longform_uat as longform_uat
from scripts.uat.run_dashscope_longform_uat import (
    ChapterAudit,
    EditorialFinding,
    LongformUatExecutionError,
    LongformUatFailureReport,
    LongformUatReport,
    RequestTrace,
    _resolve_output_paths,
    build_editorial_findings,
    render_failure_markdown_report,
    render_markdown_report,
    validate_report,
)


def _build_workspace_payload(chapter_count: int) -> dict[str, Any]:
    chapters = []
    for chapter_number in range(1, chapter_count + 1):
        chapters.append(
            {
                "chapter_number": chapter_number,
                "filename": f"chapter-{chapter_number:03d}.md",
                "word_count": 320,
                "summary": f"Summary {chapter_number}",
            }
        )

    return {
        "chapters": chapters,
    }


def _chapter_audit(count: int = 20) -> list[ChapterAudit]:
    return [
        ChapterAudit(
            chapter_number=chapter_number,
            title=f"chapter-{chapter_number:03d}.md",
            word_count=900,
            summary=f"Summary {chapter_number}",
        )
        for chapter_number in range(1, count + 1)
    ]


def _uat_report(**overrides: Any) -> LongformUatReport:
    payload: dict[str, Any] = {
        "started_at": "2026-01-01T00:00:00+00:00",
        "completed_at": "2026-01-01T00:10:00+00:00",
        "base_url": "http://127.0.0.1:8000",
        "principal_workspace_id": "user-operator",
        "workspace_id": "story-1",
        "story_title": "Story",
        "provider": "dashscope",
        "model": "qwen3.5-flash",
        "review_provider": "local",
        "review_model": "local-reviewer",
        "target_chapters": 20,
        "drafted_chapters": 20,
        "exported": True,
        "export_outcome": "exported",
        "export_failure_code": None,
        "export_path": "exports/manuscript.md",
        "warning_count": 0,
        "blocker_count": 0,
        "suggestion_count": 1,
        "review_rounds": 1,
        "export_gate_passed": True,
        "issue_codes": [],
        "run_ids": ["run-1"],
        "artifact_kinds": ["chapter_artifacts", "review", "export"],
        "editorial_notes": ["Markdown chapters are the manuscript authority."],
        "request_trace": [],
        "chapter_audit": _chapter_audit(),
        "editorial_findings": [],
    }
    payload.update(overrides)
    return LongformUatReport(**payload)


def test_build_editorial_findings_surfaces_review_issues_and_underlength_chapters() -> None:
    payload = _build_workspace_payload(20)
    chapters = cast(list[dict[str, Any]], payload["chapters"])
    chapters[2]["word_count"] = 2
    chapters[3]["summary"] = ""
    review = {
        "blockers": [
            {
                "code": "relationship_drift",
                "severity": "blocker",
                "location": "chapter-7",
                "message": "Chapter 7 breaks the established alliance trajectory.",
                "suggestion": "Restore the turning beat before release.",
            }
        ]
    }

    chapter_audit, findings = build_editorial_findings(payload, review, target_chapters=20)

    assert len(chapter_audit) == 20
    assert any(finding.area == "workspace review" for finding in findings)
    assert any(finding.area == "chapter density" for finding in findings)
    assert any(finding.area == "sidecar metadata" for finding in findings)


def test_validate_report_rejects_missing_chapter_coverage() -> None:
    report = _uat_report(
        drafted_chapters=19,
        exported=False,
        export_outcome="blocked",
        export_failure_code="EXPORT_FAILED",
        export_gate_passed=False,
        chapter_audit=[],
    )

    try:
        validate_report(report)
    except ValueError as exc:
        assert "Expected at least 20 drafted chapters" in str(exc)
    else:
        raise AssertionError("validate_report should reject missing chapter coverage")


def test_validate_report_rejects_blocked_export_outcome() -> None:
    report = _uat_report(
        exported=False,
        export_outcome="blocked",
        export_failure_code="EXPORT_FAILED",
        export_gate_passed=False,
    )

    try:
        validate_report(report)
    except ValueError as exc:
        assert "did not reach a successful export outcome" in str(exc)
    else:
        raise AssertionError("validate_report should reject blocked export outcomes")


def test_render_markdown_report_includes_editorial_findings_and_trace() -> None:
    report = _uat_report(
        issue_codes=["relationship_drift"],
        editorial_notes=["Keep a human line edit before release."],
        editorial_findings=[
            EditorialFinding(
                severity="critical",
                area="workspace review",
                chapter=7,
                summary="Alliance break lands without setup.",
                recommendation="Restore the missing setup beat.",
            )
        ],
    )

    markdown = render_markdown_report(report)

    assert "DashScope 20-Chapter Live Evidence" in markdown
    assert "Alliance break lands without setup." in markdown
    assert "Machine Evidence" in markdown


def test_render_failure_markdown_report_includes_error_and_trace() -> None:
    report = LongformUatFailureReport(
        started_at="2026-01-01T00:00:00+00:00",
        completed_at="2026-01-01T00:02:00+00:00",
        base_url="http://127.0.0.1:8000",
        target_chapters=20,
        story_title_seed="DashScope PR Gate",
        principal_workspace_id="user-operator",
        workspace_id="story-1",
        story_title="Story",
        failed_step="run_workspace",
        error_message="Workspace job failed.",
        request_trace=[
            RequestTrace(
                step="run_workspace",
                method="POST",
                path="/api/workspaces/story-1/jobs",
                status_code=202,
                duration_ms=4100,
            )
        ],
    )

    markdown = render_failure_markdown_report(report)

    assert "Failure Summary" in markdown
    assert "run_workspace" in markdown
    assert "Workspace job failed." in markdown


def test_validate_report_allows_unresolved_warnings() -> None:
    report = _uat_report(
        warning_count=1,
        blocker_count=0,
        issue_codes=["thin_chapter"],
    )

    validate_report(report)


def test_validate_report_rejects_unresolved_blockers() -> None:
    report = _uat_report(
        blocker_count=1,
        export_gate_passed=False,
        issue_codes=["empty_chapter"],
    )

    try:
        validate_report(report)
    except ValueError as exc:
        assert "unresolved review blockers" in str(exc)
    else:
        raise AssertionError("validate_report should reject blockers")


def test_resolve_output_paths_uses_artifact_dir_by_default(tmp_path: Path) -> None:
    markdown_path, json_path = _resolve_output_paths(
        output_dir=tmp_path,
        report_path=None,
        json_path=None,
        write_canonical_reports=False,
    )

    assert markdown_path == tmp_path / "LONGFORM_DASHSCOPE_LIVE_EVIDENCE.md"
    assert json_path == tmp_path / "LONGFORM_DASHSCOPE_LIVE_EVIDENCE.json"


def test_resolve_output_paths_uses_canonical_defaults_when_requested() -> None:
    markdown_path, json_path = _resolve_output_paths(
        output_dir=Path("ignored"),
        report_path=None,
        json_path=None,
        write_canonical_reports=True,
    )

    assert markdown_path.name == "LONGFORM_DASHSCOPE_LIVE_EVIDENCE.md"
    assert "docs" in markdown_path.parts
    assert json_path.name == "LONGFORM_DASHSCOPE_LIVE_EVIDENCE.json"
    assert "docs" in json_path.parts


def test_run_longform_uat_uses_workspace_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def workspace_payload(workspace_id: str) -> dict[str, Any]:
        return {
            "workspace_id": workspace_id,
            "chapters": [
                {
                    "chapter_number": 1,
                    "filename": "chapter-001.md",
                    "word_count": 420,
                    "summary": "Mira receives the ledger page.",
                },
                {
                    "chapter_number": 2,
                    "filename": "chapter-002.md",
                    "word_count": 430,
                    "summary": "The debt becomes public pressure.",
                },
            ],
            "latest_review": {
                "export_blocked": False,
                "blockers": [],
                "warnings": [
                    {
                        "code": "thin_chapter",
                        "severity": "warning",
                        "location": "chapter-001",
                        "message": "Chapter 1 is lean.",
                        "suggestion": "Expand the opening when editing.",
                    }
                ],
                "suggestions": [],
                "style_notes": ["Markdown chapters are the manuscript authority."],
            },
            "runs": [{"run_id": "run-1", "artifact_count": 6}],
            "exports": [
                {
                    "filename": "manuscript.md",
                    "artifact_id": "manuscript.md",
                    "relative_path": "exports/manuscript.md",
                }
            ],
        }

    def fake_request_json(
        session: Any,
        traces: list[RequestTrace],
        *,
        base_url: str,
        step: str,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        allowed_status_codes: tuple[int, ...] = (200,),
        timeout_seconds: int = 900,
    ) -> tuple[int, dict[str, Any]]:
        del session, base_url, headers, allowed_status_codes, timeout_seconds
        status_code = 201 if step == "create_workspace" else 202 if method == "POST" else 200
        traces.append(
            RequestTrace(
                step=step,
                method=method,
                path=path,
                status_code=status_code,
                duration_ms=25,
            )
        )
        if step == "login":
            return 200, {"workspace_id": "user-operator"}
        if step == "create_workspace":
            assert payload is not None
            return 201, {"workspace_id": str(payload["workspace_id"])}
        if step == "run_workspace":
            return 202, {"job_id": "run-job", "status": "completed"}
        if step == "poll_run_job":
            return 200, {"job_id": "run-job", "status": "completed"}
        if step == "export_workspace":
            return 202, {"job_id": "export-job", "status": "completed"}
        if step == "poll_export_job":
            return 200, {
                "job_id": "export-job",
                "status": "completed",
                "result": {
                    "result_type": "export",
                    "export": {
                        "artifact_id": "manuscript.md",
                        "filename": "manuscript.md",
                        "relative_path": "exports/manuscript.md",
                    }
                },
            }
        if step.startswith("get_workspace"):
            workspace_id = path.split("/workspaces/")[-1].split("/")[0]
            return 200, workspace_payload(workspace_id)
        raise AssertionError(f"Unexpected step: {step}")

    monkeypatch.setattr(longform_uat, "_request_json", fake_request_json)

    report = longform_uat.run_longform_uat(
        base_url="http://127.0.0.1:8000",
        target_chapters=2,
        story_title_seed="DashScope PR Gate",
        timeout_seconds=10,
    )

    assert report.exported is True
    assert report.warning_count == 1
    assert report.blocker_count == 0
    assert report.export_outcome == "exported"
    assert all(not trace.path.startswith("/api/" + "v") for trace in report.request_trace)
    assert any(
        trace.path.endswith("/jobs") and trace.step == "run_workspace"
        for trace in report.request_trace
    )


def test_run_longform_uat_wraps_failures_with_partial_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_request_json(
        session: Any,
        traces: list[RequestTrace],
        *,
        base_url: str,
        step: str,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        allowed_status_codes: tuple[int, ...] = (200,),
        timeout_seconds: int = 900,
    ) -> tuple[int, dict[str, Any]]:
        del session, base_url, headers, payload, allowed_status_codes, timeout_seconds
        if step == "login":
            traces.append(
                RequestTrace(
                    step=step,
                    method=method,
                    path=path,
                    status_code=200,
                    duration_ms=25,
                )
            )
            return 200, {"workspace_id": "user-operator"}

        traces.append(
            RequestTrace(
                step=step,
                method=method,
                path=path,
                status_code=500,
                duration_ms=55,
            )
        )
        raise RuntimeError("provider timeout")

    monkeypatch.setattr(longform_uat, "_request_json", fake_request_json)

    with pytest.raises(LongformUatExecutionError) as exc_info:
        longform_uat.run_longform_uat(
            base_url="http://127.0.0.1:8000",
            target_chapters=20,
            story_title_seed="DashScope PR Gate",
            timeout_seconds=10,
        )

    report = exc_info.value.report
    assert report.principal_workspace_id == "user-operator"
    assert report.workspace_id is not None
    assert report.workspace_id.startswith("dashscope-pr-gate")
    assert report.story_title is not None
    assert report.story_title.startswith("DashScope PR Gate")
    assert report.failed_step == "create_workspace"
    assert report.error_message == "provider timeout"
