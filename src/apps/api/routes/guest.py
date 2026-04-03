"""Guest session routes for the canonical API."""

# mypy: disable-error-code=misc

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from src.apps.api.runtime import runtime_store
from src.shared.infrastructure.config.settings import get_settings

router = APIRouter(prefix="/guest", tags=["guest"])

GUEST_SESSION_COOKIE = "novel_engine_workspace"
GUEST_SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30


def _guest_workspace_from_cookie(workspace_id: str | None) -> str | None:
    """Only resume canonical guest workspaces from the guest route."""
    if workspace_id is None:
        return None

    normalized = workspace_id.strip()
    if not normalized.startswith("guest-"):
        return None

    return normalized or None


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
    cookie_workspace = _guest_workspace_from_cookie(
        request.cookies.get(GUEST_SESSION_COOKIE)
    )
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
