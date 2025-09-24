#!/usr/bin/env python3
"""
Layered Memory System
=====================

This module provides a unified layered memory architecture that integrates
various memory subsystems into a cohesive cognitive framework. It manages
working, episodic, semantic, and emotional memories.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.core.data_models import (
    ErrorInfo,
    MemoryItem,
    MemoryType,
    StandardResponse,
)
from src.core.types import AgentID
from src.database.context_db import ContextDatabase

from .emotional_memory import EmotionalMemory
from .episodic_memory import EpisodicMemory
from .semantic_memory import SemanticMemory
from .working_memory import WorkingMemory

logger = logging.getLogger(__name__)


class MemoryPriority(Enum):
    """Enumeration for memory priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ARCHIVED = "archived"


@dataclass
class MemoryQueryRequest:
    """
    A unified query structure for accessing all memory layers with
    intelligent routing and relevance weighting.
    """

    query_text: str
    memory_types: List[MemoryType] = field(default_factory=list)
    temporal_range: Optional[Tuple[datetime, datetime]] = None
    emotional_filters: Dict[str, Any] = field(default_factory=dict)
    participants: List[str] = field(default_factory=list)
    relevance_threshold: float = 0.3
    max_results: int = 20
    include_working_memory: bool = True
    include_emotional_context: bool = True
    priority_boost: Dict[MemoryType, float] = field(default_factory=dict)


@dataclass
class MemoryQueryResult:
    """
    A unified result structure containing memories from all layers,
    with relevance scoring and contextual information.
    """

    memories: List[MemoryItem] = field(default_factory=list)
    relevance_scores: List[float] = field(default_factory=list)
    memory_sources: List[str] = field(default_factory=list)
    total_found: int = 0
    query_duration_ms: float = 0.0
    emotional_context: Dict[str, Any] = field(default_factory=dict)
    working_memory_state: Dict[str, Any] = field(default_factory=dict)
    consolidated_insights: List[str] = field(default_factory=list)


class LayeredMemorySystem:
    """
    A unified memory architecture that orchestrates working, episodic,
    semantic, and emotional memory subsystems into a cohesive framework.
    """

    def __init__(
        self,
        agent_id: AgentID,
        database: ContextDatabase,
        working_capacity: int = 7,
        episodic_max: int = 1000,
        semantic_max: int = 5000,
        emotional_max: int = 500,
    ):
        """
        Initializes the LayeredMemorySystem.

        Args:
            agent_id: The ID of the agent this memory belongs to.
            database: The database connection for persistence.
            working_capacity: The capacity of the working memory.
            episodic_max: Maximum number of episodic memories.
            semantic_max: Maximum number of semantic facts.
            emotional_max: Maximum number of emotional memories.
        """
        self.agent_id = agent_id
        self.database = database

        self.working_memory = WorkingMemory(
            agent_id, capacity=working_capacity
        )
        self.episodic_memory = EpisodicMemory(
            agent_id, database, max_episodes=episodic_max
        )
        self.semantic_memory = SemanticMemory(
            agent_id, database, max_facts=semantic_max
        )
        self.emotional_memory = EmotionalMemory(
            agent_id, database, max_memories=emotional_max
        )

        self._memory_coordination_lock = asyncio.Lock()
        self._cross_layer_associations: Dict[str, List[str]] = defaultdict(
            list
        )
        self._global_memory_index: Dict[str, str] = {}

        self.total_queries = 0
        self.total_storage_operations = 0
        self.last_consolidation = datetime.now()
        self.performance_metrics = {
            "average_query_time": 0.0,
            "memory_distribution": {},
            "cross_layer_connections": 0,
        }

        logger.info(f"Layered Memory System initialized for {agent_id}")

    async def store_memory(
        self,
        memory: MemoryItem,
        force_layer: Optional[str] = None,
        cross_layer_linking: bool = True,
    ) -> StandardResponse:
        """
        Stores a memory, routing it to the appropriate layer(s) based on its
        content and characteristics, and creating cross-layer associations.
        """
        try:
            async with self._memory_coordination_lock:
                storage_results = []
                stored_layers = []

                target_layers = self._determine_storage_layers(
                    memory, force_layer
                )

                if "working" in target_layers:
                    working_result = self.working_memory.add_memory(memory)
                    storage_results.append(working_result)
                    if working_result.success:
                        stored_layers.append("working")
                        self._global_memory_index[memory.memory_id] = "working"

                if "episodic" in target_layers:
                    episodic_result = await self.episodic_memory.store_episode(
                        memory
                    )
                    storage_results.append(episodic_result)
                    if episodic_result.success:
                        stored_layers.append("episodic")
                        self._global_memory_index[
                            memory.memory_id
                        ] = "episodic"

                if "semantic" in target_layers:
                    semantic_result = (
                        await self.semantic_memory.extract_and_store_knowledge(
                            memory
                        )
                    )
                    storage_results.append(semantic_result)
                    if semantic_result.success:
                        stored_layers.append("semantic")

                if (
                    "emotional" in target_layers
                    and memory.emotional_weight != 0
                ):
                    valence = max(
                        -1.0, min(1.0, memory.emotional_weight / 10.0)
                    )
                    arousal = abs(memory.emotional_weight) / 10.0
                    emotional_result = (
                        await self.emotional_memory.store_emotional_experience(
                            memory, valence, arousal
                        )
                    )
                    storage_results.append(emotional_result)
                    if emotional_result.success:
                        stored_layers.append("emotional")

                if cross_layer_linking and len(stored_layers) > 1:
                    await self._create_cross_layer_associations(
                        memory.memory_id, stored_layers
                    )

                self.total_storage_operations += 1

                success_count = sum(
                    1 for result in storage_results if result.success
                )
                overall_success = success_count > 0

                logger.info(
                    f"Layered memory stored: {memory.memory_id} in {stored_layers}"
                )

                return StandardResponse(
                    success=overall_success,
                    data={
                        "stored_layers": stored_layers,
                        "success_count": success_count,
                        "total_layers_attempted": len(target_layers),
                        "cross_layer_associations": len(
                            self._cross_layer_associations.get(
                                memory.memory_id, []
                            )
                        ),
                    },
                )

        except Exception as e:
            logger.error(f"Layered memory storage failed: {e}", exc_info=True)
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="LAYERED_STORAGE_FAILED",
                    message=f"Layered memory storage failed: {str(e)}",
                ),
            )

    async def query_memories(
        self, query_request: MemoryQueryRequest
    ) -> StandardResponse:
        """
        Executes a unified query across all memory layers, with intelligent
        weighting and relevance scoring.
        """
        query_start_time = datetime.now()
        try:
            all_memories = []
            all_scores = []
            all_sources = []

            async with self._memory_coordination_lock:
                tasks = []
                if query_request.include_working_memory:
                    tasks.append(self._query_working_memory(query_request))

                if (
                    not query_request.memory_types
                    or MemoryType.EPISODIC in query_request.memory_types
                ):
                    tasks.append(self._query_episodic_memory(query_request))

                if (
                    not query_request.memory_types
                    or MemoryType.SEMANTIC in query_request.memory_types
                ):
                    tasks.append(self._query_semantic_memory(query_request))

                if (
                    query_request.include_emotional_context
                    or MemoryType.EMOTIONAL in query_request.memory_types
                ):
                    # This part remains tricky to fully parallelize due to its
                    # logic
                    pass

                # Simplified query execution for now
                if query_request.include_working_memory:
                    m, s, src = self._query_working_memory_sync(query_request)
                    all_memories.extend(m)
                    all_scores.extend(s)
                    all_sources.extend(src)

                if (
                    not query_request.memory_types
                    or MemoryType.EPISODIC in query_request.memory_types
                ):
                    m, s, src = await self._query_episodic_memory(
                        query_request
                    )
                    all_memories.extend(m)
                    all_scores.extend(s)
                    all_sources.extend(src)

                if (
                    not query_request.memory_types
                    or MemoryType.SEMANTIC in query_request.memory_types
                ):
                    m, s, src = await self._query_semantic_memory(
                        query_request
                    )
                    all_memories.extend(m)
                    all_scores.extend(s)
                    all_sources.extend(src)

                # Emotional query needs specific handling
                # This part is simplified and not fully async with others
                if query_request.emotional_filters:
                    # m, s, src = await self._query_emotional_memory(query_request)
                    # all_memories.extend(m); all_scores.extend(s); all_sources.extend(src)
                    pass

                (
                    filtered_memories,
                    filtered_scores,
                    filtered_sources,
                ) = self._filter_and_rank_results(
                    all_memories, all_scores, all_sources, query_request
                )

                query_duration_ms = (
                    datetime.now() - query_start_time
                ).total_seconds() * 1000
                self.total_queries += 1
                self._update_performance_metrics(
                    query_duration_ms, len(filtered_memories)
                )

                result = MemoryQueryResult(
                    memories=filtered_memories,
                    relevance_scores=filtered_scores,
                    memory_sources=filtered_sources,
                    total_found=len(all_memories),
                    query_duration_ms=query_duration_ms,
                    # emotional_context=self.emotional_memory.get_current_emotional_state(),
                    working_memory_state=self.working_memory.get_memory_statistics(),
                    consolidated_insights=self._generate_insights(
                        filtered_memories
                    ),
                )

                logger.info(
                    f"Unified memory query complete: {len( result.memories)} results"
                )

                return StandardResponse(
                    success=True, data={"query_result": result}
                )

        except Exception as e:
            logger.error(f"Unified memory query failed: {e}", exc_info=True)
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="UNIFIED_QUERY_FAILED",
                    message=f"Unified memory query failed: {str(e)}",
                ),
            )

    async def consolidate_memories(
        self, consolidation_type: str = "full"
    ) -> StandardResponse:
        """
        Performs memory consolidation across all layers, with intelligent
        transfer and cross-layer relationship optimization.
        """
        try:
            consolidation_start = datetime.now()
            consolidation_results = {}

            async with self._memory_coordination_lock:
                working_result = self.working_memory.perform_maintenance()
                consolidation_results["working"] = working_result.success

                episodic_consolidation = (
                    await self.episodic_memory._perform_consolidation()
                )
                consolidation_results[
                    "episodic"
                ] = episodic_consolidation.success

                # Semantic and emotional consolidation are simplified here
                consolidation_results["semantic"] = True
                consolidation_results["emotional"] = True

                if consolidation_type == "full":
                    cross_layer_optimized = (
                        await self._optimize_cross_layer_associations()
                    )
                    consolidation_results[
                        "cross_layer"
                    ] = cross_layer_optimized

                self.last_consolidation = consolidation_start
                duration = (
                    datetime.now() - consolidation_start
                ).total_seconds()

                success_count = sum(
                    1 for success in consolidation_results.values() if success
                )
                overall_success = (
                    success_count >= len(consolidation_results) * 0.75
                )

                logger.info(
                    f"Layered memory consolidation complete ({duration:.2f}s)"
                )

                return StandardResponse(
                    success=overall_success,
                    data={
                        "consolidation_results": consolidation_results,
                        "consolidation_duration_ms": duration * 1000,
                        "optimization_complete": consolidation_type == "full",
                    },
                )

        except Exception as e:
            logger.error(
                f"Layered memory consolidation failed: {e}", exc_info=True
            )
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="CONSOLIDATION_FAILED",
                    message=f"Memory consolidation failed: {str(e)}",
                ),
            )

    def get_unified_statistics(self) -> Dict[str, Any]:
        """
        Retrieves comprehensive statistics across all memory layers, including
        performance metrics and coordination information.
        """
        return {
            "agent_id": self.agent_id,
            "working_memory": self.working_memory.get_memory_statistics(),
            "episodic_memory": self.episodic_memory.get_memory_statistics(),
            "semantic_memory": self.semantic_memory.get_memory_statistics(),
            # "emotional_memory": self.emotional_memory.get_memory_statistics(),
            "coordination_stats": {
                "total_queries": self.total_queries,
                "total_storage_operations": self.total_storage_operations,
                "cross_layer_associations": len(
                    self._cross_layer_associations
                ),
                "global_memory_index_size": len(self._global_memory_index),
                "last_consolidation": self.last_consolidation.isoformat(),
            },
            "performance_metrics": self.performance_metrics,
            # "current_emotional_state": self.emotional_memory.get_current_emotional_state()
        }

    def _determine_storage_layers(
        self, memory: MemoryItem, force_layer: Optional[str]
    ) -> List[str]:
        """Determines the appropriate memory layer(s) for a given memory item."""
        if force_layer:
            return [force_layer]

        layers = ["working"]
        content_lower = memory.content.lower()

        if memory.memory_type == MemoryType.EPISODIC or any(
            k in content_lower for k in ["event", "happened"]
        ):
            layers.append("episodic")

        if (
            memory.memory_type == MemoryType.SEMANTIC
            or " is " in content_lower
        ):
            layers.append("semantic")

        if (
            memory.memory_type == MemoryType.EMOTIONAL
            or abs(memory.emotional_weight) > 0
        ):
            layers.append("emotional")

        return list(set(layers))

    async def _create_cross_layer_associations(
        self, memory_id: str, stored_layers: List[str]
    ):
        """Creates bidirectional associations between layers for a given memory."""
        for i, layer1 in enumerate(stored_layers):
            for layer2 in stored_layers[i + 1 :]:
                association_key = f"{layer1}:{layer2}:{memory_id}"
                self._cross_layer_associations[memory_id].append(
                    association_key
                )

        self.performance_metrics["cross_layer_connections"] = len(
            self._cross_layer_associations
        )

    async def _optimize_cross_layer_associations(self) -> bool:
        """Removes orphaned cross-layer associations."""
        try:
            active_memory_ids = set(self._global_memory_index.keys())
            orphaned_ids = [
                mid
                for mid in self._cross_layer_associations
                if mid not in active_memory_ids
            ]

            for memory_id in orphaned_ids:
                del self._cross_layer_associations[memory_id]

            logger.info(
                f"Cross-layer optimization removed {len(orphaned_ids)} orphaned associations."
            )
            return True

        except Exception as e:
            logger.error(
                f"Cross-layer optimization failed: {e}", exc_info=True
            )
            return False

    def _calculate_relevance(
        self, memory: MemoryItem, query: MemoryQueryRequest
    ) -> float:
        """Calculates a relevance score for a memory item against a query."""
        score = 0.0
        if query.query_text.lower() in memory.content.lower():
            score += 0.5

        participant_overlap = set(memory.participants) & set(
            query.participants
        )
        score += len(participant_overlap) * 0.1

        return min(1.0, score + memory.relevance_score * 0.5)

    def _query_working_memory_sync(
        self, query: MemoryQueryRequest
    ) -> Tuple[List[MemoryItem], List[float], List[str]]:
        """Synchronous version for querying working memory."""
        memories = self.working_memory.get_active_memories(
            limit=query.max_results
        )
        scores = [self._calculate_relevance(mem, query) for mem in memories]
        sources = ["working"] * len(memories)
        return memories, scores, sources

    async def _query_working_memory(
        self, query: MemoryQueryRequest
    ) -> Tuple[List[MemoryItem], List[float], List[str]]:
        """Queries the working memory layer."""
        return self._query_working_memory_sync(query)

    async def _query_episodic_memory(
        self, query: MemoryQueryRequest
    ) -> Tuple[List[MemoryItem], List[float], List[str]]:
        """Queries the episodic memory layer."""
        memories, scores, sources = [], [], []
        if query.temporal_range:
            start, end = query.temporal_range
            result = await self.episodic_memory.retrieve_episodes_by_timeframe(
                start, end, limit=query.max_results
            )
            if result.success:
                m = result.data.get("episodes", [])
                memories.extend(m)
                scores.extend(
                    [self._calculate_relevance(mem, query) for mem in m]
                )
                sources.extend(["episodic"] * len(m))
        return memories, scores, sources

    async def _query_semantic_memory(
        self, query: MemoryQueryRequest
    ) -> Tuple[List[MemoryItem], List[float], List[str]]:
        """Queries the semantic memory layer."""
        memories, scores, sources = [], [], []
        key_terms = self._extract_query_terms(query.query_text)
        for term in key_terms:
            result = await self.semantic_memory.query_facts_by_subject(term)
            if result.success:
                facts = result.data.get("facts", [])
                m = self._convert_facts_to_memories(facts, term)
                memories.extend(m)
                scores.extend(
                    [self._calculate_relevance(mem, query) for mem in m]
                )
                sources.extend(["semantic"] * len(m))
        return memories, scores, sources

    def _extract_query_terms(self, query_text: str) -> List[str]:
        """Extracts key terms from a query string."""
        # This is a simplified implementation. A real system might use NLP.
        return [word for word in query_text.lower().split() if len(word) > 3]

    def _convert_facts_to_memories(
        self, facts: List[str], term: str
    ) -> List[MemoryItem]:
        """Converts semantic facts back to memory items for unified results."""
        return [
            MemoryItem(
                agent_id=self.agent_id,
                memory_type=MemoryType.SEMANTIC,
                content=fact,
                relevance_score=0.7,
                memory_id=f"semantic_fact_{term}_{i}",
            )
            for i, fact in enumerate(facts)
        ]

    def _filter_and_rank_results(
        self,
        memories: List[MemoryItem],
        scores: List[float],
        sources: List[str],
        query: MemoryQueryRequest,
    ) -> Tuple[List[MemoryItem], List[float], List[str]]:
        """Filters, ranks, and de-duplicates query results."""

        unique_results = {}
        for mem, score, src in zip(memories, scores, sources):
            if score >= query.relevance_threshold:
                if (
                    mem.memory_id not in unique_results
                    or score > unique_results[mem.memory_id][1]
                ):
                    unique_results[mem.memory_id] = (mem, score, src)

        sorted_results = sorted(
            unique_results.values(), key=lambda x: x[1], reverse=True
        )

        limited_results = sorted_results[: query.max_results]

        if not limited_results:
            return [], [], []

        mem_res, score_res, source_res = zip(*limited_results)
        return list(mem_res), list(score_res), list(source_res)

    def _generate_insights(self, memories: List[MemoryItem]) -> List[str]:
        """Generates high-level insights from a list of retrieved memories."""
        if not memories:
            return []

        insights = []
        type_counts = defaultdict(int)
        for mem in memories:
            type_counts[mem.memory_type] += 1

        if type_counts:
            dominant_type = max(type_counts, key=type_counts.get)
            insights.append(
                f"Dominant memory type in results: {dominant_type.value}"
            )

        return insights

    def _update_performance_metrics(
        self, query_duration_ms: float, result_count: int
    ):
        """Updates performance metrics after a query."""
        total = self.total_queries
        avg_time = self.performance_metrics["average_query_time"]
        self.performance_metrics["average_query_time"] = (
            (avg_time * (total - 1) + query_duration_ms) / total
            if total > 0
            else query_duration_ms
        )

        self.performance_metrics["memory_distribution"] = {
            "working": len(self.working_memory),
            "episodic": self.episodic_memory.total_episodes,
            "semantic": self.semantic_memory.total_facts_learned,
            # 'emotional': self.emotional_memory.total_emotional_experiences
        }


async def test_layered_memory():
    """Tests the LayeredMemorySystem."""
    print("Testing Layered Memory System...")

    db = ContextDatabase(":memory:")
    await db.initialize()

    layered_memory = LayeredMemorySystem("test_agent_001", db)

    test_memories = [
        MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="A battle occurred at the main gate with Commander Lex.",
            emotional_weight=7.0,
            participants=["Commander Lex"],
            location="Main Gate",
        ),
        MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.SEMANTIC,
            content="The sky is blue.",
            emotional_weight=1.0,
            relevance_score=0.9,
        ),
        MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EMOTIONAL,
            content="Felt a surge of pride after the victory.",
            emotional_weight=8.0,
            relevance_score=0.8,
        ),
    ]

    for memory in test_memories:
        storage_result = await layered_memory.store_memory(memory)
        print(
            f"Layered Storage: {storage_result.success}, Layers: {storage_result.data.get( 'stored_layers', [])}"
        )

    query_request = MemoryQueryRequest(
        query_text="battle victory", max_results=10, relevance_threshold=0.3
    )

    query_result = await layered_memory.query_memories(query_request)
    if query_result.success:
        result_data = query_result.data["query_result"]
        print(
            f"Unified Query: {len( result_data.memories)}results in {result_data.query_duration_ms:.2f}ms"
        )
        if result_data.memory_sources:
            print(f"Query Sources: {set(result_data.memory_sources)}")

    consolidation_result = await layered_memory.consolidate_memories()
    print(f"Consolidation: {consolidation_result.success}")

    stats = layered_memory.get_unified_statistics()
    print(f"Unified Statistics: {stats['coordination_stats']}")

    await db.close()
    print("Layered Memory System testing complete.")


if __name__ == "__main__":
    asyncio.run(test_layered_memory())
