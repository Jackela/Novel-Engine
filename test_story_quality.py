#!/usr/bin/env python3
"""
Test script to verify story generation quality after character behavior fixes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from character_factory import CharacterFactory
from director_agent import DirectorAgent
from chronicler_agent import ChroniclerAgent
from datetime import datetime

def test_story_quality():
    """Test story generation with the improved character behavior system."""
    
    print("Testing story generation quality...")
    
    # Initialize components
    factory = CharacterFactory()
    director = DirectorAgent()
    chronicler = ChroniclerAgent()
    
    # Create characters
    print("\n=== Creating Characters ===")
    engineer = factory.create_character('engineer')
    pilot = factory.create_character('pilot') 
    scientist = factory.create_character('scientist')
    
    print(f"✅ Engineer: {engineer.character_data.get('name')}")
    print(f"✅ Pilot: {pilot.character_data.get('name')}")
    print(f"✅ Scientist: {scientist.character_data.get('name')}")
    
    # Register characters with director
    print("\n=== Registering Characters ===")
    director.register_agent(engineer)
    director.register_agent(pilot)
    director.register_agent(scientist)
    
    print(f"Active agents: {len(director.registered_agents)}")
    
    # Run a few story turns
    print("\n=== Running Story Generation ===")
    for turn in range(1, 4):  # Run 3 turns
        print(f"\n--- Turn {turn} ---")
        
        # Execute turn
        turn_result = director.run_turn()
        turn_events = turn_result.get('events', [])
        
        print(f"Turn {turn} events: {len(turn_events)}")
        for event in turn_events:
            action_type = event.get('action_type', 'unknown')
            agent_name = event.get('agent_id', 'unknown')
            target = event.get('target', 'none')
            reasoning = event.get('reasoning', 'no reasoning')
            
            print(f"  • {agent_name}: {action_type} → {target}")
            print(f"    Reasoning: {reasoning[:100]}...")
    
    # Test narrative generation
    print("\n=== Testing Narrative Generation ===")
    try:
        print("Generating narrative from campaign log...")
        
        narrative_result = chronicler.transcribe_log('campaign_log.md')
        
        if narrative_result:
            print("✅ Narrative generated successfully")
            
            # Analyze the generated narrative content
            narrative_content = narrative_result
            
            # Basic quality checks
            lines = narrative_content.split('\n')
            
            print(f"📊 Narrative analysis:")
            print(f"   Lines: {len(lines)}")
            print(f"   Characters: {len(narrative_content)}")
            
            # Check for repetitive content
            unique_sentences = set()
            repetitive_sentences = []
            
            for line in lines:
                line = line.strip()
                if len(line) > 20:  # Only check substantial lines
                    if line in unique_sentences:
                        repetitive_sentences.append(line)
                    else:
                        unique_sentences.add(line)
            
            if repetitive_sentences:
                print(f"⚠️ Found {len(repetitive_sentences)} repetitive sentences:")
                for sentence in repetitive_sentences[:3]:  # Show first 3
                    print(f"   '{sentence[:80]}...'")
            else:
                print("✅ No obvious repetitive content detected")
            
            # Check for character names
            engineer_name = engineer.character_data.get('name', '')
            pilot_name = pilot.character_data.get('name', '')
            scientist_name = scientist.character_data.get('name', '')
            
            names_found = {
                engineer_name: narrative_content.count(engineer_name),
                pilot_name: narrative_content.count(pilot_name),
                scientist_name: narrative_content.count(scientist_name),
                'Unknown': narrative_content.count('Unknown'),
                'operative': narrative_content.count('operative')
            }
            
            print(f"📝 Character name usage:")
            for name, count in names_found.items():
                print(f"   {name}: {count} times")
                
        else:
            print("❌ Narrative generation failed")
            
    except Exception as e:
        print(f"❌ Narrative generation error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Story Quality Test Complete ===")

if __name__ == "__main__":
    test_story_quality()