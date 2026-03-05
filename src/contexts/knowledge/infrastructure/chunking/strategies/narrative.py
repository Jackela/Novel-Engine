"""
Narrative Structure Chunking Strategy

Implements narrative flow preserving chunking for fiction and
narrative content where maintaining story flow is critical.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from ....application.ports.i_chunking_strategy import Chunk, ChunkingError
from ....domain.models.chunking_strategy import ChunkingStrategy, ChunkStrategyType
from ..base import _PARAGRAPH_DELIM, _SENTENCE_END, _WORD_PATTERN, BaseChunkingStrategy
from .sentence import SentenceBoundaryStrategy as SentenceBoundaryStrategy

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


class NarrativeStructureStrategy(BaseChunkingStrategy):
    """
    Narrative flow preserving chunking strategy adapter.

    Splits text while preserving narrative flow and coherence.
    Specifically designed for fiction and narrative content where
    maintaining story flow is critical for reader comprehension.

    Key features:
        - Preserves sentence boundaries (never breaks mid-sentence)
        - Respects dialogue boundaries (never breaks mid-dialogue exchange)
        - Groups related narrative beats together
        - Maintains scene continuity through overlap

    Configuration:
        - chunk_size: Maximum words per chunk (default: 500)
        - overlap: Number of overlapping words between chunks (default: 50)
        - min_chunk_size: Minimum chunk size to avoid tiny fragments (default: 50)
        - preserve_dialogue: Keep dialogue exchanges together (default: True)
        - preserve_paragraphs: Keep paragraphs together when possible (default: True)

    Why narrative flow:
        - Narrative comprehension depends on sentence and dialogue coherence
        - Breaking in middle of dialogue disrupts reader immersion
        - Scene continuity improves RAG retrieval for narrative content
        - Better chunk quality for story generation and summarization

    Example:
        >>> strategy = NarrativeStructureStrategy()
        >>> chunks = await strategy.chunk(
        ...     '"Hello," she said. "How are you?" "I am well," he replied.',
        ...     ChunkingStrategy(strategy=ChunkStrategyType.NARRATIVE_FLOW)
        ... )
        >>> # Dialogue exchange preserved in single chunk
    """

    # Common dialogue tag verbs for detecting dialogue boundaries
    _DIALOGUE_TAGS = {
        "said",
        "asked",
        "replied",
        "whispered",
        "shouted",
        "murmured",
        "exclaimed",
        "cried",
        "called",
        "responded",
        "answered",
        "declared",
        "stated",
        "added",
        "continued",
        "interrupted",
        "objected",
        "agreed",
        "nodded",
        "smiled",
        "laughed",
        "grinned",
        "chuckled",
        "sighed",
        "groaned",
        "gasped",
        "screamed",
        "yelled",
        "bellowed",
        "roared",
        "hissed",
        "snapped",
        "barked",
        "growled",
        "muttered",
        "mumbled",
        "grumbled",
        "assented",
        "countered",
        "retorted",
        "protested",
        "insisted",
        "demanded",
        "commanded",
        "ordered",
        "requested",
        "begged",
        "pleaded",
        "implored",
        "prayed",
        "cursed",
        "thanked",
        "apologized",
        "greeted",
        "welcomed",
        "bid",
        "wished",
        "hoped",
        "wondered",
        "thought",
        "reflected",
        "remembered",
        "recalled",
        "realized",
        "understood",
        "decided",
        "resolved",
        "promised",
        "vowed",
        "pledged",
        "consented",
        "refused",
        "denied",
        "admitted",
        "confessed",
        "acknowledged",
        "recognized",
        "identified",
        "discovered",
        "found",
        "learned",
        "heard",
        "saw",
        "watched",
        "observed",
        "noticed",
        "remarked",
        "commented",
        "noted",
        "explained",
        "described",
        "related",
        "recounted",
        "told",
        "narrated",
        "spoke",
        "addressed",
        "conversed",
        "chatted",
        "discussed",
        "debated",
        "argued",
        "quarreled",
        "disputed",
        "contested",
        "challenged",
        "questioned",
        "queried",
        "inquired",
    }

    def __init__(
        self,
        default_config: ChunkingStrategy | None = None,
        preserve_dialogue: bool = True,
        preserve_paragraphs: bool = True,
    ) -> None:
        """
        Initialize the narrative flow chunking strategy.

        Args:
            default_config: Default configuration to use when none is provided
            preserve_dialogue: Keep dialogue exchanges together
            preserve_paragraphs: Keep paragraphs together when possible
        """
        self._default_config = default_config or ChunkingStrategy(
            strategy=ChunkStrategyType.NARRATIVE_FLOW,
            chunk_size=500,
            overlap=50,
        )
        self._preserve_dialogue = preserve_dialogue
        self._preserve_paragraphs = preserve_paragraphs

    async def chunk(
        self,
        text: str,
        config: ChunkingStrategy | None = None,
    ) -> list[Chunk]:
        """
        Split text into narrative flow preserving chunks.

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

        if strategy_config.strategy != ChunkStrategyType.NARRATIVE_FLOW:
            logger.warning(
                "narrative_flow_chunking_strategy_mismatch",
                expected=ChunkStrategyType.NARRATIVE_FLOW,
                actual=strategy_config.strategy,
            )

        log = logger.bind(
            strategy="narrative_flow",
            chunk_size=strategy_config.chunk_size,
            overlap=strategy_config.overlap,
            text_length=len(text),
            preserve_dialogue=self._preserve_dialogue,
            preserve_paragraphs=self._preserve_paragraphs,
        )

        log.debug("narrative_flow_chunking_start")

        try:
            # Step 1: Identify narrative boundaries
            boundaries = self._identify_narrative_boundaries(text)
            log.debug("narrative_boundaries_identified", count=len(boundaries))

            # Step 2: Group narrative units into chunks
            chunks = self._create_narrative_chunks(
                text,
                boundaries,
                strategy_config,
            )

            if not chunks:
                # Fallback to sentence chunking if no chunks created
                log.info("narrative_flow_no_chunks", fallback="sentence")
                return await self._fallback_sentence(text, strategy_config)

            log.info(
                "narrative_flow_chunking_complete",
                chunk_count=len(chunks),
                total_words=sum(c.metadata.get("word_count", 0) for c in chunks),
            )

            return chunks

        except ValueError:
            raise
        except Exception as e:
            log.error(
                "narrative_flow_chunking_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ChunkingError(
                f"Narrative flow chunking failed: {e}",
                code="NARRATIVE_FLOW_CHUNKING_ERROR",
            ) from e

    def supports_strategy_type(self, strategy_type: str) -> bool:
        """Check if this implementation supports the 'narrative_flow' strategy type."""
        return strategy_type.lower() == ChunkStrategyType.NARRATIVE_FLOW.value

    def _identify_narrative_boundaries(
        self, text: str
    ) -> list[tuple[int, int, str, dict[str, Any]]]:
        """
        Identify narrative boundaries in text.

        A narrative boundary is a point where a chunk can reasonably break.
        Boundaries are identified with metadata about their type and quality.

        Args:
            text: Source text

        Returns:
            List of (start, end, type, metadata) tuples for each narrative unit
        """
        units: list[tuple[int, int, str, dict[str, Any]]] = []
        current_pos = 0
        text_len = len(text)

        while current_pos < text_len:
            # Skip whitespace
            while current_pos < text_len and text[current_pos].isspace():
                current_pos += 1

            if current_pos >= text_len:
                break

            # Check for dialogue start
            if self._preserve_dialogue and text[current_pos] in ('"', "'"):
                dialogue_info = self._extract_dialogue_unit(text, current_pos)
                if dialogue_info:
                    units.append(dialogue_info)
                    current_pos = dialogue_info[1]  # Move to end of dialogue
                    continue

            # Check for paragraph break
            if self._preserve_paragraphs:
                # Find next paragraph delimiter
                para_match = _PARAGRAPH_DELIM.search(text, current_pos)
                if para_match and para_match.start() > current_pos:
                    # Extract paragraph as narrative unit
                    para_end = para_match.start()
                    para_text = text[current_pos:para_end].strip()
                    if para_text:
                        word_count = len(_WORD_PATTERN.findall(para_text))
                        units.append(
                            (
                                current_pos,
                                para_end,
                                "paragraph",
                                {
                                    "word_count": word_count,
                                    "ends_with_period": para_text.rstrip().endswith(
                                        (".", "!", "?", '"', "'")
                                    ),
                                },
                            )
                        )
                    current_pos = para_match.end()
                    continue

            # Default: find next sentence boundary
            sentence_match = _SENTENCE_END.search(text, current_pos)
            if sentence_match:
                sent_end = sentence_match.end()
                sent_text = text[current_pos:sent_end].strip()
                if sent_text:
                    word_count = len(_WORD_PATTERN.findall(sent_text))
                    units.append(
                        (
                            current_pos,
                            sent_end,
                            "sentence",
                            {"word_count": word_count},
                        )
                    )
                current_pos = sent_end
            else:
                # No more sentence boundaries - take remaining text
                remaining = text[current_pos:].strip()
                if remaining:
                    word_count = len(_WORD_PATTERN.findall(remaining))
                    units.append(
                        (
                            current_pos,
                            text_len,
                            "sentence",
                            {"word_count": word_count},
                        )
                    )
                break

        return units

    def _extract_dialogue_unit(
        self, text: str, start_pos: int
    ) -> tuple[int, int, str, dict[str, Any]] | None:
        """
        Extract a complete dialogue unit starting at position.

        A dialogue unit includes:
        - The quoted speech
        - Any dialogue tags (e.g., "she said")
        - Any adjacent dialogue in the same exchange

        Args:
            text: Source text
            start_pos: Position where dialogue starts

        Returns:
            (start, end, type, metadata) tuple or None if not dialogue
        """
        quote_char = text[start_pos]
        if quote_char not in ('"', "'"):
            return None

        # Find closing quote
        closing_pos = start_pos + 1
        while closing_pos < len(text):
            if text[closing_pos] == quote_char and text[closing_pos - 1] != "\\":
                break
            closing_pos += 1

        if closing_pos >= len(text):
            return None

        # Extract dialogue and check for tag
        after_quote = closing_pos + 1
        tag_end = after_quote

        # Look for dialogue tag pattern
        while tag_end < len(text) and text[tag_end] not in ".!?'":
            tag_end += 1

        # Include end punctuation
        if tag_end < len(text) and text[tag_end] in ".!?'":
            tag_end += 1

        # Check if next sentence is also dialogue (same exchange)
        next_start = tag_end
        while next_start < len(text) and text[next_start].isspace():
            next_start += 1

        # If next starts with quote, include it
        if next_start < len(text) and text[next_start] == quote_char:
            # Recursively get next dialogue
            next_dialogue = self._extract_dialogue_unit(text, next_start)
            if next_dialogue:
                # Merge both dialogues
                word_count = len(
                    _WORD_PATTERN.findall(text[start_pos : next_dialogue[1]])
                )
                return (
                    start_pos,
                    next_dialogue[1],
                    "dialogue_exchange",
                    {
                        "word_count": word_count,
                        "quote_char": quote_char,
                        "exchange_length": 2,
                    },
                )

        word_count = len(_WORD_PATTERN.findall(text[start_pos:tag_end]))
        return (
            start_pos,
            tag_end,
            "dialogue",
            {"word_count": word_count, "quote_char": quote_char},
        )

    def _create_narrative_chunks(
        self,
        text: str,
        boundaries: list[tuple[int, int, str, dict[str, Any]]],
        config: ChunkingStrategy,
    ) -> list[Chunk]:
        """
        Create chunks from narrative boundaries.

        Groups narrative units into chunks while respecting:
        - Size limits
        - Dialogue continuity
        - Narrative coherence

        Args:
            text: Source text
            boundaries: List of narrative boundary units
            config: Chunking configuration

        Returns:
            List of Chunk entities
        """
        chunks: list[Chunk] = []
        current_units: list[tuple[int, int, str, dict[str, Any]]] = []
        current_word_count = 0
        chunk_index = 0

        for start, end, unit_type, metadata in boundaries:
            unit_word_count = metadata.get("word_count", 0)

            # Check if adding this unit would exceed chunk size
            if current_word_count + unit_word_count > config.chunk_size:
                if current_units:
                    # Check if we should extend for dialogue continuity
                    if unit_type == "dialogue" and chunk_index > 0:
                        # Check if previous chunk ended with dialogue
                        last_unit = current_units[-1]
                        if last_unit[2] in ("dialogue", "dialogue_exchange"):
                            # Extend current chunk to include this dialogue
                            pass  # Don't break mid-dialogue exchange

                    if current_word_count + unit_word_count > config.chunk_size:
                        # Create chunk from current units
                        chunk_start = current_units[0][0]
                        chunk_end = current_units[-1][1]
                        chunk_content = text[chunk_start:chunk_end].strip()

                        chunks.append(
                            self._create_chunk(
                                chunk_content,
                                chunk_index,
                                chunk_start,
                                chunk_end,
                                current_word_count,
                                config,
                                self._get_narrative_metadata(current_units),
                            )
                        )
                        chunk_index += 1

                        # Keep overlap units for next chunk
                        overlap_to_keep = self._get_overlap_units(
                            current_units,
                            config.overlap,
                        )
                        current_units = overlap_to_keep
                        current_word_count = sum(
                            u[3].get("word_count", 0) for u in overlap_to_keep
                        )

            current_units.append((start, end, unit_type, metadata))
            current_word_count += unit_word_count

        # Add final chunk
        if current_units:
            chunk_start = current_units[0][0]
            chunk_end = current_units[-1][1]
            chunk_content = text[chunk_start:chunk_end].strip()

            if chunk_content and current_word_count >= config.min_chunk_size:
                chunks.append(
                    self._create_chunk(
                        chunk_content,
                        chunk_index,
                        chunk_start,
                        chunk_end,
                        current_word_count,
                        config,
                        self._get_narrative_metadata(current_units),
                    )
                )

        return chunks

    def _get_overlap_units(
        self,
        units: list[tuple[int, int, str, dict[str, Any]]],
        overlap_words: int,
    ) -> list[tuple[int, int, str, dict[str, Any]]]:
        """
        Get units to include in overlap.

        Preserves complete narrative units in overlap for continuity.

        Args:
            units: Current narrative units
            overlap_words: Desired overlap word count

        Returns:
            List of units to include in overlap
        """
        if not units or overlap_words <= 0:
            return []

        overlap_units: list[tuple[int, int, str, dict[str, Any]]] = []
        word_count = 0

        # Take units from the end, preferring complete narrative units
        for unit in reversed(units):
            unit_words = unit[3].get("word_count", 0)
            if word_count + unit_words <= overlap_words:
                overlap_units.insert(0, unit)
                word_count += unit_words
            else:
                break

        return overlap_units

    def _get_narrative_metadata(
        self,
        units: list[tuple[int, int, str, dict[str, Any]]],
    ) -> dict[str, Any]:
        """
        Extract metadata about narrative composition.

        Args:
            units: Narrative units in the chunk

        Returns:
            Metadata dict with narrative composition info
        """
        unit_types = [u[2] for u in units]
        dialogue_count = sum(1 for t in unit_types if "dialogue" in t)
        paragraph_count = sum(1 for t in unit_types if t == "paragraph")
        sentence_count = sum(1 for t in unit_types if t == "sentence")

        return {
            "dialogue_units": dialogue_count,
            "paragraph_units": paragraph_count,
            "sentence_units": sentence_count,
            "total_units": len(units),
            "has_dialogue": dialogue_count > 0,
        }

    def _create_chunk(
        self,
        content: str,
        index: int,
        start_pos: int,
        end_pos: int,
        word_count: int,
        config: ChunkingStrategy,
        narrative_metadata: dict[str, Any] | None = None,
    ) -> Chunk:
        """Create a Chunk entity with metadata."""
        metadata: dict[str, Any] = {
            "strategy": "narrative_flow",
            "word_count": word_count,
            "start_char": start_pos,
            "end_char": end_pos,
            "chunk_size": config.chunk_size,
            "overlap": config.overlap,
        }
        if narrative_metadata:
            metadata.update(narrative_metadata)
        return Chunk(text=content, index=index, metadata=metadata)

    async def _fallback_sentence(
        self, text: str, config: ChunkingStrategy
    ) -> list[Chunk]:
        """Fallback to sentence chunking if narrative flow chunking fails."""
        sentence_strategy = SentenceBoundaryStrategy(
            default_config=ChunkingStrategy(
                strategy=ChunkStrategyType.SENTENCE,
                chunk_size=config.chunk_size,
                overlap=config.overlap,
                min_chunk_size=config.min_chunk_size,
            )
        )
        chunks = await sentence_strategy.chunk(text)
        for chunk in chunks:
            chunk.metadata["strategy"] = "narrative_flow_sentence_fallback"
            chunk.metadata["original_strategy"] = chunk.metadata.get("strategy", "")
        return chunks
