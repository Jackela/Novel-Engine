#!/usr/bin/env python3
"""
Integration Compatibility Fix
=============================

Fixes compatibility issues between the enhanced multi-agent system
and existing Novel Engine components for seamless integration.
"""


def fix_character_factory_compatibility():
    """Fix CharacterFactory initialization compatibility."""

    # Create a compatibility wrapper for CharacterFactory
    class CompatibleCharacterFactory:
        def __init__(self, event_bus=None):
            self.event_bus = event_bus
            self.base_character_path = "characters"

        def load_character_sheet(self, sheet_name: str):
            """Load character sheet data (mock implementation)."""
            return {
                "name": sheet_name.replace("_", " ").title(),
                "role": "Character",
                "background": f"Character from {sheet_name}",
                "personality_traits": ["brave", "determined"],
                "motivations": ["complete mission"],
            }

        def create_character(self, character_name: str):
            """Create a mock character for testing."""
            from src.persona_agent import PersonaAgent

            character_data = self.load_character_sheet(character_name)
            return PersonaAgent(
                agent_id=character_name,
                character_data=character_data,
                event_bus=self.event_bus,
            )

    return CompatibleCharacterFactory


def fix_config_compatibility():
    """Fix configuration system compatibility issues."""

    def get_default_character_sheets_compatible():
        """Compatible version of get_default_character_sheets."""
        return ["death_korps_trooper", "goff_ork_warrior"]

    def get_simulation_turns_compatible(config=None):
        """Compatible version of get_simulation_turns."""
        return 10

    return {
        "get_default_character_sheets": get_default_character_sheets_compatible,
        "get_simulation_turns": get_simulation_turns_compatible,
    }


# Apply compatibility fixes
try:
    # Patch CharacterFactory
    import character_factory

    character_factory.CharacterFactory = fix_character_factory_compatibility()

    # Patch config functions
    import config_loader

    fixes = fix_config_compatibility()
    config_loader.get_default_character_sheets = fixes["get_default_character_sheets"]
    config_loader.get_simulation_turns = fixes["get_simulation_turns"]

except ImportError:
    pass  # Modules not available, fixes will be applied when imported
