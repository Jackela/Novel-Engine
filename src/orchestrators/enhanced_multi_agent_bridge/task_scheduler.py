"""Task Scheduler Module.

Manages LLM request batching, queue processing, and scheduling.
"""

from __future__ import annotations

import asyncio
import heapq
import time
from collections import deque
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

import structlog

if TYPE_CHECKING:
    from .types import LLMBatchRequest, LLMCoordinationConfig, PerformanceBudget

logger = structlog.get_logger(__name__)


class TaskScheduler:
    """Schedules and manages LLM request batching and processing."""

    def __init__(
        self,
        llm_config: LLMCoordinationConfig,
        performance_budget: PerformanceBudget,
    ) -> None:
        """Initialize the task scheduler.

        Args:
            llm_config: LLM coordination configuration
            performance_budget: Performance budget tracker
        """
        self.llm_config = llm_config
        self.performance_budget = performance_budget
        self.llm_request_queue: List[LLMBatchRequest] = []
        self.llm_batch_queue: deque = deque()
        self.llm_batch_timer: Optional[float] = None
        self._batch_processor_task: Optional[asyncio.Task] = None
        self._batch_processor_running = False
        self._batch_results: Dict[str, Dict[str, Any]] = {}
        self.coordination_stats: Dict[str, Any] = {
            "total_llm_calls": 0,
            "batch_efficiency": 0.0,
            "cost_savings": 0.0,
            "dialogue_quality_score": 0.0,
            "batched_requests": 0,
            "priority_bypasses": 0,
            "budget_violations": 0,
            "average_batch_size": 0.0,
            "cost_per_request": 0.0,
            "performance_score": 1.0,
        }

    async def start(self) -> None:
        """Start the batch processor."""
        if self._batch_processor_running:
            return

        self._batch_processor_running = True
        self._batch_processor_task = asyncio.create_task(self._batch_processor())

    async def stop(self) -> None:
        """Stop the batch processor."""
        self._batch_processor_running = False
        if self._batch_processor_task:
            self._batch_processor_task.cancel()
            try:
                await self._batch_processor_task
            except asyncio.CancelledError:
                pass

    async def submit_request(
        self,
        request: LLMBatchRequest,
        process_callback: Callable[[LLMBatchRequest], asyncio.Future[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """Submit a request for processing.

        Args:
            request: The batch request to process
            process_callback: Callback to process the request immediately

        Returns:
            Processing result
        """
        from .types import RequestPriority

        # Handle high priority requests immediately
        if (
            request.priority in [RequestPriority.CRITICAL, RequestPriority.HIGH]
            and request.priority.value / 5.0 <= self.llm_config.batch_priority_threshold
        ):
            self.coordination_stats["priority_bypasses"] += 1
            return await process_callback(request)

        # Add to priority queue for batching
        heapq.heappush(self.llm_request_queue, request)

        # Start batch processor if not running
        if not self._batch_processor_running:
            await self.start()

        # Wait for batch processing with timeout
        return await self._wait_for_result(request.request_id, request.timeout_seconds)

    async def _batch_processor(self) -> None:
        """Main batch processing loop."""
        try:
            while self._batch_processor_running:
                await self._process_batch_cycle()
                await asyncio.sleep(0.1)  # Brief pause between cycles
        except Exception as e:
            logger.error(f"Batch processor error: {e}")
        finally:
            self._batch_processor_running = False

    async def _process_batch_cycle(self) -> None:
        """Process one cycle of batch requests."""
        if not self.llm_request_queue:
            return

        batch_start_time = time.time()
        batch_requests: List[LLMBatchRequest] = []

        # Check if we should wait for more requests or process now
        batch_size = min(len(self.llm_request_queue), self.llm_config.max_batch_size)

        if batch_size < self.llm_config.max_batch_size:
            oldest_request_time = (
                self.llm_request_queue[0].created_at
                if self.llm_request_queue
                else time.time()
            )
            wait_time = (time.time() - oldest_request_time) * 1000  # Convert to ms

            # If we haven't waited long enough and have performance budget, wait
            if (
                wait_time < self.llm_config.batch_timeout_ms
                and not self.performance_budget.is_budget_exceeded()
            ):
                return

        # Extract batch
        for _ in range(batch_size):
            if self.llm_request_queue:
                batch_requests.append(heapq.heappop(self.llm_request_queue))

        if not batch_requests:
            return

        # Process batch (callback will be provided by bridge)
        batch_time = time.time() - batch_start_time
        self.performance_budget.record_batch_time(batch_time)

        # Update batch efficiency stats
        self.coordination_stats["batched_requests"] += len(batch_requests)
        total_batches = self.coordination_stats["batched_requests"] / max(
            1, len(batch_requests)
        )
        self.coordination_stats["average_batch_size"] = self.coordination_stats[
            "batched_requests"
        ] / max(1, total_batches)

        return batch_requests

    async def _wait_for_result(
        self, request_id: str, timeout_seconds: float
    ) -> Dict[str, Any]:
        """Wait for batch request to complete."""
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            if request_id in self._batch_results:
                result = self._batch_results.pop(request_id)
                return result

            await asyncio.sleep(0.05)  # 50ms polling

        # Timeout
        return {"success": False, "request_id": request_id, "error": "Request timeout"}

    def complete_request(self, request_id: str, result: Dict[str, Any]) -> None:
        """Complete a batch request and store result."""
        self._batch_results[request_id] = result

    def get_pending_count(self) -> int:
        """Get number of pending requests."""
        return len(self.llm_request_queue)

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            "pending_requests": len(self.llm_request_queue),
            "processor_running": self._batch_processor_running,
            **self.coordination_stats,
        }

    def update_coordination_stats(self, stats_update: Dict[str, Any]) -> None:
        """Update coordination statistics."""
        self.coordination_stats.update(stats_update)

    def get_remaining_requests(self) -> List[LLMBatchRequest]:
        """Get and clear remaining requests from queue."""
        remaining = []
        while self.llm_request_queue:
            remaining.append(heapq.heappop(self.llm_request_queue))
        return remaining


__all__ = ["TaskScheduler"]
