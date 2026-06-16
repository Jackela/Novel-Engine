# AGENTS.md — Novel-Engine AI Contributor Guide

> This file tells AI coding assistants how to work safely in this repository.
> Human maintainers: keep this up to date. AI assistants: read this before every task.

## 1. Project Overview

**Name:** Novel-Engine / Novel Studio 0.3.0
**Stack:** Python 3.11+ (FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 + SQLite), React 18 + Vite + TypeScript
**Package managers:** `uv` (Python), `pnpm` (Node, workspace root + frontend)
**Current status:** Audit remediation branch ready for staging validation.

The project is organized as **Clean Architecture / DDD**:

```
src/
  apps/
    api/          # FastAPI application entry
    cli/          # Operational CLI
  contexts/
    studio/       # Main domain: projects, documents, AI proposals, exports
      domain/
      application/
        services/ # Per-service modules (project, document, ai, export, job, etc.)
        facade.py # Thin coordinator over services
      infrastructure/
      interface/
    ai/           # Text-generation providers (mock, dashscope, openai_compatible)
    shared/       # Shared domain primitives
  shared/
    infrastructure/  # Config, logging, middleware, rate-limit, health
tests/            # pytest backend tests
alembic/versions/ # Database migrations — READ ONLY for AI
```

## 2. Architecture Rules

- **Domain layer** (`src/contexts/*/domain/`) must NOT import infrastructure or interface layers.
- **Application layer** (`src/contexts/*/application/`) orchestrates domain logic and uses ports.
- **Infrastructure layer** (`src/contexts/*/infrastructure/`) implements ports and talks to DB/external services.
- **Interface layer** (`src/contexts/*/interface/`) handles HTTP/API/presentation concerns.
- The project uses **import-linter** (`.importlinter`) to enforce layer boundaries. Do not break contracts.

## 3. Absolute Forbidden Zones (AI must NOT modify)

- `alembic/versions/*` — database migrations
- `.env*`, `config/env/*` — environment and secrets
- `data/*.sqlite3`, `data/backups/*`, `.coverage` — runtime data
- `AUDIT_REPORT_Linus.md` — read-only reference
- `Makefile`, `justfile`, `.pre-commit-config.yaml` — build/tooling configs

## 4. Coding Red Lines

- **Never use bare `except Exception`.** Catch specific exception types.
- **Never use SQL/FTS5 string concatenation.** Use parameterized queries or strict escaping.
- **Never delete existing `raise`, `assert`, `validate`, `sanitize`, `escape`, `auth`, `permission` code.**
- **Never introduce new dependencies** (`npm install`, `pip install`, `uv add`) without explicit human approval.
- **Never modify tests** unless the audit finding explicitly requires it.
- **Python functions should be < 50 lines.** If larger, extract helpers.
- **React components should be < 200 lines.** If larger, split into sub-components and hooks.
- **All new Python functions must have type annotations.**

## 5. One-Command Validation

Always run these after any change:

```bash
# Backend
uv run pytest -q
uv run mypy src
uv run ruff check src tests
uv run bandit -r src
uv run lint-imports

# Frontend
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend type-check
corepack pnpm --dir frontend test:unit
corepack pnpm --dir frontend build

# Full validation
corepack pnpm spec:validate
```

Note: `mypy src tests` currently passes.

## 6. Common AI Pitfalls in This Codebase

1. **`studio_store` compatibility facade**
   `src/contexts/studio/application/services/facade.py` exposes a global `studio_store`. It must be configured before use. New code should prefer dependency injection via FastAPI `Depends`. Tests may need `settings_module.reset_settings()` and `sys.modules` cleanup.

2. **Module-level singletons**
   Do not introduce new import-time side effects (e.g., creating DB engines or FastAPI apps at module import time).

3. **FTS5 search**
   `DocumentService.search` reduces input to strict tokens before calling parameterized FTS5 `MATCH`. Any change here must include malicious-input tests.

4. **AI provider error handling**
   Providers catch specific transport/JSON/value exceptions. Do not reintroduce broad catches that hide programming errors.

5. **Frontend size**
   `StudioPage.tsx` was split in a recent refactor. Do not reintroduce god components. Keep components < 200 lines.

6. **SSOT / repo hygiene / OpenAPI snapshot checks**
   `scripts/qa/check_ssot.py`, `check_repo_hygiene.py`, `check_openapi_snapshot.py` enforce product naming and API contract. A change that passes tests may still fail these.

## 7. Safe Task Size

- **One task = one audit finding or one small feature.**
- **Maximum 3 files per AI session.** If more are needed, stop and ask for approval.
- **One finding at a time.** Do not carry context across findings. Reset the conversation between findings.

## 8. Git Workflow

```bash
# Before AI session
just snapshot        # or: git add -A && git commit -m "pre-ai-snapshot"

# After AI session
just check           # run regression checks
just validate        # run full validation
```

If anything goes wrong:

```bash
just panic           # kill AI processes and rollback to last snapshot
```

## 9. How to Read the Audit Report

`AUDIT_REPORT_Linus.md` contains findings with severity ratings:

- **CRITICAL** — fix first, do not ignore
- **MAJOR** — important, plan soon
- **MINOR** — polish, can be deferred

Each finding has:
- File/location
- Description
- Why it matters
- Fix direction

AI should propose a specific change list matching one finding, wait for approval, then implement.

## 10. Emergency Contacts

- If the AI starts modifying forbidden zones, stop it immediately.
- If tests pass but `make validate` / `just validate` fails, check the QA scripts in `scripts/qa/`.
- If the AI introduces a new dependency, revert it unless explicitly approved.
