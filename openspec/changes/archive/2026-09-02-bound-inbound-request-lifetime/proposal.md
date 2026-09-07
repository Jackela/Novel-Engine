# Bound inbound request receipt lifetime

## Why

The API caps one request body at 1 MiB and inherits Node's finite header
default, but Fastify explicitly leaves complete-request receipt unlimited. A
client can therefore occupy a connection indefinitely by sending an otherwise
valid body very slowly. The implicit header default is also not yet an
executable project policy.

## What Changes

- Give the HTTP server explicit finite thresholds for receiving complete
  request headers and the complete inbound request, plus an explicit finite
  connection-check interval.
- Reject an expired partial request with HTTP 408 and close its connection;
  body-bearing routes cannot reach validation, authorization, route, database,
  or Provider work before body parsing completes.
- Reject and close any request that advertises a body for a route with no body
  contract, so a handler cannot run while an undeclared body remains
  incomplete.
- End the receipt deadline once the request has been received, so long-running
  synchronous AI handlers and proposal streams keep their existing provider,
  application, and client deadlines.
- Clarify that the existing 180-second generation floor applies to timeouts
  that enclose provider execution, not to the earlier request-receipt phase.

## Impact

- Direct HTTP clients whose incomplete request is observed beyond the
  configured receipt threshold are disconnected with HTTP 408.
- Successfully received requests, response streaming, provider retry policy,
  the 1 MiB body limit, API payloads, OpenAPI, and persistence are unchanged.
- No dependency, migration, environment variable, or frontend change is
  required.

## Non-goals

- No global route-handler timeout or SSE duration limit.
- No socket-idle timeout, request queue, or per-route timeout configuration.
- No attempt to wrap parser-level 408 responses in the application JSON error
  envelope.
- No promise that early `onRequest` or `preParsing` hooks have not run before a
  body-receipt timeout; those hooks precede Fastify body parsing.

## Validation

- Raw-socket tests for partial headers, partial bodies, and connection close.
- A completed request whose handler outlives the receipt timeout still
  succeeds.
- An SSE response whose frames outlive the receipt threshold still succeeds.
- Server policy assertions, existing body-limit coverage, full server gates,
  strict OpenSpec, and fixed-SHA evidence.
