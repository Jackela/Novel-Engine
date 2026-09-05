# Design: bounded provider response lifecycle

## One deadline owner

The shared HTTP streaming engine owns one abort controller and one first-cause
interrupt race created before calling the transport. The immutable absolute
timer and the application-owned external abort signal both participate in
dispatch, response-body, and frame waits even when an injected transport or
body ignores its signal. Chapter draft and revision streams receive the same
effective 180-second floor as synchronous generation. Existing first-event and
between-event silence budgets remain independent failure detectors; even when
configured longer, none can reset or extend the absolute deadline.

External cancellation remains distinguishable through an application-layer
control-flow error and records no job. A deadline instead becomes the existing
sanitized provider timeout. Synchronous generation passes that retryable cause
through the established attempt policy and records failure only after
exhaustion; a started stream does not retry and lands the failed job plus SSE
error frame. Iterator and body-reader cleanup is awaited within a fixed
one-second grace; a failing or uncooperative cleanup cannot replace the first
transport or cancellation cause or hang the request indefinitely.

A non-success HTTP status is registered as the first failure before its body is
cancelled, so cancellation rejection or delay cannot turn a known status into a
timeout or programming error. If dispatch loses the interruption race but its
injected transport later resolves a response, a fulfillment observer cancels
that late body within the same grace instead of leaving it to garbage
collection.

## Narrow failure normalization

Only the transport call and asynchronous body-read boundary classify fetch
rejections. A body iteration `TypeError` becomes the existing sanitized
non-retryable provider transport failure. Parsing, delta extraction, usage
extraction, and application logic remain outside that catch so programming
errors are never disguised as provider availability failures.

## Layered size limits

The infrastructure boundary consumes at most 8 MiB from either a synchronous
JSON response or a complete SSE response and at most 1 MiB for one SSE event.
It reads the original response body once rather than cloning an untrusted body.
The application proposal boundary independently caps accumulated or structured
proposal markdown at 1,000,000 Unicode code points, not UTF-16 code units.
Streaming keeps one incremental counter that joins surrogate pairs split across
deltas, covering deterministic, injected, and future providers as well as the
two HTTP adapters in linear time.

Limit failures use trusted local context only, are not retryable, report no
usage outcome, and never persist partial proposal text. Existing tests that
reuse one consumed `Response` across retry attempts must return a fresh
response per transport call, matching real fetch behavior.
