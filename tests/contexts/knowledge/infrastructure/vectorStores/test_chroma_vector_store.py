"""Tests for ChromaVectorStore.

This module provides tests for the ChromaDB vector store implementation.
Note: Tests requiring actual ChromaDB connection are marked with
'requires_chroma' marker and skipped by default.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from src.contexts.knowledge.infrastructure.vectorStores.chroma_vector_store import (
    ChromaVectorStore,
)

if TYPE_CHECKING:
    from collections.abc import Generator


class TestChromaVectorStore:
    """Test suite for ChromaVectorStore."""

    def test_init_with_default_port(self) -> None:
        """Test initialization with default port."""
        store = ChromaVectorStore(host="localhost")
        assert store._host == "localhost"
        assert store._port == 8000
        assert store._client is None

    def test_init_with_custom_port(self) -> None:
        """Test initialization with custom port."""
        store = ChromaVectorStore(host="chroma.example.com", port=9000)
        assert store._host == "chroma.example.com"
        assert store._port == 9000


class TestChromaVectorStoreWithMock:
    """Test suite for ChromaVectorStore with mocked chromadb."""

    @pytest.fixture(autouse=True)
    def setup_mock(self) -> "Generator[None, None, None]":
        """Setup mock chromadb module for all tests in this class."""
        mock_chromadb = MagicMock()
        mock_client = MagicMock()
        mock_chromadb.HttpClient.return_value = mock_client
        mock_client.list_collections.return_value = []

        with patch.dict(sys.modules, {"chromadb": mock_chromadb}):
            with patch(
                "src.contexts.knowledge.infrastructure.vectorStores.chroma_vector_store.chromadb",
                mock_chromadb,
                create=True,
            ):
                yield

    def test_get_client_creates_client(self, setup_mock: None) -> None:
        """Test that _get_client creates a new client."""
        # Need to reimport to get the patched module
        import sys

        mock_chromadb = sys.modules["chromadb"]

        store = ChromaVectorStore(host="localhost", port=8000)
        client = store._get_client()

        assert client is not None
        assert store._client is not None
        mock_chromadb.HttpClient.assert_called_once_with(host="localhost", port=8000)

    def test_get_client_reuses_client(self, setup_mock: None) -> None:
        """Test that _get_client reuses existing client."""
        import sys

        mock_chromadb = sys.modules["chromadb"]

        store = ChromaVectorStore(host="localhost", port=8000)

        # First call
        client1 = store._get_client()
        # Second call should return same client
        client2 = store._get_client()

        assert client1 is client2
        mock_chromadb.HttpClient.assert_called_once()

    def test_get_client_import_error(self) -> None:
        """Test that ImportError is raised when chromadb is not installed."""
        with patch.dict(sys.modules, {"chromadb": None}):
            store = ChromaVectorStore(host="localhost", port=8000)
            with pytest.raises(ImportError) as exc_info:
                store._get_client()
            assert "chromadb is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upsert_success(self, setup_mock: None) -> None:
        """Test successful upsert operation."""
        import sys

        mock_chromadb = sys.modules["chromadb"]
        store = ChromaVectorStore(host="localhost", port=8000)
        mock_collection = MagicMock()
        mock_chromadb.HttpClient.return_value.get_or_create_collection.return_value = (
            mock_collection
        )

        await store.upsert(
            collection="test_collection",
            documents=["doc1", "doc2"],
            embeddings=[[0.1, 0.2], [0.3, 0.4]],
            metadatas=[{"key": "value1"}, {"key": "value2"}],
            ids=["id1", "id2"],
        )

        mock_chromadb.HttpClient.return_value.get_or_create_collection.assert_called_with(
            "test_collection"
        )
        mock_collection.upsert.assert_called_once_with(
            documents=["doc1", "doc2"],
            embeddings=[[0.1, 0.2], [0.3, 0.4]],
            metadatas=[{"key": "value1"}, {"key": "value2"}],
            ids=["id1", "id2"],
        )

    @pytest.mark.asyncio
    async def test_upsert_mismatched_lengths(self) -> None:
        """Test upsert with mismatched list lengths."""
        store = ChromaVectorStore(host="localhost", port=8000)

        with pytest.raises(
            ValueError, match="All input lists must have the same length"
        ):
            await store.upsert(
                collection="test_collection",
                documents=["doc1"],  # 1 item
                embeddings=[[0.1, 0.2], [0.3, 0.4]],  # 2 items
                metadatas=[{"key": "value1"}],  # 1 item
                ids=["id1", "id2"],  # 2 items
            )

    @pytest.mark.asyncio
    async def test_upsert_empty_lists(self, setup_mock: None) -> None:
        """Test upsert with empty lists."""
        store = ChromaVectorStore(host="localhost", port=8000)

        # Empty lists should be allowed (no-op)
        await store.upsert(
            collection="test_collection",
            documents=[],
            embeddings=[],
            metadatas=[],
            ids=[],
        )

        # Verify no error was raised

    @pytest.mark.asyncio
    async def test_query_success(self, setup_mock: None) -> None:
        """Test successful query operation."""
        import sys

        from src.contexts.knowledge.application.ports.i_vector_store import QueryResult

        mock_chromadb = sys.modules["chromadb"]
        store = ChromaVectorStore(host="localhost", port=8000)
        mock_collection = MagicMock()
        mock_chromadb.HttpClient.return_value.get_or_create_collection.return_value = (
            mock_collection
        )

        # Mock query results
        mock_collection.query.return_value = {
            "ids": [["id1", "id2"]],
            "documents": [["doc1", "doc2"]],
            "distances": [[0.1, 0.2]],
            "metadatas": [[{"key": "value1"}, {"key": "value2"}]],
        }

        results = await store.query(
            query_embedding=[0.1, 0.2],
            n_results=2,
            collection="test_collection",
        )

        assert len(results) == 2
        assert isinstance(results[0], QueryResult)
        assert results[0].id == "id1"
        assert results[0].text == "doc1"
        assert results[0].score == 0.1
        assert results[0].metadata == {"key": "value1"}

    @pytest.mark.asyncio
    async def test_query_empty_results(self, setup_mock: None) -> None:
        """Test query with empty results."""
        import sys

        mock_chromadb = sys.modules["chromadb"]
        store = ChromaVectorStore(host="localhost", port=8000)
        mock_collection = MagicMock()
        mock_chromadb.HttpClient.return_value.get_or_create_collection.return_value = (
            mock_collection
        )

        mock_collection.query.return_value = {
            "ids": [],
            "documents": [],
            "distances": [],
            "metadatas": [],
        }

        results = await store.query(
            query_embedding=[0.1, 0.2],
            n_results=10,
            collection="test_collection",
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_success(self, setup_mock: None) -> None:
        """Test successful delete operation."""
        import sys

        mock_chromadb = sys.modules["chromadb"]
        store = ChromaVectorStore(host="localhost", port=8000)
        mock_collection = MagicMock()
        mock_chromadb.HttpClient.return_value.get_or_create_collection.return_value = (
            mock_collection
        )

        await store.delete(
            collection="test_collection",
            ids=["id1", "id2"],
        )

        mock_collection.delete.assert_called_once_with(ids=["id1", "id2"])

    @pytest.mark.asyncio
    async def test_count_success(self, setup_mock: None) -> None:
        """Test successful count operation."""
        import sys

        mock_chromadb = sys.modules["chromadb"]
        store = ChromaVectorStore(host="localhost", port=8000)
        mock_collection = MagicMock()
        mock_chromadb.HttpClient.return_value.get_or_create_collection.return_value = (
            mock_collection
        )

        mock_collection.count.return_value = 42

        result = await store.count(collection="test_collection")

        assert result == 42
        mock_collection.count.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_success(self, setup_mock: None) -> None:
        """Test health check when service is healthy."""
        import sys

        mock_chromadb = sys.modules["chromadb"]
        store = ChromaVectorStore(host="localhost", port=8000)
        mock_client = MagicMock()
        mock_chromadb.HttpClient.return_value = mock_client

        result = await store.health_check()

        assert result is True
        mock_client.list_collections.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, setup_mock: None) -> None:
        """Test health check when service is unhealthy."""
        import sys

        mock_chromadb = sys.modules["chromadb"]
        store = ChromaVectorStore(host="localhost", port=8000)
        mock_client = MagicMock()
        mock_client.list_collections.side_effect = Exception("Connection failed")
        mock_chromadb.HttpClient.return_value = mock_client

        result = await store.health_check()

        assert result is False


@pytest.mark.requires_chroma
class TestChromaVectorStoreIntegration:
    """Integration tests requiring actual ChromaDB server.

    These tests are skipped unless explicitly enabled.
    """

    @pytest.fixture
    async def chroma_store(self) -> ChromaVectorStore:
        """Provide connected ChromaVectorStore."""
        store = ChromaVectorStore(host="localhost", port=8000)
        yield store
        # Cleanup
        try:
            await store.clear(collection="test_collection")
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_full_workflow(self, chroma_store: ChromaVectorStore) -> None:
        """Test full workflow with real ChromaDB."""
        pytest.skip("Requires running ChromaDB server")
