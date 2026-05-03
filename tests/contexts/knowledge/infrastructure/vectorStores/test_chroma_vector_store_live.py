"""Live smoke for the Chroma-backed vector store."""

# mypy: disable-error-code=misc

from __future__ import annotations

import os
from contextlib import suppress
from uuid import uuid4

import pytest

from src.contexts.knowledge.infrastructure.vectorStores.chroma_knowledge_vector_store import (  # noqa: E501
    ChromaKnowledgeVectorStore,
)
from src.contexts.knowledge.infrastructure.vectorStores.chroma_vector_store import (
    ChromaVectorStore,
)

pytestmark = pytest.mark.requires_chroma


@pytest.mark.asyncio
async def test_chroma_vector_store_live_smoke() -> None:
    host = os.getenv("CHROMA_HOST", "localhost")
    port = int(os.getenv("CHROMA_PORT", "8000"))
    collection = f"live_smoke_{uuid4().hex}"
    store = ChromaVectorStore(host=host, port=port)
    adapter = ChromaKnowledgeVectorStore(store, collection=collection)

    try:
        assert await store.health_check() is True

        await adapter.store_embedding(
            document_id="doc-1",
            content="A hidden archive beneath the city",
            embedding=[0.1, 0.2, 0.3],
            metadata={"topic": "archive"},
        )
        await adapter.store_embedding(
            document_id="doc-2",
            content="A lantern-lit market at the edge of the forest",
            embedding=[0.9, 0.9, 0.9],
            metadata={"topic": "market"},
        )

        results = await adapter.search_similar([0.1, 0.2, 0.3], top_k=2)
        assert len(results) == 2
        assert results[0]["document_id"] == "doc-1"
        assert results[0]["content"] == "A hidden archive beneath the city"
        assert results[0]["metadata"] == {"topic": "archive"}
        assert results[0]["score"] >= results[1]["score"]

        assert await store.count(collection) == 2

        await adapter.delete_document("doc-2")
        assert await store.count(collection) == 1

        await store.clear(collection)
        assert await store.count(collection) == 0
    finally:
        with suppress(Exception):
            await store.clear(collection)
