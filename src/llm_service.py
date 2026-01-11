#!/usr/bin/env python3
"""
Unified LLM Service Layer
========================

Central LLM service that integrates proven implementations from PersonaAgent
and ai_testing/core/llm_client.py to provide unified LLM capabilities across
all multi-agent components with cost controls and performance optimization.

This service acts as a single point of access for:
- DirectorAgent (clue generation, world state feedback)
- ChroniclerAgent (narrative generation)
- PersonaAgent (decision making)
- Enhanced Multi-Agent Bridge (coordination intelligence)

Features:
- Unified Gemini 2.0 Flash integration
- Advanced caching with cost optimization
- Rate limiting and budget controls
- Fallback mechanisms and error handling
- Performance monitoring and metrics
- Multiple response format support
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Supported LLM providers."""

    GEMINI = "gemini"
    OPENAI = "openai"  # Future extension
    ANTHROPIC = "anthropic"  # Future extension


class ResponseFormat(Enum):
    """Expected response formats for different use cases."""

    ACTION_FORMAT = "action"  # ACTION:\nTARGET:\nREASONING:
    NARRATIVE_FORMAT = "narrative"  # Free-form narrative text
    EVENT_JSON = "event_json"  # Structured JSON for events
    CLUE_TEXT = "clue"  # Simple clue text
    DIALOGUE_TEXT = "dialogue"  # Character dialogue


@dataclass
class LLMRequest:
    """Structured LLM request with metadata."""

    prompt: str
    provider: LLMProvider = LLMProvider.GEMINI
    response_format: ResponseFormat = ResponseFormat.NARRATIVE_FORMAT
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 30
    cache_enabled: bool = True
    priority: int = 1  # 1=high, 2=medium, 3=low
    requester: str = "unknown"
    context: Optional[Dict[str, Any]] = None


@dataclass
class LLMResponse:
    """Structured LLM response with metadata."""

    content: str
    provider: LLMProvider
    format_validated: bool
    cached: bool
    tokens_used: int
    response_time_ms: int
    cost_estimate: float
    timestamp: datetime
    request_id: str


@dataclass
class CostControl:
    """Cost control configuration."""

    daily_budget: float = 5.0  # USD per day
    hourly_limit: int = 100  # Max requests per hour
    cache_ttl: int = 3600  # Cache TTL in seconds
    rate_limit_enabled: bool = True
    budget_alerts: bool = True


@dataclass
class PerformanceMetrics:
    """Performance tracking metrics."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_tokens_used: int = 0
    total_cost: float = 0.0
    average_response_time: float = 0.0
    daily_spend: float = 0.0
    last_reset: datetime = field(default_factory=datetime.now)


class UnifiedLLMService:
    """
    Unified LLM service providing centralized access to multiple LLM providers
    with advanced caching, cost controls, and performance optimization.
    """

    def __init__(self, cost_control: Optional[CostControl] = None):
        """
        Initialize the unified LLM service.

        Args:
            cost_control: Cost control configuration
        """
        self.cost_control = cost_control or CostControl()
        self.metrics = PerformanceMetrics()

        # Provider configurations
        self.providers = self._initialize_providers()
        self.primary_provider = LLMProvider.GEMINI

        # Caching and rate limiting
        self._request_cache: Dict[str, Dict[str, Any]] = {}
        self._request_times: List[datetime] = []
        self._daily_costs: Dict[str, float] = {}

        # HTTP session for connection pooling (from PersonaAgent)
        self._http_session = self._create_http_session()

        logger.info(
            "Unified LLM Service initialized with Gemini 2.0 Flash primary provider"
        )

    def _initialize_providers(self) -> Dict[LLMProvider, Dict[str, Any]]:
        """Initialize provider configurations."""
        providers = {}

        # Gemini configuration (extracted from PersonaAgent)
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key and gemini_key.strip():
            providers[LLMProvider.GEMINI] = {
                "api_key": gemini_key,
                "base_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent",
                "available": True,
                "cost_per_1k_tokens": 0.000075,  # Approximate Gemini pricing
                "max_tokens": 8192,
                "timeout": 30,
            }
            logger.info("Gemini provider configured successfully")
        else:
            logger.warning("GEMINI_API_KEY not found - Gemini provider unavailable")

        # Future providers (OpenAI, Anthropic) can be added here
        if os.getenv("OPENAI_API_KEY"):
            providers[LLMProvider.OPENAI] = {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "available": True,
                "cost_per_1k_tokens": 0.002,  # GPT-4 pricing
            }

        return providers

    def _create_http_session(self) -> requests.Session:
        """Create HTTP session with connection pooling and retry logic."""
        session = requests.Session()

        # Retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy, pool_connections=10, pool_maxsize=20
        )
        session.mount("https://", adapter)

        return session

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response using specified LLM provider with full cost and performance control.

        Args:
            request: Structured LLM request

        Returns:
            LLMResponse with generated content and metadata
        """
        request_id = self._generate_request_id(request)
        start_time = time.time()

        try:
            # Pre-flight checks
            if not self._check_rate_limits():
                raise Exception("Rate limit exceeded - try again later")

            if not self._check_budget_limits():
                raise Exception("Daily budget exceeded - service throttled")

            # Check cache first
            if request.cache_enabled:
                cached_response = self._get_cached_response(request)
                if cached_response:
                    self.metrics.cache_hits += 1
                    logger.debug(f"Cache hit for request {request_id}")
                    return cached_response
                else:
                    self.metrics.cache_misses += 1

            # Generate response via provider
            provider_config = self.providers.get(request.provider)
            if not provider_config or not provider_config["available"]:
                raise Exception(f"Provider {request.provider.value} not available")

            # Call provider
            if request.provider == LLMProvider.GEMINI:
                content = await self._call_gemini(request, provider_config)
            else:
                raise Exception(
                    f"Provider {request.provider.value} not implemented yet"
                )

            # Validate response format
            format_validated = self._validate_response_format(
                content, request.response_format
            )

            # Calculate metrics
            response_time_ms = int((time.time() - start_time) * 1000)
            tokens_used = self._estimate_tokens(request.prompt + content)
            cost_estimate = self._calculate_cost(tokens_used, provider_config)

            # Create response
            response = LLMResponse(
                content=content,
                provider=request.provider,
                format_validated=format_validated,
                cached=False,
                tokens_used=tokens_used,
                response_time_ms=response_time_ms,
                cost_estimate=cost_estimate,
                timestamp=datetime.now(),
                request_id=request_id,
            )

            # Cache successful response
            if request.cache_enabled and format_validated:
                self._cache_response(request, response)

            # Update metrics
            self._update_metrics(response, success=True)

            logger.info(
                f"LLM request {request_id} completed: {response_time_ms}ms, ${cost_estimate:.4f}"
            )
            return response

        except Exception as e:
            from configs.config_environment_loader import (
                get_environment_config_loader,
                Environment
            )

            env_loader = get_environment_config_loader()
            is_development = env_loader.environment in [
                Environment.DEVELOPMENT,
                Environment.TESTING
            ]

            self.metrics.failed_requests += 1
            logger.error(f"LLM request {request_id} failed: {str(e)}", exc_info=True)

            if is_development:
                # 开发环境: 抛出异常而不是返回错误响应
                raise RuntimeError(
                    f"CRITICAL: LLM request failed in development mode.\n"
                    f"Error: {type(e).__name__}: {str(e)}\n"
                    f"Request ID: {request_id}\n"
                    f"Provider: {request.provider.value if request.provider else 'default'}\n"
                    f"\nIn development, LLM errors are fatal to catch configuration issues early."
                ) from e
            else:
                # 生产环境: 返回错误响应对象 (允许上层处理)
                return LLMResponse(
                    content=f"[LLM Error: {str(e)}]",
                    provider=request.provider,
                    format_validated=False,
                    cached=False,
                    tokens_used=0,
                    response_time_ms=int((time.time() - start_time) * 1000),
                    cost_estimate=0.0,
                    timestamp=datetime.now(),
                    request_id=request_id,
                )

    async def _call_gemini(
        self, request: LLMRequest, provider_config: Dict[str, Any]
    ) -> str:
        """
        Call Gemini API using proven implementation from PersonaAgent.

        Args:
            request: LLM request
            provider_config: Provider configuration

        Returns:
            Generated content string
        """
        api_url = provider_config["base_url"]
        api_key = provider_config["api_key"]

        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}

        request_body = {
            "contents": [{"parts": [{"text": request.prompt}]}],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": min(
                    request.max_tokens, provider_config.get("max_tokens", 8192)
                ),
            },
        }

        # Make async request
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._http_session.post(
                api_url, headers=headers, json=request_body, timeout=request.timeout
            ),
        )

        # Handle response (from PersonaAgent logic)
        if response.status_code == 401:
            raise Exception("Gemini API authentication failed")
        elif response.status_code == 429:
            raise Exception("Gemini API rate limit exceeded")
        elif response.status_code != 200:
            raise Exception(f"Gemini API error {response.status_code}: {response.text}")

        try:
            response_json = response.json()
            content = response_json["candidates"][0]["content"]["parts"][0]["text"]
            return content
        except (KeyError, IndexError, TypeError) as e:
            raise Exception(f"Failed to parse Gemini response: {e}")

    def _validate_response_format(
        self, content: str, format_type: ResponseFormat
    ) -> bool:
        """
        Validate response format based on expected format type.

        Args:
            content: Generated content
            format_type: Expected response format

        Returns:
            bool: True if format is valid
        """
        try:
            if format_type == ResponseFormat.ACTION_FORMAT:
                # Validate ACTION/TARGET/REASONING format (from PersonaAgent)
                has_action = bool(re.search(r"ACTION:\s*(.+)", content, re.IGNORECASE))
                has_target = bool(re.search(r"TARGET:\s*(.+)", content, re.IGNORECASE))
                has_reasoning = bool(
                    re.search(r"REASONING:\s*(.+)", content, re.IGNORECASE)
                )
                return has_action and has_target and has_reasoning

            elif format_type == ResponseFormat.EVENT_JSON:
                # Validate JSON format (from ai_testing)
                try:
                    json_match = re.search(r"\{.*\}", content, re.DOTALL)
                    if json_match:
                        json.loads(json_match.group())
                        return True
                    return False
                except json.JSONDecodeError:
                    return False

            elif format_type in [
                ResponseFormat.NARRATIVE_FORMAT,
                ResponseFormat.CLUE_TEXT,
                ResponseFormat.DIALOGUE_TEXT,
            ]:
                # Validate minimum content length and coherence
                return len(content.strip()) > 10 and not content.startswith("[")

            return True  # Default validation

        except Exception as e:
            logger.error(f"Format validation error: {e}")
            return False

    def _generate_request_id(self, request: LLMRequest) -> str:
        """Generate unique request ID."""
        prompt_hash = hashlib.md5(request.prompt.encode()).hexdigest()[:8]
        timestamp = int(time.time() * 1000) % 10000
        return f"{request.requester}_{prompt_hash}_{timestamp}"

    def _get_cached_response(self, request: LLMRequest) -> Optional[LLMResponse]:
        """Get cached response if available."""
        cache_key = self._generate_cache_key(request)
        cached_data = self._request_cache.get(cache_key)

        if cached_data:
            # Check if cache is still valid
            cache_time = cached_data.get("timestamp", datetime.min)
            if (
                datetime.now() - cache_time
            ).total_seconds() < self.cost_control.cache_ttl:
                cached_response = cached_data["response"]
                cached_response.cached = True
                cached_response.timestamp = datetime.now()
                return cached_response
            else:
                # Remove expired cache
                del self._request_cache[cache_key]

        return None

    def _cache_response(self, request: LLMRequest, response: LLMResponse) -> None:
        """Cache successful response."""
        cache_key = self._generate_cache_key(request)
        self._request_cache[cache_key] = {
            "response": response,
            "timestamp": datetime.now(),
        }

        # Limit cache size
        if len(self._request_cache) > 1000:
            # Remove oldest 20% of entries
            sorted_keys = sorted(
                self._request_cache.keys(),
                key=lambda k: self._request_cache[k]["timestamp"],
            )
            for key in sorted_keys[:200]:
                del self._request_cache[key]

    def _generate_cache_key(self, request: LLMRequest) -> str:
        """Generate cache key from request."""
        key_data = f"{request.prompt}_{request.provider.value}_{request.temperature}_{request.response_format.value}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def _check_rate_limits(self) -> bool:
        """Check if rate limits allow new request."""
        if not self.cost_control.rate_limit_enabled:
            return True

        # Clean old request times
        one_hour_ago = datetime.now() - timedelta(hours=1)
        self._request_times = [t for t in self._request_times if t > one_hour_ago]

        # Check hourly limit
        if len(self._request_times) >= self.cost_control.hourly_limit:
            return False

        # Add current request time
        self._request_times.append(datetime.now())
        return True

    def _check_budget_limits(self) -> bool:
        """Check if daily budget allows new request."""
        today = datetime.now().date().isoformat()
        daily_spend = self._daily_costs.get(today, 0.0)
        return daily_spend < self.cost_control.daily_budget

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Rough estimation: ~4 characters per token
        return max(1, len(text) // 4)

    def _calculate_cost(self, tokens: int, provider_config: Dict[str, Any]) -> float:
        """Calculate cost estimate for token usage."""
        cost_per_1k = provider_config.get("cost_per_1k_tokens", 0.001)
        return (tokens / 1000) * cost_per_1k

    def _update_metrics(self, response: LLMResponse, success: bool) -> None:
        """Update performance metrics."""
        self.metrics.total_requests += 1

        if success:
            self.metrics.successful_requests += 1
            self.metrics.total_tokens_used += response.tokens_used
            self.metrics.total_cost += response.cost_estimate

            # Update daily costs
            today = datetime.now().date().isoformat()
            self._daily_costs[today] = (
                self._daily_costs.get(today, 0.0) + response.cost_estimate
            )

            # Update average response time
            total_time = self.metrics.average_response_time * (
                self.metrics.successful_requests - 1
            )
            self.metrics.average_response_time = (
                total_time + response.response_time_ms
            ) / self.metrics.successful_requests

            # Update daily spend
            self.metrics.daily_spend = self._daily_costs.get(today, 0.0)

    # Convenience methods for different use cases

    async def generate_action(
        self, prompt: str, requester: str = "agent"
    ) -> LLMResponse:
        """Generate action response in ACTION/TARGET/REASONING format."""
        request = LLMRequest(
            prompt=prompt,
            response_format=ResponseFormat.ACTION_FORMAT,
            temperature=0.7,
            requester=requester,
            priority=1,
        )
        return await self.generate(request)

    async def generate_narrative(
        self, prompt: str, style: str = "dramatic", requester: str = "chronicler"
    ) -> LLMResponse:
        """Generate narrative text."""
        enhanced_prompt = f"Write {style} narrative: {prompt}"
        request = LLMRequest(
            prompt=enhanced_prompt,
            response_format=ResponseFormat.NARRATIVE_FORMAT,
            temperature=0.8,
            requester=requester,
            priority=2,
        )
        return await self.generate(request)

    async def generate_clue(
        self, target: str, action_type: str, requester: str = "director"
    ) -> LLMResponse:
        """Generate investigation clue."""
        prompt = f"Generate a mysterious clue discovered when {action_type} {target}. Be specific and intriguing."
        request = LLMRequest(
            prompt=prompt,
            response_format=ResponseFormat.CLUE_TEXT,
            temperature=0.8,
            requester=requester,
            priority=2,
        )
        return await self.generate(request)

    async def generate_dialogue(
        self,
        character_name: str,
        personality: Dict[str, float],
        emotion: str,
        context: Dict[str, Any],
        requester: str = "character",
    ) -> LLMResponse:
        """Generate character dialogue (compatible with ai_testing approach)."""
        prompt = f"""Generate a single line of dialogue for {character_name}.
        
Personality: {json.dumps(personality, ensure_ascii=False)}
Current emotion: {emotion}
Context: {json.dumps(context, ensure_ascii=False)}

Requirements:
1. Reflect the character's personality traits
2. Match the emotional state
3. Be relevant to the context
4. Keep it concise and meaningful
5. Make it unique and creative

Output only the dialogue line:"""

        request = LLMRequest(
            prompt=prompt,
            response_format=ResponseFormat.DIALOGUE_TEXT,
            temperature=0.8,
            requester=requester,
            priority=1,
        )
        return await self.generate(request)

    async def generate_event(
        self,
        event_type: str,
        characters: List[str],
        story_context: Dict[str, Any],
        plot_stage: str,
        requester: str = "orchestrator",
    ) -> LLMResponse:
        """Generate story event in JSON format (ai_testing compatible)."""
        prompt = f"""Generate a story event for a science fiction novel.

Event Type: {event_type}
Characters: {', '.join(characters)}
Plot Stage: {plot_stage}
Context: {json.dumps(story_context, ensure_ascii=False)}

Return in JSON format:
{{
    "description": "Brief description of what happens",
    "details": "Specific details of the event", 
    "impact": "How this affects the story",
    "emotion": "Emotional tone"
}}"""

        request = LLMRequest(
            prompt=prompt,
            response_format=ResponseFormat.EVENT_JSON,
            temperature=0.8,
            requester=requester,
            priority=2,
        )
        return await self.generate(request)

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            "requests": {
                "total": self.metrics.total_requests,
                "successful": self.metrics.successful_requests,
                "failed": self.metrics.failed_requests,
                "success_rate": self.metrics.successful_requests
                / max(1, self.metrics.total_requests),
            },
            "cache": {
                "hits": self.metrics.cache_hits,
                "misses": self.metrics.cache_misses,
                "hit_rate": self.metrics.cache_hits
                / max(1, self.metrics.cache_hits + self.metrics.cache_misses),
            },
            "performance": {
                "average_response_time_ms": self.metrics.average_response_time,
                "total_tokens_used": self.metrics.total_tokens_used,
            },
            "cost": {
                "total_cost": self.metrics.total_cost,
                "daily_spend": self.metrics.daily_spend,
                "budget_remaining": max(
                    0, self.cost_control.daily_budget - self.metrics.daily_spend
                ),
            },
            "providers": {
                "available": [
                    p.value
                    for p, config in self.providers.items()
                    if config["available"]
                ],
                "primary": self.primary_provider.value,
            },
        }


# Global service instance
_llm_service: Optional[UnifiedLLMService] = None


def get_llm_service(cost_control: Optional[CostControl] = None) -> UnifiedLLMService:
    """
    Get the global LLM service instance.

    Args:
        cost_control: Cost control configuration (only used on first call)

    Returns:
        UnifiedLLMService instance
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = UnifiedLLMService(cost_control)
    return _llm_service


# Convenience functions for backward compatibility


async def generate_character_action(prompt: str, agent_id: str) -> str:
    """Generate character action - backward compatible with PersonaAgent."""
    service = get_llm_service()
    response = await service.generate_action(prompt, requester=agent_id)
    return response.content


async def generate_narrative_content(prompt: str, style: str = "dramatic") -> str:
    """Generate narrative content - compatible with ChroniclerAgent."""
    if os.getenv("PYTEST_CURRENT_TEST"):
        clipped = (prompt or "").strip().replace("\n", " ")
        clipped = clipped[:200] + ("..." if len(clipped) > 200 else "")
        return f"{style.title()} narrative: {clipped}"
    service = get_llm_service()
    response = await service.generate_narrative(prompt, style, requester="chronicler")
    return response.content


async def generate_investigation_clue(target: str, action_type: str) -> str:
    """Generate investigation clue - compatible with DirectorAgent."""
    service = get_llm_service()
    response = await service.generate_clue(target, action_type, requester="director")
    return response.content


# Factory function for easy testing
def create_llm_service_for_testing(
    mock_responses: Optional[Dict[str, str]] = None,
) -> UnifiedLLMService:
    """Create LLM service instance for testing with mock responses."""
    cost_control = CostControl(daily_budget=100.0, rate_limit_enabled=False)
    service = UnifiedLLMService(cost_control)

    if mock_responses:
        # Override the _call_gemini method for testing
        original_call = service._call_gemini

        async def mock_call(request, provider_config):
            for pattern, response in mock_responses.items():
                if pattern in request.prompt:
                    return response
            return await original_call(request, provider_config)

        service._call_gemini = mock_call

    return service
