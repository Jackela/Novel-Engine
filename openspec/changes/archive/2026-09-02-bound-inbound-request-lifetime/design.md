# Design: request receipt deadline without a handler deadline

## Lifecycle boundary

Node's HTTP parser owns header receipt before invoking Fastify, but emits the
request event as soon as headers complete. Fastify's early `onRequest` and
`preParsing` hooks can therefore run while a body is still arriving; body
parsing finishes before `preValidation`, `preHandler`, and the route handler.
The server's `headersTimeout` and `requestTimeout` still form the right finite
socket-occupation boundary: an incomplete request observed after its threshold
receives 408 and its connection closes, while a request received completely is
no longer subject to either threshold.

The production policy configures a 60,000 ms header threshold, a 120,000 ms
complete-request threshold, and a connection scan interval no greater than
5,000 ms. The existing 1 MiB body limit remains the byte boundary.
`connectionTimeout` and Fastify `handlerTimeout` remain disabled; either would
cover a different lifecycle and could terminate legitimate Provider work or
SSE output.

Node checks incomplete connections on that interval, so the contract treats
the configured values as thresholds rather than promising millisecond-exact
wall-clock enforcement. Tests inject short thresholds and a short scan
interval before the listener starts and wait for threshold plus interval plus
bounded CI slack.

## Undeclared request bodies

Fastify does not wait for every HTTP method's body. A GET, HEAD, or a route
without a body schema can otherwise run while a declared body remains
incomplete. A global early hook therefore detects non-empty body framing
(`Content-Length` greater than zero or `Transfer-Encoding`) on a route with no
body contract, returns the stable 422 `VALIDATION_ERROR`, marks the response
connection for close, and never enters that route's handler. Its details use
the existing validation item shape (`field`, `type`, `message`) with a stable
body-specific item.

Body-bearing routes retain normal parsing. For an incomplete POST, PUT, or
PATCH body, `onRequest` and `preParsing` may already have run, but
`preValidation`, `preHandler`, the route handler, database work, and Provider
dispatch do not run before parsing completes or times out.

## Side-effect boundary

An expired partial-header request is rejected before Fastify and therefore
cannot be guaranteed to carry the application's JSON error envelope,
correlation header, authentication result, or CORS headers. A partial body can
enter early hooks before Node's 408; those hooks may perform their established
first-contact accounting, but no body-dependent validation, authorization,
route, database, or Provider work begins. An undeclared body is instead
rejected inside Fastify with the normal validation envelope before its handler.

The undeclared body lies outside that route's accepted request schema, like
other parser/validation failures. The global policy therefore uses the shared
error envelope without adding a body or a route-specific 422 declaration to
every bodyless OpenAPI operation; the frozen baseline continues to describe
valid route inputs and their declared domain responses.

Once receipt completes, provider absolute and silence deadlines, the
application's synchronous workflow, the frontend's 300-second client timeout,
and stream cancellation remain authoritative. The receipt timer is not an
"enclosing server request timeout" for those workflows.

## Options rejected

- A global Fastify handler timeout would also cover valid 180–300 second AI
  work and would make streamed responses unsafe.
- A socket inactivity timeout would measure gaps rather than total receipt and
  would also affect unrelated keep-alive and response behavior.
- Relying only on a reverse proxy would leave direct self-hosted deployments
  unprotected and would make the repository's own server policy implicit.
- A new environment variable would add configuration surface for a defensive
  baseline that should be safe by default.
- Claiming that Node waits for every body before invoking Fastify would be
  false for early hooks and for methods whose routes declare no body.
