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

# Import core agent classes
from director_agent import DirectorAgent
from persona_agent import PersonaAgent
from character_factory import CharacterFactory

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


def initialize_director_agent():
    """
    Initialize the DirectorAgent (Game Master AI) for simulation orchestration.
    
    Returns:
        DirectorAgent: Initialized director instance or None if initialization failed
    """
    try:
        logger.info("Initializing DirectorAgent (Game Master AI)...")
        director = DirectorAgent()
        
        logger.info("DirectorAgent initialized successfully")
        logger.info(f"Campaign log path: {director.campaign_log_path}")
        
        return director
        
    except Exception as e:
        logger.error(f"Failed to initialize DirectorAgent: {str(e)}")
        return None


def create_persona_agents():
    """
    Create PersonaAgent instances for Warhammer 40k characters from configuration using CharacterFactory.
    
    Returns:
        tuple: (agents_list) or (None,) if creation failed
    """
    try:
        logger.info("Creating PersonaAgent instances using CharacterFactory...")
        
        # Initialize the character factory
        factory = CharacterFactory()
        
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
        logger.info(f"STARTING {num_turns}-TURN WARHAMMER 40K SIMULATION")
        logger.info("=" * 60)
        
        simulation_start = datetime.now()
        turn_results = []
        
        # Execute turns based on configuration
        num_turns = get_simulation_turns()
        for turn_number in range(1, num_turns + 1):
            logger.info(f"\n{'='*20} TURN {turn_number}/3 {'='*20}")
            
            try:
                # Execute turn
                turn_result = director.run_turn()
                turn_results.append(turn_result)
                
                # Log turn summary
                actions_count = turn_result.get('total_actions', 0)
                errors_count = len(turn_result.get('errors', []))
                duration = turn_result.get('turn_duration', 0)
                
                logger.info(f"Turn {turn_number}/{num_turns} completed successfully:")
                logger.info(f"  - Actions generated: {actions_count}")
                logger.info(f"  - Errors encountered: {errors_count}")
                logger.info(f"  - Turn duration: {duration:.2f} seconds")
                
                # Log participating agents
                participants = turn_result.get('participating_agents', [])
                logger.info(f"  - Participating agents: {len(participants)}")
                for agent_id in participants:
                    logger.info(f"    * {agent_id}")
                
                # Brief pause between turns for readability
                import time
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error during turn {turn_number}: {str(e)}")
                # Continue with next turn despite error
                continue
        
        # Calculate simulation statistics
        simulation_end = datetime.now()
        total_duration = (simulation_end - simulation_start).total_seconds()
        total_actions = sum(result.get('total_actions', 0) for result in turn_results)
        total_errors = sum(len(result.get('errors', [])) for result in turn_results)
        
        logger.info("=" * 60)
        logger.info(f"{num_turns}-TURN SIMULATION COMPLETED")
        logger.info("=" * 60)
        logger.info(f"Total simulation time: {total_duration:.2f} seconds")
        logger.info(f"Total turns executed: {len(turn_results)}")
        logger.info(f"Total actions generated: {total_actions}")
        logger.info(f"Total errors encountered: {total_errors}")
        
        return True
        
    except Exception as e:
        logger.error(f"Critical error during simulation: {str(e)}")
        return False


def main():
    """
    Main simulation entry point - orchestrates the complete 3-turn demonstration.
    """
    try:
        config = get_config()
        num_turns = config.simulation.turns
        character_sheets = config.characters.default_sheets
        
        print("=" * 70)
        print("WARHAMMER 40K MULTI-AGENT SIMULATOR")
        print(f"{num_turns}-Turn Demonstration with {len(character_sheets)} Characters")
        print("=" * 70)
        
    except Exception as e:
        logger.warning(f"Failed to load configuration display info: {e}")
        print("=" * 70)
        print("WARHAMMER 40K MULTI-AGENT SIMULATOR")
        print("Multi-Turn Character Demonstration")
        print("=" * 70)
    
    try:
        # Step 1: Verify required files exist
        print("\n1. Verifying character sheet files...")
        if not verify_character_sheets():
            print("✗ Character sheet verification failed")
            sys.exit(1)
        print("✓ Character sheet files verified")
        
        # Step 2: Initialize DirectorAgent
        print("\n2. Initializing DirectorAgent...")
        director = initialize_director_agent()
        if director is None:
            print("✗ DirectorAgent initialization failed")
            sys.exit(1)
        print("✓ DirectorAgent initialized successfully")
        
        # Step 3: Create PersonaAgent instances
        print("\n3. Creating PersonaAgent instances...")
        agents = create_persona_agents()
        if not agents or any(agent is None for agent in agents):
            print("✗ PersonaAgent creation failed")
            sys.exit(1)
        print(f"✓ {len(agents)} PersonaAgent instances created successfully")
        
        # Step 4: Register agents with director
        print("\n4. Registering agents with DirectorAgent...")
        if not register_agents_with_director(director, *agents):
            print("✗ Agent registration failed")
            sys.exit(1)
        print("✓ All agents registered successfully")
        
        # Step 5: Run simulation
        num_turns = get_simulation_turns()
        print(f"\n5. Executing {num_turns}-turn simulation...")
        if not run_3_turn_simulation(director):
            print("✗ Simulation execution failed")
            sys.exit(1)
        print(f"✓ {num_turns}-turn simulation completed successfully")
        
        # Step 6: Finalize campaign log
        print("\n6. Finalizing campaign log...")
        try:
            director.close_campaign_log()
            print("✓ Campaign log finalized")
        except Exception as e:
            logger.warning(f"Could not properly close campaign log: {e}")
            print("⚠ Campaign log may not be properly closed")
        
        # Final success message
        config = get_config()
        log_file = config.paths.log_file_path
        print("\n" + "=" * 70)
        print("🎯 SIMULATION COMPLETE!")
        print(f"Campaign log generated: {log_file}")
        print("Simulation log available: simulation.log")
        print("=" * 70)
        print("\nFor the Emperor! In the grim darkness of the far future, there is only war...")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Simulation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error in main simulation: {str(e)}")
        print(f"\n✗ Simulation failed with unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()