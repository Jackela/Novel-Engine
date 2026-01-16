#!/usr/bin/env python3
"""In-memory LLM provider for deterministic tests."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import uuid4

from ...domain.services.llm_provider import (
    ILLMProvider,
    LLMRequest,
    LLMResponse,
    LLMResponseStatus,
    LLMProviderError,
)
from ...domain.value_objects.common import ModelCapability, ModelId, ProviderId, ProviderType, TokenBudget


@dataclass
class MockCall:
    request: LLMRequest
    timestamp: float
    response: Optional[LLMResponse]


class MockLLMProvider(ILLMProvider):
    """Stateful fake LLM provider with call history."""

    def __init__(self) -> None:
        self._provider_id = ProviderId(
            provider_name="Mock LLM",
            provider_type=ProviderType.CUSTOM,
        )
        self._supported_models = [
            ModelId(
                model_name="mock-model",
                provider_id=self._provider_id,
                capabilities={
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CONVERSATION,
                    ModelCapability.ANALYSIS,
                },
                max_context_tokens=4096,
                max_output_tokens=1024,
            )
        ]
        self.calls: List[MockCall] = []
        self._responses: List[str] = []
        self._failure: Optional[Exception] = None
        self._delay_seconds: float = 0.0

    @property
    def provider_id(self) -> ProviderId:
        return self._provider_id

    @property
    def supported_models(self) -> List[ModelId]:
        return list(self._supported_models)

    @property
    def is_available(self) -> bool:
        return self._failure is None

    def set_responses(self, responses: List[str]) -> None:
        self._responses = list(responses)

    def set_failure(self, error: Optional[Exception]) -> None:
        self._failure = error

    def set_delay(self, seconds: float) -> None:
        self._delay_seconds = max(0.0, seconds)

    async def generate_async(
        self, request: LLMRequest, budget: Optional[TokenBudget] = None
    ) -> LLMResponse:
        if self._delay_seconds:
            await asyncio.sleep(self._delay_seconds)
        if self._failure:
            raise self._failure

        model = self.get_model_info(request.model_id.model_name)
        if model is None:
            raise LLMProviderError("Model unavailable")

        content = self._responses.pop(0) if self._responses else "mock-response"
        response = LLMResponse.create_success(
            request_id=request.request_id,
            content=content,
            model_id=model,
            input_tokens=self.estimate_tokens(request.prompt),
            output_tokens=self.estimate_tokens(content),
        )
        self.calls.append(MockCall(request=request, timestamp=time.time(), response=response))
        return response

    async def generate_stream_async(
        self, request: LLMRequest, budget: Optional[TokenBudget] = None
    ) -> AsyncIterator[str]:
        response = await self.generate_async(request, budget)
        for chunk in response.content.split():
            yield chunk + " "

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def validate_request(self, request: LLMRequest) -> bool:
        return request.is_compatible_with_model()

    def get_model_info(self, model_name: str) -> Optional[ModelId]:
        for model in self._supported_models:
            if model.model_name == model_name:
                return model
        return None

    async def health_check_async(self) -> Dict[str, Any]:
        return {
            "status": "healthy" if self.is_available else "unhealthy",
            "last_call_count": len(self.calls),
            "models_available": len(self._supported_models),
        }
