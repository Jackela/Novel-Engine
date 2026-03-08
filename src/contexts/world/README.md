# World Context

## Overview
The World Context manages the persistent game world state within the Novel Engine platform. It provides the spatial and temporal foundation for all narrative activities, tracking entities, locations, time, and environmental conditions.

This context implements the simulation backbone, handling entity placement, movement, time advancement, faction relations, and world evolution. It maintains consistency across all world-related data.

## Domain

### Aggregates
- **WorldState**: Root aggregate for world management
  - Entity management with spatial indexing
  - Calendar/time tracking
  - Environmental properties
  - Consistency enforcement
  - Snapshot/restore capabilities

### Entities
- **WorldEntity**: Individual entity within the world
  - Position (Coordinates)
  - Properties and metadata
  - Type: CHARACTER, OBJECT, LOCATION, ENVIRONMENT, ABSTRACT

### Value Objects
- **Coordinates**: Spatial positioning (x, y, z)
- **WorldCalendar**: In-game date/time
  - Year, month, day, era
  - Configurable days/month, months/year
  - `advance(days)` - Time progression
  - `from_datetime(dt)` - Migration helper
  
- **EntityType**: Classification enumeration
  - CHARACTER, OBJECT, LOCATION, ENVIRONMENT, ABSTRACT
  
- **WorldStatus**: World state enumeration
  - INITIALIZING, ACTIVE, PAUSED, ARCHIVED, ERROR

### Domain Events
- **WorldStateChanged**: Generic world change
  - **WorldChangeType**: ENTITY_ADDED, ENTITY_REMOVED, ENTITY_MOVED, ENTITY_UPDATED, STATE_SNAPSHOT, STATE_RESET, ENVIRONMENT_CHANGED, TIME_ADVANCED
  - Severity levels: MINOR, MODERATE, MAJOR, CRITICAL
  - Affected entity tracking
  - Cascade effects support
  
- Factory methods:
  - `entity_added()` - New entity in world
  - `entity_removed()` - Entity deleted
  - `entity_moved()` - Position changed
  - `entity_updated()` - Properties changed
  - `time_advanced()` - Calendar progression
  - `environment_changed()` - World conditions
  - `state_snapshot()` - Backup created
  - `state_reset()` - World reset

## Application

### Services
- **WorldSimulationService**: Main world operations
  - `create_world(name, config)` - Initialize world
  - `add_entity(world_id, entity_data)` - Add entity
  - `move_entity(world_id, entity_id, coordinates)` - Change position
  - `remove_entity(world_id, entity_id)` - Delete entity
  - `advance_time(world_id, days)` - Progress calendar
  - `get_entities_in_area(world_id, center, radius)` - Spatial query
  - `create_snapshot(world_id)` - Backup state

- **EventService**: World event management
  - `trigger_event(world_id, event_data)` - Spawn world event
  - `propagate_effects(world_id, source, radius)` - Cascade changes

- **FactionTickService**: Faction simulation
  - `process_faction_turn(world_id)` - Advance faction state
  - `update_relationships(world_id)` - Recalculate standings

- **TimeService**: Time management
  - `advance_time(world_id, days)` - Progress calendar
  - `get_current_time(world_id)` - Current date
  - `schedule_event(world_id, event, delay)` - Future events

- **GeopoliticsService**: Faction relations
  - `update_diplomacy(world_id)` - Relationship changes
  - `propagate_rumors(world_id)` - Information spread

- **RumorPropagationService**: Information diffusion
  - `propagate_rumor(world_id, rumor)` - Spread information
  - `decay_rumors(world_id)` - Age out old rumors

- **SocialGraphService**: Relationship tracking
  - `update_relationship(entity_a, entity_b, delta)` - Modify standing
  - `get_influence_network(entity_id)` - Social connections

### Commands
- **CreateWorld**: Initialize world
  - Handler: `CreateWorldHandler`
  
- **AddEntity**: Add to world
  - Handler: `AddEntityHandler`
  
- **MoveEntity**: Change position
  - Handler: `MoveEntityHandler`
  
- **AdvanceTime**: Progress calendar
  - Handler: `AdvanceTimeHandler`

### Queries
- **GetWorldState**: Complete world view
  - Handler: `GetWorldStateHandler`
  
- **GetEntitiesInArea**: Spatial query
  - Handler: `GetEntitiesInAreaHandler`
  
- **GetWorldTime**: Current date
  - Handler: `GetWorldTimeHandler`

## Infrastructure

### Repositories
- **WorldStateRepository**: World persistence
  - Implementation: PostgreSQL with JSONB for entities
  - Spatial indexing for location queries
  
- **EntityRepository**: Entity storage

### External Services
- None directly

## API

### REST Endpoints
- `POST /api/worlds` - Create world
- `GET /api/worlds/{id}` - Get world state
- `POST /api/worlds/{id}/entities` - Add entity
- `PUT /api/worlds/{id}/entities/{entity_id}/move` - Move entity
- `POST /api/worlds/{id}/time/advance` - Advance time
- `GET /api/worlds/{id}/entities` - Query entities

### WebSocket Events
- `world.entity_moved` - Real-time position updates
- `world.time_advanced` - Time progression

## Testing

### Running Tests
```bash
# Unit tests
pytest tests/contexts/world/unit/ -v

# Integration tests
pytest tests/contexts/world/integration/ -v

# All context tests
pytest tests/contexts/world/ -v
```

### Test Coverage
Current coverage: 75%
Target coverage: 85%

## Architecture Decision Records
- ADR-001: WorldState as aggregate for spatial consistency
- ADR-002: Spatial indexing for performance
- ADR-003: WorldCalendar for flexible time systems

## Integration Points

### Inbound
- Events consumed:
  - `CharacterCreated` from Character Context (auto-add to world)
  - `TurnExecutionStarted` from Orchestration Context (world update phase)

### Outbound
- Events published:
  - `WorldStateChanged` - For all dependent contexts
  - `EntityMoved` - For perception updates
  - `TimeAdvanced` - For scheduled events

### Dependencies
- **Domain**: None (pure domain)
- **Application**: Character Context (entity identities)
- **Infrastructure**: PostgreSQL

## Development Guide

### Adding New Features
1. Extend domain models (entity types, environment properties)
2. Add service methods
3. Update repository queries
4. Write tests

### Common Tasks
- **Adding entity types**: Extend `EntityType` enum
- **New spatial queries**: Update spatial index usage
- **Time system variants**: Extend `WorldCalendar` configuration

## Maintainer
Team: @world-team
Contact: world@example.com
