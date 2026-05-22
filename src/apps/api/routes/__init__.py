"""Canonical API routes for the application."""

from src.apps.api.routes.guest import router as guest_router
from src.apps.api.routes.workspaces import (
    providers_router,
)
from src.apps.api.routes.workspaces import (
    router as workspace_router,
)

__all__ = ["guest_router", "providers_router", "workspace_router"]
