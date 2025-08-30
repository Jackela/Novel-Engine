#!/usr/bin/env python3
"""
Working Memory System
=====================

This module provides a working memory implementation that simulates immediate
consciousness, adhering to the 7±2 capacity limit from cognitive psychology.
It manages a small set of recently attended memory items.
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional

from src.core.data_models import ErrorInfo, MemoryItem, StandardResponse
from src.core.types import AgentID

logger = logging.getLogger(__name__)

# A default capacity for working memory, based on Miller's Law (7 ± 2)
DEFAULT_WORKING_MEMORY_CAPACITY = 7


@dataclass
class WorkingMemoryItem:
    """
    An enhanced memory item for working memory, including metadata for
    attention and priority management.
    """

    memory_item: MemoryItem
    attention_weight: float = 1.0
    activation_level: float = 1.0
    last_activation: datetime = field(default_factory=datetime.now)
    access_frequency: int = 0

    def __post_init__(self):
        """Validates the initial values of the working memory item."""
        self.attention_weight = max(0.0, min(1.0, self.attention_weight))
        self.activation_level = max(0.0, min(2.0, self.activation_level))

    def activate(self, boost: float = 0.1):
        """Increases the activation level and attention weight of the item."""
        self.activation_level = min(2.0, self.activation_level + boost)
        self.last_activation = datetime.now()
        self.access_frequency += 1
        self.attention_weight = min(1.0, self.attention_weight + boost * 0.5)

    def decay(self, decay_rate: float = 0.95):
        """Applies decay to the item's activation and attention."""
        self.activation_level *= decay_rate
        self.attention_weight *= decay_rate

        time_since_activation = datetime.now() - self.last_activation
        if time_since_activation.total_seconds() > 300:  # 5 minutes
            self.activation_level *= 0.9

    @property
    def effective_priority(self) -> float:
        """Calculates the effective priority for memory management."""
        base_priority = self.memory_item.relevance_score
        attention_bonus = self.attention_weight * 0.3
        activation_bonus = (self.activation_level - 1.0) * 0.2
        frequency_bonus = min(0.2, self.access_frequency * 0.05)
        return base_priority + attention_bonus + activation_bonus + frequency_bonus


class WorkingMemory:
    """
    Manages the agent's immediate conscious focus, adhering to cognitive
    capacity limits (typically 7±2 items).
    """

    def __init__(
        self,
        agent_id: AgentID,
        capacity: int = DEFAULT_WORKING_MEMORY_CAPACITY,
        decay_rate: float = 0.95,
    ):
        """
        Initializes the WorkingMemory.

        Args:
            agent_id: The ID of the agent this memory belongs to.
            capacity: The capacity of the working memory (default: 7).
            decay_rate: The rate at which unused memories decay.
        """
        self.agent_id = agent_id
        self.capacity = max(5, min(9, capacity))
        self.decay_rate = decay_rate

        self._items: Deque[WorkingMemoryItem] = deque(maxlen=self.capacity * 2)
        self._priority_index: Dict[str, WorkingMemoryItem] = {}

        self.total_activations = 0
        self.total_evictions = 0
        self.last_maintenance = datetime.now()

        logger.info(
            f"WorkingMemory initialized for {agent_id} with capacity {self.capacity}"
        )

    def add_memory(
        self, memory: MemoryItem, attention_weight: float = 1.0
    ) -> StandardResponse:
        """
        Adds a memory to working memory, managing capacity through
        priority-based eviction.
        """
        try:
            existing_item = self._priority_index.get(memory.memory_id)
            if existing_item:
                existing_item.activate(boost=0.2)
                existing_item.attention_weight = max(
                    existing_item.attention_weight, attention_weight
                )
                logger.info(f"Working memory item updated: {memory.memory_id}")
                return StandardResponse(success=True, data={"updated": True})

            working_item = WorkingMemoryItem(
                memory_item=memory,
                attention_weight=attention_weight,
                activation_level=1.0 + (attention_weight * 0.5),
            )

            if len(self._items) >= self.capacity:
                evicted_item = self._evict_lowest_priority()
                if evicted_item:
                    logger.info(
                        f"Evicted item from working memory: {evicted_item.memory_item.memory_id}"
                    )

            self._items.append(working_item)
            self._priority_index[memory.memory_id] = working_item
            self.total_activations += 1

            logger.info(
                f"Added to working memory: {memory.memory_id} (size: {len(self._items)})"
            )

            return StandardResponse(
                success=True, data={"added": True, "current_size": len(self._items)}
            )

        except Exception as e:
            logger.error(f"Failed to add to working memory: {e}", exc_info=True)
            return StandardResponse(
                success=False, error=ErrorInfo(code="ADD_FAILED", message=str(e))
            )

    def get_active_memories(self, limit: Optional[int] = None) -> List[MemoryItem]:
        """
        Retrieves currently active memories, sorted by priority and attention.
        """
        limit = limit if limit is not None else len(self._items)

        sorted_items = sorted(
            self._items, key=lambda item: item.effective_priority, reverse=True
        )

        for item in sorted_items[:limit]:
            item.activate(boost=0.05)

        active_memories = [item.memory_item for item in sorted_items[:limit]]
        logger.info(f"Retrieved {len(active_memories)} active memories.")
        return active_memories

    def focus_on_memory(
        self, memory_id: str, attention_boost: float = 0.3
    ) -> StandardResponse:
        """
        Focuses attention on a specific memory, increasing its priority.
        """
        try:
            working_item = self._priority_index.get(memory_id)
            if not working_item:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="NOT_FOUND", message="Memory not in working memory"
                    ),
                )

            working_item.activate(boost=attention_boost)

            if working_item in self._items:
                self._items.remove(working_item)
                self._items.append(working_item)

            logger.info(f"Focused attention on memory: {memory_id}")
            return StandardResponse(
                success=True,
                data={"focused": True, "new_priority": working_item.effective_priority},
            )

        except Exception as e:
            logger.error(f"Failed to focus on memory: {e}", exc_info=True)
            return StandardResponse(
                success=False, error=ErrorInfo(code="FOCUS_FAILED", message=str(e))
            )

    def perform_maintenance(self) -> StandardResponse:
        """
        Performs maintenance, including decay application and priority recalculation.
        """
        try:
            maintenance_start = datetime.now()

            items_to_remove = [
                item
                for item in self._items
                if item.activation_level < 0.1 and item.attention_weight < 0.1
            ]

            for item in self._items:
                item.decay(self.decay_rate)

            for item in items_to_remove:
                self._remove_item(item)
                logger.info(
                    f"Item decayed from working memory: {item.memory_item.memory_id}"
                )

            self._rebalance_priorities()

            self.last_maintenance = maintenance_start
            duration_ms = (datetime.now() - maintenance_start).total_seconds() * 1000

            logger.info(f"Working memory maintenance complete in {duration_ms:.2f}ms")

            return StandardResponse(
                success=True,
                data={
                    "items_removed": len(items_to_remove),
                    "current_size": len(self._items),
                },
            )

        except Exception as e:
            logger.error(f"Working memory maintenance failed: {e}", exc_info=True)
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="MAINTENANCE_FAILED", message=str(e)),
            )

    def get_memory_statistics(self) -> Dict[str, Any]:
        """Returns statistics about the state of the working memory."""
        if not self._items:
            return {"capacity_usage": 0.0, "average_activation": 0.0, "total_items": 0}

        total_activation = sum(item.activation_level for item in self._items)

        return {
            "capacity_usage": len(self._items) / self.capacity,
            "average_activation": total_activation / len(self._items),
            "total_items": len(self._items),
            "total_activations": self.total_activations,
            "total_evictions": self.total_evictions,
            "last_maintenance": self.last_maintenance.isoformat(),
        }

    def _evict_lowest_priority(self) -> Optional[WorkingMemoryItem]:
        """Evicts the item with the lowest effective priority."""
        if not self._items:
            return None

        lowest_priority_item = min(
            self._items, key=lambda item: item.effective_priority
        )
        self._remove_item(lowest_priority_item)
        self.total_evictions += 1
        return lowest_priority_item

    def _remove_item(self, item: WorkingMemoryItem):
        """Removes an item from the working memory."""
        if item in self._items:
            self._items.remove(item)
        if item.memory_item.memory_id in self._priority_index:
            del self._priority_index[item.memory_item.memory_id]

    def _rebalance_priorities(self):
        """Normalizes attention weights to prevent runaway inflation."""
        if not self._items:
            return
        max_attention = max(item.attention_weight for item in self._items)
        if max_attention > 1.5:
            for item in self._items:
                item.attention_weight /= max_attention

    def clear(self):
        """Clears all items from working memory."""
        self._items.clear()
        self._priority_index.clear()
        logger.info(f"Working memory cleared for {self.agent_id}")

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f"WorkingMemory(agent={self.agent_id}, size={len(self._items)}/{self.capacity})"


if __name__ == "__main__":
    print("Testing Working Memory...")

    working_memory = WorkingMemory("test_agent", capacity=7)

    for i in range(10):
        test_memory = MemoryItem(
            agent_id="test_agent",
            content=f"Test memory item {i}",
            relevance_score=0.5 + (i * 0.05),
        )
        result = working_memory.add_memory(test_memory)
        print(f"Added memory {i}: {result.success}")

    active_memories = working_memory.get_active_memories(limit=5)
    print(f"Retrieved {len(active_memories)} active memories.")
    assert len(active_memories) == 5

    if active_memories:
        focus_result = working_memory.focus_on_memory(active_memories[0].memory_id)
        print(f"Focusing on memory: {focus_result.success}")

    maintenance_result = working_memory.perform_maintenance()
    print(f"Maintenance complete: {maintenance_result.success}")

    stats = working_memory.get_memory_statistics()
    print(f"Working Memory Statistics: {stats}")

    print("Working Memory testing complete.")
