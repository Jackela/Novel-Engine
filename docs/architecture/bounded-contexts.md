# Bounded Contexts - Novel Engine

**Constitution Reference**: Article I - Domain-Driven Design (DDD) is Law  
**Version**: 2.0.0  
**Last Updated**: 2025-11-04

## Overview

Novel Engine employs Domain-Driven Design (DDD) with explicit Bounded Contexts to ensure business logic purity and maintain clear architectural boundaries. Each bounded context represents a cohesive domain area with its own ubiquitous language, models, and business rules.

## Core Principle (Article I)

> **The Domain layer MUST be pure, containing only business rules and domain state, with NO dependencies on infrastructure (databases, APIs, or frameworks).**

## Bounded Contexts Catalog

| Context | Purpose | Primary Aggregates | Ports | Status |
|---------|---------|-------------------|-------|--------|
| **Character** | Character creation, persona management, trait modeling | Character, Persona, CharacterStats | ICharacterRepository, IPersonaGenerator | Active |
| **World** | World building, setting management, environmental state | World, Setting, WorldState | IWorldRepository, IWorldEventPublisher | Active |
| **Narrative** | Story generation, plot management, narrative coherence | Story, Plot, Scene, NarrativeArc | IStoryRepository, ILLMService | Active |
| **Simulation Orchestration** | Campaign lifecycle and turn execution | Campaign, Turn Ledger | ICampaignRepository, ITurnOrchestrator | Active |
| **Persona Intelligence** | Persona decisions and AI integration | Persona module | IPersonaAI, IPersonaRepository | Active |
| **Narrative Delivery** | Transform events into published narratives | Narrative Chronicle, Media Asset | IMediaPublisher, IChronicleRepository | Active |
| **Platform/Accelerators** | Cross-cutting capabilities (cache, metrics, logs) | CacheEntry, Tag, Namespace | ICacheRepository, IMetricsCollector | Active |

## Shared Vocabulary (Ubiquitous Language)

### Domain-Driven Design Terms
- **Bounded Context**: Cohesive domain area with explicit boundaries and ubiquitous language
- **Aggregate**: Consistent unit of change guarded by domain invariants and business rules
- **Domain Model**: Pure business logic with ZERO infrastructure dependencies
- **Value Object**: Immutable object defined by its attributes (e.g., CharacterId, Timestamp)
- **Domain Event**: Business event representing state change within bounded context
- **Domain Service**: Business logic that doesn't belong to a single entity

### Hexagonal Architecture Terms (Article II)
- **Port**: Interface (abstraction) exposed by domain/application layer for external concerns
- **Adapter**: Concrete implementation binding a port to infrastructure (databases, APIs, frameworks)
- **Anti-Corruption Layer (ACL)**: Translation boundary to legacy or third-party systems (e.g., Gemini API, OpenAI)
- **Dependency Inversion**: Domain depends on abstractions (ports), infrastructure provides implementations (adapters)

### Event-Driven Architecture Terms (Article VI)
- **Domain Event**: Published when aggregate state changes (e.g., CharacterCreated, PlotGenerated)
- **Event Bus**: Kafka-based asynchronous communication channel between bounded contexts
- **Event Subscription**: Context subscribing to domain events from other contexts
- **Eventual Consistency**: Consistency achieved asynchronously via event propagation

## Architecture Layers (Article II - Ports & Adapters)

```
Bounded Context Structure:
contexts/[context-name]/
├── domain/              # Pure business logic (Article I - ZERO infrastructure)
│   ├── models/          # Domain entities, aggregates, value objects
│   ├── services/        # Domain services for cross-entity business logic
│   └── events/          # Domain events (business state changes)
├── application/         # Use cases and orchestration
│   ├── ports/           # Interfaces (abstractions) for infrastructure
│   └── use_cases/       # Application services coordinating domain logic
└── infrastructure/      # Adapters (Article II - concrete implementations)
    ├── adapters/        # Framework-specific implementations
    ├── repositories/    # Data persistence adapters (PostgreSQL, Redis)
    └── events/          # Event bus adapters (Kafka publishers/subscribers)
```

## Cross-Context Communication Rules (Article VI - EDA)

### ❌ FORBIDDEN: Direct Synchronous Calls

```python
# ❌ WRONG - Direct cross-context call creates tight coupling
from contexts.character import CharacterService
story.character = CharacterService.get_character(id)
```

### ✅ REQUIRED: Asynchronous Event-Driven Communication

```python
# ✅ CORRECT - Event-driven communication via Kafka
# Narrative context publishes domain event
story.publish_event(CharacterRequested(character_id=id))

# Character context subscribes to CharacterRequested
# Character context publishes CharacterRetrieved event
# Narrative context subscribes to CharacterRetrieved
```

### Event Serialization & Metadata

- Events between contexts MUST be serialized via `src/event_bus.py`
- Events MUST include tenant metadata for multi-tenancy
- Events MUST include correlation IDs for distributed tracing (Article VII)

### Read Models & Data Isolation

- Read models are materialized per context (CQRS pattern)
- Direct cross-context database reads are **PROHIBITED**
- Each context owns its PostgreSQL schema (Article IV - SSOT)

## Domain Model Purity Checklist (Article I)

### ✅ Pure Domain Model Characteristics

- Only imports from within same bounded context
- Only references shared value objects/enums from `src/shared_types.py`
- No `import sqlalchemy`, `import redis`, `import fastapi`, `import httpx`
- No HTTP, database, or framework dependencies
- Business logic expressed in domain terms only
- Testable without infrastructure (unit tests with no mocks for infrastructure)

### ❌ Infrastructure Dependencies (FORBIDDEN in Domain Layer)

- Database ORMs: `sqlalchemy`, `django.db`, `peewee`
- HTTP clients: `requests`, `httpx`, `aiohttp`
- Framework decorators: `@app.route`, `@router.get`, `@dataclass` (use domain models)
- External API clients: `openai`, `anthropic`, `google.generativeai`
- Caching libraries: `redis`, `memcached`
- Message queues: `kafka-python`, `pika`, `celery`

### Example: Pure Domain Model

```python
# ✅ CORRECT - Pure domain model (contexts/character/domain/models/character.py)
from typing import List
from src.shared_types import CharacterId, PersonaType

class Character:
    """Pure domain model - no infrastructure dependencies."""
    
    def __init__(self, id: CharacterId, name: str, persona: PersonaType):
        self.id = id
        self.name = name
        self.persona = persona
        self._traits: List[str] = []
    
    def add_trait(self, trait: str) -> None:
        """Business logic for trait addition with invariants."""
        if trait in self._traits:
            raise ValueError(f"Character already has trait: {trait}")
        self._traits.append(trait)
    
    def evolve_persona(self, new_persona: PersonaType) -> 'CharacterEvolved':
        """Domain logic returns domain event."""
        self.persona = new_persona
        return CharacterEvolved(character_id=self.id, new_persona=new_persona)
```

## Single Source of Truth (Article IV)

### PostgreSQL as SSOT

- **Domain Aggregates**: Authoritative state persisted in PostgreSQL
- **Schema Ownership**: Each bounded context owns its PostgreSQL schema/tables
- **Data Authority**: Database is the single source of truth for domain state

### Redis as Non-Authoritative Cache

- **Read-Through Cache**: Redis caches frequently accessed data
- **Explicit Non-Authority**: Cache misses/invalidations fall back to PostgreSQL
- **Invalidation Strategy**: Event-driven invalidation via domain events
- **TTL Policy**: All cached entries have time-to-live (TTL) for automatic expiry

Example:
```python
# ✅ CORRECT - PostgreSQL as SSOT, Redis as cache
async def get_character(character_id: CharacterId) -> Character:
    # Try cache first (non-authoritative)
    cached = await redis_adapter.get(f"character:{character_id}")
    if cached:
        return cached
    
    # Cache miss - fetch from PostgreSQL (authoritative SSOT)
    character = await postgres_repository.get_character(character_id)
    
    # Populate cache with TTL
    await redis_adapter.set(f"character:{character_id}", character, ttl=3600)
    return character
```

## Anti-Patterns to Avoid

❌ **Distributed Monolith**: Synchronous calls between contexts creating tight coupling  
❌ **Anemic Domain Models**: Domain models with no behavior, just getters/setters  
❌ **Infrastructure Leakage**: Database, HTTP, or framework code in domain layer  
❌ **Shared Database**: Multiple contexts directly accessing same tables  
❌ **God Context**: One context handling too many unrelated responsibilities  
❌ **Missing Events**: State changes not published as domain events  
❌ **Cache as SSOT**: Treating Redis cache as authoritative instead of PostgreSQL

## Constitution Compliance

This architecture enforces:

- **Article I (DDD)**: Pure domain models, explicit bounded contexts, ubiquitous language
- **Article II (Hexagonal)**: Ports (interfaces) in application layer, Adapters in infrastructure layer
- **Article III (TDD)**: Domain models testable without infrastructure (Red-Green-Refactor cycle)
- **Article IV (SSOT)**: PostgreSQL as authoritative state, Redis as non-authoritative cache
- **Article V (SOLID)**: SRP (single context responsibility), DIP (dependency inversion via ports)
- **Article VI (EDA)**: Async communication via Kafka event bus, no direct cross-context calls
- **Article VII (Observability)**: Structured logging, Prometheus metrics, OpenTelemetry tracing in adapters

## References

- **Constitution**: `.specify/memory/constitution.md` (Articles I, II, IV, VI)
- **Hexagonal Architecture**: `docs/architecture/ports-adapters.md`
- **Event-Driven Patterns**: `docs/patterns/event-driven.md` (to be created)
- **SOLID Principles**: Constitution Article V
- **TDD Guidelines**: `docs/testing/tdd-guidelines.md` (to be created)
- **Redis Cache Policy**: `docs/data/redis-cache-policy.md` (to be created)

---

**Compliance**: This document reflects Constitution v2.0.0 requirements (Articles I, II, IV, VI).
