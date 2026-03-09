"""
Chunking Strategy Module

Provides chunking strategies for text processing with support for
fixed-size, sentence, paragraph, semantic, narrative, and auto-detection
approaches.

This module implements the Strategy pattern for chunking, allowing
different algorithms to be used interchangeably.

Example:
    >>> from chunking import ChunkingStrategyFactory, ChunkStrategyType
    >>> factory = ChunkingStrategyFactory()
    >>> strategy = factory.create(ChunkStrategyType.SENTENCE)
    >>> chunks = await strategy.chunk(text, config)

    >>> # With coherence analysis
    >>> from chunking import ChunkCoherenceAnalyzer
    >>> analyzer = ChunkCoherenceAnalyzer()
    >>> scores = await analyzer.analyze_chunks(chunks, config)
"""

# Base classes and types
from .base import (
    DEFAULT_COHERENCE_THRESHOLD,
    MAX_COHERENCE_THRESHOLD,
    MIN_COHERENCE_THRESHOLD,
    BaseChunkingStrategy,
    CoherenceScore,
)

# Coherence analyzer
from .coherence import ChunkCoherenceAnalyzer

# Factory
from .factory import ChunkingStrategyFactory

# Strategies
from .strategies import (
    AutoSelectStrategy,
    ContentType,
    FixedSizeStrategy,
    NarrativeStructureStrategy,
    ParagraphBoundaryStrategy,
    SemanticSimilarityStrategy,
    SentenceBoundaryStrategy,
)

__all__ = [
    # Base
    "BaseChunkingStrategy",
    "CoherenceScore",
    "DEFAULT_COHERENCE_THRESHOLD",
    "MIN_COHERENCE_THRESHOLD",
    "MAX_COHERENCE_THRESHOLD",
    # Coherence
    "ChunkCoherenceAnalyzer",
    # Factory
    "ChunkingStrategyFactory",
    # Strategies
    "AutoSelectStrategy",
    "ContentType",
    "FixedSizeStrategy",
    "NarrativeStructureStrategy",
    "ParagraphBoundaryStrategy",
    "SemanticSimilarityStrategy",
    "SentenceBoundaryStrategy",
]
