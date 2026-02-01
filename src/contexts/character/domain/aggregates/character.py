#!/usr/bin/env python3
"""
Character Aggregate Root

This module implements the Character aggregate root, which serves as the main
entry point for character-related domain operations and enforces business
invariants across all character data.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..events.character_events import (
    CharacterCreated,
    CharacterEvent,
    CharacterStatsChanged,
    CharacterUpdated,
)
from ..value_objects.character_id import CharacterID
from ..value_objects.character_profile import (
    CharacterClass,
    CharacterProfile,
    CharacterRace,
    Gender,
)
from ..value_objects.character_stats import (
    AbilityScore,
    CharacterStats,
    CombatStats,
    CoreAbilities,
    VitalStats,
)
from ..value_objects.character_goal import CharacterGoal, GoalStatus, GoalUrgency
from ..value_objects.character_memory import CharacterMemory
from ..value_objects.character_psychology import CharacterPsychology
from ..value_objects.skills import SkillCategory, Skills


@dataclass
class Character:
    """
    Character Aggregate Root

    The Character aggregate is responsible for maintaining consistency across
    all character-related data and enforcing business rules. It coordinates
    between value objects and raises domain events when state changes occur.

    Following DDD principles, this is the only way external systems should
    interact with character data, ensuring all business invariants are maintained.
    """

    # Entity identity
    character_id: CharacterID

    # Value objects containing character data
    profile: CharacterProfile
    stats: CharacterStats
    skills: Skills

    # Optional mutable state (not part of frozen CharacterProfile)
    # Psychology uses the Big Five model for personality quantification
    psychology: Optional[CharacterPsychology] = None

    # Character memories - immutable records of experiences that shape behavior
    memories: List[CharacterMemory] = field(default_factory=list)

    # Character goals - what the character wants to achieve
    goals: List[CharacterGoal] = field(default_factory=list)

    # Faction membership - which faction/group the character belongs to
    # Why optional: Characters may be unaffiliated (lone wolves, neutrals)
    faction_id: Optional[str] = None

    # Entity state
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: int = field(default=1)

    # Inventory: List of item IDs owned by this character
    inventory: List[str] = field(default_factory=list)

    # Domain events (not persisted)
    _events: List[CharacterEvent] = field(default_factory=list, init=False)

    def __post_init__(self):
        """Initialize aggregate and validate invariants."""
        self._validate_character_consistency()

        # Record creation event if this is a new character
        if self.version == 1 and not self._events:
            self._add_event(
                CharacterCreated.create(
                    character_id=self.character_id,
                    character_name=self.profile.name,
                    character_class=self.profile.character_class.value,
                    level=self.profile.level,
                    created_at=self.created_at,
                )
            )

    def _validate_character_consistency(self) -> None:
        """Validate business rules across all character data."""
        errors = []

        # Validate level consistency
        if self.profile.level < 1:
            errors.append("Character level must be at least 1")

        # Validate health makes sense for constitution and level
        expected_min_health = max(
            1, self.stats.core_abilities.constitution + self.profile.level
        )
        if self.stats.vital_stats.max_health < expected_min_health:
            errors.append(
                f"Character health too low for constitution and level (minimum: {expected_min_health})"
            )

        # Validate race-appropriate ability scores
        self._validate_racial_abilities(errors)

        # Validate class-appropriate skills
        self._validate_class_skills(errors)

        # Validate age appropriateness
        self._validate_age_consistency(errors)

        if errors:
            raise ValueError(f"Character validation failed: {'; '.join(errors)}")

    def _validate_racial_abilities(self, errors: List[str]) -> None:
        """Validate ability scores are appropriate for character race."""
        # Basic racial ability expectations
        racial_minimums = {
            CharacterRace.DWARF: {"constitution": 12},
            CharacterRace.ELF: {"dexterity": 12},
            CharacterRace.HALFLING: {"dexterity": 12},
            CharacterRace.GNOME: {"intelligence": 12},
            CharacterRace.HALF_ORC: {"strength": 12},
            CharacterRace.DRAGONBORN: {"strength": 12, "charisma": 11},
        }

        minimums = racial_minimums.get(self.profile.race, {})
        for ability, min_score in minimums.items():
            if hasattr(self.stats.core_abilities, ability):
                actual_score = getattr(self.stats.core_abilities, ability)
                if actual_score < min_score:
                    errors.append(
                        f"{self.profile.race.value.title()} should have {ability} >= {min_score}"
                    )

    def _validate_class_skills(self, errors: List[str]) -> None:
        """Validate character has appropriate skills for their class."""
        class_skills = {
            CharacterClass.FIGHTER: [SkillCategory.COMBAT, SkillCategory.PHYSICAL],
            CharacterClass.WIZARD: [SkillCategory.INTELLECTUAL, SkillCategory.MAGICAL],
            CharacterClass.ROGUE: [SkillCategory.PHYSICAL, SkillCategory.SOCIAL],
            CharacterClass.CLERIC: [SkillCategory.MAGICAL, SkillCategory.SOCIAL],
            CharacterClass.RANGER: [SkillCategory.SURVIVAL, SkillCategory.COMBAT],
            CharacterClass.BARD: [SkillCategory.SOCIAL, SkillCategory.ARTISTIC],
            CharacterClass.PILOT: [SkillCategory.TECHNICAL, SkillCategory.PHYSICAL],
            CharacterClass.SCIENTIST: [
                SkillCategory.INTELLECTUAL,
                SkillCategory.TECHNICAL,
            ],
            CharacterClass.ENGINEER: [
                SkillCategory.TECHNICAL,
                SkillCategory.INTELLECTUAL,
            ],
        }

        expected_categories = class_skills.get(self.profile.character_class, [])
        for category in expected_categories:
            if category not in self.skills.skill_groups:
                errors.append(
                    f"{self.profile.character_class.value.title()} should have {category.value} skills"
                )
            elif not any(
                skill.is_trained()
                for skill in self.skills.get_skills_by_category(category)
            ):
                errors.append(
                    f"{self.profile.character_class.value.title()} should be trained in at least one {category.value} skill"
                )

    def _validate_age_consistency(self, errors: List[str]) -> None:
        """Validate character age makes sense for their experience."""
        min_age_by_level = {
            range(1, 6): 16,  # Levels 1-5: Young adult
            range(6, 11): 20,  # Levels 6-10: Adult
            range(11, 16): 25,  # Levels 11-15: Experienced
            range(16, 21): 30,  # Levels 16-20: Veteran
            range(21, 100): 35,  # Levels 21+: Master
        }

        for level_range, min_age in min_age_by_level.items():
            if self.profile.level in level_range and self.profile.age < min_age:
                errors.append(
                    f"Character too young ({self.profile.age}) for level {self.profile.level} (minimum age: {min_age})"
                )
                break

    def _add_event(self, event: CharacterEvent) -> None:
        """Add a domain event to the aggregate."""
        self._events.append(event)

    def get_events(self) -> List[CharacterEvent]:
        """Get all pending domain events."""
        return self._events.copy()

    def clear_events(self) -> None:
        """Clear all pending domain events."""
        self._events.clear()

    # ==================== Character Operations ====================

    def update_profile(self, new_profile: CharacterProfile) -> None:
        """Update character profile, ensuring business rules are maintained."""
        old_profile = self.profile
        self.profile = new_profile
        self.updated_at = datetime.now()
        self.version += 1

        try:
            self._validate_character_consistency()
        except ValueError as e:
            # Rollback changes if validation fails
            self.profile = old_profile
            self.version -= 1
            raise e

        # Record update event
        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["profile"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

    def update_stats(self, new_stats: CharacterStats) -> None:
        """Update character statistics, validating health changes."""
        old_stats = self.stats

        # Business rule: Cannot lose more than half health in one update
        if (
            new_stats.vital_stats.current_health < old_stats.vital_stats.current_health
            and new_stats.vital_stats.current_health
            < old_stats.vital_stats.current_health / 2
        ):
            raise ValueError("Cannot lose more than half health in a single update")

        # Business rule: Cannot exceed maximum values
        if (
            new_stats.vital_stats.current_health > new_stats.vital_stats.max_health
            or new_stats.vital_stats.current_mana > new_stats.vital_stats.max_mana
            or new_stats.vital_stats.current_stamina > new_stats.vital_stats.max_stamina
        ):
            raise ValueError("Current values cannot exceed maximum values")

        self.stats = new_stats
        self.updated_at = datetime.now()
        self.version += 1

        try:
            self._validate_character_consistency()
        except ValueError as e:
            # Rollback changes if validation fails
            self.stats = old_stats
            self.version -= 1
            raise e

        # Record stats change event
        self._add_event(
            CharacterStatsChanged.create(
                character_id=self.character_id,
                old_health=old_stats.vital_stats.current_health,
                new_health=new_stats.vital_stats.current_health,
                old_mana=old_stats.vital_stats.current_mana,
                new_mana=new_stats.vital_stats.current_mana,
                changed_at=self.updated_at,
            )
        )

    def update_skills(self, new_skills: Skills) -> None:
        """Update character skills, ensuring class compatibility."""
        old_skills = self.skills
        self.skills = new_skills
        self.updated_at = datetime.now()
        self.version += 1

        try:
            self._validate_character_consistency()
        except ValueError as e:
            # Rollback changes if validation fails
            self.skills = old_skills
            self.version -= 1
            raise e

        # Record update event
        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["skills"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

    def update_psychology(self, new_psychology: CharacterPsychology) -> None:
        """Update character psychology (Big Five personality traits).

        Why separate from profile: CharacterProfile is frozen and represents
        the character's base identity. Psychology can evolve based on
        narrative events and character development.

        Args:
            new_psychology: The new CharacterPsychology value object

        Raises:
            TypeError: If new_psychology is not a CharacterPsychology instance
        """
        if not isinstance(new_psychology, CharacterPsychology):
            raise TypeError(
                f"Expected CharacterPsychology, got {type(new_psychology).__name__}"
            )

        self.psychology = new_psychology
        self.updated_at = datetime.now()
        self.version += 1

        # Record update event
        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["psychology"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

    def add_memory(self, memory: CharacterMemory) -> None:
        """Add a memory to the character's memory list.

        Why memories are separate from profile: CharacterProfile is frozen and
        represents the character's base identity. Memories accumulate over time
        and represent the character's experiences, affecting their behavior and
        dialogue. They are immutable event logs, not mutable state.

        Args:
            memory: The CharacterMemory to add

        Raises:
            TypeError: If memory is not a CharacterMemory instance
        """
        if not isinstance(memory, CharacterMemory):
            raise TypeError(
                f"Expected CharacterMemory, got {type(memory).__name__}"
            )

        self.memories.append(memory)
        self.updated_at = datetime.now()
        self.version += 1

        # Record update event
        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["memories"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

    def get_memories(self) -> List[CharacterMemory]:
        """Get all memories for this character.

        Returns:
            A copy of the memories list
        """
        return self.memories.copy()

    def get_core_memories(self) -> List[CharacterMemory]:
        """Get only core memories (importance > 8).

        Why this matters: Core memories are the defining experiences that
        shape a character's identity. They should be prioritized in AI
        context building and highlighted in the UI.

        Returns:
            List of memories with importance > 8
        """
        return [m for m in self.memories if m.is_core_memory()]

    def get_memories_by_tag(self, tag: str) -> List[CharacterMemory]:
        """Get memories filtered by a specific tag.

        Args:
            tag: The tag to filter by (case-insensitive)

        Returns:
            List of memories containing the specified tag
        """
        return [m for m in self.memories if m.has_tag(tag)]

    def get_recent_memories(self, count: int = 5) -> List[CharacterMemory]:
        """Get the most recent memories.

        Args:
            count: Number of memories to return (default 5)

        Returns:
            List of most recent memories, sorted by timestamp descending
        """
        sorted_memories = sorted(
            self.memories, key=lambda m: m.timestamp, reverse=True
        )
        return sorted_memories[:count]

    # ==================== Goal Operations ====================

    def add_goal(self, goal: CharacterGoal) -> None:
        """Add a goal to the character's goal list.

        Why goals are separate from profile: CharacterProfile is frozen and
        represents the character's base identity. Goals represent dynamic
        desires that drive character motivation and narrative arcs.

        Args:
            goal: The CharacterGoal to add

        Raises:
            TypeError: If goal is not a CharacterGoal instance
            ValueError: If a goal with the same ID already exists
        """
        if not isinstance(goal, CharacterGoal):
            raise TypeError(
                f"Expected CharacterGoal, got {type(goal).__name__}"
            )

        # Check for duplicate goal_id
        if any(g.goal_id == goal.goal_id for g in self.goals):
            raise ValueError(f"Goal with ID {goal.goal_id} already exists")

        self.goals.append(goal)
        self.updated_at = datetime.now()
        self.version += 1

        # Record update event
        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["goals"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

    def get_goals(self) -> List[CharacterGoal]:
        """Get all goals for this character.

        Returns:
            A copy of the goals list
        """
        return self.goals.copy()

    def get_active_goals(self) -> List[CharacterGoal]:
        """Get only active goals.

        Returns:
            List of goals with status ACTIVE
        """
        return [g for g in self.goals if g.is_active()]

    def get_completed_goals(self) -> List[CharacterGoal]:
        """Get only completed goals.

        Returns:
            List of goals with status COMPLETED
        """
        return [g for g in self.goals if g.is_completed()]

    def get_failed_goals(self) -> List[CharacterGoal]:
        """Get only failed goals.

        Returns:
            List of goals with status FAILED
        """
        return [g for g in self.goals if g.is_failed()]

    def get_urgent_goals(self) -> List[CharacterGoal]:
        """Get goals that require immediate attention (HIGH or CRITICAL urgency).

        Returns:
            List of active goals with HIGH or CRITICAL urgency
        """
        return [g for g in self.goals if g.is_active() and g.is_urgent()]

    def get_goal_by_id(self, goal_id: str) -> Optional[CharacterGoal]:
        """Find a goal by its ID.

        Args:
            goal_id: The unique identifier of the goal

        Returns:
            The CharacterGoal if found, None otherwise
        """
        return next((g for g in self.goals if g.goal_id == goal_id), None)

    def complete_goal(self, goal_id: str) -> CharacterGoal:
        """Mark a goal as completed.

        Args:
            goal_id: The ID of the goal to complete

        Returns:
            The updated CharacterGoal

        Raises:
            ValueError: If goal not found or cannot be completed
        """
        goal = self.get_goal_by_id(goal_id)
        if not goal:
            raise ValueError(f"Goal with ID {goal_id} not found")

        completed_goal = goal.complete()

        # Replace the goal in the list
        self.goals = [
            completed_goal if g.goal_id == goal_id else g
            for g in self.goals
        ]

        self.updated_at = datetime.now()
        self.version += 1

        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["goals"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

        return completed_goal

    def fail_goal(self, goal_id: str) -> CharacterGoal:
        """Mark a goal as failed.

        Args:
            goal_id: The ID of the goal to fail

        Returns:
            The updated CharacterGoal

        Raises:
            ValueError: If goal not found or cannot be failed
        """
        goal = self.get_goal_by_id(goal_id)
        if not goal:
            raise ValueError(f"Goal with ID {goal_id} not found")

        failed_goal = goal.fail()

        # Replace the goal in the list
        self.goals = [
            failed_goal if g.goal_id == goal_id else g
            for g in self.goals
        ]

        self.updated_at = datetime.now()
        self.version += 1

        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["goals"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

        return failed_goal

    def update_goal_urgency(
        self, goal_id: str, new_urgency: GoalUrgency
    ) -> CharacterGoal:
        """Update the urgency level of a goal.

        Args:
            goal_id: The ID of the goal to update
            new_urgency: The new urgency level

        Returns:
            The updated CharacterGoal

        Raises:
            ValueError: If goal not found or cannot be updated
        """
        goal = self.get_goal_by_id(goal_id)
        if not goal:
            raise ValueError(f"Goal with ID {goal_id} not found")

        updated_goal = goal.update_urgency(new_urgency)

        # Replace the goal in the list
        self.goals = [
            updated_goal if g.goal_id == goal_id else g
            for g in self.goals
        ]

        self.updated_at = datetime.now()
        self.version += 1

        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["goals"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

        return updated_goal

    def remove_goal(self, goal_id: str) -> bool:
        """Remove a goal from the character.

        Note: In most cases, goals should be marked as completed or failed
        rather than removed. This method exists for data correction.

        Args:
            goal_id: The ID of the goal to remove

        Returns:
            True if goal was found and removed, False otherwise
        """
        original_count = len(self.goals)
        self.goals = [g for g in self.goals if g.goal_id != goal_id]

        if len(self.goals) == original_count:
            return False

        self.updated_at = datetime.now()
        self.version += 1

        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["goals"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

        return True

    def level_up(self) -> None:
        """Level up the character, increasing stats appropriately."""
        if self.profile.level >= 100:
            raise ValueError("Character is already at maximum level")

        # Calculate stat increases
        new_health = (
            self.stats.vital_stats.max_health
            + 10
            + self.stats.core_abilities.constitution
        )
        new_mana = (
            self.stats.vital_stats.max_mana + 5 + self.stats.core_abilities.intelligence
        )

        # Create updated profile
        from ..value_objects.character_profile import CharacterProfile

        new_profile = CharacterProfile(
            name=self.profile.name,
            gender=self.profile.gender,
            race=self.profile.race,
            character_class=self.profile.character_class,
            age=self.profile.age,
            level=self.profile.level + 1,
            physical_traits=self.profile.physical_traits,
            personality_traits=self.profile.personality_traits,
            background=self.profile.background,
            title=self.profile.title,
            affiliation=self.profile.affiliation,
            languages=self.profile.languages,
        )

        # Create updated vital stats
        new_vital_stats = VitalStats(
            max_health=new_health,
            current_health=min(self.stats.vital_stats.current_health + 10, new_health),
            max_mana=new_mana,
            current_mana=min(self.stats.vital_stats.current_mana + 5, new_mana),
            max_stamina=self.stats.vital_stats.max_stamina + 5,
            current_stamina=self.stats.vital_stats.max_stamina + 5,
            armor_class=self.stats.vital_stats.armor_class,
            speed=self.stats.vital_stats.speed,
        )

        new_stats = CharacterStats(
            core_abilities=self.stats.core_abilities,
            vital_stats=new_vital_stats,
            combat_stats=self.stats.combat_stats,
            experience_points=self.stats.experience_points,
            skill_points=self.stats.skill_points + 5,
        )

        # Update character
        self.profile = new_profile
        self.stats = new_stats
        self.updated_at = datetime.now()
        self.version += 1

        # Record level up event
        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["level_up"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

    def heal(self, amount: int) -> None:
        """Heal the character by specified amount."""
        if amount <= 0:
            raise ValueError("Heal amount must be positive")

        # Cannot heal a dead character
        if not self.is_alive():
            return

        new_health = min(
            self.stats.vital_stats.current_health + amount,
            self.stats.vital_stats.max_health,
        )

        if new_health == self.stats.vital_stats.current_health:
            return  # No healing needed

        new_vital_stats = VitalStats(
            max_health=self.stats.vital_stats.max_health,
            current_health=new_health,
            max_mana=self.stats.vital_stats.max_mana,
            current_mana=self.stats.vital_stats.current_mana,
            max_stamina=self.stats.vital_stats.max_stamina,
            current_stamina=self.stats.vital_stats.current_stamina,
            armor_class=self.stats.vital_stats.armor_class,
            speed=self.stats.vital_stats.speed,
        )

        old_health = self.stats.vital_stats.current_health

        self.stats = CharacterStats(
            core_abilities=self.stats.core_abilities,
            vital_stats=new_vital_stats,
            combat_stats=self.stats.combat_stats,
            experience_points=self.stats.experience_points,
            skill_points=self.stats.skill_points,
        )

        self.updated_at = datetime.now()
        self.version += 1

        # Record healing event
        self._add_event(
            CharacterStatsChanged.create(
                character_id=self.character_id,
                old_health=old_health,
                new_health=new_health,
                old_mana=self.stats.vital_stats.current_mana,
                new_mana=self.stats.vital_stats.current_mana,
                changed_at=self.updated_at,
            )
        )

    def take_damage(self, amount: int) -> None:
        """Apply damage to the character."""
        if amount <= 0:
            raise ValueError("Damage amount must be positive")

        # Apply damage reduction
        actual_damage = max(1, amount - self.stats.combat_stats.damage_reduction)
        new_health = max(0, self.stats.vital_stats.current_health - actual_damage)

        new_vital_stats = VitalStats(
            max_health=self.stats.vital_stats.max_health,
            current_health=new_health,
            max_mana=self.stats.vital_stats.max_mana,
            current_mana=self.stats.vital_stats.current_mana,
            max_stamina=self.stats.vital_stats.max_stamina,
            current_stamina=self.stats.vital_stats.current_stamina,
            armor_class=self.stats.vital_stats.armor_class,
            speed=self.stats.vital_stats.speed,
        )

        old_health = self.stats.vital_stats.current_health

        self.stats = CharacterStats(
            core_abilities=self.stats.core_abilities,
            vital_stats=new_vital_stats,
            combat_stats=self.stats.combat_stats,
            experience_points=self.stats.experience_points,
            skill_points=self.stats.skill_points,
        )

        self.updated_at = datetime.now()
        self.version += 1

        # Record damage event
        self._add_event(
            CharacterStatsChanged.create(
                character_id=self.character_id,
                old_health=old_health,
                new_health=new_health,
                old_mana=self.stats.vital_stats.current_mana,
                new_mana=self.stats.vital_stats.current_mana,
                changed_at=self.updated_at,
            )
        )

    # ==================== Inventory Operations ====================

    def give_item(self, item_id: str) -> None:
        """Add an item to the character's inventory.

        Why track by ID: Items may exist as separate entities with their own
        lifecycle. Storing IDs enables loose coupling and avoids duplication.

        Args:
            item_id: The unique identifier of the item to add.

        Raises:
            ValueError: If item_id is empty or already in inventory.
        """
        if not item_id or not item_id.strip():
            raise ValueError("Item ID cannot be empty")

        if item_id in self.inventory:
            raise ValueError(f"Item {item_id} is already in inventory")

        self.inventory.append(item_id)
        self.updated_at = datetime.now()
        self.version += 1

        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["inventory_add"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

    def remove_item(self, item_id: str) -> bool:
        """Remove an item from the character's inventory.

        Args:
            item_id: The unique identifier of the item to remove.

        Returns:
            True if item was found and removed, False otherwise.
        """
        if item_id in self.inventory:
            self.inventory.remove(item_id)
            self.updated_at = datetime.now()
            self.version += 1

            self._add_event(
                CharacterUpdated.create(
                    character_id=self.character_id,
                    updated_fields=["inventory_remove"],
                    old_version=self.version - 1,
                    new_version=self.version,
                    updated_at=self.updated_at,
                )
            )
            return True
        return False

    def has_item(self, item_id: str) -> bool:
        """Check if the character has a specific item.

        Args:
            item_id: The unique identifier of the item to check.

        Returns:
            True if item is in inventory.
        """
        return item_id in self.inventory

    def get_inventory_count(self) -> int:
        """Get the number of items in inventory."""
        return len(self.inventory)

    # ==================== Faction Operations ====================

    def join_faction(self, faction_id: str) -> None:
        """Join a faction/group.

        Why separate from profile: Faction membership is dynamic and can change
        during the narrative. Characters may leave, be expelled, or switch
        allegiances based on story events.

        Args:
            faction_id: The unique identifier of the faction to join

        Raises:
            ValueError: If faction_id is empty or already a member
        """
        if not faction_id or not faction_id.strip():
            raise ValueError("Faction ID cannot be empty")

        if self.faction_id == faction_id:
            raise ValueError(f"Already a member of faction {faction_id}")

        self.faction_id = faction_id
        self.updated_at = datetime.now()
        self.version += 1

        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["faction_join"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

    def leave_faction(self) -> bool:
        """Leave the current faction.

        Returns:
            True if successfully left a faction, False if not in any faction
        """
        if self.faction_id is None:
            return False

        self.faction_id = None
        self.updated_at = datetime.now()
        self.version += 1

        self._add_event(
            CharacterUpdated.create(
                character_id=self.character_id,
                updated_fields=["faction_leave"],
                old_version=self.version - 1,
                new_version=self.version,
                updated_at=self.updated_at,
            )
        )

        return True

    def get_faction_id(self) -> Optional[str]:
        """Get the current faction ID.

        Returns:
            The faction ID or None if not in a faction
        """
        return self.faction_id

    def is_in_faction(self, faction_id: Optional[str] = None) -> bool:
        """Check if character is in a faction.

        Args:
            faction_id: If provided, check if in this specific faction.
                        If None, check if in any faction.

        Returns:
            True if in the specified faction (or any faction if faction_id is None)
        """
        if faction_id is None:
            return self.faction_id is not None
        return self.faction_id == faction_id

    # ==================== Query Methods ====================

    def is_alive(self) -> bool:
        """Check if character is alive."""
        return self.stats.vital_stats.is_alive()

    def can_level_up(self, required_xp: int) -> bool:
        """Check if character has enough experience to level up."""
        return self.stats.experience_points >= required_xp and self.profile.level < 100

    def get_character_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the character."""
        summary = {
            "id": str(self.character_id),
            "name": self.profile.name,
            "level": self.profile.level,
            "class": self.profile.character_class.value,
            "race": self.profile.race.value,
            "health": f"{self.stats.vital_stats.current_health}/{self.stats.vital_stats.max_health}",
            "profile_summary": self.profile.get_character_summary(),
            "stats_summary": self.stats.get_stats_summary(),
            "skills_summary": self.skills.get_skill_summary(),
            "inventory": self.inventory.copy(),
            "inventory_count": len(self.inventory),
            "is_alive": self.is_alive(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
        }

        # Include psychology if set
        if self.psychology is not None:
            summary["psychology"] = self.psychology.to_dict()
            summary["psychology_summary"] = self.psychology.get_personality_summary()

        # Include memories
        if self.memories:
            summary["memories"] = [m.to_dict() for m in self.memories]
            summary["memory_count"] = len(self.memories)
            summary["core_memory_count"] = len(self.get_core_memories())

        # Include goals
        if self.goals:
            summary["goals"] = [g.to_dict() for g in self.goals]
            summary["goal_count"] = len(self.goals)
            summary["active_goal_count"] = len(self.get_active_goals())
            summary["urgent_goal_count"] = len(self.get_urgent_goals())

        # Include faction membership
        if self.faction_id is not None:
            summary["faction_id"] = self.faction_id

        return summary

    @classmethod
    def create_new_character(
        cls,
        name: str,
        gender: Gender,
        race: CharacterRace,
        character_class: CharacterClass,
        age: int,
        core_abilities: CoreAbilities,
    ) -> "Character":
        """Factory method to create a new character with defaults."""
        from ..value_objects.character_profile import (
            Background,
            PersonalityTraits,
            PhysicalTraits,
        )

        # Create basic profile
        profile = CharacterProfile(
            name=name,
            gender=gender,
            race=race,
            character_class=character_class,
            age=age,
            level=1,
            physical_traits=PhysicalTraits(),
            personality_traits=PersonalityTraits(
                traits={
                    "courage": 0.5,
                    "intelligence": 0.5,
                    "charisma": 0.5,
                    "loyalty": 0.5,
                }
            ),
            background=Background(),
        )

        # Calculate starting health/mana based on class and constitution
        base_health = 20 + core_abilities.constitution
        base_mana = (
            10 + core_abilities.intelligence
            if character_class
            in [
                CharacterClass.WIZARD,
                CharacterClass.CLERIC,
                CharacterClass.SORCERER,
                CharacterClass.WARLOCK,
                CharacterClass.BARD,
                CharacterClass.DRUID,
            ]
            else 5
        )

        vital_stats = VitalStats(
            max_health=base_health,
            current_health=base_health,
            max_mana=base_mana,
            current_mana=base_mana,
            max_stamina=15 + core_abilities.constitution,
            current_stamina=15 + core_abilities.constitution,
            armor_class=10
            + core_abilities.get_ability_modifier(AbilityScore.DEXTERITY),
            speed=30,
        )

        combat_stats = CombatStats(
            base_attack_bonus=0,
            initiative_modifier=core_abilities.get_ability_modifier(
                AbilityScore.DEXTERITY
            ),
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

        # Create basic skills appropriate for class
        skills = Skills.create_basic_skills()

        return cls(
            character_id=CharacterID.generate(),
            profile=profile,
            stats=stats,
            skills=skills,
        )
