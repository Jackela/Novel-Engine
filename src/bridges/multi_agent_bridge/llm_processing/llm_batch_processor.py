"""
LLM Batch Processor
==================

Intelligent batching and processing of LLM requests for optimal performance and cost.
"""

import asyncio
import logging
import heapq
import time
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
from datetime import datetime
import threading

from ..core.types import LLMBatchRequest, RequestPriority
from ..performance.cost_tracker import CostTracker
from ..performance.performance_budget import PerformanceBudget

# Import unified LLM service
try:
    from src.llm_service import get_llm_service, LLMRequest, ResponseFormat
except ImportError:
    # Fallback for testing
    def get_llm_service():
        return None
    class LLMRequest:
        pass
    class ResponseFormat:
        pass

__all__ = ['LLMBatchProcessor']


class LLMBatchProcessor:
    """
    Intelligent LLM batch processing system.
    
    Responsibilities:
    - Queue and batch LLM requests by type and priority
    - Optimize request timing and resource utilization
    - Handle immediate vs batched processing decisions
    - Parse and distribute batch responses
    - Coordinate with cost and performance budgets
    """
    
    def __init__(self, cost_tracker: CostTracker, performance_budget: PerformanceBudget,
                 max_batch_size: int = 5, batch_timeout_ms: int = 150,
                 logger: Optional[logging.Logger] = None):
        self.cost_tracker = cost_tracker
        self.performance_budget = performance_budget
        self.max_batch_size = max_batch_size
        self.batch_timeout_ms = batch_timeout_ms
        self.logger = logger or logging.getLogger(__name__)
        
        # Request queuing
        self._request_queue: List[LLMBatchRequest] = []
        self._request_results: Dict[str, Dict[str, Any]] = {}
        self._queue_lock = threading.Lock()
        
        # Batching state
        self._batch_processor_running = False
        self._batch_processor_task: Optional[asyncio.Task] = None
        
        # LLM service
        self._llm_service = None
        
        # Statistics
        self._stats = {
            'total_requests': 0,
            'batched_requests': 0,
            'immediate_requests': 0,
            'successful_batches': 0,
            'failed_batches': 0,
            'avg_batch_size': 0.0,
            'avg_batch_time': 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize the batch processor."""
        try:
            self._llm_service = get_llm_service()
            if not self._llm_service:
                self.logger.warning("LLM service not available")
                return False
            
            # Start batch processor
            await self._start_batch_processor()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM batch processor: {e}")
            return False
    
    async def queue_llm_request(self, request_type: str, prompt: str, 
                              priority: RequestPriority = RequestPriority.NORMAL,
                              context: Optional[Dict[str, Any]] = None,
                              timeout_seconds: float = 30.0) -> str:
        """
        Queue an LLM request for processing.
        
        Args:
            request_type: Type of request ('dialogue', 'coordination', etc.)
            prompt: LLM prompt text
            priority: Request priority level
            context: Additional context data
            timeout_seconds: Maximum wait time
            
        Returns:
            str: Request ID for retrieving results
        """
        try:
            # Create batch request
            request_id = f"{request_type}_{int(time.time() * 1000000)}"
            batch_request = LLMBatchRequest(
                request_id=request_id,
                request_type=request_type,
                prompt=prompt,
                priority=priority,
                context=context or {},
                timeout_seconds=timeout_seconds,
                estimated_cost=self._estimate_request_cost(prompt)
            )
            
            # Check if we should process immediately
            if await self._should_process_immediately(batch_request):
                result = await self._process_immediate_request(batch_request)
                self._request_results[request_id] = result
                self._stats['immediate_requests'] += 1
            else:
                # Add to batch queue
                with self._queue_lock:
                    heapq.heappush(self._request_queue, batch_request)
                self._stats['batched_requests'] += 1
            
            self._stats['total_requests'] += 1
            return request_id
            
        except Exception as e:
            self.logger.error(f"Error queuing LLM request: {e}")
            raise
    
    async def wait_for_result(self, request_id: str, timeout_seconds: float = 30.0) -> Dict[str, Any]:
        """
        Wait for batch request result.
        
        Args:
            request_id: Request identifier
            timeout_seconds: Maximum wait time
            
        Returns:
            Dict containing the LLM result
        """
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout_seconds:
                if request_id in self._request_results:
                    result = self._request_results.pop(request_id)
                    return result
                
                await asyncio.sleep(0.01)  # Check every 10ms
            
            # Timeout
            self.logger.warning(f"Request {request_id} timed out after {timeout_seconds}s")
            return {'error': 'timeout', 'request_id': request_id}
            
        except Exception as e:
            self.logger.error(f"Error waiting for result {request_id}: {e}")
            return {'error': str(e), 'request_id': request_id}
    
    async def _should_process_immediately(self, batch_request: LLMBatchRequest) -> bool:
        """Determine if request should be processed immediately."""
        try:
            # Critical priority always immediate
            if batch_request.priority == RequestPriority.CRITICAL:
                return True
            
            # Check budget availability
            if not self.cost_tracker.is_under_budget(batch_request.estimated_cost):
                return False
            
            if not self.performance_budget.is_batch_budget_available():
                return False
            
            # High priority with low queue depth
            if (batch_request.priority == RequestPriority.HIGH and 
                len(self._request_queue) < 2):
                return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Error in immediate processing decision: {e}")
            return False
    
    async def _process_immediate_request(self, batch_request: LLMBatchRequest) -> Dict[str, Any]:
        """Process a single request immediately."""
        try:
            start_time = time.time()
            
            if not self._llm_service:
                return {'error': 'LLM service unavailable', 'request_id': batch_request.request_id}
            
            # Create LLM request
            llm_request = LLMRequest(
                prompt=batch_request.prompt,
                response_format=ResponseFormat.TEXT,
                max_tokens=2000,
                temperature=0.7
            )
            
            # Process request
            llm_response = await self._llm_service.process_request(llm_request)
            
            # Update tracking
            processing_time = time.time() - start_time
            self.performance_budget.record_llm_time(processing_time)
            
            if llm_response.success:
                self.cost_tracker.update_cost(
                    batch_request.request_type,
                    llm_response.cost,
                    llm_response.tokens_used
                )
                
                return {
                    'success': True,
                    'content': llm_response.content,
                    'cost': llm_response.cost,
                    'tokens': llm_response.tokens_used,
                    'processing_time': processing_time,
                    'request_id': batch_request.request_id
                }
            else:
                return {
                    'success': False,
                    'error': llm_response.error,
                    'request_id': batch_request.request_id
                }
            
        except Exception as e:
            self.logger.error(f"Error processing immediate request: {e}")
            return {'error': str(e), 'request_id': batch_request.request_id}
    
    async def _start_batch_processor(self) -> None:
        """Start the background batch processor."""
        if self._batch_processor_running:
            return
        
        self._batch_processor_running = True
        self._batch_processor_task = asyncio.create_task(self._batch_processor())
        self.logger.debug("Batch processor started")
    
    async def _batch_processor(self) -> None:
        """Main batch processing loop."""
        try:
            while self._batch_processor_running:
                await self._process_batch_cycle()
                await asyncio.sleep(self.batch_timeout_ms / 1000.0)
        except Exception as e:
            self.logger.error(f"Batch processor error: {e}")
        finally:
            self._batch_processor_running = False
    
    async def _process_batch_cycle(self) -> None:
        """Process one cycle of batch requests."""
        try:
            if not self._request_queue:
                return
            
            # Extract requests for batching
            batch_requests = []
            with self._queue_lock:
                while self._request_queue and len(batch_requests) < self.max_batch_size:
                    batch_requests.append(heapq.heappop(self._request_queue))
            
            if not batch_requests:
                return
            
            # Group by request type for optimal batching
            requests_by_type = defaultdict(list)
            for request in batch_requests:
                requests_by_type[request.request_type].append(request)
            
            # Process each type batch
            for request_type, type_requests in requests_by_type.items():
                await self._process_typed_batch(request_type, type_requests)
            
        except Exception as e:
            self.logger.error(f"Error in batch cycle: {e}")
    
    async def _process_typed_batch(self, request_type: str, requests: List[LLMBatchRequest]) -> None:
        """Process a batch of requests of the same type."""
        try:
            if not requests or not self._llm_service:
                return
            
            start_time = time.time()
            
            # Create batch prompt
            batch_prompt = self._create_batch_prompt(request_type, requests)
            
            # Create LLM request
            llm_request = LLMRequest(
                prompt=batch_prompt,
                response_format=ResponseFormat.TEXT,
                max_tokens=4000,
                temperature=0.7
            )
            
            # Process batch
            llm_response = await self._llm_service.process_request(llm_request)
            processing_time = time.time() - start_time
            
            # Track performance
            self.performance_budget.record_batch_time(processing_time)
            
            if llm_response.success:
                # Parse batch response
                parsed_results = self._parse_batch_response(llm_response.content, requests)
                
                # Update tracking
                self.cost_tracker.update_cost(request_type, llm_response.cost, llm_response.tokens_used)
                
                # Store results
                for i, request in enumerate(requests):
                    result = parsed_results[i] if i < len(parsed_results) else {'error': 'parsing_failed'}
                    result.update({
                        'success': True,
                        'cost': llm_response.cost / len(requests),  # Distribute cost
                        'tokens': llm_response.tokens_used // len(requests),
                        'processing_time': processing_time,
                        'request_id': request.request_id
                    })
                    self._request_results[request.request_id] = result
                
                self._stats['successful_batches'] += 1
                self._update_batch_stats(len(requests), processing_time)
                
            else:
                # Batch failed, store error for all requests
                error_result = {
                    'success': False,
                    'error': llm_response.error,
                    'processing_time': processing_time
                }
                
                for request in requests:
                    result = error_result.copy()
                    result['request_id'] = request.request_id
                    self._request_results[request.request_id] = result
                
                self._stats['failed_batches'] += 1
            
        except Exception as e:
            self.logger.error(f"Error processing typed batch {request_type}: {e}")
            
            # Store error for all requests
            for request in requests:
                self._request_results[request.request_id] = {
                    'success': False,
                    'error': str(e),
                    'request_id': request.request_id
                }
    
    def _create_batch_prompt(self, request_type: str, requests: List[LLMBatchRequest]) -> str:
        """Create optimized batch prompt for request type."""
        if request_type == 'dialogue':
            return self._create_dialogue_batch_prompt(requests)
        elif request_type == 'coordination':
            return self._create_coordination_batch_prompt(requests)
        else:
            return self._create_generic_batch_prompt(requests)
    
    def _create_dialogue_batch_prompt(self, requests: List[LLMBatchRequest]) -> str:
        """Create batch prompt optimized for dialogue requests."""
        batch_parts = ["# Dialogue Batch Processing", ""]
        
        for i, request in enumerate(requests):
            batch_parts.append(f"## Dialogue {i+1} (ID: {request.request_id})")
            batch_parts.append(request.prompt)
            batch_parts.append("")
        
        batch_parts.append("# Instructions")
        batch_parts.append("Process each dialogue independently and provide responses in order.")
        batch_parts.append("Format: **Response {number}:** [response content]")
        
        return "\n".join(batch_parts)
    
    def _create_coordination_batch_prompt(self, requests: List[LLMBatchRequest]) -> str:
        """Create batch prompt optimized for coordination requests."""
        batch_parts = ["# Agent Coordination Batch Processing", ""]
        
        for i, request in enumerate(requests):
            batch_parts.append(f"## Coordination Task {i+1} (ID: {request.request_id})")
            batch_parts.append(request.prompt)
            batch_parts.append("")
        
        batch_parts.append("# Instructions")
        batch_parts.append("Process each coordination task and provide strategic recommendations.")
        batch_parts.append("Format: **Coordination {number}:** [coordination response]")
        
        return "\n".join(batch_parts)
    
    def _create_generic_batch_prompt(self, requests: List[LLMBatchRequest]) -> str:
        """Create generic batch prompt."""
        batch_parts = ["# Batch Processing", ""]
        
        for i, request in enumerate(requests):
            batch_parts.append(f"## Request {i+1} (ID: {request.request_id})")
            batch_parts.append(request.prompt)
            batch_parts.append("")
        
        batch_parts.append("# Instructions")
        batch_parts.append("Process each request independently.")
        batch_parts.append("Format: **Response {number}:** [response content]")
        
        return "\n".join(batch_parts)
    
    def _parse_batch_response(self, response_content: str, requests: List[LLMBatchRequest]) -> List[Dict[str, Any]]:
        """Parse batch response into individual results."""
        try:
            results = []
            
            # Split response by response markers
            import re
            response_pattern = r'\*\*(?:Response|Dialogue|Coordination)\s+(\d+):\*\*\s*(.*?)(?=\*\*(?:Response|Dialogue|Coordination)\s+\d+:|\Z)'
            matches = re.findall(response_pattern, response_content, re.DOTALL | re.IGNORECASE)
            
            # Ensure we have results for all requests
            for i in range(len(requests)):
                if i < len(matches):
                    _, content = matches[i]
                    results.append({'content': content.strip()})
                else:
                    results.append({'content': 'No response generated', 'error': 'parsing_incomplete'})
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error parsing batch response: {e}")
            # Return error results for all requests
            return [{'error': 'parsing_failed'} for _ in requests]
    
    def _estimate_request_cost(self, prompt: str) -> float:
        """Estimate cost of a request based on prompt length."""
        # Simple estimation: ~750 chars per token, $0.03 per 1K tokens
        estimated_tokens = len(prompt) // 3  # Conservative estimate
        return (estimated_tokens / 1000) * 0.03
    
    def _update_batch_stats(self, batch_size: int, processing_time: float) -> None:
        """Update batch processing statistics."""
        try:
            # Update averages using running average
            total_batches = self._stats['successful_batches']
            
            current_avg_size = self._stats['avg_batch_size']
            current_avg_time = self._stats['avg_batch_time']
            
            self._stats['avg_batch_size'] = ((current_avg_size * (total_batches - 1)) + batch_size) / total_batches
            self._stats['avg_batch_time'] = ((current_avg_time * (total_batches - 1)) + processing_time) / total_batches
            
        except Exception as e:
            self.logger.debug(f"Error updating batch stats: {e}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics."""
        try:
            with self._queue_lock:
                queue_size = len(self._request_queue)
            
            stats = self._stats.copy()
            stats.update({
                'current_queue_size': queue_size,
                'pending_results': len(self._request_results),
                'processor_running': self._batch_processor_running,
                'batch_efficiency': self._calculate_batch_efficiency()
            })
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting processing stats: {e}")
            return {}
    
    def _calculate_batch_efficiency(self) -> float:
        """Calculate batch processing efficiency."""
        try:
            if self._stats['total_requests'] == 0:
                return 0.0
            
            # Efficiency = batched requests / total requests * 100
            batched_ratio = self._stats['batched_requests'] / self._stats['total_requests']
            return batched_ratio * 100
            
        except Exception:
            return 0.0
    
    async def shutdown(self) -> None:
        """Shutdown the batch processor gracefully."""
        try:
            self._batch_processor_running = False
            
            if self._batch_processor_task:
                self._batch_processor_task.cancel()
                try:
                    await self._batch_processor_task
                except asyncio.CancelledError:
                    pass
            
            # Process remaining requests
            if self._request_queue:
                self.logger.info(f"Processing {len(self._request_queue)} remaining requests")
                await self._process_batch_cycle()
            
            self.logger.info("LLM batch processor shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during batch processor shutdown: {e}")