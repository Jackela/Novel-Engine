#!/usr/bin/env python3
"""
ChroniclerAgent Narrative Transcription Demonstration
====================================================

This script demonstrates the complete workflow of the ChroniclerAgent's narrative
transcription capabilities. It initializes the ChroniclerAgent and uses it to
transform the structured campaign log into a dramatic Novel Engine narrative.

The demonstration showcases:
1. ChroniclerAgent initialization with output directory setup
2. Campaign log parsing and event extraction
3. LLM-guided narrative generation for each significant event
4. Story combination and atmospheric storytelling
5. Complete narrative output display
6. Validation of transcription quality

This serves as the capstone demonstration of the Novel Engine Multi-Agent
Simulator's Phase 4 story transcription capabilities.

Author: ChroniclerAgent Development Team
Phase: Phase 4 - Story Transcription (Final Integration)
"""

import logging
import os
import sys
from datetime import datetime

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agents.chronicler_agent import create_chronicler_with_output

# Configure logging for demonstration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demonstrate_chronicler_transcription():
    """
    Complete demonstration of ChroniclerAgent narrative transcription workflow.
    
    This function executes the full pipeline from campaign log to dramatic narrative,
    showcasing the transformation of structured simulation data into engaging
    Novel Engine storytelling.
    """
    print("=" * 80)
    print("Novel Engine MULTI-AGENT SIMULATOR")
    print("ChroniclerAgent Narrative Transcription Demonstration")
    print("=" * 80)
    print()
    
    # Configuration
    campaign_log_path = "campaign_log.md"
    output_directory = "demo_narratives"
    
    print(f"📖 Campaign Log: {campaign_log_path}")
    print(f"📁 Output Directory: {output_directory}")
    print()
    
    try:
        # Step 1: Initialize ChroniclerAgent
        print("🔧 STEP 1: Initializing ChroniclerAgent")
        print("-" * 40)
        
        start_time = datetime.now()
        chronicler = create_chronicler_with_output(output_directory)
        
        print("✅ ChroniclerAgent initialized successfully")
        print(f"   Narrative Style: {chronicler.narrative_style}")
        print(f"   Output Directory: {chronicler.output_directory}")
        print(f"   Max Events per Batch: {chronicler.max_events_per_batch}")
        print()
        
        # Step 2: Validate campaign log exists
        print("🔍 STEP 2: Validating Campaign Log")
        print("-" * 40)
        
        if not os.path.exists(campaign_log_path):
            raise FileNotFoundError(f"Campaign log not found: {campaign_log_path}")
        
        log_size = os.path.getsize(campaign_log_path)
        print(f"✅ Campaign log found: {log_size:,} bytes")
        print(f"   File: {os.path.abspath(campaign_log_path)}")
        print()
        
        # Step 3: Execute narrative transcription
        print("🎭 STEP 3: Executing Narrative Transcription")
        print("-" * 40)
        
        print("📝 Processing campaign events...")
        print("🧠 Generating LLM-guided narrative segments...")
        print("📚 Combining segments into cohesive story...")
        print()
        
        # Call the main transcription method
        complete_narrative = chronicler.transcribe_log(campaign_log_path)
        
        transcription_time = datetime.now()
        processing_duration = (transcription_time - start_time).total_seconds()
        
        print("✅ Narrative transcription completed successfully")
        print(f"   Processing Time: {processing_duration:.2f} seconds")
        print(f"   Narrative Length: {len(complete_narrative):,} characters")
        print()
        
        # Step 4: Display the complete narrative
        print("📖 STEP 4: Complete Narrative Story")
        print("=" * 80)
        print()
        
        # Display the narrative with proper formatting
        print(complete_narrative)
        print()
        print("=" * 80)
        print()
        
        # Step 5: Validate transcription quality
        print("✅ STEP 5: Transcription Quality Validation")
        print("-" * 40)
        
        # Check for key characters
        has_trooper_86 = "Trooper 86" in complete_narrative or "trooper 86" in complete_narrative.lower()
        has_griznork = "Griznork" in complete_narrative or "griznork" in complete_narrative.lower()
        
        # Check for Novel Engine atmosphere
        wh40k_terms = [
            "Emperor", "grim darkness", "far future", "war", "41st millennium", 
            "Space Marines", "Imperial", "Orks", "Death Korps", "Krieg"
        ]
        wh40k_score = sum(1 for term in wh40k_terms if term.lower() in complete_narrative.lower())
        
        # Check for narrative coherence (basic checks)
        has_opening = len(complete_narrative) > 100
        has_proper_structure = "." in complete_narrative and len(complete_narrative.split('.')) > 3
        
        print("🪖 Character Representation:")
        print(f"   Trooper 86 (Death Korps): {'✅ Present' if has_trooper_86 else '❌ Missing'}")
        print(f"   Griznork (Orks): {'✅ Present' if has_griznork else '❌ Missing'}")
        print()
        
        print("🌌 Novel Engine Atmosphere:")
        print(f"   Atmospheric Terms: {wh40k_score}/{len(wh40k_terms)} detected")
        print(f"   Atmosphere Quality: {'✅ Excellent' if wh40k_score >= 5 else '⚠️ Adequate' if wh40k_score >= 3 else '❌ Poor'}")
        print()
        
        print("📝 Narrative Structure:")
        print(f"   Length: {'✅ Sufficient' if has_opening else '❌ Too Short'}")
        print(f"   Structure: {'✅ Coherent' if has_proper_structure else '❌ Fragmented'}")
        print()
        
        # Step 6: Display chronicler statistics
        print("📊 STEP 6: ChroniclerAgent Performance Statistics")
        print("-" * 40)
        
        status = chronicler.get_chronicler_status()
        
        print("📈 Processing Statistics:")
        print(f"   Events Processed: {status['processing_stats']['events_processed']}")
        print(f"   Narratives Generated: {status['processing_stats']['narratives_generated']}")
        print(f"   LLM Calls Made: {status['processing_stats']['llm_calls_made']}")
        print(f"   Error Count: {status['processing_stats']['error_count']}")
        print()
        
        print("🏥 System Health:")
        print(f"   Status: {status['system_health']['status'].upper()}")
        print(f"   Templates Loaded: {status['system_health']['templates_loaded']}")
        print(f"   Faction Descriptions: {status['system_health']['faction_descriptions_loaded']}")
        print()
        
        print("🔧 Capabilities:")
        for capability, enabled in status['capabilities'].items():
            status_icon = "✅" if enabled else "❌"
            print(f"   {capability.replace('_', ' ').title()}: {status_icon}")
        print()
        
        # Step 7: Final validation and summary
        print("🎯 STEP 7: Demonstration Summary")
        print("-" * 40)
        
        overall_success = (
            has_trooper_86 and has_griznork and 
            wh40k_score >= 3 and has_opening and has_proper_structure
        )
        
        if overall_success:
            print("🎉 DEMONSTRATION SUCCESSFUL!")
            print("   ✅ ChroniclerAgent initialized without errors")
            print("   ✅ Campaign log successfully processed into narrative")
            print("   ✅ Complete story generated with character interactions")
            print("   ✅ Authentic Novel Engine storytelling demonstrated")
            print("   ✅ End-to-end workflow validated")
        else:
            print("⚠️  DEMONSTRATION PARTIALLY SUCCESSFUL")
            print("   Some quality metrics did not meet expectations")
            print("   Review the validation results above for details")
        
        print()
        print(f"📁 Narrative saved to: {output_directory}/")
        print(f"⏱️  Total demonstration time: {processing_duration:.2f} seconds")
        print()
        
        return complete_narrative, overall_success
        
    except Exception as e:
        logger.error(f"Demonstration failed: {str(e)}")
        print(f"❌ DEMONSTRATION FAILED: {str(e)}")
        print()
        print("🔧 Troubleshooting:")
        print("   1. Ensure campaign_log.md exists in the current directory")
        print("   2. Verify ChroniclerAgent dependencies are installed")
        print("   3. Check file permissions for output directory creation")
        print("   4. Review the error logs above for specific issues")
        print()
        return None, False


def display_narrative_preview(narrative: str, max_lines: int = 20):
    """
    Display a preview of the generated narrative for quick validation.
    
    Args:
        narrative: Complete narrative text
        max_lines: Maximum number of lines to display
    """
    print("📖 NARRATIVE PREVIEW (First 20 lines)")
    print("-" * 60)
    
    lines = narrative.split('\n')
    preview_lines = lines[:max_lines]
    
    for i, line in enumerate(preview_lines, 1):
        print(f"{i:2d}: {line}")
    
    if len(lines) > max_lines:
        print(f"... ({len(lines) - max_lines} more lines)")
    
    print("-" * 60)
    print()


def validate_Novel Engine_atmosphere(narrative: str) -> dict:
    """
    Validate the Novel Engine atmospheric elements in the narrative.
    
    Args:
        narrative: Complete narrative text
        
    Returns:
        Dictionary of validation results
    """
    validation_results = {
        'grimdark_terms': 0,
        'faction_terms': 0,
        'character_mentions': 0,
        'atmospheric_quality': 'Unknown'
    }
    
    narrative_lower = narrative.lower()
    
    # Check for grimdark atmosphere
    grimdark_terms = [
        'grim darkness', 'far future', 'only war', '41st millennium',
        'emperor', 'darkness', 'war', 'death', 'sacrifice', 'duty'
    ]
    
    for term in grimdark_terms:
        if term in narrative_lower:
            validation_results['grimdark_terms'] += 1
    
    # Check for faction representation
    faction_terms = [
        'death korps', 'krieg', 'astra militarum', 'imperial guard',
        'orks', 'goff', 'space marines', 'Engineering Team'
    ]
    
    for term in faction_terms:
        if term in narrative_lower:
            validation_results['faction_terms'] += 1
    
    # Check for character mentions
    characters = ['trooper 86', 'griznork']
    for character in characters:
        if character in narrative_lower:
            validation_results['character_mentions'] += 1
    
    # Determine overall atmospheric quality
    total_score = (
        validation_results['grimdark_terms'] +
        validation_results['faction_terms'] +
        validation_results['character_mentions']
    )
    
    if total_score >= 8:
        validation_results['atmospheric_quality'] = 'Excellent'
    elif total_score >= 5:
        validation_results['atmospheric_quality'] = 'Good'
    elif total_score >= 3:
        validation_results['atmospheric_quality'] = 'Adequate'
    else:
        validation_results['atmospheric_quality'] = 'Poor'
    
    return validation_results


def main():
    """
    Main function to execute the ChroniclerAgent transcription demonstration.
    """
    try:
        # Execute the complete demonstration
        narrative, success = demonstrate_chronicler_transcription()
        
        if narrative and success:
            print("🚀 ChroniclerAgent demonstration completed successfully!")
            print()
            print("The Novel Engine Multi-Agent Simulator has successfully demonstrated")
            print("its complete end-to-end workflow from structured simulation data")
            print("to dramatic narrative storytelling.")
            print()
            print("Key achievements:")
            print("✅ DirectorAgent campaign management")
            print("✅ PersonaAgent character behavior simulation")
            print("✅ ChroniclerAgent narrative transcription")
            print("✅ LLM-guided story generation")
            print("✅ Authentic Novel Engine atmosphere")
            print()
            print("The system is ready for extended campaign simulations!")
            
        else:
            print("⚠️  Demonstration encountered issues.")
            print("Please review the output above for troubleshooting guidance.")
            
    except KeyboardInterrupt:
        print("\n🛑 Demonstration interrupted by user.")
    except Exception as e:
        print(f"\n💥 Unexpected error during demonstration: {str(e)}")
        logger.error(f"Main execution failed: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()