"""
Queue Manager
=============

Interaction scheduling, priority management, and queue processing system.
Handles queuing, prioritization, and scheduling of interaction requests.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from queue import PriorityQueue
from typing import Any, Callable, Dict, List, Optional, Set

from ..core.types import (
    InteractionContext,
    InteractionEngineConfig,
    InteractionOutcome,
    InteractionPhase,
    InteractionPriority,
    InteractionType,
)

# Import enhanced core systems
try:
    from src.core.data_models import CharacterState, ErrorInfo, StandardResponse
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
        
        self.logger.info(f"Queue manager initialized with max queue size: {self.config.max_queue_size}")\n    \n    async def queue_interaction(self, context: InteractionContext,\n                               processing_callback: Optional[Callable] = None,\n                               completion_callback: Optional[Callable] = None,\n                               error_callback: Optional[Callable] = None) -> StandardResponse:\n        \"\"\"\n        Queue an interaction for processing.\n        \n        Args:\n            context: Interaction context to queue\n            processing_callback: Optional callback for processing start\n            completion_callback: Optional callback for processing completion\n            error_callback: Optional callback for processing errors\n            \n        Returns:\n            StandardResponse with queuing results\n        \"\"\"\n        try:\n            # Check queue capacity\n            if self.interaction_queue.full():\n                if self.config.auto_queue_cleanup:\n                    await self._cleanup_completed_interactions()\n                    if self.interaction_queue.full():\n                        return StandardResponse(\n                            success=False,\n                            error=ErrorInfo(\n                                code=\"QUEUE_FULL\",\n                                message=\"Interaction queue is full\",\n                                recoverable=True\n                            )\n                        )\n            \n            # Calculate priority score\n            priority_score = self._calculate_priority_score(context)\n            \n            # Create queued interaction\n            queued_interaction = QueuedInteraction(\n                context=context,\n                priority_score=priority_score,\n                processing_callback=processing_callback,\n                completion_callback=completion_callback,\n                error_callback=error_callback\n            )\n            \n            # Add to queue\n            self.interaction_queue.put_nowait(queued_interaction)\n            self.queue_stats[\"total_queued\"] += 1\n            \n            self.logger.info(f\"Interaction queued: {context.interaction_id} (priority: {priority_score})\")\n            \n            # Start queue processing if not active\n            if not self.processing_active:\n                await self.start_queue_processing()\n            \n            return StandardResponse(\n                success=True,\n                data={\n                    \"interaction_id\": context.interaction_id,\n                    \"priority_score\": priority_score,\n                    \"queue_position\": self.interaction_queue.qsize(),\n                    \"estimated_wait_time\": self._estimate_wait_time(priority_score)\n                },\n                metadata={\"blessing\": \"interaction_queued\"}\n            )\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to queue interaction: {e}\")\n            return StandardResponse(\n                success=False,\n                error=ErrorInfo(\n                    code=\"QUEUE_ERROR\",\n                    message=f\"Failed to queue interaction: {str(e)}\",\n                    recoverable=True\n                )\n            )\n    \n    async def start_queue_processing(self) -> StandardResponse:\n        \"\"\"\n        Start the queue processing loop.\n        \n        Returns:\n            StandardResponse with processing start results\n        \"\"\"\n        try:\n            if self.processing_active:\n                return StandardResponse(\n                    success=True,\n                    data={\"status\": \"already_active\"},\n                    metadata={\"blessing\": \"queue_processing_active\"}\n                )\n            \n            self.processing_active = True\n            self.queue_processor_task = asyncio.create_task(self._queue_processing_loop())\n            \n            self.logger.info(\"Queue processing started\")\n            \n            return StandardResponse(\n                success=True,\n                data={\"status\": \"started\"},\n                metadata={\"blessing\": \"queue_processing_started\"}\n            )\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to start queue processing: {e}\")\n            return StandardResponse(\n                success=False,\n                error=ErrorInfo(\n                    code=\"QUEUE_START_ERROR\",\n                    message=f\"Failed to start queue processing: {str(e)}\",\n                    recoverable=True\n                )\n            )\n    \n    async def stop_queue_processing(self) -> StandardResponse:\n        \"\"\"\n        Stop the queue processing loop.\n        \n        Returns:\n            StandardResponse with processing stop results\n        \"\"\"\n        try:\n            self.processing_active = False\n            \n            if self.queue_processor_task:\n                self.queue_processor_task.cancel()\n                try:\n                    await self.queue_processor_task\n                except asyncio.CancelledError:\n                    pass\n                self.queue_processor_task = None\n            \n            self.logger.info(\"Queue processing stopped\")\n            \n            return StandardResponse(\n                success=True,\n                data={\"status\": \"stopped\"},\n                metadata={\"blessing\": \"queue_processing_stopped\"}\n            )\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to stop queue processing: {e}\")\n            return StandardResponse(\n                success=False,\n                error=ErrorInfo(\n                    code=\"QUEUE_STOP_ERROR\",\n                    message=f\"Failed to stop queue processing: {str(e)}\",\n                    recoverable=True\n                )\n            )\n    \n    async def cancel_interaction(self, interaction_id: str) -> StandardResponse:\n        \"\"\"\n        Cancel a queued or processing interaction.\n        \n        Args:\n            interaction_id: ID of interaction to cancel\n            \n        Returns:\n            StandardResponse with cancellation results\n        \"\"\"\n        try:\n            # Check processing interactions\n            if interaction_id in self.processing_interactions:\n                interaction = self.processing_interactions[interaction_id]\n                interaction.status = QueueStatus.CANCELLED\n                self.processing_interactions.pop(interaction_id)\n                \n                self.logger.info(f\"Processing interaction cancelled: {interaction_id}\")\n                return StandardResponse(\n                    success=True,\n                    data={\"status\": \"cancelled_processing\"},\n                    metadata={\"blessing\": \"interaction_cancelled\"}\n                )\n            \n            # Check queue (more complex due to PriorityQueue structure)\n            # For simplicity, mark as cancelled and let processing loop handle it\n            # In full implementation, would need to reconstruct queue without cancelled item\n            \n            return StandardResponse(\n                success=False,\n                error=ErrorInfo(\n                    code=\"INTERACTION_NOT_FOUND\",\n                    message=f\"Interaction not found: {interaction_id}\",\n                    recoverable=False\n                )\n            )\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to cancel interaction: {e}\")\n            return StandardResponse(\n                success=False,\n                error=ErrorInfo(\n                    code=\"CANCELLATION_ERROR\",\n                    message=f\"Failed to cancel interaction: {str(e)}\",\n                    recoverable=True\n                )\n            )\n    \n    def get_queue_status(self) -> Dict[str, Any]:\n        \"\"\"\n        Get current queue status and statistics.\n        \n        Returns:\n            Dict with queue status information\n        \"\"\"\n        return {\n            \"queue_size\": self.interaction_queue.qsize(),\n            \"max_queue_size\": self.config.max_queue_size,\n            \"processing_count\": len(self.processing_interactions),\n            \"max_concurrent\": self.max_concurrent,\n            \"completed_count\": len(self.completed_interactions),\n            \"failed_count\": len(self.failed_interactions),\n            \"processing_active\": self.processing_active,\n            **self.queue_stats\n        }\n    \n    def get_interaction_status(self, interaction_id: str) -> Optional[Dict[str, Any]]:\n        \"\"\"\n        Get status of specific interaction.\n        \n        Args:\n            interaction_id: ID of interaction to check\n            \n        Returns:\n            Dict with interaction status or None if not found\n        \"\"\"\n        # Check processing\n        if interaction_id in self.processing_interactions:\n            interaction = self.processing_interactions[interaction_id]\n            return {\n                \"interaction_id\": interaction_id,\n                \"status\": interaction.status.value,\n                \"priority_score\": interaction.priority_score,\n                \"queue_time\": interaction.queue_time,\n                \"attempts\": interaction.attempts,\n                \"location\": \"processing\"\n            }\n        \n        # Check completed\n        if interaction_id in self.completed_interactions:\n            interaction = self.completed_interactions[interaction_id]\n            return {\n                \"interaction_id\": interaction_id,\n                \"status\": interaction.status.value,\n                \"priority_score\": interaction.priority_score,\n                \"queue_time\": interaction.queue_time,\n                \"attempts\": interaction.attempts,\n                \"location\": \"completed\"\n            }\n        \n        # Check failed\n        if interaction_id in self.failed_interactions:\n            interaction = self.failed_interactions[interaction_id]\n            return {\n                \"interaction_id\": interaction_id,\n                \"status\": interaction.status.value,\n                \"priority_score\": interaction.priority_score,\n                \"queue_time\": interaction.queue_time,\n                \"attempts\": interaction.attempts,\n                \"location\": \"failed\"\n            }\n        \n        return None\n    \n    async def clear_queue(self) -> StandardResponse:\n        \"\"\"\n        Clear all interactions from queue.\n        \n        Returns:\n            StandardResponse with clear results\n        \"\"\"\n        try:\n            cleared_count = self.interaction_queue.qsize()\n            \n            # Clear queue\n            while not self.interaction_queue.empty():\n                try:\n                    self.interaction_queue.get_nowait()\n                except:\n                    break\n            \n            self.logger.info(f\"Queue cleared: {cleared_count} interactions removed\")\n            \n            return StandardResponse(\n                success=True,\n                data={\"cleared_count\": cleared_count},\n                metadata={\"blessing\": \"queue_cleared\"}\n            )\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to clear queue: {e}\")\n            return StandardResponse(\n                success=False,\n                error=ErrorInfo(\n                    code=\"QUEUE_CLEAR_ERROR\",\n                    message=f\"Failed to clear queue: {str(e)}\",\n                    recoverable=True\n                )\n            )\n    \n    # Private processing methods\n    \n    async def _queue_processing_loop(self):\n        \"\"\"\n        Main queue processing loop.\n        \"\"\"\n        try:\n            while self.processing_active:\n                try:\n                    # Check if we can process more interactions\n                    async with self.processing_lock:\n                        if self.active_processors >= self.max_concurrent:\n                            await asyncio.sleep(0.1)\n                            continue\n                    \n                    # Get next interaction from queue\n                    try:\n                        queued_interaction = self.interaction_queue.get_nowait()\n                    except:\n                        # Queue empty, wait and continue\n                        await asyncio.sleep(0.5)\n                        continue\n                    \n                    # Check if interaction was cancelled\n                    if queued_interaction.status == QueueStatus.CANCELLED:\n                        continue\n                    \n                    # Start processing\n                    asyncio.create_task(self._process_queued_interaction(queued_interaction))\n                    \n                except Exception as e:\n                    self.logger.error(f\"Error in queue processing loop: {e}\")\n                    await asyncio.sleep(1)\n                    \n        except asyncio.CancelledError:\n            self.logger.info(\"Queue processing loop cancelled\")\n        except Exception as e:\n            self.logger.error(f\"Queue processing loop failed: {e}\")\n    \n    async def _process_queued_interaction(self, queued_interaction: QueuedInteraction):\n        \"\"\"\n        Process a single queued interaction.\n        \"\"\"\n        try:\n            async with self.processing_lock:\n                self.active_processors += 1\n                self.processing_interactions[queued_interaction.context.interaction_id] = queued_interaction\n            \n            queued_interaction.status = QueueStatus.PROCESSING\n            queued_interaction.attempts += 1\n            \n            # Call processing callback\n            if queued_interaction.processing_callback:\n                try:\n                    await queued_interaction.processing_callback(queued_interaction.context)\n                except Exception as e:\n                    self.logger.warning(f\"Processing callback failed: {e}\")\n            \n            # Simulate processing (in real implementation, would call interaction processor)\n            await asyncio.sleep(0.1)  # Simulate processing time\n            processing_success = True  # Simulate success\n            \n            # Handle completion\n            if processing_success:\n                queued_interaction.status = QueueStatus.COMPLETED\n                self.completed_interactions[queued_interaction.context.interaction_id] = queued_interaction\n                self.queue_stats[\"total_completed\"] += 1\n                \n                # Call completion callback\n                if queued_interaction.completion_callback:\n                    try:\n                        await queued_interaction.completion_callback(queued_interaction.context)\n                    except Exception as e:\n                        self.logger.warning(f\"Completion callback failed: {e}\")\n            else:\n                # Handle failure\n                if queued_interaction.attempts < queued_interaction.max_attempts:\n                    # Retry\n                    queued_interaction.status = QueueStatus.QUEUED\n                    self.interaction_queue.put_nowait(queued_interaction)\n                else:\n                    # Max attempts reached\n                    queued_interaction.status = QueueStatus.FAILED\n                    self.failed_interactions[queued_interaction.context.interaction_id] = queued_interaction\n                    self.queue_stats[\"total_failed\"] += 1\n                    \n                    # Call error callback\n                    if queued_interaction.error_callback:\n                        try:\n                            await queued_interaction.error_callback(queued_interaction.context)\n                        except Exception as e:\n                            self.logger.warning(f\"Error callback failed: {e}\")\n            \n            # Update statistics\n            self.queue_stats[\"total_processed\"] += 1\n            queue_time = (datetime.now() - queued_interaction.queue_time).total_seconds()\n            self._update_queue_time_stats(queue_time)\n            \n        except Exception as e:\n            self.logger.error(f\"Failed to process queued interaction: {e}\")\n            queued_interaction.status = QueueStatus.FAILED\n            self.failed_interactions[queued_interaction.context.interaction_id] = queued_interaction\n            self.queue_stats[\"total_failed\"] += 1\n        \n        finally:\n            # Cleanup\n            async with self.processing_lock:\n                self.active_processors -= 1\n                self.processing_interactions.pop(queued_interaction.context.interaction_id, None)\n    \n    async def _cleanup_completed_interactions(self):\n        \"\"\"\n        Clean up old completed and failed interactions.\n        \"\"\"\n        try:\n            cleanup_time = datetime.now() - timedelta(hours=1)\n            \n            # Clean completed interactions\n            to_remove = [\n                interaction_id for interaction_id, interaction in self.completed_interactions.items()\n                if interaction.queue_time < cleanup_time\n            ]\n            \n            for interaction_id in to_remove:\n                self.completed_interactions.pop(interaction_id, None)\n            \n            # Clean failed interactions\n            to_remove = [\n                interaction_id for interaction_id, interaction in self.failed_interactions.items()\n                if interaction.queue_time < cleanup_time\n            ]\n            \n            for interaction_id in to_remove:\n                self.failed_interactions.pop(interaction_id, None)\n            \n            if to_remove:\n                self.logger.info(f\"Cleaned up {len(to_remove)} old interactions\")\n                \n        except Exception as e:\n            self.logger.error(f\"Cleanup failed: {e}\")\n    \n    def _calculate_priority_score(self, context: InteractionContext) -> float:\n        \"\"\"\n        Calculate priority score for interaction.\n        \"\"\"\n        base_score = self.priority_weights.get(context.priority, 400)\n        \n        # Modify based on interaction type\n        type_modifiers = {\n            InteractionType.EMERGENCY: 200,\n            InteractionType.COMBAT: 100,\n            InteractionType.NEGOTIATION: 50,\n            InteractionType.DIALOGUE: 0,\n            InteractionType.MAINTENANCE: -50\n        }\n        \n        base_score += type_modifiers.get(context.interaction_type, 0)\n        \n        # Modify based on participant count\n        base_score += len(context.participants) * 10\n        \n        # Add time decay for older interactions\n        age_bonus = min(100, (datetime.now() - datetime.now()).total_seconds() * 0.1)\n        base_score += age_bonus\n        \n        return base_score\n    \n    def _estimate_wait_time(self, priority_score: float) -> float:\n        \"\"\"\n        Estimate wait time for interaction based on priority.\n        \"\"\"\n        # Simple estimation based on queue position and processing capacity\n        queue_size = self.interaction_queue.qsize()\n        processing_capacity = self.max_concurrent\n        average_processing_time = max(1.0, self.queue_stats[\"average_processing_time\"])\n        \n        # Estimate position in queue based on priority\n        estimated_position = queue_size * 0.5  # Simplified estimation\n        \n        return (estimated_position / processing_capacity) * average_processing_time\n    \n    def _update_queue_time_stats(self, queue_time: float):\n        \"\"\"\n        Update queue time statistics.\n        \"\"\"\n        total_processed = self.queue_stats[\"total_processed\"]\n        if total_processed > 0:\n            current_avg = self.queue_stats[\"average_queue_time\"]\n            self.queue_stats[\"average_queue_time\"] = (\n                (current_avg * (total_processed - 1)) + queue_time\n            ) / total_processed\n    \n    def __del__(self):\n        \"\"\"\n        Cleanup resources on destruction.\n        \"\"\"\n        if self.executor:\n            self.executor.shutdown(wait=True)"