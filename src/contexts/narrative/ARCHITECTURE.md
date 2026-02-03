# Narrative Context Architecture

This document describes the Hexagonal Architecture (Ports & Adapters) for the Narrative bounded context within Novel Engine.

## Overview

The Narrative context is responsible for generating, managing, and orchestrating story content. It follows Domain-Driven Design (DDD) principles with a clear separation between domain logic and infrastructure concerns.

## Layer Structure

```
src/contexts/narrative/
├── domain/              # Core business logic (no external dependencies)
│   ├── entities/        # Domain entities (NarrativeSegment, StoryArc)
│   ├── value_objects/   # Immutable value types (Tone, Genre, Theme)
│   ├── aggregates/      # Aggregate roots (NarrativeSession)
│   ├── events/          # Domain events (SegmentGenerated, ArcCompleted)
│   └── repositories/    # Repository interfaces (abstract ports)
│
├── application/         # Use cases and orchestration
│   ├── ports/           # Inbound/Outbound port interfaces
│   │   ├── narrative_generator_port.py    # LLM generation interface
│   │   ├── context_assembler_port.py      # World context compression
│   │   └── streaming_port.py              # SSE streaming interface
│   ├── services/        # Application services
│   │   ├── narrative_service.py           # Main orchestration
│   │   └── context_assembler.py           # World -> Prompt compression
│   ├── commands/        # CQRS write operations
│   └── queries/         # CQRS read operations
│
└── infrastructure/      # External adapters (replaceable)
    ├── generators/      # LLM generator implementations
    │   ├── openai_generator.py
    │   └── gemini_generator.py
    ├── persistence/     # Database adapters
    │   └── postgres_narrative_repo.py
    └── streaming/       # SSE/WebSocket adapters
        └── sse_adapter.py
```

## Key Ports (Interfaces)

### Inbound Ports (Driving)
- `NarrativeService`: Entry point for narrative generation requests
- `StreamingPort`: Interface for real-time narrative streaming

### Outbound Ports (Driven)
- `NarrativeGeneratorPort`: Abstract interface for LLM providers
- `ContextAssemblerPort`: Interface for world state compression
- `NarrativeRepository`: Persistence abstraction

## Dependency Rule

**Dependencies flow inward**: Infrastructure → Application → Domain

- **Domain layer**: ZERO external dependencies. Pure Python only.
- **Application layer**: Depends on Domain. Defines ports.
- **Infrastructure layer**: Implements ports. Can use external libraries.

## Data Flow

1. **Request** → API Router (Infrastructure)
2. Router calls → NarrativeService (Application)
3. Service uses → ContextAssembler (Application Port)
4. Assembler fetches → WorldState from WorldContext
5. Service calls → NarrativeGeneratorPort (Outbound Port)
6. Generator (Infrastructure) → LLM API
7. Response streams → SSE Adapter (Infrastructure)
8. Events stored → NarrativeRepository (Outbound Port)

## Key Design Decisions

### Why Hexagonal Architecture?
- **Testability**: Domain logic tested without mocks for LLMs or databases
- **Flexibility**: Swap LLM providers (OpenAI → Gemini) by changing adapters
- **Maintainability**: Clear boundaries prevent coupling creep

### Context Assembly Strategy
The `ContextAssembler` compresses world state into LLM-compatible prompts:
1. Filter world graph nodes within N hops of active characters
2. Prioritize by relevance (recent events > distant history)
3. Token-budget enforcement via tiktoken
4. Output: Structured prompt < 4000 tokens

### Streaming Architecture
SSE streaming for real-time narrative feedback:
- Token-by-token delivery for low perceived latency
- Event types: `token`, `error`, `done`
- Backpressure handling via async generators

## Related Contexts

- **Story Context**: Scene generation, character arcs
- **World Context**: World state, factions, locations
- **Character Context**: Character profiles, relationships

## Further Reading

- [Hexagonal Architecture by Alistair Cockburn](https://alistair.cockburn.us/hexagonal-architecture/)
- [Domain-Driven Design by Eric Evans](https://www.domainlanguage.com/)
- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
