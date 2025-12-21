# Novel Engine (AI Narrative Engine)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18+](https://img.shields.io/badge/react-18+-blue.svg)](https://react.dev/)

Languages: English | [简体中文](README.md)

Production-ready AI-driven narrative generation and multi-agent simulation platform, with frontend/backend collaboration, observability, and continuous delivery.

This monorepo uses the root README as the single authoritative project homepage. Subdirectory docs are now indexed with non-README filenames to avoid duplication.

---

## Highlights

- Multi-agent architecture: `DirectorAgent`, `PersonaAgent`, `ChroniclerAgent`
- Real AI integration: LLM/external APIs with graceful degradation when unavailable
- Unified configuration: `config.yaml` + environment overrides, thread-safe global access
- Production-ready: concurrency-safe, rich logging, caching & retries, error handling & observability
- Frontend: isolated `frontend/` (React 18) with design system and quality gates

![Flow-based dashboard view](docs/assets/dashboard/dashboard-flow-2025-11-14-condensed.png)

---

## Theoretical Foundation

This project is grounded in Roland Barthes’ 1967 essay “The Death of the Author.” Meaning is not dictated by an author’s singular intent; it emerges from the interplay of language systems and readers. Language precedes the author—what we call “the Human Writing System,” a socially shared symbolic memory spanning language, culture, and corpora. In this view, creation is retrieval and recombination rather than ex nihilo invention.

- Reframed role: within the system, the “author” becomes the “orchestrator.” Novel Engine does not “create meaning”; it generates paths through a semantic network.
- Value proposition: focus on compositional logic, semantic constraints, and reproducibility—not surface-level linguistic novelty.
- Core assumptions and constraints:
  - Language as closed world, open composition: modules compose within existing semantic distributions without escaping the statistical bounds of human language.
  - Composition as constraint: every generation must satisfy logical consistency, semantic coherence, and provenance.
  - Originality as rare recombination: “original” outputs are low-probability new paths in the semantic graph.
- Engineering implications:
  - Path diversification
  - Entropy-balanced generation
  - Validation-driven orchestration
  - Retrieval mechanisms and traceable weighting

See: `docs/FOUNDATIONS.en.md`

---

## Repository Structure (excerpt)

- `src/`: core backend services
- `frontend/`: React app and design system
- `docs/`: architecture, API, guides, ADRs
- `tests/`: test suites and quality gates
- `scripts/`: local validation, quality, migration scripts
- `.github/workflows/`: CI/CD workflows

See the root directory listing and `docs/index.md` for more.

---

## Quick Start

Prereqs: Python 3.11+, Node.js 18+, npm

Backend (example)

```
python -m venv .venv
./.venv/Scripts/activate  # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -U pip
pip install -r requirements.txt
pytest -q  # optional quick tests
python api_server.py  # or production entry points
```

Unified dev bootstrap (non-blocking)

1. Prepare dependencies:
   ```bash
   python -m venv .venv
   . .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   pip install -r requirements.txt
   (cd frontend && npm install)
   ```
2. Launch both stacks in the background:
   ```bash
   npm run dev:daemon
   ```
   - Backend: `http://127.0.0.1:8000/health`
   - Frontend: `http://127.0.0.1:3000`
   - Logs live in `tmp/dev_env.log`, PID files in `tmp/dev_env/`
3. Stop everything once you are done:
   ```bash
   npm run dev:stop
   ```
4. Individual commands still work, but the daemon script is now the supported workflow documented throughout the repo.

### Unified Dev Environment Scripts

Always use the wrapper scripts so FastAPI + Vite start/stop cleanly:

| Command | Description |
| --- | --- |
| `npm run dev:daemon` | Calls `scripts/dev_env.sh start --detach`, booting uvicorn (127.0.0.1:8000) and Vite (127.0.0.1:3000) in the background |
| `npm run dev:stop` | Gracefully shuts both processes down |
| `npm run dev:status` | Shows current PIDs; run this before killing stray processes |

Logs are tailed to `tmp/dev_env/backend.log` and `tmp/dev_env/frontend.log`. Playwright/UAT commands should export:

```bash
SKIP_DASHBOARD_VERIFY=true PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 npx playwright test …
```

## Coding Standards & Quality Gates

- **Frontend**: Inside `frontend/` run `npm run lint`, `npm run type-check`, and `npm test -- --run`. Dashboard changes must execute all Playwright suites (Core / Extended / Interactions / Cross-browser / Accessibility / Login) with the daemon server and env vars above. Preserve deterministic `data-role` / `data-testid` attributes for automation.
- **Backend**: Run `bash scripts/validate_ci_locally.sh` to get Black, Isort, Flake8, Mypy, and pytest coverage in one pass; for smoke checks use `pytest tests/test_security_framework.py tests/test_quality_framework.py`.
- **CI parity**: Mirror GitHub Actions with `act --pull=false -W .github/workflows/frontend-ci.yml -j build-and-test` and `act --pull=false -W .github/workflows/ci.yml -j tests`, saving logs to `tmp/act-frontend.log` and `tmp/act-ci.log`.
- **Lighthouse / MCP evidence**: `CHROME_PATH=/usr/bin/google-chrome npx @lhci/cli@0.14.0 autorun` for performance, `node scripts/mcp_chrome_runner.js --viewport WIDTHxHEIGHT …` for real UI screenshots + metadata stored in `docs/assets/dashboard/`.
- See [`docs/coding-standards.md`](docs/coding-standards.md) for the full checklist, doc-update requirements, and linkable commands.

### Flow-based Dashboard (Nov 2025)

`/dashboard` now renders semantic zones via a responsive flow grid:

- `data-role="summary-strip"` — system status banner with orchestration mode, active phase, and last updated time
- `data-role="control-cluster"` — Quick Actions + connection badge with ≥44 px targets
- `data-role="pipeline-monitor"` — Turn pipeline timeline with scrollable steps; phase changes emit to tests and the summary strip
- `data-role="stream-feed"` — Real-time activity + narrative timeline (tabs/accordion on tablet/mobile)
- `data-role="system-signals"` — Performance metrics paired with event cascade feed, height-capped with internal scroll
- `data-role="persona-ops"` / `data-role="analytics-insights"` — character networks and analytics panels

On desktop the grid uses `repeat(auto-fit, minmax(320px, 1fr))` with `grid-auto-flow: dense`, letting high-priority zones span two columns while telemetry panels wrap automatically. Tablets collapse to two columns, and mobile traffic is routed through `MobileTabbedDashboard` so only one dense panel stays open at a time.

![Flow-based dashboard screenshot](docs/assets/dashboard/dashboard-flow-2025-11-14-condensed.png)

> Capture evidence via MCP automation:  
> `node scripts/mcp_chrome_runner.js --url http://127.0.0.1:3000/dashboard --viewport 1440x900 --screenshot docs/assets/dashboard/dashboard-flow-2025-11-14-condensed.png --metadata docs/assets/dashboard/dashboard-flow-2025-11-14-condensed.json`  
> The script clicks the Demo CTA, waits for `data-role="control-cluster"`/`stream-feed`, and writes PNG+JSON into `docs/assets/dashboard/` for README/UX reports.

---

## Testing & Quality

- Python tests: `pytest` (see `pytest.ini` / `.coveragerc`)
- Local CI parity: `scripts/validate_ci_locally.sh` (Windows: `scripts/validate_ci_locally.ps1`). It defaults to touched files but supports `RUN_LINT=1`, `RUN_MYPY=1`, and `RUN_TESTS=1` to exercise the legacy code paths (lint/mypy debt still exists there).
- Frontend gates: `npm run type-check`, `npm run lint:all`, `npm run tokens:check`
- Full UAT: start via `npm run dev:daemon`, then run the Playwright suites (core/extended/cross-browser/accessibility) with `SKIP_DASHBOARD_VERIFY=true`.

**Last local validation** (2025-11-14, commit `bf1406c`)

| Scope | Commands |
| --- | --- |
| Lint & Type Safety | `npm run lint`, `npm run type-check` |
| Frontend Unit | `VITEST_MAX_THREADS=6 VITEST_MIN_THREADS=3 npx vitest run --reporter=dot` |
| Playwright Suites | `npx playwright test tests/e2e/dashboard-core-uat.spec.ts --project=chromium-desktop`<br>`npx playwright test tests/e2e/dashboard-extended-uat.spec.ts --project=chromium-desktop`<br>`npx playwright test tests/e2e/dashboard-cross-browser-uat.spec.ts --project=chromium-desktop`<br>`npx playwright test tests/e2e/dashboard-interactions.spec.ts --project=chromium-desktop`<br>`npx playwright test tests/e2e/accessibility.spec.ts --project=chromium-desktop`<br>`npx playwright test tests/e2e/login-flow.spec.ts --project=chromium-desktop` |
| Backend Tests | `pytest tests/test_security_framework.py tests/test_quality_framework.py` |
| CI Mirrors | `scripts/validate_ci_locally.sh`, `act --pull=false -W .github/workflows/frontend-ci.yml -j build-and-test`, `act --pull=false -W .github/workflows/ci.yml -j tests` |

Run `npm run dev:daemon` beforehand so both stacks are healthy; logs and artifacts live in `tmp/dev_env.log` and `reports/test-results/`.

### Demo CTA & Offline Guide

- **Run the Demo CTA flow**
  1. `cd frontend && npm install && npm run dev`;
  2. Visit `http://127.0.0.1:3000/` and click the “View Demo” button (`data-testid="cta-demo"`);
  3. Verify you land on `/dashboard`, the guest banner (`data-testid="guest-mode-banner"`) is visible, and the summary strip reflects the demo/live state.

- **Simulate offline**
  - Use DevTools Network → “Offline”, or call `page.context().setOffline(true)` in Playwright;
  - The connection indicator flips to `OFFLINE`, and when the network returns it switches back to `ONLINE/LIVE` while logging `[connection-indicator]` events in the console.

- **Playwright + Experience Report**
  - `npm run test:e2e:smoke` (<1 minute) covers the CTA/offline scenarios;
  - `npm run test:e2e` runs the full suite;
  - Each run writes `frontend/reports/experience-report-*.{md,html}` containing the CTA/offline summary and screenshot links; CI uploads the files as artifacts **and** adds a condensed CTA/offline table to the GitHub job summary so reviewers can see pass/fail status without downloading artifacts.

- **Environment variables**
  - `PLAYWRIGHT_VERIFY_ATTEMPTS` / `PLAYWRIGHT_VERIFY_RETRY_DELAY` control the dashboard verification retries inside global setup. Example:
    ```bash
    PLAYWRIGHT_VERIFY_ATTEMPTS=5 PLAYWRIGHT_VERIFY_RETRY_DELAY=8000 npm run test:e2e:smoke
    ```

---

## Documentation

- Docs Home: `docs/index.md`
- Architecture: `docs/architecture/INDEX.md`
- API: `docs/api/INDEX.md`
- Guides: `docs/guides/INDEX.md`

---

## Contributing

Contributions welcome via Issues and PRs. Please run local validation and tests before submitting to satisfy quality gates.

---

## License

MIT License. See `LICENSE`.
