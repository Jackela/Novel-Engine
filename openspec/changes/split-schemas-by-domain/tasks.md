## 1. Create New Schema Modules

- [ ] 1.1 Create `src/api/schemas/orchestration_schemas.py` with header and move orchestration schemas
- [ ] 1.2 Create `src/api/schemas/system_schemas.py` with header and move health/auth/campaign/workspace/event schemas
- [ ] 1.3 Create `src/api/schemas/social_schemas.py` with header and move relationship/item/faction schemas
- [ ] 1.4 Create `src/api/schemas/lore_schemas.py` with header and move lore/world-rule schemas
- [ ] 1.5 Create `src/api/schemas/knowledge_schemas.py` with header and move RAG/brain/routing/kb schemas
- [ ] 1.6 Create `src/api/schemas/experiment_schemas.py` with header and move experiment/prompt schemas
- [ ] 1.7 Create `src/api/schemas/world_schemas.py` with header and move calendar/diplomacy/simulation/snapshot/rumor schemas

## 2. Update Package Exports

- [ ] 2.1 Update `src/api/schemas/__init__.py` to import from all 6 new modules
- [ ] 2.2 Update `__all__` list to include all exported schemas
- [ ] 2.3 Verify no star imports are used (all explicit)

## 3. Cleanup

- [ ] 3.1 Delete `src/api/schemas/remaining_schemas.py`
- [ ] 3.2 Search for any remaining references to `remaining_schemas` in codebase
- [ ] 3.3 Remove any unused imports in new schema files

## 4. Verification

- [ ] 4.1 Run `python -c "from src.api.schemas import *"` to verify imports work
- [ ] 4.2 Run `pytest tests/` to verify all tests pass
- [ ] 4.3 Run `./scripts/ci-check.sh` to verify full CI passes
- [ ] 4.4 Run `npm run type-check` in frontend to verify TypeScript types still align

## 5. Commit

- [ ] 5.1 Stage all changes with `git add src/api/schemas/`
- [ ] 5.2 Commit with message: `refactor(prep-002): Complete schema modularization - split remaining_schemas.py`
