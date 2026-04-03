"""Run a DashScope-backed long-form UAT through the real HTTP API."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.shared.infrastructure.config.settings import NovelEngineSettings

DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "uat" / "LONGFORM_DASHSCOPE_LIVE_EVIDENCE.md"
DEFAULT_JSON_PATH = REPO_ROOT / "docs" / "reports" / "uat" / "LONGFORM_DASHSCOPE_LIVE_EVIDENCE.json"
DEFAULT_TIMEOUT_SECONDS = 900
DEFAULT_STORY_TITLE = "DashScope Longform UAT"
DEFAULT_PREMISE = (
    "A debt archivist discovers that every erased oath becomes a living ghost, "
    "and must rebuild a city's memory before its rulers vanish from history."
)
DEFAULT_THEMES = ["memory", "serial escalation", "political debt", "inheritance"]
DEFAULT_TONE = "commercial web fiction"
DEFAULT_GENRE = "fantasy"
DEFAULT_AUDIENCE = "serial web fiction readers"
DEFAULT_LOGIN_EMAIL = "operator@novel.engine"
DEFAULT_LOGIN_PASSWORD = "demo-password"


@dataclass
class RequestTrace:
    step: str
    method: str
    path: str
    status_code: int
    duration_ms: int


@dataclass
class ChapterAudit:
    chapter_number: int
    title: str
    scenes: int
    word_count: int
    hook: str


@dataclass
class EditorialFinding:
    severity: str
    area: str
    chapter: int | None
    summary: str
    recommendation: str


@dataclass
class LongformUatReport:
    started_at: str
    completed_at: str
    base_url: str
    story_id: str
    workspace_id: str
    story_title: str
    provider: str
    model: str
    review_provider: str
    review_model: str
    target_chapters: int
    drafted_chapters: int
    published: bool
    publish_outcome: str
    publish_failure_code: str | None
    quality_score: int
    continuity_score: int
    pacing_score: int
    reader_pull_score: int
    plot_clarity_score: int
    ooc_risk_score: int
    structural_gate_passed: bool
    semantic_gate_passed: bool
    publish_gate_passed: bool
    issue_codes: list[str]
    run_ids: list[str]
    artifact_kinds: list[str]
    revision_notes: list[str]
    request_trace: list[RequestTrace]
    chapter_audit: list[ChapterAudit]
    editorial_findings: list[EditorialFinding]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def _chapter_word_count(chapter: dict[str, Any]) -> int:
    words = 0
    for scene in chapter.get("scenes", []):
        content = str(scene.get("content", "")).strip()
        if content:
            words += len(content.split())
    return words


def build_editorial_findings(
    export_payload: dict[str, Any],
    review_report: dict[str, Any],
    *,
    target_chapters: int,
) -> tuple[list[ChapterAudit], list[EditorialFinding]]:
    story = export_payload["story"]
    outline = export_payload.get("outline") or {}
    outline_by_chapter = {
        int(chapter.get("chapter_number", 0)): str(chapter.get("hook", "")).strip()
        for chapter in outline.get("chapters", [])
        if isinstance(chapter, dict)
    }
    chapters = story.get("chapters", [])
    chapter_audit = [
        ChapterAudit(
            chapter_number=int(chapter.get("chapter_number", 0)),
            title=str(chapter.get("title", "")),
            scenes=len(chapter.get("scenes", [])),
            word_count=_chapter_word_count(chapter),
            hook=outline_by_chapter.get(int(chapter.get("chapter_number", 0)), ""),
        )
        for chapter in chapters
        if isinstance(chapter, dict)
    ]

    findings: list[EditorialFinding] = []
    for issue in review_report.get("issues", []):
        if not isinstance(issue, dict):
            continue
        severity = "critical" if issue.get("severity") == "blocker" else "warning"
        location = issue.get("location")
        issue_chapter: int | None = None
        if isinstance(location, str) and "chapter-" in location:
            tail = location.split("chapter-")[-1]
            if tail.isdigit():
                issue_chapter = int(tail)
        findings.append(
            EditorialFinding(
                severity=severity,
                area="system review",
                chapter=issue_chapter,
                summary=str(issue.get("message", "")).strip() or str(issue.get("code", "issue")),
                recommendation=str(issue.get("suggestion", "")).strip()
                or "Revise the affected chapter before release.",
            )
        )

    underlength_chapters = [chapter for chapter in chapter_audit if chapter.word_count < 250]
    for chapter in underlength_chapters[:5]:
        findings.append(
            EditorialFinding(
                severity="warning",
                area="chapter density",
                chapter=chapter.chapter_number,
                summary=(
                    f"Chapter {chapter.chapter_number} lands at {chapter.word_count} words, "
                    "which is too thin for a release-grade serial chapter."
                ),
                recommendation="Expand scene work, conflict turns, and hook delivery.",
            )
        )

    chapters_missing_hooks = [chapter for chapter in chapter_audit if not chapter.hook]
    for chapter in chapters_missing_hooks[:5]:
        findings.append(
            EditorialFinding(
                severity="warning",
                area="hook architecture",
                chapter=chapter.chapter_number,
                summary=f"Chapter {chapter.chapter_number} is missing an explicit outline hook.",
                recommendation="Add a sharper exit hook to sustain serial pull.",
            )
        )

    if len(chapter_audit) < target_chapters:
        findings.append(
            EditorialFinding(
                severity="critical",
                area="delivery",
                chapter=None,
                summary=(
                    f"The manuscript stopped at {len(chapter_audit)} chapters and missed the "
                    f"{target_chapters}-chapter target."
                ),
                recommendation="Re-run drafting until the configured chapter target is met.",
            )
        )

    if not findings:
        findings.append(
            EditorialFinding(
                severity="info",
                area="editorial verdict",
                chapter=None,
                summary="No release-blocking editorial defects were detected from the exported manuscript.",
                recommendation="Keep a human spot-check before external publication.",
            )
        )

    return chapter_audit, findings


def validate_report(report: LongformUatReport) -> None:
    if report.drafted_chapters < report.target_chapters:
        raise ValueError(
            f"Expected at least {report.target_chapters} drafted chapters, got {report.drafted_chapters}."
        )

    if not report.chapter_audit or len(report.chapter_audit) < report.target_chapters:
        raise ValueError("Missing chapter-level evidence for the long-form manuscript.")

    if report.quality_score <= 0 or report.review_provider == "":
        raise ValueError("Missing review evidence from the final manuscript review.")

    if report.publish_outcome not in {"published", "blocked"}:
        raise ValueError(f"Unexpected publish outcome: {report.publish_outcome}")


def render_markdown_report(report: LongformUatReport) -> str:
    request_rows = "\n".join(
        f"| {entry.step} | `{entry.method} {entry.path}` | {entry.status_code} | {entry.duration_ms} |"
        for entry in report.request_trace
    )
    chapter_rows = "\n".join(
        f"| {chapter.chapter_number} | {chapter.title or 'Untitled'} | {chapter.scenes} | {chapter.word_count} | {chapter.hook or 'missing'} |"
        for chapter in report.chapter_audit[: report.target_chapters]
    )
    finding_rows = "\n".join(
        f"| {finding.severity} | {finding.area} | {finding.chapter or '-'} | {finding.summary} | {finding.recommendation} |"
        for finding in report.editorial_findings
    )
    issue_codes = ", ".join(report.issue_codes) if report.issue_codes else "none"
    run_ids = ", ".join(report.run_ids) if report.run_ids else "none"
    artifact_kinds = ", ".join(report.artifact_kinds) if report.artifact_kinds else "none"
    revision_notes = "\n".join(f"- {note}" for note in report.revision_notes) or "- none"

    return f"""# DashScope 20-Chapter Live Evidence

## Summary

- started: `{report.started_at}`
- completed: `{report.completed_at}`
- base URL: `{report.base_url}`
- story: `{report.story_title}` (`{report.story_id}`)
- workspace: `{report.workspace_id}`
- provider/model: `{report.provider}` / `{report.model}`
- review provider/model: `{report.review_provider}` / `{report.review_model}`
- target chapters: `{report.target_chapters}`
- drafted chapters: `{report.drafted_chapters}`
- publish outcome: `{report.publish_outcome}`
- publish failure code: `{report.publish_failure_code or 'n/a'}`

## Machine Evidence

- quality score: `{report.quality_score}`
- continuity: `{report.continuity_score}`
- pacing: `{report.pacing_score}`
- reader pull: `{report.reader_pull_score}`
- plot clarity: `{report.plot_clarity_score}`
- OOC risk: `{report.ooc_risk_score}`
- structural gate: `{'pass' if report.structural_gate_passed else 'blocked'}`
- semantic gate: `{'pass' if report.semantic_gate_passed else 'blocked'}`
- publish gate: `{'pass' if report.publish_gate_passed else 'blocked'}`
- published: `{'yes' if report.published else 'no'}`
- issue codes: `{issue_codes}`
- run IDs: `{run_ids}`
- artifact kinds: `{artifact_kinds}`

## Editorial Review

Strict review was generated from the exported manuscript, outline hooks, and final system review. This is not a marketing summary; it is a release-readiness critique.

| Severity | Area | Chapter | Finding | Recommendation |
| --- | --- | --- | --- | --- |
{finding_rows}

## Chapter Audit

| Chapter | Title | Scenes | Word count | Hook |
| --- | --- | --- | --- | --- |
{chapter_rows}

## Revision Notes

{revision_notes}

## Request Trace

| Step | Request | Status | Duration (ms) |
| --- | --- | --- | --- |
{request_rows}
"""


def _request_json(
    session: requests.Session,
    traces: list[RequestTrace],
    *,
    base_url: str,
    step: str,
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    allowed_status_codes: tuple[int, ...] = (200,),
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[int, dict[str, Any]]:
    started = time.perf_counter()
    response = session.request(
        method=method,
        url=f"{base_url}{path}",
        headers=headers,
        json=payload,
        timeout=timeout_seconds,
    )
    duration_ms = int((time.perf_counter() - started) * 1000)
    traces.append(
        RequestTrace(
            step=step,
            method=method,
            path=path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
    )

    try:
        body = response.json()
    except ValueError:
        body = {"raw_text": response.text}

    if response.status_code not in allowed_status_codes:
        raise RuntimeError(
            f"{step} failed with status {response.status_code}: {json.dumps(body, ensure_ascii=False)}"
        )

    return response.status_code, body


def _wait_for_health(base_url: str, timeout_seconds: int = 90) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/health/live", timeout=5)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise RuntimeError(f"Backend at {base_url} did not become healthy in time.")


@contextmanager
def _managed_backend(settings: NovelEngineSettings) -> Iterator[str]:
    api_key = settings.llm.dashscope_api_key
    if not api_key:
        raise RuntimeError(
            "DASHSCOPE_API_KEY is required. Provide it through the environment or .env.local."
        )

    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"

    with tempfile.TemporaryDirectory(prefix="novel-engine-uat-") as temp_dir:
        db_path = Path(temp_dir) / "longform-uat.sqlite3"
        env = os.environ.copy()
        env.update(
            {
                "PYTHONPATH": f"{REPO_ROOT}{os.pathsep}{REPO_ROOT / 'src'}",
                "APP_ENVIRONMENT": "testing",
                "SECURITY_SECRET_KEY": "test-secret-key-for-longform-uat-1234567890",
                "MONITORING_METRICS_ENABLED": "false",
                "LLM_PROVIDER": "dashscope",
                "DB_URL": f"sqlite:///{db_path.as_posix()}",
            }
        )

        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "src.apps.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=REPO_ROOT,
            env=env,
        )

        try:
            _wait_for_health(base_url)
            yield base_url
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def _story_title(seed: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{seed} {timestamp}"


def run_longform_uat(
    *,
    base_url: str,
    target_chapters: int,
    story_title_seed: str,
    timeout_seconds: int,
) -> LongformUatReport:
    session = requests.Session()
    traces: list[RequestTrace] = []
    started_at = _utc_now()

    login_status, login_payload = _request_json(
        session,
        traces,
        base_url=base_url,
        step="login",
        method="POST",
        path="/api/v1/auth/login",
        payload={
            "email": DEFAULT_LOGIN_EMAIL,
            "password": DEFAULT_LOGIN_PASSWORD,
        },
        timeout_seconds=timeout_seconds,
    )
    del login_status
    access_token = str(login_payload["access_token"])
    workspace_id = str(login_payload["workspace_id"])
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    title = _story_title(story_title_seed)
    _, create_payload = _request_json(
        session,
        traces,
        base_url=base_url,
        step="create_story",
        method="POST",
        path="/api/v1/story",
        headers=auth_headers,
        payload={
            "title": title,
            "genre": DEFAULT_GENRE,
            "premise": DEFAULT_PREMISE,
            "target_chapters": target_chapters,
            "target_audience": DEFAULT_AUDIENCE,
            "themes": DEFAULT_THEMES,
            "tone": DEFAULT_TONE,
            "author_id": workspace_id,
        },
        timeout_seconds=timeout_seconds,
    )
    story_id = str(create_payload["story"]["id"])

    _request_json(
        session,
        traces,
        base_url=base_url,
        step="generate_blueprint",
        method="POST",
        path=f"/api/v1/story/{story_id}/blueprint",
        headers=auth_headers,
        timeout_seconds=timeout_seconds,
    )
    _, outline_payload = _request_json(
        session,
        traces,
        base_url=base_url,
        step="generate_outline",
        method="POST",
        path=f"/api/v1/story/{story_id}/outline",
        headers=auth_headers,
        timeout_seconds=timeout_seconds,
    )
    _, draft_payload = _request_json(
        session,
        traces,
        base_url=base_url,
        step="draft_story",
        method="POST",
        path=f"/api/v1/story/{story_id}/draft",
        headers=auth_headers,
        payload={"target_chapters": target_chapters},
        timeout_seconds=timeout_seconds,
    )
    _, review_before = _request_json(
        session,
        traces,
        base_url=base_url,
        step="review_story_before_revision",
        method="POST",
        path=f"/api/v1/story/{story_id}/review",
        headers=auth_headers,
        timeout_seconds=timeout_seconds,
    )
    _, revise_payload = _request_json(
        session,
        traces,
        base_url=base_url,
        step="revise_story",
        method="POST",
        path=f"/api/v1/story/{story_id}/revise",
        headers=auth_headers,
        timeout_seconds=timeout_seconds,
    )
    _, review_after = _request_json(
        session,
        traces,
        base_url=base_url,
        step="review_story_after_revision",
        method="POST",
        path=f"/api/v1/story/{story_id}/review",
        headers=auth_headers,
        timeout_seconds=timeout_seconds,
    )
    _, export_payload = _request_json(
        session,
        traces,
        base_url=base_url,
        step="export_story",
        method="POST",
        path=f"/api/v1/story/{story_id}/export",
        headers=auth_headers,
        timeout_seconds=timeout_seconds,
    )
    publish_status, publish_payload = _request_json(
        session,
        traces,
        base_url=base_url,
        step="publish_story",
        method="POST",
        path=f"/api/v1/story/{story_id}/publish",
        headers=auth_headers,
        allowed_status_codes=(200, 422),
        timeout_seconds=timeout_seconds,
    )
    _, runs_payload = _request_json(
        session,
        traces,
        base_url=base_url,
        step="get_runs",
        method="GET",
        path=f"/api/v1/story/{story_id}/runs",
        headers=auth_headers,
        timeout_seconds=timeout_seconds,
    )
    _, artifacts_payload = _request_json(
        session,
        traces,
        base_url=base_url,
        step="get_artifacts",
        method="GET",
        path=f"/api/v1/story/{story_id}/artifacts",
        headers=auth_headers,
        timeout_seconds=timeout_seconds,
    )
    _, workspace_payload = _request_json(
        session,
        traces,
        base_url=base_url,
        step="get_workspace",
        method="GET",
        path=f"/api/v1/story/{story_id}/workspace",
        headers=auth_headers,
        timeout_seconds=timeout_seconds,
    )

    final_report = review_after["report"]
    exported_bundle = export_payload["export"]
    chapter_audit, editorial_findings = build_editorial_findings(
        exported_bundle,
        final_report,
        target_chapters=target_chapters,
    )

    publish_outcome = "published" if publish_status == 200 else "blocked"
    publish_failure_code: str | None = None
    if publish_status != 200:
        detail = publish_payload.get("detail")
        if isinstance(detail, dict):
            publish_failure_code = str(detail.get("code", "QUALITY_GATE_FAILED"))
        else:
            publish_failure_code = "QUALITY_GATE_FAILED"

    report = LongformUatReport(
        started_at=started_at,
        completed_at=_utc_now(),
        base_url=base_url,
        story_id=story_id,
        workspace_id=workspace_id,
        story_title=title,
        provider=str(outline_payload["outline"]["provider"]),
        model=str(outline_payload["outline"]["model"]),
        review_provider=str(final_report["semantic_review"]["source_provider"]),
        review_model=str(final_report["semantic_review"]["source_model"]),
        target_chapters=target_chapters,
        drafted_chapters=int(draft_payload["story"]["chapter_count"]),
        published=publish_status == 200,
        publish_outcome=publish_outcome,
        publish_failure_code=publish_failure_code,
        quality_score=int(final_report["quality_score"]),
        continuity_score=int(final_report["structural_review"]["metrics"]["continuity_score"]),
        pacing_score=int(final_report["structural_review"]["metrics"]["pacing_score"]),
        reader_pull_score=int(final_report["semantic_review"]["metrics"]["reader_pull_score"]),
        plot_clarity_score=int(final_report["semantic_review"]["metrics"]["plot_clarity_score"]),
        ooc_risk_score=int(final_report["semantic_review"]["metrics"]["ooc_risk_score"]),
        structural_gate_passed=bool(final_report.get("structural_gate_passed", False)),
        semantic_gate_passed=bool(final_report.get("semantic_gate_passed", False)),
        publish_gate_passed=bool(final_report.get("publish_gate_passed", False)),
        issue_codes=[
            str(issue.get("code", "issue"))
            for issue in final_report.get("issues", [])
            if isinstance(issue, dict)
        ],
        run_ids=[
            str(run.get("run_id"))
            for run in runs_payload.get("runs", [])
            if isinstance(run, dict) and run.get("run_id")
        ],
        artifact_kinds=[
            str(entry.get("kind"))
            for entry in artifacts_payload.get("history", [])
            if isinstance(entry, dict) and entry.get("kind")
        ],
        revision_notes=[
            str(note)
            for note in revise_payload.get("revision_notes", [])
            if isinstance(note, str)
        ],
        request_trace=traces,
        chapter_audit=chapter_audit,
        editorial_findings=editorial_findings,
    )
    validate_report(report)
    del review_before
    del workspace_payload
    return report


def _write_reports(report: LongformUatReport, markdown_path: Path, json_path: Path) -> None:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown_report(report), encoding="utf-8")
    json_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a DashScope-backed 20-chapter UAT through the canonical HTTP API."
    )
    parser.add_argument("--base-url", default=None, help="Reuse an existing backend instead of starting one.")
    parser.add_argument("--target-chapters", type=int, default=20)
    parser.add_argument("--story-title-seed", default=DEFAULT_STORY_TITLE)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--json-path", type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        settings = NovelEngineSettings()

        if args.target_chapters < 20:
            raise ValueError("target_chapters must be at least 20 for the long-form UAT.")

        if args.base_url:
            report = run_longform_uat(
                base_url=str(args.base_url).rstrip("/"),
                target_chapters=args.target_chapters,
                story_title_seed=args.story_title_seed,
                timeout_seconds=args.timeout_seconds,
            )
        else:
            with _managed_backend(settings) as base_url:
                report = run_longform_uat(
                    base_url=base_url,
                    target_chapters=args.target_chapters,
                    story_title_seed=args.story_title_seed,
                    timeout_seconds=args.timeout_seconds,
                )

        _write_reports(report, args.report_path, args.json_path)
        print(f"Wrote {args.report_path}")
        print(f"Wrote {args.json_path}")
        return 0
    except (RuntimeError, ValueError, requests.RequestException) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
