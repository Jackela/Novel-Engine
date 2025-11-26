#!/usr/bin/env python3
"""
Unit tests for Skills Value Object

Comprehensive test suite for the Skills value object covering
individual skills, skill groups, proficiency levels, and skill management.
"""

import sys
from typing import Dict
from unittest.mock import MagicMock

import pytest

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()

# Import the value objects we're testing
from contexts.character.domain.value_objects.skills import (
    ProficiencyLevel,
    Skill,
    SkillCategory,
    SkillGroup,
    Skills,
)


class TestProficiencyLevel:
    """Test suite for ProficiencyLevel enum."""

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_proficiency_level_values(self):
        """Test proficiency level enum values."""
        assert ProficiencyLevel.UNTRAINED.value == 0
        assert ProficiencyLevel.NOVICE.value == 1
        assert ProficiencyLevel.APPRENTICE.value == 2
        assert ProficiencyLevel.JOURNEYMAN.value == 3
        assert ProficiencyLevel.EXPERT.value == 4
        assert ProficiencyLevel.MASTER.value == 5
        assert ProficiencyLevel.GRANDMASTER.value == 6
        assert ProficiencyLevel.LEGENDARY.value == 7

    @pytest.mark.unit
    @pytest.mark.fast
    def test_proficiency_level_ordering(self):
        """Test that proficiency levels can be compared."""
        assert ProficiencyLevel.UNTRAINED.value < ProficiencyLevel.NOVICE.value
        assert ProficiencyLevel.EXPERT.value > ProficiencyLevel.JOURNEYMAN.value
        assert ProficiencyLevel.LEGENDARY.value > ProficiencyLevel.MASTER.value


class TestSkillCategory:
    """Test suite for SkillCategory enum."""

    @pytest.mark.unit
    def test_skill_category_values(self):
        """Test skill category enum values."""
        expected_categories = [
            "combat",
            "social",
            "intellectual",
            "physical",
            "technical",
            "magical",
            "survival",
            "artistic",
            "professional",
        ]

        category_values = [category.value for category in SkillCategory]

        for expected in expected_categories:
            assert expected in category_values

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skill_category_uniqueness(self):
        """Test that all skill category values are unique."""
        category_values = [category.value for category in SkillCategory]
        assert len(category_values) == len(set(category_values))


class TestSkill:
    """Test suite for Skill value object."""

    # ==================== Creation Tests ====================

    @pytest.mark.unit
    def test_skill_creation_success(self):
        """Test successful skill creation."""
        skill = Skill(
            name="Sword Fighting",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.EXPERT,
            modifier=3,
            description="Expertise with sword combat",
        )

        assert skill.name == "Sword Fighting"
        assert skill.category == SkillCategory.COMBAT
        assert skill.proficiency_level == ProficiencyLevel.EXPERT
        assert skill.modifier == 3
        assert skill.description == "Expertise with sword combat"

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skill_creation_minimal(self):
        """Test skill creation with minimal data."""
        skill = Skill(
            name="Basic Combat",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.NOVICE,
            modifier=0,
        )

        assert skill.name == "Basic Combat"
        assert skill.description is None

    # ==================== Validation Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skill_empty_name_fails(self):
        """Test skill validation fails with empty name."""
        with pytest.raises(ValueError) as exc_info:
            Skill(
                name="",
                category=SkillCategory.COMBAT,
                proficiency_level=ProficiencyLevel.NOVICE,
                modifier=0,
            )
        assert "Skill name cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skill_whitespace_name_fails(self):
        """Test skill validation fails with whitespace-only name."""
        with pytest.raises(ValueError) as exc_info:
            Skill(
                name="   ",
                category=SkillCategory.COMBAT,
                proficiency_level=ProficiencyLevel.NOVICE,
                modifier=0,
            )
        assert "Skill name cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skill_name_too_long_fails(self):
        """Test skill validation fails with name too long."""
        long_name = "A" * 51  # 51 characters
        with pytest.raises(ValueError) as exc_info:
            Skill(
                name=long_name,
                category=SkillCategory.COMBAT,
                proficiency_level=ProficiencyLevel.NOVICE,
                modifier=0,
            )
        assert "Skill name cannot exceed 50 characters" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skill_modifier_too_low_fails(self):
        """Test skill validation fails with modifier too low."""
        with pytest.raises(ValueError) as exc_info:
            Skill(
                name="Test Skill",
                category=SkillCategory.COMBAT,
                proficiency_level=ProficiencyLevel.NOVICE,
                modifier=-11,  # Too low
            )
        assert "Skill modifier must be between -10 and 20" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skill_modifier_too_high_fails(self):
        """Test skill validation fails with modifier too high."""
        with pytest.raises(ValueError) as exc_info:
            Skill(
                name="Test Skill",
                category=SkillCategory.COMBAT,
                proficiency_level=ProficiencyLevel.NOVICE,
                modifier=21,  # Too high
            )
        assert "Skill modifier must be between -10 and 20" in str(exc_info.value)

    @pytest.mark.unit
    def test_skill_description_too_long_fails(self):
        """Test skill validation fails with description too long."""
        long_description = "A" * 501  # 501 characters
        with pytest.raises(ValueError) as exc_info:
            Skill(
                name="Test Skill",
                category=SkillCategory.COMBAT,
                proficiency_level=ProficiencyLevel.NOVICE,
                modifier=0,
                description=long_description,
            )
        assert "Skill description cannot exceed 500 characters" in str(exc_info.value)

    @pytest.mark.unit
    def test_skill_boundary_values(self):
        """Test skill creation at boundary values."""
        # Test minimum values
        min_skill = Skill(
            name="A",  # 1 character
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.UNTRAINED,
            modifier=-10,  # Minimum modifier
            description="A" * 500,  # Maximum description length
        )

        assert min_skill.name == "A"
        assert min_skill.modifier == -10

        # Test maximum values
        max_skill = Skill(
            name="A" * 50,  # Maximum name length
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.LEGENDARY,
            modifier=20,  # Maximum modifier
            description="Test",
        )

        assert len(max_skill.name) == 50
        assert max_skill.modifier == 20

    # ==================== Method Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_total_modifier(self):
        """Test total modifier calculation."""
        skill = Skill(
            name="Sword Fighting",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.EXPERT,  # +4
            modifier=3,  # +3
        )

        assert skill.get_total_modifier() == 7  # 4 + 3

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_total_modifier_untrained(self):
        """Test total modifier for untrained skill."""
        skill = Skill(
            name="Untrained Skill",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.UNTRAINED,  # +0
            modifier=2,  # +2
        )

        assert skill.get_total_modifier() == 2  # 0 + 2

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_total_modifier_negative(self):
        """Test total modifier with negative modifier."""
        skill = Skill(
            name="Penalized Skill",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.NOVICE,  # +1
            modifier=-3,  # -3
        )

        assert skill.get_total_modifier() == -2  # 1 + (-3)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_trained_true(self):
        """Test is_trained returns True for trained skills."""
        skill = Skill(
            name="Trained Skill",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.NOVICE,
            modifier=0,
        )

        assert skill.is_trained() is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_trained_false(self):
        """Test is_trained returns False for untrained skills."""
        skill = Skill(
            name="Untrained Skill",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.UNTRAINED,
            modifier=0,
        )

        assert skill.is_trained() is False

    @pytest.mark.unit
    def test_is_expert_level_true(self):
        """Test is_expert_level returns True for expert+ skills."""
        expert_skill = Skill(
            name="Expert Skill",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.EXPERT,
            modifier=0,
        )

        master_skill = Skill(
            name="Master Skill",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.MASTER,
            modifier=0,
        )

        assert expert_skill.is_expert_level() is True
        assert master_skill.is_expert_level() is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_expert_level_false(self):
        """Test is_expert_level returns False for below expert skills."""
        skill = Skill(
            name="Journeyman Skill",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.JOURNEYMAN,
            modifier=0,
        )

        assert skill.is_expert_level() is False

    @pytest.mark.unit
    def test_is_master_level_true(self):
        """Test is_master_level returns True for master+ skills."""
        master_skill = Skill(
            name="Master Skill",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.MASTER,
            modifier=0,
        )

        grandmaster_skill = Skill(
            name="Grandmaster Skill",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.GRANDMASTER,
            modifier=0,
        )

        assert master_skill.is_master_level() is True
        assert grandmaster_skill.is_master_level() is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_master_level_false(self):
        """Test is_master_level returns False for below master skills."""
        skill = Skill(
            name="Expert Skill",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.EXPERT,
            modifier=0,
        )

        assert skill.is_master_level() is False

    @pytest.mark.unit
    def test_get_proficiency_description(self):
        """Test proficiency description generation."""
        skill_levels = [
            (ProficiencyLevel.UNTRAINED, "No training"),
            (ProficiencyLevel.NOVICE, "Basic understanding"),
            (ProficiencyLevel.APPRENTICE, "Learning the fundamentals"),
            (ProficiencyLevel.JOURNEYMAN, "Competent practitioner"),
            (ProficiencyLevel.EXPERT, "Highly skilled professional"),
            (ProficiencyLevel.MASTER, "Acknowledged master of the art"),
            (ProficiencyLevel.GRANDMASTER, "Among the greatest practitioners"),
            (ProficiencyLevel.LEGENDARY, "Legendary skill transcending normal limits"),
        ]

        for proficiency, expected_description in skill_levels:
            skill = Skill(
                name="Test Skill",
                category=SkillCategory.COMBAT,
                proficiency_level=proficiency,
                modifier=0,
            )

            assert skill.get_proficiency_description() == expected_description


class TestSkillGroup:
    """Test suite for SkillGroup value object."""

    @pytest.fixture
    def sample_combat_skills(self) -> Dict[str, Skill]:
        """Create sample combat skills for testing."""
        return {
            "melee_combat": Skill(
                "Melee Combat", SkillCategory.COMBAT, ProficiencyLevel.EXPERT, 2
            ),
            "ranged_combat": Skill(
                "Ranged Combat", SkillCategory.COMBAT, ProficiencyLevel.JOURNEYMAN, 1
            ),
            "dodge": Skill(
                "Dodge", SkillCategory.COMBAT, ProficiencyLevel.APPRENTICE, 0
            ),
        }

    @pytest.fixture
    def sample_skill_group(self, sample_combat_skills) -> SkillGroup:
        """Create a sample skill group for testing."""
        return SkillGroup(
            name="Combat Skills",
            category=SkillCategory.COMBAT,
            base_modifier=2,
            skills=sample_combat_skills,
        )

    # ==================== Creation Tests ====================

    @pytest.mark.unit
    def test_skill_group_creation_success(self, sample_combat_skills):
        """Test successful skill group creation."""
        group = SkillGroup(
            name="Combat Skills",
            category=SkillCategory.COMBAT,
            base_modifier=2,
            skills=sample_combat_skills,
        )

        assert group.name == "Combat Skills"
        assert group.category == SkillCategory.COMBAT
        assert group.base_modifier == 2
        assert len(group.skills) == 3
        assert "melee_combat" in group.skills

    # ==================== Validation Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skill_group_empty_name_fails(self, sample_combat_skills):
        """Test skill group validation fails with empty name."""
        with pytest.raises(ValueError) as exc_info:
            SkillGroup(
                name="",
                category=SkillCategory.COMBAT,
                base_modifier=2,
                skills=sample_combat_skills,
            )
        assert "Skill group name cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skill_group_base_modifier_too_low_fails(self, sample_combat_skills):
        """Test skill group validation fails with base modifier too low."""
        with pytest.raises(ValueError) as exc_info:
            SkillGroup(
                name="Combat Skills",
                category=SkillCategory.COMBAT,
                base_modifier=-6,  # Too low
                skills=sample_combat_skills,
            )
        assert "Base modifier must be between -5 and 10" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skill_group_base_modifier_too_high_fails(self, sample_combat_skills):
        """Test skill group validation fails with base modifier too high."""
        with pytest.raises(ValueError) as exc_info:
            SkillGroup(
                name="Combat Skills",
                category=SkillCategory.COMBAT,
                base_modifier=11,  # Too high
                skills=sample_combat_skills,
            )
        assert "Base modifier must be between -5 and 10" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skill_group_empty_skills_fails(self):
        """Test skill group validation fails with no skills."""
        with pytest.raises(ValueError) as exc_info:
            SkillGroup(
                name="Empty Group",
                category=SkillCategory.COMBAT,
                base_modifier=0,
                skills={},  # Empty skills
            )
        assert "Skill group must contain at least one skill" in str(exc_info.value)

    @pytest.mark.unit
    def test_skill_group_mismatched_category_fails(self):
        """Test skill group validation fails with mismatched skill categories."""
        mismatched_skills = {
            "melee_combat": Skill(
                "Melee Combat", SkillCategory.COMBAT, ProficiencyLevel.NOVICE, 0
            ),
            "persuasion": Skill(
                "Persuasion", SkillCategory.SOCIAL, ProficiencyLevel.NOVICE, 0
            ),  # Wrong category
        }

        with pytest.raises(ValueError) as exc_info:
            SkillGroup(
                name="Mixed Group",
                category=SkillCategory.COMBAT,
                base_modifier=0,
                skills=mismatched_skills,
            )
        assert "All skills in group must match category combat" in str(exc_info.value)

    # ==================== Method Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_skill_existing(self, sample_skill_group):
        """Test getting an existing skill from group."""
        skill = sample_skill_group.get_skill("melee_combat")

        assert skill is not None
        assert skill.name == "Melee Combat"

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_get_skill_case_insensitive(self, sample_skill_group):
        """Test getting skill is case insensitive."""
        skill = sample_skill_group.get_skill("MELEE_COMBAT")

        assert skill is not None
        assert skill.name == "Melee Combat"

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_get_skill_nonexistent(self, sample_skill_group):
        """Test getting non-existent skill returns None."""
        skill = sample_skill_group.get_skill("nonexistent_skill")

        assert skill is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_skill_existing(self, sample_skill_group):
        """Test has_skill returns True for existing skills."""
        assert sample_skill_group.has_skill("melee_combat") is True
        assert sample_skill_group.has_skill("RANGED_COMBAT") is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_skill_nonexistent(self, sample_skill_group):
        """Test has_skill returns False for non-existent skills."""
        assert sample_skill_group.has_skill("nonexistent_skill") is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_average_proficiency(self, sample_skill_group):
        """Test average proficiency calculation."""
        # Expert(4) + Journeyman(3) + Apprentice(2) = 9, avg = 3.0
        avg = sample_skill_group.get_average_proficiency()

        assert avg == 3.0

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_get_average_proficiency_empty_group(self):
        """Test average proficiency for hypothetical empty group."""
        # This test is theoretical since empty groups fail validation
        # but tests the method logic
        skills = {
            "test": Skill("Test", SkillCategory.COMBAT, ProficiencyLevel.NOVICE, 0)
        }
        group = SkillGroup("Test", SkillCategory.COMBAT, 0, skills)

        # Manually test the logic by clearing skills (bypassing validation)
        group = SkillGroup("Test", SkillCategory.COMBAT, 0, skills)
        object.__setattr__(group, "skills", {})

        avg = group.get_average_proficiency()
        assert avg == 0.0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_expert_skills(self, sample_skill_group):
        """Test getting expert-level skills from group."""
        expert_skills = sample_skill_group.get_expert_skills()

        assert len(expert_skills) == 1
        assert expert_skills[0].name == "Melee Combat"

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_count_trained_skills(self, sample_skill_group):
        """Test counting trained skills in group."""
        trained_count = sample_skill_group.count_trained_skills()

        assert trained_count == 3  # All skills are trained (above UNTRAINED)

    @pytest.mark.unit
    def test_count_trained_skills_with_untrained(self):
        """Test counting trained skills with some untrained."""
        mixed_skills = {
            "trained": Skill(
                "Trained", SkillCategory.COMBAT, ProficiencyLevel.NOVICE, 0
            ),
            "untrained": Skill(
                "Untrained", SkillCategory.COMBAT, ProficiencyLevel.UNTRAINED, 0
            ),
        }

        group = SkillGroup(
            name="Mixed Group",
            category=SkillCategory.COMBAT,
            base_modifier=0,
            skills=mixed_skills,
        )

        trained_count = group.count_trained_skills()
        assert trained_count == 1  # Only the trained skill


class TestSkills:
    """Test suite for Skills value object."""

    @pytest.fixture
    def sample_skill_groups(self) -> Dict[SkillCategory, SkillGroup]:
        """Create sample skill groups for testing."""
        combat_skills = {
            "melee_combat": Skill(
                "Melee Combat", SkillCategory.COMBAT, ProficiencyLevel.EXPERT, 2
            ),
            "ranged_combat": Skill(
                "Ranged Combat", SkillCategory.COMBAT, ProficiencyLevel.JOURNEYMAN, 1
            ),
        }

        social_skills = {
            "persuasion": Skill(
                "Persuasion", SkillCategory.SOCIAL, ProficiencyLevel.APPRENTICE, 1
            ),
            "deception": Skill(
                "Deception", SkillCategory.SOCIAL, ProficiencyLevel.NOVICE, 0
            ),
        }

        return {
            SkillCategory.COMBAT: SkillGroup(
                "Combat", SkillCategory.COMBAT, 1, combat_skills
            ),
            SkillCategory.SOCIAL: SkillGroup(
                "Social", SkillCategory.SOCIAL, 0, social_skills
            ),
        }

    @pytest.fixture
    def sample_skills(self, sample_skill_groups) -> Skills:
        """Create a sample Skills instance for testing."""
        return Skills(
            skill_groups=sample_skill_groups,
            languages={"Common", "Elvish", "Draconic"},
            specializations={"melee_combat": 2, "persuasion": 1},
        )

    # ==================== Creation Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skills_creation_success(self, sample_skill_groups):
        """Test successful Skills creation."""
        skills = Skills(
            skill_groups=sample_skill_groups,
            languages={"Common", "Elvish"},
            specializations={"melee_combat": 3},
        )

        assert len(skills.skill_groups) == 2
        assert "Common" in skills.languages
        assert skills.specializations["melee_combat"] == 3

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skills_creation_minimal(self, sample_skill_groups):
        """Test Skills creation with minimal data."""
        skills = Skills(
            skill_groups=sample_skill_groups, languages=set(), specializations={}
        )

        assert len(skills.skill_groups) == 2
        assert len(skills.languages) == 0
        assert len(skills.specializations) == 0

    # ==================== Validation Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skills_empty_skill_groups_fails(self):
        """Test Skills validation fails with empty skill groups."""
        with pytest.raises(ValueError) as exc_info:
            Skills(skill_groups={}, languages={"Common"}, specializations={})  # Empty
        assert "Character must have at least one skill group" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skills_empty_language_name_fails(self, sample_skill_groups):
        """Test Skills validation fails with empty language name."""
        with pytest.raises(ValueError) as exc_info:
            Skills(
                skill_groups=sample_skill_groups,
                languages={"Common", ""},  # Empty language name
                specializations={},
            )
        assert "Language names cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skills_language_name_too_long_fails(self, sample_skill_groups):
        """Test Skills validation fails with language name too long."""
        long_language = "A" * 31  # 31 characters
        with pytest.raises(ValueError) as exc_info:
            Skills(
                skill_groups=sample_skill_groups,
                languages={"Common", long_language},
                specializations={},
            )
        assert "Language names cannot exceed 30 characters" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skills_empty_specialization_name_fails(self, sample_skill_groups):
        """Test Skills validation fails with empty specialization name."""
        with pytest.raises(ValueError) as exc_info:
            Skills(
                skill_groups=sample_skill_groups,
                languages={"Common"},
                specializations={"": 5},  # Empty specialization name
            )
        assert "Specialization names cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skills_specialization_bonus_too_low_fails(self, sample_skill_groups):
        """Test Skills validation fails with specialization bonus too low."""
        with pytest.raises(ValueError) as exc_info:
            Skills(
                skill_groups=sample_skill_groups,
                languages={"Common"},
                specializations={"test_skill": -6},  # Too low
            )
        assert "Specialization bonus must be between -5 and 15" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_skills_specialization_bonus_too_high_fails(self, sample_skill_groups):
        """Test Skills validation fails with specialization bonus too high."""
        with pytest.raises(ValueError) as exc_info:
            Skills(
                skill_groups=sample_skill_groups,
                languages={"Common"},
                specializations={"test_skill": 16},  # Too high
            )
        assert "Specialization bonus must be between -5 and 15" in str(exc_info.value)

    # ==================== Skill Lookup Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_skill_by_name_found(self, sample_skills):
        """Test getting skill by name when found."""
        skill = sample_skills.get_skill("melee_combat")

        assert skill is not None
        assert skill.name == "Melee Combat"
        assert skill.category == SkillCategory.COMBAT

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_get_skill_by_name_case_insensitive(self, sample_skills):
        """Test getting skill by name is case insensitive."""
        skill = sample_skills.get_skill("MELEE_COMBAT")

        assert skill is not None
        assert skill.name == "Melee Combat"

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_get_skill_by_name_not_found(self, sample_skills):
        """Test getting skill by name when not found."""
        skill = sample_skills.get_skill("nonexistent_skill")

        assert skill is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_skill_by_category_found(self, sample_skills):
        """Test getting skill by name and category when found."""
        skill = sample_skills.get_skill("persuasion", SkillCategory.SOCIAL)

        assert skill is not None
        assert skill.name == "Persuasion"
        assert skill.category == SkillCategory.SOCIAL

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_get_skill_by_category_wrong_category(self, sample_skills):
        """Test getting skill with wrong category returns None."""
        skill = sample_skills.get_skill("melee_combat", SkillCategory.SOCIAL)

        assert skill is None

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_skill_sufficient_proficiency(self, sample_skills):
        """Test has_skill returns True with sufficient proficiency."""
        assert sample_skills.has_skill("melee_combat", ProficiencyLevel.EXPERT) is True
        assert (
            sample_skills.has_skill("melee_combat", ProficiencyLevel.JOURNEYMAN) is True
        )

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_has_skill_insufficient_proficiency(self, sample_skills):
        """Test has_skill returns False with insufficient proficiency."""
        assert sample_skills.has_skill("persuasion", ProficiencyLevel.EXPERT) is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_skill_default_proficiency(self, sample_skills):
        """Test has_skill with default minimum proficiency."""
        assert sample_skills.has_skill("deception") is True  # NOVICE >= NOVICE

    @pytest.mark.unit
    @pytest.mark.fast
    def test_has_skill_nonexistent_skill(self, sample_skills):
        """Test has_skill returns False for non-existent skill."""
        assert sample_skills.has_skill("nonexistent_skill") is False

    # ==================== Modifier Calculation Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_skill_modifier_existing_skill(self, sample_skills):
        """Test getting skill modifier for existing skill."""
        # Melee Combat: EXPERT(4) + modifier(2) = 6 (excluding specialization)
        modifier = sample_skills.get_skill_modifier(
            "melee_combat", include_specialization=False
        )

        assert modifier == 6

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_skill_modifier_with_specialization(self, sample_skills):
        """Test getting skill modifier with specialization bonus."""
        # Melee Combat: EXPERT(4) + modifier(2) + specialization(2) = 8
        modifier = sample_skills.get_skill_modifier(
            "melee_combat", include_specialization=True
        )

        assert modifier == 8

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_skill_modifier_without_specialization(self, sample_skills):
        """Test getting skill modifier without specialization bonus."""
        # Melee Combat: EXPERT(4) + modifier(2) = 6 (ignoring specialization)
        modifier = sample_skills.get_skill_modifier(
            "melee_combat", include_specialization=False
        )

        assert modifier == 6

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_skill_modifier_nonexistent_skill(self, sample_skills):
        """Test getting skill modifier for non-existent skill returns 0."""
        modifier = sample_skills.get_skill_modifier("nonexistent_skill")

        assert modifier == 0

    # ==================== Category and Collection Methods Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_get_skills_by_category_existing(self, sample_skills):
        """Test getting skills by existing category."""
        combat_skills = sample_skills.get_skills_by_category(SkillCategory.COMBAT)

        assert len(combat_skills) == 2
        skill_names = [skill.name for skill in combat_skills]
        assert "Melee Combat" in skill_names
        assert "Ranged Combat" in skill_names

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_skills_by_category_nonexistent(self, sample_skills):
        """Test getting skills by non-existent category returns empty list."""
        magical_skills = sample_skills.get_skills_by_category(SkillCategory.MAGICAL)

        assert magical_skills == []

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_expert_skills(self, sample_skills):
        """Test getting all expert-level skills."""
        expert_skills = sample_skills.get_expert_skills()

        assert len(expert_skills) == 1
        assert expert_skills[0].name == "Melee Combat"
        assert expert_skills[0].proficiency_level == ProficiencyLevel.EXPERT

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_get_master_skills(self, sample_skills):
        """Test getting all master-level skills."""
        master_skills = sample_skills.get_master_skills()

        assert len(master_skills) == 0  # No master-level skills in sample

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_all_skills(self, sample_skills):
        """Test getting all skills across categories."""
        all_skills = sample_skills.get_all_skills()

        assert len(all_skills) == 4  # 2 combat + 2 social
        skill_names = [skill.name for skill in all_skills]
        assert "Melee Combat" in skill_names
        assert "Persuasion" in skill_names

    @pytest.mark.unit
    @pytest.mark.fast
    def test_count_trained_skills(self, sample_skills):
        """Test counting total trained skills."""
        trained_count = sample_skills.count_trained_skills()

        assert trained_count == 4  # All sample skills are trained

    # ==================== Language Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_speaks_language_existing(self, sample_skills):
        """Test speaks_language returns True for known languages."""
        assert sample_skills.speaks_language("Common") is True
        assert sample_skills.speaks_language("Elvish") is True
        assert sample_skills.speaks_language("Draconic") is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_speaks_language_case_insensitive(self, sample_skills):
        """Test speaks_language is case insensitive."""
        assert sample_skills.speaks_language("common") is True
        assert sample_skills.speaks_language("ELVISH") is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_speaks_language_unknown(self, sample_skills):
        """Test speaks_language returns False for unknown languages."""
        assert sample_skills.speaks_language("Orcish") is False
        assert sample_skills.speaks_language("Celestial") is False

    # ==================== Analysis Methods Tests ====================

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_get_strongest_category(self, sample_skills):
        """Test finding strongest skill category."""
        strongest = sample_skills.get_strongest_category()

        # Combat has higher average: EXPERT(4) + JOURNEYMAN(3) = 3.5 avg
        # Social has lower average: APPRENTICE(2) + NOVICE(1) = 1.5 avg
        assert strongest == SkillCategory.COMBAT

    @pytest.mark.unit
    @pytest.mark.unit
    def test_get_strongest_category_empty_skills(self):
        """Test strongest category with minimal skills."""
        minimal_skills = {
            "test": Skill("Test", SkillCategory.PHYSICAL, ProficiencyLevel.NOVICE, 0)
        }

        skill_groups = {
            SkillCategory.PHYSICAL: SkillGroup(
                "Physical", SkillCategory.PHYSICAL, 0, minimal_skills
            )
        }

        skills = Skills(skill_groups=skill_groups, languages=set(), specializations={})

        strongest = skills.get_strongest_category()
        assert strongest == SkillCategory.PHYSICAL

    @pytest.mark.unit
    def test_is_specialist_true(self, sample_skills):
        """Test is_specialist returns True when meeting criteria."""
        # Add more expert combat skills to test
        additional_combat_skills = {
            "melee_combat": Skill(
                "Melee Combat", SkillCategory.COMBAT, ProficiencyLevel.EXPERT, 2
            ),
            "ranged_combat": Skill(
                "Ranged Combat", SkillCategory.COMBAT, ProficiencyLevel.EXPERT, 1
            ),
            "dodge": Skill("Dodge", SkillCategory.COMBAT, ProficiencyLevel.EXPERT, 0),
        }

        skill_groups = {
            SkillCategory.COMBAT: SkillGroup(
                "Combat", SkillCategory.COMBAT, 1, additional_combat_skills
            )
        }

        skills = Skills(skill_groups=skill_groups, languages=set(), specializations={})

        assert skills.is_specialist(SkillCategory.COMBAT, min_expert_skills=3) is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_is_specialist_false(self, sample_skills):
        """Test is_specialist returns False when not meeting criteria."""
        assert (
            sample_skills.is_specialist(SkillCategory.COMBAT, min_expert_skills=3)
            is False
        )

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_can_perform_action_success(self, sample_skills):
        """Test can_perform_action returns True for achievable actions."""
        # Melee Combat modifier is 6 (or 8 with specialization), + 10 base = 16/18
        assert sample_skills.can_perform_action("melee_combat", difficulty=15) is True

    @pytest.mark.unit
    @pytest.mark.fast
    def test_can_perform_action_failure(self, sample_skills):
        """Test can_perform_action returns False for difficult actions."""
        # Deception modifier is 1, + 10 base = 11
        assert sample_skills.can_perform_action("deception", difficulty=20) is False

    @pytest.mark.unit
    @pytest.mark.fast
    def test_can_perform_action_nonexistent_skill(self, sample_skills):
        """Test can_perform_action with non-existent skill."""
        # Non-existent skill has 0 modifier, + 10 base = 10
        assert (
            sample_skills.can_perform_action("nonexistent_skill", difficulty=15)
            is False
        )

    # ==================== Summary Method Tests ====================

    @pytest.mark.unit
    def test_get_skill_summary(self, sample_skills):
        """Test comprehensive skill summary generation."""
        summary = sample_skills.get_skill_summary()

        assert summary["total_skills"] == 4
        assert summary["trained_skills"] == 4
        assert summary["expert_skills"] == 1
        assert summary["master_skills"] == 0
        assert summary["languages_known"] == 3
        assert summary["strongest_category"] == "combat"
        assert summary["specializations"] == 2
        assert len(summary["skill_categories"]) == 2
        assert len(summary["top_skills"]) <= 5

    @pytest.mark.unit
    @pytest.mark.fast
    def test_get_skill_summary_top_skills_ordering(self, sample_skills):
        """Test that top skills are ordered by modifier."""
        summary = sample_skills.get_skill_summary()

        # Should be ordered by total modifier (highest first)
        top_skills = summary["top_skills"]
        assert "Melee Combat" in top_skills  # Highest modifier

    # ==================== Factory Method Tests ====================

    @pytest.mark.unit
    def test_create_basic_skills(self):
        """Test creating basic skill set."""
        basic_skills = Skills.create_basic_skills()

        assert (
            len(basic_skills.skill_groups) == 8
        )  # Combat, Social, Physical, Intellectual, Magical, Survival, Technical, Artistic
        assert SkillCategory.COMBAT in basic_skills.skill_groups
        assert SkillCategory.SOCIAL in basic_skills.skill_groups
        assert SkillCategory.PHYSICAL in basic_skills.skill_groups
        assert SkillCategory.INTELLECTUAL in basic_skills.skill_groups
        assert SkillCategory.MAGICAL in basic_skills.skill_groups
        assert SkillCategory.SURVIVAL in basic_skills.skill_groups
        assert SkillCategory.TECHNICAL in basic_skills.skill_groups
        assert SkillCategory.ARTISTIC in basic_skills.skill_groups

        # Check combat skills
        combat_group = basic_skills.skill_groups[SkillCategory.COMBAT]
        assert combat_group.has_skill("melee_combat")
        assert combat_group.has_skill("ranged_combat")
        assert combat_group.has_skill("dodge")

        # Check languages
        assert "Common" in basic_skills.languages

        # Check specializations is empty
        assert len(basic_skills.specializations) == 0

    @pytest.mark.unit
    @pytest.mark.fast
    def test_create_basic_skills_with_level(self):
        """Test creating basic skills with specific level."""
        # Level parameter exists in signature but doesn't affect current implementation
        basic_skills = Skills.create_basic_skills(level=5)

        # Should create same basic structure regardless of level
        assert len(basic_skills.skill_groups) == 8

    # ==================== Immutability Tests ====================

    @pytest.mark.unit
    def test_skills_immutability(self, sample_skills):
        """Test that Skills is immutable (frozen dataclass)."""
        with pytest.raises(Exception):  # Should raise FrozenInstanceError
            # Test that you can't assign new values to frozen fields
            sample_skills.skill_groups = {}

    @pytest.mark.unit
    def test_skill_immutability(self):
        """Test that Skill is immutable."""
        skill = Skill("Test", SkillCategory.COMBAT, ProficiencyLevel.NOVICE, 0)

        with pytest.raises(AttributeError):
            skill.modifier = 5

    @pytest.mark.unit
    def test_skill_group_immutability(self):
        """Test that SkillGroup is immutable."""
        skills_dict = {
            "test": Skill("Test", SkillCategory.COMBAT, ProficiencyLevel.NOVICE, 0)
        }
        group = SkillGroup("Test", SkillCategory.COMBAT, 0, skills_dict)

        with pytest.raises(AttributeError):
            group.base_modifier = 5

    # ==================== Edge Cases and Integration Tests ====================

    @pytest.mark.unit
    def test_skills_with_overlapping_specializations(self, sample_skill_groups):
        """Test skills with specializations for non-existent skills."""
        skills = Skills(
            skill_groups=sample_skill_groups,
            languages={"Common"},
            specializations={
                "melee_combat": 3,  # Exists
                "nonexistent_skill": 2,  # Doesn't exist
            },
        )

        # Should work with existing skill
        modifier_existing = skills.get_skill_modifier("melee_combat")
        assert modifier_existing == 9  # EXPERT(4) + modifier(2) + specialization(3)

        # Should return 0 for non-existent skill
        modifier_nonexistent = skills.get_skill_modifier("nonexistent_skill")
        assert modifier_nonexistent == 0

    @pytest.mark.unit
    def test_skills_boundary_values_comprehensive(self):
        """Test skills with various boundary value combinations."""
        # Create skills with extreme values
        extreme_skills = {
            "max_skill": Skill(
                "Max Skill",
                SkillCategory.COMBAT,
                ProficiencyLevel.LEGENDARY,  # Max proficiency
                20,  # Max modifier
            ),
            "min_skill": Skill(
                "Min Skill",
                SkillCategory.COMBAT,
                ProficiencyLevel.UNTRAINED,  # Min proficiency
                -10,  # Min modifier
            ),
        }

        skill_groups = {
            SkillCategory.COMBAT: SkillGroup(
                "Combat", SkillCategory.COMBAT, 10, extreme_skills
            )  # Max base
        }

        skills = Skills(
            skill_groups=skill_groups,
            languages={"A" * 30},  # Max language name length
            specializations={
                "max_skill": 15,
                "min_skill": -5,
            },  # Max/min specialization bonuses
        )

        # Test maximum modifier calculation
        max_modifier = skills.get_skill_modifier("max_skill")
        assert max_modifier == 42  # LEGENDARY(7) + modifier(20) + specialization(15)

        # Test minimum modifier calculation
        min_modifier = skills.get_skill_modifier("min_skill")
        assert min_modifier == -15  # UNTRAINED(0) + modifier(-10) + specialization(-5)
