from __future__ import annotations

import shutil

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import StreamingResponse

from src.api.deps import (
    get_guest_session_manager,
    get_settings,
    get_workspace_store,
    require_workspace_id,
)
from src.api.schemas import GuestSessionResponse
from src.api.settings import APISettings
from src.workspaces import FilesystemWorkspaceStore, GuestSessionManager
from src.workspaces.guest_session import _assert_safe_cookie_value
from src.workspaces.filesystem import _safe_extract_zip_bytes, _validate_workspace_id

router = APIRouter(tags=["Guest"])


@router.post("/guest/session", response_model=GuestSessionResponse)
async def create_or_resume_guest_session(
    request: Request,
    response: Response,
    settings: APISettings = Depends(get_settings),
    manager: GuestSessionManager = Depends(get_guest_session_manager),
    store: FilesystemWorkspaceStore = Depends(get_workspace_store),
) -> GuestSessionResponse:
    token = request.cookies.get(manager.cookie_name)
    workspace_id = manager.decode(token) if token else None
    if workspace_id:
        store.get_or_create(workspace_id)
        return GuestSessionResponse(workspace_id=workspace_id, created=False)

    workspace = store.create()
    safe_cookie = _assert_safe_cookie_value(
        manager.encode(_validate_workspace_id(workspace.id))
    )
    response.set_cookie(
        manager.cookie_name,
        safe_cookie,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=manager.cookie_max_age_seconds(),
    )
    return GuestSessionResponse(workspace_id=workspace.id, created=True)


@router.get("/workspace/export")
async def export_workspace_zip(
    request: Request,
    workspace_id: str = Depends(require_workspace_id),
    settings: APISettings = Depends(get_settings),
    store: FilesystemWorkspaceStore = Depends(get_workspace_store),
) -> StreamingResponse:
    zip_bytes = store.export_zip(workspace_id)
    filename = f"workspace-{workspace_id}.zip"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    streaming = StreamingResponse(
        iter([zip_bytes]), media_type="application/zip", headers=headers
    )
    return streaming


@router.post("/workspace/import", response_model=GuestSessionResponse)
async def import_workspace_zip(
    request: Request,
    response: Response,
    archive: UploadFile = File(...),
    settings: APISettings = Depends(get_settings),
    store: FilesystemWorkspaceStore = Depends(get_workspace_store),
    manager: GuestSessionManager = Depends(get_guest_session_manager),
) -> GuestSessionResponse:
    zip_bytes = await archive.read()
    workspace = store.create()
    try:
        _safe_extract_zip_bytes(zip_bytes, workspace.root)
        store.get_or_create(workspace.id)
    except ValueError as err:
        shutil.rmtree(workspace.root, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(err)) from err
    except Exception as err:
        shutil.rmtree(workspace.root, ignore_errors=True)
        raise HTTPException(status_code=500, detail="Import failed") from err

    safe_workspace_id = _validate_workspace_id(workspace.id)
    safe_cookie = _assert_safe_cookie_value(manager.encode(safe_workspace_id))
    response.set_cookie(
        manager.cookie_name,
        safe_cookie,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=manager.cookie_max_age_seconds(),
    )
    return GuestSessionResponse(workspace_id=workspace.id, created=True)
