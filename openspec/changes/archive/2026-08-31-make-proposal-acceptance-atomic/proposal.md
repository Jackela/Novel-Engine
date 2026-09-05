# Make proposal acceptance atomic

## Why

Proposal acceptance currently commits the new manuscript revision before it
updates the proposal job's `accepted_revision_id`. A failure between those
writes leaves an accepted revision that the job does not name; retry then uses
the stale base revision and cannot repair the split state.

## What changes

- Replace the application-level pair of persistence calls with one typed
  proposal-acceptance store command.
- Re-read and validate the proposal job inside an immediate SQLite transaction,
  then create and index the revision, advance the document and project, and
  bind the job result in that same transaction.
- Make concurrent and repeated acceptance converge on the one revision already
  named by the job.
- Repair a legacy split write when an existing `ai-accepted` revision already
  carries the same `metadata.ai_job_id` but the job result is still unbound.
- Add failure-injection coverage proving every manuscript, FTS, project, and job
  write rolls back together.

## Non-goals

- No change to proposal generation, provider behavior, HTTP routes, or response
  schemas.
- No new dependency or database migration.
- No review, export, retry, or snapshot-lifecycle change in this finding.

## Validation

- Store-level transaction and legacy-repair tests.
- Existing proposal API and streaming-service tests.
- Server gates, type-check, lint, architecture policy, full tests, and strict
  OpenSpec validation.
