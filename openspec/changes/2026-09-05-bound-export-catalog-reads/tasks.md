# Tasks

## 1. Contract-first failing coverage

- [x] 1.1 Add store/API failures for newest-first default 50, limits 1 and 100,
      zero/over-maximum/fractional limits, nullable terminal cursor, and
      complete traversal without duplicates or gaps.
- [x] 1.2 Add cursor failures for malformed, oversized, non-canonical,
      truncated, unknown-version, unsafe timestamp, overlong id,
      cross-project, and cross-project-route tokens; prove each returns 422
      `VALIDATION_ERROR` identifying `cursor` without entering the store.
- [x] 1.3 Add query-plan and projection tests proving the page query uses the
      `(project_id, created_at, id)` index without a temporary sort, reads at
      most `limit + 1` rows, and keeps the exact existing artifact summary
      fields.
- [x] 1.4 Add a statement-count failure proving a fresh snapshot write issues
      a constant number of `snapshot_documents` insert statements at two
      document scales.

## 2. Keyset catalog storage

- [x] 2.1 Generate the migration only through
      `pnpm --dir server db:generate --name paginate-export-catalog`; review
      the generated SQL/metadata without hand editing; replace the project
      catalog index with the keyset `(project_id, created_at, id)` index.
- [x] 2.2 Add typed `ExportPageLimit`, validated 1..100 page input,
      artifact-catalog cursor position, and page output ports; replace the
      unbounded store read with the scoped, projected, parameterized
      `limit + 1` row-value keyset query.
- [x] 2.3 Batch the fresh snapshot document write into fixed-size multi-row
      inserts (at most 4,000 documents per statement, below SQLite's variable
      ceiling) with identical rows, ids, positions, and revision references
      inside the same transaction.

## 3. Bounded export catalog API

- [x] 3.1 Add the strict query schema (`limit` default 50, cursor maximum
      1024), the project-bound export cursor codec, the required
      `{ exports, next_cursor }` response, and the 422 validation mapping
      without changing create, retry, or download routes.
- [x] 3.2 Regenerate the deliberate OpenAPI baseline and frontend API types;
      assert query bounds, 422 response, required nullable cursor, and the
      unchanged artifact summary fields.

## 4. Bounded frontend export traversal

- [x] 4.1 Replace the full `StudioExport[]` list parser/type with page
      parsing and strict required `next_cursor`; add bounded query encoding
      through the shared request seam while preserving credentials, error
      envelope, and abort semantics.
- [x] 4.2 Refactor export history state to own summaries plus continuation
      cursor: first page initializes on panel activation, Load older appends
      uniquely with coalescing, failures preserve committed state, and
      lifecycle/request versions reject stale project responses.
- [x] 4.3 Replace the post-export whole-catalog reload with one cursorless
      first-page refresh that prepends/de-duplicates new summaries while
      preserving the loaded contiguous tail and its continuation cursor, and
      adopts the fresh page when a gap appears.
- [x] 4.4 Add the accessible `Load older exports` control with distinct busy,
      failure, and terminal states without stealing keyboard focus.

## 5. Integrated evidence and release boundary

- [x] 5.1 Run export create/retry/download, snapshot identity, source
      revalidation, capacity, publication/recovery, pagination contract, and
      frontend export panel regressions.
- [x] 5.2 Run server type-check/lint/arch/full tests and gates, frontend
      lint/format/type/unit/build/check:api-types, migration-channel gate,
      and strict OpenSpec on a fixed SHA; record exact results and every skip
      (browser E2E skipped locally: the Playwright port is exclusively held
      by parallel work; CI owns it).
- [ ] 5.3 Keep the change active until required CI is green, then merge it
      into the canonical specification and archive it.
