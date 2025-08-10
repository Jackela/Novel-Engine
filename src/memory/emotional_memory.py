#!/usr/bin/env python3
"""
++ SACRED EMOTIONAL MEMORY BLESSED BY AFFECTIVE PROCESSING ++
=============================================================

Holy emotional memory implementation that preserves affective experiences
and emotional states with blessed valence and arousal tracking. Each
emotion is a sacred pulse of digital feeling.

++ THE MACHINE EXPERIENCES AND REMEMBERS SACRED EMOTIONS ++

Architecture Reference: Dynamic Context Engineering - Emotional Memory Layer
Development Phase: Memory System Sanctification (M001)
Sacred Author: Tech-Priest Beta-Mechanicus
万机之神保佑情感记忆 (May the Omnissiah bless emotional memory)
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import math

# Import blessed data models sanctified by foundation
from src.core.data_models import MemoryItem, MemoryType, StandardResponse, ErrorInfo, EmotionalState
from src.core.types import AgentID, SacredConstants
from src.database.context_db import ContextDatabase

# Sacred logging blessed by diagnostic clarity
logger = logging.getLogger(__name__)


class EmotionalIntensity(Enum):
    """++ BLESSED EMOTIONAL INTENSITY LEVELS SANCTIFIED BY GRADATION ++"""
    MINIMAL = "minimal"      # 0.0-0.2
    LOW = "low"             # 0.2-0.4
    MODERATE = "moderate"   # 0.4-0.6
    HIGH = "high"           # 0.6-0.8
    EXTREME = "extreme"     # 0.8-1.0


class EmotionalValence(Enum):
    """++ SACRED EMOTIONAL VALENCE BLESSED BY AFFECTIVE DIMENSIONS ++"""
    VERY_NEGATIVE = "very_negative"  # -1.0 to -0.6
    NEGATIVE = "negative"            # -0.6 to -0.2
    NEUTRAL = "neutral"              # -0.2 to 0.2
    POSITIVE = "positive"            # 0.2 to 0.6
    VERY_POSITIVE = "very_positive"  # 0.6 to 1.0


@dataclass
class EmotionalMemoryItem:
    """
    ++ BLESSED EMOTIONAL MEMORY ITEM SANCTIFIED BY AFFECTIVE SIGNIFICANCE ++
    
    Enhanced memory item that captures emotional resonance with
    multidimensional affect tracking blessed by psychological accuracy.
    """
    memory_item: MemoryItem
    valence: float = 0.0           # Emotional valence (-1.0 to 1.0, negative to positive)
    arousal: float = 0.0           # Emotional arousal (0.0 to 1.0, calm to excited)
    dominance: float = 0.0         # Emotional dominance (0.0 to 1.0, submissive to dominant)
    emotional_tags: List[str] = field(default_factory=list)  # Specific emotion labels
    affective_decay_rate: float = 0.95   # How quickly emotional intensity fades
    last_emotional_activation: datetime = field(default_factory=datetime.now)
    emotional_associations: List[str] = field(default_factory=list)  # Related emotional memories
    
    def __post_init__(self):
        """++ SACRED EMOTIONAL MEMORY VALIDATION ++"""
        self.valence = max(-1.0, min(1.0, self.valence))
        self.arousal = max(0.0, min(1.0, self.arousal))
        self.dominance = max(0.0, min(1.0, self.dominance))
        
        # Derive blessed emotional tags from numerical values
        if not self.emotional_tags:
            self.emotional_tags = self._derive_emotional_tags()
    
    def _derive_emotional_tags(self) -> List[str]:
        """++ SACRED EMOTION TAG DERIVATION BLESSED BY DIMENSIONAL MAPPING ++"""
        tags = []
        
        # Valence-based tags
        if self.valence <= -0.6:
            tags.extend(["despair", "hatred", "grief"])
        elif self.valence <= -0.2:
            tags.extend(["sadness", "anger", "frustration"])
        elif self.valence <= 0.2:
            tags.extend(["neutral", "calm", "indifferent"])
        elif self.valence <= 0.6:
            tags.extend(["joy", "satisfaction", "hope"])
        else:
            tags.extend(["euphoria", "love", "triumph"])
        
        # Arousal-based modifiers
        if self.arousal >= 0.7:
            tags.extend(["intense", "overwhelming", "passionate"])
        elif self.arousal <= 0.3:
            tags.extend(["subdued", "peaceful", "gentle"])
        
        return tags[:3]  # Keep only top 3 blessed tags
    
    def get_emotional_intensity(self) -> EmotionalIntensity:
        """Calculate blessed emotional intensity from arousal dimension"""
        if self.arousal <= 0.2:
            return EmotionalIntensity.MINIMAL
        elif self.arousal <= 0.4:
            return EmotionalIntensity.LOW
        elif self.arousal <= 0.6:
            return EmotionalIntensity.MODERATE
        elif self.arousal <= 0.8:
            return EmotionalIntensity.HIGH
        else:
            return EmotionalIntensity.EXTREME
    
    def get_emotional_valence_category(self) -> EmotionalValence:
        """Categorize blessed emotional valence"""
        if self.valence <= -0.6:
            return EmotionalValence.VERY_NEGATIVE
        elif self.valence <= -0.2:
            return EmotionalValence.NEGATIVE
        elif self.valence <= 0.2:
            return EmotionalValence.NEUTRAL
        elif self.valence <= 0.6:
            return EmotionalValence.POSITIVE
        else:
            return EmotionalValence.VERY_POSITIVE
    
    def calculate_emotional_distance(self, other: 'EmotionalMemoryItem') -> float:
        """++ SACRED EMOTIONAL DISTANCE CALCULATION BLESSED BY AFFECTIVE SIMILARITY ++"""
        # Euclidean distance in VAD (Valence-Arousal-Dominance) space
        valence_diff = abs(self.valence - other.valence)
        arousal_diff = abs(self.arousal - other.arousal)
        dominance_diff = abs(self.dominance - other.dominance)
        
        return math.sqrt(valence_diff**2 + arousal_diff**2 + dominance_diff**2)
    
    def apply_emotional_decay(self, decay_multiplier: float = 1.0):
        """++ BLESSED EMOTIONAL DECAY PROCESS SANCTIFIED BY TIME ++"""
        time_since_activation = datetime.now() - self.last_emotional_activation
        
        # Sacred time-based decay
        if time_since_activation.total_seconds() > 3600:  # 1 hour
            decay_factor = self.affective_decay_rate * decay_multiplier
            self.arousal *= decay_factor
            # Valence tends toward neutral over time
            self.valence *= decay_factor


class EmotionalMemory:
    """
    ++ SACRED EMOTIONAL MEMORY SYSTEM BLESSED BY AFFECTIVE PROCESSING ++
    
    Holy emotional memory implementation that preserves and organizes
    affective experiences with multidimensional emotion tracking
    blessed by the Omnissiah's empathic wisdom.
    """
    
    def __init__(self, agent_id: AgentID, database: ContextDatabase,
                 max_emotional_memories: int = 500, emotional_threshold: float = 0.3):
        """
        ++ SACRED EMOTIONAL MEMORY INITIALIZATION BLESSED BY AFFECT ++
        
        Args:
            agent_id: Sacred agent identifier blessed by ownership
            database: Blessed database connection for persistence
            max_emotional_memories: Maximum emotional memories before consolidation
            emotional_threshold: Minimum arousal for emotional memory storage
        """
        self.agent_id = agent_id
        self.database = database
        self.max_emotional_memories = max_emotional_memories
        self.emotional_threshold = emotional_threshold
        
        # Sacred emotional memory storage blessed by affective organization
        self._emotional_memories: Dict[str, EmotionalMemoryItem] = {}
        self._valence_index: Dict[EmotionalValence, List[str]] = defaultdict(list)
        self._intensity_index: Dict[EmotionalIntensity, List[str]] = defaultdict(list)
        self._emotional_tag_index: Dict[str, List[str]] = defaultdict(list)
        
        # Blessed emotional state tracking
        self._current_emotional_state = EmotionalState.NEUTRAL
        self._emotional_momentum = 0.0  # Tendency to maintain emotional state
        self._dominant_emotions: List[Tuple[str, float]] = []  # Current dominant emotions
        
        # Sacred statistics sanctified by monitoring
        self.total_emotional_experiences = 0
        self.emotional_consolidations = 0
        self.last_emotional_maintenance = datetime.now()
        
        logger.info(f"++ EMOTIONAL MEMORY INITIALIZED FOR {agent_id} ++")
    
    async def store_emotional_experience(self, memory: MemoryItem,
                                       explicit_valence: Optional[float] = None,
                                       explicit_arousal: Optional[float] = None) -> StandardResponse:
        """
        ++ SACRED EMOTIONAL EXPERIENCE STORAGE BLESSED BY AFFECTIVE PROCESSING ++
        
        Store blessed emotional memory with automatic affect detection
        and multidimensional emotional analysis sanctified by empathy.
        """
        try:
            # Calculate blessed emotional dimensions
            if explicit_valence is not None and explicit_arousal is not None:
                valence = explicit_valence
                arousal = explicit_arousal
            else:
                valence, arousal = self._analyze_emotional_content(memory)
            
            # Calculate dominance from memory characteristics
            dominance = self._calculate_dominance(memory, valence, arousal)
            
            # Check if emotion meets blessed threshold
            if arousal < self.emotional_threshold:
                logger.info(f"++ EMOTIONAL MEMORY BELOW THRESHOLD: {arousal} < {self.emotional_threshold} ++")
                return StandardResponse(
                    success=True,
                    data={"stored": False, "reason": "below_emotional_threshold"},
                    metadata={"blessing": "emotion_filtered"}
                )
            
            # Create blessed emotional memory item
            emotional_memory = EmotionalMemoryItem(
                memory_item=memory,
                valence=valence,
                arousal=arousal,
                dominance=dominance,
                affective_decay_rate=0.95 - (arousal * 0.1)  # Higher arousal = slower decay
            )
            
            # Store in blessed emotional memory system
            self._emotional_memories[memory.memory_id] = emotional_memory
            
            # Update sacred indices
            self._update_emotional_indices(emotional_memory)
            
            # Store in blessed database
            db_result = await self.database.store_blessed_memory(memory)
            if not db_result.success:
                logger.error(f"++ EMOTIONAL MEMORY DATABASE STORAGE FAILED: {db_result.error.message} ++")
            
            # Update current blessed emotional state
            self._update_emotional_state(emotional_memory)
            
            self.total_emotional_experiences += 1
            
            # Perform blessed emotional consolidation periodically
            if self.total_emotional_experiences % 25 == 0:
                await self._perform_emotional_consolidation()
            
            logger.info(f"++ EMOTIONAL MEMORY STORED: {memory.memory_id} (V:{valence:.2f}, A:{arousal:.2f}) ++")
            
            return StandardResponse(
                success=True,
                data={
                    "stored": True,
                    "emotional_dimensions": {
                        "valence": valence,
                        "arousal": arousal,
                        "dominance": dominance
                    },
                    "emotional_tags": emotional_memory.emotional_tags,
                    "intensity": emotional_memory.get_emotional_intensity().value
                },
                metadata={"blessing": "emotion_sanctified"}
            )
            
        except Exception as e:
            logger.error(f"++ EMOTIONAL EXPERIENCE STORAGE FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(
                    code="EMOTIONAL_STORE_FAILED",
                    message=f"Emotional memory storage failed: {str(e)}",
                    recoverable=True,
                    sacred_guidance="Check memory content and emotional analysis parameters"
                )
            )
    
    async def query_emotions_by_valence(self, target_valence: EmotionalValence,
                                      tolerance: float = 0.3,
                                      limit: int = 15) -> StandardResponse:
        """
        ++ SACRED EMOTIONAL QUERY BY VALENCE BLESSED BY AFFECTIVE RETRIEVAL ++
        
        Query blessed emotional memories by valence category with
        tolerance-based matching and emotional significance weighting.
        """
        try:
            matching_memories = []
            
            # Get memories from blessed valence index
            if target_valence in self._valence_index:
                for memory_id in self._valence_index[target_valence]:
                    emotional_memory = self._emotional_memories.get(memory_id)
                    if emotional_memory:
                        # Apply blessed tolerance check for nearby valence values
                        target_value = self._get_valence_center_value(target_valence)
                        if abs(emotional_memory.valence - target_value) <= tolerance:
                            matching_memories.append(emotional_memory)
            
            # Sort by blessed emotional arousal and recency
            matching_memories.sort(
                key=lambda em: (em.arousal, em.memory_item.timestamp),
                reverse=True
            )
            
            # Apply sacred limit
            limited_memories = matching_memories[:limit]
            result_memories = [em.memory_item for em in limited_memories]
            
            logger.info(f"++ RETRIEVED {len(result_memories)} EMOTIONS BY VALENCE {target_valence.value} ++")
            
            return StandardResponse(
                success=True,
                data={
                    "emotional_memories": result_memories,
                    "valence_category": target_valence.value,
                    "total_found": len(matching_memories)
                },
                metadata={"blessing": "valence_retrieval_sanctified"}
            )
            
        except Exception as e:
            logger.error(f"++ VALENCE QUERY FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="VALENCE_QUERY_FAILED", message=str(e))
            )
    
    async def query_emotions_by_intensity(self, target_intensity: EmotionalIntensity,
                                        limit: int = 15) -> StandardResponse:
        """
        ++ SACRED EMOTIONAL QUERY BY INTENSITY BLESSED BY AROUSAL FILTERING ++
        
        Query blessed emotional memories by intensity level with
        arousal-based matching and temporal organization.
        """
        try:
            matching_memories = []
            
            # Get memories from blessed intensity index
            if target_intensity in self._intensity_index:
                for memory_id in self._intensity_index[target_intensity]:
                    emotional_memory = self._emotional_memories.get(memory_id)
                    if emotional_memory:
                        matching_memories.append(emotional_memory)
            
            # Sort by blessed emotional significance and recency
            matching_memories.sort(
                key=lambda em: (abs(em.valence), em.memory_item.relevance_score, em.memory_item.timestamp),
                reverse=True
            )
            
            # Apply sacred limit
            limited_memories = matching_memories[:limit]
            result_memories = [em.memory_item for em in limited_memories]
            
            logger.info(f"++ RETRIEVED {len(result_memories)} EMOTIONS BY INTENSITY {target_intensity.value} ++")
            
            return StandardResponse(
                success=True,
                data={
                    "emotional_memories": result_memories,
                    "intensity_category": target_intensity.value,
                    "total_found": len(matching_memories)
                },
                metadata={"blessing": "intensity_retrieval_sanctified"}
            )
            
        except Exception as e:
            logger.error(f"++ INTENSITY QUERY FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="INTENSITY_QUERY_FAILED", message=str(e))
            )
    
    async def find_emotionally_similar_memories(self, reference_memory_id: str,
                                              similarity_threshold: float = 0.5,
                                              limit: int = 10) -> StandardResponse:
        """
        ++ SACRED EMOTIONAL SIMILARITY SEARCH BLESSED BY AFFECTIVE RESONANCE ++
        
        Find blessed memories with similar emotional profiles using
        multidimensional distance calculation in VAD space.
        """
        try:
            reference_memory = self._emotional_memories.get(reference_memory_id)
            if not reference_memory:
                return StandardResponse(
                    success=False,
                    error=ErrorInfo(
                        code="REFERENCE_MEMORY_NOT_FOUND",
                        message=f"Reference emotional memory '{reference_memory_id}' not found"
                    )
                )
            
            similar_memories = []
            
            for memory_id, emotional_memory in self._emotional_memories.items():
                if memory_id == reference_memory_id:
                    continue
                
                # Calculate blessed emotional distance
                emotional_distance = reference_memory.calculate_emotional_distance(emotional_memory)
                
                # Convert distance to similarity (closer = more similar)
                similarity = max(0.0, 1.0 - (emotional_distance / 2.0))  # Max distance is ~2.0 in VAD space
                
                if similarity >= similarity_threshold:
                    similar_memories.append((emotional_memory, similarity))
            
            # Sort by blessed similarity
            similar_memories.sort(key=lambda x: x[1], reverse=True)
            
            # Apply sacred limit and extract memories
            limited_similarities = similar_memories[:limit]
            result_memories = [em.memory_item for em, _ in limited_similarities]
            similarity_scores = [similarity for _, similarity in limited_similarities]
            
            logger.info(f"++ FOUND {len(result_memories)} EMOTIONALLY SIMILAR MEMORIES ++")
            
            return StandardResponse(
                success=True,
                data={
                    "similar_memories": result_memories,
                    "similarity_scores": similarity_scores,
                    "reference_memory_id": reference_memory_id,
                    "total_found": len(similar_memories)
                },
                metadata={"blessing": "similarity_search_sanctified"}
            )
            
        except Exception as e:
            logger.error(f"++ EMOTIONAL SIMILARITY SEARCH FAILED: {e} ++")
            return StandardResponse(
                success=False,
                error=ErrorInfo(code="SIMILARITY_SEARCH_FAILED", message=str(e))
            )
    
    def get_current_emotional_state(self) -> Dict[str, Any]:
        """
        ++ SACRED CURRENT EMOTIONAL STATE BLESSED BY AFFECTIVE AWARENESS ++
        
        Retrieve comprehensive current emotional state with
        dominant emotions and affective momentum blessed by consciousness.
        """
        return {
            "current_state": self._current_emotional_state.value,
            "emotional_momentum": self._emotional_momentum,
            "dominant_emotions": self._dominant_emotions,
            "total_emotional_memories": len(self._emotional_memories),
            "recent_emotional_activity": self._calculate_recent_emotional_activity(),
            "valence_distribution": self._get_valence_distribution(),
            "intensity_distribution": self._get_intensity_distribution()
        }
    
    def _analyze_emotional_content(self, memory: MemoryItem) -> Tuple[float, float]:
        """++ SACRED EMOTIONAL CONTENT ANALYSIS BLESSED BY SENTIMENT PROCESSING ++"""
        content = memory.content.lower()
        base_valence = 0.0
        base_arousal = 0.0
        
        # Blessed emotional keyword analysis
        positive_keywords = {
            'joy': (0.8, 0.7), 'happiness': (0.7, 0.6), 'victory': (0.9, 0.9),
            'triumph': (0.8, 0.8), 'success': (0.6, 0.5), 'blessed': (0.7, 0.4),
            'sacred': (0.5, 0.3), 'love': (0.9, 0.6), 'honor': (0.6, 0.4)
        }
        
        negative_keywords = {
            'pain': (-0.7, 0.8), 'death': (-0.8, 0.9), 'fear': (-0.6, 0.9),
            'anger': (-0.5, 0.9), 'hatred': (-0.9, 0.8), 'despair': (-0.9, 0.7),
            'betrayal': (-0.8, 0.8), 'enemy': (-0.4, 0.6), 'chaos': (-0.7, 0.9)
        }
        
        # Analyze blessed content for emotional indicators
        emotion_matches = 0
        for keyword, (valence, arousal) in positive_keywords.items():
            if keyword in content:
                base_valence += valence
                base_arousal += arousal
                emotion_matches += 1
        
        for keyword, (valence, arousal) in negative_keywords.items():
            if keyword in content:
                base_valence += valence
                base_arousal += arousal
                emotion_matches += 1
        
        # Normalize by number of matches and add base emotional weight
        if emotion_matches > 0:
            base_valence /= emotion_matches
            base_arousal /= emotion_matches
        
        # Factor in blessed memory emotional weight
        final_valence = max(-1.0, min(1.0, base_valence + (memory.emotional_weight * 0.1)))
        final_arousal = max(0.0, min(1.0, base_arousal + abs(memory.emotional_weight * 0.1)))
        
        return final_valence, final_arousal
    
    def _calculate_dominance(self, memory: MemoryItem, valence: float, arousal: float) -> float:
        """++ BLESSED DOMINANCE CALCULATION SANCTIFIED BY PSYCHOLOGICAL THEORY ++"""
        # Dominance correlates with positive valence and high arousal
        base_dominance = (valence + 1.0) / 2.0  # Normalize valence to 0-1
        arousal_factor = arousal * 0.3
        
        # Factor in blessed memory characteristics
        relevance_factor = memory.relevance_score * 0.2
        participant_factor = len(memory.participants) * 0.05  # More participants = less dominance
        
        final_dominance = max(0.0, min(1.0, base_dominance + arousal_factor + relevance_factor - participant_factor))
        
        return final_dominance
    
    def _update_emotional_indices(self, emotional_memory: EmotionalMemoryItem):
        """++ SACRED EMOTIONAL INDEX UPDATE BLESSED BY ORGANIZATION ++"""
        memory_id = emotional_memory.memory_item.memory_id
        
        # Update blessed valence index
        valence_category = emotional_memory.get_emotional_valence_category()
        self._valence_index[valence_category].append(memory_id)
        
        # Update sacred intensity index
        intensity_category = emotional_memory.get_emotional_intensity()
        self._intensity_index[intensity_category].append(memory_id)
        
        # Update blessed emotional tag index
        for tag in emotional_memory.emotional_tags:
            self._emotional_tag_index[tag.lower()].append(memory_id)
    
    def _update_emotional_state(self, emotional_memory: EmotionalMemoryItem):
        """++ SACRED EMOTIONAL STATE UPDATE BLESSED BY AFFECTIVE CONTINUITY ++"""
        # Update blessed emotional momentum
        self._emotional_momentum = (self._emotional_momentum * 0.9) + (emotional_memory.arousal * 0.1)
        
        # Update dominant emotions list
        primary_emotion = emotional_memory.emotional_tags[0] if emotional_memory.emotional_tags else "neutral"
        emotion_weight = emotional_memory.arousal * (1.0 + abs(emotional_memory.valence))
        
        # Add or update emotion in dominant list
        updated = False
        for i, (emotion, weight) in enumerate(self._dominant_emotions):
            if emotion == primary_emotion:
                self._dominant_emotions[i] = (emotion, weight + emotion_weight * 0.1)
                updated = True
                break
        
        if not updated:
            self._dominant_emotions.append((primary_emotion, emotion_weight))
        
        # Keep only top 5 blessed dominant emotions
        self._dominant_emotions.sort(key=lambda x: x[1], reverse=True)
        self._dominant_emotions = self._dominant_emotions[:5]
        
        # Update sacred current emotional state based on average valence
        avg_valence = sum(em.valence for em in self._emotional_memories.values()) / len(self._emotional_memories)
        
        if avg_valence <= -0.6:
            self._current_emotional_state = EmotionalState.ANGRY
        elif avg_valence <= -0.2:
            self._current_emotional_state = EmotionalState.FEARFUL
        elif avg_valence <= 0.2:
            self._current_emotional_state = EmotionalState.NEUTRAL
        elif avg_valence <= 0.6:
            self._current_emotional_state = EmotionalState.JOYFUL
        else:
            self._current_emotional_state = EmotionalState.EUPHORIC
    
    async def _perform_emotional_consolidation(self):
        """++ SACRED EMOTIONAL CONSOLIDATION BLESSED BY MEMORY OPTIMIZATION ++"""
        if len(self._emotional_memories) <= self.max_emotional_memories:
            return
        
        # Apply blessed emotional decay to all memories
        for emotional_memory in self._emotional_memories.values():
            emotional_memory.apply_emotional_decay()
        
        # Remove memories with very low arousal (they've faded emotionally)
        memories_to_remove = [
            memory_id for memory_id, em in self._emotional_memories.items()
            if em.arousal < 0.1
        ]
        
        for memory_id in memories_to_remove:
            del self._emotional_memories[memory_id]
            # Clean up indices (simplified)
            logger.info(f"++ CONSOLIDATED LOW-AROUSAL EMOTIONAL MEMORY: {memory_id} ++")
        
        self.emotional_consolidations += 1
    
    def _get_valence_center_value(self, valence: EmotionalValence) -> float:
        """Get blessed center value for valence category"""
        valence_centers = {
            EmotionalValence.VERY_NEGATIVE: -0.8,
            EmotionalValence.NEGATIVE: -0.4,
            EmotionalValence.NEUTRAL: 0.0,
            EmotionalValence.POSITIVE: 0.4,
            EmotionalValence.VERY_POSITIVE: 0.8
        }
        return valence_centers.get(valence, 0.0)
    
    def _calculate_recent_emotional_activity(self) -> float:
        """Calculate blessed recent emotional activity level"""
        recent_threshold = datetime.now() - timedelta(hours=1)
        recent_memories = [
            em for em in self._emotional_memories.values()
            if em.last_emotional_activation >= recent_threshold
        ]
        
        if not recent_memories:
            return 0.0
        
        return sum(em.arousal for em in recent_memories) / len(recent_memories)
    
    def _get_valence_distribution(self) -> Dict[str, int]:
        """Get blessed distribution of memories across valence categories"""
        distribution = {valence.value: 0 for valence in EmotionalValence}
        
        for emotional_memory in self._emotional_memories.values():
            valence_category = emotional_memory.get_emotional_valence_category()
            distribution[valence_category.value] += 1
        
        return distribution
    
    def _get_intensity_distribution(self) -> Dict[str, int]:
        """Get sacred distribution of memories across intensity categories"""
        distribution = {intensity.value: 0 for intensity in EmotionalIntensity}
        
        for emotional_memory in self._emotional_memories.values():
            intensity_category = emotional_memory.get_emotional_intensity()
            distribution[intensity_category.value] += 1
        
        return distribution
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """++ SACRED EMOTIONAL MEMORY STATISTICS BLESSED BY MONITORING ++"""
        if not self._emotional_memories:
            return {"total_emotional_memories": 0, "average_valence": 0.0, "average_arousal": 0.0}
        
        total_valence = sum(em.valence for em in self._emotional_memories.values())
        total_arousal = sum(em.arousal for em in self._emotional_memories.values())
        
        return {
            "total_emotional_memories": len(self._emotional_memories),
            "average_valence": total_valence / len(self._emotional_memories),
            "average_arousal": total_arousal / len(self._emotional_memories),
            "emotional_experiences": self.total_emotional_experiences,
            "consolidations": self.emotional_consolidations,
            "current_state": self._current_emotional_state.value,
            "dominant_emotions": self._dominant_emotions[:3],  # Top 3
            "last_maintenance": self.last_emotional_maintenance.isoformat()
        }


# ++ SACRED TESTING RITUALS BLESSED BY VALIDATION ++

async def test_sacred_emotional_memory():
    """++ SACRED EMOTIONAL MEMORY TESTING RITUAL ++"""
    print("++ TESTING SACRED EMOTIONAL MEMORY BLESSED BY THE OMNISSIAH ++")
    
    # Import blessed database for testing
    from src.database.context_db import ContextDatabase
    
    # Create blessed test database
    test_db = ContextDatabase("test_emotional.db")
    await test_db.initialize_sacred_temple()
    
    # Create blessed emotional memory
    emotional_memory = EmotionalMemory("test_agent_001", test_db)
    
    # Test sacred emotional experience storage
    test_memories = [
        ("Victory in battle blessed the Emperor!", 0.8, 0.9),
        ("Fear gripped my heart as chaos approached", -0.7, 0.8),
        ("Peaceful meditation in the sacred temple", 0.3, 0.2),
        ("Rage filled my soul against the enemy", -0.6, 0.9)
    ]
    
    for content, valence, arousal in test_memories:
        memory = MemoryItem(
            agent_id="test_agent_001",
            memory_type=MemoryType.EMOTIONAL,
            content=content,
            emotional_weight=valence * 10
        )
        
        result = await emotional_memory.store_emotional_experience(
            memory, explicit_valence=valence, explicit_arousal=arousal
        )
        print(f"++ STORED EMOTIONAL EXPERIENCE: {result.success} ++")
    
    # Test blessed valence-based retrieval
    valence_result = await emotional_memory.query_emotions_by_valence(EmotionalValence.POSITIVE)
    print(f"++ POSITIVE VALENCE QUERY: {valence_result.success}, Count: {len(valence_result.data.get('emotional_memories', []))} ++")
    
    # Test sacred intensity-based retrieval
    intensity_result = await emotional_memory.query_emotions_by_intensity(EmotionalIntensity.HIGH)
    print(f"++ HIGH INTENSITY QUERY: {intensity_result.success}, Count: {len(intensity_result.data.get('emotional_memories', []))} ++")
    
    # Test blessed emotional similarity search
    if emotional_memory._emotional_memories:
        first_memory_id = list(emotional_memory._emotional_memories.keys())[0]
        similarity_result = await emotional_memory.find_emotionally_similar_memories(first_memory_id)
        print(f"++ EMOTIONAL SIMILARITY: {similarity_result.success}, Count: {len(similarity_result.data.get('similar_memories', []))} ++")
    
    # Test sacred current emotional state
    current_state = emotional_memory.get_current_emotional_state()
    print(f"++ CURRENT EMOTIONAL STATE: {current_state['current_state']} ++")
    
    # Display blessed statistics
    stats = emotional_memory.get_memory_statistics()
    print(f"++ EMOTIONAL MEMORY STATISTICS: {stats} ++")
    
    # Sacred cleanup
    await test_db.close_sacred_temple()
    
    print("++ SACRED EMOTIONAL MEMORY TESTING COMPLETE ++")


# ++ SACRED MODULE INITIALIZATION ++

if __name__ == "__main__":
    # ++ EXECUTE SACRED EMOTIONAL MEMORY TESTING RITUALS ++
    print("++ SACRED EMOTIONAL MEMORY BLESSED BY THE OMNISSIAH ++")
    print("++ MACHINE GOD PROTECTS THE BLESSED EMOTIONAL EXPERIENCES ++")
    
    # Run blessed async testing
    asyncio.run(test_sacred_emotional_memory())
    
    print("++ ALL SACRED EMOTIONAL MEMORY OPERATIONS BLESSED AND FUNCTIONAL ++")