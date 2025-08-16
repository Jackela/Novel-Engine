#!/usr/bin/env python3
"""
Emotional Memory System.

This module implements an emotional memory system that preserves affective
experiences and emotional states with valence and arousal tracking.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import math

from src.core.data_models import MemoryItem, MemoryType, StandardResponse, ErrorInfo, EmotionalState
from src.core.types import AgentID
from src.database.context_db import ContextDatabase

logger = logging.getLogger(__name__)


class EmotionalIntensity(Enum):
    """Enumeration for emotional intensity levels."""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"

class EmotionalValence(Enum):
    """Enumeration for emotional valence categories."""
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"

@dataclass
class EmotionalMemoryItem:
    """Represents a memory item with emotional data."""
    memory_item: MemoryItem
    valence: float = 0.0
    arousal: float = 0.0
    dominance: float = 0.0
    emotional_tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Validates emotional memory data after initialization."""
        self.valence = max(-1.0, min(1.0, self.valence))
        self.arousal = max(0.0, min(1.0, self.arousal))
        self.dominance = max(0.0, min(1.0, self.dominance))
        if not self.emotional_tags:
            self.emotional_tags = self._derive_emotional_tags()
    
    def _derive_emotional_tags(self) -> List[str]:
        """Derives emotional tags from valence and arousal values."""
        tags = []
        if self.valence <= -0.6: tags.append("very_negative")
        elif self.valence <= -0.2: tags.append("negative")
        elif self.valence >= 0.6: tags.append("very_positive")
        elif self.valence >= 0.2: tags.append("positive")
        else: tags.append("neutral")
        
        if self.arousal >= 0.7: tags.append("high_arousal")
        elif self.arousal <= 0.3: tags.append("low_arousal")
        return tags

class EmotionalMemory:
    """Manages emotional memories for an agent."""
    
    def __init__(self, agent_id: AgentID, database: ContextDatabase, max_memories: int = 500, threshold: float = 0.3):
        """Initializes the emotional memory system."""
        self.agent_id = agent_id
        self.database = database
        self.max_memories = max_memories
        self.threshold = threshold
        self._emotional_memories: Dict[str, EmotionalMemoryItem] = {}
        self._valence_index: Dict[EmotionalValence, List[str]] = defaultdict(list)
        logger.info(f"EmotionalMemory for agent {agent_id} initialized.")
    
    async def store_emotional_experience(self, memory: MemoryItem, valence: float, arousal: float) -> StandardResponse:
        """Stores an emotional experience if it meets the arousal threshold."""
        if arousal < self.threshold:
            return StandardResponse(success=True, data={"stored": False, "reason": "below_threshold"})
        
        emotional_memory = EmotionalMemoryItem(memory_item=memory, valence=valence, arousal=arousal)
        self._emotional_memories[memory.memory_id] = emotional_memory
        self._update_emotional_indices(emotional_memory)
        
        await self.database.store_memory(memory)
        
        return StandardResponse(success=True, data={"stored": True})

    def _update_emotional_indices(self, emotional_memory: EmotionalMemoryItem):
        """Updates internal indices for efficient querying."""
        # This is a simplified placeholder for a more complex indexing system.
        category = emotional_memory._derive_emotional_tags()[0]
        self._valence_index[category].append(emotional_memory.memory_item.memory_id)

async def test_emotional_memory():
    """Tests the emotional memory system."""
    print("Testing Emotional Memory System...")
    db = ContextDatabase(":memory:")
    await db.initialize()
    
    memory_system = EmotionalMemory("test_agent", db)
    
    test_memory = MemoryItem(agent_id="test_agent", memory_type=MemoryType.OBSERVATION, content="A beautiful sunset.")
    await memory_system.store_emotional_experience(test_memory, 0.8, 0.4)
    
    print("Emotional memory test complete.")

if __name__ == "__main__":
    asyncio.run(test_emotional_memory())