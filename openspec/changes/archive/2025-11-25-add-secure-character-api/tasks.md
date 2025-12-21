## 1. API surface
- [x] 1.1 Add POST /api/characters (auth required) to persist a character with validation and default fields.
- [x] 1.2 Ensure GET /api/characters returns user-created entries plus seeded defaults without duplicates.
- [x] 1.3 Make /simulations accept user-created characters, returning clear 4xx when names are missing/invalid.

## 2. Frontend integration
- [x] 2.1 Update API client/hooks to call the real character API (create + list) with auth tokens.
- [x] 2.2 Wire dashboard to render API-backed characters; show empty-state/error messaging when none exist.

## 3. Platform/interop
- [x] 3.1 Configure CORS/auth headers for the new endpoints; document required environment flags.
- [x] 3.2 Add regression tests (backend + minimal frontend hook test) covering create/list/simulate happy path and invalid input.

## 4. Validation
- [x] 4.1 Run `openspec validate add-secure-character-api --strict` and fix any issues.
