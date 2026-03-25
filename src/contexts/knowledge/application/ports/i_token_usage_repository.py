"""
Token Usage Repository Port

Defines the interface for token usage repository implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class TokenUsage:
    """Token usage record."""

    id: str
    user_id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    timestamp: datetime
    metadata: dict[str, Any]


class ITokenUsageRepository(ABC):
    """Abstract interface for token usage repository."""

    @abstractmethod
    async def save(self, usage: TokenUsage) -> None:
        """Save token usage record."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_user_id(self, user_id: str, limit: int = 100) -> list[TokenUsage]:
        """Get token usage records for a user."""
        raise NotImplementedError

    @abstractmethod
    async def get_total_usage(
        self,
        user_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """Get total token usage for a user."""
        raise NotImplementedError
