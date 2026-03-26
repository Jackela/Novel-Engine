"""Tests for the knowledge-service Chroma adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.contexts.knowledge.infrastructure.vectorStores.chroma_knowledge_vector_store import (
    ChromaKnowledgeVectorStore,
)


class _FakeChromaStore:
    def __init__(self) -> None:
        self.upsert = AsyncMock()
        self.query = AsyncMock()
        self.delete = AsyncMock()


@pytest.fixture
def chroma_store() -> _FakeChromaStore:
    return _FakeChromaStore()


@pytest.fixture
def adapter(chroma_store: _FakeChromaStore) -> ChromaKnowledgeVectorStore:
    return ChromaKnowledgeVectorStore(chroma_store)


@pytest.mark.asyncio
async def test_store_embedding_delegates_to_chroma_upsert(
    adapter: ChromaKnowledgeVectorStore,
    chroma_store: _FakeChromaStore,
) -> None:
    await adapter.store_embedding(
        document_id="doc-1",
        content="document body",
        embedding=[0.1, 0.2],
        metadata={"knowledge_base_id": "kb-1"},
    )

    chroma_store.upsert.assert_awaited_once_with(
        collection="knowledge",
        documents=["document body"],
        embeddings=[[0.1, 0.2]],
        metadatas=[{"knowledge_base_id": "kb-1"}],
        ids=["doc-1"],
    )


@pytest.mark.asyncio
async def test_search_similar_maps_query_results_to_service_contract(
    adapter: ChromaKnowledgeVectorStore,
    chroma_store: _FakeChromaStore,
) -> None:
    chroma_store.query.return_value = [
        type(
            "QueryResult",
            (),
            {
                "id": "doc-1",
                "text": "document body",
                "score": 0.25,
                "metadata": {"knowledge_base_id": "kb-1"},
            },
        )()
    ]

    results = await adapter.search_similar(
        query_embedding=[0.1, 0.2],
        top_k=3,
        filters={"knowledge_base_id": "kb-1"},
    )

    chroma_store.query.assert_awaited_once_with(
        query_embedding=[0.1, 0.2],
        n_results=3,
        where={"knowledge_base_id": "kb-1"},
        collection="knowledge",
    )
    assert results == [
        {
            "document_id": "doc-1",
            "content": "document body",
            "score": 0.8,
            "metadata": {"knowledge_base_id": "kb-1"},
        }
    ]


@pytest.mark.asyncio
async def test_delete_document_delegates_to_chroma_delete(
    adapter: ChromaKnowledgeVectorStore,
    chroma_store: _FakeChromaStore,
) -> None:
    await adapter.delete_document("doc-1")

    chroma_store.delete.assert_awaited_once_with(
        collection="knowledge",
        ids=["doc-1"],
    )
