# Novel-Engine Remediation Report

**Date:** 2026-06-17
**Status:** Audit remediation branch in progress; completed items and remaining
work are tracked with evidence rather than summarized as "zero debt."

This file replaces the prior over-confident audit summary. The previous claim
of "zero remaining technical debt" was inaccurate because the repository still
contained unused infrastructure and several large, hard-to-edit modules.

## What Changed

- Hardened Studio search by reducing user input to a strict FTS5 token allow-list.
- Stopped swallowing unexpected AI/job exceptions; provider/domain failures are
  logged with traceback and persisted as failed jobs, while programming errors
  bubble.
- Removed module-import startup side effects for the API app and Studio database.
- Aligned default LLM settings to `mock` / `studio-copilot-v1`.
- Added project and document delete endpoints, including scoped authorization
  and FTS index cleanup.
- Split Studio application services and SQLAlchemy repository implementation
  into focused modules with facade exports.
- Split the Studio frontend surface into focused topbar, navigator, editor,
  inspector, and statusbar components.
- Deleted unused outbox, Result-monad/error-handler, circuit-breaker, generic
  health, YAML config loader, empty worker/cache/policy, and broken demo code.
- Consolidated environment documentation around the root `.env.example` and
  added `frontend/.env.example`.
- Added `AGENTS.md` and `CHANGELOG.md`.
- Added a CI file-size guard for newly introduced oversized source files.
- Cleaned Python tool configuration drift in `pyproject.toml`.
- Made export artifact writes atomic so failed writers do not publish partial
  files.
- Aligned README validation commands with the current CI and hidden QA gates.

## Validation

```bash
uv run python scripts/qa/check_file_sizes.py
uv run python scripts/qa/check_ssot.py
uv run python scripts/qa/check_repo_hygiene.py
uv run ruff check src tests
uv run bandit -r src
uv run mypy src
uv run mypy src tests
uv run lint-imports
uv run pytest -q
uv run python scripts/qa/check_openapi_snapshot.py
corepack pnpm spec:validate
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend format:check
corepack pnpm --dir frontend type-check
corepack pnpm --dir frontend test:unit
corepack pnpm --dir frontend build
```

## Remaining Non-Blocking Work

- Replace the legacy `StudioStore.__getattr__` compatibility proxy with explicit
  service injection.
- Pin or vendor Swagger UI assets and define an integrity policy.
- Consider adding broader frontend unit coverage for the newly extracted Studio
  components.
