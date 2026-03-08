"""Structure router package for narrative outline management.

This package provides CRUD endpoints for managing Story, Chapter, Scene,
Beat, Conflict, Plotline, and Foreshadowing entities.

Why this structure:
    The original structure.py grew to 2800+ lines, making it difficult
    to navigate and maintain. Splitting by domain entity improves
    readability and enables parallel development.
"""

from fastapi import APIRouter

from . import (
    beats,
    chapters,
    conflicts,
    foreshadowing,
    plotlines,
    scenes,
    stories,
)
from .common import (
    get_repository,
    reset_conflict_storage,
    reset_foreshadowing_storage,
    reset_plotline_storage,
    reset_scene_storage,
)

router = APIRouter(prefix="/structure", tags=["structure"])

# Include all sub-routers
router.include_router(stories.router)
router.include_router(chapters.router)
router.include_router(scenes.router)
router.include_router(beats.router)
router.include_router(conflicts.router)
router.include_router(plotlines.router)
router.include_router(foreshadowing.router)

__all__ = [
    "router",
    "get_repository",
    "reset_scene_storage",
    "reset_conflict_storage",
    "reset_plotline_storage",
    "reset_foreshadowing_storage",
]
