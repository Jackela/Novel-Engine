"""
Retrieval Service

Service for retrieving relevant knowledge.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.contexts.knowledge.application.ports.i_embedding_service import (
    IEmbeddingService,
)
from src.contexts.knowledge.application.ports.i_vector_store import IVectorStore
from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    RetrievedChunk,
    SourceType,
)
from src.contexts.knowledge.application.services.rerank_service import RerankService


@dataclass
class RetrievalOptions:
    """Options for retrieval."""

    min_score: float = 0.0
    enable_rerank: bool = True
    max_results: int = 10


@dataclass
class RetrievalResult:
    """Result of retrieval."""

    chunks: list[RetrievedChunk] = field(default_factory=list)
    total_found: int = 0


class RetrievalService:
    """Service for retrieving relevant knowledge."""

    def __init__(
        self,
        embedding_service: IEmbeddingService,
        vector_store: IVectorStore,
        rerank_service: RerankService | None = None,
    ):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.rerank_service = rerank_service

    async def retrieve_relevant(
        self,
        query: str,
        k: int = 5,
        options: RetrievalOptions | None = None,
    ) -> RetrievalResult:
        """Retrieve relevant chunks for a query."""
        options = options or RetrievalOptions()

        # Get query embedding
        query_embedding = await self.embedding_service.embed(query)

        # Query vector store
        results = await self.vector_store.query(
            query_embedding=query_embedding,
            n_results=k,
            collection="knowledge",
        )

        # Convert to RetrievedChunk
        chunks = []
        for result in results:
            if result.score >= options.min_score:
                source_type_str = result.metadata.get("source_type", "document")
                try:
                    source_type = SourceType(source_type_str)
                except ValueError:
                    source_type = SourceType.DOCUMENT

                chunk = RetrievedChunk(
                    content=result.text,
                    score=result.score,
                    source_type=source_type,
                    metadata=result.metadata,
                )
                chunks.append(chunk)

        # Apply reranking if enabled
        if options.enable_rerank and self.rerank_service and chunks:
            # Convert to format expected by reranker
            rerank_input = [
                {
                    "id": str(i),
                    "text": c.content,
                    "score": c.score,
                    "metadata": c.metadata,
                }
                for i, c in enumerate(chunks)
            ]

            reranked = await self.rerank_service.rerank(query, rerank_input)

            # Update scores based on reranking
            for i, r in enumerate(reranked):
                if i < len(chunks):
                    chunks[i].score = r.score

        return RetrievalResult(chunks=chunks, total_found=len(chunks))
