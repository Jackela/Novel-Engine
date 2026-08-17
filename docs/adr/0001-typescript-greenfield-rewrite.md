# Rewrite Novel Engine as a TypeScript full-stack application

---
status: accepted
---

The Python implementation, while mature, no longer matches the product's
long-term maintenance needs, and we want one language across backend and
frontend. We will rewrite Novel Engine as a TypeScript full-stack application
via an in-repo greenfield implementation: the OpenSpec capability
specification (implementation-agnostic by design) is the acceptance contract,
Playwright e2e must pass against the new implementation before cutover, and
the Python implementation stays authoritative until that day. The current
quality gates (mypy, import-linter, OpenAPI snapshot, CodeQL) will be
re-established with TypeScript equivalents rather than ported incrementally.

What the current implementation fails to deliver against today's requirements
is not yet charted; a wayfinder session will map it before any rewrite code
is written.

## Considered Options

- Strangler-fig per-route migration — rejected: leaves the architecture gates
  (import-linter, OpenAPI snapshot, single test suite) half-broken for months.
- Keep Python and generate TS types from OpenAPI — rejected as the end state:
  removes type drift but keeps the two-language maintenance burden.
