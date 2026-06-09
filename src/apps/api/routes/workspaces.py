"""Local-first workspace routes."""

from __future__ import annotations

import asyncio
import json
import re
import threading
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Annotated, Any, Literal, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.apps.api.dependencies import WorkspacePrincipal, get_workspace_principal
from src.contexts.ai.application.ports.text_generation_port import (
    TextGenerationProvider,
    TextGenerationProviderName,
)
from src.contexts.ai.infrastructure.providers import create_text_generation_provider
from src.contexts.ai.infrastructure.providers.deterministic_text_generation_provider import (
    DeterministicTextGenerationProvider,
)
from src.contexts.narrative.application.services.local_writing_engine import (
    ChapterDraftArtifact,
    LocalDraftingEngine,
    LocalExporter,
    LocalReviewer,
    NovelWorkspace,
    ReviewSeverity,
    StoryConfig,
    utcnow_iso,
)
from src.shared.infrastructure.config.settings import get_settings

router = APIRouter(prefix="/workspaces", tags=["workspaces"])
providers_router = APIRouter(tags=["providers"])

SAFE_WORKSPACE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
JobOperation = Literal["draft", "run", "review", "revise", "export"]
JobStatus = Literal["queued", "running", "completed", "failed", "interrupted"]
ProviderName = Literal["mock", "dashscope", "openai_compatible"]


class WorkspaceCreateRequest(BaseModel):
    """Request for creating a local writing workspace."""

    workspace_id: str | None = Field(default=None, max_length=64)
    title: str = Field(..., min_length=1, max_length=200)
    genre: str = Field(..., min_length=1, max_length=120)
    premise: str = Field(..., min_length=10, max_length=5000)
    target_chapters: int = Field(default=12, ge=1, le=120)
    target_audience: str | None = Field(default=None, max_length=120)
    themes: list[str] = Field(default_factory=list)
    tone: str = Field(default="immersive serial fiction", max_length=200)
    force: bool = Field(default=False)


class WorkspaceJobRequest(BaseModel):
    """Request for executing a local workspace job."""

    operation: JobOperation
    chapter: int | None = Field(default=None, ge=1, le=120)
    target_chapters: int | None = Field(default=None, ge=1, le=120)
    provider: ProviderName | None = Field(default=None)


class ArtifactRef(BaseModel):
    """Browser-safe reference to a workspace artifact."""

    artifact_id: str
    filename: str | None = None
    relative_path: str
    size: int | None = None
    run_id: str | None = None


class ProviderStatus(BaseModel):
    """Text generation provider status exposed to the browser."""

    provider: ProviderName
    label: str
    configured: bool
    is_default: bool
    model: str


class ProviderListResponse(BaseModel):
    """Available provider options for workspaces."""

    default_provider: ProviderName
    providers: list[ProviderStatus]


class StoryConfigResponse(BaseModel):
    """Story configuration returned by workspace status."""

    title: str
    genre: str
    premise: str
    target_chapters: int
    tone: str
    target_audience: str | None = None
    themes: list[str]
    style_profile: dict[str, Any] = Field(default_factory=dict)
    continuity: dict[str, Any] = Field(default_factory=dict)


class ChapterStatusResponse(BaseModel):
    """Chapter metadata returned by workspace status."""

    chapter_number: int
    filename: str
    artifact_id: str
    relative_path: str
    word_count: int
    summary: str | None = None
    sidecar: dict[str, Any] = Field(default_factory=dict)


class ReviewIssueResponse(BaseModel):
    """Review issue with optional evidence details."""

    severity: ReviewSeverity
    code: str
    message: str
    location: str
    suggestion: str
    details: dict[str, Any] = Field(default_factory=dict)


class ReviewReportResponse(BaseModel):
    """Review report returned by status and job results."""

    story_title: str
    checked_at: str
    blockers: list[ReviewIssueResponse]
    warnings: list[ReviewIssueResponse]
    suggestions: list[ReviewIssueResponse]
    style_notes: list[str]
    export_blocked: bool


class RunEventResponse(BaseModel):
    """Run journal event."""

    timestamp: str
    operation: str | None = None
    status: str
    details: dict[str, Any] = Field(default_factory=dict)


class RunStatusResponse(BaseModel):
    """Run artifact summary."""

    run_id: str
    artifact_id: str
    relative_path: str
    events: list[RunEventResponse]
    artifact_count: int
    last_event: RunEventResponse | None = None


class JobEventResponse(BaseModel):
    """Job lifecycle event."""

    timestamp: str
    status: JobStatus
    details: dict[str, Any] = Field(default_factory=dict)


class ArtifactJobResult(BaseModel):
    """Safe draft/revision result returned to browsers."""

    result_type: Literal["artifact"]
    artifact: ArtifactRef
    chapter_number: int
    provider: str
    model: str
    run_id: str
    sidecar: dict[str, Any] = Field(default_factory=dict)


class ReviewJobResult(BaseModel):
    """Safe review result returned to browsers."""

    result_type: Literal["review"]
    review: ReviewReportResponse


class RunJobResult(BaseModel):
    """Safe run result returned to browsers."""

    result_type: Literal["run"]
    review: ReviewReportResponse
    run_id: str


class ExportJobResult(BaseModel):
    """Safe export result returned to browsers."""

    result_type: Literal["export"]
    export: ArtifactRef


WorkspaceJobResultResponse = Annotated[
    ArtifactJobResult | ReviewJobResult | RunJobResult | ExportJobResult,
    Field(discriminator="result_type"),
]


class WorkspaceJobResponse(BaseModel):
    """Persisted workspace job state."""

    job_id: str
    workspace_id: str
    operation: JobOperation
    status: JobStatus
    created_at: str
    updated_at: str
    provider: ProviderName
    result: WorkspaceJobResultResponse | None = None
    error: str | None = None
    failure_artifact: ArtifactRef | None = None
    events: list[JobEventResponse]


class WorkspaceStatusResponse(BaseModel):
    """Complete workspace status."""

    workspace_id: str
    story: StoryConfigResponse
    chapters: list[ChapterStatusResponse]
    latest_review: ReviewReportResponse | None = None
    exports: list[ArtifactRef]
    runs: list[RunStatusResponse]
    jobs: list[WorkspaceJobResponse]


class WorkspaceListResponse(BaseModel):
    """List of workspaces for the active principal."""

    workspaces: list[WorkspaceStatusResponse]


@dataclass(slots=True)
class WorkspaceJobRecord:
    """Process-local job metadata for workspace actions."""

    job_id: str
    principal_key: str
    workspace_id: str
    operation: JobOperation
    status: JobStatus
    created_at: str
    updated_at: str
    provider: str = "mock"
    result: dict[str, Any] | None = None
    error: str | None = None
    failure_artifact: dict[str, Any] | None = None
    events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("principal_key", None)
        return payload

    def to_storage_dict(self) -> dict[str, Any]:
        return asdict(self)


JobKey = tuple[str, str, str]
_jobs: dict[JobKey, WorkspaceJobRecord] = {}
_tasks: dict[JobKey, asyncio.Task[None]] = {}
_job_registry_lock = threading.RLock()


def reset_workspace_jobs() -> None:
    """Reset process-local job metadata for tests.

    Production restart recovery is lazy: workspace/job reads persist orphaned
    queued or running jobs as interrupted.
    """
    with _job_registry_lock:
        for task in _tasks.values():
            task.cancel()
        _tasks.clear()
        _jobs.clear()


def _require_principal(
    principal: WorkspacePrincipal | None,
) -> WorkspacePrincipal:
    if principal is not None:
        return principal
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication or guest workspace is required",
    )


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-_")
    return slug[:48] or "workspace"


def _workspace_id(value: str | None, *, title: str) -> str:
    workspace_id = value.strip() if value else f"{_slugify(title)}-{uuid4().hex[:8]}"
    if not SAFE_WORKSPACE_ID.fullmatch(workspace_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="workspace_id must be a safe slug using letters, numbers, '-' or '_'",
        )
    return workspace_id


def _principal_key(principal: WorkspacePrincipal) -> str:
    return f"{principal.kind}:{_workspace_id(principal.workspace_id, title='workspace')}"


def _principal_root(principal: WorkspacePrincipal) -> Path:
    settings = get_settings()
    root = (
        settings.data_dir
        / "novel-workspaces"
        / _workspace_id(principal.workspace_id, title="workspace")
    )
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _workspace_path(principal: WorkspacePrincipal, workspace_id: str) -> Path:
    if not SAFE_WORKSPACE_ID.fullmatch(workspace_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    root = _principal_root(principal)
    path = (root / workspace_id).resolve()
    if root not in {path, *path.parents}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Workspace path escapes the active principal",
        )
    return path


def _existing_workspace(principal: WorkspacePrincipal, workspace_id: str) -> NovelWorkspace:
    workspace = NovelWorkspace(_workspace_path(principal, workspace_id))
    if not workspace.story_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace


def _provider_is_configured(provider_name: str) -> bool:
    if provider_name == "mock":
        return True
    settings = get_settings()
    return bool(settings.llm.resolved_api_key(provider_name))


def _default_provider_name() -> TextGenerationProviderName:
    settings = get_settings()
    if settings.llm.provider == "mock":
        return "mock"
    configured = [
        provider
        for provider in ("dashscope", "openai_compatible")
        if _provider_is_configured(provider)
    ]
    if settings.llm.provider in configured:
        return settings.llm.provider
    if configured:
        return cast(TextGenerationProviderName, configured[0])
    return "mock"


def _resolve_provider_name(provider_name: str | None) -> TextGenerationProviderName:
    if provider_name is None:
        return _default_provider_name()
    return cast(TextGenerationProviderName, provider_name)


def _build_provider(provider_name: str | None) -> TextGenerationProvider:
    provider_name = _resolve_provider_name(provider_name)
    if provider_name == "mock":
        return DeterministicTextGenerationProvider()
    settings = get_settings()
    return create_text_generation_provider(
        settings,
        provider_name=cast(TextGenerationProviderName, provider_name),
    )


def _build_review_provider(provider_name: str | None) -> TextGenerationProvider:
    resolved_provider = _resolve_provider_name(provider_name)
    if resolved_provider != "mock" and not _provider_is_configured(resolved_provider):
        raise ValueError(f"Provider is not configured: {resolved_provider}")
    return _build_provider(resolved_provider)


def _effective_job_provider(
    operation: JobOperation,
    provider_name: str | None,
) -> TextGenerationProviderName:
    del operation
    resolved_provider = _resolve_provider_name(provider_name)
    if resolved_provider != "mock" and not _provider_is_configured(resolved_provider):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Provider is not configured: {resolved_provider}",
        )
    return resolved_provider


def _job_key(job: WorkspaceJobRecord) -> JobKey:
    return (job.principal_key, job.workspace_id, job.job_id)


def _job_lookup_key(
    *,
    principal_key: str,
    workspace_id: str,
    job_id: str,
) -> JobKey:
    return (principal_key, workspace_id, job_id)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for attempt in range(6):
        try:
            temp_path.replace(path)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.05 * (attempt + 1))


def _job_path(workspace: NovelWorkspace, job_id: str) -> Path:
    return workspace.jobs_dir / f"{job_id}.json"


def _store_job(workspace: NovelWorkspace, job: WorkspaceJobRecord) -> None:
    with _job_registry_lock:
        _jobs[_job_key(job)] = job
    _atomic_write_json(_job_path(workspace, job.job_id), job.to_storage_dict())


def _load_job(path: Path) -> WorkspaceJobRecord | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        return WorkspaceJobRecord(
            job_id=str(payload["job_id"]),
            principal_key=str(payload["principal_key"]),
            workspace_id=str(payload["workspace_id"]),
            operation=cast(JobOperation, payload["operation"]),
            status=cast(JobStatus, payload["status"]),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
            provider=str(payload.get("provider", "mock")),
            result=cast(dict[str, Any] | None, payload.get("result")),
            error=(
                str(payload["error"])
                if payload.get("error") is not None
                else None
            ),
            failure_artifact=(
                cast(dict[str, Any], payload["failure_artifact"])
                if isinstance(payload.get("failure_artifact"), dict)
                else None
            ),
            events=[
                cast(dict[str, Any], item)
                for item in payload.get("events", [])
                if isinstance(item, dict)
            ],
        )
    except KeyError:
        return None


def _provider_response_name(provider: str) -> ProviderName:
    if provider in {"mock", "dashscope", "openai_compatible"}:
        return cast(ProviderName, provider)
    return "mock"


def _artifact_ref_from_path(
    workspace: NovelWorkspace,
    path: Path,
    *,
    artifact_id: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id or path.name,
        "filename": path.name,
        "relative_path": workspace.relative_path(path),
        "size": path.stat().st_size if path.exists() and path.is_file() else None,
        "run_id": run_id,
    }


def _chapter_artifact_ref(
    workspace: NovelWorkspace,
    *,
    run_id: str,
    chapter_number: int,
) -> dict[str, Any]:
    artifact_path = workspace.runs_dir / run_id / f"chapter-{chapter_number:03d}.artifact.json"
    return _artifact_ref_from_path(workspace, artifact_path, run_id=run_id)


def _coerce_artifact_ref(
    workspace: NovelWorkspace,
    value: object,
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    relative_path = str(value.get("relative_path", "")).strip()
    if relative_path:
        path = (workspace.root / relative_path).resolve()
        if workspace.root not in {path, *path.parents}:
            return None
        return {
            "artifact_id": str(value.get("artifact_id") or path.name),
            "filename": str(value.get("filename") or path.name),
            "relative_path": workspace.relative_path(path),
            "size": value.get("size") if isinstance(value.get("size"), int) else None,
            "run_id": (
                str(value["run_id"]).strip()
                if value.get("run_id") is not None
                else None
            ),
        }
    filename = str(value.get("filename") or value.get("artifact_id") or "").strip()
    if not filename:
        return None
    path = workspace.exports_dir / filename
    return _artifact_ref_from_path(
        workspace,
        path,
        artifact_id=str(value.get("artifact_id") or filename),
    )


def _sanitize_string(workspace: NovelWorkspace, value: str) -> str:
    try:
        candidate = Path(value).resolve()
    except (OSError, ValueError):
        candidate = None
    if candidate is not None and workspace.root in {candidate, *candidate.parents}:
        return workspace.relative_path(candidate)

    sanitized = value
    markers = {
        str(workspace.root),
        str(workspace.root).replace("\\", "/"),
        str(get_settings().data_dir.resolve()),
        str(get_settings().data_dir.resolve()).replace("\\", "/"),
    }
    for marker in sorted(markers, key=len, reverse=True):
        if marker:
            sanitized = sanitized.replace(marker, "<workspace>")
    return sanitized


def _sanitize_public_value(workspace: NovelWorkspace, value: object) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            next_key = str(key)
            if next_key == "chapter_file":
                next_key = "chapter_relative_path"
            elif next_key == "review_report":
                next_key = "review_report_relative_path"
            sanitized[next_key] = _sanitize_public_value(workspace, item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_public_value(workspace, item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_public_value(workspace, item) for item in value]
    if isinstance(value, str):
        return _sanitize_string(workspace, value)
    return value


def _sanitize_details(workspace: NovelWorkspace, value: object) -> dict[str, Any]:
    sanitized = _sanitize_public_value(workspace, value)
    return sanitized if isinstance(sanitized, dict) else {}


def _review_result_payload(report: dict[str, Any]) -> dict[str, Any]:
    return {"result_type": "review", "review": report}


def _run_result_payload(report: dict[str, Any], run_id: str) -> dict[str, Any]:
    return {"result_type": "run", "review": report, "run_id": run_id}


def _artifact_result_payload(
    workspace: NovelWorkspace,
    artifact: dict[str, Any],
) -> dict[str, Any] | None:
    try:
        chapter_number = int(artifact.get("chapter_number", 0))
    except (TypeError, ValueError):
        return None
    if chapter_number < 1:
        return None
    run_id = str(artifact.get("run_id", "")).strip()
    if not run_id:
        return None
    return {
        "result_type": "artifact",
        "artifact": _chapter_artifact_ref(
            workspace,
            run_id=run_id,
            chapter_number=chapter_number,
        ),
        "chapter_number": chapter_number,
        "provider": str(artifact.get("provider", "")),
        "model": str(artifact.get("model", "")),
        "run_id": run_id,
        "sidecar": _sanitize_public_value(
            workspace,
            artifact.get("sidecar_metadata")
            if isinstance(artifact.get("sidecar_metadata"), dict)
            else artifact.get("sidecar", {}),
        ),
    }


def _artifact_result_from_draft(
    workspace: NovelWorkspace,
    artifact: ChapterDraftArtifact,
) -> dict[str, Any]:
    return {
        "result_type": "artifact",
        "artifact": _chapter_artifact_ref(
            workspace,
            run_id=artifact.run_id,
            chapter_number=artifact.chapter_number,
        ),
        "chapter_number": artifact.chapter_number,
        "provider": artifact.provider,
        "model": artifact.model,
        "run_id": artifact.run_id,
        "sidecar": _sanitize_public_value(workspace, artifact.sidecar_metadata),
    }


def _export_result_payload(
    workspace: NovelWorkspace,
    export_ref: dict[str, Any],
) -> dict[str, Any] | None:
    safe_ref = _coerce_artifact_ref(workspace, export_ref)
    if safe_ref is None:
        return None
    return {"result_type": "export", "export": safe_ref}


def _sanitize_job_result(
    workspace: NovelWorkspace,
    result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None

    result_type = result.get("result_type")
    if result_type == "artifact":
        payload = {
            "chapter_number": result.get("chapter_number"),
            "provider": result.get("provider"),
            "model": result.get("model"),
            "run_id": result.get("run_id"),
            "sidecar_metadata": result.get("sidecar", {}),
        }
        safe = _artifact_result_payload(workspace, payload)
        if safe is not None and isinstance(result.get("artifact"), dict):
            ref = _coerce_artifact_ref(workspace, result["artifact"])
            if ref is not None:
                safe["artifact"] = ref
        return safe
    if result_type == "review" and isinstance(result.get("review"), dict):
        return _review_result_payload(
            cast(dict[str, Any], _sanitize_public_value(workspace, result["review"]))
        )
    if result_type == "run" and isinstance(result.get("review"), dict):
        return _run_result_payload(
            cast(dict[str, Any], _sanitize_public_value(workspace, result["review"])),
            str(result.get("run_id", "")),
        )
    if result_type == "export" and isinstance(result.get("export"), dict):
        return _export_result_payload(workspace, cast(dict[str, Any], result["export"]))

    if isinstance(result.get("artifact"), dict):
        return _artifact_result_payload(
            workspace,
            cast(dict[str, Any], result["artifact"]),
        )
    if isinstance(result.get("review"), dict):
        report = cast(dict[str, Any], _sanitize_public_value(workspace, result["review"]))
        run_id = result.get("run_id")
        if run_id is not None:
            return _run_result_payload(report, str(run_id))
        return _review_result_payload(report)
    if isinstance(result.get("export"), dict):
        return _export_result_payload(workspace, cast(dict[str, Any], result["export"]))
    return None


def _job_public_payload(
    workspace: NovelWorkspace,
    job: WorkspaceJobRecord,
) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "workspace_id": job.workspace_id,
        "operation": job.operation,
        "status": job.status,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "provider": _provider_response_name(job.provider),
        "result": _sanitize_job_result(workspace, job.result),
        "error": _sanitize_string(workspace, job.error) if job.error else None,
        "failure_artifact": _coerce_artifact_ref(workspace, job.failure_artifact),
        "events": [
            {
                "timestamp": str(event.get("timestamp", "")),
                "status": cast(JobStatus, event.get("status", "queued")),
                "details": _sanitize_details(workspace, event.get("details", {})),
            }
            for event in job.events
            if isinstance(event, dict)
        ],
    }


def _workspace_jobs(
    workspace: NovelWorkspace,
    *,
    principal_key: str,
    workspace_id: str,
) -> list[WorkspaceJobRecord]:
    records: dict[str, WorkspaceJobRecord] = {}
    if workspace.jobs_dir.exists():
        for path in workspace.jobs_dir.glob("*.json"):
            job = _load_job(path)
            if job is None:
                continue
            records[job.job_id] = job
            with _job_registry_lock:
                _jobs.setdefault(_job_key(job), job)
    with _job_registry_lock:
        cached_jobs = list(_jobs.values())
        active_task_keys = set(_tasks)
    for job in cached_jobs:
        if job.workspace_id == workspace_id:
            records[job.job_id] = job

    visible: list[WorkspaceJobRecord] = []
    for job in records.values():
        if job.principal_key != principal_key or job.workspace_id != workspace_id:
            continue
        if job.status in {"queued", "running"} and _job_key(job) not in active_task_keys:
            job.error = "Job was interrupted before completion."
            _record_job_event(job, "interrupted", {"reason": "process_restart"})
            _store_job(workspace, job)
        visible.append(job)
    return visible


def _chapter_payload(workspace: NovelWorkspace) -> list[dict[str, Any]]:
    sidecars = workspace.load_latest_sidecars()
    chapters: list[dict[str, Any]] = []
    for path in workspace.list_chapters():
        try:
            chapter_number = int(path.stem.split("-")[-1])
        except ValueError:
            continue
        text = path.read_text(encoding="utf-8")
        chapters.append(
            {
                "chapter_number": chapter_number,
                "filename": path.name,
                "artifact_id": path.name,
                "relative_path": workspace.relative_path(path),
                "word_count": len(text.split()),
                "summary": sidecars.get(chapter_number, {}).get("summary"),
                "sidecar": sidecars.get(chapter_number, {}),
            }
        )
    return chapters


def _runs_payload(workspace: NovelWorkspace) -> list[dict[str, Any]]:
    if not workspace.runs_dir.exists():
        return []
    runs: list[dict[str, Any]] = []
    for run_dir in sorted(workspace.runs_dir.iterdir(), reverse=True):
        if not run_dir.is_dir():
            continue
        events_path = run_dir / "events.jsonl"
        events: list[dict[str, Any]] = []
        if events_path.exists():
            for line in events_path.read_text(encoding="utf-8").splitlines():
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict):
                    event["details"] = _sanitize_details(workspace, event.get("details", {}))
                    events.append(event)
        runs.append(
            {
                "run_id": run_dir.name,
                "artifact_id": run_dir.name,
                "relative_path": workspace.relative_path(run_dir),
                "events": events,
                "artifact_count": len(list(run_dir.glob("*.json"))),
                "last_event": events[-1] if events else None,
            }
        )
    return runs


def _exports_payload(workspace: NovelWorkspace) -> list[dict[str, Any]]:
    if not workspace.exports_dir.exists():
        return []
    return [
        {
            "filename": path.name,
            "artifact_id": path.name,
            "relative_path": workspace.relative_path(path),
            "size": path.stat().st_size,
        }
        for path in sorted(workspace.exports_dir.glob("*"))
        if path.is_file()
    ]


def _workspace_status(
    workspace_id: str,
    workspace: NovelWorkspace,
    principal_key: str,
) -> dict[str, Any]:
    config = workspace.load_config()
    review = workspace.latest_review()
    jobs = [
        _job_public_payload(workspace, job)
        for job in _workspace_jobs(
            workspace,
            principal_key=principal_key,
            workspace_id=workspace_id,
        )
    ]
    return {
        "workspace_id": workspace_id,
        "story": config.to_dict(),
        "chapters": _chapter_payload(workspace),
        "latest_review": (
            _sanitize_public_value(workspace, review.to_dict()) if review else None
        ),
        "exports": _exports_payload(workspace),
        "runs": _runs_payload(workspace),
        "jobs": sorted(jobs, key=lambda item: str(item["created_at"]), reverse=True),
    }


def _record_job_event(
    job: WorkspaceJobRecord,
    status_value: JobStatus,
    details: dict[str, Any] | None = None,
) -> None:
    job.status = status_value
    job.updated_at = utcnow_iso()
    job.events.append(
        {"timestamp": job.updated_at, "status": status_value, "details": details or {}}
    )


def _safe_error_message(exc: BaseException, workspace: NovelWorkspace) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return _sanitize_string(workspace, message)


def _store_failure_artifact(
    workspace: NovelWorkspace,
    job: WorkspaceJobRecord,
    exc: BaseException,
) -> dict[str, Any]:
    path = workspace.jobs_dir / f"{job.job_id}.failure.json"
    payload = {
        "job_id": job.job_id,
        "workspace_id": job.workspace_id,
        "operation": job.operation,
        "provider": job.provider,
        "error": _safe_error_message(exc, workspace),
        "exception_type": exc.__class__.__name__,
        "traceback": "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        ),
        "timestamp": utcnow_iso(),
    }
    _atomic_write_json(path, payload)
    return {
        "artifact_id": path.name,
        "filename": path.name,
        "relative_path": workspace.relative_path(path),
        "size": path.stat().st_size,
    }


async def _execute_job(
    job: WorkspaceJobRecord,
    workspace: NovelWorkspace,
    request: WorkspaceJobRequest,
) -> None:
    _record_job_event(job, "running")
    _store_job(workspace, job)
    try:
        with workspace.acquire_lock(operation=request.operation):
            provider_name = cast(TextGenerationProviderName, job.provider)
            if request.operation == "draft":
                chapter_number = request.chapter or workspace.latest_chapter_number() + 1
                artifact = await LocalDraftingEngine(
                    _build_provider(provider_name)
                ).draft_chapter(workspace, chapter_number)
                job.result = _artifact_result_from_draft(workspace, artifact)
            elif request.operation == "run":
                engine = LocalDraftingEngine(_build_provider(provider_name))
                target = request.target_chapters or workspace.load_config().target_chapters
                run_dir = workspace.start_run("run")
                for chapter_number in range(1, target + 1):
                    await engine.draft_chapter(workspace, chapter_number, run_dir=run_dir)
                report = await LocalReviewer(
                    _build_review_provider(provider_name)
                ).review_async(workspace)
                workspace.append_event(
                    run_dir,
                    "review",
                    "completed",
                    {"blockers": len(report.blockers), "warnings": len(report.warnings)},
                )
                workspace.append_event(
                    run_dir,
                    "run",
                    "completed",
                    {"target_chapters": target, "export_blocked": report.export_blocked},
                )
                job.result = _run_result_payload(report.to_dict(), run_dir.name)
            elif request.operation == "review":
                report = await LocalReviewer(
                    _build_review_provider(provider_name)
                ).review_async(workspace)
                job.result = _review_result_payload(report.to_dict())
            elif request.operation == "revise":
                report = workspace.latest_review() or await LocalReviewer(
                    _build_review_provider(provider_name)
                ).review_async(workspace)
                chapter_number = request.chapter or workspace.latest_chapter_number()
                if chapter_number < 1:
                    raise ValueError("No chapter available to revise")
                artifact = await LocalDraftingEngine(
                    _build_provider(provider_name)
                ).revise_chapter(workspace, chapter_number, report)
                job.result = _artifact_result_from_draft(workspace, artifact)
            else:
                exported = LocalExporter().export_markdown(workspace)
                job.result = _export_result_payload(
                    workspace,
                    _artifact_ref_from_path(workspace, exported),
                )
        _record_job_event(job, "completed")
    except asyncio.CancelledError:
        job.error = "Job was cancelled before completion."
        _record_job_event(job, "interrupted", {"reason": "cancelled"})
        raise
    except Exception as exc:
        job.error = _safe_error_message(exc, workspace)
        job.failure_artifact = _store_failure_artifact(workspace, job, exc)
        _record_job_event(job, "failed", {"failure_artifact": job.failure_artifact})
    finally:
        _store_job(workspace, job)


async def _run_job_task(
    key: JobKey,
    job: WorkspaceJobRecord,
    workspace: NovelWorkspace,
    payload: WorkspaceJobRequest,
) -> None:
    try:
        await asyncio.to_thread(lambda: asyncio.run(_execute_job(job, workspace, payload)))
    finally:
        with _job_registry_lock:
            _tasks.pop(key, None)


@providers_router.get("/providers", response_model=ProviderListResponse)
async def list_providers() -> dict[str, Any]:
    """Return configured provider options for writing jobs."""
    settings = get_settings()
    default_provider = _default_provider_name()
    labels = {
        "mock": "mock offline demo",
        "dashscope": "DashScope",
        "openai_compatible": "OpenAI compatible",
    }
    providers = []
    for provider_name in ("mock", "dashscope", "openai_compatible"):
        providers.append(
            {
                "provider": provider_name,
                "label": labels[provider_name],
                "configured": _provider_is_configured(provider_name),
                "is_default": provider_name == default_provider,
                "model": settings.llm.resolved_model(provider_name),
            }
        )
    return {"default_provider": default_provider, "providers": providers}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=WorkspaceStatusResponse,
)
async def create_workspace(
    payload: WorkspaceCreateRequest,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
) -> dict[str, Any]:
    """Create a local-first writing workspace."""
    resolved_principal = _require_principal(principal)
    workspace_id = _workspace_id(payload.workspace_id, title=payload.title)
    config = StoryConfig(
        title=payload.title,
        genre=payload.genre,
        premise=payload.premise,
        target_chapters=payload.target_chapters,
        tone=payload.tone,
        target_audience=payload.target_audience,
        themes=payload.themes,
        style_profile={
            "chapter_shape": "complete prose chapter",
            "voice": "specific, concrete, non-template prose",
        },
    )
    try:
        workspace = NovelWorkspace.create(
            _workspace_path(resolved_principal, workspace_id),
            config,
            overwrite=payload.force,
        )
    except FileExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return _workspace_status(workspace_id, workspace, _principal_key(resolved_principal))


@router.get("", response_model=WorkspaceListResponse)
async def list_workspaces(
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
) -> dict[str, Any]:
    """List local-first workspaces for the active principal."""
    resolved_principal = _require_principal(principal)
    root = _principal_root(resolved_principal)
    workspaces = []
    for path in sorted(root.iterdir()):
        if not path.is_dir() or not (path / "story.yaml").exists():
            continue
        workspaces.append(
            _workspace_status(
                path.name,
                NovelWorkspace(path),
                _principal_key(resolved_principal),
            )
        )
    return {"workspaces": workspaces}


@router.get("/{workspace_id}", response_model=WorkspaceStatusResponse)
async def get_workspace(
    workspace_id: str,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
) -> dict[str, Any]:
    """Return workspace status."""
    resolved_principal = _require_principal(principal)
    workspace = _existing_workspace(resolved_principal, workspace_id)
    return _workspace_status(workspace_id, workspace, _principal_key(resolved_principal))


@router.post(
    "/{workspace_id}/jobs",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=WorkspaceJobResponse,
)
async def create_workspace_job(
    workspace_id: str,
    payload: WorkspaceJobRequest,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
) -> dict[str, Any]:
    """Run a local workspace job and record status."""
    resolved_principal = _require_principal(principal)
    workspace = _existing_workspace(resolved_principal, workspace_id)
    provider_name = _effective_job_provider(payload.operation, payload.provider)
    job = WorkspaceJobRecord(
        job_id=str(uuid4()),
        principal_key=_principal_key(resolved_principal),
        workspace_id=workspace_id,
        operation=payload.operation,
        status="queued",
        created_at=utcnow_iso(),
        updated_at=utcnow_iso(),
        provider=provider_name,
    )
    _record_job_event(job, "queued")
    _store_job(workspace, job)
    key = _job_key(job)
    task = asyncio.create_task(_run_job_task(key, job, workspace, payload))
    with _job_registry_lock:
        _tasks[key] = task
    return _job_public_payload(workspace, job)


@router.get("/{workspace_id}/jobs/{job_id}", response_model=WorkspaceJobResponse)
async def get_workspace_job(
    workspace_id: str,
    job_id: str,
    principal: WorkspacePrincipal | None = Depends(get_workspace_principal),
) -> dict[str, Any]:
    """Return process-local job state."""
    resolved_principal = _require_principal(principal)
    workspace = _existing_workspace(resolved_principal, workspace_id)
    principal_key = _principal_key(resolved_principal)
    key = _job_lookup_key(
        principal_key=principal_key,
        workspace_id=workspace_id,
        job_id=job_id,
    )
    with _job_registry_lock:
        job = _jobs.get(key)
        task_is_active = key in _tasks
    job = job or _load_job(_job_path(workspace, job_id))
    if (
        job is None
        or job.workspace_id != workspace_id
        or job.principal_key != principal_key
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    if job.status in {"queued", "running"} and not task_is_active:
        job.error = "Job was interrupted before completion."
        _record_job_event(job, "interrupted", {"reason": "process_restart"})
        _store_job(workspace, job)
    return _job_public_payload(workspace, job)


__all__ = ["providers_router", "reset_workspace_jobs", "router"]
