## Why

`remaining_schemas.py` at 2,608 lines is still a maintainability bottleneck that slows all future development. This refactoring completes the schema modularization started in PREP-001, enabling faster development cycles and preparing the codebase for Warzone 5 world simulation features.

## What Changes

- Split `remaining_schemas.py` into 6 domain-aligned modules
- Delete `remaining_schemas.py` after migration
- Update `__init__.py` imports to maintain backward compatibility
- No API changes - all existing imports continue to work

## Capabilities

### New Capabilities

None - this is a pure refactoring with no new functionality.

### Modified Capabilities

None - no spec-level behavior changes. Only internal organization changes.

## Impact

**Files Created:**
- `src/api/schemas/world_schemas.py` (~400 lines)
- `src/api/schemas/knowledge_schemas.py` (~500 lines)
- `src/api/schemas/social_schemas.py` (~350 lines)
- `src/api/schemas/system_schemas.py` (~450 lines)
- `src/api/schemas/experiment_schemas.py` (~400 lines)
- `src/api/schemas/orchestration_schemas.py` (~150 lines)

**Files Modified:**
- `src/api/schemas/__init__.py` - Update imports
- `src/api/schemas/remaining_schemas.py` - **DELETED**

**Files Deleted:**
- `src/api/schemas/remaining_schemas.py`

**Routers Affected (import only):**
- All routers in `src/api/routers/` that import from `src.api.schemas`
- No changes needed - imports remain backward compatible

**Frontend:**
- `frontend/src/types/schemas.ts` - No changes (auto-generated from OpenAPI)
