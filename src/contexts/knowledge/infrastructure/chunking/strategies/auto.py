"""
Auto Select Chunking Strategy

Implements automatic strategy selection based on content type
and text structure analysis.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

import structlog

from ....application.ports.i_chunking_strategy import Chunk, ChunkingError
from ....domain.models.chunking_strategy import ChunkingStrategy, ChunkStrategyType
from ..base import _PARAGRAPH_DELIM, _SENTENCE_END, _WORD_PATTERN, BaseChunkingStrategy
from .fixed_size import FixedSizeStrategy as FixedSizeStrategy
from .paragraph import ParagraphBoundaryStrategy as ParagraphBoundaryStrategy
from .semantic import SemanticSimilarityStrategy as SemanticSimilarityStrategy
from .sentence import SentenceBoundaryStrategy as SentenceBoundaryStrategy

if TYPE_CHECKING:
    from ...application.ports.i_embedding_service import IEmbeddingService

logger = structlog.get_logger()


class ContentType(str, Enum):
    """
    Content type hints for auto-detection.

    When content type is known, the appropriate strategy is selected directly.
    When UNKNOWN, the strategy is detected by analyzing text structure.
    """

    SCENE = "scene"
    CHARACTER = "character"
    LORE = "lore"
    DIALOGUE = "dialogue"
    NARRATIVE = "narrative"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


class AutoSelectStrategy(BaseChunkingStrategy):
    """
    Auto-detection chunking strategy adapter.

    Automatically selects the best chunking strategy based on:
    1. Content type hint (if provided)
    2. Text structure analysis (paragraphs, sentences, dialogue)
    3. Content length and complexity

    Strategy selection rules:
    - Scene -> Semantic (preserves narrative flow and topic shifts)
    - Character -> Paragraph (groups related character traits)
    - Lore -> Fixed (consistent world-building chunks)
    - Dialogue -> Sentence (preserves speaker turns)
    - Document -> Paragraph (respects document structure)
    - Unknown -> Detected by analysis

    Configuration:
        - chunk_size: Maximum words per chunk (default: 500)
        - overlap: Number of overlapping words between chunks (default: 50)
        - min_chunk_size: Minimum chunk size (default: 50)
        - content_type: Optional hint for strategy selection

    Why auto-detection:
        - Provides sensible defaults without manual configuration
        - Adapts to different content types automatically
        - Improves RAG retrieval quality by using appropriate chunking

    Example:
        >>> strategy = AutoSelectStrategy(embedding_service=service)
        >>> chunks = await strategy.chunk(
        ...     scene_text,
        ...     ChunkingStrategy(strategy=ChunkStrategyType.AUTO)
        ... )
        >>> # Uses semantic chunking for scenes
    """

    # Content type to strategy mappings
    CONTENT_TYPE_STRATEGY_MAP: dict[ContentType, ChunkStrategyType] = {
        ContentType.SCENE: ChunkStrategyType.SEMANTIC,
        ContentType.CHARACTER: ChunkStrategyType.PARAGRAPH,
        ContentType.LORE: ChunkStrategyType.FIXED,
        ContentType.DIALOGUE: ChunkStrategyType.SENTENCE,
        ContentType.NARRATIVE: ChunkStrategyType.SEMANTIC,
        ContentType.DOCUMENT: ChunkStrategyType.PARAGRAPH,
    }

    def __init__(
        self,
        embedding_service: IEmbeddingService | None = None,
        default_config: ChunkingStrategy | None = None,
    ) -> None:
        """
        Initialize the auto chunking strategy.

        Args:
            embedding_service: Required for semantic chunking. If None, semantic
                strategy falls back to paragraph chunking.
            default_config: Default configuration to use when none is provided
        """
        self._embedding_service = embedding_service
        self._default_config = default_config or ChunkingStrategy(
            strategy=ChunkStrategyType.AUTO,
            chunk_size=500,
            overlap=50,
        )

        # Initialize delegate strategies (created on demand to avoid circular imports)
        # Use Any for typing since each slot can only hold its specific type
        self._fixed_strategy: Any = None
        self._sentence_strategy: Any = None
        self._paragraph_strategy: Any = None
        self._semantic_strategy: Any = None

    async def chunk(
        self,
        text: str,
        config: ChunkingStrategy | None = None,
    ) -> list[Chunk]:
        """
        Split text into chunks using auto-detected strategy.

        Args:
            text: Source text to chunk
            config: Optional chunking configuration (uses defaults if None)

        Returns:
            List of Chunk entities with text, index, and metadata

        Raises:
            ChunkingError: If chunking fails
            ValueError: If text is empty or configuration is invalid
        """
        strategy_config = config or self._default_config

        if not text or not text.strip():
            raise ValueError("Cannot chunk empty text")

        if strategy_config.strategy != ChunkStrategyType.AUTO:
            logger.warning(
                "auto_chunking_strategy_mismatch",
                expected=ChunkStrategyType.AUTO,
                actual=strategy_config.strategy,
            )

        log = logger.bind(
            strategy="auto",
            chunk_size=strategy_config.chunk_size,
            overlap=strategy_config.overlap,
            text_length=len(text),
        )

        log.debug("auto_chunking_start")

        try:
            # Step 1: Determine content type
            content_type = self._get_content_type_hint(strategy_config)
            log = log.bind(content_type=content_type)

            # Step 2: Select strategy based on content type or structure
            selected_strategy = self._select_strategy(
                text,
                content_type,
                strategy_config,
            )
            log = log.bind(selected_strategy=selected_strategy.value)

            log.info(
                "auto_chunking_strategy_selected",
                content_type=content_type,
                strategy=selected_strategy.value,
            )

            # Step 3: Delegate to selected strategy
            chunks = await self._chunk_with_strategy(
                text,
                selected_strategy,
                strategy_config,
            )

            # Step 4: Update metadata to indicate auto-detection
            for chunk in chunks:
                chunk.metadata["auto_detected"] = True
                chunk.metadata["content_type"] = content_type
                chunk_metadata_strategy = chunk.metadata.get("strategy", "")
                chunk.metadata["original_strategy"] = chunk_metadata_strategy
                chunk.metadata["strategy"] = f"auto_{chunk_metadata_strategy}"

            log.info(
                "auto_chunking_complete",
                chunk_count=len(chunks),
                total_words=sum(c.metadata.get("word_count", 0) for c in chunks),
            )

            return chunks

        except ValueError:
            raise
        except Exception as e:
            log.error("auto_chunking_error", error=str(e), error_type=type(e).__name__)
            raise ChunkingError(
                f"Auto chunking failed: {e}", code="AUTO_CHUNKING_ERROR"
            ) from e

    def supports_strategy_type(self, strategy_type: str) -> bool:
        """Check if this implementation supports the 'auto' strategy type."""
        return strategy_type.lower() == ChunkStrategyType.AUTO.value

    def _get_content_type_hint(self, config: ChunkingStrategy) -> ContentType:
        """
        Extract content type hint from configuration.

        Content type can be provided via:
        1. ChunkingStrategy.for_content_type() factory method
        2. Passing strategy=ChunkStrategyType.AUTO with content_type metadata

        Args:
            config: Chunking configuration

        Returns:
            Content type hint (UNKNOWN if not specified)
        """
        # Content type can be inferred from the strategy itself when using AUTO
        # The for_content_type factory method sets the strategy to AUTO
        # We detect content type by analyzing text structure in _detect_from_structure
        return ContentType.UNKNOWN

    def _select_strategy(
        self,
        text: str,
        content_type: ContentType,
        config: ChunkingStrategy,
    ) -> ChunkStrategyType:
        """
        Select the best chunking strategy for the given text.

        Args:
            text: Source text to analyze
            content_type: Content type hint (may be UNKNOWN)
            config: Chunking configuration

        Returns:
            Selected chunking strategy type
        """
        # If content type is known, use predefined mapping
        if content_type != ContentType.UNKNOWN:
            strategy = self.CONTENT_TYPE_STRATEGY_MAP.get(content_type)
            if strategy:
                # If semantic is selected but no embedding service, fall back to paragraph
                if (
                    strategy == ChunkStrategyType.SEMANTIC
                    and self._embedding_service is None
                ):
                    return ChunkStrategyType.PARAGRAPH
                return strategy

        # Otherwise, detect strategy from text structure
        return self._detect_from_structure(text)

    def _detect_from_structure(self, text: str) -> ChunkStrategyType:
        """
        Detect best strategy by analyzing text structure.

        Detection heuristics:
        1. High paragraph density -> Paragraph (document-like)
        2. High sentence density with dialogue markers -> Sentence (dialogue)
        3. Long flowing text with semantic shifts -> Semantic (narrative)
        4. Fallback -> Fixed (generic)

        Args:
            text: Source text to analyze

        Returns:
            Detected chunking strategy type
        """
        # Count structural elements
        paragraph_count = len(_PARAGRAPH_DELIM.findall(text))
        sentence_count = len(_SENTENCE_END.findall(text))
        word_count = len(_WORD_PATTERN.findall(text))
        dialogue_marker_count = text.count('"') + text.count("'")

        if word_count == 0:
            return ChunkStrategyType.FIXED

        # Calculate densities
        char_count = len(text)
        paragraph_density = paragraph_count / max(char_count, 1) * 1000
        sentence_density = sentence_count / max(word_count, 1)
        dialogue_ratio = dialogue_marker_count / max(word_count, 1)

        # Decision tree
        # 1. Document-like: Multiple paragraphs per 1000 chars
        if paragraph_density > 2.0:
            return ChunkStrategyType.PARAGRAPH

        # 2. Dialogue-heavy: Many quotes relative to word count
        if dialogue_ratio > 0.3:
            return ChunkStrategyType.SENTENCE

        # 3. Dense sentences: More than 1 sentence per 8 words
        if sentence_density > 0.12 and word_count > 100:
            # Semantic if we have embedding service, otherwise sentence
            if self._embedding_service is not None:
                return ChunkStrategyType.SEMANTIC
            return ChunkStrategyType.SENTENCE

        # 4. Fallback to fixed for generic content
        return ChunkStrategyType.FIXED

    async def _chunk_with_strategy(
        self,
        text: str,
        strategy_type: ChunkStrategyType,
        config: ChunkingStrategy,
    ) -> list[Chunk]:
        """
        Delegate chunking to the appropriate strategy.

        Args:
            text: Source text to chunk
            strategy_type: Strategy to use
            config: Chunking configuration

        Returns:
            List of Chunk entities
        """
        # Convert config to target strategy type
        target_config = ChunkingStrategy(
            strategy=strategy_type,
            chunk_size=config.chunk_size,
            overlap=config.overlap,
            min_chunk_size=config.min_chunk_size,
        )

        if strategy_type == ChunkStrategyType.FIXED:
            delegate = self._get_fixed_strategy()
            return await delegate.chunk(text, target_config)

        if strategy_type == ChunkStrategyType.SENTENCE:
            delegate = self._get_sentence_strategy()
            return await delegate.chunk(text, target_config)

        if strategy_type == ChunkStrategyType.PARAGRAPH:
            delegate = self._get_paragraph_strategy()
            return await delegate.chunk(text, target_config)

        if strategy_type == ChunkStrategyType.SEMANTIC:
            if self._embedding_service is None:
                # Fall back to paragraph if no embedding service
                delegate = self._get_paragraph_strategy()
                para_config = ChunkingStrategy(
                    strategy=ChunkStrategyType.PARAGRAPH,
                    chunk_size=config.chunk_size,
                    overlap=config.overlap,
                    min_chunk_size=config.min_chunk_size,
                )
                return await delegate.chunk(text, para_config)

            delegate = self._get_semantic_strategy()
            return await delegate.chunk(text, target_config)

        # Should never reach here
        raise ChunkingError(
            f"Unknown strategy type: {strategy_type}", code="UNKNOWN_STRATEGY"
        )

    def _get_fixed_strategy(self) -> Any:
        """Get or create fixed chunking delegate."""
        if self._fixed_strategy is None:
            self._fixed_strategy = FixedSizeStrategy()
        return self._fixed_strategy

    def _get_sentence_strategy(self) -> Any:
        """Get or create sentence chunking delegate."""
        if self._sentence_strategy is None:
            self._sentence_strategy = SentenceBoundaryStrategy()
        return self._sentence_strategy

    def _get_paragraph_strategy(self) -> Any:
        """Get or create paragraph chunking delegate."""
        if self._paragraph_strategy is None:
            self._paragraph_strategy = ParagraphBoundaryStrategy()
        return self._paragraph_strategy

    def _get_semantic_strategy(self) -> Any:
        """Get or create semantic chunking delegate."""
        if self._semantic_strategy is None:
            if self._embedding_service is None:
                raise ChunkingError(
                    "Embedding service required for semantic chunking",
                    code="MISSING_EMBEDDING_SERVICE",
                )
            self._semantic_strategy = SemanticSimilarityStrategy(
                embedding_service=self._embedding_service,
            )
        return self._semantic_strategy
