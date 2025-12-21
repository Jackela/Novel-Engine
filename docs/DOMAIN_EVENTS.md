# Domain Event Catalog

## Overview
The Novel Engine uses an **Event-Driven Architecture (EDA)** facilitated by a central `EventBus`. This decoupled system allows different components (Narrative Engine, Orchestrator, Monitoring) to communicate via immutable events.

**Source Code Reference**: `src/core/event_bus.py`

## Event Structure
All events follow a standard envelope using `Event[T]` and `EventMetadata`.

```python
@dataclass
class EventMetadata:
    event_id: str
    timestamp: datetime
    source: str
    correlation_id: Optional[str]
    causation_id: Optional[str]
    priority: EventPriority
    delivery_mode: EventDeliveryMode
    retry_count: int
```

## System Events
Events related to the lifecycle and health of the Enhanced Orchestrator.

| Event Type | Payload Class | Description | Priority |
|:--- |:--- |:--- |:--- |
| `system.startup` | `SystemStartupEvent` | Emitted when the Enhanced Orchestrator completes initialization. | SYSTEM (4) |
| `system.shutdown` | `SystemShutdownEvent` | Emitted when the system begins graceful shutdown. | SYSTEM (4) |
| `system.health.changed` | `SystemHealthEvent` | Emitted when system health transitions (e.g., Optimal -> Degraded). | HIGH (2) |
| `system.metrics.collected` | `SystemMetricsEvent` | Periodic emission of performance metrics (CPU, DB, EventBus stats). | NORMAL (1) |

## Narrative Events (Planned)
*Future integration points for the Narrative Engine.*

| Event Type | Description |
|:--- |:--- |
| `narrative.turn.started` | A new narrative turn/cycle has begun. |
| `narrative.turn.completed` | A narrative turn has concluded. |
| `character.created` | A new agent/character context has been instantiated. |
| `interaction.processed` | An interaction between agents has been resolved. |

## Event Bus Features
- **Prioritization**: LOW, NORMAL, HIGH, CRITICAL, SYSTEM.
- **Reliability**: Dead Letter Queue (DLQ) for failed events.
- **Circuit Breakers**: Prevents cascading failures from bad handlers.
- **Event Sourcing**: In-memory `EventStore` supports replay capabilities.

## Usage Example

```python
from src.core.event_bus import get_event_bus, Event, EventMetadata

await get_event_bus().publish(
    Event(
        event_type="custom.event",
        payload={"data": "value"},
        metadata=EventMetadata(source="my_service")
    )
)
```