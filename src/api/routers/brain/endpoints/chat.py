# mypy: ignore-errors

"""
Chat & Session Endpoints

BRAIN-037A-01: Chat Backend POST Endpoint
BRAIN-037A-03: Session-based chat history
PREP-013: Persistent chat session repository
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.api.routers.brain.dependencies import (
    get_brain_settings_repository,
    get_context_window_manager,
)
from src.api.routers.brain.repositories.brain_settings import BrainSettingsRepository

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["brain-settings"])

# PREP-013: Import persistent chat session repository
from src.contexts.knowledge.infrastructure.repositories.chat_session_repository import (
    ChatMessage as DomainChatMessage,
)
from src.contexts.knowledge.infrastructure.repositories.chat_session_repository import (
    ChatSessionRepository as PersistentChatSessionRepository,
)

# PREP-013: Use persistent repository instead of in-memory store
_persistent_chat_repository = PersistentChatSessionRepository()


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str  # "user" or "assistant"
    content: str


class ChatSessionStore:
    """
    Wrapper for chat session storage.

    PREP-013: Now delegates to persistent repository for durability.
    Maintains backward compatibility with existing code.
    """

    def __init__(self) -> None:
        self._repository = _persistent_chat_repository

    def get_session(self, session_id: str) -> list[ChatMessage]:
        """Get chat history for a session."""
        messages = self._repository.get_session(session_id)
        return [ChatMessage(role=m.role, content=m.content) for m in messages]

    def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Add a message to a session."""
        domain_message = DomainChatMessage(role=message.role, content=message.content)
        self._repository.add_message(session_id, domain_message)

    def clear_session(self, session_id: str) -> None:
        """Clear chat history for a session."""
        self._repository.clear_session(session_id)


# Global session store
_chat_session_store = ChatSessionStore()


class ChatChunk(BaseModel):
    """A single chunk of streaming response."""

    delta: str  # Text content added
    done: bool = False  # Whether this is the final chunk


class ChatRequest(BaseModel):
    """Request for chat completion."""

    query: str  # User's question/prompt
    chat_history: list[ChatMessage] | None = None  # Optional conversation history
    scene_id: str | None = None  # Optional scene ID for context
    max_chunks: int = 5  # Maximum chunks to retrieve for RAG
    session_id: str | None = (
        None  # BRAIN-037A-03: Optional session ID for conversation tracking
    )


class ChatSessionListResponse(BaseModel):
    """Response for listing chat sessions."""

    sessions: list[dict]
    total: int


class ChatSessionMessagesResponse(BaseModel):
    """Response for getting session messages."""

    session_id: str
    messages: list[dict]
    total: int


@router.post("/chat")
async def chat_completion(
    request: Request,
    payload: ChatRequest,
    repository: BrainSettingsRepository = Depends(get_brain_settings_repository),
    context_manager=Depends(get_context_window_manager),
) -> StreamingResponse:
    """
    Chat completion with RAG context.

    BRAIN-037A-01: Chat Backend POST Endpoint
    Accepts query and optional chat history, returns streaming response.

    Args:
        payload: Chat request with query, optional history, and scene_id

    Returns:
        StreamingResponse with SSE-formatted chat chunks
    """

    async def _stream_chat() -> AsyncIterator[str]:
        """Stream chat response with RAG context."""
        try:
            # BRAIN-037A-03: Handle session-based chat history
            session_id = payload.session_id or "default"
            chat_history = _chat_session_store.get_session(session_id)

            # If chat_history was provided in request, use it (for backward compatibility)
            if payload.chat_history is not None:
                chat_history = payload.chat_history

            # Check if RAG is enabled
            rag_config = await repository.get_rag_config()

            # Build system prompt
            system_prompt = "You are a helpful AI assistant for a novel writing tool."

            # If RAG is enabled, retrieve relevant context
            # BRAIN-037A-03: Include conversation context in RAG query for better retrieval
            if chat_history and len(chat_history) > 0:
                # Include last assistant response for context
                last_assistant_msg = next(
                    (m for m in reversed(chat_history) if m.role == "assistant"), None
                )
                if last_assistant_msg:
                    rag_query = f"{last_assistant_msg.content}\n\nUser: {payload.query}"
                else:
                    rag_query = payload.query
            else:
                rag_query = payload.query

            rag_chunks: list = []
            if rag_config.get("enabled", False):
                try:
                    from src.contexts.knowledge.application.services.retrieval_service import (
                        RetrievalService,
                    )
                    from src.contexts.knowledge.infrastructure.adapters.chromadb_vector_store import (
                        ChromaDBVectorStore,
                    )
                    from src.contexts.knowledge.infrastructure.adapters.embedding_generator_adapter import (
                        EmbeddingServiceAdapter,
                    )

                    # Get or create singleton instances
                    embedding_service = getattr(
                        request.app.state, "embedding_service", None
                    )
                    if embedding_service is None:
                        embedding_service = EmbeddingServiceAdapter(use_mock=True)
                        request.app.state.embedding_service = embedding_service

                    vector_store = getattr(request.app.state, "vector_store", None)
                    if vector_store is None:
                        vector_store = ChromaDBVectorStore()
                        request.app.state.vector_store = vector_store

                    # Retrieve relevant chunks using conversation-enhanced query
                    retrieval_service = RetrievalService(
                        embedding_service=embedding_service,
                        vector_store=vector_store,
                    )

                    result = await retrieval_service.retrieve_relevant(
                        query=rag_query,
                        k=payload.max_chunks,
                        filters=None,
                    )
                    rag_chunks = result.chunks

                except Exception as e:
                    logger.warning(
                        f"RAG retrieval failed, continuing without context: {e}"
                    )

            # OPT-009: Use ContextWindowManager to manage context and prevent overflow
            from src.contexts.knowledge.application.services.context_window_manager import (
                ChatMessage as ContextWindowChatMessage,
            )

            # Convert chat history to ContextWindowChatMessage format
            history_messages = [
                ContextWindowChatMessage(role=msg.role, content=msg.content)
                for msg in chat_history
            ]

            # Add RAG context to system prompt if chunks were retrieved
            if rag_chunks:
                context_parts: list[Any] = []
                for i, chunk in enumerate(rag_chunks, 1):
                    context_parts.append(
                        f"[Source {i}: {chunk.source_type}:{chunk.source_id}]"
                    )
                    context_parts.append(chunk.content)
                rag_context_text = "\n".join(context_parts)
                system_prompt += f"\n\nUse the following context to answer the user's question:\n\n{rag_context_text}"

            # Manage context window (prune history, optimize RAG chunks if needed)
            managed_context = await context_manager.manage_context(
                system_prompt=system_prompt,
                rag_chunks=rag_chunks,
                chat_history=history_messages,
                query=payload.query,
            )

            # Get formatted messages for LLM (for future LLM integration)
            _messages = managed_context.to_api_messages()  # noqa: F841 - used by future LLM integration
            # Add current query (already included in managed_context.chat_history)

            # For now, return a mock streaming response
            # In a full implementation, this would call an LLM service
            response_text = f'I received your question: "{payload.query}"'

            if rag_chunks:
                response_text += f"\n\nI found {len(rag_chunks)} relevant chunks from the knowledge base."
            else:
                response_text += (
                    "\n\nNo relevant context was found in the knowledge base."
                )

            # OPT-009: Indicate context management
            if chat_history:
                response_text += f"\n\n(Context: You have sent {len(chat_history)} messages in this session. "
                if managed_context.messages_pruned > 0:
                    response_text += f"Pruned {managed_context.messages_pruned} old messages to fit context window. "
                response_text += ")"

            response_text += f"\n\n(Token usage: {managed_context.total_tokens}/{context_manager._config.model_context_window} "
            response_text += f"(system: {managed_context.system_tokens}, RAG: {managed_context.rag_tokens}, history: {managed_context.history_tokens}))"

            response_text += "\n\n(Note: This is a mock response. Full LLM integration will be implemented in a future story.)"

            # Stream the response in chunks
            words = response_text.split()
            for i, word in enumerate(words):
                chunk = ChatChunk(delta=word + " ", done=i == len(words) - 1)
                yield f"data: {chunk.model_dump_json()}\n\n"
                await asyncio.sleep(0.02)  # Simulate streaming delay

            # Send final done signal
            final_chunk = ChatChunk(delta="", done=True)
            yield f"data: {final_chunk.model_dump_json()}\n\n"

            # BRAIN-037A-03: Save messages to session store
            user_msg = ChatMessage(role="user", content=payload.query)
            _chat_session_store.add_message(session_id, user_msg)
            assistant_msg = ChatMessage(role="assistant", content=response_text)
            _chat_session_store.add_message(session_id, assistant_msg)

        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            error_chunk = ChatChunk(delta=f"Error: {str(e)}", done=True)
            yield f"data: {error_chunk.model_dump_json()}\n\n"

    return StreamingResponse(
        _stream_chat(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/sessions", response_model=ChatSessionListResponse)
async def list_chat_sessions(
    limit: int = 50,
    offset: int = 0,
) -> ChatSessionListResponse:
    """
    List all chat sessions.

    PREP-013: Returns a paginated list of chat sessions.
    Sessions are ordered by most recently updated.
    """
    sessions = _persistent_chat_repository.list_sessions(limit=limit, offset=offset)
    return ChatSessionListResponse(
        sessions=[s.to_dict() for s in sessions],
        total=len(sessions),
    )


@router.get(
    "/chat/sessions/{session_id}/messages",
    response_model=ChatSessionMessagesResponse,
)
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    offset: int = 0,
) -> ChatSessionMessagesResponse:
    """
    Get messages for a specific chat session.

    PREP-013: Returns paginated messages for a session.
    Messages are ordered chronologically.
    """
    messages = _persistent_chat_repository.get_session_messages(
        session_id, limit=limit, offset=offset
    )
    return ChatSessionMessagesResponse(
        session_id=session_id,
        messages=[m.to_dict() for m in messages],
        total=len(messages),
    )


@router.delete("/chat/sessions/{session_id}")
async def clear_chat_session(session_id: str) -> dict:
    """
    Clear a chat session.

    PREP-013: Deletes all messages in a session.
    """
    _persistent_chat_repository.clear_session(session_id)
    return {"status": "success", "message": f"Session {session_id} cleared"}
