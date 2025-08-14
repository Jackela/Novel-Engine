#!/usr/bin/env python3
"""
Debug script to see what actions are available to characters
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from character_factory import CharacterFactory
from datetime import datetime

def debug_available_actions():
    """Debug what actions are available to each character."""
    
    print("Debugging available actions for characters...")
    
    factory = CharacterFactory()
    
    # Test each character
    characters = ['engineer', 'pilot', 'scientist']
    
    for char_name in characters:
        try:
            print(f"\n--- Debugging {char_name} Actions ---")
            agent = factory.create_character(char_name)
            
            character_name = agent.character_data.get('name', 'Unknown')
            print(f"Character: {character_name}")
            print(f"Role: {agent.character_data.get('role', 'Unknown')}")
            print(f"Specialization: {agent.character_data.get('specialization', 'Unknown')}")
            
            # Create a test world state
            world_state_update = {
                'current_time': datetime.now().isoformat(),
                'current_turn': 1,
                'simulation_time': datetime.now().isoformat(),
                'active_agents': 3,
                'location_updates': {},
                'recent_events': [],
                'global_context': {'phase': 'exploration'}
            }
            
            # Get available actions directly
            agent._process_world_state_update(world_state_update)
            situation_assessment = agent._assess_current_situation()
            available_actions = agent._identify_available_actions(situation_assessment)
            
            print(f"Available actions ({len(available_actions)}):")
            for i, action in enumerate(available_actions):
                print(f"  {i+1}. {action.get('type', 'unknown')} - {action.get('description', 'no description')}")
            
            # Test action evaluations
            print(f"\nAction evaluations:")
            action_evaluations = []
            for action in available_actions:
                evaluation = agent._evaluate_action_option(action, situation_assessment)
                action_evaluations.append((action, evaluation))
                print(f"  {action.get('type', 'unknown')}: {evaluation:.3f}")
            
            # Test profession-specific threshold
            threshold = agent._get_character_action_threshold()
            print(f"\nAction threshold: {threshold:.3f}")
            
            # Test profession default
            default_action = agent._get_profession_default_action()
            if default_action:
                print(f"Profession default: {default_action.action_type} targeting {default_action.target}")
                print(f"  Reasoning: {default_action.reasoning}")
            else:
                print("No profession default action")
                
        except Exception as e:
            print(f"❌ ERROR debugging {char_name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n=== Action Debug Complete ===")

if __name__ == "__main__":
    debug_available_actions()