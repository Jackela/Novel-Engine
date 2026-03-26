"""Knowledge application services."""

from __future__ import annotations

__all__ = [
    "KnowledgeApplicationService",
    "KnowledgeService",  # Deprecated: Use KnowledgeApplicationService
    "TokenTracker",
    "TokenTrackerConfig",
    "TokenAwareConfig",
    "TrackingContext",
    "create_token_tracker",
]


# Lazy imports to avoid circular dependencies
def __getattr__(name: str):
    if name == "KnowledgeApplicationService" or name == "KnowledgeService":
        from src.contexts.knowledge.application.services.knowledge_service import (
            KnowledgeApplicationService,
        )

        if name == "KnowledgeService":
            return KnowledgeApplicationService  # Alias
        return KnowledgeApplicationService
    elif name == "TokenTracker":
        from src.contexts.knowledge.application.services.token_tracker import (
            TokenTracker,
        )

        return TokenTracker
    elif name == "TokenTrackerConfig":
        from src.contexts.knowledge.application.services.token_tracker_config import (
            TokenTrackerConfig,
        )

        return TokenTrackerConfig
    elif name == "TokenAwareConfig":
        from src.contexts.knowledge.application.services.token_tracker_config import (
            TokenAwareConfig,
        )

        return TokenAwareConfig
    elif name == "TrackingContext":
        from src.contexts.knowledge.application.services.tracking_context import (
            TrackingContext,
        )

        return TrackingContext
    elif name == "create_token_tracker":
        from src.contexts.knowledge.application.services.token_tracker import (
            create_token_tracker,
        )

        return create_token_tracker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
