#!/usr/bin/env python3
"""
Unit tests for Character Goal Value Object and Aggregate Integration

Comprehensive test suite for the CharacterGoal value object and its
integration with the Character aggregate.
"""

import sys
from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()
event_bus_mock = MagicMock()
event_mock = MagicMock()
event_mock.return_value = Mock()
event_bus_mock.Event = event_mock
sys.modules["src.events.event_bus"] = event_bus_mock

from src.contexts.character.domain.value_objects.character_goal import (
    CharacterGoal,
    GoalStatus,
    GoalUrgency,
)


class TestCharacterGoalValueObject:
    """Test suite for CharacterGoal value object."""

    @pytest.mark.unit
    def test_goal_creation_success(self):
        """Test successful goal creation with all fields."""
        goal = CharacterGoal(
            description="Find the lost artifact",
            status=GoalStatus.ACTIVE,
            urgency=GoalUrgency.HIGH,
        )

        assert goal.description == "Find the lost artifact"
        assert goal.status == GoalStatus.ACTIVE
        assert goal.urgency == GoalUrgency.HIGH
        assert isinstance(goal.created_at, datetime)
        assert goal.completed_at is None
        assert isinstance(goal.goal_id, str)
        assert len(goal.goal_id) > 0

    @pytest.mark.unit
    def test_goal_creation_with_factory(self):
        """Test goal creation using factory method."""
        goal = CharacterGoal.create(
            description="Defeat the dragon",
            urgency=GoalUrgency.CRITICAL,
        )

        assert goal.description == "Defeat the dragon"
        assert goal.status == GoalStatus.ACTIVE
        assert goal.urgency == GoalUrgency.CRITICAL
        assert goal.completed_at is None

    @pytest.mark.unit
    def test_goal_creation_minimal(self):
        """Test goal creation with minimal required fields."""
        goal = CharacterGoal(description="A simple goal")

        assert goal.description == "A simple goal"
        assert goal.status == GoalStatus.ACTIVE
        assert goal.urgency == GoalUrgency.MEDIUM
        assert goal.completed_at is None

    @pytest.mark.unit
    def test_goal_creation_with_string_status(self):
        """Test that string status is converted to GoalStatus enum."""
        goal = CharacterGoal(
            description="Test goal",
            status="COMPLETED",
            urgency=GoalUrgency.LOW,
            completed_at=datetime.now(),
        )

        assert goal.status == GoalStatus.COMPLETED

    @pytest.mark.unit
    def test_goal_creation_with_string_urgency(self):
        """Test that string urgency is converted to GoalUrgency enum."""
        goal = CharacterGoal(
            description="Test goal",
            urgency="HIGH",
        )

        assert goal.urgency == GoalUrgency.HIGH

    # ==================== Validation Tests ====================

    @pytest.mark.unit
    def test_goal_invalid_empty_description(self):
        """Test that empty description raises ValueError."""
        with pytest.raises(ValueError, match="description cannot be empty"):
            CharacterGoal(description="   ")

    @pytest.mark.unit
    def test_goal_invalid_description_type(self):
        """Test that non-string description raises TypeError."""
        with pytest.raises(TypeError, match="description must be a string"):
            CharacterGoal(description=123)

    @pytest.mark.unit
    def test_goal_invalid_status(self):
        """Test that invalid status raises ValueError."""
        with pytest.raises(ValueError, match="Invalid status"):
            CharacterGoal(
                description="Test goal",
                status="INVALID_STATUS",
            )

    @pytest.mark.unit
    def test_goal_invalid_urgency(self):
        """Test that invalid urgency raises ValueError."""
        with pytest.raises(ValueError, match="Invalid urgency"):
            CharacterGoal(
                description="Test goal",
                urgency="INVALID_URGENCY",
            )

    @pytest.mark.unit
    def test_goal_active_with_completed_at(self):
        """Test that active goal with completed_at raises ValueError."""
        with pytest.raises(
            ValueError, match="Active goals should not have a completed_at timestamp"
        ):
            CharacterGoal(
                description="Test goal",
                status=GoalStatus.ACTIVE,
                completed_at=datetime.now(),
            )

    @pytest.mark.unit
    def test_goal_invalid_created_at_type(self):
        """Test that non-datetime created_at raises TypeError."""
        with pytest.raises(TypeError, match="created_at must be a datetime"):
            CharacterGoal(
                description="Test goal",
                created_at="2025-01-01",
            )

    @pytest.mark.unit
    def test_goal_invalid_completed_at_type(self):
        """Test that non-datetime completed_at raises TypeError."""
        with pytest.raises(TypeError, match="completed_at must be a datetime or None"):
            CharacterGoal(
                description="Test goal",
                status=GoalStatus.COMPLETED,
                completed_at="2025-01-01",
            )

    @pytest.mark.unit
    def test_goal_empty_goal_id(self):
        """Test that empty goal_id raises ValueError."""
        with pytest.raises(ValueError, match="goal_id cannot be empty"):
            CharacterGoal(
                description="Test goal",
                goal_id="   ",
            )

    # ==================== Query Method Tests ====================

    @pytest.mark.unit
    def test_is_active(self):
        """Test is_active method."""
        active = CharacterGoal(description="Active goal", status=GoalStatus.ACTIVE)
        completed = CharacterGoal(
            description="Completed",
            status=GoalStatus.COMPLETED,
            completed_at=datetime.now(),
        )
        failed = CharacterGoal(
            description="Failed",
            status=GoalStatus.FAILED,
            completed_at=datetime.now(),
        )

        assert active.is_active() is True
        assert completed.is_active() is False
        assert failed.is_active() is False

    @pytest.mark.unit
    def test_is_completed(self):
        """Test is_completed method."""
        active = CharacterGoal(description="Active goal", status=GoalStatus.ACTIVE)
        completed = CharacterGoal(
            description="Completed",
            status=GoalStatus.COMPLETED,
            completed_at=datetime.now(),
        )

        assert active.is_completed() is False
        assert completed.is_completed() is True

    @pytest.mark.unit
    def test_is_failed(self):
        """Test is_failed method."""
        active = CharacterGoal(description="Active goal", status=GoalStatus.ACTIVE)
        failed = CharacterGoal(
            description="Failed",
            status=GoalStatus.FAILED,
            completed_at=datetime.now(),
        )

        assert active.is_failed() is False
        assert failed.is_failed() is True

    @pytest.mark.unit
    def test_is_resolved(self):
        """Test is_resolved method."""
        active = CharacterGoal(description="Active goal", status=GoalStatus.ACTIVE)
        completed = CharacterGoal(
            description="Completed",
            status=GoalStatus.COMPLETED,
            completed_at=datetime.now(),
        )
        failed = CharacterGoal(
            description="Failed",
            status=GoalStatus.FAILED,
            completed_at=datetime.now(),
        )

        assert active.is_resolved() is False
        assert completed.is_resolved() is True
        assert failed.is_resolved() is True

    @pytest.mark.unit
    def test_is_urgent(self):
        """Test is_urgent method."""
        low = CharacterGoal(description="Low urgency", urgency=GoalUrgency.LOW)
        medium = CharacterGoal(description="Medium", urgency=GoalUrgency.MEDIUM)
        high = CharacterGoal(description="High urgency", urgency=GoalUrgency.HIGH)
        critical = CharacterGoal(description="Critical", urgency=GoalUrgency.CRITICAL)

        assert low.is_urgent() is False
        assert medium.is_urgent() is False
        assert high.is_urgent() is True
        assert critical.is_urgent() is True

    @pytest.mark.unit
    def test_get_urgency_level(self):
        """Test get_urgency_level returns lowercase string."""
        goal = CharacterGoal(description="Test", urgency=GoalUrgency.HIGH)
        assert goal.get_urgency_level() == "high"

    # ==================== State Transition Tests ====================

    @pytest.mark.unit
    def test_complete_goal(self):
        """Test completing a goal."""
        goal = CharacterGoal(description="Rescue the princess")
        completed = goal.complete()

        assert completed.status == GoalStatus.COMPLETED
        assert completed.completed_at is not None
        assert completed.goal_id == goal.goal_id
        assert completed.description == goal.description
        # Original is unchanged (immutability)
        assert goal.status == GoalStatus.ACTIVE

    @pytest.mark.unit
    def test_complete_non_active_goal_fails(self):
        """Test that completing a non-active goal raises error."""
        goal = CharacterGoal(
            description="Already done",
            status=GoalStatus.COMPLETED,
            completed_at=datetime.now(),
        )

        with pytest.raises(ValueError, match="Cannot complete a goal with status"):
            goal.complete()

    @pytest.mark.unit
    def test_fail_goal(self):
        """Test failing a goal."""
        goal = CharacterGoal(description="Impossible task")
        failed = goal.fail()

        assert failed.status == GoalStatus.FAILED
        assert failed.completed_at is not None
        assert failed.goal_id == goal.goal_id

    @pytest.mark.unit
    def test_fail_non_active_goal_fails(self):
        """Test that failing a non-active goal raises error."""
        goal = CharacterGoal(
            description="Already failed",
            status=GoalStatus.FAILED,
            completed_at=datetime.now(),
        )

        with pytest.raises(ValueError, match="Cannot fail a goal with status"):
            goal.fail()

    @pytest.mark.unit
    def test_update_urgency(self):
        """Test updating goal urgency."""
        goal = CharacterGoal(description="Urgent matter", urgency=GoalUrgency.LOW)
        updated = goal.update_urgency(GoalUrgency.CRITICAL)

        assert updated.urgency == GoalUrgency.CRITICAL
        assert updated.goal_id == goal.goal_id
        # Original is unchanged
        assert goal.urgency == GoalUrgency.LOW

    @pytest.mark.unit
    def test_update_urgency_non_active_fails(self):
        """Test that updating urgency of non-active goal raises error."""
        goal = CharacterGoal(
            description="Done",
            status=GoalStatus.COMPLETED,
            completed_at=datetime.now(),
        )

        with pytest.raises(ValueError, match="Cannot update urgency"):
            goal.update_urgency(GoalUrgency.HIGH)

    # ==================== Serialization Tests ====================

    @pytest.mark.unit
    def test_to_dict(self):
        """Test conversion to dictionary."""
        goal = CharacterGoal(
            description="Explore the ruins",
            urgency=GoalUrgency.HIGH,
        )
        result = goal.to_dict()

        assert result["description"] == "Explore the ruins"
        assert result["status"] == "ACTIVE"
        assert result["urgency"] == "HIGH"
        assert result["is_active"] is True
        assert result["is_urgent"] is True
        assert "goal_id" in result
        assert "created_at" in result
        assert "completed_at" not in result  # Not set for active goals

    @pytest.mark.unit
    def test_to_dict_completed_goal(self):
        """Test to_dict includes completed_at for resolved goals."""
        goal = CharacterGoal(description="Test").complete()
        result = goal.to_dict()

        assert result["status"] == "COMPLETED"
        assert "completed_at" in result

    @pytest.mark.unit
    def test_get_summary(self):
        """Test get_summary for display."""
        goal = CharacterGoal(
            description="A very long goal description that should be truncated",
            urgency=GoalUrgency.CRITICAL,
        )
        summary = goal.get_summary()

        assert "⏳" in summary  # Active status emoji
        assert "!!!!" in summary  # CRITICAL = 4 exclamation marks
        assert "..." in summary  # Truncated

    @pytest.mark.unit
    def test_get_summary_short_description(self):
        """Test get_summary with short description."""
        goal = CharacterGoal(description="Short goal", urgency=GoalUrgency.LOW)
        summary = goal.get_summary()

        assert "Short goal" in summary
        assert "..." not in summary


class TestCharacterGoalAggregateIntegration:
    """Test CharacterGoal integration with Character aggregate."""

    @pytest.fixture
    def character_with_goals(self):
        """Create a character with initial goals for testing."""
        from src.contexts.character.domain.aggregates.character import Character
        from src.contexts.character.domain.value_objects.character_id import CharacterID
        from src.contexts.character.domain.value_objects.character_profile import (
            Background,
            CharacterClass,
            CharacterProfile,
            CharacterRace,
            Gender,
            PersonalityTraits,
            PhysicalTraits,
        )
        from src.contexts.character.domain.value_objects.character_stats import (
            CharacterStats,
            CombatStats,
            CoreAbilities,
            VitalStats,
        )
        from src.contexts.character.domain.value_objects.skills import Skills

        profile = CharacterProfile(
            name="Test Hero",
            gender=Gender.MALE,
            race=CharacterRace.HUMAN,
            character_class=CharacterClass.FIGHTER,
            age=25,
            level=1,
            physical_traits=PhysicalTraits(),
            personality_traits=PersonalityTraits(
                traits={
                    "courage": 0.8,
                    "intelligence": 0.6,
                    "charisma": 0.5,
                    "loyalty": 0.7,
                }
            ),
            background=Background(),
        )

        core_abilities = CoreAbilities(
            strength=16,
            dexterity=14,
            constitution=14,
            intelligence=12,
            wisdom=10,
            charisma=10,
        )

        vital_stats = VitalStats(
            max_health=30,
            current_health=30,
            max_mana=10,
            current_mana=10,
            max_stamina=25,
            current_stamina=25,
            armor_class=14,
            speed=30,
        )

        combat_stats = CombatStats(
            base_attack_bonus=1,
            initiative_modifier=2,
            damage_reduction=0,
            spell_resistance=0,
            critical_hit_chance=0.05,
            critical_damage_multiplier=2.0,
        )

        stats = CharacterStats(
            core_abilities=core_abilities,
            vital_stats=vital_stats,
            combat_stats=combat_stats,
            experience_points=0,
            skill_points=5,
        )

        skills = Skills.create_basic_skills()

        character = Character(
            character_id=CharacterID.generate(),
            profile=profile,
            stats=stats,
            skills=skills,
        )

        return character

    @pytest.mark.unit
    def test_add_goal_to_character(self, character_with_goals):
        """Test adding a goal to a character."""
        goal = CharacterGoal.create(
            description="Save the village",
            urgency=GoalUrgency.HIGH,
        )

        initial_version = character_with_goals.version
        character_with_goals.add_goal(goal)

        assert len(character_with_goals.goals) == 1
        assert character_with_goals.goals[0].description == "Save the village"
        assert character_with_goals.version == initial_version + 1

    @pytest.mark.unit
    def test_add_duplicate_goal_id_fails(self, character_with_goals):
        """Test that adding a goal with duplicate ID fails."""
        goal1 = CharacterGoal(
            description="First goal",
            goal_id="duplicate-id",
        )
        goal2 = CharacterGoal(
            description="Second goal",
            goal_id="duplicate-id",
        )

        character_with_goals.add_goal(goal1)

        with pytest.raises(ValueError, match="Goal with ID .* already exists"):
            character_with_goals.add_goal(goal2)

    @pytest.mark.unit
    def test_add_invalid_goal_type_fails(self, character_with_goals):
        """Test that adding non-CharacterGoal raises TypeError."""
        with pytest.raises(TypeError, match="Expected CharacterGoal"):
            character_with_goals.add_goal("not a goal")

    @pytest.mark.unit
    def test_get_goals(self, character_with_goals):
        """Test get_goals returns a copy."""
        goal = CharacterGoal.create(description="Test goal")
        character_with_goals.add_goal(goal)

        goals = character_with_goals.get_goals()
        assert len(goals) == 1

        # Verify it's a copy
        goals.clear()
        assert len(character_with_goals.goals) == 1

    @pytest.mark.unit
    def test_get_active_goals(self, character_with_goals):
        """Test filtering active goals."""
        active1 = CharacterGoal.create(description="Active 1")
        active2 = CharacterGoal.create(description="Active 2")
        completed = CharacterGoal(
            description="Done",
            status=GoalStatus.COMPLETED,
            completed_at=datetime.now(),
        )

        character_with_goals.add_goal(active1)
        character_with_goals.add_goal(active2)
        character_with_goals.add_goal(completed)

        active = character_with_goals.get_active_goals()
        assert len(active) == 2

    @pytest.mark.unit
    def test_get_completed_goals(self, character_with_goals):
        """Test filtering completed goals."""
        active = CharacterGoal.create(description="In progress")
        completed = CharacterGoal(
            description="Done",
            status=GoalStatus.COMPLETED,
            completed_at=datetime.now(),
        )

        character_with_goals.add_goal(active)
        character_with_goals.add_goal(completed)

        result = character_with_goals.get_completed_goals()
        assert len(result) == 1
        assert result[0].description == "Done"

    @pytest.mark.unit
    def test_get_failed_goals(self, character_with_goals):
        """Test filtering failed goals."""
        failed = CharacterGoal(
            description="Failed attempt",
            status=GoalStatus.FAILED,
            completed_at=datetime.now(),
        )

        character_with_goals.add_goal(failed)

        result = character_with_goals.get_failed_goals()
        assert len(result) == 1

    @pytest.mark.unit
    def test_get_urgent_goals(self, character_with_goals):
        """Test filtering urgent goals."""
        low = CharacterGoal.create(description="Not urgent", urgency=GoalUrgency.LOW)
        high = CharacterGoal.create(description="Urgent", urgency=GoalUrgency.HIGH)
        critical = CharacterGoal.create(
            description="Very urgent", urgency=GoalUrgency.CRITICAL
        )

        character_with_goals.add_goal(low)
        character_with_goals.add_goal(high)
        character_with_goals.add_goal(critical)

        urgent = character_with_goals.get_urgent_goals()
        assert len(urgent) == 2

    @pytest.mark.unit
    def test_get_goal_by_id(self, character_with_goals):
        """Test finding a goal by ID."""
        goal = CharacterGoal.create(description="Findable goal")
        character_with_goals.add_goal(goal)

        found = character_with_goals.get_goal_by_id(goal.goal_id)
        assert found is not None
        assert found.description == "Findable goal"

        not_found = character_with_goals.get_goal_by_id("nonexistent")
        assert not_found is None

    @pytest.mark.unit
    def test_complete_goal_via_aggregate(self, character_with_goals):
        """Test completing a goal through the aggregate."""
        goal = CharacterGoal.create(description="Complete me")
        character_with_goals.add_goal(goal)

        initial_version = character_with_goals.version
        completed = character_with_goals.complete_goal(goal.goal_id)

        assert completed.status == GoalStatus.COMPLETED
        assert character_with_goals.version == initial_version + 1

        # Verify the goal in the list is updated
        stored = character_with_goals.get_goal_by_id(goal.goal_id)
        assert stored.status == GoalStatus.COMPLETED

    @pytest.mark.unit
    def test_complete_nonexistent_goal_fails(self, character_with_goals):
        """Test completing a nonexistent goal raises error."""
        with pytest.raises(ValueError, match="Goal with ID .* not found"):
            character_with_goals.complete_goal("nonexistent")

    @pytest.mark.unit
    def test_fail_goal_via_aggregate(self, character_with_goals):
        """Test failing a goal through the aggregate."""
        goal = CharacterGoal.create(description="Fail me")
        character_with_goals.add_goal(goal)

        failed = character_with_goals.fail_goal(goal.goal_id)
        assert failed.status == GoalStatus.FAILED

    @pytest.mark.unit
    def test_update_goal_urgency_via_aggregate(self, character_with_goals):
        """Test updating goal urgency through the aggregate."""
        goal = CharacterGoal.create(description="Escalate me", urgency=GoalUrgency.LOW)
        character_with_goals.add_goal(goal)

        updated = character_with_goals.update_goal_urgency(
            goal.goal_id, GoalUrgency.CRITICAL
        )
        assert updated.urgency == GoalUrgency.CRITICAL

    @pytest.mark.unit
    def test_remove_goal(self, character_with_goals):
        """Test removing a goal."""
        goal = CharacterGoal.create(description="Remove me")
        character_with_goals.add_goal(goal)
        assert len(character_with_goals.goals) == 1

        result = character_with_goals.remove_goal(goal.goal_id)
        assert result is True
        assert len(character_with_goals.goals) == 0

    @pytest.mark.unit
    def test_remove_nonexistent_goal(self, character_with_goals):
        """Test removing a nonexistent goal returns False."""
        result = character_with_goals.remove_goal("nonexistent")
        assert result is False

    @pytest.mark.unit
    def test_goals_included_in_character_summary(self, character_with_goals):
        """Test that goals are included in character summary."""
        goal = CharacterGoal.create(description="Test goal", urgency=GoalUrgency.HIGH)
        character_with_goals.add_goal(goal)

        summary = character_with_goals.get_character_summary()

        assert "goals" in summary
        assert "goal_count" in summary
        assert "active_goal_count" in summary
        assert "urgent_goal_count" in summary
        assert summary["goal_count"] == 1
        assert summary["active_goal_count"] == 1
        assert summary["urgent_goal_count"] == 1
