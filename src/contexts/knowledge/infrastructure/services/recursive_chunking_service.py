"""Recursive text chunking service.

This module provides a recursive text chunking service that splits
documents into overlapping chunks for better retrieval performance.
"""

from __future__ import annotations

from typing import Any


class RecursiveChunkingService:
    """Recursive text chunking service.

    Splits documents into overlapping chunks using recursive character
    text splitting strategy. Attempts to break at sentence or word boundaries.

    Example:
        >>> service = RecursiveChunkingService(chunk_size=500, chunk_overlap=50)
        >>> chunks = service.chunk_document(
        ...     content="Long document text here...",
        ...     chunk_size=500,
        ...     overlap=50
        ... )
        >>> print(len(chunks))  # Number of chunks
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        """Initialize recursive chunking service.

        Args:
            chunk_size: Maximum size of each chunk (default: 500)
            chunk_overlap: Number of characters to overlap between chunks (default: 50)

        Raises:
            ValueError: If chunk_size or chunk_overlap is invalid
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def chunk_document(
        self,
        content: str,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> list[dict[str, Any]]:
        """Split document into chunks.

        Args:
            content: Document content to split
            chunk_size: Maximum size of each chunk (default: 1000)
            overlap: Number of characters to overlap between chunks (default: 200)

        Returns:
            List of chunk dictionaries with 'content' and 'metadata' keys

        Raises:
            ValueError: If content is empty or parameters are invalid
        """
        if not content:
            raise ValueError("Content cannot be empty")

        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")

        chunks: list[dict[str, Any]] = []
        start = 0
        chunk_index = 0

        while start < len(content):
            end = min(start + chunk_size, len(content))
            chunk_text = content[start:end]

            # Try to break at sentence or word boundary if not at end
            if end < len(content):
                # Look for sentence boundary (period followed by space or newline)
                last_period = chunk_text.rfind(". ")
                if last_period > chunk_size * 0.5:
                    # Break at sentence if it's past halfway point
                    end = start + last_period + 1
                    chunk_text = content[start:end]
                else:
                    # Try to break at word boundary
                    last_space = chunk_text.rfind(" ")
                    if last_space > chunk_size * 0.3:
                        end = start + last_space
                        chunk_text = content[start:end]

            chunks.append(
                {
                    "content": chunk_text,
                    "metadata": {
                        "chunk_index": chunk_index,
                        "start_index": start,
                        "end_index": end,
                        "chunk_size": len(chunk_text),
                    },
                }
            )

            # Move to next chunk with overlap
            start = end - overlap
            chunk_index += 1

            # Prevent infinite loop
            if start >= len(content) or end == len(content):
                break

        return chunks

    @property
    def chunk_size(self) -> int:
        """Get default chunk size."""
        return self._chunk_size

    @property
    def chunk_overlap(self) -> int:
        """Get default chunk overlap."""
        return self._chunk_overlap
