#!/usr/bin/env python3
"""
Advanced Concurrent Processing System for Novel Engine - Iteration 2.

This module implements sophisticated concurrent processing capabilities including
optimized thread/process pools, intelligent task scheduling, load balancing,
and adaptive resource management for maximum performance.
"""

import asyncio
import threading
import multiprocessing as mp
import time
import logging
import os
import sys
import weakref
from typing import (
    Any, Dict, List, Optional, Union, Callable, Awaitable, TypeVar, Generic,
    Tuple, Set, Coroutine
)
from dataclasses import dataclass, field
from collections import deque, defaultdict
from concurrent.futures import (
    ThreadPoolExecutor, ProcessPoolExecutor, Future, as_completed, wait,
    FIRST_COMPLETED, ALL_COMPLETED
)
from enum import Enum
import queue
import psutil
from functools import wraps, partial
import pickle
import traceback
import signal

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')

class TaskPriority(Enum):
    """Task priority levels for intelligent scheduling."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class TaskType(Enum):
    """Types of tasks for optimal executor assignment."""
    CPU_BOUND = "cpu_bound"
    IO_BOUND = "io_bound"
    MIXED = "mixed"
    ASYNC = "async"

@dataclass
class TaskMetrics:
    """Metrics for task execution monitoring."""
    task_id: str
    priority: TaskPriority
    task_type: TaskType
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    success: bool = False
    error: Optional[str] = None
    worker_id: Optional[str] = None
    memory_usage: float = 0.0
    cpu_usage: float = 0.0

@dataclass
class ConcurrentTask:
    """Represents a task for concurrent execution."""
    task_id: str
    func: Callable
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    task_type: TaskType = TaskType.MIXED
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 0
    callback: Optional[Callable] = None
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"task_{id(self)}_{int(time.time() * 1000000)}"

class AdaptiveThreadPool:
    """Adaptive thread pool that adjusts size based on workload."""
    
    def __init__(self, min_workers: int = 2, max_workers: int = None,
                 auto_scale: bool = True, scale_interval: int = 30):
        self.min_workers = min_workers
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) + 4)
        self.auto_scale = auto_scale
        self.scale_interval = scale_interval
        
        self.executor = ThreadPoolExecutor(max_workers=self.min_workers)
        self.current_workers = self.min_workers
        self.task_queue_size = 0
        self.active_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        
        self.metrics = {
            'total_tasks': 0,
            'avg_execution_time': 0.0,
            'queue_wait_time': 0.0,
            'worker_utilization': 0.0
        }
        
        self.scaling_lock = threading.Lock()
        self.last_scale_time = time.time()
        
        if auto_scale:
            self._start_scaling_monitor()
    
    def _start_scaling_monitor(self):
        """Start background thread for automatic scaling."""
        def monitor():
            while self.auto_scale:
                try:
                    time.sleep(self.scale_interval)
                    self._evaluate_scaling()
                except Exception as e:
                    logger.error(f"Scaling monitor error: {e}")
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def _evaluate_scaling(self):
        """Evaluate whether to scale up or down."""
        with self.scaling_lock:
            if time.time() - self.last_scale_time < self.scale_interval:
                return
            
            # Calculate metrics
            utilization = self.active_tasks / self.current_workers
            queue_pressure = self.task_queue_size / max(self.current_workers, 1)
            
            # Scale up conditions
            if (utilization > 0.8 and queue_pressure > 2.0 and 
                self.current_workers < self.max_workers):
                self._scale_up()
            
            # Scale down conditions
            elif (utilization < 0.3 and queue_pressure < 0.5 and 
                  self.current_workers > self.min_workers):
                self._scale_down()
    
    def _scale_up(self):
        """Scale up the thread pool."""
        new_size = min(self.current_workers + 2, self.max_workers)
        if new_size > self.current_workers:
            self.executor._max_workers = new_size
            self.current_workers = new_size
            self.last_scale_time = time.time()
            logger.info(f"Scaled thread pool up to {new_size} workers")
    
    def _scale_down(self):
        """Scale down the thread pool."""
        new_size = max(self.current_workers - 1, self.min_workers)
        if new_size < self.current_workers:
            # Note: ThreadPoolExecutor doesn't support dynamic scaling down
            # This would require a custom implementation
            self.current_workers = new_size
            self.last_scale_time = time.time()
            logger.info(f"Scaled thread pool down to {new_size} workers")
    
    def submit(self, fn: Callable, *args, **kwargs) -> Future:
        """Submit a task to the thread pool."""
        self.task_queue_size += 1
        self.active_tasks += 1
        
        def wrapped_fn(*args, **kwargs):
            try:
                start_time = time.time()
                result = fn(*args, **kwargs)
                duration = time.time() - start_time
                
                self.completed_tasks += 1
                self._update_metrics(duration)
                return result
            except Exception as e:
                self.failed_tasks += 1
                raise
            finally:
                self.active_tasks -= 1
                self.task_queue_size = max(0, self.task_queue_size - 1)
        
        return self.executor.submit(wrapped_fn, *args, **kwargs)
    
    def _update_metrics(self, duration: float):
        """Update execution metrics."""
        self.metrics['total_tasks'] += 1
        
        # Update rolling average
        alpha = 0.1  # Smoothing factor
        self.metrics['avg_execution_time'] = (
            alpha * duration + 
            (1 - alpha) * self.metrics['avg_execution_time']
        )
        
        self.metrics['worker_utilization'] = (
            self.active_tasks / self.current_workers
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get thread pool statistics."""
        return {
            'current_workers': self.current_workers,
            'min_workers': self.min_workers,
            'max_workers': self.max_workers,
            'active_tasks': self.active_tasks,
            'queue_size': self.task_queue_size,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'metrics': self.metrics.copy()
        }
    
    def shutdown(self, wait: bool = True):
        """Shutdown the thread pool."""
        self.auto_scale = False
        self.executor.shutdown(wait=wait)

class IntelligentTaskScheduler:
    """Intelligent task scheduler with priority queues and load balancing."""
    
    def __init__(self, max_concurrent_tasks: int = 100):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.priority_queues = {
            TaskPriority.CRITICAL: deque(),
            TaskPriority.HIGH: deque(),
            TaskPriority.NORMAL: deque(),
            TaskPriority.LOW: deque()
        }
        
        # Different executors for different task types
        self.thread_pool = AdaptiveThreadPool(min_workers=4, max_workers=16)
        self.process_pool = ProcessPoolExecutor(max_workers=min(4, os.cpu_count() or 1))
        self.io_pool = ThreadPoolExecutor(max_workers=8)
        
        self.active_tasks = {}
        self.completed_tasks = []
        self.task_metrics = {}
        
        self.scheduler_lock = asyncio.Lock()
        self.running = False
        self.scheduler_task = None
        
    async def start(self):
        """Start the task scheduler."""
        if self.running:
            return
        
        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Intelligent task scheduler started")
    
    async def stop(self):
        """Stop the task scheduler."""
        self.running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown executors
        self.thread_pool.shutdown()
        self.process_pool.shutdown()
        self.io_pool.shutdown()
        logger.info("Task scheduler stopped")
    
    async def submit_task(self, task: ConcurrentTask) -> str:
        """Submit a task for execution."""
        async with self.scheduler_lock:
            # Add to appropriate priority queue
            self.priority_queues[task.priority].append(task)
            logger.debug(f"Task {task.task_id} queued with priority {task.priority.name}")
            return task.task_id
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                await self._process_queue()
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(1)
    
    async def _process_queue(self):
        """Process tasks from priority queues."""
        if len(self.active_tasks) >= self.max_concurrent_tasks:
            return
        
        # Process queues in priority order
        for priority in [TaskPriority.CRITICAL, TaskPriority.HIGH, 
                        TaskPriority.NORMAL, TaskPriority.LOW]:
            
            queue = self.priority_queues[priority]
            while queue and len(self.active_tasks) < self.max_concurrent_tasks:
                task = queue.popleft()
                await self._execute_task(task)
    
    async def _execute_task(self, task: ConcurrentTask):
        """Execute a task using the appropriate executor."""
        metrics = TaskMetrics(
            task_id=task.task_id,
            priority=task.priority,
            task_type=task.task_type,
            start_time=time.time()
        )
        
        try:
            # Choose executor based on task type
            if task.task_type == TaskType.CPU_BOUND:
                executor = self.process_pool
            elif task.task_type == TaskType.IO_BOUND:
                executor = self.io_pool
            else:
                executor = self.thread_pool
            
            # Submit task
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                executor, 
                self._execute_with_monitoring, 
                task, metrics
            )
            
            self.active_tasks[task.task_id] = future
            
            # Set timeout if specified
            if task.timeout:
                future = asyncio.wait_for(future, timeout=task.timeout)
            
            # Handle completion
            asyncio.create_task(self._handle_task_completion(task, future, metrics))
            
        except Exception as e:
            metrics.error = str(e)
            metrics.success = False
            metrics.end_time = time.time()
            metrics.duration = metrics.end_time - metrics.start_time
            
            logger.error(f"Task {task.task_id} execution error: {e}")
            await self._handle_task_failure(task, e, metrics)
    
    def _execute_with_monitoring(self, task: ConcurrentTask, metrics: TaskMetrics) -> Any:
        """Execute task with resource monitoring."""
        process = psutil.Process()
        start_memory = process.memory_info().rss
        start_cpu_time = process.cpu_times()
        
        try:
            result = task.func(*task.args, **task.kwargs)
            metrics.success = True
            return result
        
        except Exception as e:
            metrics.error = str(e)
            metrics.success = False
            raise
        
        finally:
            # Calculate resource usage
            end_memory = process.memory_info().rss
            end_cpu_time = process.cpu_times()
            
            metrics.memory_usage = (end_memory - start_memory) / 1024 / 1024  # MB
            metrics.cpu_usage = (
                (end_cpu_time.user + end_cpu_time.system) - 
                (start_cpu_time.user + start_cpu_time.system)
            )
    
    async def _handle_task_completion(self, task: ConcurrentTask, 
                                    future: Future, metrics: TaskMetrics):
        """Handle task completion."""
        try:
            result = await future
            metrics.end_time = time.time()
            metrics.duration = metrics.end_time - metrics.start_time
            
            # Remove from active tasks
            self.active_tasks.pop(task.task_id, None)
            
            # Store metrics
            self.task_metrics[task.task_id] = metrics
            self.completed_tasks.append(task.task_id)
            
            # Call callback if provided
            if task.callback:
                try:
                    if asyncio.iscoroutinefunction(task.callback):
                        await task.callback(result)
                    else:
                        task.callback(result)
                except Exception as e:
                    logger.error(f"Task callback error: {e}")
            
            logger.debug(f"Task {task.task_id} completed in {metrics.duration:.3f}s")
            
        except asyncio.TimeoutError:
            await self._handle_task_timeout(task, metrics)
        except Exception as e:
            await self._handle_task_failure(task, e, metrics)
    
    async def _handle_task_failure(self, task: ConcurrentTask, 
                                 error: Exception, metrics: TaskMetrics):
        """Handle task failure with retry logic."""
        metrics.end_time = time.time()
        metrics.duration = metrics.end_time - metrics.start_time
        
        self.active_tasks.pop(task.task_id, None)
        
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            logger.warning(f"Task {task.task_id} failed, retrying ({task.retry_count}/{task.max_retries})")
            
            # Add back to queue with delay
            await asyncio.sleep(min(2 ** task.retry_count, 60))  # Exponential backoff
            await self.submit_task(task)
        else:
            logger.error(f"Task {task.task_id} failed permanently: {error}")
            self.task_metrics[task.task_id] = metrics
    
    async def _handle_task_timeout(self, task: ConcurrentTask, metrics: TaskMetrics):
        """Handle task timeout."""
        logger.warning(f"Task {task.task_id} timed out")
        metrics.error = "Timeout"
        metrics.success = False
        await self._handle_task_failure(task, TimeoutError("Task timeout"), metrics)
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task."""
        if task_id in self.active_tasks:
            return {
                'status': 'running',
                'task_id': task_id
            }
        elif task_id in self.task_metrics:
            metrics = self.task_metrics[task_id]
            return {
                'status': 'completed' if metrics.success else 'failed',
                'task_id': task_id,
                'duration': metrics.duration,
                'success': metrics.success,
                'error': metrics.error
            }
        else:
            return None
    
    async def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get comprehensive scheduler statistics."""
        queue_sizes = {
            priority.name: len(queue) 
            for priority, queue in self.priority_queues.items()
        }
        
        successful_tasks = sum(1 for m in self.task_metrics.values() if m.success)
        failed_tasks = sum(1 for m in self.task_metrics.values() if not m.success)
        
        if self.task_metrics:
            avg_duration = sum(m.duration for m in self.task_metrics.values()) / len(self.task_metrics)
            avg_memory = sum(m.memory_usage for m in self.task_metrics.values()) / len(self.task_metrics)
        else:
            avg_duration = 0.0
            avg_memory = 0.0
        
        return {
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'successful_tasks': successful_tasks,
            'failed_tasks': failed_tasks,
            'queue_sizes': queue_sizes,
            'avg_duration': avg_duration,
            'avg_memory_usage': avg_memory,
            'thread_pool_stats': self.thread_pool.get_stats()
        }

class AsyncBatchProcessor:
    """High-performance batch processor for similar tasks."""
    
    def __init__(self, batch_size: int = 10, max_wait_time: float = 1.0):
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.pending_tasks = []
        self.batch_lock = asyncio.Lock()
        self.batch_timer = None
        
    async def submit_for_batch(self, func: Callable, *args, **kwargs) -> Any:
        """Submit a task for batch processing."""
        future = asyncio.Future()
        task_item = (func, args, kwargs, future)
        
        async with self.batch_lock:
            self.pending_tasks.append(task_item)
            
            # Start timer if this is the first task
            if len(self.pending_tasks) == 1:
                self.batch_timer = asyncio.create_task(self._batch_timer())
            
            # Process immediately if batch is full
            if len(self.pending_tasks) >= self.batch_size:
                await self._process_batch()
        
        return await future
    
    async def _batch_timer(self):
        """Timer to process batch after max wait time."""
        try:
            await asyncio.sleep(self.max_wait_time)
            async with self.batch_lock:
                if self.pending_tasks:
                    await self._process_batch()
        except asyncio.CancelledError:
            pass
    
    async def _process_batch(self):
        """Process the current batch of tasks."""
        if not self.pending_tasks:
            return
        
        batch = self.pending_tasks.copy()
        self.pending_tasks.clear()
        
        # Cancel timer
        if self.batch_timer:
            self.batch_timer.cancel()
            self.batch_timer = None
        
        # Process batch concurrently
        tasks = []
        for func, args, kwargs, future in batch:
            task = asyncio.create_task(self._execute_task(func, args, kwargs, future))
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_task(self, func: Callable, args: tuple, 
                          kwargs: dict, future: asyncio.Future):
        """Execute a single task from the batch."""
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, func, *args, **kwargs)
            
            future.set_result(result)
        except Exception as e:
            future.set_exception(e)

# Decorators for easy concurrent processing
def concurrent_task(task_type: TaskType = TaskType.MIXED, 
                   priority: TaskPriority = TaskPriority.NORMAL,
                   timeout: Optional[float] = None,
                   max_retries: int = 0):
    """Decorator to mark a function for concurrent execution."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            task = ConcurrentTask(
                task_id=f"{func.__name__}_{int(time.time() * 1000000)}",
                func=func,
                args=args,
                kwargs=kwargs,
                task_type=task_type,
                priority=priority,
                timeout=timeout,
                max_retries=max_retries
            )
            
            # Get global scheduler (would be injected in real app)
            scheduler = getattr(async_wrapper, '_scheduler', None)
            if scheduler:
                task_id = await scheduler.submit_task(task)
                # Wait for completion (simplified for demo)
                while True:
                    status = await scheduler.get_task_status(task_id)
                    if status and status['status'] in ['completed', 'failed']:
                        if status['success']:
                            return status.get('result')
                        else:
                            raise Exception(status.get('error', 'Task failed'))
                    await asyncio.sleep(0.1)
            else:
                return await func(*args, **kwargs)
        
        return async_wrapper
    return decorator

def batch_process(batch_size: int = 10, max_wait_time: float = 1.0):
    """Decorator for automatic batch processing."""
    processor = AsyncBatchProcessor(batch_size, max_wait_time)
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await processor.submit_for_batch(func, *args, **kwargs)
        return wrapper
    return decorator

# Global instances
task_scheduler = IntelligentTaskScheduler()

async def setup_concurrent_processing():
    """Setup the concurrent processing system."""
    await task_scheduler.start()
    logger.info("Concurrent processing system initialized")

async def shutdown_concurrent_processing():
    """Shutdown the concurrent processing system."""
    await task_scheduler.stop()
    logger.info("Concurrent processing system shutdown")

if __name__ == "__main__":
    # Example usage and testing
    async def test_concurrent_processing():
        """Test the concurrent processing system."""
        await setup_concurrent_processing()
        
        # Test CPU-bound task
        def cpu_intensive_task(n: int) -> int:
            """Simulate CPU-intensive work."""
            total = 0
            for i in range(n * 1000000):
                total += i
            return total
        
        # Test I/O-bound task
        async def io_intensive_task(delay: float) -> str:
            """Simulate I/O-intensive work."""
            await asyncio.sleep(delay)
            return f"IO task completed after {delay}s"
        
        # Submit various tasks
        tasks = []
        
        # CPU-bound tasks
        for i in range(3):
            task = ConcurrentTask(
                task_id=f"cpu_task_{i}",
                func=cpu_intensive_task,
                args=(100,),
                task_type=TaskType.CPU_BOUND,
                priority=TaskPriority.HIGH
            )
            task_id = await task_scheduler.submit_task(task)
            tasks.append(task_id)
        
        # I/O-bound tasks
        for i in range(5):
            task = ConcurrentTask(
                task_id=f"io_task_{i}",
                func=lambda d=i*0.5: asyncio.run(io_intensive_task(d)),
                task_type=TaskType.IO_BOUND,
                priority=TaskPriority.NORMAL
            )
            task_id = await task_scheduler.submit_task(task)
            tasks.append(task_id)
        
        # Wait for some tasks to complete
        await asyncio.sleep(5)
        
        # Get statistics
        stats = await task_scheduler.get_scheduler_stats()
        print(f"Scheduler stats: {stats}")
        
        # Test batch processing
        @batch_process(batch_size=3, max_wait_time=2.0)
        async def batch_task(x: int) -> int:
            await asyncio.sleep(0.1)
            return x * x
        
        # Submit batch tasks
        batch_results = await asyncio.gather(*[
            batch_task(i) for i in range(5)
        ])
        print(f"Batch results: {batch_results}")
        
        await shutdown_concurrent_processing()
    
    # Run the test
    asyncio.run(test_concurrent_processing())