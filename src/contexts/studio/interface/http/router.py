"""Public Novel Studio HTTP contract."""

from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable
from functools import wraps
from pathlib import Path
from typing import (
    Annotated,
    Any,
    Literal,
    NoReturn,
    ParamSpec,
    TypeVar,
)

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.contexts.studio.application.services import (
    CSRF_COOKIE,
    GUEST_TTL,
    SESSION_COOKIE,
    Principal,
    studio_store,
)
from src.contexts.studio.domain.exceptions import (
    InvalidOperation,
    NotFound,
    RevisionConflict,
)
from src.contexts.studio.domain.types import DocumentKind, ExportFormat
from src.shared.infrastructure.config.settings import get_settings

router = APIRouter(tags=["studio"])

P = ParamSpec("P")
T = TypeVar("T")


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


def _raise_http(exc: NotFound | RevisionConflict | InvalidOperation) -> NoReturn:
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


def _handle_domain_exceptions(
    handler: Callable[P, Awaitable[T]],
) -> Callable[P, Awaitable[T]]:
    @wraps(handler)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await handler(*args, **kwargs)
        except (NotFound, RevisionConflict, InvalidOperation) as exc:
            _raise_http(exc)

    return wrapper


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


def _csrf_cookie(
    response: Response,
    token: str,
    *,
    max_age: int | None,
) -> None:
    response.set_cookie(
        CSRF_COOKIE,
        token,
        httponly=False,
        secure=get_settings().is_production,
        samesite="lax",
        max_age=max_age,
        path="/",
    )


_CSRF_EXEMPT_PATHS = {
    "/api/setup",
    "/api/session/login",
    "/api/session/guest",
}


def get_principal(
    request: Request,
    novel_studio_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> Principal:
    principal = studio_store.principal_from_token(novel_studio_session)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Owner or guest session required.",
        )
    if (
        request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and request.url.path not in _CSRF_EXEMPT_PATHS
    ):
        cookie_token = request.cookies.get(CSRF_COOKIE)
        header_token = request.headers.get("X-CSRF-Token")
        if not cookie_token or not header_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing.",
            )
        if not secrets.compare_digest(cookie_token, header_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token invalid.",
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
@_handle_domain_exceptions
async def setup_owner(payload: OwnerSetupRequest) -> dict[str, Any]:
    return studio_store.setup_owner(payload.username, payload.password)


@router.post("/session/login")
@_handle_domain_exceptions
async def login(payload: LoginRequest, response: Response) -> dict[str, Any]:
    token, csrf_token, principal = studio_store.create_owner_session(
        payload.username,
        payload.password,
    )
    max_age = 60 * 60 * 24 * 30
    _session_cookie(response, token, max_age=max_age)
    _csrf_cookie(response, csrf_token, max_age=max_age)
    return _principal_payload(principal)


@router.post("/session/guest", status_code=status.HTTP_201_CREATED)
async def guest_session(response: Response) -> dict[str, Any]:
    token, csrf_token, principal = studio_store.create_guest_session()
    max_age = int(GUEST_TTL.total_seconds())
    _session_cookie(response, token, max_age=max_age)
    _csrf_cookie(response, csrf_token, max_age=max_age)
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
    principal: PrincipalDependency,
) -> Response:
    studio_store.logout(principal.session_id)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
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
@_handle_domain_exceptions
async def create_project(
    payload: ProjectRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return studio_store.create_project(
        principal,
        title=payload.title,
        description=payload.description,
    )


@router.get("/projects/{project_id}")
@_handle_domain_exceptions
async def get_project(project_id: str, principal: PrincipalDependency) -> dict[str, Any]:
    return studio_store.get_project(principal, project_id)


@router.patch("/projects/{project_id}")
@_handle_domain_exceptions
async def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return studio_store.update_project(
        principal,
        project_id,
        title=payload.title,
        description=payload.description,
        settings=payload.settings,
    )


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
@_handle_domain_exceptions
async def delete_project(
    project_id: str,
    principal: PrincipalDependency,
) -> Response:
    studio_store.delete_project(principal, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/projects/{project_id}/documents", status_code=status.HTTP_201_CREATED)
@_handle_domain_exceptions
async def create_document(
    project_id: str,
    payload: DocumentCreateRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return studio_store.create_document(
        principal,
        project_id,
        kind=payload.kind,
        title=payload.title,
        content_markdown=payload.content_markdown,
        position=payload.position,
        metadata=payload.metadata,
    )


@router.put("/projects/{project_id}/documents/reorder")
@_handle_domain_exceptions
async def reorder_documents(
    project_id: str,
    payload: ReorderRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return {
        "documents": studio_store.reorder_documents(
            principal,
            project_id,
            payload.document_ids,
        )
    }


@router.get("/projects/{project_id}/documents/{document_id}")
@_handle_domain_exceptions
async def get_document(
    project_id: str,
    document_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return studio_store.get_document(principal, project_id, document_id)


@router.put("/projects/{project_id}/documents/{document_id}")
@_handle_domain_exceptions
async def save_document(
    project_id: str,
    document_id: str,
    payload: DocumentSaveRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return studio_store.save_document(
        principal,
        project_id,
        document_id,
        content_markdown=payload.content_markdown,
        base_revision_id=payload.base_revision_id,
        title=payload.title,
        metadata=payload.metadata,
    )


@router.delete(
    "/projects/{project_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
@_handle_domain_exceptions
async def delete_document(
    project_id: str,
    document_id: str,
    principal: PrincipalDependency,
) -> Response:
    studio_store.delete_document(principal, project_id, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/projects/{project_id}/documents/{document_id}/revisions")
@_handle_domain_exceptions
async def list_revisions(
    project_id: str,
    document_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return {
        "revisions": studio_store.list_revisions(
            principal,
            project_id,
            document_id,
        )
    }


@router.post(
    "/projects/{project_id}/documents/{document_id}/revisions/{revision_id}/restore"
)
@_handle_domain_exceptions
async def restore_revision(
    project_id: str,
    document_id: str,
    revision_id: str,
    payload: DocumentRestoreRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return studio_store.restore_revision(
        principal,
        project_id,
        document_id,
        revision_id,
        base_revision_id=payload.base_revision_id,
    )


@router.get("/projects/{project_id}/search")
@_handle_domain_exceptions
async def search_project(
    project_id: str,
    q: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return {"results": studio_store.search(principal, project_id, q)}


@router.get("/projects/{project_id}/snapshots")
@_handle_domain_exceptions
async def list_snapshots(
    project_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return {"snapshots": studio_store.list_snapshots(principal, project_id)}


@router.post(
    "/projects/{project_id}/snapshots",
    status_code=status.HTTP_201_CREATED,
)
@_handle_domain_exceptions
async def create_snapshot(
    project_id: str,
    payload: SnapshotRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return studio_store.create_snapshot(
        principal,
        project_id,
        reason=payload.reason,
    )


@router.post("/projects/{project_id}/documents/{document_id}/ai-proposals")
@_handle_domain_exceptions
async def create_ai_proposal(
    project_id: str,
    document_id: str,
    payload: AIProposalRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return await studio_store.create_ai_proposal(
        principal,
        project_id,
        document_id,
        operation=payload.operation,
        instruction=payload.instruction,
        provider=payload.provider,
        model=get_settings().llm.resolved_model(payload.provider),
    )


@router.post("/projects/{project_id}/ai-proposals/{job_id}/accept")
@_handle_domain_exceptions
async def accept_ai_proposal(
    project_id: str,
    job_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return studio_store.accept_ai_proposal(principal, project_id, job_id)


@router.get("/projects/{project_id}/jobs")
@_handle_domain_exceptions
async def list_jobs(project_id: str, principal: PrincipalDependency) -> dict[str, Any]:
    return {"jobs": studio_store.list_jobs(principal, project_id)}


@router.post("/projects/{project_id}/jobs/{job_id}/retry")
@_handle_domain_exceptions
async def retry_job(
    project_id: str,
    job_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return await studio_store.retry_job(principal, project_id, job_id)


@router.post("/projects/{project_id}/reviews", status_code=status.HTTP_201_CREATED)
@_handle_domain_exceptions
async def create_review(
    project_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return studio_store.review_project(principal, project_id)


@router.get("/projects/{project_id}/reviews")
@_handle_domain_exceptions
async def list_reviews(
    project_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return {"reviews": studio_store.list_reviews(principal, project_id)}


@router.post("/projects/{project_id}/exports", status_code=status.HTTP_201_CREATED)
@_handle_domain_exceptions
async def create_export(
    project_id: str,
    payload: ExportRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return studio_store.export_project(
        principal,
        project_id,
        export_format=payload.format,
    )


@router.get("/projects/{project_id}/exports")
@_handle_domain_exceptions
async def list_exports(
    project_id: str,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    return {"exports": studio_store.list_exports(principal, project_id)}


@router.get("/projects/{project_id}/exports/{export_id}/download")
@_handle_domain_exceptions
async def download_export(
    project_id: str,
    export_id: str,
    principal: PrincipalDependency,
) -> FileResponse:
    path = studio_store.export_path(principal, project_id, export_id)
    return FileResponse(path, filename=path.name)


@router.post("/imports/preview")
@_handle_domain_exceptions
async def preview_import(
    payload: LegacyPathRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    _require_owner(principal)
    return studio_store.preview_legacy_workspace(_web_import_source(payload.source))


@router.post("/imports", status_code=status.HTTP_201_CREATED)
@_handle_domain_exceptions
async def import_workspace(
    payload: LegacyPathRequest,
    principal: PrincipalDependency,
) -> dict[str, Any]:
    _require_owner(principal)
    return studio_store.import_legacy_workspace(
        principal,
        _web_import_source(payload.source),
    )


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
