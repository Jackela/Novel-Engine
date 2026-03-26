"""
Knowledge Ingestion Service

Service for ingesting knowledge into the system.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SourceType(Enum):
    """Types of knowledge sources."""

    DOCUMENT = "document"
    URL = "url"
    API = "api"
    MANUAL = "manual"


@dataclass
class RetrievedChunk:
    """A retrieved chunk of knowledge."""

    content: str
    score: float
    source_type: SourceType
    metadata: dict[str, Any]


class KnowledgeIngestionService:
    """Service for ingesting knowledge."""

    pass
