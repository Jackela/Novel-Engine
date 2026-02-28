## 1. Create New Schema Modules

- [x] 1.1 Create `src/api/schemas/orchestration_schemas.py` with header and move orchestration schemas
- [x] 1.2 Create `src/api/schemas/system_schemas.py` with header and move health/auth/campaign/workspace/event schemas
- [x] 1.3 Create `src/api/schemas/social_schemas.py` with header and move relationship/item/faction schemas
- [x] 1.4 Create `src/api/schemas/lore_schemas.py` with header and move lore/world-rule schemas
- [x] 1.5 Create `src/api/schemas/knowledge_schemas.py` with header and move RAG/brain/routing/kb schemas
- [x] 1.6 Create `src/api/schemas/experiment_schemas.py` with header and move experiment/prompt schemas
- [x] 1.7 Create `src/api/schemas/world_schemas.py` with header and move calendar/diplomacy/simulation/snapshot/rumor schemas

## 2. Update Package Exports

- [x] 2.1 Update `src/api/schemas/__init__.py` to import from all 6 new modules
- [x] 2.2 Update `__all__` list to include all exported schemas
- [x] 2.3 Verify no star imports are used (all explicit)

## 3. Cleanup

- [x] 3.1 Delete `src/api/schemas/remaining_schemas.py`
- [x] 3.2 Search for any remaining references to `remaining_schemas` in codebase
- [x] 3.3 Remove any unused imports in new schema files

## 4. Verification

- [x] 4.1 Run `python -c "from src.api.schemas import *"` to verify imports work
- [x] 4.2 Run `pytest tests/` to verify all tests pass
- [x] 4.3 Run `./scripts/ci-check.sh` to verify full CI passes
- [x] 4.4 Run `npm run type-check` in frontend to verify TypeScript types still align

## 5. Commit

- [x] 5.1 Stage all changes with `git add src/api/schemas/`
- [x] 5.2 Commit with message: `refactor(prep-002): Complete schema modularization - split remaining_schemas.py`

---

**Status**: ✅ COMPLETED (2025-02-26)

All schema files verified to exist:
- `character_schemas.py` ✅
- `narrative_schemas.py` ✅
- `orchestration_schemas.py` ✅
- `system_schemas.py` ✅
- `social_schemas.py` ✅
- `lore_schemas.py` ✅
- `knowledge_schemas.py` ✅
- `experiment_schemas.py` ✅
- `world_schemas.py` ✅

Tests passing: 6288 passed, 281 skipped
