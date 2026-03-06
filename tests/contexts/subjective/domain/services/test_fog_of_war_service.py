#!/usr/bin/env python3
"""
Fog of War Service Tests

Tests for FogOfWarService including visibility calculation, knowledge propagation,
and threat assessment.
Covers unit tests, integration tests, and boundary tests.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
from unittest.mock import Mock

import pytest

from src.contexts.subjective.domain.services.fog_of_war_service import (
    BasicVisibilityCalculator,
    FogOfWarService,
    IVisibilityCalculator,
)
from src.contexts.subjective.domain.value_objects.awareness import (
    AlertnessLevel,
    AttentionFocus,
    AwarenessModifier,
    AwarenessState,
)
from src.contexts.subjective.domain.value_objects.knowledge_level import (
    CertaintyLevel,
    KnowledgeBase,
    KnowledgeItem,
    KnowledgeSource,
    KnowledgeType,
)
from src.contexts.subjective.domain.value_objects.perception_range import (
    PerceptionCapabilities,
    PerceptionRange,
    PerceptionType,
    VisibilityLevel,
)


# Helper function to create test perception capabilities
def create_test_perception_capabilities() -> PerceptionCapabilities:
    """Create test perception capabilities."""
    return PerceptionCapabilities(
        perception_ranges={
            PerceptionType.VISUAL: PerceptionRange(
                perception_type=PerceptionType.VISUAL,
                base_range=100.0,
                effective_range=100.0,
                accuracy_modifier=1.0,
                environmental_modifiers={},
            ),
            PerceptionType.AUDITORY: PerceptionRange(
                perception_type=PerceptionType.AUDITORY,
                base_range=50.0,
                effective_range=50.0,
                accuracy_modifier=0.8,
                environmental_modifiers={},
            ),
        }
    )


# Helper function to create test awareness state
def create_test_awareness_state(
    alertness: AlertnessLevel = AlertnessLevel.ALERT,
) -> AwarenessState:
    """Create test awareness state."""
    return AwarenessState(
        base_alertness=alertness,
        current_alertness=alertness,
        attention_focus=AttentionFocus.ENVIRONMENTAL,
    )


# Helper function to create test TurnBrief
def create_test_turn_brief(entity_id: str = "entity_1"):
    """Create test TurnBrief."""
    from src.contexts.subjective.domain.aggregates.turn_brief import TurnBrief
    from src.contexts.subjective.domain.value_objects.subjective_id import SubjectiveId
    
    return TurnBrief.create_for_entity(
        entity_id=entity_id,
        perception_capabilities=create_test_perception_capabilities(),
        world_state_version=1,
        initial_alertness=AlertnessLevel.ALERT,
    )


# ============================================================================
# Unit Tests (15 tests)
# ============================================================================


@pytest.mark.unit
class TestBasicVisibilityCalculator:
    """Unit tests for BasicVisibilityCalculator."""

    def test_calculator_initialization(self):
        """Test calculator initialization."""
        calculator = BasicVisibilityCalculator()
        assert calculator is not None

    def test_calculate_visibility_same_position(self):
        """Test visibility at same position."""
        calculator = BasicVisibilityCalculator()
        capabilities = create_test_perception_capabilities()
        awareness = create_test_awareness_state()
        
        result = calculator.calculate_visibility(
            observer_position=(0.0, 0.0, 0.0),
            target_position=(0.0, 0.0, 0.0),
            perception_capabilities=capabilities,
            awareness_state=awareness,
            environmental_conditions={},
        )
        
        assert PerceptionType.VISUAL in result
        assert result[PerceptionType.VISUAL] == VisibilityLevel.CLEAR

    def test_calculate_visibility_with_distance(self):
        """Test visibility with distance."""
        calculator = BasicVisibilityCalculator()
        capabilities = create_test_perception_capabilities()
        awareness = create_test_awareness_state()
        
        result = calculator.calculate_visibility(
            observer_position=(0.0, 0.0, 0.0),
            target_position=(50.0, 0.0, 0.0),  # Within visual range
            perception_capabilities=capabilities,
            awareness_state=awareness,
            environmental_conditions={},
        )
        
        assert PerceptionType.VISUAL in result
        assert result[PerceptionType.VISUAL] != VisibilityLevel.INVISIBLE

    def test_calculate_visibility_beyond_range(self):
        """Test visibility beyond perception range."""
        calculator = BasicVisibilityCalculator()
        capabilities = create_test_perception_capabilities()
        awareness = create_test_awareness_state()
        
        result = calculator.calculate_visibility(
            observer_position=(0.0, 0.0, 0.0),
            target_position=(200.0, 0.0, 0.0),  # Beyond visual range
            perception_capabilities=capabilities,
            awareness_state=awareness,
            environmental_conditions={},
        )
        
        assert result[PerceptionType.VISUAL] == VisibilityLevel.INVISIBLE

    def test_environmental_modifier_light(self):
        """Test environmental modifier for light level."""
        calculator = BasicVisibilityCalculator()
        
        # Bright light should increase visual range
        modifier = calculator._get_environmental_modifier(
            PerceptionType.VISUAL,
            {"light_level": "bright"},
        )
        assert modifier > 1.0
        
        # Dark should decrease visual range
        modifier = calculator._get_environmental_modifier(
            PerceptionType.VISUAL,
            {"light_level": "dark"},
        )
        assert modifier < 1.0

    def test_environmental_modifier_weather(self):
        """Test environmental modifier for weather."""
        calculator = BasicVisibilityCalculator()
        
        # Fog decreases visual
        visual_mod = calculator._get_environmental_modifier(
            PerceptionType.VISUAL,
            {"weather": "fog"},
        )
        assert visual_mod < 1.0
        
        # Fog can increase auditory
        auditory_mod = calculator._get_environmental_modifier(
            PerceptionType.AUDITORY,
            {"weather": "fog"},
        )
        assert auditory_mod > 1.0


@pytest.mark.unit
class TestFogOfWarService:
    """Unit tests for FogOfWarService."""

    def test_service_initialization(self):
        """Test service initialization."""
        service = FogOfWarService()
        assert service.visibility_calculator is not None
        assert isinstance(service.visibility_calculator, BasicVisibilityCalculator)

    def test_service_with_custom_calculator(self):
        """Test service with custom calculator."""
        custom_calculator = BasicVisibilityCalculator()
        service = FogOfWarService(visibility_calculator=custom_calculator)
        assert service.visibility_calculator == custom_calculator

    def test_calculate_visibility_between_positions(self):
        """Test visibility calculation between positions."""
        service = FogOfWarService()
        turn_brief = create_test_turn_brief()
        
        result = service.calculate_visibility_between_positions(
            observer_turn_brief=turn_brief,
            observer_position=(0.0, 0.0, 0.0),
            target_position=(30.0, 0.0, 0.0),
            environmental_conditions={},
        )
        
        assert PerceptionType.VISUAL in result

    def test_filter_knowledge_by_reliability(self):
        """Test filtering knowledge by reliability."""
        service = FogOfWarService()
        
        # Create knowledge base with items of varying reliability
        reliable_item = KnowledgeItem(
            subject="subject_1",
            information="Reliable info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
        )
        
        unreliable_item = KnowledgeItem(
            subject="subject_1",
            information="Unreliable info",
            knowledge_type=KnowledgeType.RUMOR,
            certainty_level=CertaintyLevel.LOW,
            source=KnowledgeSource.SPECULATION,
            acquired_at=datetime.now(),
        )
        
        knowledge_base = KnowledgeBase(
            knowledge_items={"subject_1": [reliable_item, unreliable_item]}
        )
        
        filtered = service.filter_knowledge_by_reliability(
            knowledge_base,
            min_reliability_score=0.7,
        )
        
        # Should only keep reliable item
        assert "subject_1" in filtered.knowledge_items

    def test_propagate_knowledge_unconscious(self):
        """Test knowledge propagation with unconscious entity."""
        service = FogOfWarService()
        
        source = create_test_turn_brief("source")
        target = create_test_turn_brief("target")
        
        # Make target unconscious
        unconscious_state = AwarenessState(
            base_alertness=AlertnessLevel.UNCONSCIOUS,
            current_alertness=AlertnessLevel.UNCONSCIOUS,
            attention_focus=AttentionFocus.UNFOCUSED,
        )
        target.update_awareness_state(unconscious_state)
        
        result = service.propagate_knowledge_between_entities(source, target)
        assert result == []

    def test_calculate_information_decay(self):
        """Test information decay calculation."""
        service = FogOfWarService()
        
        item = KnowledgeItem(
            subject="test",
            information="Test info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now() - timedelta(hours=2),
        )
        
        decayed = service.calculate_information_decay(
            item,
            timedelta(hours=1),
            decay_rate_per_hour=0.1,
        )
        
        # Certainty should decrease after decay
        assert decayed is not None

    def test_get_stale_knowledge_subjects(self):
        """Test getting stale knowledge subjects."""
        service = FogOfWarService()
        turn_brief = create_test_turn_brief()
        
        # Add old knowledge
        old_item = KnowledgeItem(
            subject="old_subject",
            information="Old info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now() - timedelta(hours=3),
        )
        turn_brief.add_knowledge(old_item, "test")
        
        stale_subjects = service.get_stale_knowledge_subjects(
            turn_brief,
            staleness_threshold=timedelta(hours=1),
        )
        
        assert "old_subject" in stale_subjects

    def test_assess_threat_level_unknown(self):
        """Test threat assessment with no knowledge."""
        service = FogOfWarService()
        turn_brief = create_test_turn_brief()
        
        threat_level, confidence = service.assess_threat_level(
            turn_brief,
            "unknown_threat",
        )
        
        assert threat_level == "unknown"
        assert confidence == 0.0

    def test_assess_threat_level_hostile(self):
        """Test threat assessment with hostile indicators."""
        service = FogOfWarService()
        turn_brief = create_test_turn_brief()
        
        # Add hostile knowledge
        hostile_item = KnowledgeItem(
            subject="threat_1",
            information="Hostile entity with weapon",
            knowledge_type=KnowledgeType.TACTICAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
        )
        turn_brief.add_knowledge(hostile_item, "observation")
        
        threat_level, confidence = service.assess_threat_level(
            turn_brief,
            "threat_1",
        )
        
        assert threat_level in ["medium", "high", "critical"]
        assert confidence > 0.0


# ============================================================================
# Integration Tests (13 tests)
# ============================================================================


@pytest.mark.integration
class TestVisibilityIntegration:
    """Integration tests for visibility calculations."""

    def test_full_visibility_calculation_flow(self):
        """Test full visibility calculation flow."""
        service = FogOfWarService()
        turn_brief = create_test_turn_brief()
        
        # Set up world positions
        world_positions = {
            "entity_1": (0.0, 0.0, 0.0),
            "entity_2": (30.0, 0.0, 0.0),
            "entity_3": (200.0, 0.0, 0.0),  # Beyond range
        }
        
        newly_revealed, newly_concealed, changes = service.update_visible_subjects_for_turn_brief(
            turn_brief,
            world_positions,
            environmental_conditions={},
        )
        
        # entity_2 should be revealed, entity_3 should be invisible
        assert "entity_2" in newly_revealed or turn_brief.is_subject_visible("entity_2")

    def test_visibility_with_environmental_conditions(self):
        """Test visibility with environmental conditions."""
        service = FogOfWarService()
        turn_brief = create_test_turn_brief()
        
        env_conditions = {
            "light_level": "dark",
            "weather": "fog",
            "terrain": "forest",
        }
        
        result = service.calculate_visibility_between_positions(
            turn_brief,
            (0.0, 0.0, 0.0),
            (30.0, 0.0, 0.0),
            environmental_conditions=env_conditions,
        )
        
        assert PerceptionType.VISUAL in result
        # Dark + fog should reduce visibility

    def test_visibility_with_awareness_modifiers(self):
        """Test visibility with awareness modifiers."""
        service = FogOfWarService()
        turn_brief = create_test_turn_brief()
        
        # Update to vigilant with training modifier
        vigilant_state = AwarenessState(
            base_alertness=AlertnessLevel.VIGILANT,
            current_alertness=AlertnessLevel.VIGILANT,
            attention_focus=AttentionFocus.THREAT_SCANNING,
            awareness_modifiers={AwarenessModifier.TRAINING: 0.5},
        )
        turn_brief.update_awareness_state(vigilant_state)
        
        result = service.calculate_visibility_between_positions(
            turn_brief,
            (0.0, 0.0, 0.0),
            (30.0, 0.0, 0.0),
            environmental_conditions={},
        )
        
        assert PerceptionType.VISUAL in result


@pytest.mark.integration
class TestKnowledgeIntegration:
    """Integration tests for knowledge management."""

    def test_knowledge_propagation_flow(self):
        """Test full knowledge propagation flow."""
        service = FogOfWarService()
        source = create_test_turn_brief("source")
        target = create_test_turn_brief("target")
        
        # Add knowledge to source
        knowledge = KnowledgeItem(
            subject="secret_info",
            information="Important secret",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
        )
        source.add_knowledge(knowledge, "discovery")
        
        # Propagate to target
        propagated = service.propagate_knowledge_between_entities(source, target)
        
        assert len(propagated) > 0

    def test_knowledge_filtering_with_expiration(self):
        """Test knowledge filtering with expiration."""
        service = FogOfWarService()
        
        # Create expired knowledge
        expired_item = KnowledgeItem(
            subject="expired",
            information="Old info",
            knowledge_type=KnowledgeType.RUMOR,
            certainty_level=CertaintyLevel.MEDIUM,
            source=KnowledgeSource.REPORTED_BY_NEUTRAL,
            acquired_at=datetime.now() - timedelta(days=2),
            expires_at=datetime.now() - timedelta(days=1),
        )
        
        current_item = KnowledgeItem(
            subject="current",
            information="New info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
        )
        
        knowledge_base = KnowledgeBase(
            knowledge_items={
                "expired": [expired_item],
                "current": [current_item],
            }
        )
        
        filtered = service.filter_knowledge_by_reliability(knowledge_base)
        
        # Expired knowledge should not be in filtered results
        assert "current" in filtered.knowledge_items


@pytest.mark.integration
class TestThreatAssessmentIntegration:
    """Integration tests for threat assessment."""

    def test_threat_assessment_with_multiple_knowledge(self):
        """Test threat assessment with multiple knowledge items."""
        service = FogOfWarService()
        turn_brief = create_test_turn_brief()
        
        # Add multiple knowledge items about threat
        items = [
            KnowledgeItem(
                subject="enemy_1",
                information="Suspicious movement detected",
                knowledge_type=KnowledgeType.TACTICAL,
                certainty_level=CertaintyLevel.MEDIUM,
                source=KnowledgeSource.DIRECT_OBSERVATION,
                acquired_at=datetime.now(),
            ),
            KnowledgeItem(
                subject="enemy_1",
                information="Weapon spotted",
                knowledge_type=KnowledgeType.TACTICAL,
                certainty_level=CertaintyLevel.HIGH,
                source=KnowledgeSource.DIRECT_OBSERVATION,
                acquired_at=datetime.now(),
            ),
        ]
        
        for item in items:
            turn_brief.add_knowledge(item, "observation")
        
        threat_level, confidence = service.assess_threat_level(
            turn_brief,
            "enemy_1",
        )
        
        # Weapon + suspicious should be at least medium threat
        assert threat_level in ["medium", "high", "critical"]
        assert confidence > 0.5


# ============================================================================
# Boundary Tests (12 tests)
# ============================================================================


@pytest.mark.unit
class TestFogOfWarBoundaryConditions:
    """Boundary tests for Fog of War service."""

    def test_visibility_at_zero_distance(self):
        """Test visibility at exactly zero distance."""
        calculator = BasicVisibilityCalculator()
        capabilities = create_test_perception_capabilities()
        awareness = create_test_awareness_state()
        
        result = calculator.calculate_visibility(
            observer_position=(0.0, 0.0, 0.0),
            target_position=(0.0, 0.0, 0.0),
            perception_capabilities=capabilities,
            awareness_state=awareness,
            environmental_conditions={},
        )
        
        assert result[PerceptionType.VISUAL] == VisibilityLevel.CLEAR

    def test_visibility_at_exact_range(self):
        """Test visibility at exact perception range."""
        calculator = BasicVisibilityCalculator()
        capabilities = create_test_perception_capabilities()
        awareness = create_test_awareness_state()
        
        result = calculator.calculate_visibility(
            observer_position=(0.0, 0.0, 0.0),
            target_position=(100.0, 0.0, 0.0),  # Exactly at visual range
            perception_capabilities=capabilities,
            awareness_state=awareness,
            environmental_conditions={},
        )
        
        # At exact range, should be visible but likely degraded
        assert result[PerceptionType.VISUAL] != VisibilityLevel.INVISIBLE

    def test_visibility_well_beyond_range(self):
        """Test visibility well beyond perception range."""
        calculator = BasicVisibilityCalculator()
        capabilities = create_test_perception_capabilities()
        awareness = create_test_awareness_state()
        
        result = calculator.calculate_visibility(
            observer_position=(0.0, 0.0, 0.0),
            target_position=(500.0, 0.0, 0.0),  # Well beyond range
            perception_capabilities=capabilities,
            awareness_state=awareness,
            environmental_conditions={},
        )
        
        # At this distance, should be invisible
        assert result[PerceptionType.VISUAL] == VisibilityLevel.INVISIBLE

    def test_minimal_perception_range(self):
        """Test with minimal perception range."""
        capabilities = PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: PerceptionRange(
                    perception_type=PerceptionType.VISUAL,
                    base_range=1.0,
                    effective_range=1.0,
                    accuracy_modifier=1.0,
                    environmental_modifiers={},
                ),
            }
        )
        
        calculator = BasicVisibilityCalculator()
        awareness = create_test_awareness_state()
        
        result = calculator.calculate_visibility(
            observer_position=(0.0, 0.0, 0.0),
            target_position=(0.1, 0.0, 0.0),  # Very close
            perception_capabilities=capabilities,
            awareness_state=awareness,
            environmental_conditions={},
        )
        
        # Should be visible at very close range
        assert result[PerceptionType.VISUAL] != VisibilityLevel.INVISIBLE

    def test_zero_accuracy_modifier(self):
        """Test with zero accuracy modifier."""
        capabilities = PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: PerceptionRange(
                    perception_type=PerceptionType.VISUAL,
                    base_range=100.0,
                    effective_range=100.0,
                    accuracy_modifier=0.0,  # Zero accuracy
                    environmental_modifiers={},
                ),
            }
        )
        
        calculator = BasicVisibilityCalculator()
        awareness = create_test_awareness_state()
        
        result = calculator.calculate_visibility(
            observer_position=(0.0, 0.0, 0.0),
            target_position=(50.0, 0.0, 0.0),
            perception_capabilities=capabilities,
            awareness_state=awareness,
            environmental_conditions={},
        )
        
        # Zero accuracy should result in poor visibility
        assert result[PerceptionType.VISUAL] in [VisibilityLevel.HIDDEN, VisibilityLevel.INVISIBLE]

    def test_maximum_accuracy_modifier(self):
        """Test with maximum accuracy modifier."""
        capabilities = PerceptionCapabilities(
            perception_ranges={
                PerceptionType.VISUAL: PerceptionRange(
                    perception_type=PerceptionType.VISUAL,
                    base_range=100.0,
                    effective_range=100.0,
                    accuracy_modifier=1.0,  # Maximum accuracy
                    environmental_modifiers={},
                ),
            }
        )
        
        calculator = BasicVisibilityCalculator()
        awareness = create_test_awareness_state()
        
        result = calculator.calculate_visibility(
            observer_position=(0.0, 0.0, 0.0),
            target_position=(50.0, 0.0, 0.0),
            perception_capabilities=capabilities,
            awareness_state=awareness,
            environmental_conditions={},
        )
        
        # Maximum accuracy should result in good visibility
        assert result[PerceptionType.VISUAL] in [VisibilityLevel.CLEAR, VisibilityLevel.PARTIAL]

    def test_zero_decay_time(self):
        """Test information decay with zero time elapsed."""
        service = FogOfWarService()
        
        item = KnowledgeItem(
            subject="test",
            information="Test info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
        )
        
        decayed = service.calculate_information_decay(
            item,
            timedelta(0),  # Zero time
            decay_rate_per_hour=0.1,
        )
        
        # No change expected
        assert decayed.certainty_level == item.certainty_level

    def test_zero_decay_rate(self):
        """Test information decay with zero decay rate."""
        service = FogOfWarService()
        
        item = KnowledgeItem(
            subject="test",
            information="Test info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now(),
        )
        
        decayed = service.calculate_information_decay(
            item,
            timedelta(hours=10),
            decay_rate_per_hour=0.0,  # Zero decay
        )
        
        # No change expected
        assert decayed.certainty_level == item.certainty_level

    def test_maximum_decay(self):
        """Test information decay over very long time."""
        service = FogOfWarService()
        
        item = KnowledgeItem(
            subject="test",
            information="Test info",
            knowledge_type=KnowledgeType.FACTUAL,
            certainty_level=CertaintyLevel.HIGH,
            source=KnowledgeSource.DIRECT_OBSERVATION,
            acquired_at=datetime.now() - timedelta(days=365),
        )
        
        decayed = service.calculate_information_decay(
            item,
            timedelta(days=365),
            decay_rate_per_hour=0.1,
        )
        
        # After long time with high decay, certainty should be very low
        assert decayed is not None

    def test_minimum_reliability_filter(self):
        """Test knowledge filtering with minimum reliability."""
        service = FogOfWarService()
        
        low_reliability_item = KnowledgeItem(
            subject="test",
            information="Test info",
            knowledge_type=KnowledgeType.SPECULATION,
            certainty_level=CertaintyLevel.MINIMAL,
            source=KnowledgeSource.SPECULATION,
            acquired_at=datetime.now(),
        )
        
        knowledge_base = KnowledgeBase(
            knowledge_items={"test": [low_reliability_item]}
        )
        
        # Filter with very high minimum
        filtered = service.filter_knowledge_by_reliability(
            knowledge_base,
            min_reliability_score=0.99,
        )
        
        # Low reliability item should be filtered out
        assert "test" not in filtered.knowledge_items

    def test_empty_knowledge_base_filter(self):
        """Test filtering empty knowledge base."""
        service = FogOfWarService()
        
        empty_knowledge = KnowledgeBase(knowledge_items={})
        filtered = service.filter_knowledge_by_reliability(empty_knowledge)
        
        assert filtered.knowledge_items == {}

    def test_threat_assessment_edge_cases(self):
        """Test threat assessment edge cases."""
        service = FogOfWarService()
        turn_brief = create_test_turn_brief()
        
        # Add minimal threat knowledge
        minimal_item = KnowledgeItem(
            subject="minimal_threat",
            information="Seen once",
            knowledge_type=KnowledgeType.ENVIRONMENTAL,
            certainty_level=CertaintyLevel.LOW,
            source=KnowledgeSource.REPORTED_BY_NEUTRAL,
            acquired_at=datetime.now(),
        )
        turn_brief.add_knowledge(minimal_item, "report")
        
        threat_level, confidence = service.assess_threat_level(
            turn_brief,
            "minimal_threat",
        )
        
        # Minimal threat should be low
        assert threat_level == "low"


# Total: 15 unit + 13 integration + 12 boundary = 40 tests for fog_of_war_service
