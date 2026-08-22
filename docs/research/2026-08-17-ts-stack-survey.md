# TS Stack Survey — runtime, framework, data layer, monorepo, codegen, migrations

- Date: 2026-08-17
- Ticket: [Research: TS stack survey (#243)](https://github.com/Jackela/Novel-Engine/issues/243), map [#242](https://github.com/Jackela/Novel-Engine/issues/242). Decision happens in the grilling ticket #244 — **this document is research, not a decision.**
- Evidence base: ADR-0001 (`docs/adr/0001-typescript-greenfield-rewrite.md`), pre-rewrite audit `docs/audits/2026-08-17-pre-rewrite-audit.md` (§5 R5 / R7-6, §4.2 B1, §4.3 C6 / C8 / C10, finding F-9 / F-10).
- Method: web survey of current (2026-08) primary sources — release schedules, official docs, open issue trackers — cross-checked against the audit's hard filters. All claims carry a source URL; unverified impressions are marked as such.

## Hard filters (from accepted constraints — non-negotiable)

1. **SQLite is the content authority.** WAL + per-connection PRAGMAs (`foreign_keys=ON`, WAL, `synchronous=NORMAL`, audit C6) and **FTS5** full-text search (audit B1, C10) must be first-class, including hand-written SQL that lives outside any ORM metadata.
2. **One deployable serves SPA + API** (SPA catch-all hosting, `main.py:156-183` analog; audit B10).
3. **One language** across the stack (TypeScript).
4. **Playwright e2e must pass before cutover** (ADR-0001). Playwright drives the deployed app over HTTP, so it is runtime-agnostic — it constrains *behavior parity*, not the runtime choice.

## Axis A — Runtime: Node LTS vs Bun vs Deno

### Node.js 24 (Active LTS)

- Node 24 is the Active LTS line as of 2026-08 (Active until 2026-10, Maintenance until 2028-04); Node 26 (released May 2026) is the Current line and enters LTS in Oct 2026. Sources: <https://endoflife.date/nodejs>, <https://www.herodevs.com/blog-posts/node-js-end-of-life-dates-you-should-be-aware-of>, <https://hidekazu-konishi.com/entry/nodejs_release_and_eol_timeline.html>.
- SQLite driver ecosystem is the deepest of the three:
  - **better-sqlite3** — the boring, mature, synchronous driver; ships SQLite compiled with FTS5 enabled; the de-facto standard for embedded SQLite in Node. <https://www.npmjs.com/package/better-sqlite3>, <https://dev.to/lovestaco/understanding-better-sqlite3-the-fastest-sqlite-library-for-nodejs-4n8>
  - **`node:sqlite`** (built-in) — still **Stability 1.2 "Release candidate"** in the Node 26 docs; no longer behind `--experimental-sqlite` but not Stable yet. <https://nodejs.org/api/sqlite.html>. The separate legacy `node-sqlite3` package was deprecated in 2026 (<https://www.reddit.com/r/node/comments/1q1r5s1/nodesqlite3_was_just_deprecated/>).
- Every framework/plugin below (Fastify plugins, NestJS adapters, Vite/Playwright toolchain) targets Node first; the existing `frontend/` toolchain already runs on Node.
- Single deployable SPA + API: trivial (`@fastify/static` + not-found handler, `express.static`, `@hono/node-server` `serveStatic`).

### Bun

- `bun:sqlite` is built into the runtime — synchronous, fast (docs claim 3–6x better-sqlite3 for reads), and Bun 1.2+ ships SQLite/S3/Postgres clients built in. Sources: <https://bun.com/docs/runtime/sqlite>, <https://dev.to/pockit_tools/bun-12-deep-dive-built-in-sqlite-s3-and-why-it-might-actually-replace-nodejs-4738>.
- Caveats found:
  - `node:sqlite` is **not implemented** in Bun — code written against `node:sqlite` will not run there. <https://github.com/oven-sh/bun/discussions/27092>
  - On Linux Bun statically links its own SQLite build (FTS5 compiled in, extension loading opt-in); on **macOS it uses Apple's system SQLite**, which disallows extension loading and has different WAL-persistence behavior across processes. For a product whose *content authority* is a SQLite file, platform-divergent SQLite builds are a real portability consideration. <https://bun.com/docs/runtime/sqlite>
- Production-readiness narratives exist (<https://docnative.app/blog/bun-production-ready>) but it remains a single-vendor runtime; native-module edge cases are the historical failure mode.

### Deno 2.x

- Deno 2 brought npm/node_modules compatibility (<https://deno.com/blog/v2.0>) and 2.2 added `node:sqlite` plus built-in OpenTelemetry (<https://deno.com/blog/v2.2>). Node compat is ~95% (<https://daily.dev/blog/javascript-runtimes-bun-vs-node-js-vs-deno-comparison/>).
- Practitioners still report ecosystem gaps for database drivers and production tooling on Deno (<https://www.reddit.com/r/Deno/comments/1dxnmei/would_you_consider_that_deno_is_ready_for/>); running a Node-style backend under Deno buys nothing for a single self-hosted deployable, while adding a permission model and a second toolchain to keep in sync with the frontend's Node tooling.

### Axis A verdict (research lean)

**Node 24 LTS with better-sqlite3** as the driver of record (`node:sqlite` watched as it stabilizes — it is at RC stability). Bun/Deno are viable runtimes for Hono-style apps, but for this product the SQLite-file authority, native-module maturity, and the existing frontend toolchain all point at Node. Bun remains attractive purely as a dev-time accelerator (test runner/package manager) — optional, not load-bearing.

## Axis B — HTTP framework: Fastify vs Hono vs NestJS vs Express

### Fastify v5 (current line: v5.12.x, Aug 2026)

- Current major is v5 (npm latest 5.12.0, Aug 2026; LTS line v5.11.x; security patch for CVE-2026-33806 shipped Aug 2026). Sources: <https://fastify.dev/docs/latest/Reference/LTS/>, <https://www.npmjs.com/package/fastify>, <https://github.com/fastify/fastify/releases>.
- **OpenAPI is a first-class plugin story**: `@fastify/swagger` + `@fastify/swagger-ui` generate OpenAPI v2/v3 from route definitions; with **Type Providers (TypeBox)** one schema declaration yields runtime validation, static TS request/response types, *and* the OpenAPI document. Sources: <https://fastify.dev/docs/latest/Reference/Type-Providers/>, <https://fastify.dev/docs/latest/Reference/TypeScript/>, <https://github.com/fastify/fastify-type-provider-typebox>, <https://apisyouwonthate.com/blog/fastifys-openapi-plugins-which-are-best/>, <https://www.pkgpulse.com/guides/zod-vs-typebox-2026>.
- Middleware equivalent: an encapsulated plugin/lifecycle system with direct analogs for the current stack — `@fastify/static` (SPA), `@fastify/cookie`, `@fastify/cors`, `@fastify/rate-limit`, `@fastify/helmet`, gzip, logging/hooks for correlation IDs (<https://fastify.dev/ecosystem/>).
- Testing: `fastify.inject()` performs in-process fake-HTTP requests without sockets — the direct analog of the current ASGI `TestClient` pattern (<https://fastify.dev/docs/latest/>).

### Hono v4 (on `@hono/node-server`)

- Web-standard (Request/Response) framework that runs on Node, Bun, Deno, and edge runtimes; OpenAPI via `@hono/zod-openapi` (Zod validators → OpenAPI) or the newer `hono-openapi` middleware. Sources: <https://hono.dev/examples/zod-openapi>, <https://hono.dev/examples/hono-openapi>, <https://www.npmjs.com/package/@hono/zod-openapi>.
- Testing story is excellent (`app.request()`), and it is TypeScript-first.
- The Node adapter's own docs say "Hono was not designed for Node.js at first" (<https://hono.dev/docs/getting-started/nodejs>, <https://github.com/honojs/node-server>) — Node is one target among many, and its middleware ecosystem is thinnest precisely on Node. Hono's headline advantage (cross-runtime portability) goes unused if Axis A lands on Node.

### NestJS 11

- Full-scope framework (DI, modules, decorators); Express v5 is the default adapter, Fastify is a one-line swap (<https://docs.nestjs.com/techniques/performance>).
- OpenAPI via `@nestjs/swagger` decorators. Friction found: the SPA catch-all pattern (`*` route) breaks under `path-to-regexp` v6+ with the Fastify adapter — a live open issue (<https://github.com/nestjs/swagger/issues/3348>). Since "one deployable serves SPA + API" is a hard filter, the catch-all route is not optional.
- Architectural fit is poor: the current backend is deliberately thin routers over an explicit service graph (audit §3.1); NestJS's decorator/DI machinery re-imposes a framework shape the rewrite does not need (<https://encore.dev/articles/nestjs-vs-fastify>).

### Express 5

- Still the compatibility default (and NestJS 11's baseline, <https://tech-insider.org/nestjs-tutorial-rest-api-13-steps-2026/>), but has **no first-class OpenAPI generation** — spec assembly happens via swagger-jsdoc annotations, which is stringly-typed and drift-prone; no built-in schema validation. Express 5 also inherited the `path-to-regexp` wildcard syntax change (`*` catch-alls must be rewritten). Weakest match for an OpenAPI-snapshot-gated codebase.

### Axis B verdict (research lean)

**Fastify v5 + TypeBox type provider.** Schema-declared-once (validation + TS types + OpenAPI) maps directly onto the current "thin router + injected store + OpenAPI snapshot gate" architecture; `inject()` replaces the ASGI TestClient; every current middleware (gzip/CORS/logging/rate-limit/static) has a maintained `@fastify/*` analog. **Hono is the runner-up** — pick it instead if the decision ticket wants Bun/Deno portability; NestJS and Express are poor fits (framework weight + catch-all breakage; no first-class OpenAPI respectively).

## Axis C — Data layer: hard filter = SQLite WAL + FTS5 first-class + hand-written SQL beyond ORM metadata

Context from the audit: the FTS5 virtual table already lives **outside** SQLAlchemy metadata today, maintained by hand-written SQL, with manual FTS-row cleanup on delete (C10); PRAGMAs are applied per connection (C6); search does strict token reduction into parameterized `MATCH` (B1). The TS data layer must make that posture sustainable, not fight it.

### Drizzle ORM v1 — fits, with a documented caveat

- TypeScript-first, SQL-shaped query builder + schema-in-TS; no codegen/daemon step; small runtime; first-class SQLite support across drivers (better-sqlite3, bun:sqlite, libsql/D1). Sources: <https://orm.drizzle.team/>, <https://www.turbostarter.dev/blog/drizzle-vs-prisma-typescript-orm-2026>, <https://orm.drizzle.team/docs/get-started/bun-sqlite-existing>.
- **FTS5 status: no first-class `CREATE VIRTUAL TABLE` DDL in drizzle-kit** — open enhancement since Mar 2024, unassigned (<https://github.com/drizzle-team/drizzle-orm/issues/2046>). The documented community workaround is exactly the current product's posture: declare the table in schema (or skip it) and **hand-edit the generated SQL migration** to use `CREATE VIRTUAL TABLE ... USING fts5(...)` (<https://www.answeroverflow.com/m/1146392232509833256>). Queries use the `sql` template escape hatch (`MATCH`, `snippet()`, `rank`), which is fully supported.
- Related wart: drizzle-kit **introspection** of a database containing FTS shadow tables is buggy (<https://github.com/drizzle-team/drizzle-orm/issues/3235>) — relevant because the Python-era DB has FTS tables; do not round-trip introspect it.
- Long-term-maintenance concern exists but is a judgement call, not a filter failure (<https://www.reddit.com/r/node/comments/1l3uj8j/anyone_else_concerned_about_drizzle_orms_longterm/>).
- WAL/PRAGMAs: driver-level control (better-sqlite3 pragma options / per-connection setup) — C6 semantics reproducible.

### Kysely — fits by philosophy

- Pure type-safe SQL query builder; the built-in SQLite dialect runs on better-sqlite3; raw SQL (`sql` template) is a first-class citizen, which is exactly what FTS5 `MATCH`/`snippet`/`rank` queries want. Sources: <https://kysely.dev/>, <https://kysely.dev/docs/getting-started>, <https://kysely-org.github.io/kysely-apidoc/classes/SqliteDialect.html>.
- There is **no ORM schema metadata at all** — the entire schema (relational *and* FTS) lives in hand-written migrations. That dissolves the C10 problem by construction and matches the repository-pattern, explicit-query style the current backend uses (<https://www.pkgpulse.com/guides/drizzle-vs-kysely-2026>).
- Costs: no relations/identity-map features (not needed here); migrations are TS files run through a built-in `Migrator` + the official `kysely-ctl` CLI (<https://kysely.dev/docs/migrations>, <https://github.com/kysely-org/kysely/issues/362>, <https://context7.com/kysely-org/kysely-ctl>); Kysely wraps better-sqlite3's synchronous API into async — a known design point, slight overhead, acceptable for this workload (<https://github.com/kysely-org/kysely/issues/1385>).

### Prisma — **fails the hard filter**

- **SQLite FTS5 is not supported.** The tracking issue has been open since 2021-09 and is still open with no assignee/milestone/PR (<https://github.com/prisma/prisma/issues/9414>); the docs state full-text search covers MySQL and PostgreSQL only (<https://www.prisma.io/docs/orm/prisma-client/queries/full-text-search>); TypedSQL chokes on FTS queries (<https://github.com/prisma/prisma/discussions/25975>). Prisma 7 improved performance/edge footprint in 2026 (<https://encore.dev/articles/drizzle-vs-prisma>) but the FTS gap is unchanged.
- FTS5 would therefore live entirely outside Prisma's schema model and Prisma Migrate cannot manage virtual tables — precisely the shape the audit flags as fragile (C10). **Research conclusion: Prisma is disqualified by the stated hard filter.** (The decision ticket may of course overrule the filter; it cannot overrule the facts.)

### TypeORM — not a 2026 contender

Decorator-heavy, maintenance-mode reputation, no FTS5 story, weakest type-safety of the set; excluded from the shortlist (<https://www.pkgpulse.com/guides/drizzle-orm-v1-vs-prisma-6-vs-kysely-2026>).

### Axis C verdict (research lean)

**Drizzle ORM v1 + better-sqlite3**: schema-in-TS for the ~14 relational tables, FTS5 DDL/triggers/cleanup as hand-edited SQL inside migration files (same posture as today, now versioned), `sql` template for `MATCH`/`snippet`/`rank`. **Kysely is the strong alternative** if the decision ticket prefers "everything is hand-written SQL" over "two notations" — both pass the filter; Prisma does not.

## Axis D — In-repo monorepo layout (pnpm workspace)

Repo reality today: a root `pnpm-workspace.yaml` already exists with `packages: [frontend]`, a root lockfile, and **workspace-global overrides** (`undici >=7.29.0 <8`, etc. — audit F-10). The frontend commands run as `pnpm --dir frontend ...`. So the question is only how to add the backend.

Options surveyed (typical pnpm monorepo shapes: <https://pnpm.io/workspaces>, <https://blog.logrocket.com/managing-full-stack-monorepo-pnpm/>, <https://nx.dev/blog/setup-a-monorepo-with-pnpm-workspaces-and-speed-it-up-with-nx>):

1. **Minimal-move (recommended shape)** — keep `frontend/` exactly where it is; add `server/` (TS backend) to `packages:`; optionally add `packages/contract` later for codegen output shared by both sides. Zero churn to existing CI paths and `--dir frontend` invocations.
2. **`apps/` convention** (`apps/web`, `apps/api`, `packages/*`) — the Turborepo/Nx-standard shape; cleaner at 4+ packages but forces moving/renaming the existing `frontend/` tree, touching every CI path for cosmetics.
3. **Task-runner overlay (Turborepo/Nx)** — caching/task-graph benefits only pay off with more packages and heavier CI; pnpm's own recursive filters plus catalogs (<https://pnpm.io/catalogs>) cover a 2–3 package workspace without extra tooling.

Constraint interaction to flag for #244: **pnpm overrides are workspace-global** — the `undici <8` pin (a jsdom/undici constraint from the frontend test stack, audit F-10) will also constrain the backend package's dependency resolution. The backend must either live with those pins or the overrides need a re-look at cutover; either way it belongs in the decision ticket.

### Axis D verdict (research lean)

Minimal-move: root workspace `packages: [frontend, server]` (+ optional `packages/contract`), pnpm catalogs for shared dependency versions, no Turborepo/Nx yet.

## Axis E — OpenAPI-first toolchain (replacing the hand-written trio, audit F-9)

Current pain: `frontend/src/app/types/studio.ts` (hand-written types) + `apiContract.ts`/`apiWorkflowContract.ts` (hand-written runtime parsers) + the backend OpenAPI snapshot — three artifacts kept in sync by hand.

### Direction: spec-first vs code-first

- Spec-first: the OpenAPI document is the source; server and client types are generated from it; the spec is an input, not an output (<https://zuplo.com/learning-center/openapi-first-api-gateway>, <https://swagger.io/blog/code-first-vs-design-first-api/>).
- Code-first: schemas live in route code; the OpenAPI document is generated and can be **snapshotted in CI** — which is exactly the shape of the repo's existing `check_openapi_snapshot.py` gate (<https://fastify.dev/docs/latest/Reference/Type-Providers/>; framing: <https://sookocheff.com/post/api/the-false-dichotomoy-of-design-first-and-code-first-api-development/>).
- Note the middle path: Fastify+TypeBox is code-first, but the generated document is deterministic, so "spec-as-artifact with CI snapshot" survives the rewrite either way.

### Frontend codegen tools (2026 landscape)

| Tool | Output | Notes | Source |
|---|---|---|---|
| **openapi-typescript** | Types only | Minimal, unopinionated; pairs with the existing hand-written `api.ts` fetch layer (which must keep its CSRF/credentials/abort invariants) | <https://www.pkgpulse.com/guides/orval-vs-openapi-typescript-vs-kubb-openapi-client-2026>, <https://dev.to/nyaomaru/which-openapi-codegen-should-you-choose-openapi-typescript-vs-hey-api-vs-orval-vs-kubb-100p> |
| **hey-api (`@hey-api/openapi-ts`)** | Types + SDK + plugins (Zod, TanStack Query, fetch clients) | The 2026 frontrunner for full generated clients; would replace more of `api.ts` internals | <https://github.com/hey-api/hey-api>, <https://heyapi.dev/docs/openapi/typescript/get-started>, <https://www.saschb2b.com/blog/typesafe-api-codegen-2026> |
| **orval** (v8) | Types + clients + React Query/SWR hooks | Strong when the app standardizes on React Query (this frontend has not) | <https://orval.dev/> |
| kubb | Plugin-maximal codegen | Heaviest; overkill here | <https://www.pkgpulse.com/guides/orval-vs-openapi-typescript-vs-kubb-openapi-client-2026> |

### Axis E verdict (research lean)

**Code-first (Fastify/TypeBox) → deterministic OpenAPI JSON → CI snapshot gate (continuity with today's gate) → `openapi-typescript` types-only codegen into `frontend/`**, keeping the hand-written `api.ts` fetch client because its CSRF/credentials/abort/error-normalization semantics are product invariants (audit §3.6, G7). hey-api is the upgrade path if a generated client is later wanted. This kills the three-way hand sync (F-9) with the smallest behavioral footprint.

## Axis F — Schema migration story (replacing Alembic)

Context: startup does online backup + `alembic upgrade head` (audit C7); migration history is `0001 create_all` + data backfills (C9); the map has settled an **empty-DB cutover** (no production data), so the tool must bootstrap fresh databases cleanly and then evolve the schema during/after the rewrite — including the FTS5 virtual table and its triggers.

| Option | Fit for SQLite + FTS5 | Notes | Source |
|---|---|---|---|
| **drizzle-kit** (generate/migrate) | Good — emits plain SQL migration files stored in-repo and **hand-editable** (required for FTS5 DDL + triggers); journal tracks applied state; data backfills are just SQL in the file (Alembic-analog shape) | Same tool as Axis C; no extra language | <https://orm.drizzle.team/docs/migrations>, <https://github.com/drizzle-team/drizzle-orm/issues/2046> |
| **kysely Migrator + kysely-ctl** | Good — TS migration files, full raw-SQL/DDL support, official CLI | The natural pairing if Kysely wins Axis C | <https://kysely.dev/docs/migrations>, <https://context7.com/kysely-org/kysely-ctl> |
| **Atlas** (ariga/atlas) | Capable — language-agnostic declarative planning, official Drizzle integration, diffs/lint | Adds a Go binary/Docker dependency to the toolchain; strongest as an *optional* planning/lint layer, not the core runner | <https://github.com/ariga/atlas>, <https://atlasgo.io/guides/orms/drizzle/getting-started> |
| **prisma migrate** | Excluded — cannot manage virtual tables; inherits the Prisma FTS5 disqualification | — | <https://github.com/prisma/prisma/issues/9414> |

Startup backup equivalent (C7): better-sqlite3 exposes the SQLite online-backup API (`db.backup()`), so the backup-then-migrate startup sequence ports directly on the Node+better-sqlite3 line.

### Axis F verdict (research lean)

**drizzle-kit** migrations (SQL files, hand-editable for FTS5 virtual tables/triggers — the direct Alembic analog including data backfills), Atlas optional later. Kysely Migrator if Kysely wins Axis C.

## Cross-axis fact sheet

| Axis | Finalists | Filter result | Research lean (NOT a decision) |
|---|---|---|---|
| A. Runtime | Node 24 LTS; Bun; Deno 2.x | All pass mechanically; Node has the only mature native-SQLite story | **Node 24 LTS + better-sqlite3** |
| B. Framework | Fastify v5; Hono v4; (NestJS 11, Express 5 screened out) | NestJS catch-all friction; Express has no first-class OpenAPI | **Fastify v5 + TypeBox** |
| C. Data layer | Drizzle v1; Kysely; (Prisma **excluded**, TypeORM screened out) | **Prisma fails FTS5 hard filter (open issue since 2021)** | **Drizzle + better-sqlite3** (Kysely close second) |
| D. Monorepo | minimal-move workspace; apps/* convention; +Turborepo/Nx | All pass | **Root pnpm workspace: `frontend/` kept + new `server/`** |
| E. OpenAPI | code-first+snapshot vs spec-first; openapi-typescript vs hey-api vs orval | All pass | **Code-first snapshot + openapi-typescript types-only into `frontend/`** |
| F. Migrations | drizzle-kit; kysely Migrator; Atlas (optional); prisma migrate excluded | Same as C | **drizzle-kit** |

## Combination lean (one coherent stack, for the decision ticket to grill)

> **Node 24 LTS · better-sqlite3 · Fastify v5 with TypeBox · Drizzle ORM v1 with drizzle-kit migrations (FTS5 DDL hand-written in SQL migrations, `sql` template for `MATCH`) · root pnpm workspace (`frontend/` + `server/`) · code-first OpenAPI snapshot gate + `openapi-typescript` types-only codegen into the frontend.**

Why it coheres: it preserves the current architecture's load-bearing shapes — thin routers over an explicit service graph, OpenAPI snapshot as the CI contract, SQLite file as the content authority with FTS5 as a hand-written-SQL subsystem, startup backup+migrate, in-process HTTP tests (`inject()` ↔ ASGI TestClient), single deployable serving SPA + API via `@fastify/static` — while deleting the two-language and three-way-hand-sync problems. Playwright e2e is unaffected (HTTP-level). TypeScript 7.x (native compiler, current 7.0.2 per audit F-10) is orthogonal to all axes; ecosystem tsgo-compatibility is still landing (<https://github.com/microsoft/typescript-go>, <https://github.com/withastro/roadmap/discussions/1321>) and should be tracked, not decided, here.

## Hard-constraint conflicts and flags found during research

1. **Prisma cannot do SQLite FTS5** (tracking issue open since 2021-09, still open; docs limit FTS to MySQL/Postgres). This is the only outright hard-filter elimination.
2. **Drizzle has no first-class FTS5 virtual-table DDL** (open since 2024-03). Workaround = hand-edited SQL migrations; this preserves today's C10 posture rather than fixing it — the decision ticket should accept that knowingly. Also: do **not** drizzle-introspect the Python-era DB (FTS shadow-table bug #3235).
3. **`node:sqlite` is still Stability 1.2 (RC)** even in Node 26 — fine to adopt, but better-sqlite3 is the zero-drama choice today; note the legacy `node-sqlite3` package is deprecated.
4. **Bun caveats**: `node:sqlite` unimplemented; macOS uses Apple's system SQLite (no extension loading, different WAL persistence across processes) — a real divergence for a SQLite-authoritative product.
5. **NestJS + Fastify adapter + SPA catch-all (`*`) is a live open issue** (`path-to-regexp` v6); the catch-all is mandatory under the "one deployable serves SPA + API" constraint.
6. **pnpm overrides are workspace-global**: the frontend's `undici <8` pin (audit F-10) will constrain the new backend package's dependency resolution — needs explicit handling in the decision ticket.
7. **Express 5 OpenAPI story is annotation-based** (swagger-jsdoc) — weakest fit for a snapshot-gated contract; Express 5 also changed wildcard route syntax.
8. No conflicts found against the SPA+API single-deployable constraint on Fastify/Hono (static-serving + catch-all both supported) or against Playwright e2e on any axis.

## Sources index

- Node releases/LTS: <https://endoflife.date/nodejs> · <https://nodejs.org/en/about/previous-releases> · <https://www.herodevs.com/blog-posts/node-js-end-of-life-dates-you-should-be-aware-of>
- node:sqlite stability: <https://nodejs.org/api/sqlite.html> · <https://github.com/nodejs/node/issues/57445> · node-sqlite3 deprecation: <https://www.reddit.com/r/node/comments/1q1r5s1/nodesqlite3_was_just_deprecated/>
- better-sqlite3: <https://www.npmjs.com/package/better-sqlite3>
- Bun SQLite: <https://bun.com/docs/runtime/sqlite> · <https://github.com/oven-sh/bun/discussions/27092>
- Deno: <https://deno.com/blog/v2.0> · <https://deno.com/blog/v2.2>
- Fastify: <https://fastify.dev/docs/latest/Reference/LTS/> · <https://fastify.dev/docs/latest/Reference/Type-Providers/> · <https://github.com/fastify/fastify/releases> · <https://apisyouwonthate.com/blog/fastifys-openapi-plugins-which-are-best/> · <https://fastify.dev/ecosystem/>
- Hono: <https://hono.dev/docs/getting-started/nodejs> · <https://hono.dev/examples/zod-openapi> · <https://github.com/honojs/node-server>
- NestJS: <https://docs.nestjs.com/techniques/performance> · <https://github.com/nestjs/swagger/issues/3348>
- Drizzle: <https://orm.drizzle.team/> · <https://orm.drizzle.team/docs/migrations> · FTS5: <https://github.com/drizzle-team/drizzle-orm/issues/2046> · <https://github.com/drizzle-team/drizzle-orm/issues/3235>
- Kysely: <https://kysely.dev/> · <https://kysely.dev/docs/migrations> · <https://github.com/kysely-org/kysely/issues/1385>
- Prisma FTS5: <https://github.com/prisma/prisma/issues/9414> · <https://www.prisma.io/docs/orm/prisma-client/queries/full-text-search> · <https://github.com/prisma/prisma/discussions/25975>
- Monorepo: <https://pnpm.io/workspaces> · <https://pnpm.io/catalogs> · <https://blog.logrocket.com/managing-full-stack-monorepo-pnpm/>
- OpenAPI codegen: <https://github.com/hey-api/hey-api> · <https://heyapi.dev/docs/openapi/typescript/get-started> · <https://orval.dev/> · <https://www.pkgpulse.com/guides/orval-vs-openapi-typescript-vs-kubb-openapi-client-2026> · <https://www.saschb2b.com/blog/typesafe-api-codegen-2026> · <https://dev.to/nyaomaru/which-openapi-codegen-should-you-choose-openapi-typescript-vs-hey-api-vs-orval-vs-kubb-100p>
- Spec-first vs code-first: <https://swagger.io/blog/code-first-vs-design-first-api/> · <https://zuplo.com/learning-center/openapi-first-api-gateway> · <https://sookocheff.com/post/api/the-false-dichotomoy-of-design-first-and-code-first-api-development/>
- Migrations: <https://github.com/ariga/atlas> · <https://atlasgo.io/guides/orms/drizzle/getting-started>
- TypeScript 7: <https://github.com/microsoft/typescript-go> · <https://github.com/withastro/roadmap/discussions/1321>
