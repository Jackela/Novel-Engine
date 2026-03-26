"""Authentication HTTP router.

This module provides REST API endpoints for user authentication,
including login, token refresh, and logout functionality.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import HTTPBearer
from pydantic import AliasChoices, BaseModel, Field

from src.apps.api.dependencies import (
    CurrentUser,
    get_authentication_service,
    get_current_user,
    get_identity_service,
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
    handle_identity_errors,
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


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    workspace_id: str = Field(..., description="Active workspace identifier")
    user: LoginUserResponse = Field(..., description="Authenticated user profile")
    expires_in: Optional[int] = Field(
        None, description="Access token expiration in seconds"
    )


class TokenRefreshRequest(BaseModel):
    """Token refresh request model."""

    refresh_token: str = Field(..., description="Valid refresh token", min_length=1)


class TokenRefreshResponse(BaseModel):
    """Token refresh response model."""

    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: Optional[int] = Field(
        None, description="Access token expiration in seconds"
    )


class UserResponse(BaseModel):
    """User information response model."""

    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    roles: list[str] = Field(default_factory=list, description="User roles")


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


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user and return access and refresh tokens.",
)
@handle_identity_errors
async def login(
    request: Request,
    response: Response,
    credentials: LoginRequest,
    auth_service: AuthenticationService = Depends(get_authentication_service),
) -> TokenResponse:
    """Authenticate user with username and password.

    Args:
        credentials: Login credentials (username/email and password).
        auth_service: Authentication service dependency.

    Returns:
        TokenResponse containing access and refresh tokens.

    Raises:
        HTTPException: If authentication fails.
    """
    result = await auth_service.authenticate_user(
        credentials.email,
        credentials.password,
    )

    data = ResultErrorHandler.handle(result, "login")
    user = data["user"]
    workspace_id = request.cookies.get(GUEST_SESSION_COOKIE)
    if not workspace_id:
        workspace_id = f"user-{user['username']}"

    session = await runtime_store.create_or_resume_guest_session(workspace_id)
    _set_workspace_cookie(response, session.workspace_id)

    return TokenResponse(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        token_type="bearer",
        workspace_id=session.workspace_id,
        user=LoginUserResponse(
            id=user["id"],
            name=user["username"],
            email=user["email"],
            roles=list(user.get("roles", [])),
        ),
    )


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Generate a new access token using a valid refresh token.",
)
@handle_identity_errors
async def refresh_token(
    request: TokenRefreshRequest,
    auth_service: AuthenticationService = Depends(get_authentication_service),
) -> TokenRefreshResponse:
    """Refresh access token.

    Args:
        request: Token refresh request containing the refresh token.
        auth_service: Authentication service dependency.

    Returns:
        TokenRefreshResponse containing new access token.

    Raises:
        HTTPException: If token refresh fails.
    """
    result = await auth_service.refresh_access_token(request.refresh_token)

    data = ResultErrorHandler.handle(result, "refresh_token")
    return TokenRefreshResponse(
        access_token=data["access_token"],
        token_type="bearer",
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="User logout",
    description="Invalidate user tokens (client-side only in JWT implementation).",
)
@handle_identity_errors
async def logout(user: CurrentUser = Depends(get_current_user)) -> dict:
    """User logout.

    Note: JWT tokens are stateless. This endpoint is mainly for
    client-side token cleanup. Token blacklisting would require
    additional infrastructure (Redis, database, etc.).

    Args:
        user: Current authenticated user.

    Returns:
        Success message.
    """
    return {"message": "Successfully logged out"}


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Get information about the currently authenticated user.",
)
@handle_identity_errors
async def get_current_user_info(
    user: CurrentUser = Depends(get_current_user),
) -> UserResponse:
    """Get current user information.

    Args:
        user: Current authenticated user.

    Returns:
        UserResponse containing user information.
    """
    return UserResponse(
        id=user.user_id,
        username=user.username,
        email=user.email,
        roles=user.roles,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account.",
)
@handle_identity_errors
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
