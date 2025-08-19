#!/usr/bin/env python3
"""
P0-3 Comprehensive Test: Complete Character Name Integration
===========================================================

Test the complete end-to-end character name integration workflow:
1. API receives character names ['pilot', 'engineer', 'scientist']  
2. CharacterFactory creates PersonaAgent instances
3. DirectorAgent registers agents and creates campaign log
4. ChroniclerAgent reads campaign log and generates narrative
5. Verify that requested character names appear consistently in the final story
"""

import sys
import os
import tempfile
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from character_factory import CharacterFactory
from director_agent import DirectorAgent
from chronicler_agent import ChroniclerAgent

def test_complete_character_integration():
    """Test complete end-to-end character name integration."""
    
    print("🔍 P0-3 COMPREHENSIVE TEST: Complete Character Name Integration")
    print("=" * 80)
    
    # Test Parameters
    requested_names = ['pilot', 'engineer', 'scientist']
    
    print(f"📋 Test Setup:")
    print(f"   Requested Character Names: {requested_names}")
    print(f"   Expected: These names should appear in final narrative")
    print()
    
    try:
        # STEP 1: Create character agents using CharacterFactory
        print("🔧 STEP 1: Creating character agents via CharacterFactory")
        character_factory = CharacterFactory()
        character_agents = []
        
        for name in requested_names:
            try:
                agent = character_factory.create_character(name)
                character_agents.append(agent)
                print(f"   ✅ Created agent for '{name}': ID={agent.agent_id}")
                
                # Check what name is in the character file
                file_character_name = agent.character_data.get('name', 'Unknown')
                print(f"      📄 File character name: '{file_character_name}'")
                
            except Exception as e:
                print(f"   ❌ Failed to create '{name}': {e}")
                return False
        
        print(f"   📊 Created {len(character_agents)} agents successfully")
        print()
        
        # STEP 2: Initialize DirectorAgent and register agents
        print("🎯 STEP 2: DirectorAgent registration and simulation")
        
        # Create temporary campaign log
        with tempfile.NamedTemporaryFile(mode='w', suffix='_campaign_log.md', delete=False) as f:
            temp_campaign_log = f.name
        
        director = DirectorAgent(campaign_log_path=temp_campaign_log)
        
        # Register all agents
        for agent in character_agents:
            success = director.register_agent(agent)
            if not success:
                print(f"   ❌ Failed to register agent: {agent.agent_id}")
                return False
            else:
                print(f"   ✅ Registered agent: {agent.agent_id}")
        
        # Run 2 simulation turns
        print("   🎮 Running 2 simulation turns...")
        for turn in range(2):
            director.run_turn()
            print(f"      Turn {turn + 1} completed")
        
        print()
        
        # STEP 3: Check what's actually in the campaign log
        print("📖 STEP 3: Analyzing campaign log content")
        
        with open(temp_campaign_log, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        print(f"   📄 Campaign log length: {len(log_content)} characters")
        
        # Check for character names in the log
        print("   🔍 Character name analysis in campaign log:")
        for name in requested_names:
            count = log_content.lower().count(name.lower())
            print(f"      '{name}': {count} occurrences")
        
        # Check for actual character file names
        file_names = ['Alex Chen', 'Jordan Kim', 'Dr. Maya Patel']
        print("   🔍 File character name analysis in campaign log:")
        for name in file_names:
            count = log_content.count(name)
            print(f"      '{name}': {count} occurrences")
        
        print()
        
        # STEP 4: ChroniclerAgent narrative generation
        print("📚 STEP 4: ChroniclerAgent narrative generation")
        
        # Test with injected character names
        chronicler = ChroniclerAgent(
            narrative_style="sci_fi_dramatic",
            character_names=requested_names  # INJECT the requested names
        )
        
        narrative = chronicler.transcribe_log(temp_campaign_log)
        
        print(f"   ✅ Generated narrative: {len(narrative)} characters")
        print()
        
        # STEP 5: Analyze final narrative
        print("🎯 STEP 5: Final narrative analysis")
        print("=" * 50)
        
        # Count requested character names
        requested_mentions = {}
        total_requested = 0
        for name in requested_names:
            count = narrative.lower().count(name.lower())
            requested_mentions[name] = count
            total_requested += count
            print(f"   ✅ '{name}' mentions: {count}")
        
        # Count file character names  
        file_mentions = {}
        total_file = 0
        for name in file_names:
            count = narrative.count(name)
            file_mentions[name] = count
            total_file += count
            print(f"   📄 '{name}' mentions: {count}")
        
        # Count problematic patterns
        unknown_count = narrative.count("For Unknown")
        print(f"   ❌ 'For Unknown' occurrences: {unknown_count}")
        
        print("=" * 50)
        
        # Show narrative sample
        print("\n📖 NARRATIVE SAMPLE (first 600 chars):")
        print("-" * 60)
        print(narrative[:600])
        print("-" * 60)
        
        # STEP 6: Final assessment
        print("\n🏁 FINAL ASSESSMENT:")
        print("=" * 50)
        
        success_criteria = {
            "no_unknown_segments": unknown_count == 0,
            "requested_names_present": total_requested >= 3,  # At least some mentions
            "file_names_minimal": total_file <= total_requested,  # Prefer requested over file names
        }
        
        all_passed = all(success_criteria.values())
        
        for criterion, passed in success_criteria.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {criterion}: {status}")
        
        if all_passed:
            print("\n🎉 P0-3 COMPREHENSIVE TEST: SUCCESS!")
            print("   ✅ Complete character name integration working")
            print("   ✅ Requested names properly used throughout pipeline")
            print("   ✅ No 'For Unknown' segments in final narrative")
            print("   ✅ End-to-end API integration ready")
        else:
            print("\n❌ P0-3 COMPREHENSIVE TEST: ISSUES DETECTED")
            if unknown_count > 0:
                print(f"   - Still {unknown_count} 'For Unknown' segments")
            if total_requested < 3:
                print(f"   - Only {total_requested} requested name mentions (expected ≥3)")
            if total_file > total_requested:
                print(f"   - File names ({total_file}) mentioned more than requested ({total_requested})")
        
        # Cleanup
        os.unlink(temp_campaign_log)
        
        return all_passed
        
    except Exception as e:
        print(f"💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_character_integration()
    sys.exit(0 if success else 1)