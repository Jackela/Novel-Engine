# Tasks

## 1. Provider and application normalization

- [x] 1.1 Add OpenAI-compatible and DashScope synchronous parsing tests for
      zero, `Number.MAX_SAFE_INTEGER`, `MAX_SAFE_INTEGER + 1`, `1e308`,
      `Infinity`, negative, fractional, missing, and malformed usage values.
- [x] 1.2 Add the matching final-stream-usage tests and make the shared provider
      token parser accept only non-negative safe integers.
- [x] 1.3 Harden the application resolver so invalid injected-provider usage
      follows the unified word-count fallback across proposal, stream, and
      retry landings while valid safe counts remain exact.

## 2. Persistence invariant

- [x] 2.1 Add transaction tests proving unsafe direct usage inputs commit
      neither the usage row nor the paired completed-job/retry transition.
- [x] 2.2 Validate non-negative safe integers in the single usage-write helper
      before SQL, leaving programming and contract failures visible.
- [x] 2.3 Add safe-integer CHECK constraints to both usage token columns and
      generate the migration only through
      `pnpm --dir server db:generate --name enforce-safe-usage-tokens`; never
      hand-edit Drizzle metadata.
- [x] 2.4 Prove the generated migration preserves exact valid rows and fails on
      invalid historical INTEGER/REAL values instead of coercing them.

## 3. Exact aggregate reads

- [x] 3.1 Add store and HTTP tests for exact per-model, project, and daily sums
      at safe boundaries and for fail-loud corrupt or unsafe totals.
- [x] 3.2 Read SQL sums in an exact representation, validate before converting
      to JavaScript numbers, and use one checked-add helper for project and
      daily aggregation.
- [x] 3.3 Preserve the successful usage response, per-model ordering, 30-day
      zero-fill, status codes, and existing opaque `INTERNAL_ERROR` response for
      unexpected ledger corruption.

## 4. Validation and release boundary

- [x] 4.1 Run provider sync/stream, proposal accounting, streaming, retry,
      transaction, migration, usage-store, and usage-HTTP regressions.
- [x] 4.2 Run server type-check, lint, architecture, size, migration-channel,
      OpenAPI, full tests, and strict OpenSpec; record fixed-SHA evidence and
      every skipped external or human gate.
- [ ] 4.3 Keep the change active until required CI is green, then merge the
      modified requirements into the canonical specification and archive it.
