#!/usr/bin/env python3
"""
Configuration System Usage Demonstration
========================================

This demonstration shows how the centralized configuration system works
and how it can be used to customize simulation behavior without modifying code.
"""

import os

from config_loader import ConfigLoader, get_config


def demo_basic_config():
    """Demonstrate basic configuration usage."""
    print("=== Basic Configuration Usage ===")

    # Get configuration using global function
    config = get_config()

    print(f"Simulation turns: {config.simulation.turns}")
    print(f"Max agents: {config.simulation.max_agents}")
    print(f"Character sheets path: {config.paths.character_sheets_path}")
    print(f"Log file path: {config.paths.log_file_path}")
    print(f"Output directory: {config.paths.output_directory}")
    print(f"Campaign log filename: {config.director.campaign_log_filename}")
    print(f"Narrative style: {config.chronicler.narrative_style}")
    print(f"Max events per batch: {config.chronicler.max_events_per_batch}")
    print()


def demo_convenience_functions():
    """Demonstrate convenience functions for common config values."""
    print("=== Convenience Functions ===")

    from config_loader import (
        get_campaign_log_filename,
        get_character_sheets_path,
        get_default_character_sheets,
        get_log_file_path,
        get_output_directory,
        get_simulation_turns,
    )

    print(f"Simulation turns: {get_simulation_turns()}")
    print(f"Character sheets path: {get_character_sheets_path()}")
    print(f"Log file path: {get_log_file_path()}")
    print(f"Output directory: {get_output_directory()}")
    print(f"Default character sheets: {get_default_character_sheets()}")
    print(f"Campaign log filename: {get_campaign_log_filename()}")
    print()


def demo_environment_overrides():
    """Demonstrate environment variable overrides."""
    print("=== Environment Variable Overrides ===")

    # Show current configuration
    config = get_config()
    print(f"Current simulation turns: {config.simulation.turns}")

    # Set environment variable override
    os.environ["W40K_SIMULATION_TURNS"] = "7"
    os.environ["W40K_NARRATIVE_STYLE"] = "tactical"

    try:
        # Create new loader instance to pick up environment variables
        loader = ConfigLoader()
        loader.config_file_path = "config.yaml"
        loader._config = None  # Clear cache

        # Load with overrides
        override_config = loader.load_config(force_reload=True)

        print(
            f"With environment override - turns: {override_config.simulation.turns}"
        )
        print(
            f"With environment override - narrative style: {override_config.chronicler.narrative_style}"
        )

    finally:
        # Clean up environment variables
        if "W40K_SIMULATION_TURNS" in os.environ:
            del os.environ["W40K_SIMULATION_TURNS"]
        if "W40K_NARRATIVE_STYLE" in os.environ:
            del os.environ["W40K_NARRATIVE_STYLE"]

    print()


def demo_config_sections():
    """Demonstrate accessing different configuration sections."""
    print("=== Configuration Sections ===")

    config = get_config()

    print("Simulation settings:")
    print(f"  - Turns: {config.simulation.turns}")
    print(f"  - Max agents: {config.simulation.max_agents}")
    print(f"  - API timeout: {config.simulation.api_timeout}")
    print(f"  - Logging level: {config.simulation.logging_level}")

    print("\nPaths configuration:")
    print(f"  - Character sheets: {config.paths.character_sheets_path}")
    print(f"  - Log file: {config.paths.log_file_path}")
    print(f"  - Output directory: {config.paths.output_directory}")
    print(f"  - Test narratives: {config.paths.test_narratives_directory}")

    print("\nDirector settings:")
    print(
        f"  - Campaign log filename: {config.director.campaign_log_filename}"
    )
    print(f"  - Max turn history: {config.director.max_turn_history}")
    print(f"  - Error threshold: {config.director.error_threshold}")

    print("\nChronicler settings:")
    print(
        f"  - Max events per batch: {config.chronicler.max_events_per_batch}"
    )
    print(f"  - Narrative style: {config.chronicler.narrative_style}")
    print(f"  - Output directory: {config.chronicler.output_directory}")

    print("\nFeature flags:")
    print(
        f"  - AI enhanced narratives: {config.features.ai_enhanced_narratives}"
    )
    print(f"  - Advanced world state: {config.features.advanced_world_state}")
    print(f"  - Multiplayer support: {config.features.multiplayer_support}")

    print()


def demo_usage_in_components():
    """Demonstrate how components use configuration."""
    print("=== Component Configuration Usage ===")

    # Show how DirectorAgent would use configuration
    from chronicler_agent import ChroniclerAgent
    from director_agent import DirectorAgent

    print("DirectorAgent configuration integration:")
    director = DirectorAgent()
    print(f"  - Campaign log path: {director.campaign_log_path}")
    print(f"  - Max turn history: {director.max_turn_history}")
    print(f"  - Error threshold: {director.error_threshold}")

    print("\nChroniclerAgent configuration integration:")
    chronicler = ChroniclerAgent()
    print(f"  - Output directory: {chronicler.output_directory}")
    print(f"  - Max events per batch: {chronicler.max_events_per_batch}")
    print(f"  - Narrative style: {chronicler.narrative_style}")

    print()


def main():
    """Run configuration system demonstration."""
    print("Warhammer 40k Multi-Agent Simulator")
    print("Configuration System Demonstration")
    print("=" * 60)
    print()

    demo_basic_config()
    demo_convenience_functions()
    demo_environment_overrides()
    demo_config_sections()
    demo_usage_in_components()

    print("=" * 60)
    print("Configuration System Summary:")
    print("✓ Centralized YAML-based configuration")
    print("✓ Thread-safe singleton pattern")
    print("✓ Environment variable overrides")
    print("✓ Graceful fallback to defaults")
    print("✓ Comprehensive error handling")
    print("✓ Integration with all core components")
    print("✓ Type-safe configuration access")
    print("✓ Backwards compatibility maintained")
    print("=" * 60)


if __name__ == "__main__":
    main()
