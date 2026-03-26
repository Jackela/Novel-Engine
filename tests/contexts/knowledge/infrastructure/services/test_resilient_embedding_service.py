"""Tests for resilient embedding service."""

from __future__ import annotations

import pytest

from src.contexts.knowledge.application.ports.i_embedding_service import (
    EmbeddingError,
    IEmbeddingService,
)
from src.contexts.knowledge.infrastructure.services.resilient_embedding_service import (
    CompositeEmbeddingService,
    EmbeddingServiceWithRetry,
    ResilientEmbeddingService,
)
from src.shared.infrastructure.circuit_breaker import (
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
)


class MockEmbeddingService(IEmbeddingService):
    """Mock embedding service for testing."""

    def __init__(self, dimension: int = 1536, should_fail: bool = False):
        self.dimension = dimension
        self.should_fail = should_fail
        self.call_count = 0

    async def embed(self, text: str) -> list[float]:
        self.call_count += 1
        if self.should_fail:
            raise EmbeddingError("Mock error")
        return [0.1] * self.dimension

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        if self.should_fail:
            raise EmbeddingError("Mock error")
        return [[0.1] * self.dimension for _ in texts]

    def get_dimension(self) -> int:
        return self.dimension


class TestResilientEmbeddingService:
    """Test suite for resilient embedding service."""

    @pytest.fixture(autouse=True)
    def clean_registry(self):
        """Clean registry before each test."""
        CircuitBreakerRegistry._circuit_breakers.clear()
        yield
        CircuitBreakerRegistry._circuit_breakers.clear()

    @pytest.fixture
    def mock_service(self):
        """Create mock embedding service."""
        return MockEmbeddingService()

    @pytest.mark.asyncio
    async def test_successful_embed(self, mock_service):
        """Test successful embedding generation."""
        resilient = ResilientEmbeddingService(mock_service)

        result = await resilient.embed("test text")

        assert len(result) == 1536
        assert all(x == 0.1 for x in result)
        assert mock_service.call_count == 1

    @pytest.mark.asyncio
    async def test_successful_batch_embed(self, mock_service):
        """Test successful batch embedding generation."""
        resilient = ResilientEmbeddingService(mock_service)

        result = await resilient.embed_batch(["text1", "text2"])

        assert len(result) == 2
        assert all(len(r) == 1536 for r in result)
        assert mock_service.call_count == 1

    @pytest.mark.asyncio
    async def test_caching_works(self, mock_service):
        """Test that successful results are cached and returned on failure."""
        cache = {}
        resilient = ResilientEmbeddingService(mock_service, cache=cache)

        # First call - should succeed and cache the result
        result1 = await resilient.embed("test text")
        assert len(result1) == 1536

        # Make the mock service fail
        mock_service.should_fail = True

        # Second call with same text should use cached value
        result2 = await resilient.embed("test text")

        # Results should be the same (from cache)
        assert result1 == result2

        # Different text should trigger a new call (which fails)
        # since there's no cache for this text
        with pytest.raises(EmbeddingError):
            await resilient.embed("different text")

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, mock_service):
        """Test circuit breaker opens after threshold failures."""
        mock_service.should_fail = True
        resilient = ResilientEmbeddingService(
            mock_service,
            fallback_to_zero=False,
        )

        # Trigger failures to open circuit
        for _ in range(3):
            with pytest.raises(EmbeddingError):
                await resilient.embed("test")

        # Circuit should be open now
        with pytest.raises((CircuitBreakerOpenError, EmbeddingError)):
            await resilient.embed("test")

    @pytest.mark.asyncio
    async def test_zero_fallback_when_circuit_open(self, mock_service):
        """Test zero embeddings returned when circuit is open."""
        mock_service.should_fail = True
        resilient = ResilientEmbeddingService(
            mock_service,
            fallback_to_zero=True,
        )

        # Trigger failures to open circuit
        for _ in range(3):
            with pytest.raises(EmbeddingError):
                await resilient.embed("test")

        # Should return zero embeddings as ultimate fallback
        result = await resilient.embed("test")
        assert len(result) == 1536
        assert all(x == 0.0 for x in result)

    @pytest.mark.asyncio
    async def test_batch_zero_fallback(self, mock_service):
        """Test zero embeddings for batch when circuit is open."""
        mock_service.should_fail = True
        resilient = ResilientEmbeddingService(
            mock_service,
            fallback_to_zero=True,
        )

        # Trigger failures to open circuit
        for _ in range(3):
            with pytest.raises(EmbeddingError):
                await resilient.embed_batch(["test1", "test2"])

        # Should return zero embeddings
        result = await resilient.embed_batch(["test1", "test2"])
        assert len(result) == 2
        assert all(all(x == 0.0 for x in r) for r in result)

    @pytest.mark.asyncio
    async def test_get_dimension(self, mock_service):
        """Test get_dimension method."""
        resilient = ResilientEmbeddingService(mock_service)

        dimension = resilient.get_dimension()

        assert dimension == 1536

    @pytest.mark.asyncio
    async def test_get_metrics(self, mock_service):
        """Test get_metrics method."""
        resilient = ResilientEmbeddingService(mock_service)

        metrics = resilient.get_metrics()

        assert "name" in metrics
        assert "state" in metrics
        assert "failure_count" in metrics

    @pytest.mark.asyncio
    async def test_circuit_breaker_reuse(self, mock_service):
        """Test that circuit breaker is reused from registry."""
        resilient1 = ResilientEmbeddingService(
            mock_service, circuit_breaker_name="shared"
        )
        resilient2 = ResilientEmbeddingService(
            mock_service, circuit_breaker_name="shared"
        )

        # Should use the same circuit breaker
        assert resilient1._circuit_breaker is resilient2._circuit_breaker


class TestEmbeddingServiceWithRetry:
    """Test suite for embedding service with retry."""

    @pytest.fixture
    def mock_service(self):
        """Create mock embedding service."""
        return MockEmbeddingService()

    @pytest.mark.asyncio
    async def test_success_without_retry(self, mock_service):
        """Test successful call without retry."""
        retry_service = EmbeddingServiceWithRetry(mock_service, max_retries=3)

        result = await retry_service.embed("test")

        assert len(result) == 1536
        assert mock_service.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, mock_service):
        """Test retry on timeout error."""
        call_count = 0

        async def timeout_embed(text: str) -> list[float]:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Timeout")
            return [0.1] * 1536

        mock_service.embed = timeout_embed
        retry_service = EmbeddingServiceWithRetry(
            mock_service, max_retries=3, base_delay=0.01
        )

        result = await retry_service.embed("test")

        assert len(result) == 1536
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_connection_error(self, mock_service):
        """Test retry on connection error."""
        call_count = 0

        async def connection_error_embed(text: str) -> list[float]:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection failed")
            return [0.1] * 1536

        mock_service.embed = connection_error_embed
        retry_service = EmbeddingServiceWithRetry(
            mock_service, max_retries=3, base_delay=0.01
        )

        result = await retry_service.embed("test")

        assert len(result) == 1536
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self, mock_service):
        """Test when all retries are exhausted."""
        # Track the number of times embed is called
        call_count = 0

        async def always_timeout(text: str) -> list[float]:
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Timeout")

        # Replace the embed method
        mock_service.embed = always_timeout

        retry_service = EmbeddingServiceWithRetry(
            mock_service, max_retries=2, base_delay=0.01
        )

        with pytest.raises(TimeoutError):
            await retry_service.embed("test")

        # Should have been called exactly max_retries times
        assert call_count == 2


class TestCompositeEmbeddingService:
    """Test suite for composite embedding service."""

    @pytest.fixture
    def primary_service(self):
        """Create primary mock service."""
        return MockEmbeddingService()

    @pytest.fixture
    def fallback_service(self):
        """Create fallback mock service."""
        return MockEmbeddingService()

    @pytest.mark.asyncio
    async def test_primary_service_success(self, primary_service, fallback_service):
        """Test primary service success."""
        composite = CompositeEmbeddingService(primary_service, [fallback_service])

        result = await composite.embed("test")

        assert len(result) == 1536
        assert primary_service.call_count == 1
        assert fallback_service.call_count == 0

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self, primary_service, fallback_service):
        """Test fallback when primary fails."""
        primary_service.should_fail = True
        composite = CompositeEmbeddingService(primary_service, [fallback_service])

        result = await composite.embed("test")

        assert len(result) == 1536
        assert primary_service.call_count == 1
        assert fallback_service.call_count == 1

    @pytest.mark.asyncio
    async def test_all_services_fail(self, primary_service, fallback_service):
        """Test when all services fail."""
        primary_service.should_fail = True
        fallback_service.should_fail = True
        composite = CompositeEmbeddingService(primary_service, [fallback_service])

        with pytest.raises(EmbeddingError):
            await composite.embed("test")

    @pytest.mark.asyncio
    async def test_batch_fallback(self, primary_service, fallback_service):
        """Test batch embedding fallback."""
        primary_service.should_fail = True
        composite = CompositeEmbeddingService(primary_service, [fallback_service])

        result = await composite.embed_batch(["test1", "test2"])

        assert len(result) == 2
        assert primary_service.call_count == 1
        assert fallback_service.call_count == 1


class TestResilientEmbeddingServiceIntegration:
    """Integration tests for resilient embedding service."""

    @pytest.fixture(autouse=True)
    def clean_registry(self):
        """Clean registry before each test."""
        CircuitBreakerRegistry._circuit_breakers.clear()
        yield
        CircuitBreakerRegistry._circuit_breakers.clear()

    @pytest.mark.asyncio
    async def test_end_to_end_with_circuit_breaker_and_cache(self):
        """Test complete flow with circuit breaker and cache."""
        mock = MockEmbeddingService()
        cache = {}

        resilient = ResilientEmbeddingService(
            mock,
            cache=cache,
            fallback_to_zero=True,
        )

        # First call succeeds
        result1 = await resilient.embed("test")
        assert len(result1) == 1536

        # Simulate service failure
        mock.should_fail = True

        # Should return cached value
        result2 = await resilient.embed("test")
        assert result1 == result2

        # Clear cache and open circuit
        cache.clear()

        # Trigger circuit opening
        for _ in range(3):
            try:
                await resilient.embed("different text")
            except EmbeddingError:
                pass

        # Should return zero embeddings
        result3 = await resilient.embed("another text")
        assert all(x == 0.0 for x in result3)

    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics_updated(self):
        """Test that circuit breaker metrics are updated correctly."""
        mock = MockEmbeddingService(should_fail=True)
        resilient = ResilientEmbeddingService(mock)

        # Trigger failures
        for _ in range(2):
            with pytest.raises(EmbeddingError):
                await resilient.embed("test")

        metrics = resilient.get_metrics()
        assert metrics["failure_count"] >= 2

    @pytest.mark.asyncio
    async def test_dimension_from_primary(self):
        """Test dimension is retrieved from primary service."""
        mock = MockEmbeddingService(dimension=768)
        resilient = ResilientEmbeddingService(mock)

        dimension = resilient.get_dimension()

        assert dimension == 768
