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

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Optional

from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

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


__all__ = ["router"]
