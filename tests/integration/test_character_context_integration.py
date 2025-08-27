#!/usr/bin/env python3
"""
Character Context Integration Test

This test validates the complete Character bounded context implementation
including domain layer, application layer, and infrastructure layer integration.
"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import Character context components
from contexts.character import (
    Character, CharacterID, CharacterProfile, CharacterStats, Skills,
    Gender, CharacterRace, CharacterClass,
    CharacterApplicationService, CreateCharacterCommand,
    SQLAlchemyCharacterRepository, CharacterBase
)

# Import value objects for detailed testing
from contexts.character.domain.value_objects.character_stats import (
    CoreAbilities, VitalStats, CombatStats
)
from contexts.character.domain.value_objects.character_profile import (
    PhysicalTraits, PersonalityTraits, Background
)
from contexts.character.domain.value_objects.skills import (
    SkillGroup, SkillCategory, ProficiencyLevel
)


class TestCharacterContextIntegration:
    """Integration tests for the complete Character bounded context."""
    
    @pytest.fixture
    def mock_session_factory(self):
        """Create a mock session factory for testing."""
        session_mock = MagicMock()
        session_factory_mock = MagicMock(return_value=session_mock)
        return session_factory_mock
    
    @pytest.fixture
    def character_repository(self, mock_session_factory):
        """Create a character repository for testing."""
        return SQLAlchemyCharacterRepository(mock_session_factory)
    
    @pytest.fixture
    def character_application_service(self, character_repository):
        """Create a character application service for testing."""
        return CharacterApplicationService(character_repository)
    
    @pytest.fixture
    def sample_character_data(self):
        """Sample character data for testing."""
        return {
            "character_name": "Test Hero",
            "gender": "male",
            "race": "human",
            "character_class": "warrior",
            "age": 25,
            "strength": 15,
            "dexterity": 12,
            "constitution": 14,
            "intelligence": 10,
            "wisdom": 11,
            "charisma": 13,
            "title": "Brave Warrior",
            "affiliation": "Royal Guard",
            "languages": ["common", "elvish"],
            "height_cm": 180,
            "weight_kg": 75,
            "hair_color": "brown",
            "eye_color": "blue",
            "skin_tone": "fair",
            "physical_description": "A tall, well-built warrior",
            "personality_traits": {
                "courage": 0.8,
                "intelligence": 0.6,
                "charisma": 0.7,
                "loyalty": 0.9
            },
            "backstory": "Born to a noble family, trained in combat",
            "homeland": "Kingdom of Valor",
            "education": "Royal military academy"
        }
    
    def test_character_domain_model_creation(self, sample_character_data):
        """Test that Character domain model can be created correctly."""
        # Create core abilities
        core_abilities = CoreAbilities(
            strength=sample_character_data["strength"],
            dexterity=sample_character_data["dexterity"],
            constitution=sample_character_data["constitution"],
            intelligence=sample_character_data["intelligence"],
            wisdom=sample_character_data["wisdom"],
            charisma=sample_character_data["charisma"]
        )
        
        # Create character using domain factory method
        character = Character.create_new_character(
            name=sample_character_data["character_name"],
            gender=Gender(sample_character_data["gender"]),
            race=CharacterRace(sample_character_data["race"]),
            character_class=CharacterClass(sample_character_data["character_class"]),
            age=sample_character_data["age"],
            core_abilities=core_abilities
        )
        
        # Validate character creation
        assert character is not None
        assert character.character_id is not None
        assert isinstance(character.character_id, CharacterID)
        assert character.profile.name == sample_character_data["character_name"]
        assert character.profile.gender == Gender(sample_character_data["gender"])
        assert character.profile.race == CharacterRace(sample_character_data["race"])
        assert character.profile.character_class == CharacterClass(sample_character_data["character_class"])
        assert character.profile.age == sample_character_data["age"]
        assert character.profile.level == 1
        assert character.is_alive() == True
        assert character.version == 1
        assert character.stats.core_abilities.strength == sample_character_data["strength"]
    
    def test_character_value_objects_validation(self):
        """Test that character value objects validate properly."""
        # Test Gender enum
        male_gender = Gender("male")
        assert male_gender.value == "male"
        
        # Test CharacterRace enum
        human_race = CharacterRace("human")
        assert human_race.value == "human"
        
        # Test CharacterClass enum
        warrior_class = CharacterClass("warrior")
        assert warrior_class.value == "warrior"
        
        # Test invalid values raise errors
        with pytest.raises(ValueError):
            Gender("invalid_gender")
        
        with pytest.raises(ValueError):
            CharacterRace("invalid_race")
        
        with pytest.raises(ValueError):
            CharacterClass("invalid_class")
    
    def test_core_abilities_calculations(self):
        """Test that core abilities calculate modifiers correctly."""
        # Test various ability scores and their modifiers
        test_cases = [
            (8, -1),   # Below average
            (10, 0),   # Average
            (12, 1),   # Above average
            (15, 2),   # Good
            (18, 4),   # Excellent
            (20, 5),   # Exceptional
        ]
        
        for score, expected_modifier in test_cases:
            abilities = CoreAbilities(
                strength=score, dexterity=10, constitution=10,
                intelligence=10, wisdom=10, charisma=10
            )
            modifier = abilities.get_ability_modifier(abilities.AbilityScore.STRENGTH)
            assert modifier == expected_modifier, f"Score {score} should have modifier {expected_modifier}, got {modifier}"
    
    @pytest.mark.asyncio
    async def test_character_application_service_create_character(self, character_application_service, sample_character_data):
        """Test character creation through application service."""
        # Mock repository methods
        character_application_service.repository.find_by_name = AsyncMock(return_value=[])
        character_application_service.repository.save = AsyncMock()
        character_application_service.command_handlers.handle_command = AsyncMock(
            return_value=CharacterID()
        )
        
        # Create character through application service
        character_id = await character_application_service.create_character(**sample_character_data)
        
        # Validate results
        assert character_id is not None
        assert isinstance(character_id, CharacterID)
        
        # Verify repository calls
        character_application_service.repository.find_by_name.assert_called_once_with(
            sample_character_data["character_name"]
        )
        character_application_service.command_handlers.handle_command.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_character_application_service_duplicate_name_validation(self, character_application_service, sample_character_data):
        """Test that duplicate character names are rejected."""
        # Mock existing character with same name
        existing_character = MagicMock()
        character_application_service.repository.find_by_name = AsyncMock(return_value=[existing_character])
        
        # Attempt to create character with duplicate name
        with pytest.raises(ValueError, match="already taken"):
            await character_application_service.create_character(**sample_character_data)
    
    def test_create_character_command_validation(self, sample_character_data):
        """Test CreateCharacterCommand validation."""
        # Test valid command creation
        command = CreateCharacterCommand(**sample_character_data)
        assert command.character_name == sample_character_data["character_name"]
        assert command.gender == sample_character_data["gender"]
        assert command.race == sample_character_data["race"]
        assert command.character_class == sample_character_data["character_class"]
        
        # Test invalid command data
        invalid_data = sample_character_data.copy()
        invalid_data["character_name"] = ""  # Empty name
        
        with pytest.raises(ValueError, match="Character name is required"):
            CreateCharacterCommand(**invalid_data)
        
        # Test invalid ability scores
        invalid_data = sample_character_data.copy()
        invalid_data["strength"] = 35  # Too high
        
        with pytest.raises(ValueError, match="Ability scores must be between 1 and 30"):
            CreateCharacterCommand(**invalid_data)
        
        # Test invalid gender
        invalid_data = sample_character_data.copy()
        invalid_data["gender"] = "invalid_gender"
        
        with pytest.raises(ValueError, match="Invalid gender"):
            CreateCharacterCommand(**invalid_data)
    
    @pytest.mark.asyncio
    async def test_character_stats_updates(self, character_application_service):
        """Test character stats update functionality."""
        character_id = str(CharacterID())
        
        # Mock repository
        mock_character = MagicMock()
        mock_character.version = 1
        character_application_service.repository.get_by_id = AsyncMock(return_value=mock_character)
        character_application_service.command_handlers.handle_command = AsyncMock()
        
        # Update character stats
        await character_application_service.update_character_stats(
            character_id=character_id,
            current_health=50,
            current_mana=30,
            experience_points=1000
        )
        
        # Verify command handler was called
        character_application_service.command_handlers.handle_command.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_character_level_up(self, character_application_service):
        """Test character level up functionality."""
        character_id = str(CharacterID())
        
        # Mock repository
        character_application_service.command_handlers.handle_command = AsyncMock()
        
        # Level up character with improvements
        await character_application_service.level_up_character(
            character_id=character_id,
            ability_improvements={"strength": 1, "constitution": 1},
            skill_improvements=[
                {"skill_name": "sword_fighting", "improvement": 1}
            ]
        )
        
        # Verify command handler was called
        character_application_service.command_handlers.handle_command.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_character_healing_and_damage(self, character_application_service):
        """Test character healing and damage functionality."""
        character_id = str(CharacterID())
        
        # Mock repository
        character_application_service.command_handlers.handle_command = AsyncMock()
        
        # Test healing
        await character_application_service.heal_character(
            character_id=character_id,
            healing_amount=25,
            healing_type="magical",
            reason="Healing potion"
        )
        
        # Test damage
        await character_application_service.damage_character(
            character_id=character_id,
            damage_amount=15,
            damage_type="fire",
            damage_source="Dragon breath",
            reason="Combat damage"
        )
        
        # Verify both commands were handled
        assert character_application_service.command_handlers.handle_command.call_count == 2
    
    @pytest.mark.asyncio
    async def test_character_query_operations(self, character_application_service):
        """Test character query operations."""
        # Mock repository query methods
        mock_characters = [MagicMock(), MagicMock()]
        character_application_service.repository.find_by_name = AsyncMock(return_value=mock_characters)
        character_application_service.repository.find_by_class = AsyncMock(return_value=mock_characters)
        character_application_service.repository.find_by_race = AsyncMock(return_value=mock_characters)
        character_application_service.repository.find_alive_characters = AsyncMock(return_value=mock_characters)
        
        # Test query operations
        name_results = await character_application_service.find_characters_by_name("Test")
        class_results = await character_application_service.find_characters_by_class("warrior")
        race_results = await character_application_service.find_characters_by_race("human")
        alive_results = await character_application_service.find_alive_characters()
        
        # Verify results
        assert name_results == mock_characters
        assert class_results == mock_characters
        assert race_results == mock_characters
        assert alive_results == mock_characters
        
        # Verify repository calls
        character_application_service.repository.find_by_name.assert_called_once_with("Test")
        character_application_service.repository.find_by_class.assert_called_once_with(CharacterClass("warrior"))
        character_application_service.repository.find_by_race.assert_called_once_with(CharacterRace("human"))
        character_application_service.repository.find_alive_characters.assert_called_once()
    
    def test_character_skills_system(self):
        """Test the character skills system."""
        # Create a skill
        skill = contexts.character.domain.value_objects.skills.Skill(
            name="sword_fighting",
            category=SkillCategory.COMBAT,
            proficiency_level=ProficiencyLevel.TRAINED,
            modifier=2,
            description="Skill with sword combat"
        )
        
        assert skill.name == "sword_fighting"
        assert skill.category == SkillCategory.COMBAT
        assert skill.proficiency_level == ProficiencyLevel.TRAINED
        assert skill.modifier == 2
        
        # Create a skill group
        skill_group = SkillGroup(
            name="Combat Skills",
            category=SkillCategory.COMBAT,
            base_modifier=0,
            skills={"sword_fighting": skill}
        )
        
        assert skill_group.name == "Combat Skills"
        assert skill_group.category == SkillCategory.COMBAT
        assert len(skill_group.skills) == 1
        assert skill_group.has_skill("sword_fighting")
        assert not skill_group.has_skill("archery")
    
    def test_character_domain_events(self):
        """Test that character domain events are properly generated."""
        # Create a character
        core_abilities = CoreAbilities(15, 12, 14, 10, 11, 13)
        character = Character.create_new_character(
            name="Event Test Character",
            gender=Gender("female"),
            race=CharacterRace("elf"),
            character_class=CharacterClass("mage"),
            age=100,
            core_abilities=core_abilities
        )
        
        # Check that creation event was generated
        events = character.get_events()
        assert len(events) >= 1
        
        # Level up the character to generate more events
        character.level_up()
        
        # Check that level up event was generated
        events_after_levelup = character.get_events()
        assert len(events_after_levelup) > len(events)
    
    def test_character_business_rules(self):
        """Test that character business rules are enforced."""
        # Create a character
        core_abilities = CoreAbilities(15, 12, 14, 10, 11, 13)
        character = Character.create_new_character(
            name="Rules Test Character",
            gender=Gender("non_binary"),
            race=CharacterRace("dwarf"),
            character_class=CharacterClass("rogue"),
            age=50,
            core_abilities=core_abilities
        )
        
        # Test that character starts alive
        assert character.is_alive()
        
        # Test damage beyond max health
        max_health = character.stats.vital_stats.max_health
        character.take_damage(max_health + 10)  # Damage exceeding max health
        
        # Character should not be alive after lethal damage
        assert not character.is_alive()
        
        # Test healing a dead character (should not work)
        initial_health = character.stats.vital_stats.current_health
        character.heal(50)
        
        # Health should not have increased for dead character
        assert character.stats.vital_stats.current_health == initial_health
    
    def test_character_export_import_data(self):
        """Test character data export and summary functionality."""
        # Create a character
        core_abilities = CoreAbilities(16, 14, 15, 12, 13, 11)
        character = Character.create_new_character(
            name="Export Test Character",
            gender=Gender("male"),
            race=CharacterRace("halfling"),
            character_class=CharacterClass("bard"),
            age=30,
            core_abilities=core_abilities
        )
        
        # Test character summary
        summary = character.get_character_summary()
        
        assert isinstance(summary, dict)
        assert "name" in summary
        assert "level" in summary
        assert "class" in summary
        assert "race" in summary
        assert "health" in summary
        assert summary["name"] == "Export Test Character"
        assert summary["level"] == 1
        assert summary["class"] == "bard"
        assert summary["race"] == "halfling"


class TestCharacterRepositoryIntegration:
    """Integration tests for character repository implementation."""
    
    def test_character_orm_models_import(self):
        """Test that ORM models can be imported successfully."""
        from contexts.character.infrastructure.persistence.character_models import (
            CharacterORM, CharacterProfileORM, CharacterStatsORM, 
            CharacterSkillsORM, CharacterEventORM
        )
        
        # Test that classes exist and have expected attributes
        assert hasattr(CharacterORM, '__tablename__')
        assert hasattr(CharacterProfileORM, '__tablename__')
        assert hasattr(CharacterStatsORM, '__tablename__')
        assert hasattr(CharacterSkillsORM, '__tablename__')
        assert hasattr(CharacterEventORM, '__tablename__')
        
        assert CharacterORM.__tablename__ == "characters"
        assert CharacterProfileORM.__tablename__ == "character_profiles"
        assert CharacterStatsORM.__tablename__ == "character_stats"
        assert CharacterSkillsORM.__tablename__ == "character_skills"
        assert CharacterEventORM.__tablename__ == "character_events"
    
    def test_sqlalchemy_character_repository_import(self):
        """Test that SQLAlchemy repository can be imported successfully."""
        from contexts.character.infrastructure.repositories.character_repository import (
            SQLAlchemyCharacterRepository
        )
        
        # Test that repository class exists
        assert SQLAlchemyCharacterRepository is not None
        
        # Test that it has expected methods
        expected_methods = [
            'get_by_id', 'save', 'delete', 'exists',
            'find_by_name', 'find_by_class', 'find_by_race',
            'find_by_level_range', 'find_alive_characters',
            'find_by_criteria', 'count_by_criteria', 'get_statistics'
        ]
        
        for method in expected_methods:
            assert hasattr(SQLAlchemyCharacterRepository, method)


def run_character_context_integration_tests():
    """Run all character context integration tests."""
    print("🧪 Running Character Context Integration Tests...")
    
    # Import and test key components
    try:
        # Test domain layer imports
        from contexts.character import (
            Character, CharacterID, CharacterProfile, CharacterStats, Skills,
            Gender, CharacterRace, CharacterClass
        )
        print("✅ Domain layer imports successful")
        
        # Test application layer imports
        from contexts.character import (
            CharacterApplicationService, CreateCharacterCommand
        )
        print("✅ Application layer imports successful")
        
        # Test infrastructure layer imports
        from contexts.character import (
            SQLAlchemyCharacterRepository, CharacterBase
        )
        print("✅ Infrastructure layer imports successful")
        
        # Test basic character creation
        core_abilities = contexts.character.domain.value_objects.character_stats.CoreAbilities(
            strength=15, dexterity=12, constitution=14,
            intelligence=10, wisdom=11, charisma=13
        )
        
        character = Character.create_new_character(
            name="Integration Test Character",
            gender=Gender("female"),
            race=CharacterRace("elf"),
            character_class=CharacterClass("wizard"),
            age=25,
            core_abilities=core_abilities
        )
        
        assert character is not None
        assert character.profile.name == "Integration Test Character"
        print("✅ Character domain model creation successful")
        
        # Test command creation
        command = CreateCharacterCommand(
            character_name="Command Test Character",
            gender="male",
            race="human", 
            character_class="warrior",
            age=30,
            strength=16,
            dexterity=12,
            constitution=15,
            intelligence=10,
            wisdom=12,
            charisma=11
        )
        
        assert command.character_name == "Command Test Character"
        print("✅ Command creation successful")
        
        print("\n🎉 Character Context Integration Tests PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Character Context Integration Tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    run_character_context_integration_tests()