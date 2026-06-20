from __future__ import annotations

import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status

from src.contexts.studio.application.services import (
    CSRF_COOKIE,
    GUEST_TTL,
    SESSION_COOKIE,
)
from src.contexts.studio.domain.principal import Principal
from src.contexts.studio.interface.http.dependencies import StudioStoreDependency
from src.contexts.studio.interface.http.errors import _handle_domain_exceptions
from src.contexts.studio.interface.http.schemas import LoginRequest, OwnerSetupRequest
from src.shared.infrastructure.config.settings import get_settings

session_router = APIRouter(tags=["studio"])


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
    store: StudioStoreDependency,
    novel_studio_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> Principal:
    principal = store.principal_from_token(novel_studio_session)
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


@session_router.get("/setup")
async def setup_status(store: StudioStoreDependency) -> dict[str, Any]:
    return {
        "owner_configured": store.owner_exists(),
        "version": get_settings().project_version,
    }


@session_router.post("/setup", status_code=status.HTTP_201_CREATED)
@_handle_domain_exceptions
async def setup_owner(
    payload: OwnerSetupRequest,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    return store.setup_owner(payload.username, payload.password)


@session_router.post("/session/login")
@_handle_domain_exceptions
async def login(
    payload: LoginRequest,
    response: Response,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    token, csrf_token, principal = store.create_owner_session(
        payload.username,
        payload.password,
    )
    max_age = 60 * 60 * 24 * 30
    _session_cookie(response, token, max_age=max_age)
    _csrf_cookie(response, csrf_token, max_age=max_age)
    return _principal_payload(principal)


@session_router.post("/session/guest", status_code=status.HTTP_201_CREATED)
async def guest_session(
    response: Response,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    token, csrf_token, principal = store.create_guest_session()
    max_age = int(GUEST_TTL.total_seconds())
    _session_cookie(response, token, max_age=max_age)
    _csrf_cookie(response, csrf_token, max_age=max_age)
    return _principal_payload(principal)


@session_router.get("/session")
async def current_session(principal: PrincipalDependency) -> dict[str, Any]:
    return _principal_payload(principal)


@session_router.delete(
    "/session",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def logout(
    response: Response,
    principal: PrincipalDependency,
    store: StudioStoreDependency,
) -> Response:
    store.logout(principal.session_id)
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@session_router.get("/providers")
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
