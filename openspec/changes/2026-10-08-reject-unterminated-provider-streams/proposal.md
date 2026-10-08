## Why

A Provider can return HTTP 200 and end its stream before sending a protocol completion signal. Treating that EOF as success can present incomplete text as a completed Proposal and record misleading Job and usage evidence (#674).

## What Changes

- Require explicit protocol completion before an HTTP Provider stream can succeed.
- Reject EOF without completion, including empty and heartbeat-only streams, through the existing Provider failure path.
- Preserve final usage and in-band error processing after finish-reason completion signals, cancellation precedence, failed Job evidence, and the prohibition on automatic retries after frames escape.

## Impact

Affected surfaces are HTTP Provider stream parsing and the existing streamed Proposal outcome. No API shape, configuration, dependency, database migration, or architecture change is required. Providers that previously ended without a protocol completion signal will now produce a failed outcome.
