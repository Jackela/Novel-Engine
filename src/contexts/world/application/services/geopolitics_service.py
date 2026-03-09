#!/usr/bin/env python3
"""
Geopolitics Service

Application service for managing geopolitical actions including
diplomatic relations, territory control, and resource tracking.
"""

from typing import Optional

import structlog

from src.contexts.world.domain.aggregates.diplomacy_matrix import DiplomacyMatrix
from src.contexts.world.domain.entities.location import Location
from src.contexts.world.domain.errors import (
    DiplomacyError,
    GeopoliticsError,
)
from src.contexts.world.domain.events.geopolitics_events import (
    AllianceFormedEvent,
    PactType,
    TerritoryChangedEvent,
    WarDeclaredEvent,
)
from src.contexts.world.domain.value_objects.diplomatic_status import DiplomaticStatus
from src.core.result import Err, Error, Ok, Result
from src.events.event_bus import EventBus

logger = structlog.get_logger()


class GeopoliticsService:
    """
    Application service for geopolitical operations.

    Provides a unified interface for:
    - Declaring wars and forming alliances
    - Transferring territory control
    - Querying geopolitical state

    All operations emit appropriate domain events.
    """

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        """Initialize the geopolitics service."""
        self._event_bus = event_bus or EventBus()

    def _emit_event(self, event) -> None:
        """Emit a domain event."""
        self._event_bus.publish(event)
        logger.info(
            "geopolitics_event_emitted",
            event_type=event.event_type,
            event_id=event.event_id,
        )

    def declare_war(
        self,
        matrix: DiplomacyMatrix,
        aggressor_id: str,
        defender_id: str,
        reason: str,
        world_id: Optional[str] = None,
    ) -> Result[None, Error]:
        """
        Declare war between two factions.

        Args:
            matrix: The diplomacy matrix to modify
            aggressor_id: ID of the faction declaring war
            defender_id: ID of the faction being attacked
            reason: Reason for the war declaration
            world_id: Optional world ID for event context

        Returns:
            Result containing:
            - Ok: None on success
            - Err: DiplomacyError on failure
        """
        # Set diplomatic status to AT_WAR
        result = matrix.set_status(aggressor_id, defender_id, DiplomaticStatus.AT_WAR)
        if result.is_error:
            return result

        # Emit war declared event
        event = WarDeclaredEvent.create(
            aggressor_id=aggressor_id,
            defender_id=defender_id,
            reason=reason,
            world_id=world_id or matrix.world_id,
        )
        self._emit_event(event)

        logger.info(
            "war_declared",
            aggressor=aggressor_id,
            defender=defender_id,
            reason=reason,
        )

        return Ok(None)

    def form_alliance(
        self,
        matrix: DiplomacyMatrix,
        faction_a_id: str,
        faction_b_id: str,
        pact_type: PactType = PactType.DEFENSIVE_ALLIANCE,
        world_id: Optional[str] = None,
    ) -> Result[None, Error]:
        """
        Form an alliance between two factions.

        Args:
            matrix: The diplomacy matrix to modify
            faction_a_id: ID of the first faction
            faction_b_id: ID of the second faction
            pact_type: Type of alliance (default: defensive)
            world_id: Optional world ID for event context

        Returns:
            Result containing:
            - Ok: None on success
            - Err: DiplomacyError on failure
        """
        # Check if factions are at war
        current_status = matrix.get_status(faction_a_id, faction_b_id)
        if current_status == DiplomaticStatus.AT_WAR:
            return Err(
                DiplomacyError(
                    f"Cannot form alliance: factions {faction_a_id} and {faction_b_id} are at war",
                    details={
                        "faction_a_id": faction_a_id,
                        "faction_b_id": faction_b_id,
                    },
                )
            )

        # Set diplomatic status to ALLIED
        result = matrix.set_status(faction_a_id, faction_b_id, DiplomaticStatus.ALLIED)
        if result.is_error:
            return result

        # Emit alliance formed event
        event = AllianceFormedEvent.create(
            faction_a_id=faction_a_id,
            faction_b_id=faction_b_id,
            pact_type=pact_type,
            world_id=world_id or matrix.world_id,
        )
        self._emit_event(event)

        logger.info(
            "alliance_formed",
            faction_a=faction_a_id,
            faction_b=faction_b_id,
            pact_type=pact_type.value,
        )

        return Ok(None)

    def transfer_territory(
        self,
        location: Location,
        new_controller_id: Optional[str],
        reason: str = "",
        world_id: Optional[str] = None,
    ) -> Result[None, Error]:
        """
        Transfer territory control to a new faction.

        Args:
            location: The location to transfer
            new_controller_id: ID of the new controlling faction (None for uncontrolled)
            reason: Reason for the transfer
            world_id: Optional world ID for event context

        Returns:
            Result containing:
            - Ok: None on success
            - Err: GeopoliticsError on failure
        """
        previous_controller_id = location.controlling_faction_id

        # Use the location's transfer_control method if available
        if hasattr(location, "transfer_control"):
            location.transfer_control(new_controller_id)
        else:
            location.controlling_faction_id = new_controller_id
            location.touch()

        # Emit territory changed event
        event = TerritoryChangedEvent.create(
            location_id=location.id,
            previous_controller_id=previous_controller_id,
            new_controller_id=new_controller_id,
            world_id=world_id,
            reason=reason,
        )
        self._emit_event(event)

        logger.info(
            "territory_transferred",
            location_id=location.id,
            previous_controller=previous_controller_id,
            new_controller=new_controller_id,
            reason=reason,
        )

        return Ok(None)

    def get_diplomacy_summary(
        self,
        matrix: DiplomacyMatrix,
        faction_id: str,
    ) -> Result[dict, Error]:
        """
        Get a summary of diplomatic relations for a faction.

        Args:
            matrix: The diplomacy matrix to query
            faction_id: ID of the faction to summarize

        Returns:
            Result containing:
            - Ok: Dictionary with allies, enemies, and neutral factions
            - Err: GeopoliticsError on failure
        """
        try:
            return Ok(
                {
                    "faction_id": faction_id,
                    "allies": matrix.get_allies(faction_id),
                    "enemies": matrix.get_enemies(faction_id),
                    "neutral": matrix.get_neutral(faction_id),
                }
            )
        except Exception as e:
            return Err(
                GeopoliticsError(
                    f"Failed to get diplomacy summary: {e}",
                    details={"faction_id": faction_id},
                )
            )
