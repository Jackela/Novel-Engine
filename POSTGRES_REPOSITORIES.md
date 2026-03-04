# PostgreSQL Repositories Implementation

This document describes the PostgreSQL repository implementations for the Novel Engine project.

## Overview

Two PostgreSQL repository adapters have been implemented following Hexagonal Architecture principles:

1. **PostgreSQLEventRepository** - Persists `HistoryEvent` entities
2. **PostgreSQLRumorRepository** - Persists `Rumor` entities

## Files Created

### Migration
- `migrations/V007__add_events_rumors_tables.sql` - Database schema for events and rumors tables

### Repository Implementations
- `src/contexts/world/infrastructure/persistence/postgres_event_repository.py`
- `src/contexts/world/infrastructure/persistence/postgres_rumor_repository.py`

### Integration Tests
- `tests/integration/persistence/test_postgres_event_repository.py`
- `tests/integration/persistence/test_postgres_rumor_repository.py`

### Updated Files
- `src/contexts/world/infrastructure/persistence/__init__.py` - Added exports for new repositories
- `tests/integration/persistence/__init__.py` - New test package

## PostgreSQLEventRepository

### Methods
- `get_by_id(event_id: str) -> HistoryEvent | None` - Retrieve event by ID
- `get_by_world_id(world_id: str, limit: int = 100, offset: int = 0) -> List[HistoryEvent]` - Get events for a world
- `save(event: HistoryEvent) -> HistoryEvent` - Save or update an event
- `save_all(events: List[HistoryEvent]) -> List[HistoryEvent]` - Batch save with transactions
- `delete(event_id: str) -> bool` - Delete an event
- `get_by_location_id(location_id: str) -> List[HistoryEvent]` - Get events at a location
- `get_by_faction_id(faction_id: str) -> List[HistoryEvent]` - Get events involving a faction
- `clear() -> None` - Clear all events (testing utility)

### Features
- UPSERT support for create/update operations
- UUID array support for relationships (location_ids, faction_ids, etc.)
- Enum type preservation (EventType, EventSignificance, EventOutcome, ImpactScope)
- JSONB support for structured_date (WorldCalendar)
- Transaction support for batch operations

## PostgreSQLRumorRepository

### Methods
- `get_by_id(rumor_id: str) -> Rumor | None` - Retrieve rumor by ID
- `get_active_rumors(world_id: str) -> List[Rumor]` - Get rumors with truth_value > 0
- `get_by_world_id(world_id: str) -> List[Rumor]` - Get all rumors for a world
- `save(rumor: Rumor) -> Rumor` - Save or update a rumor
- `save_all(rumors: List[Rumor]) -> List[Rumor]` - Batch save with transactions
- `delete(rumor_id: str) -> bool` - Delete a rumor
- `get_by_location_id(location_id: str) -> List[Rumor]` - Get rumors at a location
- `get_by_event_id(event_id: str) -> List[Rumor]` - Get rumors from an event
- `clear() -> None` - Clear all rumors (testing utility)

### Features
- UPSERT support for create/update operations
- Set type preservation for current_locations
- Enum type preservation (RumorOrigin)
- JSONB support for created_date (WorldCalendar)
- Foreign key support for source_event_id
- Transaction support for batch operations

## Database Schema

### history_events table
```sql
CREATE TABLE history_events (
    id UUID PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    description TEXT,
    event_type VARCHAR(50) NOT NULL,
    significance VARCHAR(50) NOT NULL,
    outcome VARCHAR(50) DEFAULT 'neutral',
    date_description VARCHAR(200) NOT NULL,
    -- ... additional fields
);
```

### rumors table
```sql
CREATE TABLE rumors (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    truth_value INTEGER NOT NULL CHECK (truth_value >= 0 AND truth_value <= 100),
    origin_type VARCHAR(50) NOT NULL,
    source_event_id UUID REFERENCES history_events(id),
    origin_location_id UUID NOT NULL,
    current_locations UUID[] NOT NULL DEFAULT '{}',
    -- ... additional fields
);
```

## Indexes

### history_events
- `idx_history_events_type` - For filtering by event type
- `idx_history_events_significance` - For filtering by significance
- `idx_history_events_location_ids` - GIN index for location lookups
- `idx_history_events_faction_ids` - GIN index for faction lookups
- `idx_history_events_narrative_importance` - For importance sorting
- `idx_history_events_is_secret` - For secret event queries

### rumors
- `idx_rumors_origin_location` - For world-based queries
- `idx_rumors_truth_value` - For truth value sorting
- `idx_rumors_active` - Partial index for active rumors (truth > 0)
- `idx_rumors_current_locations` - GIN index for location lookups
- `idx_rumors_source_event` - For event-based lookups

## Usage

```python
import asyncpg
from src.contexts.world.infrastructure.persistence import PostgreSQLEventRepository, PostgreSQLRumorRepository

# Create connection pool
pool = await asyncpg.create_pool("postgresql://user:pass@localhost/db")

# Create repositories
event_repo = PostgreSQLEventRepository(pool)
rumor_repo = PostgreSQLRumorRepository(pool)

# Use repositories
from src.contexts.world.domain.entities import HistoryEvent, Rumor

event = HistoryEvent.create_war(name="Battle", ...)
await event_repo.save(event)

retrieved = await event_repo.get_by_id(event.id)
```

## Testing

Integration tests require a running PostgreSQL database:

```bash
# Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=novel_engine_test
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password

# Run integration tests
pytest tests/integration/persistence/ -v
```

For unit tests without PostgreSQL, use the InMemory implementations:
```python
from src.contexts.world.infrastructure.persistence import (
    InMemoryEventRepository,
    InMemoryRumorRepository
)
```

## Architecture Compliance

These implementations follow the Hexagonal Architecture principles:
- **Domain Layer**: Repository interfaces (ports) remain pure and database-agnostic
- **Infrastructure Layer**: PostgreSQL adapters implement the port interfaces
- **Dependency Inversion**: Domain depends on abstractions, not concrete implementations
- **Testability**: Both InMemory and PostgreSQL implementations can be used interchangeably
