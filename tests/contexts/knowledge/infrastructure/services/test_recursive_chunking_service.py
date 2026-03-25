"""Tests for RecursiveChunkingService.

This module provides comprehensive tests for the recursive chunking
service implementation.
"""

from __future__ import annotations

import pytest

from src.contexts.knowledge.infrastructure.services.recursive_chunking_service import (
    RecursiveChunkingService,
)


class TestRecursiveChunkingService:
    """Test suite for RecursiveChunkingService."""

    def test_init_with_default_values(self) -> None:
        """Test initialization with default values."""
        service = RecursiveChunkingService()
        assert service.chunk_size == 500
        assert service.chunk_overlap == 50

    def test_init_with_custom_values(self) -> None:
        """Test initialization with custom values."""
        service = RecursiveChunkingService(chunk_size=1000, chunk_overlap=100)
        assert service.chunk_size == 1000
        assert service.chunk_overlap == 100

    def test_init_invalid_chunk_size(self) -> None:
        """Test initialization with invalid chunk size."""
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            RecursiveChunkingService(chunk_size=0)

        with pytest.raises(ValueError, match="chunk_size must be positive"):
            RecursiveChunkingService(chunk_size=-1)

    def test_init_invalid_chunk_overlap(self) -> None:
        """Test initialization with invalid chunk overlap."""
        with pytest.raises(ValueError, match="chunk_overlap must be non-negative"):
            RecursiveChunkingService(chunk_overlap=-1)

    def test_init_overlap_greater_than_size(self) -> None:
        """Test initialization with overlap greater than size."""
        with pytest.raises(
            ValueError, match="chunk_overlap must be less than chunk_size"
        ):
            RecursiveChunkingService(chunk_size=100, chunk_overlap=100)

        with pytest.raises(
            ValueError, match="chunk_overlap must be less than chunk_size"
        ):
            RecursiveChunkingService(chunk_size=100, chunk_overlap=150)

    def test_chunk_document_empty_content(self) -> None:
        """Test chunking empty content raises error."""
        service = RecursiveChunkingService()
        with pytest.raises(ValueError, match="Content cannot be empty"):
            service.chunk_document("")

    def test_chunk_document_single_chunk(self) -> None:
        """Test chunking short content creates single chunk."""
        service = RecursiveChunkingService()
        content = "Short content"
        chunks = service.chunk_document(content, chunk_size=100, overlap=10)

        assert len(chunks) == 1
        assert chunks[0]["content"] == content
        assert chunks[0]["metadata"]["chunk_index"] == 0
        assert chunks[0]["metadata"]["start_index"] == 0
        assert chunks[0]["metadata"]["end_index"] == len(content)

    def test_chunk_document_multiple_chunks(self) -> None:
        """Test chunking long content creates multiple chunks."""
        service = RecursiveChunkingService()
        # Create content that will definitely create multiple chunks
        content = "This is a test sentence. " * 20  # About 500 characters
        chunks = service.chunk_document(content, chunk_size=100, overlap=10)

        assert len(chunks) > 1
        # Verify overlap
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]["content"]
            curr_chunk = chunks[i]["content"]
            # Check that there's some overlap between consecutive chunks
            assert any(word in curr_chunk for word in prev_chunk.split()[:3])

    def test_chunk_document_respects_chunk_size(self) -> None:
        """Test that chunks respect maximum chunk size."""
        service = RecursiveChunkingService()
        content = "Word " * 100  # 500 characters
        chunks = service.chunk_document(content, chunk_size=50, overlap=5)

        for chunk in chunks:
            assert len(chunk["content"]) <= 50

    def test_chunk_document_sentence_boundary(self) -> None:
        """Test that chunking respects sentence boundaries when possible."""
        service = RecursiveChunkingService()
        # Create content with clear sentence boundaries
        sentences = [f"This is sentence number {i}. " for i in range(10)]
        content = "".join(sentences)
        chunks = service.chunk_document(content, chunk_size=100, overlap=10)

        # At least some chunks should end with a period
        chunks_ending_with_period = sum(
            1 for chunk in chunks if chunk["content"].rstrip().endswith(".")
        )
        assert chunks_ending_with_period > 0

    def test_chunk_document_metadata(self) -> None:
        """Test that chunk metadata is correct."""
        service = RecursiveChunkingService(chunk_size=50, chunk_overlap=10)
        content = "Word " * 20
        chunks = service.chunk_document(content)

        for i, chunk in enumerate(chunks):
            assert "content" in chunk
            assert "metadata" in chunk
            metadata = chunk["metadata"]
            assert metadata["chunk_index"] == i
            assert "start_index" in metadata
            assert "end_index" in metadata
            assert "chunk_size" in metadata
            assert metadata["chunk_size"] == len(chunk["content"])

    def test_chunk_document_invalid_params(self) -> None:
        """Test chunking with invalid parameters."""
        service = RecursiveChunkingService()
        content = "Some content here"

        with pytest.raises(ValueError, match="chunk_size must be positive"):
            service.chunk_document(content, chunk_size=0)

        with pytest.raises(ValueError, match="overlap must be non-negative"):
            service.chunk_document(content, overlap=-1)

        with pytest.raises(ValueError, match="overlap must be less than chunk_size"):
            service.chunk_document(content, chunk_size=50, overlap=50)

    def test_chunk_document_prevents_infinite_loop(self) -> None:
        """Test that chunking doesn't create infinite loop."""
        service = RecursiveChunkingService()
        # Very short content with large overlap
        content = "a" * 100
        chunks = service.chunk_document(content, chunk_size=30, overlap=25)

        # Should finish and not hang
        assert len(chunks) > 0
        assert len(chunks) < 20  # Reasonable number of chunks

    def test_chunk_document_whitespace_handling(self) -> None:
        """Test handling of whitespace in content."""
        service = RecursiveChunkingService()
        content = "   Leading and trailing spaces   "
        chunks = service.chunk_document(content, chunk_size=100, overlap=10)

        assert len(chunks) == 1
        # Content should be preserved as-is
        assert chunks[0]["content"] == content

    def test_chunk_document_unicode_content(self) -> None:
        """Test handling of unicode content."""
        service = RecursiveChunkingService()
        content = "Hello 世界！これはテストです。 " * 10
        chunks = service.chunk_document(content, chunk_size=50, overlap=5)

        assert len(chunks) > 0
        # Verify all chunks contain valid content
        for chunk in chunks:
            assert len(chunk["content"]) > 0

    def test_chunk_document_newline_handling(self) -> None:
        """Test handling of newlines in content."""
        service = RecursiveChunkingService()
        content = "Line 1\nLine 2\nLine 3\n" * 10
        chunks = service.chunk_document(content, chunk_size=50, overlap=5)

        assert len(chunks) > 0
        # Newlines should be preserved
        for chunk in chunks:
            assert "\n" in chunk["content"] or len(chunk["content"]) < 50
