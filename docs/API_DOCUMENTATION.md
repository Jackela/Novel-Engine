# API Documentation - Dynamic Context Engineering Framework

## Overview

The Dynamic Context Engineering Framework provides a comprehensive API for managing intelligent agent interactions with dynamic context loading, multi-layer memory systems, and real-time state evolution.

## Core Components API Reference

### 1. System Orchestrator

The central coordination system that manages all framework components.

#### `SystemOrchestrator`

```python
class SystemOrchestrator:
    def __init__(self, database_path: str, config: Optional[OrchestratorConfig] = None)
    
    async def startup() -> StandardResponse
    async def shutdown() -> StandardResponse
    
    # Agent Management
    async def create_agent_context(agent_id: str, initial_state: Optional[CharacterState] = None) -> StandardResponse
    
    # Context Processing
    async def process_dynamic_context(context: DynamicContext) -> StandardResponse
    
    # Multi-Agent Interactions
    async def orchestrate_multi_agent_interaction(
        participants: List[str], 
        interaction_type: InteractionType = InteractionType.DIALOGUE,
        context: Optional[Dict[str, Any]] = None
    ) -> StandardResponse
    
    # System Monitoring
    async def get_system_metrics() -> StandardResponse
```

**Example Usage:**
```python
from src.core.system_orchestrator import SystemOrchestrator, OrchestratorConfig

# Initialize system
config = OrchestratorConfig(mode=OrchestratorMode.DEVELOPMENT)
orchestrator = SystemOrchestrator("data/my_project.db", config)
await orchestrator.startup()

# Create an agent
result = await orchestrator.create_agent_context("agent_001")
```

---

### 2. Multi-Layer Memory System

Advanced memory management with cognitive science foundations.

#### `LayeredMemorySystem`

```python
class LayeredMemorySystem:
    def __init__(self, agent_id: AgentID, database: ContextDatabase, 
                 working_capacity: int = 7, episodic_max: int = 1000,
                 semantic_max: int = 5000, emotional_max: int = 500)
    
    # Core Memory Operations
    async def store_memory(memory_item: MemoryItem) -> StandardResponse
    async def retrieve_memories(query: MemoryQueryRequest) -> StandardResponse
    async def update_memory(memory_id: str, updates: Dict[str, Any]) -> StandardResponse
    async def delete_memory(memory_id: str) -> StandardResponse
    
    # Advanced Operations
    async def get_working_memory_context() -> StandardResponse
    async def consolidate_memories() -> StandardResponse
    async def get_memory_statistics() -> StandardResponse
```

**Memory Types:**
- **Working Memory**: Current focus items (7±2 capacity)
- **Episodic Memory**: Event-based memories with temporal context
- **Semantic Memory**: Knowledge and factual information
- **Emotional Memory**: Emotionally-charged memories with intensity ratings

**Example Usage:**
```python
from src.core.data_models import MemoryItem, MemoryType

# Create a memory item
memory = MemoryItem(
    memory_id="task_001",
    agent_id="agent_001",
    memory_type=MemoryType.EPISODIC,
    content="Completed data analysis task with 95% accuracy",
    emotional_intensity=0.7,
    relevance_score=0.9,
    context_tags=["task", "analysis", "success"]
)

# Store memory
memory_system = LayeredMemorySystem("agent_001", database)
result = await memory_system.store_memory(memory)
```

---

### 3. Dynamic Template Engine

Context-aware content generation with Jinja2 integration.

#### `DynamicTemplateEngine`

```python
class DynamicTemplateEngine:
    def __init__(self, template_dir: Path, memory_query_engine: MemoryQueryEngine)
    
    # Template Operations
    async def render_template(
        template_id: str, 
        context: TemplateContext,
        enable_memory_queries: bool = True,
        enable_cross_references: bool = True
    ) -> StandardResponse
    
    async def register_template(template_id: str, template_content: str) -> StandardResponse
    async def list_templates() -> StandardResponse
    async def validate_template(template_content: str) -> StandardResponse
```

**Template Context Structure:**
```python
@dataclass
class TemplateContext:
    agent_id: str
    character_state: Optional[CharacterState] = None
    context_variables: Dict[str, Any] = field(default_factory=dict)
    memory_queries: List[str] = field(default_factory=list)
    cross_references: List[str] = field(default_factory=list)
```

**Example Usage:**
```python
# Create template context
template_context = TemplateContext(
    agent_id="agent_001",
    character_state=character_state,
    context_variables={
        "current_task": "data_analysis",
        "mood": "focused"
    }
)

# Render template
template_engine = DynamicTemplateEngine(Path("templates"), memory_engine)
result = await template_engine.render_template("agent_response", template_context)
```

---

### 4. Character Interaction System

Manage complex multi-character interactions with relationship dynamics.

#### `CharacterInteractionProcessor`

```python
class CharacterInteractionProcessor:
    def __init__(self, database: ContextDatabase, interaction_engine: InteractionEngine,
                 equipment_system: DynamicEquipmentSystem, memory_system: LayeredMemorySystem,
                 template_engine: DynamicTemplateEngine, character_manager: CharacterTemplateManager)
    
    # Interaction Processing
    async def process_character_interaction(
        interaction_context: InteractionContext,
        characters: List[str], 
        social_environment: Optional[SocialEnvironment] = None
    ) -> StandardResponse
    
    # Conversation Management
    async def initiate_conversation(
        participants: List[str], 
        topic: str = "",
        location: str = "", 
        context: SocialContext = SocialContext.CASUAL
    ) -> StandardResponse
    
    # Relationship Management
    async def get_relationship_status(character_a: str, character_b: str) -> StandardResponse
    
    # Conflict Resolution
    async def resolve_conflict(
        conflicted_characters: List[str], 
        conflict_type: str = "disagreement",
        mediator: Optional[str] = None
    ) -> StandardResponse
```

**Interaction Types:**
- `DIALOGUE` - Conversational interactions
- `COMBAT` - Conflict situations
- `COOPERATION` - Collaborative activities
- `NEGOTIATION` - Diplomatic exchanges
- `RITUAL` - Ceremonial interactions
- `INSTRUCTION` - Teaching/learning scenarios
- `EMERGENCY` - Crisis situations

**Example Usage:**
```python
# Multi-character conversation
result = await character_processor.initiate_conversation(
    participants=["agent_001", "agent_002", "agent_003"],
    topic="Project planning discussion",
    location="Virtual meeting room",
    context=SocialContext.FORMAL
)
```

---

### 5. Dynamic Equipment System

Real-time equipment state management with predictive maintenance.

#### `DynamicEquipmentSystem`

```python
class DynamicEquipmentSystem:
    def __init__(self, database: ContextDatabase, memory_system: LayeredMemorySystem)
    
    # Equipment Management
    async def create_equipment(equipment_data: EquipmentItem) -> StandardResponse
    async def get_equipment_status(equipment_id: str) -> StandardResponse
    async def update_equipment_condition(equipment_id: str, new_condition: str) -> StandardResponse
    
    # Usage Tracking
    async def use_equipment(
        equipment_id: str, 
        agent_id: str,
        usage_context: Dict[str, Any],
        expected_duration: int = 60
    ) -> StandardResponse
    
    # Maintenance System
    async def schedule_maintenance(equipment_id: str, maintenance_type: str) -> StandardResponse
    async def get_maintenance_schedule(agent_id: Optional[str] = None) -> StandardResponse
    
    # Agent Equipment
    async def assign_equipment_to_agent(equipment_id: str, agent_id: str) -> StandardResponse
    async def get_agent_equipment(agent_id: str) -> StandardResponse
```

**Equipment Categories:**
- `COGITATOR` - Computing devices
- `WEAPON` - Combat equipment
- `TOOL` - Utility instruments
- `MEDICAL` - Healthcare devices
- `COMMUNICATION` - Communication systems
- `TRANSPORT` - Movement equipment
- `SENSOR` - Detection devices
- `POWER` - Energy systems
- `ARMOR` - Protective equipment
- `SERVO_SKULL` - Automated assistants

**Example Usage:**
```python
# Create equipment
equipment = EquipmentItem(
    equipment_id="cogitator_001",
    name="Sacred Cogitator Mark VII",
    equipment_type="cogitator",
    owner_id="agent_001",
    condition="excellent"
)

equipment_system = DynamicEquipmentSystem(database, memory_system)
await equipment_system.create_equipment(equipment)

# Use equipment
usage_result = await equipment_system.use_equipment(
    equipment_id="cogitator_001",
    agent_id="agent_001", 
    usage_context={"task": "data_analysis", "intensity": "medium"},
    expected_duration=120
)
```

---

## Data Models

### Core Data Structures

#### `DynamicContext`
```python
@dataclass
class DynamicContext:
    agent_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    character_state: Optional[CharacterState] = None
    memory_context: List[MemoryItem] = field(default_factory=list)
    environmental_context: Optional[EnvironmentalState] = None
```

#### `CharacterState`
```python
@dataclass
class CharacterState:
    agent_id: str
    name: str
    current_status: str = "active"
    background_summary: str = ""
    personality_traits: str = ""
    emotional_state: Optional[EmotionalState] = None
    skills: Dict[str, float] = field(default_factory=dict)
    relationships: Dict[str, float] = field(default_factory=dict)
    current_location: str = ""
    inventory: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
```

#### `MemoryItem`
```python
@dataclass
class MemoryItem:
    memory_id: str
    agent_id: str
    memory_type: MemoryType
    content: str
    emotional_intensity: float = 0.0  # 0.0 to 1.0
    relevance_score: float = 0.5      # 0.0 to 1.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    context_tags: List[str] = field(default_factory=list)
    associated_agents: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

---

## Configuration

### `OrchestratorConfig`
```python
@dataclass
class OrchestratorConfig:
    mode: OrchestratorMode = OrchestratorMode.AUTONOMOUS
    max_concurrent_agents: int = 10
    memory_cleanup_interval: int = 3600        # seconds
    template_cache_size: int = 100
    interaction_queue_size: int = 50
    equipment_maintenance_interval: int = 1800  # seconds
    health_check_interval: int = 300           # seconds
    auto_save_interval: int = 600              # seconds
    debug_logging: bool = False
    enable_metrics: bool = True
    enable_auto_backup: bool = True
    max_memory_items_per_agent: int = 10000
    performance_monitoring: bool = True
```

---

## Response Format

All API methods return a `StandardResponse` object:

```python
@dataclass
class StandardResponse:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[ErrorInfo] = None
    timestamp: datetime = field(default_factory=datetime.now)
```

**Success Response Example:**
```python
StandardResponse(
    success=True,
    message="Operation completed successfully",
    data={
        "agent_id": "agent_001",
        "memories_processed": 3,
        "interaction_id": "conv_20241209_143022"
    }
)
```

**Error Response Example:**
```python
StandardResponse(
    success=False,
    message="Agent not found",
    error=ErrorInfo(
        error_type="validation_error",
        error_code="AGENT_NOT_FOUND",
        details={"agent_id": "invalid_agent"}
    )
)
```

---

## Error Handling

### Common Error Types
- `validation_error` - Input validation failures
- `processing_error` - Processing operation failures
- `database_error` - Database operation issues
- `template_error` - Template rendering problems
- `interaction_error` - Character interaction failures
- `system_error` - System-level errors

### Error Codes
- `AGENT_NOT_FOUND` - Specified agent doesn't exist
- `MEMORY_CAPACITY_EXCEEDED` - Memory system capacity limits
- `TEMPLATE_RENDER_FAILED` - Template rendering errors
- `INTERACTION_PROCESSING_FAILED` - Interaction processing issues
- `DATABASE_CONNECTION_ERROR` - Database connectivity problems

---

## Performance Considerations

### Memory Management
- Working memory limited to 7±2 items per cognitive science principles
- Automatic memory cleanup based on relevance and access patterns
- LRU caching for frequently accessed memories

### Concurrency
- Full async/await support throughout the framework
- Configurable concurrent agent limits
- Database connection pooling

### Optimization Features
- Template caching system
- Memory consolidation algorithms
- Predictive equipment maintenance scheduling
- Real-time performance monitoring

---

## Integration Examples

### Basic Agent Setup
```python
import asyncio
from src.core.system_orchestrator import SystemOrchestrator
from src.core.data_models import CharacterState, MemoryItem, MemoryType

async def setup_basic_agent():
    # Initialize system
    orchestrator = SystemOrchestrator("data/my_app.db")
    await orchestrator.startup()
    
    # Create agent with character state
    character_state = CharacterState(
        agent_id="assistant_001",
        name="AI Assistant Alpha",
        background_summary="Helpful AI assistant specialized in data analysis",
        personality_traits="Analytical, helpful, detail-oriented"
    )
    
    result = await orchestrator.create_agent_context("assistant_001", character_state)
    return orchestrator, result

# Run setup
orchestrator, result = await setup_basic_agent()
```

### Multi-Agent Conversation
```python
async def multi_agent_discussion():
    # Orchestrate three-agent discussion
    result = await orchestrator.orchestrate_multi_agent_interaction(
        participants=["analyst_001", "researcher_002", "coordinator_003"],
        interaction_type=InteractionType.COOPERATION,
        context={
            "topic": "Quarterly analysis review",
            "location": "Virtual conference room",
            "urgency": "normal",
            "duration_minutes": 30
        }
    )
    
    if result.success:
        interaction_data = result.data
        print(f"Interaction completed with {interaction_data['phases_processed']} phases")
        print(f"Relationship changes: {interaction_data['relationship_changes']}")
    
    return result
```

This API documentation provides comprehensive coverage of the Dynamic Context Engineering Framework's capabilities, enabling developers to integrate and utilize the system effectively for intelligent agent applications.