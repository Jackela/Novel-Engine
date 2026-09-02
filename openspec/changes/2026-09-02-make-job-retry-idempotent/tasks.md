# Tasks

## 1. Contract-first retry identity coverage

- [ ] 1.1 Add HTTP failures for missing, empty, short, over-128, whitespace,
      non-ASCII, and invalid-character `Idempotency-Key` values; prove the
      required 16..128 pattern in OpenAPI and that body-only or absent keys
      create no Job or event. Cover duplicate header combination and the
      intentional schema-first anonymous 422 behavior.
- [ ] 1.2 Add store/API red tests proving same owner/project/source/key creates
      one retry Job, same-key terminal replay returns the exact full Job and
      events, same-key running replay returns the existing 409
      `OPERATION_IN_FLIGHT` with `Retry-After: 1`, and a different key
      after settlement creates a distinct retry.
- [ ] 1.3 Race concurrent requests at the reservation seam and prove the unique
      winner alone executes; cover identical key across another source Job,
      project, and owner, plus 404 ownership behavior with no scope disclosure.

## 2. Durable reservation and replay

- [ ] 2.1 Add nullable retry-idempotency persistence and the partial unique
      project/source/key index to the Drizzle schema; generate and review the
      semantic migration and metadata without hand editing generated metadata.
- [ ] 2.2 Add a narrow store command that, in one immediate scoped transaction,
      returns terminal replay, running conflict, or a newly inserted running
      retry Job plus first event; normalize only the expected unique race by
      reloading its winner. Catch only the retry-key index conflict at the Job
      insert; first-event and every other constraint failure must roll back.
- [ ] 2.3 Refactor shared retry orchestration so only the reservation creator
      dispatches proposal, review, or export work; terminal/running replays must
      bypass provider construction, review evaluation, export rendering,
      artifact publication, compensation, and terminal writes.
- [ ] 2.4 Preserve startup recovery for keyed running Jobs and prove a restart
      makes the same key replay the recovered interrupted Job without creating
      or executing another retry.

## 3. Operation and accounting invariants

- [ ] 3.1 Cover fresh and prior-retry source Jobs for proposal, review, and
      export; retain failed/interrupted eligibility and explicit import,
      completed, and unsupported-kind rejection for an unreserved key.
- [ ] 3.2 For completed and failed terminal proposal replays, assert provider
      call count, Job/event count, and usage rows/totals do not change; retain
      the original atomic proposal retry outcome-plus-usage behavior.
- [ ] 3.3 For completed and failed review/export replays, assert evaluation,
      render/gateway, snapshot, assessment/issue, artifact, file, Job, and event
      evidence does not change; retain existing landing and cleanup semantics.

## 4. HTTP and frontend ownership

- [ ] 4.1 Add the required bounded header schema, CORS allow-list entry, stable
      keyed 409 mapping and `Retry-After`, complete terminal 200 response, and
      unchanged auth, CSRF, capacity, error-envelope, and full-Job event-order
      contracts. Declare the `Retry-After` response header in OpenAPI and prove
      generated-type drift coverage.
- [ ] 4.2 Regenerate the OpenAPI snapshot and frontend generated types; update
      the shared API client to send `Idempotency-Key` through the existing
      credential, CSRF, abort, timeout, and parsing path.
- [ ] 4.3 Add a `sessionStorage` retry-attempt registry scoped by owner/project/source
      Job. Generate before dispatch; retain across ambiguous errors, 409,
      503, project switches and reload; clear on terminal 200 or
      401/403/404/422, and clear all entries on logout/session change.
- [ ] 4.4 Prove double activation uses one key, late old-project settlement
      cannot mutate the visible project, returning to an unresolved source
      reuses its key, and a known terminal result lets a later explicit retry
      generate a new key while preserving existing busy/focus behavior.

## 5. Validation and release boundary

- [ ] 5.1 Run focused retry, proposal, review, export, usage, restart,
      authorization, capacity, OpenAPI, generated-type, migration, and frontend
      ownership tests, including real provider/gateway spies at replay seams.
- [ ] 5.2 Run server gates, type-check, lint, architecture and full tests;
      frontend lint, format, type-check, unit tests and build; strict OpenSpec
      and the relevant browser workflow. Record exact results and skipped gates
      against a fixed SHA.
- [ ] 5.3 Keep this breaking change active until required CI and compatibility
      review are green; then merge the complete modified requirements into the
      canonical specification and archive the unchanged change folder.
