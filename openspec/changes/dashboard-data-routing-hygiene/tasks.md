## Implementation Tasks

### REVERSAL NOTE (2025-11-19)
This change has been **reversed** to remove API versioning. The system now uses `/api/characters` instead of `/api/v1/characters` because:
- Backend had no actual version control logic (v1 endpoints were just aliases)
- Keeping v1 without versioning logic was misleading
- Frontend-backend consistency is more important than placeholder versioning

### Completed Reversal Tasks
1. Backend changes
   - [x] Remove `/api/v1/*` endpoints from api_server.py
   - [x] Remove `/api/v1/*` endpoints from src/api/main_api_server.py
   - [x] Remove `/api/v1/*` endpoints from production_api_server.py
   - [x] Update SSE endpoint from `/api/v1/events/stream` to `/api/events/stream`

2. Frontend changes
   - [x] Update `useDashboardCharactersDataset` to use `/api/characters` (removing `/api/v1/characters`)
   - [x] Update `useRealtimeEvents` to use `/api/events/stream` (removing `/api/v1/events/stream`)
   - [x] Update Vite proxy config to remove `/v1` proxy, keep only `/api` proxy

3. Tests
   - [x] Update `dashboard-accessibility.test.tsx` to verify only `/api/characters` endpoints (no versioning)

4. Validation
   - [x] Re-run `npm run lint` (passed with test-only warnings)
   - [x] Re-run `npm run type-check` (pre-existing errors in AuthContext.tsx, unrelated to changes)
   - [x] Run full test suite

### Original Implementation Tasks (SUPERSEDED)
1. Evidence & spec alignment
   - [x] Validate `/api/characters` contract (no versioning) with backend
2. Tests-first (TDD)
   - [x] Extend `dashboard-accessibility.test.tsx` to assert only `/api/characters` URLs are hit
3. Implementation
   - [x] Refactor `useDashboardCharactersDataset` to use `/api/characters` base
   - [x] Align Vite proxy to handle `/api/*` without version prefixes
4. Validation & audit
   - [x] Re-run `npm run lint`, `npm run type-check`, and full `npx vitest run`
