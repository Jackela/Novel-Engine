# Make job retry idempotent

## Why

`POST /api/projects/:projectId/jobs/:jobId/retry` performs proposal, review, or
export work synchronously. If that work reaches a terminal Job but the HTTP
response is lost, the author cannot distinguish success from no execution.
Replaying the request currently creates another retry Job, may call the
provider again, and may add a second usage event for one intended attempt.

## What Changes

- Require every retry request to carry a bounded client-generated
  `Idempotency-Key` header and persist that key on the retry Job.
- Admit at most one retry Job for the logical owner, project, source Job, and
  key. The creator alone may execute proposal, review, or export work.
- Return the same complete terminal Job for a sequential replay of the same
  key without executing provider, review, export, artifact, or usage work
  again.
- Return the existing stable 409 response when the same keyed retry is still `running`;
  the client retains the key and may replay it later.
- Treat a different key as an explicit new retry attempt, subject to the
  existing retryability, project-pipeline, and capacity rules.
- Make the Studio retain one key across ambiguous transport failure, timeout,
  abort, every 409/503, project navigation, and in-flight responses, while
  preventing
  that key from crossing owner, project, or source-Job scope.

## Impact

- **Breaking API change:** retry requests without a valid `Idempotency-Key`
  header are rejected with 422 and do not create or execute a Job. Existing
  clients must generate and retain a key per intended retry attempt.
- Adds a nullable retry-idempotency column and a scoped unique index through the
  generated migration channel. Historical and non-retry Jobs keep null.
- Changes the retry route schema, application/store ports, OpenAPI snapshot,
  generated frontend types, API client, and Studio retry state ownership.
- Does not make fresh proposal, review, or export creation idempotent and does
  not introduce asynchronous workers, polling, leases, or provider-level
  idempotency.

## Validation

- Store and HTTP tests for reservation, terminal replay, running conflict,
  concurrent uniqueness, restart recovery, ownership and project scope, key
  validation, and different-key attempts.
- Proposal, review, and export tests with both fresh and previously retried
  source Jobs, proving replay performs no provider or artifact work and adds no
  Job, event, assessment, snapshot, export, or usage evidence.
- Frontend tests for synchronous key creation, double activation, ambiguous
  failure reuse, 409 reuse, terminal clearing, explicit new attempts, project
  switching, owner-session clearing, and stale-response ownership.
- Migration, OpenAPI, generated-type drift, server/frontend owning checks, and
  strict OpenSpec validation.
