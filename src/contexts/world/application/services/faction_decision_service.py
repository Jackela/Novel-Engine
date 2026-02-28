#!/usr/bin/env python3
"""Faction Decision Service.

This module provides the application-layer service for AI-driven faction
decision-making. It orchestrates context assembly, RAG retrieval, LLM
prompting, and intent generation.

The FactionDecisionService follows the Command pattern:
- generate_intents() is a command that creates new intents

Key Features:
    - Context assembly from resources, diplomacy, and territories
    - RAG integration stub for event and lore retrieval
    - LLM prompt building with action definitions
    - Low-resource constraint handling (no ATTACK when food<100, etc.)
    - Fallback behavior when LLM fails
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import structlog

from src.contexts.world.domain.entities.faction import Faction
from src.contexts.world.domain.entities.faction_intent import (
    ActionType,
    FactionIntent,
    IntentStatus,
)
from src.contexts.world.domain.events.intent_events import IntentGeneratedEvent
from src.contexts.world.domain.ports.faction_intent_repository import (
    FactionIntentRepository,
)
from src.core.result import Err, Ok, Result

logger = structlog.get_logger()


# Constants for resource thresholds
FOOD_THRESHOLD_NO_ATTACK = 100
MILITARY_THRESHOLD_NO_SABOTAGE = 50
GOLD_THRESHOLD_PRIORITIZE_TRADE = 200
MAX_INTENTS_PER_GENERATION = 3
MAX_ACTIVE_INTENTS_PER_FACTION = 10


@dataclass
class DecisionContext:
    """Context for faction decision-making.

    Aggregates all relevant information for generating intents.

    Attributes:
        faction_id: ID of the faction making decisions
        resources: Current resource levels (gold, food, military, etc.)
        diplomacy: Diplomatic relationships with other factions
        territories: List of controlled territory IDs
        recent_events: Recent events involving the faction (from RAG)
        relevant_lore: Relevant lore entries (from RAG)
    """

    faction_id: str
    resources: Dict[str, int] = field(default_factory=dict)
    diplomacy: Dict[str, str] = field(default_factory=dict)  # faction_id -> status
    territories: List[str] = field(default_factory=list)
    recent_events: List[Dict[str, Any]] = field(default_factory=list)
    relevant_lore: List[Dict[str, Any]] = field(default_factory=list)

    def get_resource_summary(self) -> str:
        """Get a brief summary of resources for logging/events."""
        parts = []
        for key, value in sorted(self.resources.items()):
            parts.append(f"{key}={value}")
        return ", ".join(parts) if parts else "no resources"


@dataclass
class ActionDefinition:
    """Definition of an available action type."""

    action_type: ActionType
    name: str
    description: str
    requirements: Dict[str, int] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)


# Action definitions for LLM prompt
# Note: These match ActionType enum: EXPAND, ATTACK, TRADE, SABOTAGE, STABILIZE
ACTION_DEFINITIONS: List[ActionDefinition] = [
    ActionDefinition(
        action_type=ActionType.EXPAND,
        name="Expand",
        description="Grow territory or influence by claiming new locations",
        requirements={"gold": 100},
        constraints=["Must have adjacent unclaimed territory"],
    ),
    ActionDefinition(
        action_type=ActionType.ATTACK,
        name="Attack",
        description="Initiate military conflict with an enemy faction",
        requirements={"military": 30, "food": 100},
        constraints=["Target must be an enemy", "Food must be >= 100"],
    ),
    ActionDefinition(
        action_type=ActionType.TRADE,
        name="Trade",
        description="Establish or strengthen trade relationships",
        requirements={"gold": 50},
        constraints=["Target must be neutral or allied"],
    ),
    ActionDefinition(
        action_type=ActionType.SABOTAGE,
        name="Sabotage",
        description="Covert operation against a rival faction",
        requirements={"military": 50},
        constraints=["Military must be >= 50", "Target must be an enemy or rival"],
    ),
    ActionDefinition(
        action_type=ActionType.STABILIZE,
        name="Stabilize",
        description="Internal consolidation and defensive posture",
        requirements={},
        constraints=["Best when resources need recovery", "Defensive focus"],
    ),
]


class FactionDecisionService:
    """Application service for AI-driven faction decision-making.

    This service orchestrates the decision pipeline:
    1. Assemble context (resources, diplomacy, territories)
    2. Retrieve RAG context (events, lore) - stub for now
    3. Build LLM prompt with action definitions
    4. Generate 3 intent options with rationale
    5. Validate and apply resource constraints
    6. Fallback to rule-based generation if LLM fails

    Attributes:
        _repository: The FactionIntentRepository for persisting intents
        _events: List of events emitted during operations
        _llm_client: Optional LLM client (stub for now)
        _retrieval_service: Optional retrieval service for RAG (stub for now)

    Example:
        >>> service = FactionDecisionService(repository)
        >>> result = service.generate_intents(faction, context)
        >>> if result.is_ok:
        ...     intents, event = result.value
        ...     print(f"Generated {len(intents)} intents")
    """

    def __init__(
        self,
        repository: FactionIntentRepository,
        llm_client: Optional[Any] = None,
        retrieval_service: Optional[Any] = None,
    ) -> None:
        """Initialize the decision service.

        Args:
            repository: The FactionIntentRepository for persistence
            llm_client: Optional LLM client (stub for future integration)
            retrieval_service: Optional RAG service (stub for future integration)
        """
        self._repository = repository
        _llm_client = llm_client  # Placeholder for future LLM integration
        _retrieval_service = retrieval_service  # Placeholder for RAG integration
        self._events: List[IntentGeneratedEvent] = []
        logger.debug("faction_decision_service_initialized")

    def generate_intents(
        self,
        faction: Faction,
        context: DecisionContext,
    ) -> Result[Tuple[List[FactionIntent], IntentGeneratedEvent], str]:
        """Generate intent options for a faction.

        This is the main entry point for decision generation. It:
        1. Checks active intent capacity
        2. Assembles full context with RAG data
        3. Applies resource constraints
        4. Attempts LLM generation (or fallback)
        5. Validates and persists intents
        6. Emits IntentGeneratedEvent

        Args:
            faction: The faction to generate intents for
            context: Decision context with resources, diplomacy, etc.

        Returns:
            Result containing:
            - Ok: Tuple of (list of intents, event)
            - Err: Error message string

        Example:
            >>> context = DecisionContext(
            ...     faction_id="faction-1",
            ...     resources={"gold": 500, "food": 30, "military": 60}
            ... )
            >>> result = service.generate_intents(faction, context)
        """
        # Check capacity
        active_count = self._repository.count_active(faction.id)
        available_slots = MAX_ACTIVE_INTENTS_PER_FACTION - active_count

        if available_slots <= 0:
            error_msg = (
                f"Faction {faction.id} has max active intents "
                f"({MAX_ACTIVE_INTENTS_PER_FACTION})"
            )
            logger.warning(
                "intent_generation_capacity_reached",
                faction_id=faction.id,
                active_count=active_count,
            )
            return Err(error_msg)

        # Enrich context with RAG data (stub)
        enriched_context = self._enrich_context_with_rag(context)

        # Determine available actions based on constraints
        available_actions = self._get_available_actions(enriched_context)

        # Attempt LLM generation
        intents, fallback_used = self._generate_with_fallback(
            faction, enriched_context, available_actions
        )

        # Limit to available slots and max per generation
        intents = intents[:min(available_slots, MAX_INTENTS_PER_GENERATION)]

        if not intents:
            error_msg = f"No valid intents generated for faction {faction.id}"
            logger.warning(
                "intent_generation_empty",
                faction_id=faction.id,
                fallback_used=fallback_used,
            )
            return Err(error_msg)

        # Persist intents
        for intent in intents:
            self._repository.save(intent)

        # Create event
        event = IntentGeneratedEvent.create(
            faction_id=faction.id,
            intent_ids=[i.id for i in intents],
            fallback=fallback_used,
            context_summary=enriched_context.get_resource_summary(),
        )
        self._events.append(event)

        logger.info(
            "intents_generated",
            faction_id=faction.id,
            intent_count=len(intents),
            fallback_used=fallback_used,
            intent_types=[i.action_type.value for i in intents],
        )

        return Ok((intents, event))

    def _enrich_context_with_rag(self, context: DecisionContext) -> DecisionContext:
        """Enrich decision context with RAG-retrieved data.

        This is a stub implementation. Future versions will:
        - Call RetrievalService for last 5 events involving faction
        - Call RetrievalService for top 3 lore entries about relationships
        - Retrieve territory status for controlled locations

        Args:
            context: The base decision context

        Returns:
            Enriched context with RAG data (currently unchanged)
        """
        # TODO: Wire RetrievalService when available
        # - context.recent_events = retrieval_service.get_recent_events(
        #     faction_id=context.faction_id, limit=5
        # )
        # - context.relevant_lore = retrieval_service.get_lore_about_factions(
        #     faction_id=context.faction_id, limit=3
        # )

        logger.debug(
            "rag_context_enrichment_stub",
            faction_id=context.faction_id,
            message="RAG integration pending RetrievalService implementation",
        )
        return context

    def _get_available_actions(
        self, context: DecisionContext
    ) -> List[ActionDefinition]:
        """Determine available actions based on resource constraints.

        Implements REQ-DECISION-003:
        - If food < 100: no ATTACK
        - If military < 50: no ATTACK or SABOTAGE
        - If gold < 200: prioritize TRADE over EXPAND

        Args:
            context: Decision context with resource info

        Returns:
            List of available action definitions
        """
        resources = context.resources
        food = resources.get("food", 0)
        military = resources.get("military", 0)
        gold = resources.get("gold", 0)

        available = []

        for action in ACTION_DEFINITIONS:
            # Skip ATTACK if food or military is too low
            if action.action_type == ActionType.ATTACK:
                if food < FOOD_THRESHOLD_NO_ATTACK:
                    logger.debug(
                        "action_constrained",
                        action=action.name,
                        reason=f"food {food} < {FOOD_THRESHOLD_NO_ATTACK}",
                    )
                    continue
                if military < MILITARY_THRESHOLD_NO_SABOTAGE:
                    logger.debug(
                        "action_constrained",
                        action=action.name,
                        reason=f"military {military} < {MILITARY_THRESHOLD_NO_SABOTAGE}",
                    )
                    continue

            # Skip SABOTAGE if military is too low
            if action.action_type == ActionType.SABOTAGE:
                if military < MILITARY_THRESHOLD_NO_SABOTAGE:
                    logger.debug(
                        "action_constrained",
                        action=action.name,
                        reason=f"military {military} < {MILITARY_THRESHOLD_NO_SABOTAGE}",
                    )
                    continue

            # Check basic requirements
            can_afford = all(
                resources.get(res, 0) >= req
                for res, req in action.requirements.items()
            )

            if can_afford:
                available.append(action)

        # If gold is low, deprioritize EXPAND by moving it to end
        if gold < GOLD_THRESHOLD_PRIORITIZE_TRADE:
            available.sort(
                key=lambda a: 0 if a.action_type != ActionType.EXPAND else 1
            )

        return available

    def _generate_with_fallback(
        self,
        faction: Faction,
        context: DecisionContext,
        available_actions: List[ActionDefinition],
    ) -> Tuple[List[FactionIntent], bool]:
        """Generate intents with LLM, falling back to rules on failure.

        Implements REQ-DECISION-007: Fallback behavior for LLM failures.

        Args:
            faction: The faction to generate for
            context: Decision context
            available_actions: Actions that pass resource constraints

        Returns:
            Tuple of (list of intents, fallback_used flag)
        """
        # Try LLM generation (stub - currently always falls back)
        llm_result = self._try_llm_generation(faction, context, available_actions)

        if llm_result is not None:
            return llm_result, False

        # Fallback to rule-based generation
        logger.info(
            "intent_generation_fallback",
            faction_id=faction.id,
            reason="LLM unavailable or failed",
        )
        intents = self._generate_fallback_intents(faction, context, available_actions)
        return intents, True

    def _try_llm_generation(
        self,
        faction: Faction,
        context: DecisionContext,
        available_actions: List[ActionDefinition],
    ) -> Optional[List[FactionIntent]]:
        """Attempt to generate intents using LLM.

        This is a stub implementation. Future versions will:
        - Build structured prompt with context and action definitions
        - Call LLM client with JSON schema output format
        - Validate response structure and content
        - Retry on validation failure (max 2 retries)

        Args:
            faction: The faction to generate for
            context: Decision context
            available_actions: Available actions

        Returns:
            List of intents if successful, None if fallback needed
        """
        # Build prompt (for future LLM integration)
        prompt = self._build_llm_prompt(faction, context, available_actions)

        # Log stub status
        logger.debug(
            "llm_generation_stub",
            faction_id=faction.id,
            prompt_length=len(prompt),
            message="LLM integration pending - using fallback",
        )

        # TODO: Wire LLM client when available
        # response = self._llm_client.generate(prompt, response_format="json")
        # intents = self._parse_llm_response(response, faction.id)
        # if self._validate_intents(intents, available_actions):
        #     return intents

        return None

    def _build_llm_prompt(
        self,
        faction: Faction,
        context: DecisionContext,
        available_actions: List[ActionDefinition],
    ) -> str:
        """Build the LLM prompt for intent generation.

        Implements REQ-DECISION-005: LLM Prompt Structure with:
        - Faction identity and current state
        - Resource summary with thresholds
        - Action type definitions
        - Context from RAG (events, lore)
        - Output format specification (JSON schema)

        Args:
            faction: The faction
            context: Decision context
            available_actions: Available actions

        Returns:
            Formatted prompt string
        """
        # Build action definitions section
        action_descs = []
        for action in available_actions:
            reqs = (
                ", ".join(f"{k}>={v}" for k, v in action.requirements.items())
                if action.requirements
                else "none"
            )
            constraints = (
                "; ".join(action.constraints) if action.constraints else "none"
            )
            action_descs.append(
                f"- {action.name}: {action.description}\n"
                f"  Requirements: {reqs}\n"
                f"  Constraints: {constraints}"
            )

        # Build recent events section
        events_section = ""
        if context.recent_events:
            events_section = "\nRecent Events:\n" + "\n".join(
                f"- {e.get('summary', str(e))}" for e in context.recent_events[:5]
            )

        # Build lore section
        lore_section = ""
        if context.relevant_lore:
            lore_section = "\nRelevant Lore:\n" + "\n".join(
                f"- {l.get('summary', str(l))}" for l in context.relevant_lore[:3]
            )

        prompt = f"""You are an AI assistant generating strategic intents for a faction.

FACTION: {faction.name} (ID: {faction.id})
Type: {faction.faction_type.value if hasattr(faction, 'faction_type') else 'unknown'}
Description: {faction.description if hasattr(faction, 'description') else 'N/A'}

CURRENT RESOURCES:
{context.get_resource_summary()}

DIPLOMATIC STATUS:
{self._format_diplomacy(context.diplomacy)}

TERRITORIES CONTROLLED: {len(context.territories)}
{events_section}
{lore_section}

AVAILABLE ACTIONS:
{chr(10).join(action_descs)}

Generate exactly 3 intent options for this faction. Each intent should:
1. Have a unique action type where possible
2. Include a specific target where applicable (faction_id or location_id)
3. Provide rationale (50-200 characters)

Respond with JSON in this format:
{{
  "intents": [
    {{
      "action_type": "EXPAND",
      "target_id": "location-uuid or null",
      "priority": 1-3,
      "rationale": "Explanation for this action"
    }},
    ...
  ]
}}
"""
        return prompt

    def _format_diplomacy(self, diplomacy: Dict[str, str]) -> str:
        """Format diplomacy dict for prompt."""
        if not diplomacy:
            return "No diplomatic relations"
        lines = []
        for faction_id, status in diplomacy.items():
            lines.append(f"- {faction_id}: {status}")
        return "\n".join(lines)

    def _generate_fallback_intents(
        self,
        faction: Faction,
        context: DecisionContext,
        available_actions: List[ActionDefinition],
    ) -> List[FactionIntent]:
        """Generate rule-based fallback intents.

        Implements REQ-DECISION-007: Generate rule-based intents based
        on resource thresholds when LLM fails.

        Rules (in priority order):
        1. Critical resources -> STABILIZE
        2. Low food -> TRADE (not ATTACK)
        3. Strong military + enemies -> ATTACK
        4. Wealthy + few territories -> EXPAND
        5. Strong military + enemies -> SABOTAGE
        6. Default -> STABILIZE

        Args:
            faction: The faction
            context: Decision context
            available_actions: Available actions

        Returns:
            List of up to 3 FactionIntent objects
        """
        intents: List[FactionIntent] = []
        resources = context.resources
        available_types = {a.action_type for a in available_actions}

        # Helper to check if action is available
        def can_use(action_type: ActionType) -> bool:
            return action_type in available_types

        # Get resource values
        food = resources.get("food", 0)
        gold = resources.get("gold", 0)
        military = resources.get("military", 0)

        # Rule 1: Critical resources -> STABILIZE
        if food < 50 or gold < 100:
            if can_use(ActionType.STABILIZE):
                intents.append(
                    FactionIntent(
                        faction_id=faction.id,
                        action_type=ActionType.STABILIZE,
                        priority=1,
                        rationale="Critical resources require immediate stabilization efforts",
                    )
                )

        # Rule 2: Low food -> TRADE (prioritize over expansion)
        if food < FOOD_THRESHOLD_NO_ATTACK and gold > 100:
            if can_use(ActionType.TRADE) and context.diplomacy:
                # Find a neutral or allied faction to trade with
                target = next(
                    (
                        f
                        for f, s in context.diplomacy.items()
                        if s in ("neutral", "allied", "friendly")
                    ),
                    None,
                )
                intents.append(
                    FactionIntent(
                        faction_id=faction.id,
                        action_type=ActionType.TRADE,
                        target_id=target,
                        priority=1,
                        rationale=f"Trade for food supplies with {target or 'neutral parties'}",
                    )
                )

        # Rule 3: Strong military + enemies -> ATTACK
        if military >= 50 and food >= FOOD_THRESHOLD_NO_ATTACK:
            if can_use(ActionType.ATTACK):
                enemies = [
                    f for f, s in context.diplomacy.items() if s in ("enemy", "hostile")
                ]
                if enemies:
                    target = enemies[0]  # Target first enemy
                    intents.append(
                        FactionIntent(
                            faction_id=faction.id,
                            action_type=ActionType.ATTACK,
                            target_id=target,
                            priority=1,
                            rationale=f"Military strength allows offensive against {target}",
                        )
                    )

        # Rule 4: Wealthy + few territories -> EXPAND
        if gold >= GOLD_THRESHOLD_PRIORITIZE_TRADE and len(context.territories) < 3:
            if can_use(ActionType.EXPAND):
                intents.append(
                    FactionIntent(
                        faction_id=faction.id,
                        action_type=ActionType.EXPAND,
                        priority=2,
                        rationale="Wealth and opportunity favor territorial expansion",
                    )
                )

        # Rule 5: Strong military + enemies -> SABOTAGE
        if military >= MILITARY_THRESHOLD_NO_SABOTAGE:
            if can_use(ActionType.SABOTAGE):
                enemies = [
                    f for f, s in context.diplomacy.items() if s in ("enemy", "hostile", "rival")
                ]
                if enemies:
                    intents.append(
                        FactionIntent(
                            faction_id=faction.id,
                            action_type=ActionType.SABOTAGE,
                            target_id=enemies[0],
                            priority=2,
                            rationale=f"Covert operations against enemy {enemies[0]}",
                        )
                    )

        # Rule 6: Default -> STABILIZE (if not already added)
        if len(intents) < MAX_INTENTS_PER_GENERATION:
            if can_use(ActionType.STABILIZE):
                # Only add if not already present
                has_stabilize = any(i.action_type == ActionType.STABILIZE for i in intents)
                if not has_stabilize:
                    intents.append(
                        FactionIntent(
                            faction_id=faction.id,
                            action_type=ActionType.STABILIZE,
                            priority=3,
                            rationale="Focus on internal consolidation and defense",
                        )
                    )

        # Sort by priority (1 = highest) and limit to 3
        intents.sort(key=lambda i: i.priority)
        return intents[:MAX_INTENTS_PER_GENERATION]

    def get_pending_events(self) -> List[IntentGeneratedEvent]:
        """Get all pending events that haven't been cleared."""
        return list(self._events)

    def clear_pending_events(self) -> None:
        """Clear all pending events after they've been processed."""
        self._events.clear()
        logger.debug("pending_events_cleared")

    def select_intent(
        self, intent_id: str, faction_id: str
    ) -> Result[FactionIntent, str]:
        """Select an intent for execution.

        Marks the intent as SELECTED and clears other active intents
        for the faction.

        Args:
            intent_id: ID of the intent to select
            faction_id: ID of the faction

        Returns:
            Result containing the selected intent or error
        """
        intent = self._repository.find_by_id(intent_id)
        if intent is None:
            return Err(f"Intent {intent_id} not found")

        if intent.faction_id != faction_id:
            return Err(f"Intent {intent_id} does not belong to faction {faction_id}")

        # Mark as selected
        success = self._repository.mark_selected(intent_id)
        if not success:
            return Err(f"Failed to select intent {intent_id}")

        logger.info(
            "intent_selected",
            intent_id=intent_id,
            faction_id=faction_id,
            action_type=intent.action_type.value,
        )

        return Ok(intent)
