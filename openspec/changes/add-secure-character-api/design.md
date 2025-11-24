# Design: Authenticated Character API + Simulation Support

## Context
- Current `/api/characters` only lists seeded names; POST is not supported.
- `secure_main_api.py` has auth and CORS controls; Playwright audit showed CORS and validation causing friction.
- Simulations reject unknown names and cannot see user-created characters.

## Approach
- Implement POST `/api/characters` in the authenticated API surface (prefer secure_main_api) with request validation and user ownership.
- Persist characters to an accessible store (DB or in-memory placeholder if no DB available) and merge with baseline defaults on list.
- Update simulation flow to resolve character names from the user store; return 4xx with missing names listed.
- Ensure CORS/auth headers set for the new endpoints; keep validation on but allow configurable skip for local dev.
- Environment knobs: `CORS_ORIGINS` to allow the front-end origin and `SKIP_INPUT_VALIDATION=1` for local debugging when middleware blocks requests.

## Risks / Trade-offs
- Persistence choice: in-memory is simplest but not durable; DB-backed requires migrations. Start minimal with clear upgrade path.
- Validation strictness vs. dev ergonomics: keep toggle (`SKIP_INPUT_VALIDATION`) but document expected defaults.

## Open Questions
- Storage layer preference (existing SQLite via SecurityService vs. new table/file)?
- Should characters be scoped per user only, or allow shared/public characters?
