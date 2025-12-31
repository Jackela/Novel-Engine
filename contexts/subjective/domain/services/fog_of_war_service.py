#!/usr/bin/env python3
"""
Fog of War Domain Service

This module implements the FogOfWarService, a domain service that handles
visibility calculations, information filtering, and knowledge propagation
mechanics in the subjective context.
"""

import logging
import math
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..aggregates.turn_brief import TurnBrief
from ..value_objects.awareness import AlertnessLevel, AwarenessState
from ..value_objects.knowledge_level import (
    CertaintyLevel,
    KnowledgeBase,
    KnowledgeItem,
    KnowledgeSource,
    KnowledgeType,
)
from ..value_objects.perception_range import (
    PerceptionCapabilities,
    PerceptionType,
    VisibilityLevel,
)

logger = logging.getLogger(__name__)


class IVisibilityCalculator(ABC):
    """
    Interface for visibility calculation strategies.

    This allows different visibility calculation algorithms to be plugged in
    based on game rules, environment type, or performance requirements.
    """

    @abstractmethod
    def calculate_visibility(
        self,
        observer_position: Tuple[float, float, float],
        target_position: Tuple[float, float, float],
        perception_capabilities: PerceptionCapabilities,
        awareness_state: AwarenessState,
        environmental_conditions: Dict[str, Any],
    ) -> Dict[PerceptionType, VisibilityLevel]:
        """
        Calculate visibility levels for all perception types.

        Args:
            observer_position: (x, y, z) position of observer
            target_position: (x, y, z) position of target
            perception_capabilities: Observer's perception capabilities
            awareness_state: Observer's current awareness state
            environmental_conditions: Environmental factors affecting visibility

        Returns:
            Dictionary mapping perception types to visibility levels
        """
        pass


class BasicVisibilityCalculator(IVisibilityCalculator):
    """
    Basic implementation of visibility calculations using simple distance-based rules.
    """

    def calculate_visibility(
        self,
        observer_position: Tuple[float, float, float],
        target_position: Tuple[float, float, float],
        perception_capabilities: PerceptionCapabilities,
        awareness_state: AwarenessState,
        environmental_conditions: Dict[str, Any],
    ) -> Dict[PerceptionType, VisibilityLevel]:
        """Calculate visibility using basic distance-based rules."""

        # Calculate 3D distance
        dx = target_position[0] - observer_position[0]
        dy = target_position[1] - observer_position[1]
        dz = target_position[2] - observer_position[2]
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)

        visibility_results = {}

        # Get awareness bonus
        awareness_bonus = awareness_state.get_perception_bonus()

        # Calculate visibility for each perception type
        for (
            perception_type,
            perception_range,
        ) in perception_capabilities.perception_ranges.items():
            # Apply awareness bonus to effective range
            effective_range = perception_range.effective_range * (1.0 + awareness_bonus)

            # Apply environmental modifiers
            env_modifier = self._get_environmental_modifier(
                perception_type, environmental_conditions
            )
            effective_range *= env_modifier

            # Create temporary modified perception range
            from ..value_objects.perception_range import PerceptionRange

            modified_range = PerceptionRange(
                perception_type=perception_type,
                base_range=perception_range.base_range,
                effective_range=effective_range,
                accuracy_modifier=perception_range.accuracy_modifier
                * (1.0 + awareness_bonus * 0.5),
                environmental_modifiers=perception_range.environmental_modifiers,
            )

            # Calculate visibility
            visibility = modified_range.calculate_visibility_at_distance(distance)
            visibility_results[perception_type] = visibility

        return visibility_results

    def _get_environmental_modifier(
        self, perception_type: PerceptionType, environmental_conditions: Dict[str, Any]
    ) -> float:
        """Get environmental modifier for a specific perception type."""

        # Default modifiers for different environmental conditions
        light_level = environmental_conditions.get(
            "light_level", "normal"
        )  # "bright", "normal", "dim", "dark"
        weather = environmental_conditions.get(
            "weather", "clear"
        )  # "clear", "fog", "rain", "storm"
        terrain = environmental_conditions.get(
            "terrain", "open"
        )  # "open", "forest", "urban", "underground"

        modifier = 1.0

        # Light level effects (primarily affects visual)
        if perception_type == PerceptionType.VISUAL:
            light_modifiers = {"bright": 1.2, "normal": 1.0, "dim": 0.7, "dark": 0.3}
            modifier *= light_modifiers.get(light_level, 1.0)

        # Weather effects
        weather_effects = {
            PerceptionType.VISUAL: {
                "clear": 1.0,
                "fog": 0.3,
                "rain": 0.8,
                "storm": 0.5,
            },
            PerceptionType.AUDITORY: {
                "clear": 1.0,
                "fog": 1.1,  # Sound travels better in fog
                "rain": 0.7,
                "storm": 0.4,
            },
            PerceptionType.THERMAL: {
                "clear": 1.0,
                "fog": 0.9,
                "rain": 0.8,
                "storm": 0.6,
            },
        }

        if perception_type in weather_effects:
            modifier *= weather_effects[perception_type].get(weather, 1.0)

        # Terrain effects
        terrain_effects = {
            PerceptionType.VISUAL: {
                "open": 1.0,
                "forest": 0.6,
                "urban": 0.8,
                "underground": 0.4,
            },
            PerceptionType.AUDITORY: {
                "open": 1.0,
                "forest": 0.8,
                "urban": 0.7,  # Urban noise interference
                "underground": 1.3,  # Sound echoes
            },
            PerceptionType.VIBRATIONAL: {
                "open": 0.8,
                "forest": 0.6,
                "urban": 1.2,  # Hard surfaces transmit vibrations better
                "underground": 1.5,
            },
        }

        if perception_type in terrain_effects:
            modifier *= terrain_effects[perception_type].get(terrain, 1.0)

        return max(0.1, modifier)  # Minimum 10% effectiveness


class FogOfWarService:
    """
    Domain service for managing fog of war calculations and information filtering.

    This service encapsulates the complex business logic around what entities
    can perceive, how information propagates between them, and how knowledge
    degrades over time.
    """

    def __init__(self, visibility_calculator: Optional[IVisibilityCalculator] = None):
        """
        Initialize the FogOfWarService.

        Args:
            visibility_calculator: Strategy for calculating visibility (uses basic if None)
        """
        self.visibility_calculator = (
            visibility_calculator or BasicVisibilityCalculator()
        )
        self.logger = logger.getChild(self.__class__.__name__)

    def calculate_visibility_between_positions(
        self,
        observer_turn_brief: TurnBrief,
        observer_position: Tuple[float, float, float],
        target_position: Tuple[float, float, float],
        environmental_conditions: Optional[Dict[str, Any]] = None,
    ) -> Dict[PerceptionType, VisibilityLevel]:
        """
        Calculate visibility levels between two positions.

        Args:
            observer_turn_brief: The TurnBrief of the observing entity
            observer_position: Position of the observer
            target_position: Position of the target
            environmental_conditions: Environmental factors affecting visibility

        Returns:
            Dictionary mapping perception types to visibility levels
        """
        env_conditions = environmental_conditions or {}

        return self.visibility_calculator.calculate_visibility(
            observer_position=observer_position,
            target_position=target_position,
            perception_capabilities=observer_turn_brief.perception_capabilities,
            awareness_state=observer_turn_brief.awareness_state,
            environmental_conditions=env_conditions,
        )

    def update_visible_subjects_for_turn_brief(
        self,
        turn_brief: TurnBrief,
        world_positions: Dict[str, Tuple[float, float, float]],
        environmental_conditions: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[str], List[str], Dict[str, VisibilityLevel]]:
        """
        Update visible subjects for a TurnBrief based on current world positions.

        Args:
            turn_brief: The TurnBrief to update
            world_positions: Dictionary mapping subject IDs to positions
            environmental_conditions: Environmental factors

        Returns:
            Tuple of (newly_revealed, newly_concealed, visibility_changes)
        """
        if turn_brief.entity_id not in world_positions:
            self.logger.warning(
                f"Observer entity {turn_brief.entity_id} not found in world positions"
            )
            return [], [], {}

        observer_position = world_positions[turn_brief.entity_id]
        old_visible = set(turn_brief.visible_subjects.keys())
        new_visible = set()
        visibility_changes = {}

        # Calculate visibility for all subjects
        for subject_id, position in world_positions.items():
            if subject_id == turn_brief.entity_id:
                continue  # Skip self

            visibility_results = self.calculate_visibility_between_positions(
                turn_brief, observer_position, position, environmental_conditions
            )

            # Get the best visibility level
            best_visibility = VisibilityLevel.INVISIBLE
            for visibility in visibility_results.values():
                if visibility != VisibilityLevel.INVISIBLE:
                    visibility_order = [
                        VisibilityLevel.CLEAR,
                        VisibilityLevel.PARTIAL,
                        VisibilityLevel.OBSCURED,
                        VisibilityLevel.HIDDEN,
                        VisibilityLevel.INVISIBLE,
                    ]
                    if visibility_order.index(visibility) < visibility_order.index(
                        best_visibility
                    ):
                        best_visibility = visibility

            # Track changes
            old_visibility = turn_brief.get_subject_visibility(subject_id)

            if best_visibility != VisibilityLevel.INVISIBLE:
                new_visible.add(subject_id)
                if best_visibility != old_visibility:
                    visibility_changes[subject_id] = best_visibility
            elif old_visibility != VisibilityLevel.INVISIBLE:
                visibility_changes[subject_id] = VisibilityLevel.INVISIBLE

        # Determine newly revealed and concealed
        newly_revealed = list(new_visible - old_visible)
        newly_concealed = list(old_visible - new_visible)

        return newly_revealed, newly_concealed, visibility_changes

    def filter_knowledge_by_reliability(
        self,
        knowledge_base: KnowledgeBase,
        min_reliability_score: float = 0.3,
        current_time: Optional[datetime] = None,
    ) -> KnowledgeBase:
        """
        Filter a knowledge base to only include reliable knowledge.

        Args:
            knowledge_base: The knowledge base to filter
            min_reliability_score: Minimum reliability score to keep
            current_time: Current time for staleness checks

        Returns:
            Filtered knowledge base
        """
        check_time = current_time or datetime.now()
        filtered_items = {}

        for subject, items in knowledge_base.knowledge_items.items():
            reliable_items = []

            for item in items:
                if (
                    item.is_current(check_time)
                    and item.get_reliability_score() >= min_reliability_score
                ):
                    reliable_items.append(item)

            if reliable_items:
                filtered_items[subject] = reliable_items

        return KnowledgeBase(knowledge_items=filtered_items)

    def propagate_knowledge_between_entities(
        self,
        source_turn_brief: TurnBrief,
        target_turn_brief: TurnBrief,
        knowledge_types: Optional[List[KnowledgeType]] = None,
        max_propagation_distance: float = 10.0,
        source_reliability_modifier: float = 0.9,
    ) -> List[KnowledgeItem]:
        """
        Propagate knowledge from one entity to another.

        Args:
            source_turn_brief: TurnBrief of the knowledge source
            target_turn_brief: TurnBrief of the knowledge recipient
            knowledge_types: Types of knowledge to propagate (None for all)
            max_propagation_distance: Maximum distance for knowledge sharing
            source_reliability_modifier: Reliability reduction for shared knowledge

        Returns:
            List of knowledge items that can be propagated
        """
        # Check if entities can communicate (simplified - both need to be aware)
        if (
            source_turn_brief.awareness_state.current_alertness
            == AlertnessLevel.UNCONSCIOUS
            or target_turn_brief.awareness_state.current_alertness
            == AlertnessLevel.UNCONSCIOUS
        ):
            return []

        propagatable_knowledge = []
        filter_types = set(knowledge_types) if knowledge_types else None

        for subject, items in source_turn_brief.knowledge_base.knowledge_items.items():
            for item in items:
                # Filter by knowledge type if specified
                if filter_types and item.knowledge_type not in filter_types:
                    continue

                # Only propagate current, reliable knowledge
                if (
                    item.is_current() and item.get_reliability_score() >= 0.5
                ):  # Minimum for sharing
                    # Create new knowledge item with reduced reliability
                    propagated_item = KnowledgeItem(
                        subject=item.subject,
                        information=item.information,
                        knowledge_type=item.knowledge_type,
                        certainty_level=item.certainty_level,
                        source=KnowledgeSource.REPORTED_BY_ALLY,  # Assume ally for now
                        acquired_at=datetime.now(),
                        expires_at=item.expires_at,
                        tags=item.tags,
                    )

                    propagatable_knowledge.append(propagated_item)

        return propagatable_knowledge

    def calculate_information_decay(
        self,
        knowledge_item: KnowledgeItem,
        time_elapsed: timedelta,
        decay_rate_per_hour: float = 0.05,
    ) -> KnowledgeItem:
        """
        Calculate how knowledge decays over time.

        Args:
            knowledge_item: The knowledge item to decay
            time_elapsed: Time since the knowledge was acquired
            decay_rate_per_hour: How much certainty decreases per hour

        Returns:
            Updated knowledge item with potentially reduced certainty
        """
        if time_elapsed.total_seconds() <= 0:
            return knowledge_item

        hours_elapsed = time_elapsed.total_seconds() / 3600.0
        decay_amount = decay_rate_per_hour * hours_elapsed

        # Convert certainty to numeric, apply decay, convert back
        certainty_values = {
            CertaintyLevel.ABSOLUTE: 1.0,
            CertaintyLevel.HIGH: 0.85,
            CertaintyLevel.MEDIUM: 0.65,
            CertaintyLevel.LOW: 0.40,
            CertaintyLevel.MINIMAL: 0.20,
            CertaintyLevel.UNKNOWN: 0.0,
        }

        reverse_mapping = {v: k for k, v in certainty_values.items()}

        current_certainty_value = certainty_values[knowledge_item.certainty_level]
        new_certainty_value = max(0.0, current_certainty_value - decay_amount)

        # Find the closest certainty level
        closest_certainty = min(
            reverse_mapping.keys(), key=lambda x: abs(x - new_certainty_value)
        )
        new_certainty_level = reverse_mapping[closest_certainty]

        if new_certainty_level != knowledge_item.certainty_level:
            return knowledge_item.with_updated_certainty(
                new_certainty_level, knowledge_item.source
            )

        return knowledge_item

    def get_stale_knowledge_subjects(
        self, turn_brief: TurnBrief, staleness_threshold: timedelta = timedelta(hours=1)
    ) -> List[str]:
        """
        Get subjects with stale knowledge that needs updating.

        Args:
            turn_brief: The TurnBrief to check
            staleness_threshold: How old knowledge must be to be considered stale

        Returns:
            List of subjects with stale knowledge
        """
        current_time = datetime.now()
        cutoff_time = current_time - staleness_threshold

        stale_subjects = []

        for subject, items in turn_brief.knowledge_base.knowledge_items.items():
            # Check if all knowledge about this subject is stale
            has_current_knowledge = any(
                item.is_current(current_time) and item.acquired_at > cutoff_time
                for item in items
            )

            if not has_current_knowledge:
                stale_subjects.append(subject)

        return stale_subjects

    def assess_threat_level(
        self,
        turn_brief: TurnBrief,
        threat_subject: str,
        threat_capabilities: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, float]:
        """
        Assess the threat level of a subject based on available knowledge.

        Args:
            turn_brief: The TurnBrief making the assessment
            threat_subject: The subject being assessed
            threat_capabilities: Known capabilities of the threat

        Returns:
            Tuple of (threat_level, confidence) where threat_level is
            "low", "medium", "high", or "critical"
        """
        # Get knowledge about the threat
        threat_knowledge = turn_brief.knowledge_base.get_knowledge_about(threat_subject)

        if not threat_knowledge:
            return "unknown", 0.0

        # Analyze knowledge to determine threat level
        threat_indicators = 0
        total_confidence = 0.0
        knowledge_count = 0

        for knowledge in threat_knowledge:
            reliability = knowledge.get_reliability_score()
            total_confidence += reliability
            knowledge_count += 1

            # Look for threat indicators in the knowledge
            info_lower = knowledge.information.lower()
            if any(
                word in info_lower
                for word in ["hostile", "aggressive", "weapon", "attack"]
            ):
                threat_indicators += 2 * reliability
            elif any(
                word in info_lower for word in ["suspicious", "unknown", "moving"]
            ):
                threat_indicators += 1 * reliability

        if knowledge_count == 0:
            return "unknown", 0.0

        average_confidence = total_confidence / knowledge_count

        # Determine threat level based on indicators
        if threat_indicators >= 3.0:
            threat_level = "critical"
        elif threat_indicators >= 2.0:
            threat_level = "high"
        elif threat_indicators >= 1.0:
            threat_level = "medium"
        else:
            threat_level = "low"

        return threat_level, average_confidence
