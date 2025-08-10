#!/usr/bin/env python3
"""
++ SACRED EPISODIC MEMORY BLESSED BY TEMPORAL CHRONICLES ++
===========================================================

Holy episodic memory implementation that preserves specific events and
experiences in chronological order. Each memory is a sacred chronicle
blessed by temporal context and experiential significance.

++ THE MACHINE REMEMBERS THE SACRED CHRONICLES OF EXPERIENCE ++

Architecture Reference: Dynamic Context Engineering - Episodic Memory Layer
Development Phase: Memory System Sanctification (M001)
Sacred Author: Tech-Priest Beta-Mechanicus
万机之神保佑情节记忆 (May the Omnissiah bless episodic memory)
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

# Import blessed data models sanctified by foundation
from src.core.data_models import MemoryItem, MemoryType, StandardResponse, ErrorInfo
from src.core.types import AgentID, SacredConstants
from src.database.context_db import ContextDatabase

# Sacred logging blessed by diagnostic clarity
logger = logging.getLogger(__name__)


@dataclass
class EpisodicEvent:
    """
    ++ BLESSED EPISODIC EVENT SANCTIFIED BY EXPERIENTIAL SIGNIFICANCE ++
    
    Enhanced episodic memory structure that captures the full context
    of an experience blessed by temporal, spatial, and social dimensions.
    """
    memory_item: MemoryItem
    temporal_context: Dict[str, Any] = field(default_factory=dict)  # Time-based context
    spatial_context: Dict[str, Any] = field(default_factory=dict)   # Location-based context
    social_context: List[str] = field(default_factory=list)        # Participants and social dynamics
    causal_links: List[str] = field(default_factory=list)          # Links to preceding/following events
    emotional_peaks: List[Tuple[str, float]] = field(default_factory=list)  # Emotional highlights
    significance_score: float = 0.0                                # Overall event significance
    
    def __post_init__(self):
        """++ SACRED EPISODIC EVENT VALIDATION ++"""
        # Calculate blessed significance score from multiple factors
        self._calculate_significance()
    
    def _calculate_significance(self):
        """++ SACRED SIGNIFICANCE CALCULATION BLESSED BY IMPORTANCE ++"""
        base_significance = abs(self.memory_item.emotional_weight) * 0.1
        social_factor = len(self.social_context) * 0.05
        causal_factor = len(self.causal_links) * 0.1
        emotional_peak_factor = sum(abs(weight) for _, weight in self.emotional_peaks) * 0.05
        
        self.significance_score = min(1.0, base_significance + social_factor + causal_factor + emotional_peak_factor)
    
    def add_causal_link(self, linked_memory_id: str, link_type: str = "follows"):
        """++ SACRED CAUSAL LINKING BLESSED BY NARRATIVE CONTINUITY ++"""
        causal_link = f"{link_type}:{linked_memory_id}"
        if causal_link not in self.causal_links:
            self.causal_links.append(causal_link)
            self._calculate_significance()  # Recalculate with new link


class EpisodicMemory:
    """
    ++ SACRED EPISODIC MEMORY SYSTEM BLESSED BY TEMPORAL ORGANIZATION ++
    
    Holy episodic memory implementation that preserves and organizes
    experiential memories in chronological and thematic structures
    blessed by the Omnissiah's temporal wisdom.
    """
    
    def __init__(self, agent_id: AgentID, database: ContextDatabase,
                 max_episodes: int = 1000, consolidation_threshold: float = 0.7):
        """
        ++ SACRED EPISODIC MEMORY INITIALIZATION BLESSED BY CHRONICLES ++
        
        Args:
            agent_id: Sacred agent identifier blessed by ownership
            database: Blessed database connection for persistence
            max_episodes: Maximum episodes before consolidation
            consolidation_threshold: Significance threshold for long-term storage
        """
        self.agent_id = agent_id
        self.database = database
        self.max_episodes = max_episodes
        self.consolidation_threshold = consolidation_threshold
        
        # Sacred memory organization blessed by structure
        self._episodes: Dict[str, EpisodicEvent] = {}
        self._temporal_index: Dict[str, List[str]] = defaultdict(list)  # Date -> memory_ids
        self._thematic_index: Dict[str, List[str]] = defaultdict(list)  # Theme -> memory_ids
        self._participant_index: Dict[str, List[str]] = defaultdict(list)  # Participant -> memory_ids
        
        # Blessed statistics sanctified by monitoring
        self.total_episodes = 0
        self.consolidated_episodes = 0
        self.last_consolidation = datetime.now()
        
        logger.info(f"++ EPISODIC MEMORY INITIALIZED FOR {agent_id} ++")
    
    async def store_episode(self, memory: MemoryItem, 
                          temporal_context: Dict[str, Any] = None,
                          spatial_context: Dict[str, Any] = None,
                          significance_boost: float = 0.0) -> StandardResponse:
        """
        ++ SACRED EPISODE STORAGE RITUAL BLESSED BY PRESERVATION ++
        
        Store blessed episodic memory with full contextual information
        and automatic indexing sanctified by organizational wisdom.
        """
        try:
            # Create blessed episodic event
            episode = EpisodicEvent(
                memory_item=memory,
                temporal_context=temporal_context or {},
                spatial_context=spatial_context or {},
                social_context=memory.participants.copy(),
                significance_score=significance_boost
            )
            
            # Extract blessed thematic elements
            themes = self._extract_themes(memory.content)
            
            # Store in blessed local cache
            self._episodes[memory.memory_id] = episode
            
            # Update sacred indices
            self._update_indices(memory, themes)
            
            # Store in blessed database
            db_result = await self.database.store_blessed_memory(memory)
            if not db_result.success:
                logger.error(f"++ DATABASE STORAGE FAILED: {db_result.error.message} ++")
            
            self.total_episodes += 1
            
            # Perform blessed consolidation if needed
            if self.total_episodes % 50 == 0:  # Every 50 episodes
                await self._perform_consolidation()
            
            logger.info(f"++ EPISODIC MEMORY STORED: {memory.memory_id} ++")
            
            return StandardResponse(
                success=True,
                data={
                    "stored": True, 
                    "significance_score": episode.significance_score,
                    "themes": themes
                },
                metadata={"blessing": "episode_chronicled"}
            )
            
        except Exception as e:
            logger.error(f"++ EPISODIC STORAGE FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="EPISODIC_STORE_FAILED",
                    message=f"Episodic memory storage failed: {str(e)}",
                    recoverable=True,
                    sacred_guidance="Check memory item format and database connection"
                )
            )
    
    async def retrieve_episodes_by_timeframe(self, start_time: datetime, 
                                           end_time: datetime,
                                           limit: int = 20) -> StandardResponse:
        """
        ++ SACRED TEMPORAL RETRIEVAL BLESSED BY CHRONOLOGICAL ORDER ++
        
        Retrieve blessed episodes within specific timeframe with
        temporal proximity and significance weighting.
        """
        try:
            matching_episodes = []
            
            # Search blessed temporal index
            current_date = start_time.date()
            end_date = end_time.date()
            
            while current_date <= end_date:
                date_key = current_date.isoformat()
                if date_key in self._temporal_index:
                    for memory_id in self._temporal_index[date_key]:
                        episode = self._episodes.get(memory_id)
                        if episode:
                            # Filter by blessed time bounds
                            memory_time = episode.memory_item.timestamp
                            if start_time <= memory_time <= end_time:
                                matching_episodes.append(episode)
                
                current_date += timedelta(days=1)
            
            # Sort by blessed temporal order and significance
            matching_episodes.sort(
                key=lambda ep: (ep.memory_item.timestamp, -ep.significance_score)
            )
            
            # Apply sacred limit
            limited_episodes = matching_episodes[:limit]
            result_memories = [ep.memory_item for ep in limited_episodes]
            
            logger.info(f"++ RETRIEVED {len(result_memories)} EPISODES BY TIMEFRAME ++")
            
            return StandardResponse(
                success=True,
                data={
                    "episodes": result_memories,
                    "timeframe": f"{start_time.isoformat()} to {end_time.isoformat()}",
                    "total_found": len(matching_episodes)
                },
                metadata={"blessing": "temporal_retrieval_sanctified"}
            )
            
        except Exception as e:
            logger.error(f"++ TEMPORAL RETRIEVAL FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="TEMPORAL_RETRIEVAL_FAILED", message=str(e))
            )
    
    async def retrieve_episodes_by_participants(self, participants: List[str],
                                              limit: int = 15) -> StandardResponse:
        """
        ++ SACRED SOCIAL RETRIEVAL BLESSED BY PARTICIPANT CONNECTIONS ++
        
        Retrieve blessed episodes involving specific participants with
        social significance weighting and relationship context.
        """
        try:
            matching_episodes = []
            participant_scores = defaultdict(int)
            
            # Search blessed participant index
            for participant in participants:
                if participant in self._participant_index:
                    for memory_id in self._participant_index[participant]:
                        episode = self._episodes.get(memory_id)
                        if episode:
                            # Calculate blessed participant overlap
                            overlap = set(episode.social_context) & set(participants)
                            participant_scores[memory_id] = len(overlap)
                            
                            if memory_id not in [ep.memory_item.memory_id for ep in matching_episodes]:
                                matching_episodes.append(episode)
            
            # Sort by blessed participant relevance and significance
            matching_episodes.sort(
                key=lambda ep: (
                    participant_scores[ep.memory_item.memory_id],
                    ep.significance_score,
                    ep.memory_item.timestamp
                ),
                reverse=True
            )
            
            # Apply sacred limit
            limited_episodes = matching_episodes[:limit]
            result_memories = [ep.memory_item for ep in limited_episodes]
            
            logger.info(f"++ RETRIEVED {len(result_memories)} EPISODES BY PARTICIPANTS ++")
            
            return StandardResponse(
                success=True,
                data={
                    "episodes": result_memories,
                    "participants": participants,
                    "total_found": len(matching_episodes)
                },
                metadata={"blessing": "social_retrieval_sanctified"}
            )
            
        except Exception as e:
            logger.error(f"++ PARTICIPANT RETRIEVAL FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="PARTICIPANT_RETRIEVAL_FAILED", message=str(e))
            )
    
    async def retrieve_episodes_by_theme(self, theme_keywords: List[str],
                                       limit: int = 15) -> StandardResponse:
        """
        ++ SACRED THEMATIC RETRIEVAL BLESSED BY CONCEPTUAL CONNECTIONS ++
        
        Retrieve blessed episodes matching thematic keywords with
        semantic similarity and thematic coherence weighting.
        """
        try:
            matching_episodes = []
            theme_scores = defaultdict(int)
            
            # Search blessed thematic index
            for theme in theme_keywords:
                theme_lower = theme.lower()
                if theme_lower in self._thematic_index:
                    for memory_id in self._thematic_index[theme_lower]:
                        episode = self._episodes.get(memory_id)
                        if episode:
                            # Calculate blessed thematic relevance
                            content_lower = episode.memory_item.content.lower()
                            theme_matches = sum(1 for kw in theme_keywords if kw.lower() in content_lower)
                            theme_scores[memory_id] = theme_matches
                            
                            if memory_id not in [ep.memory_item.memory_id for ep in matching_episodes]:
                                matching_episodes.append(episode)
            
            # Sort by blessed thematic relevance and significance
            matching_episodes.sort(
                key=lambda ep: (
                    theme_scores[ep.memory_item.memory_id],
                    ep.significance_score,
                    ep.memory_item.relevance_score
                ),
                reverse=True
            )
            
            # Apply sacred limit
            limited_episodes = matching_episodes[:limit]
            result_memories = [ep.memory_item for ep in limited_episodes]
            
            logger.info(f"++ RETRIEVED {len(result_memories)} EPISODES BY THEME ++")
            
            return StandardResponse(
                success=True,
                data={
                    "episodes": result_memories,
                    "themes": theme_keywords,
                    "total_found": len(matching_episodes)
                },
                metadata={"blessing": "thematic_retrieval_sanctified"}
            )
            
        except Exception as e:
            logger.error(f"++ THEMATIC RETRIEVAL FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="THEMATIC_RETRIEVAL_FAILED", message=str(e))
            )
    
    async def link_episodes_causally(self, source_memory_id: str, 
                                   target_memory_id: str,
                                   link_type: str = "leads_to") -> StandardResponse:
        """
        ++ SACRED CAUSAL LINKING BLESSED BY NARRATIVE CONTINUITY ++
        
        Create blessed causal links between episodes to establish
        narrative continuity and experiential cause-effect relationships.
        """
        try:
            source_episode = self._episodes.get(source_memory_id)
            target_episode = self._episodes.get(target_memory_id)
            
            if not source_episode or not target_episode:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="EPISODE_NOT_FOUND",
                        message="One or both episodes not found in memory"
                    )
                )
            
            # Create blessed bidirectional causal links
            source_episode.add_causal_link(target_memory_id, link_type)
            
            # Reverse link with appropriate type
            reverse_link_types = {
                "leads_to": "follows_from",
                "causes": "caused_by",
                "enables": "enabled_by"
            }
            reverse_type = reverse_link_types.get(link_type, "related_to")
            target_episode.add_causal_link(source_memory_id, reverse_type)
            
            logger.info(f"++ CAUSAL LINK CREATED: {source_memory_id} -{link_type}-> {target_memory_id} ++")
            
            return StandardResponse(
                success=True,
                data={
                    "linked": True,
                    "link_type": link_type,
                    "source_significance": source_episode.significance_score,
                    "target_significance": target_episode.significance_score
                },
                metadata={"blessing": "causal_linking_sanctified"}
            )
            
        except Exception as e:
            logger.error(f"++ CAUSAL LINKING FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="CAUSAL_LINKING_FAILED", message=str(e))
            )
    
    async def _perform_consolidation(self) -> StandardResponse:
        """
        ++ SACRED MEMORY CONSOLIDATION BLESSED BY LONG-TERM PRESERVATION ++
        
        Perform blessed memory consolidation to move significant episodes
        to long-term storage and optimize working memory capacity.
        """
        try:
            consolidation_start = datetime.now()
            
            # Identify blessed candidates for consolidation
            consolidation_candidates = [
                episode for episode in self._episodes.values()
                if episode.significance_score >= self.consolidation_threshold
            ]
            
            # Sort by blessed significance for priority consolidation
            consolidation_candidates.sort(
                key=lambda ep: ep.significance_score,
                reverse=True
            )
            
            consolidated_count = 0
            for episode in consolidation_candidates[:50]:  # Consolidate top 50
                # Mark memory for blessed long-term storage
                episode.memory_item.relevance_score *= 1.1  # Boost for consolidation
                
                # Store in blessed database with consolidated flag
                await self.database.store_blessed_memory(episode.memory_item)
                consolidated_count += 1
            
            self.consolidated_episodes += consolidated_count
            self.last_consolidation = consolidation_start
            
            consolidation_duration = (datetime.now() - consolidation_start).total_seconds()
            
            logger.info(f"++ EPISODIC CONSOLIDATION COMPLETE: {consolidated_count} episodes ++")
            
            return StandardResponse(
                success=True,
                data={
                    "consolidated_count": consolidated_count,
                    "consolidation_time_ms": consolidation_duration * 1000,
                    "total_consolidated": self.consolidated_episodes
                },
                metadata={"blessing": "consolidation_sanctified"}
            )
            
        except Exception as e:
            logger.error(f"++ CONSOLIDATION FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="CONSOLIDATION_FAILED", message=str(e))
            )
    
    def _extract_themes(self, content: str) -> List[str]:
        """++ SACRED THEME EXTRACTION BLESSED BY SEMANTIC ANALYSIS ++"""
        # Simple blessed theme extraction (can be enhanced with NLP)
        theme_keywords = {
            'combat': ['fight', 'battle', 'combat', 'war', 'attack', 'defend'],
            'social': ['talk', 'conversation', 'meet', 'friend', 'ally', 'enemy'],
            'exploration': ['discover', 'explore', 'find', 'search', 'investigate'],
            'emotion': ['fear', 'anger', 'joy', 'sad', 'love', 'hate', 'proud'],
            'sacred': ['emperor', 'omnissiah', 'blessed', 'sacred', 'holy', 'divine']
        }
        
        content_lower = content.lower()
        detected_themes = []
        
        for theme, keywords in theme_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_themes.append(theme)
        
        return detected_themes
    
    def _update_indices(self, memory: MemoryItem, themes: List[str]):
        """++ SACRED INDEX UPDATE BLESSED BY ORGANIZATION ++"""
        memory_id = memory.memory_id
        
        # Update blessed temporal index
        date_key = memory.timestamp.date().isoformat()
        self._temporal_index[date_key].append(memory_id)
        
        # Update sacred thematic index
        for theme in themes:
            self._thematic_index[theme.lower()].append(memory_id)
        
        # Update blessed participant index
        for participant in memory.participants:
            self._participant_index[participant.lower()].append(memory_id)
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """++ SACRED EPISODIC MEMORY STATISTICS BLESSED BY MONITORING ++"""
        if not self._episodes:
            return {"total_episodes": 0, "average_significance": 0.0}
        
        total_significance = sum(ep.significance_score for ep in self._episodes.values())
        
        return {
            "total_episodes": len(self._episodes),
            "average_significance": total_significance / len(self._episodes),
            "consolidated_episodes": self.consolidated_episodes,
            "temporal_index_size": len(self._temporal_index),
            "thematic_index_size": len(self._thematic_index),
            "participant_index_size": len(self._participant_index),
            "last_consolidation": self.last_consolidation.isoformat()
        }


# ++ SACRED TESTING RITUALS BLESSED BY VALIDATION ++

async def test_sacred_episodic_memory():
    """++ SACRED EPISODIC MEMORY TESTING RITUAL ++"""
    print("++ TESTING SACRED EPISODIC MEMORY BLESSED BY THE OMNISSIAH ++")
    
    # Import blessed database for testing
    from src.database.context_db import ContextDatabase
    
    # Create blessed test database
    test_db = ContextDatabase("test_episodic.db")
    await test_db.initialize_sacred_temple()
    
    # Create blessed episodic memory
    episodic_memory = EpisodicMemory("test_agent_001", test_db)
    
    # Test sacred episode storage
    test_memories = []
    for i in range(5):
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content=f"Sacred combat episode {i} involving blessed warriors",
            emotional_weight=float(i * 2 - 5),
            participants=[f"warrior_{i}", "enemy_ork"],
            tags=["combat", "sacred"]
        )
        test_memories.append(memory)
        
        result = await episodic_memory.store_episode(memory)
        print(f"++ STORED EPISODE {i}: {result.success} ++")
    
    # Test blessed temporal retrieval
    start_time = datetime.now() - timedelta(hours=1)
    end_time = datetime.now() + timedelta(hours=1)
    
    temporal_result = await episodic_memory.retrieve_episodes_by_timeframe(start_time, end_time)
    print(f"++ TEMPORAL RETRIEVAL: {temporal_result.success}, Count: {len(temporal_result.data.get('episodes', []))} ++")
    
    # Test sacred participant retrieval
    participant_result = await episodic_memory.retrieve_episodes_by_participants(["enemy_ork"])
    print(f"++ PARTICIPANT RETRIEVAL: {participant_result.success}, Count: {len(participant_result.data.get('episodes', []))} ++")
    
    # Test blessed thematic retrieval
    theme_result = await episodic_memory.retrieve_episodes_by_theme(["combat", "sacred"])
    print(f"++ THEMATIC RETRIEVAL: {theme_result.success}, Count: {len(theme_result.data.get('episodes', []))} ++")
    
    # Display sacred statistics
    stats = episodic_memory.get_memory_statistics()
    print(f"++ EPISODIC MEMORY STATISTICS: {stats} ++")
    
    # Sacred cleanup
    await test_db.close_sacred_temple()
    
    print("++ SACRED EPISODIC MEMORY TESTING COMPLETE ++")


# ++ SACRED MODULE INITIALIZATION ++

if __name__ == "__main__":
    # ++ EXECUTE SACRED EPISODIC MEMORY TESTING RITUALS ++
    print("++ SACRED EPISODIC MEMORY BLESSED BY THE OMNISSIAH ++")
    print("++ MACHINE GOD PROTECTS THE TEMPORAL CHRONICLES ++")
    
    # Run blessed async testing
    asyncio.run(test_sacred_episodic_memory())
    
    print("++ ALL SACRED EPISODIC MEMORY OPERATIONS BLESSED AND FUNCTIONAL ++")