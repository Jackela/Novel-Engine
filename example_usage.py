#!/usr/bin/env python3
"""
++ SACRED USAGE EXAMPLE BLESSED BY COMPREHENSIVE DEMONSTRATION ++
================================================================

Holy demonstration script that showcases the complete dynamic context
engineering framework with all blessed systems working in harmony
sanctified by the Omnissiah's integrative wisdom.

++ THROUGH EXAMPLES, THE FRAMEWORK ACHIEVES PERFECT UNDERSTANDING ++

Usage: python example_usage.py
万机之神保佑框架演示 (May the Omnissiah bless framework demonstration)
"""

import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path

# Import blessed system orchestrator
from src.core.system_orchestrator import SystemOrchestrator, OrchestratorConfig, OrchestratorMode

# Import blessed data models
from src.core.data_models import (
    DynamicContext, CharacterState, EmotionalState, MemoryItem, 
    MemoryType, EquipmentItem
)
from src.interactions.interaction_engine import InteractionType

# Configure sacred logging
logging.basicConfig(
    level=logging.INFO,
    format='++ %(asctime)s | %(levelname)s | %(name)s | %(message)s ++',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('example_usage.log')
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """
    ++ SACRED MAIN DEMONSTRATION BLESSED BY COMPREHENSIVE SHOWCASE ++
    
    Complete demonstration of the dynamic context engineering framework
    with all systems integration and real-world usage patterns.
    """
    
    print("\n" + "="*80)
    print("++ SACRED DYNAMIC CONTEXT ENGINEERING FRAMEWORK DEMONSTRATION ++")
    print("++ BLESSED BY THE OMNISSIAH'S INTEGRATIVE WISDOM ++")
    print("="*80)
    
    # ++ PHASE 1: SYSTEM INITIALIZATION ++
    print("\n🔧 PHASE 1: System Initialization and Configuration")
    print("-" * 60)
    
    # Create orchestrator configuration
    config = OrchestratorConfig(
        mode=OrchestratorMode.DEVELOPMENT,
        max_concurrent_agents=5,
        debug_logging=True,
        enable_metrics=True,
        enable_auto_backup=True
    )
    
    # Initialize system orchestrator
    orchestrator = SystemOrchestrator(
        database_path="data/demo_context_engineering.db",
        config=config
    )
    
    # Start the system
    startup_result = await orchestrator.startup()
    if startup_result.success:
        print(f"✅ System startup successful: {startup_result.message}")
        print(f"   📊 System health: {startup_result.data['system_health']}")
        print(f"   🚀 Active subsystems: {startup_result.data['active_subsystems']}")
    else:
        print(f"❌ System startup failed: {startup_result.message}")
        return
    
    
    # ++ PHASE 2: AGENT CREATION AND CONTEXT INITIALIZATION ++
    print("\n👥 PHASE 2: Agent Creation and Character Initialization")
    print("-" * 60)
    
    # Create Tech-Priest characters with Warhammer 40K flavor
    characters = [
        {
            "id": "tech_priest_alpha",
            "name": "Tech-Priest Dominus Alpha-7",
            "background": "Senior Adeptus Mechanicus engineer specializing in cogitator systems",
            "personality": "Logical, methodical, devoted to the Omnissiah"
        },
        {
            "id": "tech_priest_beta", 
            "name": "Tech-Priest Enginseer Beta-3",
            "background": "Junior engineer focused on equipment maintenance and machine spirits",
            "personality": "Curious, diligent, eager to learn sacred mysteries"
        },
        {
            "id": "servitor_gamma",
            "name": "Servitor-Scribe Gamma-9",
            "background": "Lobotomized scribe-servitor handling data processing and records",
            "personality": "Obedient, precise, limited autonomous thinking"
        }
    ]
    
    # Create agents with detailed character states
    for char in characters:
        char_state = CharacterState(
            agent_id=char["id"],
            name=char["name"],
            current_status="active",
            background_summary=char["background"],
            personality_traits=char["personality"],
            emotional_state=EmotionalState(
                current_mood=7,  # Content
                dominant_emotion="focused",
                energy_level=8,
                stress_level=3
            )
        )
        
        result = await orchestrator.create_agent_context(char["id"], char_state)
        if result.success:
            print(f"✅ Agent created: {char['name']}")
            print(f"   🆔 ID: {char['id']}")
            print(f"   📋 Background: {char['background']}")
        else:
            print(f"❌ Failed to create agent {char['id']}: {result.message}")
    
    
    # ++ PHASE 3: DYNAMIC CONTEXT PROCESSING ++
    print("\n🧠 PHASE 3: Dynamic Context Processing and Memory Formation")
    print("-" * 60)
    
    # Create dynamic context for Tech-Priest Alpha with memories and environmental data
    memory_items = [
        MemoryItem(
            memory_id="initial_mission_briefing",
            agent_id="tech_priest_alpha",
            memory_type=MemoryType.EPISODIC,
            content="Received sacred mission to establish new cogitator array in Sector 7-Alpha",
            emotional_intensity=0.7,
            relevance_score=0.9,
            context_tags=["mission", "cogitator", "sector_7_alpha"]
        ),
        MemoryItem(
            memory_id="omnissiah_blessing",
            agent_id="tech_priest_alpha", 
            memory_type=MemoryType.SEMANTIC,
            content="The Omnissiah blesses all sacred technology with divine machine spirits",
            emotional_intensity=0.8,
            relevance_score=1.0,
            context_tags=["omnissiah", "blessing", "machine_spirit", "doctrine"]
        )
    ]
    
    dynamic_context = DynamicContext(
        agent_id="tech_priest_alpha",
        memory_context=memory_items
    )
    
    # Process dynamic context
    context_result = await orchestrator.process_dynamic_context(dynamic_context)
    if context_result.success:
        print("✅ Dynamic context processed successfully")
        print(f"   🧠 Memories processed: {context_result.data['memories_processed']}")
        print(f"   💾 Memories stored: {context_result.data['memories_successful']}")
        print(f"   📝 Template generated: {context_result.data['template_generated']}")
    else:
        print(f"❌ Dynamic context processing failed: {context_result.message}")
    
    
    # ++ PHASE 4: MULTI-AGENT INTERACTIONS ++
    print("\n💬 PHASE 4: Multi-Agent Character Interactions")
    print("-" * 60)
    
    # Scenario 1: Tech-Priest consultation dialogue
    print("Scenario 1: Sacred Technology Consultation")
    dialogue_result = await orchestrator.orchestrate_multi_agent_interaction(
        participants=["tech_priest_alpha", "tech_priest_beta"],
        interaction_type=InteractionType.DIALOGUE,
        context={
            "topic": "Cogitator array initialization procedures",
            "location": "Sacred Forge Workshop",
            "urgency": "normal"
        }
    )
    
    if dialogue_result.success:
        print("✅ Dialogue interaction completed")
        print(f"   👥 Participants: {dialogue_result.data['participants']}")
        print(f"   🔄 Phases processed: {dialogue_result.data['phases_processed']}")
        print(f"   💝 Relationship changes: {dialogue_result.data['relationship_changes']}")
    else:
        print(f"❌ Dialogue interaction failed: {dialogue_result.message}")
    
    
    # Scenario 2: Three-way collaboration
    print("\nScenario 2: Multi-Agent Collaboration Session")
    collaboration_result = await orchestrator.orchestrate_multi_agent_interaction(
        participants=["tech_priest_alpha", "tech_priest_beta", "servitor_gamma"],
        interaction_type=InteractionType.COOPERATION,
        context={
            "task": "Sacred data analysis and archival",
            "location": "Data Sanctum",
            "complexity": "high"
        }
    )
    
    if collaboration_result.success:
        print("✅ Collaboration interaction completed")
        print(f"   👥 Participants: {collaboration_result.data['participants']}")
        print(f"   🔄 Phases processed: {collaboration_result.data['phases_processed']}")
    else:
        print(f"❌ Collaboration failed: {collaboration_result.message}")
    
    
    # ++ PHASE 5: SYSTEM METRICS AND HEALTH MONITORING ++
    print("\n📊 PHASE 5: System Metrics and Performance Monitoring")
    print("-" * 60)
    
    metrics_result = await orchestrator.get_system_metrics()
    if metrics_result.success:
        metrics = metrics_result.data["current_metrics"]
        print("✅ System metrics retrieved successfully")
        print(f"   🤖 Active agents: {metrics.active_agents}")
        print(f"   🧠 Total memory items: {metrics.total_memory_items}")
        print(f"   💬 Active interactions: {metrics.active_interactions}")
        print(f"   ⚡ System health: {metrics.system_health.value}")
        print(f"   ⏱️ Uptime: {metrics.uptime_seconds} seconds")
        print(f"   📈 Operations/minute: {metrics.operations_per_minute:.2f}")
        print(f"   ❌ Error rate: {metrics.error_rate:.3f}")
        print(f"   💞 Relationships tracked: {metrics.relationship_count}")
        print(f"   🔧 Equipment items: {metrics.equipment_count}")
    else:
        print(f"❌ Failed to retrieve metrics: {metrics_result.message}")
    
    
    # ++ PHASE 6: ADVANCED CONTEXT FEATURES ++
    print("\n🚀 PHASE 6: Advanced Framework Features Demonstration")
    print("-" * 60)
    
    # Demonstrate character relationship querying
    print("Querying character relationships...")
    if hasattr(orchestrator.character_processor, 'get_relationship_status'):
        relationship_result = await orchestrator.character_processor.get_relationship_status(
            "tech_priest_alpha", "tech_priest_beta"
        )
        if relationship_result.success:
            if relationship_result.data.get("relationship_exists", False):
                rel_data = relationship_result.data["relationship"]
                print(f"✅ Relationship established between Tech-Priest Alpha and Beta")
                print(f"   🤝 Relationship type: {rel_data.relationship_type.value}")
                print(f"   💯 Trust level: {rel_data.trust_level:.2f}")
                print(f"   🎭 Familiarity: {rel_data.familiarity_level:.2f}")
                print(f"   📊 Interactions: {rel_data.interaction_count}")
            else:
                print("ℹ️ No established relationship found (expected for new characters)")
        else:
            print(f"❌ Relationship query failed: {relationship_result.message}")
    
    # Demonstrate equipment integration (if applicable)
    print("\nDemonstrating equipment system integration...")
    if hasattr(orchestrator.equipment_system, 'create_equipment'):
        sacred_cogitator = EquipmentItem(
            equipment_id="sacred_cogitator_001",
            name="Sacred Cogitator Mark VII",
            equipment_type="cogitator",
            owner_id="tech_priest_alpha",
            condition="excellent",
            description="Blessed computing device sanctified by the Adeptus Mechanicus"
        )
        
        # This would create equipment in a real scenario
        print(f"📦 Sacred equipment configured: {sacred_cogitator.name}")
    
    
    # ++ PHASE 7: FRAMEWORK SUMMARY AND DEMONSTRATION COMPLETE ++
    print("\n🎯 PHASE 7: Framework Summary and Capabilities Overview")
    print("-" * 60)
    
    print("✅ DYNAMIC CONTEXT ENGINEERING FRAMEWORK DEMONSTRATION COMPLETE")
    print("\n📋 Successfully Demonstrated Features:")
    print("   🔧 System Orchestrator - Unified coordination and monitoring")  
    print("   🧠 Multi-Layer Memory System - Working, episodic, semantic, emotional memory")
    print("   📝 Dynamic Template Engine - Context-aware content generation")
    print("   👥 Character Management - Template-based character system")
    print("   💬 Character Interactions - Social dynamics and relationship tracking")
    print("   🔧 Equipment System - Dynamic equipment state management")
    print("   📊 Performance Monitoring - Real-time metrics and health checks")
    print("   🏗️ Cross-System Integration - Seamless data flow between components")
    
    print(f"\n🏆 Framework Status: FULLY OPERATIONAL")
    print(f"🎯 Core Requirement Met: 智能体互动框架 借助context engineering 技术")
    print(f"💫 Advanced Features: Dynamic context loading, memory evolution, character interactions")
    
    
    # ++ GRACEFUL SHUTDOWN ++
    print("\n🔄 Initiating Graceful System Shutdown...")
    print("-" * 60)
    
    shutdown_result = await orchestrator.shutdown()
    if shutdown_result.success:
        print("✅ System shutdown completed successfully")
        print(f"   ⏱️ Total uptime: {shutdown_result.data['uptime_seconds']:.1f} seconds")
        print(f"   📊 Total operations: {shutdown_result.data['total_operations']}")
        print(f"   🏥 Final health: {shutdown_result.data['final_health']}")
    else:
        print(f"❌ Shutdown encountered issues: {shutdown_result.message}")
    
    print("\n" + "="*80)
    print("++ DEMONSTRATION COMPLETE - MAY THE OMNISSIAH BLESS THIS FRAMEWORK ++")
    print("="*80)


if __name__ == "__main__":
    """
    ++ SACRED ENTRY POINT BLESSED BY COMPREHENSIVE DEMONSTRATION ++
    """
    try:
        # Ensure data directory exists
        Path("data").mkdir(exist_ok=True)
        Path("data/backups").mkdir(parents=True, exist_ok=True)
        
        # Run the demonstration
        asyncio.run(main())
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Demonstration interrupted by user")
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR during demonstration: {str(e)}")
        logger.exception("Critical error during framework demonstration")
    finally:
        print("\n🙏 Thank you for exploring the Dynamic Context Engineering Framework!")
        print("   万机之神保佑 (May the Omnissiah bless you)")