"""
Threat Assessor
===============

Advanced threat assessment system for PersonaAgent decision making.
Analyzes world events, environmental factors, and character context to determine threat levels.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..protocols import ThreatLevel, WorldEvent


class ThreatCategory(Enum):
    """Categories of threats that can be assessed."""

    PHYSICAL = "physical"  # Direct physical danger
    POLITICAL = "political"  # Political/factional threats
    ECONOMIC = "economic"  # Resource/economic threats
    SOCIAL = "social"  # Relationship/reputation threats
    ENVIRONMENTAL = "environmental"  # Environmental hazards
    UNKNOWN = "unknown"  # Unidentified threats


@dataclass
class ThreatFactor:
    """Individual threat factor with assessment details."""

    factor_type: ThreatCategory
    severity: float  # 0.0 to 1.0
    certainty: float  # 0.0 to 1.0 (how certain we are about this threat)
    immediacy: float  # 0.0 to 1.0 (how immediate the threat is)
    source: str  # What/who is the source of this threat
    description: str = ""
    evidence: List[str] = field(default_factory=list)

    def get_weighted_severity(self) -> float:
        """Get severity weighted by certainty and immediacy."""
        return self.severity * self.certainty * (0.5 + 0.5 * self.immediacy)


@dataclass
class ThreatAssessment:
    """Comprehensive threat assessment result."""

    overall_threat_level: ThreatLevel
    threat_factors: List[ThreatFactor]
    confidence: float  # Overall confidence in assessment (0.0 to 1.0)
    assessment_timestamp: float
    primary_threat_source: Optional[str] = None
    recommended_response: Optional[str] = None

    def __post_init__(self):
        if self.assessment_timestamp == 0.0:
            self.assessment_timestamp = datetime.now().timestamp()


class ThreatAssessor:
    """
    Advanced threat assessment system for character decision making.

    Responsibilities:
    - Analyze world events for threat indicators
    - Evaluate threat levels from character perspective
    - Consider character-specific vulnerabilities
    - Track threat patterns and escalation
    - Provide threat-based decision recommendations
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

        # Threat assessment history
        self._assessment_history: List[ThreatAssessment] = []

        # Known threat patterns
        self._threat_patterns: Dict[str, Dict[str, Any]] = {}

        # Character vulnerability profiles
        self._vulnerability_profiles: Dict[str, Dict[str, float]] = {}

        # Environmental threat factors
        self._environmental_factors: Dict[str, float] = {}

    async def assess_threat(
        self,
        event: WorldEvent,
        character_data: Dict[str, Any],
        world_context: Optional[Dict[str, Any]] = None,
    ) -> ThreatAssessment:
        """
        Perform comprehensive threat assessment for a world event.

        Args:
            event: World event to assess
            character_data: Character's data and context
            world_context: Additional world context information

        Returns:
            ThreatAssessment: Comprehensive threat analysis
        """
        try:
            self.logger.debug(f"Assessing threat for event {event.event_id}")

            # Analyze individual threat factors
            threat_factors = await self._analyze_threat_factors(
                event, character_data, world_context
            )

            # Calculate overall threat level
            overall_threat = await self._calculate_overall_threat(
                threat_factors
            )

            # Determine confidence level
            confidence = await self._calculate_assessment_confidence(
                threat_factors, character_data
            )

            # Identify primary threat source
            primary_source = await self._identify_primary_threat_source(
                threat_factors
            )

            # Generate recommended response
            recommended_response = (
                await self._generate_response_recommendation(
                    overall_threat, threat_factors, character_data
                )
            )

            # Create assessment
            assessment = ThreatAssessment(
                overall_threat_level=overall_threat,
                threat_factors=threat_factors,
                confidence=confidence,
                assessment_timestamp=datetime.now().timestamp(),
                primary_threat_source=primary_source,
                recommended_response=recommended_response,
            )

            # Record assessment
            await self._record_assessment(assessment, event, character_data)

            self.logger.debug(
                f"Threat assessment completed: {overall_threat.value}(confidence: {confidence:.2f})"
            )
            return assessment

        except Exception as e:
            self.logger.error(f"Threat assessment failed: {e}")
            # Return minimal safe assessment
            return ThreatAssessment(
                overall_threat_level=ThreatLevel.MODERATE,
                threat_factors=[],
                confidence=0.5,
                assessment_timestamp=datetime.now().timestamp(),
                recommended_response="proceed_with_caution",
            )

    async def assess_environmental_threats(
        self,
        location: str,
        world_state: Dict[str, Any],
        character_data: Dict[str, Any],
    ) -> List[ThreatFactor]:
        """
        Assess environmental threats at a specific location.

        Args:
            location: Location to assess
            world_state: Current world state
            character_data: Character context

        Returns:
            List of environmental threat factors
        """
        try:
            environmental_threats = []

            # Check known environmental hazards
            location_data = world_state.get("locations", {}).get(location, {})
            hazards = location_data.get("hazards", [])

            for hazard in hazards:
                threat_factor = await self._evaluate_environmental_hazard(
                    hazard, character_data
                )
                if threat_factor:
                    environmental_threats.append(threat_factor)

            # Check weather/climate threats
            weather_threats = await self._assess_weather_threats(
                location, world_state, character_data
            )
            environmental_threats.extend(weather_threats)

            # Check resource scarcity threats
            resource_threats = await self._assess_resource_threats(
                location, world_state, character_data
            )
            environmental_threats.extend(resource_threats)

            return environmental_threats

        except Exception as e:
            self.logger.error(f"Environmental threat assessment failed: {e}")
            return []

    async def assess_political_threats(
        self, character_data: Dict[str, Any], world_state: Dict[str, Any]
    ) -> List[ThreatFactor]:
        """
        Assess political and factional threats to character.

        Args:
            character_data: Character information
            world_state: Current world state

        Returns:
            List of political threat factors
        """
        try:
            political_threats = []

            character_faction = character_data.get("faction_info", {}).get(
                "faction", "Independent"
            )

            # Check factional conflicts
            factional_conflicts = world_state.get("factional_conflicts", [])
            for conflict in factional_conflicts:
                if character_faction in conflict.get("involved_factions", []):
                    threat_factor = await self._evaluate_factional_conflict(
                        conflict, character_data
                    )
                    if threat_factor:
                        political_threats.append(threat_factor)

            # Check reputation threats
            reputation_threats = await self._assess_reputation_threats(
                character_data, world_state
            )
            political_threats.extend(reputation_threats)

            # Check authority threats
            authority_threats = await self._assess_authority_threats(
                character_data, world_state
            )
            political_threats.extend(authority_threats)

            return political_threats

        except Exception as e:
            self.logger.error(f"Political threat assessment failed: {e}")
            return []

    async def update_threat_patterns(
        self, recent_events: List[WorldEvent], outcomes: List[Dict[str, Any]]
    ) -> None:
        """
        Update threat pattern recognition based on recent events and outcomes.

        Args:
            recent_events: Recent world events
            outcomes: Outcomes/results from those events
        """
        try:
            for event, outcome in zip(recent_events, outcomes):
                pattern_key = f"{event.event_type}_{event.source}"

                if pattern_key not in self._threat_patterns:
                    self._threat_patterns[pattern_key] = {
                        "occurrences": 0,
                        "threat_escalations": 0,
                        "average_severity": 0.0,
                        "typical_outcomes": [],
                    }

                pattern = self._threat_patterns[pattern_key]
                pattern["occurrences"] += 1

                # Track if this event led to threat escalation
                if outcome.get("threat_escalated", False):
                    pattern["threat_escalations"] += 1

                # Update average severity
                event_severity = outcome.get("severity", 0.5)
                pattern["average_severity"] = (
                    pattern["average_severity"] * (pattern["occurrences"] - 1)
                    + event_severity
                ) / pattern["occurrences"]

                # Track typical outcomes
                outcome_type = outcome.get("outcome_type", "unknown")
                pattern["typical_outcomes"].append(outcome_type)

                # Keep only recent outcomes
                if len(pattern["typical_outcomes"]) > 20:
                    pattern["typical_outcomes"] = pattern["typical_outcomes"][
                        -10:
                    ]

            self.logger.debug(
                f"Updated {len(self._threat_patterns)} threat patterns"
            )

        except Exception as e:
            self.logger.error(f"Threat pattern update failed: {e}")

    async def get_threat_trend(
        self, time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Analyze threat trends over specified time window.

        Args:
            time_window_hours: Time window for analysis in hours

        Returns:
            Dict containing threat trend analysis
        """
        try:
            cutoff_time = datetime.now().timestamp() - (
                time_window_hours * 3600
            )

            # Filter recent assessments
            recent_assessments = [
                assessment
                for assessment in self._assessment_history
                if assessment.assessment_timestamp >= cutoff_time
            ]

            if not recent_assessments:
                return {"trend": "no_data", "assessments_count": 0}

            # Calculate trend metrics
            threat_levels = [
                self._threat_level_to_numeric(a.overall_threat_level)
                for a in recent_assessments
            ]

            if len(threat_levels) >= 2:
                # Simple linear trend
                x = list(range(len(threat_levels)))
                slope = self._calculate_slope(x, threat_levels)

                if slope > 0.1:
                    trend = "increasing"
                elif slope < -0.1:
                    trend = "decreasing"
                else:
                    trend = "stable"
            else:
                trend = "insufficient_data"

            # Calculate average threat level
            avg_threat = sum(threat_levels) / len(threat_levels)

            # Identify most common threat categories
            threat_categories = []
            for assessment in recent_assessments:
                for factor in assessment.threat_factors:
                    threat_categories.append(factor.factor_type.value)

            category_counts = {}
            for category in threat_categories:
                category_counts[category] = (
                    category_counts.get(category, 0) + 1
                )

            most_common_category = (
                max(category_counts.items(), key=lambda x: x[1])[0]
                if category_counts
                else "none"
            )

            return {
                "trend": trend,
                "average_threat_level": avg_threat,
                "assessments_count": len(recent_assessments),
                "most_common_threat_category": most_common_category,
                "category_distribution": category_counts,
                "time_window_hours": time_window_hours,
            }

        except Exception as e:
            self.logger.error(f"Threat trend analysis failed: {e}")
            return {"trend": "error", "error": str(e)}

    async def _analyze_threat_factors(
        self,
        event: WorldEvent,
        character_data: Dict[str, Any],
        world_context: Optional[Dict[str, Any]],
    ) -> List[ThreatFactor]:
        """Analyze individual threat factors from an event."""
        try:
            threat_factors = []

            # Analyze direct threats from event
            direct_threats = await self._analyze_direct_threats(
                event, character_data
            )
            threat_factors.extend(direct_threats)

            # Analyze indirect threats
            indirect_threats = await self._analyze_indirect_threats(
                event, character_data, world_context
            )
            threat_factors.extend(indirect_threats)

            # Analyze relational threats
            relational_threats = await self._analyze_relational_threats(
                event, character_data
            )
            threat_factors.extend(relational_threats)

            # Consider character-specific vulnerabilities
            vulnerability_threats = await self._analyze_vulnerability_threats(
                event, character_data
            )
            threat_factors.extend(vulnerability_threats)

            return threat_factors

        except Exception as e:
            self.logger.error(f"Threat factor analysis failed: {e}")
            return []

    async def _analyze_direct_threats(
        self, event: WorldEvent, character_data: Dict[str, Any]
    ) -> List[ThreatFactor]:
        """Analyze direct threats from event to character."""
        try:
            threats = []

            # Check if character is directly affected
            character_id = character_data.get("agent_id", "")
            if character_id in event.affected_entities:
                severity = await self._calculate_direct_threat_severity(
                    event, character_data
                )
                certainty = 0.9  # High certainty for direct effects
                immediacy = await self._calculate_threat_immediacy(event)

                threat = ThreatFactor(
                    factor_type=await self._classify_threat_type(event),
                    severity=severity,
                    certainty=certainty,
                    immediacy=immediacy,
                    source=event.source,
                    description=f"Direct threat from {event.event_type}",
                    evidence=[
                        f"Character {character_id} directly affected by event {event.event_id}"
                    ],
                )
                threats.append(threat)

            return threats

        except Exception as e:
            self.logger.debug(f"Direct threat analysis failed: {e}")
            return []

    async def _analyze_indirect_threats(
        self,
        event: WorldEvent,
        character_data: Dict[str, Any],
        world_context: Optional[Dict[str, Any]],
    ) -> List[ThreatFactor]:
        """Analyze indirect threats that may affect character."""
        try:
            threats = []

            # Check location-based threats
            character_location = character_data.get("state", {}).get(
                "current_location"
            )
            if character_location == event.location:
                severity = await self._calculate_indirect_threat_severity(
                    event, character_data
                )
                certainty = (
                    0.7  # Moderate certainty for location-based threats
                )
                immediacy = (
                    await self._calculate_threat_immediacy(event) * 0.8
                )  # Slightly reduced immediacy

                threat = ThreatFactor(
                    factor_type=ThreatCategory.ENVIRONMENTAL,
                    severity=severity,
                    certainty=certainty,
                    immediacy=immediacy,
                    source=event.source,
                    description=f"Indirect threat from nearby {event.event_type}",
                    evidence=[
                        f"Event at same location as character: {character_location}"
                    ],
                )
                threats.append(threat)

            # Check factional relationship threats
            character_faction = character_data.get("faction_info", {}).get(
                "faction", "Independent"
            )
            event_source_faction = (
                world_context.get("entity_factions", {}).get(event.source)
                if world_context
                else None
            )

            if (
                event_source_faction
                and character_faction != event_source_faction
            ):
                # Check if factions are hostile
                faction_relations = (
                    world_context.get("faction_relations", {})
                    if world_context
                    else {}
                )
                relation_key = f"{character_faction}_{event_source_faction}"
                relation_score = faction_relations.get(relation_key, 0.0)

                if relation_score < -0.3:  # Hostile relations
                    severity = min(0.6, abs(relation_score))
                    threat = ThreatFactor(
                        factor_type=ThreatCategory.POLITICAL,
                        severity=severity,
                        certainty=0.6,
                        immediacy=0.3,
                        source=event_source_faction,
                        description="Indirect political threat from hostile faction",
                        evidence=[
                            f"Hostile relations with faction {event_source_faction}"
                        ],
                    )
                    threats.append(threat)

            return threats

        except Exception as e:
            self.logger.debug(f"Indirect threat analysis failed: {e}")
            return []

    async def _calculate_overall_threat(
        self, threat_factors: List[ThreatFactor]
    ) -> ThreatLevel:
        """Calculate overall threat level from individual factors."""
        try:
            if not threat_factors:
                return ThreatLevel.NEGLIGIBLE

            # Calculate weighted severity scores
            weighted_scores = [
                factor.get_weighted_severity() for factor in threat_factors
            ]

            # Use max score with some influence from average
            max_score = max(weighted_scores)
            avg_score = sum(weighted_scores) / len(weighted_scores)

            # Combine max and average (70% max, 30% average)
            combined_score = 0.7 * max_score + 0.3 * avg_score

            # Apply factor count bonus for multiple threats
            if len(threat_factors) > 1:
                factor_bonus = min(0.2, len(threat_factors) * 0.05)
                combined_score += factor_bonus

            # Map to threat levels
            if combined_score < 0.15:
                return ThreatLevel.NEGLIGIBLE
            elif combined_score < 0.35:
                return ThreatLevel.LOW
            elif combined_score < 0.55:
                return ThreatLevel.MODERATE
            elif combined_score < 0.75:
                return ThreatLevel.HIGH
            else:
                return ThreatLevel.CRITICAL

        except Exception as e:
            self.logger.error(f"Overall threat calculation failed: {e}")
            return ThreatLevel.MODERATE

    # Helper methods for specific threat analysis

    async def _calculate_direct_threat_severity(
        self, event: WorldEvent, character_data: Dict[str, Any]
    ) -> float:
        """Calculate severity of direct threats."""
        # Base severity on event type
        event_severities = {
            "battle": 0.8,
            "attack": 0.9,
            "political_change": 0.4,
            "discovery": 0.2,
            "death": 1.0,
            "injury": 0.6,
            "capture": 0.9,
        }

        return event_severities.get(event.event_type, 0.5)

    async def _calculate_indirect_threat_severity(
        self, event: WorldEvent, character_data: Dict[str, Any]
    ) -> float:
        """Calculate severity of indirect threats."""
        # Indirect threats are typically less severe
        direct_severity = await self._calculate_direct_threat_severity(
            event, character_data
        )
        return direct_severity * 0.6

    async def _calculate_threat_immediacy(self, event: WorldEvent) -> float:
        """Calculate how immediate a threat is."""
        # Recent events are more immediate
        time_diff = datetime.now().timestamp() - event.timestamp
        if time_diff < 300:  # 5 minutes
            return 1.0
        elif time_diff < 3600:  # 1 hour
            return 0.8
        elif time_diff < 86400:  # 1 day
            return 0.5
        else:
            return 0.2

    async def _classify_threat_type(self, event: WorldEvent) -> ThreatCategory:
        """Classify the type of threat from an event."""
        type_mapping = {
            "battle": ThreatCategory.PHYSICAL,
            "attack": ThreatCategory.PHYSICAL,
            "political_change": ThreatCategory.POLITICAL,
            "economic_crisis": ThreatCategory.ECONOMIC,
            "reputation_damage": ThreatCategory.SOCIAL,
            "environmental_disaster": ThreatCategory.ENVIRONMENTAL,
        }

        return type_mapping.get(event.event_type, ThreatCategory.UNKNOWN)

    def _threat_level_to_numeric(self, threat_level: ThreatLevel) -> float:
        """Convert threat level to numeric value for trend analysis."""
        mapping = {
            ThreatLevel.NEGLIGIBLE: 0.1,
            ThreatLevel.LOW: 0.3,
            ThreatLevel.MODERATE: 0.5,
            ThreatLevel.HIGH: 0.7,
            ThreatLevel.CRITICAL: 0.9,
        }
        return mapping.get(threat_level, 0.5)

    def _calculate_slope(self, x: List[int], y: List[float]) -> float:
        """Calculate simple linear regression slope."""
        n = len(x)
        if n < 2:
            return 0.0

        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        return slope

    # Placeholder methods for future implementation

    async def _analyze_relational_threats(
        self, event: WorldEvent, character_data: Dict[str, Any]
    ) -> List[ThreatFactor]:
        """Analyze threats based on character relationships."""
        return []  # Placeholder

    async def _analyze_vulnerability_threats(
        self, event: WorldEvent, character_data: Dict[str, Any]
    ) -> List[ThreatFactor]:
        """Analyze threats based on character vulnerabilities."""
        return []  # Placeholder

    async def _evaluate_environmental_hazard(
        self, hazard: Dict[str, Any], character_data: Dict[str, Any]
    ) -> Optional[ThreatFactor]:
        """Evaluate a specific environmental hazard."""
        return None  # Placeholder

    async def _assess_weather_threats(
        self,
        location: str,
        world_state: Dict[str, Any],
        character_data: Dict[str, Any],
    ) -> List[ThreatFactor]:
        """Assess weather-related threats."""
        return []  # Placeholder

    async def _assess_resource_threats(
        self,
        location: str,
        world_state: Dict[str, Any],
        character_data: Dict[str, Any],
    ) -> List[ThreatFactor]:
        """Assess resource scarcity threats."""
        return []  # Placeholder

    async def _evaluate_factional_conflict(
        self, conflict: Dict[str, Any], character_data: Dict[str, Any]
    ) -> Optional[ThreatFactor]:
        """Evaluate threat from factional conflict."""
        return None  # Placeholder

    async def _assess_reputation_threats(
        self, character_data: Dict[str, Any], world_state: Dict[str, Any]
    ) -> List[ThreatFactor]:
        """Assess reputation-based threats."""
        return []  # Placeholder

    async def _assess_authority_threats(
        self, character_data: Dict[str, Any], world_state: Dict[str, Any]
    ) -> List[ThreatFactor]:
        """Assess threats from authorities."""
        return []  # Placeholder

    async def _calculate_assessment_confidence(
        self,
        threat_factors: List[ThreatFactor],
        character_data: Dict[str, Any],
    ) -> float:
        """Calculate confidence in threat assessment."""
        if not threat_factors:
            return 0.5

        # Average certainty of all factors
        avg_certainty = sum(
            factor.certainty for factor in threat_factors
        ) / len(threat_factors)
        return avg_certainty

    async def _identify_primary_threat_source(
        self, threat_factors: List[ThreatFactor]
    ) -> Optional[str]:
        """Identify the primary source of threats."""
        if not threat_factors:
            return None

        # Find factor with highest weighted severity
        max_factor = max(
            threat_factors, key=lambda f: f.get_weighted_severity()
        )
        return max_factor.source

    async def _generate_response_recommendation(
        self,
        threat_level: ThreatLevel,
        threat_factors: List[ThreatFactor],
        character_data: Dict[str, Any],
    ) -> str:
        """Generate recommended response to threats."""
        if threat_level == ThreatLevel.CRITICAL:
            return "immediate_defensive_action"
        elif threat_level == ThreatLevel.HIGH:
            return "prepare_defenses"
        elif threat_level == ThreatLevel.MODERATE:
            return "monitor_situation"
        elif threat_level == ThreatLevel.LOW:
            return "maintain_awareness"
        else:
            return "continue_normal_operations"

    async def _record_assessment(
        self,
        assessment: ThreatAssessment,
        event: WorldEvent,
        character_data: Dict[str, Any],
    ) -> None:
        """Record threat assessment for history and learning."""
        try:
            self._assessment_history.append(assessment)

            # Keep history limited
            if len(self._assessment_history) > 500:
                self._assessment_history = self._assessment_history[-250:]

            self.logger.debug(
                f"Recorded threat assessment for event {event.event_id}"
            )

        except Exception as e:
            self.logger.debug(f"Assessment recording failed: {e}")

    def get_assessment_history(
        self, limit: int = 10
    ) -> List[ThreatAssessment]:
        """Get recent threat assessment history."""
        return (
            self._assessment_history[-limit:]
            if self._assessment_history
            else []
        )
