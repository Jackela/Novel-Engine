# TS backend stack: Node 24 LTS, Fastify v5 + TypeBox, Drizzle + better-sqlite3

---
status: accepted
---

The greenfield TS backend (ADR-0001) runs on **Node 24 LTS** with
**better-sqlite3** as the SQLite driver of record, **Fastify v5 with the
TypeBox type provider** as the HTTP framework, **Drizzle ORM + drizzle-kit**
as the data layer and migration tool, a **minimal pnpm workspace**
(`frontend/` unchanged, new `server/` sibling), and a **code-first OpenAPI
snapshot gate with openapi-typescript types-only codegen** feeding the
carried-forward frontend's hand-written `api.ts` (whose CSRF, credentials,
and abort semantics are product invariants).

Rationale and primary sources: the wayfinder stack survey
(`research/ts-stack-survey` branch,
`docs/research/2026-08-17-ts-stack-survey.md`), decided in map ticket #244
under the audit's hard filters — SQLite (WAL, per-connection PRAGMAs, FTS5)
as content authority, one deployable serving SPA + API, one language,
Playwright e2e before cutover.

Accepted postures and interactions:

- **FTS5 stays outside ORM metadata**, exactly as today: the virtual table's
  DDL, triggers, and manual row cleanup live as hand-edited SQL inside
  drizzle-kit migration files; `MATCH`/`snippet`/`rank` queries use the `sql`
  template. Drizzle has no first-class `CREATE VIRTUAL TABLE` DDL
  (drizzle-orm#2046) — this is a documented acceptance, not an oversight.
- **Do not drizzle-introspect** a database containing FTS shadow tables
  (drizzle-orm#3235); irrelevant at empty-DB cutover but worth remembering.
- **pnpm overrides are workspace-global**: the frontend's security pins
  (notably `undici <8` for jsdom 29) also constrain `server/` dependency
  resolution. They stay; revisit only if the server stack ever needs a newer
  undici at cutover.
- **`node:sqlite` is watched, not used**: it is Stability 1.2 (RC) on Node 26;
  better-sqlite3 remains the boring, FTS5-enabled choice until the built-in
  stabilizes.

## Considered Options

- Bun — rejected: `node:sqlite` unimplemented; on macOS it uses Apple's
  system SQLite (no extension loading, platform-divergent WAL behavior) —
  unacceptable for a product whose content authority is a SQLite file.
- Deno 2.x — rejected: ~95% Node compat buys nothing for a single
  self-hosted deployable already committed to the frontend's Node toolchain.
- Hono v4 — rejected (runner-up): its cross-runtime advantage goes unused on
  Node and its Node-adapter middleware ecosystem is thinner; `@fastify/*`
  covers every current middleware with maintained analogs.
- NestJS 11 — rejected: the SPA catch-all route breaks under its Fastify
  adapter (`path-to-regexp` v6, nestjs/swagger#3348) and the catch-all is
  load-bearing; its decorator/DI machinery re-imposes a framework shape the
  thin-router + explicit-service-graph architecture deliberately avoids.
- Express 5 — rejected: no first-class OpenAPI generation; annotation-driven
  specs are drift-prone under a snapshot gate.
- Prisma — rejected: no SQLite FTS5 support (prisma/prisma#9414, open since
  2021) — fails the hard filter outright.
- Kysely — rejected as primary (documented fallback): philosophically the
  closest to a pure hand-written-SQL posture, but Drizzle's schema-in-TS plus
  drizzle-kit is the closer analog to the current SQLAlchemy-models +
  Alembic setup and gives typed end-to-end queries for the relational core.
- Turborepo/Nx — rejected: a 2-package workspace doesn't justify a task
  runner; pnpm catalogs cover shared versioning.
- spec-first OpenAPI, hey-api, orval — rejected for now: the code-first
  snapshot preserves the current gate shape; hey-api remains the upgrade path
  if generated clients are ever wanted beyond types.
