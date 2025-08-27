#!/usr/bin/env python3
"""
Skills Value Object

This module implements character skills and proficiencies, representing learned
abilities, expertise levels, and skill-based modifiers for character actions.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from enum import Enum


class SkillCategory(Enum):
    """Categories of skills for organization."""
    COMBAT = "combat"
    SOCIAL = "social"
    INTELLECTUAL = "intellectual"
    PHYSICAL = "physical"
    TECHNICAL = "technical"
    MAGICAL = "magical"
    SURVIVAL = "survival"
    ARTISTIC = "artistic"
    PROFESSIONAL = "professional"


class ProficiencyLevel(Enum):
    """Levels of skill proficiency."""
    UNTRAINED = 0
    NOVICE = 1
    APPRENTICE = 2
    JOURNEYMAN = 3
    EXPERT = 4
    MASTER = 5
    GRANDMASTER = 6
    LEGENDARY = 7


@dataclass(frozen=True)
class Skill:
    """Individual skill with name, category, and proficiency level."""
    name: str
    category: SkillCategory
    proficiency_level: ProficiencyLevel
    modifier: int  # Additional modifier from equipment, training, etc.
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate skill data."""
        if not self.name or not self.name.strip():
            raise ValueError("Skill name cannot be empty")
        
        if len(self.name.strip()) > 50:
            raise ValueError("Skill name cannot exceed 50 characters")
        
        if not -10 <= self.modifier <= 20:
            raise ValueError("Skill modifier must be between -10 and 20")
        
        if self.description and len(self.description) > 500:
            raise ValueError("Skill description cannot exceed 500 characters")
    
    def get_total_modifier(self) -> int:
        """Get the total skill modifier including proficiency."""
        return self.proficiency_level.value + self.modifier
    
    def is_trained(self) -> bool:
        """Check if character has training in this skill."""
        return self.proficiency_level != ProficiencyLevel.UNTRAINED
    
    def is_expert_level(self) -> bool:
        """Check if character is expert level or higher."""
        return self.proficiency_level.value >= ProficiencyLevel.EXPERT.value
    
    def is_master_level(self) -> bool:
        """Check if character is master level or higher."""
        return self.proficiency_level.value >= ProficiencyLevel.MASTER.value
    
    def get_proficiency_description(self) -> str:
        """Get a text description of the proficiency level."""
        descriptions = {
            ProficiencyLevel.UNTRAINED: "No training",
            ProficiencyLevel.NOVICE: "Basic understanding",
            ProficiencyLevel.APPRENTICE: "Learning the fundamentals",
            ProficiencyLevel.JOURNEYMAN: "Competent practitioner", 
            ProficiencyLevel.EXPERT: "Highly skilled professional",
            ProficiencyLevel.MASTER: "Acknowledged master of the art",
            ProficiencyLevel.GRANDMASTER: "Among the greatest practitioners",
            ProficiencyLevel.LEGENDARY: "Legendary skill transcending normal limits"
        }
        return descriptions[self.proficiency_level]


@dataclass(frozen=True)
class SkillGroup:
    """Group of related skills with shared modifiers."""
    name: str
    category: SkillCategory
    base_modifier: int
    skills: Dict[str, Skill]
    
    def __post_init__(self):
        """Validate skill group."""
        if not self.name or not self.name.strip():
            raise ValueError("Skill group name cannot be empty")
        
        if not -5 <= self.base_modifier <= 10:
            raise ValueError("Base modifier must be between -5 and 10")
        
        if not self.skills:
            raise ValueError("Skill group must contain at least one skill")
        
        # Validate all skills in group match category
        for skill in self.skills.values():
            if skill.category != self.category:
                raise ValueError(f"All skills in group must match category {self.category.value}")
    
    def get_skill(self, skill_name: str) -> Optional[Skill]:
        """Get a specific skill from the group."""
        return self.skills.get(skill_name.lower())
    
    def has_skill(self, skill_name: str) -> bool:
        """Check if group contains a specific skill."""
        return skill_name.lower() in self.skills
    
    def get_average_proficiency(self) -> float:
        """Get the average proficiency level for the group."""
        if not self.skills:
            return 0.0
        
        total = sum(skill.proficiency_level.value for skill in self.skills.values())
        return total / len(self.skills)
    
    def get_expert_skills(self) -> List[Skill]:
        """Get all expert-level or higher skills in the group."""
        return [skill for skill in self.skills.values() if skill.is_expert_level()]
    
    def count_trained_skills(self) -> int:
        """Count the number of trained skills in the group."""
        return sum(1 for skill in self.skills.values() if skill.is_trained())


@dataclass(frozen=True)
class Skills:
    """
    Complete skills value object representing all character abilities.
    
    Organizes skills by category and provides methods for skill checks,
    proficiency queries, and skill-based character interactions.
    """
    
    skill_groups: Dict[SkillCategory, SkillGroup]
    languages: Set[str]
    specializations: Dict[str, int]  # Special skill bonuses
    
    def __post_init__(self):
        """Validate skills data."""
        if not self.skill_groups:
            raise ValueError("Character must have at least one skill group")
        
        # Validate language set
        if self.languages:
            for language in self.languages:
                if not language or not language.strip():
                    raise ValueError("Language names cannot be empty")
                if len(language) > 30:
                    raise ValueError("Language names cannot exceed 30 characters")
        
        # Validate specializations
        if self.specializations:
            for spec_name, bonus in self.specializations.items():
                if not spec_name or not spec_name.strip():
                    raise ValueError("Specialization names cannot be empty")
                if not -5 <= bonus <= 15:
                    raise ValueError("Specialization bonus must be between -5 and 15")
    
    def get_skill(self, skill_name: str, category: Optional[SkillCategory] = None) -> Optional[Skill]:
        """Get a specific skill, optionally filtered by category."""
        skill_name_lower = skill_name.lower()
        
        if category:
            group = self.skill_groups.get(category)
            return group.get_skill(skill_name_lower) if group else None
        
        # Search all categories
        for group in self.skill_groups.values():
            skill = group.get_skill(skill_name_lower)
            if skill:
                return skill
        
        return None
    
    def has_skill(self, skill_name: str, min_proficiency: ProficiencyLevel = ProficiencyLevel.NOVICE) -> bool:
        """Check if character has a skill at minimum proficiency level."""
        skill = self.get_skill(skill_name)
        if not skill:
            return False
        
        return skill.proficiency_level.value >= min_proficiency.value
    
    def get_skill_modifier(self, skill_name: str, include_specialization: bool = True) -> int:
        """Get the total modifier for a skill including specializations."""
        skill = self.get_skill(skill_name)
        if not skill:
            return 0  # Untrained
        
        modifier = skill.get_total_modifier()
        
        # Add specialization bonus
        if include_specialization and skill_name.lower() in self.specializations:
            modifier += self.specializations[skill_name.lower()]
        
        return modifier
    
    def get_skills_by_category(self, category: SkillCategory) -> List[Skill]:
        """Get all skills in a specific category."""
        group = self.skill_groups.get(category)
        return list(group.skills.values()) if group else []
    
    def get_expert_skills(self) -> List[Skill]:
        """Get all expert-level or higher skills."""
        expert_skills = []
        for group in self.skill_groups.values():
            expert_skills.extend(group.get_expert_skills())
        return expert_skills
    
    def get_master_skills(self) -> List[Skill]:
        """Get all master-level or higher skills."""
        return [skill for skill in self.get_all_skills() if skill.is_master_level()]
    
    def get_all_skills(self) -> List[Skill]:
        """Get all skills across all categories."""
        all_skills = []
        for group in self.skill_groups.values():
            all_skills.extend(group.skills.values())
        return all_skills
    
    def count_trained_skills(self) -> int:
        """Count total number of trained skills."""
        return sum(group.count_trained_skills() for group in self.skill_groups.values())
    
    def speaks_language(self, language: str) -> bool:
        """Check if character speaks a specific language."""
        return language.lower() in {lang.lower() for lang in self.languages}
    
    def get_strongest_category(self) -> SkillCategory:
        """Get the skill category with the highest average proficiency."""
        if not self.skill_groups:
            return SkillCategory.PHYSICAL
        
        category_averages = {
            category: group.get_average_proficiency()
            for category, group in self.skill_groups.items()
        }
        
        return max(category_averages.keys(), key=lambda k: category_averages[k])
    
    def is_specialist(self, category: SkillCategory, min_expert_skills: int = 3) -> bool:
        """Check if character is a specialist in a skill category."""
        expert_skills = self.get_skills_by_category(category)
        expert_count = sum(1 for skill in expert_skills if skill.is_expert_level())
        return expert_count >= min_expert_skills
    
    def get_skill_summary(self) -> Dict[str, any]:
        """Get a comprehensive summary of character skills."""
        all_skills = self.get_all_skills()
        expert_skills = self.get_expert_skills()
        master_skills = self.get_master_skills()
        
        return {
            "total_skills": len(all_skills),
            "trained_skills": self.count_trained_skills(),
            "expert_skills": len(expert_skills),
            "master_skills": len(master_skills),
            "languages_known": len(self.languages),
            "strongest_category": self.get_strongest_category().value,
            "specializations": len(self.specializations),
            "skill_categories": list(self.skill_groups.keys()),
            "top_skills": [skill.name for skill in sorted(all_skills, 
                key=lambda s: s.get_total_modifier(), reverse=True)[:5]]
        }
    
    def can_perform_action(self, skill_name: str, difficulty: int) -> bool:
        """Check if character can reasonably perform an action requiring a skill."""
        skill_modifier = self.get_skill_modifier(skill_name)
        # Basic success threshold: skill modifier + base roll (assume average of 10)
        return skill_modifier + 10 >= difficulty
    
    @classmethod
    def create_basic_skills(cls, level: int = 1) -> 'Skills':
        """Create a basic skill set for a new character."""
        # Create basic skill groups
        combat_skills = SkillGroup(
            name="Combat Skills",
            category=SkillCategory.COMBAT,
            base_modifier=0,
            skills={
                "melee_combat": Skill("Melee Combat", SkillCategory.COMBAT, ProficiencyLevel.NOVICE, 0),
                "ranged_combat": Skill("Ranged Combat", SkillCategory.COMBAT, ProficiencyLevel.NOVICE, 0),
                "dodge": Skill("Dodge", SkillCategory.COMBAT, ProficiencyLevel.NOVICE, 0),
            }
        )
        
        social_skills = SkillGroup(
            name="Social Skills",
            category=SkillCategory.SOCIAL,
            base_modifier=0,
            skills={
                "persuasion": Skill("Persuasion", SkillCategory.SOCIAL, ProficiencyLevel.NOVICE, 0),
                "deception": Skill("Deception", SkillCategory.SOCIAL, ProficiencyLevel.UNTRAINED, 0),
                "intimidation": Skill("Intimidation", SkillCategory.SOCIAL, ProficiencyLevel.UNTRAINED, 0),
            }
        )
        
        physical_skills = SkillGroup(
            name="Physical Skills",
            category=SkillCategory.PHYSICAL,
            base_modifier=0,
            skills={
                "athletics": Skill("Athletics", SkillCategory.PHYSICAL, ProficiencyLevel.NOVICE, 0),
                "acrobatics": Skill("Acrobatics", SkillCategory.PHYSICAL, ProficiencyLevel.UNTRAINED, 0),
                "stealth": Skill("Stealth", SkillCategory.PHYSICAL, ProficiencyLevel.NOVICE, 0),
            }
        )
        
        intellectual_skills = SkillGroup(
            name="Intellectual Skills",
            category=SkillCategory.INTELLECTUAL,
            base_modifier=0,
            skills={
                "investigation": Skill("Investigation", SkillCategory.INTELLECTUAL, ProficiencyLevel.NOVICE, 0),
                "history": Skill("History", SkillCategory.INTELLECTUAL, ProficiencyLevel.UNTRAINED, 0),
                "arcana": Skill("Arcana", SkillCategory.INTELLECTUAL, ProficiencyLevel.UNTRAINED, 0),
            }
        )
        
        magical_skills = SkillGroup(
            name="Magical Skills", 
            category=SkillCategory.MAGICAL,
            base_modifier=0,
            skills={
                "spellcasting": Skill("Spellcasting", SkillCategory.MAGICAL, ProficiencyLevel.NOVICE, 0),
                "enchantment": Skill("Enchantment", SkillCategory.MAGICAL, ProficiencyLevel.UNTRAINED, 0),
                "magical_theory": Skill("Magical Theory", SkillCategory.MAGICAL, ProficiencyLevel.UNTRAINED, 0),
            }
        )
        
        survival_skills = SkillGroup(
            name="Survival Skills",
            category=SkillCategory.SURVIVAL,
            base_modifier=0,
            skills={
                "wilderness_survival": Skill("Wilderness Survival", SkillCategory.SURVIVAL, ProficiencyLevel.NOVICE, 0),
                "tracking": Skill("Tracking", SkillCategory.SURVIVAL, ProficiencyLevel.UNTRAINED, 0),
                "foraging": Skill("Foraging", SkillCategory.SURVIVAL, ProficiencyLevel.UNTRAINED, 0),
            }
        )
        
        technical_skills = SkillGroup(
            name="Technical Skills",
            category=SkillCategory.TECHNICAL,
            base_modifier=0,
            skills={
                "engineering": Skill("Engineering", SkillCategory.TECHNICAL, ProficiencyLevel.NOVICE, 0),
                "technology": Skill("Technology", SkillCategory.TECHNICAL, ProficiencyLevel.UNTRAINED, 0),
                "repair": Skill("Repair", SkillCategory.TECHNICAL, ProficiencyLevel.UNTRAINED, 0),
            }
        )
        
        artistic_skills = SkillGroup(
            name="Artistic Skills",
            category=SkillCategory.ARTISTIC,
            base_modifier=0,
            skills={
                "performance": Skill("Performance", SkillCategory.ARTISTIC, ProficiencyLevel.NOVICE, 0),
                "art": Skill("Art", SkillCategory.ARTISTIC, ProficiencyLevel.UNTRAINED, 0),
                "music": Skill("Music", SkillCategory.ARTISTIC, ProficiencyLevel.UNTRAINED, 0),
            }
        )
        
        return cls(
            skill_groups={
                SkillCategory.COMBAT: combat_skills,
                SkillCategory.SOCIAL: social_skills,
                SkillCategory.PHYSICAL: physical_skills,
                SkillCategory.INTELLECTUAL: intellectual_skills,
                SkillCategory.MAGICAL: magical_skills,
                SkillCategory.SURVIVAL: survival_skills,
                SkillCategory.TECHNICAL: technical_skills,
                SkillCategory.ARTISTIC: artistic_skills,
            },
            languages={"Common"},
            specializations={}
        )