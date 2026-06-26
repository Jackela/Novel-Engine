from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse

from src.contexts.studio.domain.exceptions import InvalidOperation, NotFound
from src.contexts.studio.domain.principal import Principal
from src.contexts.studio.interface.http.dependencies import StudioStoreDependency
from src.contexts.studio.interface.http.errors import _handle_domain_exceptions
from src.contexts.studio.interface.http.schemas import (
    AIProposalRequest,
    ExportRequest,
    LegacyPathRequest,
)
from src.contexts.studio.interface.http.session_router import PrincipalDependency

workflow_router = APIRouter(tags=["studio"])


def _require_owner(principal: Principal) -> None:
    if principal.kind != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This operation requires the local Owner.",
        )


def _web_import_source(source: str, data_dir: Path) -> Path:
    if source in {".", ".."} or "/" in source or "\\" in source:
        raise InvalidOperation(
            "Web imports must name a workspace directory under data/imports."
        )

    import_root = (data_dir / "imports").resolve()
    import_root.mkdir(parents=True, exist_ok=True)
    for candidate in import_root.iterdir():
        if candidate.name != source or candidate.is_symlink() or not candidate.is_dir():
            continue
        resolved = candidate.resolve()
        if resolved.is_relative_to(import_root):
            return resolved
    raise NotFound("Import workspace not found under data/imports.")


@workflow_router.post("/projects/{project_id}/documents/{document_id}/ai-proposals")
@_handle_domain_exceptions
async def create_ai_proposal(
    project_id: str,
    document_id: str,
    payload: AIProposalRequest,
    request: Request,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    settings = request.app.state.settings
    return await store.create_ai_proposal(
        principal,
        project_id,
        document_id,
        operation=payload.operation,
        instruction=payload.instruction,
        provider=payload.provider,
        model=settings.llm.resolved_model(payload.provider),
    )


@workflow_router.post("/projects/{project_id}/ai-proposals/{job_id}/accept")
@_handle_domain_exceptions
async def accept_ai_proposal(
    project_id: str,
    job_id: str,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return store.accept_ai_proposal(principal, project_id, job_id)


@workflow_router.get("/projects/{project_id}/jobs")
@_handle_domain_exceptions
async def list_jobs(
    project_id: str,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return {"jobs": store.list_jobs(principal, project_id)}


@workflow_router.post("/projects/{project_id}/jobs/{job_id}/retry")
@_handle_domain_exceptions
async def retry_job(
    project_id: str,
    job_id: str,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return await store.retry_job(principal, project_id, job_id)


@workflow_router.post(
    "/projects/{project_id}/reviews",
    status_code=status.HTTP_201_CREATED,
)
@_handle_domain_exceptions
async def create_review(
    project_id: str,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return store.review_project(principal, project_id)


@workflow_router.get("/projects/{project_id}/reviews")
@_handle_domain_exceptions
async def list_reviews(
    project_id: str,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return {"reviews": store.list_reviews(principal, project_id)}


@workflow_router.post(
    "/projects/{project_id}/exports",
    status_code=status.HTTP_201_CREATED,
)
@_handle_domain_exceptions
async def create_export(
    project_id: str,
    payload: ExportRequest,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return store.export_project(
        principal,
        project_id,
        export_format=payload.format,
    )


@workflow_router.get("/projects/{project_id}/exports")
@_handle_domain_exceptions
async def list_exports(
    project_id: str,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return {"exports": store.list_exports(principal, project_id)}


@workflow_router.get("/projects/{project_id}/exports/{export_id}/download")
@_handle_domain_exceptions
async def download_export(
    project_id: str,
    export_id: str,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> FileResponse:
    path = store.export_path(principal, project_id, export_id)
    return FileResponse(path, filename=path.name)


@workflow_router.post("/imports/preview")
@_handle_domain_exceptions
async def preview_import(
    payload: LegacyPathRequest,
    request: Request,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    _require_owner(principal)
    return store.preview_legacy_workspace(
        _web_import_source(payload.source, request.app.state.settings.data_dir)
    )


@workflow_router.post("/imports", status_code=status.HTTP_201_CREATED)
@_handle_domain_exceptions
async def import_workspace(
    payload: LegacyPathRequest,
    request: Request,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    _require_owner(principal)
    return store.import_legacy_workspace(
        principal,
        _web_import_source(payload.source, request.app.state.settings.data_dir),
    )
