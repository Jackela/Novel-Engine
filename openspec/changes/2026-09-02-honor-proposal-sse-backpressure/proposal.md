# Honor proposal SSE backpressure

## Why

The streamed proposal route writes every frame and immediately asks the
application generator for the next one, even when Node reports that the
write has reached its backpressure threshold. A slow or non-reading client can
therefore make the server continue pulling Provider output and accumulate
response data in memory instead of applying the writable-stream backpressure
boundary.

## What Changes

- Pause proposal-frame production whenever an SSE write reports downstream
  backpressure, and resume only after that response emits `drain`.
- Bound each drain wait to 30 seconds and race it against request cancellation,
  response failure, and premature connection close; an interruption that wins
  permanently stops further pulls and writes.
- Distinguish Node's normal `finish` then `close` lifecycle from a premature
  disconnect, while preserving the exact first failure that actually wins.
- Preserve frame order, first-cause failure identity, exact generator cleanup,
  and the existing no-partial-job behavior for disconnects before a terminal
  proposal outcome is produced.
- Treat loss of a terminal frame after its job has landed as an indeterminate
  client outcome: complete a client-ordered audit refresh, stop automatic
  continuation, and never auto-accept an unobserved proposal.
- Remove every temporary and connection-lifetime listener on all terminal
  paths so repeated streams and repeated drain cycles do not accumulate
  subscriptions.

## Impact

- Slow proposal consumers apply bounded pull pressure to the existing
  application generator and Provider stream rather than growing the response
  queue without bound.
- SSE frame shape, routes, OpenAPI, Provider deadlines, proposal landing, and
  manuscript mutation rules remain unchanged. Frontend stream callers gain
  explicit indeterminate-outcome audit handling; the frame parser is unchanged.
- No dependency, migration, configuration, or public payload change is
  required.

## Non-goals

- No workflow concurrency quota, queue, or shutdown-drain policy.
- No rollback of a durable terminal job that was produced before a later
  disconnect prevented delivery of its terminal frame.
- No transport acknowledgement that proves a frame was consumed by the client,
  and no automatic recovery or idempotent replay of an unobserved terminal job.
- No claim that job history uniquely correlates an unobserved terminal job to
  the interrupted request; safe replay needs a separate attempt-id contract.
- No server-quiescence guarantee for the audit refresh: the prior stream may
  finish cleanup or land a terminal job after that snapshot returns.

## Validation

- Deterministic response-writer tests for write success, write backpressure,
  drain, the 30-second no-progress deadline, premature and normal close,
  exact error identity, cleanup failure, and listener removal.
- Existing proposal disconnect/landing tests, stream lifecycle leak coverage,
  frontend audit-refresh tests, full package gates, strict OpenSpec, and
  fixed-SHA evidence.
