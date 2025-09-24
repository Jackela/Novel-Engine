#!/usr/bin/env python3
"""
Test Wave 3 Improvements - Content Generation Variety
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from complete_workflow_test import CompleteNovelWorkflow


def test_content_variety():
    """Test the improved content generation variety"""
    print("=" * 80)
    print("TESTING WAVE 3 IMPROVEMENTS - CONTENT VARIETY")
    print("=" * 80)

    workflow = CompleteNovelWorkflow()

    # Step 1: Create characters
    workflow.create_custom_characters()

    # Step 2: Generate events with improved variety
    events = workflow.advance_story_rounds(rounds=60)

    # Analyze content variety
    print("\n📊 CONTENT VARIETY ANALYSIS:")
    print("-" * 40)

    # 1. Check dialogue extraction
    dialogues = []
    actions = []
    discoveries = []
    conflicts = []
    crises = []
    environments = []

    for event in events:
        content = event.content
        event_type = event.event_type.value

        if event_type == "dialogue":
            dialogues.append(content)
        elif event_type == "action":
            actions.append(content)
        elif event_type == "discovery":
            discoveries.append(content)
        elif event_type == "conflict":
            conflicts.append(content)
        elif event_type == "crisis":
            crises.append(content)
        elif event_type == "environment":
            environments.append(content)

    # Check for "Unknown" dialogues
    unknown_count = sum(1 for d in dialogues if "Unknown" in d)
    print(f"✅ Dialogues with 'Unknown': {unknown_count}/{len(dialogues)}")
    if unknown_count > 0:
        print("  ❌ FAILED: Still has Unknown dialogues!")
    else:
        print("  ✅ PASSED: No Unknown dialogues!")

    # Check dialogue variety
    unique_dialogues = len(set(dialogues))
    dialogue_variety = unique_dialogues / max(1, len(dialogues))
    print(
        f"✅ Dialogue variety: {dialogue_variety:.1%} ({unique_dialogues}/{len(dialogues)} unique)"
    )
    if dialogue_variety < 0.8:
        print("  ⚠️ WARNING: Low dialogue variety")

    # Check action variety
    unique_actions = len(set(actions))
    action_variety = unique_actions / max(1, len(actions))
    print(
        f"✅ Action variety: {action_variety:.1%} ({unique_actions}/{len(actions)} unique)"
    )

    # Check discovery variety
    unique_discoveries = len(set(discoveries))
    discovery_variety = unique_discoveries / max(1, len(discoveries))
    print(
        f"✅ Discovery variety: {discovery_variety:.1%} ({unique_discoveries}/{len(discoveries)} unique)"
    )

    # Check conflict variety
    unique_conflicts = len(set(conflicts))
    conflict_variety = unique_conflicts / max(1, len(conflicts))
    print(
        f"✅ Conflict variety: {conflict_variety:.1%} ({unique_conflicts}/{len(conflicts)} unique)"
    )

    # Check crisis variety
    unique_crises = len(set(crises))
    crisis_variety = unique_crises / max(1, len(crises))
    print(
        f"✅ Crisis variety: {crisis_variety:.1%} ({unique_crises}/{len(crises)} unique)"
    )

    # 2. Check character balance
    print("\n👥 CHARACTER BALANCE:")
    print("-" * 40)

    character_counter = Counter()
    for event in events:
        if hasattr(event, "character") and event.character != "Narrator":
            character_counter[event.character] += 1

    total_char_events = sum(character_counter.values())
    for char_name, count in character_counter.most_common():
        percentage = (
            (count / total_char_events) * 100 if total_char_events > 0 else 0
        )
        print(f"  {char_name}: {count} events ({percentage:.1f}%)")

    # Check balance
    if character_counter:
        max_count = max(character_counter.values())
        min_count = min(character_counter.values())
        imbalance_ratio = max_count / max(1, min_count)
        print(f"\n  Balance ratio: {imbalance_ratio:.1f}:1 (max:min)")
        if imbalance_ratio > 3:
            print("  ⚠️ WARNING: Character imbalance detected!")
        else:
            print("  ✅ Good character balance!")

    # 3. Check for repetitive phrases
    print("\n🔍 REPETITION CHECK:")
    print("-" * 40)

    # Generate novel to check for repetitive content
    novel = workflow.generate_novel()

    problematic_phrases = [
        "他们穿越了时空裂缝",
        "启动了古老的防御系统",
        "三人合力激活了量子传送门",
        "Unknown",
    ]

    for phrase in problematic_phrases:
        count = novel.count(phrase)
        if count > 2:
            print(f"  ❌ '{phrase}': {count} occurrences (TOO MANY!)")
        elif count > 0:
            print(f"  ⚠️ '{phrase}': {count} occurrences")
        else:
            print(f"  ✅ '{phrase}': 0 occurrences")

    # 4. Overall evaluation
    evaluation = workflow.evaluate_quality()

    print("\n📈 QUALITY METRICS:")
    print("-" * 40)
    print(f"  Overall Score: {evaluation['overall_score']:.1f}/100")
    print(
        f"  Dialogue Variety: {evaluation['enhanced_metrics']['dialogue_variety']:.1%}"
    )
    print(
        f"  Repetition Ratio: {evaluation['enhanced_metrics']['repetition_ratio']:.1%}"
    )
    print(
        f"  Event Types: {evaluation['enhanced_metrics']['unique_event_types']}"
    )

    # Final verdict
    print("\n" + "=" * 80)
    print("WAVE 3 TEST RESULTS:")
    print("-" * 40)

    success_criteria = [
        ("No Unknown dialogues", unknown_count == 0),
        ("High dialogue variety (>80%)", dialogue_variety > 0.8),
        (
            "Good character balance (<3:1)",
            imbalance_ratio < 3 if character_counter else False,
        ),
        (
            "Low repetition (<20%)",
            evaluation["enhanced_metrics"]["repetition_ratio"] < 0.2,
        ),
        (
            "Multiple event types (>=4)",
            evaluation["enhanced_metrics"]["unique_event_types"] >= 4,
        ),
    ]

    passed = 0
    for criteria, result in success_criteria:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {criteria}")
        if result:
            passed += 1

    print(f"\nFinal Score: {passed}/{len(success_criteria)} criteria passed")

    if passed >= 4:
        print("🎉 WAVE 3 IMPROVEMENTS SUCCESSFUL!")
    else:
        print("⚠️ WAVE 3 NEEDS MORE WORK")

    print("=" * 80)

    # Save test results
    results = {
        "unknown_dialogues": unknown_count,
        "dialogue_variety": dialogue_variety,
        "action_variety": action_variety,
        "discovery_variety": discovery_variety,
        "conflict_variety": conflict_variety,
        "crisis_variety": crisis_variety,
        "character_balance": dict(character_counter),
        "imbalance_ratio": imbalance_ratio if character_counter else 0,
        "repetition_ratio": evaluation["enhanced_metrics"]["repetition_ratio"],
        "overall_score": evaluation["overall_score"],
        "passed_criteria": passed,
        "total_criteria": len(success_criteria),
    }

    report_path = Path("ai_testing/reports/wave3_test_results.json")
    report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\n📄 Test results saved to: {report_path}")

    return passed >= 4


if __name__ == "__main__":
    print("Testing Wave 3 Improvements...")
    success = test_content_variety()

    if success:
        print("\n✅ Ready to proceed to Wave 4!")
    else:
        print("\n⚠️ Wave 3 needs additional improvements")
