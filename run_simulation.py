#!/usr/bin/env python3
"""
Warhammer 40k Multi-Agent Simulation Runner
==========================================

This script demonstrates the first complete 3-turn simulation using the newly created
character sheets for Death Korps trooper and Goff Klan Ork. It showcases the 
interaction between the DirectorAgent (Game Master AI) and PersonaAgent instances
in an authentic Warhammer 40k setting.

The simulation demonstrates:
1. DirectorAgent initialization and campaign log setup
2. PersonaAgent creation with authentic W40k character sheets
3. Agent registration and validation
4. 3-turn simulation execution with character interactions
5. Campaign log generation for narrative tracking

Characters:
- Trooper 86: Death Korps of Krieg trooper (Astra Militarum)
- Griznork: Goff Klan Ork warrior

Usage:
    python run_simulation.py

Output:
    - Console output showing simulation progress
    - campaign_log.md with detailed narrative log
"""

import logging
import sys
import os
from pathlib import Path
from datetime import datetime

import time
from src.event_bus import EventBus

# Import core agent classes
from director_agent import DirectorAgent
from src.persona_agent import PersonaAgent
from character_factory import CharacterFactory
from chronicler_agent import ChroniclerAgent

# Import configuration system
from config_loader import get_config, get_simulation_turns, get_default_character_sheets, get_log_file_path

# Configure logging for simulation tracking
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('simulation.log', mode='w')
    ]
)
logger = logging.getLogger(__name__)


def verify_character_sheets():
    """
    Verify that required character sheet files exist before starting simulation.
    
    Returns:
        bool: True if all required files exist, False otherwise
    """
    try:
        # Get character sheet files from configuration
        config = get_config()
        required_files = config.characters.default_sheets
        character_sheets_path = config.paths.character_sheets_path
    except Exception as e:
        logger.warning(f"Failed to load configuration, using defaults: {e}")
        required_files = ['character_krieg.md', 'character_ork.md']
        character_sheets_path = '.'
    
    missing_files = []
    for file_name in required_files:
        # Construct full path using character_sheets_path
        file_path = os.path.join(character_sheets_path, file_name)
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"Missing required character sheet files: {missing_files}")
        return False
    
    logger.info("All required character sheet files found")
    return True


def initialize_director_agent(event_bus: EventBus):
    """
    Initialize the DirectorAgent (Game Master AI) for simulation orchestration.
    
    Returns:
        DirectorAgent: Initialized director instance or None if initialization failed
    """
    try:
        logger.info("Initializing DirectorAgent (Game Master AI)...")
        director = DirectorAgent(event_bus)
        
        logger.info("DirectorAgent initialized successfully")
        logger.info(f"Campaign log path: {director.campaign_log_path}")
        
        return director
        
    except Exception as e:
        logger.error(f"Failed to initialize DirectorAgent: {str(e)}")
        return None


def create_persona_agents(event_bus: EventBus):
    """
    Create PersonaAgent instances for Warhammer 40k characters from configuration using CharacterFactory.
    
    Returns:
        tuple: (agents_list) or (None,) if creation failed
    """
    try:
        logger.info("Creating PersonaAgent instances using CharacterFactory...")
        
        # Initialize the character factory
        factory = CharacterFactory(event_bus)
        
        # Get character sheets from configuration
        config = get_config()
        character_sheets = config.characters.default_sheets
        
        agents = []
        
        for character_dir in character_sheets:
            # Extract character name from directory path
            # Handle paths like "characters/krieg" -> "krieg"
            if character_dir.startswith("characters/"):
                character_name = character_dir.split("characters/")[1]
            else:
                # Fallback: use the last part of the path
                character_name = os.path.basename(character_dir)
            
            logger.info(f"Creating agent for character: {character_name}")
            
            # Use CharacterFactory to create the agent
            agent = factory.create_character(character_name)
            character_display_name = agent.character_data.get('name', 'Unknown')
            logger.info(f"Agent created: {character_display_name} ({agent.agent_id})")
            agents.append(agent)
        
        return tuple(agents)
        
    except Exception as e:
        logger.error(f"Failed to create PersonaAgent instances: {str(e)}")
        return None, None


def register_agents_with_director(director, *agents):
    """
    Register PersonaAgent instances with the DirectorAgent.
    
    Args:
        director: DirectorAgent instance
        *agents: Variable number of PersonaAgent instances
        
    Returns:
        bool: True if all agents registered successfully, False otherwise
    """
    try:
        logger.info("Registering agents with DirectorAgent...")
        
        # Register each agent
        for i, agent in enumerate(agents):
            character_name = agent.character_data.get('name', 'Unknown')
            success = director.register_agent(agent)
            if success:
                logger.info(f"Agent {i+1} registered successfully: {character_name}")
            else:
                logger.error(f"Failed to register agent {i+1}: {character_name}")
                return False
        
        # Verify both agents are registered
        registered_count = len(director.registered_agents)
        logger.info(f"Agent registration complete: {registered_count} agents registered")
        
        # Log agent details
        for agent in director.registered_agents:
            char_name = agent.character_data.get('name', 'Unknown')
            faction = agent.subjective_worldview.get('primary_faction', 'Unknown')
            logger.info(f"  - {char_name} ({agent.agent_id}) - {faction}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to register agents: {str(e)}")
        return False


def run_3_turn_simulation(director):
    """
    Execute the multi-agent simulation for the configured number of turns.
    
    Args:
        director: DirectorAgent instance with registered agents
        
    Returns:
        bool: True if simulation completed successfully, False otherwise
    """
    try:
        num_turns = get_simulation_turns()
        logger.info("=" * 60)
        logger.info(f"STARTING {num_turns}-TURN SIMULATION")
        logger.info("=" * 60)
        
        simulation_start = datetime.now()
        
        for turn_number in range(1, num_turns + 1):
            logger.info(f"\n{'='*20} TURN {turn_number}/{num_turns} {'='*20}")
            director.run_turn()
            # Wait for events to be processed. This is a temporary solution.
            time.sleep(1)
        
        simulation_end = datetime.now()
        total_duration = (simulation_end - simulation_start).total_seconds()
        
        logger.info("=" * 60)
        logger.info(f"{num_turns}-TURN SIMULATION COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Total simulation time: {total_duration:.2f} seconds")
        
        return True
        
    except Exception as e:
        logger.error(f"Critical error during simulation: {str(e)}")
        return False


def initialize_chronicler_agent(event_bus: EventBus):
    """Initializes the ChroniclerAgent."""
    try:
        logger.info("Initializing ChroniclerAgent...")
        chronicler = ChroniclerAgent(event_bus)
        logger.info("ChroniclerAgent initialized successfully.")
        return chronicler
    except Exception as e:
        logger.error(f"Failed to initialize ChroniclerAgent: {e}")
        return None

def main():
    """
    Main simulation entry point - orchestrates the complete 3-turn demonstration.
    """
    try:
        config = get_config()
        num_turns = config.simulation.turns
        character_sheets = config.characters.default_sheets
        
        print("=" * 70)
        print("STORYFORGE AI - INTERACTIVE STORY ENGINE")
        print(f"{num_turns}-Turn Simulation with {len(character_sheets)} Characters")
        print("=" * 70)
        
    except Exception as e:
        logger.warning(f"Failed to load configuration display info: {e}")
        print("=" * 70)
        print("STORYFORGE AI - INTERACTIVE STORY ENGINE")
        print("Multi-Turn Character Demonstration")
        print("=" * 70)
    
    try:
        # Step 0: Initialize Event Bus
        print("\n0. Initializing Event Bus...")
        event_bus = EventBus()
        print("✓ Event Bus initialized")

        # Step 1: Verify required files exist
        print("\n1. Verifying character sheet files...")
        if not verify_character_sheets():
            print("✗ Character sheet verification failed")
            sys.exit(1)
        print("✓ Character sheet files verified")
        
        # Step 2: Initialize DirectorAgent
        print("\n2. Initializing DirectorAgent...")
        director = initialize_director_agent(event_bus)
        if director is None:
            print("✗ DirectorAgent initialization failed")
            sys.exit(1)
        print("✓ DirectorAgent initialized successfully")

        # Step 3: Initialize ChroniclerAgent
        print("\n3. Initializing ChroniclerAgent...")
        chronicler = initialize_chronicler_agent(event_bus)
        if chronicler is None:
            print("✗ ChroniclerAgent initialization failed")
            sys.exit(1)
        print("✓ ChroniclerAgent initialized successfully")
        
        # Step 4: Create PersonaAgent instances
        print("\n4. Creating PersonaAgent instances...")
        agents = create_persona_agents(event_bus)
        if not agents or any(agent is None for agent in agents):
            print("✗ PersonaAgent creation failed")
            sys.exit(1)
        print(f"✓ {len(agents)} PersonaAgent instances created successfully")
        
        # Step 5: Register agents with director
        print("\n5. Registering agents with DirectorAgent...")
        if not register_agents_with_director(director, *agents):
            print("✗ Agent registration failed")
            sys.exit(1)
        print("✓ All agents registered successfully")
        
        # Step 6: Run simulation
        num_turns = get_simulation_turns()
        print(f"\n6. Executing {num_turns}-turn simulation...")
        if not run_3_turn_simulation(director):
            print("✗ Simulation execution failed")
            sys.exit(1)
        print(f"✓ {num_turns}-turn simulation completed successfully")
        
        # Step 7: Finalize narrative
        print("\n7. Finalizing narrative...")
        event_bus.emit("SIMULATION_END")
        time.sleep(1) # Give chronicler time to process
        print("✓ Narrative finalized")

        # Final success message
        config = get_config()
        log_file = config.paths.log_file_path
        print("\n" + "=" * 70)
        print("🎯 SIMULATION COMPLETE!")
        print(f"Campaign log generated: {log_file}")
        print("Simulation log available: simulation.log")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Simulation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error in main simulation: {str(e)}")
        print(f"\n✗ Simulation failed with unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()