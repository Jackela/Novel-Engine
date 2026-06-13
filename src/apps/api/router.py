"""Novel Studio API router registration."""

from __future__ import annotations

from fastapi import APIRouter

from src.contexts.studio.interface.http.router import router as studio_router

api_router = APIRouter()

api_router.include_router(studio_router)
