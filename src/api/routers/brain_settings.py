"""
Brain Settings Router

Warzone 4: AI Brain - BRAIN-033
REST API for managing Brain settings including API keys, RAG configuration,
and knowledge base status.

Constitution Compliance:
- Article II (Hexagonal): Router handles HTTP, Service handles business logic
- Article I (DDD): No business logic in router layer
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Optional

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.schemas import (
    APIKeysRequest,
    APIKeysResponse,
    BrainSettingsResponse,
    KnowledgeBaseStatusResponse,
    RAGConfigRequest,
    RAGConfigResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["brain-settings"])

# Encryption key for API keys (in production, use environment variable)
# For now, we generate a key per server restart (keys persist encrypted)
_DEFAULT_ENCRYPTION_KEY = Fernet.generate_key()
_fernet = Fernet(_DEFAULT_ENCRYPTION_KEY)


def get_encryption_key() -> bytes:
    """
    Get the encryption key for API keys.

    Why: Dependency injection for testability.

    Returns:
        The encryption key as bytes
    """
    import os

    key = os.getenv("BRAIN_SETTINGS_ENCRYPTION_KEY")
    if key:
        return key.encode() if isinstance(key, str) else key
    return _DEFAULT_ENCRYPTION_KEY


def get_fernet() -> Fernet:
    """
    Get the Fernet encryptor for API keys.

    Returns:
        Fernet encryptor instance
    """
    key = get_encryption_key()
    return Fernet(key)


def get_brain_settings_repository(request: Request) -> "BrainSettingsRepository":
    """
    Get or create the brain settings repository from app state.

    Why: Lazy initialization and singleton pattern for the repository.

    Args:
        request: FastAPI request object

    Returns:
        The brain settings repository instance
    """
    repository = getattr(request.app.state, "brain_settings_repository", None)
    if repository is None:
        repository = InMemoryBrainSettingsRepository()
        request.app.state.brain_settings_repository = repository
        logger.info("Initialized InMemoryBrainSettingsRepository")
    return repository


def _encrypt_api_key(key: str, fernet: Fernet) -> str:
    """Encrypt an API key."""
    if not key:
        return ""
    return fernet.encrypt(key.encode()).decode()


def _decrypt_api_key(encrypted: str, fernet: Fernet) -> str:
    """Decrypt an API key."""
    if not encrypted:
        return ""
    try:
        return fernet.decrypt(encrypted.encode()).decode()
    except Exception:
        return ""


def _mask_api_key(key: str) -> str:
    """Mask an API key for display (show first 8 and last 4 chars)."""
    if not key or len(key) < 12:
        return "•" * 20 if key else ""
    return f"{key[:8]}{'•' * (len(key) - 12)}{key[-4:]}"


# ==================== Repository ====================


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

    async def get_api_keys(self, fernet: Fernet) -> dict[str, str]:
        """Get all API keys (decrypted)."""
        return {
            "openai": _decrypt_api_key(self._api_keys.get("openai", ""), fernet),
            "anthropic": _decrypt_api_key(self._api_keys.get("anthropic", ""), fernet),
            "gemini": _decrypt_api_key(self._api_keys.get("gemini", ""), fernet),
        }

    async def set_api_key(
        self, provider: str, key: str, fernet: Fernet
    ) -> None:
        """Set an API key (encrypted)."""
        if key:
            self._api_keys[provider] = _encrypt_api_key(key, fernet)
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


# ==================== Query Endpoints ====================


@router.get("/brain/settings", response_model=BrainSettingsResponse)
async def get_brain_settings(
    repository: InMemoryBrainSettingsRepository = Depends(get_brain_settings_repository),
    fernet: Fernet = Depends(get_fernet),
) -> BrainSettingsResponse:
    """
    Get all brain settings.

    Returns:
        Combined brain settings including API keys, RAG config, and KB status

    Raises:
        500: If retrieval fails
    """
    try:
        # Get API keys
        api_keys_dict = await repository.get_api_keys(fernet)
        ollama_url = await repository.get_ollama_base_url()

        # Get RAG config
        rag_dict = await repository.get_rag_config()

        # Get KB status
        kb_dict = await repository.get_kb_status()

        return BrainSettingsResponse(
            api_keys=APIKeysResponse(
                openai_key=_mask_api_key(api_keys_dict["openai"]),
                anthropic_key=_mask_api_key(api_keys_dict["anthropic"]),
                gemini_key=_mask_api_key(api_keys_dict["gemini"]),
                ollama_base_url=ollama_url,
                has_openai=bool(api_keys_dict["openai"]),
                has_anthropic=bool(api_keys_dict["anthropic"]),
                has_gemini=bool(api_keys_dict["gemini"]),
            ),
            rag_config=RAGConfigResponse(**rag_dict),
            knowledge_base=KnowledgeBaseStatusResponse(**kb_dict),
        )

    except Exception as e:
        logger.error(f"Failed to get brain settings: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/brain/settings/api-keys", response_model=APIKeysResponse)
async def get_api_keys(
    repository: InMemoryBrainSettingsRepository = Depends(get_brain_settings_repository),
    fernet: Fernet = Depends(get_fernet),
) -> APIKeysResponse:
    """
    Get API keys (masked).

    Returns:
        API keys with masked values

    Raises:
        500: If retrieval fails
    """
    try:
        api_keys_dict = await repository.get_api_keys(fernet)
        ollama_url = await repository.get_ollama_base_url()

        return APIKeysResponse(
            openai_key=_mask_api_key(api_keys_dict["openai"]),
            anthropic_key=_mask_api_key(api_keys_dict["anthropic"]),
            gemini_key=_mask_api_key(api_keys_dict["gemini"]),
            ollama_base_url=ollama_url,
            has_openai=bool(api_keys_dict["openai"]),
            has_anthropic=bool(api_keys_dict["anthropic"]),
            has_gemini=bool(api_keys_dict["gemini"]),
        )

    except Exception as e:
        logger.error(f"Failed to get API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/brain/settings/rag-config", response_model=RAGConfigResponse)
async def get_rag_config(
    repository: InMemoryBrainSettingsRepository = Depends(get_brain_settings_repository),
) -> RAGConfigResponse:
    """
    Get RAG configuration.

    Returns:
        Current RAG configuration

    Raises:
        500: If retrieval fails
    """
    try:
        rag_dict = await repository.get_rag_config()
        return RAGConfigResponse(**rag_dict)

    except Exception as e:
        logger.error(f"Failed to get RAG config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/brain/settings/knowledge-base", response_model=KnowledgeBaseStatusResponse)
async def get_knowledge_base_status(
    repository: InMemoryBrainSettingsRepository = Depends(get_brain_settings_repository),
) -> KnowledgeBaseStatusResponse:
    """
    Get knowledge base status.

    Returns:
        Current knowledge base status

    Raises:
        500: If retrieval fails
    """
    try:
        kb_dict = await repository.get_kb_status()
        return KnowledgeBaseStatusResponse(**kb_dict)

    except Exception as e:
        logger.error(f"Failed to get KB status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Mutation Endpoints ====================


@router.put("/brain/settings/api-keys", response_model=APIKeysResponse)
async def update_api_keys(
    payload: APIKeysRequest,
    repository: InMemoryBrainSettingsRepository = Depends(get_brain_settings_repository),
    fernet: Fernet = Depends(get_fernet),
) -> APIKeysResponse:
    """
    Update API keys.

    Request Body:
        API keys to update (only provided keys are updated)

    Returns:
        Updated API keys (masked)

    Raises:
        400: If validation fails
        500: If update fails
    """
    try:
        if payload.openai_key is not None:
            await repository.set_api_key("openai", payload.openai_key, fernet)
        if payload.anthropic_key is not None:
            await repository.set_api_key("anthropic", payload.anthropic_key, fernet)
        if payload.gemini_key is not None:
            await repository.set_api_key("gemini", payload.gemini_key, fernet)
        if payload.ollama_base_url is not None:
            await repository.set_ollama_base_url(payload.ollama_base_url)

        # Return updated keys
        api_keys_dict = await repository.get_api_keys(fernet)
        ollama_url = await repository.get_ollama_base_url()

        return APIKeysResponse(
            openai_key=_mask_api_key(api_keys_dict["openai"]),
            anthropic_key=_mask_api_key(api_keys_dict["anthropic"]),
            gemini_key=_mask_api_key(api_keys_dict["gemini"]),
            ollama_base_url=ollama_url,
            has_openai=bool(api_keys_dict["openai"]),
            has_anthropic=bool(api_keys_dict["anthropic"]),
            has_gemini=bool(api_keys_dict["gemini"]),
        )

    except Exception as e:
        logger.error(f"Failed to update API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/brain/settings/rag-config", response_model=RAGConfigResponse)
async def update_rag_config(
    payload: RAGConfigRequest,
    repository: InMemoryBrainSettingsRepository = Depends(get_brain_settings_repository),
) -> RAGConfigResponse:
    """
    Update RAG configuration.

    Request Body:
        RAG settings to update (only provided fields are updated)

    Returns:
        Updated RAG configuration

    Raises:
        400: If validation fails
        500: If update fails
    """
    try:
        updates = payload.model_dump(exclude_unset=True)
        updated = await repository.update_rag_config(updates)
        return RAGConfigResponse(**updated)

    except Exception as e:
        logger.error(f"Failed to update RAG config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/brain/settings/test-connection", response_model=dict[str, str])
async def test_connection(
    repository: InMemoryBrainSettingsRepository = Depends(get_brain_settings_repository),
    fernet: Fernet = Depends(get_fernet),
) -> dict[str, str]:
    """
    Test API key connections.

    Returns:
        Status of each provider connection

    Raises:
        500: If test fails
    """
    try:
        api_keys_dict = await repository.get_api_keys(fernet)

        results = {}
        # For now, just check if keys are present
        # In production, make actual API calls to verify
        results["openai"] = "configured" if api_keys_dict["openai"] else "not_configured"
        results["anthropic"] = "configured" if api_keys_dict["anthropic"] else "not_configured"
        results["gemini"] = "configured" if api_keys_dict["gemini"] else "not_configured"

        return results

    except Exception as e:
        logger.error(f"Failed to test connections: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


__all__ = ["router"]
