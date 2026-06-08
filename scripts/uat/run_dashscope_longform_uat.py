"""Run a DashScope-backed long-form UAT through the real HTTP API."""

from __future__ import annotations

import argparse
import json
import os
import re
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

DEFAULT_REPORT_PATH = (
    REPO_ROOT / "docs" / "reports" / "uat" / "LONGFORM_DASHSCOPE_LIVE_EVIDENCE.md"
)
DEFAULT_JSON_PATH = (
    REPO_ROOT / "docs" / "reports" / "uat" / "LONGFORM_DASHSCOPE_LIVE_EVIDENCE.json"
)
DEFAULT_ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "longform-uat"
DEFAULT_TIMEOUT_SECONDS = 900
DEFAULT_RETRY_DELAY_SECONDS = 3
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
    word_count: int
    summary: str


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
    principal_workspace_id: str
    workspace_id: str
    story_title: str
    provider: str
    model: str
    review_provider: str
    review_model: str
    target_chapters: int
    drafted_chapters: int
    exported: bool
    export_outcome: str
    export_failure_code: str | None
    export_path: str | None
    warning_count: int
    blocker_count: int
    suggestion_count: int
    review_rounds: int
    export_gate_passed: bool
    issue_codes: list[str]
    run_ids: list[str]
    artifact_kinds: list[str]
    editorial_notes: list[str]
    request_trace: list[RequestTrace]
    chapter_audit: list[ChapterAudit]
    editorial_findings: list[EditorialFinding]


@dataclass
class LongformUatFailureReport:
    started_at: str
    completed_at: str
    base_url: str
    target_chapters: int
    story_title_seed: str
    principal_workspace_id: str | None
    workspace_id: str | None
    story_title: str | None
    failed_step: str
    error_message: str
    request_trace: list[RequestTrace]
    job_payload: dict[str, Any] | None = None
    workspace_snapshot: dict[str, Any] | None = None


class LongformUatExecutionError(RuntimeError):
    def __init__(self, report: LongformUatFailureReport):
        super().__init__(report.error_message)
        self.report = report


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def build_editorial_findings(
    workspace_payload: dict[str, Any],
    review_report: dict[str, Any],
    *,
    target_chapters: int,
) -> tuple[list[ChapterAudit], list[EditorialFinding]]:
    chapters = workspace_payload.get("chapters", [])
    chapter_audit = [
        ChapterAudit(
            chapter_number=int(chapter.get("chapter_number", 0)),
            title=str(chapter.get("filename", "")),
            word_count=int(chapter.get("word_count", 0)),
            summary=str(chapter.get("summary", "")).strip(),
        )
        for chapter in chapters
        if isinstance(chapter, dict)
    ]

    findings: list[EditorialFinding] = []
    for bucket, severity in (
        ("blockers", "critical"),
        ("warnings", "warning"),
        ("suggestions", "info"),
    ):
        for issue in review_report.get(bucket, []):
            if not isinstance(issue, dict):
                continue
            location = issue.get("location")
            issue_chapter: int | None = None
            if isinstance(location, str) and "chapter-" in location:
                tail = location.split("chapter-")[-1]
                if tail.isdigit():
                    issue_chapter = int(tail)
            findings.append(
                EditorialFinding(
                    severity=severity,
                    area="workspace review",
                    chapter=issue_chapter,
                    summary=str(issue.get("message", "")).strip()
                    or str(issue.get("code", "issue")),
                    recommendation=str(issue.get("suggestion", "")).strip()
                    or "Use as editorial guidance before external release.",
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

    chapters_missing_summaries = [chapter for chapter in chapter_audit if not chapter.summary]
    for chapter in chapters_missing_summaries[:5]:
        findings.append(
            EditorialFinding(
                severity="warning",
                area="sidecar metadata",
                chapter=chapter.chapter_number,
                summary=f"Chapter {chapter.chapter_number} is missing a sidecar summary.",
                recommendation="Regenerate or review sidecar metadata before handoff.",
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

    if report.review_provider == "":
        raise ValueError("Missing review evidence from the final manuscript review.")

    if not report.exported or report.export_outcome != "exported":
        raise ValueError(
            "Long-form UAT did not reach a successful export outcome."
        )

    if report.blocker_count > 0:
        raise ValueError(
            "Long-form UAT finished with unresolved review blockers."
        )


def render_markdown_report(report: LongformUatReport) -> str:
    request_rows = "\n".join(
        f"| {entry.step} | `{entry.method} {entry.path}` | {entry.status_code} | {entry.duration_ms} |"
        for entry in report.request_trace
    )
    chapter_rows = "\n".join(
        f"| {chapter.chapter_number} | {chapter.title or 'Untitled'} | {chapter.word_count} | {chapter.summary or 'missing'} |"
        for chapter in report.chapter_audit[: report.target_chapters]
    )
    finding_rows = "\n".join(
        f"| {finding.severity} | {finding.area} | {finding.chapter or '-'} | {finding.summary} | {finding.recommendation} |"
        for finding in report.editorial_findings
    )
    issue_codes = ", ".join(report.issue_codes) if report.issue_codes else "none"
    run_ids = ", ".join(report.run_ids) if report.run_ids else "none"
    artifact_kinds = ", ".join(report.artifact_kinds) if report.artifact_kinds else "none"
    editorial_notes = "\n".join(f"- {note}" for note in report.editorial_notes) or "- none"

    return f"""# DashScope 20-Chapter Live Evidence

## Summary

- started: `{report.started_at}`
- completed: `{report.completed_at}`
- base URL: `{report.base_url}`
- story: `{report.story_title}`
- principal workspace: `{report.principal_workspace_id}`
- workspace: `{report.workspace_id}`
- provider/model: `{report.provider}` / `{report.model}`
- review provider/model: `{report.review_provider}` / `{report.review_model}`
- target chapters: `{report.target_chapters}`
- drafted chapters: `{report.drafted_chapters}`
- export outcome: `{report.export_outcome}`
- export failure code: `{report.export_failure_code or 'n/a'}`
- export path: `{report.export_path or 'n/a'}`
- review rounds: `{report.review_rounds}`

## Machine Evidence

- warnings: `{report.warning_count}`
- blockers: `{report.blocker_count}`
- suggestions: `{report.suggestion_count}`
- export gate: `{'pass' if report.export_gate_passed else 'blocked'}`
- exported: `{'yes' if report.exported else 'no'}`
- issue codes: `{issue_codes}`
- run IDs: `{run_ids}`
- artifact kinds: `{artifact_kinds}`

## Editorial Review

Workspace review was generated from local chapter Markdown and sidecar metadata. Warnings are editorial advice; only blockers prevent export.

| Severity | Area | Chapter | Finding | Recommendation |
| --- | --- | --- | --- | --- |
{finding_rows}

## Chapter Audit

| Chapter | File | Word count | Sidecar summary |
| --- | --- | --- | --- |
{chapter_rows}

## Editorial Notes

{editorial_notes}

## Request Trace

| Step | Request | Status | Duration (ms) |
| --- | --- | --- | --- |
{request_rows}
"""


def render_failure_markdown_report(report: LongformUatFailureReport) -> str:
    request_rows = "\n".join(
        f"| {entry.step} | `{entry.method} {entry.path}` | {entry.status_code} | {entry.duration_ms} |"
        for entry in report.request_trace
    ) or "| none | `n/a` | 0 | 0 |"
    story_title = report.story_title or "n/a"
    principal_workspace_id = report.principal_workspace_id or "n/a"
    workspace_id = report.workspace_id or "n/a"
    job_payload = report.job_payload or {}
    job_status = str(job_payload.get("status", "n/a"))
    job_operation = str(job_payload.get("operation", "n/a"))
    job_provider = str(job_payload.get("provider", "n/a"))
    job_error = str(job_payload.get("error", "n/a"))
    failure_artifact = job_payload.get("failure_artifact")
    failure_artifact_path = "n/a"
    if isinstance(failure_artifact, dict):
        failure_artifact_path = str(
            failure_artifact.get("relative_path")
            or failure_artifact.get("filename")
            or failure_artifact.get("artifact_id")
            or "n/a"
        )
    event_rows = _render_failure_event_rows(job_payload)
    snapshot = report.workspace_snapshot or {}
    chapters = snapshot.get("chapters", [])
    runs = snapshot.get("runs", [])
    jobs = snapshot.get("jobs", [])
    drafted_count = len(chapters) if isinstance(chapters, list) else 0
    run_count = len(runs) if isinstance(runs, list) else 0
    job_count = len(jobs) if isinstance(jobs, list) else 0
    run_event_rows = _render_workspace_run_event_rows(snapshot)

    return f"""# DashScope 20-Chapter Live Evidence

## Failure Summary

- started: `{report.started_at}`
- completed: `{report.completed_at}`
- base URL: `{report.base_url}`
- target chapters: `{report.target_chapters}`
- story title seed: `{report.story_title_seed}`
- story title: `{story_title}`
- principal workspace: `{principal_workspace_id}`
- workspace: `{workspace_id}`
- failed step: `{report.failed_step}`
- error: `{report.error_message}`

## Failed Job

- status: `{job_status}`
- operation: `{job_operation}`
- provider: `{job_provider}`
- job error: `{job_error}`
- failure artifact: `{failure_artifact_path}`

| Event status | Details |
| --- | --- |
{event_rows}

## Workspace Snapshot

- drafted chapters observed: `{drafted_count}`
- run count: `{run_count}`
- job count: `{job_count}`

| Run event status | Details |
| --- | --- |
{run_event_rows}

## Request Trace

| Step | Request | Status | Duration (ms) |
| --- | --- | --- | --- |
{request_rows}
"""


def _short_json(value: object, *, limit: int = 240) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    text = text.replace("\n", " ").replace("|", "\\|")
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _render_failure_event_rows(job_payload: dict[str, Any]) -> str:
    events = job_payload.get("events", [])
    if not isinstance(events, list) or not events:
        return "| none | n/a |"
    rows: list[str] = []
    for event in events[-6:]:
        if not isinstance(event, dict):
            continue
        rows.append(
            "| "
            f"{str(event.get('status', 'n/a'))} | "
            f"{_short_json(event.get('details', {}))} |"
        )
    return "\n".join(rows) or "| none | n/a |"


def _render_workspace_run_event_rows(snapshot: dict[str, Any]) -> str:
    runs = snapshot.get("runs", [])
    if not isinstance(runs, list) or not runs:
        return "| none | n/a |"
    latest_run = runs[0]
    if not isinstance(latest_run, dict):
        return "| none | n/a |"
    events = latest_run.get("events", [])
    if not isinstance(events, list) or not events:
        return "| none | n/a |"
    rows: list[str] = []
    for event in events[-8:]:
        if not isinstance(event, dict):
            continue
        rows.append(
            "| "
            f"{str(event.get('status', 'n/a'))} | "
            f"{_short_json(event.get('details', {}))} |"
        )
    return "\n".join(rows) or "| none | n/a |"


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
    last_error: RuntimeError | requests.RequestException | None = None
    for attempt in range(2):
        try:
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

            if response.status_code in allowed_status_codes:
                return response.status_code, body

            last_error = RuntimeError(
                f"{step} failed with status {response.status_code}: {json.dumps(body, ensure_ascii=False)}"
            )
            if attempt == 0 and _is_transient_status(response.status_code, body):
                time.sleep(DEFAULT_RETRY_DELAY_SECONDS)
                continue
            raise last_error
        except requests.RequestException as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)
            traces.append(
                RequestTrace(
                    step=step,
                    method=method,
                    path=path,
                    status_code=0,
                    duration_ms=duration_ms,
                )
            )
            last_error = exc
            if attempt == 0 and _is_transient_request_exception(exc):
                time.sleep(DEFAULT_RETRY_DELAY_SECONDS)
                continue
            raise

    if last_error is None:
        raise RuntimeError(f"{step} failed without a recorded response")
    raise last_error


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
                "LLM_TIMEOUT": "180",
                "APP_DATA_DIR": str(Path(temp_dir) / "data"),
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


def _workspace_slug(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", title.strip().lower()).strip("-_")
    return slug[:64] or "dashscope-longform-uat"


def _is_transient_status(status_code: int, body: dict[str, Any]) -> bool:
    if status_code in {408, 429, 500, 502, 503, 504}:
        return True
    text = json.dumps(body, ensure_ascii=False).lower()
    return any(
        marker in text
        for marker in (
            "timeout",
            "timed out",
            "temporarily unavailable",
            "temporary failure",
            "transient",
            "try again",
        )
    )


def _is_transient_request_exception(exc: requests.RequestException) -> bool:
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True
    text = str(exc).lower()
    return any(
        marker in text
        for marker in ("timeout", "timed out", "temporary", "transient", "try again")
    )


def _issue_counts(review_payload: dict[str, Any]) -> tuple[int, int, int]:
    warnings = review_payload.get("warnings", [])
    blockers = review_payload.get("blockers", [])
    suggestions = review_payload.get("suggestions", [])
    return (
        len(warnings) if isinstance(warnings, list) else 0,
        len(blockers) if isinstance(blockers, list) else 0,
        len(suggestions) if isinstance(suggestions, list) else 0,
    )


def _poll_job_until_terminal(
    session: requests.Session,
    traces: list[RequestTrace],
    *,
    base_url: str,
    step: str,
    path: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    payload: dict[str, Any] = {}
    while time.time() < deadline:
        _, payload = _request_json(
            session,
            traces,
            base_url=base_url,
            step=step,
            method="GET",
            path=path,
            timeout_seconds=min(timeout_seconds, 60),
        )
        if payload.get("status") in {"completed", "failed", "interrupted"}:
            return payload
        time.sleep(DEFAULT_RETRY_DELAY_SECONDS)
    raise RuntimeError(f"{step} did not finish within {timeout_seconds} seconds: {payload}")


def _try_fetch_workspace_snapshot(
    session: requests.Session,
    traces: list[RequestTrace],
    *,
    base_url: str,
    workspace_id: str,
    timeout_seconds: int,
) -> dict[str, Any] | None:
    try:
        _, payload = _request_json(
            session,
            traces,
            base_url=base_url,
            step="get_workspace_after_failed_job",
            method="GET",
            path=f"/api/workspaces/{workspace_id}",
            timeout_seconds=timeout_seconds,
        )
    except (RuntimeError, requests.RequestException):
        return None
    return payload


def _resolve_output_paths(
    *,
    output_dir: Path,
    report_path: Path | None,
    json_path: Path | None,
    write_canonical_reports: bool,
) -> tuple[Path, Path]:
    if write_canonical_reports:
        return report_path or DEFAULT_REPORT_PATH, json_path or DEFAULT_JSON_PATH

    base_dir = output_dir
    return (
        report_path or base_dir / DEFAULT_REPORT_PATH.name,
        json_path or base_dir / DEFAULT_JSON_PATH.name,
    )


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
    principal_workspace_id: str | None = None
    workspace_id: str | None = None
    title: str | None = None
    latest_job_payload: dict[str, Any] | None = None
    workspace_snapshot: dict[str, Any] | None = None
    failed_step_override: str | None = None

    try:
        login_status, login_payload = _request_json(
            session,
            traces,
            base_url=base_url,
            step="login",
            method="POST",
            path="/api/auth/login",
            payload={
                "email": DEFAULT_LOGIN_EMAIL,
                "password": DEFAULT_LOGIN_PASSWORD,
            },
            timeout_seconds=timeout_seconds,
        )
        del login_status
        principal_workspace_id = str(login_payload["workspace_id"])

        title = _story_title(story_title_seed)
        workspace_id = _workspace_slug(title)
        _, create_payload = _request_json(
            session,
            traces,
            base_url=base_url,
            step="create_workspace",
            method="POST",
            path="/api/workspaces",
            allowed_status_codes=(201,),
            payload={
                "workspace_id": workspace_id,
                "title": title,
                "genre": DEFAULT_GENRE,
                "premise": DEFAULT_PREMISE,
                "target_chapters": target_chapters,
                "target_audience": DEFAULT_AUDIENCE,
                "themes": DEFAULT_THEMES,
                "tone": DEFAULT_TONE,
            },
            timeout_seconds=timeout_seconds,
        )
        workspace_id = str(create_payload["workspace_id"])

        _, run_job_payload = _request_json(
            session,
            traces,
            base_url=base_url,
            step="run_workspace",
            method="POST",
            path=f"/api/workspaces/{workspace_id}/jobs",
            allowed_status_codes=(202,),
            payload={
                "operation": "run",
                "target_chapters": target_chapters,
                "provider": "dashscope",
            },
            timeout_seconds=timeout_seconds,
        )
        run_job_id = str(run_job_payload["job_id"])
        run_job_payload = _poll_job_until_terminal(
            session,
            traces,
            base_url=base_url,
            step="poll_run_job",
            path=f"/api/workspaces/{workspace_id}/jobs/{run_job_id}",
            timeout_seconds=timeout_seconds,
        )
        latest_job_payload = run_job_payload
        if run_job_payload.get("status") != "completed":
            failed_step_override = "poll_run_job"
            workspace_snapshot = _try_fetch_workspace_snapshot(
                session,
                traces,
                base_url=base_url,
                workspace_id=workspace_id,
                timeout_seconds=timeout_seconds,
            )
            raise RuntimeError(f"Run job failed: {run_job_payload.get('error')}")

        _, workspace_payload = _request_json(
            session,
            traces,
            base_url=base_url,
            step="get_workspace_after_run",
            method="GET",
            path=f"/api/workspaces/{workspace_id}",
            timeout_seconds=timeout_seconds,
        )
        workspace_snapshot = workspace_payload
        final_review = dict(workspace_payload.get("latest_review") or {})
        review_rounds = 1 if final_review else 0

        _, export_job_payload = _request_json(
            session,
            traces,
            base_url=base_url,
            step="export_workspace",
            method="POST",
            path=f"/api/workspaces/{workspace_id}/jobs",
            allowed_status_codes=(202,),
            payload={"operation": "export", "provider": "dashscope"},
            timeout_seconds=timeout_seconds,
        )
        export_job_id = str(export_job_payload["job_id"])
        export_job_payload = _poll_job_until_terminal(
            session,
            traces,
            base_url=base_url,
            step="poll_export_job",
            path=f"/api/workspaces/{workspace_id}/jobs/{export_job_id}",
            timeout_seconds=timeout_seconds,
        )
        latest_job_payload = export_job_payload
        _, workspace_payload = _request_json(
            session,
            traces,
            base_url=base_url,
            step="get_workspace_after_export",
            method="GET",
            path=f"/api/workspaces/{workspace_id}",
            timeout_seconds=timeout_seconds,
        )
        workspace_snapshot = workspace_payload

        final_review = dict(workspace_payload.get("latest_review") or final_review)
        warning_count, blocker_count, suggestion_count = _issue_counts(final_review)
        chapter_audit, editorial_findings = build_editorial_findings(
            workspace_payload,
            final_review,
            target_chapters=target_chapters,
        )

        exported = export_job_payload.get("status") == "completed"
        export_result = export_job_payload.get("result")
        export_payload = (
            export_result.get("export", {})
            if isinstance(export_result, dict)
            else {}
        )
        export_outcome = "exported" if exported else "blocked"
        export_failure_code = (
            None if exported else str(export_job_payload.get("error") or "EXPORT_FAILED")
        )
        export_path = None
        if isinstance(export_payload, dict):
            raw_export_path = (
                export_payload.get("relative_path")
                or export_payload.get("filename")
                or export_payload.get("artifact_id")
            )
            export_path = str(raw_export_path) if raw_export_path else None
        settings = NovelEngineSettings()
        issue_codes = [
            str(issue.get("code", "issue"))
            for bucket in ("blockers", "warnings", "suggestions")
            for issue in final_review.get(bucket, [])
            if isinstance(issue, dict)
        ]
        run_ids = [
            str(run.get("run_id"))
            for run in workspace_payload.get("runs", [])
            if isinstance(run, dict) and run.get("run_id")
        ]
        artifact_kinds = [
            "chapter_artifacts"
            for run in workspace_payload.get("runs", [])
            if isinstance(run, dict) and int(run.get("artifact_count", 0)) > 0
        ]
        if final_review:
            artifact_kinds.append("review")
        if workspace_payload.get("exports"):
            artifact_kinds.append("export")

        report = LongformUatReport(
            started_at=started_at,
            completed_at=_utc_now(),
            base_url=base_url,
            principal_workspace_id=principal_workspace_id,
            workspace_id=workspace_id,
            story_title=title,
            provider="dashscope",
            model=settings.llm.resolved_model("dashscope"),
            review_provider="local",
            review_model="local-reviewer",
            target_chapters=target_chapters,
            drafted_chapters=len(workspace_payload.get("chapters", [])),
            exported=exported,
            export_outcome=export_outcome,
            export_failure_code=export_failure_code,
            export_path=export_path,
            warning_count=warning_count,
            blocker_count=blocker_count,
            suggestion_count=suggestion_count,
            review_rounds=review_rounds,
            export_gate_passed=not bool(final_review.get("export_blocked", True)),
            issue_codes=issue_codes,
            run_ids=run_ids,
            artifact_kinds=artifact_kinds,
            editorial_notes=[
                str(note)
                for note in final_review.get("style_notes", [])
                if str(note).strip()
            ],
            request_trace=traces,
            chapter_audit=chapter_audit,
            editorial_findings=editorial_findings,
        )
        validate_report(report)
        return report
    except (RuntimeError, ValueError, requests.RequestException) as exc:
        failed_step = failed_step_override or (traces[-1].step if traces else "startup")
        raise LongformUatExecutionError(
            LongformUatFailureReport(
                started_at=started_at,
                completed_at=_utc_now(),
                base_url=base_url,
                target_chapters=target_chapters,
                story_title_seed=story_title_seed,
                principal_workspace_id=principal_workspace_id,
                workspace_id=workspace_id,
                story_title=title,
                failed_step=failed_step,
                error_message=str(exc),
                request_trace=traces,
                job_payload=latest_job_payload,
                workspace_snapshot=workspace_snapshot,
            )
        ) from exc


def _write_reports(report: LongformUatReport, markdown_path: Path, json_path: Path) -> None:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown_report(report), encoding="utf-8")
    json_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")


def _write_failure_reports(
    report: LongformUatFailureReport,
    markdown_path: Path,
    json_path: Path,
) -> None:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_failure_markdown_report(report), encoding="utf-8")
    json_path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a DashScope-backed 20-chapter UAT through the workspace API."
    )
    parser.add_argument("--base-url", default=None, help="Reuse an existing backend instead of starting one.")
    parser.add_argument("--target-chapters", type=int, default=20)
    parser.add_argument("--story-title-seed", default=DEFAULT_STORY_TITLE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_ARTIFACTS_DIR)
    parser.add_argument("--report-path", type=Path, default=None)
    parser.add_argument("--json-path", type=Path, default=None)
    parser.add_argument(
        "--write-canonical-reports",
        action="store_true",
        help="Write evidence to docs/reports/uat instead of an artifact directory.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    markdown_path, json_path = _resolve_output_paths(
        output_dir=args.output_dir,
        report_path=args.report_path,
        json_path=args.json_path,
        write_canonical_reports=args.write_canonical_reports,
    )
    try:
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

        _write_reports(report, markdown_path, json_path)
        print(f"Wrote {markdown_path}")
        print(f"Wrote {json_path}")
        return 0
    except LongformUatExecutionError as exc:
        _write_failure_reports(exc.report, markdown_path, json_path)
        print(f"Wrote {markdown_path}")
        print(f"Wrote {json_path}")
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except (RuntimeError, ValueError, requests.RequestException) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
