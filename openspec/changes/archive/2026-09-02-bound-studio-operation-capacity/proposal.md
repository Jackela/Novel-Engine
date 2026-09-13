# Bound Studio operation capacity

## Why

The app rejects duplicate work for one target, but different proposal, review,
export, and retry targets can all run at once without an application or
per-project ceiling. A burst can therefore create too many Provider requests,
large captured sources, render buffers, and artifact writes before the host
has a chance to recover.

## What Changes

- Admit expensive Studio workflows through one app-local, token-bound permit
  guard with defaults of four operations per app and two per project.
- Reject excess work immediately with a stable 503
  `OPERATION_CAPACITY_EXCEEDED` envelope and `Retry-After: 5`; do not queue or
  start any Provider, job, snapshot, review, artifact, cleanup intent, or usage
  side effect.
- Preserve project-deletion and identical-target 409 precedence, make every
  permit release idempotent and generation-safe, and hold capacity through all
  request-scoped cleanup.
- Accept bounded `API_MAX_ACTIVE_WORKFLOWS` and
  `API_MAX_ACTIVE_WORKFLOWS_PER_PROJECT` overrides, validated before persistence
  startup, and document the capacity response in OpenAPI and the error catalog.

## Impact

- Changes the Studio application guard and its proposal, review, export, retry,
  and project-deletion call sites; no asynchronous worker or database lease is
  introduced.
- Changes server configuration, the unified error channel, CORS-exposed
  headers, five workflow route contracts, and the deliberate OpenAPI baseline.
- Adds no dependency or migration and does not change successful payloads,
  terminal job landing, or frontend polling behavior.

## Non-goals

- No FIFO queue, priority, fairness guarantee, operation weights, automatic
  retry, distributed semaphore, lease, heartbeat, or worker process.
- No capacity accounting for CRUD, proposal acceptance, project deletion,
  reads/downloads, authentication, legacy import execution, backup, migration,
  startup recovery, or artifact reconciliation.
- No dynamic hot reload or capacity dashboard; a new process reads new limits.

## Validation

- Pure permit tests for priority, two-level limits, token ownership,
  double/late release, and project-exclusive interaction.
- API tests for every admitted workflow, pre-stream JSON refusal, stable
  envelope/header/OpenAPI, and zero-side-effect refusal.
- Completion, known failure, unexpected failure, disconnect, response-drain,
  Provider disposal, export rollback/ack, and retry cleanup regression tests.
- Configuration startup tests, full server gates, strict OpenSpec, independent
  review, and fixed-SHA evidence.
