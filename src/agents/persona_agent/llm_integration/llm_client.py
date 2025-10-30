"""
LLM Client
==========

Advanced LLM integration client for PersonaAgent character responses.
Handles API communication, prompt formatting, and response processing.
"""

import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import requests


class LLMProvider(Enum):
    """Supported LLM providers."""

    GEMINI = "gemini"
    OPENAI = "openai"
    LOCAL = "local"
    FALLBACK = "fallback"


class ResponseFormat(Enum):
    """Response format types."""

    TEXT = "text"
    JSON = "json"
    STRUCTURED = "structured"


@dataclass
class LLMRequest:
    """Represents an LLM API request."""

    prompt: str
    character_context: Dict[str, Any]
    response_format: ResponseFormat = ResponseFormat.TEXT
    max_tokens: int = 500
    temperature: float = 0.7
    top_p: float = 0.9
    stop_sequences: List[str] = None

    def __post_init__(self):
        if self.stop_sequences is None:
            self.stop_sequences = []


@dataclass
class LLMResponse:
    """Represents an LLM API response."""

    success: bool
    content: str
    provider: LLMProvider
    tokens_used: int = 0
    response_time: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LLMClient:
    """
    Advanced LLM integration client for PersonaAgent.

    Responsibilities:
    - Manage connections to multiple LLM providers
    - Handle API authentication and rate limiting
    - Format prompts with character-specific context
    - Process and validate LLM responses
    - Implement fallback strategies and error handling
    - Cache responses for efficiency
    - Track usage and performance metrics
    """

    def __init__(self, character_id: str, logger: Optional[logging.Logger] = None):
        self.character_id = character_id
        self.logger = logger or logging.getLogger(__name__)

        # Provider configuration
        self._providers = {
            LLMProvider.GEMINI: self._setup_gemini_client(),
            LLMProvider.OPENAI: self._setup_openai_client(),
            LLMProvider.LOCAL: self._setup_local_client(),
            LLMProvider.FALLBACK: None,  # Uses built-in responses
        }

        # Provider priority order
        self._provider_priority = [
            LLMProvider.GEMINI,
            LLMProvider.OPENAI,
            LLMProvider.LOCAL,
            LLMProvider.FALLBACK,
        ]

        # Rate limiting
        self._rate_limits = {
            LLMProvider.GEMINI: {
                "requests_per_minute": 60,
                "last_request": 0,
                "request_count": 0,
            },
            LLMProvider.OPENAI: {
                "requests_per_minute": 60,
                "last_request": 0,
                "request_count": 0,
            },
            LLMProvider.LOCAL: {
                "requests_per_minute": 120,
                "last_request": 0,
                "request_count": 0,
            },
        }

        # Response caching
        self._response_cache: Dict[str, Tuple[LLMResponse, float]] = {}
        self._cache_ttl = 300  # 5 minutes

        # Usage tracking
        self._usage_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_tokens": 0,
            "provider_usage": {provider.value: 0 for provider in LLMProvider},
            "average_response_time": 0.0,
        }

        # Configuration
        self._config = {
            "timeout": 30,
            "max_retries": 3,
            "retry_delay": 1.0,
            "enable_caching": True,
            "fallback_enabled": True,
            "default_temperature": 0.7,
            "default_max_tokens": 500,
        }

        # Fallback responses
        self._fallback_responses = self._initialize_fallback_responses()

    async def generate_character_response(
        self, prompt: str, context: Dict[str, Any]
    ) -> str:
        """
        Generate character response using LLM.

        Args:
            prompt: Base prompt for the LLM
            context: Character context and additional data

        Returns:
            str: Generated character response
        """
        try:
            # Format prompt with character context
            formatted_prompt = await self.format_prompt(prompt, context)

            # Create LLM request
            request = LLMRequest(
                prompt=formatted_prompt,
                character_context=context,
                response_format=ResponseFormat.TEXT,
                max_tokens=context.get(
                    "max_tokens", self._config["default_max_tokens"]
                ),
                temperature=context.get(
                    "temperature", self._config["default_temperature"]
                ),
            )

            # Generate response
            response = await self._generate_response(request)

            if response.success:
                return response.content
            else:
                self.logger.warning(f"LLM generation failed: {response.error}")
                return await self._get_fallback_response(prompt, context)

        except Exception as e:
            self.logger.error(f"Character response generation failed: {e}")
            return await self._get_fallback_response(prompt, context)

    async def validate_api_connection(self) -> bool:
        """
        Validate LLM API connection.

        Returns:
            bool: True if at least one provider is available
        """
        try:
            for provider in self._provider_priority[:-1]:  # Exclude fallback
                if await self._test_provider_connection(provider):
                    self.logger.info(f"LLM provider {provider.value} is available")
                    return True

            self.logger.warning("No LLM providers available, fallback mode only")
            return self._config["fallback_enabled"]

        except Exception as e:
            self.logger.error(f"API connection validation failed: {e}")
            return False

    async def format_prompt(
        self, base_prompt: str, character_data: Dict[str, Any]
    ) -> str:
        """
        Format prompt with character-specific context.

        Args:
            base_prompt: Base prompt template
            character_data: Character context and data

        Returns:
            str: Formatted prompt with character context
        """
        try:
            # Extract character information
            character_name = character_data.get("basic_info", {}).get("name", "Unknown")
            faction = character_data.get("faction_info", {}).get(
                "faction", "Independent"
            )
            personality = character_data.get("personality", {})
            current_state = character_data.get("state", {})

            # Build character context section
            context_parts = []

            # Basic identity
            context_parts.append(f"Character: {character_name}")
            context_parts.append(f"Faction: {faction}")

            # Personality traits
            if personality:
                trait_descriptions = []
                for trait, value in personality.items():
                    if isinstance(value, (int, float)) and value != 0.5:
                        intensity = (
                            "high"
                            if value > 0.7
                            else "low" if value < 0.3 else "moderate"
                        )
                        trait_descriptions.append(f"{trait} ({intensity})")

                if trait_descriptions:
                    context_parts.append(
                        f"Personality: {', '.join(trait_descriptions)}"
                    )

            # Current state
            if current_state:
                state_info = []
                if "current_location" in current_state:
                    state_info.append(f"Location: {current_state['current_location']}")
                if "current_status" in current_state:
                    state_info.append(f"Status: {current_state['current_status']}")
                if "morale_level" in current_state:
                    morale = current_state["morale_level"]
                    morale_desc = (
                        "high"
                        if morale > 0.6
                        else "low" if morale < 0.4 else "moderate"
                    )
                    state_info.append(f"Morale: {morale_desc}")

                if state_info:
                    context_parts.append(f"Current State: {', '.join(state_info)}")

            # Goals and motivations
            goals = character_data.get("goals", [])
            if goals:
                goal_descriptions = [
                    goal.get("title", goal.get("description", ""))[:50]
                    for goal in goals[:3]
                ]
                context_parts.append(f"Goals: {'; '.join(goal_descriptions)}")

            # Recent memories or context
            recent_events = character_data.get("recent_events", [])
            if recent_events:
                context_parts.append(
                    f"Recent Events: {len(recent_events)} events to consider"
                )

            # Combine context
            character_context = "\n".join(context_parts)

            # Format the full prompt
            formatted_prompt = f"""{character_context}

{base_prompt}

Respond as {character_name}, staying in character based on the personality, faction, and current situation described above."""

            return formatted_prompt

        except Exception as e:
            self.logger.error(f"Prompt formatting failed: {e}")
            return base_prompt  # Return original prompt on error

    async def get_usage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics."""
        try:
            # Calculate success rate
            total_requests = self._usage_stats["total_requests"]
            success_rate = (
                (self._usage_stats["successful_requests"] / total_requests)
                if total_requests > 0
                else 0.0
            )

            # Provider statistics
            provider_stats = {}
            for provider, count in self._usage_stats["provider_usage"].items():
                provider_stats[provider] = {
                    "requests": count,
                    "percentage": (
                        (count / total_requests * 100) if total_requests > 0 else 0.0
                    ),
                }

            return {
                "total_requests": total_requests,
                "successful_requests": self._usage_stats["successful_requests"],
                "failed_requests": self._usage_stats["failed_requests"],
                "success_rate": success_rate,
                "total_tokens_used": self._usage_stats["total_tokens"],
                "average_response_time": self._usage_stats["average_response_time"],
                "provider_statistics": provider_stats,
                "cache_size": len(self._response_cache),
                "available_providers": [
                    p.value
                    for p in self._provider_priority
                    if await self._is_provider_available(p)
                ],
            }

        except Exception as e:
            self.logger.error(f"Usage statistics calculation failed: {e}")
            return {"error": str(e)}

    # Private helper methods

    async def _generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response using available providers."""
        try:
            # Check cache first
            if self._config["enable_caching"]:
                cached_response = await self._get_cached_response(request)
                if cached_response:
                    return cached_response

            # Try providers in priority order
            last_error = None
            for provider in self._provider_priority:
                if not await self._is_provider_available(provider):
                    continue

                if not await self._check_rate_limit(provider):
                    continue

                try:
                    start_time = time.time()
                    response = await self._call_provider(provider, request)
                    response_time = time.time() - start_time

                    if response.success:
                        response.response_time = response_time

                        # Cache successful response
                        if self._config["enable_caching"]:
                            await self._cache_response(request, response)

                        # Update statistics
                        await self._update_usage_stats(response, True)

                        return response
                    else:
                        last_error = response.error

                except Exception as e:
                    last_error = str(e)
                    self.logger.warning(f"Provider {provider.value} failed: {e}")
                    continue

            # All providers failed
            self._usage_stats["failed_requests"] += 1
            return LLMResponse(
                success=False,
                content="",
                provider=LLMProvider.FALLBACK,
                error=f"All providers failed. Last error: {last_error}",
            )

        except Exception as e:
            self.logger.error(f"Response generation failed: {e}")
            return LLMResponse(
                success=False, content="", provider=LLMProvider.FALLBACK, error=str(e)
            )

    async def _call_provider(
        self, provider: LLMProvider, request: LLMRequest
    ) -> LLMResponse:
        """Call specific LLM provider."""
        try:
            if provider == LLMProvider.GEMINI:
                return await self._call_gemini(request)
            elif provider == LLMProvider.OPENAI:
                return await self._call_openai(request)
            elif provider == LLMProvider.LOCAL:
                return await self._call_local(request)
            elif provider == LLMProvider.FALLBACK:
                return await self._call_fallback(request)
            else:
                return LLMResponse(
                    success=False,
                    content="",
                    provider=provider,
                    error=f"Unsupported provider: {provider}",
                )

        except Exception as e:
            return LLMResponse(
                success=False, content="", provider=provider, error=str(e)
            )

    async def _call_gemini(self, request: LLMRequest) -> LLMResponse:
        """Call Gemini API."""
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return LLMResponse(
                    success=False,
                    content="",
                    provider=LLMProvider.GEMINI,
                    error="GEMINI_API_KEY not found",
                )

            url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"

            payload = {
                "contents": [{"parts": [{"text": request.prompt}]}],
                "generationConfig": {
                    "temperature": request.temperature,
                    "topP": request.top_p,
                    "maxOutputTokens": request.max_tokens,
                },
            }

            if request.stop_sequences:
                payload["generationConfig"]["stopSequences"] = request.stop_sequences

            headers = {
                "Content-Type": "application/json",
            }

            params = {"key": api_key}

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                params=params,
                timeout=self._config["timeout"],
            )

            if response.status_code == 200:
                response_data = response.json()

                if "candidates" in response_data and response_data["candidates"]:
                    candidate = response_data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        content = candidate["content"]["parts"][0]["text"]

                        # Extract token usage if available
                        tokens_used = response_data.get("usageMetadata", {}).get(
                            "totalTokenCount", 0
                        )

                        return LLMResponse(
                            success=True,
                            content=content,
                            provider=LLMProvider.GEMINI,
                            tokens_used=tokens_used,
                            metadata=response_data,
                        )

            return LLMResponse(
                success=False,
                content="",
                provider=LLMProvider.GEMINI,
                error=f"API error: {response.status_code} - {response.text}",
            )

        except Exception as e:
            return LLMResponse(
                success=False, content="", provider=LLMProvider.GEMINI, error=str(e)
            )

    async def _call_openai(self, request: LLMRequest) -> LLMResponse:
        """Call OpenAI API."""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return LLMResponse(
                    success=False,
                    content="",
                    provider=LLMProvider.OPENAI,
                    error="OPENAI_API_KEY not found",
                )

            url = "https://api.openai.com/v1/chat/completions"

            payload = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": request.prompt}],
                "temperature": request.temperature,
                "top_p": request.top_p,
                "max_tokens": request.max_tokens,
            }

            if request.stop_sequences:
                payload["stop"] = request.stop_sequences

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            response = requests.post(
                url, json=payload, headers=headers, timeout=self._config["timeout"]
            )

            if response.status_code == 200:
                response_data = response.json()

                if "choices" in response_data and response_data["choices"]:
                    content = response_data["choices"][0]["message"]["content"]
                    tokens_used = response_data.get("usage", {}).get("total_tokens", 0)

                    return LLMResponse(
                        success=True,
                        content=content,
                        provider=LLMProvider.OPENAI,
                        tokens_used=tokens_used,
                        metadata=response_data,
                    )

            return LLMResponse(
                success=False,
                content="",
                provider=LLMProvider.OPENAI,
                error=f"API error: {response.status_code} - {response.text}",
            )

        except Exception as e:
            return LLMResponse(
                success=False, content="", provider=LLMProvider.OPENAI, error=str(e)
            )

    async def _call_local(self, request: LLMRequest) -> LLMResponse:
        """Call local LLM server."""
        try:
            # This is a placeholder for local LLM integration
            # Could integrate with Ollama, llama.cpp, or other local solutions

            local_endpoint = os.getenv(
                "LOCAL_LLM_ENDPOINT", "http://localhost:8000/generate"
            )

            payload = {
                "prompt": request.prompt,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
            }

            response = requests.post(
                local_endpoint, json=payload, timeout=self._config["timeout"]
            )

            if response.status_code == 200:
                response_data = response.json()
                content = response_data.get("text", response_data.get("response", ""))

                return LLMResponse(
                    success=True,
                    content=content,
                    provider=LLMProvider.LOCAL,
                    tokens_used=len(content.split()),  # Approximate token count
                    metadata=response_data,
                )

            return LLMResponse(
                success=False,
                content="",
                provider=LLMProvider.LOCAL,
                error=f"Local LLM error: {response.status_code}",
            )

        except Exception as e:
            return LLMResponse(
                success=False, content="", provider=LLMProvider.LOCAL, error=str(e)
            )

    async def _call_fallback(self, request: LLMRequest) -> LLMResponse:
        """Use fallback responses when no LLM is available."""
        try:
            # Analyze prompt to determine response type
            prompt_lower = request.prompt.lower()

            # Simple keyword-based response selection
            if any(
                word in prompt_lower for word in ["attack", "combat", "fight", "battle"]
            ):
                response_category = "combat"
            elif any(
                word in prompt_lower
                for word in ["negotiate", "talk", "diplomacy", "discuss"]
            ):
                response_category = "social"
            elif any(
                word in prompt_lower
                for word in ["explore", "investigate", "search", "look"]
            ):
                response_category = "exploration"
            elif any(
                word in prompt_lower for word in ["help", "assist", "support", "aid"]
            ):
                response_category = "helpful"
            else:
                response_category = "neutral"

            # Get fallback response
            responses = self._fallback_responses.get(
                response_category, self._fallback_responses["neutral"]
            )

            # Simple selection based on character context
            character_name = request.character_context.get("basic_info", {}).get(
                "name", "Character"
            )
            faction = request.character_context.get("faction_info", {}).get(
                "faction", "Independent"
            )

            # Select appropriate response template
            import random

            template = random.choice(responses)

            # Simple template variable replacement
            response_text = template.replace("{character_name}", character_name)
            response_text = response_text.replace("{faction}", faction)

            return LLMResponse(
                success=True,
                content=response_text,
                provider=LLMProvider.FALLBACK,
                tokens_used=len(response_text.split()),
                metadata={"fallback_category": response_category},
            )

        except Exception as e:
            return LLMResponse(
                success=False,
                content="I'm not sure how to respond to that.",
                provider=LLMProvider.FALLBACK,
                error=str(e),
            )

    # Configuration and setup methods

    def _setup_gemini_client(self) -> Optional[Any]:
        """Setup Gemini API client."""
        # API key validation is done in _call_gemini
        return {"configured": os.getenv("GEMINI_API_KEY") is not None}

    def _setup_openai_client(self) -> Optional[Any]:
        """Setup OpenAI API client."""
        # API key validation is done in _call_openai
        return {"configured": os.getenv("OPENAI_API_KEY") is not None}

    def _setup_local_client(self) -> Optional[Any]:
        """Setup local LLM client."""
        return {
            "configured": True,
            "endpoint": os.getenv("LOCAL_LLM_ENDPOINT", "http://localhost:8000"),
        }

    def _initialize_fallback_responses(self) -> Dict[str, List[str]]:
        """Initialize fallback response templates."""
        return {
            "combat": [
                "I ready myself for battle, drawing upon my training and resolve.",
                "The situation calls for action. I prepare to defend myself and my allies.",
                "This conflict will test our strength. I stand firm in my convictions.",
            ],
            "social": [
                "I approach this conversation with caution, weighing my words carefully.",
                "Diplomacy may serve us better than force in this situation.",
                "Let us discuss this matter and find common ground if possible.",
            ],
            "exploration": [
                "I examine the area carefully, alert for any signs of danger or opportunity.",
                "This unknown territory requires careful investigation.",
                "I proceed with caution, gathering information as I advance.",
            ],
            "helpful": [
                "I am willing to assist, though I must consider the implications carefully.",
                "If it serves our cause, I will provide what aid I can.",
                "Let me see how I might be of service in this matter.",
            ],
            "neutral": [
                "I consider the situation carefully before making my decision.",
                "This requires thought and consideration of all factors.",
                "I weigh my options based on what I know of the circumstances.",
            ],
        }

    # Utility methods

    async def _get_fallback_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """Get fallback response when LLM fails."""
        try:
            request = LLMRequest(prompt=prompt, character_context=context)
            response = await self._call_fallback(request)
            return response.content

        except Exception as e:
            self.logger.error(f"Fallback response generation failed: {e}")
            return "I'm uncertain how to respond in this situation."

    async def _test_provider_connection(self, provider: LLMProvider) -> bool:
        """Test connection to a specific provider."""
        try:
            if provider == LLMProvider.FALLBACK:
                return True

            test_request = LLMRequest(
                prompt="Test connection. Respond with 'OK'.",
                character_context={},
                max_tokens=10,
            )

            response = await self._call_provider(provider, test_request)
            return response.success

        except Exception:
            return False

    async def _is_provider_available(self, provider: LLMProvider) -> bool:
        """Check if provider is available and configured."""
        try:
            if provider == LLMProvider.FALLBACK:
                return self._config["fallback_enabled"]
            elif provider == LLMProvider.GEMINI:
                return (
                    self._providers[provider]
                    and os.getenv("GEMINI_API_KEY") is not None
                )
            elif provider == LLMProvider.OPENAI:
                return (
                    self._providers[provider]
                    and os.getenv("OPENAI_API_KEY") is not None
                )
            elif provider == LLMProvider.LOCAL:
                return self._providers[provider] is not None

            return False

        except Exception:
            return False

    async def _check_rate_limit(self, provider: LLMProvider) -> bool:
        """Check if provider rate limit allows request."""
        try:
            if provider not in self._rate_limits:
                return True

            rate_info = self._rate_limits[provider]
            current_time = time.time()

            # Reset counter if minute has passed
            if current_time - rate_info["last_request"] > 60:
                rate_info["request_count"] = 0
                rate_info["last_request"] = current_time

            # Check if under limit
            if rate_info["request_count"] < rate_info["requests_per_minute"]:
                rate_info["request_count"] += 1
                return True

            return False

        except Exception:
            return True  # Allow on error

    async def _get_cached_response(self, request: LLMRequest) -> Optional[LLMResponse]:
        """Get cached response if available and valid."""
        try:
            cache_key = self._generate_cache_key(request)

            if cache_key in self._response_cache:
                cached_response, cache_time = self._response_cache[cache_key]

                # Check if cache is still valid
                if time.time() - cache_time < self._cache_ttl:
                    return cached_response
                else:
                    # Remove expired cache entry
                    del self._response_cache[cache_key]

            return None

        except Exception:
            return None

    async def _cache_response(self, request: LLMRequest, response: LLMResponse) -> None:
        """Cache successful response."""
        try:
            cache_key = self._generate_cache_key(request)
            self._response_cache[cache_key] = (response, time.time())

            # Limit cache size
            if len(self._response_cache) > 1000:
                # Remove oldest entries
                sorted_cache = sorted(
                    self._response_cache.items(), key=lambda x: x[1][1]
                )
                for key, _ in sorted_cache[:200]:  # Remove oldest 200 entries
                    del self._response_cache[key]

        except Exception as e:
            self.logger.debug(f"Response caching failed: {e}")

    def _generate_cache_key(self, request: LLMRequest) -> str:
        """Generate cache key for request."""
        import hashlib

        # Include relevant request parameters in cache key
        key_data = f"{request.prompt}_{request.temperature}_{request.max_tokens}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def _update_usage_stats(self, response: LLMResponse, success: bool) -> None:
        """Update usage statistics."""
        try:
            self._usage_stats["total_requests"] += 1

            if success:
                self._usage_stats["successful_requests"] += 1
                self._usage_stats["total_tokens"] += response.tokens_used
                self._usage_stats["provider_usage"][response.provider.value] += 1

                # Update average response time
                total_time = self._usage_stats["average_response_time"] * (
                    self._usage_stats["successful_requests"] - 1
                )
                self._usage_stats["average_response_time"] = (
                    total_time + response.response_time
                ) / self._usage_stats["successful_requests"]
            else:
                self._usage_stats["failed_requests"] += 1

        except Exception as e:
            self.logger.debug(f"Usage statistics update failed: {e}")
