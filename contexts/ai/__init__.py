#!/usr/bin/env python3
"""
AI Gateway Context - M8 Complete Implementation

This bounded context handles integration with Large Language Model (LLM) providers,
managing AI service orchestration, token budgets, model selection, and response
processing for the Novel Engine platform.

Complete M8 Implementation Features:
- Multi-provider support (OpenAI, Ollama) with intelligent routing
- Comprehensive operational policies (caching, rate limiting, cost tracking, retry/fallback)
- Unified ExecuteLLM service for complete orchestration
- Token budget management and cost enforcement
- Streaming support and real-time responses
- Circuit breaker patterns and resilience

Architecture follows Domain-Driven Design patterns with:
- Domain Layer: Abstract interfaces, value objects, business rules
- Infrastructure Layer: Concrete providers and operational policies
- Application Layer: Orchestration services and use cases
"""

__version__ = "1.0.0"
__author__ = "Novel Engine AI Team"

# Application layer exports
from .application import ExecuteLLMService, LLMExecutionResult

# Domain layer exports
from .domain.services.llm_provider import (
    ILLMProvider,
    LLMRequest,
    LLMRequestType,
    LLMResponse,
    LLMResponseStatus,
)
from .domain.value_objects.common import (
    ModelCapability,
    ModelId,
    ProviderId,
    ProviderType,
    TokenBudget,
)

# Infrastructure layer exports
from .infrastructure import (  # Policy services; Provider implementations
    DefaultCostTracker,
    ExponentialBackoffRetry,
    ICacheService,
    ICostTracker,
    InMemoryCacheService,
    IRateLimiter,
    IRetryPolicy,
    OllamaProvider,
    OpenAIProvider,
    TokenBucketRateLimiter,
)

__all__ = [
    # Domain Layer - Core Interfaces
    "ILLMProvider",
    "LLMRequest",
    "LLMResponse",
    "LLMRequestType",
    "LLMResponseStatus",
    # Domain Layer - Value Objects
    "ProviderId",
    "ModelId",
    "TokenBudget",
    "ProviderType",
    "ModelCapability",
    # Infrastructure Layer - Policy Services
    "ICacheService",
    "InMemoryCacheService",
    "IRateLimiter",
    "TokenBucketRateLimiter",
    "ICostTracker",
    "DefaultCostTracker",
    "IRetryPolicy",
    "ExponentialBackoffRetry",
    # Infrastructure Layer - Provider Implementations
    "OpenAIProvider",
    "OllamaProvider",
    # Application Layer - Orchestration Services
    "ExecuteLLMService",
    "LLMExecutionResult",
]
