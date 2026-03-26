"""Canonical API routes for the application."""

from src.apps.api.routes.dashboard import router as dashboard_router
from src.apps.api.routes.guest import router as guest_router

__all__ = ["dashboard_router", "guest_router"]
