#!/usr/bin/env python3
"""
Memory Query Engine
===================

This module provides an advanced memory query engine for searching across
all memory layers. It supports semantic understanding, contextual intelligence,
and various query types to retrieve relevant information efficiently.
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.core.data_models import ErrorInfo, MemoryItem, MemoryType, StandardResponse
from src.database.context_db import ContextDatabase

from .layered_memory import LayeredMemorySystem, MemoryQueryRequest, MemoryQueryResult

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Enumeration of different query types supported by the engine."""

    SIMPLE_TEXT = "simple_text"
    SEMANTIC = "semantic"
    TEMPORAL = "temporal"
    EMOTIONAL = "emotional"
    CONTEXTUAL = "contextual"
    ASSOCIATIVE = "associative"
    HYBRID = "hybrid"


@dataclass
class QueryContext:
    """
    Holds contextual information to guide intelligent query processing
    and result ranking.
    """

    current_situation: str = ""
    active_participants: List[str] = field(default_factory=list)
    location_context: str = ""
    emotional_state: str = "neutral"
    temporal_focus: Optional[str] = None  # e.g., "recent", "distant"
    priority_themes: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    boost_patterns: List[str] = field(default_factory=list)
    max_age_days: Optional[int] = None
    min_relevance: float = 0.3


@dataclass
class QueryMetrics:
    """
    Tracks comprehensive metrics for query performance and result quality analysis.
    """

    query_duration_ms: float = 0.0
    memories_searched: int = 0
    memories_matched: int = 0
    layers_queried: List[str] = field(default_factory=list)
    semantic_score: float = 0.0
    relevance_distribution: Dict[str, int] = field(default_factory=dict)
    query_complexity: float = 0.0
    cache_hits: int = 0
    processing_steps: List[str] = field(default_factory=list)


class MemoryQueryEngine:
    """
    A query processing system that provides advanced search capabilities
    across all memory layers with semantic understanding and contextual intelligence.
    """

    def __init__(
        self,
        layered_memory: LayeredMemorySystem,
        enable_semantic_search: bool = True,
        enable_query_cache: bool = True,
        cache_expiry_minutes: int = 30,
    ):
        """
        Initializes the MemoryQueryEngine.

        Args:
            layered_memory: The layered memory system for data access.
            enable_semantic_search: Flag to enable semantic similarity matching.
            enable_query_cache: Flag to enable query result caching.
            cache_expiry_minutes: Cache expiration time in minutes.
        """
        self.layered_memory = layered_memory
        self.enable_semantic_search = enable_semantic_search
        self.enable_query_cache = enable_query_cache
        self.cache_expiry_minutes = cache_expiry_minutes

        self._query_cache: Dict[str, Tuple[datetime, MemoryQueryResult]] = {}
        self._query_statistics: Dict[str, Any] = defaultdict(int)

        logger.info(f"MemoryQueryEngine initialized for {layered_memory.agent_id}")

    async def execute_query(
        self,
        query_text: str,
        context: Optional[QueryContext] = None,
        query_type: Optional[QueryType] = None,
    ) -> StandardResponse:
        """
        Executes an intelligent query with natural language understanding,
        contextual awareness, and multi-layer search optimization.
        """
        query_start_time = datetime.now()
        try:
            context = context or QueryContext()
            cache_key = self._generate_cache_key(query_text, context)

            if self.enable_query_cache and cache_key in self._query_cache:
                cached_time, cached_result = self._query_cache[cache_key]
                if (
                    datetime.now() - cached_time
                ).total_seconds() < self.cache_expiry_minutes * 60:
                    self._query_statistics["cache_hits"] += 1
                    logger.info(f"Query cache hit for: {query_text[:50]}...")
                    return StandardResponse(
                        success=True, data={"query_result": cached_result}
                    )

            query_type = query_type or self._analyze_query_type(query_text)

            processing_result = await self._process_query_by_type(
                query_text, context, query_type
            )
            if not processing_result.success:
                return processing_result

            query_result = processing_result.data["query_result"]
            enhanced_result = self._apply_contextual_ranking(
                query_result, context, query_text
            )

            query_duration_ms = (
                datetime.now() - query_start_time
            ).total_seconds() * 1000
            metrics = QueryMetrics(
                query_duration_ms=query_duration_ms,
                memories_searched=enhanced_result.total_found,
                memories_matched=len(enhanced_result.memories),
                layers_queried=list(set(enhanced_result.memory_sources)),
                query_complexity=self._calculate_query_complexity(query_text),
            )
            enhanced_result.query_duration_ms = query_duration_ms

            if self.enable_query_cache:
                self._query_cache[cache_key] = (datetime.now(), enhanced_result)
                self._cleanup_expired_cache()

            self._update_query_statistics(query_type, metrics)

            logger.info(
                f"Query executed: '{query_text[:50]}...' in {query_duration_ms:.2f}ms"
            )

            return StandardResponse(
                success=True,
                data={
                    "query_result": enhanced_result,
                    "query_metrics": metrics,
                    "query_type": query_type.value,
                },
            )

        except Exception as e:
            logger.error(f"Query execution failed: {e}", exc_info=True)
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="QUERY_FAILED", message=f"Query execution failed: {e}"
                ),
            )

    async def execute_associative_query(
        self, seed_memory_id: str, association_depth: int = 2, max_results: int = 15
    ) -> StandardResponse:
        """
        Executes an associative query to find related memories through
        semantic and contextual connections.
        """
        try:
            seed_memories = await self._get_memory_by_id(seed_memory_id)
            if not seed_memories:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="SEED_NOT_FOUND", message="Seed memory not found"
                    ),
                )

            seed_memory = seed_memories[0]
            associated_memories = []
            processed_ids = {seed_memory_id}

            current_level = [seed_memory]
            for depth in range(association_depth):
                next_level = []

                for memory in current_level:
                    # This is a simplified stand-in for a real association logic
                    associations = await self._find_contextual_associations(
                        memory, max_results
                    )

                    for assoc_memory, relevance in associations:
                        if (
                            assoc_memory.memory_id not in processed_ids
                            and len(associated_memories) < max_results
                        ):
                            associated_memories.append(
                                (assoc_memory, relevance, f"depth_{depth + 1}")
                            )
                            processed_ids.add(assoc_memory.memory_id)
                            next_level.append(assoc_memory)

                current_level = next_level
                if not current_level:
                    break

            associated_memories.sort(key=lambda x: x[1], reverse=True)

            result = MemoryQueryResult(
                memories=[mem for mem, _, _ in associated_memories],
                relevance_scores=[score for _, score, _ in associated_memories],
                memory_sources=["associative"] * len(associated_memories),
            )

            logger.info(
                f"Associative query found {len(result.memories)} associations for {seed_memory_id}"
            )

            return StandardResponse(success=True, data={"query_result": result})

        except Exception as e:
            logger.error(f"Associative query failed: {e}", exc_info=True)
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="ASSOCIATIVE_QUERY_FAILED", message=str(e)),
            )

    async def execute_temporal_analysis(
        self, timeframe_days: int = 30, analysis_type: str = "trends"
    ) -> StandardResponse:
        """
        Executes temporal analysis to identify patterns, trends,
        and significant events over time.
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=timeframe_days)

            temporal_query = MemoryQueryRequest(
                query_text="",
                temporal_range=(start_time, end_time),
                max_results=1000,
                relevance_threshold=0.1,
            )

            temporal_result = await self.layered_memory.query_memories(temporal_query)
            if not temporal_result.success:
                return temporal_result

            memories = temporal_result.data["query_result"].memories

            analysis_map = {
                "trends": self._analyze_memory_trends,
                "emotional_patterns": self._analyze_emotional_patterns,
                "activity_cycles": self._analyze_activity_cycles,
            }
            analysis_func = analysis_map.get(
                analysis_type, self._analyze_general_patterns
            )
            analysis_result = analysis_func(memories)

            logger.info(
                f"Temporal analysis '{analysis_type}' completed for the last {timeframe_days} days."
            )

            return StandardResponse(
                success=True,
                data={
                    "analysis_result": analysis_result,
                    "timeframe_days": timeframe_days,
                    "analysis_type": analysis_type,
                    "memories_analyzed": len(memories),
                },
            )

        except Exception as e:
            logger.error(f"Temporal analysis failed: {e}", exc_info=True)
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="TEMPORAL_ANALYSIS_FAILED", message=str(e)),
            )

    def _analyze_query_type(self, query_text: str) -> QueryType:
        """Analyzes the query text to determine its type."""
        query_lower = query_text.lower()
        if any(k in query_lower for k in ["when", "time", "date", "recent"]):
            return QueryType.TEMPORAL
        if any(k in query_lower for k in ["feel", "emotion", "mood"]):
            return QueryType.EMOTIONAL
        if any(k in query_lower for k in ["what is", "define", "explain"]):
            return QueryType.SEMANTIC
        return QueryType.SIMPLE_TEXT

    async def _process_query_by_type(
        self, query_text: str, context: QueryContext, query_type: QueryType
    ) -> StandardResponse:
        """Processes a query based on its determined type."""

        processing_map = {
            QueryType.TEMPORAL: self._process_temporal_query,
            QueryType.EMOTIONAL: self._process_emotional_query,
            QueryType.SEMANTIC: self._process_semantic_query,
            QueryType.CONTEXTUAL: self._process_contextual_query,
            QueryType.SIMPLE_TEXT: self._process_simple_query,
        }

        process_func = processing_map.get(query_type, self._process_simple_query)
        return await process_func(query_text, context)

    async def _process_simple_query(
        self, query_text: str, context: QueryContext
    ) -> StandardResponse:
        """Processes a simple text-based query."""
        query_request = MemoryQueryRequest(
            query_text=query_text,
            max_results=20,
            relevance_threshold=context.min_relevance,
            participants=context.active_participants,
        )
        return await self.layered_memory.query_memories(query_request)

    async def _process_temporal_query(
        self, query_text: str, context: QueryContext
    ) -> StandardResponse:
        """Processes a query focused on a temporal aspect."""
        temporal_range = self._extract_temporal_range(
            query_text
        ) or self._resolve_temporal_focus(context.temporal_focus)

        query_request = MemoryQueryRequest(
            query_text=query_text,
            temporal_range=temporal_range,
            max_results=25,
            relevance_threshold=context.min_relevance,
            participants=context.active_participants,
        )
        return await self.layered_memory.query_memories(query_request)

    async def _process_emotional_query(
        self, query_text: str, context: QueryContext
    ) -> StandardResponse:
        """Processes a query focused on an emotional aspect."""
        emotional_filters = self._extract_emotional_filters(query_text)

        query_request = MemoryQueryRequest(
            query_text=query_text,
            memory_types=[MemoryType.EMOTIONAL, MemoryType.EPISODIC],
            emotional_filters=emotional_filters,
            max_results=20,
            relevance_threshold=context.min_relevance,
        )
        return await self.layered_memory.query_memories(query_request)

    async def _process_semantic_query(
        self, query_text: str, context: QueryContext
    ) -> StandardResponse:
        """Processes a query focused on semantic knowledge."""
        query_request = MemoryQueryRequest(
            query_text=query_text,
            memory_types=[MemoryType.SEMANTIC],
            max_results=15,
            relevance_threshold=max(0.5, context.min_relevance),
            include_working_memory=False,
        )
        return await self.layered_memory.query_memories(query_request)

    async def _process_contextual_query(
        self, query_text: str, context: QueryContext
    ) -> StandardResponse:
        """Processes a query with heavy emphasis on the current context."""
        enhanced_query = (
            f"{query_text} {context.current_situation} {context.location_context}"
        )

        query_request = MemoryQueryRequest(
            query_text=enhanced_query,
            participants=context.active_participants,
            max_results=20,
            relevance_threshold=context.min_relevance,
        )
        return await self.layered_memory.query_memories(query_request)

    def _apply_contextual_ranking(
        self, result: MemoryQueryResult, context: QueryContext, query_text: str
    ) -> MemoryQueryResult:
        """Reranks query results based on contextual relevance."""
        if not result.memories:
            return result

        enhanced_scores = []
        for i, memory in enumerate(result.memories):
            score = result.relevance_scores[i]
            if context.active_participants and set(memory.participants) & set(
                context.active_participants
            ):
                score += 0.1
            if (
                context.location_context
                and context.location_context.lower() in memory.content.lower()
            ):
                score += 0.15
            enhanced_scores.append(min(1.0, score))

        sorted_results = sorted(
            zip(result.memories, enhanced_scores, result.memory_sources),
            key=lambda x: x[1],
            reverse=True,
        )

        result.memories, result.relevance_scores, result.memory_sources = zip(
            *sorted_results
        )
        return result

    async def _find_contextual_associations(
        self, memory: MemoryItem, max_results: int
    ) -> List[Tuple[MemoryItem, float]]:
        """Finds contextually associated memories."""
        associations = []
        if memory.participants:
            query = MemoryQueryRequest(
                query_text="", participants=memory.participants, max_results=max_results
            )
            result = await self.layered_memory.query_memories(query)
            if result.success:
                for mem in result.data["query_result"].memories:
                    if mem.memory_id != memory.memory_id:
                        associations.append((mem, 0.6))
        return associations[:max_results]

    def _extract_key_terms(self, content: str) -> List[str]:
        """Extracts key terms from content."""
        words = content.lower().split()
        stop_words = {"the", "a", "an", "in", "on", "at", "is", "and"}
        return [word for word in words if word not in stop_words and len(word) > 3][:5]

    def _extract_temporal_range(
        self, query_text: str
    ) -> Optional[Tuple[datetime, datetime]]:
        """Extracts a temporal range from a query string."""
        now = datetime.now()
        query_lower = query_text.lower()
        if "yesterday" in query_lower:
            start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0)
            return (start, start.replace(hour=23, minute=59, second=59))
        if "last week" in query_lower:
            return (now - timedelta(days=7), now)
        return None

    def _resolve_temporal_focus(
        self, temporal_focus: Optional[str]
    ) -> Optional[Tuple[datetime, datetime]]:
        """Resolves a temporal focus string to a datetime range."""
        now = datetime.now()
        if temporal_focus == "recent":
            return (now - timedelta(days=7), now)
        if temporal_focus == "distant":
            return (now - timedelta(days=365), now - timedelta(days=30))
        return None

    def _extract_emotional_filters(self, query_text: str) -> Dict[str, Any]:
        """Extracts emotional filters from a query string."""
        # This is a placeholder for a more sophisticated NLP-based implementation.
        from .emotional_memory import EmotionalValence

        filters = {}
        if "happy" in query_text.lower():
            filters["valence"] = EmotionalValence.POSITIVE
        if "sad" in query_text.lower():
            filters["valence"] = EmotionalValence.NEGATIVE
        return filters

    async def _get_memory_by_id(self, memory_id: str) -> List[MemoryItem]:
        """Retrieves a memory by its ID from any layer."""
        # This is a simplified retrieval. A real implementation would be more robust.
        query = MemoryQueryRequest(query_text=f"id:{memory_id}")
        result = await self.layered_memory.query_memories(query)
        if result.success:
            return [
                mem
                for mem in result.data["query_result"].memories
                if mem.memory_id == memory_id
            ]
        return []

    def _calculate_query_complexity(self, query_text: str) -> float:
        """Calculates a simple complexity score for a query."""
        return min(len(query_text.split()) / 20.0, 1.0)

    def _analyze_memory_trends(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Analyzes trends in a list of memories."""
        daily_counts = defaultdict(int)
        for mem in memories:
            daily_counts[mem.timestamp.date().isoformat()] += 1
        return {"daily_memory_counts": dict(daily_counts)}

    def _analyze_emotional_patterns(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Analyzes emotional patterns in a list of memories."""
        emotions = [
            mem.emotional_weight for mem in memories if mem.emotional_weight != 0
        ]
        if not emotions:
            return {}
        return {"average_emotion": sum(emotions) / len(emotions)}

    def _analyze_activity_cycles(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Analyzes activity cycles in a list of memories."""
        hourly_activity = defaultdict(int)
        for mem in memories:
            hourly_activity[mem.timestamp.hour] += 1
        return {"hourly_activity": dict(hourly_activity)}

    def _analyze_general_patterns(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Analyzes general patterns in a list of memories."""
        type_counts = defaultdict(int)
        for mem in memories:
            type_counts[mem.memory_type.value] += 1
        return {"memory_type_distribution": dict(type_counts)}

    def _generate_cache_key(self, query_text: str, context: QueryContext) -> str:
        """Generates a cache key for a query and its context."""
        context_str = f"{context.current_situation}|{context.active_participants}"
        return str(hash(f"{query_text}|{context_str}"))

    def _cleanup_expired_cache(self):
        """Removes expired entries from the query cache."""
        expiry_limit = datetime.now() - timedelta(minutes=self.cache_expiry_minutes)
        expired_keys = [
            k for k, (ts, _) in self._query_cache.items() if ts < expiry_limit
        ]
        for key in expired_keys:
            del self._query_cache[key]

    def _update_query_statistics(self, query_type: QueryType, metrics: QueryMetrics):
        """Updates query statistics."""
        self._query_statistics["total_queries"] += 1
        self._query_statistics[f"{query_type.value}_queries"] += 1
        self._query_statistics["total_duration_ms"] += metrics.query_duration_ms
        total_queries = self._query_statistics["total_queries"]
        total_duration = self._query_statistics["total_duration_ms"]
        self._query_statistics["average_query_time"] = (
            total_duration / total_queries if total_queries > 0 else 0
        )

    def get_query_statistics(self) -> Dict[str, Any]:
        """Returns statistics about query engine performance."""
        total = self._query_statistics.get("total_queries", 1)
        hits = self._query_statistics.get("cache_hits", 0)
        return {
            "query_statistics": dict(self._query_statistics),
            "cache_size": len(self._query_cache),
            "cache_hit_rate": hits / total if total > 0 else 0,
        }


async def test_memory_query_engine():
    """Tests the MemoryQueryEngine."""
    print("Testing Memory Query Engine...")

    db = ContextDatabase(":memory:")
    await db.initialize()
    layered_memory = LayeredMemorySystem("test_agent", db)
    query_engine = MemoryQueryEngine(layered_memory)

    test_memory = MemoryItem(
        agent_id="test_agent",
        content="A test event happened yesterday.",
        memory_type=MemoryType.EPISODIC,
        emotional_weight=2.0,
    )
    await layered_memory.store_memory(test_memory)

    query = "what happened yesterday"
    result = await query_engine.execute_query(query)

    if result.success:
        query_result = result.data["query_result"]
        print(f"Query '{query}' found {len(query_result.memories)} results.")
        assert len(query_result.memories) > 0
    else:
        print(f"Query failed: {result.error.message}")
        assert False

    stats = query_engine.get_query_statistics()
    print(f"Query Engine Stats: {stats}")

    await db.close()
    print("Memory Query Engine testing complete.")


if __name__ == "__main__":
    asyncio.run(test_memory_query_engine())
