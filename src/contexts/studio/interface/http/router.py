"""Public Novel Studio HTTP contract."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.contexts.studio.application.services import (
    GUEST_TTL,
    SESSION_COOKIE,
    InvalidOperation,
    NotFound,
    Principal,
    RevisionConflict,
    studio_store,
)
from src.contexts.studio.domain.types import DocumentKind, ExportFormat
from src.shared.infrastructure.config.settings import get_settings

router = APIRouter(tags=["studio"])


class OwnerSetupRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=10, max_length=200)


class LoginRequest(BaseModel):
    username: str
    password: str


class ProjectRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=10_000)


class ProjectUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=240)
    description: str | None = Field(default=None, max_length=10_000)
    settings: dict[str, Any] | None = None


class DocumentCreateRequest(BaseModel):
    kind: DocumentKind
    title: str = Field(min_length=1, max_length=240)
    content_markdown: str = ""
    position: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentSaveRequest(BaseModel):
    content_markdown: str
    base_revision_id: str | None
    title: str | None = Field(default=None, max_length=240)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentRestoreRequest(BaseModel):
    base_revision_id: str | None


class ReorderRequest(BaseModel):
    document_ids: list[str] = Field(min_length=1)


class AIProposalRequest(BaseModel):
    operation: Literal["continue", "rewrite", "generate"]
    instruction: str = Field(default="", max_length=10_000)
    provider: Literal["mock", "dashscope", "openai_compatible"] = "mock"


class ExportRequest(BaseModel):
    format: ExportFormat


class LegacyPathRequest(BaseModel):
    source: str = Field(
        min_length=1,
        max_length=240,
        description="Workspace directory name under data/imports.",
    )


class SnapshotRequest(BaseModel):
    reason: str = Field(default="manual", min_length=1, max_length=48)


def _raise_http(exc: Exception) -> None:
    if isinstance(exc, NotFound):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, RevisionConflict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "current_revision_id": exc.current_revision_id,
            },
        ) from exc
    if isinstance(exc, InvalidOperation):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    raise exc


def _session_cookie(
    response: Response,
    token: str,
    *,
    max_age: int | None,
) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=get_settings().is_production,
        samesite="lax",
        max_age=max_age,
        path="/",
    )


def get_principal(
    novel_studio_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> Principal:
    principal = studio_store.principal_from_token(novel_studio_session)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Owner or guest session required.",
        )
    return principal


PrincipalDependency = Annotated[Principal, Depends(get_principal)]


def _require_owner(principal: Principal) -> None:
    if principal.kind != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires the local Owner.",
        )


def _web_import_source(source: str) -> Path:
    if source in {".", ".."} or "/" in source or "\\" in source:
        raise InvalidOperation(
            "Web imports must name a workspace directory under data/imports."
        )

    import_root = (get_settings().data_dir / "imports").resolve()
    import_root.mkdir(parents=True, exist_ok=True)
    for candidate in import_root.iterdir():
        if candidate.name != source or candidate.is_symlink() or not candidate.is_dir():
            continue
        resolved = candidate.resolve()
        if resolved.is_relative_to(import_root):
            return resolved
    raise NotFound("Import workspace not found under data/imports.")


@router.get("/setup")
async def setup_status() -> dict[str, Any]:
    return {
        "owner_configured": studio_store.owner_exists(),
        "version": get_settings().project_version,
    }


@router.post("/setup", status_code=status.HTTP_201_CREATED)
async def setup_owner(payload: OwnerSetupRequest) -> dict[str, Any]:
    try:
        return studio_store.setup_owner(payload.username, payload.password)
    except Exception as exc:
        _raise_http(exc)
        raise


@router.post("/session/login")
async def login(payload: LoginRequest, response: Response) -> dict[str, Any]:
    try:
        token, principal = studio_store.create_owner_session(
            payload.username,
            payload.password,
        )
    except Exception as exc:
        _raise_http(exc)
        raise
    _session_cookie(response, token, max_age=60 * 60 * 24 * 30)
    return _principal_payload(principal)


@router.post("/session/guest", status_code=status.HTTP_201_CREATED)
async def guest_session(response: Response) -> dict[str, Any]:
    token, principal = studio_store.create_guest_session()
    _session_cookie(response, token, max_age=int(GUEST_TTL.total_seconds()))
    return _principal_payload(principal)


@router.get("/session")
async def current_session(principal: PrincipalDependency) -> dict[str, Any]:
    return _principal_payload(principal)


@router.delete(
    "/session",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def logout(
    response: Response,
    novel_studio_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> Response:
    studio_store.logout(novel_studio_session)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/providers")
async def providers(principal: PrincipalDependency) -> dict[str, Any]:
    del principal
    settings = get_settings()
    items = []
    for provider in ("mock", "dashscope", "openai_compatible"):
        items.append(
            {
                "provider": provider,
                "configured": provider == "mock"
                or bool(settings.llm.resolved_api_key(provider)),
                "model": settings.llm.resolved_model(provider),
                "is_default": provider == settings.llm.provider,
            }
        )
    return {"providers": items}


@router.get("/projects")
async def list_projects(principal: PrincipalDependency) -> dict[str, Any]:
    return {"projects": studio_store.list_projects(principal)}


@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return studio_store.create_project(
            principal,
            title=payload.title,
            description=payload.description,
        )
    except Exception as exc:
        _raise_http(exc)
        raise


@router.get("/projects/{project_id}")
async def get_project(project_id: str, principal: PrincipalDependency) -> dict[str, Any]:
    try:
        return studio_store.get_project(principal, project_id)
    except Exception as exc:
        _raise_http(exc)
        raise


@router.patch("/projects/{project_id}")
async def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return studio_store.update_project(
            principal,
            project_id,
            title=payload.title,
            description=payload.description,
            settings=payload.settings,
        )
    except Exception as exc:
        _raise_http(exc)
        raise


@router.post("/projects/{project_id}/documents", status_code=status.HTTP_201_CREATED)
async def create_document(
    project_id: str,
    payload: DocumentCreateRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return studio_store.create_document(
            principal,
            project_id,
            kind=payload.kind,
            title=payload.title,
            content_markdown=payload.content_markdown,
            position=payload.position,
            metadata=payload.metadata,
        )
    except Exception as exc:
        _raise_http(exc)
        raise


@router.put("/projects/{project_id}/documents/reorder")
async def reorder_documents(
    project_id: str,
    payload: ReorderRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return {
            "documents": studio_store.reorder_documents(
                principal,
                project_id,
                payload.document_ids,
            )
        }
    except Exception as exc:
        _raise_http(exc)
        raise


@router.get("/projects/{project_id}/documents/{document_id}")
async def get_document(
    project_id: str,
    document_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return studio_store.get_document(principal, project_id, document_id)
    except Exception as exc:
        _raise_http(exc)
        raise


@router.put("/projects/{project_id}/documents/{document_id}")
async def save_document(
    project_id: str,
    document_id: str,
    payload: DocumentSaveRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return studio_store.save_document(
            principal,
            project_id,
            document_id,
            content_markdown=payload.content_markdown,
            base_revision_id=payload.base_revision_id,
            title=payload.title,
            metadata=payload.metadata,
        )
    except Exception as exc:
        _raise_http(exc)
        raise


@router.get("/projects/{project_id}/documents/{document_id}/revisions")
async def list_revisions(
    project_id: str,
    document_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return {
            "revisions": studio_store.list_revisions(
                principal,
                project_id,
                document_id,
            )
        }
    except Exception as exc:
        _raise_http(exc)
        raise


@router.post(
    "/projects/{project_id}/documents/{document_id}/revisions/{revision_id}/restore"
)
async def restore_revision(
    project_id: str,
    document_id: str,
    revision_id: str,
    payload: DocumentRestoreRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return studio_store.restore_revision(
            principal,
            project_id,
            document_id,
            revision_id,
            base_revision_id=payload.base_revision_id,
        )
    except Exception as exc:
        _raise_http(exc)
        raise


@router.get("/projects/{project_id}/search")
async def search_project(
    project_id: str,
    q: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return {"results": studio_store.search(principal, project_id, q)}
    except Exception as exc:
        _raise_http(exc)
        raise


@router.get("/projects/{project_id}/snapshots")
async def list_snapshots(
    project_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return {"snapshots": studio_store.list_snapshots(principal, project_id)}
    except Exception as exc:
        _raise_http(exc)
        raise


@router.post(
    "/projects/{project_id}/snapshots",
    status_code=status.HTTP_201_CREATED,
)
async def create_snapshot(
    project_id: str,
    payload: SnapshotRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return studio_store.create_snapshot(
            principal,
            project_id,
            reason=payload.reason,
        )
    except Exception as exc:
        _raise_http(exc)
        raise


@router.post("/projects/{project_id}/documents/{document_id}/ai-proposals")
async def create_ai_proposal(
    project_id: str,
    document_id: str,
    payload: AIProposalRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return studio_store.create_ai_proposal(
            principal,
            project_id,
            document_id,
            operation=payload.operation,
            instruction=payload.instruction,
            provider=payload.provider,
            model=get_settings().llm.resolved_model(payload.provider),
        )
    except Exception as exc:
        _raise_http(exc)
        raise


@router.post("/projects/{project_id}/ai-proposals/{job_id}/accept")
async def accept_ai_proposal(
    project_id: str,
    job_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return studio_store.accept_ai_proposal(principal, project_id, job_id)
    except Exception as exc:
        _raise_http(exc)
        raise


@router.get("/projects/{project_id}/jobs")
async def list_jobs(project_id: str, principal: PrincipalDependency) -> dict[str, Any]:
    try:
        return {"jobs": studio_store.list_jobs(principal, project_id)}
    except Exception as exc:
        _raise_http(exc)
        raise


@router.post("/projects/{project_id}/jobs/{job_id}/retry")
async def retry_job(
    project_id: str,
    job_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return studio_store.retry_job(principal, project_id, job_id)
    except Exception as exc:
        _raise_http(exc)
        raise


@router.post("/projects/{project_id}/reviews", status_code=status.HTTP_201_CREATED)
async def create_review(
    project_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return studio_store.review_project(principal, project_id)
    except Exception as exc:
        _raise_http(exc)
        raise


@router.get("/projects/{project_id}/reviews")
async def list_reviews(
    project_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return {"reviews": studio_store.list_reviews(principal, project_id)}
    except Exception as exc:
        _raise_http(exc)
        raise


@router.post("/projects/{project_id}/exports", status_code=status.HTTP_201_CREATED)
async def create_export(
    project_id: str,
    payload: ExportRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return studio_store.export_project(
            principal,
            project_id,
            export_format=payload.format,
        )
    except Exception as exc:
        _raise_http(exc)
        raise


@router.get("/projects/{project_id}/exports")
async def list_exports(
    project_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    try:
        return {"exports": studio_store.list_exports(principal, project_id)}
    except Exception as exc:
        _raise_http(exc)
        raise


@router.get("/projects/{project_id}/exports/{export_id}/download")
async def download_export(
    project_id: str,
    export_id: str,
    principal: PrincipalDependency,
) -> FileResponse:
    try:
        path = studio_store.export_path(principal, project_id, export_id)
        return FileResponse(path, filename=path.name)
    except Exception as exc:
        _raise_http(exc)
        raise


@router.post("/imports/preview")
async def preview_import(
    payload: LegacyPathRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    _require_owner(principal)
    try:
        return studio_store.preview_legacy_workspace(_web_import_source(payload.source))
    except Exception as exc:
        _raise_http(exc)
        raise


@router.post("/imports", status_code=status.HTTP_201_CREATED)
async def import_workspace(
    payload: LegacyPathRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    _require_owner(principal)
    try:
        return studio_store.import_legacy_workspace(
            principal,
            _web_import_source(payload.source),
        )
    except Exception as exc:
        _raise_http(exc)
        raise


def _principal_payload(principal: Principal) -> dict[str, Any]:
    return {
        "session_id": principal.session_id,
        "kind": principal.kind,
        "owner_id": principal.owner_id,
        "expires_at": (
            principal.expires_at.isoformat().replace("+00:00", "Z")
            if principal.expires_at
            else None
        ),
    }


__all__ = ["get_principal", "router"]
