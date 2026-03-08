"""
Brain Settings Router (Backward Compatibility)

Warzone 4: AI Brain - BRAIN-033
REST API for managing Brain settings including API keys, RAG configuration,
and knowledge base status.

.. deprecated::
    This module is deprecated. Use `src.api.routers.brain` instead.
    All functionality has been migrated to the new brain router package.

Constitution Compliance:
- Article II (Hexagonal): Router handles HTTP, Service handles business logic
- Article I (DDD): No business logic in router layer
"""

import warnings

# Emit deprecation warning
warnings.warn(
    "brain_settings module is deprecated, use brain module directly. "
    "Import from src.api.routers.brain instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export all symbols from the new brain module
from src.api.routers.brain import (
    BrainSettingsRepository,
    IngestionJob,
    IngestionJobStore,
    InMemoryBrainSettingsRepository,
    InMemoryTokenUsageRepository,
    RealtimeUsageBroadcaster,
    get_usage_broadcaster,
    router,
)
from src.api.routers.brain.core import (
    decrypt_api_key as _decrypt_api_key,
    encrypt_api_key as _encrypt_api_key,
    get_encryption_key,
    get_fernet,
    mask_api_key as _mask_api_key,
    require_encryption as _require_encryption,
)
from src.api.routers.brain.services.ingestion_worker import (
    run_ingestion_job as _run_ingestion_job,
)

__all__ = [
    "router",
    "InMemoryBrainSettingsRepository",
    "BrainSettingsRepository",
    "InMemoryTokenUsageRepository",
    "RealtimeUsageBroadcaster",
    "get_usage_broadcaster",
    "IngestionJobStore",
    "IngestionJob",
    # Encryption utilities (for test compatibility)
    "get_encryption_key",
    "get_fernet",
    # Private functions (for test compatibility)
    "_decrypt_api_key",
    "_encrypt_api_key",
    "_mask_api_key",
    "_require_encryption",
    "_run_ingestion_job",
]
