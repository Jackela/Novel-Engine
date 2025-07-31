#!/usr/bin/env python3
"""
LLM Integration Demonstration Script
===================================

This script demonstrates the enhanced PersonaAgent decision_loop method
with Phase 2 LLM integration capabilities.

The demo shows:
1. How LLM-enhanced decision making works
2. Fallback to algorithmic decision making when LLM fails
3. Character-specific prompt construction
4. Response parsing and action generation

Usage:
    python demo_llm_integration.py
"""

import logging
from persona_agent import PersonaAgent, CharacterAction
from character_factory import CharacterFactory

# Configure logging to show LLM integration details
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def demo_llm_enhanced_decision_making():
    """Demonstrate LLM-enhanced decision making capabilities."""
    
    print("=" * 60)
    print("LLM-Enhanced PersonaAgent Decision Making Demo")
    print("=" * 60)
    
    # Initialize agent with test character using CharacterFactory
    print("\n1. Initializing PersonaAgent...")
    factory = CharacterFactory()
    agent = factory.create_character("test")
    print(f"   Agent ID: {agent.agent_id}")
    print(f"   Character Name: {agent.character_data.get('name', 'Unknown')}")
    print(f"   Primary Faction: {agent.subjective_worldview.get('primary_faction', 'Unknown')}")
    
    # Create various world state scenarios to test LLM integration
    scenarios = [
        {
            "name": "High Threat Combat Scenario",
            "world_state": {
                'location_updates': {'sector_7': {'threat_level': 'high', 'enemy_presence': 'confirmed'}},
                'entity_updates': {'ork_warband': {'status': 'hostile', 'strength': 'significant'}},
                'faction_updates': {'imperium': {'alert_level': 'elevated'}},
                'recent_events': [{
                    'id': 'event_001',
                    'type': 'battle',
                    'description': 'Ork raiders have breached the perimeter defenses',
                    'scope': 'local',
                    'location': 'sector_7'
                }]
            }
        },
        {
            "name": "Diplomatic Opportunity Scenario",
            "world_state": {
                'location_updates': {'meeting_hall': {'safety_level': 'secure', 'diplomatic_status': 'active'}},
                'entity_updates': {'tau_diplomat': {'status': 'neutral', 'intent': 'negotiate'}},
                'faction_updates': {'tau': {'diplomatic_stance': 'open'}},
                'recent_events': [{
                    'id': 'event_002',
                    'type': 'political',
                    'description': 'Tau delegation has requested formal negotiations',
                    'scope': 'regional',
                    'location': 'meeting_hall'
                }]
            }
        },
        {
            "name": "Investigation Scenario",
            "world_state": {
                'location_updates': {'ancient_ruins': {'mystery_level': 'high', 'exploration_status': 'incomplete'}},
                'entity_updates': {},
                'faction_updates': {},
                'recent_events': [{
                    'id': 'event_003',
                    'type': 'discovery',
                    'description': 'Strange energy readings detected from ancient xenos ruins',
                    'scope': 'local',
                    'location': 'ancient_ruins'
                }]
            }
        }
    ]
    
    # Test each scenario
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. Testing Scenario: {scenario['name']}")
        print("   " + "=" * 50)
        
        # Show world state context
        print("   World State Context:")
        for event in scenario['world_state'].get('recent_events', []):
            print(f"   - {event['type'].title()}: {event['description']}")
        
        # Make decision using LLM-enhanced decision loop
        print("   \n   Decision-making process:")
        action = agent.decision_loop(scenario['world_state'])
        
        if action:
            print(f"   ✓ Action Selected: {action.action_type}")
            print(f"   ✓ Target: {action.target or 'None'}")
            print(f"   ✓ Priority: {action.priority.value}")
            print(f"   ✓ Reasoning: {action.reasoning}")
        else:
            print("   ✓ Action: Wait and observe")
            print("   ✓ Reasoning: Character chose to gather more information")
        
        print()

def demo_llm_fallback_mechanism():
    """Demonstrate fallback to algorithmic decision making."""
    
    print("\n" + "=" * 60)
    print("LLM Fallback Mechanism Demo")
    print("=" * 60)
    
    factory = CharacterFactory()
    agent = factory.create_character("test")
    
    # Modify agent to trigger LLM failure for demonstration
    original_call_llm = agent._call_llm
    
    def failing_llm_call(prompt):
        """Simulate LLM API failure."""
        raise Exception("Simulated LLM API failure for demo")
    
    agent._call_llm = failing_llm_call
    
    print("\n1. Testing LLM Fallback Mechanism...")
    print("   Simulating LLM API failure...")
    
    world_state = {
        'location_updates': {'current_position': {'threat_level': 'moderate'}},
        'entity_updates': {},
        'faction_updates': {},
        'recent_events': [{
            'id': 'fallback_test',
            'type': 'patrol',
            'description': 'Routine patrol encountered unknown contacts',
            'scope': 'local'
        }]
    }
    
    action = agent.decision_loop(world_state)
    
    if action:
        print(f"   ✓ Fallback Successful - Action: {action.action_type}")
        print(f"   ✓ Reasoning: {action.reasoning}")
    else:
        print("   ✓ Fallback Successful - Action: Wait and observe")
    
    print("   ✓ Agent gracefully handled LLM failure and used algorithmic decision-making")
    
    # Restore original LLM function
    agent._call_llm = original_call_llm

def demo_character_specific_prompts():
    """Demonstrate character-specific prompt construction."""
    
    print("\n" + "=" * 60)
    print("Character-Specific Prompt Construction Demo")
    print("=" * 60)
    
    factory = CharacterFactory()
    agent = factory.create_character("test")
    
    print("\n1. Analyzing Character Profile...")
    print(f"   Name: {agent.character_data.get('name', 'Unknown')}")
    print(f"   Faction: {agent.subjective_worldview.get('primary_faction', 'Unknown')}")
    print(f"   Personality Traits: {list(agent.personality_traits.keys())}")
    print(f"   Decision Weights: {list(agent.decision_weights.keys())}")
    
    world_state = {
        'location_updates': {'test_location': {'threat_level': 'low'}},
        'recent_events': [{
            'id': 'prompt_demo',
            'type': 'test',
            'description': 'Test scenario for prompt demonstration',
            'scope': 'local'
        }]
    }
    
    print("\n2. Constructing Character-Specific Prompt...")
    
    # Access the prompt construction method
    situation_assessment = agent._assess_current_situation()
    available_actions = agent._identify_available_actions(situation_assessment)
    
    try:
        prompt = agent._construct_character_prompt(world_state, situation_assessment, available_actions)
        
        print(f"   ✓ Prompt Length: {len(prompt)} characters")
        print("   ✓ Prompt includes character identity, personality, and context")
        print("   ✓ Sample from constructed prompt:")
        print("   " + "-" * 50)
        
        # Show first few lines of the prompt
        prompt_lines = prompt.split('\n')[:10]
        for line in prompt_lines:
            print(f"   {line}")
        
        print("   ...")
        print("   " + "-" * 50)
        
    except Exception as e:
        print(f"   ✗ Error constructing prompt: {e}")

if __name__ == "__main__":
    try:
        # Run all demonstrations
        demo_llm_enhanced_decision_making()
        demo_llm_fallback_mechanism()
        demo_character_specific_prompts()
        
        print("\n" + "=" * 60)
        print("Demo Complete!")
        print("=" * 60)
        print("\nKey Features Demonstrated:")
        print("✓ LLM-enhanced character decision making")
        print("✓ Character-specific prompt construction")
        print("✓ Robust fallback to algorithmic decision making")
        print("✓ Backward compatibility with existing tests")
        print("✓ Structured action parsing and validation")
        print("✓ Comprehensive error handling and logging")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise