# Novel Engine

Novel Engine is a narrative simulation platform with a canonical FastAPI backend and a Vite-based frontend. The repository is being converged onto a single source of truth: one backend app, one frontend app, one test surface, and no legacy compatibility layer.

## Canonical entrypoints

- `src/apps/api/main.py`: canonical backend application entrypoint
- `frontend/`: canonical frontend workspace
- `tests/`: source-backed backend, contract, and infrastructure tests

## Local development

### Backend

```bash
uv sync --extra dev --extra test --frozen
uv run pytest -q
uv run pytest \
  tests/unit/infrastructure \
  tests/apps/api/test_health.py \
  --cov=src/shared/infrastructure/auth \
  --cov=src/shared/infrastructure/config \
  --cov=src/shared/infrastructure/health \
  --cov=src/shared/infrastructure/persistence \
  --cov-report=term-missing \
  --cov-fail-under=80 \
  -q
uv run pytest \
  tests/shared/infrastructure/circuit_breaker \
  tests/shared/infrastructure/middleware \
  tests/apps/api/middleware \
  --cov=src/shared/infrastructure/circuit_breaker \
  --cov=src/shared/infrastructure/middleware \
  --cov=src/apps/api/middleware \
  --cov-report=term-missing \
  --cov-fail-under=80 \
  -q
uv run pytest \
  tests/shared/infrastructure/honcho \
  tests/contexts/ai \
  --cov=src/shared/infrastructure/honcho \
  --cov=src.shared.infrastructure.health.checks.honcho_health_check \
  --cov=src/contexts/ai/infrastructure/providers \
  --cov-report=term-missing \
  --cov-fail-under=80 \
  -q
uv run ruff check src tests
uv run mypy \
  src \
  tests \
  --no-error-summary \
  --show-column-numbers
uv run lint-imports
uv run python scripts/qa/check_openapi_snapshot.py
uv run python scripts/qa/run_api_public_audit.py
```

Runtime configuration is loaded from `NovelEngineSettings` and environment
variables. The YAML files under `config/examples/` are examples only; they are
not loaded as production configuration by the canonical FastAPI app.

When `pyproject.toml` dependencies change, refresh and commit `uv.lock` in the same change:

```bash
uv lock
```

If you want the optional Honcho integration installed locally, use:

```bash
uv sync --extra dev --extra test --extra honcho --frozen
```

PR CI does not require live Honcho credentials. The default Honcho and AI provider
tests use mocks and deterministic providers; live Honcho smoke remains opt-in with
`ENABLE_HONCHO_TESTS=1`.

### Frontend

```bash
npm --prefix frontend install
npm --prefix frontend run type-check
npm --prefix frontend run test:coverage
npm --prefix frontend run build
npm --prefix frontend run test:e2e:smoke
npm --prefix frontend run test:e2e:full-audit
npm --prefix frontend run audit:dependencies
npm --prefix frontend run audit:exports
```

`test:e2e:smoke` and `test:e2e:full-audit` launch the canonical backend and frontend stack through Playwright.

### Health semantics

- `GET /health` always returns HTTP `200`. Use `overall_status` and `components.*.status` in the response body for observability and alerting.
- `GET /health/ready` keeps `200/503` readiness semantics and is the probe endpoint for traffic orchestration.

When backend routes or response contracts change, refresh the canonical OpenAPI snapshot:

```bash
uv run python scripts/qa/check_openapi_snapshot.py --write
```

### DashScope long-form gate

The release-grade long-form validation path now has two modes:

- PR gate: GitHub Actions runs `DashScope Longform Gate` against every in-repo pull request targeting protected branches. It writes artifacts and a job summary, but it does not rewrite checked-in evidence files.
- Canonical refresh: a manual run updates the checked-in UAT evidence under `docs/reports/uat/` after a human-reviewed baseline is confirmed.

```bash
uv run python scripts/uat/run_dashscope_longform_uat.py --target-chapters 20 --write-canonical-reports
```

The canonical refresh command starts a clean local backend, uses the real HTTP API with DashScope, and writes:

- `docs/reports/uat/LONGFORM_DASHSCOPE_LIVE_EVIDENCE.md`
- `docs/reports/uat/LONGFORM_DASHSCOPE_LIVE_EVIDENCE.json`

See [docs/reports/uat/INDEX.md](docs/reports/uat/INDEX.md) and [docs/reports/uat/VERIFICATION_MATRIX.md](docs/reports/uat/VERIFICATION_MATRIX.md) for the full acceptance model.

## Testing model

- `uv run pytest -q` is the default backend behavior gate.
- Platform infrastructure coverage is gated at 80% across auth, config, health, and persistence modules.
- Circuit breaker and middleware coverage is gated at 80% across shared circuit breaker, shared middleware, and API middleware modules.
- Honcho and AI provider infrastructure coverage is gated at 80% with mock-based tests; live DashScope and Honcho credentials are not required for PR CI.
- External-service-heavy tests are opt-in through explicit environment flags in `tests/conftest.py`.
- Frontend smoke and full-audit coverage are exercised with Playwright against the canonical backend and frontend stack.
- Frontend dependency drift is gated with `npm --prefix frontend run audit:dependencies` (Knip-based static audit).
- Frontend export-surface drift is gated with `npm --prefix frontend run audit:exports` (Knip exports audit).
- Frontend security advisories are gated with `npm --prefix frontend audit --audit-level=high`.
- OpenAPI snapshot drift is gated with `uv run python scripts/qa/check_openapi_snapshot.py`.
- Public API audit is enforced via `uv run python scripts/qa/run_api_public_audit.py` and must keep method+path coverage at 100%.
- CI runs backend quality on the canonical backend surface, backend tests, 80% platform and circuit/middleware coverage floors, frontend platform coverage, frontend validation, frontend full-audit, public API audit, OpenAPI snapshot check, import-linter, and CodeQL.
- `DashScope Longform Gate` is a required PR check for same-repo pull requests into protected branches.
- The canonical checked-in UAT evidence is refreshed manually; normal PR gate runs only upload artifacts.
- DashScope live provider contracts and long-form UAT remain manual or opt-in through `ENABLE_DASHSCOPE_TESTS=1` plus `DASHSCOPE_API_KEY`.
- The long-form gate is only green when the real run reaches `publish=success` with `warning=0` and `blocker=0`.
- CodeQL scans the canonical source surface only; generated caches and build outputs are excluded, and default-branch merges must keep the scan clean or use documented suppressions for confirmed false positives. See [docs/security/codeql-alerts.md](docs/security/codeql-alerts.md).

## Repository hygiene rules

- Generated artifacts such as `__pycache__`, coverage output, Playwright reports, and temporary scratch directories are not source of truth.
- Checked-in tests must validate live source-backed behavior. Stale fixtures, dead mocks, and tests for removed modules should be deleted or rewritten.
- Implemented product capabilities, including Honcho-related integration, are part of the supported surface and should be validated instead of removed.
- Changes should converge the repo toward SSOT. Do not add a second entrypoint, hidden compatibility shim, or silent fallback path.
- Dependabot updates should be merged promptly once green; keep bot branches disposable by closing stale or superseded PRs and deleting merged branches automatically.
