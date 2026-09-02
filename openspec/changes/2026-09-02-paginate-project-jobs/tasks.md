# Tasks

## 1. Contract-first failing coverage

- [ ] 1.1 Add store/API failures for default 50, limits 1 and 100, rejection of
      zero, over-maximum, fractional, malformed, oversized, unknown-version,
      out-of-range timestamp, overlong id, and cross-project cursors, plus
      unchanged authentication/ownership behavior and proof invalid cursors do
      not enter the store.
- [ ] 1.2 Add stable-order traversal tests for equal timestamps, no duplicate or
      missing ids, nullable terminal cursor, a newer insert between pages, and
      deletion of the prior boundary row.
- [ ] 1.3 Seed at least 32,767 jobs directly in one transaction and prove a
      first page returns 200 with at most 100 jobs and at most 100 event ids;
      add query-plan failures requiring the tuple-range composite-index search,
      no temporary job sort, and the existing event index with no event sort.

## 2. Bounded persistence and HTTP contract

- [ ] 2.1 Introduce typed job-page input/output ports with `createdAtMs`, enforce
      integer limits 1..100 again at the store boundary, and implement the
      parameterized row-value `limit + 1` keyset query while preserving
      newest-first list jobs/events.
- [ ] 2.2 Replace the single-column project index with the
      `(project_id, created_at, id)` jobs index in the Drizzle schema and generate
      its create/drop migration through the governed semantic-name command;
      review all generated SQL and metadata without hand editing metadata.
- [ ] 2.3 Add bounded query schemas (`cursor` max 1024) and strict project-bound cursor codec,
      return stable 422 validation envelopes for every invalid token, and emit
      required `{ jobs, next_cursor }` responses.
- [ ] 2.4 Preserve oldest-first single terminal Job response documentation and
      add a list-specific newest-first jobs/events schema or description;
      assert OpenAPI query integer/default/min/max, cursor pattern/maxLength,
      422 envelope, and required nullable `next_cursor`, then regenerate the
      deliberate snapshot and frontend types and pass drift validation.

## 3. Explicit frontend traversal

- [ ] 3.1 Add API parser/query tests for required string-or-null
      `next_cursor`, limit/cursor encoding, and retained transport semantics.
- [ ] 3.2 Extend jobs state with first-page replacement and explicit older-page
      append, defensive de-duplication, coalescing, error preservation, and
      project/request stale-response protection; coalesce only duplicate
      same-project/same-cursor older loads, and make every first-page intent
      invalidate older append ownership and issue its own cursorless request.
- [ ] 3.3 Prove refresh, accepted-proposal refresh, retry completion, project
      switch, and unknown-outcome audit reset to exactly one first-page request;
      cover each while an older page is in flight, and prove loading older pages
      never settles or changes audit state. Project switch clears state always,
      fetches immediately only while Jobs remains visible, and otherwise waits
      until the inspector opens. For every same-project first-page intent, prove
      failure preserves committed jobs/cursor and reports the error (with audit
      failed where applicable); prove a failed new-project read never restores
      old-project state.
- [ ] 3.4 Add the accessible `Load older jobs` control with distinct busy/end
      states and keyboard tests: terminal success returns focus to Refresh jobs,
      while failure retains focus on the retryable load-older control.

## 4. Evidence and release boundary

- [ ] 4.1 Re-run synchronous jobs, event order, retry, proposal lifecycle,
      unknown-outcome audit, whole-book, authorization, OpenAPI, generated-type,
      migration-channel, and architecture regressions.
- [ ] 4.2 Run owning server and frontend full validation, relevant Playwright
      workflow, strict OpenSpec, and independent code/UX review on a fixed SHA;
      record exact results and every skipped external or human gate.
- [ ] 4.3 Keep this change active until required CI is green; record that compact
      JobSummary/detail and attempt-correlated audit remain separate findings.
