# Contributing to Novel Engine

The full engineering conventions, architecture contracts, and coding red lines
live in the root [AGENTS.md](AGENTS.md). This file is only a pointer — when in
doubt, AGENTS.md is authoritative.

## Environment

- Node 24 (server) / Node 22 (validate scripts), pnpm 11 workspace (`server/` + `frontend/`).
- Copy env templates as described in `server/src/shared/infrastructure/config/server_config.ts` docs; never commit `.env*`.

## Common validation commands

```bash
pnpm --dir server gates                      # SSOT, hygiene, size, migration, OpenAPI gates
pnpm --dir frontend lint && pnpm --dir frontend type-check && pnpm --dir frontend test:unit && pnpm --dir frontend build
pnpm spec:validate                           # OpenSpec product spec
```

CI (`.github/workflows/ci.yml`) is the authoritative full gate.

## Issues and PRs

- Issues and specs are tracked as GitHub issues; see `docs/agents/issue-tracker.md` and `docs/agents/triage-labels.md` for conventions.
- PRs are squash-merged and must be green in CI before merge.
- Domain vocabulary is defined in [CONTEXT.md](CONTEXT.md); use its canonical terms.
