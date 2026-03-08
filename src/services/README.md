# Services Module

## Purpose
Shared domain services used across multiple contexts. Provides high-level orchestration that bridges the REST API (Imperative Shell) and the core system (Functional Core).

This module coordinates multi-agent interactions, simulation management, and narrative generation through an async service layer.

## Components

### ApiOrchestrationService
Main service for managing simulation lifecycles.

**File:** `src/services/api_service.py`

Bridges the REST API with the SystemOrchestrator, handling:
- Simulation initialization
- Background execution
- Pause/resume/stop operations
- SSE event broadcasting
- Narrative generation

```python
from src.services import ApiOrchestrationService
from src.core.system_orchestrator import SystemOrchestrator
from src.core.event_bus import EventBus

# Initialize
orchestrator = SystemOrchestrator()
event_bus = EventBus()
service = ApiOrchestrationService(
    orchestrator=orchestrator,
    event_bus=event_bus
)

# Start simulation
result = await service.start_simulation(
    SimulationRequest(
        character_names=["Alice", "Bob"],
        turns=5
    )
)

# Check status
status = await service.get_status()

# Get generated narrative
narrative = await service.get_narrative()

# Control execution
await service.pause_simulation()
await service.stop_simulation()
```

#### Methods

**start_simulation(request: SimulationRequest) -> Dict[str, Any]**
- Starts a new simulation in the background
- Creates agents from character names
- Launches async orchestration loop
- Raises: ValueError if simulation already running

**stop_simulation() -> Dict[str, Any]**
- Stops the current simulation
- Sets stop flag for graceful termination
- Returns: Success status and message

**pause_simulation() -> Dict[str, Any]**
- Pauses the current simulation
- Simulation can be resumed by starting again
- Returns: Success status and message

**get_status() -> Dict[str, Any]**
- Returns current orchestration status
- Includes: current_turn, total_turns, queue_length, status

**get_narrative() -> Dict[str, Any]**
- Returns generated narrative content
- Includes: story text, participants, log path

## Architecture

```
┌─────────────────┐
│   REST API      │  ← FastAPI routes
│   (api_server)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ApiOrchestration│  ← This module
│    Service      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ SystemOrchestrator│ ← Core orchestration
│   (Functional)  │
└─────────────────┘
```

## State Management

The service maintains internal state for API compatibility:

```python
self._state = {
    "current_turn": 0,
    "total_turns": 0,
    "queue_length": 0,
    "average_processing_time": 0.0,
    "status": "idle",  # idle, running, paused, stopping, completed, error
    "steps": [],
    "last_updated": None,
}

self._narrative = {
    "story": "",
    "log_path": "",
    "participants": [],
    "turns_completed": 0,
    "last_generated": None,
}
```

## SSE Broadcasting

The service broadcasts events via the EventBus for real-time UI updates:

```python
await self._broadcast_sse(
    event_type="story",      # system, story, character
    title="Turn 1 Started",
    description="Beginning turn processing",
    severity="low"           # low, medium, high
)
```

Events are published to the `dashboard_event` topic.

## Execution Flow

1. **Initialization**
   - Create character agents from names
   - Setup DirectorAgent
   - Initialize ChroniclerAgent

2. **Turn Loop**
   - Check stop/pause flags
   - Execute director.run_turn()
   - Record timing metrics
   - Broadcast progress events

3. **Finalization**
   - Generate narrative via Chronicler
   - Update final status
   - Broadcast completion

## Testing

```bash
pytest tests/services/ -v
```

## Integration

This module is used by:
- **API Layer**: `api_server.py` routes
- **CLI Tools**: Command-line simulation runners
- **Background Jobs**: Async processing workers

## Future Enhancements

- WebSocket support for real-time updates
- Simulation persistence and resume
- Multi-campaign management
- Simulation replay capabilities
- Custom agent injection

## Related Components

- **DirectorAgent**: Turn-by-turn orchestration (in `src/agents/`)
- **ChroniclerAgent**: Narrative generation (in `src/agents/`)
- **CharacterFactory**: Agent creation (in `src/config/`)
- **SystemOrchestrator**: Core orchestration (in `src/core/`)
