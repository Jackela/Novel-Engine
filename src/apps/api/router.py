"""Canonical API router registration."""

from __future__ import annotations

from fastapi import APIRouter

from src.apps.api.routes.dashboard import router as dashboard_router
from src.apps.api.routes.guest import router as guest_router
from src.apps.api.routes.world import router as world_router
from src.contexts.identity.interface.http.auth_router import router as auth_router
from src.contexts.knowledge.interface.http.knowledge_router import (
    router as knowledge_router,
)

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(guest_router)
api_router.include_router(dashboard_router)
api_router.include_router(knowledge_router)
api_router.include_router(world_router)
