## Context

The Novel Engine is a narrative simulation platform being extended to support Warzone 5, a dynamic geopolitical simulation. The system follows strict Hexagonal Architecture with:
- **Domain Layer**: Pure Python entities with Pydantic models
- **Application Layer**: Services orchestrating domain logic
- **API Layer**: FastAPI routers with schema validation
- **Frontend**: React with TypeScript, TanStack Query, Zustand

Currently, the `world` context exists with `Faction` and `Location` entities. This change adds foundational timekeeping.

## Goals / Non-Goals

**Goals:**
- Provide a single source of truth for in-world time
- Enable safe time advancement with validation (no backward time travel)
- Emit domain events that other systems can eventually subscribe to
- Establish the repository pattern for calendar persistence

**Non-Goals:**
- Complex calendar systems (leap years, variable month lengths, lunar cycles)
- UI timeline visualization (future change)
- Time-based event handlers (subscribing systems come later)
- Multi-calendar support (different cultures with different calendars)

## Decisions

### 1. Calendar Format: Fixed 360-day year
**Choice**: 12 months × 30 days = 360 days per year

**Rationale**: Simplifies initial implementation while remaining intuitive for fantasy settings. Many RPG and strategy games use this convention.

**Alternatives Considered**:
- Gregorian calendar (365.25 days): Too complex for fantasy setting, leap years add unnecessary complexity
- Configurable calendar: Over-engineering for MVP, can be added later

### 2. Storage: Repository Pattern with In-Memory Default
**Choice**: Define `CalendarRepository` port with `InMemoryCalendarRepository` implementation

**Rationale**: Follows existing patterns in the codebase (`FactionRepository`, `LocationRepository`). Keeps domain pure while allowing future persistence swap.

**Alternatives Considered**:
- Singleton with global state: Violates hexagonal architecture, harder to test
- Direct database: Premature, violates domain isolation

### 3. Event Publishing: Simple Domain Events
**Choice**: `TimeAdvancedEvent` emitted by `WorldCalendar.advance_days()`

**Rationale**: Establishes the event pattern without requiring full event bus infrastructure. Events can be collected and processed synchronously initially.

**Alternatives Considered**:
- Full event bus with async handlers: Over-engineering for MVP
- No events: Would require tight coupling when time-based features are added

### 4. API Design: RESTful with Single Resource
**Choice**: `GET /api/world/time` and `POST /api/world/time/advance`

**Rationale**: Simple, discoverable, follows REST conventions. The world has ONE calendar, so no collection endpoints needed.

**Alternatives Considered**:
- GraphQL subscription: Adds complexity, WebSocket infrastructure not needed yet
- Single PATCH endpoint: Less discoverable, conflates read/write concerns

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| In-memory storage loses calendar state on restart | Document clearly; persistence is future work. Default to sensible starting date. |
| No time zone / locale handling | Fantasy setting doesn't need Earth time zones. Display string is locale-agnostic. |
| Event handlers not yet implemented | Events are still valuable for logging and future extensibility. Document as integration point. |
| Fixed calendar format limits flexibility | Design `WorldCalendar` to accept configuration in constructor. MVP uses defaults. |
