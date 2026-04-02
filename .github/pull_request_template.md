## Summary

- what changed:
- why it changed:

## Validation

- [ ] `pytest -q`
- [ ] `ruff check src tests`
- [ ] `mypy src tests --no-error-summary --show-column-numbers`
- [ ] `lint-imports`
- [ ] `npm --prefix frontend run type-check`
- [ ] `npm --prefix frontend run test`
- [ ] `npm --prefix frontend run build`
- [ ] `npm --prefix frontend run test:e2e:smoke`

## Risk Review

- [ ] No legacy compatibility layer or silent fallback was introduced
- [ ] Public contracts changed intentionally and are covered by tests
- [ ] Generated artifacts, caches, and temporary reports are not committed
- [ ] README and repo-level docs remain accurate

## Notes

- follow-up work:
- rollout or operational concerns:
