# Novel Engine API Reference

**Version**: 2.0.0  
**Last Updated**: 2024-11-04  
**Status**: Current  
**Audience**: Developers, Integration Teams

**Navigation**: [Home](../../README.md) > [Docs](../index.md) > [API](INDEX.md) > API Reference

---

## Overview

Novel Engine provides two complementary APIs:
1. **REST API** - HTTP endpoints for web/mobile applications
2. **Python Framework API** - Direct Python integration for advanced use cases

---

# Part 1: REST API

Production-ready HTTP/JSON API for managing characters, running story simulations, and monitoring system health.

## Base Configuration

**Base URL**: `http://localhost:8000`  
**Content Type**: `application/json`  
**API Base Path**: `/api`  
**Authentication**: None (JWT planned)

### Rate Limiting
- **Default**: 100 requests per minute per IP
- **Burst**: 200 requests in 5-minute window
- **Story Generation**: 5 concurrent simulations per user

### Versioning & Stability
The product API uses a single stable path (`/api/*`). Breaking changes require an explicit migration plan.

---

## REST Endpoints

### System Health & Monitoring

#### `GET /health`
System health check for monitoring and load balancers.

**Response** (200 OK):
```json
{
  "api": "healthy" | "degraded" | "error",
  "config": "loaded" | "error",
  "version": "1.0.0",
  "timestamp": "2025-08-12T10:30:00Z",
  "uptime_seconds": 3600
}
```

**Status Codes**:
- `200` - System healthy
- `503` - System degraded/unavailable

---

#### `GET /meta/system-status`
Detailed system metrics and performance data.

**Response**:
```json
{
  "api": "healthy",
  "config": "loaded",
  "version": "1.0.0",
  "performance": {
    "avg_response_time_ms": 150,
    "cache_hit_rate": 0.89,
    "active_connections": 12,
    "memory_usage_mb": 512,
    "cpu_usage_percent": 25.6
  },
  "features": {
    "character_generation": true,
    "story_simulation": true,
    "caching_enabled": true
  }
}
```

---

#### `GET /meta/policy`
Returns the current operational policy of the Engine.

**Response** (200 OK):
```json
{
  "mode": "neutral",
  "monetization": "disabled",
  "provenance_required": true
}
```

---

### Character Management

#### `GET /characters`
Retrieve all character names or full character list.

**Response**:
```json
{
  "characters": ["krieg", "isabella_varr", "ork_warboss"],
  "count": 3,
  "timestamp": "2025-08-12T10:30:00Z"
}
```

---

#### `GET /characters/{character_name}`
Get detailed character information.

**Parameters**:
- `character_name` (string, required) - URL-encoded character name

**Response** (200 OK):
```json
{
  "character_name": "krieg",
  "narrative_context": "A battle-hardened soldier...",
  "structured_data": {
    "combat_stats": {
      "strength": 8,
      "dexterity": 6,
      "intelligence": 7,
      "perception": 9
    },
    "equipment": {
      "primary_weapon": "Lasgun",
      "armor": "Flak Armor"
    },
    "psychological_profile": {
      "loyalty": 10,
      "morale": 8
    }
  },
  "creation_date": "2025-08-10T15:20:00Z"
}
```

**Status Codes**:
- `200` - Character found
- `404` - Character not found
- `400` - Invalid character name

---

#### `POST /characters`
Create a new character with multipart form data.

**Content-Type**: `multipart/form-data`

**Form Fields**:
- `name` (string, required) - Character name (3-50 characters)
- `description` (string, required) - Character description (10-2000 characters)
- `files` (file[], optional) - Supporting files (max 5 files, 10MB total)

**Validation Rules**:
- Character names must be unique
- Allowed file types: .txt, .md, .json, .yaml

**Response** (201 Created):
```json
{
  "success": true,
  "character": {
    "name": "new_character",
    "creation_status": "processing",
    "estimated_completion": "2025-08-12T10:35:00Z"
  },
  "message": "Character creation initiated successfully"
}
```

**Status Codes**:
- `201` - Character creation started
- `400` - Invalid input data
- `409` - Character name already exists
- `413` - File size too large

---

### Story Simulation

#### `POST /simulations`
Run a story simulation with specified characters.

**Request Body**:
```json
{
  "character_names": ["krieg", "ork_warboss"],
  "turns": 5,
  "narrative_style": "action",
  "scenario": "optional scenario description",
  "constraints": {
    "max_words_per_turn": 200,
    "tone": "dark",
    "perspective": "third_person"
  }
}
```

**Validation Rules**:
- 2-6 characters per simulation
- 3-20 turns maximum
- All characters must exist in system

**Response** (201 Created):
```json
{
  "simulation_id": "sim_1234567890",
  "status": "completed",
  "participants": ["krieg", "ork_warboss"],
  "turns_executed": 5,
  "story": "The battlefield stretched endlessly...",
  "metadata": {
    "word_count": 1247,
    "generation_time_seconds": 45.2,
    "quality_score": 0.87
  },
  "created_at": "2025-08-12T10:30:00Z"
}
```

**Status Codes**:
- `201` - Simulation started
- `400` - Invalid parameters
- `404` - Character not found
- `429` - Rate limit exceeded

---

#### `POST /simulations/run`
Initiates a simulation from a predefined seed scenario.

**Request Body**:
```json
{
  "seed_id": "string",
  "steps": 10
}
```

**Response** (202 Accepted):
```json
{
  "run_id": "string"
}
```

**Error Codes**:
- `400` - Malformed request or invalid steps
- `404` - Seed ID not found

---

#### `POST /simulations/{run_id}/turn`
Submits character actions for a specific turn.

**Request Body**: `List[CharacterAction]` (see Schemas)

**Response** (200 OK):
```json
{
  "world": {},
  "log_id": "string"
}
```

**Error Codes**:
- `422` - Invalid action schema
- `409` - Adjudication rejected actions (see Iron Laws)
- `404` - Run ID not found

**Adjudication Error Codes**:
- `E001_RESOURCE_NEGATIVE` - Resource conservation violation
- `E002_TARGET_INVALID` - Information limit violation
- `E003_ACTION_IMPOSSIBLE` - State consistency violation
- `E004_LOGIC_VIOLATION` - Rule adherence violation
- `E005_CANON_BREACH` - Canon preservation violation

---

#### `GET /simulations/{simulation_id}`
Get simulation status and results.

**Response**:
```json
{
  "simulation_id": "sim_1234567890",
  "status": "completed",
  "progress": 100,
  "estimated_remaining_seconds": 0,
  "story": "...",
  "error": null
}
```

---

#### `POST /chronicle`
Generate a narrative chronicle from a completed simulation.

**Request Body**:
```json
{
  "run_id": "string"
}
```

**Response** (200 OK): `ChronicleSpec` object

**Error Codes**:
- `404` - Run ID not found or incomplete

---

### Campaign Management

#### `GET /campaigns`
List all campaigns (story collections).

**Response**:
```json
{
  "campaigns": ["default", "warhammer_40k", "custom"],
  "count": 3
}
```

---

#### `POST /campaigns`
Create a new campaign.

**Request Body**:
```json
{
  "campaign_name": "my_campaign",
  "description": "Campaign description"
}
```

**Response** (201 Created):
```json
{
  "success": true,
  "campaign": {
    "name": "my_campaign",
    "created_at": "2025-08-12T10:30:00Z"
  }
}
```

---

## REST API Data Models

### Character Stats Schema
```json
{
  "strength": 1-10,
  "dexterity": 1-10,
  "intelligence": 1-10,
  "willpower": 1-10,
  "perception": 1-10,
  "charisma": 1-10
}
```

### Equipment Schema
```json
{
  "id": "unique_identifier",
  "name": "Equipment Name",
  "type": "weapon" | "armor" | "tool" | "special",
  "condition": 0.0-1.0,
  "properties": {}
}
```

---

## REST API Error Responses

All errors follow this format:
```json
{
  "error": true,
  "error_code": "VALIDATION_ERROR",
  "message": "Human-readable error message",
  "details": {
    "field": "specific field with error",
    "received": "actual value received",
    "expected": "expected format or constraint"
  },
  "timestamp": "2025-08-12T10:30:00Z",
  "request_id": "req_1234567890"
}
```

### Error Codes
- `VALIDATION_ERROR` - Input validation failed
- `RESOURCE_NOT_FOUND` - Requested resource doesn't exist
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `SYSTEM_UNAVAILABLE` - Service temporarily unavailable
- `INTERNAL_ERROR` - Unexpected server error

---

# Part 2: Python Framework API

Advanced Python API for direct integration with the Dynamic Context Engineering Framework.

## Core Components

### 1. System Orchestrator

Central coordination system managing all framework components.

#### `SystemOrchestrator`

```python
class SystemOrchestrator:
    def __init__(self, database_path: str, config: Optional[OrchestratorConfig] = None)
    
    async def startup() -> StandardResponse
    async def shutdown() -> StandardResponse
    
    # Agent Management
    async def create_agent_context(
        agent_id: str, 
        initial_state: Optional[CharacterState] = None
    ) -> StandardResponse
    
    # Context Processing
    async def process_dynamic_context(
        context: DynamicContext
    ) -> StandardResponse
    
    # Multi-Agent Interactions
    async def orchestrate_multi_agent_interaction(
        participants: List[str], 
        interaction_type: InteractionType = InteractionType.DIALOGUE,
        context: Optional[Dict[str, Any]] = None
    ) -> StandardResponse
    
    # System Monitoring
    async def get_system_metrics() -> StandardResponse
```

**Example Usage**:
```python
from src.core.system_orchestrator import SystemOrchestrator

orchestrator = SystemOrchestrator("data/my_project.db")
await orchestrator.startup()

result = await orchestrator.create_agent_context("agent_001")
```

---

### 2. Multi-Layer Memory System

Advanced memory management with cognitive science foundations.

#### `LayeredMemorySystem`

```python
class LayeredMemorySystem:
    def __init__(
        self, 
        agent_id: AgentID, 
        database: ContextDatabase,
        working_capacity: int = 7,
        episodic_max: int = 1000,
        semantic_max: int = 5000,
        emotional_max: int = 500
    )
    
    # Memory Operations
    async def store_memory(memory_item: MemoryItem) -> StandardResponse
    async def retrieve_memories(query: MemoryQueryRequest) -> StandardResponse
    async def update_memory(memory_id: str, updates: Dict[str, Any]) -> StandardResponse
    async def delete_memory(memory_id: str) -> StandardResponse
    
    # Advanced Operations
    async def get_working_memory_context() -> StandardResponse
    async def consolidate_memories() -> StandardResponse
    async def get_memory_statistics() -> StandardResponse
```

**Memory Types**:
- **Working Memory**: Current focus (7±2 capacity)
- **Episodic Memory**: Event-based with temporal context
- **Semantic Memory**: Knowledge and facts
- **Emotional Memory**: Emotionally-charged memories

**Example**:
```python
from src.core.data_models import MemoryItem, MemoryType

memory = MemoryItem(
    memory_id="task_001",
    agent_id="agent_001",
    memory_type=MemoryType.EPISODIC,
    content="Completed analysis with 95% accuracy",
    emotional_intensity=0.7,
    relevance_score=0.9,
    context_tags=["task", "analysis"]
)

memory_system = LayeredMemorySystem("agent_001", database)
await memory_system.store_memory(memory)
```

---

### 3. Dynamic Template Engine

Context-aware content generation with Jinja2 integration.

#### `DynamicTemplateEngine`

```python
class DynamicTemplateEngine:
    def __init__(
        self, 
        template_dir: Path, 
        memory_query_engine: MemoryQueryEngine
    )
    
    async def render_template(
        template_id: str, 
        context: TemplateContext,
        enable_memory_queries: bool = True,
        enable_cross_references: bool = True
    ) -> StandardResponse
    
    async def register_template(
        template_id: str, 
        template_content: str
    ) -> StandardResponse
    
    async def list_templates() -> StandardResponse
    async def validate_template(template_content: str) -> StandardResponse
```

---

### 4. Character Interaction System

Multi-character interactions with relationship dynamics.

#### `CharacterInteractionProcessor`

```python
class CharacterInteractionProcessor:
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
    async def get_relationship_status(
        character_a: str, 
        character_b: str
    ) -> StandardResponse
    
    # Conflict Resolution
    async def resolve_conflict(
        conflicted_characters: List[str], 
        conflict_type: str = "disagreement",
        mediator: Optional[str] = None
    ) -> StandardResponse
```

**Interaction Types**:
- `DIALOGUE` - Conversational interactions
- `COMBAT` - Conflict situations
- `COOPERATION` - Collaborative activities
- `NEGOTIATION` - Diplomatic exchanges
- `RITUAL` - Ceremonial interactions
- `INSTRUCTION` - Teaching/learning scenarios
- `EMERGENCY` - Crisis situations

---

### 5. Dynamic Equipment System

Real-time equipment state management.

#### `DynamicEquipmentSystem`

```python
class DynamicEquipmentSystem:
    # Equipment Management
    async def create_equipment(equipment_data: EquipmentItem) -> StandardResponse
    async def get_equipment_status(equipment_id: str) -> StandardResponse
    async def update_equipment_condition(
        equipment_id: str, 
        new_condition: str
    ) -> StandardResponse
    
    # Usage Tracking
    async def use_equipment(
        equipment_id: str, 
        agent_id: str,
        usage_context: Dict[str, Any],
        expected_duration: int = 60
    ) -> StandardResponse
    
    # Maintenance
    async def schedule_maintenance(
        equipment_id: str, 
        maintenance_type: str
    ) -> StandardResponse
    
    # Agent Equipment
    async def assign_equipment_to_agent(
        equipment_id: str, 
        agent_id: str
    ) -> StandardResponse
    async def get_agent_equipment(agent_id: str) -> StandardResponse
```

---

## Python API Data Models

### DynamicContext
```python
@dataclass
class DynamicContext:
    agent_id: str
    timestamp: datetime
    character_state: Optional[CharacterState]
    memory_context: List[MemoryItem]
    environmental_context: Optional[EnvironmentalState]
```

### CharacterState
```python
@dataclass
class CharacterState:
    agent_id: str
    name: str
    current_status: str
    background_summary: str
    personality_traits: str
    emotional_state: Optional[EmotionalState]
    skills: Dict[str, float]
    relationships: Dict[str, float]
    current_location: str
    inventory: List[str]
    metadata: Dict[str, Any]
```

### MemoryItem
```python
@dataclass
class MemoryItem:
    memory_id: str
    agent_id: str
    memory_type: MemoryType
    content: str
    emotional_intensity: float  # 0.0 to 1.0
    relevance_score: float      # 0.0 to 1.0
    access_count: int
    last_accessed: Optional[datetime]
    context_tags: List[str]
    associated_agents: List[str]
    metadata: Dict[str, Any]
```

---

## Python API Response Format

All methods return `StandardResponse`:

```python
@dataclass
class StandardResponse:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[ErrorInfo] = None
    timestamp: datetime = field(default_factory=datetime.now)
```

**Success Example**:
```python
StandardResponse(
    success=True,
    message="Operation completed",
    data={"agent_id": "agent_001", "memories_processed": 3}
)
```

**Error Example**:
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

## Configuration

### OrchestratorConfig
```python
@dataclass
class OrchestratorConfig:
    mode: OrchestratorMode = OrchestratorMode.AUTONOMOUS
    max_concurrent_agents: int = 10
    memory_cleanup_interval: int = 3600  # seconds
    template_cache_size: int = 100
    debug_logging: bool = False
    enable_metrics: bool = True
```

---

## Performance Guidelines

### REST API Performance
- Health checks: < 50ms
- Character queries: < 200ms
- Story generation: 30-180 seconds

### Python API Performance
- Working memory: 7±2 items (cognitive science)
- Automatic memory cleanup based on relevance
- LRU caching for frequent access
- Full async/await support
- Database connection pooling

### Caching
- Character data: 5 minutes
- System status: 30 seconds
- Story results: 24 hours
- Template cache: 100 templates

---

## Integration Examples

### REST API Integration (JavaScript)
```javascript
// Fetch character
const response = await fetch('http://localhost:8000/characters/krieg');
const character = await response.json();

// Run simulation
const simulation = await fetch('http://localhost:8000/simulations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    character_names: ['krieg', 'ork_warboss'],
    turns: 5,
    narrative_style: 'action'
  })
});
```

### Python API Integration
```python
import asyncio
from src.core.system_orchestrator import SystemOrchestrator
from src.core.data_models import CharacterState

async def setup_agent():
    orchestrator = SystemOrchestrator("data/app.db")
    await orchestrator.startup()
    
    character_state = CharacterState(
        agent_id="agent_001",
        name="AI Assistant",
        background_summary="Helpful assistant",
        personality_traits="Analytical, helpful"
    )
    
    result = await orchestrator.create_agent_context(
        "agent_001", 
        character_state
    )
    return orchestrator, result

orchestrator, result = await setup_agent()
```

---

## See Also

- [Core Systems Integration Guide](../guides/CORE_SYSTEMS_INTEGRATION_GUIDE.md)
- [Data Schemas](./schemas.md)
- [OpenAPI Snapshot](./openapi.json)

---

**Last Updated**: 2024-11-04  
**Maintained by**: Novel Engine Development Team  
**License**: MIT
