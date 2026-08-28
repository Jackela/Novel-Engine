# Architecture overview

Novel Engine is a self-hosted, single-author writing studio. The backend is a
TypeScript server on Node 24 LTS: Fastify v5 with the TypeBox type provider for
HTTP, Drizzle ORM over better-sqlite3 for persistence, and SQLite as the
content authority. The frontend is a React 19 + Vite application served by the
same deployable. Code lives in a minimal pnpm workspace (`frontend/` +
`server/`), and the server is organized into bounded contexts — `studio`
(authoring), `ai` (text generation), and the `shared` kernel — whose import
boundaries are executable policy, not convention (`server/.dependency-cruiser.cjs`).
The stack decision is recorded in ADR-0001 through ADR-0003; the product
vocabulary lives in the root `CONTEXT.md`.

## Composition root and runtime composition

`buildApp()` in `server/src/apps/api/app.ts` is the composition root of the TS
server. It takes an injectable `AppOptions` object — logger, data directory,
session secret, CORS origins, trusted proxies, auth rate limit, AI provider
keys and factory, resolved `ServerConfig`, SPA dist directory, injectable clock,
and health probe — and wires every service onto one Fastify instance. There are
no module-global app instances and no import-time database handles: handlers
reach services through the options passed at registration time.

When a `dataDirectory` is configured, startup runs the persistence pipeline —
backup, migrations, restart recovery — through `openStudioDatabase()` before
the app serves traffic, and decorates the instance with a `StudioDatabase`
handle closed in an `onClose` hook. When it is absent, the app boots as a
database-free walking skeleton. Misconfigured production starts fail fast:
`assertStartupGuards()` runs before any side effect, so a bad start creates no
directories and opens no databases.

The CLI (`server/src/apps/cli/main.ts`: `serve`, `import`, `backup`, `doctor`)
builds short-lived app instances through the same `buildApp()` factory; no
state is shared through module globals between commands.

## Bounded contexts and enforced dependency direction

`server/src` is split into `src/apps` (composition roots), `src/contexts/studio`,
`src/contexts/ai`, and `src/shared`. Each context is layered into `domain`,
`application`, `infrastructure`, and `interface`. The contracts, enforced by
`server/.dependency-cruiser.cjs` and checked by `pnpm --dir server arch` in CI:

- Domain layers never import application, infrastructure, or interface layers.
- Application layers orchestrate domain behavior through ports; they never
  import infrastructure or interface code.
- Interface layers own HTTP concerns only — no direct infrastructure imports.
- Bounded contexts never import `src.apps`; `src.shared` never imports bounded
  contexts; and the `ai` context is a leaf provider module, importable only
  through its application ports, never importing `studio`.

Infrastructure is therefore supplied at composition points — `buildApp()` or a
CLI command — rather than selected by application services. `pnpm --dir server
arch` is executable policy: a violating import fails the build.

## Persistence: SQLite as content authority

SQLite (`novel-engine.sqlite3` in the configured data directory) is the
authority for projects, documents, revisions, snapshots, reviews, exports,
jobs, and auth state. `DrizzleStudioStore`
(`server/src/contexts/studio/infrastructure/`) implements the studio ports over
Drizzle + better-sqlite3; `DrizzleAuthStore` serves the shared auth store.
Schema changes go through drizzle-kit migrations in `server/drizzle/`,
generated only via `pnpm --dir server db:generate`; hand-editing
`server/drizzle/meta/*` is forbidden, and the migration-channel gate enforces
this.

Full-text search is the deliberate exception to ORM metadata: the FTS5 virtual
table DDL, triggers, and row cleanup are hand-written SQL inside the migration
files, and `MATCH` input is reduced to strict tokens by
`buildFtsMatchQuery()` (`server/src/contexts/studio/application/fts_match_query.ts`)
before reaching a parameterized query. SQL and FTS expressions are never built
by string concatenation.

Revisions and snapshots are immutable references. A conflict-checked save
creates a new revision; restore creates a new current revision from history
rather than rewriting it. Snapshots pin the exact revision selected for each
document, and both reviews and exports read from that frozen revision set —
never from live documents.

## AI providers: ports and adapters

The `ai` context is a ports-and-adapters leaf. Application code depends on the
`TextGenerationProviderFactory` port
(`server/src/contexts/ai/application/ports/text_generation.ts`); the
infrastructure factory (`server/src/contexts/ai/infrastructure/providers/text_provider_factory.ts`)
builds deterministic, DashScope, and OpenAI-compatible adapters. Provider
failures are normalized only for known transport, HTTP, JSON, and provider
error classes, and a keyed provider never falls back to the mock — a missing
API key fails explicitly. `AppOptions.textProviderFactory` lets tests inject
capturing providers.

## HTTP surface and the OpenAPI snapshot

Routes are thin: `server/src/contexts/studio/interface/http/` and
`server/src/contexts/ai/interface/http/` define TypeBox schemas and delegate to
services; shared routes (auth, health, version, SPA serving) live in
`server/src/shared/interface/http/`. The unified error envelope is registered
before route plugins, and the SPA wildcard registers last so the JSON API stays
distinct.

The API contract is code-first: Fastify swagger produces `/openapi.json`, and
the frozen snapshot `server/qa-baselines/openapi.current.json` is compared by
the OpenAPI gate. Route-adding changes must regenerate it deliberately via
`pnpm --dir server openapi:snapshot`. Frontend types are generated from the
same document (`frontend/generated/api-types.ts` via `pnpm --dir frontend
gen:api-types`), and a CI step fails on drift. Browser requests always go
through `frontend/src/app/api.ts`, whose CSRF, credentials, abort, and
error-envelope semantics are product invariants.

## Quality gates

CI (`.github/workflows/ci.yml`) is the authoritative full gate:

- The `validate` job (Node 22) installs locked pnpm dependencies, audits
  production dependency security, runs `pnpm --dir server gates` and
  `pnpm spec:validate`, then the full frontend suite (lint, format, type-check,
  unit tests, build), the generated API-types drift check, React static
  diagnostics, and Playwright Studio workflows against the built TS backend.
- The `server` job (Node 24) runs the workspace gates, `pnpm --dir server arch`
  (dependency-cruiser), type-check, lint, and the vitest suite (Fastify
  `inject()` against hermetic temp data dirs). A dependent container job
  verifies fresh install, persistence across restart, and deep-link serving.

The Node split is deliberate and current: product code targets Node 24 LTS
(server runtime, `server` job), while the `validate` job and the CodeQL
workflow still pin Node 22 for tooling. Treat both pins as facts of CI, not
drift to fix casually.

`pnpm --dir server gates` composes the five release gates: SSOT
(`readWorkspaceVersion` against `server/package.json`), repo hygiene, file
size limits, migration channel, and the OpenAPI snapshot.
`pnpm spec:validate` validates the OpenSpec product specification
(`openspec/`). CodeQL analyzes `javascript-typescript` only — the repository
is single-language — on pushes and pull requests to `main`/`develop` plus a
scheduled weekly run (`.github/workflows/codeql.yml`).

After source changes, rerun the release-equivalent commands in
`openwiki/quickstart.md` and wait for hosted `validate`, container, and CodeQL
jobs before merge.

## Change guidance

- Change runtime ownership or request access through `server/src/apps/api/app.ts`
  and its injectable `AppOptions` together; preserve per-app database lifecycle
  and `onClose` disposal.
- Add application behavior behind an application port and service before
  changing repository infrastructure; `pnpm --dir server arch`
  (dependency-cruiser) in CI verifies the layer rules.
- Preserve revision IDs in snapshots and the restore-as-new-revision behavior
  when modifying history or export paths; exports must write from the exact
  snapshot revision set.
- For export changes, keep snapshot comparison, chapter-only selection, and
  atomic output replacement intact; run the focused service tests plus the
  CI-equivalent backend/frontend checks as applicable.
- Route-adding changes regenerate the OpenAPI snapshot
  (`pnpm --dir server openapi:snapshot`); frontend contract changes regenerate
  the API types (`pnpm --dir frontend gen:api-types`).
- Migrations are generated only via `pnpm --dir server db:generate`; FTS5 DDL
  stays hand-written inside migration files, and FTS input keeps its strict
  token reduction.
