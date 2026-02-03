# World Context Architecture

This document describes the World Bounded Context following Hexagonal Architecture (Ports & Adapters) principles.

## Layer Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        DOMAIN LAYER                              │
│  (Business Rules, Entities, Aggregates, Value Objects)          │
├─────────────────────────────────────────────────────────────────┤
│                      APPLICATION LAYER                           │
│  (Use Cases, Commands, Queries, Ports)                          │
├─────────────────────────────────────────────────────────────────┤
│                     INFRASTRUCTURE LAYER                         │
│  (Adapters: Persistence, LLM Generators, Projections)           │
└─────────────────────────────────────────────────────────────────┘
```

## Domain Layer (`domain/`)

The innermost layer containing pure business logic. No external dependencies.

### Aggregates (`aggregates/`)

- **WorldState**: The aggregate root for runtime world simulation. Maintains consistency boundaries for entities, coordinates, and spatial indexing during gameplay.

### Entities (`entities/`)

Domain entities representing world lore concepts:

| Entity | Purpose |
|--------|---------|
| `WorldSetting` | Core world configuration (genre, era, tone, magic/tech levels) |
| `Faction` | Political/social groups with alignment, influence, territories |
| `Location` | Places with climate, resources, connections, population |
| `HistoryEvent` | Historical events linking factions and locations |

### Value Objects (`value_objects/`)

- **Coordinates**: Immutable 3D position with distance calculations

### Events (`events/`)

- **WorldStateChanged**: Domain event for tracking all world state mutations (entity added/removed/moved/updated, time advanced, environment changed)

### Repositories (`repositories/`)

Repository interfaces (Ports) for persistence:

- **WorldStateRepository**: Interface for WorldState aggregate persistence

## Application Layer (`application/`)

Orchestrates domain logic. Contains use cases, commands, and port definitions.

### Ports (`ports/`)

Interfaces for external dependencies (Dependency Inversion):

| Port | Purpose |
|------|---------|
| `WorldGeneratorPort` | Protocol for world lore generation |
| `WorldGenerationInput` | Immutable input DTO for generation |
| `WorldGenerationResult` | Immutable output DTO with generated entities |

### Commands (`commands/`)

Write operations following CQRS pattern:

- `world_commands.py`: Command definitions
- `handlers.py`: Command handlers coordinating domain logic

### Use Cases (`use_cases/`)

Application-specific business rules:

- `update_world_state_uc.py`: Use case for updating world state

### Queries (`queries/`)

Read operations (queries are in infrastructure for now):

- Query interfaces defined here, implementations in infrastructure

## Infrastructure Layer (`infrastructure/`)

Adapters implementing ports for external concerns.

### Generators (`generators/`)

| Adapter | Implements | Description |
|---------|------------|-------------|
| `LLMWorldGenerator` | `WorldGeneratorPort` | Gemini-based world lore generation |

**Self-Correction Retry Mechanism** (in `LLMWorldGenerator`):

The generator employs a multi-stage JSON extraction strategy:
1. Direct JSON parsing attempt
2. Markdown code block extraction (`\`\`\`json ... \`\`\``)
3. Embedded JSON object detection (find `{` to `}`)

If parsing fails at all stages, the result is wrapped in an error result with a descriptive message, preserving the original request parameters.

### Persistence (`persistence/`)

| Adapter | Purpose |
|---------|---------|
| `models.py` | SQLAlchemy ORM models |
| `postgres_world_state_repo.py` | PostgreSQL implementation of WorldStateRepository |

### Projections (`projections/`)

Read model projections for query optimization:

- `world_read_model.py`: Read-optimized world state views
- `world_projector.py`: Event handlers updating read models

### Queries (`queries/`)

Query implementations:

- `world_queries.py`: SQL-based query implementations

## Dependency Rules

```
ALLOWED:
  Domain ← Application ← Infrastructure

FORBIDDEN:
  Domain → Application (Domain knows nothing of Application)
  Domain → Infrastructure (Domain knows nothing of adapters)
  Application → Infrastructure (except through Ports)
```

## Relationship Mapping

Entities maintain cross-references using UUID strings:

```
WorldSetting
    │
    ├── has many → Faction
    │                 │
    │                 ├── headquarters_id → Location
    │                 └── territories[] → Location[]
    │
    ├── has many → Location
    │                 │
    │                 ├── parent_location_id → Location
    │                 ├── child_location_ids[] → Location[]
    │                 └── connections[] → Location[]
    │
    └── has many → HistoryEvent
                      │
                      ├── location_ids[] → Location[]
                      ├── faction_ids[] → Faction[]
                      ├── preceding_event_ids[] → HistoryEvent[]
                      ├── following_event_ids[] → HistoryEvent[]
                      └── related_event_ids[] → HistoryEvent[]
```

## LLM Generation Flow

```
1. WorldGenerationInput (Application Port)
        │
        ▼
2. LLMWorldGenerator.generate() (Infrastructure Adapter)
        │
        ├── _load_system_prompt() ← YAML template
        ├── _build_user_prompt() ← Parameter interpolation
        ├── _call_gemini() ← HTTP to Gemini API
        ├── _extract_json() ← Multi-strategy JSON extraction
        └── _build_result() ← Entity construction with ID resolution
        │
        ▼
3. WorldGenerationResult (Application Port)
        │
        ├── WorldSetting (Domain Entity)
        ├── List[Faction] (Domain Entities)
        ├── List[Location] (Domain Entities)
        └── List[HistoryEvent] (Domain Entities)
```

## Temporary ID Resolution

During LLM generation, the model produces temporary IDs for cross-references:

| Phase | ID Format | Example |
|-------|-----------|---------|
| LLM Output | `temp_id` strings | `temp_faction_1`, `temp_location_1` |
| Build Phase | UUID assignment | `550e8400-e29b-41d4-a716-446655440000` |
| Resolution | ID map lookup | `temp_faction_1` → `550e8400-...` |

The resolution order is critical:
1. **Locations first** (factions reference them)
2. **Factions second** (events reference them)
3. **Events third** (events reference each other)

## Error Handling

Errors are handled via Result pattern at the application layer:

- Generator failures return `WorldGenerationResult` with error state `WorldSetting`
- All errors are logged via `structlog` with structured JSON
- Original request parameters are preserved in error results for debugging

## Testing Strategy

| Layer | Test Type | Location |
|-------|-----------|----------|
| Domain | Unit Tests | `tests/unit/contexts/world/domain/` |
| Application | Integration Tests | `tests/integration/contexts/world/` |
| Infrastructure | Integration Tests | `tests/integration/contexts/world/` |
| Full Stack | E2E Tests | `tests/e2e/` |
