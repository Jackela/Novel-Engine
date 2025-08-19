#!/usr/bin/env python3
"""
Test script to verify character name loading fixes
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from character_factory import CharacterFactory

def test_character_names():
    """Test that character names are loaded correctly after the fix."""
    
    print("Testing character name loading fixes...")
    
    factory = CharacterFactory()
    
    # Test each character
    test_characters = ['engineer', 'pilot', 'scientist']
    expected_names = ['Jordan Kim', 'Alex Chen', 'Dr. Maya Patel']
    
    for i, char_name in enumerate(test_characters):
        try:
            print(f"\n--- Testing {char_name} ---")
            agent = factory.create_character(char_name)
            
            loaded_name = agent.character_data.get('name', 'FAILED_TO_LOAD')
            expected_name = expected_names[i]
            
            print(f"Expected: {expected_name}")
            print(f"Loaded: {loaded_name}")
            
            if loaded_name == expected_name:
                print(f"✅ SUCCESS: {char_name} name loaded correctly")
            else:
                print(f"❌ FAILED: {char_name} name not loaded correctly")
                print(f"Character data keys: {list(agent.character_data.keys())}")
                
        except Exception as e:
            print(f"❌ ERROR creating {char_name}: {e}")
    
    print("\n=== Character Name Loading Test Complete ===")

if __name__ == "__main__":
    test_character_names()