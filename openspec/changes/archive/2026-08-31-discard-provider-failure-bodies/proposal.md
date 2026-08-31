# Discard untrusted Provider failure bodies

## Why

HTTP Provider adapters currently append non-success response bodies to a
`ProviderTransportError`. Proposal and review workflows persist that message
in job and event rows and can return it through JSON or SSE. A remote Provider
therefore controls long-lived, author-visible diagnostics and can echo API
credentials, manuscript text, forged log lines, or other sensitive content.

Retry decisions already use the normalized numeric status rather than the
message. The response body is unnecessary at this trust boundary and must not
cross it.

## What Changes

- Treat every non-success Provider response body as untrusted diagnostics and
  cancel and discard it without reading it.
- Build the public/persisted failure only from trusted local context and the
  normalized numeric HTTP status.
- Preserve the structured status that drives the shared retry policy.
- Clarify that the default retry budget is three total attempts, matching the
  executable policy.
- Add adversarial coverage across both HTTP adapters, stored job/event data,
  JSON job payloads, and SSE error frames.

## Impact

- Changes failure-message text and failure-body disposal behavior for
  non-success HTTP Provider responses.
- No successful Provider response, API shape, SSE frame shape, database
  schema, migration, retryable status set, or retry count changes.
- No diagnostic body store or new dependency is introduced.
