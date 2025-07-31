#!/usr/bin/env python3
"""
Test script to validate memory logging functionality
"""

from persona_agent import PersonaAgent
from character_factory import CharacterFactory
import os

def test_memory_logging():
    """Test the update_memory functionality with real character directories"""
    print("Testing memory logging functionality...")
    
    # Test with Krieg character using CharacterFactory
    factory = CharacterFactory()
    krieg_agent = factory.create_character("krieg")
    
    # Test memory logging
    krieg_agent.update_memory("Test event: Agent initialized successfully")
    krieg_agent.update_memory("Test event: Combat training completed")
    krieg_agent.update_memory("Test event: Mission briefing received")
    
    # Check if memory.log was created and contains our entries
    memory_log_path = os.path.join("characters/krieg", "memory.log")
    
    if os.path.exists(memory_log_path):
        print(f"✓ Memory log file created: {memory_log_path}")
        
        with open(memory_log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("\nMemory log contents:")
        print("=" * 50)
        print(content)
        print("=" * 50)
        
        # Verify our test entries are present
        test_events = [
            "Agent initialized successfully",
            "Combat training completed", 
            "Mission briefing received"
        ]
        
        for event in test_events:
            if event in content:
                print(f"✓ Found test event: {event}")
            else:
                print(f"✗ Missing test event: {event}")
    else:
        print(f"✗ Memory log file not found: {memory_log_path}")
    
    print("\nTesting with Ork character...")
    
    # Test with Ork character using CharacterFactory
    ork_agent = factory.create_character("ork")
    ork_agent.update_memory("WAAAGH! Started new mission")
    ork_agent.update_memory("Found some good enemies to fight")
    
    ork_memory_path = os.path.join("characters/ork", "memory.log")
    if os.path.exists(ork_memory_path):
        print(f"✓ Ork memory log created: {ork_memory_path}")
        
        with open(ork_memory_path, 'r', encoding='utf-8') as f:
            ork_content = f.read()
        
        print("Ork memory log contents:")
        print("-" * 30)
        print(ork_content)
        print("-" * 30)
    
    print("\nMemory logging test completed!")

if __name__ == "__main__":
    test_memory_logging()