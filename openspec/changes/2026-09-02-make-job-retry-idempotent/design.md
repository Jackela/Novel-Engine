# Design: durable retry-attempt identity

## Wire contract and key lifecycle

Retry attempt identity is transport metadata, so the route requires an
`Idempotency-Key` header rather than adding it to the inherited Job request
payload. The accepted value is an opaque, case-sensitive ASCII token of 16
through 128 characters using only letters, digits, `.`, `_`, `~`, and `-`.
The Studio generates a UUID with the browser cryptographic API before dispatch.
The server neither trims nor case-folds the parsed value.

The frontend owns a retry-attempt registry in browser `sessionStorage`, keyed
by the authenticated owner session, project id, and source Job id. It writes
the generated key synchronously before starting the request, so two
activations that escape the visual pending guard still use one attempt
identity. It retains the key after
an ambiguous network error, client timeout, abort, project switch, page reload
within the same browser-tab session, every 409, or every 503. Returning to that
owner/project/source retry reuses the key. A terminal Job response or a 401,
403, 404, or 422 response clears the entry; the next explicit retry then
generates a different key. Retaining an unused key after an admission 409/503
is safe and removes any need for the client to infer whether reservation
occurred. Logout or owner
session replacement clears the registry. A late response from an old project
may settle only its matching registry entry and must not mutate the visible
project.

The tab-session registry is recovery state, not an audit authority. The
persisted retry Job and its key are authoritative after reservation. The key
is not added to Job response bodies, events, usage evidence, logs, or artifact
paths.

## Persistence identity

Retry Jobs gain nullable `retry_idempotency_key`; fresh, import, historical,
and pre-migration retry Jobs retain null. A generated unique partial index over
`(project_id, retry_of_job_id, retry_idempotency_key)` for non-null keys is the
database concurrency authority.

The logical uniqueness scope is owner, project, source Job, and key. Project
identifiers are globally unique, and every lookup first proves the route
project belongs to the authenticated owner, so the physical project/source/key
index realizes that logical scope without denormalizing owner id onto Jobs.
The same text key may therefore be used independently for another owner,
project, or source Job, while no request may use it to discover or replay a Job
outside its authenticated project scope.

## Reserve, replay, and execute

The application separates retry admission from execution:

1. It validates authentication, project/source scope, and the required header,
   then performs a cheap scoped lookup. An existing terminal keyed retry is
   returned immediately; an existing `running` retry maps to the stable keyed
   409. These replay paths do not acquire provider capacity.
2. An apparently new attempt acquires the existing project retry/capacity
   permit, then enters one immediate store transaction. That transaction
   repeats scoped lookup and source eligibility, and either returns the winner,
   reports it in flight, or inserts exactly one `running` retry Job with its
   first event and idempotency key.
3. Only the request whose transaction created the row executes proposal,
   review, or export work. A uniqueness race reloads the winning row and follows
   its terminal-or-running result; it never falls through to execution.
   The implementation may normalize only a conflict from the retry-key unique
   index at the Job-row insert itself. A first-event or any other constraint
   failure rolls back the complete reservation and remains visible.
4. Existing atomic terminal transitions remain unchanged. Successful proposal
   retry completion and its usage event still commit together; review and
   export retain their snapshot/artifact outcome transactions.

The stable in-flight choice avoids holding an HTTP request open for provider or
filesystem work whose duration is unknown. A same-key `running` replay returns
the existing 409 `OPERATION_IN_FLIGHT` with `Retry-After: 1`; it creates no row
or event and performs no work. Once the creator reaches `completed` or `failed`,
the next replay returns 200 with that same full Job and its existing events. If
the process stops after reservation, normal startup recovery changes the Job
to `interrupted`; the same key then returns that terminal interrupted Job. A
new attempt requires a different key.

The first scoped lookup is only a fast path. The immediate reservation
transaction and unique index are authoritative across concurrent requests and
restarts within the repository's single-process data-directory contract.
Capacity refusal before reservation returns the existing 503 and leaves the
key reusable because no Job exists.

## Operation coverage and evidence

The mechanism wraps the shared retry admission path before dispatch by kind,
so it applies equally when the source is a fresh or earlier retry Job of kind
`proposal`, `review`, or `export`. Import and non-retryable states retain their
existing rejection. Replaying a terminal key returns stored Job state only:

- proposal replay does not construct a provider, generate text, or add usage;
- review replay does not evaluate, create a snapshot/assessment, or add issues;
- export replay does not render, publish, create a snapshot/artifact, or run
  compensation;
- no replay appends a Job event or refreshes timestamps.

Different keys are never deduplicated with each other. After the prior attempt
is terminal, an author may explicitly submit a different key for the same
eligible source Job and receive a distinct retry Job. Existing same-project
pipeline and global capacity guards still decide whether a distinct attempt
may start at that moment.

## Compatibility and migration

The header is required in the Fastify request schema, allowed by the CORS
contract, and documented as a required OpenAPI header parameter with its
pattern and bounds. Missing, malformed, short, or overlong keys receive the
ordinary unified 422 validation response before retry reservation. A JSON body
field is not an alternative; this avoids two competing key authorities. CSRF,
credentials, error-envelope,
abort, and timeout behavior remain owned by the shared frontend request path.
The schema uses Fastify's lowercase `idempotency-key` property and permits the
normal request-header object; duplicate headers are rejected after Node's
combined comma value fails the token pattern. Header validation is
intentionally schema-first, so an anonymous request with a missing or invalid key receives
422 before the authentication pre-handler.

The migration is generated through the repository channel. The new column is
nullable so existing rows migrate without synthesized identities; the partial
unique index applies only to newly keyed retries. Deployment does not infer
that two historical retry Jobs were one attempt.

## Options rejected

- Deduplicating only in React does not cover response loss, reload, another
  client, concurrent requests, or a server restart.
- Looking up the newest retry Job without a client key can mistake an earlier
  author intent for the request being replayed.
- Returning the existing `running` Job with 200 would violate the synchronous
  terminal-response contract; waiting couples a second request to unbounded
  provider/filesystem duration.
- Storing the key only in an event or request JSON cannot support an efficient,
  authoritative uniqueness constraint and mixes transport identity with the
  inherited operation payload.
- Silently accepting a missing key preserves the duplicate side effect for old
  clients and creates two retry contracts indefinitely.
