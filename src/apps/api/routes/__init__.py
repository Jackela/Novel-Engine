"""Canonical API routes for the application."""

from src.apps.api.routes.guest import router as guest_router
from src.apps.api.routes.story import router as story_router

__all__ = ["guest_router", "story_router"]
