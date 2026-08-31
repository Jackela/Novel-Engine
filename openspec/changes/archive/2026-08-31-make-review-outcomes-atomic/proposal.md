# Make review outcomes atomic

## Why

Editorial review currently persists its immutable snapshot before provider work
starts, then persists the assessment and terminal job in later transactions. A
provider or persistence failure can therefore leave a snapshot with no review,
permanently block document deletion, or expose an assessment whose job is still
missing or running.

## What changes

- Read a complete, ordered review source without persisting a snapshot before
  invoking the provider.
- On fresh success, create the review snapshot, snapshot documents, assessment,
  issues, completed job, and completed event in one immediate transaction.
- On retry success, create the same review evidence and transition the existing
  running retry job to completed in one immediate transaction, including the
  provider's actual model.
- Revalidate captured document/revision ownership when the result lands, so a
  concurrent delete produces a failed job instead of partial evidence.
- Treat a missing or non-array top-level `findings` value as a known provider
  contract failure while continuing to filter invalid individual findings by
  the server-owned closed vocabulary.
- Remove historical review snapshots that have no assessment through the
  generated migration channel.
- Add failure-injection and concurrency coverage for fresh and retried reviews.

## Non-goals

- No HTTP route, response-schema, provider-selection, or frontend change.
- No change to proposal, export, usage-accounting, or general restart-recovery
  behavior.
- No background worker, lease, snapshot garbage collector, or long-lived
  database transaction around provider work.

## Validation

- Baseline reproduction proving a failed review leaves deletion-blocking rows.
- Store-level rollback and source-invalidation tests for fresh and retry paths.
- Service/API tests for provider failures, strict root-envelope validation,
  cleanup reporting, job events, model provenance, and successful evidence
  retention.
- Migration upgrade test preserving completed review snapshots while removing
  only unreferenced review snapshots.
- Server gates, type-check, lint, architecture policy, full tests, build, and
  strict OpenSpec validation.
