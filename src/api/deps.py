from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, Response

from src.api.settings import APISettings
from src.workspaces import (
    FilesystemCharacterStore,
    FilesystemWorkspaceStore,
    GuestSessionManager,
)


def get_settings(request: Request) -> APISettings:
    settings = getattr(request.app.state, "settings", None)
    if not settings:
        settings = APISettings.from_env()
        request.app.state.settings = settings
    return settings


def get_workspace_store(request: Request) -> FilesystemWorkspaceStore:
    store = getattr(request.app.state, "workspace_store", None)
    if not store:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")
    return store


def get_workspace_character_store(request: Request) -> FilesystemCharacterStore:
    store = getattr(request.app.state, "workspace_character_store", None)
    if not store:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")
    return store


def get_guest_session_manager(request: Request) -> GuestSessionManager:
    manager = getattr(request.app.state, "guest_session_manager", None)
    if not manager:
        raise HTTPException(status_code=503, detail="Workspace service unavailable")
    return manager


def get_optional_workspace_id(
    request: Request,
    manager: GuestSessionManager = Depends(get_guest_session_manager),
    store: FilesystemWorkspaceStore = Depends(get_workspace_store),
) -> Optional[str]:
    token = request.cookies.get(manager.cookie_name)
    if not token:
        default_workspace_id = getattr(request.app.state, "default_workspace_id", None)
        if default_workspace_id:
            store.get_or_create(default_workspace_id)
            return default_workspace_id
        return None
    workspace_id = manager.decode(token)
    if not workspace_id:
        return None
    store.get_or_create(workspace_id)
    return workspace_id


def require_workspace_id(
    request: Request,
    response: Response,
    settings: APISettings = Depends(get_settings),
    manager: GuestSessionManager = Depends(get_guest_session_manager),
    store: FilesystemWorkspaceStore = Depends(get_workspace_store),
) -> str:
    token = request.cookies.get(manager.cookie_name)
    if not token:
        default_workspace_id = getattr(request.app.state, "default_workspace_id", None)
        if default_workspace_id:
            response.set_cookie(
                manager.cookie_name,
                manager.encode(default_workspace_id),
                httponly=settings.cookie_httponly,
                secure=settings.cookie_secure,
                samesite=settings.cookie_samesite,
                max_age=manager.cookie_max_age_seconds(),
            )
            store.get_or_create(default_workspace_id)
            return default_workspace_id
    result = manager.resolve_or_create(token)

    response.set_cookie(
        manager.cookie_name,
        manager.encode(result.workspace_id),
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=manager.cookie_max_age_seconds(),
    )
    return result.workspace_id
