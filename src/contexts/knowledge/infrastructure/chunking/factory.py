"""
Chunking Strategy Factory

Provides factory pattern for creating chunking strategy instances.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from ...application.ports.i_chunking_strategy import ChunkingError
from ...domain.models.chunking_strategy import ChunkStrategyType
from .base import BaseChunkingStrategy
from .strategies.auto import AutoSelectStrategy, ContentType
from .strategies.fixed_size import FixedSizeStrategy
from .strategies.narrative import NarrativeStructureStrategy
from .strategies.paragraph import ParagraphBoundaryStrategy
from .strategies.semantic import SemanticSimilarityStrategy
from .strategies.sentence import SentenceBoundaryStrategy

if TYPE_CHECKING:
    from ...application.ports.i_embedding_service import IEmbeddingService

T = TypeVar("T", bound=BaseChunkingStrategy)


class ChunkingStrategyFactory:
    """
    Factory for creating chunking strategy instances.

    Provides a centralized way to create and configure chunking strategies
    based on strategy type and optional dependencies.

    Example:
        >>> factory = ChunkingStrategyFactory()
        >>> strategy = factory.create(ChunkStrategyType.FIXED)
        >>> chunks = await strategy.chunk(text, config)

        >>> # With embedding service for semantic chunking
        >>> factory = ChunkingStrategyFactory(embedding_service=service)
        >>> strategy = factory.create(ChunkStrategyType.SEMANTIC)
    """

    def __init__(
        self,
        embedding_service: IEmbeddingService | None = None,
    ) -> None:
        """
        Initialize the factory with optional dependencies.

        Args:
            embedding_service: Service for generating embeddings.
                Required for semantic chunking.
        """
        self._embedding_service = embedding_service

    def create(self, strategy_type: ChunkStrategyType | str) -> BaseChunkingStrategy:
        """
        Create a chunking strategy instance.

        Args:
            strategy_type: The type of strategy to create

        Returns:
            Configured strategy instance

        Raises:
            ChunkingError: If strategy type is not supported or
                required dependencies are missing
        """
        if isinstance(strategy_type, str):
            try:
                strategy_type = ChunkStrategyType(strategy_type.lower())
            except ValueError as e:
                raise ChunkingError(
                    f"Unknown strategy type: {strategy_type}",
                    code="UNKNOWN_STRATEGY_TYPE",
                ) from e

        strategy_map = {
            ChunkStrategyType.FIXED: self._create_fixed_strategy,
            ChunkStrategyType.SENTENCE: self._create_sentence_strategy,
            ChunkStrategyType.PARAGRAPH: self._create_paragraph_strategy,
            ChunkStrategyType.SEMANTIC: self._create_semantic_strategy,
            ChunkStrategyType.NARRATIVE_FLOW: self._create_narrative_strategy,
            ChunkStrategyType.AUTO: self._create_auto_strategy,
        }

        creator = strategy_map.get(strategy_type)
        if creator is None:
            raise ChunkingError(
                f"Unsupported strategy type: {strategy_type}",
                code="UNSUPPORTED_STRATEGY_TYPE",
            )

        return creator()

    def create_for_content(
        self,
        content_type: ContentType,
    ) -> BaseChunkingStrategy:
        """
        Create the best strategy for a specific content type.

        Args:
            content_type: Type of content to chunk

        Returns:
            Configured strategy instance optimized for the content type
        """
        auto_strategy = AutoSelectStrategy(
            embedding_service=self._embedding_service,
        )

        # Map content type to strategy and create directly
        if content_type in AutoSelectStrategy.CONTENT_TYPE_STRATEGY_MAP:
            strategy_type = AutoSelectStrategy.CONTENT_TYPE_STRATEGY_MAP[content_type]
            return self.create(strategy_type)

        # Fallback to auto-detection
        return auto_strategy

    def _create_fixed_strategy(self) -> FixedSizeStrategy:
        """Create a fixed-size chunking strategy."""
        return FixedSizeStrategy()

    def _create_sentence_strategy(self) -> SentenceBoundaryStrategy:
        """Create a sentence boundary chunking strategy."""
        return SentenceBoundaryStrategy()

    def _create_paragraph_strategy(self) -> ParagraphBoundaryStrategy:
        """Create a paragraph boundary chunking strategy."""
        return ParagraphBoundaryStrategy()

    def _create_semantic_strategy(self) -> SemanticSimilarityStrategy:
        """Create a semantic similarity chunking strategy."""
        if self._embedding_service is None:
            raise ChunkingError(
                "Embedding service required for semantic chunking",
                code="MISSING_EMBEDDING_SERVICE",
            )
        return SemanticSimilarityStrategy(
            embedding_service=self._embedding_service,
        )

    def _create_narrative_strategy(self) -> NarrativeStructureStrategy:
        """Create a narrative structure chunking strategy."""
        return NarrativeStructureStrategy()

    def _create_auto_strategy(self) -> AutoSelectStrategy:
        """Create an auto-select chunking strategy."""
        return AutoSelectStrategy(
            embedding_service=self._embedding_service,
        )

    @staticmethod
    def get_supported_strategies() -> list[ChunkStrategyType]:
        """
        Get list of supported strategy types.

        Returns:
            List of supported ChunkStrategyType values
        """
        return [
            ChunkStrategyType.FIXED,
            ChunkStrategyType.SENTENCE,
            ChunkStrategyType.PARAGRAPH,
            ChunkStrategyType.SEMANTIC,
            ChunkStrategyType.NARRATIVE_FLOW,
            ChunkStrategyType.AUTO,
        ]

    @staticmethod
    def get_strategy_description(strategy_type: ChunkStrategyType) -> str:
        """
        Get description for a strategy type.

        Args:
            strategy_type: Strategy type to describe

        Returns:
            Human-readable description of the strategy
        """
        descriptions = {
            ChunkStrategyType.FIXED: (
                "Fixed-size chunking with configurable overlap. "
                "Simple and predictable, works well for most content."
            ),
            ChunkStrategyType.SENTENCE: (
                "Sentence-aware chunking that preserves sentence boundaries. "
                "Better semantic coherence than fixed-size."
            ),
            ChunkStrategyType.PARAGRAPH: (
                "Paragraph-aware chunking that preserves document structure. "
                "Best for structured documents."
            ),
            ChunkStrategyType.SEMANTIC: (
                "Semantic similarity chunking using embeddings. "
                "Groups related sentences regardless of boundaries. "
                "Requires embedding service."
            ),
            ChunkStrategyType.NARRATIVE_FLOW: (
                "Narrative flow preserving chunking for fiction. "
                "Preserves dialogue and maintains story flow."
            ),
            ChunkStrategyType.AUTO: (
                "Auto-detection chunking that selects best strategy "
                "based on content type and structure."
            ),
        }
        return descriptions.get(
            strategy_type, "No description available for this strategy."
        )
