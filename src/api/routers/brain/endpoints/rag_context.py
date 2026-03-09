"""
RAG Context Retrieval Endpoints

BRAIN-036-02: Context Inspector backend endpoint
BRAIN-036-03: Highlight used chunks based on relevance threshold
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Query, Request

from src.api.routers.brain.dependencies import get_brain_settings_repository
from src.api.routers.brain.repositories.brain_settings import BrainSettingsRepository
from src.api.schemas import RAGContextResponse, RetrievedChunkResponse

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["brain-settings"])


@router.get("/context", response_model=RAGContextResponse)
async def get_rag_context(
    request: Request,
    query: str = Query(..., description="Query to retrieve context for"),
    scene_id: str | None = Query(None, description="Scene ID to get context for"),
    max_chunks: int = Query(5, ge=1, le=20, description="Maximum chunks to retrieve"),
    used_threshold: float = Query(
        0.7, ge=0, le=1, description="Score threshold to mark chunk as used"
    ),
    repository: BrainSettingsRepository = Depends(get_brain_settings_repository),
) -> RAGContextResponse:
    """
    Get RAG context for a query or scene.

    BRAIN-036-02: Context Inspector backend endpoint
    BRAIN-036-03: Highlight used chunks based on relevance threshold

    Args:
        query: Search query for context retrieval
        scene_id: Optional scene ID (if provided, uses scene content as query base)
        max_chunks: Maximum number of chunks to retrieve
        used_threshold: Score threshold to mark chunk as "used" (default: 0.7)

    Returns:
        RAGContextResponse with retrieved chunks, scores, and metadata
    """
    try:
        # Check if RAG is enabled
        rag_config = await repository.get_rag_config()
        if not rag_config.get("enabled", False):
            return RAGContextResponse(
                query=query,
                chunks=[],
                total_tokens=0,
                chunk_count=0,
                sources=[],
            )

        # Import retrieval service and adapters
        from src.contexts.knowledge.application.services.retrieval_service import (
            RetrievalService,
        )
        from src.contexts.knowledge.application.services.token_counter import (
            TokenCounter,
        )
        from src.contexts.knowledge.infrastructure.adapters.chromadb_vector_store import (
            ChromaDBVectorStore,
        )
        from src.contexts.knowledge.infrastructure.adapters.embedding_generator_adapter import (
            EmbeddingServiceAdapter,
        )

        # Create dependencies (lazy initialization for performance)
        token_counter = TokenCounter()

        # Get or create singleton instances from app state
        embedding_service = getattr(request.app.state, "embedding_service", None)
        if embedding_service is None:
            embedding_service = EmbeddingServiceAdapter(
                use_mock=True
            )  # Use mock for now
            request.app.state.embedding_service = embedding_service

        vector_store = getattr(request.app.state, "vector_store", None)
        if vector_store is None:
            vector_store = ChromaDBVectorStore()
            request.app.state.vector_store = vector_store

        # Create retrieval service
        retrieval_service = RetrievalService(
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

        # Retrieve relevant chunks
        result = await retrieval_service.retrieve_relevant(
            query=query,
            k=max_chunks,
            filters=None,
        )

        # Convert to response format
        chunks_response: list[RetrievedChunkResponse] = []
        total_tokens = 0

        for chunk in result.chunks:
            # Count tokens for this chunk
            count_result = token_counter.count(chunk.content)
            if count_result.is_error:
                # Fallback to rough estimation
                token_count = len(chunk.content) // 4
            else:
                token_count = count_result.unwrap().token_count

            # BRAIN-036-03: Mark chunk as used if score meets threshold
            is_used = chunk.score >= used_threshold

            chunks_response.append(
                RetrievedChunkResponse(
                    chunk_id=chunk.chunk_id,
                    source_id=chunk.source_id,
                    source_type=chunk.source_type.value,
                    content=chunk.content,
                    score=round(chunk.score, 3),
                    token_count=token_count,
                    metadata=chunk.metadata or {},
                    used=is_used,
                )
            )
            total_tokens += token_count

        # Extract source references
        sources = retrieval_service.get_sources(result.chunks)
        source_refs = [f"{s['source_type']}:{s['source_id']}" for s in sources]

        return RAGContextResponse(
            query=query,
            chunks=chunks_response,
            total_tokens=total_tokens,
            chunk_count=len(chunks_response),
            sources=source_refs,
        )

    except Exception as e:
        logger.error(f"Failed to get RAG context: {e}")
        # Return empty context on error for graceful degradation
        return RAGContextResponse(
            query=query,
            chunks=[],
            total_tokens=0,
            chunk_count=0,
            sources=[],
        )
