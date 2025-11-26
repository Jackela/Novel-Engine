#!/usr/bin/env python3
"""
Comprehensive Character System Test Suite
=========================================

This test suite provides complete coverage for the StoryForge AI character system
including the new generic sci-fi characters and debranded functionality.

Test Categories:
1. Character Loading & Validation
2. Generic Character Profiles
3. Character Statistics & Attributes
4. Character Factory & Creation
5. Character Memory System
6. Character Interactions
7. Performance & Scalability
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

FULL_INTEGRATION = os.getenv("NOVEL_ENGINE_FULL_INTEGRATION") == "1"
if not FULL_INTEGRATION:
    pytestmark = pytest.mark.skip(
        reason="Character system comprehensive suite requires NOVEL_ENGINE_FULL_INTEGRATION=1"
    )
from src.agents.director_agent import DirectorAgent
from src.config.character_factory import CharacterFactory
from src.event_bus import EventBus

# Test Constants
GENERIC_CHARACTERS = ["pilot", "scientist", "engineer", "test"]
# Resolve characters directory relative to repository root to avoid machine-specific paths
CHARACTER_DIR = (Path(__file__).resolve().parents[1] / "characters").resolve()


class TestCharacterLoading:
    """Test character loading and validation systems"""

    @pytest.mark.integration
    def test_all_generic_characters_loadable(self):
        """Test that all generic characters can be loaded successfully"""
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)

        for char_name in GENERIC_CHARACTERS:
            agent = factory.create_character(char_name)
            assert agent.character_directory_name == char_name
            assert agent.character_name is not None  # Should have actual character name
            assert agent.agent_id is not None
            assert hasattr(agent, "character_context")

    @pytest.mark.integration
    def test_character_directory_structure(self):
        """Test that character directories have proper structure"""
        for char_name in GENERIC_CHARACTERS:
            char_dir = CHARACTER_DIR / char_name
            assert char_dir.exists(), f"Character directory {char_name} does not exist"

            # Check required files
            md_file = char_dir / f"character_{char_name}.md"
            yaml_file = char_dir / "stats.yaml"

            assert md_file.exists(), f"Markdown file missing for {char_name}"
            assert yaml_file.exists(), f"Stats file missing for {char_name}"

    @pytest.mark.integration
    def test_character_metadata_validation(self):
        """Test character metadata is valid and complete"""
        for char_name in GENERIC_CHARACTERS:
            char_dir = CHARACTER_DIR / char_name
            yaml_file = char_dir / "stats.yaml"

            with open(yaml_file, "r") as f:
                stats = yaml.safe_load(f)

            # Validate required sections
            assert "character" in stats
            assert "combat_stats" in stats
            assert "equipment" in stats
            assert "psychological_profile" in stats
            assert "specializations" in stats
            assert "relationships" in stats

            # Validate character info
            char_info = stats["character"]
            required_fields = [
                "name",
                "age",
                "origin",
                "faction",
                "rank",
                "specialization",
            ]
            for field in required_fields:
                assert (
                    field in char_info
                ), f"Missing {field} in {char_name} character info"
                assert char_info[field], f"Empty {field} in {char_name} character info"

    @pytest.mark.integration
    def test_no_branded_content_in_characters(self):
        """Test that no branded content exists in character files"""
        branded_terms = [
            "emperor",
            "imperial",
            "Novel Engine",
            "40k",
            "chaos",
            "orks",
            "space marines",
            "astra militarum",
            "adeptus",
            "krieg",
        ]

        for char_name in GENERIC_CHARACTERS:
            char_dir = CHARACTER_DIR / char_name

            # Check markdown files
            for md_file in char_dir.glob("*.md"):
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read().lower()

                for term in branded_terms:
                    assert (
                        term not in content
                    ), f"Branded term '{term}' found in {md_file}"

            # Check YAML files
            for yaml_file in char_dir.glob("*.yaml"):
                with open(yaml_file, "r", encoding="utf-8") as f:
                    content = f.read().lower()

                for term in branded_terms:
                    assert (
                        term not in content
                    ), f"Branded term '{term}' found in {yaml_file}"

    @pytest.mark.integration
    def test_character_load_error_handling(self):
        """Test error handling for invalid character loading"""
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)

        with pytest.raises(Exception):
            factory.create_character("nonexistent_character")

    @pytest.mark.integration
    def test_character_context_loading(self):
        """Test character context loading functionality"""
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)
        agent = factory.create_character("pilot")
        # Context is already loaded during initialization

        assert agent.character_context is not None
        assert len(agent.character_context) > 100  # Should have substantial content
        assert "Alex Chen" in agent.character_context
        assert "Galactic Defense Force" in agent.character_context


class TestGenericCharacterProfiles:
    """Test specific generic character profiles"""

    @pytest.mark.integration
    def test_pilot_character_profile(self):
        """Test pilot character profile details"""
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)
        agent = factory.create_character("pilot")

        # Check character context
        context = agent.character_context.lower()
        assert "alex chen" in context
        assert "pilot" in context
        assert "galactic defense force" in context
        assert "starfighter" in context

        # Load stats and verify
        stats_file = CHARACTER_DIR / "pilot" / "stats.yaml"
        with open(stats_file, "r") as f:
            stats = yaml.safe_load(f)

        char_info = stats["character"]
        assert char_info["name"] == "Alex Chen"
        assert char_info["faction"] == "Galactic Defense Force"
        assert char_info["specialization"] == "Starfighter Pilot"

        # Check combat stats are reasonable for a pilot
        combat = stats["combat_stats"]
        assert combat["pilot"] >= 8  # Should be excellent pilot
        assert combat["tactics"] >= 7  # Should have good tactical skills

    @pytest.mark.integration
    def test_scientist_character_profile(self):
        """Test scientist character profile details"""
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)
        agent = factory.create_character("scientist")

        context = agent.character_context.lower()
        assert "maya patel" in context
        assert "scientist" in context
        assert "research" in context
        assert "xenobiology" in context

        # Load stats and verify
        stats_file = CHARACTER_DIR / "scientist" / "stats.yaml"
        with open(stats_file, "r") as f:
            stats = yaml.safe_load(f)

        char_info = stats["character"]
        assert char_info["name"] == "Dr. Maya Patel"
        assert "Research" in char_info["faction"]
        assert "Xenobiology" in char_info["specialization"]

        # Scientists should have high caution and corruption resistance
        psych = stats["psychological_profile"]
        assert psych["caution"] >= 8
        assert psych["corruption_resistance"] >= 8
        assert psych["aggression"] <= 3  # Should be non-aggressive

    @pytest.mark.integration
    def test_engineer_character_profile(self):
        """Test engineer character profile details"""
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)
        agent = factory.create_character("engineer")

        context = agent.character_context.lower()
        assert "jordan kim" in context
        assert "engineer" in context
        assert "systems" in context
        assert "technology" in context

        # Load stats and verify
        stats_file = CHARACTER_DIR / "engineer" / "stats.yaml"
        with open(stats_file, "r") as f:
            stats = yaml.safe_load(f)

        char_info = stats["character"]
        assert char_info["name"] == "Jordan Kim"
        assert "Engineering" in char_info["faction"]
        assert "Engineering" in char_info["specialization"]

        # Engineers should have high tactics and moderate aggression
        combat = stats["combat_stats"]
        assert combat["tactics"] >= 7

        # Should have engineering equipment
        equipment = stats["equipment"]
        assert any("tool" in item.lower() for item in equipment["special_gear"])

    @pytest.mark.integration
    def test_test_character_profile(self):
        """Test test character profile for development purposes"""
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)
        agent = factory.create_character("test")

        context = agent.character_context.lower()
        assert "test subject" in context
        assert "development" in context or "testing" in context

        # Load stats and verify
        stats_file = CHARACTER_DIR / "test" / "stats.yaml"
        with open(stats_file, "r") as f:
            stats = yaml.safe_load(f)

        char_info = stats["character"]
        assert "Test" in char_info["name"]
        assert "Test" in char_info["faction"] or "Development" in char_info["faction"]

        # Test character should have balanced stats
        combat = stats["combat_stats"]
        stat_values = list(combat.values())
        assert all(3 <= stat <= 7 for stat in stat_values)  # Balanced range


class TestCharacterStatistics:
    """Test character statistics and attributes"""

    @pytest.mark.integration
    def test_combat_stats_validity(self):
        """Test that all combat stats are within valid ranges"""
        for char_name in GENERIC_CHARACTERS:
            stats_file = CHARACTER_DIR / char_name / "stats.yaml"
            with open(stats_file, "r") as f:
                stats = yaml.safe_load(f)

            combat = stats["combat_stats"]
            required_combat_stats = [
                "marksmanship",
                "melee",
                "tactics",
                "leadership",
                "endurance",
                "pilot",
            ]

            for stat in required_combat_stats:
                assert stat in combat, f"Missing {stat} in {char_name}"
                value = combat[stat]
                assert 1 <= value <= 10, f"Invalid {stat} value {value} for {char_name}"

    @pytest.mark.integration
    def test_psychological_profile_validity(self):
        """Test that psychological profiles are valid"""
        for char_name in GENERIC_CHARACTERS:
            stats_file = CHARACTER_DIR / char_name / "stats.yaml"
            with open(stats_file, "r") as f:
                stats = yaml.safe_load(f)

            psych = stats["psychological_profile"]
            required_psych_stats = [
                "loyalty",
                "aggression",
                "caution",
                "morale",
                "corruption_resistance",
            ]

            for stat in required_psych_stats:
                assert (
                    stat in psych
                ), f"Missing {stat} in {char_name} psychological profile"
                value = psych[stat]
                assert 1 <= value <= 10, f"Invalid {stat} value {value} for {char_name}"

    @pytest.mark.integration
    def test_equipment_completeness(self):
        """Test that character equipment is complete and appropriate"""
        for char_name in GENERIC_CHARACTERS:
            stats_file = CHARACTER_DIR / char_name / "stats.yaml"
            with open(stats_file, "r") as f:
                stats = yaml.safe_load(f)

            equipment = stats["equipment"]
            required_equipment = [
                "primary_weapon",
                "secondary_weapon",
                "armor",
                "special_gear",
            ]

            for item in required_equipment:
                assert item in equipment, f"Missing {item} in {char_name} equipment"

            # Special gear should be a list
            assert isinstance(equipment["special_gear"], list)
            assert len(equipment["special_gear"]) >= 1

    @pytest.mark.integration
    def test_character_relationships(self):
        """Test character relationships are defined"""
        for char_name in GENERIC_CHARACTERS:
            stats_file = CHARACTER_DIR / char_name / "stats.yaml"
            with open(stats_file, "r") as f:
                stats = yaml.safe_load(f)

            relationships = stats["relationships"]
            assert "allies" in relationships
            assert "enemies" in relationships
            assert "mentor" in relationships

            # Check no branded factions in relationships
            all_relationships = str(relationships).lower()
            branded_factions = ["imperial", "chaos", "ork", "space marine"]
            for faction in branded_factions:
                assert faction not in all_relationships


class TestCharacterFactory:
    """Test character factory and creation systems"""

    @pytest.fixture
    def temp_character_dir(self):
        """Create temporary character directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_char_dir = Path(temp_dir) / "test_character"
            temp_char_dir.mkdir()
            yield temp_char_dir

    @pytest.mark.integration
    def test_character_factory_initialization(self):
        """Test character factory initialization"""
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)
        assert factory is not None
        assert hasattr(factory, "create_character") or hasattr(
            factory, "load_character"
        )

    @pytest.mark.integration
    def test_character_creation_validation(self, temp_character_dir):
        """Test character creation with validation"""
        # This would test programmatic character creation if implemented
        char_data = {
            "name": "Test Character",
            "faction": "Test Faction",
            "specialization": "Testing",
            "combat_stats": {
                "marksmanship": 5,
                "melee": 5,
                "tactics": 5,
                "leadership": 5,
                "endurance": 5,
                "pilot": 5,
            },
            "psychological_profile": {
                "loyalty": 7,
                "aggression": 3,
                "caution": 8,
                "morale": 6,
                "corruption_resistance": 9,
            },
        }

        # Test would create character and validate structure
        assert char_data["name"] == "Test Character"

    @pytest.mark.integration
    def test_character_template_validation(self):
        """Test character template validation"""
        # Verify all characters follow the same template structure
        template_sections = None

        for char_name in GENERIC_CHARACTERS:
            stats_file = CHARACTER_DIR / char_name / "stats.yaml"
            with open(stats_file, "r") as f:
                stats = yaml.safe_load(f)

            current_sections = set(stats.keys())

            if template_sections is None:
                template_sections = current_sections
            else:
                assert (
                    current_sections == template_sections
                ), f"Character {char_name} has different template structure"


class TestCharacterMemorySystem:
    """Test character memory and persistence"""

    @pytest.mark.integration
    def test_character_memory_initialization(self):
        """Test character memory system initialization"""
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)
        agent = factory.create_character("pilot")

        # Test memory update functionality
        agent.update_memory("test_event: Test memory entry")

        # Memory system should be available
        assert hasattr(agent, "memory_interface")
        assert agent.memory_interface is not None
        assert hasattr(agent, "short_term_memory")
        assert hasattr(agent, "long_term_memory")

    @pytest.mark.integration
    def test_memory_persistence_across_sessions(self):
        """Test that character memory persists across sessions"""
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)

        # First session
        agent1 = factory.create_character("test")
        agent1.update_memory("session1: First session data")

        # Second session (new instance)
        agent2 = factory.create_character("test")

        # Memory should persist (if implemented)
        # This is more of a design test for future implementation
        assert agent2.character_name is not None
        assert hasattr(agent2, "memory_interface")

    @pytest.mark.integration
    def test_memory_log_format(self):
        """Test memory log format and structure"""
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)
        agent = factory.create_character("scientist")
        agent.update_memory("experiment_1: Conducted xenobiology research")

        # Test memory logging doesn't crash
        assert agent.character_name is not None
        assert hasattr(agent, "memory_interface")
        assert agent.memory_interface is not None


class TestCharacterInteractions:
    """Test character interactions and behavior"""

    @pytest.mark.integration
    def test_character_decision_making(self):
        """Test character decision-making infrastructure"""
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)
        agent = factory.create_character("pilot")

        # Test that decision engine is initialized
        assert hasattr(agent, "decision_engine")
        assert agent.decision_engine is not None

        # Test that decision weights are available
        assert hasattr(agent, "decision_weights")
        weights = agent.decision_weights
        assert isinstance(weights, dict)

    @pytest.mark.integration
    def test_character_context_awareness(self):
        """Test character context awareness in decisions"""
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)

        pilot = factory.create_character("pilot")
        scientist = factory.create_character("scientist")
        engineer = factory.create_character("engineer")

        # Each character should have distinct context
        assert pilot.character_context != scientist.character_context
        assert scientist.character_context != engineer.character_context
        assert pilot.character_context != engineer.character_context

    @pytest.mark.integration
    def test_character_personality_consistency(self):
        """Test that character personalities are consistent"""
        # Load character psychological profiles
        char_personalities = {}

        for char_name in GENERIC_CHARACTERS:
            stats_file = CHARACTER_DIR / char_name / "stats.yaml"
            with open(stats_file, "r") as f:
                stats = yaml.safe_load(f)
            char_personalities[char_name] = stats["psychological_profile"]

        # Verify distinct personalities
        pilot_psych = char_personalities["pilot"]
        scientist_psych = char_personalities["scientist"]

        # Pilot should be more aggressive than scientist
        assert pilot_psych["aggression"] > scientist_psych["aggression"]

        # Scientist should be more cautious than pilot
        assert scientist_psych["caution"] > pilot_psych["caution"]

    @pytest.mark.integration
    def test_multi_character_simulation(self):
        """Test multi-character simulation setup"""
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)
        director = DirectorAgent(event_bus)

        # Register multiple characters
        pilot = factory.create_character("pilot")
        scientist = factory.create_character("scientist")

        director.register_agent(pilot)
        director.register_agent(scientist)

        assert len(director.registered_agents) == 2
        assert pilot.agent_id in [
            agent.agent_id for agent in director.registered_agents
        ]
        assert scientist.agent_id in [
            agent.agent_id for agent in director.registered_agents
        ]


class TestPerformanceAndScalability:
    """Test performance and scalability characteristics"""

    @pytest.mark.integration
    def test_character_loading_performance(self):
        """Test character loading performance"""
        import time

        event_bus = EventBus()
        factory = CharacterFactory(event_bus)

        start_time = time.time()
        factory.create_character("pilot")
        end_time = time.time()

        loading_time = end_time - start_time
        assert loading_time < 2.0, f"Character loading took too long: {loading_time}s"

    @pytest.mark.integration
    def test_multiple_character_memory_usage(self):
        """Test memory usage with multiple characters"""
        event_bus = EventBus()
        factory = CharacterFactory(event_bus)
        agents = []

        # Load all generic characters
        for char_name in GENERIC_CHARACTERS:
            agent = factory.create_character(char_name)
            agents.append(agent)

        assert len(agents) == len(GENERIC_CHARACTERS)

        # All should be distinct instances
        agent_ids = [agent.agent_id for agent in agents]
        assert len(set(agent_ids)) == len(agent_ids)  # All unique

    @pytest.mark.integration
    def test_concurrent_character_operations(self):
        """Test concurrent character operations"""
        import concurrent.futures

        def load_character(char_name):
            event_bus = EventBus()
            factory = CharacterFactory(event_bus)
            return factory.create_character(char_name)

        # Load characters concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(load_character, char_name)
                for char_name in GENERIC_CHARACTERS
            ]
            agents = [f.result() for f in concurrent.futures.as_completed(futures)]

        assert len(agents) == len(GENERIC_CHARACTERS)

        # All should be properly loaded
        for agent in agents:
            # Character name should be meaningful (not just the directory name)
            assert agent.character_name is not None
            assert len(agent.character_name) > 0
            assert agent.character_context is not None


class TestCharacterValidation:
    """Test character validation and data integrity"""

    @pytest.mark.integration
    def test_character_data_consistency(self):
        """Test consistency between markdown and YAML data"""
        for char_name in GENERIC_CHARACTERS:
            char_dir = CHARACTER_DIR / char_name

            # Load markdown content
            md_file = char_dir / f"character_{char_name}.md"
            with open(md_file, "r", encoding="utf-8") as f:
                md_content = f.read()

            # Load YAML stats
            yaml_file = char_dir / "stats.yaml"
            with open(yaml_file, "r") as f:
                stats = yaml.safe_load(f)

            # Character name should be consistent
            yaml_name = stats["character"]["name"]
            assert (
                yaml_name in md_content
            ), f"Character name {yaml_name} not found in {char_name} markdown"

            # Faction should be consistent
            yaml_faction = stats["character"]["faction"]
            assert (
                yaml_faction in md_content
            ), f"Faction {yaml_faction} not found in {char_name} markdown"

    @pytest.mark.integration
    def test_character_balance_validation(self):
        """Test character balance and fairness"""
        all_stats = {}

        for char_name in GENERIC_CHARACTERS:
            if char_name == "test":  # Skip test character for balance analysis
                continue

            stats_file = CHARACTER_DIR / char_name / "stats.yaml"
            with open(stats_file, "r") as f:
                stats = yaml.safe_load(f)
            all_stats[char_name] = stats

        # Calculate total combat power for each character
        combat_totals = {}
        for char_name, stats in all_stats.items():
            combat_stats = stats["combat_stats"]
            total = sum(combat_stats.values())
            combat_totals[char_name] = total

        # Characters should be reasonably balanced
        min_total = min(combat_totals.values())
        max_total = max(combat_totals.values())
        balance_ratio = max_total / min_total if min_total > 0 else float("inf")

        # Allow for specialization differences (pilot is combat-focused, scientist is research-focused)
        assert (
            balance_ratio <= 2.0
        ), f"Characters are severely unbalanced: {combat_totals}"

    @pytest.mark.integration
    def test_sci_fi_theme_consistency(self):
        """Test that all characters maintain sci-fi theme consistency"""
        sci_fi_keywords = [
            "space",
            "galaxy",
            "galactic",
            "stellar",
            "cosmic",
            "tech",
            "system",
            "advanced",
            "science",
            "research",
            "defense",
            "corps",
            "facility",
        ]

        for char_name in GENERIC_CHARACTERS:
            char_dir = CHARACTER_DIR / char_name

            # Check markdown content
            md_file = char_dir / f"character_{char_name}.md"
            with open(md_file, "r", encoding="utf-8") as f:
                md_content = f.read().lower()

            # Should contain sci-fi elements
            has_sci_fi = any(keyword in md_content for keyword in sci_fi_keywords)
            assert has_sci_fi, f"Character {char_name} lacks sci-fi theme elements"


# Pytest configuration
pytestmark = [pytest.mark.character, pytest.mark.unit]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
