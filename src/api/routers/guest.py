from __future__ import annotations

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
    result = manager.resolve_or_create(token)
    if result.created:
        response.set_cookie(
            manager.cookie_name,
            manager.encode(result.workspace_id),
            httponly=True,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=manager.cookie_max_age_seconds(),
        )
    return GuestSessionResponse(
        workspace_id=result.workspace_id, created=result.created
    )


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
) -> GuestSessionResponse:
    zip_bytes = await archive.read()
    try:
        workspace = store.import_zip(zip_bytes)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err

    return GuestSessionResponse(workspace_id=workspace.id, created=True)
