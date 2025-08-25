"""
Queue Manager
=============

Interaction scheduling, priority management, and queue processing system.
Handles queuing, prioritization, and scheduling of interaction requests.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from queue import PriorityQueue
from concurrent.futures import ThreadPoolExecutor

from ..core.types import (
    InteractionContext, InteractionType, InteractionPriority,
    InteractionPhase, InteractionOutcome, InteractionEngineConfig
)

# Import enhanced core systems
try:
    from src.core.data_models import StandardResponse, ErrorInfo, CharacterState
    from src.core.types import AgentID
except ImportError:
    # Fallback for testing
    class StandardResponse:
        def __init__(self, success=True, data=None, error=None, metadata=None):
            self.success = success
            self.data = data or {}
            self.error = error
            self.metadata = metadata or {}
        
        def get(self, key, default=None):
            return getattr(self, key, default)
        
        def __getitem__(self, key):
            return getattr(self, key)
    
    class ErrorInfo:
        def __init__(self, code="", message="", recoverable=True):
            self.code = code
            self.message = message
            self.recoverable = recoverable
    
    CharacterState = dict
    AgentID = str

__all__ = ['QueueManager', 'QueuedInteraction', 'QueueStatus']


class QueueStatus(Enum):
    """Queue processing status."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEFERRED = "deferred"


@dataclass
class QueuedInteraction:
    """
    Queued interaction with scheduling information.
    """
    context: InteractionContext
    priority_score: float = 0.0
    queue_time: datetime = field(default_factory=datetime.now)
    scheduled_time: Optional[datetime] = None
    attempts: int = 0
    max_attempts: int = 3
    status: QueueStatus = QueueStatus.QUEUED
    processing_callback: Optional[Callable] = None
    completion_callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """Priority comparison for queue ordering (higher priority first)."""
        if not isinstance(other, QueuedInteraction):
            return NotImplemented
        return self.priority_score > other.priority_score


class QueueManager:
    """
    Interaction Queue and Scheduling Management System
    
    Responsibilities:
    - Queue interaction requests with priority handling
    - Schedule interactions based on resource availability
    - Manage concurrent interaction processing
    - Handle queue cleanup and maintenance
    - Provide queue monitoring and statistics
    """
    
    def __init__(self, config: InteractionEngineConfig,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize queue manager.
        
        Args:
            config: Interaction engine configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # Queue management
        self.interaction_queue: PriorityQueue = PriorityQueue(maxsize=self.config.max_queue_size)
        self.processing_interactions: Dict[str, QueuedInteraction] = {}
        self.completed_interactions: Dict[str, QueuedInteraction] = {}
        self.failed_interactions: Dict[str, QueuedInteraction] = {}
        
        # Scheduling state
        self.active_processors = 0
        self.max_concurrent = self.config.max_concurrent_interactions
        self.processing_lock = asyncio.Lock()
        
        # Queue statistics
        self.queue_stats = {
            "total_queued": 0,
            "total_processed": 0,
            "total_completed": 0,
            "total_failed": 0,
            "average_queue_time": 0.0,
            "average_processing_time": 0.0
        }
        
        # Priority scoring weights
        self.priority_weights = {
            InteractionPriority.CRITICAL: 1000,
            InteractionPriority.URGENT: 800,
            InteractionPriority.HIGH: 600,
            InteractionPriority.NORMAL: 400,
            InteractionPriority.LOW: 200
        }
        
        # Queue processing task
        self.queue_processor_task = None
        self.processing_active = False
        
        # Thread pool for concurrent processing
        self.executor = ThreadPoolExecutor(
            max_workers=self.max_concurrent
        ) if self.config.enable_parallel_processing else None
        
        self.logger.info(f"Queue manager initialized with max queue size: {self.config.max_queue_size}")
    
    async def queue_interaction(self, context: InteractionContext,
                               processing_callback: Optional[Callable] = None,
                               completion_callback: Optional[Callable] = None,
                               error_callback: Optional[Callable] = None) -> StandardResponse:
        """
        Queue an interaction for processing.
        
        Args:
            context: Interaction context to queue
            processing_callback: Optional callback for processing start
            completion_callback: Optional callback for processing completion
            error_callback: Optional callback for processing errors
            
        Returns:
            StandardResponse with queuing results
        """
        try:
            # Check queue capacity
            if self.interaction_queue.full():
                if self.config.auto_queue_cleanup:
                    await self._cleanup_completed_interactions()
                    if self.interaction_queue.full():
                        return StandardResponse(
                            success=False,
                            error=ErrorInfo(
                                code="QUEUE_FULL",
                                message="Interaction queue is full",
                                recoverable=True
                            )
                        )
            
            # Calculate priority score
            priority_score = self._calculate_priority_score(context)
            
            # Create queued interaction
            queued_interaction = QueuedInteraction(
                context=context,
                priority_score=priority_score,
                processing_callback=processing_callback,
                completion_callback=completion_callback,
                error_callback=error_callback
            )
            
            # Add to queue
            self.interaction_queue.put_nowait(queued_interaction)
            self.queue_stats["total_queued"] += 1
            
            self.logger.info(f"Interaction queued: {context.interaction_id} (priority: {priority_score})")
            
            # Start queue processing if not active
            if not self.processing_active:
                await self.start_queue_processing()
            
            return StandardResponse(
                success=True,
                data={
                    "interaction_id": context.interaction_id,
                    "priority_score": priority_score,
                    "queue_position": self.interaction_queue.qsize(),
                    "estimated_wait_time": self._estimate_wait_time(priority_score)
                },
                metadata={"blessing": "interaction_queued"}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to queue interaction: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="QUEUE_ERROR",
                    message=f"Failed to queue interaction: {str(e)}",
                    recoverable=True
                )
            )
    
    async def start_queue_processing(self) -> StandardResponse:
        """
        Start the queue processing loop.
        
        Returns:
            StandardResponse with processing start results
        """
        try:
            if self.processing_active:
                return StandardResponse(
                    success=True,
                    data={"status": "already_active"},
                    metadata={"blessing": "queue_processing_active"}
                )
            
            self.processing_active = True
            self.queue_processor_task = asyncio.create_task(self._queue_processing_loop())
            
            self.logger.info("Queue processing started")
            
            return StandardResponse(
                success=True,
                data={"status": "started"},
                metadata={"blessing": "queue_processing_started"}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to start queue processing: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="QUEUE_START_ERROR",
                    message=f"Failed to start queue processing: {str(e)}",
                    recoverable=True
                )
            )
    
    async def stop_queue_processing(self) -> StandardResponse:
        """
        Stop the queue processing loop.
        
        Returns:
            StandardResponse with processing stop results
        """
        try:
            self.processing_active = False
            
            if self.queue_processor_task:
                self.queue_processor_task.cancel()
                try:
                    await self.queue_processor_task
                except asyncio.CancelledError:
                    pass
                self.queue_processor_task = None
            
            self.logger.info("Queue processing stopped")
            
            return StandardResponse(
                success=True,
                data={"status": "stopped"},
                metadata={"blessing": "queue_processing_stopped"}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to stop queue processing: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="QUEUE_STOP_ERROR",
                    message=f"Failed to stop queue processing: {str(e)}",
                    recoverable=True
                )
            )
    
    async def cancel_interaction(self, interaction_id: str) -> StandardResponse:
        """
        Cancel a queued or processing interaction.
        
        Args:
            interaction_id: ID of interaction to cancel
            
        Returns:
            StandardResponse with cancellation results
        """
        try:
            # Check processing interactions
            if interaction_id in self.processing_interactions:
                interaction = self.processing_interactions[interaction_id]
                interaction.status = QueueStatus.CANCELLED
                self.processing_interactions.pop(interaction_id)
                
                self.logger.info(f"Processing interaction cancelled: {interaction_id}")
                return StandardResponse(
                    success=True,
                    data={"status": "cancelled_processing"},
                    metadata={"blessing": "interaction_cancelled"}
                )
            
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="INTERACTION_NOT_FOUND",
                    message=f"Interaction not found: {interaction_id}",
                    recoverable=False
                )
            )
            
        except Exception as e:
            self.logger.error(f"Failed to cancel interaction: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="CANCELLATION_ERROR",
                    message=f"Failed to cancel interaction: {str(e)}",
                    recoverable=True
                )
            )
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get current queue status and statistics.
        
        Returns:
            Dict with queue status information
        """
        return {
            "queue_size": self.interaction_queue.qsize(),
            "max_queue_size": self.config.max_queue_size,
            "processing_count": len(self.processing_interactions),
            "max_concurrent": self.max_concurrent,
            "completed_count": len(self.completed_interactions),
            "failed_count": len(self.failed_interactions),
            "processing_active": self.processing_active,
            **self.queue_stats
        }
    
    def get_interaction_status(self, interaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of specific interaction.
        
        Args:
            interaction_id: ID of interaction to check
            
        Returns:
            Dict with interaction status or None if not found
        """
        # Check processing
        if interaction_id in self.processing_interactions:
            interaction = self.processing_interactions[interaction_id]
            return {
                "interaction_id": interaction_id,
                "status": interaction.status.value,
                "priority_score": interaction.priority_score,
                "queue_time": interaction.queue_time,
                "attempts": interaction.attempts,
                "location": "processing"
            }
        
        # Check completed
        if interaction_id in self.completed_interactions:
            interaction = self.completed_interactions[interaction_id]
            return {
                "interaction_id": interaction_id,
                "status": interaction.status.value,
                "priority_score": interaction.priority_score,
                "queue_time": interaction.queue_time,
                "attempts": interaction.attempts,
                "location": "completed"
            }
        
        # Check failed
        if interaction_id in self.failed_interactions:
            interaction = self.failed_interactions[interaction_id]
            return {
                "interaction_id": interaction_id,
                "status": interaction.status.value,
                "priority_score": interaction.priority_score,
                "queue_time": interaction.queue_time,
                "attempts": interaction.attempts,
                "location": "failed"
            }
        
        return None
    
    async def clear_queue(self) -> StandardResponse:
        """
        Clear all interactions from queue.
        
        Returns:
            StandardResponse with clear results
        """
        try:
            cleared_count = self.interaction_queue.qsize()
            
            # Clear queue
            while not self.interaction_queue.empty():
                try:
                    self.interaction_queue.get_nowait()
                except:
                    break
            
            self.logger.info(f"Queue cleared: {cleared_count} interactions removed")
            
            return StandardResponse(
                success=True,
                data={"cleared_count": cleared_count},
                metadata={"blessing": "queue_cleared"}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to clear queue: {e}")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="QUEUE_CLEAR_ERROR",
                    message=f"Failed to clear queue: {str(e)}",
                    recoverable=True
                )
            )
    
    # Private processing methods
    
    async def _queue_processing_loop(self):
        """
        Main queue processing loop.
        """
        try:
            while self.processing_active:
                try:
                    # Check if we can process more interactions
                    async with self.processing_lock:
                        if self.active_processors >= self.max_concurrent:
                            await asyncio.sleep(0.1)
                            continue
                    
                    # Get next interaction from queue
                    try:
                        queued_interaction = self.interaction_queue.get_nowait()
                    except:
                        # Queue empty, wait and continue
                        await asyncio.sleep(0.5)
                        continue
                    
                    # Check if interaction was cancelled
                    if queued_interaction.status == QueueStatus.CANCELLED:
                        continue
                    
                    # Start processing
                    asyncio.create_task(self._process_queued_interaction(queued_interaction))
                    
                except Exception as e:
                    self.logger.error(f"Error in queue processing loop: {e}")
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            self.logger.info("Queue processing loop cancelled")
        except Exception as e:
            self.logger.error(f"Queue processing loop failed: {e}")
    
    async def _process_queued_interaction(self, queued_interaction: QueuedInteraction):
        """
        Process a single queued interaction.
        """
        try:
            async with self.processing_lock:
                self.active_processors += 1
                self.processing_interactions[queued_interaction.context.interaction_id] = queued_interaction
            
            queued_interaction.status = QueueStatus.PROCESSING
            queued_interaction.attempts += 1
            
            # Call processing callback
            if queued_interaction.processing_callback:
                try:
                    await queued_interaction.processing_callback(queued_interaction.context)
                except Exception as e:
                    self.logger.warning(f"Processing callback failed: {e}")
            
            # Simulate processing (in real implementation, would call interaction processor)
            await asyncio.sleep(0.1)  # Simulate processing time
            processing_success = True  # Simulate success
            
            # Handle completion
            if processing_success:
                queued_interaction.status = QueueStatus.COMPLETED
                self.completed_interactions[queued_interaction.context.interaction_id] = queued_interaction
                self.queue_stats["total_completed"] += 1
                
                # Call completion callback
                if queued_interaction.completion_callback:
                    try:
                        await queued_interaction.completion_callback(queued_interaction.context)
                    except Exception as e:
                        self.logger.warning(f"Completion callback failed: {e}")
            else:
                # Handle failure
                if queued_interaction.attempts < queued_interaction.max_attempts:
                    # Retry
                    queued_interaction.status = QueueStatus.QUEUED
                    self.interaction_queue.put_nowait(queued_interaction)
                else:
                    # Max attempts reached
                    queued_interaction.status = QueueStatus.FAILED
                    self.failed_interactions[queued_interaction.context.interaction_id] = queued_interaction
                    self.queue_stats["total_failed"] += 1
                    
                    # Call error callback
                    if queued_interaction.error_callback:
                        try:
                            await queued_interaction.error_callback(queued_interaction.context)
                        except Exception as e:
                            self.logger.warning(f"Error callback failed: {e}")
            
            # Update statistics
            self.queue_stats["total_processed"] += 1
            queue_time = (datetime.now() - queued_interaction.queue_time).total_seconds()
            self._update_queue_time_stats(queue_time)
            
        except Exception as e:
            self.logger.error(f"Failed to process queued interaction: {e}")
            queued_interaction.status = QueueStatus.FAILED
            self.failed_interactions[queued_interaction.context.interaction_id] = queued_interaction
            self.queue_stats["total_failed"] += 1
        
        finally:
            # Cleanup
            async with self.processing_lock:
                self.active_processors -= 1
                self.processing_interactions.pop(queued_interaction.context.interaction_id, None)
    
    async def _cleanup_completed_interactions(self):
        """
        Clean up old completed and failed interactions.
        """
        try:
            cleanup_time = datetime.now() - timedelta(hours=1)
            
            # Clean completed interactions
            to_remove = [
                interaction_id for interaction_id, interaction in self.completed_interactions.items()
                if interaction.queue_time < cleanup_time
            ]
            
            for interaction_id in to_remove:
                self.completed_interactions.pop(interaction_id, None)
            
            # Clean failed interactions
            to_remove = [
                interaction_id for interaction_id, interaction in self.failed_interactions.items()
                if interaction.queue_time < cleanup_time
            ]
            
            for interaction_id in to_remove:
                self.failed_interactions.pop(interaction_id, None)
            
            if to_remove:
                self.logger.info(f"Cleaned up {len(to_remove)} old interactions")
                
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
    
    def _calculate_priority_score(self, context: InteractionContext) -> float:
        """
        Calculate priority score for interaction.
        """
        base_score = self.priority_weights.get(context.priority, 400)
        
        # Modify based on interaction type
        type_modifiers = {
            InteractionType.EMERGENCY: 200,
            InteractionType.COMBAT: 100,
            InteractionType.NEGOTIATION: 50,
            InteractionType.DIALOGUE: 0,
            InteractionType.MAINTENANCE: -50
        }
        
        base_score += type_modifiers.get(context.interaction_type, 0)
        
        # Modify based on participant count
        base_score += len(context.participants) * 10
        
        # Add time decay for older interactions
        age_bonus = min(100, (datetime.now() - datetime.now()).total_seconds() * 0.1)
        base_score += age_bonus
        
        return base_score
    
    def _estimate_wait_time(self, priority_score: float) -> float:
        """
        Estimate wait time for interaction based on priority.
        """
        # Simple estimation based on queue position and processing capacity
        queue_size = self.interaction_queue.qsize()
        processing_capacity = self.max_concurrent
        average_processing_time = max(1.0, self.queue_stats["average_processing_time"])
        
        # Estimate position in queue based on priority
        estimated_position = queue_size * 0.5  # Simplified estimation
        
        return (estimated_position / processing_capacity) * average_processing_time
    
    def _update_queue_time_stats(self, queue_time: float):
        """
        Update queue time statistics.
        """
        total_processed = self.queue_stats["total_processed"]
        if total_processed > 0:
            current_avg = self.queue_stats["average_queue_time"]
            self.queue_stats["average_queue_time"] = (
                (current_avg * (total_processed - 1)) + queue_time
            ) / total_processed
    
    def __del__(self):
        """
        Cleanup resources on destruction.
        """
        if self.executor:
            self.executor.shutdown(wait=True)