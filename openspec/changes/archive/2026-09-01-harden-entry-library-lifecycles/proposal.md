# Harden entry and project-library lifecycles

## Why

The project library currently treats any failure from its parallel session and
project-list requests as an authentication failure and replaces navigation to
the entry route. A transient network, timeout, contract, or server failure is
therefore hidden behind the login screen. Entry and library bootstrap requests
also outlive their route owner and can start or publish follow-up work after the
surface has unmounted.

## What changes

- Classify project-library bootstrap failures: only HTTP 401 returns to entry;
  operational failures stay on the library and expose an accessible Retry.
- Give entry and library bootstrap reads an abort owner so route cleanup stops
  cancellable work and late completions cannot publish or navigate.
- Expose exact pending state for library loading, project creation, and logout,
  and prevent duplicate submissions while each operation is pending.
- Keep failures readable through live-region semantics and restore command focus
  only when the author has not deliberately moved it.

## Non-goals

- No new state-management, form, accessibility, or request dependency.
- No changes to server authentication, session, or project-list contracts.
- No cancellation claim for mutations that may already have committed.

## Validation

- Deferred and reverse-completion component tests for unmount, retry, and
  duplicate-command boundaries.
- Frontend unit, type, lint, format, build, API-drift, React Doctor, and browser
  workflow checks.
- Strict OpenSpec validation and an independent closure review.
