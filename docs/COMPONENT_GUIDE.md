# Component Guide - Dynamic Context Engineering Framework

## Architecture Overview

The Dynamic Context Engineering Framework follows a layered architecture with clear separation of concerns and comprehensive integration between components.

```
┌─────────────────────────────────────────────────────────────┐
│                SystemOrchestrator                           │
│               (Unified Coordination)                        │
└─────────────┬───────────────┬───────────────┬───────────────┘
              │               │               │
    ┌─────────▼─────────┐ ┌───▼─────────┐ ┌───▼─────────────┐
    │  Memory System   │ │  Template   │ │  Interaction    │
    │                  │ │  System     │ │  System         │
    │ 🧠 Multi-layer   │ │ 📝 Dynamic  │ │ 💬 Character    │
    │    Architecture  │ │    Jinja2   │ │    Social       │
    └─────────┬────────┘ └───┬─────────┘ └───┬─────────────┘
              │              │               │
              └──────────────┼───────────────┘
                             │
                    ┌────────▼────────┐
                    │  Database Core  │
                    │                 │
                    │ 💾 SQLite +     │
                    │    aiosqlite    │
                    └─────────────────┘
```

---

## Core Components

### 1. System Orchestrator (`SystemOrchestrator`)

**Location:** `src/core/system_orchestrator.py`

**Purpose:** Central coordination system that manages all framework components, provides unified API, system health monitoring, and comprehensive agent lifecycle management.

#### Key Responsibilities:
- **System Lifecycle Management** - Startup, shutdown, and configuration
- **Agent Context Management** - Create, manage, and coordinate agent states
- **Cross-System Integration** - Ensure data consistency across all subsystems
- **Performance Monitoring** - Real-time metrics, health checks, and optimization
- **Resource Management** - Memory cleanup, backup systems, and resource allocation

#### Core Methods:
```python
async def startup() -> StandardResponse
async def shutdown() -> StandardResponse
async def create_agent_context(agent_id: str, initial_state: Optional[CharacterState]) -> StandardResponse
async def process_dynamic_context(context: DynamicContext) -> StandardResponse
async def orchestrate_multi_agent_interaction(participants: List[str], ...) -> StandardResponse
async def get_system_metrics() -> StandardResponse
```

#### Configuration Options:
```python
@dataclass
class OrchestratorConfig:
    mode: OrchestratorMode = OrchestratorMode.AUTONOMOUS
    max_concurrent_agents: int = 10
    memory_cleanup_interval: int = 3600
    template_cache_size: int = 100
    health_check_interval: int = 300
    enable_metrics: bool = True
    enable_auto_backup: bool = True
```

---

### 2. Multi-Layer Memory System

**Components:**
- `LayeredMemorySystem` - Main coordination (`src/memory/layered_memory.py`)
- `WorkingMemory` - Current focus memory (`src/memory/working_memory.py`)
- `EpisodicMemory` - Event-based memories (`src/memory/episodic_memory.py`) 
- `SemanticMemory` - Knowledge storage (`src/memory/semantic_memory.py`)
- `EmotionalMemory` - Emotion-linked memories (`src/memory/emotional_memory.py`)
- `MemoryQueryEngine` - Intelligent querying (`src/memory/memory_query_engine.py`)

#### 2.1 LayeredMemorySystem

**Purpose:** Unified memory architecture that integrates all memory subsystems with intelligent context resolution and cross-layer memory access.

**Key Features:**
- **Cognitive Science Foundation** - Based on 7±2 working memory capacity
- **Automatic Memory Consolidation** - Moves memories between layers based on usage
- **Intelligent Querying** - Context-aware memory retrieval
- **Memory Lifecycle Management** - Automatic cleanup and optimization

**Memory Flow:**
```
New Information → WorkingMemory (7±2 items)
                      ↓
                 Consolidation Process
                      ↓
    EpisodicMemory ← → SemanticMemory ← → EmotionalMemory
```

#### 2.2 Working Memory

**Purpose:** Manages current focus items with strict capacity limits based on cognitive science principles.

**Characteristics:**
- **Capacity:** 7±2 items (configurable)
- **Duration:** Active items only
- **Priority:** Recent, frequently accessed, high emotional intensity
- **Overflow:** Automatic consolidation to long-term memory

#### 2.3 Episodic Memory

**Purpose:** Stores event-based memories with temporal and contextual information.

**Features:**
- **Temporal Organization** - Chronological event sequencing
- **Context Rich** - Location, participants, circumstances
- **Narrative Structure** - Story-like memory organization
- **Auto-Aging** - Older memories naturally fade unless reinforced

#### 2.4 Semantic Memory

**Purpose:** Manages factual knowledge, concepts, and learned information.

**Features:**
- **Hierarchical Organization** - Concept relationships and categories
- **Cross-Reference Support** - Links between related knowledge
- **Truth Maintenance** - Consistency checking and updating
- **Generalization** - Abstract concept formation

#### 2.5 Emotional Memory

**Purpose:** Stores memories with strong emotional associations and manages emotional context.

**Features:**
- **Emotional Intensity Tracking** - 0.0 to 1.0 intensity scale
- **Mood Influence** - Emotional state affects memory retrieval
- **Trauma Modeling** - Special handling for high-intensity negative memories
- **Emotional Contagion** - Emotions spread to related memories

---

### 3. Dynamic Template System

**Components:**
- `DynamicTemplateEngine` - Core engine (`src/templates/dynamic_template_engine.py`)
- `ContextRenderer` - Rendering logic (`src/templates/context_renderer.py`)
- `CharacterTemplateManager` - Character templates (`src/templates/character_template_manager.py`)

#### 3.1 DynamicTemplateEngine

**Purpose:** Jinja2-based template engine with memory system integration and cross-document reference resolution.

**Key Features:**
- **Memory Integration** - Direct access to agent memories in templates
- **Cross-Document References** - Automatic resolution of document links
- **Context-Aware Rendering** - Dynamic content based on agent state
- **Template Caching** - Performance optimization for frequent templates

**Template Capabilities:**
```jinja2
{# Access agent memories #}
{% for memory in query_memories("recent", limit=5) %}
  - {{ memory.content }}
{% endfor %}

{# Cross-document references #}
{{ load_document("character_background.md") }}

{# Context variables #}
{{ agent.name }} is feeling {{ agent.emotional_state.dominant_emotion }}
```

#### 3.2 CharacterTemplateManager

**Purpose:** Manages character-specific templates, archetypes, and personality-driven content generation.

**Features:**
- **8 Character Archetypes** - Pre-defined personality templates
- **Dynamic Persona Switching** - Context-based personality adaptation
- **Template Inheritance** - Hierarchical template organization
- **Personality-Driven Content** - Templates adapt to character traits

**Supported Archetypes:**
- `WARRIOR` - Combat-focused, brave, direct
- `SCHOLAR` - Knowledge-seeking, analytical, cautious
- `DIPLOMAT` - Social, persuasive, cooperative
- `ROGUE` - Sneaky, independent, opportunistic
- `LEADER` - Commanding, decisive, responsible
- `MYSTIC` - Spiritual, intuitive, mysterious
- `ENGINEER` - Technical, logical, problem-solving
- `HEALER` - Caring, empathetic, supportive

---

### 4. Interaction System

**Components:**
- `InteractionEngine` - Core processing (`src/interactions/interaction_engine.py`)
- `CharacterInteractionProcessor` - Character-specific interactions (`src/interactions/character_interaction_processor.py`)
- `DynamicEquipmentSystem` - Equipment state management (`src/interactions/dynamic_equipment_system.py`)

#### 4.1 InteractionEngine

**Purpose:** Orchestrates character interactions with dynamic state management and phase-based execution.

**Interaction Types:**
- `DIALOGUE` - Conversational interactions
- `COMBAT` - Conflict and battle situations
- `COOPERATION` - Collaborative activities
- `NEGOTIATION` - Diplomatic exchanges
- `RITUAL` - Ceremonial or formal interactions
- `INSTRUCTION` - Teaching and learning scenarios
- `MAINTENANCE` - Equipment and system upkeep
- `EXPLORATION` - Discovery and investigation
- `EMERGENCY` - Crisis response situations

**Processing Flow:**
```
Interaction Request → Context Analysis → Phase Planning → 
Phase Execution → State Updates → Memory Formation → 
Equipment Integration → Outcome Generation
```

#### 4.2 CharacterInteractionProcessor

**Purpose:** Handles character-specific social dynamics, relationship evolution, and multi-character conversations.

**Key Features:**
- **11 Relationship Types** - From ally to enemy, mentor to student
- **8 Social Contexts** - Private, public, formal, combat, etc.
- **Dynamic Relationship Evolution** - Trust, respect, familiarity tracking
- **Multi-Phase Interactions** - Complex interactions broken into phases
- **Conflict Resolution** - Mediated dispute resolution

**Relationship Dynamics:**
```python
@dataclass
class RelationshipData:
    relationship_type: RelationshipType
    trust_level: float = 0.0        # -1.0 to 1.0
    respect_level: float = 0.0      # -1.0 to 1.0
    affection_level: float = 0.0    # -1.0 to 1.0
    familiarity_level: float = 0.0  # 0.0 to 1.0
    interaction_count: int = 0
    compatibility_score: float = 0.0
```

#### 4.3 DynamicEquipmentSystem

**Purpose:** Real-time equipment state tracking with wear accumulation, machine spirit moods, and predictive maintenance.

**Equipment Categories:**
- `COGITATOR` - Computing devices with processing power
- `WEAPON` - Combat equipment with damage potential
- `TOOL` - Utility instruments for tasks
- `MEDICAL` - Healthcare and healing devices
- `COMMUNICATION` - Information transmission systems
- `TRANSPORT` - Movement and mobility equipment
- `SENSOR` - Detection and monitoring devices
- `POWER` - Energy generation and storage
- `ARMOR` - Protective equipment and barriers
- `SERVO_SKULL` - Autonomous assistance drones

**Wear and Maintenance Model:**
```python
# Equipment condition tracking
wear_accumulation = base_wear * usage_intensity * duration_modifier
machine_spirit_mood = calculate_spirit_response(wear_level, maintenance_history)
failure_probability = predict_failure_risk(wear_accumulation, age, usage_patterns)
```

**Machine Spirit System (Warhammer 40K Theme):**
- **Mood States:** Content, Displeased, Wrathful, Blessed
- **Appeasement Rituals:** Maintenance activities that improve mood
- **Performance Impact:** Spirit mood affects equipment performance
- **Sacred Oils and Incense:** Ceremonial maintenance items

---

### 5. Database System

**Location:** `src/database/context_db.py`

**Purpose:** Unified database interface providing persistent storage for all framework components with async operations and comprehensive schema management.

#### Key Features:
- **SQLite Foundation** - Lightweight, embedded database
- **Async Operations** - Full aiosqlite integration
- **Schema Management** - Automatic table creation and migration
- **Transaction Support** - ACID compliance for data integrity
- **Connection Pooling** - Efficient resource management

#### Database Schema:
```sql
-- Core Tables
CREATE TABLE memories (...)           -- Memory storage
CREATE TABLE character_states (...)   -- Character state snapshots
CREATE TABLE character_interactions (...) -- Interaction logs
CREATE TABLE templates (...)          -- Template storage
CREATE TABLE equipment (...)          -- Equipment items
CREATE TABLE relationships (...)      -- Character relationships
CREATE TABLE system_state (...)       -- System metadata
```

---

## Integration Patterns

### Component Communication Flow

1. **Request Entry Point**
   - SystemOrchestrator receives API calls
   - Validates request parameters and system state
   - Routes to appropriate subsystem

2. **Memory Integration**
   - All operations can trigger memory formation
   - Context queries pull relevant memories
   - Memory consolidation happens asynchronously

3. **Template Processing**
   - Dynamic content generation uses current context
   - Memory queries embedded in templates
   - Cross-document references resolved automatically

4. **State Synchronization**
   - Character states updated across all systems
   - Equipment modifications reflected in memory
   - Relationship changes propagated to all participants

5. **Response Generation**
   - StandardResponse format ensures consistency
   - Error handling and logging throughout
   - Performance metrics collected automatically

### Cross-System Data Flow

```
User Request → SystemOrchestrator
                    ↓
            Validate & Route
                    ↓
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
Memory System → Template System → Interaction System
    │               │               │
    └───────────────┼───────────────┘
                    ▼
              Database System
                    ▼
            StandardResponse
```

---

## Performance Characteristics

### Memory Management
- **Working Memory:** O(1) access, limited capacity
- **Long-term Memory:** B-tree indexed, O(log n) queries
- **Memory Consolidation:** Background process, O(n) periodic cleanup

### Template Processing
- **Cache Hit:** O(1) template retrieval
- **Cache Miss:** O(n) template compilation + caching
- **Memory Queries:** Indexed database queries, optimized

### Interaction Processing
- **Simple Interactions:** O(1) processing time
- **Multi-Phase Interactions:** O(n) phases, parallelizable
- **Relationship Updates:** O(1) per relationship pair

### Database Operations
- **Single Operations:** O(1) with proper indexing
- **Batch Operations:** O(n) with transaction optimization
- **Complex Queries:** O(log n) with B-tree indexes

---

## Extension Points

### Adding New Memory Types
```python
class CustomMemoryType(MemorySubsystem):
    def __init__(self, agent_id: str, database: ContextDatabase):
        super().__init__(agent_id, database)
        self.custom_logic = CustomLogicHandler()
    
    async def store_custom_memory(self, memory_data: Dict[str, Any]) -> StandardResponse:
        # Custom storage logic
        pass
```

### Custom Interaction Types
```python
class CustomInteractionProcessor:
    async def process_custom_interaction(self, context: InteractionContext) -> InteractionOutcome:
        # Custom interaction logic
        return InteractionOutcome(...)
```

### Template Extensions
```python
# Custom Jinja2 filters and functions
@template_engine.filter('custom_filter')
def custom_filter(value, parameter):
    return processed_value

@template_engine.global_function
def custom_memory_query(agent_id: str, query_type: str):
    return query_results
```

This component guide provides comprehensive understanding of the framework's architecture, enabling developers to effectively utilize, extend, and maintain the Dynamic Context Engineering Framework.