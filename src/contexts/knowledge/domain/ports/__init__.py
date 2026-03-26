"""Knowledge domain ports.

This module defines the ports (interfaces) for the knowledge context,
following the hexagonal architecture pattern.
"""

from __future__ import annotations

from .document_repository_port import DocumentRepositoryPort
from .knowledge_repository_port import KnowledgeRepositoryPort

__all__ = ["KnowledgeRepositoryPort", "DocumentRepositoryPort"]
