# Tasks

## 1. Contract-first failing coverage

- [ ] 1.1 Add store/API failures for newest-first default 50, limits 1 and 100,
      zero/over-maximum/fractional limits, nullable terminal cursor, complete
      traversal without duplicates/gaps, concurrent newer insertion, and a
      deleted boundary row.
- [ ] 1.2 Add cursor failures for malformed, oversized, non-canonical,
      truncated, unknown-version, unsafe revision number, overlong id,
      cross-project, and cross-document tokens; prove each returns 422
      `VALIDATION_ERROR`, does not enter the store, and preserves auth/404 scope.
- [ ] 1.3 Add projection tests proving the list query and payload omit
      `content_markdown` and `metadata`, return exact stored `word_count`, use at
      most `limit + 1` rows, and use the existing document/revision index without
      a temporary sort.

## 2. Exact persisted revision word counts

- [x] 2.1 Move the existing Unicode-aware word counter to a pure Studio domain
      utility and pin ASCII, Chinese, punctuation, apostrophe, hyphen, numeric,
      empty, and unpaired-surrogate behavior without changing current results.
- [x] 2.2 Add nullable `word_count` to the Drizzle revision schema and generate
      the migration only through
      `pnpm --dir server db:generate --name persist-revision-word-count`; review
      generated SQL/metadata without hand editing either.
- [x] 2.3 Make the sole revision insertion helper persist the exact non-negative
      count atomically for project seeds, imports, saves, proposal acceptance,
      and restores; make all revision projections consume stored authority and
      reject null, negative, non-integer, or unsafe counts through one typed
      internal invariant error without adding a public error code.
- [x] 2.4 Add a context-owned pre-serve reconciler that backfills null rows in
      restart-safe batches of at most 256 after backup/migration, proves partial
      progress resumes, verifies no null remains, and fails before export
      reconciliation/job recovery/traffic on any error.

## 3. Bounded revision summary API

- [ ] 3.1 Introduce typed `RevisionSummaryRecord`, validated 1..100 page input,
      document-bound cursor, and page output ports; replace the unbounded store
      read with the scoped, projected, parameterized `limit + 1` keyset query.
- [ ] 3.2 Add the strict query schema (`limit` default 50, cursor maximum 1024),
      canonical cursor codec, required `{ revisions, next_cursor }` response,
      and stable validation/error mapping without changing restore routes.
- [ ] 3.3 Prove restore still performs one scoped exact full-revision read and
      replays body/metadata into a new `restore` revision; list summaries and
      cursors must never become restore authority.
- [ ] 3.4 Regenerate the deliberate OpenAPI baseline and frontend API types;
      assert query bounds, 422 response, required nullable cursor, closed source
      enum, summary fields, and the absence of content/metadata.

## 4. Bounded frontend history traversal

- [ ] 4.1 Replace the full `Revision` list parser/type with summary-page parsing,
      bounded query encoding, and strict required `next_cursor`; preserve shared
      credentials, error envelope, and abort behavior.
- [ ] 4.2 Refactor revision state to own summaries plus continuation cursor:
      first page initializes, Load older appends uniquely, same-owner/same-cursor
      requests coalesce, failures preserve committed state, and lifecycle/request
      versions reject stale project/document responses.
- [ ] 4.3 Replace every successful autosave/accept/restore whole-history reload
      with one cursorless first-page refresh that prepends/de-duplicates new
      summaries while preserving the already loaded contiguous tail and its
      continuation cursor; prove repeated saves never traverse older pages.
- [ ] 4.4 Bound the module-global cache and request-version map to eight owners
      with inactive LRU eviction, active-owner protection, fresh reload after
      eviction, and cleanup on owner transition/unmount.
- [ ] 4.5 Add the accessible `Load older revisions` control with distinct busy,
      failure, and terminal states; retain focus for retry and move terminal
      keyboard focus to the History heading.

## 5. Integrated evidence and release boundary

- [ ] 5.1 Run revision create/save/import/accept/restore, migration/startup,
      authorization, OpenAPI/type drift, query-plan, frontend contract/cache,
      autosave, History, and stale/abort regressions.
- [ ] 5.2 Run server type-check/lint/arch/size/full tests, frontend
      lint/format/type/unit/build, relevant Playwright History workflow,
      migration-channel gates, strict OpenSpec, and independent code/UX review
      on a fixed SHA; record exact results and every skip.
- [ ] 5.3 Keep the change active until required CI is green, then merge it into
      the canonical specification and archive it. Record project-shell,
      review-history, project-catalog, and export-catalog pagination as separate
      later changes.
