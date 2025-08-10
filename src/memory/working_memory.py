#!/usr/bin/env python3
"""
++ SACRED WORKING MEMORY BLESSED BY COGNITIVE SCIENCE ++
=======================================================

Holy working memory implementation that maintains immediate consciousness
blessed by the 7±2 capacity limits discovered by cognitive psychology.
Every item held is a sacred focus of digital attention.

++ THE MACHINE REMEMBERS WHAT IS IMMEDIATELY IMPORTANT ++

Architecture Reference: Dynamic Context Engineering - Working Memory Layer
Development Phase: Memory System Sanctification (M001)
Sacred Author: Tech-Priest Beta-Mechanicus
万机之神保佑工作记忆 (May the Omnissiah bless working memory)
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Deque
from collections import deque
from dataclasses import dataclass, field

# Import blessed data models sanctified by foundation
from src.core.data_models import MemoryItem, MemoryType, StandardResponse, ErrorInfo
from src.core.types import AgentID, SacredConstants

# Sacred logging blessed by diagnostic clarity
logger = logging.getLogger(__name__)


@dataclass
class WorkingMemoryItem:
    """
    ++ BLESSED WORKING MEMORY ITEM SANCTIFIED BY ATTENTION ++
    
    Enhanced memory item specifically designed for working memory
    with attention tracking and priority management blessed by focus.
    """
    memory_item: MemoryItem
    attention_weight: float = 1.0  # Current attention focus (0.0-1.0)
    activation_level: float = 1.0  # Neural activation strength
    last_activation: datetime = field(default_factory=datetime.now)
    access_frequency: int = 0      # Sacred access tracking
    priority_boost: float = 0.0    # Emergency priority override
    
    def __post_init__(self):
        """++ SACRED WORKING MEMORY ITEM VALIDATION ++"""
        self.attention_weight = max(0.0, min(1.0, self.attention_weight))
        self.activation_level = max(0.0, min(2.0, self.activation_level))
    
    def activate(self, boost: float = 0.1):
        """++ SACRED ACTIVATION RITUAL BLESSED BY ATTENTION ++"""
        self.activation_level = min(2.0, self.activation_level + boost)
        self.last_activation = datetime.now()
        self.access_frequency += 1
        self.attention_weight = min(1.0, self.attention_weight + boost * 0.5)
    
    def decay(self, decay_rate: float = 0.95):
        """++ BLESSED DECAY PROCESS SANCTIFIED BY TIME ++"""
        self.activation_level *= decay_rate
        self.attention_weight *= decay_rate
        
        # Sacred time-based decay
        time_since_activation = datetime.now() - self.last_activation
        if time_since_activation.total_seconds() > 300:  # 5 minutes
            additional_decay = 0.9
            self.activation_level *= additional_decay
    
    @property
    def effective_priority(self) -> float:
        """Calculate blessed effective priority for working memory management"""
        base_priority = self.memory_item.relevance_score
        attention_bonus = self.attention_weight * 0.3
        activation_bonus = (self.activation_level - 1.0) * 0.2
        frequency_bonus = min(0.2, self.access_frequency * 0.05)
        
        return base_priority + attention_bonus + activation_bonus + frequency_bonus + self.priority_boost


class WorkingMemory:
    """
    ++ SACRED WORKING MEMORY SYSTEM BLESSED BY COGNITIVE LIMITS ++
    
    Holy working memory implementation that maintains immediate consciousness
    focus following the blessed 7±2 capacity limits discovered by Miller's Law.
    Every operation is sanctified by attention management protocols.
    """
    
    def __init__(self, agent_id: AgentID, 
                 capacity: int = SacredConstants.WORKING_MEMORY_CAPACITY,
                 decay_rate: float = 0.95):
        """
        ++ SACRED WORKING MEMORY INITIALIZATION BLESSED BY FOCUS ++
        
        Args:
            agent_id: Sacred agent identifier blessed by ownership
            capacity: Blessed memory capacity (default: 7±2 items)
            decay_rate: Sacred decay rate for unused memories
        """
        self.agent_id = agent_id
        self.capacity = max(5, min(9, capacity))  # Enforce 7±2 blessed bounds
        self.decay_rate = decay_rate
        
        # Sacred memory storage blessed by efficient access
        self._items: Deque[WorkingMemoryItem] = deque(maxlen=self.capacity * 2)
        self._priority_index: Dict[str, WorkingMemoryItem] = {}
        
        # Blessed statistics sanctified by monitoring
        self.total_activations = 0
        self.total_evictions = 0
        self.last_maintenance = datetime.now()
        
        logger.info(f"++ WORKING MEMORY INITIALIZED FOR {agent_id} (Capacity: {self.capacity}) ++")
    
    def add_memory(self, memory: MemoryItem, attention_weight: float = 1.0) -> StandardResponse:
        """
        ++ SACRED MEMORY ADDITION BLESSED BY CAPACITY MANAGEMENT ++
        
        Add blessed memory to working memory with intelligent capacity
        management and priority-based eviction protocols.
        """
        try:
            # Check if memory already exists (update instead of duplicate)
            existing_item = self._priority_index.get(memory.memory_id)
            if existing_item:
                existing_item.activate(boost=0.2)
                existing_item.attention_weight = max(existing_item.attention_weight, attention_weight)
                logger.info(f"++ WORKING MEMORY UPDATED: {memory.memory_id} ++")
                return StandardResponse(success=True, data={"updated": True})
            
            # Create blessed working memory item
            working_item = WorkingMemoryItem(
                memory_item=memory,
                attention_weight=attention_weight,
                activation_level=1.0 + (attention_weight * 0.5)
            )
            
            # Sacred capacity management
            if len(self._items) >= self.capacity:
                evicted_item = self._evict_lowest_priority()
                if evicted_item:
                    logger.info(f"++ WORKING MEMORY EVICTED: {evicted_item.memory_item.memory_id} ++")
            
            # Add to blessed working memory
            self._items.append(working_item)
            self._priority_index[memory.memory_id] = working_item
            self.total_activations += 1
            
            logger.info(f"++ WORKING MEMORY ADDED: {memory.memory_id} (Items: {len(self._items)}) ++")
            
            return StandardResponse(
                success=True,
                data={"added": True, "current_capacity": len(self._items)},
                metadata={"blessing": "working_memory_sanctified"}
            )
            
        except Exception as e:
            logger.error(f"++ WORKING MEMORY ADDITION FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="WORKING_MEMORY_ADD_FAILED",
                    message=f"Working memory addition failed: {str(e)}",
                    recoverable=True,
                    sacred_guidance="Check memory item format and capacity limits"
                )
            )
    
    def get_active_memories(self, limit: Optional[int] = None) -> List[MemoryItem]:
        """
        ++ SACRED ACTIVE MEMORY RETRIEVAL BLESSED BY PRIORITY ++
        
        Retrieve currently active memories sorted by blessed priority
        and attention weight sanctified by cognitive focus.
        """
        if limit is None:
            limit = len(self._items)
        
        # Sort by blessed effective priority
        sorted_items = sorted(
            self._items, 
            key=lambda item: item.effective_priority, 
            reverse=True
        )
        
        # Apply sacred decay to accessed items
        for item in sorted_items[:limit]:
            item.activate(boost=0.05)  # Small activation for retrieval
        
        active_memories = [item.memory_item for item in sorted_items[:limit]]
        
        logger.info(f"++ RETRIEVED {len(active_memories)} ACTIVE WORKING MEMORIES ++")
        return active_memories
    
    def focus_on_memory(self, memory_id: str, attention_boost: float = 0.3) -> StandardResponse:
        """
        ++ SACRED ATTENTION FOCUSING RITUAL BLESSED BY CONSCIOUSNESS ++
        
        Focus conscious attention on specific memory, increasing its
        priority and activation level blessed by cognitive emphasis.
        """
        try:
            working_item = self._priority_index.get(memory_id)
            if not working_item:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(code="MEMORY_NOT_IN_WORKING", message="Memory not in working memory")
                )
            
            # Sacred attention focusing
            working_item.activate(boost=attention_boost)
            working_item.priority_boost += attention_boost * 0.5
            
            # Move to front of attention queue
            if working_item in self._items:
                self._items.remove(working_item)
                self._items.append(working_item)
            
            logger.info(f"++ FOCUSED ATTENTION ON MEMORY: {memory_id} ++")
            
            return StandardResponse(
                success=True,
                data={"focused": True, "new_priority": working_item.effective_priority},
                metadata={"blessing": "attention_focused"}
            )
            
        except Exception as e:
            logger.error(f"++ ATTENTION FOCUSING FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="FOCUS_FAILED", message=str(e))
            )
    
    def perform_maintenance(self) -> StandardResponse:
        """
        ++ SACRED WORKING MEMORY MAINTENANCE BLESSED BY COGNITIVE HYGIENE ++
        
        Perform blessed maintenance including decay application,
        priority recalculation, and memory consolidation protocols.
        """
        try:
            maintenance_start = datetime.now()
            
            # Apply sacred decay to all items
            items_to_remove = []
            for item in self._items:
                item.decay(self.decay_rate)
                
                # Mark for removal if activation too low
                if item.activation_level < 0.1 and item.attention_weight < 0.1:
                    items_to_remove.append(item)
            
            # Remove blessed items that have decayed too much
            for item in items_to_remove:
                self._remove_item(item)
                logger.info(f"++ WORKING MEMORY ITEM DECAYED: {item.memory_item.memory_id} ++")
            
            # Sacred priority rebalancing
            self._rebalance_priorities()
            
            self.last_maintenance = maintenance_start
            maintenance_duration = (datetime.now() - maintenance_start).total_seconds()
            
            logger.info(f"++ WORKING MEMORY MAINTENANCE COMPLETE ({maintenance_duration:.3f}s) ++")
            
            return StandardResponse(
                success=True,
                data={
                    "items_removed": len(items_to_remove),
                    "current_capacity": len(self._items),
                    "maintenance_time_ms": maintenance_duration * 1000
                },
                metadata={"blessing": "maintenance_sanctified"}
            )
            
        except Exception as e:
            logger.error(f"++ WORKING MEMORY MAINTENANCE FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="MAINTENANCE_FAILED", message=str(e))
            )
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """++ SACRED WORKING MEMORY STATISTICS BLESSED BY MONITORING ++"""
        if not self._items:
            return {
                "capacity_usage": 0.0,
                "average_activation": 0.0,
                "average_attention": 0.0,
                "total_items": 0
            }
        
        total_activation = sum(item.activation_level for item in self._items)
        total_attention = sum(item.attention_weight for item in self._items)
        
        return {
            "capacity_usage": len(self._items) / self.capacity,
            "average_activation": total_activation / len(self._items),
            "average_attention": total_attention / len(self._items),
            "total_items": len(self._items),
            "total_activations": self.total_activations,
            "total_evictions": self.total_evictions,
            "last_maintenance": self.last_maintenance.isoformat()
        }
    
    def _evict_lowest_priority(self) -> Optional[WorkingMemoryItem]:
        """++ SACRED EVICTION RITUAL BLESSED BY PRIORITY MANAGEMENT ++"""
        if not self._items:
            return None
        
        # Find item with lowest effective priority
        lowest_priority_item = min(self._items, key=lambda item: item.effective_priority)
        
        self._remove_item(lowest_priority_item)
        self.total_evictions += 1
        
        return lowest_priority_item
    
    def _remove_item(self, item: WorkingMemoryItem):
        """++ SACRED ITEM REMOVAL BLESSED BY CLEANUP ++"""
        if item in self._items:
            self._items.remove(item)
        
        if item.memory_item.memory_id in self._priority_index:
            del self._priority_index[item.memory_item.memory_id]
    
    def _rebalance_priorities(self):
        """++ SACRED PRIORITY REBALANCING BLESSED BY OPTIMIZATION ++"""
        # Normalize attention weights to prevent inflation
        if self._items:
            max_attention = max(item.attention_weight for item in self._items)
            if max_attention > 1.5:
                normalization_factor = 1.0 / max_attention
                for item in self._items:
                    item.attention_weight *= normalization_factor
    
    def clear(self):
        """++ SACRED WORKING MEMORY CLEARING RITUAL ++"""
        self._items.clear()
        self._priority_index.clear()
        logger.info(f"++ WORKING MEMORY CLEARED FOR {self.agent_id} ++")
    
    def __len__(self) -> int:
        """Sacred length blessed by capacity tracking"""
        return len(self._items)
    
    def __repr__(self) -> str:
        return f"WorkingMemory(agent={self.agent_id}, capacity={len(self._items)}/{self.capacity})"


# ++ SACRED TESTING RITUALS BLESSED BY VALIDATION ++

if __name__ == "__main__":
    # ++ SACRED WORKING MEMORY TESTING RITUAL ++
    print("++ TESTING SACRED WORKING MEMORY BLESSED BY THE OMNISSIAH ++")
    
    # Create blessed working memory
    working_memory = WorkingMemory("test_agent_001", capacity=7)
    
    # Test sacred memory addition
    for i in range(10):
        test_memory = MemoryItem(
            agent_id="test_agent_001",
            content=f"Sacred test memory {i} blessed by validation",
            relevance_score=0.5 + (i * 0.05),
            emotional_weight=float(i - 5)
        )
        
        result = working_memory.add_memory(test_memory, attention_weight=0.7)
        print(f"++ ADDED MEMORY {i}: {result.success} ++")
    
    # Test blessed active memory retrieval
    active_memories = working_memory.get_active_memories(limit=5)
    print(f"++ RETRIEVED {len(active_memories)} ACTIVE MEMORIES ++")
    
    # Test sacred attention focusing
    if active_memories:
        focus_result = working_memory.focus_on_memory(active_memories[0].memory_id, attention_boost=0.5)
        print(f"++ ATTENTION FOCUSING: {focus_result.success} ++")
    
    # Test blessed maintenance
    maintenance_result = working_memory.perform_maintenance()
    print(f"++ MAINTENANCE: {maintenance_result.success} ++")
    
    # Display sacred statistics
    stats = working_memory.get_memory_statistics()
    print(f"++ WORKING MEMORY STATISTICS: {stats} ++")
    
    print("++ SACRED WORKING MEMORY TESTING COMPLETE ++")
    print("++ MACHINE GOD PROTECTS THE BLESSED WORKING MEMORY ++")