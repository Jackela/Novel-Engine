from __future__ import annotations

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.api.deps import get_settings
from src.api.schemas import (
    AuthResponse,
    CSRFTokenResponse,
    LoginRequest,
    RefreshTokenRequest,
)
from src.api.settings import APISettings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


class LogoutRequest(BaseModel):
    access_token: Optional[str] = Field(
        None, description="Optional access token to invalidate"
    )


class LogoutResponse(BaseModel):
    success: bool
    message: str


class TokenValidationResponse(BaseModel):
    valid: bool
    expires_at: Optional[int] = Field(
        None, description="Token expiry timestamp in milliseconds"
    )
    user_id: Optional[str] = None
    error: Optional[str] = None


@router.post("/api/auth/login", response_model=AuthResponse)
async def login(
    credentials: LoginRequest,
    response: Response,
    settings: APISettings = Depends(get_settings),
):
    try:
        if not credentials.email or not credentials.password:
            raise HTTPException(
                status_code=400, detail="Email and password are required"
            )

        user_data = {
            "id": str(uuid.uuid4()),
            "email": credentials.email,
            "name": credentials.email.split("@")[0],
            "role": "user",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        access_token_expires = datetime.now(UTC) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        refresh_token_expires = datetime.now(UTC) + timedelta(days=30)

        access_token_payload = {
            "user_id": user_data["id"],
            "email": user_data["email"],
            "exp": access_token_expires,
            "iat": datetime.now(UTC),
            "type": "access",
        }

        refresh_token_payload = {
            "user_id": user_data["id"],
            "email": user_data["email"],
            "exp": refresh_token_expires,
            "iat": datetime.now(UTC),
            "type": "refresh",
        }

        access_token = jwt.encode(
            access_token_payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        refresh_token = jwt.encode(
            refresh_token_payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        cookie_max_age = (
            settings.refresh_cookie_max_age_seconds
            if credentials.remember_me
            else settings.cookie_max_age_seconds
        )

        response.set_cookie(
            key=settings.cookie_name,
            value=access_token,
            httponly=settings.cookie_httponly,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=settings.cookie_max_age_seconds,
        )

        response.set_cookie(
            key=settings.refresh_cookie_name,
            value=refresh_token,
            httponly=settings.cookie_httponly,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=cookie_max_age,
        )

        logger.info("User login successful (cookies set)")

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            user=user_data,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Login failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Login failed: {exc}")


@router.post("/api/auth/refresh", response_model=AuthResponse)
async def refresh_token(
    payload: RefreshTokenRequest,
    response: Response,
    request: Request,
    settings: APISettings = Depends(get_settings),
):
    try:
        refresh_token_value = (
            request.cookies.get(settings.refresh_cookie_name) or payload.refresh_token
        )
        if not refresh_token_value:
            raise HTTPException(status_code=401, detail="No refresh token provided")

        try:
            token_payload = jwt.decode(
                refresh_token_value,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )

            if token_payload.get("type") != "refresh":
                raise HTTPException(status_code=401, detail="Invalid token type")

            user_id = token_payload.get("user_id")
            email = token_payload.get("email")

            if not user_id or not email:
                raise HTTPException(status_code=401, detail="Invalid token payload")

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Refresh token has expired")
        except jwt.InvalidTokenError as exc:
            raise HTTPException(status_code=401, detail=f"Invalid refresh token: {exc}")

        user_data = {
            "id": user_id,
            "email": email,
            "name": email.split("@")[0],
            "role": "user",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }

        access_token_expires = datetime.now(UTC) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        access_token_payload = {
            "user_id": user_id,
            "email": email,
            "exp": access_token_expires,
            "iat": datetime.now(UTC),
            "type": "access",
        }
        access_token = jwt.encode(
            access_token_payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        response.set_cookie(
            key=settings.cookie_name,
            value=access_token,
            httponly=settings.cookie_httponly,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            max_age=settings.cookie_max_age_seconds,
        )

        logger.info("Token refreshed for user: %s", email)

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token_value,
            token_type="Bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            user=user_data,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Token refresh failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {exc}")


@router.get("/api/auth/csrf-token", response_model=CSRFTokenResponse)
async def get_csrf_token(
    response: Response,
    settings: APISettings = Depends(get_settings),
):
    try:
        csrf_token = secrets.token_urlsafe(32)

        response.set_cookie(
            key=settings.csrf_cookie_name,
            value=csrf_token,
            httponly=False,
            secure=settings.cookie_secure,
            samesite="strict",
            max_age=settings.csrf_cookie_max_age_seconds,
        )

        logger.debug("CSRF token generated and set")
        return CSRFTokenResponse(csrf_token=csrf_token)

    except Exception as exc:
        logger.error("CSRF token generation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate CSRF token: {exc}"
        )


@router.post("/api/auth/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    body: Optional[LogoutRequest] = None,
    settings: APISettings = Depends(get_settings),
):
    try:
        auth_header = request.headers.get("Authorization", "")
        token: Optional[str] = None

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        elif body and body.access_token:
            token = body.access_token

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        masked_token = f"{token[:10]}..." if token and len(token) > 10 else "no-token"

        logger.info(
            "Logout event: token=%s, ip=%s, ua=%s",
            masked_token,
            client_ip,
            user_agent[:50],
        )

        response.delete_cookie(
            key=settings.cookie_name,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
        )
        response.delete_cookie(
            key=settings.refresh_cookie_name,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
        )
        response.delete_cookie(
            key=settings.csrf_cookie_name,
            secure=settings.cookie_secure,
            samesite="strict",
        )

        logger.info("Authentication cookies cleared successfully")
        return LogoutResponse(success=True, message="Logout successful")

    except Exception as exc:
        logger.warning("Logout encountered an error (still returning success): %s", exc)
        return LogoutResponse(success=True, message="Logout successful")


@router.get("/api/auth/validate", response_model=TokenValidationResponse)
async def validate_token(
    request: Request,
    settings: APISettings = Depends(get_settings),
):
    try:
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content=TokenValidationResponse(
                    valid=False,
                    error="Missing or invalid Authorization header",
                ).model_dump(),
            )

        token = auth_header[7:]
        if not token:
            return JSONResponse(
                status_code=401,
                content=TokenValidationResponse(
                    valid=False, error="No token provided"
                ).model_dump(),
            )

        try:
            payload = jwt.decode(
                token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
            )

            exp = payload.get("exp")
            user_id = payload.get("user_id") or payload.get("sub")

            if exp:
                from datetime import timezone

                exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
                now = datetime.now(timezone.utc)

                if now > exp_datetime:
                    return JSONResponse(
                        status_code=401,
                        content=TokenValidationResponse(
                            valid=False, error="Token has expired"
                        ).model_dump(),
                    )

                expires_at_ms = int(exp * 1000)
                return TokenValidationResponse(
                    valid=True, expires_at=expires_at_ms, user_id=user_id
                )

            return TokenValidationResponse(valid=True, user_id=user_id)

        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content=TokenValidationResponse(
                    valid=False, error="Token has expired"
                ).model_dump(),
            )
        except jwt.InvalidTokenError as exc:
            return JSONResponse(
                status_code=401,
                content=TokenValidationResponse(
                    valid=False, error=f"Invalid token: {exc}"
                ).model_dump(),
            )

    except Exception as exc:
        logger.error("Token validation error: %s", exc)
        return JSONResponse(
            status_code=401,
            content=TokenValidationResponse(
                valid=False, error="Token validation failed"
            ).model_dump(),
        )
