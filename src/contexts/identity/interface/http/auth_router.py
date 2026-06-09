"""Authentication HTTP router.

This module provides REST API endpoints for user authentication,
including login, token refresh, and logout functionality.
"""

# mypy: disable-error-code=misc

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer
from pydantic import AliasChoices, BaseModel, Field

from src.apps.api.dependencies import (
    CurrentUser,
    get_authentication_service,
    get_current_user,
    get_current_user_optional,
    get_identity_service,
    user_workspace_id,
)
from src.apps.api.routes.guest import (
    GUEST_SESSION_COOKIE,
    GUEST_SESSION_MAX_AGE_SECONDS,
)
from src.apps.api.services import runtime_store
from src.contexts.identity.application.services.authentication_service import (
    AuthenticationService,
)
from src.contexts.identity.application.services.identity_service import (
    IdentityApplicationService,
)
from src.contexts.identity.interface.http.error_handlers import (
    ResultErrorHandler,
)
from src.shared.infrastructure.auth.refresh_sessions import get_refresh_session_store
from src.shared.infrastructure.auth.session_cookies import (
    ACCESS_TOKEN_COOKIE,
    REFRESH_TOKEN_COOKIE,
    REFRESH_TOKEN_PATH,
)
from src.shared.infrastructure.config.settings import get_settings

security = HTTPBearer(auto_error=False)

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
    },
)


class LoginRequest(BaseModel):
    """Login request model."""

    email: str = Field(
        ...,
        description="Username or email",
        min_length=1,
        validation_alias=AliasChoices("email", "username"),
    )
    password: str = Field(..., description="Password", min_length=1)


class LoginUserResponse(BaseModel):
    """User information returned alongside login tokens."""

    id: str = Field(..., description="User ID")
    name: str = Field(..., description="Display name")
    email: str = Field(..., description="Email address")
    roles: list[str] = Field(default_factory=list, description="User roles")


class SessionResponse(BaseModel):
    """Browser session summary returned after authentication."""

    workspace_id: str = Field(..., description="Active workspace identifier")
    identity_kind: str = Field(default="user", description="Resolved session identity kind")
    workspace_kind: str = Field(default="user", description="Resolved workspace kind")
    active_workspace: dict[str, str] = Field(
        default_factory=dict,
        description="Resolved active workspace summary",
    )
    user: LoginUserResponse = Field(..., description="Authenticated user profile")
    expires_in: Optional[int] = Field(
        None, description="Access token expiration in seconds"
    )


class TokenRefreshRequest(BaseModel):
    """Token refresh request model."""

    refresh_token: str | None = Field(
        default=None,
        description="Legacy API-client refresh token; browsers use HttpOnly cookies.",
        min_length=1,
    )


class UserResponse(BaseModel):
    """User information response model."""

    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    roles: list[str] = Field(default_factory=list, description="User roles")


class CurrentUserResponse(UserResponse):
    """Current user plus the server-owned workspace namespace."""

    workspace_id: str = Field(..., description="Active workspace identifier")
    identity_kind: str = Field(default="user", description="Resolved identity kind")
    workspace_kind: str = Field(default="user", description="Resolved workspace kind")
    active_workspace: dict[str, str] = Field(
        default_factory=dict,
        description="Resolved active workspace summary",
    )


class RegisterRequest(BaseModel):
    """User registration request model."""

    email: str = Field(..., description="Email address")
    username: str = Field(..., description="Username", min_length=3)
    password: str = Field(..., description="Password", min_length=8)


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


def _set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
) -> None:
    settings = get_settings()
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.security.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.security.refresh_token_expire_days * 24 * 60 * 60,
        path=REFRESH_TOKEN_PATH,
    )


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(key=REFRESH_TOKEN_COOKIE, path=REFRESH_TOKEN_PATH)
    response.delete_cookie(key=GUEST_SESSION_COOKIE, path="/")


def _active_workspace_payload(workspace_id: str) -> dict[str, str]:
    return {
        "workspace_id": workspace_id,
        "workspace_kind": "user",
        "label": "Signed-in workspace",
        "persistence": "persistent",
        "summary": "Stable author workspace bound to the authenticated identity.",
    }


def _roles_from_user(user: dict[str, object]) -> list[str]:
    roles = user.get("roles", [])
    if not isinstance(roles, list):
        return []
    return [str(role) for role in roles]


def _session_response_from_user(
    user: dict[str, object],
    workspace_id: str,
) -> SessionResponse:
    return SessionResponse(
        workspace_id=workspace_id,
        active_workspace=_active_workspace_payload(workspace_id),
        user=LoginUserResponse(
            id=str(user["id"]),
            name=str(user["username"]),
            email=str(user["email"]),
            roles=_roles_from_user(user),
        ),
    )


@router.post(
    "/login",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user and establish an HttpOnly browser session.",
)
async def login(
    response: Response,
    credentials: LoginRequest,
    auth_service: AuthenticationService = Depends(get_authentication_service),
) -> SessionResponse:
    """Authenticate user with username and password.

    Args:
        credentials: Login credentials (username/email and password).
        auth_service: Authentication service dependency.

    Returns:
        SessionResponse containing the resolved user workspace.

    Raises:
        HTTPException: If authentication fails.
    """
    result = await auth_service.authenticate_user(
        credentials.email,
        credentials.password,
    )

    data = ResultErrorHandler.handle(result, "login")
    user = data["user"]
    workspace_id = user_workspace_id(
        user_id=str(user["id"]),
        username=str(user["username"]),
    )
    session = await runtime_store.create_or_resume_guest_session(workspace_id)
    _set_workspace_cookie(response, session.workspace_id)

    refresh_issue = get_refresh_session_store().create(
        user_id=str(user["id"]),
        expires_in_days=get_settings().security.refresh_token_expire_days,
        user_snapshot={
            "id": str(user["id"]),
            "username": str(user["username"]),
            "email": str(user["email"]),
            "roles": list(user.get("roles", [])),
        },
    )
    _set_auth_cookies(
        response,
        access_token=str(data["access_token"]),
        refresh_token=refresh_issue.raw_token,
    )

    return _session_response_from_user(user, session.workspace_id)


@router.post(
    "/refresh",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Rotate the refresh cookie and issue a new browser session cookie.",
)
async def refresh_token(
    response: Response,
    request: Request,
    payload: TokenRefreshRequest | None = Body(default=None),
    auth_service: AuthenticationService = Depends(get_authentication_service),
) -> SessionResponse:
    """Refresh access token.

    Args:
        request: HTTP request containing the refresh cookie.
        auth_service: Authentication service dependency.

    Returns:
        SessionResponse containing the current user workspace.

    Raises:
        HTTPException: If token refresh fails.
    """
    raw_refresh_token = payload.refresh_token if payload is not None else None
    if not raw_refresh_token:
        raw_refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if not raw_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh session is required",
        )

    refresh_issue = get_refresh_session_store().rotate(
        raw_token=raw_refresh_token,
        expires_in_days=get_settings().security.refresh_token_expire_days,
    )
    if refresh_issue is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh session is invalid or expired",
        )

    access_token = await auth_service.generate_token(
        refresh_issue.session.user_id,
        "access",
    )
    _set_auth_cookies(
        response,
        access_token=access_token,
        refresh_token=refresh_issue.raw_token,
    )

    user = refresh_issue.session.user_snapshot
    workspace_id = user_workspace_id(
        user_id=str(user["id"]),
        username=str(user["username"]),
    )
    session = await runtime_store.create_or_resume_guest_session(workspace_id)
    _set_workspace_cookie(response, session.workspace_id)
    return _session_response_from_user(user, session.workspace_id)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="User logout",
    description="Revoke the current refresh session and clear browser cookies.",
)
async def logout(
    request: Request,
    response: Response,
    user: CurrentUser | None = Depends(get_current_user_optional),
) -> dict:
    """User logout.

    Args:
        request: HTTP request containing the refresh cookie.
        response: HTTP response used to clear cookies.
        user: Current authenticated user.

    Returns:
        Success message.
    """
    del user
    get_refresh_session_store().revoke(request.cookies.get(REFRESH_TOKEN_COOKIE))
    _clear_session_cookies(response)
    return {"message": "Successfully logged out"}


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get information about the currently authenticated user.",
)
async def get_current_user_info(
    response: Response,
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUserResponse:
    """Get current user information.

    Args:
        user: Current authenticated user.

    Returns:
        UserResponse containing user information.
    """
    workspace_id = user_workspace_id(user_id=user.user_id, username=user.username)
    _set_workspace_cookie(response, workspace_id)
    return CurrentUserResponse(
        id=user.user_id,
        username=user.username,
        email=user.email,
        roles=user.roles,
        workspace_id=workspace_id,
        active_workspace=_active_workspace_payload(workspace_id),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account.",
)
async def register(
    request: RegisterRequest,
    identity_service: IdentityApplicationService = Depends(get_identity_service),
) -> UserResponse:
    """Register a new user.

    Args:
        request: Registration request containing user details.
        identity_service: Identity service dependency.

    Returns:
        UserResponse containing created user information.

    Raises:
        HTTPException: If registration fails.
    """
    result = await identity_service.register_user(
        email=request.email,
        username=request.username,
        password=request.password,
    )

    user = ResultErrorHandler.handle(result, "register")
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        roles=user.roles,
    )
