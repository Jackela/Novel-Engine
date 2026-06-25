from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response, status

from src.contexts.studio.interface.http.dependencies import StudioStoreDependency
from src.contexts.studio.interface.http.errors import _handle_domain_exceptions
from src.contexts.studio.interface.http.schemas import (
    DocumentCreateRequest,
    DocumentRestoreRequest,
    DocumentSaveRequest,
    ProjectRequest,
    ProjectUpdateRequest,
    ReorderRequest,
    SnapshotRequest,
)
from src.contexts.studio.interface.http.session_router import PrincipalDependency

project_router = APIRouter(tags=["studio"])


@project_router.get("/projects")
async def list_projects(
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return {"projects": store.list_projects(principal)}


@project_router.post("/projects", status_code=status.HTTP_201_CREATED)
@_handle_domain_exceptions
async def create_project(
    payload: ProjectRequest,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return store.create_project(
        principal,
        title=payload.title,
        description=payload.description,
    )


@project_router.get("/projects/{project_id}")
@_handle_domain_exceptions
async def get_project(
    project_id: str,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return store.get_project(principal, project_id)


@project_router.patch("/projects/{project_id}")
@_handle_domain_exceptions
async def update_project(
    project_id: str,
    payload: ProjectUpdateRequest,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return store.update_project(
        principal,
        project_id,
        title=payload.title,
        description=payload.description,
        settings=payload.settings,
    )


@project_router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
@_handle_domain_exceptions
async def delete_project(
    project_id: str,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> Response:
    store.delete_project(principal, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@project_router.post(
    "/projects/{project_id}/documents",
    status_code=status.HTTP_201_CREATED,
)
@_handle_domain_exceptions
async def create_document(
    project_id: str,
    payload: DocumentCreateRequest,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return store.create_document(
        principal,
        project_id,
        kind=payload.kind,
        title=payload.title,
        content_markdown=payload.content_markdown,
        position=payload.position,
        metadata=payload.metadata,
    )


@project_router.put("/projects/{project_id}/documents/reorder")
@_handle_domain_exceptions
async def reorder_documents(
    project_id: str,
    payload: ReorderRequest,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return {
        "documents": store.reorder_documents(
            principal,
            project_id,
            payload.document_ids,
        )
    }


@project_router.get("/projects/{project_id}/documents/{document_id}")
@_handle_domain_exceptions
async def get_document(
    project_id: str,
    document_id: str,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return store.get_document(principal, project_id, document_id)


@project_router.put("/projects/{project_id}/documents/{document_id}")
@_handle_domain_exceptions
async def save_document(
    project_id: str,
    document_id: str,
    payload: DocumentSaveRequest,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return store.save_document(
        principal,
        project_id,
        document_id,
        content_markdown=payload.content_markdown,
        base_revision_id=payload.base_revision_id,
        title=payload.title,
        metadata=payload.metadata,
    )


@project_router.delete(
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
    store: StudioStoreDependency,
) -> Response:
    store.delete_document(principal, project_id, document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@project_router.get("/projects/{project_id}/documents/{document_id}/revisions")
@_handle_domain_exceptions
async def list_revisions(
    project_id: str,
    document_id: str,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return {
        "revisions": store.list_revisions(
            principal,
            project_id,
            document_id,
        )
    }


@project_router.post(
    "/projects/{project_id}/documents/{document_id}/revisions/{revision_id}/restore"
)
@_handle_domain_exceptions
async def restore_revision(
    project_id: str,
    document_id: str,
    revision_id: str,
    payload: DocumentRestoreRequest,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return store.restore_revision(
        principal,
        project_id,
        document_id,
        revision_id,
        base_revision_id=payload.base_revision_id,
    )


@project_router.get("/projects/{project_id}/search")
@_handle_domain_exceptions
async def search_project(
    project_id: str,
    q: str,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return {"results": store.search(principal, project_id, q)}


@project_router.get("/projects/{project_id}/snapshots")
@_handle_domain_exceptions
async def list_snapshots(
    project_id: str,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return {"snapshots": store.list_snapshots(principal, project_id)}


@project_router.post(
    "/projects/{project_id}/snapshots",
    status_code=status.HTTP_201_CREATED,
)
@_handle_domain_exceptions
async def create_snapshot(
    project_id: str,
    payload: SnapshotRequest,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return store.create_snapshot(
        principal,
        project_id,
        reason=payload.reason,
    )
