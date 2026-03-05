"""
Tests for LLM Service Module

Coverage targets:
- Provider routing (OpenAI, Anthropic, etc.)
- Caching behavior
- Error handling (rate limits, timeouts)
- Fallback mechanisms
"""

import asyncio
import hashlib
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from src.core.llm_service import (
    CostControl,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    PerformanceMetrics,
    ResponseFormat,
    UnifiedLLMService,
    create_llm_service_for_testing,
    generate_character_action,
    generate_investigation_clue,
    generate_narrative_content,
    get_llm_service,
)


class TestLLMProvider:
    """Tests for LLMProvider enum."""

    def test_providers(self):
        """Test all providers are defined."""
        assert LLMProvider.GEMINI.value == "gemini"
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"


class TestResponseFormat:
    """Tests for ResponseFormat enum."""

    def test_formats(self):
        """Test all response formats are defined."""
        assert ResponseFormat.ACTION_FORMAT.value == "action"
        assert ResponseFormat.NARRATIVE_FORMAT.value == "narrative"
        assert ResponseFormat.EVENT_JSON.value == "event_json"
        assert ResponseFormat.CLUE_TEXT.value == "clue"
        assert ResponseFormat.DIALOGUE_TEXT.value == "dialogue"


class TestLLMRequest:
    """Tests for LLMRequest dataclass."""

    def test_default_request(self):
        """Test default request values."""
        request = LLMRequest(prompt="Test prompt")
        
        assert request.prompt == "Test prompt"
        assert request.provider == LLMProvider.GEMINI
        assert request.response_format == ResponseFormat.NARRATIVE_FORMAT
        assert request.temperature == 0.7
        assert request.max_tokens == 2000
        assert request.timeout == 30
        assert request.cache_enabled is True
        assert request.priority == 1
        assert request.requester == "unknown"

    def test_custom_request(self):
        """Test custom request values."""
        request = LLMRequest(
            prompt="Test prompt",
            provider=LLMProvider.OPENAI,
            response_format=ResponseFormat.ACTION_FORMAT,
            temperature=0.5,
            max_tokens=1000,
            cache_enabled=False,
            priority=2,
            requester="test_agent",
        )
        
        assert request.provider == LLMProvider.OPENAI
        assert request.response_format == ResponseFormat.ACTION_FORMAT
        assert request.temperature == 0.5
        assert request.max_tokens == 1000
        assert request.cache_enabled is False
        assert request.priority == 2
        assert request.requester == "test_agent"


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_response_creation(self):
        """Test response creation."""
        response = LLMResponse(
            content="Test content",
            provider=LLMProvider.GEMINI,
            format_validated=True,
            cached=False,
            tokens_used=100,
            response_time_ms=500,
            cost_estimate=0.001,
            timestamp=datetime.now(),
            request_id="req123",
        )
        
        assert response.content == "Test content"
        assert response.provider == LLMProvider.GEMINI
        assert response.format_validated is True
        assert response.cached is False
        assert response.tokens_used == 100
        assert response.response_time_ms == 500
        assert response.cost_estimate == 0.001
        assert response.request_id == "req123"


class TestCostControl:
    """Tests for CostControl dataclass."""

    def test_default_cost_control(self):
        """Test default cost control values."""
        control = CostControl()
        
        assert control.daily_budget == 5.0
        assert control.hourly_limit == 100
        assert control.cache_ttl == 3600
        assert control.rate_limit_enabled is True
        assert control.budget_alerts is True

    def test_custom_cost_control(self):
        """Test custom cost control values."""
        control = CostControl(
            daily_budget=10.0,
            hourly_limit=200,
            cache_ttl=7200,
            rate_limit_enabled=False,
        )
        
        assert control.daily_budget == 10.0
        assert control.hourly_limit == 200
        assert control.cache_ttl == 7200
        assert control.rate_limit_enabled is False


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics dataclass."""

    def test_default_metrics(self):
        """Test default metrics values."""
        metrics = PerformanceMetrics()
        
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
        assert metrics.total_tokens_used == 0
        assert metrics.total_cost == 0.0
        assert metrics.average_response_time == 0.0
        assert metrics.daily_spend == 0.0


@pytest.mark.asyncio
class TestUnifiedLLMService:
    """Tests for UnifiedLLMService class."""

    @pytest.fixture
    def cost_control(self):
        """Create a test cost control config."""
        return CostControl(
            daily_budget=10.0,
            hourly_limit=100,
            cache_ttl=3600,
            rate_limit_enabled=False,  # Disable for testing
        )

    @pytest_asyncio.fixture
    async def llm_service(self, cost_control):
        """Create a UnifiedLLMService instance."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            service = UnifiedLLMService(cost_control)
            yield service

    def test_initialization(self, cost_control):
        """Test service initialization."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            service = UnifiedLLMService(cost_control)
            
            assert service.cost_control == cost_control
            assert isinstance(service.metrics, PerformanceMetrics)
            assert service.primary_provider == LLMProvider.GEMINI
            assert service._request_cache == {}

    def test_initialization_without_api_key(self, cost_control):
        """Test service initialization without API key."""
        with patch.dict(os.environ, {}, clear=True):
            service = UnifiedLLMService(cost_control)
            
            # Gemini should not be available without API key
            assert LLMProvider.GEMINI not in service.providers

    def test_initialize_providers(self, cost_control):
        """Test provider initialization."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key", "OPENAI_API_KEY": "openai_key"}):
            service = UnifiedLLMService(cost_control)
            
            assert LLMProvider.GEMINI in service.providers
            assert service.providers[LLMProvider.GEMINI]["available"] is True
            assert LLMProvider.OPENAI in service.providers
            assert service.providers[LLMProvider.OPENAI]["available"] is True

    def test_create_http_session(self, llm_service):
        """Test HTTP session creation."""
        session = llm_service._create_http_session()
        
        assert session is not None
        # Check adapters are mounted
        assert "https://" in session.adapters

    def test_generate_request_id(self, llm_service):
        """Test request ID generation."""
        request = LLMRequest(prompt="Test prompt", requester="tester")
        request_id = llm_service._generate_request_id(request)
        
        assert request_id.startswith("tester_")
        assert len(request_id) > 10  # Should have hash and timestamp

    def test_generate_cache_key(self, llm_service):
        """Test cache key generation."""
        request1 = LLMRequest(prompt="Test prompt", temperature=0.7)
        request2 = LLMRequest(prompt="Test prompt", temperature=0.7)
        request3 = LLMRequest(prompt="Different prompt", temperature=0.7)
        
        key1 = llm_service._generate_cache_key(request1)
        key2 = llm_service._generate_cache_key(request2)
        key3 = llm_service._generate_cache_key(request3)
        
        # Same request should produce same key
        assert key1 == key2
        # Different request should produce different key
        assert key1 != key3
        # Should be SHA256 hash (64 characters)
        assert len(key1) == 64

    def test_estimate_tokens(self, llm_service):
        """Test token estimation."""
        # Rough estimate: ~4 characters per token
        text = "a" * 100
        tokens = llm_service._estimate_tokens(text)
        
        assert tokens == 25  # 100 / 4
        
        # Empty text should return at least 1
        assert llm_service._estimate_tokens("") == 1

    def test_calculate_cost(self, llm_service):
        """Test cost calculation."""
        provider_config = {"cost_per_1k_tokens": 0.002}
        cost = llm_service._calculate_cost(1000, provider_config)
        
        assert cost == 0.002
        
        cost = llm_service._calculate_cost(500, provider_config)
        assert cost == 0.001

    def test_check_rate_limits_disabled(self, llm_service):
        """Test rate limit check when disabled."""
        llm_service.cost_control.rate_limit_enabled = False
        assert llm_service._check_rate_limits() is True

    def test_check_rate_limits_enabled(self, llm_service):
        """Test rate limit check when enabled."""
        llm_service.cost_control.rate_limit_enabled = True
        llm_service.cost_control.hourly_limit = 100
        
        # Should allow requests under limit
        assert llm_service._check_rate_limits() is True
        
        # Fill up to limit
        for _ in range(99):
            llm_service._request_times.append(datetime.now())
        
        # Should still allow one more
        assert llm_service._check_rate_limits() is True
        
        # Next should fail
        assert llm_service._check_rate_limits() is False

    def test_check_budget_limits(self, llm_service):
        """Test budget limit check."""
        today = datetime.now().date().isoformat()
        
        # Under budget
        llm_service._daily_costs[today] = 4.0
        llm_service.cost_control.daily_budget = 5.0
        assert llm_service._check_budget_limits() is True
        
        # Over budget
        llm_service._daily_costs[today] = 6.0
        assert llm_service._check_budget_limits() is False

    def test_cache_response(self, llm_service):
        """Test caching a response."""
        request = LLMRequest(prompt="Test prompt")
        response = LLMResponse(
            content="Test content",
            provider=LLMProvider.GEMINI,
            format_validated=True,
            cached=False,
            tokens_used=10,
            response_time_ms=100,
            cost_estimate=0.001,
            timestamp=datetime.now(),
            request_id="req123",
        )
        
        llm_service._cache_response(request, response)
        
        cache_key = llm_service._generate_cache_key(request)
        assert cache_key in llm_service._request_cache
        assert llm_service._request_cache[cache_key]["response"] == response

    def test_get_cached_response_hit(self, llm_service):
        """Test getting cached response - cache hit."""
        request = LLMRequest(prompt="Test prompt")
        response = LLMResponse(
            content="Test content",
            provider=LLMProvider.GEMINI,
            format_validated=True,
            cached=False,
            tokens_used=10,
            response_time_ms=100,
            cost_estimate=0.001,
            timestamp=datetime.now(),
            request_id="req123",
        )
        
        llm_service._cache_response(request, response)
        cached = llm_service._get_cached_response(request)
        
        assert cached is not None
        assert cached.cached is True  # Should be marked as cached
        assert cached.content == "Test content"

    def test_get_cached_response_miss(self, llm_service):
        """Test getting cached response - cache miss."""
        request = LLMRequest(prompt="Non-cached prompt")
        cached = llm_service._get_cached_response(request)
        
        assert cached is None

    def test_get_cached_response_expired(self, llm_service):
        """Test getting cached response - expired."""
        request = LLMRequest(prompt="Test prompt")
        response = LLMResponse(
            content="Test content",
            provider=LLMProvider.GEMINI,
            format_validated=True,
            cached=False,
            tokens_used=10,
            response_time_ms=100,
            cost_estimate=0.001,
            timestamp=datetime.now(),
            request_id="req123",
        )
        
        llm_service._cache_response(request, response)
        cache_key = llm_service._generate_cache_key(request)
        
        # Manually expire the cache
        llm_service._request_cache[cache_key]["timestamp"] = (
            datetime.now() - timedelta(seconds=7200)  # 2 hours ago
        )
        llm_service.cost_control.cache_ttl = 3600  # 1 hour TTL
        
        cached = llm_service._get_cached_response(request)
        assert cached is None  # Should be expired
        assert cache_key not in llm_service._request_cache  # Should be removed

    def test_update_metrics_success(self, llm_service):
        """Test metrics update on success."""
        response = LLMResponse(
            content="Test content",
            provider=LLMProvider.GEMINI,
            format_validated=True,
            cached=False,
            tokens_used=100,
            response_time_ms=500,
            cost_estimate=0.001,
            timestamp=datetime.now(),
            request_id="req123",
        )
        
        llm_service._update_metrics(response, success=True)
        
        assert llm_service.metrics.total_requests == 1
        assert llm_service.metrics.successful_requests == 1
        assert llm_service.metrics.total_tokens_used == 100
        assert llm_service.metrics.total_cost == 0.001

    def test_validate_response_format_action(self, llm_service):
        """Test action format validation."""
        valid_action = """ACTION: Attack
TARGET: Enemy
REASONING: The enemy is weak"""
        
        assert llm_service._validate_response_format(
            valid_action, ResponseFormat.ACTION_FORMAT
        ) is True
        
        invalid_action = "Just some text"
        assert llm_service._validate_response_format(
            invalid_action, ResponseFormat.ACTION_FORMAT
        ) is False

    def test_validate_response_format_json(self, llm_service):
        """Test JSON format validation."""
        valid_json = '{"key": "value", "number": 123}'
        
        assert llm_service._validate_response_format(
            valid_json, ResponseFormat.EVENT_JSON
        ) is True
        
        invalid_json = "not valid json"
        assert llm_service._validate_response_format(
            invalid_json, ResponseFormat.EVENT_JSON
        ) is False

    def test_validate_response_format_narrative(self, llm_service):
        """Test narrative format validation."""
        valid_narrative = "This is a narrative text with sufficient length."
        
        assert llm_service._validate_response_format(
            valid_narrative, ResponseFormat.NARRATIVE_FORMAT
        ) is True
        
        too_short = "Hi"
        assert llm_service._validate_response_format(
            too_short, ResponseFormat.NARRATIVE_FORMAT
        ) is False
        
        error_format = "[Error: something went wrong]"
        assert llm_service._validate_response_format(
            error_format, ResponseFormat.NARRATIVE_FORMAT
        ) is False

    def test_get_metrics(self, llm_service):
        """Test getting comprehensive metrics."""
        # Set up some metrics
        llm_service.metrics.total_requests = 100
        llm_service.metrics.successful_requests = 90
        llm_service.metrics.failed_requests = 10
        llm_service.metrics.cache_hits = 50
        llm_service.metrics.cache_misses = 50
        
        metrics = llm_service.get_metrics()
        
        assert metrics["requests"]["total"] == 100
        assert metrics["requests"]["successful"] == 90
        assert metrics["requests"]["failed"] == 10
        assert metrics["requests"]["success_rate"] == 0.9
        assert metrics["cache"]["hits"] == 50
        assert metrics["cache"]["misses"] == 50
        assert metrics["cache"]["hit_rate"] == 0.5


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_llm_service_singleton(self):
        """Test that get_llm_service returns singleton."""
        import src.core.llm_service as llm_module
        original = llm_module._llm_service
        llm_module._llm_service = None
        
        try:
            with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
                service1 = get_llm_service()
                service2 = get_llm_service()
                assert service1 is service2
        finally:
            llm_module._llm_service = original

    def test_create_llm_service_for_testing(self):
        """Test creating LLM service for testing."""
        mock_responses = {"test prompt": "mock response"}
        
        service = create_llm_service_for_testing(mock_responses)
        
        assert service is not None
        assert service.cost_control.rate_limit_enabled is False


class TestGenerateMethods:
    """Tests for generate methods."""

    async def test_generate_action_request(self):
        """Test generate action creates correct request."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            service = UnifiedLLMService(CostControl(rate_limit_enabled=False))
            
            # Mock the generate method
            service.generate = AsyncMock(return_value=LLMResponse(
                content="ACTION: Test\nTARGET: Test\nREASONING: Test",
                provider=LLMProvider.GEMINI,
                format_validated=True,
                cached=False,
                tokens_used=10,
                response_time_ms=100,
                cost_estimate=0.001,
                timestamp=datetime.now(),
                request_id="req123",
            ))
            
            response = await service.generate_action("Test prompt", "test_agent")
            
            # Check that generate was called with correct request
            call_args = service.generate.call_args[0][0]
            assert call_args.prompt == "Test prompt"
            assert call_args.response_format == ResponseFormat.ACTION_FORMAT
            assert call_args.requester == "test_agent"
            assert call_args.priority == 1

    async def test_generate_narrative_request(self):
        """Test generate narrative creates correct request."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            service = UnifiedLLMService(CostControl(rate_limit_enabled=False))
            
            service.generate = AsyncMock(return_value=LLMResponse(
                content="Narrative text",
                provider=LLMProvider.GEMINI,
                format_validated=True,
                cached=False,
                tokens_used=10,
                response_time_ms=100,
                cost_estimate=0.001,
                timestamp=datetime.now(),
                request_id="req123",
            ))
            
            response = await service.generate_narrative("Test prompt", "dramatic")
            
            call_args = service.generate.call_args[0][0]
            assert "dramatic narrative" in call_args.prompt.lower()
            assert call_args.response_format == ResponseFormat.NARRATIVE_FORMAT
            assert call_args.temperature == 0.8

    async def test_generate_clue_request(self):
        """Test generate clue creates correct request."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            service = UnifiedLLMService(CostControl(rate_limit_enabled=False))
            
            service.generate = AsyncMock(return_value=LLMResponse(
                content="A mysterious clue",
                provider=LLMProvider.GEMINI,
                format_validated=True,
                cached=False,
                tokens_used=10,
                response_time_ms=100,
                cost_estimate=0.001,
                timestamp=datetime.now(),
                request_id="req123",
            ))
            
            response = await service.generate_clue("treasure", "searching")
            
            call_args = service.generate.call_args[0][0]
            assert "treasure" in call_args.prompt.lower()
            assert "searching" in call_args.prompt.lower()
            assert call_args.response_format == ResponseFormat.CLUE_TEXT

    async def test_generate_dialogue_request(self):
        """Test generate dialogue creates correct request."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            service = UnifiedLLMService(CostControl(rate_limit_enabled=False))
            
            service.generate = AsyncMock(return_value=LLMResponse(
                content="Character dialogue line",
                provider=LLMProvider.GEMINI,
                format_validated=True,
                cached=False,
                tokens_used=10,
                response_time_ms=100,
                cost_estimate=0.001,
                timestamp=datetime.now(),
                request_id="req123",
            ))
            
            personality = {"bravery": 0.8, "intelligence": 0.6}
            context = {"location": "castle", "situation": "battle"}
            
            response = await service.generate_dialogue(
                "Arthur", personality, "angry", context
            )
            
            call_args = service.generate.call_args[0][0]
            assert "Arthur" in call_args.prompt
            assert "angry" in call_args.prompt
            assert call_args.response_format == ResponseFormat.DIALOGUE_TEXT

    async def test_generate_event_request(self):
        """Test generate event creates correct request."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            service = UnifiedLLMService(CostControl(rate_limit_enabled=False))
            
            service.generate = AsyncMock(return_value=LLMResponse(
                content='{"description": "Event desc"}',
                provider=LLMProvider.GEMINI,
                format_validated=True,
                cached=False,
                tokens_used=10,
                response_time_ms=100,
                cost_estimate=0.001,
                timestamp=datetime.now(),
                request_id="req123",
            ))
            
            response = await service.generate_event(
                event_type="battle",
                characters=["Arthur", "Mordred"],
                story_context={"setting": "Camelot"},
                plot_stage="climax",
            )
            
            call_args = service.generate.call_args[0][0]
            assert "battle" in call_args.prompt
            assert "Arthur" in call_args.prompt
            assert "Mordred" in call_args.prompt
            assert call_args.response_format == ResponseFormat.EVENT_JSON
