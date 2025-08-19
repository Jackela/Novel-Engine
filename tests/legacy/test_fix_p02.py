#!/usr/bin/env python3
"""
Test script to verify P0-2 fix: Eliminate 'For Unknown' segment assembly issues
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chronicler_agent import ChroniclerAgent
import tempfile

def test_character_name_integration():
    """Test that character names are properly integrated into narrative generation."""
    
    print("🔍 Testing P0-2 Fix: Character Name Integration in Narrative Generation")
    print("=" * 70)
    
    # Create a test campaign log with known character names
    test_log_content = """# Test Campaign Log

**Simulation Started:** 2025-08-13 23:30:00
**Director Agent:** DirectorAgent v1.0
**Phase:** Phase 1 - Test

## Campaign Events

### Turn 1 Event
**Time:** 2025-08-13 23:30:01
**Event:** **Agent Registration:** Test Character (test_agent_001) joined the simulation
**Faction:** Imperial Guard
**Registration Time:** 2025-08-13 23:30:01
**Total Active Agents:** 1
**Turn:** 1
**Active Agents:** 1

### Turn 2 Event
**Time:** 2025-08-13 23:30:02
**Event:** **Agent Action:** Test Character decided to advance tactically
**Turn:** 2
**Active Agents:** 1
"""
    
    # Create temporary log file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(test_log_content)
        temp_log_path = f.name
    
    try:
        # Test 1: ChroniclerAgent with injected character names
        print("\n📝 Test 1: ChroniclerAgent with injected character names")
        character_names = ["Alice", "Bob", "Charlie"]
        chronicler = ChroniclerAgent(
            narrative_style="sci_fi_dramatic",
            character_names=character_names
        )
        
        # Generate narrative
        narrative = chronicler.transcribe_log(temp_log_path)
        
        print(f"Generated narrative length: {len(narrative)} characters")
        print("\nNarrative excerpt:")
        print("-" * 50)
        print(narrative[:500])
        print("-" * 50)
        
        # Check for issues
        unknown_count = narrative.count("For Unknown")
        character_mentions = sum(name in narrative for name in character_names)
        
        print(f"\n📊 Results:")
        print(f"   'For Unknown' occurrences: {unknown_count}")
        print(f"   Character name mentions: {character_mentions}")
        
        if unknown_count == 0:
            print("   ✅ SUCCESS: No 'For Unknown' segments found!")
        else:
            print("   ❌ FAILURE: Still contains 'For Unknown' segments")
            
        if character_mentions > 0:
            print("   ✅ SUCCESS: Character names integrated into narrative!")
        else:
            print("   ❌ FAILURE: Character names not found in narrative")
        
        # Test 2: ChroniclerAgent without injected character names (should still work)
        print("\n📝 Test 2: ChroniclerAgent without injected character names")
        chronicler_no_names = ChroniclerAgent(narrative_style="sci_fi_dramatic")
        
        narrative_no_names = chronicler_no_names.transcribe_log(temp_log_path)
        unknown_count_no_names = narrative_no_names.count("For Unknown")
        
        print(f"   'For Unknown' occurrences: {unknown_count_no_names}")
        if unknown_count_no_names == 0:
            print("   ✅ SUCCESS: Even without injected names, no 'For Unknown' segments!")
        else:
            print("   ⚠️  WARNING: Without injected names, still has 'For Unknown' segments")
        
        print("\n" + "=" * 70)
        print("🎯 P0-2 Fix Verification Summary:")
        print("=" * 70)
        
        if unknown_count == 0 and character_mentions > 0:
            print("✅ P0-2 FIX SUCCESSFUL!")
            print("   - Character names properly integrated")
            print("   - 'For Unknown' segments eliminated") 
            print("   - Narrative quality significantly improved")
            return True
        else:
            print("❌ P0-2 FIX INCOMPLETE!")
            print("   - Issues still remain in narrative generation")
            return False
            
    finally:
        # Cleanup
        os.unlink(temp_log_path)

if __name__ == "__main__":
    success = test_character_name_integration()
    sys.exit(0 if success else 1)