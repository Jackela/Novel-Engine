## ADDED Requirements

### Requirement: Bounded inbound HTTP request receipt

The HTTP server MUST configure a 60,000 millisecond threshold for receiving
complete request headers, a 120,000 millisecond threshold for receiving a
complete inbound request, and an incomplete-connection scan interval no longer
than 5,000 milliseconds. When a scan observes an incomplete request beyond its
applicable threshold, the server MUST respond HTTP 408 and close its
connection. The existing request-body size boundary MUST remain in force.

A request that advertises a non-empty body for a route with no body contract
MUST instead be rejected with HTTP 422 `VALIDATION_ERROR` and its connection
MUST close before that route's handler runs. Its unified-envelope
`details.errors` MUST contain a stable `body` field item with a machine-readable
type and a human-readable message. For a body-bearing route, early request and
parsing hooks MAY run while its body is arriving, but body validation,
authorization, the route handler, database operations, and Provider dispatch
MUST NOT run until parsing completes successfully.

Once a request has been received completely, the receipt deadlines MUST no
longer constrain its route handler, synchronous Provider work, or streamed
response. The HTTP server owns incomplete-request 408 responses outside the
application reply path: partial headers expire before Fastify, while a partial
body may already have entered early request/parsing hooks. Those 408 responses
therefore are not required to use the unified JSON error envelope.

#### Scenario: Slow headers expire before application work

- **GIVEN** a client opens a connection but does not finish request headers
- **WHEN** an incomplete-connection scan observes the header threshold exceeded
- **THEN** the server responds 408 and closes the connection
- **AND** Fastify hooks and route handlers have not run for that request

#### Scenario: Slow body expires before application work

- **GIVEN** a client declares a request body but sends only part of it
- **WHEN** an incomplete-connection scan observes the request threshold exceeded
- **THEN** the server responds 408 and closes the connection
- **AND** body validation, authorization, the route handler, database work, and
  Provider dispatch have not run, although early request/parsing hooks may have
  run

#### Scenario: Undeclared request body never reaches its handler

- **GIVEN** a route has no request-body contract
- **WHEN** a client advertises a non-empty body for that route
- **THEN** the server returns 422 `VALIDATION_ERROR` and closes the connection
- **AND** `details.errors` identifies field `body` with a stable type and
  message
- **AND** the route handler does not run while that body remains incomplete

#### Scenario: Completed receipt does not time out a long handler

- **GIVEN** a valid request is received completely within both receipt
  deadlines
- **WHEN** its synchronous Provider workflow continues longer than the
  complete-request receipt deadline
- **THEN** the receipt deadline does not terminate the handler or response
- **AND** the workflow remains governed by its Provider, application, and
  client deadlines

## MODIFIED Requirements

### Requirement: Unified error envelope
Every API error response produced through the application reply lifecycle MUST
use a single error envelope with a stable `code`, a human-readable `message`,
and an optional `details` object. The HTTP server's incomplete-request 408 is
the sole exception: it MAY be emitted directly outside the application reply
path, whether it wins before Fastify sees partial headers or after only early
request/parsing hooks have observed a partial body. The legacy
`{"detail": ...}` shape MUST NOT appear. A document save conflict (HTTP 409)
MUST identify the conflicting revision inside `details`.

#### Scenario: Validation failure
- **GIVEN** a request body violates a schema constraint
- **WHEN** the API responds through the application reply lifecycle
- **THEN** the status is 422 and the body is `{"error": {"code": "VALIDATION_ERROR", "message": ..., "details": ...}}`
- **AND** each invalid field is listed with its message and error type

#### Scenario: Incomplete-request 408 stays parser-owned
- **GIVEN** an incomplete request is observed beyond its receipt threshold
- **WHEN** the HTTP server emits its timeout response outside the application
  reply path
- **THEN** the status is 408 and the connection closes
- **AND** that parser-owned response is not required to carry the unified JSON
  envelope

#### Scenario: Conflict error carries the current revision
- **GIVEN** a client saves a document based on revision A while the document points to revision B
- **WHEN** the API responds
- **THEN** the status is 409 with error code `REVISION_CONFLICT`
- **AND** `details.current_revision_id` equals revision B's identifier

#### Scenario: Internal failure is opaque but traceable
- **GIVEN** an unhandled failure occurs while serving a request
- **WHEN** the API responds
- **THEN** the status is 500 with error code `INTERNAL_ERROR` and an `error_id`
- **AND** the response leaks no stack trace or internal detail

### Requirement: Provider transient failure handling
For synchronous structured generation calls, both HTTP providers MUST share
one retry policy with an identical retryable set: HTTP 429, 500, 502, 503,
504, transport timeout (including an absolute response deadline), and malformed
JSON responses are retried up to the configured limit (default three total
attempts, with one-second spacing between attempts); every other error fails
immediately without retry. Retry decisions MUST read structured error fields
(status code, timeout, retryability), never substring matches on
human-readable message text, and both HTTP providers MUST share the same retry
module. A retryable per-attempt deadline failure MUST NOT record the normal
failed proposal outcome until the attempt budget is exhausted. Synchronous
generation steps (`chapter_draft`, `chapter_revision`) MUST be granted a
timeout floor of 180 seconds. Any product-owned client or application-handler
timeout that remains active while Provider execution runs MUST NOT be shorter
than that floor; the earlier inbound request-receipt threshold is complete
before Provider execution and does not enclose it.

#### Scenario: Transient error is retried
- **GIVEN** the provider answers 429 once and then succeeds
- **WHEN** a proposal is requested
- **THEN** the job completes with a proposal
- **AND** the transient failure is not surfaced as a job error

#### Scenario: Persistent failure exhausts retries
- **GIVEN** the provider answers 503 on every attempt
- **WHEN** a proposal is requested
- **THEN** the job fails with the provider error after three total attempts by default

#### Scenario: Non-retryable failure is immediate
- **GIVEN** the provider answers 401
- **WHEN** a proposal is requested
- **THEN** the job fails after one attempt

#### Scenario: Generation timeout floor
- **GIVEN** a chapter revision generation on an HTTP provider
- **WHEN** the request is dispatched
- **THEN** the provider call is granted at least 180 seconds
- **AND** no product-owned client or application-handler timeout that remains
  active during Provider execution ends sooner
