# Novel Engine Architecture Guide

> LLM-optimized navigation for AI agents and developers

## Quick Navigation

### Entry Points

| Component | Path | Purpose |
|-----------|------|---------|
| API Server | `src/api/main_api_server.py` | FastAPI application factory |
| Routers | `src/api/routers/` | HTTP endpoint definitions (thin layer) |
| Services | `src/api/services/` | Business logic layer |

### Data Contracts (Single Source of Truth)

| Location | Type | Purpose |
|----------|------|---------|
| `src/api/schemas.py` | Pydantic | All API request/response models |
| `frontend/src/types/schemas.ts` | Zod | Frontend validation schemas |

## API Layer Architecture

```
src/api/
├── main_api_server.py    # FastAPI app with lifespan
├── schemas.py            # Pydantic models (SSOT)
├── routers/              # Thin HTTP handlers
│   ├── orchestration.py  # Orchestration endpoints
│   ├── characters.py     # Character CRUD
│   ├── events.py         # SSE streaming
│   ├── health.py         # Health checks
│   └── meta.py           # System status
└── services/             # Business logic
    ├── orchestration_service.py
    └── events_service.py
```

### Router Pattern

Routers are **thin** - they only handle HTTP concerns:

```python
@router.get("/api/orchestration/status", response_model=OrchestrationStatusResponse)
async def get_status(
    service: OrchestrationService = Depends(get_service)
) -> OrchestrationStatusResponse:
    return await service.get_status()
```

Business logic lives in **services**.

## DDD Bounded Contexts

```
src/contexts/
├── character/       # Character management
├── narratives/      # Story arcs, pacing
├── orchestration/   # Turn execution
├── interactions/    # Agent negotiations
├── subjective/      # Character POV
├── world/           # World state
├── knowledge/       # Information retrieval
└── ai/              # LLM provider abstraction
```

### Context Structure

Each context follows DDD layering:

```
contexts/{name}/
├── domain/
│   ├── aggregates/      # Aggregate roots
│   ├── entities/        # Domain entities
│   ├── value_objects/   # Immutable values
│   └── services/        # Domain services
├── application/
│   ├── commands/        # CQRS commands
│   ├── queries/         # CQRS queries
│   └── services/        # Application services
└── infrastructure/
    └── repositories/    # Persistence
```

## Key Patterns

1. **Routers are thin** - Only HTTP concerns, delegate to services
2. **Services own logic** - Business rules, orchestration
3. **Schemas are explicit** - No `Dict[str, Any]` in public APIs
4. **Contexts are isolated** - Cross-context via events

## Schema Organization

### Orchestration

```python
OrchestrationStartRequest   # POST /api/orchestration/start
OrchestrationStartResponse
OrchestrationStatusResponse # GET /api/orchestration/status
NarrativeResponse           # GET /api/orchestration/narrative
```

### Events/Analytics

```python
SSEEventData               # SSE event structure
SSEStatsResponse           # GET /events/stats
AnalyticsMetricsResponse   # GET /analytics/metrics
```

### Health/Meta

```python
HealthResponse             # GET /
HealthCheckResponse        # GET /health
SystemStatusResponse       # GET /meta/system-status
PolicyInfoResponse         # GET /meta/policy
```

## Validation Commands

```bash
# Backend
pytest tests/                    # All tests
pytest tests/unit/               # Unit tests only
pytest tests/integration/        # Integration tests

# Frontend
cd frontend && npm run type-check   # TypeScript validation
cd frontend && npm run lint:all     # Full lint suite
cd frontend && npm run test         # Jest tests

# Full validation
./scripts/validate_ci_locally.sh
```

## Import Guidelines

```python
# API layer imports
from src.api.schemas import OrchestrationStartRequest
from src.api.services import OrchestrationService

# Context imports
from src.contexts.character import Character, CharacterApplicationService
from src.contexts.narratives import NarrativeArc, StoryArcPhase
```

## File Quick Reference

| Need | File |
|------|------|
| Add API schema | `src/api/schemas.py` |
| Add router endpoint | `src/api/routers/*.py` |
| Add business logic | `src/api/services/*.py` |
| Character domain | `src/contexts/character/` |
| Story/narrative | `src/contexts/narratives/` |
| Frontend types | `frontend/src/types/schemas.ts` |
