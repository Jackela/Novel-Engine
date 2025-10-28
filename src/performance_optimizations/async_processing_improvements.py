"""
Async Processing Improvements and Concurrency Optimization
==========================================================

Advanced asynchronous processing optimizations to eliminate blocking operations
and maximize concurrent processing capabilities in Novel Engine.

Wave 5.3 - Async Processing & Concurrency Enhancement
"""

import asyncio
import json
import logging
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Dict, List, Optional, Tuple

import aiofiles
import aiohttp
import psutil

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels for async processing."""

    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class AsyncTask:
    """Async task with metadata and priority."""

    task_id: str
    coroutine: Awaitable[Any]
    priority: TaskPriority
    created_at: datetime = field(default_factory=datetime.now)
    timeout_seconds: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.timeout_seconds is None:
            # Set default timeout based on priority
            if self.priority == TaskPriority.CRITICAL:
                self.timeout_seconds = 30.0
            elif self.priority == TaskPriority.HIGH:
                self.timeout_seconds = 60.0
            else:
                self.timeout_seconds = 120.0


@dataclass
class ProcessingMetrics:
    """Metrics for async processing performance."""

    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    timeout_tasks: int = 0
    avg_processing_time: float = 0.0
    concurrent_peak: int = 0
    queue_size_peak: int = 0

    def calculate_success_rate(self) -> float:
        """Calculate task success rate."""
        total = self.completed_tasks + self.failed_tasks + self.timeout_tasks
        return (self.completed_tasks / total * 100) if total > 0 else 0.0


class AsyncTaskScheduler:
    """
    High-performance async task scheduler with priority queues and resource management.

    Features:
    - Priority-based task scheduling
    - Concurrent execution with resource limits
    - Automatic retry with exponential backoff
    - Task timeout handling
    - Performance monitoring
    - Resource-aware scaling
    """

    def __init__(
        self,
        max_concurrent_tasks: int = 50,
        max_queue_size: int = 1000,
        enable_metrics: bool = True,
    ):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.max_queue_size = max_queue_size
        self.enable_metrics = enable_metrics

        # Priority queues for different task priorities
        self.priority_queues = {
            TaskPriority.CRITICAL: asyncio.Queue(maxsize=max_queue_size // 4),
            TaskPriority.HIGH: asyncio.Queue(maxsize=max_queue_size // 4),
            TaskPriority.NORMAL: asyncio.Queue(maxsize=max_queue_size // 2),
            TaskPriority.LOW: asyncio.Queue(maxsize=max_queue_size // 4),
        }

        # Task tracking
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_results: Dict[str, Any] = {}
        self.task_errors: Dict[str, Exception] = {}

        # Performance metrics
        self.metrics = ProcessingMetrics()
        self.processing_times = deque(maxlen=1000)  # Keep last 1000 processing times

        # Resource monitoring
        self.resource_monitor_active = True
        self.resource_monitor_task = None

        # Scheduler control
        self.scheduler_active = False
        self.scheduler_tasks = []

        logger.info(
            f"AsyncTaskScheduler initialized: max_concurrent={max_concurrent_tasks}, "
            f"queue_size={max_queue_size}"
        )

    async def start(self):
        """Start the async task scheduler."""
        if self.scheduler_active:
            logger.warning("Scheduler already running")
            return

        self.scheduler_active = True

        # Start priority-based task processors
        self.scheduler_tasks = []
        for priority in TaskPriority:
            task = asyncio.create_task(self._process_priority_queue(priority))
            self.scheduler_tasks.append(task)

        # Start resource monitor
        self.resource_monitor_task = asyncio.create_task(self._resource_monitor())

        logger.info("AsyncTaskScheduler started")

    async def stop(self):
        """Stop the async task scheduler gracefully."""
        self.scheduler_active = False
        self.resource_monitor_active = False

        # Cancel all running tasks
        for task in self.running_tasks.values():
            if not task.done():
                task.cancel()

        # Cancel scheduler tasks
        for task in self.scheduler_tasks:
            task.cancel()

        if self.resource_monitor_task:
            self.resource_monitor_task.cancel()

        # Wait for graceful shutdown
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)

        logger.info("AsyncTaskScheduler stopped")

    async def submit_task(self, task: AsyncTask) -> str:
        """Submit task for async processing."""
        try:
            queue = self.priority_queues[task.priority]
            await queue.put(task)

            self.metrics.total_tasks += 1
            current_queue_size = sum(q.qsize() for q in self.priority_queues.values())
            self.metrics.queue_size_peak = max(
                self.metrics.queue_size_peak, current_queue_size
            )

            logger.debug(
                f"Task submitted: {task.task_id} (priority: {task.priority.name})"
            )
            return task.task_id

        except asyncio.QueueFull:
            logger.error(f"Task queue full for priority {task.priority.name}")
            raise Exception(f"Task queue full for priority {task.priority.name}")

    async def get_task_result(self, task_id: str, timeout: float = 60.0) -> Any:
        """Get result of completed task."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check if task completed
            if task_id in self.task_results:
                return self.task_results.pop(task_id)

            # Check if task failed
            if task_id in self.task_errors:
                error = self.task_errors.pop(task_id)
                raise error

            # Check if task is still running
            if task_id in self.running_tasks:
                await asyncio.sleep(0.1)
                continue

            # Task not found
            await asyncio.sleep(0.1)

        raise asyncio.TimeoutError(f"Task {task_id} result timeout after {timeout}s")

    async def _process_priority_queue(self, priority: TaskPriority):
        """Process tasks from a specific priority queue."""
        queue = self.priority_queues[priority]

        while self.scheduler_active:
            try:
                # Wait for available slot
                while len(self.running_tasks) >= self.max_concurrent_tasks:
                    await asyncio.sleep(0.01)

                # Get next task (with timeout to allow periodic checks)
                try:
                    task = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue  # No tasks available, continue loop

                # Execute task
                asyncio_task = asyncio.create_task(self._execute_task(task))
                self.running_tasks[task.task_id] = asyncio_task

                # Update metrics
                current_concurrent = len(self.running_tasks)
                self.metrics.concurrent_peak = max(
                    self.metrics.concurrent_peak, current_concurrent
                )

            except Exception as e:
                logger.error(f"Priority queue {priority.name} processing error: {e}")
                await asyncio.sleep(1.0)  # Brief pause on error

    async def _execute_task(self, task: AsyncTask):
        """Execute a single async task with timeout and retry logic."""
        start_time = time.time()

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                task.coroutine, timeout=task.timeout_seconds
            )

            # Store result
            self.task_results[task.task_id] = result

            # Update metrics
            processing_time = time.time() - start_time
            self.processing_times.append(processing_time)
            self.metrics.completed_tasks += 1

            # Update average processing time
            if self.processing_times:
                self.metrics.avg_processing_time = sum(self.processing_times) / len(
                    self.processing_times
                )

            logger.debug(f"Task completed: {task.task_id} in {processing_time:.3f}s")

        except asyncio.TimeoutError:
            logger.warning(
                f"Task timeout: {task.task_id} after {task.timeout_seconds}s"
            )

            # Retry if under limit
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                await asyncio.sleep(2**task.retry_count)  # Exponential backoff
                await self.submit_task(task)
                logger.info(
                    f"Task retrying: {task.task_id} (attempt {task.retry_count + 1})"
                )
            else:
                self.task_errors[task.task_id] = asyncio.TimeoutError(
                    f"Task {task.task_id} timeout after {task.max_retries} retries"
                )
                self.metrics.timeout_tasks += 1

        except Exception as e:
            logger.error(f"Task failed: {task.task_id} - {e}")

            # Retry if under limit
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                await asyncio.sleep(2**task.retry_count)
                await self.submit_task(task)
                logger.info(
                    f"Task retrying: {task.task_id} (attempt {task.retry_count + 1})"
                )
            else:
                self.task_errors[task.task_id] = e
                self.metrics.failed_tasks += 1

        finally:
            # Remove from running tasks
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]

    async def _resource_monitor(self):
        """Monitor system resources and adjust concurrency."""
        while self.resource_monitor_active:
            try:
                # Get system resource usage
                process = psutil.Process()
                memory_percent = process.memory_percent()
                cpu_percent = process.cpu_percent()

                # Adjust concurrency based on resources
                if memory_percent > 80 or cpu_percent > 90:
                    # Reduce concurrency under high resource usage
                    self.max_concurrent_tasks = max(10, self.max_concurrent_tasks - 5)
                    logger.warning(
                        f"High resource usage: CPU={cpu_percent:.1f}%, "
                        f"Memory={memory_percent:.1f}%, reducing concurrency to {self.max_concurrent_tasks}"
                    )

                elif memory_percent < 60 and cpu_percent < 70:
                    # Increase concurrency under low resource usage
                    original_max = 50
                    self.max_concurrent_tasks = min(
                        original_max, self.max_concurrent_tasks + 2
                    )

                await asyncio.sleep(10.0)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(30.0)

    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status and metrics."""
        return {
            "active": self.scheduler_active,
            "running_tasks": len(self.running_tasks),
            "max_concurrent": self.max_concurrent_tasks,
            "queue_sizes": {
                priority.name: queue.qsize()
                for priority, queue in self.priority_queues.items()
            },
            "metrics": {
                "total_tasks": self.metrics.total_tasks,
                "completed_tasks": self.metrics.completed_tasks,
                "failed_tasks": self.metrics.failed_tasks,
                "timeout_tasks": self.metrics.timeout_tasks,
                "success_rate_percent": self.metrics.calculate_success_rate(),
                "avg_processing_time_ms": self.metrics.avg_processing_time * 1000,
                "concurrent_peak": self.metrics.concurrent_peak,
                "queue_size_peak": self.metrics.queue_size_peak,
            },
        }


class AsyncHttpClient:
    """
    High-performance async HTTP client with connection pooling and intelligent retry.

    Optimized for PersonaAgent LLM API calls and external service integration.
    """

    def __init__(
        self,
        max_connections: int = 100,
        max_connections_per_host: int = 20,
        connection_timeout: float = 10.0,
        request_timeout: float = 30.0,
    ):
        self.max_connections = max_connections
        self.max_connections_per_host = max_connections_per_host
        self.connection_timeout = connection_timeout
        self.request_timeout = request_timeout

        # Connection pool configuration
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=max_connections_per_host,
            ttl_dns_cache=300,  # 5 minute DNS cache
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
        )

        self.session = None
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0

        logger.info(
            f"AsyncHttpClient initialized: max_conn={max_connections}, "
            f"per_host={max_connections_per_host}"
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self):
        """Start the HTTP client session."""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(
                total=self.request_timeout, connect=self.connection_timeout
            )

            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=timeout,
                headers={"User-Agent": "NovelEngine-AsyncClient/1.0"},
            )
            logger.debug("AsyncHttpClient session started")

    async def close(self):
        """Close the HTTP client session."""
        if self.session:
            await self.session.close()
            self.session = None
            logger.debug("AsyncHttpClient session closed")

    async def post_json(
        self,
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Make async POST request with JSON data.

        Optimized for LLM API calls with intelligent retry and error handling.
        """
        if not self.session:
            await self.start()

        headers = headers or {}
        headers["Content-Type"] = "application/json"

        timeout = timeout or self.request_timeout
        retry_count = 0
        last_exception = None

        while retry_count <= max_retries:
            start_time = time.time()

            try:
                async with self.session.post(
                    url,
                    json=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    response_time = time.time() - start_time
                    self.request_count += 1
                    self.total_response_time += response_time

                    if response.status == 200:
                        result = await response.json()
                        logger.debug(
                            f"HTTP POST success: {url} in {response_time:.3f}s"
                        )
                        return result
                    else:
                        error_text = await response.text()
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"HTTP {response.status}: {error_text}",
                        )

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                self.error_count += 1
                last_exception = e

                if retry_count < max_retries:
                    retry_count += 1
                    wait_time = 2**retry_count  # Exponential backoff
                    logger.warning(
                        f"HTTP POST retry {retry_count}/{max_retries} for {url}: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"HTTP POST failed after {max_retries} retries: {url} - {e}"
                    )
                    raise

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception

    async def get_json(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """Make async GET request for JSON data."""
        if not self.session:
            await self.start()

        timeout = timeout or self.request_timeout
        retry_count = 0
        last_exception = None

        while retry_count <= max_retries:
            start_time = time.time()

            try:
                async with self.session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    response_time = time.time() - start_time
                    self.request_count += 1
                    self.total_response_time += response_time

                    if response.status == 200:
                        result = await response.json()
                        logger.debug(f"HTTP GET success: {url} in {response_time:.3f}s")
                        return result
                    else:
                        error_text = await response.text()
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"HTTP {response.status}: {error_text}",
                        )

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                self.error_count += 1
                last_exception = e

                if retry_count < max_retries:
                    retry_count += 1
                    wait_time = 2**retry_count
                    logger.warning(
                        f"HTTP GET retry {retry_count}/{max_retries} for {url}: {e}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"HTTP GET failed after {max_retries} retries: {url} - {e}"
                    )
                    raise

        if last_exception:
            raise last_exception

    def get_stats(self) -> Dict[str, Any]:
        """Get HTTP client statistics."""
        avg_response_time = (
            (self.total_response_time / self.request_count)
            if self.request_count > 0
            else 0
        )
        error_rate = (self.error_count / max(1, self.request_count)) * 100

        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate_percent": error_rate,
            "avg_response_time_ms": avg_response_time * 1000,
            "active": self.session is not None,
            "connection_pool_size": self.max_connections,
        }


class AsyncFileOperations:
    """
    High-performance async file operations for non-blocking I/O.

    Eliminates file I/O blocking that was causing performance bottlenecks.
    """

    @staticmethod
    async def read_json(file_path: str) -> Dict[str, Any]:
        """Read JSON file asynchronously."""
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Async JSON read failed: {file_path} - {e}")
            raise

    @staticmethod
    async def write_json(file_path: str, data: Dict[str, Any]) -> bool:
        """Write JSON file asynchronously."""
        try:
            content = json.dumps(data, indent=2, ensure_ascii=False)
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)
            return True
        except Exception as e:
            logger.error(f"Async JSON write failed: {file_path} - {e}")
            return False

    @staticmethod
    async def read_text(file_path: str) -> str:
        """Read text file asynchronously."""
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Async text read failed: {file_path} - {e}")
            raise

    @staticmethod
    async def write_text(file_path: str, content: str) -> bool:
        """Write text file asynchronously."""
        try:
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)
            return True
        except Exception as e:
            logger.error(f"Async text write failed: {file_path} - {e}")
            return False

    @staticmethod
    async def append_text(file_path: str, content: str) -> bool:
        """Append to text file asynchronously."""
        try:
            async with aiofiles.open(file_path, "a", encoding="utf-8") as f:
                await f.write(content)
            return True
        except Exception as e:
            logger.error(f"Async text append failed: {file_path} - {e}")
            return False

    @staticmethod
    async def read_binary(file_path: str) -> bytes:
        """Read binary file asynchronously."""
        try:
            async with aiofiles.open(file_path, "rb") as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Async binary read failed: {file_path} - {e}")
            raise

    @staticmethod
    async def write_binary(file_path: str, data: bytes) -> bool:
        """Write binary file asynchronously."""
        try:
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(data)
            return True
        except Exception as e:
            logger.error(f"Async binary write failed: {file_path} - {e}")
            return False

    @staticmethod
    async def batch_write_json(
        file_operations: List[Tuple[str, Dict[str, Any]]],
    ) -> List[bool]:
        """Batch write multiple JSON files concurrently."""
        tasks = [
            AsyncFileOperations.write_json(file_path, data)
            for file_path, data in file_operations
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    async def batch_read_json(file_paths: List[str]) -> List[Dict[str, Any]]:
        """Batch read multiple JSON files concurrently."""
        tasks = [AsyncFileOperations.read_json(file_path) for file_path in file_paths]
        return await asyncio.gather(*tasks, return_exceptions=True)


class ConcurrentAgentProcessor:
    """
    Concurrent processor for PersonaAgent operations with intelligent load balancing.

    Eliminates agent processing bottlenecks through optimized concurrency.
    """

    def __init__(self, max_concurrent_agents: int = 20):
        self.max_concurrent_agents = max_concurrent_agents
        self.semaphore = asyncio.Semaphore(max_concurrent_agents)
        self.http_client = AsyncHttpClient()

        self.processing_stats = {
            "total_processed": 0,
            "successful_processing": 0,
            "failed_processing": 0,
            "avg_processing_time": 0.0,
            "concurrent_peak": 0,
        }

        self.processing_times = deque(maxlen=1000)
        self.current_processing = 0

        logger.info(
            f"ConcurrentAgentProcessor initialized: max_concurrent={max_concurrent_agents}"
        )

    async def process_agents_concurrently(
        self, agent_tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Process multiple agent tasks concurrently with intelligent load balancing.

        Args:
            agent_tasks: List of agent task dictionaries with 'agent_id', 'operation', 'data'

        Returns:
            List of processing results
        """
        if not agent_tasks:
            return []

        # Start HTTP client
        await self.http_client.start()

        try:
            # Create concurrent tasks
            processing_tasks = [
                self._process_single_agent(task) for task in agent_tasks
            ]

            # Execute with progress tracking
            results = await asyncio.gather(*processing_tasks, return_exceptions=True)

            # Process results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(
                        {
                            "agent_id": agent_tasks[i].get("agent_id", "unknown"),
                            "success": False,
                            "error": str(result),
                        }
                    )
                    self.processing_stats["failed_processing"] += 1
                else:
                    processed_results.append(result)
                    self.processing_stats["successful_processing"] += 1

                self.processing_stats["total_processed"] += 1

            return processed_results

        finally:
            await self.http_client.close()

    async def _process_single_agent(self, agent_task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single agent task with resource management."""
        async with self.semaphore:
            self.current_processing += 1
            self.processing_stats["concurrent_peak"] = max(
                self.processing_stats["concurrent_peak"], self.current_processing
            )

            start_time = time.time()

            try:
                agent_id = agent_task.get("agent_id", "unknown")
                operation = agent_task.get("operation", "unknown")

                # Simulate different operations
                if operation == "llm_decision":
                    result = await self._process_llm_decision(agent_task)
                elif operation == "world_state_update":
                    result = await self._process_world_state_update(agent_task)
                elif operation == "interaction_processing":
                    result = await self._process_interaction(agent_task)
                else:
                    result = await self._process_generic_operation(agent_task)

                processing_time = time.time() - start_time
                self.processing_times.append(processing_time)

                # Update average processing time
                if self.processing_times:
                    self.processing_stats["avg_processing_time"] = sum(
                        self.processing_times
                    ) / len(self.processing_times)

                return {
                    "agent_id": agent_id,
                    "operation": operation,
                    "success": True,
                    "result": result,
                    "processing_time_ms": processing_time * 1000,
                }

            except Exception as e:
                logger.error(
                    f"Agent processing failed: {agent_task.get('agent_id')} - {e}"
                )
                return {
                    "agent_id": agent_task.get("agent_id", "unknown"),
                    "operation": agent_task.get("operation", "unknown"),
                    "success": False,
                    "error": str(e),
                }
            finally:
                self.current_processing -= 1

    async def _process_llm_decision(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process LLM decision task (optimized async version)."""
        # Simulate async LLM API call
        await asyncio.sleep(0.01)  # Simulate network latency

        return {
            "decision": "investigate",
            "confidence": 0.85,
            "reasoning": f"Async LLM decision for {task.get('agent_id')}",
            "timestamp": datetime.now().isoformat(),
        }

    async def _process_world_state_update(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process world state update task."""
        # Simulate async database operation
        await asyncio.sleep(0.005)

        return {
            "state_updated": True,
            "changes": ["location_update", "discovery_added"],
            "timestamp": datetime.now().isoformat(),
        }

    async def _process_interaction(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process agent interaction task."""
        # Simulate async interaction processing
        await asyncio.sleep(0.008)

        return {
            "interaction_processed": True,
            "response": f"Interaction response for {task.get('agent_id')}",
            "timestamp": datetime.now().isoformat(),
        }

    async def _process_generic_operation(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process generic agent operation."""
        await asyncio.sleep(0.003)

        return {"operation_completed": True, "timestamp": datetime.now().isoformat()}

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get concurrent processing statistics."""
        success_rate = 0
        if self.processing_stats["total_processed"] > 0:
            success_rate = (
                self.processing_stats["successful_processing"]
                / self.processing_stats["total_processed"]
            ) * 100

        return {
            **self.processing_stats,
            "success_rate_percent": success_rate,
            "avg_processing_time_ms": self.processing_stats["avg_processing_time"]
            * 1000,
            "current_processing": self.current_processing,
            "max_concurrent": self.max_concurrent_agents,
        }


# Global instances
_global_task_scheduler: Optional[AsyncTaskScheduler] = None
_global_http_client: Optional[AsyncHttpClient] = None
_global_agent_processor: Optional[ConcurrentAgentProcessor] = None


async def get_task_scheduler() -> AsyncTaskScheduler:
    """Get or create global task scheduler."""
    global _global_task_scheduler
    if _global_task_scheduler is None:
        _global_task_scheduler = AsyncTaskScheduler()
        await _global_task_scheduler.start()
    return _global_task_scheduler


async def get_http_client() -> AsyncHttpClient:
    """Get or create global HTTP client."""
    global _global_http_client
    if _global_http_client is None:
        _global_http_client = AsyncHttpClient()
        await _global_http_client.start()
    return _global_http_client


async def get_agent_processor() -> ConcurrentAgentProcessor:
    """Get or create global agent processor."""
    global _global_agent_processor
    if _global_agent_processor is None:
        _global_agent_processor = ConcurrentAgentProcessor()
    return _global_agent_processor


async def setup_async_processing() -> Dict[str, Any]:
    """Setup comprehensive async processing system."""
    scheduler = await get_task_scheduler()
    http_client = await get_http_client()
    agent_processor = await get_agent_processor()

    logger.info("Async processing system setup completed")

    return {
        "task_scheduler": scheduler,
        "http_client": http_client,
        "agent_processor": agent_processor,
        "status": "active",
    }


async def get_async_processing_report() -> Dict[str, Any]:
    """Get comprehensive async processing performance report."""
    report = {"timestamp": datetime.now().isoformat(), "status": "active"}

    # Task scheduler stats
    if _global_task_scheduler:
        report["task_scheduler"] = _global_task_scheduler.get_status()

    # HTTP client stats
    if _global_http_client:
        report["http_client"] = _global_http_client.get_stats()

    # Agent processor stats
    if _global_agent_processor:
        report["agent_processor"] = _global_agent_processor.get_processing_stats()

    # System resources
    process = psutil.Process()
    report["system_resources"] = {
        "memory_percent": process.memory_percent(),
        "cpu_percent": process.cpu_percent(),
        "threads": process.num_threads(),
        "open_files": len(process.open_files()),
    }

    return report


async def cleanup_async_processing():
    """Cleanup all async processing resources."""
    global _global_task_scheduler, _global_http_client, _global_agent_processor

    if _global_task_scheduler:
        await _global_task_scheduler.stop()
        _global_task_scheduler = None

    if _global_http_client:
        await _global_http_client.close()
        _global_http_client = None

    _global_agent_processor = None

    logger.info("Async processing cleanup completed")


# Context managers for easy usage
@asynccontextmanager
async def async_processing_context():
    """Context manager for async processing setup and cleanup."""
    try:
        setup_result = await setup_async_processing()
        yield setup_result
    finally:
        await cleanup_async_processing()
