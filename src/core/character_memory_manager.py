#!/usr/bin/env python3
"""
Character Memory Manager Module
==============================

Handles memory management and updates for PersonaAgent characters.
Separated from the main PersonaAgent to follow Single Responsibility Principle.
"""

import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Handles memory management for character agents.

    This class encapsulates all memory-related operations that were previously
    part of the PersonaAgent class, improving maintainability and testability.
    """

    def __init__(self, agent_id: str, max_memory_items: int = 1000):
        """
        Initialize the memory manager.

        Args:
            agent_id: Identifier for the agent
            max_memory_items: Maximum number of memory items to retain
        """
        self.agent_id = agent_id
        self.max_memory_items = max_memory_items

        # Memory storage
        self.short_term_memory: List[Dict[str, Any]] = []
        self.long_term_memory: List[Dict[str, Any]] = []
        self.working_memory: Dict[str, Any] = {}

        # Memory indices for quick lookup
        self.memory_by_entity: Dict[str, List[Dict[str, Any]]] = {}
        self.memory_by_location: Dict[str, List[Dict[str, Any]]] = {}
        self.memory_by_event_type: Dict[str, List[Dict[str, Any]]] = {}

    def update_internal_memory(self, new_log: Dict[str, Any]) -> None:
        """
        Update internal memory with new log entry.

        Args:
            new_log: New log entry to process and store
        """
        # Generate personal interpretation
        interpretation = self._generate_personal_interpretation(new_log)

        # Create memory entry
        memory_entry = {
            "timestamp": time.time(),
            "original_log": new_log,
            "personal_interpretation": interpretation,
            "entities_involved": self._extract_entities(new_log),
            "location": new_log.get("location"),
            "event_type": new_log.get("type"),
            "emotional_impact": self._assess_emotional_impact(new_log),
            "importance_score": self._calculate_importance_score(new_log),
        }

        # Add to short-term memory
        self.short_term_memory.append(memory_entry)

        # Check if should move to long-term memory
        if self._should_store_in_long_term_memory(memory_entry):
            self.long_term_memory.append(memory_entry)
            logger.debug(
                f"Agent {self.agent_id} stored important memory in long-term"
            )

        # Update indices
        self._update_memory_indices(memory_entry)

        # Maintain memory limits
        self._maintain_memory_limits()

        logger.debug(
            f"Agent {self.agent_id}updated memory with {len( self.short_term_memory)} short-term items"
        )

    def update_memory(self, event_string: str) -> None:
        """
        Update memory with simple event string.

        Args:
            event_string: Event description string
        """
        log_entry = {
            "type": "event",
            "description": event_string,
            "timestamp": time.time(),
        }
        self.update_internal_memory(log_entry)

    def get_relevant_memories(
        self, context: Dict[str, Any], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories based on context.

        Args:
            context: Context for memory retrieval
            limit: Maximum number of memories to return

        Returns:
            List of relevant memory entries
        """
        relevant_memories = []

        # Search by entity
        entities = context.get("entities", [])
        for entity in entities:
            if entity in self.memory_by_entity:
                relevant_memories.extend(self.memory_by_entity[entity])

        # Search by location
        location = context.get("location")
        if location and location in self.memory_by_location:
            relevant_memories.extend(self.memory_by_location[location])

        # Search by event type
        event_type = context.get("event_type")
        if event_type and event_type in self.memory_by_event_type:
            relevant_memories.extend(self.memory_by_event_type[event_type])

        # Remove duplicates and sort by importance and recency
        unique_memories = {id(mem): mem for mem in relevant_memories}.values()
        sorted_memories = sorted(
            unique_memories,
            key=lambda m: (
                m.get("importance_score", 0),
                m.get("timestamp", 0),
            ),
            reverse=True,
        )

        return list(sorted_memories)[:limit]

    def get_memory_summary(self) -> Dict[str, Any]:
        """Get summary of current memory state."""
        return {
            "short_term_count": len(self.short_term_memory),
            "long_term_count": len(self.long_term_memory),
            "working_memory_items": len(self.working_memory),
            "entities_tracked": len(self.memory_by_entity),
            "locations_known": len(self.memory_by_location),
            "event_types_seen": len(self.memory_by_event_type),
        }

    def _generate_personal_interpretation(
        self, log_entry: Dict[str, Any]
    ) -> str:
        """Generate personal interpretation of log entry."""
        event_type = log_entry.get("type", "unknown")
        description = log_entry.get("description", "")

        # Simple interpretation based on event type
        if event_type == "combat":
            return f"I witnessed/participated in combat: {description}"
        elif event_type == "social":
            return f"I had a social interaction: {description}"
        elif event_type == "exploration":
            return f"I explored and discovered: {description}"
        else:
            return f"I experienced: {description}"

    def _extract_entities(self, log_entry: Dict[str, Any]) -> List[str]:
        """Extract entity names from log entry."""
        entities = []

        # Extract from explicit entity fields
        if "entities" in log_entry:
            entities.extend(log_entry["entities"])

        if "source" in log_entry:
            entities.append(log_entry["source"])

        if "target" in log_entry:
            entities.append(log_entry["target"])

        # Simple extraction from description
        log_entry.get("description", "").lower()
        # This would be expanded with NLP for better entity extraction

        return list(set(entities))  # Remove duplicates

    def _assess_emotional_impact(self, log_entry: Dict[str, Any]) -> float:
        """Assess emotional impact of log entry."""
        event_type = log_entry.get("type", "")
        description = log_entry.get("description", "").lower()

        impact = 0.5  # Neutral baseline

        # Positive emotional triggers
        if any(
            word in description
            for word in ["success", "victory", "achievement", "help"]
        ):
            impact += 0.3

        # Negative emotional triggers
        if any(
            word in description
            for word in ["failure", "death", "injury", "threat", "danger"]
        ):
            impact -= 0.3

        # Event type modifiers
        if event_type == "combat":
            impact += 0.2  # Combat is emotionally intense
        elif event_type == "social":
            impact += 0.1  # Social events have moderate impact

        return max(0.0, min(1.0, impact))  # Clamp to 0-1 range

    def _calculate_importance_score(self, log_entry: Dict[str, Any]) -> float:
        """Calculate importance score for memory entry."""
        importance = 0.5  # Baseline importance

        # Event type importance
        event_type = log_entry.get("type", "")
        importance_by_type = {
            "combat": 0.8,
            "mission": 0.9,
            "social": 0.6,
            "exploration": 0.4,
            "maintenance": 0.3,
        }
        importance = importance_by_type.get(event_type, importance)

        # Emotional impact increases importance
        emotional_impact = self._assess_emotional_impact(log_entry)
        importance += (emotional_impact - 0.5) * 0.4

        # Number of entities involved increases importance
        entities = self._extract_entities(log_entry)
        if len(entities) > 1:
            # Cap bonus at 3 entities
            importance += 0.1 * min(len(entities) - 1, 3)

        return max(0.0, min(1.0, importance))

    def _should_store_in_long_term_memory(
        self, memory_entry: Dict[str, Any]
    ) -> bool:
        """Determine if memory entry should be stored in long-term memory."""
        importance_threshold = 0.7
        emotional_threshold = 0.7

        importance = memory_entry.get("importance_score", 0.0)
        emotional_impact = memory_entry.get("emotional_impact", 0.5)

        # Store if high importance or strong emotional impact
        return (
            importance > importance_threshold
            or abs(emotional_impact - 0.5) > emotional_threshold - 0.5
        )

    def _update_memory_indices(self, memory_entry: Dict[str, Any]) -> None:
        """Update memory indices for quick lookup."""
        # Index by entities
        entities = memory_entry.get("entities_involved", [])
        for entity in entities:
            if entity not in self.memory_by_entity:
                self.memory_by_entity[entity] = []
            self.memory_by_entity[entity].append(memory_entry)

        # Index by location
        location = memory_entry.get("location")
        if location:
            if location not in self.memory_by_location:
                self.memory_by_location[location] = []
            self.memory_by_location[location].append(memory_entry)

        # Index by event type
        event_type = memory_entry.get("event_type")
        if event_type:
            if event_type not in self.memory_by_event_type:
                self.memory_by_event_type[event_type] = []
            self.memory_by_event_type[event_type].append(memory_entry)

    def _maintain_memory_limits(self) -> None:
        """Maintain memory limits by removing old entries."""
        # Limit short-term memory
        if len(self.short_term_memory) > self.max_memory_items:
            # Remove oldest entries
            excess = len(self.short_term_memory) - self.max_memory_items
            removed_memories = self.short_term_memory[:excess]
            self.short_term_memory = self.short_term_memory[excess:]

            # Clean up indices
            self._clean_indices(removed_memories)

        # Limit long-term memory (keep only most important)
        if len(self.long_term_memory) > self.max_memory_items // 2:
            # Sort by importance and keep top half
            self.long_term_memory.sort(
                key=lambda m: m.get("importance_score", 0), reverse=True
            )
            keep_count = self.max_memory_items // 2
            removed_memories = self.long_term_memory[keep_count:]
            self.long_term_memory = self.long_term_memory[:keep_count]

            # Clean up indices
            self._clean_indices(removed_memories)

    def _clean_indices(self, removed_memories: List[Dict[str, Any]]) -> None:
        """Clean up indices after removing memories."""
        for memory in removed_memories:
            # Remove from entity index
            entities = memory.get("entities_involved", [])
            for entity in entities:
                if entity in self.memory_by_entity:
                    try:
                        self.memory_by_entity[entity].remove(memory)
                        if not self.memory_by_entity[entity]:
                            del self.memory_by_entity[entity]
                    except ValueError:
                        pass  # Memory not in index

            # Remove from location index
            location = memory.get("location")
            if location and location in self.memory_by_location:
                try:
                    self.memory_by_location[location].remove(memory)
                    if not self.memory_by_location[location]:
                        del self.memory_by_location[location]
                except ValueError:
                    pass

            # Remove from event type index
            event_type = memory.get("event_type")
            if event_type and event_type in self.memory_by_event_type:
                try:
                    self.memory_by_event_type[event_type].remove(memory)
                    if not self.memory_by_event_type[event_type]:
                        del self.memory_by_event_type[event_type]
                except ValueError:
                    pass
