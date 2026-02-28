## Context

**Current State (Post PREP-001):**
```
src/api/schemas/
├── __init__.py           (395 lines) - Re-exports
├── character_schemas.py  (396 lines) - Character, Psychology, Memory, Goals, Dialogue
├── narrative_schemas.py  (813 lines) - Story, Chapter, Scene, Beat, Plotline, Pacing
└── remaining_schemas.py  (2,608 lines) - Everything else
```

**Problem:** `remaining_schemas.py` contains 16+ domain concerns mixed together, making:
- Navigation difficult (finding a schema requires scrolling/searching)
- Code review harder (changes touch a large file)
- Merge conflicts more likely (many developers editing same file)
- Warzone 5 preparation slower (world simulation schemas are scattered)

## Goals / Non-Goals

**Goals:**
- Split `remaining_schemas.py` into 6 domain-aligned modules (~300-500 lines each)
- Maintain 100% backward compatibility for all imports
- Complete in a single atomic change with no intermediate broken states

**Non-Goals:**
- No schema content changes (no field additions, removals, or type changes)
- No router changes (imports continue to work as-is)
- No frontend changes (schemas.ts is auto-generated)

## Decisions

### D1: Module Boundaries

**Decision:** Split by domain context, not by schema count.

| Module | Domain | Schemas Included | Est. Lines |
|--------|--------|------------------|------------|
| `world_schemas.py` | World Simulation | Calendar, Diplomacy, Simulation, Snapshot, Rumor | ~400 |
| `knowledge_schemas.py` | AI Brain / RAG | RAG, Brain Settings, Routing, Knowledge Base | ~500 |
| `social_schemas.py` | Social Systems | Relationship, Item, Faction | ~350 |
| `system_schemas.py` | Platform | Health, Auth, Campaign, Workspace, Event | ~450 |
| `experiment_schemas.py` | A/B Testing | Experiment, Prompt Management | ~400 |
| `orchestration_schemas.py` | Orchestration | Orchestration status/control | ~150 |

**Rationale:** Domain alignment matches the `src/contexts/` directory structure, making it intuitive to find related schemas.

**Alternative Considered:** Split by file size (equal distribution) - rejected because it would mix unrelated concerns.

### D2: Import Strategy

**Decision:** Use explicit re-exports in `__init__.py`, not star imports.

```python
# __init__.py pattern
from src.api.schemas.world_schemas import (
    CalendarResponse,
    DiplomacyMatrixResponse,
    # ... explicit list
)
```

**Rationale:**
- Explicit imports prevent namespace pollution
- IDEs can trace imports correctly
- Easier to detect unused schemas
- Matches existing pattern in current `__init__.py`

**Alternative Considered:** `from module import *` - rejected because it hides import origins and can cause name collisions.

### D3: Enum Placement

**Decision:** Enums used by multiple schemas go in the same file as their primary schema.

**Rationale:** Reduces circular import risk, keeps related types together.

**Example:** `HealthScoreEnum` stays in `narrative_schemas.py` (already there), `ConfidentialityLevel` moves to `knowledge_schemas.py`.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Circular imports between new modules | Keep all schemas self-contained; if A depends on B's type, use `from pydantic import BaseModel` forward refs |
| Missed import updates in routers | Run full test suite after change; `grep` for all `remaining_schemas` references |
| Frontend type sync issues | Regenerate OpenAPI spec and verify `schemas.ts` matches |

## Migration Plan

**Phase 1: Create New Modules**
1. Create 6 new schema files with headers
2. Move schemas from `remaining_schemas.py` to appropriate module
3. Add imports within each module (no cross-module dependencies)

**Phase 2: Update __init__.py**
1. Replace `remaining_schemas` import with 6 new module imports
2. Verify `__all__` list is complete
3. Run `python -c "from src.api.schemas import *"` to verify

**Phase 3: Cleanup**
1. Delete `remaining_schemas.py`
2. Run full test suite: `./scripts/ci-check.sh`
3. Commit as single atomic change

**Rollback:** If issues arise, revert the commit - no data migration involved.

## Open Questions

None - the approach is straightforward refactoring with no ambiguity.
