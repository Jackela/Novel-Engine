"""Tests for the KnowledgeBase aggregate root.

This module contains comprehensive tests for the KnowledgeBase domain aggregate,
covering document management, indexing, and metadata operations.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from src.contexts.knowledge.domain.aggregates.knowledge_base import (
    KnowledgeBase,
)


@pytest.fixture
def valid_knowledge_base() -> KnowledgeBase:
    """Create a valid knowledge base for testing."""
    return KnowledgeBase(
        name="Test Knowledge Base",
        owner_id="user-123",
        description="A test knowledge base",
    )


class TestKnowledgeBase:
    """Test cases for KnowledgeBase aggregate root."""

    def test_create_knowledge_base_with_valid_data(self) -> None:
        """Test knowledge base creation with valid data."""
        kb = KnowledgeBase(
            name="My KB",
            owner_id="user-123",
            description="Test description",
            project_id="project-456",
            embedding_model="text-embedding-3-large",
            is_public=True,
        )

        assert kb.name == "My KB"
        assert kb.owner_id == "user-123"
        assert kb.description == "Test description"
        assert kb.project_id == "project-456"
        assert kb.embedding_model == "text-embedding-3-large"
        assert kb.is_public is True
        assert kb.document_count == 0
        assert kb.indexed_count == 0
        assert isinstance(kb.id, UUID)
        assert kb.version == 0

    def test_create_knowledge_base_with_minimal_data(self) -> None:
        """Test knowledge base creation with minimal required data."""
        kb = KnowledgeBase(name="My KB", owner_id="user-123")

        assert kb.name == "My KB"
        assert kb.owner_id == "user-123"
        assert kb.description is None
        assert kb.project_id is None
        assert kb.is_public is False
        assert kb.embedding_model == "text-embedding-3-small"  # Default

    def test_create_with_empty_name_raises_error(self) -> None:
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            KnowledgeBase(name="", owner_id="user-123")

    def test_create_with_whitespace_name_raises_error(self) -> None:
        """Test that whitespace-only name raises ValueError."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            KnowledgeBase(name="   ", owner_id="user-123")

    def test_create_with_too_long_name_raises_error(self) -> None:
        """Test that name exceeding 200 characters raises ValueError."""
        with pytest.raises(ValueError, match="cannot exceed 200 characters"):
            KnowledgeBase(name="x" * 201, owner_id="user-123")

    def test_create_with_empty_owner_id_raises_error(self) -> None:
        """Test that empty owner_id raises ValueError."""
        with pytest.raises(ValueError, match="must have an owner"):
            KnowledgeBase(name="My KB", owner_id="")


class TestKnowledgeBaseDocuments:
    """Test cases for document management."""

    def test_add_document(self, valid_knowledge_base: KnowledgeBase) -> None:
        """Test adding a document."""
        document = valid_knowledge_base.add_document(
            title="Test Document",
            content="This is test content",
            content_type="text",
            source="test.txt",
            tags=["test", "sample"],
        )

        assert document.title == "Test Document"
        assert document.content == "This is test content"
        assert document.content_type == "text"
        assert document.source == "test.txt"
        assert document.tags == ["test", "sample"]
        assert valid_knowledge_base.document_count == 1

    def test_add_document_with_minimal_data(
        self, valid_knowledge_base: KnowledgeBase
    ) -> None:
        """Test adding document with minimal data."""
        document = valid_knowledge_base.add_document(
            title="Simple Doc",
            content="Simple content",
        )

        assert document.content_type == "text"  # Default
        assert document.source is None
        assert document.tags == []

    def test_add_multiple_documents(self, valid_knowledge_base: KnowledgeBase) -> None:
        """Test adding multiple documents."""
        doc1 = valid_knowledge_base.add_document("Doc 1", "Content 1")
        doc2 = valid_knowledge_base.add_document("Doc 2", "Content 2")

        assert valid_knowledge_base.document_count == 2
        assert str(doc1.id) != str(doc2.id)

    def test_add_document_beyond_maximum_raises_error(
        self, valid_knowledge_base: KnowledgeBase
    ) -> None:
        """Test that adding more than 1000 documents raises ValueError."""
        # Add 1000 documents
        for i in range(1000):
            valid_knowledge_base.add_document(f"Doc {i}", f"Content {i}")

        assert valid_knowledge_base.document_count == 1000

        # 1001st document should fail
        with pytest.raises(ValueError, match="cannot exceed 1000 documents"):
            valid_knowledge_base.add_document("Extra Doc", "Extra Content")

    def test_get_document(self, valid_knowledge_base: KnowledgeBase) -> None:
        """Test getting a document by ID."""
        document = valid_knowledge_base.add_document("Test Doc", "Content")
        doc_id = str(document.id)

        retrieved = valid_knowledge_base.get_document(doc_id)

        assert retrieved is not None
        assert retrieved.id == document.id
        assert retrieved.title == "Test Doc"

    def test_get_nonexistent_document_returns_none(
        self, valid_knowledge_base: KnowledgeBase
    ) -> None:
        """Test getting non-existent document returns None."""
        result = valid_knowledge_base.get_document("nonexistent-id")
        assert result is None

    def test_remove_document(self, valid_knowledge_base: KnowledgeBase) -> None:
        """Test removing a document."""
        document = valid_knowledge_base.add_document("To Remove", "Content")
        doc_id = str(document.id)

        result = valid_knowledge_base.remove_document(doc_id)

        assert result is True
        assert valid_knowledge_base.document_count == 0

    def test_remove_nonexistent_document_returns_false(
        self, valid_knowledge_base: KnowledgeBase
    ) -> None:
        """Test removing non-existent document returns False."""
        result = valid_knowledge_base.remove_document("nonexistent-id")
        assert result is False

    def test_remove_document_from_multiple(
        self, valid_knowledge_base: KnowledgeBase
    ) -> None:
        """Test removing one document from multiple."""
        doc1 = valid_knowledge_base.add_document("Doc 1", "Content 1")
        doc2 = valid_knowledge_base.add_document("Doc 2", "Content 2")
        doc3 = valid_knowledge_base.add_document("Doc 3", "Content 3")

        valid_knowledge_base.remove_document(str(doc2.id))

        assert valid_knowledge_base.document_count == 2
        assert valid_knowledge_base.get_document(str(doc1.id)) is not None
        assert valid_knowledge_base.get_document(str(doc3.id)) is not None


class TestKnowledgeBaseSearch:
    """Test cases for search functionality."""

    def test_search_by_tags_single_tag(
        self, valid_knowledge_base: KnowledgeBase
    ) -> None:
        """Test searching by single tag."""
        doc1 = valid_knowledge_base.add_document(
            "Doc 1", "Content", tags=["python", "testing"]
        )
        doc2 = valid_knowledge_base.add_document(
            "Doc 2", "Content", tags=["java", "testing"]
        )
        doc3 = valid_knowledge_base.add_document("Doc 3", "Content", tags=["python"])

        results = valid_knowledge_base.search_by_tags(["python"])

        assert len(results) == 2
        assert doc1 in results
        assert doc3 in results
        assert doc2 not in results

    def test_search_by_tags_multiple_tags(
        self, valid_knowledge_base: KnowledgeBase
    ) -> None:
        """Test searching by multiple tags (OR logic)."""
        doc1 = valid_knowledge_base.add_document("Doc 1", "Content", tags=["python"])
        doc2 = valid_knowledge_base.add_document("Doc 2", "Content", tags=["java"])
        valid_knowledge_base.add_document("Doc 3", "Content", tags=["javascript"])

        results = valid_knowledge_base.search_by_tags(["python", "java"])

        assert len(results) == 2
        assert doc1 in results
        assert doc2 in results

    def test_search_by_tags_no_match(self, valid_knowledge_base: KnowledgeBase) -> None:
        """Test searching with tags that don't match any document."""
        valid_knowledge_base.add_document("Doc", "Content", tags=["python"])

        results = valid_knowledge_base.search_by_tags(["nonexistent"])

        assert len(results) == 0

    def test_search_by_tags_empty_list(
        self, valid_knowledge_base: KnowledgeBase
    ) -> None:
        """Test searching with empty tag list."""
        valid_knowledge_base.add_document("Doc", "Content", tags=["python"])

        results = valid_knowledge_base.search_by_tags([])

        assert len(results) == 0


class TestKnowledgeBaseIndexing:
    """Test cases for indexing counts."""

    def test_indexed_count_property(self, valid_knowledge_base: KnowledgeBase) -> None:
        """Test indexed_count property."""
        # Initially no indexed documents
        assert valid_knowledge_base.indexed_count == 0

        # Add documents (not indexed by default)
        doc1 = valid_knowledge_base.add_document("Doc 1", "Content")
        doc2 = valid_knowledge_base.add_document("Doc 2", "Content")

        assert valid_knowledge_base.indexed_count == 0

        # Mark one as indexed
        doc1.set_indexed()
        assert valid_knowledge_base.indexed_count == 1

        # Mark another as indexed
        doc2.set_indexed()
        assert valid_knowledge_base.indexed_count == 2


class TestKnowledgeBaseMetadata:
    """Test cases for metadata operations."""

    def test_update_metadata(self, valid_knowledge_base: KnowledgeBase) -> None:
        """Test updating metadata."""
        valid_knowledge_base.update_metadata("key1", "value1")
        valid_knowledge_base.update_metadata("key2", 123)

        assert valid_knowledge_base.metadata["key1"] == "value1"
        assert valid_knowledge_base.metadata["key2"] == 123

    def test_update_metadata_overwrites_existing(
        self, valid_knowledge_base: KnowledgeBase
    ) -> None:
        """Test that update overwrites existing metadata."""
        valid_knowledge_base.update_metadata("key", "old_value")
        valid_knowledge_base.update_metadata("key", "new_value")

        assert valid_knowledge_base.metadata["key"] == "new_value"


class TestKnowledgeBaseSerialization:
    """Test cases for serialization."""

    def test_to_dict(self, valid_knowledge_base: KnowledgeBase) -> None:
        """Test converting to dictionary."""
        valid_knowledge_base.add_document("Test Doc", "Test Content")
        valid_knowledge_base.update_metadata("key", "value")

        kb_dict = valid_knowledge_base.to_dict()

        assert kb_dict["name"] == "Test Knowledge Base"
        assert kb_dict["owner_id"] == "user-123"
        assert kb_dict["description"] == "A test knowledge base"
        assert kb_dict["document_count"] == 1
        assert kb_dict["indexed_count"] == 0
        assert kb_dict["embedding_model"] == "text-embedding-3-small"
        assert kb_dict["is_public"] is False
        assert kb_dict["metadata"] == {"key": "value"}
        assert "id" in kb_dict
        assert "created_at" in kb_dict
        assert "updated_at" in kb_dict


class TestKnowledgeBaseInvariants:
    """Test cases for invariant validation."""

    def test_document_count_matches_documents_list(
        self, valid_knowledge_base: KnowledgeBase
    ) -> None:
        """Test that document_count property matches actual count."""
        assert valid_knowledge_base.document_count == len(
            valid_knowledge_base.documents
        )

        valid_knowledge_base.add_document("Doc 1", "Content")
        assert valid_knowledge_base.document_count == len(
            valid_knowledge_base.documents
        )

        valid_knowledge_base.add_document("Doc 2", "Content")
        assert valid_knowledge_base.document_count == len(
            valid_knowledge_base.documents
        )

    def test_indexed_count_never_exceeds_document_count(
        self, valid_knowledge_base: KnowledgeBase
    ) -> None:
        """Test that indexed_count never exceeds document_count."""
        doc = valid_knowledge_base.add_document("Doc", "Content")
        doc.set_indexed()

        assert valid_knowledge_base.indexed_count <= valid_knowledge_base.document_count
