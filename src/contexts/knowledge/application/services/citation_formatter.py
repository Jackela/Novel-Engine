"""
Citation Formatter Service

Generates and manages citations for RAG-retrieved content.
Shows where retrieved information comes from with clickable source markers.

Constitution Compliance:
- Article II (Hexagonal): Application service for citation formatting
- Article V (SOLID): SRP - citation formatting only

Warzone 4: AI Brain - BRAIN-012
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import structlog

from ...domain.models.source_type import SourceType
from ..services.knowledge_ingestion_service import RetrievedChunk

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class SourceReference:
    """
    A reference to a source used in RAG retrieval.

    Why frozen:
        Immutable snapshot ensures source references aren't modified.

    Attributes:
        source_type: Type of source (CHARACTER, LORE, SCENE, etc.)
        source_id: Unique ID of the source entity
        citation_id: Short ID for display (e.g., "C1", "L2")
        display_name: Human-readable name for the source
        chunk_count: Number of chunks from this source
        relevance_score: Average relevance score across chunks
    """

    source_type: SourceType
    source_id: str
    citation_id: str
    display_name: str
    chunk_count: int = 1
    relevance_score: float = 0.0


@dataclass(frozen=True, slots=True)
class ChunkCitation:
    """
    Citation marker for a specific chunk.

    Attributes:
        chunk_id: ID of the chunk
        citation_id: Short ID for display (e.g., "[1]")
        source_reference: Reference to the source
        position_hint: Suggested position in text for citation insertion
    """

    chunk_id: str
    citation_id: str
    source_reference: SourceReference
    position_hint: str | None = None


@dataclass(frozen=True, slots=True)
class CitationFormat:
    """
    Formatted citation output.

    Attributes:
        inline_markers: List of inline citation markers for insertion
        sources_list: Formatted sources list for display
        references_dict: Dict mapping citation IDs to source references
    """

    inline_markers: list[str]
    sources_list: str
    references_dict: dict[str, SourceReference]


@dataclass
class CitationFormatterConfig:
    """
    Configuration for citation formatting.

    Attributes:
        format_style: Citation format style (numeric, alphabetic, source_type)
        include_chunk_index: Whether to include chunk index in citations
        include_relevance: Whether to include relevance scores
        max_sources_display: Maximum number of sources to display in list
    """

    format_style: str = "numeric"  # numeric, alphabetic, source_type
    include_chunk_index: bool = False
    include_relevance: bool = False
    max_sources_display: int = 20


class CitationFormatter:
    """
    Service for formatting citations from retrieved chunks.

    Generates citation markers, source lists, and reference dictionaries
    for RAG-retrieved content.

    Why this matters:
        When AI generates content using RAG, users need to know where
        information came from. Citations provide transparency and allow
        verification of AI claims.

    Example:
        >>> formatter = CitationFormatter()
        >>> citations = formatter.format_chunks(chunks)
        >>> print(citations.sources_list)
        >>> Sources: [Character:alice] [Lore:kingdom_history]
    """

    # Citation prefixes by source type
    SOURCE_TYPE_PREFIXES: dict[SourceType, str] = {
        SourceType.CHARACTER: "C",
        SourceType.LORE: "L",
        SourceType.SCENE: "S",
        SourceType.PLOTLINE: "P",
        SourceType.ITEM: "I",
        SourceType.LOCATION: "Loc",
    }

    def __init__(self, config: CitationFormatterConfig | None = None):
        """
        Initialize the citation formatter.

        Args:
            config: Optional configuration for citation formatting
        """
        self._config = config or CitationFormatterConfig()

    def format_chunks(
        self,
        chunks: list[RetrievedChunk],
        source_names: dict[str, str] | None = None,
    ) -> CitationFormat:
        """
        Format citations for a list of retrieved chunks.

        Args:
            chunks: List of retrieved chunks
            source_names: Optional mapping of source_id to display names

        Returns:
            CitationFormat with formatted citations

        Example:
            >>> citations = formatter.format_chunks(chunks)
            >>> for marker in citations.inline_markers:
            >>>     print(f"Insert {marker} after relevant sentence")
        """
        if not chunks:
            return CitationFormat(
                inline_markers=[],
                sources_list="",
                references_dict={},
            )

        # Group chunks by source
        source_groups = self._group_by_source(chunks)

        # Generate citation IDs and references
        references = self._generate_references(source_groups, source_names)

        # Create inline markers
        markers = self._generate_inline_markers(chunks, references)

        # Format sources list
        sources_text = self._format_sources_list(references)

        return CitationFormat(
            inline_markers=markers,
            sources_list=sources_text,
            references_dict=references,
        )

    def get_sources(
        self,
        chunks: list[RetrievedChunk],
        source_names: dict[str, str] | None = None,
    ) -> list[SourceReference]:
        """
        Extract unique source references from chunks.

        Args:
            chunks: List of retrieved chunks
            source_names: Optional mapping of source_id to display names

        Returns:
            List of unique SourceReference objects, sorted by relevance

        Example:
            >>> sources = formatter.get_sources(chunks)
            >>> for source in sources:
            >>>     print(f"{source.source_type}:{source.source_id}")
        """
        if not chunks:
            return []

        # Group by source
        source_groups = self._group_by_source(chunks)

        # Generate references without formatting
        references = self._generate_references(source_groups, source_names)

        # Return as list, sorted by relevance score
        return sorted(
            list(references.values()),
            key=lambda r: r.relevance_score,
            reverse=True,
        )

    def format_citation_marker(
        self,
        chunk: RetrievedChunk,
        citation_id: str,
    ) -> str:
        """
        Format a single inline citation marker.

        Args:
            chunk: The chunk to cite
            citation_id: The citation ID for this chunk

        Returns:
            Formatted citation marker string

        Example:
            >>> marker = formatter.format_citation_marker(chunk, "1")
            >>> print(marker)  # "[1]"
        """
        if self._config.format_style == "alphabetic":
            return f"[{citation_id}]"
        elif self._config.format_style == "source_type":
            prefix = self.SOURCE_TYPE_PREFIXES.get(
                chunk.source_type, chunk.source_type.value[0].upper()
            )
            chunk_index = chunk.metadata.get("chunk_index", "")
            if self._config.include_chunk_index and isinstance(chunk_index, int):
                return f"[{prefix}{chunk.source_id}:{chunk_index}]"
            return f"[{prefix}:{chunk.source_id}]"
        else:
            # Default numeric style
            return f"[{citation_id}]"

    def _group_by_source(
        self,
        chunks: list[RetrievedChunk],
    ) -> dict[tuple[SourceType, str], list[RetrievedChunk]]:
        """
        Group chunks by their source.

        Args:
            chunks: List of retrieved chunks

        Returns:
            Dict mapping (source_type, source_id) to list of chunks
        """
        groups: dict[tuple[SourceType, str], list[RetrievedChunk]] = defaultdict(list)

        for chunk in chunks:
            key = (chunk.source_type, chunk.source_id)
            groups[key].append(chunk)

        return dict(groups)

    def _generate_references(
        self,
        source_groups: dict[tuple[SourceType, str], list[RetrievedChunk]],
        source_names: dict[str, str] | None,
    ) -> dict[str, SourceReference]:
        """
        Generate source references from grouped chunks.

        Args:
            source_groups: Chunks grouped by source
            source_names: Optional mapping of source_id to display names

        Returns:
            Dict mapping citation IDs to SourceReference objects
        """
        references: dict[str, SourceReference] = {}

        for idx, ((source_type, source_id), chunks) in enumerate(
            source_groups.items(), 1
        ):
            # Calculate average relevance score
            avg_score = sum(c.score for c in chunks) / len(chunks)

            # Generate citation ID based on format style
            if self._config.format_style == "alphabetic":
                citation_id = self._number_to_alpha(idx)
            elif self._config.format_style == "source_type":
                prefix = self.SOURCE_TYPE_PREFIXES.get(
                    source_type, source_type.value[0].upper()
                )
                citation_id = f"{prefix}:{source_id}"
            else:  # numeric (default)
                citation_id = str(idx)

            # Get display name
            if source_names and source_id in source_names:
                display_name = source_names[source_id]
            else:
                display_name = self._generate_display_name(
                    source_type, source_id, chunks[0]
                )

            references[citation_id] = SourceReference(
                source_type=source_type,
                source_id=source_id,
                citation_id=citation_id,
                display_name=display_name,
                chunk_count=len(chunks),
                relevance_score=avg_score,
            )

        return references

    def _generate_inline_markers(
        self,
        chunks: list[RetrievedChunk],
        references: dict[str, SourceReference],
    ) -> list[str]:
        """
        Generate inline citation markers for chunks.

        Args:
            chunks: List of retrieved chunks
            references: Source reference mapping

        Returns:
            List of citation marker strings
        """
        markers: list[str] = []

        for idx, chunk in enumerate(chunks, 1):
            if self._config.format_style == "source_type":
                marker = self.format_citation_marker(chunk, "")
            elif self._config.format_style == "alphabetic":
                # Generate alphabetic citation ID
                marker = f"[{self._number_to_alpha(idx)}]"
            else:
                marker = f"[{idx}]"

            if self._config.include_relevance:
                marker = f"{marker} (score: {chunk.score:.2f})"

            markers.append(marker)

        return markers

    def _format_sources_list(
        self,
        references: dict[str, SourceReference],
    ) -> str:
        """
        Format the sources list for display.

        Args:
            references: Source reference mapping

        Returns:
            Formatted sources list string
        """
        if not references:
            return ""

        lines: list[str] = ["Sources:"]
        sorted_refs = sorted(
            references.values(),
            key=lambda r: r.relevance_score,
            reverse=True,
        )[: self._config.max_sources_display]

        for ref in sorted_refs:
            if self._config.include_relevance:
                line = f"  [{ref.citation_id}] {ref.source_type.value}:{ref.source_id} - {ref.display_name} (relevance: {ref.relevance_score:.2f})"
            else:
                line = f"  [{ref.citation_id}] {ref.source_type.value}:{ref.source_id} - {ref.display_name}"
            lines.append(line)

        if len(references) > self._config.max_sources_display:
            lines.append(
                f"  ... and {len(references) - self._config.max_sources_display} more"
            )

        return "\n".join(lines)

    def _generate_display_name(
        self,
        source_type: SourceType,
        source_id: str,
        chunk: RetrievedChunk,
    ) -> str:
        """
        Generate a display name for a source.

        Args:
            source_type: Type of source
            source_id: Source ID
            chunk: First chunk from this source

        Returns:
            Human-readable display name
        """
        # Try to extract name from metadata
        metadata = chunk.metadata or {}
        if "name" in metadata:
            return str(metadata["name"])

        # Use source_id as fallback
        return source_id

    def _number_to_alpha(self, n: int) -> str:
        """
        Convert a number to alphabetic format (1=a, 2=b, ..., 27=aa).

        Args:
            n: Number to convert

        Returns:
            Alphabetic string
        """
        result = ""
        while n > 0:
            n -= 1
            result = chr(n % 26 + ord("a")) + result
            n //= 26
        return result


__all__ = [
    "CitationFormatter",
    "CitationFormatterConfig",
    "SourceReference",
    "ChunkCitation",
    "CitationFormat",
]
