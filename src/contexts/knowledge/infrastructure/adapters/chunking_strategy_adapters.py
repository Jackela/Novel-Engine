"""
Chunking Strategy Adapters

Implements IChunkingStrategy port for various chunking approaches.
Adapts the existing TextChunker domain service to the hexagonal architecture.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapters implementing application port
- Article V (SOLID): SRP - each adapter handles one strategy type

Warzone 4: AI Brain - BRAIN-039A-02, BRAIN-039A-03, BRAIN-039A-04
"""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Any

import structlog

from ...application.ports.i_chunking_strategy import Chunk, ChunkingError, IChunkingStrategy
from ...domain.models.chunking_strategy import (
    ChunkStrategyType,
    ChunkingStrategy,
)

if TYPE_CHECKING:
    from ...application.ports.i_embedding_service import IEmbeddingService

logger = structlog.get_logger()

# Word pattern for counting
_WORD_PATTERN = re.compile(r"\S+")

# Sentence end pattern: . ! ? followed by whitespace
_SENTENCE_END = re.compile(r'[.!?]+\s+', re.MULTILINE)

# Paragraph delimiter: two or more newlines
_PARAGRAPH_DELIM = re.compile(r'\n\n+', re.MULTILINE)


class FixedChunkingStrategy:
    """
    Fixed-size chunking strategy adapter.

    Splits text into chunks of a fixed word count with configurable overlap.
    This is the simplest and most predictable chunking approach.

    Configuration:
        - chunk_size: Maximum words per chunk (default: 500)
        - overlap: Number of overlapping words between chunks (default: 50)
        - min_chunk_size: Minimum chunk size to avoid tiny fragments (default: 50)

    Why fixed-size:
        - Predictable chunk sizes for vector storage
        - Simple to understand and debug
        - Works well for most content types
        - Consistent token counts for LLM context windows

    Example:
        >>> strategy = FixedChunkingStrategy()
        >>> chunks = await strategy.chunk(
        ...     "This is a long text..." * 100,
        ...     ChunkingStrategy.strategy=ChunkStrategyType.FIXED,
        ...     chunk_size=200,
        ...     overlap=20
        ... )
        >>> len(chunks)
        3
        >>> chunks[0].index
        0
        >>> chunks[1].index
        1
        >>> # Chunks overlap by 20 words
    """

    def __init__(self, default_config: ChunkingStrategy | None = None):
        """
        Initialize the fixed chunking strategy.

        Args:
            default_config: Default configuration to use when none is provided
        """
        self._default_config = default_config or ChunkingStrategy.default()

    async def chunk(
        self,
        text: str,
        config: ChunkingStrategy | None = None,
    ) -> list[Chunk]:
        """
        Split text into fixed-size chunks with overlap.

        Args:
            text: Source text to chunk
            config: Optional chunking configuration (uses defaults if None)

        Returns:
            List of Chunk entities with text, index, and metadata

        Raises:
            ChunkingError: If chunking fails
            ValueError: If text is empty or configuration is invalid

        Example:
            >>> strategy = FixedChunkingStrategy()
            >>> chunks = await strategy.chunk("long text...")
            >>> chunks[0].text
            'long text...'
            >>> chunks[0].metadata["word_count"]
            500
        """
        # Use provided config or default
        strategy_config = config or self._default_config

        # Validate input
        if not text or not text.strip():
            raise ValueError("Cannot chunk empty text")

        # Ensure we're using the FIXED strategy type
        if strategy_config.strategy != ChunkStrategyType.FIXED:
            logger.warning(
                "fixed_chunking_strategy_mismatch",
                expected=ChunkStrategyType.FIXED,
                actual=strategy_config.strategy,
            )
            # Continue anyway - the config might have been set elsewhere

        log = logger.bind(
            strategy="fixed",
            chunk_size=strategy_config.chunk_size,
            overlap=strategy_config.overlap,
            text_length=len(text),
        )

        log.debug("fixed_chunking_start")

        try:
            # Extract words from text
            words = _WORD_PATTERN.findall(text)

            if not words:
                return []

            chunks = []
            chunk_index = 0
            i = 0
            start_char_pos = 0
            total_char_pos = 0

            while i < len(words):
                # Determine end of this chunk
                end_idx = min(i + strategy_config.chunk_size, len(words))

                # Extract chunk words
                chunk_words = words[i:end_idx]
                chunk_text = " ".join(chunk_words)

                # Find character positions for metadata
                chunk_start = self._find_char_position(text, words, i)
                chunk_end = self._find_char_position(text, words, end_idx - 1) + len(words[end_idx - 1])

                # Create metadata
                metadata: dict[str, Any] = {
                    "strategy": "fixed",
                    "word_count": len(chunk_words),
                    "start_char": chunk_start,
                    "end_char": chunk_end,
                    "chunk_size": strategy_config.chunk_size,
                    "overlap": strategy_config.overlap,
                }

                chunks.append(
                    Chunk(
                        text=chunk_text,
                        index=chunk_index,
                        metadata=metadata,
                    )
                )

                chunk_index += 1
                # Move forward by effective chunk size (chunk_size - overlap)
                i += strategy_config.effective_chunk_size()

            log.info(
                "fixed_chunking_complete",
                chunk_count=len(chunks),
                total_words=sum(c.metadata.get("word_count", 0) for c in chunks),
            )

            return chunks

        except ValueError:
            raise
        except Exception as e:
            log.error("fixed_chunking_error", error=str(e), error_type=type(e).__name__)
            raise ChunkingError(f"Fixed chunking failed: {e}", code="FIXED_CHUNKING_ERROR") from e

    def supports_strategy_type(self, strategy_type: str) -> bool:
        """
        Check if this implementation supports a given strategy type.

        Args:
            strategy_type: The strategy type identifier

        Returns:
            True if strategy_type is "fixed" (case-insensitive)
        """
        return strategy_type.lower() == ChunkStrategyType.FIXED.value

    def _find_char_position(self, text: str, words: list[str], word_index: int) -> int:
        """
        Find the character position of a word in the original text.

        Args:
            text: Original text
            words: List of words extracted from text
            word_index: Index of word to find

        Returns:
            Character position where the word starts
        """
        if word_index >= len(words):
            return len(text)
        if word_index < 0:
            return 0

        target_word = words[word_index]
        words_found = 0

        for match in _WORD_PATTERN.finditer(text):
            if words_found == word_index:
                if match.group() == target_word:
                    return match.start()
            words_found += 1

        # Fallback: search from estimated position
        estimated_pos = (word_index * 5)  # Rough estimate
        search_start = max(0, estimated_pos - 50)
        found_pos = text.find(target_word, search_start)
        return max(0, found_pos)


class SentenceChunkingStrategy:
    """
    Sentence-aware chunking strategy adapter.

    Splits text into chunks at sentence boundaries with configurable overlap.
    Preserves sentence integrity for better semantic coherence.

    Configuration:
        - chunk_size: Maximum words per chunk (default: 500)
        - overlap: Number of overlapping words between chunks (default: 50)
        - min_chunk_size: Minimum chunk size to avoid tiny fragments (default: 50)

    Why sentence-aware:
        - Preserves natural language boundaries
        - Better semantic coherence than fixed-size
        - Avoids mid-sentence breaks
        - Ideal for narrative text and dialogue

    Example:
        >>> strategy = SentenceChunkingStrategy()
        >>> chunks = await strategy.chunk(
        ...     "This is sentence one. This is sentence two.",
        ...     ChunkingStrategy(strategy=ChunkStrategyType.SENTENCE)
        ... )
        >>> len(chunks)
        1
    """

    def __init__(self, default_config: ChunkingStrategy | None = None):
        """
        Initialize the sentence chunking strategy.

        Args:
            default_config: Default configuration to use when none is provided
        """
        self._default_config = default_config or ChunkingStrategy(
            strategy=ChunkStrategyType.SENTENCE,
            chunk_size=500,
            overlap=50,
        )

    async def chunk(
        self,
        text: str,
        config: ChunkingStrategy | None = None,
    ) -> list[Chunk]:
        """
        Split text into sentence-aware chunks with overlap.

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

        if strategy_config.strategy != ChunkStrategyType.SENTENCE:
            logger.warning(
                "sentence_chunking_strategy_mismatch",
                expected=ChunkStrategyType.SENTENCE,
                actual=strategy_config.strategy,
            )

        log = logger.bind(
            strategy="sentence",
            chunk_size=strategy_config.chunk_size,
            overlap=strategy_config.overlap,
            text_length=len(text),
        )

        log.debug("sentence_chunking_start")

        try:
            # Find all sentence boundaries
            sentences: list[tuple[int, int]] = []
            last_end = 0

            for match in _SENTENCE_END.finditer(text):
                end_pos = match.end()
                sentences.append((last_end, end_pos))
                last_end = end_pos

            # Add remaining text as last sentence if any
            if last_end < len(text.strip()):
                sentences.append((last_end, len(text)))

            # If no sentence breaks found, fall back to fixed chunking
            if not sentences:
                log.info("sentence_chunking_no_breaks", fallback="fixed")
                return await self._fallback_fixed(text, strategy_config)

            chunks = []
            current_sentences: list[tuple[int, int]] = []
            current_word_count = 0
            chunk_index = 0

            for start, end in sentences:
                sentence_text = text[start:end].strip()
                if not sentence_text:
                    continue

                sentence_words = len(_WORD_PATTERN.findall(sentence_text))

                # Check if adding this sentence would exceed chunk size
                if current_word_count + sentence_words > strategy_config.chunk_size:
                    if current_sentences:
                        # Create chunk from accumulated sentences
                        chunk_start = current_sentences[0][0]
                        chunk_end = current_sentences[-1][1]
                        chunk_content = text[chunk_start:chunk_end].strip()

                        chunks.append(self._create_chunk(
                            chunk_content,
                            chunk_index,
                            chunk_start,
                            chunk_end,
                            current_word_count,
                            strategy_config,
                        ))
                        chunk_index += 1

                    # Keep overlap sentences for next chunk
                    overlap_to_keep: list[tuple[int, int]] = []
                    overlap_count = 0
                    # Walk backwards from the end of current sentences
                    for s_start, s_end in reversed(current_sentences):
                        s_words = len(_WORD_PATTERN.findall(text[s_start:s_end]))
                        if overlap_count + s_words <= strategy_config.overlap:
                            overlap_to_keep.insert(0, (s_start, s_end))
                            overlap_count += s_words
                        else:
                            break

                    current_sentences = overlap_to_keep
                    current_word_count = overlap_count

                current_sentences.append((start, end))
                current_word_count += sentence_words

            # Add final chunk if any sentences remain
            if current_sentences:
                chunk_start = current_sentences[0][0]
                chunk_end = current_sentences[-1][1]
                chunk_content = text[chunk_start:chunk_end].strip()

                chunks.append(self._create_chunk(
                    chunk_content,
                    chunk_index,
                    chunk_start,
                    chunk_end,
                    current_word_count,
                    strategy_config,
                ))

            if not chunks:
                # Fallback if something went wrong
                return await self._fallback_fixed(text, strategy_config)

            log.info(
                "sentence_chunking_complete",
                chunk_count=len(chunks),
                total_words=sum(c.metadata.get("word_count", 0) for c in chunks),
            )

            return chunks

        except ValueError:
            raise
        except Exception as e:
            log.error("sentence_chunking_error", error=str(e), error_type=type(e).__name__)
            raise ChunkingError(f"Sentence chunking failed: {e}", code="SENTENCE_CHUNKING_ERROR") from e

    def supports_strategy_type(self, strategy_type: str) -> bool:
        """Check if this implementation supports the 'sentence' strategy type."""
        return strategy_type.lower() == ChunkStrategyType.SENTENCE.value

    def _create_chunk(
        self,
        content: str,
        index: int,
        start_pos: int,
        end_pos: int,
        word_count: int,
        config: ChunkingStrategy,
    ) -> Chunk:
        """Create a Chunk entity with metadata."""
        metadata: dict[str, Any] = {
            "strategy": "sentence",
            "word_count": word_count,
            "start_char": start_pos,
            "end_char": end_pos,
            "chunk_size": config.chunk_size,
            "overlap": config.overlap,
        }
        return Chunk(text=content, index=index, metadata=metadata)

    async def _fallback_fixed(self, text: str, config: ChunkingStrategy) -> list[Chunk]:
        """Fallback to fixed chunking if no sentence breaks found."""
        fixed_strategy = FixedChunkingStrategy(default_config=config)
        # Convert to SENTENCE type config for fixed strategy
        fixed_config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=config.chunk_size,
            overlap=config.overlap,
            min_chunk_size=config.min_chunk_size,
        )
        chunks = await fixed_strategy.chunk(text, fixed_config)
        # Update metadata to reflect sentence strategy was attempted
        for chunk in chunks:
            chunk.metadata["strategy"] = "sentence_fixed_fallback"
        return chunks


class ParagraphChunkingStrategy:
    """
    Paragraph-aware chunking strategy adapter.

    Splits text into chunks at paragraph boundaries with configurable overlap.
    Preserves paragraph integrity for document structure.

    Configuration:
        - chunk_size: Maximum words per chunk (default: 500)
        - overlap: Number of overlapping words between chunks (default: 50)
        - min_chunk_size: Minimum chunk size to avoid tiny fragments (default: 50)

    Why paragraph-aware:
        - Preserves document structure
        - Groups related sentences together
        - Better for structured documents
        - Maintains thematic coherence

    Example:
        >>> strategy = ParagraphChunkingStrategy()
        >>> chunks = await strategy.chunk(
        ...     "Para one.\\n\\nPara two.\\n\\nPara three.",
        ...     ChunkingStrategy(strategy=ChunkStrategyType.PARAGRAPH)
        ... )
        >>> len(chunks)
        3
    """

    def __init__(self, default_config: ChunkingStrategy | None = None):
        """
        Initialize the paragraph chunking strategy.

        Args:
            default_config: Default configuration to use when none is provided
        """
        self._default_config = default_config or ChunkingStrategy(
            strategy=ChunkStrategyType.PARAGRAPH,
            chunk_size=500,
            overlap=50,
        )

    async def chunk(
        self,
        text: str,
        config: ChunkingStrategy | None = None,
    ) -> list[Chunk]:
        """
        Split text into paragraph-aware chunks with overlap.

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

        if strategy_config.strategy != ChunkStrategyType.PARAGRAPH:
            logger.warning(
                "paragraph_chunking_strategy_mismatch",
                expected=ChunkStrategyType.PARAGRAPH,
                actual=strategy_config.strategy,
            )

        log = logger.bind(
            strategy="paragraph",
            chunk_size=strategy_config.chunk_size,
            overlap=strategy_config.overlap,
            text_length=len(text),
        )

        log.debug("paragraph_chunking_start")

        try:
            # Split by paragraph delimiters
            paragraphs: list[tuple[int, int]] = []
            last_end = 0

            for match in _PARAGRAPH_DELIM.finditer(text):
                end_pos = match.end() - len(match.group())  # Exclude delimiter
                paragraphs.append((last_end, end_pos))
                last_end = match.end()

            # Add remaining text
            if last_end < len(text.strip()):
                paragraphs.append((last_end, len(text)))

            # If no paragraph breaks found, fall back to fixed chunking
            if not paragraphs:
                log.info("paragraph_chunking_no_breaks", fallback="fixed")
                return await self._fallback_fixed(text, strategy_config)

            chunks = []
            current_paragraphs: list[tuple[int, int]] = []
            current_word_count = 0
            chunk_index = 0

            for start, end in paragraphs:
                para_text = text[start:end].strip()
                if not para_text:
                    continue

                para_words = len(_WORD_PATTERN.findall(para_text))

                if current_word_count + para_words > strategy_config.chunk_size:
                    if current_paragraphs:
                        # Create chunk
                        chunk_start = current_paragraphs[0][0]
                        chunk_end = current_paragraphs[-1][1]
                        chunk_content = text[chunk_start:chunk_end].strip()

                        chunks.append(self._create_chunk(
                            chunk_content,
                            chunk_index,
                            chunk_start,
                            chunk_end,
                            current_word_count,
                            strategy_config,
                        ))
                        chunk_index += 1

                    # Keep overlap paragraphs
                    overlap_to_keep: list[tuple[int, int]] = []
                    overlap_count = 0
                    for p_start, p_end in reversed(current_paragraphs):
                        p_words = len(_WORD_PATTERN.findall(text[p_start:p_end]))
                        if overlap_count + p_words <= strategy_config.overlap:
                            overlap_to_keep.insert(0, (p_start, p_end))
                            overlap_count += p_words
                        else:
                            break

                    current_paragraphs = overlap_to_keep
                    current_word_count = overlap_count

                current_paragraphs.append((start, end))
                current_word_count += para_words

            # Add final chunk
            if current_paragraphs:
                chunk_start = current_paragraphs[0][0]
                chunk_end = current_paragraphs[-1][1]
                chunk_content = text[chunk_start:chunk_end].strip()

                chunks.append(self._create_chunk(
                    chunk_content,
                    chunk_index,
                    chunk_start,
                    chunk_end,
                    current_word_count,
                    strategy_config,
                ))

            if not chunks:
                # Fallback if something went wrong
                return await self._fallback_fixed(text, strategy_config)

            log.info(
                "paragraph_chunking_complete",
                chunk_count=len(chunks),
                total_words=sum(c.metadata.get("word_count", 0) for c in chunks),
            )

            return chunks

        except ValueError:
            raise
        except Exception as e:
            log.error("paragraph_chunking_error", error=str(e), error_type=type(e).__name__)
            raise ChunkingError(f"Paragraph chunking failed: {e}", code="PARAGRAPH_CHUNKING_ERROR") from e

    def supports_strategy_type(self, strategy_type: str) -> bool:
        """Check if this implementation supports the 'paragraph' strategy type."""
        return strategy_type.lower() == ChunkStrategyType.PARAGRAPH.value

    def _create_chunk(
        self,
        content: str,
        index: int,
        start_pos: int,
        end_pos: int,
        word_count: int,
        config: ChunkingStrategy,
    ) -> Chunk:
        """Create a Chunk entity with metadata."""
        metadata: dict[str, Any] = {
            "strategy": "paragraph",
            "word_count": word_count,
            "start_char": start_pos,
            "end_char": end_pos,
            "chunk_size": config.chunk_size,
            "overlap": config.overlap,
        }
        return Chunk(text=content, index=index, metadata=metadata)

    async def _fallback_fixed(self, text: str, config: ChunkingStrategy) -> list[Chunk]:
        """Fallback to fixed chunking if no paragraph breaks found."""
        fixed_strategy = FixedChunkingStrategy(default_config=config)
        # Convert to PARAGRAPH type config for fixed strategy
        fixed_config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=config.chunk_size,
            overlap=config.overlap,
            min_chunk_size=config.min_chunk_size,
        )
        chunks = await fixed_strategy.chunk(text, fixed_config)
        # Update metadata to reflect paragraph strategy was attempted
        for chunk in chunks:
            chunk.metadata["strategy"] = "paragraph_fixed_fallback"
        return chunks


class SemanticChunkingStrategy:
    """
    Semantic-aware chunking strategy adapter.

    Groups semantically related sentences into chunks using embeddings.
    Maintains narrative coherence by grouping sentences that discuss
    similar topics or themes.

    Configuration:
        - chunk_size: Maximum words per chunk (default: 500)
        - overlap: Number of overlapping words between chunks (default: 50)
        - min_chunk_size: Minimum chunk size to avoid tiny fragments (default: 50)
        - similarity_threshold: Minimum cosine similarity to group sentences (default: 0.75)
        - max_sentences_per_chunk: Maximum sentences in a semantic group (default: 10)

    Why semantic chunking:
        - Groups related content regardless of sentence boundaries
        - Preserves thematic coherence better than fixed-size approaches
        - Ideal for narrative text with shifting topics
        - Better retrieval quality for RAG applications

    Algorithm:
        1. Split text into sentences
        2. Generate embeddings for each sentence
        3. Group sentences by semantic similarity using cosine similarity
        4. Create chunks from semantically coherent groups
        5. Apply overlap between chunks for context continuity

    Example:
        >>> strategy = SemanticChunkingStrategy(embedding_service=service)
        >>> chunks = await strategy.chunk(
        ...     "The warrior entered. The castle was dark. Meanwhile, the princess waited.",
        ...     ChunkingStrategy(strategy=ChunkStrategyType.SEMANTIC)
        ... )
        >>> len(chunks)
        2
    """

    # Default semantic chunking parameters
    DEFAULT_SIMILARITY_THRESHOLD = 0.75
    DEFAULT_MAX_SENTENCES_PER_CHUNK = 10
    DEFAULT_MIN_SENTENCES_PER_CHUNK = 2

    def __init__(
        self,
        embedding_service: IEmbeddingService,
        default_config: ChunkingStrategy | None = None,
    ):
        """
        Initialize the semantic chunking strategy.

        Args:
            embedding_service: Service for generating text embeddings
            default_config: Default configuration to use when none is provided
        """
        self._embedding_service = embedding_service
        self._default_config = default_config or ChunkingStrategy(
            strategy=ChunkStrategyType.SEMANTIC,
            chunk_size=500,
            overlap=50,
        )

    async def chunk(
        self,
        text: str,
        config: ChunkingStrategy | None = None,
    ) -> list[Chunk]:
        """
        Split text into semantically coherent chunks.

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

        if strategy_config.strategy != ChunkStrategyType.SEMANTIC:
            logger.warning(
                "semantic_chunking_strategy_mismatch",
                expected=ChunkStrategyType.SEMANTIC,
                actual=strategy_config.strategy,
            )

        log = logger.bind(
            strategy="semantic",
            chunk_size=strategy_config.chunk_size,
            overlap=strategy_config.overlap,
            text_length=len(text),
        )

        log.debug("semantic_chunking_start")

        try:
            # Step 1: Split text into sentences
            sentences = self._split_into_sentences(text)
            if not sentences:
                log.info("semantic_chunking_no_sentences", fallback="fixed")
                return await self._fallback_fixed(text, strategy_config)

            # Step 2: Generate embeddings for all sentences
            sentence_texts = [s[2] for s in sentences]
            embeddings = await self._embedding_service.embed_batch(sentence_texts)

            # Step 3: Group sentences by semantic similarity
            semantic_groups = self._group_by_similarity(
                sentences,
                embeddings,
                strategy_config,
            )

            # Step 4: Create chunks from semantic groups
            chunks = await self._create_chunks_from_groups(
                text,
                semantic_groups,
                strategy_config,
            )

            if not chunks:
                # Fallback if something went wrong
                log.info("semantic_chunking_no_chunks", fallback="fixed")
                return await self._fallback_fixed(text, strategy_config)

            log.info(
                "semantic_chunking_complete",
                chunk_count=len(chunks),
                total_words=sum(c.metadata.get("word_count", 0) for c in chunks),
            )

            return chunks

        except ValueError:
            raise
        except Exception as e:
            log.error("semantic_chunking_error", error=str(e), error_type=type(e).__name__)
            raise ChunkingError(f"Semantic chunking failed: {e}", code="SEMANTIC_CHUNKING_ERROR") from e

    def supports_strategy_type(self, strategy_type: str) -> bool:
        """Check if this implementation supports the 'semantic' strategy type."""
        return strategy_type.lower() == ChunkStrategyType.SEMANTIC.value

    def _split_into_sentences(self, text: str) -> list[tuple[int, int, str]]:
        """
        Split text into sentences with position tracking.

        Args:
            text: Source text

        Returns:
            List of (start_pos, end_pos, sentence_text) tuples
        """
        sentences: list[tuple[int, int, str]] = []
        last_end = 0

        for match in _SENTENCE_END.finditer(text):
            end_pos = match.end()
            sentence_text = text[last_end:end_pos].strip()
            if sentence_text:
                sentences.append((last_end, end_pos, sentence_text))
            last_end = end_pos

        # Add remaining text as last sentence
        if last_end < len(text.strip()):
            remaining = text[last_end:].strip()
            if remaining:
                sentences.append((last_end, len(text), remaining))

        return sentences

    def _group_by_similarity(
        self,
        sentences: list[tuple[int, int, str]],
        embeddings: list[list[float]],
        config: ChunkingStrategy,
    ) -> list[list[tuple[int, int, str]]]:
        """
        Group sentences by semantic similarity.

        Uses cosine similarity to determine sentence relatedness.
        Sentences are grouped when similarity exceeds threshold.

        Args:
            sentences: List of (start, end, text) tuples
            embeddings: List of embedding vectors for each sentence
            config: Chunking configuration

        Returns:
            List of sentence groups, where each group is a list of sentences
        """
        if not sentences:
            return []

        groups: list[list[tuple[int, int, str]]] = []
        current_group: list[tuple[int, int, str]] = [sentences[0]]

        # Use default similarity threshold (could be made configurable)
        similarity_threshold = self.DEFAULT_SIMILARITY_THRESHOLD
        max_sentences = self.DEFAULT_MAX_SENTENCES_PER_CHUNK

        for i in range(1, len(sentences)):
            sentence = sentences[i]
            current_embedding = embeddings[i]

            # Calculate similarity with last sentence in current group
            last_idx = sentences.index(current_group[-1])
            last_embedding = embeddings[last_idx]

            similarity = self._cosine_similarity(current_embedding, last_embedding)

            # Check word count of current group
            group_text = " ".join(s[2] for s in current_group)
            group_words = len(_WORD_PATTERN.findall(group_text))

            # Decide whether to start a new group
            should_start_new = (
                similarity < similarity_threshold or
                len(current_group) >= max_sentences or
                group_words >= config.chunk_size
            )

            if should_start_new and current_group:
                # Save current group and start new one
                groups.append(current_group)
                current_group = [sentence]
            else:
                # Add to current group
                current_group.append(sentence)

        # Add final group
        if current_group:
            groups.append(current_group)

        return groups

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score between -1 and 1
        """
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def _create_chunks_from_groups(
        self,
        original_text: str,
        semantic_groups: list[list[tuple[int, int, str]]],
        config: ChunkingStrategy,
    ) -> list[Chunk]:
        """
        Create Chunk entities from semantic groups with overlap.

        Args:
            original_text: Full source text
            semantic_groups: Groups of related sentences
            config: Chunking configuration

        Returns:
            List of Chunk entities
        """
        chunks: list[Chunk] = []
        chunk_index = 0

        for group in semantic_groups:
            # Get group text bounds
            start_pos = group[0][0]
            end_pos = group[-1][1]

            # Apply overlap by including sentences from previous group
            if chunk_index > 0 and config.overlap > 0:
                overlap_words = config.overlap
                # Find sentences to include for overlap
                overlap_sentences = self._get_overlap_sentences(
                    semantic_groups[chunk_index - 1],
                    overlap_words,
                )
                if overlap_sentences:
                    start_pos = overlap_sentences[0][0]

            chunk_text = original_text[start_pos:end_pos].strip()
            word_count = len(_WORD_PATTERN.findall(chunk_text))

            if word_count < config.min_chunk_size:
                # Merge with next group if too small
                if chunk_index + 1 < len(semantic_groups):
                    next_group = semantic_groups[chunk_index + 1]
                    end_pos = next_group[-1][1]
                    chunk_text = original_text[start_pos:end_pos].strip()
                    word_count = len(_WORD_PATTERN.findall(chunk_text))

            # Skip if still too small (unless it's the only chunk)
            if word_count < config.min_chunk_size and len(chunks) > 0:
                continue

            metadata: dict[str, Any] = {
                "strategy": "semantic",
                "word_count": word_count,
                "start_char": start_pos,
                "end_char": end_pos,
                "chunk_size": config.chunk_size,
                "overlap": config.overlap,
                "sentence_count": len(group),
            }

            chunks.append(
                Chunk(
                    text=chunk_text,
                    index=chunk_index,
                    metadata=metadata,
                )
            )

            chunk_index += 1

        return chunks

    def _get_overlap_sentences(
        self,
        prev_group: list[tuple[int, int, str]],
        overlap_words: int,
    ) -> list[tuple[int, int, str]]:
        """
        Get sentences from previous group for overlap.

        Args:
            prev_group: Previous sentence group
            overlap_words: Desired overlap word count

        Returns:
            List of sentences to include for overlap
        """
        if not prev_group:
            return []

        # Take sentences from the end of previous group
        overlap_sentences: list[tuple[int, int, str]] = []
        word_count = 0

        for sentence in reversed(prev_group):
            sent_words = len(_WORD_PATTERN.findall(sentence[2]))
            if word_count + sent_words <= overlap_words:
                overlap_sentences.insert(0, sentence)
                word_count += sent_words
            else:
                break

        return overlap_sentences

    async def _fallback_fixed(self, text: str, config: ChunkingStrategy) -> list[Chunk]:
        """Fallback to fixed chunking if semantic chunking fails."""
        fixed_strategy = FixedChunkingStrategy(default_config=config)
        fixed_config = ChunkingStrategy(
            strategy=ChunkStrategyType.FIXED,
            chunk_size=config.chunk_size,
            overlap=config.overlap,
            min_chunk_size=config.min_chunk_size,
        )
        chunks = await fixed_strategy.chunk(text, fixed_config)
        for chunk in chunks:
            chunk.metadata["strategy"] = "semantic_fixed_fallback"
        return chunks


__all__ = [
    "FixedChunkingStrategy",
    "SentenceChunkingStrategy",
    "ParagraphChunkingStrategy",
    "SemanticChunkingStrategy",
]
