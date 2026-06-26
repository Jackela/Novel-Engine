# Changelog

## 0.3.1

- Remediated Linus-style audit findings across security, architecture,
  documentation, and dead code.
- Added AI guardrails, local safety checks, and stronger CI/pre-commit mypy
  coverage for tests.
- Hardened AI proposal acceptance, app-owned API runtime settings, token bucket
  cleanup, and frontend API response contract parsing.

## 0.3.0

- Added the self-hosted Novel Studio API and React writing workspace.
- Added SQLite-backed projects, documents, revisions, snapshots, reviews,
  exports, durable jobs, sessions, CSRF protection, and rate limiting.
- Added provider adapters for mock, DashScope, and OpenAI-compatible text
  generation.
- Hardened FTS5 search query construction, startup factories, LLM defaults,
  delete endpoints, and documentation consistency.
