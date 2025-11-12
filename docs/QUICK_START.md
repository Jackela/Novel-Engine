# Quick Start Guide - Dynamic Context Engineering Framework

## 🚀 Getting Started in 5 Minutes

This guide will get you up and running with the Dynamic Context Engineering Framework quickly.

## Prerequisites

- Python 3.8 or higher
- Basic understanding of async/await concepts
- Familiarity with SQLite databases (helpful but not required)

## Installation

1. **Clone and Set Up**
```bash
git clone <repository-url>
cd Novel-Engine
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the Demo**
```bash
python example_usage.py
```

The demo will showcase all framework capabilities in a comprehensive demonstration.

---

## Basic Usage

### 1. Initialize the System

```python
import asyncio
from src.core.system_orchestrator import SystemOrchestrator, OrchestratorConfig, OrchestratorMode

async def setup_system():
    # Create configuration
    config = OrchestratorConfig(
        mode=OrchestratorMode.DEVELOPMENT,
        max_concurrent_agents=5,
        debug_logging=True,
        enable_metrics=True
    )
    
    # Initialize orchestrator
    orchestrator = SystemOrchestrator("data/my_project.db", config)
    
    # Start the system
    startup_result = await orchestrator.startup()
    
    if startup_result.success:
        print(f"✅ System started: {startup_result.data['system_health']}")
        return orchestrator
    else:
        print(f"❌ Startup failed: {startup_result.message}")
        return None

# Run setup
orchestrator = await setup_system()
```

### 2. Create Your First Agent

```python
from src.core.data_models import CharacterState, EmotionalState

async def create_agent():
    # Define character state
    character_state = CharacterState(
        agent_id="my_first_agent",
        name="AI Assistant Alpha",
        background_summary="A helpful AI assistant specializing in data analysis",
        personality_traits="Analytical, helpful, detail-oriented",
        emotional_state=EmotionalState(
            current_mood=8,
            dominant_emotion="focused",
            energy_level=9,
            stress_level=2
        )
    )
    
    # Create agent context
    result = await orchestrator.create_agent_context("my_first_agent", character_state)
    
    if result.success:
        print(f"✅ Agent created: {character_state.name}")
        return result.data
    else:
        print(f"❌ Agent creation failed: {result.message}")
        return None

agent_data = await create_agent()
```

### 3. Add Memories to Your Agent

```python
from src.core.data_models import MemoryItem, MemoryType, DynamicContext

async def add_memories():
    # Create some memories
    memories = [
        MemoryItem(
            memory_id="welcome_message",
            agent_id="my_first_agent",
            memory_type=MemoryType.EPISODIC,
            content="Received welcome and introduction to the system",
            emotional_intensity=0.6,
            relevance_score=0.8,
            context_tags=["introduction", "welcome", "system"]
        ),
        MemoryItem(
            memory_id="capability_knowledge",
            agent_id="my_first_agent", 
            memory_type=MemoryType.SEMANTIC,
            content="I am capable of data analysis, natural language processing, and helping users with various tasks",
            emotional_intensity=0.4,
            relevance_score=0.9,
            context_tags=["capabilities", "skills", "knowledge"]
        )
    ]
    
    # Create dynamic context
    context = DynamicContext(
        agent_id="my_first_agent",
        memory_context=memories
    )
    
    # Process the context
    result = await orchestrator.process_dynamic_context(context)
    
    if result.success:
        print(f"✅ Processed {result.data['memories_processed']} memories")
        print(f"✅ Successfully stored: {result.data['memories_successful']}")
        return result.data
    else:
        print(f"❌ Memory processing failed: {result.message}")
        return None

memory_result = await add_memories()
```

### 4. Create Multi-Agent Interactions

```python
from src.interactions.interaction_engine import InteractionType

async def multi_agent_interaction():
    # First, create another agent
    second_agent_state = CharacterState(
        agent_id="data_analyst",
        name="Data Analyst Beta",
        background_summary="Specialized in statistical analysis and data visualization",
        personality_traits="Methodical, precise, curious"
    )
    
    await orchestrator.create_agent_context("data_analyst", second_agent_state)
    
    # Now orchestrate an interaction
    interaction_result = await orchestrator.orchestrate_multi_agent_interaction(
        participants=["my_first_agent", "data_analyst"],
        interaction_type=InteractionType.DIALOGUE,
        context={
            "topic": "Data analysis collaboration",
            "location": "Virtual workspace",
            "urgency": "normal"
        }
    )
    
    if interaction_result.success:
        print("✅ Interaction completed successfully!")
        print(f"   Participants: {interaction_result.data['participants']}")
        print(f"   Phases processed: {interaction_result.data['phases_processed']}")
        return interaction_result.data
    else:
        print(f"❌ Interaction failed: {interaction_result.message}")
        return None

interaction_data = await multi_agent_interaction()
```

### 5. Monitor System Performance

```python
async def check_system_status():
    metrics_result = await orchestrator.get_system_metrics()
    
    if metrics_result.success:
        metrics = metrics_result.data["current_metrics"]
        
        print("📊 System Status:")
        print(f"   🤖 Active agents: {metrics.active_agents}")
        print(f"   🧠 Total memories: {metrics.total_memory_items}")
        print(f"   💬 Active interactions: {metrics.active_interactions}")
        print(f"   ⚡ System health: {metrics.system_health.value}")
        print(f"   ⏱️ Uptime: {metrics.uptime_seconds}s")
        print(f"   📈 Operations/min: {metrics.operations_per_minute:.2f}")
        print(f"   ❌ Error rate: {metrics.error_rate:.3f}")
        
        return metrics
    else:
        print(f"❌ Failed to get metrics: {metrics_result.message}")
        return None

system_metrics = await check_system_status()
```

### 6. Graceful Shutdown

```python
async def shutdown_system():
    shutdown_result = await orchestrator.shutdown()
    
    if shutdown_result.success:
        print("✅ System shutdown completed")
        print(f"   Total uptime: {shutdown_result.data['uptime_seconds']:.1f}s")
        print(f"   Total operations: {shutdown_result.data['total_operations']}")
    else:
        print(f"❌ Shutdown issues: {shutdown_result.message}")
    
    return shutdown_result

await shutdown_system()
```

---

## Complete Example Script

Here's a complete working example you can run:

```python
#!/usr/bin/env python3
"""
Quick Start Example - Dynamic Context Engineering Framework
"""

import asyncio
from pathlib import Path
from src.core.system_orchestrator import SystemOrchestrator, OrchestratorConfig, OrchestratorMode
from src.core.data_models import CharacterState, MemoryItem, MemoryType, DynamicContext, EmotionalState
from src.interactions.interaction_engine import InteractionType

async def main():
    print("🚀 Starting Dynamic Context Engineering Framework Demo")
    
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    # 1. Initialize System
    config = OrchestratorConfig(
        mode=OrchestratorMode.DEVELOPMENT,
        debug_logging=True,
        enable_metrics=True
    )
    
    orchestrator = SystemOrchestrator("data/quickstart_demo.db", config)
    startup_result = await orchestrator.startup()
    
    if not startup_result.success:
        print(f"❌ Failed to start system: {startup_result.message}")
        return
    
    print("✅ System initialized successfully")
    
    try:
        # 2. Create Agents
        agents = [
            {
                "id": "analyst_001", 
                "name": "Senior Data Analyst",
                "background": "Expert in statistical analysis and machine learning",
                "personality": "Analytical, methodical, detail-oriented"
            },
            {
                "id": "researcher_002",
                "name": "Research Specialist", 
                "background": "Specialist in information gathering and synthesis",
                "personality": "Curious, thorough, systematic"
            }
        ]
        
        for agent in agents:
            character_state = CharacterState(
                agent_id=agent["id"],
                name=agent["name"],
                background_summary=agent["background"],
                personality_traits=agent["personality"],
                emotional_state=EmotionalState(
                    current_mood=7,
                    dominant_emotion="focused", 
                    energy_level=8,
                    stress_level=3
                )
            )
            
            result = await orchestrator.create_agent_context(agent["id"], character_state)
            if result.success:
                print(f"✅ Created agent: {agent['name']}")
            else:
                print(f"❌ Failed to create {agent['id']}: {result.message}")
        
        # 3. Add Memories
        memory = MemoryItem(
            memory_id="project_briefing",
            agent_id="analyst_001",
            memory_type=MemoryType.EPISODIC,
            content="Attended project briefing for Q4 analysis initiative",
            emotional_intensity=0.6,
            relevance_score=0.9,
            context_tags=["project", "briefing", "Q4", "analysis"]
        )
        
        context = DynamicContext(
            agent_id="analyst_001",
            memory_context=[memory]
        )
        
        memory_result = await orchestrator.process_dynamic_context(context)
        if memory_result.success:
            print(f"✅ Processed memories for analyst_001")
        
        # 4. Multi-Agent Interaction
        interaction_result = await orchestrator.orchestrate_multi_agent_interaction(
            participants=["analyst_001", "researcher_002"],
            interaction_type=InteractionType.COOPERATION,
            context={
                "topic": "Q4 analysis project planning",
                "location": "Virtual meeting room",
                "duration_minutes": 20
            }
        )
        
        if interaction_result.success:
            print("✅ Multi-agent interaction completed")
            print(f"   Phases: {interaction_result.data['phases_processed']}")
        
        # 5. System Metrics
        metrics_result = await orchestrator.get_system_metrics()
        if metrics_result.success:
            metrics = metrics_result.data["current_metrics"]
            print("\n📊 Final System Metrics:")
            print(f"   Active agents: {metrics.active_agents}")
            print(f"   Total memories: {metrics.total_memory_items}")
            print(f"   System health: {metrics.system_health.value}")
        
    except Exception as e:
        print(f"❌ Error during demo: {str(e)}")
    
    finally:
        # 6. Cleanup
        shutdown_result = await orchestrator.shutdown()
        if shutdown_result.success:
            print("✅ System shutdown completed successfully")
        
        print("\n🎯 Quick Start Demo Complete!")
        print("   Check out PROJECT_GUIDE.md for detailed documentation")
        print("   Run example_usage.py for a comprehensive demonstration")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Next Steps

### Explore Advanced Features

1. **Character Relationships**
```python
# Query character relationships
relationship = await orchestrator.character_processor.get_relationship_status(
    "analyst_001", "researcher_002"
)
```

2. **Equipment System**
```python
from src.core.data_models import EquipmentItem

# Create and assign equipment
equipment = EquipmentItem(
    equipment_id="laptop_001",
    name="Analysis Laptop",
    equipment_type="cogitator",
    owner_id="analyst_001"
)
```

3. **Template System**
```python
from src.templates.dynamic_template_engine import TemplateContext

# Use dynamic templates
template_context = TemplateContext(
    agent_id="analyst_001",
    context_variables={"current_project": "Q4_analysis"}
)
```

### Learning Resources

- **Full Documentation**: Check `docs/API_DOCUMENTATION.md`
- **Component Details**: Review `docs/COMPONENT_GUIDE.md` 
- **Project Overview**: Read `PROJECT_GUIDE.md`
- **Complete Demo**: Run `example_usage.py`

### Configuration Tips

- **Development Mode**: Use `OrchestratorMode.DEVELOPMENT` for testing
- **Production Mode**: Switch to `OrchestratorMode.PRODUCTION` for deployment
- **Debug Logging**: Enable for troubleshooting
- **Performance Monitoring**: Enable for optimization insights

### Common Patterns

1. **Agent Creation → Memory Formation → Interactions → Metrics**
2. **Always check `StandardResponse.success` before using data**
3. **Use try/except blocks for robust error handling**
4. **Call `shutdown()` for graceful cleanup**

You're now ready to build sophisticated multi-agent systems with dynamic context engineering! 🎉