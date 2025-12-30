# Tasks: Refactor Frontend API + UX

## 1. Establish API SSOT client
- [x] Add a single API client module and migrate existing services/hooks to use it (no duplicated axios wrappers).
- [x] Normalize errors into a single shape suitable for UI display and logging.

## 2. Guest session bootstrap
- [x] Ensure the app creates/resumes a guest session early (app init), and surfaces session state to the UI.
- [x] Ensure all product API requests are scoped to the session (cookies/headers as required by backend).

## 3. Usable flows
- [x] Character management: list/create/edit/delete backed by real API responses.
- [x] Story/simulation run: start a run, render output, and handle failures/retry.
- [x] Persistence: refresh the page and confirm workspace data is still present.

## 4. Tests and validation
- [x] Add unit/integration tests for API client error normalization and guest bootstrap.
- [x] Extend Playwright flows to cover “guest → create character → run → refresh → still present”.
- [x] Run full frontend + backend CI checks and `openspec validate refactor-frontend-api-and-ux --strict`.
