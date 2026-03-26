"""Dashboard and orchestration routes for the canonical API."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.apps.api.routes.guest import (
    GUEST_SESSION_COOKIE,
    GUEST_SESSION_MAX_AGE_SECONDS,
)
from src.apps.api.runtime import runtime_store
from src.shared.infrastructure.config.settings import get_settings

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _default_character_names() -> list[str]:
    settings = get_settings()
    characters_dir = settings.base_dir / "characters"
    if not characters_dir.exists():
        return []

    return sorted(
        path.name
        for path in characters_dir.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )[:3]


class OrchestrationRequest(BaseModel):
    """Start orchestration request payload."""

    character_names: list[str] = Field(default_factory=_default_character_names)
    total_turns: int = Field(default=3, ge=1, le=12)
    workspace_id: str | None = None


def _set_workspace_cookie(response: Response, workspace_id: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=GUEST_SESSION_COOKIE,
        value=workspace_id,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=GUEST_SESSION_MAX_AGE_SECONDS,
        path="/",
    )


async def _resolve_stream_workspace_id(request: Request) -> str:
    """Resolve the workspace for SSE delivery and ensure it exists."""
    runtime_service = runtime_store
    workspace_id = request.query_params.get("workspace_id") or request.cookies.get(
        GUEST_SESSION_COOKIE
    )
    if workspace_id:
        await runtime_service.create_or_resume_guest_session(workspace_id)
        return workspace_id

    session = await runtime_service.create_or_resume_guest_session(None)
    return session.workspace_id


@router.get("/status")
async def dashboard_status(
    request: Request,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    """Return the current dashboard snapshot."""
    runtime_service = runtime_store
    resolved_workspace_id = workspace_id or request.cookies.get(GUEST_SESSION_COOKIE)
    if resolved_workspace_id:
        await runtime_service.create_or_resume_guest_session(resolved_workspace_id)

    return await runtime_service.get_dashboard_status(resolved_workspace_id)


@router.get("/orchestration")
async def orchestration_status(
    request: Request,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    """Return the current orchestration state."""
    runtime_service = runtime_store
    resolved_workspace_id = workspace_id or request.cookies.get(GUEST_SESSION_COOKIE)
    if resolved_workspace_id:
        await runtime_service.create_or_resume_guest_session(resolved_workspace_id)

    return await runtime_service.get_snapshot(resolved_workspace_id)


@router.post("/orchestration/start")
async def start_orchestration(
    request: Request,
    response: Response,
    payload: OrchestrationRequest,
) -> dict[str, Any]:
    """Start a dashboard orchestration run."""
    runtime_service = runtime_store
    cookie_workspace = request.cookies.get(GUEST_SESSION_COOKIE)

    if cookie_workspace:
        session = await runtime_service.create_or_resume_guest_session(cookie_workspace)
    else:
        session = await runtime_service.create_or_resume_guest_session(
            payload.workspace_id
        )
        _set_workspace_cookie(response, session.workspace_id)

    try:
        orchestration = await runtime_service.start_orchestration(
            payload.character_names,
            total_turns=payload.total_turns,
            workspace_id=session.workspace_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return orchestration


@router.post("/orchestration/pause")
async def pause_orchestration(
    request: Request,
    payload: OrchestrationRequest | None = None,
) -> dict[str, Any]:
    """Pause the active orchestration run."""
    runtime_service = runtime_store
    cookie_workspace = request.cookies.get(GUEST_SESSION_COOKIE)
    resolved_workspace_id = cookie_workspace or (payload.workspace_id if payload else None)
    if resolved_workspace_id:
        await runtime_service.create_or_resume_guest_session(resolved_workspace_id)

    return await runtime_service.pause_orchestration(resolved_workspace_id)


@router.post("/orchestration/stop")
async def stop_orchestration(
    request: Request,
    payload: OrchestrationRequest | None = None,
) -> dict[str, Any]:
    """Stop the active orchestration run."""
    runtime_service = runtime_store
    cookie_workspace = request.cookies.get(GUEST_SESSION_COOKIE)
    resolved_workspace_id = cookie_workspace or (payload.workspace_id if payload else None)
    if resolved_workspace_id:
        await runtime_service.create_or_resume_guest_session(resolved_workspace_id)

    return await runtime_service.stop_orchestration(resolved_workspace_id)


@router.get("/events/stream")
async def stream_events(request: Request) -> StreamingResponse:
    """Server-Sent Events stream for dashboard updates."""
    runtime_service = runtime_store
    workspace_id = await _resolve_stream_workspace_id(request)

    subscriber = await runtime_service.register_subscriber(workspace_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        yield "retry: 3000\n\n"

        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    event = await asyncio.wait_for(subscriber.get(), timeout=15)
                except asyncio.TimeoutError:
                    event = runtime_service._build_event(
                        workspace_id=workspace_id,
                        event_type="system",
                        title="Heartbeat",
                        description="Dashboard connection is alive",
                        data=await runtime_service.get_snapshot(workspace_id),
                    )

                yield f"event: {event['type']}\n"
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        finally:
            runtime_service.unregister_subscriber(workspace_id, subscriber)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
