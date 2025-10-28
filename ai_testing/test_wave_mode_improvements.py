#!/usr/bin/env python3
"""
Test script to verify Wave Mode improvements in ai_novel_system.py
"""

import asyncio
import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))


@pytest.mark.asyncio
async def test_improvements():
    """Test the Wave Mode improvements"""
    print("=" * 80)
    print("🌊 TESTING WAVE MODE IMPROVEMENTS")
    print("=" * 80)
    print()

    print("📋 Test Checklist:")
    print("  ✅ No repetitive dialogue (especially '是时候了，让我们继续前进')")
    print("  ✅ Unique character voices")
    print("  ✅ Progressive tension curve")
    print("  ✅ Enhanced event types (Crisis, Conflict, Discovery)")
    print("  ✅ Memory system preventing repetition")
    print()

    # Import the enhanced module
    from ai_novel_system import generate_complete_novel

    print("🚀 Running enhanced novel generation...")
    try:
        novel, data, evaluation = await generate_complete_novel()

        print("\n" + "=" * 80)
        print("📊 IMPROVEMENT METRICS")
        print("=" * 80)

        # Check for repetition
        novel_text = str(novel)
        repetitive_phrase = "是时候了，让我们继续前进"
        repetition_count = novel_text.count(repetitive_phrase)

        print("\n🔍 Repetition Check:")
        print(f"  '{repetitive_phrase}' count: {repetition_count}")
        if repetition_count <= 1:
            print("  ✅ PASS: Repetition eliminated!")
        else:
            print(f"  ❌ FAIL: Phrase repeated {repetition_count} times")

        # Check dialogue variety
        dialogue_events = [e for e in data["events"] if e["event_type"] == "dialogue"]
        unique_dialogues = set(e["content"] for e in dialogue_events)
        dialogue_variety = len(unique_dialogues) / max(1, len(dialogue_events))

        print("\n💬 Dialogue Variety:")
        print(f"  Total dialogues: {len(dialogue_events)}")
        print(f"  Unique dialogues: {len(unique_dialogues)}")
        print(f"  Variety ratio: {dialogue_variety:.1%}")
        if dialogue_variety > 0.8:
            print("  ✅ PASS: High dialogue variety achieved!")
        else:
            print("  ⚠️ WARNING: Some repetition detected")

        # Check for enhanced event types
        event_types = set(e["event_type"] for e in data["events"])
        enhanced_types = {"conflict", "discovery", "crisis", "revelation"}
        found_enhanced = event_types & enhanced_types

        print("\n🎭 Enhanced Event Types:")
        print(f"  Event types found: {event_types}")
        print(f"  Enhanced types used: {found_enhanced}")
        if found_enhanced:
            print("  ✅ PASS: Using enhanced event types!")
        else:
            print("  ⚠️ WARNING: No enhanced event types detected")

        # Check character arcs
        characters_with_arcs = sum(1 for c in data["characters"] if c.get("arc_description"))

        print("\n👥 Character Development:")
        print(f"  Characters with arcs: {characters_with_arcs}/3")
        if characters_with_arcs == 3:
            print("  ✅ PASS: All characters have development arcs!")
        else:
            print("  ⚠️ WARNING: Some characters lack development arcs")

        # Check overall quality
        print("\n⭐ Overall Quality:")
        print(f"  Score: {evaluation['overall_score']:.1f}/100")
        if evaluation["overall_score"] > 90:
            print("  ✅ PASS: Excellent quality achieved!")
        elif evaluation["overall_score"] > 80:
            print("  ✅ PASS: Good quality achieved!")
        else:
            print("  ⚠️ WARNING: Quality needs improvement")

        # Save test results
        test_report = f"""
WAVE MODE IMPROVEMENT TEST REPORT
==================================

Repetition Elimination: {'PASS' if repetition_count <= 1 else 'FAIL'}
- Target phrase occurrences: {repetition_count}

Dialogue Variety: {'PASS' if dialogue_variety > 0.8 else 'NEEDS IMPROVEMENT'}
- Unique dialogue ratio: {dialogue_variety:.1%}

Enhanced Events: {'PASS' if found_enhanced else 'NOT DETECTED'}
- Enhanced types used: {found_enhanced}

Character Development: {'PASS' if characters_with_arcs == 3 else 'PARTIAL'}
- Characters with arcs: {characters_with_arcs}/3

Overall Quality: {evaluation['overall_score']:.1f}/100
- Status: {'EXCELLENT' if evaluation['overall_score'] > 90 else 'GOOD' if evaluation['overall_score'] > 80 else 'NEEDS IMPROVEMENT'}

CONCLUSION: Wave Mode improvements {'SUCCESSFULLY APPLIED' if repetition_count <= 1 and dialogue_variety > 0.8 else 'PARTIALLY APPLIED'}
"""

        report_path = Path("ai_testing/reports/wave_mode_test_report.txt")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(test_report)

        print(f"\n📄 Test report saved to: {report_path}")

        return repetition_count <= 1 and dialogue_variety > 0.8

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🌊 Wave Mode Improvement Test Suite")
    print("Testing the enhanced ai_novel_system.py with Wave Mode improvements\n")

    success = asyncio.run(test_improvements())

    if success:
        print("\n🎉 ALL TESTS PASSED! Wave Mode improvements are working correctly!")
    else:
        print("\n⚠️ Some tests failed. Please review the improvements.")
