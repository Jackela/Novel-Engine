## 1. Implementation
- [x] 1.1 Align `/api/characters` response shape to normalized objects with required fields and deterministic ordering.
- [x] 1.2 Ensure list/detail endpoints honor workspace scoping and emit cache/etag hints for reuse.
- [x] 1.3 Simplify frontend transforms/queries to consume the normalized shape and hydrate dashboard datasets.
- [x] 1.4 Add tests for list ordering, workspace isolation, and transform parity across list/detail.

## 2. Validation
- [x] 2.1 Backend tests (pytest) / mypy (if touched)
- [x] 2.2 `npm run lint:all`
- [x] 2.3 `npm run type-check`
- [x] 2.4 `npm run test`
- [x] 2.5 `npm run test:e2e:smoke`
