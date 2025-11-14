# Coding Standards & Tooling Contract

This document summarizes the conventions enforced across the Novel-Engine repo. Treat it as the single source of truth when writing or reviewing code.

## 1. Runtime & Wrapper Expectations

- **Dev servers**: always start via `npm run dev:daemon` (wrapper around `scripts/dev_env.sh`). Stop with `npm run dev:stop`. Direct `vite`/`uvicorn` usage is discouraged because the wrappers pipe logs to `tmp/dev_env/*.log` for MCP/Playwright evidence.
- **Playwright / UAT**: set `SKIP_DASHBOARD_VERIFY=true PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000` for every run so global setup can find the dashboard. Example: `SKIP_DASHBOARD_VERIFY=true PLAYWRIGHT_BASE_URL=... npx playwright test tests/e2e/dashboard-core-uat.spec.ts --project=chromium-desktop`.
- **MCP evidence**: capture real UI states with `node scripts/mcp_chrome_runner.js --url http://127.0.0.1:3000/dashboard --viewport 1440x900 --screenshot docs/assets/dashboard/dashboard-flow-YYYY-MM-DD.png --metadata docs/assets/dashboard/dashboard-flow-YYYY-MM-DD.json`. The runner auto-clicks the Demo CTA and waits for the `data-role` hooks we rely on in specs and tests.

## 2. Frontend (TypeScript + React)

### Layout & Semantics
- Use the flow-based layout defined in `openspec/specs/dashboard-layout/spec.md`. Critical zones must expose deterministic hooks: `data-role="control-cluster"`, `data-role="stream-feed"`, `data-role="pipeline"`, etc.
- Components exposing interactions **must** provide stable `data-testid` attributes (e.g., `quick-action-play`, `connection-status`). Tests and MCP automation rely on these selectors.
- Prefer CSS grid/flex tokens (see `frontend/src/components/layout/BentoGrid.tsx`) over inline styles. Clamp tall visuals with CSS functions (`clamp`, `minmax`) to keep first-fold density predictable.

### Lint, Type-Check, Tests
- Run locally before committing:
  ```bash
  cd frontend
  npm run lint
  npm run type-check
  npm test -- --run
  ```
- Playwright suites required for dashboard/UI changes:
  ```bash
  SKIP_DASHBOARD_VERIFY=true PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 \
  npx playwright test tests/e2e/dashboard-core-uat.spec.ts --project=chromium-desktop
  npx playwright test tests/e2e/dashboard-extended-uat.spec.ts --project=chromium-desktop
  npx playwright test tests/e2e/dashboard-interactions.spec.ts --project=chromium-desktop
  npx playwright test tests/e2e/dashboard-cross-browser-uat.spec.ts
  npx playwright test tests/e2e/accessibility.spec.ts --project=chromium-desktop
  npx playwright test tests/e2e/login-flow.spec.ts --project=chromium-desktop
  ```
  (All commands assume the daemon wrapper is already running.)

### Snapshot & Evidence
- Store MCP screenshots/JSON in `docs/assets/dashboard/` with date suffixes (`dashboard-flow-YYYY-MM-DD[-suffix].png`). Update both README files and `docs/assets/dashboard/README.md` whenever evidence changes.
- Cite the latest regression log in `docs/testing/uat/UAT_REAL_TESTING_RESULTS.md` (include command table + log locations under `tmp/` or `frontend/test-results/`).

## 3. Backend (Python)

### Formatting, Linting, Tests
- Use the CI parity script to run the exact GitHub workflow locally:
  ```bash
  bash scripts/validate_ci_locally.sh
  ```
  This script creates `.venv-ci/`, installs requirements, runs Black, Isort, Flake8, Mypy, and the pytest suite with coverage.
- For focused suites (security/quality), the canonical commands are:
  ```bash
  pytest tests/test_security_framework.py tests/test_quality_framework.py
  ```
- Shared types should import from `src/core/types/shared_types.py`. The legacy `src/shared_types/` shim is removed; keep imports consistent so `act` runs don’t fail with `ModuleNotFoundError`.

## 4. Continuous Integration

- Use `act` to mirror both workflows before pushing:
  ```bash
  act --pull=false -W .github/workflows/frontend-ci.yml -j build-and-test   # Vite + Vitest + Playwright smoke
  act --pull=false -W .github/workflows/ci.yml -j tests                      # Backend pytest
  ```
  Save logs (e.g., `tmp/act-frontend.log`, `tmp/act-ci.log`) and reference them in UAT docs.
- Lighthouse CI must be run with a real Chrome binary defined explicitly:
  ```bash
  cd frontend
  CHROME_PATH=/usr/bin/google-chrome npx @lhci/cli@0.14.0 autorun
  ```
  This prevents WSL from creating stray `undefined:/Users/...` directories when Chromium can’t infer the home path.

## 5. Documentation Expectations

- Any change touching layout, evidence, or CI must update:
  - README & README.en (sections: dev workflow, coding standards, screenshot references).
  - `docs/assets/dashboard/README.md` (table of MCP captures).
  - `docs/testing/uat/UAT_REAL_TESTING_RESULTS.md` (latest regression summary, command table, log references).
- Keep OpenSpec changes (`openspec/changes/<id>/`) validated via `openspec validate <id> --strict`. Every task list must be checked off before a change is considered complete.

Following this checklist ensures the next contributor (human or AI) can reproduce the stack, gather evidence, and pass CI without guesswork. EOF
