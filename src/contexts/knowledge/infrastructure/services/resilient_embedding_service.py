"""Embedding service with circuit breaker and fallback protection."""

from __future__ import annotations

from typing import Any

import structlog

from src.contexts.knowledge.application.ports.i_embedding_service import (
    EmbeddingError,
    IEmbeddingService,
)
from src.shared.infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitBreakerRegistry,
)
from src.shared.infrastructure.fallback import CachedFallback

logger = structlog.get_logger(__name__)


class ResilientEmbeddingService(IEmbeddingService):
    """Embedding service with circuit breaker and fallback strategies."""

    # OpenAI text-embedding-3-small dimension
    DEFAULT_DIMENSION = 1536

    def __init__(
        self,
        primary_service: IEmbeddingService,
        cache: dict[str, Any] | None = None,
        circuit_breaker_name: str = "openai_api",
        fallback_to_zero: bool = True,
    ):
        """
        Initialize resilient embedding service.

        Args:
            primary_service: The underlying embedding service to protect
            cache: Optional cache dictionary for fallback embeddings
            circuit_breaker_name: Name of circuit breaker to use
            fallback_to_zero: Whether to return zero embeddings as ultimate fallback
        """
        self._primary = primary_service
        self._cache = cache or {}
        self._fallback_to_zero = fallback_to_zero

        # Get or create circuit breaker
        try:
            self._circuit_breaker = CircuitBreakerRegistry.get(circuit_breaker_name)
        except KeyError:
            # Create new circuit breaker if not exists
            self._circuit_breaker = CircuitBreaker(
                name=circuit_breaker_name,
                config=CircuitBreakerConfig(
                    failure_threshold=3,
                    recovery_timeout=60.0,
                    half_open_max_calls=2,
                    success_threshold=2,
                ),
                expected_exception=(EmbeddingError, TimeoutError, ConnectionError),
            )
            CircuitBreakerRegistry.register(circuit_breaker_name, self._circuit_breaker)

    async def embed(self, text: str) -> list[float]:
        """
        Generate embedding with circuit breaker and fallback.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            CircuitBreakerOpenError: If circuit is open and no fallback available
            EmbeddingError: If embedding generation fails
        """
        cache_key = f"embed:{hash(text) % 1000000}"

        async def _do_embed() -> list[float]:
            return await self._circuit_breaker.call(
                self._primary.embed,
                text,
            )

        # Try with cached fallback first
        cached_fallback = CachedFallback[list[float]](
            cache=self._cache,
            cache_key=cache_key,
            default_value=None,
        )

        try:
            result = await cached_fallback.execute(_do_embed)
            return result
        except CircuitBreakerOpenError:
            logger.error(
                "Circuit breaker open for embedding",
                text_length=len(text),
                has_cached_fallback=cache_key in self._cache,
            )
            # Return cached value if available
            if cache_key in self._cache:
                return self._cache[cache_key]
            # Ultimate fallback: return zero embeddings
            if self._fallback_to_zero:
                logger.warning("Using zero embeddings as fallback")
                return [0.0] * self.get_dimension()
            raise
        except EmbeddingError as e:
            logger.error(
                "Embedding generation failed",
                error=str(e),
                text_length=len(text),
            )
            # Check if we have a cached value from a previous successful call
            if cache_key in self._cache:
                return self._cache[cache_key]
            raise
        except EmbeddingError as e:
            logger.error(
                "Embedding generation failed",
                error=str(e),
                text_length=len(text),
            )
            # Check if we have a cached value from a previous successful call
            if cache_key in self._cache:
                return self._cache[cache_key]
            # Return zero embeddings if enabled
            if self._fallback_to_zero:
                logger.warning(
                    "Using zero embeddings as fallback after embedding error"
                )
                return [0.0] * self.get_dimension()
            raise

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        cache_key = f"embed_batch:{len(texts)}:{hash(tuple(texts)) % 1000000}"

        async def _do_embed_batch() -> list[list[float]]:
            return await self._circuit_breaker.call(
                self._primary.embed_batch,
                texts,
            )

        # Try with cached fallback
        cached_fallback = CachedFallback[list[list[float]]](
            cache=self._cache,
            cache_key=cache_key,
            default_value=None,
        )

        try:
            result = await cached_fallback.execute(_do_embed_batch)
            return result
        except CircuitBreakerOpenError:
            logger.error(
                "Circuit breaker open for batch embedding",
                batch_size=len(texts),
                has_cached_fallback=cache_key in self._cache,
            )
            # Return cached value if available
            if cache_key in self._cache:
                return self._cache[cache_key]
            # Ultimate fallback: return list of zero embeddings
            if self._fallback_to_zero:
                logger.warning("Using zero embeddings as batch fallback")
                return [[0.0] * self.get_dimension() for _ in texts]
            raise

    def get_dimension(self) -> int:
        """Get the dimension of the embeddings."""
        return (
            self._primary.get_dimension()
            if hasattr(self._primary, "get_dimension")
            else self.DEFAULT_DIMENSION
        )

    def get_metrics(self) -> dict[str, Any]:
        """Get circuit breaker metrics."""
        return self._circuit_breaker.get_metrics()


class EmbeddingServiceWithRetry(IEmbeddingService):
    """Embedding service with retry logic."""

    def __init__(
        self,
        primary_service: IEmbeddingService,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ):
        self._primary = primary_service
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay

    async def embed(self, text: str) -> list[float]:
        """Generate embedding with retry logic."""
        import asyncio

        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                return await self._primary.embed(text)
            except (TimeoutError, ConnectionError) as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    delay = min(
                        self._base_delay * (2**attempt),
                        self._max_delay,
                    )
                    logger.warning(
                        f"Embedding attempt {attempt + 1} failed, retrying in {delay}s",
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self._max_retries} embedding retries failed",
                        error=str(e),
                    )

        if last_error:
            raise last_error
        raise EmbeddingError("All retries failed")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate batch embeddings with retry logic."""
        import asyncio

        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                return await self._primary.embed_batch(texts)
            except (TimeoutError, ConnectionError) as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    delay = min(
                        self._base_delay * (2**attempt),
                        self._max_delay,
                    )
                    logger.warning(
                        f"Batch embedding attempt {attempt + 1} failed, retrying in {delay}s",
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {self._max_retries} batch embedding retries failed",
                        error=str(e),
                    )

        if last_error:
            raise last_error
        raise EmbeddingError("All retries failed")

    def get_dimension(self) -> int:
        """Get the dimension of the embeddings."""
        return self._primary.get_dimension()


class CompositeEmbeddingService(IEmbeddingService):
    """Embedding service that tries multiple providers."""

    def __init__(
        self,
        primary_service: IEmbeddingService,
        fallback_services: list[IEmbeddingService],
    ):
        self._primary = primary_service
        self._fallbacks = fallback_services

    async def embed(self, text: str) -> list[float]:
        """Try primary service, fall back to alternatives."""
        try:
            return await self._primary.embed(text)
        except Exception as e:
            logger.warning(
                "Primary embedding service failed, trying fallbacks",
                error=str(e),
            )

            for i, fallback in enumerate(self._fallbacks):
                try:
                    return await fallback.embed(text)
                except Exception as fallback_e:
                    logger.warning(
                        f"Fallback service {i + 1} failed",
                        error=str(fallback_e),
                    )

            raise EmbeddingError("All embedding services failed")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Try primary service for batch, fall back to alternatives."""
        try:
            return await self._primary.embed_batch(texts)
        except Exception as e:
            logger.warning(
                "Primary batch embedding service failed, trying fallbacks",
                error=str(e),
            )

            for i, fallback in enumerate(self._fallbacks):
                try:
                    return await fallback.embed_batch(texts)
                except Exception as fallback_e:
                    logger.warning(
                        f"Fallback service {i + 1} failed for batch",
                        error=str(fallback_e),
                    )

            raise EmbeddingError("All embedding services failed")

    def get_dimension(self) -> int:
        """Get the dimension of the embeddings from primary service."""
        return self._primary.get_dimension()
