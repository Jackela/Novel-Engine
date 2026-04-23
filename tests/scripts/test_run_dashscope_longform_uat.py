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


def _build_export_payload(chapter_count: int) -> dict[str, Any]:
    chapters = []
    outline_chapters = []
    for chapter_number in range(1, chapter_count + 1):
        chapters.append(
            {
                "chapter_number": chapter_number,
                "title": f"Chapter {chapter_number}",
                "scenes": [
                    {
                        "content": " ".join(["serial"] * 320),
                    }
                ],
            }
        )
        outline_chapters.append(
            {
                "chapter_number": chapter_number,
                "hook": f"Hook {chapter_number}",
            }
        )

    return {
        "story": {
            "chapters": chapters,
        },
        "outline": {
            "chapters": outline_chapters,
        },
    }


def test_build_editorial_findings_surfaces_review_issues_and_underlength_chapters() -> None:
    payload = _build_export_payload(20)
    story = cast(dict[str, Any], payload["story"])
    outline = cast(dict[str, Any], payload["outline"])
    story["chapters"][2]["scenes"][0]["content"] = "too short"
    outline["chapters"][3]["hook"] = ""
    review = {
        "issues": [
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
    assert any(finding.area == "system review" for finding in findings)
    assert any(finding.area == "chapter density" for finding in findings)
    assert any(finding.area == "hook architecture" for finding in findings)


def test_validate_report_rejects_missing_chapter_coverage() -> None:
    report = LongformUatReport(
        started_at="2026-01-01T00:00:00+00:00",
        completed_at="2026-01-01T00:10:00+00:00",
        base_url="http://127.0.0.1:8000",
        story_id="story-1",
        workspace_id="user-operator",
        story_title="Story",
        provider="dashscope",
        model="qwen3.5-flash",
        review_provider="dashscope",
        review_model="qwen3.5-flash",
        target_chapters=20,
        drafted_chapters=19,
        published=False,
        publish_outcome="blocked",
        publish_failure_code="QUALITY_GATE_FAILED",
        warning_count=1,
        blocker_count=0,
        review_rounds=1,
        revision_rounds=0,
        quality_score=86,
        continuity_score=88,
        pacing_score=83,
        reader_pull_score=82,
        plot_clarity_score=80,
        ooc_risk_score=12,
        structural_gate_passed=False,
        semantic_gate_passed=True,
        publish_gate_passed=False,
        issue_codes=["quality_gate_failed"],
        run_ids=[],
        artifact_kinds=[],
        revision_notes=[],
        request_trace=[],
        chapter_audit=[],
        editorial_findings=[],
    )

    try:
        validate_report(report)
    except ValueError as exc:
        assert "Expected at least 20 drafted chapters" in str(exc)
    else:
        raise AssertionError("validate_report should reject missing chapter coverage")


def test_validate_report_rejects_blocked_publish_outcome() -> None:
    report = LongformUatReport(
        started_at="2026-01-01T00:00:00+00:00",
        completed_at="2026-01-01T00:10:00+00:00",
        base_url="http://127.0.0.1:8000",
        story_id="story-1",
        workspace_id="user-operator",
        story_title="Story",
        provider="dashscope",
        model="qwen3.5-flash",
        review_provider="dashscope",
        review_model="qwen3.5-flash",
        target_chapters=20,
        drafted_chapters=20,
        published=False,
        publish_outcome="blocked",
        publish_failure_code="QUALITY_GATE_FAILED",
        warning_count=0,
        blocker_count=0,
        review_rounds=2,
        revision_rounds=1,
        quality_score=86,
        continuity_score=88,
        pacing_score=83,
        reader_pull_score=82,
        plot_clarity_score=80,
        ooc_risk_score=12,
        structural_gate_passed=False,
        semantic_gate_passed=True,
        publish_gate_passed=False,
        issue_codes=["quality_gate_failed"],
        run_ids=[],
        artifact_kinds=[],
        revision_notes=[],
        request_trace=[],
        chapter_audit=[
            ChapterAudit(
                chapter_number=chapter_number,
                title=f"Chapter {chapter_number}",
                scenes=3,
                word_count=900,
                hook=f"Hook {chapter_number}",
            )
            for chapter_number in range(1, 21)
        ],
        editorial_findings=[],
    )

    try:
        validate_report(report)
    except ValueError as exc:
        assert "did not reach a successful publish outcome" in str(exc)
    else:
        raise AssertionError("validate_report should reject blocked publish outcomes")


def test_render_markdown_report_includes_editorial_findings_and_trace() -> None:
    report = LongformUatReport(
        started_at="2026-01-01T00:00:00+00:00",
        completed_at="2026-01-01T00:10:00+00:00",
        base_url="http://127.0.0.1:8000",
        story_id="story-1",
        workspace_id="user-operator",
        story_title="Story",
        provider="dashscope",
        model="qwen3.5-flash",
        review_provider="dashscope",
        review_model="qwen3.5-flash",
        target_chapters=20,
        drafted_chapters=20,
        published=True,
        publish_outcome="published",
        publish_failure_code=None,
        warning_count=0,
        blocker_count=0,
        review_rounds=2,
        revision_rounds=1,
        quality_score=86,
        continuity_score=88,
        pacing_score=83,
        reader_pull_score=82,
        plot_clarity_score=80,
        ooc_risk_score=12,
        structural_gate_passed=True,
        semantic_gate_passed=True,
        publish_gate_passed=True,
        issue_codes=["relationship_drift"],
        run_ids=["run-1"],
        artifact_kinds=["outline", "review"],
        revision_notes=["Repair chapter 7."],
        request_trace=[],
        chapter_audit=[
            ChapterAudit(
                chapter_number=1,
                title="Chapter 1",
                scenes=3,
                word_count=900,
                hook="A better hook",
            )
        ]
        * 20,
        editorial_findings=[
            EditorialFinding(
                severity="critical",
                area="system review",
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
        story_id="story-1",
        workspace_id="user-operator",
        story_title="Story",
        failed_step="review_story_round_2",
        error_message="Long-form UAT exhausted the editorial closure loop.",
        request_trace=[
            RequestTrace(
                step="review_story_round_2",
                method="POST",
                path="/api/v1/story/story-1/review",
                status_code=200,
                duration_ms=4100,
            )
        ],
    )

    markdown = render_failure_markdown_report(report)

    assert "Failure Summary" in markdown
    assert "review_story_round_2" in markdown
    assert "Long-form UAT exhausted the editorial closure loop." in markdown


def test_validate_report_rejects_unresolved_warnings() -> None:
    report = LongformUatReport(
        started_at="2026-01-01T00:00:00+00:00",
        completed_at="2026-01-01T00:10:00+00:00",
        base_url="http://127.0.0.1:8000",
        story_id="story-1",
        workspace_id="user-operator",
        story_title="Story",
        provider="dashscope",
        model="qwen3.5-flash",
        review_provider="dashscope",
        review_model="qwen3.5-flash",
        target_chapters=20,
        drafted_chapters=20,
        published=True,
        publish_outcome="published",
        publish_failure_code=None,
        warning_count=1,
        blocker_count=0,
        review_rounds=3,
        revision_rounds=2,
        quality_score=90,
        continuity_score=92,
        pacing_score=90,
        reader_pull_score=91,
        plot_clarity_score=88,
        ooc_risk_score=10,
        structural_gate_passed=True,
        semantic_gate_passed=True,
        publish_gate_passed=False,
        issue_codes=["late_arc_fallout"],
        run_ids=["run-1"],
        artifact_kinds=["outline", "review", "export"],
        revision_notes=["Expand the political fallout in Chapter 19."],
        request_trace=[],
        chapter_audit=[
            ChapterAudit(
                chapter_number=chapter_number,
                title=f"Chapter {chapter_number}",
                scenes=3,
                word_count=900,
                hook=f"Hook {chapter_number}",
            )
            for chapter_number in range(1, 21)
        ],
        editorial_findings=[],
    )

    try:
        validate_report(report)
    except ValueError as exc:
        assert "unresolved review warnings or blockers" in str(exc)
    else:
        raise AssertionError("validate_report should reject zero-warning failures")


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
            return 200, {"access_token": "token", "workspace_id": "user-operator"}

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
    assert report.workspace_id == "user-operator"
    assert report.story_title is not None
    assert report.story_title.startswith("DashScope PR Gate")
    assert report.failed_step == "create_story"
    assert report.error_message == "provider timeout"
