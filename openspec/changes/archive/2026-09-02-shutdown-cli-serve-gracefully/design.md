# Design: signal-owned CLI serve lifecycle

## Signal latch

A small CLI-owned module adapts process signal events behind an injectable
port. It registers stable handler references for `SIGINT` and `SIGTERM`,
settles one promise from the first signal, and keeps both handlers installed
while shutdown is in progress so later signals cannot start a second close.
Disposal removes those exact references, is idempotent, and is a no-fail
operation for valid references registered through the same source. Partial
registration failure therefore removes anything already installed before the
original registration error escapes unchanged.

The signal value maps to the conventional shell status (`128 + 2 = 130` for
`SIGINT`, `128 + 15 = 143` for `SIGTERM`). The helper does not call
`process.exit`, mutate global exit state, or own Fastify.

## Serve orchestration

The serve runner is a discriminated boundary whose lifecycle owner is known
before invocation:

- `cli-owned` starts the listener and returns once it is listening. This is the
  production default.
- `runner-owned` owns listening, waiting, and application cleanup, and returns
  only when its whole injected lifecycle is complete. This preserves the
  existing test seam without process-signal coupling.

For `cli-owned`, `serveCommand` creates the latch after building the app but
before invoking the runner. A signal arriving during listener startup is
therefore captured rather than left to the process default; after the runner
settles, the captured first signal owns the same shutdown path. The runner's
successful return establishes that listening began, after which the command
awaits the latch. A `runner-owned` invocation never registers CLI signal
handlers. Its fulfillment returns command status `0`; its rejection reaches the
existing CLI error channel and returns `1`. The CLI never closes the app a
second time in either runner-owned outcome, because that runner's contract owns
cleanup on success and failure. A plain function is not silently assigned an
ownership mode; the runner result itself remains `void`.

The winning CLI-owned signal starts one `app.close()` operation, which drains
Fastify and closes the injected database/lock lifecycle. A successful close
returns the mapped signal exit code to `main`, which continues to set
`process.exitCode`. If close rejects, the existing CLI error channel exposes
that failure and returns `1`; the signal code never hides failed cleanup.

Every path that registers handlers disposes the exact references. Registration
failure closes the already-built app. Listener-start failure retains the
existing primary error while handler disposal and application cleanup are
attempted. If registration or listening fails together with application
cleanup, an aggregate preserves the primary failure first and the cleanup
failure after it. No failure path may abandon an app or subscription. The
signal source remains injectable so tests never send real signals to their own
process, but its removal operation must honor the no-fail contract above.

After successful registration, the latch wait is a resolve-only promise: its
event source can fail while registering subscriptions, but removal is total and
there is no separate rejection-capable wait seam. Registration failure follows
the cleanup rules above rather than introducing an uncovered wait-rejection
path.

## Deferred drain policy

Fastify close can wait for active streams. A time-bounded drain, forced abort,
or second-signal escalation requires a separate policy and is intentionally not
smuggled into this lifecycle fix.
