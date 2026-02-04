"""
Tests for Citation Formatter Service

Warzone 4: AI Brain - BRAIN-012
Tests for citation formatting and source attribution.
"""

import pytest

from src.contexts.knowledge.application.services.citation_formatter import (
    CitationFormatter,
    CitationFormatterConfig,
    SourceReference,
    ChunkCitation,
    CitationFormat,
)
from src.contexts.knowledge.application.services.knowledge_ingestion_service import RetrievedChunk
from src.contexts.knowledge.domain.models.source_type import SourceType


@pytest.fixture
def sample_chunks() -> list[RetrievedChunk]:
    """Create sample retrieved chunks for testing."""
    return [
        RetrievedChunk(
            chunk_id="char_alice_chunk_0",
            source_id="char_alice",
            source_type=SourceType.CHARACTER,
            content="Alice is a brave warrior with exceptional sword skills.",
            score=0.92,
            metadata={
                "source_id": "char_alice",
                "source_type": "CHARACTER",
                "chunk_index": 0,
                "total_chunks": 1,
                "name": "Alice the Brave",
            },
        ),
        RetrievedChunk(
            chunk_id="lore_kingdom_chunk_0",
            source_id="lore_kingdom_history",
            source_type=SourceType.LORE,
            content="The Kingdom of Eldoria was founded in the Age of Myth.",
            score=0.87,
            metadata={
                "source_id": "lore_kingdom_history",
                "source_type": "LORE",
                "chunk_index": 0,
                "total_chunks": 2,
                "name": "Kingdom History",
            },
        ),
        RetrievedChunk(
            chunk_id="char_alice_chunk_1",
            source_id="char_alice",
            source_type=SourceType.CHARACTER,
            content="She carries a magical sword passed down through generations.",
            score=0.88,
            metadata={
                "source_id": "char_alice",
                "source_type": "CHARACTER",
                "chunk_index": 1,
                "total_chunks": 2,
                "name": "Alice the Brave",
            },
        ),
        RetrievedChunk(
            chunk_id="scene_tavern_chunk_0",
            source_id="scene_tavern_encounter",
            source_type=SourceType.SCENE,
            content="The tavern was dimly lit, filled with the smell of ale and adventure.",
            score=0.75,
            metadata={
                "source_id": "scene_tavern_encounter",
                "source_type": "SCENE",
                "chunk_index": 0,
                "total_chunks": 1,
                "name": "Tavern Encounter",
            },
        ),
    ]


class TestCitationFormatter:
    """Tests for CitationFormatter class."""

    def test_format_chunks_with_numeric_style(self, sample_chunks):
        """Test formatting chunks with numeric citation style."""
        formatter = CitationFormatter(CitationFormatterConfig(format_style="numeric"))

        result = formatter.format_chunks(sample_chunks)

        assert isinstance(result, CitationFormat)
        assert len(result.inline_markers) == 4
        assert result.inline_markers == ["[1]", "[2]", "[3]", "[4]"]
        assert len(result.references_dict) == 3  # 3 unique sources
        assert "Sources:" in result.sources_list

    def test_format_chunks_with_alphabetic_style(self, sample_chunks):
        """Test formatting chunks with alphabetic citation style."""
        formatter = CitationFormatter(CitationFormatterConfig(format_style="alphabetic"))

        result = formatter.format_chunks(sample_chunks)

        assert len(result.inline_markers) == 4
        assert result.inline_markers == ["[a]", "[b]", "[c]", "[d]"]

    def test_format_chunks_with_source_type_style(self, sample_chunks):
        """Test formatting chunks with source type citation style."""
        formatter = CitationFormatter(CitationFormatterConfig(format_style="source_type"))

        result = formatter.format_chunks(sample_chunks)

        # Citation IDs should contain source type prefixes
        assert any("C:" in ref.citation_id or "char_alice" in ref.citation_id
                   for ref in result.references_dict.values())

    def test_format_chunks_empty_list(self):
        """Test formatting empty chunk list."""
        formatter = CitationFormatter()

        result = formatter.format_chunks([])

        assert result.inline_markers == []
        assert result.sources_list == ""
        assert result.references_dict == {}

    def test_format_chunks_with_custom_names(self, sample_chunks):
        """Test formatting with custom display names."""
        formatter = CitationFormatter()
        source_names = {
            "char_alice": "Alice, Warrior of Light",
            "lore_kingdom_history": "Ancient Eldoria Chronicles",
        }

        result = formatter.format_chunks(sample_chunks, source_names)

        # Check custom names are used
        alice_ref = next(
            (r for r in result.references_dict.values()
             if r.source_id == "char_alice"),
            None
        )
        assert alice_ref is not None
        assert "Alice, Warrior of Light" in alice_ref.display_name

    def test_get_sources_returns_unique_sources(self, sample_chunks):
        """Test that get_sources returns unique sources."""
        formatter = CitationFormatter()

        sources = formatter.get_sources(sample_chunks)

        # Should have 3 unique sources (alice appears twice)
        assert len(sources) == 3

        # Check source types
        source_types = {s.source_type for s in sources}
        assert source_types == {SourceType.CHARACTER, SourceType.LORE, SourceType.SCENE}

    def test_get_sources_sorted_by_relevance(self, sample_chunks):
        """Test that sources are sorted by relevance score."""
        formatter = CitationFormatter()

        sources = formatter.get_sources(sample_chunks)

        # Should be sorted by relevance (highest first)
        assert sources[0].source_id == "char_alice"
        assert sources[0].relevance_score == pytest.approx(0.9, 0.1)  # Average of 0.92 and 0.88

    def test_get_sources_includes_chunk_count(self, sample_chunks):
        """Test that sources include chunk count."""
        formatter = CitationFormatter()

        sources = formatter.get_sources(sample_chunks)

        alice = next(s for s in sources if s.source_id == "char_alice")
        assert alice.chunk_count == 2

        kingdom = next(s for s in sources if s.source_id == "lore_kingdom_history")
        assert kingdom.chunk_count == 1

    def test_format_citation_marker_numeric(self, sample_chunks):
        """Test formatting single citation marker in numeric style."""
        formatter = CitationFormatter(CitationFormatterConfig(format_style="numeric"))

        marker = formatter.format_citation_marker(sample_chunks[0], "1")
        assert marker == "[1]"

    def test_format_citation_marker_source_type(self, sample_chunks):
        """Test formatting single citation marker in source type style."""
        formatter = CitationFormatter(CitationFormatterConfig(format_style="source_type"))

        marker = formatter.format_citation_marker(sample_chunks[0], "")
        assert "C:" in marker or "char_alice" in marker

    def test_include_chunk_index_in_marker(self, sample_chunks):
        """Test including chunk index in citation markers."""
        formatter = CitationFormatter(
            CitationFormatterConfig(
                format_style="source_type",
                include_chunk_index=True
            )
        )

        marker = formatter.format_citation_marker(sample_chunks[0], "")
        # Should contain chunk index
        assert ":0" in marker or ":1" in marker

    def test_include_relevance_in_markers(self, sample_chunks):
        """Test including relevance scores in markers."""
        formatter = CitationFormatter(
            CitationFormatterConfig(include_relevance=True)
        )

        result = formatter.format_chunks(sample_chunks)

        # Markers should include scores
        for marker in result.inline_markers:
            assert "score:" in marker

    def test_max_sources_display_limit(self, sample_chunks):
        """Test max_sources_display limits sources in list."""
        formatter = CitationFormatter(CitationFormatterConfig(max_sources_display=2))

        result = formatter.format_chunks(sample_chunks)

        # Should have all references but only 2 in formatted list
        assert len(result.references_dict) == 3
        assert "... and 1 more" in result.sources_list or "... and" in result.sources_list

    def test_sources_list_format(self, sample_chunks):
        """Test the format of the sources list."""
        formatter = CitationFormatter()

        result = formatter.format_chunks(sample_chunks)

        lines = result.sources_list.split("\n")
        assert lines[0] == "Sources:"
        # Each source should start with "  ["
        for line in lines[1:]:
            if line.strip() and not line.strip().startswith("..."):
                assert line.strip().startswith("[")

    def test_number_to_alpha_conversion(self):
        """Test number to alphabetic conversion."""
        formatter = CitationFormatter()

        # Single letters
        assert formatter._number_to_alpha(1) == "a"
        assert formatter._number_to_alpha(26) == "z"

        # Double letters
        assert formatter._number_to_alpha(27) == "aa"
        assert formatter._number_to_alpha(28) == "ab"
        assert formatter._number_to_alpha(52) == "az"
        assert formatter._number_to_alpha(53) == "ba"

    def test_source_reference_immutability(self, sample_chunks):
        """Test that SourceReference is immutable (frozen)."""
        formatter = CitationFormatter()

        sources = formatter.get_sources(sample_chunks)

        # SourceReference should be frozen dataclass
        with pytest.raises(Exception):  # FrozenInstanceError or similar
            sources[0].source_id = "modified"

    def test_source_type_prefixes(self):
        """Test source type prefixes are correct."""
        prefixes = CitationFormatter.SOURCE_TYPE_PREFIXES

        assert prefixes[SourceType.CHARACTER] == "C"
        assert prefixes[SourceType.LORE] == "L"
        assert prefixes[SourceType.SCENE] == "S"
        assert prefixes[SourceType.PLOTLINE] == "P"
        assert prefixes[SourceType.ITEM] == "I"
        assert prefixes[SourceType.LOCATION] == "Loc"


class TestSourceReference:
    """Tests for SourceReference value object."""

    def test_source_reference_creation(self):
        """Test creating a SourceReference."""
        ref = SourceReference(
            source_type=SourceType.CHARACTER,
            source_id="char_1",
            citation_id="C1",
            display_name="Alice",
            chunk_count=3,
            relevance_score=0.95,
        )

        assert ref.source_type == SourceType.CHARACTER
        assert ref.source_id == "char_1"
        assert ref.citation_id == "C1"
        assert ref.display_name == "Alice"
        assert ref.chunk_count == 3
        assert ref.relevance_score == 0.95

    def test_source_reference_defaults(self):
        """Test SourceReference default values."""
        ref = SourceReference(
            source_type=SourceType.LORE,
            source_id="lore_1",
            citation_id="L1",
            display_name="History",
        )

        assert ref.chunk_count == 1
        assert ref.relevance_score == 0.0


class TestCitationFormat:
    """Tests for CitationFormat value object."""

    def test_citation_format_creation(self):
        """Test creating a CitationFormat."""
        format_obj = CitationFormat(
            inline_markers=["[1]", "[2]"],
            sources_list="Sources:\n  [1] Character:alice",
            references_dict={"1": SourceReference(
                source_type=SourceType.CHARACTER,
                source_id="alice",
                citation_id="1",
                display_name="Alice",
            )},
        )

        assert len(format_obj.inline_markers) == 2
        assert "Sources:" in format_obj.sources_list
        assert "1" in format_obj.references_dict
