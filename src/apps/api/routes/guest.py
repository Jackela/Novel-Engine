"""Guest session routes for the canonical API."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from src.apps.api.runtime import runtime_store
from src.shared.infrastructure.config.settings import get_settings

router = APIRouter(prefix="/guest", tags=["guest"])

GUEST_SESSION_COOKIE = "novel_engine_workspace"
GUEST_SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30


class GuestSessionResponse(BaseModel):
    """Guest session response payload."""

    workspace_id: str
    created: bool = Field(default=True)


@router.post("/session", response_model=GuestSessionResponse)
async def create_or_resume_guest_session(
    request: Request,
    response: Response,
) -> GuestSessionResponse:
    """Create or resume a guest workspace session."""
    settings = get_settings()
    cookie_workspace = request.cookies.get(GUEST_SESSION_COOKIE)
    session = await runtime_store.create_or_resume_guest_session(cookie_workspace)

    response.set_cookie(
        key=GUEST_SESSION_COOKIE,
        value=session.workspace_id,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=GUEST_SESSION_MAX_AGE_SECONDS,
        path="/",
    )

    return GuestSessionResponse(
        workspace_id=session.workspace_id,
        created=session.is_new_session,
    )
