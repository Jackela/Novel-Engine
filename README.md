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
  src \
  tests \
  --no-error-summary \
  --show-column-numbers
lint-imports
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

### DashScope long-form gate

The release-grade long-form validation path now has two modes:

- PR gate: GitHub Actions runs `DashScope Longform Gate` against every in-repo pull request targeting protected branches. It writes artifacts and a job summary, but it does not rewrite checked-in evidence files.
- Canonical refresh: a manual run updates the checked-in UAT evidence under `docs/reports/uat/` after a human-reviewed baseline is confirmed.

```bash
python scripts/uat/run_dashscope_longform_uat.py --target-chapters 20 --write-canonical-reports
```

The canonical refresh command starts a clean local backend, uses the real HTTP API with DashScope, and writes:

- `docs/reports/uat/LONGFORM_DASHSCOPE_LIVE_EVIDENCE.md`
- `docs/reports/uat/LONGFORM_DASHSCOPE_LIVE_EVIDENCE.json`

See [docs/reports/uat/INDEX.md](docs/reports/uat/INDEX.md) and [docs/reports/uat/VERIFICATION_MATRIX.md](docs/reports/uat/VERIFICATION_MATRIX.md) for the full acceptance model.

## Testing model

- `pytest -q` is the default backend gate.
- External-service-heavy tests are opt-in through explicit environment flags in `tests/conftest.py`.
- Frontend smoke coverage is exercised with Playwright against the canonical backend and frontend stack.
- CI runs backend quality on the canonical backend surface, backend tests, frontend validation, import-linter, and CodeQL.
- `DashScope Longform Gate` is a required PR check for same-repo pull requests into protected branches.
- The canonical checked-in UAT evidence is refreshed manually; normal PR gate runs only upload artifacts.
- The long-form gate is only green when the real run reaches `publish=success` with `warning=0` and `blocker=0`.
- CodeQL scans the canonical source surface only; generated caches and build outputs are excluded, and default-branch merges must keep the scan clean or use documented suppressions for confirmed false positives. See [docs/security/codeql-alerts.md](docs/security/codeql-alerts.md).

## Repository hygiene rules

- Generated artifacts such as `__pycache__`, coverage output, Playwright reports, and temporary scratch directories are not source of truth.
- Checked-in tests must validate live source-backed behavior. Stale fixtures, dead mocks, and tests for removed modules should be deleted or rewritten.
- Implemented product capabilities, including Honcho-related integration, are part of the supported surface and should be validated instead of removed.
- Changes should converge the repo toward SSOT. Do not add a second entrypoint, hidden compatibility shim, or silent fallback path.
- Dependabot updates should be merged promptly once green; keep bot branches disposable by closing stale or superseded PRs and deleting merged branches automatically.
