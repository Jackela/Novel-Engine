# PROJECT KNOWLEDGE BASE — Novel-Engine

> Repository-wide instructions. Deeper `AGENTS.md` files add local rules and take precedence within their directories.

## OVERVIEW

Novel Engine 0.4.0 is a self-hosted writing studio. Backend: Node.js 24, Fastify v5, TypeBox, Drizzle (better-sqlite3), SQLite. Frontend: React 19, Vite, TypeScript. Package manager: pnpm 11 (workspace: `frontend/` + `server/`). The Python stack is retired at git tag `python-final` (0.3.x); history is the archive.

Domain vocabulary is defined in `CONTEXT.md`; use its canonical terms in code names, docs, and discussion.

## STRUCTURE

```text
server/                   # TS backend (ADR-0002): Fastify app, CLI, gates, Node QA twins
├── src/apps/             # api (buildApp factory) and cli composition roots
├── src/contexts/
│   ├── studio/           # Projects, documents, revisions, jobs, reviews, exports, volumes, lore, resident context, usage
│   └── ai/               # Structured text generation: application services, provider HTTP routes, streaming adapters
├── src/shared/           # Cross-cutting domain and infrastructure
├── scripts/qa/           # SSOT, hygiene, size, migration-channel, OpenAPI gates
├── qa-baselines/         # Frozen OpenAPI snapshot (code-first, regenerated deliberately)
└── drizzle/              # SQL migrations (FTS5 DDL hand-written inside migration files)
frontend/                 # React application, generated API types, browser tests
openspec/                 # Canonical product specification (novel-engine capability)
docs/adr/                 # Architecture decision records
```

Generated/runtime trees such as caches, `htmlcov/`, `frontend/coverage/`, `frontend/dist/`, `server/dist/`, `node_modules/`, `test-results/`, and `data/` are not architecture.

## WHERE TO LOOK

| Task | Location | Notes |
|---|---|---|
| Build the API app | `server/src/apps/api/app.ts` | Canonical `buildApp()` factory; plugins via injectable options |
| CLI entry | `server/src/apps/cli/main.ts` | `serve`, `import`, `backup`, `doctor` |
| Add HTTP behavior | `server/src/contexts/studio/interface/http/` | Thin routes; TypeBox schemas; services via `StudioStore` |
| Change workflows | `server/src/contexts/studio/application/` | Per-capability services behind ports |
| Change persistence | `server/src/contexts/studio/infrastructure/` | Drizzle store parts; FTS5 SQL lives in `db/` helpers |
| Change AI providers | `server/src/contexts/ai/infrastructure/` | Factory plus deterministic/DashScope/OpenAI-compatible adapters |
| Change AI HTTP surface | `server/src/contexts/ai/interface/http/provider_routes.ts` | Provider routes mounted by `buildApp`; application ports in `server/src/contexts/ai/application/ports/` |
| Change volumes/lore | `server/src/contexts/studio/interface/http/volume_routes.ts`, `server/src/contexts/studio/interface/http/lore_routes.ts` | Volume and lore entry HTTP behavior; services in `server/src/contexts/studio/application/volume_service.ts`, `lorebook.ts` |
| Change usage reporting | `server/src/contexts/studio/interface/http/job_routes.ts` | `/api/projects/:projectId/usage`; aggregation via `jobHistory.aggregateProjectUsage` |
| Change SSE streaming | `server/src/contexts/studio/interface/http/proposal_routes.ts` | `text/event-stream` proposal generation; stream orchestration in `server/src/contexts/studio/application/proposal_streaming.ts` |
| Change config/env | `server/src/shared/infrastructure/config/server_config.ts` | `.env.local` + process env; startup guards |
| Change frontend API contract | `frontend/src/app/api.ts`, `frontend/src/app/types/studio.ts` | Derive from `frontend/generated/api-types.ts` (`pnpm --dir frontend gen:api-types`) |
| Change Studio UI | `frontend/src/features/studio/` | Page shell, hooks, and panels |
| Add backend coverage | `server/tests/` | vitest + Fastify `inject()`; hermetic temp data dirs |
| Validate policy | `server/scripts/qa/`, `.github/workflows/ci.yml` | CI is the authoritative full gate; run twins via `pnpm --dir server gates` |

## CODE MAP

| Symbol | Location | Role / reach |
|---|---|---|
| `buildApp` | `server/src/apps/api/app.ts` | API composition root; used by CLI, tests, OpenAPI snapshot |
| `runCli` | `server/src/apps/cli/main.ts` | Operational CLI: serve/import/backup/doctor |
| `DrizzleStudioStore` | `server/src/contexts/studio/infrastructure/` | Persistence implementation used by API/CLI/tests |
| `loadServerConfig` | `server/src/shared/infrastructure/config/server_config.ts` | Env resolution + production startup guards |
| `readWorkspaceVersion` | `server/src/shared/infrastructure/workspace_manifest.ts` | Release-version SSOT reader (server/package.json) |
| `buildFtsMatchQuery` | `server/src/contexts/studio/application/fts_match_query.ts` | Strict token reduction before parameterized FTS5 MATCH |
| `assembleResidentContext` | `server/src/contexts/studio/application/resident_context.ts:158` | Resident context assembler (ADR-0004 layer 1) feeding every proposal generation |
| `api` | `frontend/src/app/api.ts` | Shared HTTP client used by pages, hooks, and tests |
| `StudioPage` | `frontend/src/features/studio/StudioPage.tsx` | Route-level UI composition shell |

## ARCHITECTURE CONTRACTS

- Domain (`src/contexts/*/domain`, `src/shared/domain`) imports neither application, infrastructure, nor interface.
- Application orchestrates domain behavior through ports; it must not import infrastructure or interface.
- Infrastructure implements ports and owns Drizzle, files, and external transports.
- Interface owns HTTP/request/response concerns and must not import infrastructure directly.
- Contexts do not import `src.apps`; `src.shared` does not import bounded contexts. The `ai` context has its own domain/application/interface/infrastructure layers, but code outside `ai` (except the composition root) may import it only through its application ports, and `ai` never imports `studio`.
- `server/.dependency-cruiser.cjs` is executable policy, not documentation.

## ABSOLUTE FORBIDDEN ZONES

- `.env*`, `config/env/*`
- `data/*.sqlite3`, `data/backups/*`
- `AUDIT_REPORT_Linus.md`
- `Makefile`, `justfile`

Require separate human confirmation before changing root package/lock files, `README.md`, `compose.yaml`, or `Dockerfile`. Never introduce dependencies without explicit approval.

## CODING RED LINES

- Never swallow unexpected errors; catch specific transport, parsing, value, or domain exceptions; programming errors must remain visible.
- Never construct SQL/FTS5 expressions by string concatenation. Parameterize or apply strict token reduction.
- Never delete existing `throw`, `assert`, `validate`, `sanitize`, `escape`, `auth`, or `permission` logic.
- Never introduce import-time database handles, Fastify app instances, or magic proxies; runtime wiring happens in composition roots.
- Do not modify tests unless the finding explicitly requires it.
- Keep functions small (file-size gate enforces limits); split orchestration.
- React components should stay below 200 lines; split orchestration into hooks/components.

## PROJECT-SPECIFIC INVARIANTS

- Each app instance owns its database handle through `buildApp` options; handlers reach services through the injected store; tests use Fastify `inject()`.
- CLI commands build short-lived app instances; no shared runtime through module globals.
- FTS5 input is reduced to strict tokens (`buildFtsMatchQuery`) before parameterized MATCH; preserve malicious-input coverage.
- AI providers normalize only known transport/HTTP/JSON/provider failures; the keyed provider never falls back to the mock.
- Revisions and snapshots are immutable references. Exports must write from the exact snapshot revision set.
- The OpenAPI baseline (`server/qa-baselines/openapi.current.json`) regenerates deliberately via `pnpm --dir server openapi:snapshot`; route-adding changes must regenerate it.
- Frontend requests go through `frontend/src/app/api.ts`; keep CSRF, credentials, abort, and error-envelope semantics intact.
- Product identity and API shape are enforced by SSOT, repo-hygiene, file-size, migration-channel, OpenAPI snapshot, and OpenSpec gates.
- Migrations generate only through `pnpm --dir server db:generate`; never hand-edit `server/drizzle/meta/*`.

## WORKFLOW CONSTRAINTS

- One task is one audit finding or one small feature.
- Prefer surgical changes; do not rewrite whole modules.
- Run relevant tests before and after changes. Review `git diff` and preserve unrelated worktree edits.
- Do not carry implementation context across unrelated findings.

## HARNESS ENGINEERING OVERLAY

- Start from the owning layer, current baseline, and matching validation surface before editing.
- Prefer baseline-first work: reproduce the failure, inspect the existing contract, or capture the current behavior before changing it.
- Keep evidence replayable. Report exact commands, browser/API flows, or skipped checks with reasons.
- Validate through the surface that owns the change: service/API tests for backend behavior, browser workflows for UI behavior, import/spec/SSOT gates for contracts.
- Treat generated outputs, caches, local evidence, and ignored agent configuration as harness state, not product architecture.

## VALIDATION

```bash
# Server (TS backend)
pnpm --dir server gates
pnpm --dir server type-check
pnpm --dir server lint
pnpm --dir server arch
pnpm --dir server test

# Frontend
pnpm --dir frontend lint
pnpm --dir frontend format:check
pnpm --dir frontend type-check
pnpm --dir frontend test:unit
pnpm --dir frontend build

# Product/spec
pnpm spec:validate
```

CI additionally runs the API-types drift check, React static diagnostics, Playwright workflows against the TS backend, and a container persistence check. `make validate` / `just validate` wrap a subset; consult `.github/workflows/ci.yml` for the full contract.

## GIT / AUDIT

Before AI work use `just snapshot` (or a deliberate snapshot commit). After work use `just check` and `just validate`. `just panic` is the emergency rollback path and must not be invoked casually.

Audit findings in `AUDIT_REPORT_Linus.md` are read-only references. Match one finding, its stated location, and its fix direction; do not broaden scope merely because nearby cleanup is possible.

### Issue tracker

Issues and specs for this repo live as GitHub issues on `Jackela/Novel-Engine`.
Tracker configuration, including the Wayfinding operations section, is
`docs/agents/issue-tracker.md`; triage labels are `docs/agents/triage-labels.md`.

## Agent skills

### Issue tracker

GitHub Issues in `Jackela/Novel-Engine` are the work tracker. Before creating,
triaging, claiming, resolving, or mapping a ticket, read
`docs/agents/issue-tracker.md`.

### Triage labels

Use the five canonical triage roles mapped in
`docs/agents/triage-labels.md` when triaging GitHub issues.

### Domain docs

This repository is single-context: use root `CONTEXT.md` for domain vocabulary
and the relevant decision record in `docs/adr/` for architecture decisions.
See `docs/agents/domain.md`.
