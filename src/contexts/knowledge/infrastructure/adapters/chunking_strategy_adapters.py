"""
Chunking Strategy Adapters (Legacy Compatibility)

.. deprecated::
    This module is deprecated. Use the new strategy pattern module:
    `src.contexts.knowledge.infrastructure.chunking` instead.

    Old import:
        from ...infrastructure.adapters.chunking_strategy_adapters import (
            FixedChunkingStrategy,
            SentenceChunkingStrategy,
            ...
        )

    New import:
        from ...infrastructure.chunking import (
            FixedSizeStrategy,
            SentenceBoundaryStrategy,
            ...
        )

Migration Guide:
    - FixedChunkingStrategy -> FixedSizeStrategy
    - SentenceChunkingStrategy -> SentenceBoundaryStrategy
    - ParagraphChunkingStrategy -> ParagraphBoundaryStrategy
    - SemanticChunkingStrategy -> SemanticSimilarityStrategy
    - NarrativeFlowChunkingStrategy -> NarrativeStructureStrategy
    - AutoChunkingStrategy -> AutoSelectStrategy
    - ContentType (unchanged)
    - CoherenceScore (unchanged)
    - ChunkCoherenceAnalyzer (unchanged)

The new module provides a cleaner Strategy pattern implementation with:
    - BaseChunkingStrategy abstract base class
    - ChunkingStrategyFactory for creating strategies
    - Better separation of concerns
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from ..chunking import (
    DEFAULT_COHERENCE_THRESHOLD,
    MAX_COHERENCE_THRESHOLD,
    MIN_COHERENCE_THRESHOLD,
    AutoSelectStrategy,
    ChunkCoherenceAnalyzer,
    ChunkingStrategyFactory,
    CoherenceScore,
    ContentType,
    FixedSizeStrategy,
    NarrativeStructureStrategy,
    ParagraphBoundaryStrategy,
    SemanticSimilarityStrategy,
    SentenceBoundaryStrategy,
)
from ..chunking.base import BaseChunkingStrategy

if TYPE_CHECKING:
    from ...domain.models.chunking_strategy import ChunkingStrategy

# Emit deprecation warning
warnings.warn(
    "chunking_strategy_adapters.py is deprecated. "
    "Use 'from ...infrastructure.chunking import ...' instead. "
    "See module docstring for migration guide.",
    DeprecationWarning,
    stacklevel=2,
)


# Legacy adapter classes that delegate to new implementations
class FixedChunkingStrategy(FixedSizeStrategy):
    """
    Legacy adapter for fixed-size chunking.

    .. deprecated::
        Use FixedSizeStrategy from chunking module instead.
    """

    def __init__(self, default_config: ChunkingStrategy | None = None) -> None:
        warnings.warn(
            "FixedChunkingStrategy is deprecated. Use FixedSizeStrategy.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(default_config)


class SentenceChunkingStrategy(SentenceBoundaryStrategy):
    """
    Legacy adapter for sentence boundary chunking.

    .. deprecated::
        Use SentenceBoundaryStrategy from chunking module instead.
    """

    def __init__(self, default_config: ChunkingStrategy | None = None) -> None:
        warnings.warn(
            "SentenceChunkingStrategy is deprecated. Use SentenceBoundaryStrategy.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(default_config)


class ParagraphChunkingStrategy(ParagraphBoundaryStrategy):
    """
    Legacy adapter for paragraph boundary chunking.

    .. deprecated::
        Use ParagraphBoundaryStrategy from chunking module instead.
    """

    def __init__(self, default_config: ChunkingStrategy | None = None) -> None:
        warnings.warn(
            "ParagraphChunkingStrategy is deprecated. Use ParagraphBoundaryStrategy.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(default_config)


class SemanticChunkingStrategy(SemanticSimilarityStrategy):
    """
    Legacy adapter for semantic similarity chunking.

    .. deprecated::
        Use SemanticSimilarityStrategy from chunking module instead.
    """

    def __init__(
        self,
        embedding_service: Any,
        default_config: ChunkingStrategy | None = None,
    ) -> None:
        warnings.warn(
            "SemanticChunkingStrategy is deprecated. Use SemanticSimilarityStrategy.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(embedding_service, default_config)


class NarrativeFlowChunkingStrategy(NarrativeStructureStrategy):
    """
    Legacy adapter for narrative structure chunking.

    .. deprecated::
        Use NarrativeStructureStrategy from chunking module instead.
    """

    def __init__(
        self,
        default_config: ChunkingStrategy | None = None,
        preserve_dialogue: bool = True,
        preserve_paragraphs: bool = True,
    ) -> None:
        warnings.warn(
            "NarrativeFlowChunkingStrategy is deprecated. "
            "Use NarrativeStructureStrategy.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(default_config, preserve_dialogue, preserve_paragraphs)


class AutoChunkingStrategy(AutoSelectStrategy):
    """
    Legacy adapter for auto-select chunking.

    .. deprecated::
        Use AutoSelectStrategy from chunking module instead.
    """

    def __init__(
        self,
        embedding_service: Any | None = None,
        default_config: ChunkingStrategy | None = None,
    ) -> None:
        warnings.warn(
            "AutoChunkingStrategy is deprecated. Use AutoSelectStrategy.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(embedding_service, default_config)


__all__ = [
    # Legacy constants
    "DEFAULT_COHERENCE_THRESHOLD",
    "MIN_COHERENCE_THRESHOLD",
    "MAX_COHERENCE_THRESHOLD",
    # Legacy types
    "CoherenceScore",
    "ContentType",
    # Legacy analyzers
    "ChunkCoherenceAnalyzer",
    # Legacy strategies (deprecated)
    "FixedChunkingStrategy",
    "SentenceChunkingStrategy",
    "ParagraphChunkingStrategy",
    "SemanticChunkingStrategy",
    "NarrativeFlowChunkingStrategy",
    "AutoChunkingStrategy",
    # New types for migration
    "BaseChunkingStrategy",
    "ChunkingStrategyFactory",
    "FixedSizeStrategy",
    "SentenceBoundaryStrategy",
    "ParagraphBoundaryStrategy",
    "SemanticSimilarityStrategy",
    "NarrativeStructureStrategy",
    "AutoSelectStrategy",
]
