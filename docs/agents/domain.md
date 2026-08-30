# Domain docs

How engineering skills consume Novel Engine's domain documentation while
exploring or changing the repository.

## Single context

This repository has one canonical domain context: read the root
[`CONTEXT.md`](../../CONTEXT.md) before naming domain concepts, proposing a
change, or tracing behavior. It defines the shared vocabulary for Novel Engine
and for the existing contexts under `server/src/`.

There is no `CONTEXT-MAP.md` and no per-context `CONTEXT.md` convention. Do
not create or infer a context map; use the root context as the vocabulary
authority.

## Decisions and local rules

- Read every relevant decision record in [`docs/adr/`](../adr/) before making
  an architectural proposal or implementation decision. Surface a conflict
  with an ADR instead of silently overriding it.
- Start with the root [`AGENTS.md`](../../AGENTS.md), then read any nested
  `AGENTS.md` that governs the target directory. Nested instructions add local
  rules and take precedence within their directory; they do not replace the
  root domain vocabulary.
- The existing `server/src/contexts/` directories are bounded contexts in the
  architecture. Use the root `CONTEXT.md` terminology when discussing, naming,
  or testing their capabilities; do not introduce per-context glossaries or
  synonym drift.

## Vocabulary rule

Use terms exactly as defined in `CONTEXT.md` in issues, specifications, code,
tests, and user-facing documentation. If a needed term is absent, record the
gap for domain modeling rather than silently inventing competing terminology.
