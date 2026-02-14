"""
Reranker Adapters

Implements IReranker protocol for various reranking providers.
Supports Cohere API for cloud-based reranking and sentence-transformers for local reranking.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapters implementing application port
- Article V (SOLID): SRP - each adapter handles one provider only

Warzone 4: AI Brain - BRAIN-010B
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import structlog

from ...application.ports.i_reranker import (
    RerankDocument,
    RerankerError,
    RerankOutput,
    RerankResult,
)

if TYPE_CHECKING:
    pass

logger = structlog.get_logger()


# Default configuration values
DEFAULT_COHERE_MODEL = "rerank-v3.5"
DEFAULT_LOCAL_MODEL = "ms-marco-MiniLM-L-6-v2"


class CohereReranker:
    """
    Cohere API reranker for cross-encoder reranking.

    Uses Cohere's Rerank API for high-quality reranking of search results.
    Requires a COHERE_API_KEY environment variable or api_key parameter.

    Configuration:
        - COHERE_API_KEY: Required API authentication key
        - COHERE_RERANK_MODEL: Model name (default: rerank-v3.5)

    Attributes:
        _model: Cohere rerank model identifier
        _api_key: Cohere API authentication key
        _base_url: Cohere API endpoint URL

    Example:
        >>> reranker = CohereReranker(api_key="...")
        >>> documents = [
        ...     RerankDocument(index=0, content="brave knight fights", score=0.7),
        ...     RerankDocument(index=1, content="sad princess cries", score=0.6),
        ... ]
        >>> output = await reranker.rerank(
        ...     query="brave knight",
        ...     documents=documents,
        ...     top_k=3,
        ... )
        >>> # Results are reranked by relevance to query
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """
        Initialize the Cohere reranker.

        Args:
            model: Cohere rerank model name (defaults to rerank-v3.5)
            api_key: Cohere API key (defaults to COHERE_API_KEY env var)
            base_url: Custom API base URL (for testing/proxies)

        Raises:
            ValueError: If API key is not provided and not in environment
        """
        self._model: str = model or os.getenv(
            "COHERE_RERANK_MODEL", DEFAULT_COHERE_MODEL
        )
        self._api_key = api_key or os.getenv("COHERE_API_KEY", "")

        if not self._api_key:
            raise ValueError(
                "COHERE_API_KEY environment variable or api_key parameter is required"
            )

        self._base_url = base_url or "https://api.cohere.ai/v1/rerank"

    async def rerank(
        self,
        query: str,
        documents: list[RerankDocument],
        top_k: int | None = None,
    ) -> RerankOutput:
        """
        Rerank documents using the Cohere Rerank API.

        Args:
            query: Search query text
            documents: List of RerankDocument with index, content, and original scores
            top_k: Optional number of top results to return

        Returns:
            RerankOutput with reranked results sorted by relevance

        Raises:
            RerankerError: If API call fails
        """
        import time

        log = logger.bind(model=self._model, document_count=len(documents))

        if not documents:
            return RerankOutput(
                results=[],
                query=query,
                total_reranked=0,
                model=self._model,
                latency_ms=0.0,
            )

        # Prepare documents for API
        docs = [doc.content for doc in documents]

        # Calculate average original score for improvement tracking
        avg_original_score = sum(d.score for d in documents) / len(documents)

        request_body = {
            "query": query,
            "documents": docs,
            "top_n": top_k if top_k is not None else len(documents),
            "model": self._model,
        }

        log.debug("cohere_rerank_start", query_length=len(query))

        start_time = time.perf_counter()
        try:
            response = await self._make_request(request_body)
            latency_ms = (time.perf_counter() - start_time) * 1000

            results = self._parse_results(response, documents, top_k)

            # Calculate score improvement
            avg_new_score = (
                sum(r.relevance_score for r in results) / len(results)
                if results
                else 0.0
            )
            score_improvement = max(0.0, avg_new_score - avg_original_score)

            log.info(
                "cohere_rerank_complete",
                latency_ms=latency_ms,
                output_count=len(results),
                score_improvement=score_improvement,
            )

            return RerankOutput(
                results=results,
                query=query,
                total_reranked=len(documents),
                model=self._model,
                latency_ms=latency_ms,
                score_improvement=score_improvement,
            )

        except RerankerError:
            raise
        except Exception as e:
            log.error(
                "cohere_rerank_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise RerankerError(f"Cohere reranking failed: {e}") from e

    async def _make_request(self, request_body: dict) -> dict[str, Any]:
        """
        Make HTTP request to Cohere API.

        Args:
            request_body: Request payload for the API

        Returns:
            Parsed JSON response

        Raises:
            RerankerError: On HTTP or API errors
        """
        import httpx

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-Client-Name": "novel-engine",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    self._base_url,
                    headers=headers,
                    json=request_body,
                )

                # Handle specific error codes
                if response.status_code == 401:
                    raise RerankerError(
                        "Cohere API authentication failed - check COHERE_API_KEY"
                    )
                elif response.status_code == 429:
                    raise RerankerError("Cohere API rate limit exceeded")
                elif response.status_code >= 400:
                    error_text = response.text
                    try:
                        error_json = response.json()
                        error_message = error_json.get("message", error_text)
                    except Exception:
                        error_message = error_text
                    raise RerankerError(
                        f"Cohere API error {response.status_code}: {error_message}"
                    )

                return response.json()

            except httpx.TimeoutException as e:
                raise RerankerError("Cohere API request timed out") from e
            except httpx.RequestError as e:
                raise RerankerError(f"Cohere API request failed: {e}") from e

    def _parse_results(
        self,
        response_json: dict,
        documents: list[RerankDocument],
        top_k: int | None,
    ) -> list[RerankResult]:
        """
        Parse Cohere API response into RerankResult list.

        Args:
            response_json: Parsed JSON response from Cohere
            documents: Original documents for index mapping
            top_k: Optional top-k limit

        Returns:
            List of RerankResult sorted by relevance
        """
        try:
            cohere_results = response_json["results"]
        except KeyError as e:
            raise RerankerError(f"Invalid Cohere response structure: {e}")

        results: list[RerankResult] = []

        for item in cohere_results:
            # Cohere returns index and relevance_score
            index = item.get("index")
            relevance_score = item.get("relevance_score", 0.0)

            if index is not None and 0 <= index < len(documents):
                results.append(
                    RerankResult(
                        index=index,
                        score=relevance_score,  # Use Cohere's score
                        relevance_score=relevance_score,
                    )
                )

        # Results are already sorted by Cohere
        if top_k is not None:
            results = results[:top_k]

        return results


class LocalReranker:
    """
    Local reranker using sentence-transformers cross-encoder models.

    Performs reranking locally using sentence-transformers cross-encoder models.
    No API calls required - runs entirely on your machine.

    Recommended models:
        - ms-marco-MiniLM-L-6-v2: Fast, good quality (default)
        - cross-encoder/ms-marco-electra-base: Better quality, slower
        - cross-encoder/quora-roberta-base: Good for question-answer

    Configuration:
        - LOCAL_RERANK_MODEL: HuggingFace model name
        - LOCAL_RERANK_DEVICE: Device to use (cpu/cuda, default: cpu)

    Attributes:
        _model_name: HuggingFace model identifier
        _device: Device for model inference
        _model: Loaded sentence-transformers model (lazy loaded)
        _tokenizer: Associated tokenizer

    Example:
        >>> reranker = LocalReranker(model="ms-marco-MiniLM-L-6-v2")
        >>> documents = [
        ...     RerankDocument(index=0, content="brave knight fights", score=0.7),
        ...     RerankDocument(index=1, content="sad princess cries", score=0.6),
        ... ]
        >>> output = await reranker.rerank(
        ...     query="brave knight",
        ...     documents=documents,
        ...     top_k=3,
        ... )
        >>> # Results are reranked by cross-encoder scores
    """

    def __init__(
        self,
        model: str | None = None,
        device: str | None = None,
        cache_dir: str | None = None,
    ):
        """
        Initialize the local reranker.

        Args:
            model: HuggingFace model name (defaults to ms-marco-MiniLM-L-6-v2)
            device: Device for inference (cpu/cuda, defaults to cpu)
            cache_dir: Optional cache directory for model files
        """
        self._model_name: str = model or os.getenv(
            "LOCAL_RERANK_MODEL", DEFAULT_LOCAL_MODEL
        )
        self._device: str = device or os.getenv("LOCAL_RERANK_DEVICE", "cpu")
        self._cache_dir = cache_dir
        self._model: Any = None  # Lazy loaded
        self._load_attempted = False

    async def rerank(
        self,
        query: str,
        documents: list[RerankDocument],
        top_k: int | None = None,
    ) -> RerankOutput:
        """
        Rerank documents using local sentence-transformers model.

        Args:
            query: Search query text
            documents: List of RerankDocument with index, content, and original scores
            top_k: Optional number of top results to return

        Returns:
            RerankOutput with reranked results sorted by relevance

        Raises:
            RerankerError: If model is not available or scoring fails
        """
        import time

        log = logger.bind(
            model=self._model_name,
            device=self._device,
            document_count=len(documents),
        )

        if not documents:
            return RerankOutput(
                results=[],
                query=query,
                total_reranked=0,
                model=self._model_name,
                latency_ms=0.0,
            )

        # Calculate average original score for improvement tracking
        avg_original_score = sum(d.score for d in documents) / len(documents)

        log.debug("local_rerank_start", query_length=len(query))

        start_time = time.perf_counter()
        try:
            # Ensure model is loaded
            model = self._get_model()

            # Prepare query-document pairs
            doc_contents = [doc.content for doc in documents]
            pairs = [[query, doc] for doc in doc_contents]

            # Run cross-encoder scoring
            import torch

            with torch.no_grad():
                scores = model.predict(pairs, convert_to_tensor=True)
                # Convert to list if tensor
                if hasattr(scores, "tolist"):
                    scores = scores.tolist()
                elif hasattr(scores, "cpu"):
                    scores = scores.cpu().tolist()

            latency_ms = (time.perf_counter() - start_time) * 1000

            # Build results sorted by score
            scored = [(i, float(score)) for i, score in enumerate(scores)]
            scored.sort(key=lambda x: x[1], reverse=True)

            # Apply top_k
            if top_k is not None:
                scored = scored[:top_k]

            # Normalize scores to 0-1 range using softmax-like normalization
            max_score = max(s for _, s in scored) if scored else 1.0
            min_score = min(s for _, s in scored) if scored else 0.0
            score_range = max_score - min_score if max_score != min_score else 1.0

            results = [
                RerankResult(
                    index=idx,
                    score=score,
                    relevance_score=(score - min_score) / score_range,
                )
                for idx, score in scored
            ]

            # Calculate score improvement
            avg_new_score = (
                sum(r.relevance_score for r in results) / len(results)
                if results
                else 0.0
            )
            score_improvement = max(0.0, avg_new_score - avg_original_score)

            log.info(
                "local_rerank_complete",
                latency_ms=latency_ms,
                output_count=len(results),
                score_improvement=score_improvement,
            )

            return RerankOutput(
                results=results,
                query=query,
                total_reranked=len(documents),
                model=self._model_name,
                latency_ms=latency_ms,
                score_improvement=score_improvement,
            )

        except ImportError as e:
            log.error("local_rerank_import_error", error=str(e))
            raise RerankerError(
                "sentence-transformers package is required for LocalReranker. "
                "Install with: pip install sentence-transformers"
            ) from e
        except Exception as e:
            log.error(
                "local_rerank_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise RerankerError(f"Local reranking failed: {e}") from e

    def _get_model(self) -> Any:
        """
        Lazy load the sentence-transformers model.

        Returns:
            Loaded sentence-transformers cross-encoder model

        Raises:
            RerankerError: If model cannot be loaded
        """
        if self._model is not None:
            return self._model

        if self._load_attempted:
            raise RerankerError(f"Failed to load reranker model: {self._model_name}")

        self._load_attempted = True

        try:
            from sentence_transformers import CrossEncoder

            logger.info(
                "local_rerank_loading_model",
                model=self._model_name,
                device=self._device,
            )

            self._model = CrossEncoder(
                self._model_name,
                device=self._device,
            )

            return self._model

        except ImportError as e:
            raise RerankerError(
                "sentence-transformers package is required. "
                "Install with: pip install sentence-transformers"
            ) from e
        except Exception as e:
            raise RerankerError(f"Failed to load model {self._model_name}: {e}") from e


class NoOpReranker:
    """
    No-operation reranker that returns results in original order.

    Useful for testing and as a fallback when reranking is disabled.

    Example:
        >>> reranker = NoOpReranker()
        >>> documents = [RerankDocument(index=0, content="test", score=0.5)]
        >>> output = await reranker.rerank("query", documents)
        >>> # Results unchanged
    """

    def __init__(self, latency_ms: float = 0.0):
        """
        Initialize the no-op reranker.

        Args:
            latency_ms: Simulated latency in milliseconds (for testing)
        """
        self._latency_ms = latency_ms

    async def rerank(
        self,
        query: str,
        documents: list[RerankDocument],
        top_k: int | None = None,
    ) -> RerankOutput:
        """
        Return documents in original order without reranking.

        Args:
            query: Search query (ignored)
            documents: Documents to return unchanged
            top_k: Optional limit on number of results

        Returns:
            RerankOutput with results in original order
        """
        import asyncio

        if self._latency_ms > 0:
            await asyncio.sleep(self._latency_ms / 1000.0)

        # Return in original order
        docs_to_return = documents[:top_k] if top_k is not None else documents
        results = [
            RerankResult(
                index=doc.index,
                score=doc.score,
                relevance_score=doc.score,
            )
            for doc in docs_to_return
        ]

        return RerankOutput(
            results=results,
            query=query,
            total_reranked=len(documents),
            model="noop",
            latency_ms=self._latency_ms,
            score_improvement=0.0,
        )


__all__ = [
    "CohereReranker",
    "LocalReranker",
    "NoOpReranker",
    "DEFAULT_COHERE_MODEL",
    "DEFAULT_LOCAL_MODEL",
]
