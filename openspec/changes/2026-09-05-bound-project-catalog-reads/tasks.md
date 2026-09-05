# Tasks

## 1. Contract-first failing coverage

- [x] 1.1 Add store/API failures for newest-first default 50, limits 1 and
      100, zero/over-maximum/fractional/non-integer limits, id tie-break
      order, nullable terminal cursor, and complete traversal without
      duplicates or gaps.
- [x] 1.2 Add cursor failures for malformed, oversized, non-canonical,
      truncated, unknown-version, unsafe timestamp, empty/overlong id, and
      cross-owner tokens; prove each returns 422 `VALIDATION_ERROR`
      identifying `cursor`, does not enter the store, and preserves
      authentication precedence.
- [x] 1.3 Add projection and plan evidence proving the list query and
      payload omit `settings` and `import_hash`, read at most `limit + 1`
      rows, and use the covering owner/updated/id index without a
      temporary sort.

## 2. Bounded catalog API

- [x] 2.1 Introduce typed `ProjectCatalogSummaryRecord`, validated 1..100
      page input, owner-scoped cursor position, and page output ports;
      replace the unbounded `findProjects` store read with the projected,
      parameterized `limit + 1` keyset query.
- [x] 2.2 Add the owner-bound cursor codec on the shared canonical base64url
      facility, the strict query schema (`limit` default 50, cursor maximum
      1024), and the required `{ projects, next_cursor }` response without
      changing create/update/detail/delete routes.
- [x] 2.3 Generate the covering `(owner_id, updated_at, id)` index migration
      only through `pnpm --dir server db:generate --name
      paginate-project-catalog`; review the generated SQL/metadata without
      hand editing either.
- [x] 2.4 Regenerate the deliberate OpenAPI baseline and frontend API types;
      assert query bounds, 422 response, required nullable cursor, summary
      fields, and the absence of settings/import_hash.

## 3. Bounded frontend library traversal

- [x] 3.1 Replace the whole-list `parseProjects` with strict page parsing
      (required nullable `next_cursor`, five-field rows) and a bounded query
      encoder; preserve shared credentials, error envelope, and abort
      behavior.
- [x] 3.2 Extend the library bootstrap state to summaries plus continuation
      cursor: first page initializes, reload replaces with a fresh first
      page, Load older appends uniquely, duplicate older requests coalesce,
      failures preserve committed rows and cursor, and abort/stale-response
      rules reject late publications.
- [x] 3.3 Add the accessible `Load older projects` control with distinct
      busy and failure states; keep already rendered rows while loading and
      preserve keyboard focus semantics of the existing commands.

## 4. Integrated evidence

- [x] 4.1 Run the catalog contract suites (red → green), project
      create/update/detail/delete/import regressions, and the
      migration-channel gate.
- [x] 4.2 Run server type-check/lint/arch/gates/full tests, frontend
      lint/format/type/unit/build and API-types drift, and strict OpenSpec
      validation on the fixed candidate SHA; record exact results and every
      skip.
- [ ] 4.3 Keep the change active until required CI is green; browser
      Playwright workflows are intentionally not run locally (port policy,
      CI owns them) and human acceptance remains with the owner.
