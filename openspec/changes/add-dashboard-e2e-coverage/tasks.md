1. [x] Add a focused login spec that verifies successful login, error handling, and skip-link focus behavior using Playwright (`frontend/tests/e2e/login-flow.spec.ts`).
2. [x] Add a dashboard interactions spec that exercises world-map selection, quick-action toggles, pipeline state transitions, and responsive layouts (desktop + tablet projects) (`frontend/tests/e2e/dashboard-interactions.spec.ts`).
3. [x] Wire the new specs into `npm run test:e2e` (or dedicated npm scripts) and ensure they run in CI alongside the existing quick smoke (CI now sets `RUN_E2E=true` with `PLAYWRIGHT_PROJECTS=chromium-desktop`).
4. [x] Rerun `npm run lint` and the updated Playwright commands, attaching/summarizing results.
