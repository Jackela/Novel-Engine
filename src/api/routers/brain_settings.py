"""
Brain Settings Router

Warzone 4: AI Brain - BRAIN-033
REST API for managing Brain settings including API keys, RAG configuration,
and knowledge base status.

BRAIN-035A: Token usage analytics endpoint

Constitution Compliance:
- Article II (Hexagonal): Router handles HTTP, Service handles business logic
- Article I (DDD): No business logic in router layer
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional

from cryptography.fernet import Fernet
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from src.api.schemas import (
    APIKeysRequest,
    APIKeysResponse,
    BrainSettingsResponse,
    IngestionJobResponse,
    IngestionJobStatus,
    KnowledgeBaseStatusResponse,
    RAGConfigRequest,
    RAGConfigResponse,
    StartIngestionJobRequest,
    StartIngestionJobResponse,
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


# ==================== Token Usage Analytics (BRAIN-035A) ====================


def get_token_usage_repository(request: Request) -> "InMemoryTokenUsageRepository":
    """
    Get or create the token usage repository from app state.

    Why: Lazy initialization and singleton pattern for the repository.

    Args:
        request: FastAPI request object

    Returns:
        The token usage repository instance
    """
    repository = getattr(request.app.state, "token_usage_repository", None)
    if repository is None:
        repository = InMemoryTokenUsageRepository()
        request.app.state.token_usage_repository = repository
        # Seed with mock data for BRAIN-035A testing
        _seed_mock_data(repository)
        logger.info("Initialized InMemoryTokenUsageRepository with mock data")
    return repository


class InMemoryTokenUsageRepository:
    """
    In-memory repository for token usage analytics.

    Stores usage events for cost tracking and visualization.
    """

    def __init__(self) -> None:
        self._usages: list[dict] = []

    async def add_usage(self, usage: dict) -> None:
        """Add a usage event."""
        self._usages.append(usage)

    async def get_usages(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        provider: str | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        """Get usage events with optional filters."""
        filtered = self._usages

        if start_time:
            filtered = [u for u in filtered if datetime.fromisoformat(u["timestamp"]) >= start_time]
        if end_time:
            filtered = [u for u in filtered if datetime.fromisoformat(u["timestamp"]) <= end_time]
        if provider:
            filtered = [u for u in filtered if u["provider"] == provider]

        return filtered[-limit:]

    async def get_summary(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict:
        """Get aggregated usage summary."""
        usages = await self.get_usages(start_time, end_time)

        if not usages:
            return {
                "total_tokens": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost": 0.0,
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "avg_latency_ms": 0.0,
                "period_start": start_time.isoformat() if start_time else None,
                "period_end": end_time.isoformat() if end_time else None,
            }

        total_tokens = sum(u["total_tokens"] for u in usages)
        total_input = sum(u["input_tokens"] for u in usages)
        total_output = sum(u["output_tokens"] for u in usages)
        total_cost = sum(float(u.get("total_cost", 0)) for u in usages)
        total_latency = sum(u.get("latency_ms", 0) for u in usages)
        successful = sum(1 for u in usages if u.get("success", True))

        return {
            "total_tokens": total_tokens,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost": round(total_cost, 6),
            "total_requests": len(usages),
            "successful_requests": successful,
            "failed_requests": len(usages) - successful,
            "avg_latency_ms": round(total_latency / len(usages), 2) if usages else 0.0,
            "period_start": min(u["timestamp"] for u in usages),
            "period_end": max(u["timestamp"] for u in usages),
        }

    async def get_daily_stats(
        self,
        days: int = 30,
    ) -> list[dict]:
        """Get daily aggregated stats for the last N days."""
        now = datetime.now(UTC)
        daily_stats: dict[str, dict] = {}

        for i in range(days):
            date = (now - timedelta(days=days - i - 1)).date()
            date_str = date.isoformat()
            daily_stats[date_str] = {
                "date": date_str,
                "total_tokens": 0,
                "total_cost": 0.0,
                "total_requests": 0,
                "providers": {},
            }

        for usage in self._usages:
            timestamp = datetime.fromisoformat(usage["timestamp"])
            date_str = timestamp.date().isoformat()

            if date_str in daily_stats:
                daily_stats[date_str]["total_tokens"] += usage["total_tokens"]
                daily_stats[date_str]["total_cost"] += float(usage.get("total_cost", 0))
                daily_stats[date_str]["total_requests"] += 1

                provider = usage["provider"]
                if provider not in daily_stats[date_str]["providers"]:
                    daily_stats[date_str]["providers"][provider] = {
                        "tokens": 0,
                        "cost": 0.0,
                        "requests": 0,
                    }
                daily_stats[date_str]["providers"][provider]["tokens"] += usage["total_tokens"]
                daily_stats[date_str]["providers"][provider]["cost"] += float(usage.get("total_cost", 0))
                daily_stats[date_str]["providers"][provider]["requests"] += 1

        return list(daily_stats.values())

    async def get_model_breakdown(self) -> list[dict]:
        """Get cost breakdown by model."""
        model_stats: dict[str, dict] = {}

        for usage in self._usages:
            model = usage.get("model_identifier", f"{usage['provider']}:{usage['model_name']}")
            if model not in model_stats:
                model_stats[model] = {
                    "provider": usage["provider"],
                    "model_name": usage["model_name"],
                    "model_identifier": model,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "total_requests": 0,
                }
            model_stats[model]["total_tokens"] += usage["total_tokens"]
            model_stats[model]["total_cost"] += float(usage.get("total_cost", 0))
            model_stats[model]["total_requests"] += 1

        # Sort by cost descending
        return sorted(model_stats.values(), key=lambda x: x["total_cost"], reverse=True)


def _seed_mock_data(repository: InMemoryTokenUsageRepository) -> None:
    """Seed mock usage data for BRAIN-035A testing."""
    now = datetime.now(UTC)
    providers = ["openai", "anthropic", "gemini"]

    models = {
        "openai": ["gpt-4o", "gpt-4o-mini"],
        "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
        "gemini": ["gemini-2.0-flash", "gemini-2.5-pro"],
    }

    pricing = {
        "openai": {"gpt-4o": (5.0, 15.0), "gpt-4o-mini": (0.15, 0.6)},
        "anthropic": {"claude-3-5-sonnet-20241022": (3.0, 15.0), "claude-3-5-haiku-20241022": (0.8, 4.0)},
        "gemini": {"gemini-2.0-flash": (0.075, 0.3), "gemini-2.5-pro": (1.25, 10.0)},
    }

    # Generate 30 days of mock data
    for day in range(30):
        date = now - timedelta(days=30 - day)

        # 5-20 requests per day
        num_requests = 5 + (day * 7) % 16

        for _ in range(num_requests):
            provider = providers[day % 3]
            model_list = models[provider]
            model = model_list[(day + _) % len(model_list)]

            input_tokens = 500 + (_ * 200) % 2000
            output_tokens = 200 + (_ * 100) % 1000
            total_tokens = input_tokens + output_tokens

            cost_input, cost_output = pricing[provider][model]
            input_cost = input_tokens * cost_input / 1_000_000
            output_cost = output_tokens * cost_output / 1_000_000
            total_cost = input_cost + output_cost

            timestamp = date + timedelta(hours=_ % 24, minutes=(_ * 7) % 60)

            repository._usages.append(
                {
                    "id": f"mock-{day}-{_}",
                    "timestamp": timestamp.isoformat(),
                    "provider": provider,
                    "model_name": model,
                    "model_identifier": f"{provider}:{model}",
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "input_cost": str(Decimal(str(input_cost)).quantize(Decimal("0.000001"))),
                    "output_cost": str(Decimal(str(output_cost)).quantize(Decimal("0.000001"))),
                    "total_cost": str(Decimal(str(total_cost)).quantize(Decimal("0.000001"))),
                    "latency_ms": 500 + (_ * 50) % 2000,
                    "success": True,
                    "workspace_id": None,
                    "user_id": None,
                }
            )


@router.get("/brain/usage/summary")
async def get_usage_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to summarize"),
    repository: InMemoryTokenUsageRepository = Depends(get_token_usage_repository),
) -> dict:
    """
    Get token usage summary for the specified time period.

    Args:
        days: Number of days to look back (default: 30)

    Returns:
        Aggregated usage summary including tokens, costs, and request counts
    """
    try:
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        summary = await repository.get_summary(start_time, end_time)
        return summary

    except Exception as e:
        logger.error(f"Failed to get usage summary: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/brain/usage/daily")
async def get_daily_usage(
    days: int = Query(30, ge=1, le=365, description="Number of days to return"),
    repository: InMemoryTokenUsageRepository = Depends(get_token_usage_repository),
) -> list[dict]:
    """
    Get daily usage statistics over time.

    Args:
        days: Number of days to return (default: 30)

    Returns:
        List of daily stats with tokens, costs, and request counts
    """
    try:
        daily_stats = await repository.get_daily_stats(days)
        return daily_stats

    except Exception as e:
        logger.error(f"Failed to get daily usage: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/brain/usage/by-model")
async def get_usage_by_model(
    repository: InMemoryTokenUsageRepository = Depends(get_token_usage_repository),
) -> list[dict]:
    """
    Get usage breakdown by model.

    Returns:
        List of models with total tokens, costs, and request counts
    """
    try:
        model_breakdown = await repository.get_model_breakdown()
        return model_breakdown

    except Exception as e:
        logger.error(f"Failed to get usage by model: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Model Pricing (BRAIN-035B-01) ====================


class ModelPricingResponse(BaseModel):
    """
    Model pricing information response.

    Attributes:
        provider: LLM provider name
        model_name: Model identifier
        display_name: Human-readable model name
        cost_per_1m_input_tokens: Cost per 1M input tokens in USD
        cost_per_1m_output_tokens: Cost per 1M output tokens in USD
        max_context_tokens: Maximum input context window
        max_output_tokens: Maximum output tokens
        deprecated: Whether model is deprecated
    """

    provider: str
    model_name: str
    display_name: str
    cost_per_1m_input_tokens: float
    cost_per_1m_output_tokens: float
    max_context_tokens: int
    max_output_tokens: int
    deprecated: bool = False


@router.get("/brain/models", response_model=list[ModelPricingResponse])
async def get_model_pricing(
    include_deprecated: bool = Query(False, description="Include deprecated models"),
    provider: str | None = Query(None, description="Filter by provider"),
) -> list[ModelPricingResponse]:
    """
    Get model pricing information from the ModelRegistry.

    Returns:
        List of models with pricing data grouped by provider

    Raises:
        500: If retrieval fails
    """
    try:
        from src.contexts.knowledge.application.services.model_registry import (
            DEFAULT_MODELS,
            LLMProvider,
        )

        models: list[ModelPricingResponse] = []

        # Provider filter
        provider_filter = None
        if provider:
            try:
                provider_filter = LLMProvider(provider)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid provider: {provider}. Must be one of: {[p.value for p in LLMProvider]}",
                )

        for llm_provider, model_list in DEFAULT_MODELS.items():
            if provider_filter and llm_provider != provider_filter:
                continue

            for model_def in model_list:
                if not include_deprecated and model_def.deprecated:
                    continue

                models.append(
                    ModelPricingResponse(
                        provider=model_def.provider.value,
                        model_name=model_def.model_name,
                        display_name=model_def.display_name,
                        cost_per_1m_input_tokens=model_def.cost_per_1m_input_tokens,
                        cost_per_1m_output_tokens=model_def.cost_per_1m_output_tokens,
                        max_context_tokens=model_def.max_context_tokens,
                        max_output_tokens=model_def.max_output_tokens,
                        deprecated=model_def.deprecated,
                    )
                )

        # Sort by provider, then by cost (descending for comparison)
        models.sort(key=lambda m: (m.provider, -m.cost_per_1m_output_tokens))

        return models

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model pricing: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== CSV Export (BRAIN-035B-03) ====================


from fastapi.responses import Response


@router.get("/brain/usage/export")
async def export_usage_csv(
    days: int = Query(30, ge=1, le=365, description="Number of days to export"),
    repository: InMemoryTokenUsageRepository = Depends(get_token_usage_repository),
) -> Response:
    """
    Export usage data as CSV file.

    BRAIN-035B-03: CSV Export for usage analytics

    Args:
        days: Number of days to look back (default: 30)

    Returns:
        CSV file with usage data including timestamp, model, tokens, and cost
    """
    try:
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=days)

        # Get usage data
        usages = await repository.get_usages(start_time, end_time)

        # Build CSV content
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            "Timestamp",
            "Provider",
            "Model",
            "Input Tokens",
            "Output Tokens",
            "Total Tokens",
            "Input Cost",
            "Output Cost",
            "Total Cost",
            "Latency (ms)",
            "Success"
        ])

        # Write data rows
        for usage in usages:
            writer.writerow([
                usage["timestamp"],
                usage["provider"],
                usage["model_name"],
                usage["input_tokens"],
                usage["output_tokens"],
                usage["total_tokens"],
                usage.get("input_cost", "0"),
                usage.get("output_cost", "0"),
                usage.get("total_cost", "0"),
                usage.get("latency_ms", 0),
                usage.get("success", True),
            ])

        # Create response with CSV file
        csv_content = output.getvalue()
        filename = f"usage_export_{end_time.strftime('%Y%m%d_%H%M%S')}.csv"

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        logger.error(f"Failed to export usage CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Real-time Usage Streaming (BRAIN-035B-04) ====================


import asyncio
import json
from datetime import UTC, datetime
from typing import AsyncIterator


class RealtimeUsageBroadcaster:
    """
    Broadcasts real-time token usage events to connected clients.

    Why:
        - Enables live token counting during LLM generation
        - Supports multiple concurrent clients via fan-out pattern
        - Session-based tracking isolates users' active generations

    Attributes:
        _active_sessions: Dict of session_id -> current usage tracking
        _subscribers: Dict of queue -> set of session_ids to watch
        _lock: Async lock for thread-safe operations
    """

    def __init__(self) -> None:
        self._active_sessions: dict[str, dict] = {}
        self._subscribers: dict[asyncio.Queue, set[str]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def start_session(
        self,
        session_id: str,
        provider: str,
        model_name: str,
    ) -> None:
        """Start tracking a new generation session."""
        async with self._lock:
            self._active_sessions[session_id] = {
                "provider": provider,
                "model_name": model_name,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "start_time": datetime.now(UTC).isoformat(),
                "is_complete": False,
            }
            # Broadcast session start
            await self._broadcast_to_all({
                "type": "session_start",
                "session_id": session_id,
                "provider": provider,
                "model_name": model_name,
                "timestamp": datetime.now(UTC).isoformat(),
            })

    async def update_session(
        self,
        session_id: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
    ) -> None:
        """Update a session with new token usage."""
        async with self._lock:
            if session_id not in self._active_sessions:
                return

            session = self._active_sessions[session_id]
            session["input_tokens"] = input_tokens
            session["output_tokens"] = output_tokens
            session["total_tokens"] = input_tokens + output_tokens
            session["cost"] = cost

            # Broadcast update
            await self._broadcast_to_all({
                "type": "token_update",
                "session_id": session_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost": cost,
                "timestamp": datetime.now(UTC).isoformat(),
            })

    async def complete_session(self, session_id: str) -> None:
        """Mark a session as complete."""
        async with self._lock:
            if session_id not in self._active_sessions:
                return

            self._active_sessions[session_id]["is_complete"] = True
            session = self._active_sessions[session_id]

            # Broadcast completion
            await self._broadcast_to_all({
                "type": "session_complete",
                "session_id": session_id,
                **session,
                "timestamp": datetime.now(UTC).isoformat(),
            })

            # Remove session after a delay
            asyncio.create_task(self._cleanup_session(session_id))

    async def _cleanup_session(self, session_id: str) -> None:
        """Remove a session after a delay."""
        await asyncio.sleep(60)  # Keep for 1 minute after completion
        async with self._lock:
            self._active_sessions.pop(session_id, None)

    async def _broadcast_to_all(self, event: dict) -> None:
        """Broadcast an event to all subscribers."""
        for queue in list(self._subscribers.keys()):
            try:
                await queue.put(event)
            except Exception:
                # Remove dead queue
                self._subscribers.pop(queue, None)

    async def subscribe(self) -> AsyncIterator[dict]:
        """Subscribe to real-time usage events."""
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._subscribers[queue] = set()

            # Send current state
            for session_id, session in self._active_sessions.items():
                await queue.put({
                    "type": "session_state",
                    "session_id": session_id,
                    **session,
                    "timestamp": datetime.now(UTC).isoformat(),
                })

        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                self._subscribers.pop(queue, None)


# Global broadcaster instance
_usage_broadcaster = RealtimeUsageBroadcaster()


def get_usage_broadcaster() -> RealtimeUsageBroadcaster:
    """Get the global usage broadcaster instance."""
    return _usage_broadcaster


@router.get("/brain/usage/stream")
async def stream_realtime_usage(
    broadcaster: RealtimeUsageBroadcaster = Depends(get_usage_broadcaster),
) -> StreamingResponse:
    """
    Stream real-time token usage events via SSE.

    BRAIN-035B-04: Real-time Usage Counter

    Returns Server-Sent Events stream with:
        - session_start: New generation session started
        - token_update: Live token count updates
        - session_complete: Generation finished
        - session_state: Current state of active sessions

    Example:
        ```javascript
        const eventSource = new EventSource('/api/brain/usage/stream');
        eventSource.onmessage = (e) => {
            const event = JSON.parse(e.data);
            console.log(event.type, event);
        };
        ```
    """
    async def _sse_generator() -> AsyncIterator[str]:
        """Generate SSE events for real-time usage."""
        try:
            async for event in broadcaster.subscribe():
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            logger.debug("SSE stream cancelled")
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== Async Ingestion Job API (OPT-005) ====================


import asyncio
import uuid
from datetime import UTC, datetime
from enum import Enum

from fastapi import BackgroundTasks, HTTPException
from src.api.schemas import (
    IngestionJobStatus,
    IngestionJobResponse,
    StartIngestionJobRequest,
    StartIngestionJobResponse,
)
from src.contexts.knowledge.application.services.knowledge_ingestion_service import (
    IngestionResult,
    KnowledgeIngestionService,
)


class IngestionJob:
    """
    An async ingestion job.

    Attributes:
        job_id: Unique identifier for the job
        status: Current job status
        progress: Progress percentage (0-100)
        source_id: ID of the source being ingested
        source_type: Type of source
        content: Content to ingest
        tags: Optional tags
        extra_metadata: Optional additional metadata
        created_at: When the job was created
        started_at: When the job started processing
        completed_at: When the job completed
        error: Error message if job failed
        chunk_count: Number of chunks created
        entries_created: Number of entries created
    """

    def __init__(
        self,
        job_id: str,
        source_id: str,
        source_type: str,
        content: str,
        tags: list[str] | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ):
        self.job_id = job_id
        self.status = IngestionJobStatus.PENDING
        self.progress = 0.0
        self.source_id = source_id
        self.source_type = source_type
        self.content = content
        self.tags = tags
        self.extra_metadata = extra_metadata
        self.created_at = datetime.now(UTC)
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.error: str | None = None
        self.chunk_count: int | None = None
        self.entries_created: int | None = None

    def to_response(self) -> IngestionJobResponse:
        """Convert to API response model."""
        return IngestionJobResponse(
            job_id=self.job_id,
            status=self.status,
            progress=self.progress,
            source_id=self.source_id,
            source_type=self.source_type,
            created_at=self.created_at.isoformat(),
            started_at=self.started_at.isoformat() if self.started_at else None,
            completed_at=self.completed_at.isoformat() if self.completed_at else None,
            error=self.error,
            chunk_count=self.chunk_count,
            entries_created=self.entries_created,
        )


class IngestionJobStore:
    """
    In-memory store for async ingestion jobs.

    Why:
        - Track job status across async operations
        - Allow clients to poll for status updates
        - Simple implementation for now; can be replaced with Redis/DB later
    """

    def __init__(self) -> None:
        self._jobs: dict[str, IngestionJob] = {}
        self._lock = asyncio.Lock()

    async def create_job(
        self,
        source_id: str,
        source_type: str,
        content: str,
        tags: list[str] | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> IngestionJob:
        """Create a new ingestion job."""
        job_id = str(uuid.uuid4())
        job = IngestionJob(
            job_id=job_id,
            source_id=source_id,
            source_type=source_type,
            content=content,
            tags=tags,
            extra_metadata=extra_metadata,
        )

        async with self._lock:
            self._jobs[job_id] = job

        logger.info(f"ingestion_job_created: job_id={job_id}, source_id={source_id}, source_type={source_type}")

        return job

    async def get_job(self, job_id: str) -> IngestionJob | None:
        """Get a job by ID."""
        async with self._lock:
            return self._jobs.get(job_id)

    async def update_job(
        self,
        job_id: str,
        status: IngestionJobStatus | None = None,
        progress: float | None = None,
        error: str | None = None,
        chunk_count: int | None = None,
        entries_created: int | None = None,
    ) -> IngestionJob | None:
        """Update job status."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None

            if status is not None:
                job.status = status
                if status == IngestionJobStatus.RUNNING and job.started_at is None:
                    job.started_at = datetime.now(UTC)
                elif status in (IngestionJobStatus.COMPLETED, IngestionJobStatus.FAILED, IngestionJobStatus.CANCELLED):
                    if job.completed_at is None:
                        job.completed_at = datetime.now(UTC)

            if progress is not None:
                job.progress = progress

            if error is not None:
                job.error = error

            if chunk_count is not None:
                job.chunk_count = chunk_count

            if entries_created is not None:
                job.entries_created = entries_created

            return job

    async def list_jobs(self, limit: int = 100) -> list[IngestionJob]:
        """List all jobs, most recent first."""
        async with self._lock:
            jobs = list(self._jobs.values())
            jobs.sort(key=lambda j: j.created_at, reverse=True)
            return jobs[:limit]


# Global job store instance
_ingestion_job_store = IngestionJobStore()


def get_ingestion_job_store(request: Request) -> IngestionJobStore:
    """
    Get the ingestion job store from app state.

    Why: Dependency injection for testability.

    Args:
        request: FastAPI request object

    Returns:
        The ingestion job store instance
    """
    store = getattr(request.app.state, "ingestion_job_store", None)
    if store is None:
        store = IngestionJobStore()
        request.app.state.ingestion_job_store = store
        logger.info("Initialized IngestionJobStore")
    return store


def get_ingestion_service(request: Request) -> KnowledgeIngestionService:
    """
    Get or create the ingestion service from app state.

    Args:
        request: FastAPI request object

    Returns:
        The knowledge ingestion service instance
    """
    from src.contexts.knowledge.infrastructure.adapters.chromadb_vector_store import (
        ChromaDBVectorStore,
    )
    from src.contexts.knowledge.infrastructure.adapters.embedding_generator_adapter import (
        EmbeddingServiceAdapter,
    )

    service = getattr(request.app.state, "ingestion_service", None)
    if service is None:
        # Create dependencies
        embedding_service = EmbeddingServiceAdapter(use_mock=True)
        vector_store = ChromaDBVectorStore()

        # Create service
        service = KnowledgeIngestionService(
            embedding_service=embedding_service,
            vector_store=vector_store,
        )
        request.app.state.ingestion_service = service
        logger.info("Initialized KnowledgeIngestionService for async jobs")

    return service


async def _run_ingestion_job(
    job_id: str,
    store: IngestionJobStore,
    service: KnowledgeIngestionService,
) -> None:
    """
    Background worker that executes an ingestion job.

    Args:
        job_id: ID of the job to execute
        store: Job store for updates
        service: Ingestion service for processing
    """
    job = await store.get_job(job_id)
    if job is None:
        logger.warning(f"ingestion_job_not_found: job_id={job_id}")
        return

    try:
        # Update to running
        await store.update_job(job_id, status=IngestionJobStatus.RUNNING, progress=10.0)

        # Execute ingestion
        result: IngestionResult = await service.ingest(
            content=job.content,
            source_type=job.source_type,
            source_id=job.source_id,
            tags=job.tags,
            extra_metadata=job.extra_metadata,
        )

        # Update to completed
        await store.update_job(
            job_id,
            status=IngestionJobStatus.COMPLETED,
            progress=100.0,
            chunk_count=result.chunk_count,
            entries_created=result.entries_created,
        )

        logger.info(f"ingestion_job_completed: job_id={job_id}, source_id={job.source_id}, chunk_count={result.chunk_count}")

    except Exception as e:
        # Update to failed
        error_msg = f"{type(e).__name__}: {e}"
        await store.update_job(
            job_id,
            status=IngestionJobStatus.FAILED,
            error=error_msg,
        )

        logger.error(f"ingestion_job_failed: job_id={job_id}, source_id={job.source_id}, error={error_msg}")


@router.post(
    "/brain/ingestion",
    status_code=202,
    response_model=StartIngestionJobResponse,
)
async def start_ingestion_job(
    request: Request,
    payload: StartIngestionJobRequest,
    background_tasks: BackgroundTasks,
    store: IngestionJobStore = Depends(get_ingestion_job_store),
    service: KnowledgeIngestionService = Depends(get_ingestion_service),
) -> StartIngestionJobResponse:
    """
    Start an async ingestion job.

    OPT-005: Async Ingestion Job API

    Args:
        payload: Ingestion job request

    Returns:
        202 Accepted with job_id for tracking

    Raises:
        400: If validation fails
        500: If job creation fails
    """
    try:
        # Validate input
        if not payload.content or not payload.content.strip():
            raise HTTPException(status_code=400, detail="content cannot be empty")

        if not payload.source_id or not payload.source_id.strip():
            raise HTTPException(status_code=400, detail="source_id cannot be empty")

        # Create job
        job = await store.create_job(
            source_id=payload.source_id,
            source_type=payload.source_type,
            content=payload.content,
            tags=payload.tags,
            extra_metadata=payload.extra_metadata,
        )

        # Queue background work
        background_tasks.add_task(_run_ingestion_job, job.job_id, store, service)

        return StartIngestionJobResponse(
            job_id=job.job_id,
            status=job.status,
            message="Ingestion job started. Poll /api/brain/ingestion/{job_id} for status.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start ingestion job: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/brain/ingestion/{job_id}",
    response_model=IngestionJobResponse,
)
async def get_ingestion_job_status(
    job_id: str,
    store: IngestionJobStore = Depends(get_ingestion_job_store),
) -> IngestionJobResponse:
    """
    Get the status of an async ingestion job.

    OPT-005: Async Ingestion Job API

    Args:
        job_id: ID of the job to query

    Returns:
        Current job status with progress and results

    Raises:
        404: If job not found
        500: If retrieval fails
    """
    try:
        job = await store.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        return job.to_response()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get ingestion job status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/brain/ingestion",
    response_model=List[IngestionJobResponse],
)
async def list_ingestion_jobs(
    request: Request,
    limit: int = 100,
) -> List[IngestionJobResponse]:
    """
    List all ingestion jobs, most recent first.

    OPT-005: Async Ingestion Job API

    Args:
        limit: Maximum number of jobs to return (default: 100)

    Returns:
        List of job status responses
    """
    try:
        store = get_ingestion_job_store(request)
        jobs = await store.list_jobs(limit)
        return [job.to_response() for job in jobs]

    except Exception as e:
        logger.error(f"Failed to list ingestion jobs: {e}")
        return []


__all__ = ["router", "RealtimeUsageBroadcaster", "get_usage_broadcaster", "IngestionJobStore", "get_ingestion_job_store"]


# ==================== RAG Context Retrieval (BRAIN-036-02) ====================


from fastapi.responses import StreamingResponse
from src.api.schemas import RAGContextResponse, RetrievedChunkResponse


@router.get("/brain/context", response_model=RAGContextResponse)
async def get_rag_context(
    request: Request,
    query: str = Query(..., description="Query to retrieve context for"),
    scene_id: str | None = Query(None, description="Scene ID to get context for"),
    max_chunks: int = Query(5, ge=1, le=20, description="Maximum chunks to retrieve"),
    used_threshold: float = Query(0.7, ge=0, le=1, description="Score threshold to mark chunk as used"),
    repository: InMemoryBrainSettingsRepository = Depends(get_brain_settings_repository),
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
            embedding_service = EmbeddingServiceAdapter(use_mock=True)  # Use mock for now
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
            token_result = token_counter.count(chunk.content)
            token_count = token_result.token_count

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
        source_refs = [
            f"{s['source_type']}:{s['source_id']}" for s in sources
        ]

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


# ==================== Chat Endpoint (BRAIN-037A-01) ====================


import json
import asyncio
from typing import AsyncIterator


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str  # "user" or "assistant"
    content: str


def get_context_window_manager(request: Request) -> "ContextWindowManager":
    """
    Get or create the context window manager from app state.

    OPT-009: Context Window Manager integration

    Args:
        request: FastAPI request object

    Returns:
        The context window manager instance
    """
    from src.contexts.knowledge.application.services.context_window_manager import (
        create_context_window_manager,
    )

    manager = getattr(request.app.state, "context_window_manager", None)
    if manager is None:
        manager = create_context_window_manager(
            model_name="gpt-4o",
            enable_rag_optimization=True,
        )
        request.app.state.context_window_manager = manager
        logger.info("Initialized ContextWindowManager")

    return manager


class ChatRequest(BaseModel):
    """Request for chat completion."""
    query: str  # User's question/prompt
    chat_history: list[ChatMessage] | None = None  # Optional conversation history
    scene_id: str | None = None  # Optional scene ID for context
    max_chunks: int = 5  # Maximum chunks to retrieve for RAG
    session_id: str | None = None  # BRAIN-037A-03: Optional session ID for conversation tracking


# BRAIN-037A-03: In-memory session storage for chat history
class ChatSessionStore:
    """In-memory store for chat sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[ChatMessage]] = {}

    def get_session(self, session_id: str) -> list[ChatMessage]:
        """Get chat history for a session."""
        return self._sessions.get(session_id, [])

    def add_message(self, session_id: str, message: ChatMessage) -> None:
        """Add a message to a session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append(message)

    def clear_session(self, session_id: str) -> None:
        """Clear chat history for a session."""
        self._sessions.pop(session_id, None)


# Global session store
_chat_session_store = ChatSessionStore()


class ChatChunk(BaseModel):
    """A single chunk of streaming response."""
    delta: str  # Text content added
    done: bool = False  # Whether this is the final chunk


@router.post("/brain/chat")
async def chat_completion(
    request: Request,
    payload: ChatRequest,
    repository: InMemoryBrainSettingsRepository = Depends(get_brain_settings_repository),
    context_manager: "ContextWindowManager" = Depends(get_context_window_manager),
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
            rag_query = payload.query
            if chat_history and len(chat_history) > 0:
                # Include last assistant response for context
                last_assistant_msg = next((m for m in reversed(chat_history) if m.role == "assistant"), None)
                if last_assistant_msg:
                    rag_query = f"{last_assistant_msg.content}\n\nUser: {payload.query}"

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
                    embedding_service = getattr(request.app.state, "embedding_service", None)
                    if embedding_service is None:
                        embedding_service = EmbeddingServiceAdapter(use_mock=True)
                        request.app.state.embedding_service = embedding_service

                    vector_store = getattr(request.app.state, "vector_store", None)
                    if vector_store is None:
                        vector_store = ChromaDBVectorStore()
                        request.app.state.vector_store = vector_store

                    # Retrieve relevant chunks
                    retrieval_service = RetrievalService(
                        embedding_service=embedding_service,
                        vector_store=vector_store,
                    )

                    result = await retrieval_service.retrieve_relevant(
                        query=payload.query,
                        k=payload.max_chunks,
                        filters=None,
                    )
                    rag_chunks = result.chunks

                except Exception as e:
                    logger.warning(f"RAG retrieval failed, continuing without context: {e}")

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
                context_parts = []
                for i, chunk in enumerate(rag_chunks, 1):
                    context_parts.append(f"[Source {i}: {chunk.source_type}:{chunk.source_id}]")
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

            # Get formatted messages for LLM
            messages = managed_context.to_api_messages()
            # Add current query (already included in managed_context.chat_history)

            # For now, return a mock streaming response
            # In a full implementation, this would call an LLM service
            response_text = f"I received your question: \"{payload.query}\""

            if rag_chunks:
                response_text += f"\n\nI found {len(rag_chunks)} relevant chunks from the knowledge base."
            else:
                response_text += "\n\nNo relevant context was found in the knowledge base."

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
