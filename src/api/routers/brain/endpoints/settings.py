"""
Brain Settings Endpoints

Settings CRUD endpoints for API keys, RAG configuration, and knowledge base status.
"""

from __future__ import annotations

import structlog

from fastapi import APIRouter, Depends, HTTPException

from src.api.routers.brain.core import get_fernet, mask_api_key, require_encryption
from src.api.routers.brain.dependencies import get_brain_settings_repository
from src.api.routers.brain.repositories.brain_settings import BrainSettingsRepository


from typing import Any
from src.api.schemas import (
    APIKeysRequest,
    APIKeysResponse,
    BrainSettingsResponse,
    KnowledgeBaseStatusResponse,
    RAGConfigRequest,
    RAGConfigResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["brain-settings"])


@router.get("/settings", response_model=BrainSettingsResponse)
async def get_brain_settings(
    repository: BrainSettingsRepository = Depends(get_brain_settings_repository),
    fernet=Depends(get_fernet),
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
                openai_key=mask_api_key(api_keys_dict["openai"]),
                anthropic_key=mask_api_key(api_keys_dict["anthropic"]),
                gemini_key=mask_api_key(api_keys_dict["gemini"]),
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


@router.get("/settings/api-keys", response_model=APIKeysResponse)
async def get_api_keys(
    repository: BrainSettingsRepository = Depends(get_brain_settings_repository),
    fernet=Depends(get_fernet),
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
            openai_key=mask_api_key(api_keys_dict["openai"]),
            anthropic_key=mask_api_key(api_keys_dict["anthropic"]),
            gemini_key=mask_api_key(api_keys_dict["gemini"]),
            ollama_base_url=ollama_url,
            has_openai=bool(api_keys_dict["openai"]),
            has_anthropic=bool(api_keys_dict["anthropic"]),
            has_gemini=bool(api_keys_dict["gemini"]),
        )

    except Exception as e:
        logger.error(f"Failed to get API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/settings/rag-config", response_model=RAGConfigResponse)
async def get_rag_config(
    repository: BrainSettingsRepository = Depends(get_brain_settings_repository),
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


@router.get("/settings/knowledge-base", response_model=KnowledgeBaseStatusResponse)
async def get_knowledge_base_status(
    repository: BrainSettingsRepository = Depends(get_brain_settings_repository),
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


@router.put("/settings/api-keys", response_model=APIKeysResponse)
async def update_api_keys(
    payload: APIKeysRequest,
    repository: BrainSettingsRepository = Depends(get_brain_settings_repository),
    fernet=Depends(get_fernet),
) -> APIKeysResponse:
    """
    Update API keys.

    OPT-014: Requires BRAIN_SETTINGS_ENCRYPTION_KEY to be set.

    Request Body:
        API keys to update (only provided keys are updated)

    Returns:
        Updated API keys (masked)

    Raises:
        400: If validation fails
        503: If encryption key is not configured
        500: If update fails
    """
    # OPT-014: Require encryption for storing API keys
    if (
        payload.openai_key is not None
        or payload.anthropic_key is not None
        or payload.gemini_key is not None
    ):
        require_encryption(fernet)

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
            openai_key=mask_api_key(api_keys_dict["openai"]),
            anthropic_key=mask_api_key(api_keys_dict["anthropic"]),
            gemini_key=mask_api_key(api_keys_dict["gemini"]),
            ollama_base_url=ollama_url,
            has_openai=bool(api_keys_dict["openai"]),
            has_anthropic=bool(api_keys_dict["anthropic"]),
            has_gemini=bool(api_keys_dict["gemini"]),
        )

    except Exception as e:
        logger.error(f"Failed to update API keys: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/settings/rag-config", response_model=RAGConfigResponse)
async def update_rag_config(
    payload: RAGConfigRequest,
    repository: BrainSettingsRepository = Depends(get_brain_settings_repository),
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


@router.post("/settings/test-connection", response_model=dict[str, str])
async def test_connection(
    repository: BrainSettingsRepository = Depends(get_brain_settings_repository),
    fernet=Depends(get_fernet),
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

        results: dict[Any, Any] = {}
        # For now, just check if keys are present
        # In production, make actual API calls to verify
        results["openai"] = (
            "configured" if api_keys_dict["openai"] else "not_configured"
        )
        results["anthropic"] = (
            "configured" if api_keys_dict["anthropic"] else "not_configured"
        )
        results["gemini"] = (
            "configured" if api_keys_dict["gemini"] else "not_configured"
        )

        return results

    except Exception as e:
        logger.error(f"Failed to test connections: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
