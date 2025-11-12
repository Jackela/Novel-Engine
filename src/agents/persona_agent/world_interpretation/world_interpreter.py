"""
World Interpreter
=================

Advanced world event interpretation system for PersonaAgent.
Processes world events through character's subjective lens, considering personality,
biases, knowledge, and factional perspectives.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..protocols import (
    SubjectiveInterpretation,
    ThreatLevel,
    WorldEvent,
)


class InterpretationBias(Enum):
    """Types of interpretation biases characters can exhibit."""

    OPTIMISTIC = "optimistic"  # Tends to see positive aspects
    PESSIMISTIC = "pessimistic"  # Tends to focus on negative aspects
    PARANOID = "paranoid"  # Sees threats everywhere
    NAIVE = "naive"  # Misses subtle implications
    CYNICAL = "cynical"  # Distrusts motives and outcomes
    IDEALISTIC = "idealistic"  # Interprets through ideological lens
    PRAGMATIC = "pragmatic"  # Focuses on practical implications
    EMOTIONAL = "emotional"  # Interpretation colored by emotions


@dataclass
class InterpretationContext:
    """Context information for event interpretation."""

    character_personality: Dict[str, float]
    recent_memories: List[Dict[str, Any]]
    current_emotional_state: str
    factional_beliefs: Dict[str, float]
    knowledge_base: Dict[str, Any]
    relationship_context: Dict[str, float]  # entity_id -> relationship_score
    current_biases: List[InterpretationBias]
    stress_level: float = 0.5  # 0.0 (calm) to 1.0 (extremely stressed)


@dataclass
class MemoryFragment:
    """Represents a stored memory fragment."""

    memory_id: str
    event_id: str
    character_interpretation: str
    emotional_weight: float  # How emotionally significant this memory is
    memory_type: str  # episodic, semantic, procedural
    timestamp: float
    decay_factor: float = 1.0  # How well this memory is retained
    associated_entities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class WorldInterpreter:
    """
    Advanced world event interpretation engine for PersonaAgent.

    Responsibilities:
    - Process world events through character's subjective perspective
    - Apply personality-based interpretation biases
    - Consider character's knowledge, memories, and relationships
    - Generate subjective understanding with emotional responses
    - Update character's worldview based on interpretations
    - Manage relevant memory retrieval and storage
    """

    def __init__(self, character_id: str, logger: Optional[logging.Logger] = None):
        self.character_id = character_id
        self.logger = logger or logging.getLogger(__name__)

        # Memory storage
        self._memory_fragments: List[MemoryFragment] = []
        self._episodic_memories: Dict[str, MemoryFragment] = {}
        self._semantic_knowledge: Dict[str, Any] = {}

        # Worldview and beliefs
        self._worldview: Dict[str, float] = {}  # belief_key -> strength (-1.0 to 1.0)
        self._faction_perceptions: Dict[str, Dict[str, float]] = (
            {}
        )  # faction -> attributes
        self._entity_relationships: Dict[str, float] = (
            {}
        )  # entity_id -> relationship score

        # Interpretation patterns learned over time
        self._interpretation_patterns: Dict[str, Dict[str, Any]] = {}

        # Bias tendencies
        self._bias_tendencies: Dict[InterpretationBias, float] = {
            bias: 0.0 for bias in InterpretationBias
        }

        # Emotional state tracking
        self._emotional_history: List[Dict[str, Any]] = []
        self._current_mood: str = "neutral"

    async def interpret_event(
        self, event: WorldEvent, character_context: Dict[str, Any]
    ) -> SubjectiveInterpretation:
        """
        Interpret a world event from character's subjective perspective.

        Args:
            event: World event to interpret
            character_context: Character's current context and data

        Returns:
            SubjectiveInterpretation: Character's subjective understanding
        """
        try:
            self.logger.debug(
                f"Interpreting event {event.event_id} for character {self.character_id}"
            )

            # Build interpretation context
            context = await self._build_interpretation_context(character_context)

            # Retrieve relevant memories
            await self.get_relevant_memories(
                {"event_type": event.event_type, "entities": event.affected_entities},
                limit=5,
            )

            # Generate base understanding
            base_understanding = await self._generate_base_understanding(event, context)

            # Apply interpretation biases
            biased_understanding = await self._apply_interpretation_biases(
                base_understanding, event, context
            )

            # Determine emotional response
            emotional_response = await self._generate_emotional_response(
                event, biased_understanding, context
            )

            # Calculate belief impacts
            belief_impacts = await self._calculate_belief_impacts(
                event, biased_understanding, context
            )

            # Assess threat level from character's perspective
            threat_assessment = await self._assess_subjective_threat(event, context)

            # Calculate relationship changes
            relationship_changes = await self._calculate_relationship_changes(
                event, biased_understanding, context
            )

            # Determine memory priority
            memory_priority = await self._calculate_memory_priority(
                event, emotional_response, threat_assessment
            )

            # Create interpretation
            interpretation = SubjectiveInterpretation(
                original_event_id=event.event_id,
                character_understanding=biased_understanding,
                emotional_response=emotional_response,
                belief_impact=belief_impacts,
                threat_assessment=threat_assessment,
                relationship_changes=relationship_changes,
                memory_priority=memory_priority,
            )

            # Store as memory if significant enough
            if memory_priority > 0.3:
                await self._store_interpretation_as_memory(interpretation, event)

            self.logger.debug(
                f"Event interpretation completed with threat level: {threat_assessment}"
            )
            return interpretation

        except Exception as e:
            self.logger.error(f"Event interpretation failed: {e}")
            # Return minimal safe interpretation
            return SubjectiveInterpretation(
                original_event_id=event.event_id,
                character_understanding="Something happened, but I'm not sure what to make of it.",
                emotional_response="confused",
                threat_assessment=ThreatLevel.MODERATE,
            )

    async def update_worldview(self, interpretation: SubjectiveInterpretation) -> None:
        """
        Update character's worldview based on event interpretation.

        Args:
            interpretation: Subjective interpretation to incorporate
        """
        try:
            # Update beliefs based on interpretation
            for belief, impact in interpretation.belief_impact.items():
                current_strength = self._worldview.get(belief, 0.0)
                new_strength = current_strength + (
                    impact * 0.1
                )  # Gradual belief change
                self._worldview[belief] = max(-1.0, min(1.0, new_strength))

            # Update relationship scores
            for entity_id, change in interpretation.relationship_changes.items():
                current_score = self._entity_relationships.get(entity_id, 0.0)
                new_score = current_score + (
                    change * 0.05
                )  # Gradual relationship change
                self._entity_relationships[entity_id] = max(-1.0, min(1.0, new_score))

            # Update emotional state
            await self._update_emotional_state(interpretation.emotional_response)

            # Learn from interpretation patterns
            await self._learn_interpretation_pattern(interpretation)

            self.logger.debug(
                f"Worldview updated from interpretation of event {interpretation.original_event_id}"
            )

        except Exception as e:
            self.logger.error(f"Worldview update failed: {e}")

    async def get_relevant_memories(
        self, context: Dict[str, Any], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories for decision making.

        Args:
            context: Context for memory retrieval
            limit: Maximum number of memories to return

        Returns:
            List of relevant memory data
        """
        try:
            relevant_memories = []

            # Search by event type
            event_type = context.get("event_type")
            if event_type:
                for memory in self._memory_fragments:
                    if event_type.lower() in memory.tags:
                        relevant_memories.append(memory)

            # Search by entities
            entities = context.get("entities", [])
            for entity in entities:
                for memory in self._memory_fragments:
                    if entity in memory.associated_entities:
                        relevant_memories.append(memory)

            # Remove duplicates
            unique_memories = {memory.memory_id: memory for memory in relevant_memories}
            relevant_memories = list(unique_memories.values())

            # Sort by relevance (emotional weight * decay factor * recency)
            current_time = datetime.now().timestamp()

            def memory_relevance_score(memory):
                recency = max(
                    0.1, 1.0 - (current_time - memory.timestamp) / (30 * 24 * 3600)
                )  # 30 days
                return memory.emotional_weight * memory.decay_factor * recency

            relevant_memories.sort(key=memory_relevance_score, reverse=True)

            # Convert to dict format and limit
            memory_data = []
            for memory in relevant_memories[:limit]:
                memory_data.append(
                    {
                        "memory_id": memory.memory_id,
                        "description": memory.character_interpretation,
                        "emotional_weight": memory.emotional_weight,
                        "timestamp": memory.timestamp,
                        "tags": memory.tags,
                        "entities": memory.associated_entities,
                    }
                )

            self.logger.debug(f"Retrieved {len(memory_data)} relevant memories")
            return memory_data

        except Exception as e:
            self.logger.error(f"Memory retrieval failed: {e}")
            return []

    async def store_memory(
        self, memory: Dict[str, Any], memory_type: str = "episodic"
    ) -> bool:
        """
        Store a memory in the character's memory system.

        Args:
            memory: Memory data to store
            memory_type: Type of memory (episodic, semantic, procedural)

        Returns:
            bool: True if storage successful
        """
        try:
            memory_id = f"{self.character_id}_memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self._memory_fragments)}"

            memory_fragment = MemoryFragment(
                memory_id=memory_id,
                event_id=memory.get("event_id", "unknown"),
                character_interpretation=memory.get("description", ""),
                emotional_weight=memory.get("emotional_weight", 0.5),
                memory_type=memory_type,
                timestamp=memory.get("timestamp", datetime.now().timestamp()),
                associated_entities=memory.get("entities", []),
                tags=memory.get("tags", []),
            )

            # Store in appropriate collection
            self._memory_fragments.append(memory_fragment)

            if memory_type == "episodic":
                self._episodic_memories[memory_id] = memory_fragment

            # Manage memory capacity
            await self._manage_memory_capacity()

            self.logger.debug(f"Stored {memory_type} memory: {memory_id}")
            return True

        except Exception as e:
            self.logger.error(f"Memory storage failed: {e}")
            return False

    async def get_worldview_summary(self) -> Dict[str, Any]:
        """Get summary of character's current worldview."""
        try:
            # Categorize beliefs
            strong_beliefs = {k: v for k, v in self._worldview.items() if abs(v) > 0.7}
            moderate_beliefs = {
                k: v for k, v in self._worldview.items() if 0.3 < abs(v) <= 0.7
            }

            # Relationship summary
            allies = {k: v for k, v in self._entity_relationships.items() if v > 0.5}
            enemies = {k: v for k, v in self._entity_relationships.items() if v < -0.5}

            # Bias summary
            dominant_biases = [
                bias.value
                for bias, strength in self._bias_tendencies.items()
                if strength > 0.5
            ]

            return {
                "strong_beliefs": strong_beliefs,
                "moderate_beliefs": moderate_beliefs,
                "total_beliefs": len(self._worldview),
                "allies": allies,
                "enemies": enemies,
                "neutral_relationships": len(self._entity_relationships)
                - len(allies)
                - len(enemies),
                "dominant_biases": dominant_biases,
                "current_mood": self._current_mood,
                "memory_count": len(self._memory_fragments),
                "interpretation_patterns": len(self._interpretation_patterns),
            }

        except Exception as e:
            self.logger.error(f"Worldview summary failed: {e}")
            return {"error": str(e)}

    # Private helper methods

    async def _build_interpretation_context(
        self, character_context: Dict[str, Any]
    ) -> InterpretationContext:
        """Build comprehensive interpretation context."""
        try:
            personality = character_context.get("personality", {})
            current_state = character_context.get("state", {})
            faction_info = character_context.get("faction_info", {})

            # Determine current biases based on personality and state
            current_biases = await self._determine_active_biases(
                personality, current_state
            )

            # Get recent memories
            recent_memories = await self.get_relevant_memories(
                {"recent": True}, limit=5
            )

            return InterpretationContext(
                character_personality=personality,
                recent_memories=recent_memories,
                current_emotional_state=current_state.get("emotional_state", "neutral"),
                factional_beliefs=faction_info.get("beliefs", {}),
                knowledge_base=self._semantic_knowledge,
                relationship_context=self._entity_relationships,
                current_biases=current_biases,
                stress_level=current_state.get("stress_level", 0.5),
            )

        except Exception as e:
            self.logger.error(f"Interpretation context building failed: {e}")
            raise

    async def _generate_base_understanding(
        self, event: WorldEvent, context: InterpretationContext
    ) -> str:
        """Generate base understanding of event before applying biases."""
        try:
            # Start with objective description
            base_description = event.description or f"A {event.event_type} occurred"

            # Add context based on character's knowledge
            if event.source in context.knowledge_base:
                source_info = context.knowledge_base[event.source]
                base_description += (
                    f" involving {source_info.get('description', event.source)}"
                )

            # Add location context if relevant
            if event.location and event.location in context.knowledge_base:
                location_info = context.knowledge_base[event.location]
                base_description += (
                    f" at {location_info.get('description', event.location)}"
                )

            # Consider affected entities character knows about
            known_entities = [
                entity
                for entity in event.affected_entities
                if entity in context.relationship_context
            ]

            if known_entities:
                if len(known_entities) == 1:
                    base_description += f" affecting {known_entities[0]}"
                else:
                    base_description += f" affecting {', '.join(known_entities[:-1])} and {known_entities[-1]}"

            return base_description

        except Exception as e:
            self.logger.error(f"Base understanding generation failed: {e}")
            return event.description or "Something happened"

    async def _apply_interpretation_biases(
        self, base_understanding: str, event: WorldEvent, context: InterpretationContext
    ) -> str:
        """Apply character's interpretation biases to base understanding."""
        try:
            biased_understanding = base_understanding

            for bias in context.current_biases:
                if bias == InterpretationBias.OPTIMISTIC:
                    # Look for positive aspects
                    if "victory" in event.event_type or "success" in event.event_type:
                        biased_understanding += ". This could lead to good outcomes."

                elif bias == InterpretationBias.PESSIMISTIC:
                    # Focus on negative implications
                    if "battle" in event.event_type or "conflict" in event.event_type:
                        biased_understanding += ". This will likely lead to suffering."

                elif bias == InterpretationBias.PARANOID:
                    # See hidden threats
                    if (
                        event.source not in context.relationship_context
                        or context.relationship_context[event.source] < 0.5
                    ):
                        biased_understanding += (
                            ". There may be hidden motives behind this."
                        )

                elif bias == InterpretationBias.CYNICAL:
                    # Distrust motives
                    biased_understanding += (
                        ". Someone is probably benefiting from this at others' expense."
                    )

                elif bias == InterpretationBias.NAIVE:
                    # Miss subtle implications
                    biased_understanding = base_understanding  # Keep it simple

                elif bias == InterpretationBias.IDEALISTIC:
                    # View through ideological lens
                    faction_beliefs = context.factional_beliefs
                    if (
                        "justice" in faction_beliefs
                        and faction_beliefs["justice"] > 0.5
                    ):
                        biased_understanding += (
                            ". This is either just or unjust, no middle ground."
                        )

            return biased_understanding

        except Exception as e:
            self.logger.debug(f"Bias application failed: {e}")
            return base_understanding

    async def _generate_emotional_response(
        self, event: WorldEvent, understanding: str, context: InterpretationContext
    ) -> str:
        """Generate character's emotional response to the event."""
        try:
            # Base emotional response on event type
            event_emotions = {
                "battle": ["fearful", "angry", "determined"],
                "victory": ["proud", "elated", "satisfied"],
                "defeat": ["disappointed", "angry", "worried"],
                "discovery": ["curious", "excited", "cautious"],
                "death": ["sad", "shocked", "angry"],
                "betrayal": ["angry", "hurt", "disappointed"],
            }

            possible_emotions = event_emotions.get(
                event.event_type, ["neutral", "curious"]
            )

            # Modify based on relationships
            if event.source in context.relationship_context:
                relationship_score = context.relationship_context[event.source]
                if relationship_score > 0.5:  # Ally
                    if "battle" in event.event_type:
                        possible_emotions = ["concerned", "supportive", "worried"]
                elif relationship_score < -0.5:  # Enemy
                    if "victory" in understanding.lower():
                        possible_emotions = ["satisfied", "vindicated", "pleased"]

            # Consider personality traits
            personality = context.character_personality
            if personality.get("aggression", 0.5) > 0.7:
                if "angry" not in possible_emotions and any(
                    word in understanding.lower()
                    for word in ["attack", "threat", "enemy"]
                ):
                    possible_emotions.append("angry")

            if personality.get("loyalty", 0.5) > 0.7:
                if any(
                    entity in event.affected_entities
                    for entity in context.relationship_context
                    if context.relationship_context[entity] > 0.5
                ):
                    possible_emotions = ["protective", "concerned", "determined"]

            # Select primary emotion based on stress level
            if context.stress_level > 0.7:
                stress_emotions = ["anxious", "overwhelmed", "panicked"]
                primary_emotion = stress_emotions[0]
            else:
                # Choose first emotion from possible list (could be randomized)
                primary_emotion = (
                    possible_emotions[0] if possible_emotions else "neutral"
                )

            return primary_emotion

        except Exception as e:
            self.logger.debug(f"Emotional response generation failed: {e}")
            return "confused"

    async def _calculate_belief_impacts(
        self, event: WorldEvent, understanding: str, context: InterpretationContext
    ) -> Dict[str, float]:
        """Calculate how the event impacts character's beliefs."""
        try:
            belief_impacts = {}

            # Example belief impacts based on event types
            if event.event_type == "victory":
                if (
                    event.source in context.relationship_context
                    and context.relationship_context[event.source] > 0.5
                ):
                    belief_impacts["allies_are_strong"] = 0.2
                    belief_impacts["justice_prevails"] = 0.1

            elif event.event_type == "betrayal":
                belief_impacts["people_are_trustworthy"] = -0.3
                belief_impacts["loyalty_matters"] = 0.2

            elif event.event_type == "death":
                belief_impacts["life_is_precious"] = 0.1
                belief_impacts["world_is_dangerous"] = 0.2

            # Factor in character's existing beliefs and personality
            for belief, impact in belief_impacts.items():
                # Stronger personalities have stronger belief changes
                personality_strength = sum(
                    abs(v) for v in context.character_personality.values()
                ) / len(context.character_personality)
                belief_impacts[belief] = impact * personality_strength

            return belief_impacts

        except Exception as e:
            self.logger.debug(f"Belief impact calculation failed: {e}")
            return {}

    async def _assess_subjective_threat(
        self, event: WorldEvent, context: InterpretationContext
    ) -> ThreatLevel:
        """Assess threat level from character's subjective perspective."""
        try:
            base_threat = ThreatLevel.NEGLIGIBLE

            # Direct threats
            if self.character_id in event.affected_entities:
                if "attack" in event.event_type or "battle" in event.event_type:
                    base_threat = ThreatLevel.HIGH
                elif "injury" in event.event_type:
                    base_threat = ThreatLevel.MODERATE

            # Threats to allies
            allies = [
                entity
                for entity, relationship in context.relationship_context.items()
                if relationship > 0.5
            ]

            if any(ally in event.affected_entities for ally in allies):
                if base_threat == ThreatLevel.NEGLIGIBLE:
                    base_threat = ThreatLevel.LOW

            # Factional threats
            if (
                event.source in context.relationship_context
                and context.relationship_context[event.source] < -0.3
            ):
                # Hostile entity involved
                if base_threat == ThreatLevel.NEGLIGIBLE:
                    base_threat = ThreatLevel.LOW
                else:
                    # Escalate existing threat
                    threat_levels = list(ThreatLevel)
                    current_index = threat_levels.index(base_threat)
                    if current_index < len(threat_levels) - 1:
                        base_threat = threat_levels[current_index + 1]

            # Apply interpretation biases
            for bias in context.current_biases:
                if bias == InterpretationBias.PARANOID:
                    # Escalate threat level
                    threat_levels = list(ThreatLevel)
                    current_index = threat_levels.index(base_threat)
                    if current_index < len(threat_levels) - 1:
                        base_threat = threat_levels[current_index + 1]

                elif bias == InterpretationBias.NAIVE:
                    # Reduce threat level
                    threat_levels = list(ThreatLevel)
                    current_index = threat_levels.index(base_threat)
                    if current_index > 0:
                        base_threat = threat_levels[current_index - 1]

            return base_threat

        except Exception as e:
            self.logger.debug(f"Subjective threat assessment failed: {e}")
            return ThreatLevel.MODERATE

    async def _calculate_relationship_changes(
        self, event: WorldEvent, understanding: str, context: InterpretationContext
    ) -> Dict[str, float]:
        """Calculate how the event affects relationships."""
        try:
            relationship_changes = {}

            # Direct actions by entities
            if "attack" in event.event_type:
                if event.source != self.character_id:
                    # Someone attacked
                    if self.character_id in event.affected_entities:
                        # Attacked me
                        relationship_changes[event.source] = -0.3
                    else:
                        # Attacked someone else
                        for entity in event.affected_entities:
                            if (
                                entity in context.relationship_context
                                and context.relationship_context[entity] > 0.5
                            ):
                                # Attacked my ally
                                relationship_changes[event.source] = -0.2

            elif "help" in event.event_type or "rescue" in event.event_type:
                if self.character_id in event.affected_entities:
                    # Someone helped me
                    relationship_changes[event.source] = 0.2

            # Shared experiences
            if (
                len(event.affected_entities) > 1
                and self.character_id in event.affected_entities
            ):
                # Shared experience with others
                for entity in event.affected_entities:
                    if entity != self.character_id:
                        if "victory" in event.event_type:
                            relationship_changes[entity] = (
                                0.1  # Bonding through shared victory
                            )
                        elif "defeat" in event.event_type:
                            relationship_changes[entity] = (
                                0.05  # Small bonding through shared hardship
                            )

            return relationship_changes

        except Exception as e:
            self.logger.debug(f"Relationship change calculation failed: {e}")
            return {}

    async def _calculate_memory_priority(
        self, event: WorldEvent, emotional_response: str, threat_level: ThreatLevel
    ) -> float:
        """Calculate how likely this event is to be remembered."""
        try:
            priority = 0.5  # Base priority

            # Emotional intensity increases memory priority
            high_emotion_responses = [
                "angry",
                "fearful",
                "elated",
                "shocked",
                "devastated",
            ]
            if emotional_response in high_emotion_responses:
                priority += 0.3

            # Threat level increases memory priority
            threat_bonuses = {
                ThreatLevel.NEGLIGIBLE: 0.0,
                ThreatLevel.LOW: 0.1,
                ThreatLevel.MODERATE: 0.2,
                ThreatLevel.HIGH: 0.3,
                ThreatLevel.CRITICAL: 0.4,
            }
            priority += threat_bonuses.get(threat_level, 0.0)

            # Personal involvement increases memory priority
            if self.character_id in event.affected_entities:
                priority += 0.2

            # Unique or rare events are more memorable
            similar_events = len(
                [
                    memory
                    for memory in self._memory_fragments
                    if event.event_type in memory.tags
                ]
            )
            if similar_events < 3:  # Rare event type
                priority += 0.15

            return max(0.0, min(1.0, priority))

        except Exception as e:
            self.logger.debug(f"Memory priority calculation failed: {e}")
            return 0.5

    async def _determine_active_biases(
        self, personality: Dict[str, float], current_state: Dict[str, Any]
    ) -> List[InterpretationBias]:
        """Determine which interpretation biases are currently active."""
        try:
            active_biases = []

            # Personality-based biases
            personality.get("aggression", 0.5)
            optimism = personality.get("optimism", 0.5)
            paranoia = personality.get("paranoia", 0.5)
            intelligence = personality.get("intelligence", 0.5)

            if optimism > 0.7:
                active_biases.append(InterpretationBias.OPTIMISTIC)
            elif optimism < 0.3:
                active_biases.append(InterpretationBias.PESSIMISTIC)

            if paranoia > 0.6:
                active_biases.append(InterpretationBias.PARANOID)

            if intelligence < 0.4:
                active_biases.append(InterpretationBias.NAIVE)
            elif intelligence > 0.8:
                active_biases.append(InterpretationBias.PRAGMATIC)

            # State-based biases
            stress_level = current_state.get("stress_level", 0.5)
            if stress_level > 0.7:
                active_biases.append(InterpretationBias.EMOTIONAL)

            morale = current_state.get("morale_level", 0.5)
            if morale < 0.3:
                active_biases.append(InterpretationBias.CYNICAL)

            return active_biases

        except Exception as e:
            self.logger.debug(f"Bias determination failed: {e}")
            return [InterpretationBias.PRAGMATIC]  # Safe default

    async def _store_interpretation_as_memory(
        self, interpretation: SubjectiveInterpretation, event: WorldEvent
    ) -> None:
        """Store interpretation as a memory fragment."""
        try:
            memory_data = {
                "event_id": event.event_id,
                "description": interpretation.character_understanding,
                "emotional_weight": interpretation.memory_priority,
                "timestamp": event.timestamp,
                "entities": event.affected_entities,
                "tags": [event.event_type, interpretation.emotional_response],
            }

            await self.store_memory(memory_data, "episodic")

        except Exception as e:
            self.logger.debug(f"Memory storage failed: {e}")

    async def _update_emotional_state(self, new_emotion: str) -> None:
        """Update character's emotional state."""
        try:
            # Record emotional history
            emotion_record = {
                "emotion": new_emotion,
                "timestamp": datetime.now().timestamp(),
                "previous_mood": self._current_mood,
            }
            self._emotional_history.append(emotion_record)

            # Update current mood
            self._current_mood = new_emotion

            # Keep emotional history limited
            if len(self._emotional_history) > 50:
                self._emotional_history = self._emotional_history[-25:]

        except Exception as e:
            self.logger.debug(f"Emotional state update failed: {e}")

    async def _learn_interpretation_pattern(
        self, interpretation: SubjectiveInterpretation
    ) -> None:
        """Learn from interpretation patterns for future use."""
        try:
            # This is a placeholder for machine learning or pattern recognition
            # that could improve interpretation quality over time
            pass

        except Exception as e:
            self.logger.debug(f"Pattern learning failed: {e}")

    async def _manage_memory_capacity(self) -> None:
        """Manage memory capacity by removing old/irrelevant memories."""
        try:
            max_memories = 1000  # Configurable limit

            if len(self._memory_fragments) > max_memories:
                # Sort by relevance (emotional_weight * decay_factor * recency)
                current_time = datetime.now().timestamp()

                def memory_importance(memory):
                    age_days = (current_time - memory.timestamp) / (24 * 3600)
                    recency_factor = max(
                        0.1, 1.0 - (age_days / 365)
                    )  # Decay over a year
                    return (
                        memory.emotional_weight * memory.decay_factor * recency_factor
                    )

                # Keep the most important memories
                self._memory_fragments.sort(key=memory_importance, reverse=True)
                removed_count = len(self._memory_fragments) - max_memories
                self._memory_fragments = self._memory_fragments[:max_memories]

                self.logger.debug(
                    f"Removed {removed_count} old memories to manage capacity"
                )

        except Exception as e:
            self.logger.debug(f"Memory capacity management failed: {e}")
