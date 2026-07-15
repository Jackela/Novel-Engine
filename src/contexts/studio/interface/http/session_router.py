from __future__ import annotations

import secrets
from typing import Annotated, Any
from urllib.parse import urlsplit

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

session_router = APIRouter(tags=["studio"])


def _session_cookie(
    response: Response,
    token: str,
    *,
    max_age: int | None,
    secure: bool,
) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=max_age,
        path="/",
    )


def _csrf_cookie(
    response: Response,
    token: str,
    *,
    max_age: int | None,
    secure: bool,
) -> None:
    response.set_cookie(
        CSRF_COOKIE,
        token,
        httponly=False,
        secure=secure,
        samesite="lax",
        max_age=max_age,
        path="/",
    )


_CSRF_EXEMPT_PATHS = {
    "/api/setup",
    "/api/session/login",
    "/api/session/guest",
}
_LOCALHOST_CORS_PORTS = frozenset({"5173", "4173", "8000"})


def _is_configured_setup_origin(origin: str, request: Request) -> bool:
    """Allow exact configured origins and explicit localhost port wildcards."""
    configured = request.app.state.settings.security.cors_origins
    for allowed in configured:
        allowed_origin = allowed.rstrip("/").lower()
        if allowed_origin == "*":
            continue
        if origin == allowed_origin:
            return True
        if not allowed_origin.endswith(":*"):
            continue
        prefix = allowed_origin[:-1]
        local_prefixes = (
            "http://localhost:",
            "https://localhost:",
            "http://127.0.0.1:",
            "https://127.0.0.1:",
        )
        if prefix in local_prefixes and origin.startswith(prefix):
            return origin[len(prefix) :] in _LOCALHOST_CORS_PORTS
    return False


def _is_same_origin_request(request: Request) -> bool:
    """Allow unauthenticated setup only from trusted browser origins.

    First-run setup has no CSRF cookie yet, so browsers need an origin check
    instead.  Requests without browser origin metadata remain allowed for
    local CLI/bootstrap clients that do not send ``Origin`` or ``Referer``.
    """
    expected = f"{request.url.scheme.lower()}://{request.url.netloc.lower()}"
    for header_name in ("origin", "referer"):
        header_value = request.headers.get(header_name)
        if not header_value:
            continue
        parsed = urlsplit(header_value)
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or header_value.strip().lower() == "null"
        ):
            return False
        if header_name == "origin" and (parsed.path or parsed.query or parsed.fragment):
            return False
        try:
            port = parsed.port
        except ValueError:
            return False
        if port is not None and not 1 <= port <= 65535:
            return False
        origin = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
        if origin != expected and not _is_configured_setup_origin(origin, request):
            return False
    return True


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
async def setup_status(
    request: Request, store: StudioStoreDependency
) -> dict[str, Any]:
    return {
        "owner_configured": store.owner_exists(),
        "version": request.app.state.settings.project_version,
    }


@session_router.post("/setup", status_code=status.HTTP_201_CREATED)
@_handle_domain_exceptions
async def setup_owner(
    request: Request,
    payload: OwnerSetupRequest,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    if not _is_same_origin_request(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Setup requests must be same-origin.",
        )
    return store.setup_owner(payload.username, payload.password)


@session_router.post("/session/login")
@_handle_domain_exceptions
async def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    token, csrf_token, principal = store.create_owner_session(
        payload.username,
        payload.password,
    )
    max_age = 60 * 60 * 24 * 30
    secure = (
        request.app.state.settings.is_production
        or request.app.state.settings.is_staging
    )
    _session_cookie(response, token, max_age=max_age, secure=secure)
    _csrf_cookie(response, csrf_token, max_age=max_age, secure=secure)
    return _principal_payload(principal)


@session_router.post("/session/guest", status_code=status.HTTP_201_CREATED)
async def guest_session(
    request: Request,
    response: Response,
    store: StudioStoreDependency,
) -> dict[str, Any]:
    token, csrf_token, principal = store.create_guest_session()
    max_age = int(GUEST_TTL.total_seconds())
    secure = (
        request.app.state.settings.is_production
        or request.app.state.settings.is_staging
    )
    _session_cookie(response, token, max_age=max_age, secure=secure)
    _csrf_cookie(response, csrf_token, max_age=max_age, secure=secure)
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
async def providers(request: Request, principal: PrincipalDependency) -> dict[str, Any]:
    del principal
    settings = request.app.state.settings
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
