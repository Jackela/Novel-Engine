# PROJECT KNOWLEDGE BASE — Novel-Engine

> Repository-wide instructions. Deeper `AGENTS.md` files add local rules and take precedence within their directories.

## OVERVIEW

Novel Studio 0.3.1 is a self-hosted writing studio. Backend: Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, SQLite. Frontend: React 19, Vite, TypeScript. Package managers: `uv` and pnpm 11.

## STRUCTURE

```text
src/
├── apps/                 # FastAPI and CLI composition roots
├── contexts/
│   ├── studio/           # Projects, documents, revisions, jobs, reviews, exports
│   └── ai/               # Structured text-generation ports and providers
└── shared/               # Cross-cutting domain and infrastructure
frontend/                 # React application and browser tests
tests/                    # Backend unit, API, contract, and e2e tests
scripts/qa/               # SSOT, hygiene, size, and OpenAPI gates
openspec/                 # Canonical product specifications
alembic/versions/         # Migrations; read-only for AI
```

Generated/runtime trees such as `.venv/`, caches, `htmlcov/`, `frontend/coverage/`, `frontend/dist/`, `node_modules/`, `test-results/`, and `data/` are not architecture.

## WHERE TO LOOK

| Task | Location | Notes |
|---|---|---|
| Build the API app | `src/apps/api/main.py` | Canonical `create_application()` factory |
| Own runtime state | `src/apps/api/runtime.py` | Database/store lifecycle via `app.state` |
| Add HTTP behavior | `src/contexts/studio/interface/http/` | Thin routers; injected `StudioStoreDependency` |
| Change workflows | `src/contexts/studio/application/services/` | Per-capability services behind `StudioStore` |
| Change persistence | `src/contexts/studio/infrastructure/repository/` | SQLAlchemy repository mixins |
| Change AI providers | `src/contexts/ai/infrastructure/providers/` | Factory plus deterministic/DashScope/OpenAI adapters |
| Change frontend API contract | `frontend/src/app/api.ts`, `frontend/src/app/types/studio.ts` | Keep synchronized with OpenAPI |
| Change Studio UI | `frontend/src/features/studio/` | Page shell, hooks, and panels |
| Add backend coverage | `tests/` | Reuse canonical fixtures in `tests/conftest.py` |
| Validate policy | `scripts/qa/`, `.github/workflows/ci.yml` | CI is the authoritative full gate |

## CODE MAP

| Symbol | Location | Role / reach |
|---|---|---|
| `create_application` | `src/apps/api/main.py` | API composition root; used by CLI, tests, OpenAPI snapshot |
| `StudioRuntime` / `lifespan` | `src/apps/api/runtime.py` | Creates, attaches, initializes, and disposes runtime |
| `StudioStore` | `src/contexts/studio/application/services/facade.py` | Main application facade used by API, CLI, and tests |
| `StudioServiceRegistry` | `src/contexts/studio/application/services/facade_base.py` | Constructs per-capability service graph |
| `SqlAlchemyStudioRepository` | `src/contexts/studio/infrastructure/repository/` | Persistence implementation used by API/CLI/tests |
| `create_text_generation_provider` | `src/contexts/ai/infrastructure/providers/provider_factory.py` | Provider selection/configuration hub |
| `api` | `frontend/src/app/api.ts` | Shared HTTP client used by pages, hooks, and tests |
| `StudioPage` | `frontend/src/features/studio/StudioPage.tsx` | Route-level UI composition shell |

## ARCHITECTURE CONTRACTS

- Domain (`src/contexts/*/domain`, `src/shared/domain`) imports neither application, infrastructure, nor interface.
- Application orchestrates domain behavior through ports; it must not import infrastructure or interface.
- Infrastructure implements ports and owns SQLAlchemy, files, and external transports.
- Interface owns HTTP/request/response concerns and must not import infrastructure directly.
- Contexts do not import `src.apps`; `src.shared` does not import bounded contexts.
- `.importlinter` is executable policy, not documentation.

## ABSOLUTE FORBIDDEN ZONES

- `alembic/versions/*`
- `.env*`, `config/env/*`
- `data/*.sqlite3`, `data/backups/*`, `.coverage`
- `AUDIT_REPORT_Linus.md`
- `src/events/outbox.py`, `src/apps/workers/__init__.py`
- `Makefile`, `justfile`, `.pre-commit-config.yaml`

Require separate human confirmation before changing `pyproject.toml`, root package/lock files, `README.md`, `compose.yaml`, or `Dockerfile`. Never introduce dependencies without explicit approval.

## CODING RED LINES

- Never use bare `except Exception`; catch specific transport, parsing, value, or domain exceptions.
- Never construct SQL/FTS5 expressions by string concatenation. Parameterize or apply strict token reduction.
- Never delete existing `raise`, `assert`, `validate`, `sanitize`, `escape`, `auth`, or `permission` logic.
- Never introduce import-time database engines, FastAPI apps, store instances, or magic proxies.
- Do not modify tests unless the finding explicitly requires it.
- New Python functions require type annotations and should stay below 50 lines.
- React components should stay below 200 lines; split orchestration into hooks/components.

## PROJECT-SPECIFIC INVARIANTS

- Each FastAPI app owns one `StudioRuntime`/`StudioStore` through `app.state`; handlers receive it through `Depends`.
- CLI commands create short-lived runtime objects. Do not share API runtime through module globals.
- `DocumentService.search` reduces input to strict tokens before parameterized FTS5 `MATCH`; preserve malicious-input coverage.
- AI providers normalize only known transport/HTTP/JSON/provider failures; programming errors must remain visible.
- Revisions and snapshots are immutable references. Exports must write from the exact snapshot revision set.
- Frontend requests go through `frontend/src/app/api.ts`; keep CSRF, credentials, abort, and error semantics intact.
- Product identity and API shape are enforced by SSOT, repo-hygiene, file-size, OpenAPI snapshot, and OpenSpec gates.

## WORKFLOW CONSTRAINTS

- One task is one audit finding or one small feature.
- Maximum three modified files per AI session. Stop and request approval if more are required.
- Prefer surgical changes; do not rewrite whole modules.
- Run relevant tests before and after changes. Review `git diff` and preserve unrelated worktree edits.
- Do not carry implementation context across unrelated findings.
- For AI-assisted code changes, run `uv run python scripts/ai/regression_check.py`; PR CI enforces the safety/security diff checks while process rules enforce scope.

## HARNESS ENGINEERING OVERLAY

- Start from the owning layer, current baseline, and matching validation surface before editing.
- Prefer baseline-first work: reproduce the failure, inspect the existing contract, or capture the current behavior before changing it.
- Keep evidence replayable. Report exact commands, browser/API flows, or skipped checks with reasons.
- Validate through the surface that owns the change: service/API tests for backend behavior, browser workflows for UI behavior, import/spec/SSOT gates for contracts.
- Treat generated outputs, caches, local evidence, and ignored agent configuration as harness state, not product architecture.

## VALIDATION

```bash
# Backend
uv run pytest -q
uv run mypy src tests
uv run ruff format --check src tests scripts
uv run ruff check src tests scripts
uv run bandit -r src
uv run lint-imports

# Frontend
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend type-check
corepack pnpm --dir frontend test:unit
corepack pnpm --dir frontend build

# Product/spec
corepack pnpm spec:validate
```

CI additionally runs SSOT, repo hygiene, file-size, OpenAPI snapshot, frontend format, Playwright smoke, and container persistence checks. `make validate` is only a partial gate; consult `.github/workflows/ci.yml` for the full contract.

## GIT / AUDIT

Before AI work use `just snapshot` (or a deliberate snapshot commit). After work use `just check` and `just validate`. `just panic` is the emergency rollback path and must not be invoked casually.

Audit findings in `AUDIT_REPORT_Linus.md` are read-only references. Match one finding, its stated location, and its fix direction; do not broaden scope merely because nearby cleanup is possible.
