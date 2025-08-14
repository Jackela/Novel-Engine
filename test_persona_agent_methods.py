#!/usr/bin/env python3
"""
Test script to verify PersonaAgent method availability
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from character_factory import CharacterFactory

def test_persona_agent_methods():
    """Test that PersonaAgent methods are accessible."""
    
    print("Testing PersonaAgent method availability...")
    
    factory = CharacterFactory()
    agent = factory.create_character('engineer')
    
    print(f"Agent created: {agent.character_data.get('name', 'Unknown')}")
    print(f"Agent ID: {agent.agent_id}")
    
    # Check if the method exists
    if hasattr(agent, '_identify_narrative_actions'):
        print("✅ _identify_narrative_actions method exists")
        
        # Try to call it with a test situation
        test_situation = {
            'threat_level': 'low',
            'current_environment': 'safe',
            'active_objectives': []
        }
        
        try:
            narrative_actions = agent._identify_narrative_actions(test_situation)
            print(f"✅ _identify_narrative_actions executed successfully")
            print(f"   Returned {len(narrative_actions)} actions: {[action.get('type', 'unknown') for action in narrative_actions]}")
        except Exception as e:
            print(f"❌ _identify_narrative_actions failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ _identify_narrative_actions method does not exist")
        print(f"Available methods: {[m for m in dir(agent) if m.startswith('_identify')]}")

if __name__ == "__main__":
    test_persona_agent_methods()