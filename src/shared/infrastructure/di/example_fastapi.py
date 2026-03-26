"""Example: Using DI Container in FastAPI Application.

This module demonstrates how to integrate the DI container
with a FastAPI application.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException

# Import DI container components
from src.shared.infrastructure.di import (
    ApplicationContainer,
    container_lifespan,
    get_authentication_service,
    get_current_user,
)
from src.shared.infrastructure.di.providers import get_container


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager with DI container.

    This lifespan handler:
    1. Initializes the DI container
    2. Configures it from application settings
    3. Manages resource lifecycle (startup/shutdown)
    """
    # Get or create global container
    container = get_container()

    # Configure container from settings
    from src.shared.infrastructure.config.settings import get_settings

    settings = get_settings()
    container.config.from_dict(
        {
            "database": {
                "url": settings.database.url,
                "max_connections": settings.database.pool_size,
            },
            "security": {
                "secret_key": settings.security.secret_key,
                "algorithm": settings.security.algorithm,
                "access_token_expire_minutes": settings.security.access_token_expire_minutes,
                "refresh_token_expire_days": settings.security.refresh_token_expire_days,
            },
            "honcho": {
                "base_url": "https://api.honcho.dev",
                "api_key": None,  # Load from environment
            },
        }
    )

    # Use container lifespan for resource management
    async with container_lifespan(container):
        # Store container in app state for access in endpoints
        app.state.container = container
        yield


# Create FastAPI app with DI container lifespan
app = FastAPI(
    title="Novel Engine API",
    version="0.1.0",
    lifespan=app_lifespan,
)


@app.post("/auth/login")
async def login(
    username: str,
    password: str,
    auth_service=Depends(get_authentication_service),
):
    """Login endpoint using DI container.

    The auth_service is automatically injected by the DI container.
    """
    result = await auth_service.authenticate_user(username, password)

    if result.is_error:
        raise HTTPException(
            status_code=401,
            detail=result.error,
        )

    return result.value


@app.post("/auth/refresh")
async def refresh_token(
    refresh_token: str,
    auth_service=Depends(get_authentication_service),
):
    """Refresh access token."""
    result = await auth_service.refresh_access_token(refresh_token)

    if result.is_error:
        raise HTTPException(
            status_code=401,
            detail=result.error,
        )

    return result.value


@app.get("/users/me")
async def get_current_user_info(
    user: dict = Depends(get_current_user),
):
    """Get current user info from JWT token.

    The user is automatically extracted from the Authorization header
    and validated using the JWT manager from the DI container.
    """
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "novel-engine"}


# Example: Direct container access (for advanced use cases)
@app.get("/system/info")
async def system_info():
    """Get system information using direct container access."""
    container: ApplicationContainer = app.state.container

    # Access core services directly
    jwt_manager = container.core.jwt_manager()

    return {
        "jwt_algorithm": jwt_manager._algorithm,
        "token_expiry_minutes": jwt_manager._access_token_expire_minutes,
    }


# Example: Custom dependency with container access
def get_knowledge_service():
    """Custom dependency factory."""
    container = get_container()
    return container.knowledge.knowledge_service()


if __name__ == "__main__":
    import uvicorn

    # Run the application
    uvicorn.run(app, host="0.0.0.0", port=8000)
