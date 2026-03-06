#!/usr/bin/env python3
"""FactionIntentGenerator Service.

This module provides the FactionIntentGenerator service for generating faction
intents based on world state, faction characteristics, and diplomatic relations.
Uses rule-based decision logic to determine strategic actions.

Note: This is a legacy rule-based generator. For AI-driven decision making,
use FactionDecisionService which supports LLM integration and RAG context.

Typical usage example:
    >>> from src.contexts.world.application.services import FactionIntentGenerator
    >>> from src.contexts.world.domain.entities import Faction
    >>> generator = FactionIntentGenerator()
    >>> result = generator.generate_intents(faction, world, diplomacy)
    >>> if result.is_ok:
    ...     intents = result.value

Result Pattern:
    All public methods return Result[T, Error] for explicit error handling.
"""

from typing import Any, Dict, List, Optional

from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.domain.entities.faction import Faction, FactionStatus
from src.contexts.world.domain.entities.faction_intent import (
    ActionType,
    FactionIntent,
)
from src.contexts.world.domain.errors import IntentGenerationError
from src.core.result import Err, Error, Ok, Result


class FactionIntentGenerator:
    """Service for generating faction intents based on world state.

    Uses rule-based decision logic to determine what actions a faction
    should consider taking. Rules are evaluated in priority order, and
    the first matching rule for each category generates an intent.

    The generator returns up to 3 intents per faction, sorted by priority
    (1 = highest priority, ascending order).

    Attributes:
        MAX_INTENTS: Maximum number of intents to return per faction.

    Example:
        >>> generator = FactionIntentGenerator()
        >>> intents = generator.generate_intents(faction, world, diplomacy)
        >>> if intents:
        ...     print(f"Top priority: {intents[0].action_type.value}")
    """

    MAX_INTENTS = 3

    def generate_intents(
        self,
        faction: Faction,
        world: WorldState,
        diplomacy: DiplomacyMatrix,
    ) -> Result[List[FactionIntent], Error]:
        """Generate intents for a faction based on world state.

        Analyzes faction resources, diplomatic relations, and world context
        to determine strategic intents. Returns at most MAX_INTENTS sorted
        by priority (ascending, 1 = highest).

        Args:
            faction: The faction to generate intents for.
            world: Current world state (used for context, though most
                decisions are based on faction and diplomacy).
            diplomacy: Diplomatic relations matrix for checking allies/enemies.

        Returns:
            Result containing:
            - Ok: List of FactionIntent objects, sorted by priority ascending.
                  Returns empty list if faction is collapsed or no valid intents.
            - Err: Error if generation fails

        Example:
            >>> result = generator.generate_intents(faction, world, diplomacy)
            >>> if result.is_ok:
            ...     intents = result.value
            ...     for intent in intents:
            ...         print(f"{intent.action_type.value}: {intent.rationale}")
        """
        try:
            # Edge case: Collapsed factions have no intents
            if faction.status == FactionStatus.DISBANDED:
                return Ok([])

            intents: List[FactionIntent] = []

            # Rule 1: Critical resources - STABILIZE
            if faction.economic_power < 20:
                intents.append(
                    FactionIntent(
                        faction_id=faction.id,
                        action_type=ActionType.STABILIZE,
                        priority=1,
                        rationale="Recover economic stability",
                    )
                )

            # Rule 2: Attack weakest enemy if significantly stronger
            attack_intent = self._try_generate_attack_intent(faction, diplomacy)
            if attack_intent:
                intents.append(attack_intent)

            # Rule 3: Seek trade opportunities
            trade_intent = self._try_generate_trade_intent(faction, diplomacy)
            if trade_intent:
                intents.append(trade_intent)

            # Rule 4: Expand if few territories and wealthy
            expand_intent = self._try_generate_expand_intent(faction, world)
            if expand_intent:
                intents.append(expand_intent)

            # Rule 5: Sabotage enemies if military is strong
            sabotage_intent = self._try_generate_sabotage_intent(faction, diplomacy)
            if sabotage_intent:
                intents.append(sabotage_intent)

            # Rule 6: Default - STABILIZE (only if no other intents)
            if not intents:
                intents.append(
                    FactionIntent(
                        faction_id=faction.id,
                        action_type=ActionType.STABILIZE,
                        priority=3,
                        rationale="Focus on internal affairs",
                    )
                )

            # Sort by priority ascending (1 = highest) and limit to MAX_INTENTS
            intents.sort(key=lambda i: i.priority)
            return Ok(intents[: self.MAX_INTENTS])
        except Exception as e:
            return Err(
                IntentGenerationError(
                    f"Failed to generate intents for faction {faction.id}: {e}",
                    details={"faction_id": faction.id, "faction_name": faction.name},
                )
            )

    def _try_generate_attack_intent(
        self,
        faction: Faction,
        diplomacy: DiplomacyMatrix,
    ) -> Optional[FactionIntent]:
        """Try to generate an ATTACK intent.

        Conditions:
            - Faction has enemies
            - Military strength >= 30

        Args:
            faction: The faction to check.
            diplomacy: Diplomatic relations matrix.

        Returns:
            FactionIntent if conditions met, None otherwise.
        """
        enemies = diplomacy.get_enemies(faction.id)

        if not enemies:
            return None

        if faction.military_strength < 30:
            return None

        target_id = enemies[0]  # Target first enemy
        return FactionIntent(
            faction_id=faction.id,
            action_type=ActionType.ATTACK,
            target_id=target_id,
            priority=1,
            rationale="Launch offensive against enemy faction",
        )

    def _try_generate_trade_intent(
        self,
        faction: Faction,
        diplomacy: DiplomacyMatrix,
    ) -> Optional[FactionIntent]:
        """Try to generate a TRADE intent.

        Conditions:
            - Faction has neutral parties to trade with
            - Faction has wealth > 40

        Args:
            faction: The faction to check.
            diplomacy: Diplomatic relations matrix.

        Returns:
            FactionIntent if conditions met, None otherwise.
        """
        if faction.economic_power <= 40:
            return None

        neutrals = diplomacy.get_neutral(faction.id)

        if not neutrals:
            return None

        target_id = neutrals[0]
        return FactionIntent(
            faction_id=faction.id,
            action_type=ActionType.TRADE,
            target_id=target_id,
            priority=2,
            rationale="Establish trade with neutral faction",
        )

    def _try_generate_expand_intent(
        self,
        faction: Faction,
        world: WorldState,
    ) -> Optional[FactionIntent]:
        """Try to generate an EXPAND intent.

        Conditions:
            - Fewer than 3 territories
            - Wealth > 50

        Args:
            faction: The faction to check.
            world: World state (for finding adjacent unclaimed locations).

        Returns:
            FactionIntent if conditions met, None otherwise.
        """
        if len(faction.territories) >= 3:
            return None

        if faction.economic_power <= 50:
            return None

        return FactionIntent(
            faction_id=faction.id,
            action_type=ActionType.EXPAND,
            target_id=None,  # No specific target - resolved during simulation
            priority=2,
            rationale="Expand into new territory",
        )

    def _try_generate_sabotage_intent(
        self,
        faction: Faction,
        diplomacy: DiplomacyMatrix,
    ) -> Optional[FactionIntent]:
        """Try to generate a SABOTAGE intent.

        Conditions:
            - Military > 50
            - Has enemies

        Args:
            faction: The faction to check.
            diplomacy: Diplomatic relations matrix.

        Returns:
            FactionIntent if conditions met, None otherwise.
        """
        if faction.military_strength <= 50:
            return None

        enemies = diplomacy.get_enemies(faction.id)
        if not enemies:
            return None

        faction.territories[0] if faction.territories else None

        return FactionIntent(
            faction_id=faction.id,
            action_type=ActionType.SABOTAGE,
            target_id=enemies[0],
            priority=2,
            rationale="Covert operations against enemy",
        )
