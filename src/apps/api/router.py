"""
API Router Configuration

Central router aggregation for all API endpoints.
"""

from fastapi import APIRouter

# Create main API router
api_router = APIRouter()


def register_context_routers() -> None:
    """
    Register all context-specific routers.

    This function dynamically imports and registers routers from
    different bounded contexts to maintain loose coupling.
    """
    # Context routers will be registered here
    # These are placeholder imports that will be enabled as contexts are implemented

    # Identity/Authentication Context
    try:
        from src.contexts.identity.interfaces.api import router as identity_router

        api_router.include_router(identity_router, prefix="/auth", tags=["auth"])
    except ImportError:
        pass

    # Narrative Context
    try:
        from src.contexts.narrative.interfaces.api import router as narrative_router

        api_router.include_router(
            narrative_router, prefix="/stories", tags=["narrative"]
        )
    except ImportError:
        pass

    # Character Context
    try:
        from src.contexts.character.interfaces.api import router as character_router

        api_router.include_router(
            character_router, prefix="/characters", tags=["characters"]
        )
    except ImportError:
        pass

    # Knowledge Context
    try:
        from src.contexts.knowledge.interfaces.api import router as knowledge_router

        api_router.include_router(
            knowledge_router, prefix="/knowledge", tags=["knowledge"]
        )
    except ImportError:
        pass


# Register context routers on module load
register_context_routers()
