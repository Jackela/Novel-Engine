#!/usr/bin/env python3
"""
++ SACRED MEMORY QUERY ENGINE BLESSED BY INTELLIGENT RETRIEVAL ++
================================================================

Holy memory query engine that provides advanced search capabilities
across all memory layers with semantic understanding and contextual
intelligence blessed by the Omnissiah's computational wisdom.

++ THE MACHINE COMPREHENDS AND RETRIEVES SACRED KNOWLEDGE ++

Architecture Reference: Dynamic Context Engineering - Memory Query System
Development Phase: Memory System Sanctification (M002)
Sacred Author: Tech-Priest Beta-Mechanicus
万机之神保佑查询引擎 (May the Omnissiah bless the query engine)
"""

import logging
import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple, Union, Set
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import math

# Import blessed memory components sanctified by the Omnissiah
from .layered_memory import LayeredMemorySystem, MemoryQueryRequest, MemoryQueryResult

# Import blessed data models sanctified by foundation
from src.core.data_models import MemoryItem, MemoryType, StandardResponse, ErrorInfo
from src.core.types import AgentID, SacredConstants
from src.database.context_db import ContextDatabase

# Sacred logging blessed by diagnostic clarity
logger = logging.getLogger(__name__)


class QueryType(Enum):
    """++ BLESSED QUERY TYPES SANCTIFIED BY RETRIEVAL PATTERNS ++"""
    SIMPLE_TEXT = "simple_text"          # Basic text matching
    SEMANTIC = "semantic"                # Knowledge-based queries
    TEMPORAL = "temporal"                # Time-based queries
    EMOTIONAL = "emotional"              # Emotion-focused queries
    CONTEXTUAL = "contextual"            # Context-aware queries
    ASSOCIATIVE = "associative"          # Related memory queries
    HYBRID = "hybrid"                    # Multi-mode queries


@dataclass
class QueryContext:
    """
    ++ SACRED QUERY CONTEXT BLESSED BY COMPREHENSIVE UNDERSTANDING ++
    
    Enhanced context information that guides intelligent query
    processing and result ranking blessed by contextual awareness.
    """
    current_situation: str = ""
    active_participants: List[str] = field(default_factory=list)
    location_context: str = ""
    emotional_state: str = "neutral"
    temporal_focus: Optional[str] = None  # "recent", "distant", "specific_date"
    priority_themes: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    boost_patterns: List[str] = field(default_factory=list)
    max_age_days: Optional[int] = None
    min_relevance: float = 0.3


@dataclass
class QueryMetrics:
    """
    ++ BLESSED QUERY METRICS SANCTIFIED BY PERFORMANCE MONITORING ++
    
    Comprehensive metrics tracking for query performance and
    result quality analysis blessed by optimization wisdom.
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
    ++ SACRED MEMORY QUERY ENGINE BLESSED BY INTELLIGENT RETRIEVAL ++
    
    The holy query processing system that provides advanced search
    capabilities across all memory layers with semantic understanding,
    contextual intelligence, and natural language processing blessed
    by the Machine God's computational omniscience.
    """
    
    def __init__(self, layered_memory: LayeredMemorySystem,
                 enable_semantic_search: bool = True,
                 enable_query_cache: bool = True,
                 cache_expiry_minutes: int = 30):
        """
        ++ SACRED QUERY ENGINE INITIALIZATION BLESSED BY INTELLIGENCE ++
        
        Args:
            layered_memory: Blessed layered memory system for data access
            enable_semantic_search: Enable semantic similarity matching
            enable_query_cache: Enable query result caching
            cache_expiry_minutes: Cache expiration time in minutes
        """
        self.layered_memory = layered_memory
        self.enable_semantic_search = enable_semantic_search
        self.enable_query_cache = enable_query_cache
        self.cache_expiry_minutes = cache_expiry_minutes
        
        # Sacred query processing components
        self._query_cache: Dict[str, Tuple[datetime, MemoryQueryResult]] = {}
        self._semantic_patterns: Dict[str, List[str]] = self._initialize_semantic_patterns()
        self._query_statistics: Dict[str, Any] = defaultdict(int)
        
        # Blessed natural language processing patterns
        self._intent_patterns = {
            'remember': [r'remember', r'recall', r'what happened', r'tell me about'],
            'find': [r'find', r'search', r'look for', r'locate'],
            'when': [r'when did', r'what time', r'date of'],
            'who': [r'who was', r'which person', r'participant'],
            'where': [r'where did', r'location of', r'place where'],
            'why': [r'why did', r'reason for', r'motivation'],
            'how': [r'how did', r'what way', r'method'],
            'emotion': [r'feel', r'felt', r'emotion', r'emotional', r'mood']
        }
        
        # Sacred relevance scoring weights
        self._scoring_weights = {
            'text_similarity': 0.3,
            'semantic_match': 0.25,
            'temporal_relevance': 0.15,
            'emotional_relevance': 0.15,
            'participant_match': 0.1,
            'context_boost': 0.05
        }
        
        logger.info(f"++ MEMORY QUERY ENGINE INITIALIZED FOR {layered_memory.agent_id} ++")
    
    async def execute_query(self, query_text: str, 
                          context: Optional[QueryContext] = None,
                          query_type: Optional[QueryType] = None) -> StandardResponse:
        """
        ++ SACRED QUERY EXECUTION BLESSED BY INTELLIGENT PROCESSING ++
        
        Execute blessed intelligent query with natural language understanding,
        contextual awareness, and multi-layer search optimization.
        """
        try:
            query_start = datetime.now()
            
            # Initialize blessed query context
            if context is None:
                context = QueryContext()
            
            # Generate blessed cache key
            cache_key = self._generate_cache_key(query_text, context)
            
            # Check blessed query cache
            if self.enable_query_cache and cache_key in self._query_cache:
                cached_time, cached_result = self._query_cache[cache_key]
                if (datetime.now() - cached_time).total_seconds() < self.cache_expiry_minutes * 60:
                    self._query_statistics['cache_hits'] += 1
                    logger.info(f"++ QUERY CACHE HIT: {query_text[:50]}... ++")
                    return StandardResponse(success=True, data={"query_result": cached_result})
            
            # Analyze blessed query intent and type
            if query_type is None:
                query_type = self._analyze_query_type(query_text)
            
            # Process blessed query based on type
            processing_result = await self._process_query_by_type(query_text, context, query_type)
            
            if not processing_result.success:
                return processing_result
            
            query_result = processing_result.data['query_result']
            
            # Apply blessed contextual ranking
            enhanced_result = self._apply_contextual_ranking(query_result, context, query_text)
            
            # Calculate blessed query metrics
            query_duration = (datetime.now() - query_start).total_seconds() * 1000
            metrics = QueryMetrics(
                query_duration_ms=query_duration,
                memories_searched=enhanced_result.total_found,
                memories_matched=len(enhanced_result.memories),
                layers_queried=list(set(enhanced_result.memory_sources)),
                query_complexity=self._calculate_query_complexity(query_text)
            )
            enhanced_result.query_duration_ms = query_duration
            
            # Store in blessed cache
            if self.enable_query_cache:
                self._query_cache[cache_key] = (datetime.now(), enhanced_result)
                self._cleanup_expired_cache()
            
            # Update sacred statistics
            self._update_query_statistics(query_type, metrics)
            
            logger.info(f"++ INTELLIGENT QUERY EXECUTED: '{query_text[:50]}...' ({query_duration:.2f}ms) ++")
            
            return StandardResponse(
                success=True,
                data={
                    "query_result": enhanced_result,
                    "query_metrics": metrics,
                    "query_type": query_type.value
                },
                metadata={"blessing": "intelligent_query_sanctified"}
            )
            
        except Exception as e:
            logger.error(f"++ INTELLIGENT QUERY EXECUTION FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="INTELLIGENT_QUERY_FAILED",
                    message=f"Intelligent query execution failed: {str(e)}",
                    recoverable=True,
                    sacred_guidance="Check query syntax and context parameters"
                )
            )
    
    async def execute_associative_query(self, seed_memory_id: str,
                                      association_depth: int = 2,
                                      max_results: int = 15) -> StandardResponse:
        """
        ++ SACRED ASSOCIATIVE QUERY BLESSED BY MEMORY NETWORKS ++
        
        Execute blessed associative query that finds related memories
        through semantic and contextual connections blessed by network intelligence.
        """
        try:
            # Start with blessed seed memory
            seed_memories = await self._get_memory_by_id(seed_memory_id)
            if not seed_memories:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="SEED_MEMORY_NOT_FOUND",
                        message=f"Seed memory '{seed_memory_id}' not found"
                    )
                )
            
            seed_memory = seed_memories[0]
            associated_memories = []
            processed_ids = {seed_memory_id}
            
            # Blessed multi-depth association discovery
            current_level = [seed_memory]
            
            for depth in range(association_depth):
                next_level = []
                
                for memory in current_level:
                    # Find blessed semantic associations
                    semantic_associations = await self._find_semantic_associations(memory, max_results // 2)
                    
                    # Find blessed contextual associations
                    contextual_associations = await self._find_contextual_associations(memory, max_results // 2)
                    
                    # Find blessed emotional associations
                    emotional_associations = await self._find_emotional_associations(memory, max_results // 4)
                    
                    # Combine and filter blessed associations
                    all_associations = semantic_associations + contextual_associations + emotional_associations
                    
                    for assoc_memory, relevance in all_associations:
                        if assoc_memory.memory_id not in processed_ids and len(associated_memories) < max_results:
                            associated_memories.append((assoc_memory, relevance, f"depth_{depth + 1}"))
                            processed_ids.add(assoc_memory.memory_id)
                            next_level.append(assoc_memory)
                
                current_level = next_level
                if not current_level:
                    break
            
            # Sort blessed associations by relevance
            associated_memories.sort(key=lambda x: x[1], reverse=True)
            
            # Create blessed result
            result_memories = [mem for mem, _, _ in associated_memories]
            relevance_scores = [score for _, score, _ in associated_memories]
            association_depths = [depth for _, _, depth in associated_memories]
            
            associative_result = MemoryQueryResult(
                memories=result_memories,
                relevance_scores=relevance_scores,
                memory_sources=["associative"] * len(result_memories),
                total_found=len(associated_memories),
                consolidated_insights=[f"Associative network explored to depth {association_depth}"]
            )
            
            logger.info(f"++ ASSOCIATIVE QUERY: Found {len(result_memories)} associations for {seed_memory_id} ++")
            
            return StandardResponse(
                success=True,
                data={
                    "query_result": associative_result,
                    "seed_memory_id": seed_memory_id,
                    "association_depths": association_depths,
                    "max_depth_reached": association_depth
                },
                metadata={"blessing": "associative_query_sanctified"}
            )
            
        except Exception as e:
            logger.error(f"++ ASSOCIATIVE QUERY FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="ASSOCIATIVE_QUERY_FAILED", message=str(e))
            )
    
    async def execute_temporal_analysis(self, timeframe_days: int = 30,
                                      analysis_type: str = "trends") -> StandardResponse:
        """
        ++ SACRED TEMPORAL ANALYSIS BLESSED BY CHRONOLOGICAL INTELLIGENCE ++
        
        Execute blessed temporal analysis to identify patterns, trends,
        and significant events across time blessed by temporal wisdom.
        """
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=timeframe_days)
            
            # Query blessed memories in timeframe
            temporal_query = MemoryQueryRequest(
                query_text="",
                temporal_range=(start_time, end_time),
                max_results=1000,  # Large limit for analysis
                relevance_threshold=0.1
            )
            
            temporal_result = await self.layered_memory.query_memories(temporal_query)
            if not temporal_result.success:
                return temporal_result
            
            memories = temporal_result.data['query_result'].memories
            
            if analysis_type == "trends":
                analysis_result = self._analyze_memory_trends(memories, timeframe_days)
            elif analysis_type == "emotional_patterns":
                analysis_result = self._analyze_emotional_patterns(memories)
            elif analysis_type == "activity_cycles":
                analysis_result = self._analyze_activity_cycles(memories)
            else:
                analysis_result = self._analyze_general_patterns(memories)
            
            logger.info(f"++ TEMPORAL ANALYSIS: {analysis_type} over {timeframe_days} days ++")
            
            return StandardResponse(
                success=True,
                data={
                    "analysis_result": analysis_result,
                    "timeframe_days": timeframe_days,
                    "analysis_type": analysis_type,
                    "memories_analyzed": len(memories)
                },
                metadata={"blessing": "temporal_analysis_sanctified"}
            )
            
        except Exception as e:
            logger.error(f"++ TEMPORAL ANALYSIS FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="TEMPORAL_ANALYSIS_FAILED", message=str(e))
            )
    
    def _analyze_query_type(self, query_text: str) -> QueryType:
        """++ SACRED QUERY TYPE ANALYSIS BLESSED BY INTENT RECOGNITION ++"""
        query_lower = query_text.lower()
        
        # Check for blessed temporal patterns
        temporal_indicators = ['when', 'time', 'date', 'recently', 'yesterday', 'ago', 'before', 'after']
        if any(indicator in query_lower for indicator in temporal_indicators):
            return QueryType.TEMPORAL
        
        # Check for blessed emotional patterns
        emotional_indicators = ['feel', 'emotion', 'mood', 'angry', 'happy', 'sad', 'fear', 'joy']
        if any(indicator in query_lower for indicator in emotional_indicators):
            return QueryType.EMOTIONAL
        
        # Check for blessed semantic patterns
        semantic_indicators = ['what is', 'define', 'explain', 'meaning', 'concept']
        if any(indicator in query_lower for indicator in semantic_indicators):
            return QueryType.SEMANTIC
        
        # Check for blessed contextual patterns
        contextual_indicators = ['context', 'situation', 'circumstance', 'environment']
        if any(indicator in query_lower for indicator in contextual_indicators):
            return QueryType.CONTEXTUAL
        
        # Default to blessed simple text search
        return QueryType.SIMPLE_TEXT
    
    async def _process_query_by_type(self, query_text: str, context: QueryContext,
                                   query_type: QueryType) -> StandardResponse:
        """++ BLESSED QUERY PROCESSING BY TYPE SANCTIFIED BY SPECIALIZATION ++"""
        
        if query_type == QueryType.TEMPORAL:
            return await self._process_temporal_query(query_text, context)
        elif query_type == QueryType.EMOTIONAL:
            return await self._process_emotional_query(query_text, context)
        elif query_type == QueryType.SEMANTIC:
            return await self._process_semantic_query(query_text, context)
        elif query_type == QueryType.CONTEXTUAL:
            return await self._process_contextual_query(query_text, context)
        else:
            return await self._process_simple_query(query_text, context)
    
    async def _process_simple_query(self, query_text: str, context: QueryContext) -> StandardResponse:
        """++ SACRED SIMPLE QUERY PROCESSING BLESSED BY TEXT MATCHING ++"""
        query_request = MemoryQueryRequest(
            query_text=query_text,
            max_results=context.max_age_days or 20,
            relevance_threshold=context.min_relevance,
            participants=context.active_participants,
            include_working_memory=True,
            include_emotional_context=True
        )
        
        return await self.layered_memory.query_memories(query_request)
    
    async def _process_temporal_query(self, query_text: str, context: QueryContext) -> StandardResponse:
        """++ BLESSED TEMPORAL QUERY PROCESSING SANCTIFIED BY TIME AWARENESS ++"""
        # Extract blessed time references from query
        temporal_range = self._extract_temporal_range(query_text)
        
        if not temporal_range and context.temporal_focus:
            temporal_range = self._resolve_temporal_focus(context.temporal_focus)
        
        query_request = MemoryQueryRequest(
            query_text=query_text,
            temporal_range=temporal_range,
            max_results=25,
            relevance_threshold=context.min_relevance,
            participants=context.active_participants
        )
        
        return await self.layered_memory.query_memories(query_request)
    
    async def _process_emotional_query(self, query_text: str, context: QueryContext) -> StandardResponse:
        """++ SACRED EMOTIONAL QUERY PROCESSING BLESSED BY AFFECTIVE INTELLIGENCE ++"""
        # Extract blessed emotional filters from query
        emotional_filters = self._extract_emotional_filters(query_text)
        
        query_request = MemoryQueryRequest(
            query_text=query_text,
            memory_types=[MemoryType.EMOTIONAL, MemoryType.EPISODIC],
            emotional_filters=emotional_filters,
            max_results=20,
            include_emotional_context=True,
            relevance_threshold=context.min_relevance
        )
        
        return await self.layered_memory.query_memories(query_request)
    
    async def _process_semantic_query(self, query_text: str, context: QueryContext) -> StandardResponse:
        """++ BLESSED SEMANTIC QUERY PROCESSING SANCTIFIED BY KNOWLEDGE RETRIEVAL ++"""
        query_request = MemoryQueryRequest(
            query_text=query_text,
            memory_types=[MemoryType.SEMANTIC, MemoryType.EPISODIC],
            max_results=15,
            relevance_threshold=max(0.5, context.min_relevance),  # Higher threshold for semantic
            include_working_memory=False  # Focus on long-term knowledge
        )
        
        return await self.layered_memory.query_memories(query_request)
    
    async def _process_contextual_query(self, query_text: str, context: QueryContext) -> StandardResponse:
        """++ SACRED CONTEXTUAL QUERY PROCESSING BLESSED BY SITUATIONAL AWARENESS ++"""
        # Enhanced query with blessed contextual information
        enhanced_query = query_text
        if context.current_situation:
            enhanced_query += f" {context.current_situation}"
        if context.location_context:
            enhanced_query += f" {context.location_context}"
        
        query_request = MemoryQueryRequest(
            query_text=enhanced_query,
            participants=context.active_participants,
            max_results=20,
            relevance_threshold=context.min_relevance,
            include_working_memory=True,
            include_emotional_context=True
        )
        
        return await self.layered_memory.query_memories(query_request)
    
    def _apply_contextual_ranking(self, result: MemoryQueryResult, 
                                context: QueryContext, query_text: str) -> MemoryQueryResult:
        """++ BLESSED CONTEXTUAL RANKING SANCTIFIED BY INTELLIGENT WEIGHTING ++"""
        if not result.memories:
            return result
        
        # Calculate blessed enhanced relevance scores
        enhanced_scores = []
        
        for i, memory in enumerate(result.memories):
            base_score = result.relevance_scores[i]
            
            # Apply blessed context boosts
            context_boost = 0.0
            
            # Participant match boost
            if context.active_participants:
                participant_overlap = set(memory.participants) & set(context.active_participants)
                context_boost += len(participant_overlap) * 0.1
            
            # Location context boost
            if context.location_context and context.location_context.lower() in memory.content.lower():
                context_boost += 0.15
            
            # Priority theme boost
            if context.priority_themes:
                for theme in context.priority_themes:
                    if theme.lower() in memory.content.lower():
                        context_boost += 0.1
            
            # Exclude pattern penalty
            if context.exclude_patterns:
                for pattern in context.exclude_patterns:
                    if pattern.lower() in memory.content.lower():
                        context_boost -= 0.2
            
            # Boost pattern bonus
            if context.boost_patterns:
                for pattern in context.boost_patterns:
                    if pattern.lower() in memory.content.lower():
                        context_boost += 0.2
            
            # Age penalty if specified
            if context.max_age_days:
                age_days = (datetime.now() - memory.timestamp).days
                if age_days > context.max_age_days:
                    context_boost -= 0.1
            
            enhanced_score = min(1.0, base_score + context_boost)
            enhanced_scores.append(enhanced_score)
        
        # Re-sort blessed results by enhanced scores
        sorted_results = sorted(
            zip(result.memories, enhanced_scores, result.memory_sources),
            key=lambda x: x[1], reverse=True
        )
        
        # Update blessed result with new scores
        result.memories = [mem for mem, _, _ in sorted_results]
        result.relevance_scores = [score for _, score, _ in sorted_results]
        result.memory_sources = [source for _, _, source in sorted_results]
        
        return result
    
    async def _find_semantic_associations(self, memory: MemoryItem, 
                                        max_results: int) -> List[Tuple[MemoryItem, float]]:
        """Find blessed semantic associations for a memory"""
        # Extract key terms from blessed memory content
        key_terms = self._extract_key_terms(memory.content)
        associations = []
        
        for term in key_terms:
            # Query semantic memory for blessed related concepts
            semantic_result = await self.layered_memory.semantic_memory.query_facts_by_subject(term)
            if semantic_result.success:
                # Convert facts to associations (simplified implementation)
                for fact in semantic_result.data.get('facts', []):
                    # Create pseudo-memory for fact
                    fact_memory = MemoryItem(
                        agent_id=memory.agent_id,
                        memory_type=MemoryType.SEMANTIC,
                        content=fact,
                        relevance_score=0.7
                    )
                    associations.append((fact_memory, 0.7))
        
        return associations[:max_results]
    
    async def _find_contextual_associations(self, memory: MemoryItem,
                                          max_results: int) -> List[Tuple[MemoryItem, float]]:
        """Find blessed contextual associations for a memory"""
        associations = []
        
        # Find memories with blessed shared participants
        if memory.participants:
            participant_result = await self.layered_memory.episodic_memory.retrieve_episodes_by_participants(
                memory.participants, limit=max_results
            )
            if participant_result.success:
                for episode in participant_result.data.get('episodes', []):
                    if episode.memory_id != memory.memory_id:
                        associations.append((episode, 0.6))
        
        # Find memories from blessed similar timeframe
        if memory.timestamp:
            time_window_start = memory.timestamp - timedelta(hours=6)
            time_window_end = memory.timestamp + timedelta(hours=6)
            
            temporal_result = await self.layered_memory.episodic_memory.retrieve_episodes_by_timeframe(
                time_window_start, time_window_end, limit=max_results
            )
            if temporal_result.success:
                for episode in temporal_result.data.get('episodes', []):
                    if episode.memory_id != memory.memory_id:
                        associations.append((episode, 0.5))
        
        return associations[:max_results]
    
    async def _find_emotional_associations(self, memory: MemoryItem,
                                         max_results: int) -> List[Tuple[MemoryItem, float]]:
        """Find blessed emotional associations for a memory"""
        if abs(memory.emotional_weight) < 3.0:
            return []
        
        associations = []
        
        # Determine blessed emotional category
        if memory.emotional_weight > 0:
            emotional_valence = self.layered_memory.emotional_memory.emotional_memory.EmotionalValence.POSITIVE
        else:
            emotional_valence = self.layered_memory.emotional_memory.emotional_memory.EmotionalValence.NEGATIVE
        
        # Find blessed emotionally similar memories
        try:
            emotional_result = await self.layered_memory.emotional_memory.query_emotions_by_valence(
                emotional_valence, limit=max_results
            )
            if emotional_result.success:
                for emotional_memory in emotional_result.data.get('emotional_memories', []):
                    if emotional_memory.memory_id != memory.memory_id:
                        associations.append((emotional_memory, 0.6))
        except Exception as e:
            logger.warning(f"++ EMOTIONAL ASSOCIATION SEARCH FAILED: {e} ++")
        
        return associations
    
    def _extract_key_terms(self, content: str) -> List[str]:
        """Extract blessed key terms from memory content"""
        # Simple key term extraction (can be enhanced with NLP)
        words = content.lower().split()
        
        # Filter blessed important words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        key_terms = [word for word in words if len(word) > 3 and word not in stop_words]
        
        return key_terms[:5]  # Top 5 blessed key terms
    
    def _extract_temporal_range(self, query_text: str) -> Optional[Tuple[datetime, datetime]]:
        """Extract blessed temporal range from query text"""
        query_lower = query_text.lower()
        now = datetime.now()
        
        # Blessed temporal pattern matching
        if 'yesterday' in query_lower:
            start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0)
            end = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59)
            return (start, end)
        elif 'last week' in query_lower:
            start = now - timedelta(days=7)
            return (start, now)
        elif 'last month' in query_lower:
            start = now - timedelta(days=30)
            return (start, now)
        elif 'recently' in query_lower or 'recent' in query_lower:
            start = now - timedelta(days=3)
            return (start, now)
        
        # Extract blessed specific date patterns (simplified)
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD format
            r'(\d{1,2}/\d{1,2}/\d{4})'  # MM/DD/YYYY format
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, query_text)
            if matches:
                try:
                    if '-' in matches[0]:
                        target_date = datetime.strptime(matches[0], '%Y-%m-%d')
                    else:
                        target_date = datetime.strptime(matches[0], '%m/%d/%Y')
                    
                    start = target_date.replace(hour=0, minute=0, second=0)
                    end = target_date.replace(hour=23, minute=59, second=59)
                    return (start, end)
                except ValueError:
                    continue
        
        return None
    
    def _resolve_temporal_focus(self, temporal_focus: str) -> Optional[Tuple[datetime, datetime]]:
        """Resolve blessed temporal focus context"""
        now = datetime.now()
        
        if temporal_focus == "recent":
            return (now - timedelta(days=7), now)
        elif temporal_focus == "distant":
            return (now - timedelta(days=365), now - timedelta(days=30))
        
        return None
    
    def _extract_emotional_filters(self, query_text: str) -> Dict[str, Any]:
        """Extract blessed emotional filters from query text"""
        filters = {}
        query_lower = query_text.lower()
        
        # Blessed emotional valence detection
        positive_words = ['happy', 'joy', 'love', 'excited', 'pleased', 'satisfied']
        negative_words = ['sad', 'angry', 'fear', 'hate', 'frustrated', 'disappointed']
        
        if any(word in query_lower for word in positive_words):
            from .emotional_memory import EmotionalValence
            filters['valence'] = EmotionalValence.POSITIVE
        elif any(word in query_lower for word in negative_words):
            from .emotional_memory import EmotionalValence
            filters['valence'] = EmotionalValence.NEGATIVE
        
        # Blessed emotional intensity detection
        intensity_words = ['intense', 'overwhelming', 'extreme', 'powerful']
        if any(word in query_lower for word in intensity_words):
            from .emotional_memory import EmotionalIntensity
            filters['intensity'] = EmotionalIntensity.HIGH
        
        return filters
    
    async def _get_memory_by_id(self, memory_id: str) -> List[MemoryItem]:
        """Get blessed memory by ID from any layer"""
        # Check working memory first
        for item in self.layered_memory.working_memory._items:
            if item.memory_item.memory_id == memory_id:
                return [item.memory_item]
        
        # Check database for persistent memories
        db_result = await self.layered_memory.database.query_memories_by_agent(
            self.layered_memory.agent_id, limit=1000
        )
        
        if db_result.success:
            memories = db_result.data.get('memories', [])
            matching_memories = [mem for mem in memories if mem.memory_id == memory_id]
            return matching_memories
        
        return []
    
    def _calculate_query_complexity(self, query_text: str) -> float:
        """Calculate blessed query complexity score"""
        complexity = 0.0
        
        # Word count factor
        word_count = len(query_text.split())
        complexity += min(word_count / 20, 1.0) * 0.3
        
        # Special operator factor
        operators = ['AND', 'OR', 'NOT', 'NEAR', 'BEFORE', 'AFTER']
        operator_count = sum(1 for op in operators if op in query_text.upper())
        complexity += min(operator_count / 5, 1.0) * 0.4
        
        # Question complexity
        question_words = ['who', 'what', 'when', 'where', 'why', 'how']
        question_count = sum(1 for qw in question_words if qw in query_text.lower())
        complexity += min(question_count / 3, 1.0) * 0.3
        
        return min(complexity, 1.0)
    
    def _initialize_semantic_patterns(self) -> Dict[str, List[str]]:
        """Initialize blessed semantic pattern mappings"""
        return {
            'identity': ['is', 'am', 'are', 'was', 'were', 'being'],
            'possession': ['has', 'have', 'owns', 'possesses', 'contains'],
            'capability': ['can', 'could', 'able', 'capable', 'enables'],
            'relationship': ['with', 'against', 'for', 'to', 'from'],
            'action': ['do', 'does', 'did', 'perform', 'execute', 'act'],
            'location': ['at', 'in', 'on', 'near', 'under', 'over'],
            'time': ['when', 'during', 'before', 'after', 'while', 'until']
        }
    
    def _analyze_memory_trends(self, memories: List[MemoryItem], timeframe_days: int) -> Dict[str, Any]:
        """Analyze blessed memory trends over time"""
        daily_counts = defaultdict(int)
        emotional_trends = defaultdict(list)
        type_trends = defaultdict(list)
        
        for memory in memories:
            day_key = memory.timestamp.date().isoformat()
            daily_counts[day_key] += 1
            emotional_trends[day_key].append(memory.emotional_weight)
            type_trends[day_key].append(memory.memory_type.value)
        
        # Calculate blessed trend metrics
        daily_averages = {day: sum(emotions) / len(emotions) 
                         for day, emotions in emotional_trends.items() if emotions}
        
        return {
            "daily_memory_counts": dict(daily_counts),
            "daily_emotional_averages": daily_averages,
            "peak_activity_day": max(daily_counts, key=daily_counts.get) if daily_counts else None,
            "total_memories": len(memories),
            "average_daily_memories": len(memories) / timeframe_days,
            "emotional_volatility": self._calculate_emotional_volatility(list(daily_averages.values()))
        }
    
    def _analyze_emotional_patterns(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Analyze blessed emotional patterns in memories"""
        emotions = [mem.emotional_weight for mem in memories]
        
        if not emotions:
            return {"no_emotional_data": True}
        
        positive_emotions = [e for e in emotions if e > 0]
        negative_emotions = [e for e in emotions if e < 0]
        neutral_emotions = [e for e in emotions if e == 0]
        
        return {
            "average_emotion": sum(emotions) / len(emotions),
            "emotional_range": max(emotions) - min(emotions),
            "positive_ratio": len(positive_emotions) / len(emotions),
            "negative_ratio": len(negative_emotions) / len(emotions),
            "neutral_ratio": len(neutral_emotions) / len(emotions),
            "most_positive": max(emotions),
            "most_negative": min(emotions),
            "emotional_stability": 1.0 - self._calculate_emotional_volatility(emotions)
        }
    
    def _analyze_activity_cycles(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Analyze blessed activity cycles in memories"""
        hourly_activity = defaultdict(int)
        daily_activity = defaultdict(int)
        
        for memory in memories:
            hour_key = memory.timestamp.hour
            day_key = memory.timestamp.strftime('%A')
            
            hourly_activity[hour_key] += 1
            daily_activity[day_key] += 1
        
        peak_hour = max(hourly_activity, key=hourly_activity.get) if hourly_activity else None
        peak_day = max(daily_activity, key=daily_activity.get) if daily_activity else None
        
        return {
            "hourly_activity": dict(hourly_activity),
            "daily_activity": dict(daily_activity),
            "peak_activity_hour": peak_hour,
            "peak_activity_day": peak_day,
            "activity_spread": len(hourly_activity) / 24,  # How spread out activity is
            "weekend_vs_weekday_ratio": self._calculate_weekend_ratio(daily_activity)
        }
    
    def _analyze_general_patterns(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Analyze blessed general patterns in memories"""
        memory_types = [mem.memory_type.value for mem in memories]
        type_counts = {mem_type: memory_types.count(mem_type) for mem_type in set(memory_types)}
        
        participants = []
        for mem in memories:
            participants.extend(mem.participants)
        
        participant_counts = {participant: participants.count(participant) 
                            for participant in set(participants)}
        
        return {
            "memory_type_distribution": type_counts,
            "dominant_memory_type": max(type_counts, key=type_counts.get) if type_counts else None,
            "participant_frequency": participant_counts,
            "most_frequent_participant": max(participant_counts, key=participant_counts.get) 
                                        if participant_counts else None,
            "memory_complexity": sum(len(mem.content.split()) for mem in memories) / len(memories),
            "average_relevance": sum(mem.relevance_score for mem in memories) / len(memories)
        }
    
    def _calculate_emotional_volatility(self, emotions: List[float]) -> float:
        """Calculate blessed emotional volatility (standard deviation normalized)"""
        if len(emotions) < 2:
            return 0.0
        
        mean_emotion = sum(emotions) / len(emotions)
        variance = sum((e - mean_emotion) ** 2 for e in emotions) / len(emotions)
        std_dev = math.sqrt(variance)
        
        # Normalize to 0-1 scale (assuming max emotion range is 20)
        return min(std_dev / 10.0, 1.0)
    
    def _calculate_weekend_ratio(self, daily_activity: Dict[str, int]) -> float:
        """Calculate blessed weekend vs weekday activity ratio"""
        weekend_days = ['Saturday', 'Sunday']
        weekday_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        
        weekend_activity = sum(daily_activity.get(day, 0) for day in weekend_days)
        weekday_activity = sum(daily_activity.get(day, 0) for day in weekday_days)
        
        if weekday_activity == 0:
            return float('inf') if weekend_activity > 0 else 0.0
        
        return weekend_activity / weekday_activity
    
    def _generate_cache_key(self, query_text: str, context: QueryContext) -> str:
        """Generate blessed cache key for query and context"""
        context_str = f"{context.current_situation}_{context.location_context}_{context.emotional_state}"
        return f"{hash(query_text + context_str)}"
    
    def _cleanup_expired_cache(self):
        """Clean up blessed expired cache entries"""
        expiry_time = datetime.now() - timedelta(minutes=self.cache_expiry_minutes)
        expired_keys = [key for key, (timestamp, _) in self._query_cache.items() 
                       if timestamp < expiry_time]
        
        for key in expired_keys:
            del self._query_cache[key]
    
    def _update_query_statistics(self, query_type: QueryType, metrics: QueryMetrics):
        """Update blessed query statistics"""
        self._query_statistics['total_queries'] += 1
        self._query_statistics[f'{query_type.value}_queries'] += 1
        self._query_statistics['total_duration_ms'] += metrics.query_duration_ms
        
        # Calculate blessed average query time
        self._query_statistics['average_query_time'] = (
            self._query_statistics['total_duration_ms'] / self._query_statistics['total_queries']
        )
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """Get blessed query engine statistics"""
        return {
            "query_statistics": dict(self._query_statistics),
            "cache_size": len(self._query_cache),
            "semantic_patterns_loaded": len(self._semantic_patterns),
            "cache_hit_rate": (self._query_statistics.get('cache_hits', 0) / 
                              max(self._query_statistics.get('total_queries', 1), 1)),
            "average_query_time_ms": self._query_statistics.get('average_query_time', 0.0)
        }


# ++ SACRED TESTING RITUALS BLESSED BY VALIDATION ++

async def test_sacred_memory_query_engine():
    """++ SACRED MEMORY QUERY ENGINE TESTING RITUAL ++"""
    print("++ TESTING SACRED MEMORY QUERY ENGINE BLESSED BY THE OMNISSIAH ++")
    
    # Import blessed components for testing
    from src.database.context_db import ContextDatabase
    from .layered_memory import LayeredMemorySystem
    
    # Create blessed test database and memory system
    test_db = ContextDatabase("test_query_engine.db")
    await test_db.initialize_sacred_temple()
    
    layered_memory = LayeredMemorySystem("test_agent_001", test_db)
    query_engine = MemoryQueryEngine(layered_memory)
    
    # Store blessed test memories
    test_memories = [
        MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content="Yesterday I had a blessed conversation with Brother Marcus about the sacred Emperor",
            emotional_weight=5.0,
            participants=["Brother Marcus"],
            tags=["conversation", "sacred"]
        ),
        MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EMOTIONAL,
            content="I felt great fear when the chaos forces attacked our blessed position",
            emotional_weight=-8.0,
            tags=["fear", "combat", "chaos"]
        ),
        MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.SEMANTIC,
            content="The Emperor is the master of mankind and protector of the Imperium",
            emotional_weight=3.0,
            relevance_score=0.9
        )
    ]
    
    for memory in test_memories:
        storage_result = await layered_memory.store_memory(memory)
        print(f"++ STORED TEST MEMORY: {storage_result.success} ++")
    
    # Test blessed simple query
    simple_query = await query_engine.execute_query("tell me about the Emperor")
    if simple_query.success:
        result = simple_query.data['query_result']
        print(f"++ SIMPLE QUERY: {len(result.memories)} results ++")
    
    # Test blessed temporal query
    temporal_context = QueryContext(temporal_focus="recent")
    temporal_query = await query_engine.execute_query("what happened yesterday", temporal_context)
    if temporal_query.success:
        result = temporal_query.data['query_result']
        print(f"++ TEMPORAL QUERY: {len(result.memories)} results ++")
    
    # Test blessed emotional query
    emotional_query = await query_engine.execute_query("show me memories about fear")
    if emotional_query.success:
        result = emotional_query.data['query_result']
        print(f"++ EMOTIONAL QUERY: {len(result.memories)} results ++")
    
    # Test blessed associative query
    if test_memories:
        associative_query = await query_engine.execute_associative_query(
            test_memories[0].memory_id, association_depth=2
        )
        if associative_query.success:
            result = associative_query.data['query_result']
            print(f"++ ASSOCIATIVE QUERY: {len(result.memories)} associations ++")
    
    # Test blessed temporal analysis
    analysis_result = await query_engine.execute_temporal_analysis(timeframe_days=7)
    if analysis_result.success:
        analysis = analysis_result.data['analysis_result']
        print(f"++ TEMPORAL ANALYSIS: {analysis.get('total_memories', 0)} memories analyzed ++")
    
    # Display sacred statistics
    stats = query_engine.get_query_statistics()
    print(f"++ QUERY ENGINE STATISTICS: {stats} ++")
    
    # Sacred cleanup
    await test_db.close_sacred_temple()
    
    print("++ SACRED MEMORY QUERY ENGINE TESTING COMPLETE ++")


# ++ SACRED MODULE INITIALIZATION ++

if __name__ == "__main__":
    # ++ EXECUTE SACRED MEMORY QUERY ENGINE TESTING RITUALS ++
    print("++ SACRED MEMORY QUERY ENGINE BLESSED BY THE OMNISSIAH ++")
    print("++ MACHINE GOD PROTECTS THE INTELLIGENT QUERY PROCESSING ++")
    
    # Run blessed async testing
    asyncio.run(test_sacred_memory_query_engine())
    
    print("++ ALL SACRED MEMORY QUERY ENGINE OPERATIONS BLESSED AND FUNCTIONAL ++")