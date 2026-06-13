## Summary

- product behavior changed:
- canonical OpenSpec requirement:

## Validation

- [ ] `uv run ruff check src tests`
- [ ] `uv run pytest -q`
- [ ] `pnpm spec:validate`
- [ ] `pnpm --dir frontend type-check`
- [ ] `pnpm --dir frontend test:unit`
- [ ] `pnpm --dir frontend build`
- [ ] Relevant Studio flow verified in Chromium
- [ ] SSOT and OpenAPI snapshot checks pass

## Data and Compatibility

- [ ] SQLite migration and backup behavior reviewed
- [ ] Revision, snapshot, or export semantics are covered by tests
- [ ] No retired workspace, Knowledge, RPG Character, or writing CLI surface returned
- [ ] Public API changes are represented in `openspec/specs/novel-studio/spec.md`
