#!/usr/bin/env python3
"""
Real AI Generation Test
Validates that we have genuine LLM generation, not template selection
"""

import json
import logging
import os
import sys
from datetime import datetime

# Add the ai_testing directory to the Python path
sys.path.append(os.path.dirname(__file__))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_real_ai_generation():
    """Test that we have real AI generation working"""
    print("🤖 Testing Real AI Generation Capabilities")
    print("=" * 50)

    try:
        # Import the new LLM client
        from core.llm_client import LLMClient

        print("✅ Successfully imported new LLM client")

        # Initialize client
        llm_client = LLMClient(primary_provider="gemini")
        print(f"✅ LLM client initialized with provider: {llm_client.primary_provider}")

        # Run comprehensive generation test
        print("\n🧪 Running Generation Tests...")
        test_results = llm_client.test_generation()

        # Display results
        print("\n📊 Test Results:")
        print(f"Provider: {test_results['provider']}")
        print(f"Connection: {'✅' if test_results['connection'] else '❌'}")
        print(f"Dialogue Test: {'✅' if test_results['dialogue_test'] else '❌'}")
        print(f"Event Test: {'✅' if test_results['event_test'] else '❌'}")
        print(f"Narrative Test: {'✅' if test_results['narrative_test'] else '❌'}")
        print(f"Overall Success: {'✅' if test_results['overall_success'] else '❌'}")

        if test_results.get("errors"):
            print(f"\n⚠️ Errors: {test_results['errors']}")

        # Show sample outputs
        if test_results.get("sample_dialogue"):
            print(f"\n💬 Sample Dialogue: {test_results['sample_dialogue']}")

        if test_results.get("sample_event"):
            print(
                f"\n🎭 Sample Event: {json.dumps(test_results['sample_event'], ensure_ascii=False, indent=2)}"
            )

        if test_results.get("sample_narrative"):
            print(f"\n📖 Sample Narrative: {test_results['sample_narrative']}")

        # Test multiple character personalities to verify uniqueness
        print("\n🎭 Testing Character Personality Differences...")

        characters = [
            {
                "name": "哲学诗人·墨羽",
                "personality": {"philosophical": 0.9, "mysterious": 0.8, "poetic": 0.9},
                "emotion": "contemplative",
            },
            {
                "name": "量子工程师·星辰",
                "personality": {"logical": 0.9, "precise": 0.8, "technical": 0.9},
                "emotion": "focused",
            },
            {
                "name": "时空舞者·流光",
                "personality": {"creative": 0.9, "spontaneous": 0.8, "artistic": 0.9},
                "emotion": "inspired",
            },
        ]

        dialogues = []
        context = {"location": "虚空观察站", "tension": 0.7, "discovery": "维度裂缝"}

        for character in characters:
            dialogue = llm_client.generate_dialogue(
                character_name=character["name"],
                personality=character["personality"],
                emotion=character["emotion"],
                context=context,
                temperature=0.8,
            )
            dialogues.append(
                {
                    "character": character["name"],
                    "dialogue": dialogue,
                    "personality_type": max(
                        character["personality"], key=character["personality"].get
                    ),
                }
            )
            print(f"  {character['name']}: {dialogue}")

        # Analyze uniqueness
        unique_dialogues = len(set(d["dialogue"] for d in dialogues))
        print("\n📈 Uniqueness Analysis:")
        print(f"Generated dialogues: {len(dialogues)}")
        print(f"Unique dialogues: {unique_dialogues}")
        print(f"Uniqueness rate: {unique_dialogues/len(dialogues)*100:.1f}%")

        # Validate no template patterns
        template_indicators = ["[", "]", "随机", "模板", "选择"]
        has_template_patterns = any(
            any(indicator in d["dialogue"] for indicator in template_indicators)
            for d in dialogues
        )

        print("\n🔍 Template Pattern Check:")
        print(
            f"Template patterns detected: {'❌ Yes' if has_template_patterns else '✅ No'}"
        )

        # Final assessment
        success_criteria = [
            test_results["overall_success"],
            unique_dialogues == len(dialogues),  # All dialogues unique
            not has_template_patterns,  # No template patterns
            all(
                len(d["dialogue"]) > 5 for d in dialogues
            ),  # All dialogues have content
        ]

        overall_success = all(success_criteria)

        print("\n🎯 MVP Validation:")
        print(
            f"Real AI generation: {'✅' if test_results['overall_success'] else '❌'}"
        )
        print(
            f"Character uniqueness: {'✅' if unique_dialogues == len(dialogues) else '❌'}"
        )
        print(f"No template patterns: {'✅' if not has_template_patterns else '❌'}")
        print(
            f"Content quality: {'✅' if all(len(d['dialogue']) > 5 for d in dialogues) else '❌'}"
        )

        print(
            f"\n🏆 OVERALL RESULT: {'✅ SUCCESS - Real AI Generation Validated' if overall_success else '❌ FAILURE - Issues Detected'}"
        )

        # Save detailed results
        report = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "real_ai_generation_validation",
            "provider": test_results["provider"],
            "overall_success": overall_success,
            "generation_tests": test_results,
            "character_tests": dialogues,
            "uniqueness_rate": unique_dialogues / len(dialogues),
            "template_patterns_detected": has_template_patterns,
            "success_criteria": {
                "real_ai_generation": test_results["overall_success"],
                "character_uniqueness": unique_dialogues == len(dialogues),
                "no_template_patterns": not has_template_patterns,
                "content_quality": all(len(d["dialogue"]) > 5 for d in dialogues),
            },
        }

        report_file = f"reports/real_ai_generation_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs("reports", exist_ok=True)
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📄 Detailed report saved: {report_file}")

        return overall_success

    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_real_ai_generation()
    sys.exit(0 if success else 1)
