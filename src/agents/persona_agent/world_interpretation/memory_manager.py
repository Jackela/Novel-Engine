"""
Memory Manager
==============

Advanced memory management system for PersonaAgent.
Handles short-term and long-term memory, memory consolidation, and retrieval.
"""

import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple



class MemoryType(Enum):
    """Types of memories."""

    EPISODIC = "episodic"  # Specific events and experiences
    SEMANTIC = "semantic"  # General knowledge and facts
    PROCEDURAL = "procedural"  # Skills and procedures
    EMOTIONAL = "emotional"  # Emotionally significant experiences
    WORKING = "working"  # Temporary working memory


class MemoryStrength(Enum):
    """Memory strength levels."""

    WEAK = "weak"  # 0.0 - 0.3
    MODERATE = "moderate"  # 0.3 - 0.6
    STRONG = "strong"  # 0.6 - 0.8
    VIVID = "vivid"  # 0.8 - 1.0


@dataclass
class Memory:
    """Represents a stored memory with all metadata."""

    memory_id: str
    memory_type: MemoryType
    content: Dict[str, Any]
    strength: float = 0.5  # 0.0 to 1.0
    emotional_weight: float = (
        0.0  # -1.0 to 1.0 (negative = traumatic, positive = pleasant)
    )

    # Timing
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    last_accessed: float = field(default_factory=lambda: datetime.now().timestamp())
    last_reinforced: float = field(default_factory=lambda: datetime.now().timestamp())

    # Context and associations
    tags: List[str] = field(default_factory=list)
    associated_entities: List[str] = field(default_factory=list)
    associated_locations: List[str] = field(default_factory=list)
    related_memories: List[str] = field(default_factory=list)  # IDs of related memories

    # Decay and consolidation
    decay_rate: float = 0.01  # How fast this memory fades
    consolidation_level: float = 0.0  # How well consolidated (0.0 to 1.0)
    access_count: int = 0
    reinforcement_count: int = 0

    # Source and reliability
    source: str = "experience"  # experience, told, inferred, etc.
    reliability: float = 1.0  # How reliable/accurate this memory is

    def get_current_strength(self) -> float:
        """Calculate current memory strength accounting for decay."""
        time_since_reinforcement = datetime.now().timestamp() - self.last_reinforced
        decay_factor = math.exp(
            -self.decay_rate * time_since_reinforcement / (24 * 3600)
        )  # Daily decay
        return self.strength * decay_factor * (0.5 + 0.5 * self.consolidation_level)

    def get_retrieval_probability(self, query_relevance: float = 1.0) -> float:
        """Calculate probability this memory will be retrieved for a query."""
        current_strength = self.get_current_strength()
        emotional_boost = (
            abs(self.emotional_weight) * 0.2
        )  # Emotional memories more retrievable
        recency_boost = (
            max(
                0,
                1.0
                - (datetime.now().timestamp() - self.last_accessed) / (7 * 24 * 3600),
            )
            * 0.1
        )
        return min(
            1.0, current_strength * query_relevance + emotional_boost + recency_boost
        )


@dataclass
class MemoryQuery:
    """Query parameters for memory retrieval."""

    keywords: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    time_range: Optional[Tuple[float, float]] = None
    memory_types: List[MemoryType] = field(default_factory=list)
    emotional_range: Optional[Tuple[float, float]] = None
    minimum_strength: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)


class MemoryManager:
    """
    Advanced memory management system for PersonaAgent.

    Responsibilities:
    - Store and organize memories by type and content
    - Handle memory decay and consolidation over time
    - Provide intelligent memory retrieval with relevance scoring
    - Manage memory capacity and cleanup
    - Support different memory types and strengths
    - Maintain associations between related memories
    """

    def __init__(self, character_id: str, logger: Optional[logging.Logger] = None):
        self.character_id = character_id
        self.logger = logger or logging.getLogger(__name__)

        # Memory storage by type
        self._memories: Dict[str, Memory] = {}
        self._memories_by_type: Dict[MemoryType, List[str]] = {
            memory_type: [] for memory_type in MemoryType
        }

        # Working memory (temporary, limited capacity)
        self._working_memory: List[str] = []  # Memory IDs in working memory
        self._working_memory_capacity = 7  # Miller's magic number

        # Memory statistics and metrics
        self._stats = {
            "total_memories": 0,
            "memories_by_type": {mt.value: 0 for mt in MemoryType},
            "consolidations_performed": 0,
            "memories_forgotten": 0,
            "average_access_frequency": 0.0,
        }

        # Configuration
        self._config = {
            "max_total_memories": 10000,
            "consolidation_threshold": 0.7,
            "forgetting_threshold": 0.1,
            "emotional_memory_bonus": 0.3,
            "working_memory_decay_rate": 0.1,
        }

        # Memory associations graph
        self._memory_associations: Dict[str, Dict[str, float]] = (
            {}
        )  # memory_id -> {related_id: strength}

    async def store_memory(
        self, memory: Dict[str, Any], memory_type: str = "episodic"
    ) -> bool:
        """
        Store a new memory in the system.

        Args:
            memory: Memory content and metadata
            memory_type: Type of memory to store

        Returns:
            bool: True if storage successful
        """
        try:
            memory_id = f"{self.character_id}_mem_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self._memories)}"

            # Create memory object
            memory_obj = Memory(
                memory_id=memory_id,
                memory_type=MemoryType(memory_type),
                content=memory.get("content", {}),
                strength=memory.get("strength", 0.7),
                emotional_weight=memory.get("emotional_weight", 0.0),
                tags=memory.get("tags", []),
                associated_entities=memory.get("entities", []),
                associated_locations=memory.get("locations", []),
                source=memory.get("source", "experience"),
                reliability=memory.get("reliability", 1.0),
            )

            # Adjust initial strength based on emotional weight
            if abs(memory_obj.emotional_weight) > 0.5:
                memory_obj.strength += self._config["emotional_memory_bonus"]
                memory_obj.strength = min(1.0, memory_obj.strength)

            # Store memory
            self._memories[memory_id] = memory_obj
            self._memories_by_type[MemoryType(memory_type)].append(memory_id)

            # Update statistics
            self._stats["total_memories"] += 1
            self._stats["memories_by_type"][memory_type] += 1

            # Add to working memory if appropriate
            if (
                memory_type in ["episodic", "emotional"]
                or abs(memory_obj.emotional_weight) > 0.3
            ):
                await self._add_to_working_memory(memory_id)

            # Create associations with existing memories
            await self._create_memory_associations(memory_obj)

            # Manage memory capacity
            await self._manage_memory_capacity()

            self.logger.debug(f"Stored {memory_type} memory: {memory_id}")
            return True

        except Exception as e:
            self.logger.error(f"Memory storage failed: {e}")
            return False

    async def retrieve_memories(
        self, query: Dict[str, Any], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories based on query parameters.

        Args:
            query: Query parameters and criteria
            limit: Maximum number of memories to return

        Returns:
            List of retrieved memory data
        """
        try:
            # Convert dict query to MemoryQuery object
            memory_query = MemoryQuery(
                keywords=query.get("keywords", []),
                entities=query.get("entities", []),
                locations=query.get("locations", []),
                memory_types=[MemoryType(mt) for mt in query.get("memory_types", [])],
                minimum_strength=query.get("minimum_strength", 0.0),
                context=query.get("context", {}),
            )

            # Get candidate memories
            candidates = await self._get_candidate_memories(memory_query)

            # Score and rank candidates
            scored_memories = []
            for memory_id in candidates:
                memory = self._memories[memory_id]
                relevance_score = await self._calculate_relevance_score(
                    memory, memory_query
                )
                retrieval_probability = memory.get_retrieval_probability(
                    relevance_score
                )

                scored_memories.append((memory, relevance_score, retrieval_probability))

            # Sort by retrieval probability
            scored_memories.sort(key=lambda x: x[2], reverse=True)

            # Select top memories and update access statistics
            retrieved_memories = []
            for memory, relevance, probability in scored_memories[:limit]:
                if probability > 0.1:  # Minimum threshold for retrieval
                    # Update access statistics
                    memory.access_count += 1
                    memory.last_accessed = datetime.now().timestamp()

                    # Add to working memory
                    await self._add_to_working_memory(memory.memory_id)

                    # Convert to return format
                    memory_data = await self._memory_to_dict(memory)
                    memory_data["relevance_score"] = relevance
                    memory_data["retrieval_probability"] = probability

                    retrieved_memories.append(memory_data)

            self.logger.debug(
                f"Retrieved {len(retrieved_memories)} memories from {len(candidates)} candidates"
            )
            return retrieved_memories

        except Exception as e:
            self.logger.error(f"Memory retrieval failed: {e}")
            return []

    async def consolidate_memories(self) -> None:
        """
        Move important short-term memories to long-term storage.
        Perform memory consolidation based on access patterns and importance.
        """
        try:
            consolidation_candidates = []

            # Find memories that qualify for consolidation
            for memory_id, memory in self._memories.items():
                if memory.consolidation_level < self._config["consolidation_threshold"]:
                    # Calculate consolidation score
                    consolidation_score = await self._calculate_consolidation_score(
                        memory
                    )
                    if consolidation_score > 0.5:
                        consolidation_candidates.append((memory, consolidation_score))

            # Sort by consolidation score
            consolidation_candidates.sort(key=lambda x: x[1], reverse=True)

            # Consolidate top candidates
            consolidated_count = 0
            for memory, score in consolidation_candidates[
                :20
            ]:  # Limit per consolidation cycle
                await self._consolidate_memory(memory)
                consolidated_count += 1

            # Update statistics
            self._stats["consolidations_performed"] += consolidated_count

            self.logger.info(f"Consolidated {consolidated_count} memories")

        except Exception as e:
            self.logger.error(f"Memory consolidation failed: {e}")

    async def reinforce_memory(
        self, memory_id: str, reinforcement_strength: float = 0.1
    ) -> bool:
        """
        Reinforce a specific memory to prevent decay.

        Args:
            memory_id: ID of memory to reinforce
            reinforcement_strength: Amount to strengthen (0.0 to 1.0)

        Returns:
            bool: True if reinforcement successful
        """
        try:
            if memory_id not in self._memories:
                return False

            memory = self._memories[memory_id]

            # Increase memory strength
            old_strength = memory.strength
            memory.strength = min(1.0, memory.strength + reinforcement_strength)
            memory.reinforcement_count += 1
            memory.last_reinforced = datetime.now().timestamp()

            # Update consolidation level
            memory.consolidation_level = min(
                1.0, memory.consolidation_level + reinforcement_strength * 0.5
            )

            self.logger.debug(
                f"Reinforced memory {memory_id}: {old_strength:.2f} -> {memory.strength:.2f}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Memory reinforcement failed: {e}")
            return False

    async def forget_memory(
        self, memory_id: str, reason: str = "natural_decay"
    ) -> bool:
        """
        Remove a memory from the system.

        Args:
            memory_id: ID of memory to forget
            reason: Reason for forgetting

        Returns:
            bool: True if successful
        """
        try:
            if memory_id not in self._memories:
                return False

            memory = self._memories[memory_id]

            # Remove from type index
            if memory_id in self._memories_by_type[memory.memory_type]:
                self._memories_by_type[memory.memory_type].remove(memory_id)

            # Remove from working memory
            if memory_id in self._working_memory:
                self._working_memory.remove(memory_id)

            # Remove associations
            if memory_id in self._memory_associations:
                # Remove bidirectional associations
                for related_id, strength in self._memory_associations[
                    memory_id
                ].items():
                    if related_id in self._memory_associations:
                        self._memory_associations[related_id].pop(memory_id, None)
                del self._memory_associations[memory_id]

            # Remove memory
            del self._memories[memory_id]

            # Update statistics
            self._stats["total_memories"] -= 1
            self._stats["memories_by_type"][memory.memory_type.value] -= 1
            self._stats["memories_forgotten"] += 1

            self.logger.debug(f"Forgot memory {memory_id} ({reason})")
            return True

        except Exception as e:
            self.logger.error(f"Memory forgetting failed: {e}")
            return False

    async def get_working_memory(self) -> List[Dict[str, Any]]:
        """Get current working memory contents."""
        try:
            working_memories = []

            for memory_id in self._working_memory:
                if memory_id in self._memories:
                    memory = self._memories[memory_id]
                    memory_data = await self._memory_to_dict(memory)
                    working_memories.append(memory_data)

            return working_memories

        except Exception as e:
            self.logger.error(f"Working memory retrieval failed: {e}")
            return []

    async def get_memory_statistics(self) -> Dict[str, Any]:
        """Get comprehensive memory system statistics."""
        try:
            # Calculate average memory strength
            if self._memories:
                total_strength = sum(
                    memory.get_current_strength() for memory in self._memories.values()
                )
                avg_strength = total_strength / len(self._memories)
            else:
                avg_strength = 0.0

            # Memory type distribution
            type_distribution = {}
            for memory_type, memory_ids in self._memories_by_type.items():
                type_distribution[memory_type.value] = len(memory_ids)

            # Emotional memory distribution
            emotional_memories = {"positive": 0, "negative": 0, "neutral": 0}

            for memory in self._memories.values():
                if memory.emotional_weight > 0.2:
                    emotional_memories["positive"] += 1
                elif memory.emotional_weight < -0.2:
                    emotional_memories["negative"] += 1
                else:
                    emotional_memories["neutral"] += 1

            # Consolidation status
            consolidated_memories = sum(
                1
                for memory in self._memories.values()
                if memory.consolidation_level >= self._config["consolidation_threshold"]
            )

            return {
                "total_memories": len(self._memories),
                "working_memory_size": len(self._working_memory),
                "average_strength": avg_strength,
                "type_distribution": type_distribution,
                "emotional_distribution": emotional_memories,
                "consolidated_memories": consolidated_memories,
                "memory_associations": len(self._memory_associations),
                "stats": self._stats.copy(),
            }

        except Exception as e:
            self.logger.error(f"Memory statistics calculation failed: {e}")
            return {"error": str(e)}

    async def save_memory_state(self, file_path: str) -> bool:
        """Save memory system state to file."""
        try:
            # Prepare serializable data
            memories_data = {}
            for memory_id, memory in self._memories.items():
                memories_data[memory_id] = {
                    "memory_id": memory.memory_id,
                    "memory_type": memory.memory_type.value,
                    "content": memory.content,
                    "strength": memory.strength,
                    "emotional_weight": memory.emotional_weight,
                    "created_at": memory.created_at,
                    "last_accessed": memory.last_accessed,
                    "last_reinforced": memory.last_reinforced,
                    "tags": memory.tags,
                    "associated_entities": memory.associated_entities,
                    "associated_locations": memory.associated_locations,
                    "related_memories": memory.related_memories,
                    "decay_rate": memory.decay_rate,
                    "consolidation_level": memory.consolidation_level,
                    "access_count": memory.access_count,
                    "reinforcement_count": memory.reinforcement_count,
                    "source": memory.source,
                    "reliability": memory.reliability,
                }

            state_data = {
                "character_id": self.character_id,
                "memories": memories_data,
                "working_memory": self._working_memory,
                "memory_associations": self._memory_associations,
                "stats": self._stats,
                "config": self._config,
                "saved_at": datetime.now().isoformat(),
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Memory state saved to {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Memory state save failed: {e}")
            return False

    async def load_memory_state(self, file_path: str) -> bool:
        """Load memory system state from file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                state_data = json.load(f)

            # Validate character ID
            if state_data.get("character_id") != self.character_id:
                self.logger.error("Character ID mismatch in memory state file")
                return False

            # Load memories
            self._memories = {}
            self._memories_by_type = {memory_type: [] for memory_type in MemoryType}

            for memory_id, memory_data in state_data.get("memories", {}).items():
                memory = Memory(
                    memory_id=memory_data["memory_id"],
                    memory_type=MemoryType(memory_data["memory_type"]),
                    content=memory_data["content"],
                    strength=memory_data["strength"],
                    emotional_weight=memory_data["emotional_weight"],
                    created_at=memory_data["created_at"],
                    last_accessed=memory_data["last_accessed"],
                    last_reinforced=memory_data["last_reinforced"],
                    tags=memory_data["tags"],
                    associated_entities=memory_data["associated_entities"],
                    associated_locations=memory_data["associated_locations"],
                    related_memories=memory_data["related_memories"],
                    decay_rate=memory_data["decay_rate"],
                    consolidation_level=memory_data["consolidation_level"],
                    access_count=memory_data["access_count"],
                    reinforcement_count=memory_data["reinforcement_count"],
                    source=memory_data["source"],
                    reliability=memory_data["reliability"],
                )

                self._memories[memory_id] = memory
                self._memories_by_type[memory.memory_type].append(memory_id)

            # Load other state
            self._working_memory = state_data.get("working_memory", [])
            self._memory_associations = state_data.get("memory_associations", {})
            self._stats.update(state_data.get("stats", {}))
            self._config.update(state_data.get("config", {}))

            self.logger.info(f"Memory state loaded from {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Memory state load failed: {e}")
            return False

    # Private helper methods

    async def _add_to_working_memory(self, memory_id: str) -> None:
        """Add memory to working memory with capacity management."""
        try:
            if memory_id in self._working_memory:
                # Move to front (most recent)
                self._working_memory.remove(memory_id)
                self._working_memory.insert(0, memory_id)
            else:
                # Add to front
                self._working_memory.insert(0, memory_id)

                # Manage capacity
                if len(self._working_memory) > self._working_memory_capacity:
                    removed_id = self._working_memory.pop()
                    self.logger.debug(
                        f"Removed {removed_id} from working memory (capacity limit)"
                    )

        except Exception as e:
            self.logger.debug(f"Working memory addition failed: {e}")

    async def _get_candidate_memories(self, query: MemoryQuery) -> List[str]:
        """Get candidate memories that might match the query."""
        try:
            candidates = set()

            # Filter by memory type
            if query.memory_types:
                for memory_type in query.memory_types:
                    candidates.update(self._memories_by_type.get(memory_type, []))
            else:
                # Include all memories
                candidates.update(self._memories.keys())

            # Filter by minimum strength
            if query.minimum_strength > 0:
                strength_filtered = set()
                for memory_id in candidates:
                    memory = self._memories[memory_id]
                    if memory.get_current_strength() >= query.minimum_strength:
                        strength_filtered.add(memory_id)
                candidates = strength_filtered

            # Filter by entities
            if query.entities:
                entity_filtered = set()
                for memory_id in candidates:
                    memory = self._memories[memory_id]
                    if any(
                        entity in memory.associated_entities
                        for entity in query.entities
                    ):
                        entity_filtered.add(memory_id)
                candidates = entity_filtered

            # Filter by locations
            if query.locations:
                location_filtered = set()
                for memory_id in candidates:
                    memory = self._memories[memory_id]
                    if any(
                        location in memory.associated_locations
                        for location in query.locations
                    ):
                        location_filtered.add(memory_id)
                candidates = location_filtered

            return list(candidates)

        except Exception as e:
            self.logger.error(f"Candidate memory filtering failed: {e}")
            return []

    async def _calculate_relevance_score(
        self, memory: Memory, query: MemoryQuery
    ) -> float:
        """Calculate how relevant a memory is to the query."""
        try:
            score = 0.0

            # Keyword matching
            if query.keywords:
                content_text = str(memory.content).lower()
                keyword_matches = sum(
                    1 for keyword in query.keywords if keyword.lower() in content_text
                )
                score += (keyword_matches / len(query.keywords)) * 0.4

            # Entity matching
            if query.entities:
                entity_matches = len(
                    set(query.entities) & set(memory.associated_entities)
                )
                score += (entity_matches / len(query.entities)) * 0.3

            # Location matching
            if query.locations:
                location_matches = len(
                    set(query.locations) & set(memory.associated_locations)
                )
                score += (location_matches / len(query.locations)) * 0.2

            # Context matching (flexible matching based on context keys)
            if query.context:
                context_score = 0.0
                for key, value in query.context.items():
                    if key in memory.content:
                        if memory.content[key] == value:
                            context_score += 1.0
                        elif str(value).lower() in str(memory.content[key]).lower():
                            context_score += 0.5
                if query.context:
                    score += (context_score / len(query.context)) * 0.1

            # Base relevance if no specific criteria matched
            if score == 0.0 and not (
                query.keywords or query.entities or query.locations or query.context
            ):
                score = 0.5  # Default relevance

            return min(1.0, score)

        except Exception as e:
            self.logger.debug(f"Relevance score calculation failed: {e}")
            return 0.0

    async def _calculate_consolidation_score(self, memory: Memory) -> float:
        """Calculate how much a memory should be consolidated."""
        try:
            score = 0.0

            # Access frequency
            age_days = (datetime.now().timestamp() - memory.created_at) / (24 * 3600)
            if age_days > 0:
                access_frequency = memory.access_count / age_days
                score += (
                    min(0.3, access_frequency / 5.0) * 0.4
                )  # Normalize to reasonable frequency

            # Emotional significance
            emotional_score = abs(memory.emotional_weight) * 0.3
            score += emotional_score

            # Memory strength
            score += memory.get_current_strength() * 0.2

            # Association richness (memories with more associations are more important)
            association_count = len(self._memory_associations.get(memory.memory_id, {}))
            association_score = min(0.1, association_count / 20.0)  # Normalize
            score += association_score

            # Source reliability
            score += memory.reliability * 0.1

            return min(1.0, score)

        except Exception as e:
            self.logger.debug(f"Consolidation score calculation failed: {e}")
            return 0.0

    async def _consolidate_memory(self, memory: Memory) -> None:
        """Perform consolidation on a specific memory."""
        try:
            # Increase consolidation level
            old_level = memory.consolidation_level
            memory.consolidation_level = min(1.0, memory.consolidation_level + 0.3)

            # Reduce decay rate for consolidated memories
            memory.decay_rate *= 0.8

            # Strengthen memory slightly
            memory.strength = min(1.0, memory.strength + 0.1)

            self.logger.debug(
                f"Consolidated memory {memory.memory_id}: level {old_level:.2f} -> {memory.consolidation_level:.2f}"
            )

        except Exception as e:
            self.logger.debug(f"Memory consolidation failed: {e}")

    async def _create_memory_associations(self, new_memory: Memory) -> None:
        """Create associations between new memory and existing memories."""
        try:
            if new_memory.memory_id not in self._memory_associations:
                self._memory_associations[new_memory.memory_id] = {}

            # Find related memories
            for memory_id, existing_memory in self._memories.items():
                if memory_id == new_memory.memory_id:
                    continue

                association_strength = (
                    await self._calculate_memory_association_strength(
                        new_memory, existing_memory
                    )
                )

                if association_strength > 0.3:
                    # Create bidirectional association
                    self._memory_associations[new_memory.memory_id][
                        memory_id
                    ] = association_strength

                    if memory_id not in self._memory_associations:
                        self._memory_associations[memory_id] = {}
                    self._memory_associations[memory_id][
                        new_memory.memory_id
                    ] = association_strength

        except Exception as e:
            self.logger.debug(f"Memory association creation failed: {e}")

    async def _calculate_memory_association_strength(
        self, memory1: Memory, memory2: Memory
    ) -> float:
        """Calculate association strength between two memories."""
        try:
            strength = 0.0

            # Entity overlap
            entity_overlap = len(
                set(memory1.associated_entities) & set(memory2.associated_entities)
            )
            if memory1.associated_entities and memory2.associated_entities:
                entity_score = entity_overlap / max(
                    len(memory1.associated_entities), len(memory2.associated_entities)
                )
                strength += entity_score * 0.4

            # Location overlap
            location_overlap = len(
                set(memory1.associated_locations) & set(memory2.associated_locations)
            )
            if memory1.associated_locations and memory2.associated_locations:
                location_score = location_overlap / max(
                    len(memory1.associated_locations), len(memory2.associated_locations)
                )
                strength += location_score * 0.3

            # Tag overlap
            tag_overlap = len(set(memory1.tags) & set(memory2.tags))
            if memory1.tags and memory2.tags:
                tag_score = tag_overlap / max(len(memory1.tags), len(memory2.tags))
                strength += tag_score * 0.2

            # Temporal proximity
            time_diff = abs(memory1.created_at - memory2.created_at)
            if time_diff < 24 * 3600:  # Within 24 hours
                temporal_score = 1.0 - (time_diff / (24 * 3600))
                strength += temporal_score * 0.1

            return min(1.0, strength)

        except Exception as e:
            self.logger.debug(f"Association strength calculation failed: {e}")
            return 0.0

    async def _manage_memory_capacity(self) -> None:
        """Manage memory system capacity by removing weak memories."""
        try:
            if len(self._memories) <= self._config["max_total_memories"]:
                return

            # Find weak memories to remove
            weak_memories = []
            for memory_id, memory in self._memories.items():
                current_strength = memory.get_current_strength()
                if current_strength < self._config["forgetting_threshold"]:
                    weak_memories.append((memory_id, current_strength))

            # Sort by strength (weakest first)
            weak_memories.sort(key=lambda x: x[1])

            # Remove excess memories
            excess_count = len(self._memories) - self._config["max_total_memories"]
            removal_count = min(len(weak_memories), excess_count)

            for memory_id, strength in weak_memories[:removal_count]:
                await self.forget_memory(memory_id, "capacity_management")

            if removal_count > 0:
                self.logger.debug(
                    f"Removed {removal_count} weak memories for capacity management"
                )

        except Exception as e:
            self.logger.debug(f"Memory capacity management failed: {e}")

    async def _memory_to_dict(self, memory: Memory) -> Dict[str, Any]:
        """Convert memory object to dictionary format."""
        return {
            "memory_id": memory.memory_id,
            "memory_type": memory.memory_type.value,
            "content": memory.content,
            "strength": memory.get_current_strength(),
            "emotional_weight": memory.emotional_weight,
            "created_at": memory.created_at,
            "last_accessed": memory.last_accessed,
            "tags": memory.tags,
            "entities": memory.associated_entities,
            "locations": memory.associated_locations,
            "consolidation_level": memory.consolidation_level,
            "access_count": memory.access_count,
            "source": memory.source,
            "reliability": memory.reliability,
        }
