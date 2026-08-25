## Summary

- product behavior changed:
- canonical OpenSpec requirement:

## Validation

- [ ] `pnpm --dir server gates`
- [ ] `pnpm --dir server type-check`
- [ ] `pnpm --dir server lint`
- [ ] `pnpm --dir server test`
- [ ] `pnpm spec:validate`
- [ ] `pnpm --dir frontend type-check`
- [ ] `pnpm --dir frontend test:unit`
- [ ] `pnpm --dir frontend build`
- [ ] Relevant Studio flow verified in Chromium
- [ ] OpenAPI baseline regenerated if routes changed (`pnpm --dir server openapi:snapshot`)

## Data and Compatibility

- [ ] SQLite migration and backup behavior reviewed
- [ ] Revision, snapshot, or export semantics are covered by tests
- [ ] No retired workspace, Knowledge, RPG Character, or writing CLI surface returned
- [ ] Public API changes are represented in `openspec/specs/novel-engine/spec.md`
