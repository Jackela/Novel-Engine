#!/usr/bin/env python3
"""
Test script to verify character decision-making behavior
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from character_factory import CharacterFactory
from datetime import datetime

def test_character_decisions():
    """Test that characters make varied decisions rather than all waiting."""
    
    print("Testing character decision-making behavior...")
    
    factory = CharacterFactory()
    
    # Test each character
    characters = ['engineer', 'pilot', 'scientist']
    
    for char_name in characters:
        try:
            print(f"\n--- Testing {char_name} Decision Making ---")
            agent = factory.create_character(char_name)
            
            character_name = agent.character_data.get('name', 'Unknown')
            print(f"Character: {character_name}")
            
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
            
            # Test decision making
            print("Calling decision_loop...")
            decision = agent.decision_loop(world_state_update)
            
            if decision:
                print(f"✅ {character_name} made a decision:")
                print(f"   Action: {decision.action_type}")
                print(f"   Target: {decision.target}")
                print(f"   Reasoning: {decision.reasoning}")
                print(f"   Priority: {decision.priority}")
            else:
                print(f"⚠️ {character_name} chose to wait/observe (None returned)")
                
        except Exception as e:
            print(f"❌ ERROR testing {char_name}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n=== Character Decision Test Complete ===")

if __name__ == "__main__":
    test_character_decisions()