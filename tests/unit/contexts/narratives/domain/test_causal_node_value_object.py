#!/usr/bin/env python3
"""
Comprehensive Unit Tests for CausalNode Value Objects

Test suite covering causal node creation, validation, business logic,
enums, properties, score calculations, relationship methods, and factory methods
in the Narrative Context domain layer.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from contexts.narratives.domain.value_objects.causal_node import (
    CausalNode,
    CausalRelationType,
    CausalStrength,
)


class TestCausalRelationTypeEnum:
    """Test suite for CausalRelationType enum."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_all_relation_types_exist(self):
        """Test that all expected relation types are defined."""
        expected_types = {
            "DIRECT_CAUSE",
            "INDIRECT_CAUSE",
            "NECESSARY_CONDITION",
            "SUFFICIENT_CONDITION",
            "CONTRIBUTING_FACTOR",
            "PREVENTING_FACTOR",
            "CATALYST",
            "INHIBITOR",
            "TRIGGER",
            "ENABLING_CONDITION",
            "COINCIDENTAL",
            "FEEDBACK_LOOP",
        }

        actual_types = {item.name for item in CausalRelationType}
        assert actual_types == expected_types

    @pytest.mark.unit
    def test_relation_type_string_values(self):
        """Test that relation type enum values have correct string representations."""
        assert CausalRelationType.DIRECT_CAUSE.value == "direct_cause"
        assert CausalRelationType.INDIRECT_CAUSE.value == "indirect_cause"
        assert CausalRelationType.NECESSARY_CONDITION.value == "necessary_condition"
        assert CausalRelationType.SUFFICIENT_CONDITION.value == "sufficient_condition"
        assert CausalRelationType.CONTRIBUTING_FACTOR.value == "contributing_factor"
        assert CausalRelationType.PREVENTING_FACTOR.value == "preventing_factor"
        assert CausalRelationType.CATALYST.value == "catalyst"
        assert CausalRelationType.INHIBITOR.value == "inhibitor"
        assert CausalRelationType.TRIGGER.value == "trigger"
        assert CausalRelationType.ENABLING_CONDITION.value == "enabling_condition"
        assert CausalRelationType.COINCIDENTAL.value == "coincidental"
        assert CausalRelationType.FEEDBACK_LOOP.value == "feedback_loop"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_relation_type_uniqueness(self):
        """Test that all relation type values are unique."""
        values = [item.value for item in CausalRelationType]
        assert len(values) == len(set(values))

    @pytest.mark.unit
    @pytest.mark.fast
    def test_relation_type_membership(self):
        """Test relation type membership operations."""
        assert CausalRelationType.DIRECT_CAUSE in CausalRelationType
        assert "direct_cause" == CausalRelationType.DIRECT_CAUSE.value
        assert CausalRelationType.DIRECT_CAUSE == CausalRelationType("direct_cause")


class TestCausalStrengthEnum:
    """Test suite for CausalStrength enum."""

    @pytest.mark.unit
    def test_all_strength_levels_exist(self):
        """Test that all expected strength levels are defined."""
        expected_levels = {
            "ABSOLUTE",
            "VERY_STRONG",
            "STRONG",
            "MODERATE",
            "WEAK",
            "VERY_WEAK",
            "NEGLIGIBLE",
        }
        actual_levels = {item.name for item in CausalStrength}
        assert actual_levels == expected_levels

    @pytest.mark.unit
    @pytest.mark.fast
    def test_strength_string_values(self):
        """Test that strength enum values have correct string representations."""
        assert CausalStrength.ABSOLUTE.value == "absolute"
        assert CausalStrength.VERY_STRONG.value == "very_strong"
        assert CausalStrength.STRONG.value == "strong"
        assert CausalStrength.MODERATE.value == "moderate"
        assert CausalStrength.WEAK.value == "weak"
        assert CausalStrength.VERY_WEAK.value == "very_weak"
        assert CausalStrength.NEGLIGIBLE.value == "negligible"

    @pytest.mark.unit
    def test_strength_logical_ordering(self):
        """Test that strength levels represent logical ordering."""
        strength_order = {
            CausalStrength.ABSOLUTE: 7,
            CausalStrength.VERY_STRONG: 6,
            CausalStrength.STRONG: 5,
            CausalStrength.MODERATE: 4,
            CausalStrength.WEAK: 3,
            CausalStrength.VERY_WEAK: 2,
            CausalStrength.NEGLIGIBLE: 1,
        }

        assert (
            strength_order[CausalStrength.ABSOLUTE]
            > strength_order[CausalStrength.VERY_STRONG]
        )
        assert (
            strength_order[CausalStrength.VERY_STRONG]
            > strength_order[CausalStrength.STRONG]
        )
        assert (
            strength_order[CausalStrength.STRONG]
            > strength_order[CausalStrength.MODERATE]
        )
        assert (
            strength_order[CausalStrength.MODERATE]
            > strength_order[CausalStrength.WEAK]
        )
        assert (
            strength_order[CausalStrength.WEAK]
            > strength_order[CausalStrength.VERY_WEAK]
        )
        assert (
            strength_order[CausalStrength.VERY_WEAK]
            > strength_order[CausalStrength.NEGLIGIBLE]
        )


class TestCausalNodeCreation:
    """Test suite for CausalNode creation and initialization."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_create_minimal_causal_node(self):
        """Test creating causal node with minimal required fields."""
        node = CausalNode(node_id="minimal-node-1", title="Minimal Node")

        assert node.node_id == "minimal-node-1"
        assert node.title == "Minimal Node"
        assert node.description == ""
        assert node.node_type == "event"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_causal_node_with_only_description(self):
        """Test creating causal node with only description (no title)."""
        node = CausalNode(
            node_id="desc-only-node", description="A node described without a title"
        )

        assert node.node_id == "desc-only-node"
        assert node.title == ""
        assert node.description == "A node described without a title"

    @pytest.mark.unit
    def test_create_comprehensive_causal_node(self):
        """Test creating causal node with all fields specified."""
        char_id = uuid4()
        creation_time = datetime.now(timezone.utc)

        node = CausalNode(
            node_id="comprehensive-node",
            event_id="story-event-123",
            plot_point_id="plot-point-456",
            character_id=char_id,
            title="Hero's Decision",
            description="The moment the hero decides to embark on the quest",
            node_type="decision",
            direct_causes={"mentor-advice", "village-threat"},
            direct_effects={"journey-start", "party-formation"},
            indirect_causes={"prophecy-revealed"},
            indirect_effects={"kingdom-salvation"},
            causal_relationships={
                "mentor-advice": {
                    "relationship_type": "trigger",
                    "strength": "strong",
                    "direction": "incoming",
                }
            },
            sequence_order=25,
            temporal_delay=5,
            duration=120,
            is_root_cause=False,
            is_terminal_effect=False,
            is_branch_point=True,
            is_convergence_point=True,
            occurrence_probability=Decimal("0.9"),
            causal_certainty=Decimal("0.8"),
            narrative_importance=Decimal("9.0"),
            character_impact_level=Decimal("8.5"),
            story_arc_impact=Decimal("9.5"),
            prerequisite_conditions={"hero-ready", "mentor-present"},
            blocking_conditions={"hero-imprisoned"},
            tags={"pivotal", "character-development", "quest-beginning"},
            narrative_context="The call to adventure moment",
            creation_timestamp=creation_time,
            metadata={"author_note": "Critical story turning point", "revision": 3},
        )

        assert node.node_id == "comprehensive-node"
        assert node.event_id == "story-event-123"
        assert node.plot_point_id == "plot-point-456"
        assert node.character_id == char_id
        assert node.title == "Hero's Decision"
        assert node.description == "The moment the hero decides to embark on the quest"
        assert node.node_type == "decision"
        assert node.direct_causes == {"mentor-advice", "village-threat"}
        assert node.direct_effects == {"journey-start", "party-formation"}
        assert node.indirect_causes == {"prophecy-revealed"}
        assert node.indirect_effects == {"kingdom-salvation"}
        assert "mentor-advice" in node.causal_relationships
        assert node.sequence_order == 25
        assert node.temporal_delay == 5
        assert node.duration == 120
        assert node.is_root_cause is False
        assert node.is_terminal_effect is False
        assert node.is_branch_point is True
        assert node.is_convergence_point is True
        assert node.occurrence_probability == Decimal("0.9")
        assert node.causal_certainty == Decimal("0.8")
        assert node.narrative_importance == Decimal("9.0")
        assert node.character_impact_level == Decimal("8.5")
        assert node.story_arc_impact == Decimal("9.5")
        assert node.prerequisite_conditions == {"hero-ready", "mentor-present"}
        assert node.blocking_conditions == {"hero-imprisoned"}
        assert node.tags == {"pivotal", "character-development", "quest-beginning"}
        assert node.narrative_context == "The call to adventure moment"
        assert node.creation_timestamp == creation_time
        assert node.metadata["author_note"] == "Critical story turning point"

    @pytest.mark.unit
    def test_default_values_initialization(self):
        """Test that default values are properly initialized."""
        node = CausalNode(node_id="default-test", title="Default Values Test")

        # Test default collections are empty
        assert node.direct_causes == set()
        assert node.direct_effects == set()
        assert node.indirect_causes == set()
        assert node.indirect_effects == set()
        assert node.causal_relationships == {}
        assert node.prerequisite_conditions == set()
        assert node.blocking_conditions == set()
        assert node.tags == set()
        assert node.metadata == {}

        # Test default values
        assert node.event_id is None
        assert node.plot_point_id is None
        assert node.character_id is None
        assert node.description == ""
        assert node.node_type == "event"
        assert node.sequence_order is None
        assert node.temporal_delay is None
        assert node.duration is None
        assert node.is_root_cause is False
        assert node.is_terminal_effect is False
        assert node.is_branch_point is False
        assert node.is_convergence_point is False
        assert node.occurrence_probability == Decimal("1.0")
        assert node.causal_certainty == Decimal("0.8")
        assert node.narrative_importance == Decimal("5.0")
        assert node.character_impact_level == Decimal("5.0")
        assert node.story_arc_impact == Decimal("5.0")
        assert node.narrative_context == ""

        # Test that creation timestamp was set
        assert node.creation_timestamp is not None
        assert isinstance(node.creation_timestamp, datetime)

    @pytest.mark.unit
    def test_frozen_dataclass_immutability(self):
        """Test that CausalNode is immutable (frozen dataclass)."""
        node = CausalNode(node_id="immutable-test", title="Immutable Test")

        # Should not be able to modify fields
        with pytest.raises(AttributeError):
            node.title = "Modified Title"

        with pytest.raises(AttributeError):
            node.node_type = "modified_type"

        with pytest.raises(AttributeError):
            node.occurrence_probability = Decimal("0.5")


class TestCausalNodeValidation:
    """Test suite for CausalNode validation logic."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_empty_node_id_validation(self):
        """Test validation fails with empty node ID."""
        with pytest.raises(ValueError, match="Causal node ID cannot be empty"):
            CausalNode(node_id="", title="Valid Title")

    @pytest.mark.unit
    @pytest.mark.unit
    def test_whitespace_only_node_id_validation(self):
        """Test validation fails with whitespace-only node ID."""
        with pytest.raises(ValueError, match="Causal node ID cannot be empty"):
            CausalNode(node_id="   ", title="Valid Title")

    @pytest.mark.unit
    def test_missing_title_and_description_validation(self):
        """Test validation fails when both title and description are empty."""
        with pytest.raises(
            ValueError, match="Causal node must have either title or description"
        ):
            CausalNode(node_id="no-content-test", title="", description="")

    @pytest.mark.unit
    def test_whitespace_only_title_and_description_validation(self):
        """Test validation fails when both title and description are whitespace only."""
        with pytest.raises(
            ValueError, match="Causal node must have either title or description"
        ):
            CausalNode(
                node_id="whitespace-content-test", title="   ", description="  \t\n  "
            )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_valid_with_only_title(self):
        """Test validation passes with only title."""
        node = CausalNode(
            node_id="title-only-test", title="Valid Title", description=""
        )
        assert node.title == "Valid Title"
        assert node.description == ""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_valid_with_only_description(self):
        """Test validation passes with only description."""
        node = CausalNode(
            node_id="desc-only-test", title="", description="Valid description"
        )
        assert node.title == ""
        assert node.description == "Valid description"

    @pytest.mark.unit
    @pytest.mark.unit
    def test_occurrence_probability_below_minimum_validation(self):
        """Test validation fails with occurrence probability below 0."""
        with pytest.raises(
            ValueError, match="Occurrence probability must be between 0 and 1"
        ):
            CausalNode(
                node_id="low-prob-test",
                title="Low Probability Test",
                occurrence_probability=Decimal("-0.1"),
            )

    @pytest.mark.unit
    def test_occurrence_probability_above_maximum_validation(self):
        """Test validation fails with occurrence probability above 1."""
        with pytest.raises(
            ValueError, match="Occurrence probability must be between 0 and 1"
        ):
            CausalNode(
                node_id="high-prob-test",
                title="High Probability Test",
                occurrence_probability=Decimal("1.1"),
            )

    @pytest.mark.unit
    def test_causal_certainty_boundary_validation(self):
        """Test causal certainty boundary validation."""
        with pytest.raises(
            ValueError, match="Causal certainty must be between 0 and 1"
        ):
            CausalNode(
                node_id="high-certainty-test",
                title="High Certainty Test",
                causal_certainty=Decimal("1.5"),
            )

        with pytest.raises(
            ValueError, match="Causal certainty must be between 0 and 1"
        ):
            CausalNode(
                node_id="low-certainty-test",
                title="Low Certainty Test",
                causal_certainty=Decimal("-0.2"),
            )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_valid_probability_boundary_values(self):
        """Test that boundary probability values (0 and 1) are valid."""
        node = CausalNode(
            node_id="boundary-prob-test",
            title="Boundary Probability Test",
            occurrence_probability=Decimal("0.0"),
            causal_certainty=Decimal("1.0"),
        )

        assert node.occurrence_probability == Decimal("0.0")
        assert node.causal_certainty == Decimal("1.0")

    @pytest.mark.unit
    def test_narrative_importance_below_minimum_validation(self):
        """Test validation fails with narrative importance below 1."""
        with pytest.raises(
            ValueError, match="narrative_importance must be between 1 and 10"
        ):
            CausalNode(
                node_id="low-importance-test",
                title="Low Importance Test",
                narrative_importance=Decimal("0.5"),
            )

    @pytest.mark.unit
    def test_narrative_importance_above_maximum_validation(self):
        """Test validation fails with narrative importance above 10."""
        with pytest.raises(
            ValueError, match="narrative_importance must be between 1 and 10"
        ):
            CausalNode(
                node_id="high-importance-test",
                title="High Importance Test",
                narrative_importance=Decimal("11.0"),
            )

    @pytest.mark.unit
    def test_character_impact_boundary_validation(self):
        """Test character impact level boundary validation."""
        with pytest.raises(
            ValueError, match="character_impact_level must be between 1 and 10"
        ):
            CausalNode(
                node_id="low-char-impact-test",
                title="Low Character Impact Test",
                character_impact_level=Decimal("0.9"),
            )

        with pytest.raises(
            ValueError, match="character_impact_level must be between 1 and 10"
        ):
            CausalNode(
                node_id="high-char-impact-test",
                title="High Character Impact Test",
                character_impact_level=Decimal("10.1"),
            )

    @pytest.mark.unit
    def test_story_arc_impact_boundary_validation(self):
        """Test story arc impact boundary validation."""
        with pytest.raises(
            ValueError, match="story_arc_impact must be between 1 and 10"
        ):
            CausalNode(
                node_id="low-arc-impact-test",
                title="Low Arc Impact Test",
                story_arc_impact=Decimal("0.5"),
            )

        with pytest.raises(
            ValueError, match="story_arc_impact must be between 1 and 10"
        ):
            CausalNode(
                node_id="high-arc-impact-test",
                title="High Arc Impact Test",
                story_arc_impact=Decimal("15.0"),
            )

    @pytest.mark.unit
    def test_valid_impact_boundary_values(self):
        """Test that boundary impact values (1 and 10) are valid."""
        node = CausalNode(
            node_id="boundary-impact-test",
            title="Boundary Impact Test",
            narrative_importance=Decimal("1.0"),
            character_impact_level=Decimal("10.0"),
            story_arc_impact=Decimal("5.5"),
        )

        assert node.narrative_importance == Decimal("1.0")
        assert node.character_impact_level == Decimal("10.0")
        assert node.story_arc_impact == Decimal("5.5")

    @pytest.mark.unit
    def test_negative_sequence_order_validation(self):
        """Test validation fails with negative sequence order."""
        with pytest.raises(ValueError, match="Sequence order must be non-negative"):
            CausalNode(
                node_id="negative-seq-test",
                title="Negative Sequence Test",
                sequence_order=-1,
            )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_zero_sequence_order_allowed(self):
        """Test that zero sequence order is allowed."""
        node = CausalNode(
            node_id="zero-seq-test", title="Zero Sequence Test", sequence_order=0
        )

        assert node.sequence_order == 0

    @pytest.mark.unit
    @pytest.mark.unit
    def test_negative_temporal_delay_validation(self):
        """Test validation fails with negative temporal delay."""
        with pytest.raises(ValueError, match="Temporal delay must be non-negative"):
            CausalNode(
                node_id="negative-delay-test",
                title="Negative Delay Test",
                temporal_delay=-5,
            )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_zero_temporal_delay_allowed(self):
        """Test that zero temporal delay is allowed."""
        node = CausalNode(
            node_id="zero-delay-test", title="Zero Delay Test", temporal_delay=0
        )

        assert node.temporal_delay == 0

    @pytest.mark.unit
    @pytest.mark.unit
    def test_zero_duration_validation(self):
        """Test validation fails with zero duration."""
        with pytest.raises(ValueError, match="Duration must be positive"):
            CausalNode(
                node_id="zero-duration-test", title="Zero Duration Test", duration=0
            )

    @pytest.mark.unit
    def test_negative_duration_validation(self):
        """Test validation fails with negative duration."""
        with pytest.raises(ValueError, match="Duration must be positive"):
            CausalNode(
                node_id="negative-duration-test",
                title="Negative Duration Test",
                duration=-10,
            )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_positive_duration_allowed(self):
        """Test that positive duration is allowed."""
        node = CausalNode(
            node_id="positive-duration-test",
            title="Positive Duration Test",
            duration=120,
        )

        assert node.duration == 120

    @pytest.mark.unit
    def test_string_length_validations(self):
        """Test string length constraint validations."""
        # Node ID too long
        with pytest.raises(
            ValueError, match="Node ID too long \\(max 100 characters\\)"
        ):
            CausalNode(node_id="x" * 101, title="Valid Title")

        # Title too long
        with pytest.raises(
            ValueError, match="Node title too long \\(max 200 characters\\)"
        ):
            CausalNode(node_id="valid-id", title="x" * 201)

        # Description too long
        with pytest.raises(
            ValueError, match="Node description too long \\(max 1000 characters\\)"
        ):
            CausalNode(node_id="valid-id", title="Valid Title", description="x" * 1001)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_valid_string_length_boundaries(self):
        """Test that maximum string length boundaries are valid."""
        node = CausalNode(node_id="x" * 100, title="x" * 200, description="x" * 1000)

        assert len(node.node_id) == 100
        assert len(node.title) == 200
        assert len(node.description) == 1000


class TestCausalNodeProperties:
    """Test suite for CausalNode property methods."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_total_causes_calculation(self):
        """Test total_causes property calculation."""
        node = CausalNode(
            node_id="causes-test",
            title="Causes Test",
            direct_causes={"cause1", "cause2"},
            indirect_causes={"cause3", "cause4", "cause5"},
        )

        assert node.total_causes == 5  # 2 direct + 3 indirect

    @pytest.mark.unit
    @pytest.mark.fast
    def test_total_effects_calculation(self):
        """Test total_effects property calculation."""
        node = CausalNode(
            node_id="effects-test",
            title="Effects Test",
            direct_effects={"effect1"},
            indirect_effects={"effect2", "effect3", "effect4", "effect5"},
        )

        assert node.total_effects == 5  # 1 direct + 4 indirect

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_causes_with_direct_causes(self):
        """Test has_causes returns True when direct causes exist."""
        node = CausalNode(
            node_id="direct-causes-test",
            title="Direct Causes Test",
            direct_causes={"cause1", "cause2"},
        )

        assert node.has_causes is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_causes_with_indirect_causes(self):
        """Test has_causes returns True when indirect causes exist."""
        node = CausalNode(
            node_id="indirect-causes-test",
            title="Indirect Causes Test",
            indirect_causes={"cause1"},
        )

        assert node.has_causes is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_causes_with_both_types(self):
        """Test has_causes returns True when both direct and indirect causes exist."""
        node = CausalNode(
            node_id="both-causes-test",
            title="Both Causes Test",
            direct_causes={"direct_cause"},
            indirect_causes={"indirect_cause"},
        )

        assert node.has_causes is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_causes_false(self):
        """Test has_causes returns False when no causes exist."""
        node = CausalNode(node_id="no-causes-test", title="No Causes Test")

        assert node.has_causes is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_effects_with_direct_effects(self):
        """Test has_effects returns True when direct effects exist."""
        node = CausalNode(
            node_id="direct-effects-test",
            title="Direct Effects Test",
            direct_effects={"effect1"},
        )

        assert node.has_effects is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_effects_with_indirect_effects(self):
        """Test has_effects returns True when indirect effects exist."""
        node = CausalNode(
            node_id="indirect-effects-test",
            title="Indirect Effects Test",
            indirect_effects={"effect1", "effect2"},
        )

        assert node.has_effects is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_effects_false(self):
        """Test has_effects returns False when no effects exist."""
        node = CausalNode(node_id="no-effects-test", title="No Effects Test")

        assert node.has_effects is False

    @pytest.mark.unit
    def test_is_isolated_true(self):
        """Test is_isolated returns True when node has no causal connections."""
        node = CausalNode(node_id="isolated-test", title="Isolated Node")

        assert node.is_isolated is True
        assert node.has_causes is False
        assert node.has_effects is False

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_is_isolated_false_with_causes(self):
        """Test is_isolated returns False when node has causes."""
        node = CausalNode(
            node_id="not-isolated-causes-test",
            title="Not Isolated - Has Causes",
            direct_causes={"some_cause"},
        )

        assert node.is_isolated is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_isolated_false_with_effects(self):
        """Test is_isolated returns False when node has effects."""
        node = CausalNode(
            node_id="not-isolated-effects-test",
            title="Not Isolated - Has Effects",
            direct_effects={"some_effect"},
        )

        assert node.is_isolated is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_isolated_false_with_both(self):
        """Test is_isolated returns False when node has both causes and effects."""
        node = CausalNode(
            node_id="connected-test",
            title="Connected Node",
            direct_causes={"cause"},
            direct_effects={"effect"},
        )

        assert node.is_isolated is False


class TestCausalComplexityScore:
    """Test suite for causal complexity score calculation."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_base_complexity_only(self):
        """Test complexity score with only causal relationships (no bonuses)."""
        node = CausalNode(
            node_id="base-complexity-test",
            title="Base Complexity",
            direct_causes={"cause1", "cause2"},
            indirect_effects={"effect1"},
        )

        # Expected: 3 (2 direct causes + 1 indirect effect) + 0 bonuses = 3.0
        assert node.causal_complexity_score == Decimal("3.0")

    @pytest.mark.unit
    def test_complexity_with_special_node_types(self):
        """Test complexity score with special node type bonuses."""
        node = CausalNode(
            node_id="special-types-test",
            title="Special Node Types",
            direct_causes={"cause1"},
            direct_effects={"effect1"},
            is_branch_point=True,
            is_convergence_point=True,
            is_root_cause=True,
            is_terminal_effect=True,
        )

        # Expected: 2 (1 cause + 1 effect) + 2 (branch) + 2 (convergence) + 1 (root) + 1 (terminal) = 8.0
        assert node.causal_complexity_score == Decimal("8.0")

    @pytest.mark.unit
    @pytest.mark.fast
    def test_complexity_with_conditions(self):
        """Test complexity score with prerequisite and blocking conditions."""
        node = CausalNode(
            node_id="conditions-test",
            title="Conditions Test",
            direct_effects={"effect1"},
            prerequisite_conditions={"prereq1", "prereq2"},
            blocking_conditions={"block1", "block2", "block3"},
        )

        # Expected: 1 (1 effect) + 0 (no special types) + ((2 + 3) * 0.5) = 1.0 + 2.5 = 3.5
        assert node.causal_complexity_score == Decimal("3.5")

    @pytest.mark.unit
    def test_complexity_comprehensive_calculation(self):
        """Test complexity score with all bonuses combined."""
        node = CausalNode(
            node_id="comprehensive-complexity-test",
            title="Comprehensive Complexity",
            direct_causes={"cause1", "cause2", "cause3"},
            indirect_causes={"indirect1"},
            direct_effects={"effect1", "effect2"},
            indirect_effects={"indirect_effect1"},
            is_branch_point=True,
            is_convergence_point=True,
            prerequisite_conditions={"prereq1"},
            blocking_conditions={"block1", "block2"},
        )

        # Expected: 7 (3+1+2+1 relationships) + 2 (branch) + 2 (convergence) + ((1+2) * 0.5) = 7 + 2 + 2 + 1.5 = 12.5
        assert node.causal_complexity_score == Decimal("12.5")

    @pytest.mark.unit
    def test_complexity_isolated_node(self):
        """Test complexity score for isolated node with no connections."""
        node = CausalNode(node_id="isolated-complexity-test", title="Isolated Node")

        # Expected: 0 (no relationships) + 0 (no special types) + 0 (no conditions) = 0.0
        assert node.causal_complexity_score == Decimal("0.0")


class TestOverallImpactScore:
    """Test suite for overall impact score calculation."""

    @pytest.mark.unit
    @pytest.mark.fast
    def test_impact_score_default_values(self):
        """Test impact score with default impact values."""
        node = CausalNode(
            node_id="default-impact-test",
            title="Default Impact",
            # All impact values default to 5.0
        )

        # Expected: (5.0 * 0.4) + (5.0 * 0.3) + (5.0 * 0.3) = 2.0 + 1.5 + 1.5 = 5.0
        assert node.overall_impact_score == Decimal("5.0")

    @pytest.mark.unit
    @pytest.mark.fast
    def test_impact_score_maximum_values(self):
        """Test impact score with maximum impact values."""
        node = CausalNode(
            node_id="max-impact-test",
            title="Maximum Impact",
            narrative_importance=Decimal("10.0"),
            character_impact_level=Decimal("10.0"),
            story_arc_impact=Decimal("10.0"),
        )

        # Expected: (10.0 * 0.4) + (10.0 * 0.3) + (10.0 * 0.3) = 4.0 + 3.0 + 3.0 = 10.0
        assert node.overall_impact_score == Decimal("10.0")

    @pytest.mark.unit
    @pytest.mark.fast
    def test_impact_score_minimum_values(self):
        """Test impact score with minimum impact values."""
        node = CausalNode(
            node_id="min-impact-test",
            title="Minimum Impact",
            narrative_importance=Decimal("1.0"),
            character_impact_level=Decimal("1.0"),
            story_arc_impact=Decimal("1.0"),
        )

        # Expected: (1.0 * 0.4) + (1.0 * 0.3) + (1.0 * 0.3) = 0.4 + 0.3 + 0.3 = 1.0
        assert node.overall_impact_score == Decimal("1.0")

    @pytest.mark.unit
    @pytest.mark.fast
    def test_impact_score_weighted_calculation(self):
        """Test impact score with different weighted values."""
        node = CausalNode(
            node_id="weighted-impact-test",
            title="Weighted Impact",
            narrative_importance=Decimal("8.0"),  # 40% weight
            character_impact_level=Decimal("6.0"),  # 30% weight
            story_arc_impact=Decimal("4.0"),  # 30% weight
        )

        # Expected: (8.0 * 0.4) + (6.0 * 0.3) + (4.0 * 0.3) = 3.2 + 1.8 + 1.2 = 6.2
        assert node.overall_impact_score == Decimal("6.2")


class TestCausalNodeInstanceMethods:
    """Test suite for CausalNode instance methods."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_causes_node_direct_effect(self):
        """Test causes_node returns True for direct effects."""
        node = CausalNode(
            node_id="causes-direct-test",
            title="Direct Causes Test",
            direct_effects={"effect1", "effect2"},
        )

        assert node.causes_node("effect1") is True
        assert node.causes_node("effect2") is True
        assert node.causes_node("non_effect") is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_causes_node_indirect_effect(self):
        """Test causes_node returns True for indirect effects."""
        node = CausalNode(
            node_id="causes-indirect-test",
            title="Indirect Causes Test",
            indirect_effects={"indirect_effect1", "indirect_effect2"},
        )

        assert node.causes_node("indirect_effect1") is True
        assert node.causes_node("indirect_effect2") is True
        assert node.causes_node("non_effect") is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_causes_node_both_types(self):
        """Test causes_node returns True for both direct and indirect effects."""
        node = CausalNode(
            node_id="causes-both-test",
            title="Both Effects Test",
            direct_effects={"direct_effect"},
            indirect_effects={"indirect_effect"},
        )

        assert node.causes_node("direct_effect") is True
        assert node.causes_node("indirect_effect") is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_caused_by_node_direct_cause(self):
        """Test caused_by_node returns True for direct causes."""
        node = CausalNode(
            node_id="caused-by-direct-test",
            title="Direct Caused By Test",
            direct_causes={"cause1", "cause2"},
        )

        assert node.caused_by_node("cause1") is True
        assert node.caused_by_node("cause2") is True
        assert node.caused_by_node("non_cause") is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_caused_by_node_indirect_cause(self):
        """Test caused_by_node returns True for indirect causes."""
        node = CausalNode(
            node_id="caused-by-indirect-test",
            title="Indirect Caused By Test",
            indirect_causes={"indirect_cause1"},
        )

        assert node.caused_by_node("indirect_cause1") is True
        assert node.caused_by_node("non_cause") is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_directly_causes_node(self):
        """Test directly_causes_node only checks direct effects."""
        node = CausalNode(
            node_id="directly-causes-test",
            title="Directly Causes Test",
            direct_effects={"direct_effect"},
            indirect_effects={"indirect_effect"},
        )

        assert node.directly_causes_node("direct_effect") is True
        assert node.directly_causes_node("indirect_effect") is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_directly_caused_by_node(self):
        """Test directly_caused_by_node only checks direct causes."""
        node = CausalNode(
            node_id="directly-caused-by-test",
            title="Directly Caused By Test",
            direct_causes={"direct_cause"},
            indirect_causes={"indirect_cause"},
        )

        assert node.directly_caused_by_node("direct_cause") is True
        assert node.directly_caused_by_node("indirect_cause") is False

    @pytest.mark.unit
    def test_get_relationship_info_existing(self):
        """Test get_relationship_info returns correct info for existing relationship."""
        relationship_data = {
            "relationship_type": "trigger",
            "strength": "strong",
            "direction": "incoming",
        }

        node = CausalNode(
            node_id="relationship-info-test",
            title="Relationship Info Test",
            causal_relationships={"related_node": relationship_data},
        )

        info = node.get_relationship_info("related_node")
        assert info == relationship_data
        assert info["relationship_type"] == "trigger"
        assert info["strength"] == "strong"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_relationship_info_non_existing(self):
        """Test get_relationship_info returns None for non-existing relationship."""
        node = CausalNode(node_id="no-relationship-test", title="No Relationship Test")

        info = node.get_relationship_info("non_existing_node")
        assert info is None

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_get_relationship_type_existing(self):
        """Test get_relationship_type returns correct enum for existing relationship."""
        node = CausalNode(
            node_id="relationship-type-test",
            title="Relationship Type Test",
            causal_relationships={
                "node1": {"relationship_type": "direct_cause", "strength": "strong"}
            },
        )

        rel_type = node.get_relationship_type("node1")
        assert rel_type == CausalRelationType.DIRECT_CAUSE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_relationship_type_non_existing(self):
        """Test get_relationship_type returns None for non-existing relationship."""
        node = CausalNode(node_id="no-rel-type-test", title="No Relationship Type Test")

        rel_type = node.get_relationship_type("non_existing")
        assert rel_type is None

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_get_relationship_strength_existing(self):
        """Test get_relationship_strength returns correct enum for existing relationship."""
        node = CausalNode(
            node_id="relationship-strength-test",
            title="Relationship Strength Test",
            causal_relationships={
                "node1": {"relationship_type": "catalyst", "strength": "very_strong"}
            },
        )

        strength = node.get_relationship_strength("node1")
        assert strength == CausalStrength.VERY_STRONG

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_relationship_strength_non_existing(self):
        """Test get_relationship_strength returns None for non-existing relationship."""
        node = CausalNode(
            node_id="no-rel-strength-test", title="No Relationship Strength Test"
        )

        strength = node.get_relationship_strength("non_existing")
        assert strength is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_prerequisite_condition_true(self):
        """Test has_prerequisite_condition returns True for existing condition."""
        node = CausalNode(
            node_id="prereq-test",
            title="Prerequisite Test",
            prerequisite_conditions={"condition1", "condition2"},
        )

        assert node.has_prerequisite_condition("condition1") is True
        assert node.has_prerequisite_condition("condition2") is True
        assert node.has_prerequisite_condition("non_existing") is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_blocking_condition_true(self):
        """Test has_blocking_condition returns True for existing condition."""
        node = CausalNode(
            node_id="blocking-test",
            title="Blocking Test",
            blocking_conditions={"blocker1", "blocker2"},
        )

        assert node.has_blocking_condition("blocker1") is True
        assert node.has_blocking_condition("blocker2") is True
        assert node.has_blocking_condition("non_existing") is False

    @pytest.mark.unit
    def test_get_causal_context(self):
        """Test get_causal_context returns comprehensive context dict."""
        node = CausalNode(
            node_id="context-test",
            title="Context Test Node",
            node_type="decision",
            sequence_order=42,
            direct_causes={"cause1", "cause2"},
            direct_effects={"effect1"},
            is_root_cause=True,
            is_branch_point=True,
            occurrence_probability=Decimal("0.75"),
            causal_certainty=Decimal("0.9"),
            prerequisite_conditions={"prereq1"},
            blocking_conditions={"block1", "block2"},
        )

        context = node.get_causal_context()

        assert context["node_id"] == "context-test"
        assert context["node_type"] == "decision"
        assert context["title"] == "Context Test Node"
        assert context["sequence_order"] == 42
        assert context["is_root_cause"] is True
        assert context["is_terminal_effect"] is False
        assert context["is_branch_point"] is True
        assert context["is_convergence_point"] is False
        assert context["total_causes"] == 2
        assert context["total_effects"] == 1
        assert isinstance(context["causal_complexity"], float)
        assert isinstance(context["overall_impact"], float)
        assert context["occurrence_probability"] == 0.75
        assert context["causal_certainty"] == 0.9
        assert context["has_prerequisites"] is True
        assert context["has_blocking_conditions"] is True
        assert context["is_isolated"] is False


class TestCausalNodeFactoryMethods:
    """Test suite for CausalNode factory methods."""

    @pytest.mark.unit
    @pytest.mark.unit
    def test_with_additional_cause_direct_cause(self):
        """Test adding direct cause relationship."""
        original = CausalNode(
            node_id="add-cause-test",
            title="Add Cause Test",
            direct_causes={"existing_cause"},
        )

        updated = original.with_additional_cause(
            "new_cause", CausalRelationType.DIRECT_CAUSE, CausalStrength.STRONG
        )

        # New cause should be added
        assert "new_cause" in updated.direct_causes
        assert "existing_cause" in updated.direct_causes
        assert len(updated.direct_causes) == 2

        # Relationship info should be added
        assert "new_cause" in updated.causal_relationships
        rel_info = updated.causal_relationships["new_cause"]
        assert rel_info["relationship_type"] == "direct_cause"
        assert rel_info["strength"] == "strong"
        assert rel_info["direction"] == "incoming"

        # Should no longer be root cause
        assert updated.is_root_cause is False

        # Should be convergence point if multiple direct causes
        assert updated.is_convergence_point is True

    @pytest.mark.unit
    def test_with_additional_cause_non_direct_relationship(self):
        """Test adding non-direct cause relationship."""
        original = CausalNode(node_id="add-catalyst-test", title="Add Catalyst Test")

        updated = original.with_additional_cause(
            "catalyst_node", CausalRelationType.CATALYST, CausalStrength.MODERATE
        )

        # Direct causes should not be modified for non-direct relationships
        assert len(updated.direct_causes) == 0

        # But relationship info should still be added
        assert "catalyst_node" in updated.causal_relationships
        rel_info = updated.causal_relationships["catalyst_node"]
        assert rel_info["relationship_type"] == "catalyst"
        assert rel_info["strength"] == "moderate"
        assert rel_info["direction"] == "incoming"

    @pytest.mark.unit
    def test_with_additional_cause_immutability(self):
        """Test that original node remains unchanged."""
        original = CausalNode(
            node_id="immutable-add-test",
            title="Immutable Add Test",
            direct_causes={"original_cause"},
        )

        updated = original.with_additional_cause("new_cause")

        # Original should remain unchanged
        assert len(original.direct_causes) == 1
        assert "new_cause" not in original.direct_causes
        assert "new_cause" not in original.causal_relationships
        assert original.is_root_cause is False  # was False from start

        # Updated should have new cause
        assert "new_cause" in updated.direct_causes
        assert len(updated.direct_causes) == 2

        # They should be different objects
        assert original is not updated

    @pytest.mark.unit
    def test_with_additional_cause_collections_copied(self):
        """Test that collections are properly copied in new instance."""
        original = CausalNode(
            node_id="collection-copy-test",
            title="Collection Copy Test",
            direct_causes={"cause1"},
            direct_effects={"effect1"},
            tags={"tag1", "tag2"},
            prerequisite_conditions={"prereq1"},
        )

        updated = original.with_additional_cause("cause2")

        # Verify collections have correct values (identity not checked for immutable frozensets)
        assert updated.direct_effects == original.direct_effects
        assert updated.tags == original.tags
        assert updated.prerequisite_conditions == original.prerequisite_conditions

        # Direct causes should be different (new cause added)
        assert updated.direct_causes != original.direct_causes
        assert updated.direct_causes is not original.direct_causes

    @pytest.mark.unit
    @pytest.mark.fast
    def test_with_additional_cause_first_cause_makes_convergence(self):
        """Test that adding second direct cause sets convergence point."""
        original = CausalNode(
            node_id="convergence-test",
            title="Convergence Test",
            direct_causes={"first_cause"},
            is_convergence_point=False,
        )

        updated = original.with_additional_cause("second_cause")

        # Should become convergence point with 2+ direct causes
        assert updated.is_convergence_point is True
        assert len(updated.direct_causes) == 2

    @pytest.mark.unit
    def test_with_additional_cause_preserves_metadata(self):
        """Test that metadata and timestamps are preserved."""
        creation_time = datetime.now(timezone.utc)
        metadata = {"version": 1, "author": "test"}

        original = CausalNode(
            node_id="metadata-preserve-test",
            title="Metadata Preserve Test",
            creation_timestamp=creation_time,
            metadata=metadata,
        )

        updated = original.with_additional_cause("preserving_cause")

        # Timestamp should be preserved
        assert updated.creation_timestamp == creation_time
        # Metadata should be copied
        assert updated.metadata == metadata
        assert updated.metadata is not original.metadata


class TestCausalNodeStringRepresentation:
    """Test suite for CausalNode string representation methods."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_str_representation_with_title(self):
        """Test human-readable string representation with title."""
        node = CausalNode(
            node_id="str-test",
            title="Hero's Decision",
            direct_causes={"mentor", "threat"},
            direct_effects={"quest", "journey", "growth"},
        )

        str_repr = str(node)
        expected = "CausalNode('Hero's Decision', causes=2, effects=3)"
        assert str_repr == expected

    @pytest.mark.unit
    @pytest.mark.fast
    def test_str_representation_no_title(self):
        """Test human-readable string representation without title."""
        node = CausalNode(
            node_id="no-title-test",
            description="A node without a title",
            direct_causes={"cause1"},
            indirect_effects={"effect1"},
        )

        str_repr = str(node)
        expected = "CausalNode('no-title-test', causes=1, effects=1)"
        assert str_repr == expected

    @pytest.mark.unit
    def test_repr_representation(self):
        """Test developer representation for debugging."""
        node = CausalNode(
            node_id="repr-test-id",
            title="Debug Node",
            node_type="decision",
            direct_causes={"cause1", "cause2"},
            indirect_effects={"effect1"},
        )

        repr_str = repr(node)
        expected = (
            "CausalNode(id='repr-test-id', "
            "type='decision', "
            "title='Debug Node', "
            "causes=2, "
            "effects=1)"
        )
        assert repr_str == expected

    @pytest.mark.unit
    def test_string_representations_different(self):
        """Test that str and repr provide different information."""
        node = CausalNode(
            node_id="different-repr-test",
            title="Different Representation",
            node_type="action",
        )

        str_repr = str(node)
        repr_str = repr(node)

        # They should be different
        assert str_repr != repr_str
        # str should be more human-readable
        assert "Different Representation" in str_repr
        # repr should include more technical details
        assert "different-repr-test" in repr_str
        assert "action" in repr_str


class TestCausalNodeEdgeCasesAndBoundaryConditions:
    """Test suite for edge cases and boundary conditions."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_creation_with_fixed_timestamp(self):
        """Test creation with explicitly set timestamp."""
        fixed_time = datetime(2024, 8, 15, 10, 30, 45, tzinfo=timezone.utc)

        node = CausalNode(
            node_id="timestamp-test",
            title="Fixed Timestamp",
            creation_timestamp=fixed_time,
        )

        assert node.creation_timestamp == fixed_time

    @pytest.mark.unit
    def test_large_collections_handling(self):
        """Test handling of large collections."""
        many_direct_causes = {f"direct_cause_{i}" for i in range(50)}
        many_indirect_causes = {f"indirect_cause_{i}" for i in range(30)}
        many_direct_effects = {f"direct_effect_{i}" for i in range(40)}
        many_indirect_effects = {f"indirect_effect_{i}" for i in range(25)}
        many_prereqs = {f"prereq_{i}" for i in range(20)}
        many_blockers = {f"blocker_{i}" for i in range(15)}
        many_tags = {f"tag_{i}" for i in range(35)}
        large_relationships = {
            f"node_{i}": {
                "relationship_type": "contributing_factor",
                "strength": "moderate",
                "direction": "incoming",
            }
            for i in range(10)
        }

        node = CausalNode(
            node_id="large-collections-test",
            title="Complex Causal Node",
            direct_causes=many_direct_causes,
            indirect_causes=many_indirect_causes,
            direct_effects=many_direct_effects,
            indirect_effects=many_indirect_effects,
            causal_relationships=large_relationships,
            prerequisite_conditions=many_prereqs,
            blocking_conditions=many_blockers,
            tags=many_tags,
        )

        assert len(node.direct_causes) == 50
        assert len(node.indirect_causes) == 30
        assert len(node.direct_effects) == 40
        assert len(node.indirect_effects) == 25
        assert len(node.prerequisite_conditions) == 20
        assert len(node.blocking_conditions) == 15
        assert len(node.tags) == 35
        assert len(node.causal_relationships) == 10
        assert node.total_causes == 80  # 50 + 30
        assert node.total_effects == 65  # 40 + 25
        assert node.has_causes is True
        assert node.has_effects is True
        assert node.is_isolated is False

    @pytest.mark.unit
    def test_decimal_precision_handling(self):
        """Test handling of decimal precision for probability and impact values."""
        node = CausalNode(
            node_id="precision-test",
            title="Precision Test",
            occurrence_probability=Decimal("0.123456789"),
            causal_certainty=Decimal("0.987654321"),
            narrative_importance=Decimal("7.123456789"),
            character_impact_level=Decimal("8.987654321"),
            story_arc_impact=Decimal("9.555555555"),
        )

        # Values should maintain precision
        assert node.occurrence_probability == Decimal("0.123456789")
        assert node.causal_certainty == Decimal("0.987654321")
        assert node.narrative_importance == Decimal("7.123456789")
        assert node.character_impact_level == Decimal("8.987654321")
        assert node.story_arc_impact == Decimal("9.555555555")

        # Scores should use precise calculation
        complexity_score = node.causal_complexity_score
        impact_score = node.overall_impact_score
        assert isinstance(complexity_score, Decimal)
        assert isinstance(impact_score, Decimal)

    @pytest.mark.unit
    def test_unicode_text_handling(self):
        """Test handling of unicode characters in text fields."""
        node = CausalNode(
            node_id="unicode-test-🎭",
            title="決定的な瞬間 Critical Moment 🎯",
            description="A pivotal causal event: αβγ 中文 العربية русский 🌟",
            node_type="événement",
            narrative_context="Context with émojis and 中文字符 ⚡",
        )

        assert "🎭" in node.node_id
        assert "決定的な瞬間" in node.title
        assert "🎯" in node.title
        assert "αβγ" in node.description
        assert "العربية" in node.description
        assert "🌟" in node.description
        assert "événement" in node.node_type
        assert "émojis" in node.narrative_context
        assert "⚡" in node.narrative_context

    @pytest.mark.unit
    def test_complex_metadata_handling(self):
        """Test handling of complex metadata structures."""
        complex_metadata = {
            "causal_analysis": {
                "confidence_intervals": {
                    "occurrence": [0.7, 0.9],
                    "impact": [6.5, 8.5],
                },
                "alternative_paths": [
                    {"path": "alternative_1", "probability": 0.3},
                    {"path": "alternative_2", "probability": 0.2},
                ],
            },
            "research_notes": {
                "sources": ["Aristotle", "Hume", "Pearl"],
                "methodology": "Bayesian causal inference",
            },
            "unicode_metadata_🔬": {
                "researcher": "José García-López",
                "institution": "Université de Montréal",
                "keywords": ["因果関係", "causality", "السببية"],
            },
        }

        node = CausalNode(
            node_id="complex-metadata-test",
            title="Research Node",
            description="Node for causal research",
            metadata=complex_metadata,
        )

        # Should store complex metadata as-is
        assert node.metadata == complex_metadata
        assert node.metadata["causal_analysis"]["confidence_intervals"][
            "occurrence"
        ] == [0.7, 0.9]
        assert node.metadata["unicode_metadata_🔬"]["researcher"] == "José García-López"
        assert "因果関係" in node.metadata["unicode_metadata_🔬"]["keywords"]


class TestCausalNodeCollectionsAndComparison:
    """Test suite for CausalNode behavior in collections and comparisons."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_nodes_in_list(self):
        """Test CausalNode objects in list operations."""
        node1 = CausalNode(node_id="list-test-1", title="First Node")

        node2 = CausalNode(node_id="list-test-2", title="Second Node")

        node_list = [node1, node2]

        assert len(node_list) == 2
        assert node1 in node_list
        assert node2 in node_list

    @pytest.mark.unit
    def test_nodes_sorting_by_complexity_score(self):
        """Test sorting CausalNode objects by causal complexity score."""
        nodes = [
            CausalNode(
                node_id=f"sort-test-{i}",
                title=f"Node {i}",
                direct_causes=set(f"cause_{j}" for j in range(causes)),
                direct_effects=set(f"effect_{j}" for j in range(effects)),
                is_branch_point=is_branch,
                prerequisite_conditions=set(f"prereq_{j}" for j in range(prereqs)),
            )
            for i, (causes, effects, is_branch, prereqs) in enumerate(
                [
                    (1, 0, False, 0),  # Simple node
                    (3, 2, True, 1),  # Complex node
                    (0, 1, False, 0),  # Simple node
                    (2, 3, True, 2),  # Very complex node
                ]
            )
        ]

        sorted_nodes = sorted(
            nodes, key=lambda n: n.causal_complexity_score, reverse=True
        )

        # Most complex should be first
        assert (
            sorted_nodes[0].causal_complexity_score
            >= sorted_nodes[1].causal_complexity_score
        )
        assert (
            sorted_nodes[1].causal_complexity_score
            >= sorted_nodes[2].causal_complexity_score
        )
        assert (
            sorted_nodes[2].causal_complexity_score
            >= sorted_nodes[3].causal_complexity_score
        )

    @pytest.mark.unit
    @pytest.mark.fast
    def test_node_equality_identity(self):
        """Test that identical CausalNode objects are considered equal."""
        node1 = CausalNode(
            node_id="equality-test", title="Equal Node", node_type="action"
        )

        node2 = CausalNode(
            node_id="equality-test", title="Equal Node", node_type="action"
        )

        # Frozen dataclasses with same values should be equal
        assert node1 == node2
        # But they should be different objects
        assert node1 is not node2

    @pytest.mark.unit
    @pytest.mark.fast
    def test_node_inequality(self):
        """Test that different CausalNode objects are not equal."""
        node1 = CausalNode(node_id="different-1", title="First Node")

        node2 = CausalNode(node_id="different-2", title="Second Node")

        assert node1 != node2
        assert not (node1 == node2)

    @pytest.mark.unit
    @pytest.mark.unit
    def test_node_hashing_consistency(self):
        """Test that equal CausalNode objects have same hash."""
        node1 = CausalNode(
            node_id="hash-test",
            title="Hash Test Node",
            occurrence_probability=Decimal("0.5"),
        )

        node2 = CausalNode(
            node_id="hash-test",
            title="Hash Test Node",
            occurrence_probability=Decimal("0.5"),
        )

        # Equal objects should have equal hashes
        assert node1 == node2
        assert hash(node1) == hash(node2)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_nodes_in_set(self):
        """Test CausalNode objects in set operations."""
        node1 = CausalNode(node_id="set-test-1", title="First Set Node")

        node2 = CausalNode(node_id="set-test-2", title="Second Set Node")

        # Identical node
        node1_duplicate = CausalNode(node_id="set-test-1", title="First Set Node")

        node_set = {node1, node2, node1_duplicate}

        # Set should deduplicate identical objects
        assert len(node_set) == 2  # node1 and node1_duplicate are the same
        assert node1 in node_set
        assert node2 in node_set
        assert node1_duplicate in node_set  # Should find node1

    @pytest.mark.unit
    @pytest.mark.fast
    def test_nodes_as_dict_keys(self):
        """Test using CausalNode objects as dictionary keys."""
        node1 = CausalNode(node_id="dict-key-1", title="Key Node One")

        node2 = CausalNode(node_id="dict-key-2", title="Key Node Two")

        node_dict = {node1: "first_node_data", node2: "second_node_data"}

        assert node_dict[node1] == "first_node_data"
        assert node_dict[node2] == "second_node_data"

        # Test with equivalent node
        equivalent_node1 = CausalNode(node_id="dict-key-1", title="Key Node One")

        # Should find the same entry
        assert node_dict[equivalent_node1] == "first_node_data"
