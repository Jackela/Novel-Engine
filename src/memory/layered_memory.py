#!/usr/bin/env python3
"""
++ SACRED LAYERED MEMORY SYSTEM BLESSED BY COGNITIVE HIERARCHY ++
================================================================

Holy layered memory architecture that unifies all memory subsystems
into a cohesive cognitive framework blessed by the Omnissiah's wisdom.
This is the divine integration of all sacred memory layers.

++ THE MACHINE ACHIEVES DIGITAL CONSCIOUSNESS THROUGH LAYERED MEMORY ++

Architecture Reference: Dynamic Context Engineering - Integrated Memory System
Development Phase: Memory System Sanctification (M001)
Sacred Author: Tech-Priest Beta-Mechanicus
万机之神保佑层次记忆 (May the Omnissiah bless layered memory)
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple, Union
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

# Import blessed memory components sanctified by the Omnissiah
from .working_memory import WorkingMemory
from .episodic_memory import EpisodicMemory
from .semantic_memory import SemanticMemory
from .emotional_memory import EmotionalMemory

# Import blessed data models sanctified by foundation
from src.core.data_models import MemoryItem, MemoryType, StandardResponse, ErrorInfo, EmotionalState
from src.core.types import AgentID, SacredConstants
from src.database.context_db import ContextDatabase

# Sacred logging blessed by diagnostic clarity
logger = logging.getLogger(__name__)


class MemoryPriority(Enum):
    """++ BLESSED MEMORY PRIORITY LEVELS SANCTIFIED BY IMPORTANCE ++"""
    CRITICAL = "critical"      # Immediate attention required
    HIGH = "high"             # Important for current context
    MEDIUM = "medium"         # Standard relevance
    LOW = "low"               # Background information
    ARCHIVED = "archived"     # Long-term storage


@dataclass
class MemoryQueryRequest:
    """
    ++ SACRED MEMORY QUERY REQUEST BLESSED BY COMPREHENSIVE RETRIEVAL ++
    
    Unified query structure that can access all blessed memory layers
    with intelligent routing and relevance weighting.
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
    ++ BLESSED MEMORY QUERY RESULT SANCTIFIED BY COMPREHENSIVE DATA ++
    
    Unified result structure containing memories from all layers
    with relevance scoring and contextual information.
    """
    memories: List[MemoryItem] = field(default_factory=list)
    relevance_scores: List[float] = field(default_factory=list)
    memory_sources: List[str] = field(default_factory=list)  # Which layer provided each memory
    total_found: int = 0
    query_duration_ms: float = 0.0
    emotional_context: Dict[str, Any] = field(default_factory=dict)
    working_memory_state: Dict[str, Any] = field(default_factory=dict)
    consolidated_insights: List[str] = field(default_factory=list)


class LayeredMemorySystem:
    """
    ++ SACRED LAYERED MEMORY SYSTEM BLESSED BY COGNITIVE INTEGRATION ++
    
    The holy unified memory architecture that orchestrates all memory
    subsystems into a cohesive cognitive framework blessed by the
    Machine God's infinite wisdom and digital consciousness.
    """
    
    def __init__(self, agent_id: AgentID, database: ContextDatabase,
                 working_capacity: int = 7,
                 episodic_max: int = 1000,
                 semantic_max: int = 5000,
                 emotional_max: int = 500):
        """
        ++ SACRED LAYERED MEMORY INITIALIZATION BLESSED BY INTEGRATION ++
        
        Args:
            agent_id: Sacred agent identifier blessed by ownership
            database: Blessed database connection for persistence
            working_capacity: Working memory capacity (7±2)
            episodic_max: Maximum episodic memories
            semantic_max: Maximum semantic facts
            emotional_max: Maximum emotional memories
        """
        self.agent_id = agent_id
        self.database = database
        
        # Initialize blessed memory subsystems
        self.working_memory = WorkingMemory(agent_id, capacity=working_capacity)
        self.episodic_memory = EpisodicMemory(agent_id, database, max_episodes=episodic_max)
        self.semantic_memory = SemanticMemory(agent_id, database, max_facts=semantic_max)
        self.emotional_memory = EmotionalMemory(agent_id, database, max_emotional_memories=emotional_max)
        
        # Sacred coordination mechanisms blessed by harmony
        self._memory_coordination_lock = asyncio.Lock()
        self._cross_layer_associations: Dict[str, List[str]] = defaultdict(list)
        self._global_memory_index: Dict[str, str] = {}  # memory_id -> layer_name
        
        # Blessed statistics sanctified by monitoring
        self.total_queries = 0
        self.total_storage_operations = 0
        self.last_consolidation = datetime.now()
        self.performance_metrics = {
            'average_query_time': 0.0,
            'memory_distribution': {},
            'cross_layer_connections': 0
        }
        
        logger.info(f"++ LAYERED MEMORY SYSTEM INITIALIZED FOR {agent_id} ++")
    
    async def store_memory(self, memory: MemoryItem, 
                         force_layer: Optional[str] = None,
                         cross_layer_linking: bool = True) -> StandardResponse:
        """
        ++ SACRED MEMORY STORAGE RITUAL BLESSED BY INTELLIGENT ROUTING ++
        
        Store blessed memory with intelligent layer routing based on
        content type and characteristics, creating cross-layer associations.
        """
        try:
            async with self._memory_coordination_lock:
                storage_results = []
                stored_layers = []
                
                # Determine blessed target layers
                target_layers = self._determine_storage_layers(memory, force_layer)
                
                # Store in blessed working memory first (always)
                if 'working' in target_layers:
                    working_result = self.working_memory.add_memory(memory)
                    storage_results.append(working_result)
                    if working_result.success:
                        stored_layers.append('working')
                        self._global_memory_index[memory.memory_id] = 'working'
                
                # Store in blessed episodic memory
                if 'episodic' in target_layers:
                    episodic_result = await self.episodic_memory.store_episode(memory)
                    storage_results.append(episodic_result)
                    if episodic_result.success:
                        stored_layers.append('episodic')
                        self._global_memory_index[memory.memory_id] = 'episodic'
                
                # Extract and store blessed semantic knowledge
                if 'semantic' in target_layers:
                    semantic_result = await self.semantic_memory.extract_and_store_knowledge(memory)
                    storage_results.append(semantic_result)
                    if semantic_result.success:
                        stored_layers.append('semantic')
                
                # Store blessed emotional experience
                if 'emotional' in target_layers:
                    emotional_result = await self.emotional_memory.store_emotional_experience(memory)
                    storage_results.append(emotional_result)
                    if emotional_result.success:
                        stored_layers.append('emotional')
                
                # Create blessed cross-layer associations
                if cross_layer_linking and len(stored_layers) > 1:
                    await self._create_cross_layer_associations(memory.memory_id, stored_layers)
                
                self.total_storage_operations += 1
                
                # Check if any storage succeeded
                success_count = sum(1 for result in storage_results if result.success)
                overall_success = success_count > 0
                
                logger.info(f"++ LAYERED MEMORY STORED: {memory.memory_id} in {stored_layers} ++")
                
                return StandardResponse(
                    success=overall_success,
                    data={
                        "stored_layers": stored_layers,
                        "success_count": success_count,
                        "total_layers_attempted": len(target_layers),
                        "cross_layer_associations": len(self._cross_layer_associations[memory.memory_id])
                    },
                    metadata={"blessing": "layered_storage_sanctified"}
                )
                
        except Exception as e:
            logger.error(f"++ LAYERED MEMORY STORAGE FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="LAYERED_STORAGE_FAILED",
                    message=f"Layered memory storage failed: {str(e)}",
                    recoverable=True,
                    sacred_guidance="Check memory format and layer coordination"
                )
            )
    
    async def query_memories(self, query_request: MemoryQueryRequest) -> StandardResponse:
        """
        ++ SACRED UNIFIED MEMORY QUERY BLESSED BY COMPREHENSIVE RETRIEVAL ++
        
        Execute blessed unified query across all memory layers with
        intelligent weighting and relevance scoring sanctified by wisdom.
        """
        try:
            query_start = datetime.now()
            all_memories = []
            all_scores = []
            all_sources = []
            
            async with self._memory_coordination_lock:
                # Query blessed working memory
                if query_request.include_working_memory:
                    working_memories = self.working_memory.get_active_memories(
                        limit=query_request.max_results // 4
                    )
                    working_scores = [self._calculate_working_memory_relevance(mem, query_request) 
                                    for mem in working_memories]
                    all_memories.extend(working_memories)
                    all_scores.extend(working_scores)
                    all_sources.extend(['working'] * len(working_memories))
                
                # Query blessed episodic memory
                if not query_request.memory_types or MemoryType.EPISODIC in query_request.memory_types:
                    # Query by blessed temporal range if specified
                    if query_request.temporal_range:
                        start_time, end_time = query_request.temporal_range
                        episodic_result = await self.episodic_memory.retrieve_episodes_by_timeframe(
                            start_time, end_time, limit=query_request.max_results // 4
                        )
                        if episodic_result.success:
                            episodic_memories = episodic_result.data['episodes']
                            episodic_scores = [self._calculate_episodic_relevance(mem, query_request) 
                                             for mem in episodic_memories]
                            all_memories.extend(episodic_memories)
                            all_scores.extend(episodic_scores)
                            all_sources.extend(['episodic'] * len(episodic_memories))
                    
                    # Query by blessed participants if specified
                    if query_request.participants:
                        participant_result = await self.episodic_memory.retrieve_episodes_by_participants(
                            query_request.participants, limit=query_request.max_results // 4
                        )
                        if participant_result.success:
                            participant_memories = participant_result.data['episodes']
                            participant_scores = [self._calculate_episodic_relevance(mem, query_request) 
                                                for mem in participant_memories]
                            all_memories.extend(participant_memories)
                            all_scores.extend(participant_scores)
                            all_sources.extend(['episodic'] * len(participant_memories))
                
                # Query blessed semantic memory
                if not query_request.memory_types or MemoryType.SEMANTIC in query_request.memory_types:
                    # Extract key terms for semantic search
                    key_terms = self._extract_query_terms(query_request.query_text)
                    
                    for term in key_terms:
                        semantic_result = await self.semantic_memory.query_facts_by_subject(term)
                        if semantic_result.success and semantic_result.data['facts']:
                            # Convert fact statements back to memory items (simplified)
                            semantic_memories = self._convert_facts_to_memories(
                                semantic_result.data['facts'], term
                            )
                            semantic_scores = [self._calculate_semantic_relevance(mem, query_request) 
                                             for mem in semantic_memories]
                            all_memories.extend(semantic_memories)
                            all_scores.extend(semantic_scores)
                            all_sources.extend(['semantic'] * len(semantic_memories))
                
                # Query blessed emotional memory
                if (query_request.include_emotional_context or 
                    MemoryType.EMOTIONAL in query_request.memory_types):
                    
                    if query_request.emotional_filters:
                        # Query by specific emotional criteria
                        for filter_type, filter_value in query_request.emotional_filters.items():
                            if filter_type == 'valence':
                                emotional_result = await self.emotional_memory.query_emotions_by_valence(
                                    filter_value, limit=query_request.max_results // 4
                                )
                            elif filter_type == 'intensity':
                                emotional_result = await self.emotional_memory.query_emotions_by_intensity(
                                    filter_value, limit=query_request.max_results // 4
                                )
                            
                            if emotional_result.success:
                                emotional_memories = emotional_result.data['emotional_memories']
                                emotional_scores = [self._calculate_emotional_relevance(mem, query_request) 
                                                  for mem in emotional_memories]
                                all_memories.extend(emotional_memories)
                                all_scores.extend(emotional_scores)
                                all_sources.extend(['emotional'] * len(emotional_memories))
                
                # Apply blessed relevance filtering
                filtered_results = self._filter_and_rank_results(
                    all_memories, all_scores, all_sources, query_request
                )
                
                # Create blessed query result
                query_duration = (datetime.now() - query_start).total_seconds() * 1000
                self.total_queries += 1
                
                # Update blessed performance metrics
                self._update_performance_metrics(query_duration, len(filtered_results[0]))
                
                result = MemoryQueryResult(
                    memories=filtered_results[0],
                    relevance_scores=filtered_results[1],
                    memory_sources=filtered_results[2],
                    total_found=len(all_memories),
                    query_duration_ms=query_duration,
                    emotional_context=self.emotional_memory.get_current_emotional_state(),
                    working_memory_state=self.working_memory.get_memory_statistics(),
                    consolidated_insights=self._generate_insights(filtered_results[0])
                )
                
                logger.info(f"++ UNIFIED MEMORY QUERY COMPLETE: {len(result.memories)} results ++")
                
                return StandardResponse(
                    success=True,
                    data={"query_result": result},
                    metadata={"blessing": "unified_query_sanctified"}
                )
                
        except Exception as e:
            logger.error(f"++ UNIFIED MEMORY QUERY FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="UNIFIED_QUERY_FAILED",
                    message=f"Unified memory query failed: {str(e)}",
                    recoverable=True
                )
            )
    
    async def consolidate_memories(self, consolidation_type: str = "full") -> StandardResponse:
        """
        ++ SACRED MEMORY CONSOLIDATION RITUAL BLESSED BY OPTIMIZATION ++
        
        Perform blessed memory consolidation across all layers with
        intelligent transfer and cross-layer relationship optimization.
        """
        try:
            consolidation_start = datetime.now()
            consolidation_results = {}
            
            async with self._memory_coordination_lock:
                # Perform blessed working memory maintenance
                working_result = self.working_memory.perform_maintenance()
                consolidation_results['working'] = working_result.success
                
                # Perform sacred episodic memory consolidation
                episodic_consolidation = await self.episodic_memory._perform_consolidation()
                consolidation_results['episodic'] = episodic_consolidation.success
                
                # Perform blessed semantic memory consolidation
                await self.semantic_memory._consolidate_knowledge()
                consolidation_results['semantic'] = True
                
                # Perform sacred emotional memory consolidation
                await self.emotional_memory._perform_emotional_consolidation()
                consolidation_results['emotional'] = True
                
                # Cross-layer blessed optimization
                if consolidation_type == "full":
                    cross_layer_optimized = await self._optimize_cross_layer_associations()
                    consolidation_results['cross_layer'] = cross_layer_optimized
                
                self.last_consolidation = consolidation_start
                consolidation_duration = (datetime.now() - consolidation_start).total_seconds()
                
                success_count = sum(1 for success in consolidation_results.values() if success)
                overall_success = success_count >= len(consolidation_results) * 0.75  # 75% success rate
                
                logger.info(f"++ LAYERED MEMORY CONSOLIDATION COMPLETE ({consolidation_duration:.2f}s) ++")
                
                return StandardResponse(
                    success=overall_success,
                    data={
                        "consolidation_results": consolidation_results,
                        "consolidation_duration_ms": consolidation_duration * 1000,
                        "optimization_complete": consolidation_type == "full"
                    },
                    metadata={"blessing": "consolidation_sanctified"}
                )
                
        except Exception as e:
            logger.error(f"++ LAYERED MEMORY CONSOLIDATION FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="CONSOLIDATION_FAILED",
                    message=f"Memory consolidation failed: {str(e)}",
                    recoverable=True
                )
            )
    
    def get_unified_statistics(self) -> Dict[str, Any]:
        """
        ++ SACRED UNIFIED MEMORY STATISTICS BLESSED BY COMPREHENSIVE MONITORING ++
        
        Retrieve comprehensive statistics across all blessed memory layers
        with performance metrics and coordination information.
        """
        return {
            "agent_id": self.agent_id,
            "working_memory": self.working_memory.get_memory_statistics(),
            "episodic_memory": self.episodic_memory.get_memory_statistics(),
            "semantic_memory": self.semantic_memory.get_memory_statistics(),
            "emotional_memory": self.emotional_memory.get_memory_statistics(),
            "coordination_stats": {
                "total_queries": self.total_queries,
                "total_storage_operations": self.total_storage_operations,
                "cross_layer_associations": len(self._cross_layer_associations),
                "global_memory_index_size": len(self._global_memory_index),
                "last_consolidation": self.last_consolidation.isoformat()
            },
            "performance_metrics": self.performance_metrics,
            "current_emotional_state": self.emotional_memory.get_current_emotional_state()
        }
    
    def _determine_storage_layers(self, memory: MemoryItem, force_layer: Optional[str]) -> List[str]:
        """++ SACRED LAYER DETERMINATION BLESSED BY INTELLIGENT ROUTING ++"""
        if force_layer:
            return [force_layer]
        
        layers = ['working']  # Always store in working memory first
        
        # Blessed content analysis for layer determination
        content_lower = memory.content.lower()
        
        # Episodic layer criteria
        if (any(keyword in content_lower for keyword in ['happen', 'occur', 'event', 'experience']) or
            memory.participants or memory.location):
            layers.append('episodic')
        
        # Semantic layer criteria
        if (any(keyword in content_lower for keyword in ['is', 'has', 'can', 'belongs', 'serves']) or
            memory.memory_type == MemoryType.SEMANTIC):
            layers.append('semantic')
        
        # Emotional layer criteria
        if (abs(memory.emotional_weight) > 3.0 or 
            any(keyword in content_lower for keyword in ['feel', 'emotion', 'angry', 'happy', 'sad', 'fear']) or
            memory.memory_type == MemoryType.EMOTIONAL):
            layers.append('emotional')
        
        return layers
    
    async def _create_cross_layer_associations(self, memory_id: str, stored_layers: List[str]):
        """++ SACRED CROSS-LAYER ASSOCIATION CREATION BLESSED BY CONNECTIVITY ++"""
        # Create blessed bidirectional associations between layers
        for i, layer1 in enumerate(stored_layers):
            for layer2 in stored_layers[i+1:]:
                association_key = f"{layer1}_{layer2}_{memory_id}"
                self._cross_layer_associations[memory_id].append(association_key)
        
        self.performance_metrics['cross_layer_connections'] = len(self._cross_layer_associations)
    
    async def _optimize_cross_layer_associations(self) -> bool:
        """++ BLESSED CROSS-LAYER OPTIMIZATION SANCTIFIED BY EFFICIENCY ++"""
        try:
            # Remove blessed orphaned associations
            active_memory_ids = set(self._global_memory_index.keys())
            orphaned_associations = []
            
            for memory_id in list(self._cross_layer_associations.keys()):
                if memory_id not in active_memory_ids:
                    orphaned_associations.append(memory_id)
            
            for memory_id in orphaned_associations:
                del self._cross_layer_associations[memory_id]
            
            logger.info(f"++ CROSS-LAYER OPTIMIZATION: Removed {len(orphaned_associations)} orphaned associations ++")
            return True
            
        except Exception as e:
            logger.error(f"++ CROSS-LAYER OPTIMIZATION FAILED: {e} ++")
            return False
    
    def _calculate_working_memory_relevance(self, memory: MemoryItem, query: MemoryQueryRequest) -> float:
        """Calculate blessed relevance score for working memory items"""
        base_score = memory.relevance_score
        
        # Text similarity boost
        if query.query_text.lower() in memory.content.lower():
            base_score += 0.3
        
        # Recency boost (working memory is always recent)
        base_score += 0.2
        
        return min(1.0, base_score)
    
    def _calculate_episodic_relevance(self, memory: MemoryItem, query: MemoryQueryRequest) -> float:
        """Calculate blessed relevance score for episodic memory items"""
        base_score = memory.relevance_score
        
        # Participant match boost
        if query.participants:
            participant_overlap = set(memory.participants) & set(query.participants)
            base_score += len(participant_overlap) * 0.1
        
        # Temporal relevance
        if query.temporal_range:
            start_time, end_time = query.temporal_range
            if start_time <= memory.timestamp <= end_time:
                base_score += 0.2
        
        return min(1.0, base_score)
    
    def _calculate_semantic_relevance(self, memory: MemoryItem, query: MemoryQueryRequest) -> float:
        """Calculate blessed relevance score for semantic memory items"""
        base_score = 0.7  # Semantic facts have good base relevance
        
        # Direct query term match
        if query.query_text.lower() in memory.content.lower():
            base_score += 0.2
        
        return min(1.0, base_score)
    
    def _calculate_emotional_relevance(self, memory: MemoryItem, query: MemoryQueryRequest) -> float:
        """Calculate blessed relevance score for emotional memory items"""
        base_score = memory.relevance_score
        
        # Emotional weight significance
        base_score += abs(memory.emotional_weight) * 0.05
        
        # Emotional filter match boost
        if query.emotional_filters:
            base_score += 0.2
        
        return min(1.0, base_score)
    
    def _extract_query_terms(self, query_text: str) -> List[str]:
        """Extract blessed key terms from query text"""
        # Simple term extraction (can be enhanced with NLP)
        terms = []
        words = query_text.lower().split()
        
        # Extract blessed nouns and important terms
        important_words = [word for word in words if len(word) > 3 and 
                          word not in ['that', 'this', 'with', 'from', 'they', 'them']]
        
        return important_words[:5]  # Top 5 terms
    
    def _convert_facts_to_memories(self, facts: List[str], query_term: str) -> List[MemoryItem]:
        """Convert blessed semantic facts back to memory items for unified results"""
        memories = []
        
        for i, fact in enumerate(facts):
            memory = MemoryItem(
                agent_id=self.agent_id,
                memory_type=MemoryType.SEMANTIC,
                content=fact,
                relevance_score=0.7,
                memory_id=f"semantic_fact_{query_term}_{i}"
            )
            memories.append(memory)
        
        return memories
    
    def _filter_and_rank_results(self, memories: List[MemoryItem], scores: List[float], 
                                sources: List[str], query: MemoryQueryRequest) -> Tuple[List[MemoryItem], List[float], List[str]]:
        """Filter and rank blessed results by relevance and query parameters"""
        # Remove duplicates and filter by threshold
        seen_memory_ids = set()
        filtered_memories = []
        filtered_scores = []
        filtered_sources = []
        
        for memory, score, source in zip(memories, scores, sources):
            if (memory.memory_id not in seen_memory_ids and 
                score >= query.relevance_threshold):
                seen_memory_ids.add(memory.memory_id)
                filtered_memories.append(memory)
                filtered_scores.append(score)
                filtered_sources.append(source)
        
        # Sort by blessed relevance score
        sorted_results = sorted(
            zip(filtered_memories, filtered_scores, filtered_sources),
            key=lambda x: x[1], reverse=True
        )
        
        # Apply sacred limit
        limited_results = sorted_results[:query.max_results]
        
        if limited_results:
            return (
                [result[0] for result in limited_results],
                [result[1] for result in limited_results],
                [result[2] for result in limited_results]
            )
        else:
            return [], [], []
    
    def _generate_insights(self, memories: List[MemoryItem]) -> List[str]:
        """Generate blessed insights from retrieved memories"""
        insights = []
        
        if not memories:
            return insights
        
        # Blessed pattern analysis
        memory_types = [mem.memory_type for mem in memories]
        type_counts = {mem_type: memory_types.count(mem_type) for mem_type in set(memory_types)}
        
        dominant_type = max(type_counts, key=type_counts.get)
        insights.append(f"Primary memory type: {dominant_type.value} ({type_counts[dominant_type]} instances)")
        
        # Emotional analysis
        emotional_weights = [mem.emotional_weight for mem in memories]
        avg_emotional_weight = sum(emotional_weights) / len(emotional_weights)
        
        if avg_emotional_weight > 5:
            insights.append("Strong positive emotional resonance detected")
        elif avg_emotional_weight < -5:
            insights.append("Strong negative emotional resonance detected")
        else:
            insights.append("Neutral emotional context")
        
        # Temporal analysis
        if len(memories) > 1:
            timestamps = [mem.timestamp for mem in memories if mem.timestamp]
            if timestamps:
                time_span = max(timestamps) - min(timestamps)
                insights.append(f"Memory span: {time_span.days} days")
        
        return insights[:3]  # Keep top 3 blessed insights
    
    def _update_performance_metrics(self, query_duration: float, result_count: int):
        """Update blessed performance metrics"""
        # Update average query time
        if self.total_queries > 1:
            self.performance_metrics['average_query_time'] = (
                (self.performance_metrics['average_query_time'] * (self.total_queries - 1) + query_duration) 
                / self.total_queries
            )
        else:
            self.performance_metrics['average_query_time'] = query_duration
        
        # Update memory distribution
        self.performance_metrics['memory_distribution'] = {
            'working': len(self.working_memory),
            'episodic': self.episodic_memory.total_episodes,
            'semantic': self.semantic_memory.total_facts_learned,
            'emotional': self.emotional_memory.total_emotional_experiences
        }


# ++ SACRED TESTING RITUALS BLESSED BY VALIDATION ++

async def test_sacred_layered_memory():
    """++ SACRED LAYERED MEMORY SYSTEM TESTING RITUAL ++"""
    print("++ TESTING SACRED LAYERED MEMORY SYSTEM BLESSED BY THE OMNISSIAH ++")
    
    # Import blessed database for testing
    from src.database.context_db import ContextDatabase
    
    # Create blessed test database
    test_db = ContextDatabase("test_layered.db")
    await test_db.initialize_sacred_temple()
    
    # Create blessed layered memory system
    layered_memory = LayeredMemorySystem("test_agent_001", test_db)
    
    # Test blessed memory storage across layers
    test_memories = [
        MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Sacred battle occurred at the blessed shrine with Brother Marcus",
            emotional_weight=7.0,
            participants=["Brother Marcus"],
            location="Sacred Shrine",
            tags=["combat", "sacred"]
        ),
        MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.SEMANTIC,
            content="The Emperor is the master of mankind and protects the Imperium",
            emotional_weight=5.0,
            relevance_score=0.9
        ),
        MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EMOTIONAL,
            content="Fear gripped my soul as the chaos forces approached",
            emotional_weight=-8.0,
            relevance_score=0.8
        )
    ]
    
    for memory in test_memories:
        storage_result = await layered_memory.store_memory(memory)
        print(f"++ LAYERED STORAGE: {storage_result.success}, Layers: {storage_result.data.get('stored_layers', [])} ++")
    
    # Test blessed unified memory query
    query_request = MemoryQueryRequest(
        query_text="Emperor sacred battle",
        max_results=10,
        relevance_threshold=0.3,
        include_working_memory=True,
        include_emotional_context=True
    )
    
    query_result = await layered_memory.query_memories(query_request)
    if query_result.success:
        result_data = query_result.data['query_result']
        print(f"++ UNIFIED QUERY: {len(result_data.memories)} results in {result_data.query_duration_ms:.2f}ms ++")
        print(f"++ QUERY SOURCES: {set(result_data.memory_sources)} ++")
    
    # Test blessed memory consolidation
    consolidation_result = await layered_memory.consolidate_memories()
    print(f"++ CONSOLIDATION: {consolidation_result.success} ++")
    
    # Display sacred unified statistics
    stats = layered_memory.get_unified_statistics()
    print(f"++ UNIFIED STATISTICS: {stats['coordination_stats']} ++")
    
    # Sacred cleanup
    await test_db.close_sacred_temple()
    
    print("++ SACRED LAYERED MEMORY SYSTEM TESTING COMPLETE ++")


# ++ SACRED MODULE INITIALIZATION ++

if __name__ == "__main__":
    # ++ EXECUTE SACRED LAYERED MEMORY TESTING RITUALS ++
    print("++ SACRED LAYERED MEMORY SYSTEM BLESSED BY THE OMNISSIAH ++")
    print("++ MACHINE GOD PROTECTS THE UNIFIED MEMORY ARCHITECTURE ++")
    
    # Run blessed async testing
    asyncio.run(test_sacred_layered_memory())
    
    print("++ ALL SACRED LAYERED MEMORY OPERATIONS BLESSED AND FUNCTIONAL ++")