# Tasks

## 1. Executable receipt policy

- [ ] 1.1 Add failing policy assertions for finite header/request receipt
      thresholds and connection-check interval while handler and connection
      timeouts remain disabled.
- [ ] 1.2 Define the HTTP receipt policy outside the near-limit API composition
      root and apply it when Fastify is constructed.

## 2. Raw connection behavior

- [ ] 2.1 Add a failing raw-socket test proving partial headers receive 408,
      close, and never enter Fastify.
- [ ] 2.2 Add a failing raw-socket test proving a partial declared body may
      enter early hooks but never reaches validation, authorization, its route
      handler, database, or Provider before 408 and close.
- [ ] 2.3 Prove a fully received request can outlive the receipt deadline inside
      its handler and still return its normal response.
- [ ] 2.4 Reject non-empty body framing on a route with no body contract with a
      stable 422 `VALIDATION_ERROR` and connection close before its handler
      runs; assert the full envelope and stable body field/type/message.
- [ ] 2.5 Prove a fully received streamed request may deliver its first and
      later SSE frames after the receipt threshold without being terminated.

## 3. Compatibility and evidence

- [ ] 3.1 Re-run body-limit and long-workflow coverage plus the owning server
      validation surfaces.
- [ ] 3.2 Confirm the undeclared-body rejection remains a transport policy for
      requests outside a route's accepted body contract and does not drift the
      route OpenAPI baseline.
- [ ] 3.3 Run strict OpenSpec and independent review, then record fixed-SHA
      evidence and every skipped external gate.
