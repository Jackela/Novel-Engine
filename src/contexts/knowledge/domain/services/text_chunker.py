"""
TextChunker Domain Service

Splits text into overlapping chunks for vector storage and RAG retrieval.

Warzone 4: AI Brain - BRAIN-003
Implements various chunking strategies optimized for semantic search.

Constitution Compliance:
- Article I (DDD): Domain service with pure business logic
- Article II (Hexagonal): No infrastructure dependencies
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, List, Tuple

from ..models.chunking_strategy import (
    ChunkingStrategy,
    ChunkStrategyType,
)


@dataclass(frozen=True, slots=True)
class TextChunk:
    """
    A single chunk of text with metadata for vector storage.

    Why frozen:
        Immutable chunk ensures consistency between creation and storage.

    Attributes:
        content: The chunked text content
        chunk_index: Zero-based index of this chunk in the sequence
        start_pos: Character position where this chunk starts in source text
        end_pos: Character position where this chunk ends in source text
        word_count: Number of words in this chunk
    """

    content: str
    chunk_index: int
    start_pos: int
    end_pos: int
    word_count: int


@dataclass(frozen=True, slots=True)
class ChunkedDocument:
    """
    Result of chunking a document.

    Attributes:
        chunks: List of text chunks
        total_chunks: Total number of chunks
        total_words: Total word count across all chunks
        strategy: The chunking strategy used
    """

    chunks: list[TextChunk]
    total_chunks: int
    total_words: int
    strategy: ChunkingStrategy


class TextChunker:
    """
    Domain service for splitting text into chunks for RAG.

    Supports multiple chunking strategies:
    - FIXED: Split by word count with overlap
    - SENTENCE: Split by sentence boundaries with overlap
    - PARAGRAPH: Split by paragraph boundaries with overlap
    - SEMANTIC: Split by semantic boundaries (higher-level structure)

    All methods are static to keep the service stateless.
    """

    # Regex patterns for splitting
    _SENTENCE_END: Final[re.Pattern] = re.compile(r"[.!?]+\s+", re.MULTILINE)
    _PARAGRAPH_DELIM: Final[re.Pattern] = re.compile(r"\n\n+", re.MULTILINE)
    _WORD_PATTERN: Final[re.Pattern] = re.compile(r"\S+")

    @staticmethod
    def chunk(text: str, strategy: ChunkingStrategy) -> ChunkedDocument:
        """
        Split text into chunks according to the given strategy.

        Args:
            text: Source text to chunk
            strategy: ChunkingStrategy configuration

        Returns:
            ChunkedDocument with chunks and metadata

        Raises:
            ValueError: If text is empty or strategy is invalid
        """
        if not text or not text.strip():
            raise ValueError("Cannot chunk empty text")

        if strategy.strategy == ChunkStrategyType.FIXED:
            chunks = TextChunker._chunk_fixed(text, strategy)
        elif strategy.strategy == ChunkStrategyType.SENTENCE:
            chunks = TextChunker._chunk_by_sentence(text, strategy)
        elif strategy.strategy == ChunkStrategyType.PARAGRAPH:
            chunks = TextChunker._chunk_by_paragraph(text, strategy)
        elif strategy.strategy == ChunkStrategyType.SEMANTIC:
            chunks = TextChunker._chunk_semantic(text, strategy)
        else:
            raise ValueError(f"Unknown strategy type: {strategy.strategy}")

        total_words = sum(chunk.word_count for chunk in chunks)

        return ChunkedDocument(
            chunks=chunks,
            total_chunks=len(chunks),
            total_words=total_words,
            strategy=strategy,
        )

    @staticmethod
    def _chunk_fixed(text: str, strategy: ChunkingStrategy) -> list[TextChunk]:
        """Chunk by fixed word count with overlap."""
        words = TextChunker._WORD_PATTERN.findall(text)
        chunks = []
        chunk_index = 0

        if not words:
            return []

        i = 0
        while i < len(words):
            # Determine end of this chunk
            end_idx = min(i + strategy.chunk_size, len(words))

            # Extract chunk words
            chunk_words = words[i:end_idx]
            chunk_content = " ".join(chunk_words)

            # Track positions
            start_pos = TextChunker._find_position(text, words, i)
            end_pos = TextChunker._find_position(text, words, end_idx - 1) + len(
                words[end_idx - 1]
            )

            chunks.append(
                TextChunk(
                    content=chunk_content,
                    chunk_index=chunk_index,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    word_count=len(chunk_words),
                )
            )

            chunk_index += 1
            # Move forward by effective chunk size
            i += strategy.effective_chunk_size()

        return chunks

    @staticmethod
    def _chunk_by_sentence(text: str, strategy: ChunkingStrategy) -> list[TextChunk]:
        """Chunk by sentence boundaries with overlap."""
        # Find all sentence boundaries
        sentences: List[Tuple[int, int]] = []
        last_end = 0

        for match in TextChunker._SENTENCE_END.finditer(text):
            end_pos = match.end()
            sentences.append((last_end, end_pos))
            last_end = end_pos

        # Add remaining text as last sentence if any
        if last_end < len(text.strip()):
            sentences.append((last_end, len(text)))

        if not sentences:
            # No sentence breaks found, fall back to fixed
            return TextChunker._chunk_fixed(text, strategy)

        # Group sentences into chunks by word count
        chunks: List[TextChunk] = []
        current_sentences: List[Tuple[int, int]] = []
        current_word_count = 0
        chunk_index = 0
        # Overlap tracking computed dynamically for each chunk

        for start, end in sentences:
            sentence_text = text[start:end].strip()
            if not sentence_text:
                continue

            sentence_words = len(TextChunker._WORD_PATTERN.findall(sentence_text))

            # Check if adding this sentence would exceed chunk size
            if current_word_count + sentence_words > strategy.chunk_size:
                if current_sentences:
                    # Create chunk from accumulated sentences
                    chunk_start = current_sentences[0][0]
                    chunk_end = current_sentences[-1][1]
                    chunk_content = text[chunk_start:chunk_end].strip()

                    chunks.append(
                        TextChunk(
                            content=chunk_content,
                            chunk_index=chunk_index,
                            start_pos=chunk_start,
                            end_pos=chunk_end,
                            word_count=current_word_count,
                        )
                    )

                    chunk_index += 1

                # Keep overlap sentences for next chunk
                overlap_to_keep: List[Tuple[int, int]] = []
                overlap_count = 0
                overlap_limit = strategy.overlap or 0
                # Walk backwards from the end of current sentences
                for s_start, s_end in reversed(current_sentences):
                    s_words = len(
                        TextChunker._WORD_PATTERN.findall(text[s_start:s_end])
                    )
                    if overlap_count + s_words <= overlap_limit:
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

            chunks.append(
                TextChunk(
                    content=chunk_content,
                    chunk_index=chunk_index,
                    start_pos=chunk_start,
                    end_pos=chunk_end,
                    word_count=current_word_count,
                )
            )

        return chunks if chunks else TextChunker._chunk_fixed(text, strategy)

    @staticmethod
    def _chunk_by_paragraph(text: str, strategy: ChunkingStrategy) -> list[TextChunk]:
        """Chunk by paragraph boundaries with overlap."""
        # Split by paragraph delimiters
        paragraphs: List[Tuple[int, int]] = []
        last_end = 0

        for match in TextChunker._PARAGRAPH_DELIM.finditer(text):
            end_pos = match.end()
            paragraphs.append(
                (last_end, end_pos - len(match.group()))
            )  # Exclude delimiter
            last_end = end_pos

        # Add remaining text
        if last_end < len(text.strip()):
            paragraphs.append((last_end, len(text)))

        if not paragraphs:
            return TextChunker._chunk_fixed(text, strategy)

        # Group paragraphs into chunks
        chunks: List[TextChunk] = []
        current_paragraphs: List[Tuple[int, int]] = []
        current_word_count = 0
        chunk_index = 0

        for start, end in paragraphs:
            para_text = text[start:end].strip()
            if not para_text:
                continue

            para_words = len(TextChunker._WORD_PATTERN.findall(para_text))

            if current_word_count + para_words > strategy.chunk_size:
                if current_paragraphs:
                    # Create chunk
                    chunk_start = current_paragraphs[0][0]
                    chunk_end = current_paragraphs[-1][1]
                    chunk_content = text[chunk_start:chunk_end].strip()

                    chunks.append(
                        TextChunk(
                            content=chunk_content,
                            chunk_index=chunk_index,
                            start_pos=chunk_start,
                            end_pos=chunk_end,
                            word_count=current_word_count,
                        )
                    )

                    chunk_index += 1

                # Keep overlap paragraphs
                overlap_to_keep: List[Tuple[int, int]] = []
                overlap_count = 0
                overlap_limit = strategy.overlap or 0
                for p_start, p_end in reversed(current_paragraphs):
                    p_words = len(
                        TextChunker._WORD_PATTERN.findall(text[p_start:p_end])
                    )
                    if overlap_count + p_words <= overlap_limit:
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

            chunks.append(
                TextChunk(
                    content=chunk_content,
                    chunk_index=chunk_index,
                    start_pos=chunk_start,
                    end_pos=chunk_end,
                    word_count=current_word_count,
                )
            )

        return chunks if chunks else TextChunker._chunk_fixed(text, strategy)

    @staticmethod
    def _chunk_semantic(text: str, strategy: ChunkingStrategy) -> list[TextChunk]:
        """
        Chunk by semantic boundaries (combination of paragraphs and sentences).

        Why:
            Semantic chunking respects document structure while maintaining
            reasonable chunk sizes for embedding models.
        """
        # First try paragraph-level chunking
        para_chunks = TextChunker._chunk_by_paragraph(text, strategy)

        # If paragraphs are too large, fall back to sentence chunking
        if (
            len(para_chunks) == 1
            and para_chunks[0].word_count > strategy.chunk_size * 1.5
        ):
            return TextChunker._chunk_by_sentence(text, strategy)

        return para_chunks

    @staticmethod
    def _find_position(text: str, words: list[str], word_index: int) -> int:
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

        target_word = words[word_index]
        words_found = 0

        for match in TextChunker._WORD_PATTERN.finditer(text):
            if words_found == word_index:
                # Check if this matches our target word
                if match.group() == target_word:
                    return match.start()
            words_found += 1

        # Fallback: search from the beginning
        return text.find(target_word, max(0, (word_index - 5) * 10))

    @staticmethod
    def count_words(text: str) -> int:
        """
        Count words in text.

        Args:
            text: Text to count words in

        Returns:
            Number of words (sequences of non-whitespace characters)
        """
        return len(TextChunker._WORD_PATTERN.findall(text))

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count for text.

        Why:
            Quick approximation for budgeting context windows.
            Assumes ~1.3 tokens per word for English text.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        word_count = TextChunker.count_words(text)
        return int(word_count * 1.3)


__all__ = [
    "TextChunker",
    "TextChunk",
    "ChunkedDocument",
]
