# Ports & Adapters Architecture (Hexagonal)

**Constitution Reference**: Article II - The Ports & Adapters Architecture  
**Version**: 2.0.0  
**Last Updated**: 2025-11-04

## Overview

Novel Engine strictly enforces the **Hexagonal Architecture** (Ports and Adapters pattern). This upholds the **Dependency Inversion Principle** (the 'D' in SOLID) by ensuring:

1. **Domain and Application layers define Ports** (abstract interfaces)
2. **Infrastructure layers provide Adapters** (concrete implementations)
3. **Dependencies point inward**: Infrastructure depends on domain, never the reverse

## Core Principle (Article II)

> **Domain and Application layers define Ports (abstract interfaces). Infrastructure layers provide Adapters (concrete implementations). This upholds the Dependency Inversion Principle.**

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     External Systems                         │
│   (Web, CLI, Kafka, PostgreSQL, Redis, OpenAI, Gemini)      │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ Adapters (Infrastructure)
                            │
┌───────────────────────────┼─────────────────────────────────┐
│                           │                                  │
│  ┌────────────────────────┴──────────────────────────────┐  │
│  │         Infrastructure Layer (Adapters)               │  │
│  │  - PostgreSQLRepository                               │  │
│  │  - RedisCacheAdapter                                  │  │
│  │  - KafkaEventPublisher                                │  │
│  │  - OpenAIAdapter, GeminiAdapter (ACL)                 │  │
│  │  - FastAPIController                                  │  │
│  └────────────────────────┬──────────────────────────────┘  │
│                           │ implements                       │
│  ┌────────────────────────┴──────────────────────────────┐  │
│  │       Application Layer (Ports + Use Cases)           │  │
│  │  - ICharacterRepository (Port)                        │  │
│  │  - ICacheService (Port)                               │  │
│  │  - ILLMService (Port)                                 │  │
│  │  - CreateCharacterUseCase                             │  │
│  │  - GeneratePlotUseCase                                │  │
│  └────────────────────────┬──────────────────────────────┘  │
│                           │ orchestrates                     │
│  ┌────────────────────────┴──────────────────────────────┐  │
│  │           Domain Layer (Pure Business Logic)          │  │
│  │  - Character (Aggregate)                              │  │
│  │  - Story (Aggregate)                                  │  │
│  │  - CharacterService (Domain Service)                  │  │
│  │  - CharacterCreated (Domain Event)                    │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Ports & Adapters Matrix

| Context | Port (Interface) | Adapter Implementation | Direction | Infrastructure | Notes |
|---------|------------------|------------------------|-----------|----------------|-------|
| **Character** | `ICharacterRepository` | `PostgreSQLCharacterRepository` | Outbound | PostgreSQL | Character persistence |
| **Character** | `IPersonaGenerator` | `GeminiPersonaAdapter` | Outbound | Gemini API (ACL) | AI persona generation with retry/cache |
| **Character** | `ICharacterEventPublisher` | `KafkaCharacterEventPublisher` | Outbound | Kafka | Domain events: CharacterCreated, PersonaEvolved |
| **World** | `IWorldRepository` | `PostgreSQLWorldRepository` | Outbound | PostgreSQL | World state persistence |
| **World** | `IWorldEventPublisher` | `KafkaWorldEventPublisher` | Outbound | Kafka | Domain events: WorldCreated, SettingChanged |
| **Narrative** | `IStoryRepository` | `PostgreSQLStoryRepository` | Outbound | PostgreSQL | Story aggregate persistence |
| **Narrative** | `ILLMService` | `OpenAIAdapter` | Outbound | OpenAI API (ACL) | Plot/scene generation via LLM |
| **Narrative** | `INarrativeEventPublisher` | `KafkaNarrativeEventPublisher` | Outbound | Kafka | Domain events: PlotGenerated, SceneCreated |
| **Simulation** | `DirectorAgent.turn_processor` | `src/director_agent.py` | Inbound | FastAPI | Orchestrates campaign turns |
| **Simulation** | `EventBus.publish` | `src/core/event_bus.py` | Outbound | Kafka | Emits CampaignCreated, TurnAdvanced |
| **Persona** | `PersonaAgent.gemini_client` | `GeminiHTTPXAdapter` | Outbound | Gemini API (ACL) | HTTPX wrapper with retries, caching (Redis) |
| **Persona** | `PersonaAgent.decision_port` | `LocalStrategyFallback` | Inbound | In-Memory | Deterministic decisions when Gemini unavailable |
| **Chronicle** | `ChroniclerAgent.storage_gateway` | `S3StorageAdapter` | Outbound | AWS S3 / Local Files | Persists narrative markdown, media assets |
| **Chronicle** | `ExperienceAPI.fetch_campaign` | `FastAPIWorldRouter` | Inbound | FastAPI | HTTP API for frontend dashboard |
| **Platform** | `ICacheRepository` | `RedisCacheAdapter` | Outbound | Redis | Non-authoritative cache (Article IV) |
| **Platform** | `IMetricsCollector` | `PrometheusMetricsAdapter` | Outbound | Prometheus | Application-level metrics (Article VII) |
| **Platform** | `IFeatureFlagService` | `LaunchDarklyAdapter` | Outbound | LaunchDarkly | Feature flag management |
| **Platform** | `ITracingService` | `OpenTelemetryAdapter` | Outbound | OpenTelemetry | Distributed tracing (Article VII) |

## Port Types

### Inbound Ports (Driving Adapters)
**Direction**: External → Application/Domain  
**Purpose**: Entry points into the application (HTTP controllers, CLI, message consumers)  
**Examples**: 
- `DirectorAgent.turn_processor` (FastAPI controller calling use cases)
- `PersonaAgent.decision_port` (CLI calling persona decision logic)

### Outbound Ports (Driven Adapters)
**Direction**: Application/Domain → External  
**Purpose**: Application needs external services (databases, APIs, message publishers)  
**Examples**:
- `ICharacterRepository` → `PostgreSQLCharacterRepository`
- `ILLMService` → `OpenAIAdapter` or `GeminiAdapter`
- `IEventPublisher` → `KafkaEventPublisher`

## Dependency Inversion Principle (SOLID 'D')

### ✅ CORRECT: Domain Defines Abstractions (Ports)

```python
# src/contexts/character/application/ports/character_repository.py
from abc import ABC, abstractmethod
from src.contexts.character.domain.models import Character
from src.core.types.shared_types import CharacterId

class ICharacterRepository(ABC):
    """Port (abstraction) defined by application layer."""
    
    @abstractmethod
    async def get_character(self, id: CharacterId) -> Character:
        """Retrieve character by ID."""
        pass
    
    @abstractmethod
    async def save_character(self, character: Character) -> None:
        """Persist character aggregate."""
        pass
```

### ✅ CORRECT: Infrastructure Implements Adapters

```python
# src/contexts/character/infrastructure/repositories/postgresql_character_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from src.contexts.character.application.ports import ICharacterRepository
from src.contexts.character.domain.models import Character
from src.core.types.shared_types import CharacterId

class PostgreSQLCharacterRepository(ICharacterRepository):
    """Adapter (concrete implementation) in infrastructure layer."""
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def get_character(self, id: CharacterId) -> Character:
        # PostgreSQL-specific implementation
        result = await self._session.execute(
            select(CharacterORM).where(CharacterORM.id == id)
        )
        orm_char = result.scalar_one()
        return self._to_domain_model(orm_char)
    
    async def save_character(self, character: Character) -> None:
        # PostgreSQL-specific implementation
        orm_char = self._to_orm(character)
        self._session.add(orm_char)
        await self._session.commit()
```

### ❌ WRONG: Domain Depending on Infrastructure

```python
# ❌ FORBIDDEN - Domain layer importing infrastructure
from sqlalchemy import select  # Database ORM in domain layer!
from redis import Redis  # Cache library in domain layer!

class Character:
    def save(self):
        # ❌ Domain model should NOT know about database
        session.add(self)
        session.commit()
```

## Anti-Corruption Layer (ACL)

External systems (Gemini API, OpenAI, LaunchDarkly) require ACL to translate between external contracts and internal domain models.

### Example: Gemini API ACL

```python
# src/contexts/persona/infrastructure/adapters/gemini_persona_adapter.py
from src.contexts.persona.application.ports import IPersonaGenerator
from src.contexts.persona.domain.models import Persona
import google.generativeai as genai  # External API client

class GeminiPersonaAdapter(IPersonaGenerator):
    """ACL translating Gemini API responses to domain models."""
    
    def __init__(self, api_key: str, redis_cache: ICacheRepository):
        self._client = genai.GenerativeModel("gemini-pro")
        self._cache = redis_cache
    
    async def generate_persona(self, prompt: str) -> Persona:
        # Check cache (Article IV - Redis as non-authoritative cache)
        cached = await self._cache.get(f"persona:{hash(prompt)}")
        if cached:
            return cached
        
        # Call external API
        response = await self._client.generate_content_async(prompt)
        
        # ACL: Translate external response to domain model
        persona = self._translate_to_domain(response)
        
        # Cache result with TTL
        await self._cache.set(f"persona:{hash(prompt)}", persona, ttl=3600)
        
        return persona
    
    def _translate_to_domain(self, api_response) -> Persona:
        """ACL translation layer."""
        # Convert Gemini API format to internal Persona domain model
        return Persona(
            traits=self._extract_traits(api_response),
            background=self._extract_background(api_response),
            personality_type=self._map_personality_type(api_response)
        )
```

## Adapter Guidelines (Article VII - Observability)

All adapters MUST implement observability:

### ✅ Required: Structured Logging

```python
import structlog

logger = structlog.get_logger()

class PostgreSQLCharacterRepository(ICharacterRepository):
    async def get_character(self, id: CharacterId) -> Character:
        logger.info(
            "character_repository_get",
            character_id=id,
            trace_id=get_trace_id(),  # Article VII - OpenTelemetry
            tenant_id=get_tenant_id(),  # Multi-tenancy
            operation="character_fetch"
        )
        # ... implementation ...
```

### ✅ Required: Prometheus Metrics

```python
from prometheus_client import Counter, Histogram

character_fetch_total = Counter(
    'character_fetch_total',
    'Total character fetches',
    ['status', 'tenant']
)
character_fetch_duration = Histogram(
    'character_fetch_duration_seconds',
    'Character fetch latency'
)

class PostgreSQLCharacterRepository(ICharacterRepository):
    async def get_character(self, id: CharacterId) -> Character:
        with character_fetch_duration.time():
            try:
                character = await self._fetch(id)
                character_fetch_total.labels(status='success', tenant=tenant_id).inc()
                return character
            except Exception:
                character_fetch_total.labels(status='error', tenant=tenant_id).inc()
                raise
```

### ✅ Required: OpenTelemetry Distributed Tracing

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class PostgreSQLCharacterRepository(ICharacterRepository):
    async def get_character(self, id: CharacterId) -> Character:
        with tracer.start_as_current_span("character_repository.get_character") as span:
            span.set_attribute("character.id", str(id))
            span.set_attribute("tenant.id", get_tenant_id())
            # ... implementation ...
```

## Security & ACL Documentation

External adapters (Gemini, OpenAI, LaunchDarkly) require:

1. **ACL Documentation**: Translation logic documented in adapter
2. **Security Charter**: API key management, rate limiting, retry policies
3. **Data Protection**: No PII/sensitive data sent to external APIs without explicit consent
4. **Audit Logging**: All external API calls logged with trace ID and tenant metadata

## Constitution Compliance

This architecture enforces:

- **Article II (Hexagonal)**: Ports in application layer, Adapters in infrastructure layer
- **Article I (DDD)**: Domain layer remains pure, no infrastructure dependencies
- **Article V (SOLID - DIP)**: Dependencies point inward, domain defines abstractions
- **Article IV (SSOT)**: PostgreSQL adapters persist authoritative state
- **Article VI (EDA)**: Kafka adapters publish domain events asynchronously
- **Article VII (Observability)**: All adapters instrumented with logs, metrics, tracing

## References

- **Constitution**: `.specify/memory/constitution.md` (Articles I, II, IV, V, VI, VII)
- **Bounded Contexts**: `docs/architecture/bounded-contexts.md`
- **SOLID Principles**: Constitution Article V
- **Observability Standards**: `docs/observability/standards.md` (to be created)

---

**Compliance**: This document reflects Constitution v2.0.0 Article II requirements.




