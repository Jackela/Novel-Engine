# Novel Engine

Novel Engine is a local-first novel writing engine. Complete chapter
Markdown files are the manuscript source of truth; structured JSON is kept as
sidecar evidence for continuity, review, and recovery. The FastAPI backend and
Vite frontend remain available as platform adapters, but the primary writing
path is now the `novel-engine` CLI.

## Canonical entrypoints

- `src/contexts/narrative/application/services/local_writing_engine.py`: local-first writing engine
- `src/apps/cli/novel_engine.py`: thin CLI adapter for the writing engine
- `src/apps/api/routes/workspaces.py`: workspace/job API adapter
- `src/apps/api/main.py`: canonical backend application entrypoint
- `frontend/`: canonical frontend workspace
- `tests/`: source-backed backend, contract, and infrastructure tests

## Local writing workflow

```bash
uv run novel-engine init \
  --workspace .data/my-novel \
  --title "The Salt Ledger" \
  --genre mystery \
  --premise "A courier receives a page that names debts before they happen." \
  --target-chapters 3
uv run novel-engine draft --workspace .data/my-novel --chapter 1
uv run novel-engine review --workspace .data/my-novel
uv run novel-engine export --workspace .data/my-novel
```

Workspace layout:

- `story.yaml`: story premise, style, target chapter count, and continuity notes
- `manuscript/chapters/chapter-001.md`: authoritative chapter prose
- `artifacts/runs/{run_id}/`: events, raw model output, sidecar metadata, and manifests
- `artifacts/reviews/latest.json`: blocker/warning/suggestion review report
- `exports/manuscript.md`: combined manuscript export

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
uv run python scripts/qa/check_repo_hygiene.py
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

## Optional integrations

The local writing engine does not require Honcho, Chroma, Postgres, or a live
LLM provider. Those integrations are optional adapters around the local-first
core and should not be required for CLI drafting, workspace jobs, or the
default frontend smoke path.

```bash
uv sync --extra dev --extra test --extra honcho --extra chroma --extra postgres --frozen
```

- Honcho tests use mocks by default; live Honcho smoke is opt-in with `ENABLE_HONCHO_TESTS=1`.
- Chroma live smoke is an optional integration job and uses `ENABLE_CHROMA_TESTS=1`.
- DashScope long-form UAT is release evidence, not a dependency for local writing.
- `npm audit --audit-level=high` is the frontend security gate; current lockfile has no high+ advisories.

### Git hooks

The repository tracks `.pre-commit-config.yaml` as the local Git hook source of
truth. Do not rely on `PRE_COMMIT_ALLOW_NO_CONFIG=1` for normal development; it
is only appropriate when temporarily working on a historical branch that does
not yet contain the hook configuration.

Install the Python dependencies and hooks after cloning or refreshing the
workspace:

```bash
uv sync --extra dev --extra test --frozen
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

The `pre-commit` stage runs fast deterministic checks. The `pre-push` stage runs
the strict local quality gate, including backend tests, OpenAPI/API audits,
frontend type checks, unit tests, build, Playwright smoke/full-audit tests, and
frontend dependency/export audits.

Manual hook runs:

```bash
uv run pre-commit run --all-files
uv run pre-commit run --hook-stage pre-push --all-files
```

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

The canonical refresh command starts a clean local backend, uses the real workspace API with DashScope, and writes:

- `docs/reports/uat/LONGFORM_DASHSCOPE_LIVE_EVIDENCE.md`
- `docs/reports/uat/LONGFORM_DASHSCOPE_LIVE_EVIDENCE.json`

See [docs/reports/uat/INDEX.md](docs/reports/uat/INDEX.md) and [docs/reports/uat/VERIFICATION_MATRIX.md](docs/reports/uat/VERIFICATION_MATRIX.md) for the full acceptance model.

## Testing model

- `uv run pytest -q` is the default backend behavior gate.
- Shared infrastructure coverage is gated at 80% across auth, config, health, and persistence modules.
- Circuit breaker and middleware coverage is gated at 80% across shared circuit breaker, shared middleware, and API middleware modules.
- Optional integration coverage is gated with mock-based Honcho and AI provider tests; live DashScope and Honcho credentials are not required for PR CI.
- External-service-heavy tests are opt-in through explicit environment flags in `tests/conftest.py`.
- Frontend smoke and full-audit coverage are exercised with Playwright against the canonical backend and frontend stack.
- Frontend dependency drift is gated with `npm --prefix frontend run audit:dependencies` (Knip-based static audit).
- Frontend export-surface drift is gated with `npm --prefix frontend run audit:exports` (Knip exports audit).
- Frontend security advisories are gated with `npm --prefix frontend audit --audit-level=high`.
- OpenAPI snapshot drift is gated with `uv run python scripts/qa/check_openapi_snapshot.py`.
- Public API audit is enforced via `uv run python scripts/qa/run_api_public_audit.py` and must keep method+path coverage at 100%.
- Repository hygiene is gated with `uv run python scripts/qa/check_repo_hygiene.py`; external provider API versions are allowlisted, but project API versioning and removed story pipeline symbols are not.
- CI runs backend quality on the canonical backend surface, backend tests, 80% shared infrastructure and circuit/middleware coverage floors, frontend validation, frontend full-audit, public API audit, OpenAPI snapshot check, import-linter, repository hygiene, and CodeQL.
- `DashScope Longform Gate` is a required PR check for same-repo pull requests into protected branches.
- The canonical checked-in UAT evidence is refreshed manually; normal PR gate runs only upload artifacts.
- DashScope live provider contracts and long-form UAT remain manual or opt-in through `ENABLE_DASHSCOPE_TESTS=1` plus `DASHSCOPE_API_KEY`.
- The long-form gate is only green when the real run reaches `export=success` with `blocker=0`; warnings are kept as editorial advice and do not fail export.
- CodeQL scans the canonical source surface only; generated caches and build outputs are excluded, and default-branch merges must keep the scan clean or use documented suppressions for confirmed false positives. See [docs/security/codeql-alerts.md](docs/security/codeql-alerts.md).

## Repository hygiene rules

- Generated artifacts such as `__pycache__`, coverage output, Playwright reports, and temporary scratch directories are not source of truth.
- Checked-in tests must validate live source-backed behavior. Stale fixtures, dead mocks, and tests for removed modules should be deleted or rewritten.
- Optional integrations should stay isolated from the local-first writing path and be validated by explicit integration tests.
- Changes should converge the repo toward SSOT. Do not add a second entrypoint, hidden shim, or silent fallback path.
- Dependabot updates should be merged promptly once green; keep bot branches disposable by closing stale or superseded PRs and deleting merged branches automatically.
