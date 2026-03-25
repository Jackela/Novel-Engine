"""Persistence layer for knowledge context.

This module provides database models and persistence utilities
for the knowledge context.
"""

from src.contexts.knowledge.infrastructure.persistence.models import (
    Base,
    DocumentModel,
    KnowledgeBaseModel,
)

__all__ = [
    "Base",
    "KnowledgeBaseModel",
    "DocumentModel",
]
