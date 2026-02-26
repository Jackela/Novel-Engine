"""Diplomatic Pact Domain Entity.

This module defines the DiplomaticPact entity which represents formal
agreements between factions, such as trade agreements, alliances, or wars.

Typical usage example:
    >>> from src.contexts.world.domain.entities import DiplomaticPact, PactType
    >>> alliance = DiplomaticPact.create_alliance(
    ...     faction_a_id="kingdom-1",
    ...     faction_b_id="kingdom-2",
    ...     terms={"mutual_defense": True}
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .entity import Entity


class PactType(str, Enum):
    """Classification of diplomatic pact types.

    Determines the nature and effects of an agreement between factions.

    Attributes:
        TRADE_AGREEMENT: Economic cooperation for mutual benefit.
        NON_AGGRESSION: Mutual promise not to attack each other.
        ALLIANCE: Full military and economic cooperation.
        WAR: State of open hostilities between factions.
        CEASEFIRE: Temporary halt to hostilities.
        VASSALAGE: One faction submits to another's authority.
        DEFENSIVE_PACT: Mutual defense against third-party attacks.
        RESEARCH_AGREEMENT: Shared knowledge and technology.
    """

    TRADE_AGREEMENT = "trade_agreement"
    NON_AGGRESSION = "non_aggression"
    ALLIANCE = "alliance"
    WAR = "war"
    CEASEFIRE = "ceasefire"
    VASSALAGE = "vassalage"
    DEFENSIVE_PACT = "defensive_pact"
    RESEARCH_AGREEMENT = "research_agreement"

    def is_hostile(self) -> bool:
        """Check if this pact type represents hostilities."""
        return self == PactType.WAR

    def is_friendly(self) -> bool:
        """Check if this pact type represents friendly relations."""
        return self in (
            PactType.ALLIANCE,
            PactType.DEFENSIVE_PACT,
            PactType.TRADE_AGREEMENT,
            PactType.RESEARCH_AGREEMENT,
        )

    def is_economic(self) -> bool:
        """Check if this pact type has economic effects."""
        return self in (
            PactType.TRADE_AGREEMENT,
            PactType.ALLIANCE,
            PactType.VASSALAGE,
        )

    def is_military(self) -> bool:
        """Check if this pact type has military implications."""
        return self in (
            PactType.ALLIANCE,
            PactType.DEFENSIVE_PACT,
            PactType.WAR,
            PactType.VASSALAGE,
        )


# Pact types that are incompatible with each other
INCOMPATIBLE_PACTS: Dict[PactType, set] = {
    PactType.WAR: {
        PactType.TRADE_AGREEMENT,
        PactType.NON_AGGRESSION,
        PactType.ALLIANCE,
        PactType.DEFENSIVE_PACT,
        PactType.RESEARCH_AGREEMENT,
    },
    PactType.ALLIANCE: {PactType.WAR},
    PactType.NON_AGGRESSION: {PactType.WAR},
    PactType.TRADE_AGREEMENT: {PactType.WAR},
    PactType.DEFENSIVE_PACT: {PactType.WAR},
    PactType.RESEARCH_AGREEMENT: {PactType.WAR},
}


@dataclass(eq=False)
class DiplomaticPact(Entity):
    """DiplomaticPact Entity.

    Represents a formal agreement between two factions. Pacts have
    types, terms, and optional expiration dates.

    Attributes:
        pact_type: The type of agreement.
        faction_a_id: ID of the first faction.
        faction_b_id: ID of the second faction.
        signed_date: When the pact was signed.
        expires_date: Optional expiration date.
        terms: Dictionary of pact-specific terms and conditions.
        is_broken: Whether the pact has been broken/violated.
        broken_date: When the pact was broken (if applicable).
        broken_by: ID of faction that broke the pact (if applicable).
    """

    pact_type: PactType = PactType.TRADE_AGREEMENT
    faction_a_id: str = ""
    faction_b_id: str = ""
    signed_date: datetime = field(default_factory=datetime.now)
    expires_date: Optional[datetime] = None
    terms: Dict[str, Any] = field(default_factory=dict)
    is_broken: bool = False
    broken_date: Optional[datetime] = None
    broken_by: Optional[str] = None

    def __eq__(self, other: object) -> bool:
        """Compare pacts by identity, not by mutable attributes."""
        return super().__eq__(other)

    def _validate_business_rules(self) -> List[str]:
        """Validate DiplomaticPact-specific business rules."""
        errors = []

        if not self.faction_a_id or not self.faction_a_id.strip():
            errors.append("Faction A ID cannot be empty")

        if not self.faction_b_id or not self.faction_b_id.strip():
            errors.append("Faction B ID cannot be empty")

        if self.faction_a_id == self.faction_b_id:
            errors.append("A faction cannot make a pact with itself")

        if self.expires_date and self.expires_date < self.signed_date:
            errors.append("Expiration date cannot be before signed date")

        if self.is_broken and not self.broken_date:
            errors.append("Broken pact must have a broken_date")

        if self.is_broken and not self.broken_by:
            errors.append("Broken pact must have broken_by faction")

        return errors

    def is_active(self, current_date: Optional[datetime] = None) -> bool:
        """Check if the pact is currently active.

        A pact is active if:
        - It has not been broken
        - The current date is on or after the signed date
        - The current date is before the expiration date (if set)

        Args:
            current_date: The date to check against. Defaults to now.

        Returns:
            True if the pact is active, False otherwise.
        """
        if self.is_broken:
            return False

        check_date = current_date or datetime.now()

        # Check if signed
        if check_date < self.signed_date:
            return False

        # Check if expired
        if self.expires_date and check_date >= self.expires_date:
            return False

        return True

    def involves_faction(self, faction_id: str) -> bool:
        """Check if a faction is party to this pact.

        Args:
            faction_id: The faction ID to check.

        Returns:
            True if the faction is involved in this pact.
        """
        return faction_id in (self.faction_a_id, self.faction_b_id)

    def get_other_faction(self, faction_id: str) -> Optional[str]:
        """Get the other faction in this pact.

        Args:
            faction_id: One of the faction IDs in the pact.

        Returns:
            The other faction's ID, or None if faction_id is not in the pact.
        """
        if faction_id == self.faction_a_id:
            return self.faction_b_id
        elif faction_id == self.faction_b_id:
            return self.faction_a_id
        return None

    def break_pact(self, broken_by_faction_id: str) -> None:
        """Mark the pact as broken by a specific faction.

        Args:
            broken_by_faction_id: ID of the faction breaking the pact.

        Raises:
            ValueError: If the faction is not party to this pact.
        """
        if not self.involves_faction(broken_by_faction_id):
            raise ValueError(
                f"Faction {broken_by_faction_id} is not party to this pact"
            )

        self.is_broken = True
        self.broken_date = datetime.now()
        self.broken_by = broken_by_faction_id
        self.touch()

    def renew(self, new_expires_date: datetime) -> None:
        """Renew the pact with a new expiration date.

        Args:
            new_expires_date: The new expiration date.

        Raises:
            ValueError: If pact is broken or new date is in the past.
        """
        if self.is_broken:
            raise ValueError("Cannot renew a broken pact")

        if new_expires_date < datetime.now():
            raise ValueError("New expiration date cannot be in the past")

        self.expires_date = new_expires_date
        self.touch()

    def is_incompatible_with(self, other_pact_type: PactType) -> bool:
        """Check if another pact type is incompatible with this one.

        Args:
            other_pact_type: The other pact type to check.

        Returns:
            True if the pact types are incompatible.
        """
        incompatible = INCOMPATIBLE_PACTS.get(self.pact_type, set())
        return other_pact_type in incompatible

    def _to_dict_specific(self) -> Dict[str, Any]:
        """Convert DiplomaticPact-specific data to dictionary."""
        return {
            "pact_type": self.pact_type.value,
            "faction_a_id": self.faction_a_id,
            "faction_b_id": self.faction_b_id,
            "signed_date": self.signed_date.isoformat(),
            "expires_date": self.expires_date.isoformat() if self.expires_date else None,
            "terms": self.terms,
            "is_broken": self.is_broken,
            "broken_date": self.broken_date.isoformat() if self.broken_date else None,
            "broken_by": self.broken_by,
        }

    @classmethod
    def create_alliance(
        cls,
        faction_a_id: str,
        faction_b_id: str,
        terms: Optional[Dict[str, Any]] = None,
        duration_days: Optional[int] = None,
    ) -> DiplomaticPact:
        """Create an alliance pact.

        Factory method for creating alliance pacts with optional duration.

        Args:
            faction_a_id: First faction ID.
            faction_b_id: Second faction ID.
            terms: Optional pact terms.
            duration_days: Optional duration in days (None = permanent).

        Returns:
            A new DiplomaticPact configured as an alliance.
        """
        expires = None
        if duration_days:
            from datetime import timedelta
            expires = datetime.now() + timedelta(days=duration_days)

        return cls(
            pact_type=PactType.ALLIANCE,
            faction_a_id=faction_a_id,
            faction_b_id=faction_b_id,
            terms=terms or {},
            expires_date=expires,
        )

    @classmethod
    def create_trade_agreement(
        cls,
        faction_a_id: str,
        faction_b_id: str,
        terms: Optional[Dict[str, Any]] = None,
        duration_days: Optional[int] = None,
    ) -> DiplomaticPact:
        """Create a trade agreement pact.

        Factory method for creating trade agreement pacts.

        Args:
            faction_a_id: First faction ID.
            faction_b_id: Second faction ID.
            terms: Optional pact terms.
            duration_days: Optional duration in days.

        Returns:
            A new DiplomaticPact configured as a trade agreement.
        """
        expires = None
        if duration_days:
            from datetime import timedelta
            expires = datetime.now() + timedelta(days=duration_days)

        return cls(
            pact_type=PactType.TRADE_AGREEMENT,
            faction_a_id=faction_a_id,
            faction_b_id=faction_b_id,
            terms=terms or {},
            expires_date=expires,
        )

    @classmethod
    def create_war_declaration(
        cls,
        faction_a_id: str,
        faction_b_id: str,
        casus_belli: Optional[str] = None,
    ) -> DiplomaticPact:
        """Create a war declaration pact.

        Factory method for creating war declarations.

        Args:
            faction_a_id: Declaring faction ID.
            faction_b_id: Target faction ID.
            casus_belli: Optional justification for the war.

        Returns:
            A new DiplomaticPact configured as a war declaration.
        """
        terms = {}
        if casus_belli:
            terms["casus_belli"] = casus_belli

        return cls(
            pact_type=PactType.WAR,
            faction_a_id=faction_a_id,
            faction_b_id=faction_b_id,
            terms=terms,
            # Wars don't expire by default
            expires_date=None,
        )

    @classmethod
    def create_ceasefire(
        cls,
        faction_a_id: str,
        faction_b_id: str,
        duration_days: int = 30,
        terms: Optional[Dict[str, Any]] = None,
    ) -> DiplomaticPact:
        """Create a ceasefire pact.

        Factory method for creating ceasefire agreements.

        Args:
            faction_a_id: First faction ID.
            faction_b_id: Second faction ID.
            duration_days: Duration of ceasefire (default 30 days).
            terms: Optional pact terms.

        Returns:
            A new DiplomaticPact configured as a ceasefire.
        """
        from datetime import timedelta

        return cls(
            pact_type=PactType.CEASEFIRE,
            faction_a_id=faction_a_id,
            faction_b_id=faction_b_id,
            terms=terms or {},
            expires_date=datetime.now() + timedelta(days=duration_days),
        )
