# mypy: disable-error-code="misc, unreachable"
"""Tests for the Document entity.

This module contains comprehensive tests for the Document domain entity,
covering content management, tagging, indexing, and chunking.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from src.contexts.knowledge.domain.entities.document import Document


@pytest.fixture
def valid_document() -> Document:
    """Create a valid document for testing."""
    return Document(
        knowledge_base_id="kb-123",
        title="Test Document",
        content="This is the content of the test document.",
    )


class TestDocument:
    """Test cases for Document entity."""

    def test_create_document_with_valid_data(self) -> None:
        """Test document creation with valid data."""
        doc = Document(
            knowledge_base_id="kb-123",
            title="My Document",
            content="This is the content.",
            content_type="markdown",
            source="readme.md",
            tags=["docs", "intro"],
        )

        assert doc.knowledge_base_id == "kb-123"
        assert doc.title == "My Document"
        assert doc.content == "This is the content."
        assert doc.content_type == "markdown"
        assert doc.source == "readme.md"
        assert doc.tags == ["docs", "intro"]
        assert isinstance(doc.id, UUID)
        assert doc.is_indexed is False
        assert doc.word_count == 4  # "This is the content."

    def test_create_document_with_minimal_data(self) -> None:
        """Test document creation with minimal data."""
        doc = Document(
            knowledge_base_id="kb-123",
            title="Simple Doc",
            content="Simple content.",
        )

        assert doc.content_type == "text"  # Default
        assert doc.source is None
        assert doc.tags == []
        assert doc.chunks == []
        assert doc.embedding is None

    def test_create_with_empty_knowledge_base_id_raises_error(self) -> None:
        """Test that empty knowledge_base_id raises ValueError."""
        with pytest.raises(ValueError, match="must belong to a knowledge base"):
            Document(
                knowledge_base_id="",
                title="Test",
                content="Content",
            )

    def test_create_with_empty_title_raises_error(self) -> None:
        """Test that empty title raises ValueError."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            Document(
                knowledge_base_id="kb-123",
                title="",
                content="Content",
            )

    def test_create_with_whitespace_title_raises_error(self) -> None:
        """Test that whitespace-only title raises ValueError."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            Document(
                knowledge_base_id="kb-123",
                title="   ",
                content="Content",
            )

    def test_create_with_too_long_title_raises_error(self) -> None:
        """Test that title exceeding 300 characters raises ValueError."""
        with pytest.raises(ValueError, match="cannot exceed 300 characters"):
            Document(
                knowledge_base_id="kb-123",
                title="x" * 301,
                content="Content",
            )

    def test_create_with_empty_content_raises_error(self) -> None:
        """Test that empty content raises ValueError."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            Document(
                knowledge_base_id="kb-123",
                title="Test",
                content="",
            )

    def test_word_count_calculation(self) -> None:
        """Test word count calculation on creation."""
        doc = Document(
            knowledge_base_id="kb-123",
            title="Test",
            content="One two three four five",
        )

        assert doc.word_count == 5

    def test_word_count_with_empty_string_raises_error(self) -> None:
        """Test that empty content raises ValueError (no words)."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            Document(
                knowledge_base_id="kb-123",
                title="Test",
                content="",
            )


class TestDocumentContent:
    """Test cases for content management."""

    def test_update_content(self, valid_document: Document) -> None:
        """Test updating document content."""
        valid_document.update_content("New content here with more words")

        assert valid_document.content == "New content here with more words"
        assert valid_document.word_count == 6
        assert valid_document.is_indexed is False  # Should reset
        assert valid_document.indexed_at is None
        assert valid_document.chunks == []
        assert valid_document.chunk_count == 0

    def test_update_content_resets_indexing(self, valid_document: Document) -> None:
        """Test that updating content resets indexing status."""
        # First mark as indexed
        valid_document.set_indexed(embedding=[0.1, 0.2, 0.3])
        assert valid_document.is_indexed is True
        assert valid_document.embedding is not None

        # Update content
        valid_document.update_content("New content")

        assert valid_document.is_indexed is False
        assert valid_document.embedding is None  # Embedding should be reset

    def test_update_title(self, valid_document: Document) -> None:
        """Test updating document title."""
        valid_document.update_title("New Title")

        assert valid_document.title == "New Title"

    def test_update_title_with_empty_raises_error(
        self, valid_document: Document
    ) -> None:
        """Test that updating to empty title raises ValueError."""
        with pytest.raises(ValueError, match="Title cannot be empty"):
            valid_document.update_title("")

    def test_update_title_with_whitespace_raises_error(
        self, valid_document: Document
    ) -> None:
        """Test that updating to whitespace title raises ValueError."""
        with pytest.raises(ValueError, match="Title cannot be empty"):
            valid_document.update_title("   ")

    def test_update_title_too_long_raises_error(self, valid_document: Document) -> None:
        """Test that updating to long title raises ValueError."""
        with pytest.raises(ValueError, match="Title cannot exceed 300"):
            valid_document.update_title("x" * 301)

    def test_content_hash_property(self, valid_document: Document) -> None:
        """Test content_hash property."""
        hash1 = valid_document.content_hash
        hash2 = valid_document.content_hash

        assert hash1 == hash2  # Should be deterministic
        assert len(hash1) == 16  # First 16 chars of MD5

    def test_content_hash_changes_with_content(self, valid_document: Document) -> None:
        """Test that content_hash changes when content changes."""
        hash1 = valid_document.content_hash
        valid_document.update_content("Different content")
        hash2 = valid_document.content_hash

        assert hash1 != hash2


class TestDocumentTags:
    """Test cases for tag management."""

    def test_add_tag(self, valid_document: Document) -> None:
        """Test adding a tag."""
        valid_document.add_tag("python")

        assert "python" in valid_document.tags
        assert len(valid_document.tags) == 1

    def test_add_tag_normalizes_case(self, valid_document: Document) -> None:
        """Test that tags are normalized to lowercase."""
        valid_document.add_tag("PYTHON")

        assert "python" in valid_document.tags
        assert "PYTHON" not in valid_document.tags

    def test_add_tag_strips_whitespace(self, valid_document: Document) -> None:
        """Test that tags have whitespace stripped."""
        valid_document.add_tag("  python  ")

        assert "python" in valid_document.tags

    def test_add_duplicate_tag_ignored(self, valid_document: Document) -> None:
        """Test that adding duplicate tag is ignored."""
        valid_document.add_tag("python")
        valid_document.add_tag("python")

        assert valid_document.tags.count("python") == 1

    def test_add_empty_tag_ignored(self, valid_document: Document) -> None:
        """Test that empty tag is ignored."""
        valid_document.add_tag("")
        valid_document.add_tag("   ")

        assert len(valid_document.tags) == 0

    def test_remove_tag(self, valid_document: Document) -> None:
        """Test removing a tag."""
        valid_document.add_tag("python")
        valid_document.add_tag("testing")

        valid_document.remove_tag("python")

        assert "python" not in valid_document.tags
        assert "testing" in valid_document.tags

    def test_remove_tag_normalizes_case(self, valid_document: Document) -> None:
        """Test that removing tag normalizes case."""
        valid_document.add_tag("python")

        valid_document.remove_tag("PYTHON")

        assert "python" not in valid_document.tags

    def test_remove_nonexistent_tag_does_nothing(
        self, valid_document: Document
    ) -> None:
        """Test removing non-existent tag does nothing."""
        valid_document.add_tag("python")

        valid_document.remove_tag("nonexistent")

        assert "python" in valid_document.tags


class TestDocumentIndexing:
    """Test cases for indexing management."""

    def test_set_indexed_without_embedding(self, valid_document: Document) -> None:
        """Test marking as indexed without embedding."""
        valid_document.set_indexed()

        assert valid_document.is_indexed is True
        assert valid_document.indexed_at is not None
        assert valid_document.embedding is None

    def test_set_indexed_with_embedding(self, valid_document: Document) -> None:
        """Test marking as indexed with embedding."""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        valid_document.set_indexed(embedding=embedding)

        assert valid_document.is_indexed is True
        assert valid_document.embedding == embedding

    def test_set_indexed_updates_timestamp(self, valid_document: Document) -> None:
        """Test that set_indexed updates timestamp."""
        from datetime import datetime

        valid_document.set_indexed()

        assert valid_document.indexed_at is not None
        assert isinstance(valid_document.indexed_at, datetime)


class TestDocumentChunks:
    """Test cases for chunk management."""

    def test_add_chunks(self, valid_document: Document) -> None:
        """Test adding chunks to document."""
        chunks = [
            {"content": "Chunk 1", "metadata": {"index": 0}},
            {"content": "Chunk 2", "metadata": {"index": 1}},
            {"content": "Chunk 3", "metadata": {"index": 2}},
        ]

        valid_document.add_chunks(chunks)

        assert len(valid_document.chunks) == 3
        assert valid_document.chunk_count == 3

    def test_add_chunks_overwrites_existing(self, valid_document: Document) -> None:
        """Test that add_chunks overwrites existing chunks."""
        valid_document.add_chunks([{"content": "Old", "metadata": {}}])

        new_chunks = [{"content": "New", "metadata": {}}]
        valid_document.add_chunks(new_chunks)

        assert len(valid_document.chunks) == 1
        assert valid_document.chunks[0]["content"] == "New"

    def test_get_chunk_content(self, valid_document: Document) -> None:
        """Test getting content of a specific chunk."""
        chunks = [
            {"content": "First chunk", "metadata": {}},
            {"content": "Second chunk", "metadata": {}},
        ]
        valid_document.add_chunks(chunks)

        assert valid_document.get_chunk_content(0) == "First chunk"
        assert valid_document.get_chunk_content(1) == "Second chunk"

    def test_get_chunk_content_out_of_range(self, valid_document: Document) -> None:
        """Test getting chunk content with invalid index."""
        valid_document.add_chunks([{"content": "Only chunk", "metadata": {}}])

        assert valid_document.get_chunk_content(-1) is None
        assert valid_document.get_chunk_content(1) is None
        assert valid_document.get_chunk_content(100) is None


class TestDocumentMetadata:
    """Test cases for metadata operations."""

    def test_update_metadata(self, valid_document: Document) -> None:
        """Test updating metadata."""
        valid_document.update_metadata("author", "John Doe")
        valid_document.update_metadata("version", 2)

        assert valid_document.metadata["author"] == "John Doe"
        assert valid_document.metadata["version"] == 2

    def test_update_metadata_overwrites_existing(
        self, valid_document: Document
    ) -> None:
        """Test that update overwrites existing metadata."""
        valid_document.update_metadata("key", "old_value")
        valid_document.update_metadata("key", "new_value")

        assert valid_document.metadata["key"] == "new_value"


class TestDocumentSerialization:
    """Test cases for serialization."""

    def test_to_dict(self, valid_document: Document) -> None:
        """Test converting to dictionary."""
        valid_document.add_tag("test")
        valid_document.set_indexed()

        doc_dict = valid_document.to_dict()

        assert doc_dict["knowledge_base_id"] == "kb-123"
        assert doc_dict["title"] == "Test Document"
        assert doc_dict["content"] == "This is the content of the test document."
        assert doc_dict["content_type"] == "text"
        assert doc_dict["tags"] == ["test"]
        # "This is the content of the test document." = 8 words
        assert doc_dict["word_count"] == 8
        assert doc_dict["chunk_count"] == 0
        assert doc_dict["is_indexed"] is True
        assert doc_dict["indexed_at"] is not None
        assert "id" in doc_dict
        assert "created_at" in doc_dict
        assert "updated_at" in doc_dict

    def test_to_search_result(self, valid_document: Document) -> None:
        """Test converting to search result format."""
        valid_document.add_tag("test")
        result = valid_document.to_search_result()

        assert result["id"] == str(valid_document.id)
        assert result["title"] == "Test Document"
        assert "content_preview" in result
        assert result["content_type"] == "text"
        assert result["tags"] == ["test"]
        # "This is the content of the test document." = 8 words
        assert result["word_count"] == 8
        assert "metadata" in result
        assert "content" not in result  # Should not include full content

    def test_to_search_result_short_content(self, valid_document: Document) -> None:
        """Test search result with short content (no truncation)."""
        valid_document.update_content("Short")

        result = valid_document.to_search_result()

        assert result["content_preview"] == "Short"

    def test_to_search_result_long_content(self, valid_document: Document) -> None:
        """Test search result with long content (truncated)."""
        valid_document.update_content("x" * 300)

        result = valid_document.to_search_result()

        assert len(result["content_preview"]) == 203  # 200 + "..."
        assert result["content_preview"].endswith("...")


class TestDocumentInvariants:
    """Test cases for invariant validation."""

    def test_document_belongs_to_knowledge_base(self) -> None:
        """Test that document always belongs to a knowledge base."""
        doc = Document(
            knowledge_base_id="kb-123",
            title="Test",
            content="Content",
        )

        assert doc.knowledge_base_id == "kb-123"

    def test_chunk_count_matches_chunks_list(self, valid_document: Document) -> None:
        """Test that chunk_count always matches chunks list length."""
        assert valid_document.chunk_count == len(valid_document.chunks)

        valid_document.add_chunks([{"content": "Chunk 1", "metadata": {}}])
        assert valid_document.chunk_count == len(valid_document.chunks)

        valid_document.add_chunks(
            [
                {"content": "Chunk 1", "metadata": {}},
                {"content": "Chunk 2", "metadata": {}},
            ]
        )
        assert valid_document.chunk_count == len(valid_document.chunks)

    def test_word_count_positive(self, valid_document: Document) -> None:
        """Test that word_count is always positive."""
        assert valid_document.word_count >= 0

    def test_id_is_uuid(self, valid_document: Document) -> None:
        """Test that document ID is a valid UUID."""
        assert isinstance(valid_document.id, UUID)
