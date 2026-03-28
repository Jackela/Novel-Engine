# Novel Engine

Novel Engine is a narrative simulation platform with a canonical FastAPI backend and a Vite-based frontend. The repository is being converged onto a single source of truth: one backend app, one frontend app, one test surface, and no legacy compatibility layer.

## Canonical entrypoints

- `src/apps/api/main.py`: canonical backend application entrypoint
- `frontend/`: canonical frontend workspace
- `tests/`: source-backed backend, contract, and infrastructure tests

## Local development

### Backend

```bash
python -m pip install -e ".[dev,test]"
pytest -q
ruff check src tests
mypy \
  src/apps/api \
  src/contexts/identity \
  src/contexts/knowledge/interface/http \
  src/contexts/world/interface/http \
  src/shared/infrastructure/config \
  src/shared/infrastructure/health \
  src/shared/infrastructure/logging \
  src/shared/infrastructure/middleware \
  src/shared/infrastructure/honcho \
  src/shared/interface/http \
  src/contexts/knowledge/application/services \
  --no-error-summary \
  --show-column-numbers
```

If you want the optional Honcho integration installed locally, use:

```bash
python -m pip install -e ".[dev,test,honcho]"
```

### Frontend

```bash
npm --prefix frontend install
npm --prefix frontend run type-check
npm --prefix frontend run test
npm --prefix frontend run build
npm --prefix frontend run test:e2e:smoke
```

`test:e2e:smoke` launches the canonical backend and frontend stack through Playwright.

## Testing model

- `pytest -q` is the default backend gate.
- External-service-heavy tests are opt-in through explicit environment flags in `tests/conftest.py`.
- Frontend smoke coverage is exercised with Playwright against the canonical backend and frontend stack.
- CI runs backend quality on the canonical backend surface, backend tests, frontend validation, and CodeQL.
- CodeQL scans the canonical source surface only; generated caches and build outputs are excluded, and default-branch merges must keep the scan clean or use documented suppressions for confirmed false positives. See [docs/security/codeql-alerts.md](docs/security/codeql-alerts.md).

## Repository hygiene rules

- Generated artifacts such as `__pycache__`, coverage output, Playwright reports, and temporary scratch directories are not source of truth.
- Checked-in tests must validate live source-backed behavior. Stale fixtures, dead mocks, and tests for removed modules should be deleted or rewritten.
- Implemented product capabilities, including Honcho-related integration, are part of the supported surface and should be validated instead of removed.
- Changes should converge the repo toward SSOT. Do not add a second entrypoint, hidden compatibility shim, or silent fallback path.
