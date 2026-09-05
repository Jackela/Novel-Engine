# Design: immediate app-local workflow admission

## One guard, two limits

Each `buildApp()` owns one `InFlightOperationGuard`, preserving the current
single-process authority model. The guard admits at most four expensive
workflows across the app and two for one project by default. Configuration may
override those values with integers from 1 through 1024; the per-project value
cannot exceed the app value. Resolution and validation happen before database
open, migration, backup, reconciliation, Provider construction, or traffic.

The five counted workflow families are synchronous proposal, streaming
proposal, editorial review, export, and retry of proposal/review/export. Each
HTTP request holds one permit regardless of format or Provider. A whole-book
run is not another unit: each streamed chapter request holds its own permit.
Project deletion remains project-exclusive but consumes no capacity, so an
idle project can be deleted even when other projects fill the app limit.

## Atomic priority and refusal

One synchronous guard transition applies this fixed order after HTTP
authentication, CSRF, and schema validation:

1. an existing project-exclusive owner returns 409 `OPERATION_IN_FLIGHT`;
2. an identical target returns 409 `OPERATION_IN_FLIGHT`;
3. a full project returns the project-scoped capacity error;
4. a full app returns the application-scoped capacity error;
5. otherwise the guard records one permit and both counts atomically.

Project-scoped capacity wins when both limits are full because it is the more
specific diagnosis. Existing application seams acquire before Provider
construction and durable workflow evidence. Some missing-resource or invalid
retry requests can therefore see capacity refusal while the app is saturated;
splitting validation from atomic admission would widen every workflow and is
not part of this bounded-resource change.

Refusal returns 503 `OPERATION_CAPACITY_EXCEEDED`, `Retry-After: 5`, and:

```json
{
  "error": {
    "code": "OPERATION_CAPACITY_EXCEEDED",
    "message": "Studio operation capacity is exhausted.",
    "details": {
      "scope": "project",
      "limit": 2,
      "in_flight": 2,
      "project_id": "project-id",
      "retry_after_seconds": 5
    }
  }
}
```

`scope` is `project` or `application`; `in_flight` is the count for that scope,
and `project_id` always identifies the requesting project. `Retry-After` is an
earliest retry hint, not a promise that capacity will exist in five seconds,
and neither server nor frontend retries automatically. The header is emitted
through a controlled `AppError` response-header seam and exposed through CORS.
The 503 OpenAPI response documents the optional header because
persistence-unavailable 503 responses do not carry it.

## Token-bound lifetime

`acquire(target)` returns a permit with an opaque unique token and idempotent
`release()`. The running map stores both target and token; release changes
state only when that exact token still owns the key. A duplicate or delayed
release is a no-op, so an old cleanup cannot release a later operation that
reused the same target. Failed acquisition changes no map or counter.

Project-exclusive acquisition uses the same token rule. This closes the same
late-release hazard for project deletion and centralizes guard invariants.
Callers no longer pair public `enter/exit` methods themselves.

A workflow holds its permit until its outermost `finally` finishes all owned
cleanup. For streams this includes response drain waits, disconnect handling,
`frames.return()`, Provider disposal, and in-flight exit. For exports it
includes artifact acknowledgement or rollback and cleanup reporting. Landing a
terminal job, yielding a terminal frame, or observing response close does not
release streaming capacity early. A non-streaming permit may release after its
service and owned cleanup finish, before Fastify serializes the already-small
terminal payload; ordinary response serialization is not expensive-workflow
ownership.

## Zero-side-effect refusal

Capacity refusal occurs before Provider factory invocation and before creation
of a job, job event, usage event, project snapshot, snapshot document, review,
review issue, export row, staged artifact, manifest, cleanup intent, or final
artifact. Retry refusal is specifically before its new `running` retry job and
first event. Streaming refusal happens on the first generator pull, before the
reply is hijacked, so it remains a normal JSON envelope.

## Options rejected

- A request queue would retain sockets, hide overload duration, and introduce
  cancellation/fairness/shutdown ownership absent from the synchronous model.
- Database leases or a distributed semaphore would contradict the current
  one-process data-directory authority and add recovery states without benefit.
- Target-string `exit()` permits late cleanup to release a newer owner; token
  identity is the smaller reliable contract.
- Reusing `SERVICE_UNAVAILABLE` would conflate retryable saturation with an app
  instance that has no persistence service.

## Active-delta archive ordering

`2026-09-02-fail-loud-env-local-loading` also replaces the complete
`Environment configuration surface` requirement. This change deliberately
includes that active delta's fail-loud text and scenarios. After required CI is
green, the fail-loud change MUST archive first; this capacity change is then
revalidated against that canonical result and archives second. Reversing the
order would let the older complete-replacement delta erase the capacity
configuration contract.
