"""
Context Window Manager Service

Prevents context window overflow by intelligently pruning chat history and
RAG context to fit within model token limits.

Constitution Compliance:
- Article II (Hexagonal): Application service for context window management
- Article V (SOLID): SRP - context window management only

OPT-009: Context Window Manager
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING
from collections import deque

import structlog

from .token_counter import TokenCounter, LLMProvider
from .context_optimizer import ContextOptimizer, PackingStrategy
from ..services.knowledge_ingestion_service import RetrievedChunk

if TYPE_CHECKING:
    pass


logger = structlog.get_logger()


# Default context window sizes for common models
DEFAULT_CONTEXT_WINDOWS: dict[str, int] = {
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-4-turbo": 128000,
    "gpt-4": 8192,
    "gpt-3.5-turbo": 16385,
    "claude-3-5-sonnet": 200000,
    "claude-3-5-haiku": 200000,
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "gemini-2.0-flash": 1000000,
    "gemini-1.5-pro": 2800000,
    "gemini-1.5-flash": 2800000,
}


class PruningStrategy(str, Enum):
    """Strategies for pruning chat history.

    Why Enum:
        Type-safe strategy selection with string compatibility.
    """

    OLDEST_FIRST = "oldest_first"  # Remove oldest messages first
    LEAST_RECENT = "least_recent"  # Remove messages furthest from current turn
    KEEP_SYSTEM = "keep_system"  # Always preserve system prompt


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """
    A chat message for context management.

    Attributes:
        role: Message role (system, user, assistant)
        content: Message content
        tokens: Estimated token count (0 if not counted)
    """

    role: str
    content: str
    tokens: int = 0

    def with_tokens(self, token_count: int) -> "ChatMessage":
        """Return a new ChatMessage with updated token count."""
        return ChatMessage(role=self.role, content=self.content, tokens=token_count)


@dataclass(frozen=True, slots=True)
class ContextWindowConfig:
    """
    Configuration for context window management.

    Attributes:
        model_context_window: Total context window for the model
        system_prompt_tokens: Reserved tokens for system prompt
        reserve_for_response: Reserve tokens for LLM response
        pruning_strategy: Strategy for pruning history
        enable_rag_optimization: Whether to optimize RAG chunks
        rag_strategy: Strategy for RAG chunk optimization
    """

    model_context_window: int = 128000  # Default to GPT-4o
    system_prompt_tokens: int = 500
    reserve_for_response: int = 2000
    pruning_strategy: PruningStrategy = PruningStrategy.OLDEST_FIRST
    enable_rag_optimization: bool = True
    rag_strategy: PackingStrategy = PackingStrategy.REMOVE_REDUNDANCY


@dataclass
class ManagedContext:
    """
    Result of context window management.

    Attributes:
        system_prompt: System prompt (possibly truncated)
        rag_chunks: Optimized RAG chunks
        chat_history: Pruned chat history
        total_tokens: Total token count
        system_tokens: Tokens used by system prompt
        rag_tokens: Tokens used by RAG chunks
        history_tokens: Tokens used by chat history
        reserved_tokens: Reserved for response
        messages_pruned: Number of messages removed from history
        chunks_optimized: Number of chunks optimized/removed
        fits_window: Whether context fits within window
    """

    system_prompt: str
    rag_chunks: list[RetrievedChunk]
    chat_history: list[ChatMessage]
    total_tokens: int
    system_tokens: int
    rag_tokens: int
    history_tokens: int
    reserved_tokens: int
    messages_pruned: int
    chunks_optimized: int
    fits_window: bool

    def to_api_messages(self) -> list[dict[str, str]]:
        """
        Convert to API message format.

        Returns:
            List of message dicts with 'role' and 'content' keys
        """
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend([
            {"role": msg.role, "content": msg.content}
            for msg in self.chat_history
        ])
        return messages


class ContextWindowManager:
    """
    Manages context window to prevent overflow.

    Priority Order (per OPT-009):
    1. System Prompt - Always preserved
    2. RAG Chunks - Optimized but preserved
    3. Recent History - Oldest pruned first

    Constitution Compliance:
        - Article II (Hexagonal): Application service
        - Article V (SOLID): SRP - context window management

    Example:
        >>> manager = ContextWindowManager()
        >>> result = await manager.manage_context(
        ...     system_prompt="You are a helpful assistant.",
        ...     rag_chunks=chunks,
        ...     chat_history=history,
        ... )
        >>> print(f"Fits in window: {result.fits_window}")
    """

    def __init__(
        self,
        token_counter: TokenCounter | None = None,
        context_optimizer: ContextOptimizer | None = None,
        config: ContextWindowConfig | None = None,
    ):
        """
        Initialize the context window manager.

        Args:
            token_counter: Token counter for estimation (creates default if None)
            context_optimizer: Context optimizer for RAG chunks (creates default if None)
            config: Context window configuration
        """
        self._token_counter = token_counter or TokenCounter()
        self._context_optimizer = context_optimizer or ContextOptimizer(
            token_counter=self._token_counter
        )
        self._config = config or ContextWindowConfig()

    async def manage_context(
        self,
        system_prompt: str,
        rag_chunks: list[RetrievedChunk],
        chat_history: list[ChatMessage],
        query: str,
        config: ContextWindowConfig | None = None,
    ) -> ManagedContext:
        """
        Manage context to fit within token window.

        Args:
            system_prompt: System prompt for the LLM
            rag_chunks: Retrieved RAG chunks
            chat_history: Conversation history (oldest first)
            query: Current user query to add
            config: Optional config override

        Returns:
            ManagedContext with optimized/pruned content

        Raises:
            ValueError: If system prompt alone exceeds window
        """
        cfg = config or self._config

        logger.debug(
            "context_window_management_start",
            model_window=cfg.model_context_window,
            chunks_count=len(rag_chunks),
            history_count=len(chat_history),
        )

        # Calculate available tokens
        available_for_content = (
            cfg.model_context_window
            - cfg.system_prompt_tokens
            - cfg.reserve_for_response
        )

        # Count system prompt tokens
        system_tokens = self._token_counter.count(system_prompt).token_count

        if system_tokens > cfg.model_context_window:
            raise ValueError(
                f"System prompt ({system_tokens} tokens) exceeds model context window "
                f"({cfg.model_context_window} tokens)"
            )

        # Step 1: Optimize RAG chunks (if enabled)
        managed_chunks, rag_tokens, chunks_optimized = await self._manage_rag_chunks(
            rag_chunks,
            available_for_content,
            cfg,
        )

        # Step 2: Prune chat history to fit remaining space
        remaining_for_history = available_for_content - rag_tokens
        managed_history, history_tokens, messages_pruned = self._prune_history(
            chat_history,
            query,
            remaining_for_history,
            cfg,
        )

        # Calculate totals
        total_tokens = system_tokens + rag_tokens + history_tokens
        fits_window = total_tokens <= (cfg.model_context_window - cfg.reserve_for_response)

        result = ManagedContext(
            system_prompt=system_prompt,
            rag_chunks=managed_chunks,
            chat_history=managed_history,
            total_tokens=total_tokens,
            system_tokens=system_tokens,
            rag_tokens=rag_tokens,
            history_tokens=history_tokens,
            reserved_tokens=cfg.reserve_for_response,
            messages_pruned=messages_pruned,
            chunks_optimized=chunks_optimized,
            fits_window=fits_window,
        )

        logger.info(
            "context_window_management_complete",
            total_tokens=total_tokens,
            system_tokens=system_tokens,
            rag_tokens=rag_tokens,
            history_tokens=history_tokens,
            messages_pruned=messages_pruned,
            chunks_optimized=chunks_optimized,
            fits_window=fits_window,
        )

        return result

    async def _manage_rag_chunks(
        self,
        chunks: list[RetrievedChunk],
        available_tokens: int,
        config: ContextWindowConfig,
    ) -> tuple[list[RetrievedChunk], int, int]:
        """
        Manage RAG chunks to fit within token budget.

        Args:
            chunks: Input chunks
            available_tokens: Tokens available for RAG
            config: Context window config

        Returns:
            Tuple of (managed_chunks, token_count, optimized_count)
        """
        if not chunks:
            return [], 0, 0

        if not config.enable_rag_optimization:
            # Simple truncation without optimization
            total = 0
            kept = []
            for chunk in chunks:
                chunk_tokens = self._token_counter.count(chunk.content).token_count
                if total + chunk_tokens > available_tokens:
                    break
                kept.append(chunk)
                total += chunk_tokens
            return kept, total, len(chunks) - len(kept)

        # Use ContextOptimizer for intelligent optimization
        result = await self._context_optimizer.optimize_context(
            chunks=chunks,
            max_tokens=available_tokens,
            strategy=config.rag_strategy,
        )

        optimized_count = len(chunks) - len(result.chunks)
        return result.chunks, result.total_tokens, optimized_count

    def _prune_history(
        self,
        history: list[ChatMessage],
        query: str,
        available_tokens: int,
        config: ContextWindowConfig,
    ) -> tuple[list[ChatMessage], int, int]:
        """
        Prune chat history to fit within token budget.

        Args:
            history: Chat history (oldest first)
            query: Current query to add (always included)
            available_tokens: Tokens available for history
            config: Context window config

        Returns:
            Tuple of (pruned_history, token_count, pruned_count)
        """
        if not history:
            # Just include the query
            query_tokens = self._token_counter.count(query).token_count
            return [
                ChatMessage(role="user", content=query, tokens=query_tokens)
            ], query_tokens, 0

        # Count tokens for all history messages
        history_with_tokens = []
        for msg in history:
            tokens = self._token_counter.count(msg.content).token_count
            history_with_tokens.append(msg.with_tokens(tokens))

        # Calculate current query tokens
        query_tokens = self._token_counter.count(query).token_count

        # Pruning strategy: OLDEST_FIRST (default)
        # Keep recent messages, remove oldest first
        if config.pruning_strategy == PruningStrategy.OLDEST_FIRST:
            return self._prune_oldest_first(
                history_with_tokens,
                query,
                query_tokens,
                available_tokens,
            )

        # Default to oldest first
        return self._prune_oldest_first(
            history_with_tokens,
            query,
            query_tokens,
            available_tokens,
        )

    def _prune_oldest_first(
        self,
        history: list[ChatMessage],
        query: str,
        query_tokens: int,
        available_tokens: int,
    ) -> tuple[list[ChatMessage], int, int]:
        """
        Prune oldest messages first.

        Keeps the current query and most recent history.
        """
        # Always include the current query
        kept: list[ChatMessage] = [
            ChatMessage(role="user", content=query, tokens=query_tokens)
        ]
        total_tokens = query_tokens

        # Add history from newest to oldest until budget exhausted
        for msg in reversed(history):
            if total_tokens + msg.tokens > available_tokens:
                break
            kept.insert(0, msg)  # Insert at beginning to maintain order
            total_tokens += msg.tokens

        pruned = len(history) - (len(kept) - 1)  # -1 for the query
        return kept, total_tokens, pruned

    def calculate_available_tokens(
        self,
        model_name: str | None = None,
        system_prompt: str | None = None,
        reserve_for_response: int | None = None,
    ) -> int:
        """
        Calculate available tokens for RAG + history.

        Args:
            model_name: Model name to look up context window
            system_prompt: System prompt to count
            reserve_for_response: Override default reservation

        Returns:
            Available token count
        """
        # Get model context window
        if model_name and model_name in DEFAULT_CONTEXT_WINDOWS:
            model_window = DEFAULT_CONTEXT_WINDOWS[model_name]
        else:
            model_window = self._config.model_context_window

        # Count system prompt or use default
        system_tokens = (
            self._token_counter.count(system_prompt).token_count
            if system_prompt
            else self._config.system_prompt_tokens
        )

        # Get reserve amount
        reserve = reserve_for_response or self._config.reserve_for_response

        available = model_window - system_tokens - reserve
        return max(0, available)


def create_context_window_manager(
    model_name: str | None = None,
    provider: LLMProvider = LLMProvider.OPENAI,
    enable_rag_optimization: bool = True,
) -> ContextWindowManager:
    """
    Factory function to create a configured ContextWindowManager.

    Args:
        model_name: Model name for context window size
        provider: LLM provider for token counting
        enable_rag_optimization: Whether to enable RAG chunk optimization

    Returns:
        Configured ContextWindowManager instance

    Example:
        >>> manager = create_context_window_manager(model_name="gpt-4o")
        >>> result = await manager.manage_context(system, chunks, history, query)
    """
    token_counter = TokenCounter(default_provider=provider)

    # Get model context window
    model_window = DEFAULT_CONTEXT_WINDOWS.get(model_name, 128000) if model_name else 128000

    config = ContextWindowConfig(
        model_context_window=model_window,
        enable_rag_optimization=enable_rag_optimization,
    )

    return ContextWindowManager(
        token_counter=token_counter,
        config=config,
    )


__all__ = [
    "ContextWindowManager",
    "ContextWindowConfig",
    "ManagedContext",
    "ChatMessage",
    "PruningStrategy",
    "create_context_window_manager",
    "DEFAULT_CONTEXT_WINDOWS",
]
