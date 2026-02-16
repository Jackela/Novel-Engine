#!/usr/bin/env python3
"""FactionIntentGenerator Service.

This module provides the FactionIntentGenerator service for generating faction
intents based on world state, faction characteristics, and diplomatic relations.
Uses rule-based decision logic to determine strategic actions.

Typical usage example:
    >>> from src.contexts.world.application.services import FactionIntentGenerator
    >>> from src.contexts.world.domain.entities import Faction
    >>> generator = FactionIntentGenerator()
    >>> intents = generator.generate_intents(faction, world, diplomacy)
"""

from typing import List, Optional

from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.aggregates.world_state import WorldState
from src.contexts.world.domain.entities.faction import Faction, FactionStatus
from src.contexts.world.domain.entities.faction_intent import (
    FactionIntent,
    IntentType,
)


class FactionIntentGenerator:
    """Service for generating faction intents based on world state.

    Uses rule-based decision logic to determine what actions a faction
    should consider taking. Rules are evaluated in priority order, and
    the first matching rule for each category generates an intent.

    The generator returns up to 3 intents per faction, sorted by priority
    (descending, so highest priority first).

    Attributes:
        MAX_INTENTS: Maximum number of intents to return per faction.

    Example:
        >>> generator = FactionIntentGenerator()
        >>> intents = generator.generate_intents(faction, world, diplomacy)
        >>> if intents:
        ...     print(f"Top priority: {intents[0].intent_type.value}")
    """

    MAX_INTENTS = 3

    def generate_intents(
        self,
        faction: Faction,
        world: WorldState,
        diplomacy: DiplomacyMatrix,
    ) -> List[FactionIntent]:
        """Generate intents for a faction based on world state.

        Analyzes faction resources, diplomatic relations, and world context
        to determine strategic intents. Returns at most MAX_INTENTS sorted
        by priority (descending).

        Args:
            faction: The faction to generate intents for.
            world: Current world state (used for context, though most
                decisions are based on faction and diplomacy).
            diplomacy: Diplomatic relations matrix for checking allies/enemies.

        Returns:
            List of FactionIntent objects, sorted by priority descending.
            Returns empty list if faction is collapsed or no valid intents.

        Example:
            >>> intents = generator.generate_intents(faction, world, diplomacy)
            >>> for intent in intents:
            ...     print(f"{intent.intent_type.value}: {intent.narrative}")
        """
        # Edge case: Collapsed factions have no intents
        if faction.status == FactionStatus.DISBANDED:
            return []

        intents: List[FactionIntent] = []

        # Rule 1: Critical resources - RECOVER
        if faction.economic_power < 20:
            intents.append(
                FactionIntent(
                    faction_id=faction.id,
                    intent_type=IntentType.RECOVER,
                    priority=9,
                    narrative="Recover economic stability",
                )
            )

        # Rule 2: Attack weakest enemy if significantly weaker
        attack_intent = self._try_generate_attack_intent(faction, diplomacy)
        if attack_intent:
            intents.append(attack_intent)

        # Rule 3: Seek alliance if isolated and wealthy
        ally_intent = self._try_generate_ally_intent(faction, diplomacy)
        if ally_intent:
            intents.append(ally_intent)

        # Rule 4: Expand if few territories and wealthy
        expand_intent = self._try_generate_expand_intent(faction, world)
        if expand_intent:
            intents.append(expand_intent)

        # Rule 5: Defend if military is strong and has enemies
        defend_intent = self._try_generate_defend_intent(faction, diplomacy)
        if defend_intent:
            intents.append(defend_intent)

        # Rule 6: Default - CONSOLIDATE (only if no other intents)
        if not intents:
            intents.append(
                FactionIntent(
                    faction_id=faction.id,
                    intent_type=IntentType.CONSOLIDATE,
                    priority=1,
                    narrative="Focus on internal affairs",
                )
            )

        # Sort by priority descending and limit to MAX_INTENTS
        intents.sort(key=lambda i: i.priority, reverse=True)
        return intents[: self.MAX_INTENTS]

    def _try_generate_attack_intent(
        self,
        faction: Faction,
        diplomacy: DiplomacyMatrix,
    ) -> Optional[FactionIntent]:
        """Try to generate an ATTACK intent.

        Conditions:
            - Faction has enemies
            - Strongest enemy has military < 50% of faction's military

        Args:
            faction: The faction to check.
            diplomacy: Diplomatic relations matrix.

        Returns:
            FactionIntent if conditions met, None otherwise.
        """
        enemies = diplomacy.get_enemies(faction.id)

        if not enemies:
            return None

        # Find strongest enemy (by military strength - would need faction lookup)
        # For now, we target the first enemy since we don't have access to
        # all faction data here. The service would need a faction repository
        # to look up enemy military strengths.
        # For the MVP, we assume we can attack if we have enemies and our
        # military is strong enough (> 30).
        if faction.military_strength < 30:
            return None

        target_id = enemies[0]  # Target first enemy
        return FactionIntent(
            faction_id=faction.id,
            intent_type=IntentType.ATTACK,
            target_id=target_id,
            priority=7,
            narrative=f"Launch offensive against enemy faction",
        )

    def _try_generate_ally_intent(
        self,
        faction: Faction,
        diplomacy: DiplomacyMatrix,
    ) -> Optional[FactionIntent]:
        """Try to generate an ALLY intent.

        Conditions:
            - Faction has no allies
            - Faction has wealth > 40

        Args:
            faction: The faction to check.
            diplomacy: Diplomatic relations matrix.

        Returns:
            FactionIntent if conditions met, None otherwise.
        """
        allies = diplomacy.get_allies(faction.id)

        # Already has allies
        if allies:
            return None

        # Not wealthy enough to pursue alliances
        if faction.economic_power <= 40:
            return None

        # Find wealthiest neutral faction
        neutrals = diplomacy.get_neutral(faction.id)

        if not neutrals:
            return None

        # For MVP, pick first neutral faction (would need faction repo to find wealthiest)
        target_id = neutrals[0]
        return FactionIntent(
            faction_id=faction.id,
            intent_type=IntentType.ALLY,
            target_id=target_id,
            priority=6,
            narrative=f"Seek alliance with neutral faction",
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

        Note:
            For MVP, we don't have a way to find adjacent unclaimed locations
            without a location repository. This method returns an intent with
            target_id=None if expansion is possible but no specific target found.
        """
        if len(faction.territories) >= 3:
            return None

        if faction.economic_power <= 50:
            return None

        # For MVP, we don't have access to location data to find unclaimed
        # territories. Return an expand intent without a specific target.
        # The simulation service would resolve this by picking an available location.
        return FactionIntent(
            faction_id=faction.id,
            intent_type=IntentType.EXPAND,
            target_id=None,  # No specific target - resolved during simulation
            priority=5,
            narrative="Expand into new territory",
        )

    def _try_generate_defend_intent(
        self,
        faction: Faction,
        diplomacy: DiplomacyMatrix,
    ) -> Optional[FactionIntent]:
        """Try to generate a DEFEND intent.

        Conditions:
            - Military > 80
            - Has enemies

        Args:
            faction: The faction to check.
            diplomacy: Diplomatic relations matrix.

        Returns:
            FactionIntent if conditions met, None otherwise.
        """
        if faction.military_strength <= 80:
            return None

        enemies = diplomacy.get_enemies(faction.id)
        if not enemies:
            return None

        # Target is a border territory (for MVP, just use first territory or None)
        target_id = faction.territories[0] if faction.territories else None

        return FactionIntent(
            faction_id=faction.id,
            intent_type=IntentType.DEFEND,
            target_id=target_id,
            priority=4,
            narrative="Fortify defensive positions",
        )
