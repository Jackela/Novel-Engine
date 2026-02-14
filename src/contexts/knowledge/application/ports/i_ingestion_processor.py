"""
IIngestionProcessor Port

Interface for content-specific ingestion processors.

Each processor defines chunking defaults and metadata enrichment
for its source type without implementing embedding or storage logic.

Constitution Compliance:
- Article II (Hexagonal): Application port defining processor contract
- Article V (SOLID): SRP - processor handles content-specific behavior only
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ...domain.models.chunking_strategy import ChunkingStrategy
from ...domain.models.source_type import SourceType


class IIngestionProcessor(ABC):
    """
    Interface for content-specific ingestion processors.

    Processors define:
    - The chunking strategy defaults for their content type
    - Metadata enrichment specific to the content type

    Processors do NOT handle:
    - Embedding generation (handled by IEmbeddingService)
    - Vector storage (handled by IVectorStore)

    Why:
        Separates content-specific concerns from the ingestion pipeline,
        allowing easy addition of new source types and consistent processing.

    Example:
        >>> processor = CharacterProcessor()
        >>> strategy = processor.get_chunking_strategy()
        >>> metadata = processor.enrich_metadata({"name": "Aldric"})
    """

    @property
    @abstractmethod
    def source_type(self) -> SourceType:
        """
        Get the source type this processor handles.

        Returns:
            SourceType enum value for this processor
        """
        ...

    @abstractmethod
    def get_chunking_strategy(
        self, custom_strategy: ChunkingStrategy | None = None
    ) -> ChunkingStrategy:
        """
        Get the chunking strategy for this content type.

        Args:
            custom_strategy: Optional custom strategy to override defaults

        Returns:
            ChunkingStrategy to use for this content type

        Why:
            Allows per-source-type defaults while supporting overrides.
        """
        ...

    @abstractmethod
    def enrich_metadata(
        self,
        base_metadata: dict[str, Any],
        content: str,
    ) -> dict[str, Any]:
        """
        Enrich metadata with content-type-specific information.

        Args:
            base_metadata: Base metadata from the ingestion request
            content: The content being ingested (for analysis)

        Returns:
            Enriched metadata dictionary

        Why:
            Different source types have different metadata needs.
            Characters may need role tracking, locations may need coordinates, etc.
        """
        ...

    def supports_batching(self) -> bool:
        """
        Check if this processor supports batch ingestion optimization.

        Returns:
            True if batching is supported (default)

        Why:
            Some content types may have constraints that prevent batching.
        """
        return True


__all__ = ["IIngestionProcessor"]
