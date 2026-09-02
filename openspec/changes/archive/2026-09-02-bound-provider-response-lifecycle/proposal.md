# Bound provider response lifecycles

## Why

HTTP provider streams currently begin their silence timer only after a response
exists, have no absolute end-to-end deadline, and let a body-read `TypeError`
escape the provider failure boundary. Provider-controlled JSON bodies, SSE
events, total stream bytes, and accumulated proposal text are also unbounded.
A slow or oversized upstream can therefore hold a request indefinitely or
consume memory without producing the failed-job evidence promised by the
proposal contract.

## What changes

- Start one absolute provider deadline before dispatch and keep it through
  connection, headers, and complete response consumption.
- Normalize only transport/body-read failures; extractor and application
  programming errors remain visible.
- Bound synchronous JSON bodies, total SSE bytes, individual SSE events, and
  accumulated proposal markdown with stable server-authored failures.
- Preserve the existing provider port, API payloads, retry set, silence
  budgets, abort semantics, and chapter-generation timeout floor.

## Non-goals

- No streaming retry after deltas have been delivered.
- No new provider, queue, worker, dependency, or client-visible field.
- No change to HTTP failure-body privacy or token accounting.

## Validation

- Fake-timer tests for pre-response hangs, slow-drip streams, silence budgets,
  and the chapter timeout floor.
- Body-read failure and size-bound tests at provider and proposal-service seams.
- Full server gates, architecture, tests, OpenSpec, and browser workflows.
