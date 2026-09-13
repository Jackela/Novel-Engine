# Tasks

## 1. Response-writer contract

- [x] 1.1 Add failing tests proving `write(true)` pulls once and
      `write(false)` stops before the next generator pull.
- [x] 1.2 Add failing drain tests proving one resume per drain and no temporary
      listener accumulation across repeated pressure cycles.
- [x] 1.3 Add failing fake-clock coverage proving a drain wait expires after
      30 seconds, aborts unfinished generation, and cannot be revived by a
      late drain.
- [x] 1.4 Extract a focused response monitor/writer that preserves frame order,
      writer-observable exact first cause, stable drain-timeout diagnostics,
      and one-write-per-frame semantics.

## 2. Disconnect and failure ownership

- [x] 2.1 Add failing tests for premature response close, socket close, exact
      response error, and request cancellation winning while a drain is pending.
- [x] 2.2 Prove a late drain never resumes pulling, the raw response is not
      ended after disconnect, and generator return runs exactly once.
- [x] 2.3 Prove normal `finish` then `close` does not cancel generation or
      overwrite a first cause.
- [x] 2.4 Preserve primary-first aggregation when response and generator
      cleanup both fail, without promoting a normal disconnect into a server
      error.

## 3. Unknown-outcome audit refresh

- [x] 3.1 Update frontend stream and whole-book contracts so cancellation no
      longer promises that the server persisted nothing after a terminal
      outcome may have landed.
- [x] 3.2 Represent terminal-frame loss as `outcome unknown`; start and await a
      non-coalesced jobs audit read after client-observed stream settlement,
      gate proposal/retry/whole-book-resume actions until it succeeds, and keep
      refresh failure in the unknown state with an audit-refresh-only Retry.
- [x] 3.3 After a successful audit refresh, warn that the previous attempt may
      already be saved and label the explicit next action as generating another
      proposal; never infer correlation or auto-accept an unobserved job.
- [x] 3.4 Add manual and whole-book hook/UI tests for Stop, transport loss,
      done-frame and error-frame loss, client-settlement refresh ordering and
      failure, same-project document change, project-identity isolation, action
      gating, stale-result suppression, no false server-quiescence claim, and
      no later whole-book chapter.

## 4. Route integration and evidence

- [x] 4.1 Wire the proposal route through the focused writer without changing
      its pre-stream validation, SSE schema, frame format, or landing behavior.
- [x] 4.2 Add route/application integration coverage for drain timeout both
      before terminal persistence (no job/usage/revision) and after a terminal
      done or error job lands (no rollback and no extra failed job).
- [x] 4.3 Re-run disconnect persistence and repeated-listener lifecycle tests,
      frontend proposal/whole-book tests, and the owning package validations.
- [x] 4.4 Run strict OpenSpec and independent review, then record fixed-SHA
      evidence and every skipped external gate.
