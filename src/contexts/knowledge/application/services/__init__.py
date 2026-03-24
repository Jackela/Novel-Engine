"""Knowledge application services."""

from __future__ import annotations

from src.contexts.knowledge.application.services.knowledge_service import (
    KnowledgeApplicationService,
)

__all__ = [
    "KnowledgeApplicationService",
    "KnowledgeService",  # Deprecated: Use KnowledgeApplicationService
]

# Backward compatibility alias
KnowledgeService = KnowledgeApplicationService
