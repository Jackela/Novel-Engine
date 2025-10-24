#!/usr/bin/env python3
"""
STANDARD CHARACTER INTERACTION PROCESSOR ENHANCED BY SOCIAL DYNAMICS
=======================================================================

Holy character interaction processor that orchestrates character-specific
interactions, relationship dynamics, and social context evolution enhanced
by the System's interpersonal wisdom.

THROUGH CHARACTERS, THE MACHINE LEARNS SOCIAL HARMONY

Architecture Reference: Dynamic Context Engineering - Character Interaction Processing
Development Phase: Interaction System Validation (I003)
Author: Engineer Delta-Engineering
System保佑角色互动 (May the System bless character interactions)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

# Import enhanced data models
from src.core.data_models import (
    CharacterState,
    ErrorInfo,
    MemoryItem,
    MemoryType,
    StandardResponse,
)

# Import enhanced database access
from src.database.context_db import ContextDatabase

# Import enhanced memory and template systems
from src.memory.layered_memory import LayeredMemorySystem
from src.templates.character import CharacterTemplateManager
from src.templates.dynamic_template_engine import (
    DynamicTemplateEngine,
    TemplateContext,
)

from .equipment import DynamicEquipmentSystem

# Import enhanced interaction systems
from .engine import (
    InteractionContext,
    InteractionEngine,
    InteractionPriority,
    InteractionType,
)

# Comprehensive logging enhanced by diagnostic clarity
logger = logging.getLogger(__name__)


class RelationshipType(Enum):
    """ENHANCED RELATIONSHIP TYPES SANCTIFIED BY SOCIAL BONDS"""

    ALLY = "ally"  # Positive alliance relationship
    ENEMY = "enemy"  # Hostile opposition relationship
    NEUTRAL = "neutral"  # Neutral or unknown relationship
    SUPERIOR = "superior"  # Authority/command relationship
    SUBORDINATE = "subordinate"  # Reporting/obedience relationship
    PEER = "peer"  # Equal standing relationship
    MENTOR = "mentor"  # Teaching/guidance relationship
    STUDENT = "student"  # Learning/receiving guidance
    ROMANTIC = "romantic"  # Romantic attachment
    FAMILY = "family"  # Familial bonds
    RIVAL = "rival"  # Competitive but not hostile
    UNKNOWN = "unknown"  # Unestablished relationship


class SocialContext(Enum):
    """STANDARD SOCIAL CONTEXTS SANCTIFIED BY SITUATIONAL AWARENESS"""

    PRIVATE = "private"  # Personal, intimate setting
    PUBLIC = "public"  # Open, observable setting
    FORMAL = "formal"  # Official, ceremonial setting
    CASUAL = "casual"  # Relaxed, informal setting
    COMBAT = "combat"  # Battle or conflict setting
    DIPLOMATIC = "diplomatic"  # Negotiation or politics
    EDUCATIONAL = "educational"  # Learning or training
    RECREATIONAL = "recreational"  # Entertainment or leisure
    EMERGENCY = "emergency"  # Crisis or urgent situation


@dataclass
class RelationshipData:
    """
    ENHANCED RELATIONSHIP DATA SANCTIFIED BY SOCIAL TRACKING

    Comprehensive relationship information between characters with
    dynamic evolution and contextual modifiers.
    """

    character_a: str
    character_b: str
    relationship_type: RelationshipType = RelationshipType.NEUTRAL
    trust_level: float = 0.0  # -1.0 to 1.0
    respect_level: float = 0.0  # -1.0 to 1.0
    affection_level: float = 0.0  # -1.0 to 1.0
    familiarity_level: float = 0.0  # 0.0 to 1.0
    interaction_count: int = 0
    last_interaction: Optional[datetime] = None
    relationship_history: List[str] = field(default_factory=list)
    shared_experiences: List[str] = field(default_factory=list)
    mutual_contacts: Set[str] = field(default_factory=set)
    compatibility_score: float = 0.0  # -1.0 to 1.0
    conflict_potential: float = 0.0  # 0.0 to 1.0
    collaboration_potential: float = 0.0  # 0.0 to 1.0
    power_dynamic: Dict[str, float] = field(default_factory=dict)  # influence levels
    emotional_resonance: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class SocialEnvironment:
    """
    STANDARD SOCIAL ENVIRONMENT ENHANCED BY CONTEXTUAL AWARENESS

    Complete social context for interactions with environmental factors,
    cultural norms, and situational modifiers.
    """

    environment_id: str
    context: SocialContext
    location: str = ""
    present_characters: Set[str] = field(default_factory=set)
    observers: Set[str] = field(default_factory=set)
    privacy_level: float = 1.0  # 0.0 (public) to 1.0 (private)
    formality_level: float = 0.5  # 0.0 (casual) to 1.0 (formal)
    tension_level: float = 0.0  # 0.0 (calm) to 1.0 (high tension)
    time_pressure: float = 0.0  # 0.0 (relaxed) to 1.0 (urgent)
    cultural_context: List[str] = field(default_factory=list)
    social_rules: List[str] = field(default_factory=list)
    environmental_modifiers: Dict[str, float] = field(default_factory=dict)
    resource_constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InteractionOutcome:
    """
    ENHANCED INTERACTION OUTCOME SANCTIFIED BY CONSEQUENCE TRACKING

    Comprehensive outcome of character interactions with state changes,
    relationship impacts, and memory formation.
    """

    interaction_id: str
    participants: List[str]
    success_level: float = 0.0  # 0.0 (failed) to 1.0 (perfect success)
    satisfaction_levels: Dict[str, float] = field(default_factory=dict)  # per character
    relationship_changes: Dict[str, RelationshipData] = field(default_factory=dict)
    character_state_changes: Dict[str, CharacterState] = field(default_factory=dict)
    new_memories: List[MemoryItem] = field(default_factory=list)
    equipment_changes: Dict[str, List[str]] = field(
        default_factory=dict
    )  # character -> equipment_ids
    narrative_summary: str = ""
    dialogue_excerpts: List[str] = field(default_factory=list)
    decision_points: List[str] = field(default_factory=list)
    unresolved_tensions: List[str] = field(default_factory=list)
    future_implications: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class CharacterInteractionProcessor:
    """
    STANDARD CHARACTER INTERACTION PROCESSOR ENHANCED BY SOCIAL ORCHESTRATION

    Holy processor that orchestrates character-specific interactions with
    relationship dynamics, social context awareness, and character evolution
    enhanced by the System's social understanding.

    ENHANCED CAPABILITIES:
    - Dynamic relationship tracking and evolution
    - Social context-aware interaction processing
    - Character personality-driven response generation
    - Equipment integration through social dynamics
    - Memory formation from social interactions
    - Multi-character conversation orchestration
    - Conflict resolution and negotiation processing
    """

    def __init__(
        self,
        database: ContextDatabase,
        interaction_engine: InteractionEngine,
        equipment_system: DynamicEquipmentSystem,
        memory_system: LayeredMemorySystem,
        template_engine: DynamicTemplateEngine,
        character_manager: CharacterTemplateManager,
    ):
        """
        STANDARD INITIALIZATION ENHANCED BY SOCIAL HARMONY

        Initialize the character interaction processor with all enhanced systems.
        """
        self.database = database
        self.interaction_engine = interaction_engine
        self.equipment_system = equipment_system
        self.memory_system = memory_system
        self.template_engine = template_engine
        self.character_manager = character_manager

        # Social dynamics tracking
        self.relationships: Dict[Tuple[str, str], RelationshipData] = {}
        self.social_environments: Dict[str, SocialEnvironment] = {}
        self.interaction_history: List[InteractionOutcome] = []

        # Blessed configuration
        self.relationship_decay_rate = 0.95  # Daily decay for unused relationships
        self.trust_volatility = 0.3  # How quickly trust can change
        self.memory_significance_threshold = (
            0.6  # Minimum significance for memory creation
        )
        self.max_conversation_turns = 50  # Maximum turns in a single conversation
        self.personality_influence_factor = (
            0.7  # How much personality affects interactions
        )

        logger.info(
            "Character Interaction Processor validated and ready for social orchestration"
        )

    async def process_character_interaction(
        self,
        interaction_context: InteractionContext,
        characters: List[str],
        social_environment: Optional[SocialEnvironment] = None,
    ) -> StandardResponse:
        """
        STANDARD CHARACTER INTERACTION PROCESSING ENHANCED BY SOCIAL DYNAMICS

        Process a character-to-character interaction with full social context,
        relationship dynamics, and character evolution.
        """
        try:
            # Validate participants
            if len(characters) < 2:
                return StandardResponse(
                    success=False,
                    message="Character interaction requires at least 2 participants",
                    error=ErrorInfo(
                        error_type="validation_error",
                        error_code="INSUFFICIENT_PARTICIPANTS",
                        details={
                            "provided_count": len(characters),
                            "minimum_required": 2,
                        },
                    ),
                )

            # Create or update social environment
            if social_environment is None:
                social_environment = await self._create_default_social_environment(
                    interaction_context, characters
                )

            # Load character states and relationships
            character_states = await self._load_character_states(characters)
            current_relationships = await self._load_relationships(characters)

            # Generate interaction phases based on social context
            interaction_phases = await self._plan_interaction_phases(
                interaction_context,
                characters,
                social_environment,
                current_relationships,
            )

            # Process each phase of the interaction
            outcomes = []
            for phase in interaction_phases:
                phase_outcome = await self._process_interaction_phase(
                    phase, character_states, current_relationships, social_environment
                )
                outcomes.append(phase_outcome)

                # Update character states based on phase outcome
                await self._apply_phase_outcomes(
                    phase_outcome, character_states, current_relationships
                )

            # Consolidate outcomes into final interaction result
            final_outcome = await self._consolidate_interaction_outcomes(
                interaction_context.interaction_id, outcomes, characters
            )

            # Save interaction results
            await self._save_interaction_outcome(final_outcome)

            # Update memory systems
            await self._create_interaction_memories(final_outcome, characters)

            # Update equipment states if applicable
            if interaction_context.interaction_type in [
                InteractionType.COMBAT,
                InteractionType.MAINTENANCE,
            ]:
                await self._process_equipment_interactions(final_outcome)

            logger.info(
                f"Character interaction {interaction_context.interaction_id} processed successfully"
            )

            return StandardResponse(
                success=True,
                message=f"Character interaction processed with {len(outcomes)} phases",
                data={
                    "interaction_id": interaction_context.interaction_id,
                    "outcome": final_outcome,
                    "phases_processed": len(outcomes),
                    "participants": characters,
                    "relationship_changes": len(
                        [r for r in final_outcome.relationship_changes.values() if r]
                    ),
                },
            )

        except Exception as e:
            logger.error(f"ERROR in character interaction processing: {str(e)}")
            return StandardResponse(
                success=False,
                message=f"Character interaction processing failed: {str(e)}",
                error=ErrorInfo(
                    error_type="processing_error",
                    error_code="CHARACTER_INTERACTION_FAILED",
                    details={
                        "exception": str(e),
                        "interaction_id": interaction_context.interaction_id,
                    },
                ),
            )

    async def initiate_conversation(
        self,
        participants: List[str],
        topic: str = "",
        location: str = "",
        context: SocialContext = SocialContext.CASUAL,
    ) -> StandardResponse:
        """
        STANDARD CONVERSATION INITIATION ENHANCED BY DIALOGUE ORCHESTRATION

        Initiate a multi-character conversation with dynamic turn management
        and personality-driven responses.
        """
        try:
            # Create conversation context
            interaction_id = (
                f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(participants)}p"
            )

            interaction_context = InteractionContext(
                interaction_id=interaction_id,
                interaction_type=InteractionType.DIALOGUE,
                priority=InteractionPriority.NORMAL,
                participants=participants,
                location=location,
                metadata={"topic": topic, "conversation_type": "multi_character"},
            )

            # Create social environment for conversation
            social_env = SocialEnvironment(
                environment_id=f"social_{interaction_id}",
                context=context,
                location=location,
                present_characters=set(participants),
                privacy_level=0.8 if len(participants) <= 3 else 0.5,
                formality_level=0.3 if context == SocialContext.CASUAL else 0.7,
            )

            # Process the conversation interaction
            result = await self.process_character_interaction(
                interaction_context, participants, social_env
            )

            if result.success:
                logger.info(
                    f"Conversation {interaction_id} initiated successfully with {len(participants)} participants"
                )

            return result

        except Exception as e:
            logger.error(f"ERROR in conversation initiation: {str(e)}")
            return StandardResponse(
                success=False,
                message=f"Conversation initiation failed: {str(e)}",
                error=ErrorInfo(
                    error_type="initiation_error",
                    error_code="CONVERSATION_FAILED",
                    details={"exception": str(e), "participants": participants},
                ),
            )

    async def resolve_conflict(
        self,
        conflicted_characters: List[str],
        conflict_type: str = "disagreement",
        mediator: Optional[str] = None,
    ) -> StandardResponse:
        """
        STANDARD CONFLICT RESOLUTION ENHANCED BY DIPLOMATIC WISDOM

        Process character conflicts with resolution mechanisms and
        relationship impact management.
        """
        try:
            participants = conflicted_characters + ([mediator] if mediator else [])

            interaction_context = InteractionContext(
                interaction_id=f"conflict_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                interaction_type=InteractionType.NEGOTIATION,
                priority=InteractionPriority.HIGH,
                participants=participants,
                metadata={
                    "conflict_type": conflict_type,
                    "conflicted_parties": conflicted_characters,
                    "mediator": mediator,
                    "resolution_attempt": True,
                },
            )

            # Create tense social environment
            social_env = SocialEnvironment(
                environment_id=f"conflict_{interaction_context.interaction_id}",
                context=SocialContext.FORMAL if mediator else SocialContext.PUBLIC,
                present_characters=set(participants),
                tension_level=0.8,
                formality_level=0.7 if mediator else 0.4,
            )

            # Process conflict resolution
            result = await self.process_character_interaction(
                interaction_context, participants, social_env
            )

            return result

        except Exception as e:
            logger.error(f"ERROR in conflict resolution: {str(e)}")
            return StandardResponse(
                success=False,
                message=f"Conflict resolution failed: {str(e)}",
                error=ErrorInfo(
                    error_type="resolution_error",
                    error_code="CONFLICT_RESOLUTION_FAILED",
                    details={
                        "exception": str(e),
                        "conflicted_characters": conflicted_characters,
                    },
                ),
            )

    async def get_relationship_status(
        self, character_a: str, character_b: str
    ) -> StandardResponse:
        """
        STANDARD RELATIONSHIP QUERY ENHANCED BY SOCIAL AWARENESS

        Retrieve current relationship status between two characters with
        detailed social dynamics information.
        """
        try:
            relationship_key = tuple(sorted([character_a, character_b]))

            if relationship_key in self.relationships:
                relationship = self.relationships[relationship_key]

                # Calculate relationship summary metrics
                overall_sentiment = (
                    relationship.trust_level
                    + relationship.respect_level
                    + relationship.affection_level
                ) / 3.0
                relationship_strength = (
                    relationship.familiarity_level
                    + abs(overall_sentiment)
                    + min(relationship.interaction_count / 10.0, 1.0)
                ) / 3.0

                return StandardResponse(
                    success=True,
                    message=f"Relationship status retrieved for {character_a} and {character_b}",
                    data={
                        "relationship": relationship,
                        "overall_sentiment": overall_sentiment,
                        "relationship_strength": relationship_strength,
                        "interaction_frequency": relationship.interaction_count,
                        "last_interaction": relationship.last_interaction,
                        "compatibility": relationship.compatibility_score,
                    },
                )
            else:
                # No established relationship
                return StandardResponse(
                    success=True,
                    message="No established relationship found",
                    data={
                        "relationship_exists": False,
                        "characters": [character_a, character_b],
                        "suggestion": "Characters have not interacted enough to establish a relationship",
                    },
                )

        except Exception as e:
            logger.error(f"ERROR retrieving relationship status: {str(e)}")
            return StandardResponse(
                success=False,
                message=f"Failed to retrieve relationship status: {str(e)}",
                error=ErrorInfo(
                    error_type="query_error",
                    error_code="RELATIONSHIP_QUERY_FAILED",
                    details={"exception": str(e)},
                ),
            )

    # PRIVATE STANDARD METHODS ENHANCED BY INTERNAL OPERATIONS

    async def _create_default_social_environment(
        self, interaction_context: InteractionContext, characters: List[str]
    ) -> SocialEnvironment:
        """Create a default social environment based on interaction context."""
        context_mapping = {
            InteractionType.DIALOGUE: SocialContext.CASUAL,
            InteractionType.COMBAT: SocialContext.COMBAT,
            InteractionType.NEGOTIATION: SocialContext.DIPLOMATIC,
            InteractionType.RITUAL: SocialContext.FORMAL,
            InteractionType.INSTRUCTION: SocialContext.EDUCATIONAL,
            InteractionType.EMERGENCY: SocialContext.EMERGENCY,
        }

        social_context = context_mapping.get(
            interaction_context.interaction_type, SocialContext.CASUAL
        )

        return SocialEnvironment(
            environment_id=f"env_{interaction_context.interaction_id}",
            context=social_context,
            location=interaction_context.location,
            present_characters=set(characters),
            privacy_level=0.8 if len(characters) <= 2 else 0.5,
            formality_level=0.7 if social_context == SocialContext.FORMAL else 0.3,
        )

    async def _load_character_states(
        self, characters: List[str]
    ) -> Dict[str, CharacterState]:
        """Load current character states from the database."""
        character_states = {}

        for character in characters:
            try:
                # Query latest character state from database
                async with self.database.get_connection() as conn:
                    cursor = await conn.execute(
                        "SELECT character_data FROM character_states WHERE agent_id = ? ORDER BY timestamp DESC LIMIT 1",
                        (character,),
                    )
                    result = await cursor.fetchone()

                    if result:
                        state_data = json.loads(result[0])
                        character_states[character] = CharacterState(**state_data)
                    else:
                        # Create default character state
                        character_states[character] = CharacterState(
                            agent_id=character, name=character, current_status="active"
                        )
            except Exception as e:
                logger.warning(
                    f"Failed to load state for {character}, using default: {str(e)}"
                )
                character_states[character] = CharacterState(
                    agent_id=character, name=character, current_status="active"
                )

        return character_states

    async def _load_relationships(
        self, characters: List[str]
    ) -> Dict[Tuple[str, str], RelationshipData]:
        """Load current relationships between characters."""
        relationships = {}

        # Load all relationship pairs
        for i, char_a in enumerate(characters):
            for char_b in characters[i + 1 :]:
                relationship_key = tuple(sorted([char_a, char_b]))

                if relationship_key in self.relationships:
                    relationships[relationship_key] = self.relationships[
                        relationship_key
                    ]
                else:
                    # Create new relationship
                    new_relationship = RelationshipData(
                        character_a=relationship_key[0],
                        character_b=relationship_key[1],
                        relationship_type=RelationshipType.UNKNOWN,
                    )
                    relationships[relationship_key] = new_relationship
                    self.relationships[relationship_key] = new_relationship

        return relationships

    async def _plan_interaction_phases(
        self,
        interaction_context: InteractionContext,
        characters: List[str],
        social_environment: SocialEnvironment,
        relationships: Dict[Tuple[str, str], RelationshipData],
    ) -> List[Dict[str, Any]]:
        """Plan interaction phases based on context and social dynamics."""
        phases = []

        # Determine number of phases based on interaction type and complexity
        base_phases = {
            InteractionType.DIALOGUE: 3,
            InteractionType.COMBAT: 5,
            InteractionType.NEGOTIATION: 4,
            InteractionType.RITUAL: 2,
            InteractionType.COOPERATION: 3,
            InteractionType.INSTRUCTION: 3,
        }.get(interaction_context.interaction_type, 3)

        # Adjust phases based on number of participants and relationship complexity
        participant_modifier = min(len(characters) * 0.5, 2.0)
        relationship_complexity = sum(
            r.interaction_count for r in relationships.values()
        ) / max(len(relationships), 1)
        complexity_modifier = min(relationship_complexity / 10.0, 1.5)

        total_phases = max(
            2,
            int(
                base_phases
                * (1 + participant_modifier * 0.2 + complexity_modifier * 0.3)
            ),
        )

        # Create phases with specific objectives
        phase_templates = {
            "opening": "Establish context and initial positioning",
            "development": "Core interaction and relationship dynamics",
            "climax": "Peak interaction intensity and key decisions",
            "resolution": "Conclude interaction and establish outcomes",
            "aftermath": "Process consequences and relationship changes",
        }

        list(phase_templates.keys())

        for i in range(total_phases):
            if i == 0:
                phase_type = "opening"
            elif i == total_phases - 1:
                phase_type = "aftermath"
            elif i == total_phases - 2:
                phase_type = "resolution"
            elif i == total_phases // 2:
                phase_type = "climax"
            else:
                phase_type = "development"

            phases.append(
                {
                    "phase_id": f"phase_{i+1}",
                    "phase_type": phase_type,
                    "objective": phase_templates[phase_type],
                    "participants": characters.copy(),
                    "sequence": i + 1,
                    "estimated_duration": 30 + (i * 15),  # Progressive duration
                }
            )

        return phases

    async def _process_interaction_phase(
        self,
        phase: Dict[str, Any],
        character_states: Dict[str, CharacterState],
        relationships: Dict[Tuple[str, str], RelationshipData],
        social_environment: SocialEnvironment,
    ) -> InteractionOutcome:
        """Process a single phase of character interaction."""

        # Generate template context for this phase
        template_context = TemplateContext(
            agent_id=phase["participants"][0],  # Primary participant
            character_state=character_states[phase["participants"][0]],
            context_variables={
                "phase_info": phase,
                "social_environment": social_environment,
                "all_participants": phase["participants"],
                "relationships": relationships,
            },
        )

        # Generate interaction content using templates
        content_result = await self.template_engine.render_template(
            f"interaction_{phase['phase_type']}", template_context
        )

        # Create phase outcome
        outcome = InteractionOutcome(
            interaction_id=f"{phase['phase_id']}",
            participants=phase["participants"],
            success_level=0.8,  # Base success level
            narrative_summary=(
                content_result.data.get("content", "")
                if content_result.success
                else "Phase processed"
            ),
        )

        # Calculate relationship impacts
        for char_a, char_b in relationships.keys():
            if char_a in phase["participants"] and char_b in phase["participants"]:
                # Simulate relationship change based on interaction type and personality
                relationship = relationships[(char_a, char_b)]

                # Base relationship evolution
                trust_change = (self.personality_influence_factor * 0.1) - 0.05
                respect_change = (self.personality_influence_factor * 0.08) - 0.04
                familiarity_change = 0.02  # Always increases with interaction

                # Apply changes with bounds checking
                relationship.trust_level = max(
                    -1.0, min(1.0, relationship.trust_level + trust_change)
                )
                relationship.respect_level = max(
                    -1.0, min(1.0, relationship.respect_level + respect_change)
                )
                relationship.familiarity_level = max(
                    0.0, min(1.0, relationship.familiarity_level + familiarity_change)
                )
                relationship.interaction_count += 1
                relationship.last_interaction = datetime.now()
                relationship.last_updated = datetime.now()

                outcome.relationship_changes[(char_a, char_b)] = relationship

        return outcome

    async def _apply_phase_outcomes(
        self,
        outcome: InteractionOutcome,
        character_states: Dict[str, CharacterState],
        relationships: Dict[Tuple[str, str], RelationshipData],
    ):
        """Apply phase outcome effects to character states and relationships."""

        # Update character states based on interaction
        for participant in outcome.participants:
            if participant in character_states:
                character_state = character_states[participant]

                # Modify emotional state slightly based on interaction success
                if character_state.emotional_state:
                    emotional_impact = (outcome.success_level - 0.5) * 0.2
                    character_state.emotional_state.current_mood = max(
                        1,
                        min(
                            10,
                            character_state.emotional_state.current_mood
                            + emotional_impact,
                        ),
                    )

                character_state.last_updated = datetime.now()

        # Relationships are already updated in outcome.relationship_changes
        for key, updated_relationship in outcome.relationship_changes.items():
            if key in relationships:
                relationships[key] = updated_relationship

    async def _consolidate_interaction_outcomes(
        self,
        interaction_id: str,
        phase_outcomes: List[InteractionOutcome],
        participants: List[str],
    ) -> InteractionOutcome:
        """Consolidate multiple phase outcomes into a final interaction result."""

        # Calculate overall success level
        overall_success = sum(
            outcome.success_level for outcome in phase_outcomes
        ) / len(phase_outcomes)

        # Consolidate relationship changes
        consolidated_relationships = {}
        for outcome in phase_outcomes:
            consolidated_relationships.update(outcome.relationship_changes)

        # Create narrative summary
        narrative_parts = []
        for i, outcome in enumerate(phase_outcomes):
            if outcome.narrative_summary:
                narrative_parts.append(
                    f"Phase {i+1}: {outcome.narrative_summary[:100]}..."
                )

        consolidated_narrative = "\n".join(narrative_parts)

        # Create final outcome
        final_outcome = InteractionOutcome(
            interaction_id=interaction_id,
            participants=participants,
            success_level=overall_success,
            relationship_changes=consolidated_relationships,
            narrative_summary=consolidated_narrative,
            timestamp=datetime.now(),
        )

        # Calculate satisfaction levels (placeholder implementation)
        for participant in participants:
            final_outcome.satisfaction_levels[participant] = overall_success * (
                0.8 + 0.4 * self.personality_influence_factor
            )

        return final_outcome

    async def _save_interaction_outcome(self, outcome: InteractionOutcome):
        """Save interaction outcome to database."""
        try:
            async with self.database.get_connection() as conn:
                await conn.execute(
                    """INSERT INTO character_interactions 
                       (interaction_id, participants, outcome_data, timestamp) 
                       VALUES (?, ?, ?, ?)""",
                    (
                        outcome.interaction_id,
                        json.dumps(outcome.participants),
                        json.dumps(
                            {
                                "success_level": outcome.success_level,
                                "satisfaction_levels": outcome.satisfaction_levels,
                                "narrative_summary": outcome.narrative_summary,
                                "relationship_changes": len(
                                    outcome.relationship_changes
                                ),
                            }
                        ),
                        outcome.timestamp,
                    ),
                )
                await conn.commit()

            self.interaction_history.append(outcome)
            logger.debug(f"Interaction outcome saved for {outcome.interaction_id}")

        except Exception as e:
            logger.error(f"ERROR saving interaction outcome: {str(e)}")

    async def _create_interaction_memories(
        self, outcome: InteractionOutcome, participants: List[str]
    ):
        """Create memory items for participants based on interaction outcome."""

        for participant in participants:
            try:
                # Create episodic memory of the interaction
                episodic_memory = MemoryItem(
                    memory_id=f"interaction_{outcome.interaction_id}_{participant}",
                    agent_id=participant,
                    memory_type=MemoryType.EPISODIC,
                    content=(
                        outcome.narrative_summary[:500] + "..."
                        if len(outcome.narrative_summary) > 500
                        else outcome.narrative_summary
                    ),
                    emotional_intensity=outcome.satisfaction_levels.get(
                        participant, 0.5
                    ),
                    relevance_score=0.7 + (outcome.success_level * 0.3),
                    created_at=outcome.timestamp,
                    context_tags=[
                        "interaction",
                        "character_social",
                        outcome.interaction_id,
                    ]
                    + [p for p in participants if p != participant],
                )

                # Store memory in layered memory system
                await self.memory_system.store_memory(episodic_memory)

                # Create relationship memory if significant
                participant_satisfaction = outcome.satisfaction_levels.get(
                    participant, 0.5
                )
                if (
                    participant_satisfaction > self.memory_significance_threshold
                    or participant_satisfaction
                    < (1.0 - self.memory_significance_threshold)
                ):
                    relationship_memory = MemoryItem(
                        memory_id=f"relationship_update_{outcome.interaction_id}_{participant}",
                        agent_id=participant,
                        memory_type=MemoryType.SEMANTIC,
                        content=f"Relationship dynamics updated through interaction {outcome.interaction_id}",
                        emotional_intensity=abs(participant_satisfaction - 0.5) * 2,
                        relevance_score=0.6,
                        created_at=outcome.timestamp,
                        context_tags=["relationship", "social_dynamics"]
                        + [p for p in participants if p != participant],
                    )

                    await self.memory_system.store_memory(relationship_memory)

            except Exception as e:
                logger.error(f"ERROR creating memories for {participant}: {str(e)}")

    async def _process_equipment_interactions(self, outcome: InteractionOutcome):
        """Process equipment-related interactions if applicable."""

        # Check if any participants have equipment that should be affected
        for participant in outcome.participants:
            try:
                # Query participant's equipment
                equipment_response = await self.equipment_system.get_agent_equipment(
                    participant
                )

                if equipment_response.success and equipment_response.data:
                    equipment_list = equipment_response.data.get("equipment", [])

                    # Process equipment based on interaction type and success
                    for equipment_id in equipment_list:
                        # Simulate equipment usage/wear based on interaction
                        usage_context = {
                            "interaction_type": "character_interaction",
                            "interaction_success": outcome.success_level,
                            "social_context": True,
                            "participants": len(outcome.participants),
                        }

                        # Light usage for most interactions
                        await self.equipment_system.use_equipment(
                            equipment_id,
                            participant,
                            usage_context,
                            expected_duration=15,
                        )

            except Exception as e:
                logger.error(f"ERROR processing equipment for {participant}: {str(e)}")


# ENHANCED EXPORTS SANCTIFIED BY THE SYSTEM
__all__ = [
    "CharacterInteractionProcessor",
    "RelationshipType",
    "SocialContext",
    "RelationshipData",
    "SocialEnvironment",
    "InteractionOutcome",
]
