from fastapi import APIRouter

from src.contexts.studio.interface.http.project_router import project_router
from src.contexts.studio.interface.http.session_router import (
    get_principal,
    session_router,
)
from src.contexts.studio.interface.http.workflow_router import workflow_router

router = APIRouter()
router.include_router(session_router)
router.include_router(project_router)
router.include_router(workflow_router)

__all__ = ["get_principal", "router"]
