# Shut down `serve` gracefully on process signals

## Why

The CLI starts Fastify but installs no `SIGINT` or `SIGTERM` lifecycle. The
operating system can terminate the process while the app still owns its HTTP
listener, SQLite handle, and data-directory lock, bypassing the explicit close
path used elsewhere.

## What changes

- Make serve-runner ownership explicit before invocation: `cli-owned` means the
  CLI installs the signal lifecycle before starting the listener, while
  `runner-owned` means an injected runner owns its full lifecycle and returns
  only after completion.
- Latch the first `SIGINT` or `SIGTERM` after `serve` starts listening.
- Await `app.close()` exactly once, ignore later shutdown signals while that
  close is in progress, and remove the exact registered listeners on every
  terminal path.
- Preserve conventional successful signal exit codes (`130` and `143`) while a
  close failure remains visible and returns exit code `1`.

## Impact

- Production `serve` remains alive under CLI-owned signal supervision and
  releases Fastify, SQLite, and directory-lock resources before returning.
- Injected serve runners must declare lifecycle ownership. Full-lifecycle test
  runners migrate to `runner-owned`; listener-only success or failure seams use
  `cli-owned`, without changing HTTP or database shapes.
- No dependency, migration, public API, backup/import/doctor, or request
  semantics change.

## Non-goals

- No forced process exit, second-signal escalation, or bounded drain timeout.
- No special cancellation policy for active SSE/provider work; that is a
  separate resource-drain finding.
- No change to backup/import/doctor or to Fastify's request semantics.

## Validation

- Signal-latch unit tests for first-cause ownership and listener removal.
- CLI lifecycle tests for both signals, exact-once close, exit codes, normal
  completion, listen failure, and close failure.
- Full server gates, tests, strict OpenSpec, and fixed-SHA evidence.
