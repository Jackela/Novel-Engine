#!/usr/bin/env python3
"""
Negotiation Party Value Objects

This module implements value objects for representing negotiation participants
and their capabilities within the Interaction bounded context.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID


class PartyRole(Enum):
    """Enumeration of roles a party can have in negotiations."""

    PRIMARY_NEGOTIATOR = "primary_negotiator"
    SECONDARY_NEGOTIATOR = "secondary_negotiator"
    ADVISOR = "advisor"
    OBSERVER = "observer"
    MEDIATOR = "mediator"
    ARBITRATOR = "arbitrator"
    REPRESENTATIVE = "representative"
    PRINCIPAL = "principal"


class AuthorityLevel(Enum):
    """Enumeration of authority levels for negotiation decisions."""

    FULL_AUTHORITY = "full_authority"
    LIMITED_AUTHORITY = "limited_authority"
    ADVISORY_ONLY = "advisory_only"
    OBSERVER_ONLY = "observer_only"
    CONDITIONAL_AUTHORITY = "conditional_authority"


class NegotiationStyle(Enum):
    """Enumeration of negotiation styles."""

    COMPETITIVE = "competitive"
    COLLABORATIVE = "collaborative"
    ACCOMMODATING = "accommodating"
    AVOIDING = "avoiding"
    COMPROMISING = "compromising"
    INTEGRATIVE = "integrative"
    DISTRIBUTIVE = "distributive"


class CommunicationPreference(Enum):
    """Enumeration of communication preferences."""

    DIRECT = "direct"
    DIPLOMATIC = "diplomatic"
    FORMAL = "formal"
    INFORMAL = "informal"
    AGGRESSIVE = "aggressive"
    PASSIVE = "passive"
    ANALYTICAL = "analytical"
    EMOTIONAL = "emotional"


@dataclass(frozen=True)
class NegotiationCapability:
    """
    Value object representing a specific negotiation capability.
    """

    capability_name: str
    proficiency_level: Decimal
    confidence_modifier: Decimal
    applicable_domains: Set[str]
    prerequisites: Optional[Set[str]] = field(default_factory=set)

    def __post_init__(self):
        """Validate negotiation capability data."""
        if not self.capability_name.strip():
            raise ValueError("capability_name cannot be empty")

        if not (0 <= self.proficiency_level <= 100):
            raise ValueError("proficiency_level must be between 0 and 100")

        if not (-50 <= self.confidence_modifier <= 50):
            raise ValueError("confidence_modifier must be between -50 and 50")

        if not self.applicable_domains:
            raise ValueError("applicable_domains cannot be empty")

        # Ensure all domain names are valid strings
        for domain in self.applicable_domains:
            if not isinstance(domain, str) or not domain.strip():
                raise ValueError(
                    "All applicable_domains must be non-empty strings"
                )

        # Validate prerequisites
        if self.prerequisites:
            for prereq in self.prerequisites:
                if not isinstance(prereq, str) or not prereq.strip():
                    raise ValueError(
                        "All prerequisites must be non-empty strings"
                    )

    def applies_to_domain(self, domain: str) -> bool:
        """Check if capability applies to specific domain."""
        return domain.lower() in {d.lower() for d in self.applicable_domains}

    def get_effective_proficiency(self) -> Decimal:
        """Get proficiency level adjusted by confidence modifier."""
        adjusted = self.proficiency_level + self.confidence_modifier
        return max(Decimal("0"), min(Decimal("100"), adjusted))

    def __eq__(self, other: Any) -> bool:
        """Compare NegotiationCapability instances for equality."""
        if not isinstance(other, NegotiationCapability):
            return False
        return (
            self.capability_name == other.capability_name
            and self.proficiency_level == other.proficiency_level
            and self.confidence_modifier == other.confidence_modifier
            and self.applicable_domains == other.applicable_domains
            and self.prerequisites == other.prerequisites
        )


@dataclass(frozen=True)
class PartyPreferences:
    """
    Value object representing negotiation preferences and constraints.
    """

    negotiation_style: NegotiationStyle
    communication_preference: CommunicationPreference
    risk_tolerance: Decimal
    time_pressure_sensitivity: Decimal
    preferred_session_duration: Optional[int] = None  # minutes
    maximum_session_duration: Optional[int] = None  # minutes
    cultural_considerations: Set[str] = field(default_factory=set)
    taboo_topics: Set[str] = field(default_factory=set)
    preferred_meeting_times: Optional[Dict[str, Any]] = None
    language_preferences: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """Validate party preferences data."""
        if not (0 <= self.risk_tolerance <= 100):
            raise ValueError("risk_tolerance must be between 0 and 100")

        if not (0 <= self.time_pressure_sensitivity <= 100):
            raise ValueError(
                "time_pressure_sensitivity must be between 0 and 100"
            )

        if (
            self.preferred_session_duration
            and self.preferred_session_duration <= 0
        ):
            raise ValueError("preferred_session_duration must be positive")

        if (
            self.maximum_session_duration
            and self.maximum_session_duration <= 0
        ):
            raise ValueError("maximum_session_duration must be positive")

        if (
            self.preferred_session_duration
            and self.maximum_session_duration
            and self.preferred_session_duration > self.maximum_session_duration
        ):
            raise ValueError(
                "preferred_session_duration cannot exceed maximum_session_duration"
            )

        # Validate string sets
        for field_name, string_set in [
            ("cultural_considerations", self.cultural_considerations),
            ("taboo_topics", self.taboo_topics),
            ("language_preferences", self.language_preferences),
        ]:
            for item in string_set:
                if not isinstance(item, str) or not item.strip():
                    raise ValueError(
                        f"All {field_name} must be non-empty strings"
                    )

    def is_compatible_with(self, other: "PartyPreferences") -> bool:
        """Check if preferences are compatible with another party."""
        # Time compatibility
        if (
            self.maximum_session_duration
            and other.maximum_session_duration
            and min(
                self.maximum_session_duration, other.maximum_session_duration
            )
            < 30
        ):
            return False  # Minimum viable session time

        # Language compatibility
        if (
            self.language_preferences
            and other.language_preferences
            and not self.language_preferences.intersection(
                other.language_preferences
            )
        ):
            return False

        # Taboo topics overlap
        if self.taboo_topics.intersection(other.taboo_topics):
            return True  # Shared taboos are compatible

        # Style compatibility (simplified) - P3 Sprint 2 Pattern: Use valid enum values and safe comparison
        incompatible_styles = {
            (NegotiationStyle.COMPETITIVE, NegotiationStyle.AVOIDING),
            (NegotiationStyle.COMPETITIVE, NegotiationStyle.ACCOMMODATING),
        }

        # P3 Sprint 2 Pattern: Compare enum values instead of sorting enum objects to avoid type errors
        style_pair = tuple(
            sorted(
                [self.negotiation_style.value, other.negotiation_style.value]
            )
        )
        style_value_pairs = {
            (style1.value, style2.value)
            for style1, style2 in incompatible_styles
        }
        return style_pair not in style_value_pairs

    def __eq__(self, other: Any) -> bool:
        """Compare PartyPreferences instances for equality."""
        if not isinstance(other, PartyPreferences):
            return False
        return (
            self.negotiation_style == other.negotiation_style
            and self.communication_preference == other.communication_preference
            and self.risk_tolerance == other.risk_tolerance
            and self.time_pressure_sensitivity
            == other.time_pressure_sensitivity
            and self.preferred_session_duration
            == other.preferred_session_duration
            and self.maximum_session_duration == other.maximum_session_duration
            and self.cultural_considerations == other.cultural_considerations
            and self.taboo_topics == other.taboo_topics
            and self.preferred_meeting_times == other.preferred_meeting_times
            and self.language_preferences == other.language_preferences
        )


@dataclass(frozen=True)
class NegotiationParty:
    """
    Value object representing a participant in negotiations.

    Encapsulates party identity, role, authority, capabilities, and preferences
    following DDD principles for immutable value objects.
    """

    party_id: UUID
    entity_id: UUID  # Reference to the actual entity (character, faction, etc.)
    party_name: str
    role: PartyRole
    authority_level: AuthorityLevel
    capabilities: List[NegotiationCapability]
    preferences: PartyPreferences
    constraints: Dict[str, Any] = field(default_factory=dict)
    reputation_modifiers: Dict[str, Decimal] = field(default_factory=dict)
    active_mandates: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """Validate negotiation party data."""
        if not self.party_name.strip():
            raise ValueError("party_name cannot be empty")

        # Validate capability names are unique
        capability_names = [cap.capability_name for cap in self.capabilities]
        if len(capability_names) != len(set(capability_names)):
            raise ValueError("Capability names must be unique")

        # Validate reputation modifiers
        for domain, modifier in self.reputation_modifiers.items():
            if not isinstance(domain, str) or not domain.strip():
                raise ValueError(
                    "Reputation modifier domains must be non-empty strings"
                )
            if not (-100 <= modifier <= 100):
                raise ValueError(
                    f"Reputation modifier for {domain} must be between -100 and 100"
                )

        # Validate active mandates
        for mandate in self.active_mandates:
            if not isinstance(mandate, str) or not mandate.strip():
                raise ValueError(
                    "All active_mandates must be non-empty strings"
                )

        # Authority level validation
        if (
            self.role == PartyRole.OBSERVER
            and self.authority_level != AuthorityLevel.OBSERVER_ONLY
        ):
            raise ValueError("Observer role must have observer-only authority")

        if self.role == PartyRole.ADVISOR and self.authority_level not in [
            AuthorityLevel.ADVISORY_ONLY,
            AuthorityLevel.OBSERVER_ONLY,
        ]:
            raise ValueError(
                "Advisor role should have advisory or observer authority"
            )

    def get_capability(
        self, capability_name: str
    ) -> Optional[NegotiationCapability]:
        """Get specific capability by name."""
        return next(
            (
                cap
                for cap in self.capabilities
                if cap.capability_name == capability_name
            ),
            None,
        )

    def get_capabilities_for_domain(
        self, domain: str
    ) -> List[NegotiationCapability]:
        """Get all capabilities applicable to specific domain."""
        return [
            cap for cap in self.capabilities if cap.applies_to_domain(domain)
        ]

    def get_effective_proficiency(
        self, capability_name: str, domain: str
    ) -> Optional[Decimal]:
        """Get effective proficiency for capability in specific domain."""
        capability = self.get_capability(capability_name)
        if not capability or not capability.applies_to_domain(domain):
            return None

        base_proficiency = capability.get_effective_proficiency()

        # Apply reputation modifier if available
        reputation_modifier = self.reputation_modifiers.get(
            domain, Decimal("0")
        )
        adjusted = base_proficiency + reputation_modifier

        return max(Decimal("0"), min(Decimal("100"), adjusted))

    def can_make_binding_decisions(self) -> bool:
        """Check if party can make binding negotiation decisions."""
        return self.authority_level in [
            AuthorityLevel.FULL_AUTHORITY,
            AuthorityLevel.LIMITED_AUTHORITY,
            AuthorityLevel.CONDITIONAL_AUTHORITY,
        ]

    def has_mandate(self, mandate: str) -> bool:
        """Check if party has specific active mandate."""
        return mandate in self.active_mandates

    def is_compatible_with(self, other: "NegotiationParty") -> bool:
        """Check basic compatibility with another negotiation party."""
        # Cannot negotiate with self
        if self.entity_id == other.entity_id:
            return False

        # Check preference compatibility
        if not self.preferences.is_compatible_with(other.preferences):
            return False

        # At least one party must have decision-making authority
        if not (
            self.can_make_binding_decisions()
            or other.can_make_binding_decisions()
        ):
            return False

        return True

    def get_negotiation_power(self, domain: str) -> Decimal:
        """Calculate overall negotiation power in specific domain."""
        relevant_capabilities = self.get_capabilities_for_domain(domain)

        if not relevant_capabilities:
            return Decimal("0")

        # Weight by authority level
        authority_multiplier = {
            AuthorityLevel.FULL_AUTHORITY: Decimal("1.0"),
            AuthorityLevel.LIMITED_AUTHORITY: Decimal("0.8"),
            AuthorityLevel.CONDITIONAL_AUTHORITY: Decimal("0.7"),
            AuthorityLevel.ADVISORY_ONLY: Decimal("0.3"),
            AuthorityLevel.OBSERVER_ONLY: Decimal("0.1"),
        }[self.authority_level]

        # Calculate weighted average proficiency
        total_proficiency = sum(
            self.get_effective_proficiency(cap.capability_name, domain)
            or Decimal("0")
            for cap in relevant_capabilities
        )

        # P3 Sprint 2 Pattern: Ensure Decimal arithmetic remains in Decimal type
        avg_proficiency = total_proficiency / Decimal(
            len(relevant_capabilities)
        )

        # Apply authority multiplier
        negotiation_power = avg_proficiency * authority_multiplier

        # Apply role modifier
        role_modifier = {
            PartyRole.PRIMARY_NEGOTIATOR: Decimal("1.0"),
            PartyRole.SECONDARY_NEGOTIATOR: Decimal("0.9"),
            PartyRole.REPRESENTATIVE: Decimal("0.95"),
            PartyRole.PRINCIPAL: Decimal("1.1"),
            PartyRole.MEDIATOR: Decimal("0.8"),
            PartyRole.ARBITRATOR: Decimal("0.7"),
            PartyRole.ADVISOR: Decimal("0.4"),
            PartyRole.OBSERVER: Decimal("0.1"),
        }[self.role]

        return negotiation_power * role_modifier

    def with_updated_capability(
        self, capability: NegotiationCapability
    ) -> "NegotiationParty":
        """Create new party with updated capability."""
        updated_capabilities = [
            capability
            if cap.capability_name == capability.capability_name
            else cap
            for cap in self.capabilities
        ]

        # Add capability if it doesn't exist
        if not any(
            cap.capability_name == capability.capability_name
            for cap in self.capabilities
        ):
            updated_capabilities.append(capability)

        return NegotiationParty(
            party_id=self.party_id,
            entity_id=self.entity_id,
            party_name=self.party_name,
            role=self.role,
            authority_level=self.authority_level,
            capabilities=updated_capabilities,
            preferences=self.preferences,
            constraints=self.constraints,
            reputation_modifiers=self.reputation_modifiers,
            active_mandates=self.active_mandates,
        )

    def with_updated_authority(
        self, authority_level: AuthorityLevel
    ) -> "NegotiationParty":
        """Create new party with updated authority level."""
        return NegotiationParty(
            party_id=self.party_id,
            entity_id=self.entity_id,
            party_name=self.party_name,
            role=self.role,
            authority_level=authority_level,
            capabilities=self.capabilities,
            preferences=self.preferences,
            constraints=self.constraints,
            reputation_modifiers=self.reputation_modifiers,
            active_mandates=self.active_mandates,
        )

    def add_mandate(self, mandate: str) -> "NegotiationParty":
        """Create new party with additional mandate."""
        if mandate in self.active_mandates:
            return self  # Already has mandate

        updated_mandates = self.active_mandates | {mandate}

        return NegotiationParty(
            party_id=self.party_id,
            entity_id=self.entity_id,
            party_name=self.party_name,
            role=self.role,
            authority_level=self.authority_level,
            capabilities=self.capabilities,
            preferences=self.preferences,
            constraints=self.constraints,
            reputation_modifiers=self.reputation_modifiers,
            active_mandates=updated_mandates,
        )

    @property
    def is_decision_maker(self) -> bool:
        """Check if party is a decision maker."""
        return (
            self.role
            in [
                PartyRole.PRIMARY_NEGOTIATOR,
                PartyRole.SECONDARY_NEGOTIATOR,
                PartyRole.PRINCIPAL,
            ]
            and self.can_make_binding_decisions()
        )

    @property
    def total_capabilities_count(self) -> int:
        """Get total number of capabilities."""
        return len(self.capabilities)

    @property
    def average_proficiency(self) -> Decimal:
        """Get average proficiency across all capabilities."""
        if not self.capabilities:
            return Decimal("0")

        total = sum(
            cap.get_effective_proficiency() for cap in self.capabilities
        )
        # P3 Sprint 2 Pattern: Ensure Decimal arithmetic for return type consistency
        return total / Decimal(len(self.capabilities))

    def __eq__(self, other: Any) -> bool:
        """Compare NegotiationParty instances for equality."""
        if not isinstance(other, NegotiationParty):
            return False
        return (
            self.party_id == other.party_id
            and self.entity_id == other.entity_id
            and self.party_name == other.party_name
            and self.role == other.role
            and self.authority_level == other.authority_level
            and self.capabilities == other.capabilities
            and self.preferences == other.preferences
            and self.constraints == other.constraints
            and self.reputation_modifiers == other.reputation_modifiers
            and self.active_mandates == other.active_mandates
        )

    def __str__(self) -> str:
        """Return string representation of negotiation party."""
        return f"NegotiationParty(name={self.party_name}, role={self.role.value}, authority={self.authority_level.value})"
