# Tasks

## 1. Lifecycle ownership contract

- [ ] 1.1 Replace the ambiguous serve function with a discriminated
      `cli-owned` or `runner-owned` boundary whose owner is known before
      invocation.
- [ ] 1.2 Classify existing runners by behavior: complete-lifecycle runners use
      `runner-owned`, while listener-only success or failure seams use
      `cli-owned`.
- [ ] 1.3 Prove a fulfilled or rejected `runner-owned` lifecycle neither
      registers signals nor triggers a second CLI-owned close, returning `0`
      or the unified error-channel status `1` respectively.

## 2. Signal latch

- [ ] 2.1 Add failing unit tests for both signal orders, repeated signals,
      first-cause ownership, idempotent exact-reference disposal, and rollback
      when the second handler registration fails.
- [ ] 2.2 Implement the injectable single-settlement latch without mutating
      global exit state or calling `process.exit`.

## 3. CLI-owned orchestration

- [ ] 3.1 Add failing CLI tests for pre-listen registration, a signal captured
      during startup, `SIGINT`/`SIGTERM`, one application close, `130`/`143`,
      and handler removal after successful shutdown.
- [ ] 3.2 Cover listener failure, registration failure, signal-close failure,
      and listener-or-registration plus application-cleanup failure while
      preserving the primary error and closing the app once.
- [ ] 3.3 Wire the production runner through CLI-owned supervision without
      changing backup/import/doctor or listener-failure semantics.

## 4. Validation and evidence

- [ ] 4.1 Run focused lifecycle tests and the owning server validation surfaces.
- [ ] 4.2 Run strict OpenSpec and an independent closure review, then record
      fixed-SHA results and every skipped external gate.
