"""
Brain Router

Aggregates all brain-related endpoints:
- Settings: API keys, RAG config, knowledge base status
- Usage: Token usage analytics, streaming, model pricing
- Ingestion: Async ingestion jobs
- RAG Context: Context retrieval
- Chat: Chat completion and session management
"""

from fastapi import APIRouter

from src.api.routers.brain.endpoints import (
    chat,
    ingestion,
    rag_context,
    settings,
    usage,
)

router = APIRouter(tags=["brain-settings"])

# Include all sub-routers with appropriate prefixes
router.include_router(settings.router, prefix="/brain")
router.include_router(usage.router, prefix="/brain")
router.include_router(ingestion.router, prefix="/brain")
router.include_router(rag_context.router, prefix="/brain")
router.include_router(chat.router, prefix="/brain")

# Re-export for backward compatibility
from src.api.routers.brain.repositories.brain_settings import (
    BrainSettingsRepository,
    InMemoryBrainSettingsRepository,
)
from src.api.routers.brain.repositories.ingestion import IngestionJob, IngestionJobStore
from src.api.routers.brain.repositories.token_usage import InMemoryTokenUsageRepository
from src.api.routers.brain.services.usage_broadcaster import (
    RealtimeUsageBroadcaster,
    get_usage_broadcaster,
)

__all__ = [
    # Router
    "router",
    # Repositories
    "BrainSettingsRepository",
    "InMemoryBrainSettingsRepository",
    "InMemoryTokenUsageRepository",
    "IngestionJob",
    "IngestionJobStore",
    # Services
    "RealtimeUsageBroadcaster",
    "get_usage_broadcaster",
]
