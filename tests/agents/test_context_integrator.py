#!/usr/bin/env python3
"""
Test suite for ContextIntegrator module.

Tests context integration, merging, and data transformation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.unit

from src.agents.context_integrator import ContextIntegrator


@dataclass
class MockCharacterContext:
    """Mock CharacterContext for testing."""

    character_name: str = "Test Character"
    load_success: bool = True
    load_timestamp: datetime = field(default_factory=datetime.now)
    validation_warnings: List[str] = field(default_factory=list)
    memory_context: Any = None
    objectives_context: Any = None
    profile_context: Any = None
    stats_context: Any = None


@dataclass
class MockMemoryContext:
    """Mock MemoryContext for testing."""

    behavioral_triggers: List[Any] = field(default_factory=list)
    relationships: List[Any] = field(default_factory=list)
    formative_events: List[Any] = field(default_factory=list)


@dataclass
class MockBehavioralTrigger:
    """Mock BehavioralTrigger for testing."""

    trigger_name: str = "test_trigger"
    trigger_conditions: List[str] = field(default_factory=list)
    behavioral_response: str = "cautious"
    override_conditions: List[str] = field(default_factory=list)
    memory_origin: str = "test"


@dataclass
class MockRelationshipType:
    """Mock RelationshipType for testing."""

    value: str = "ally"


@dataclass
class MockRelationship:
    """Mock Relationship for testing."""

    character_name: str = "Ally"
    trust_level: Any = None
    relationship_type: Any = field(default_factory=MockRelationshipType)
    emotional_dynamics: Dict[str, Any] = field(default_factory=dict)
    conflict_points: List[str] = field(default_factory=list)
    shared_experiences: List[str] = field(default_factory=list)
    memory_foundation: str = ""


@dataclass
class MockTrustLevel:
    """Mock TrustLevel for testing."""

    score: int = 50


@dataclass
class MockMemoryType:
    """Mock MemoryType for testing."""

    value: str = "formative"


@dataclass
class MockFormativeEvent:
    """Mock FormativeEvent for testing."""

    event_name: str = "test_event"
    age: int = 20
    description: str = "Test description"
    memory_type: Any = field(default_factory=MockMemoryType)
    emotional_impact: str = "positive"
    decision_influence: str = "encourages caution"
    trigger_phrases: List[str] = field(default_factory=list)
    key_lesson: str = ""


@dataclass
class MockObjectivesContext:
    """Mock ObjectivesContext for testing."""

    core_objectives: List[Any] = field(default_factory=list)
    strategic_objectives: List[Any] = field(default_factory=list)
    tactical_objectives: List[Any] = field(default_factory=list)
    resource_allocation: Any = None
    current_focus: str = ""


@dataclass
class MockObjective:
    """Mock Objective for testing."""

    name: str = "test_objective"
    priority: float = 0.5
    status: Any = None
    success_metrics: List[str] = field(default_factory=list)
    timeline: str = ""
    motivation_source: str = ""
    risk_factors: List[str] = field(default_factory=list)


@dataclass
class MockStatus:
    """Mock Status for testing."""

    value: str = "active"


@dataclass
class MockProfileContext:
    """Mock ProfileContext for testing."""

    emotional_drives: List[Any] = field(default_factory=list)
    personality_traits: List[Any] = field(default_factory=list)
    background_summary: str = ""
    key_life_phases: List[str] = field(default_factory=list)
    physical_description: str = ""
    distinguishing_features: List[str] = field(default_factory=list)
    core_skills: List[str] = field(default_factory=list)
    specializations: List[str] = field(default_factory=list)
    equipment: List[str] = field(default_factory=list)
    resources: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MockEmotionalDrive:
    """Mock EmotionalDrive for testing."""

    name: str = "security"
    dominance_level: str = "Core"
    foundation: str = "childhood"
    positive_expression: str = "caution"
    negative_expression: str = "paranoia"
    trigger_events: List[str] = field(default_factory=list)
    soothing_behaviors: List[str] = field(default_factory=list)


@dataclass
class MockPersonalityTrait:
    """Mock PersonalityTrait for testing."""

    name: str = "brave"
    score: float = 0.8
    emotional_foundation: str = "upbringing"
    positive_expression: str = "heroism"
    negative_expression: str = "recklessness"
    emotional_triggers: List[str] = field(default_factory=list)


@dataclass
class MockStatsContext:
    """Mock StatsContext for testing."""

    combat_stats: Any = None
    psychological_profile: Any = None
    relationships: Dict[str, List[Any]] = field(default_factory=dict)
    equipment: Dict[str, Any] = field(default_factory=dict)
    objectives: Dict[str, Any] = field(default_factory=dict)


class TestContextIntegratorInitialization:
    """Test ContextIntegrator initialization."""

    def test_initialization(self):
        """Test basic initialization."""
        integrator = ContextIntegrator()
        assert integrator is not None


class TestContextIntegratorMerging:
    """Test context merging methods."""

    @pytest.fixture
    def integrator(self):
        """Create a ContextIntegrator."""
        return ContextIntegrator()

    @pytest.fixture
    def existing_data(self):
        """Create existing character data."""
        return {
            "name": "Test Character",
            "faction": "Alliance",
            "level": 5,
        }

    def test_merge_contexts_basic(self, integrator, existing_data):
        """Test basic context merging."""
        context = MockCharacterContext(
            character_name="Test Character",
            load_success=True,
        )

        merged = integrator.merge_contexts(existing_data, context)

        assert "enhanced_context" in merged
        assert merged["context_load_success"] is True
        assert "name" in merged  # Preserved from existing

    def test_merge_contexts_with_memory(self, integrator, existing_data):
        """Test merging with memory context."""
        trigger = MockBehavioralTrigger(
            trigger_name="danger",
            trigger_conditions=["enemy present"],
        )
        memory_ctx = MockMemoryContext(
            behavioral_triggers=[trigger],
        )
        context = MockCharacterContext(
            character_name="Test",
            memory_context=memory_ctx,
        )

        merged = integrator.merge_contexts(existing_data, context)

        assert "memory_context" in merged
        assert "behavioral_triggers" in merged

    def test_merge_contexts_with_objectives(self, integrator, existing_data):
        """Test merging with objectives context."""
        objective = MockObjective(
            name="Defend Base",
            priority=0.8,
            status=MockStatus("active"),
        )
        objectives_ctx = MockObjectivesContext(
            core_objectives=[objective],
        )
        context = MockCharacterContext(
            character_name="Test",
            objectives_context=objectives_ctx,
        )

        merged = integrator.merge_contexts(existing_data, context)

        assert "objectives_context" in merged
        assert "active_objectives" in merged

    def test_merge_contexts_with_profile(self, integrator, existing_data):
        """Test merging with profile context."""
        drive = MockEmotionalDrive(name="security", dominance_level="Core")
        trait = MockPersonalityTrait(name="brave", score=0.8)
        profile_ctx = MockProfileContext(
            emotional_drives=[drive],
            personality_traits=[trait],
        )
        context = MockCharacterContext(
            character_name="Test",
            profile_context=profile_ctx,
        )

        merged = integrator.merge_contexts(existing_data, context)

        assert "profile_context" in merged
        assert "emotional_drives" in merged
        assert "enhanced_personality" in merged

    def test_merge_contexts_error_handling(self, integrator, existing_data):
        """Test error handling during merge."""
        # Create context that will cause error - using None as context
        # to trigger the error handling path

        merged = integrator.merge_contexts(existing_data, None)  # type: ignore

        # Should return original data on error (None context causes AttributeError)
        assert merged == existing_data


class TestContextIntegratorMemoryIntegration:
    """Test memory context integration."""

    @pytest.fixture
    def integrator(self):
        """Create a ContextIntegrator."""
        return ContextIntegrator()

    def test_integrate_memory_data_triggers(self, integrator):
        """Test integrating behavioral triggers."""
        merged_data: Dict[str, Any] = {}
        trigger = MockBehavioralTrigger(
            trigger_name="danger",
            trigger_conditions=["enemy"],
            behavioral_response="defend",
        )
        memory_ctx = MockMemoryContext(behavioral_triggers=[trigger])

        integrator._integrate_memory_data(merged_data, memory_ctx)

        assert "behavioral_triggers" in merged_data
        assert "danger" in merged_data["behavioral_triggers"]

    def test_integrate_memory_data_relationships(self, integrator):
        """Test integrating relationship data."""
        merged_data: Dict[str, Any] = {}
        relationship = MockRelationship(
            character_name="Ally",
            trust_level=MockTrustLevel(75),
        )
        memory_ctx = MockMemoryContext(relationships=[relationship])

        integrator._integrate_memory_data(merged_data, memory_ctx)

        assert "enhanced_relationships" in merged_data
        assert "Ally" in merged_data["enhanced_relationships"]

    def test_integrate_memory_data_formative_events(self, integrator):
        """Test integrating formative events."""
        merged_data: Dict[str, Any] = {}
        event = MockFormativeEvent(
            event_name="Childhood Trauma",
            age=10,
            decision_influence="encourages caution",
        )
        memory_ctx = MockMemoryContext(formative_events=[event])

        integrator._integrate_memory_data(merged_data, memory_ctx)

        assert "formative_events" in merged_data
        assert "Childhood Trauma" in merged_data["formative_events"]


class TestContextIntegratorObjectivesIntegration:
    """Test objectives context integration."""

    @pytest.fixture
    def integrator(self):
        """Create a ContextIntegrator."""
        return ContextIntegrator()

    def test_integrate_core_objectives(self, integrator):
        """Test integrating core objectives."""
        merged_data: Dict[str, Any] = {}
        objective = MockObjective(
            name="Protect Family",
            priority=0.9,
            status=MockStatus("active"),
        )
        objectives_ctx = MockObjectivesContext(core_objectives=[objective])

        integrator._integrate_objectives_data(merged_data, objectives_ctx)

        assert "active_objectives" in merged_data
        assert "Protect Family" in merged_data["active_objectives"]

    def test_integrate_strategic_objectives(self, integrator):
        """Test integrating strategic objectives."""
        merged_data: Dict[str, Any] = {}
        objective = MockObjective(
            name="Expand Territory",
            priority=0.7,
            status=MockStatus("active"),
        )
        objectives_ctx = MockObjectivesContext(strategic_objectives=[objective])

        integrator._integrate_objectives_data(merged_data, objectives_ctx)

        assert "active_objectives" in merged_data
        obj_data = merged_data["active_objectives"]["Expand Territory"]
        assert obj_data["tier"] == "strategic"

    def test_integrate_resource_allocation(self, integrator):
        """Test integrating resource allocation."""
        merged_data: Dict[str, Any] = {}
        allocation = Mock()
        allocation.time_energy_percentages = {"combat": 40, "diplomacy": 30}
        allocation.success_thresholds = {"win_rate": 0.7}
        objectives_ctx = MockObjectivesContext(resource_allocation=allocation)

        integrator._integrate_objectives_data(merged_data, objectives_ctx)

        assert "resource_allocation" in merged_data


class TestContextIntegratorProfileIntegration:
    """Test profile context integration."""

    @pytest.fixture
    def integrator(self):
        """Create a ContextIntegrator."""
        return ContextIntegrator()

    def test_integrate_emotional_drives(self, integrator):
        """Test integrating emotional drives."""
        merged_data: Dict[str, Any] = {}
        drive = MockEmotionalDrive(
            name="security",
            dominance_level="Dominant",
            foundation="childhood trauma",
        )
        profile_ctx = MockProfileContext(emotional_drives=[drive])

        integrator._integrate_profile_data(merged_data, profile_ctx)

        assert "emotional_drives" in merged_data
        assert "security" in merged_data["emotional_drives"]

    def test_integrate_personality_traits(self, integrator):
        """Test integrating personality traits."""
        merged_data: Dict[str, Any] = {}
        trait = MockPersonalityTrait(
            name="brave",
            score=0.85,
            emotional_foundation="military training",
        )
        profile_ctx = MockProfileContext(personality_traits=[trait])

        integrator._integrate_profile_data(merged_data, profile_ctx)

        assert "enhanced_personality" in merged_data
        assert "brave" in merged_data["enhanced_personality"]

    def test_integrate_background_info(self, integrator):
        """Test integrating background information."""
        merged_data: Dict[str, Any] = {}
        profile_ctx = MockProfileContext(
            background_summary="War veteran",
            key_life_phases=["Childhood", "Military Service"],
        )

        integrator._integrate_profile_data(merged_data, profile_ctx)

        assert "enhanced_background" in merged_data
        assert merged_data["enhanced_background"]["background_summary"] == "War veteran"


class TestContextIntegratorStatsIntegration:
    """Test stats context integration."""

    @pytest.fixture
    def integrator(self):
        """Create a ContextIntegrator."""
        return ContextIntegrator()

    def test_integrate_combat_stats(self, integrator):
        """Test integrating combat stats."""
        merged_data: Dict[str, Any] = {}
        stats = Mock()
        stats.primary_stats = {"strength": 18, "agility": 14}
        stats_ctx = MockStatsContext(combat_stats=stats)

        integrator._integrate_stats_data(merged_data, stats_ctx)

        assert "enhanced_combat_stats" in merged_data

    def test_integrate_psychological_profile(self, integrator):
        """Test integrating psychological profile."""
        merged_data: Dict[str, Any] = {}
        profile = Mock()
        profile.traits = {"anxiety": 0.3, "confidence": 0.8}
        stats_ctx = MockStatsContext(psychological_profile=profile)

        integrator._integrate_stats_data(merged_data, stats_ctx)

        assert "enhanced_psychological_traits" in merged_data

    def test_integrate_quantified_relationships(self, integrator):
        """Test integrating quantified relationships."""
        merged_data: Dict[str, Any] = {}
        rel = Mock()
        rel.name = "Commander"
        rel.trust_level = 80
        rel.relationship_type = "superior"
        stats_ctx = MockStatsContext(relationships={"allies": [rel]})

        integrator._integrate_stats_data(merged_data, stats_ctx)

        assert "quantified_relationships" in merged_data
        assert "Commander" in merged_data["quantified_relationships"]


class TestContextIntegratorSummary:
    """Test summary generation."""

    @pytest.fixture
    def integrator(self):
        """Create a ContextIntegrator."""
        return ContextIntegrator()

    def test_get_integration_summary_no_context(self, integrator):
        """Test summary with no enhanced context."""
        merged_data: Dict[str, Any] = {}

        summary = integrator.get_integration_summary(merged_data)

        assert summary["integration_status"] == "no_context"
        assert summary["components"] == []

    def test_get_integration_summary_success(self, integrator):
        """Test summary with successful integration."""
        context = MockCharacterContext(
            character_name="Test",
            load_success=True,
        )
        merged_data: Dict[str, Any] = {
            "enhanced_context": context,
            "memory_context": {},
            "objectives_context": {},
            "profile_context": {},
            "stats_context": {},
            "behavioral_triggers": {"trigger1": {}},
            "active_objectives": {"obj1": {}},
            "enhanced_relationships": {"rel1": {}},
            "context_load_success": True,  # Required for "success" status
        }

        summary = integrator.get_integration_summary(merged_data)

        assert summary["integration_status"] == "success"
        assert "memory" in summary["components"]
        assert summary["behavioral_triggers_count"] == 1

    def test_get_integration_summary_partial(self, integrator):
        """Test summary with partial integration."""
        context = MockCharacterContext(
            character_name="Test",
            load_success=False,
        )
        merged_data: Dict[str, Any] = {
            "enhanced_context": context,
        }

        summary = integrator.get_integration_summary(merged_data)

        assert summary["integration_status"] == "partial"

    def test_get_integration_summary_error_handling(self, integrator):
        """Test summary error handling."""
        merged_data: Dict[str, Any] = None  # type: ignore

        summary = integrator.get_integration_summary(merged_data)  # type: ignore

        assert summary["integration_status"] == "error"


class TestContextIntegratorEdgeCases:
    """Test edge cases."""

    @pytest.fixture
    def integrator(self):
        """Create a ContextIntegrator."""
        return ContextIntegrator()

    def test_merge_with_none_context(self, integrator):
        """Test merging with None context."""
        existing_data = {"name": "Test"}

        # This should be handled gracefully
        result = integrator.merge_contexts(existing_data, None)  # type: ignore

        # Result should contain enhanced_context with None or handle gracefully
        assert "enhanced_context" in result or result == existing_data

    def test_integrate_memory_with_exception(self, integrator):
        """Test memory integration with exception."""
        merged_data: Dict[str, Any] = {}
        memory_ctx = Mock()
        memory_ctx.behavioral_triggers = None  # Will cause iteration error

        # Should not raise
        integrator._integrate_memory_data(merged_data, memory_ctx)

    def test_integrate_objectives_with_exception(self, integrator):
        """Test objectives integration with exception."""
        merged_data: Dict[str, Any] = {}
        objectives_ctx = Mock()
        objectives_ctx.core_objectives = None

        # Should not raise
        integrator._integrate_objectives_data(merged_data, objectives_ctx)

    def test_integrate_profile_with_exception(self, integrator):
        """Test profile integration with exception."""
        merged_data: Dict[str, Any] = {}
        profile_ctx = Mock()
        profile_ctx.emotional_drives = None

        # Should not raise
        integrator._integrate_profile_data(merged_data, profile_ctx)

    def test_integrate_stats_with_exception(self, integrator):
        """Test stats integration with exception."""
        merged_data: Dict[str, Any] = {}
        stats_ctx = Mock()
        stats_ctx.combat_stats = None

        # Should not raise
        integrator._integrate_stats_data(merged_data, stats_ctx)


class TestContextIntegratorIntegration:
    """Integration tests."""

    def test_full_integration_flow(self):
        """Test full context integration flow."""
        integrator = ContextIntegrator()

        # Existing character data
        existing_data = {
            "name": "Warrior",
            "faction": "Alliance",
            "level": 10,
        }

        # Create comprehensive context
        trigger = MockBehavioralTrigger(
            trigger_name="combat",
            trigger_conditions=["enemy present"],
            behavioral_response="aggressive",
        )
        relationship = MockRelationship(
            character_name="Commander",
            trust_level=MockTrustLevel(90),
        )
        event = MockFormativeEvent(
            event_name="Training",
            age=18,
            decision_influence="promotes discipline",
        )

        memory_ctx = MockMemoryContext(
            behavioral_triggers=[trigger],
            relationships=[relationship],
            formative_events=[event],
        )

        objective = MockObjective(
            name="Victory",
            priority=0.9,
            status=MockStatus("active"),
        )
        objectives_ctx = MockObjectivesContext(
            core_objectives=[objective],
        )

        drive = MockEmotionalDrive(
            name="honor",
            dominance_level="Dominant",
        )
        trait = MockPersonalityTrait(
            name="brave",
            score=0.9,
        )
        profile_ctx = MockProfileContext(
            emotional_drives=[drive],
            personality_traits=[trait],
            background_summary="Veteran warrior",
        )

        context = MockCharacterContext(
            character_name="Warrior",
            load_success=True,
            memory_context=memory_ctx,
            objectives_context=objectives_ctx,
            profile_context=profile_ctx,
            stats_context=MockStatsContext(),
        )

        # Merge contexts
        merged = integrator.merge_contexts(existing_data, context)

        # Verify all components were integrated
        assert "enhanced_context" in merged
        assert "behavioral_triggers" in merged
        assert "active_objectives" in merged
        assert "emotional_drives" in merged
        assert merged["name"] == "Warrior"  # Original data preserved

        # Check summary
        summary = integrator.get_integration_summary(merged)
        assert summary["integration_status"] == "success"
        assert len(summary["components"]) == 4
