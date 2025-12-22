## Implementation Tasks
1. Establish API SSOT client
   - [ ] Add a single API client module and migrate existing services/hooks to use it (no duplicated axios wrappers).
   - [ ] Normalize errors into a single shape suitable for UI display and logging.

2. Guest session bootstrap
   - [ ] Ensure the app creates/resumes a guest session early (app init), and surfaces session state to the UI.
   - [ ] Ensure all product API requests are scoped to the session (cookies/headers as required by backend).

3. Usable flows
   - [ ] Character management: list/create/edit/delete backed by real API responses.
   - [ ] Story/simulation run: start a run, render output, and handle failures/retry.
   - [ ] Persistence: refresh the page and confirm workspace data is still present.

4. Tests and validation
   - [ ] Add unit/integration tests for API client error normalization and guest bootstrap.
   - [ ] Extend Playwright flows to cover “guest → create character → run → refresh → still present”.
   - [ ] Run full frontend + backend CI checks and `openspec validate refactor-frontend-api-and-ux --strict`.

