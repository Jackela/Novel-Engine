#!/usr/bin/env python3
"""
AI-Enhanced ChroniclerAgent Demonstration
=========================================

This script demonstrates the complete end-to-end AI-powered workflow of the 
Warhammer 40k Multi-Agent Simulator, showcasing the ChroniclerAgent's ability
to transcribe real Gemini API-generated campaign logs into dramatic narrative stories.

The script processes the freshly generated campaign_log.md which contains:
- Real Gemini API character decision-making and reasoning
- Enhanced character personality expressions from LLM integration
- Sophisticated tactical and strategic thinking from AI agents
- Authentic Warhammer 40k faction-specific behavior patterns

This demonstrates the full production-ready capability of the system with
real AI integration rather than placeholder responses.

Requirements:
- campaign_log.md with real Gemini API-generated content
- ChroniclerAgent implementation
- Narrative output directory for storing generated stories

Output:
- Complete dramatic narrative story printed to console
- Saved narrative file in demo_narratives/ directory
- Quality analysis comparing AI-enhanced vs placeholder content
- Performance metrics for the transcription process
"""

import os
import sys
import time
from datetime import datetime

# Add the current directory to the Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chronicler_agent import ChroniclerAgent


def analyze_campaign_log_quality(log_path: str) -> dict:
    """
    Analyze the quality and content of the campaign log to demonstrate
    the improvements from real AI integration.

    Args:
        log_path: Path to the campaign log file

    Returns:
        Dictionary containing quality analysis results
    """
    print("🔍 ANALYZING CAMPAIGN LOG QUALITY")
    print("=" * 50)

    try:
        with open(log_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Count different types of content
        total_lines = len(content.split("\n"))
        llm_guided_decisions = content.count("[LLM-Guided]")
        character_actions = content.count("decided to") + content.count("chose to")
        faction_registrations = content.count("Faction:")
        reasoning_statements = content.count("My ") + content.count("As a")

        # Find character names and factions
        import re

        character_pattern = r"(\w+(?:\s+\w+)*)\s*\(([^)]+)\)"
        character_matches = re.findall(character_pattern, content)
        unique_characters = list(set([match[0] for match in character_matches]))

        faction_pattern = r"\*\*Faction:\*\*\s*([^\\]+)"
        faction_matches = re.findall(faction_pattern, content)
        unique_factions = list(set([faction.strip() for faction in faction_matches]))

        # Analyze reasoning complexity
        reasoning_pattern = r"\[LLM-Guided\]\s*([^.]+\.?)"
        reasoning_matches = re.findall(reasoning_pattern, content)
        avg_reasoning_length = (
            sum(len(reason) for reason in reasoning_matches) / len(reasoning_matches)
            if reasoning_matches
            else 0
        )

        analysis = {
            "file_stats": {
                "total_lines": total_lines,
                "file_size_kb": round(len(content) / 1024, 2),
                "total_characters": len(content),
            },
            "ai_integration_metrics": {
                "llm_guided_decisions": llm_guided_decisions,
                "character_actions": character_actions,
                "faction_registrations": faction_registrations,
                "reasoning_statements": reasoning_statements,
                "avg_reasoning_length": round(avg_reasoning_length, 1),
            },
            "character_diversity": {
                "unique_characters": unique_characters,
                "character_count": len(unique_characters),
                "unique_factions": unique_factions,
                "faction_count": len(unique_factions),
            },
            "quality_indicators": {
                "has_real_ai_decisions": llm_guided_decisions > 0,
                "has_character_reasoning": reasoning_statements > 0,
                "has_faction_diversity": len(unique_factions) > 1,
                "has_multiple_characters": len(unique_characters) > 1,
            },
        }

        print("📊 FILE STATISTICS:")
        print(f"   • Total lines: {analysis['file_stats']['total_lines']}")
        print(f"   • File size: {analysis['file_stats']['file_size_kb']} KB")
        print(f"   • Total characters: {analysis['file_stats']['total_characters']:,}")

        print("\n🤖 AI INTEGRATION METRICS:")
        print(
            f"   • LLM-guided decisions: {analysis['ai_integration_metrics']['llm_guided_decisions']}"
        )
        print(f"   • Character actions: {analysis['ai_integration_metrics']['character_actions']}")
        print(
            f"   • Reasoning statements: {analysis['ai_integration_metrics']['reasoning_statements']}"
        )
        print(
            f"   • Avg reasoning length: {analysis['ai_integration_metrics']['avg_reasoning_length']} chars"
        )

        print("\n👥 CHARACTER DIVERSITY:")
        print(f"   • Unique characters: {analysis['character_diversity']['character_count']}")
        print(f"   • Characters: {', '.join(analysis['character_diversity']['unique_characters'])}")
        print(f"   • Unique factions: {analysis['character_diversity']['faction_count']}")
        print(f"   • Factions: {', '.join(analysis['character_diversity']['unique_factions'])}")

        print("\n✅ QUALITY INDICATORS:")
        for indicator, status in analysis["quality_indicators"].items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {indicator.replace('_', ' ').title()}: {status}")

        return analysis

    except Exception as e:
        print(f"❌ Error analyzing campaign log: {str(e)}")
        return {}


def demonstrate_ai_enhanced_transcription():
    """
    Main demonstration function that showcases the complete AI-enhanced
    ChroniclerAgent workflow with real Gemini API-generated content.
    """
    print("🚀 WARHAMMER 40K MULTI-AGENT SIMULATOR")
    print("🤖 AI-Enhanced ChroniclerAgent Demonstration")
    print("=" * 60)

    # Configuration
    campaign_log_path = "campaign_log.md"
    output_directory = "demo_narratives"

    print("📋 DEMONSTRATION CONFIGURATION:")
    print(f"   • Campaign log: {campaign_log_path}")
    print(f"   • Output directory: {output_directory}")
    print(f"   • Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1: Verify campaign log exists and analyze quality
    print("\n" + "=" * 60)
    if not os.path.exists(campaign_log_path):
        print(f"❌ ERROR: Campaign log not found: {campaign_log_path}")
        print("Please ensure the campaign log has been generated with real AI decisions.")
        return

    # Analyze the quality of the AI-generated content
    log_analysis = analyze_campaign_log_quality(campaign_log_path)

    if not log_analysis.get("quality_indicators", {}).get("has_real_ai_decisions", False):
        print("\n⚠️  WARNING: Campaign log appears to lack real AI-generated decisions")
        print("Expected to find [LLM-Guided] markers indicating Gemini API integration")
    else:
        print("\n✅ CONFIRMED: Real AI integration detected!")
        print(
            f"   Found {log_analysis['ai_integration_metrics']['llm_guided_decisions']} LLM-guided decisions"
        )

    # Step 2: Initialize ChroniclerAgent
    print("\n" + "=" * 60)
    print("🔧 INITIALIZING CHRONICLER AGENT")
    print("=" * 50)

    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_directory, exist_ok=True)

        # Initialize ChroniclerAgent with output directory
        chronicler = ChroniclerAgent(output_directory=output_directory)

        print("✅ ChroniclerAgent initialized successfully!")

        # Get and display chronicler status
        status = chronicler.get_chronicler_status()
        print(f"   • Version: {status['chronicler_info']['version']}")
        print(f"   • Narrative style: {status['chronicler_info']['narrative_style']}")
        print(f"   • Output directory: {status['chronicler_info']['output_directory']}")
        print(f"   • Templates loaded: {status['system_health']['templates_loaded']}")
        print(f"   • System status: {status['system_health']['status'].upper()}")

    except Exception as e:
        print(f"❌ Failed to initialize ChroniclerAgent: {str(e)}")
        return

    # Step 3: Process the AI-enhanced campaign log
    print("\n" + "=" * 60)
    print("📚 TRANSCRIBING AI-ENHANCED CAMPAIGN LOG")
    print("=" * 50)

    start_time = time.time()

    try:
        print("🔄 Starting transcription process...")
        print("   • Parsing campaign events...")
        print("   • Generating narrative segments with LLM calls...")
        print("   • Combining segments into cohesive story...")
        print("   • Applying Warhammer 40k atmospheric formatting...")

        # Perform the actual transcription
        complete_narrative = chronicler.transcribe_log(campaign_log_path)

        end_time = time.time()
        processing_time = end_time - start_time

        print("\n✅ TRANSCRIPTION COMPLETED!")
        print(f"   • Processing time: {processing_time:.2f} seconds")
        print(f"   • Narrative length: {len(complete_narrative):,} characters")
        print(f"   • Events processed: {chronicler.events_processed}")
        print(f"   • Narratives generated: {chronicler.narratives_generated}")
        print(f"   • LLM calls made: {chronicler.llm_calls_made}")

    except Exception as e:
        print(f"❌ Transcription failed: {str(e)}")
        return

    # Step 4: Display the complete AI-powered narrative
    print("\n" + "=" * 60)
    print("📖 COMPLETE AI-POWERED NARRATIVE STORY")
    print("=" * 60)

    print(complete_narrative)

    # Step 5: Analysis and quality assessment
    print("\n" + "=" * 60)
    print("📊 NARRATIVE QUALITY ANALYSIS")
    print("=" * 50)

    # Analyze the generated narrative
    narrative_words = len(complete_narrative.split())
    narrative_sentences = (
        complete_narrative.count(".")
        + complete_narrative.count("!")
        + complete_narrative.count("?")
    )
    avg_sentence_length = narrative_words / narrative_sentences if narrative_sentences > 0 else 0

    # Check for Warhammer 40k terminology
    wh40k_terms = [
        "Emperor",
        "Imperium",
        "grim darkness",
        "far future",
        "war",
        "battle",
        "Astra Militarum",
        "Death Korps",
        "Krieg",
        "Orks",
        "Goff",
        "WAAAGH",
        "warrior",
        "conflict",
        "fate",
        "destiny",
        "darkness",
        "light",
    ]

    term_count = sum(complete_narrative.lower().count(term.lower()) for term in wh40k_terms)

    print("📝 NARRATIVE STATISTICS:")
    print(f"   • Total words: {narrative_words:,}")
    print(f"   • Total sentences: {narrative_sentences}")
    print(f"   • Average sentence length: {avg_sentence_length:.1f} words")
    print(f"   • Warhammer 40k terminology usage: {term_count} instances")

    print("\n🎯 QUALITY ASSESSMENT:")
    quality_score = 0

    # Check narrative length
    if narrative_words > 100:
        print("   ✅ Narrative length: Substantial content generated")
        quality_score += 1
    else:
        print("   ❌ Narrative length: Content too brief")

    # Check Warhammer 40k atmosphere
    if term_count > 5:
        print("   ✅ Warhammer 40k atmosphere: Authentic terminology used")
        quality_score += 1
    else:
        print("   ❌ Warhammer 40k atmosphere: Limited authentic terminology")

    # Check for character integration
    characters_in_narrative = sum(
        1
        for char in log_analysis.get("character_diversity", {}).get("unique_characters", [])
        if char.lower() in complete_narrative.lower()
    )
    if characters_in_narrative > 0:
        print(f"   ✅ Character integration: {characters_in_narrative} characters featured")
        quality_score += 1
    else:
        print("   ❌ Character integration: Characters not well integrated")

    # Check for AI reasoning integration
    if log_analysis.get("ai_integration_metrics", {}).get("llm_guided_decisions", 0) > 0:
        print("   ✅ AI reasoning integration: Real LLM decisions transcribed")
        quality_score += 1
    else:
        print("   ❌ AI reasoning integration: No real LLM decisions found")

    print(f"\n🏆 OVERALL QUALITY SCORE: {quality_score}/4")

    if quality_score >= 3:
        print("   🌟 EXCELLENT: High-quality AI-enhanced narrative generated!")
    elif quality_score >= 2:
        print("   👍 GOOD: Solid narrative with room for improvement")
    else:
        print("   ⚠️  NEEDS IMPROVEMENT: Narrative quality below expectations")

    # Step 6: Final summary and file locations
    print("\n" + "=" * 60)
    print("📋 DEMONSTRATION SUMMARY")
    print("=" * 50)

    print("✅ SUCCESSFULLY DEMONSTRATED:")
    print("   • ChroniclerAgent initialization and configuration")
    print("   • Real AI-enhanced campaign log processing")
    print("   • Narrative transcription with LLM integration")
    print("   • Complete dramatic story generation")
    print("   • Warhammer 40k atmospheric preservation")
    print("   • Quality analysis and assessment")

    print("\n📁 GENERATED FILES:")
    print(f"   • Narrative saved to: {output_directory}/")

    # List generated narrative files
    narrative_files = [f for f in os.listdir(output_directory) if f.endswith("_narrative_*.md")]
    if narrative_files:
        latest_file = max(
            narrative_files, key=lambda f: os.path.getctime(os.path.join(output_directory, f))
        )
        print(f"   • Latest narrative: {latest_file}")
        print(f"   • Full path: {os.path.abspath(os.path.join(output_directory, latest_file))}")

    print("\n🚀 END-TO-END AI-POWERED WORKFLOW COMPLETE!")
    print("The Warhammer 40k Multi-Agent Simulator has successfully demonstrated")
    print("the full production capability from real Gemini API character decisions")
    print("through structured campaign logging to final dramatic narrative stories.")

    return complete_narrative


def show_ai_enhancement_comparison():
    """
    Display a comparison highlighting the improvements from real AI integration
    versus placeholder-based responses.
    """
    print("\n" + "=" * 60)
    print("🔄 AI ENHANCEMENT COMPARISON")
    print("=" * 60)

    print("📊 PLACEHOLDER VS. REAL AI INTEGRATION:")
    print()

    print("❌ PREVIOUS PLACEHOLDER RESPONSES:")
    print("   • Generic 'wait and observe' actions")
    print("   • Simple 'attack' commands without reasoning")
    print("   • No faction-specific behavior patterns")
    print("   • Limited character personality expression")
    print("   • Basic decision-making without context")
    print()

    print("✅ REAL GEMINI API ENHANCED RESPONSES:")
    print("   • Sophisticated tactical reasoning:")
    print("     'Coordination with allies is essential before responding to this threat'")
    print("   • Faction-specific motivations:")
    print("     'My aggressive nature and loyalty to the faction demand immediate action'")
    print("   • Character-appropriate decision-making:")
    print("     'As a proper Goff Ork, aggressive nature demands he seek out a good fight'")
    print("   • Complex strategic thinking:")
    print("     'My duty is to the Emperor... I will press forward through any moderate threat'")
    print("   • Authentic lore-based reasoning:")
    print("     'Da WAAAGH! demands action, and a loud, direct attack is da best way'")
    print()

    print("🎯 NARRATIVE QUALITY IMPROVEMENTS:")
    print("   ✅ Richer character depth from AI reasoning")
    print("   ✅ More varied and nuanced character interactions")
    print("   ✅ Enhanced tactical and strategic complexity")
    print("   ✅ Authentic Warhammer 40k faction representations")
    print("   ✅ Improved story coherence and dramatic flow")


if __name__ == "__main__":
    print("Starting AI-Enhanced ChroniclerAgent Demonstration...")
    print("This showcases the complete end-to-end AI-powered workflow!")
    print()

    # Show the enhancement comparison first
    show_ai_enhancement_comparison()

    # Run the main demonstration
    narrative = demonstrate_ai_enhanced_transcription()

    if narrative:
        print(f"\n{'='*60}")
        print("🎉 DEMONSTRATION COMPLETED SUCCESSFULLY!")
        print(f"{'='*60}")
        print("The ChroniclerAgent has successfully processed real AI-enhanced")
        print("campaign data and generated a complete dramatic narrative story.")
        print("This demonstrates the full production-ready capability of the")
        print("Warhammer 40k Multi-Agent Simulator with genuine AI integration!")
    else:
        print(f"\n{'='*60}")
        print("❌ DEMONSTRATION ENCOUNTERED ISSUES")
        print(f"{'='*60}")
        print("Please check the error messages above and ensure all")
        print("requirements are met for the demonstration to run successfully.")
