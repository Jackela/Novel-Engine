"""
Brain Settings Repository

In-memory repository for brain settings.
Stores API keys (encrypted), RAG configuration, and knowledge base status.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.api.routers.brain.core import decrypt_api_key, encrypt_api_key

if TYPE_CHECKING:
    from cryptography.fernet import Fernet


class InMemoryBrainSettingsRepository:
    """
    In-memory repository for brain settings.

    Stores API keys (encrypted), RAG configuration, and knowledge base status.
    """

    def __init__(self) -> None:
        self._api_keys: dict[str, str] = {}
        self._ollama_base_url: str = "http://localhost:11434"
        self._rag_config: dict = {
            "enabled": True,
            "max_chunks": 5,
            "score_threshold": 0.0,
            "context_token_limit": 4000,
            "include_sources": True,
            "chunk_size": 500,
            "chunk_overlap": 50,
            "hybrid_search_weight": 0.7,
        }
        self._kb_status: dict = {
            "total_entries": 0,
            "characters_count": 0,
            "lore_count": 0,
            "scenes_count": 0,
            "plotlines_count": 0,
            "last_sync": None,
            "is_healthy": True,
        }

    async def get_api_keys(self, fernet: Fernet | None) -> dict[str, str]:
        """
        Get all API keys (decrypted).

        OPT-014: Returns empty strings if decryption fails.

        Args:
            fernet: Fernet encryptor instance (may be None)

        Returns:
            Dictionary with decrypted API keys
        """
        return {
            "openai": decrypt_api_key(self._api_keys.get("openai", ""), fernet),
            "anthropic": decrypt_api_key(self._api_keys.get("anthropic", ""), fernet),
            "gemini": decrypt_api_key(self._api_keys.get("gemini", ""), fernet),
        }

    async def set_api_key(self, provider: str, key: str, fernet: Fernet | None) -> None:
        """
        Set an API key (encrypted).

        OPT-014: If encryption fails, key is not stored.

        Args:
            provider: The API provider name
            key: The API key to store
            fernet: Fernet encryptor instance (may be None)
        """
        if key:
            encrypted = encrypt_api_key(key, fernet)
            # OPT-014: Only store if encryption succeeded (non-empty result)
            if encrypted:
                self._api_keys[provider] = encrypted
        elif provider in self._api_keys:
            del self._api_keys[provider]

    async def get_ollama_base_url(self) -> str:
        """Get Ollama base URL."""
        return self._ollama_base_url

    async def set_ollama_base_url(self, url: str) -> None:
        """Set Ollama base URL."""
        self._ollama_base_url = url or "http://localhost:11434"

    async def get_rag_config(self) -> dict:
        """Get RAG configuration."""
        return self._rag_config.copy()

    async def update_rag_config(self, updates: dict) -> dict:
        """Update RAG configuration."""
        for key, value in updates.items():
            if value is not None and key in self._rag_config:
                self._rag_config[key] = value
        return self._rag_config.copy()

    async def get_kb_status(self) -> dict:
        """Get knowledge base status."""
        return self._kb_status.copy()

    async def update_kb_status(self, updates: dict) -> dict:
        """Update knowledge base status."""
        self._kb_status.update(updates)
        return self._kb_status.copy()


# Type alias for dependency injection
BrainSettingsRepository = InMemoryBrainSettingsRepository

__all__ = ["InMemoryBrainSettingsRepository", "BrainSettingsRepository"]
