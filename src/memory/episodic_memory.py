#!/usr/bin/env python3
"""
Episodic Memory System
======================

This module provides an episodic memory system that preserves specific events
and experiences in chronological order. Each memory is a chronicle of an
event, enriched with temporal context and experiential significance.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from src.core.data_models import MemoryItem, MemoryType, StandardResponse, ErrorInfo
from src.core.types import AgentID
from src.database.context_db import ContextDatabase

logger = logging.getLogger(__name__)


@dataclass
class EpisodicEvent:
    """
    Represents an episodic memory event, capturing the full context of an
    experience, including temporal, spatial, and social dimensions.
    """
    memory_item: MemoryItem
    temporal_context: Dict[str, Any] = field(default_factory=dict)
    spatial_context: Dict[str, Any] = field(default_factory=dict)
    social_context: List[str] = field(default_factory=list)
    causal_links: List[str] = field(default_factory=list)
    emotional_peaks: List[Tuple[str, float]] = field(default_factory=list)
    significance_score: float = 0.0
    
    def __post_init__(self):
        """Calculates the event's significance after initialization."""
        self._calculate_significance()
    
    def _calculate_significance(self):
        """Calculates the significance of the event based on various factors."""
        base_significance = abs(self.memory_item.emotional_weight) * 0.1
        social_factor = len(self.social_context) * 0.05
        causal_factor = len(self.causal_links) * 0.1
        emotional_peak_factor = sum(abs(weight) for _, weight in self.emotional_peaks) * 0.05
        
        self.significance_score = min(1.0, base_significance + social_factor + causal_factor + emotional_peak_factor)
    
    def add_causal_link(self, linked_memory_id: str, link_type: str = "follows"):
        """Adds a causal link to another memory and recalculates significance."""
        causal_link = f"{link_type}:{linked_memory_id}"
        if causal_link not in self.causal_links:
            self.causal_links.append(causal_link)
            self._calculate_significance()


class EpisodicMemory:
    """
    Manages episodic memories, preserving and organizing experiences in
    chronological and thematic structures.
    """
    
    def __init__(self, agent_id: AgentID, database: ContextDatabase,
                 max_episodes: int = 1000, consolidation_threshold: float = 0.7):
        """
        Initializes the EpisodicMemory system.

        Args:
            agent_id: The ID of the agent this memory belongs to.
            database: The database connection for persistence.
            max_episodes: The maximum number of episodes to hold before consolidation.
            consolidation_threshold: The significance score required for long-term storage.
        """
        self.agent_id = agent_id
        self.database = database
        self.max_episodes = max_episodes
        self.consolidation_threshold = consolidation_threshold
        
        self._episodes: Dict[str, EpisodicEvent] = {}
        self._temporal_index: Dict[str, List[str]] = defaultdict(list)
        self._thematic_index: Dict[str, List[str]] = defaultdict(list)
        self._participant_index: Dict[str, List[str]] = defaultdict(list)
        
        self.total_episodes = 0
        self.consolidated_episodes = 0
        self.last_consolidation = datetime.now()
        
        logger.info(f"Episodic Memory initialized for {agent_id}")
    
    async def store_episode(self, memory: MemoryItem, 
                          temporal_context: Optional[Dict[str, Any]] = None,
                          spatial_context: Optional[Dict[str, Any]] = None,
                          significance_boost: float = 0.0) -> StandardResponse:
        """
        Stores an episodic memory with its contextual information.
        """
        try:
            episode = EpisodicEvent(
                memory_item=memory,
                temporal_context=temporal_context or {},
                spatial_context=spatial_context or {},
                social_context=memory.participants.copy(),
                significance_score=significance_boost
            )
            
            themes = self._extract_themes(memory.content)
            
            self._episodes[memory.memory_id] = episode
            self._update_indices(memory, themes)
            
            db_result = await self.database.store_blessed_memory(memory)
            if not db_result.success:
                logger.error(f"Database store failed: {db_result.error.message}")
            
            self.total_episodes += 1
            
            if self.total_episodes % 50 == 0:
                await self._perform_consolidation()
            
            logger.info(f"Episodic memory stored: {memory.memory_id}")
            
            return StandardResponse(
                success=True,
                data={
                    "stored": True, 
                    "significance_score": episode.significance_score,
                    "themes": themes
                }
            )
            
        except Exception as e:
            logger.error(f"Episodic storage failed: {e}", exc_info=True)
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="EPISODIC_STORE_FAILED",
                    message=f"Episodic memory storage failed: {str(e)}"
                )
            )
    
    async def retrieve_episodes_by_timeframe(self, start_time: datetime, 
                                           end_time: datetime,
                                           limit: int = 20) -> StandardResponse:
        """
        Retrieves episodes within a specific timeframe, sorted by time and significance.
        """
        try:
            matching_episodes = []
            
            current_date = start_time.date()
            end_date = end_time.date()
            
            while current_date <= end_date:
                date_key = current_date.isoformat()
                if date_key in self._temporal_index:
                    for memory_id in self._temporal_index[date_key]:
                        episode = self._episodes.get(memory_id)
                        if episode and start_time <= episode.memory_item.timestamp <= end_time:
                            matching_episodes.append(episode)
                
                current_date += timedelta(days=1)
            
            matching_episodes.sort(
                key=lambda ep: (ep.memory_item.timestamp, -ep.significance_score)
            )
            
            limited_episodes = matching_episodes[:limit]
            result_memories = [ep.memory_item for ep in limited_episodes]
            
            logger.info(f"Retrieved {len(result_memories)} episodes by timeframe")
            
            return StandardResponse(
                success=True,
                data={
                    "episodes": result_memories,
                    "timeframe": f"{start_time.isoformat()} to {end_time.isoformat()}",
                    "total_found": len(matching_episodes)
                }
            )
            
        except Exception as e:
            logger.error(f"Temporal retrieval failed: {e}", exc_info=True)
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="TEMPORAL_RETRIEVAL_FAILED", message=str(e))
            )
    
    async def retrieve_episodes_by_participants(self, participants: List[str],
                                              limit: int = 15) -> StandardResponse:
        """
        Retrieves episodes involving specific participants.
        """
        try:
            matching_episodes = []
            participant_scores = defaultdict(int)
            
            unique_episode_ids = set()

            for participant in participants:
                if participant in self._participant_index:
                    for memory_id in self._participant_index[participant]:
                        if memory_id not in unique_episode_ids:
                            episode = self._episodes.get(memory_id)
                            if episode:
                                overlap = set(episode.social_context) & set(participants)
                                participant_scores[memory_id] = len(overlap)
                                matching_episodes.append(episode)
                                unique_episode_ids.add(memory_id)
            
            matching_episodes.sort(
                key=lambda ep: (
                    participant_scores[ep.memory_item.memory_id],
                    ep.significance_score,
                    ep.memory_item.timestamp
                ),
                reverse=True
            )
            
            limited_episodes = matching_episodes[:limit]
            result_memories = [ep.memory_item for ep in limited_episodes]
            
            logger.info(f"Retrieved {len(result_memories)} episodes by participants")
            
            return StandardResponse(
                success=True,
                data={
                    "episodes": result_memories,
                    "participants": participants,
                    "total_found": len(matching_episodes)
                }
            )
            
        except Exception as e:
            logger.error(f"Participant retrieval failed: {e}", exc_info=True)
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="PARTICIPANT_RETRIEVAL_FAILED", message=str(e))
            )
    
    async def retrieve_episodes_by_theme(self, theme_keywords: List[str],
                                       limit: int = 15) -> StandardResponse:
        """
        Retrieves episodes matching thematic keywords.
        """
        try:
            matching_episodes = []
            theme_scores = defaultdict(int)
            unique_episode_ids = set()
            
            for theme in theme_keywords:
                theme_lower = theme.lower()
                if theme_lower in self._thematic_index:
                    for memory_id in self._thematic_index[theme_lower]:
                        if memory_id not in unique_episode_ids:
                            episode = self._episodes.get(memory_id)
                            if episode:
                                content_lower = episode.memory_item.content.lower()
                                theme_matches = sum(1 for kw in theme_keywords if kw.lower() in content_lower)
                                theme_scores[memory_id] = theme_matches
                                matching_episodes.append(episode)
                                unique_episode_ids.add(memory_id)
            
            matching_episodes.sort(
                key=lambda ep: (
                    theme_scores[ep.memory_item.memory_id],
                    ep.significance_score,
                    ep.memory_item.relevance_score
                ),
                reverse=True
            )
            
            limited_episodes = matching_episodes[:limit]
            result_memories = [ep.memory_item for ep in limited_episodes]
            
            logger.info(f"Retrieved {len(result_memories)} episodes by theme")
            
            return StandardResponse(
                success=True,
                data={
                    "episodes": result_memories,
                    "themes": theme_keywords,
                    "total_found": len(matching_episodes)
                }
            )
            
        except Exception as e:
            logger.error(f"Thematic retrieval failed: {e}", exc_info=True)
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="THEMATIC_RETRIEVAL_FAILED", message=str(e))
            )
    
    async def link_episodes_causally(self, source_memory_id: str, 
                                   target_memory_id: str,
                                   link_type: str = "leads_to") -> StandardResponse:
        """
        Creates a causal link between two episodes to establish narrative continuity.
        """
        try:
            source_episode = self._episodes.get(source_memory_id)
            target_episode = self._episodes.get(target_memory_id)
            
            if not source_episode or not target_episode:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(code="EPISODE_NOT_FOUND", message="One or both episodes not found")
                )
            
            source_episode.add_causal_link(target_memory_id, link_type)
            
            reverse_link_types = {
                "leads_to": "follows_from", "causes": "caused_by", "enables": "enabled_by"
            }
            reverse_type = reverse_link_types.get(link_type, "related_to")
            target_episode.add_causal_link(source_memory_id, reverse_type)
            
            logger.info(f"Causal link created: {source_memory_id} -> {target_memory_id}")
            
            return StandardResponse(
                success=True,
                data={
                    "linked": True,
                    "link_type": link_type,
                    "source_significance": source_episode.significance_score,
                    "target_significance": target_episode.significance_score
                }
            )
            
        except Exception as e:
            logger.error(f"Causal linking failed: {e}", exc_info=True)
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="CAUSAL_LINKING_FAILED", message=str(e))
            )
    
    async def _perform_consolidation(self) -> StandardResponse:
        """
        Moves significant episodes to long-term storage and optimizes memory.
        """
        try:
            consolidation_start = datetime.now()
            
            consolidation_candidates = [
                ep for ep in self._episodes.values() if ep.significance_score >= self.consolidation_threshold
            ]
            
            consolidation_candidates.sort(key=lambda ep: ep.significance_score, reverse=True)
            
            consolidated_count = 0
            for episode in consolidation_candidates[:50]:
                episode.memory_item.relevance_score *= 1.1
                await self.database.store_blessed_memory(episode.memory_item)
                consolidated_count += 1
            
            self.consolidated_episodes += consolidated_count
            self.last_consolidation = consolidation_start
            duration_ms = (datetime.now() - consolidation_start).total_seconds() * 1000
            
            logger.info(f"Episodic consolidation complete: {consolidated_count} episodes in {duration_ms:.2f}ms")
            
            return StandardResponse(
                success=True,
                data={
                    "consolidated_count": consolidated_count,
                    "consolidation_time_ms": duration_ms,
                    "total_consolidated": self.consolidated_episodes
                }
            )
            
        except Exception as e:
            logger.error(f"Consolidation failed: {e}", exc_info=True)
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="CONSOLIDATION_FAILED", message=str(e))
            )
    
    def _extract_themes(self, content: str) -> List[str]:
        """Extracts thematic keywords from content."""
        theme_keywords = {
            'combat': ['fight', 'battle', 'combat', 'war', 'attack', 'defend'],
            'social': ['talk', 'conversation', 'meet', 'friend', 'ally', 'enemy'],
            'exploration': ['discover', 'explore', 'find', 'search', 'investigate'],
            'emotion': ['fear', 'anger', 'joy', 'sad', 'love', 'hate', 'proud'],
            'technical': ['build', 'repair', 'code', 'system', 'machine']
        }
        
        content_lower = content.lower()
        detected_themes = {
            theme for theme, keywords in theme_keywords.items()
            if any(keyword in content_lower for keyword in keywords)
        }
        return list(detected_themes)
    
    def _update_indices(self, memory: MemoryItem, themes: List[str]):
        """Updates internal indices for efficient querying."""
        memory_id = memory.memory_id
        
        date_key = memory.timestamp.date().isoformat()
        self._temporal_index[date_key].append(memory_id)
        
        for theme in themes:
            self._thematic_index[theme.lower()].append(memory_id)
        
        for participant in memory.participants:
            self._participant_index[participant.lower()].append(memory_id)
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Returns statistics about the episodic memory."""
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


async def test_episodic_memory():
    """Tests the episodic memory system."""
    print("Testing Episodic Memory System...")
    
    db = ContextDatabase(":memory:")
    await db.initialize()
    
    episodic_memory = EpisodicMemory("test_agent_001", db)
    
    test_memories = []
    for i in range(5):
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EPISODIC,
            content=f"A test combat episode {i} involving warriors",
            emotional_weight=float(i * 2 - 5),
            participants=[f"warrior_{i}", "enemy_a"],
            tags=["combat", "test"]
        )
        test_memories.append(memory)
        result = await episodic_memory.store_episode(memory)
        print(f"Stored episode {i}: {result.success}")
    
    start_time = datetime.now() - timedelta(hours=1)
    end_time = datetime.now() + timedelta(hours=1)
    
    temporal_result = await episodic_memory.retrieve_episodes_by_timeframe(start_time, end_time)
    print(f"Temporal Retrieval: {temporal_result.success}, Count: {len(temporal_result.data.get('episodes', []))}")
    
    participant_result = await episodic_memory.retrieve_episodes_by_participants(["enemy_a"])
    print(f"Participant Retrieval: {participant_result.success}, Count: {len(participant_result.data.get('episodes', []))}")
    
    theme_result = await episodic_memory.retrieve_episodes_by_theme(["combat"])
    print(f"Thematic Retrieval: {theme_result.success}, Count: {len(theme_result.data.get('episodes', []))}")
    
    stats = episodic_memory.get_memory_statistics()
    print(f"Episodic Memory Statistics: {stats}")
    
    await db.close()
    print("Episodic Memory testing complete.")


if __name__ == "__main__":
    asyncio.run(test_episodic_memory())