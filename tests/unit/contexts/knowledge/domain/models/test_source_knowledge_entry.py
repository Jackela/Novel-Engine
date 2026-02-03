"""
Unit Tests for SourceKnowledgeEntry Entity

Tests the RAG-focused knowledge entry entity.

Warzone 4: AI Brain - BRAIN-003
Tests entity creation, validation, and behavior.

Constitution Compliance:
- Article III (TDD): Tests written to validate entity behavior
- Article I (DDD): Tests entity invariants and behaviors
"""

import datetime

import pytest

from src.contexts.knowledge.domain.models.source_knowledge_entry import (
    SourceKnowledgeEntry,
    SourceMetadata,
)
from src.contexts.knowledge.domain.models.source_type import SourceType


class TestSourceMetadata:
    """Unit tests for SourceMetadata value object."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_metadata_with_required_fields(self):
        """Test creating metadata with required fields."""
        metadata = SourceMetadata(word_count=100)

        assert metadata.word_count == 100
        assert metadata.chunk_index == 0
        assert metadata.total_chunks == 1
        assert metadata.tags == []
        assert metadata.extra == {}

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_metadata_with_all_fields(self):
        """Test creating metadata with all fields."""
        metadata = SourceMetadata(
            word_count=100,
            chunk_index=2,
            total_chunks=5,
            tags=["hero", "warrior"],
            extra={"chapter": 1},
        )

        assert metadata.word_count == 100
        assert metadata.chunk_index == 2
        assert metadata.total_chunks == 5
        assert metadata.tags == ["hero", "warrior"]
        assert metadata.extra == {"chapter": 1}

    @pytest.mark.unit
    @pytest.mark.fast
    def test_metadata_is_immutable(self):
        """Test that SourceMetadata is frozen (immutable)."""
        metadata = SourceMetadata(word_count=100)

        # Attempting to modify should raise
        with pytest.raises(Exception):  # FrozenInstanceError
            metadata.word_count = 200


class TestSourceKnowledgeEntry:
    """Unit tests for SourceKnowledgeEntry entity."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_entry_with_required_fields(self):
        """Test creating entry with required fields."""
        metadata = SourceMetadata(word_count=100)
        entry = SourceKnowledgeEntry(
            id="test-id",
            content="Test content",
            source_type=SourceType.CHARACTER,
            source_id="char-1",
            metadata=metadata,
        )

        assert entry.id == "test-id"
        assert entry.content == "Test content"
        assert entry.source_type == SourceType.CHARACTER
        assert entry.source_id == "char-1"
        assert entry.metadata.word_count == 100
        assert entry.embedding_id is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_entry_with_factory_method(self):
        """Test creating entry using factory method."""
        entry = SourceKnowledgeEntry.create(
            content="Test content",
            source_type=SourceType.CHARACTER,
            source_id="char-1",
            word_count=2,
        )

        assert entry.content == "Test content"
        assert entry.source_type == SourceType.CHARACTER
        assert entry.source_id == "char-1"
        assert entry.metadata.word_count == 2
        assert entry.embedding_id is None
        assert entry.id is not None  # Auto-generated UUID

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_entry_with_string_source_type(self):
        """Test creating entry with string source type."""
        entry = SourceKnowledgeEntry.create(
            content="Test content",
            source_type="LORE",
            source_id="lore-1",
            word_count=2,
        )

        assert entry.source_type == SourceType.LORE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_entry_with_explicit_id(self):
        """Test creating entry with explicit ID."""
        entry = SourceKnowledgeEntry.create(
            content="Test content",
            source_type=SourceType.SCENE,
            source_id="scene-1",
            word_count=2,
            id="custom-id",
        )

        assert entry.id == "custom-id"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_entry_with_tags(self):
        """Test creating entry with tags."""
        entry = SourceKnowledgeEntry.create(
            content="Test content",
            source_type=SourceType.CHARACTER,
            source_id="char-1",
            word_count=2,
            tags=["hero", "protagonist"],
        )

        assert entry.metadata.tags == ["hero", "protagonist"]

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_entry_with_extra_metadata(self):
        """Test creating entry with extra metadata."""
        entry = SourceKnowledgeEntry.create(
            content="Test content",
            source_type=SourceType.CHARACTER,
            source_id="char-1",
            word_count=2,
            extra_metadata={"chapter": 1, "scene": 5},
        )

        assert entry.metadata.extra == {"chapter": 1, "scene": 5}

    @pytest.mark.unit
    @pytest.mark.fast
    def test_content_is_stripped_on_creation(self):
        """Test that content is stripped on creation."""
        entry = SourceKnowledgeEntry.create(
            content="  Test content  ",
            source_type=SourceType.CHARACTER,
            source_id="char-1",
            word_count=2,
        )

        assert entry.content == "Test content"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_timestamps_are_utc(self):
        """Test that timestamps are in UTC."""
        entry = SourceKnowledgeEntry.create(
            content="Test content",
            source_type=SourceType.CHARACTER,
            source_id="char-1",
            word_count=2,
        )

        assert entry.created_at.tzinfo is not None
        assert entry.updated_at.tzinfo is not None


class TestSourceKnowledgeEntryValidation:
    """Unit tests for SourceKnowledgeEntry validation."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_empty_id_raises_error(self):
        """Test that empty ID raises ValueError."""
        metadata = SourceMetadata(word_count=100)

        with pytest.raises(ValueError) as exc_info:
            SourceKnowledgeEntry(
                id="",
                content="Test content",
                source_type=SourceType.CHARACTER,
                source_id="char-1",
                metadata=metadata,
            )

        assert "id is required" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_empty_content_raises_error(self):
        """Test that empty content raises ValueError."""
        metadata = SourceMetadata(word_count=100)

        with pytest.raises(ValueError) as exc_info:
            SourceKnowledgeEntry(
                id="test-id",
                content="",
                source_type=SourceType.CHARACTER,
                source_id="char-1",
                metadata=metadata,
            )

        assert "content cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_whitespace_only_content_raises_error(self):
        """Test that whitespace-only content raises ValueError."""
        metadata = SourceMetadata(word_count=100)

        with pytest.raises(ValueError) as exc_info:
            SourceKnowledgeEntry(
                id="test-id",
                content="   ",
                source_type=SourceType.CHARACTER,
                source_id="char-1",
                metadata=metadata,
            )

        assert "content cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_invalid_source_type_raises_error(self):
        """Test that invalid source type raises ValueError."""
        metadata = SourceMetadata(word_count=100)

        with pytest.raises(ValueError) as exc_info:
            SourceKnowledgeEntry(
                id="test-id",
                content="Test content",
                source_type="INVALID",  # type: ignore
                source_id="char-1",
                metadata=metadata,
            )

        assert "source_type must be a SourceType" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_empty_source_id_raises_error(self):
        """Test that empty source_id raises ValueError."""
        metadata = SourceMetadata(word_count=100)

        with pytest.raises(ValueError) as exc_info:
            SourceKnowledgeEntry(
                id="test-id",
                content="Test content",
                source_type=SourceType.CHARACTER,
                source_id="",
                metadata=metadata,
            )

        assert "source_id is required" in str(exc_info.value)


class TestSourceKnowledgeEntryBehavior:
    """Unit tests for SourceKnowledgeEntry behavior methods."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_embedding_id(self):
        """Test setting the embedding ID."""
        entry = SourceKnowledgeEntry.create(
            content="Test content",
            source_type=SourceType.CHARACTER,
            source_id="char-1",
            word_count=2,
        )

        assert entry.embedding_id is None

        entry.set_embedding_id("embed-123")

        assert entry.embedding_id == "embed-123"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_set_empty_embedding_id_raises_error(self):
        """Test that setting empty embedding ID raises ValueError."""
        entry = SourceKnowledgeEntry.create(
            content="Test content",
            source_type=SourceType.CHARACTER,
            source_id="char-1",
            word_count=2,
        )

        with pytest.raises(ValueError) as exc_info:
            entry.set_embedding_id("")

        assert "embedding_id cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_content_invalidates_embedding(self):
        """Test that updating content clears embedding ID."""
        entry = SourceKnowledgeEntry.create(
            content="Test content",
            source_type=SourceType.CHARACTER,
            source_id="char-1",
            word_count=2,
        )
        entry.set_embedding_id("embed-123")

        entry.update_content("New content")

        assert entry.content == "New content"
        assert entry.embedding_id is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_update_empty_content_raises_error(self):
        """Test that updating with empty content raises ValueError."""
        entry = SourceKnowledgeEntry.create(
            content="Test content",
            source_type=SourceType.CHARACTER,
            source_id="char-1",
            word_count=2,
        )

        with pytest.raises(ValueError) as exc_info:
            entry.update_content("")

        assert "content cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_embedding_returns_true_when_set(self):
        """Test has_embedding returns True when embedding_id is set."""
        entry = SourceKnowledgeEntry.create(
            content="Test content",
            source_type=SourceType.CHARACTER,
            source_id="char-1",
            word_count=2,
        )

        assert entry.has_embedding() is False

        entry.set_embedding_id("embed-123")

        assert entry.has_embedding() is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_vector_document_id_with_embedding(self):
        """Test get_vector_document_id returns embedding_id when set."""
        entry = SourceKnowledgeEntry.create(
            content="Test content",
            source_type=SourceType.CHARACTER,
            source_id="char-1",
            word_count=2,
        )
        entry.set_embedding_id("embed-123")

        assert entry.get_vector_document_id() == "embed-123"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_vector_document_id_without_embedding(self):
        """Test get_vector_document_id returns entry id when no embedding."""
        entry = SourceKnowledgeEntry.create(
            content="Test content",
            source_type=SourceType.CHARACTER,
            source_id="char-1",
            word_count=2,
        )

        assert entry.get_vector_document_id() == entry.id

    @pytest.mark.unit
    @pytest.mark.fast
    def test_to_vector_metadata(self):
        """Test to_vector_metadata returns correct dict."""
        entry = SourceKnowledgeEntry.create(
            content="Test content",
            source_type=SourceType.CHARACTER,
            source_id="char-1",
            word_count=100,
            chunk_index=2,
            total_chunks=5,
            tags=["hero"],
            extra_metadata={"chapter": 1},
        )

        metadata = entry.to_vector_metadata()

        assert metadata["source_type"] == "CHARACTER"
        assert metadata["source_id"] == "char-1"
        assert metadata["chunk_index"] == 2
        assert metadata["total_chunks"] == 5
        assert metadata["word_count"] == 100
        assert metadata["tags"] == ["hero"]
        assert metadata["chapter"] == 1
        assert "created_at" in metadata
