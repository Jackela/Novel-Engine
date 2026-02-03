#!/usr/bin/env python3
"""
LLM Coordination Service
========================

Manages LLM request batching, caching, and optimization for enhanced performance.
"""

import asyncio
import hashlib
import logging
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .types import (
    BatchedRequest,
    CoordinationMetrics,
    LLMCoordinationConfig,
    RequestPriority,
)


class LLMCoordinator:
    """
    Coordinates and optimizes LLM requests for enhanced performance.

    Responsibilities:
    - Request batching and prioritization
    - Response caching and optimization
    - Cost control and monitoring
    - Performance metrics tracking
    """

    def __init__(
        self, config: LLMCoordinationConfig, logger: Optional[logging.Logger] = None
    ):
        """Initialize LLM coordinator."""
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        # Request management
        self.pending_requests: Dict[RequestPriority, deque] = {
            priority: deque() for priority in RequestPriority
        }
        self.active_requests: Dict[str, BatchedRequest] = {}

        # Caching system
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_stats = {"hits": 0, "misses": 0}

        # Metrics tracking
        self.metrics = CoordinationMetrics()
        self.response_times: deque = deque(maxlen=100)

        # Async coordination
        self._batch_processor_task: Optional[asyncio.Task] = None
        self._cache_cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Single-flight & backoff
        self._inflight: Dict[str, asyncio.Future] = {}
        self._waiters_count: Dict[str, int] = {}
        self._negative_cache: Dict[str, float] = {}  # key -> next_allowed_epoch
        self._fail_counts: Dict[str, int] = {}

    async def initialize(self) -> bool:
        """Initialize the LLM coordinator."""
        try:
            self.logger.info("Initializing LLM Coordinator")

            # Start background tasks
            if self.config.enable_smart_batching:
                self._batch_processor_task = asyncio.create_task(
                    self._batch_processor()
                )

            if self.config.enable_caching:
                self._cache_cleanup_task = asyncio.create_task(self._cache_cleanup())

            self.logger.info("LLM Coordinator initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize LLM Coordinator: {e}")
            return False

    async def submit_request(
        self,
        agent_id: str,
        request_type: str,
        content: Dict[str, Any],
        priority: RequestPriority = RequestPriority.NORMAL,
        callback: Optional[callable] = None,
    ) -> str:
        """
        Submit an LLM request for processing.

        Args:
            agent_id: ID of the requesting agent
            request_type: Type of request (dialogue, action, etc.)
            content: Request content
            priority: Request priority level
            callback: Optional callback for async processing

        Returns:
            str: Request ID
        """
        try:
            # Create request
            request = BatchedRequest(
                request_id=f"{agent_id}_{int(time.time() * 1000)}",
                agent_id=agent_id,
                request_type=request_type,
                priority=priority,
                content=content,
                callback=callback,
            )

            cache_key = None
            # Check cache first
            if self.config.enable_caching:
                cache_key = self._generate_cache_key(request)
                cached_result = await self._get_cached_response(cache_key)

                if cached_result is not None:
                    self.cache_stats["hits"] += 1
                    if callback:
                        await callback(cached_result)
                    return request.request_id
                else:
                    self.cache_stats["misses"] += 1

            # Negative cache/backoff
            backoff_until = self._negative_cache.get(cache_key) if cache_key else None
            if backoff_until and time.time() < backoff_until:
                result = {
                    "request_id": request.request_id,
                    "agent_id": request.agent_id,
                    "error": "temporarily unavailable (backoff)",
                    "success": False,
                }
                if callback:
                    await callback(result)
                return request.request_id

            # Single-flight deduplication
            if cache_key and cache_key in self._inflight:
                # attach waiter to existing future
                fut = self._inflight[cache_key]
                self._waiters_count[cache_key] = (
                    self._waiters_count.get(cache_key, 0) + 1
                )

                async def _await_and_callback():
                    try:
                        res = await fut
                        if callback:
                            await callback(res)
                    except Exception:
                        self.logger.debug(
                            "Single-flight callback failed", exc_info=True
                        )

                asyncio.create_task(_await_and_callback())
                # record single-flight merge metric
                try:
                    from src.metrics.global_metrics import metrics as _metrics

                    _metrics.record_single_flight_merged(1)
                except Exception:
                    self.logger.debug(
                        "Single-flight metrics update failed", exc_info=True
                    )
                return request.request_id

            # Handle critical priority requests immediately
            if priority == RequestPriority.CRITICAL:
                result = await self._process_single_request(request)
                if callback:
                    await callback(result)
                return request.request_id

            # Queue for batch processing
            self.pending_requests[priority].append(request)
            self.active_requests[request.request_id] = request
            self.metrics.total_requests += 1

            self.logger.debug(
                f"Request {request.request_id} queued with priority {priority.name}"
            )

            return request.request_id

        except Exception as e:
            self.logger.error(f"Failed to submit request: {e}")
            raise

    async def _batch_processor(self) -> None:
        """Background task for processing batched requests."""
        try:
            while not self._shutdown_event.is_set():
                # Process batches by priority
                for priority in RequestPriority:
                    if self.pending_requests[priority]:
                        await self._process_priority_batch(priority)

                # Wait before next batch cycle
                await asyncio.sleep(self.config.batch_timeout_ms / 1000.0)

        except asyncio.CancelledError:
            self.logger.info("Batch processor task cancelled")
        except Exception as e:
            self.logger.error(f"Batch processor error: {e}")

    async def _process_priority_batch(self, priority: RequestPriority) -> None:
        """Process a batch of requests with the same priority."""
        try:
            requests_to_process = []

            # Collect batch
            while (
                len(requests_to_process) < self.config.max_batch_size
                and self.pending_requests[priority]
            ):
                request = self.pending_requests[priority].popleft()
                requests_to_process.append(request)

            if not requests_to_process:
                return

            # Process batch
            start_time = time.time()
            results = await self._process_batch(requests_to_process)
            processing_time = time.time() - start_time

            # Update metrics
            self.response_times.append(processing_time * 1000)  # Convert to ms
            self._update_response_time_metrics()

            # Handle results
            for request, result in zip(requests_to_process, results):
                if request.callback:
                    try:
                        await request.callback(result)
                    except Exception as e:
                        self.logger.error(
                            f"Callback error for request {request.request_id}: {e}"
                        )

                # Update request tracking
                del self.active_requests[request.request_id]

                # Cache result if enabled
                if self.config.enable_caching:
                    cache_key = self._generate_cache_key(request)
                    await self._cache_response(cache_key, result)

            self.logger.debug(
                f"Processed batch of {len(requests_to_process)} {priority.name} requests in {processing_time:.3f}s"
            )

        except Exception as e:
            self.logger.error(f"Failed to process priority batch {priority.name}: {e}")

            # Mark requests as failed
            for request in requests_to_process:
                self.metrics.failed_requests += 1
                if request.request_id in self.active_requests:
                    del self.active_requests[request.request_id]

    async def _process_batch(self, requests: List[BatchedRequest]) -> List[Any]:
        """Process a batch of requests using the LLM service."""
        try:
            # Import here to avoid circular dependencies
            from src.core.llm_service import get_llm_service

            get_llm_service()
            results = []

            # Process each request in the batch
            for request in requests:
                try:
                    result = await self._process_single_request(request)
                    results.append(result)
                    self.metrics.successful_requests += 1
                except Exception as e:
                    self.logger.error(
                        f"Failed to process request {request.request_id}: {e}"
                    )
                    results.append({"error": str(e)})
                    self.metrics.failed_requests += 1

            return results

        except Exception as e:
            self.logger.error(f"Batch processing failed: {e}")
            return [{"error": str(e)} for _ in requests]

    async def _process_single_request(self, request: BatchedRequest) -> Any:
        """Process a single LLM request."""
        try:
            # Import here to avoid circular dependencies
            from src.core.llm_service import LLMRequest, ResponseFormat, get_llm_service

            llm_service = get_llm_service()

            # Convert to LLM service request format
            llm_request = LLMRequest(
                prompt=str(request.content.get("prompt", "")),
                response_format=(
                    ResponseFormat.JSON
                    if request.content.get("json_mode")
                    else ResponseFormat.TEXT
                ),
                max_tokens=request.content.get("max_tokens", 150),
                temperature=request.content.get("temperature", 0.7),
                metadata={
                    "agent_id": request.agent_id,
                    "request_type": request.request_type,
                },
            )

            # Single-flight key setup
            cache_key = self._generate_cache_key(request)
            fut: Optional[asyncio.Future] = None
            if cache_key not in self._inflight:
                fut = asyncio.get_running_loop().create_future()
                self._inflight[cache_key] = fut
                self._waiters_count[cache_key] = self._waiters_count.get(cache_key, 0)

            # Make request
            response = await llm_service.generate_response(llm_request)

            result = {
                "request_id": request.request_id,
                "agent_id": request.agent_id,
                "response": response.content,
                "usage": response.usage,
                "success": True,
            }

            # resolve inflight and cleanup
            if fut is not None:
                try:
                    fut.set_result(result)
                except Exception:
                    self.logger.debug(
                        "Failed to resolve inflight future", exc_info=True
                    )
                finally:
                    self._inflight.pop(cache_key, None)
                    self._waiters_count.pop(cache_key, None)

            return result

        except Exception as e:
            self.logger.error(f"Single request processing failed: {e}")
            # backoff: exponential per key
            try:
                key = self._generate_cache_key(request)
                cnt = self._fail_counts.get(key, 0) + 1
                self._fail_counts[key] = cnt
                backoff = min(60, 2 ** min(cnt, 5))  # cap 60s
                self._negative_cache[key] = time.time() + backoff
            except Exception:
                self.logger.debug("Negative cache backoff update failed", exc_info=True)
            return {
                "request_id": request.request_id,
                "agent_id": request.agent_id,
                "error": str(e),
                "success": False,
            }

    def _generate_cache_key(self, request: BatchedRequest) -> str:
        """Generate cache key for request."""
        content_str = str(sorted(request.content.items()))
        key_data = f"{request.request_type}:{content_str}"
        return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()  # nosec B324

    async def _get_cached_response(self, cache_key: str) -> Optional[Any]:
        """Get cached response if valid."""
        if cache_key not in self.cache:
            return None

        result, timestamp = self.cache[cache_key]

        # Check if cache entry is still valid
        if datetime.now() - timestamp > timedelta(
            seconds=self.config.cache_ttl_seconds
        ):
            del self.cache[cache_key]
            return None

        return result

    async def _cache_response(self, cache_key: str, response: Any) -> None:
        """Cache a response."""
        if len(self.cache) > 10000:  # Limit cache size
            # Remove oldest entries
            oldest_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k][1])[
                :1000
            ]
            for key in oldest_keys:
                del self.cache[key]

        self.cache[cache_key] = (response, datetime.now())

    async def _cache_cleanup(self) -> None:
        """Background task for cache cleanup."""
        try:
            while not self._shutdown_event.is_set():
                await asyncio.sleep(60)  # Check every minute

                current_time = datetime.now()
                expired_keys = []

                for cache_key, (_, timestamp) in self.cache.items():
                    if current_time - timestamp > timedelta(
                        seconds=self.config.cache_ttl_seconds
                    ):
                        expired_keys.append(cache_key)

                for key in expired_keys:
                    del self.cache[key]

                if expired_keys:
                    self.logger.debug(
                        f"Cleaned up {len(expired_keys)} expired cache entries"
                    )

        except asyncio.CancelledError:
            self.logger.info("Cache cleanup task cancelled")
        except Exception as e:
            self.logger.error(f"Cache cleanup error: {e}")

    def _update_response_time_metrics(self) -> None:
        """Update response time metrics."""
        if self.response_times:
            self.metrics.avg_response_time_ms = sum(self.response_times) / len(
                self.response_times
            )

    async def get_metrics(self) -> CoordinationMetrics:
        """Get current coordination metrics."""
        # Update cache hit rate
        total_cache_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        if total_cache_requests > 0:
            self.metrics.cache_hit_rate = (
                self.cache_stats["hits"] / total_cache_requests
            )

        # Update batch efficiency
        if self.metrics.total_requests > 0:
            self.metrics.batch_efficiency = (
                self.metrics.successful_requests / self.metrics.total_requests
            )

        return self.metrics

    async def get_status(self) -> Dict[str, Any]:
        """Get current coordinator status."""
        return {
            "pending_requests": {
                priority.name: len(queue)
                for priority, queue in self.pending_requests.items()
            },
            "active_requests": len(self.active_requests),
            "cache_size": len(self.cache),
            "cache_stats": self.cache_stats.copy(),
            "metrics": await self.get_metrics(),
            "background_tasks": {
                "batch_processor": self._batch_processor_task is not None
                and not self._batch_processor_task.done(),
                "cache_cleanup": self._cache_cleanup_task is not None
                and not self._cache_cleanup_task.done(),
            },
        }

    async def shutdown(self) -> None:
        """Shutdown the coordinator."""
        try:
            self.logger.info("Shutting down LLM Coordinator")

            # Signal shutdown
            self._shutdown_event.set()

            # Cancel background tasks
            if self._batch_processor_task:
                self._batch_processor_task.cancel()
                try:
                    await self._batch_processor_task
                except asyncio.CancelledError:
                    self.logger.debug(
                        "Batch processor task cancelled during shutdown",
                        exc_info=True,
                    )

            if self._cache_cleanup_task:
                self._cache_cleanup_task.cancel()
                try:
                    await self._cache_cleanup_task
                except asyncio.CancelledError:
                    self.logger.debug(
                        "Cache cleanup task cancelled during shutdown",
                        exc_info=True,
                    )

            # Process any remaining pending requests
            await self._flush_pending_requests()

            self.logger.info("LLM Coordinator shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during LLM Coordinator shutdown: {e}")

    async def _flush_pending_requests(self) -> None:
        """Process any remaining pending requests."""
        try:
            for priority in RequestPriority:
                if self.pending_requests[priority]:
                    await self._process_priority_batch(priority)
        except Exception as e:
            self.logger.error(f"Error flushing pending requests: {e}")

