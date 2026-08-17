## 1. Specification

- [x] 1.1 Rename the product label in the capability spec and add this change delta
- [x] 1.2 Define Novel Engine as canonical in CONTEXT.md and mark Novel Studio as removed

## 2. Surfaces

- [x] 2.1 Backend: settings defaults (`project_name`, API title), docstrings, CLI help, log messages
- [x] 2.2 Frontend: `index.html` title/description, entry/library/status strings, `api.ts` offline messages
- [x] 2.3 Docs and tooling: README, AGENTS.md, DESIGN.md, `.env.example`, CI workflow, issue templates, `check_ssot` message, OpenAPI snapshot

## 3. Verification

- [x] 3.1 `corepack pnpm spec:validate` green
- [x] 3.2 `uv run python scripts/qa/check_openapi_snapshot.py` green after snapshot update
- [ ] 3.3 CI green, then archive this change
