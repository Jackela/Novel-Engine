#!/usr/bin/env python3
"""
Cache Service Port for AI Gateway

Defines the abstract interface for caching LLM responses.
Infrastructure adapters implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ...domain.services.llm_provider import LLMRequest, LLMResponse


class ICacheService(ABC):
    """
    Abstract interface for AI Gateway caching service.

    Provides caching functionality for LLM responses to optimize
    performance and reduce API costs for repeated requests.
    """

    @abstractmethod
    async def get_async(self, request: LLMRequest) -> Optional[LLMResponse]:
        """
        Retrieve cached response for request.

        Args:
            request: LLM request to check for cached response

        Returns:
            Cached response if found and valid, None otherwise
        """

    @abstractmethod
    async def put_async(
        self, request: LLMRequest, response: LLMResponse, ttl_seconds: int = 3600
    ) -> None:
        """
        Cache response for request.

        Args:
            request: Original LLM request
            response: Response to cache
            ttl_seconds: Time-to-live in seconds (0 = no expiry)
        """

    @abstractmethod
    async def invalidate_async(self, request: LLMRequest) -> bool:
        """
        Remove cached entry for request.

        Args:
            request: Request whose cached response should be removed

        Returns:
            True if entry was found and removed, False otherwise
        """

    @abstractmethod
    async def clear_async(self) -> int:
        """
        Clear all cached entries.

        Returns:
            Number of entries cleared
        """

    @abstractmethod
    async def get_stats_async(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache performance metrics
        """
