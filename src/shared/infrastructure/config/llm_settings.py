from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

from src.shared.infrastructure.config.settings_base import _settings_config

__all__ = ["LLMSettings"]


class LLMSettings(BaseSettings):
    model_config = _settings_config(env_prefix="LLM_")

    provider: Literal["mock", "dashscope", "openai_compatible"] = Field(
        default="mock",
        description="LLM provider name",
    )
    model: str = Field(default="studio-copilot-v1", description="LLM model name")
    api_key: str | None = Field(
        default=None,
        description="API key for OpenAI-compatible providers",
        validation_alias=AliasChoices("LLM_API_KEY", "OPENAI_API_KEY"),
    )
    api_base: str | None = Field(
        default=None,
        description="Custom API base URL",
        validation_alias=AliasChoices("LLM_API_BASE", "OPENAI_API_BASE"),
    )
    dashscope_api_key: str | None = Field(
        default=None,
        description="DashScope API key",
        validation_alias=AliasChoices("DASHSCOPE_API_KEY"),
    )
    dashscope_api_base: str | None = Field(
        default=None,
        description="DashScope API base URL",
        validation_alias=AliasChoices("DASHSCOPE_API_BASE"),
    )
    dashscope_model: str | None = Field(
        default=None,
        description="DashScope model override",
        validation_alias=AliasChoices("DASHSCOPE_MODEL"),
    )
    dashscope_transport_mode: Literal[
        "text_generation", "multimodal_generation", "responses"
    ] = Field(
        default="multimodal_generation",
        description="DashScope native transport mode",
        validation_alias=AliasChoices("DASHSCOPE_TRANSPORT_MODE"),
    )
    dashscope_review_model: str | None = Field(
        default=None,
        description="DashScope review model override",
        validation_alias=AliasChoices("DASHSCOPE_REVIEW_MODEL"),
    )
    openai_compatible_model: str | None = Field(
        default=None,
        description="OpenAI-compatible model override",
        validation_alias=AliasChoices("OPENAI_COMPATIBLE_MODEL"),
    )
    timeout: int = Field(
        default=30, ge=5, le=300, description="Request timeout in seconds"
    )
    max_tokens: int = Field(
        default=4096, ge=1, le=8192, description="Max tokens per request"
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )
    top_p: float = Field(default=0.95, ge=0.0, le=1.0, description="Top-p sampling")
    top_k: int = Field(default=40, ge=1, le=100, description="Top-k sampling")
    retry_attempts: int = Field(
        default=3, ge=1, le=10, description="Number of retry attempts"
    )
    retry_delay: float = Field(
        default=1.0, ge=0.1, le=10.0, description="Retry delay in seconds"
    )

    def resolved_api_key(
        self,
        provider_name: Literal["mock", "dashscope", "openai_compatible"] | str,
    ) -> str | None:
        if provider_name == "dashscope":
            return self.dashscope_api_key
        if provider_name == "openai_compatible":
            return self.api_key
        return None

    def resolved_api_base(
        self,
        provider_name: Literal["mock", "dashscope", "openai_compatible"] | str,
    ) -> str | None:
        if provider_name == "dashscope":
            return self.dashscope_api_base or "https://dashscope.aliyuncs.com/api/v1"
        if provider_name == "openai_compatible":
            return self.api_base or "https://api.openai.com/v1"
        return None

    def resolved_model(
        self,
        provider_name: Literal["mock", "dashscope", "openai_compatible"] | str,
    ) -> str:
        if provider_name == "dashscope":
            return self.dashscope_model or self.model or "qwen3.5-flash"
        if provider_name == "openai_compatible":
            return self.openai_compatible_model or self.model or "gpt-4o-mini"
        return self.model or "deterministic-story-v1"

    def resolved_review_model(
        self,
        provider_name: Literal["mock", "dashscope", "openai_compatible"] | str,
    ) -> str:
        if provider_name == "dashscope":
            return self.dashscope_review_model or self.resolved_model("dashscope")
        return self.resolved_model(provider_name)

    def resolved_dashscope_transport_mode(
        self,
    ) -> Literal["text_generation", "multimodal_generation", "responses"]:
        return self.dashscope_transport_mode
