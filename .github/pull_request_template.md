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
- [ ] `DashScope Longform Gate` passed on the PR
- [ ] If this PR refreshes the canonical UAT evidence: `python scripts/uat/run_dashscope_longform_uat.py --target-chapters 20 --write-canonical-reports`

## Risk Review

- [ ] No legacy compatibility layer or silent fallback was introduced
- [ ] Publish semantics still require `publish=success` with `warning=0` and `blocker=0`
- [ ] Public contracts changed intentionally and are covered by tests
- [ ] Generated artifacts, caches, and temporary reports are not committed
- [ ] README and repo-level docs remain accurate
- [ ] `docs/reports/uat/VERIFICATION_MATRIX.md` still matches the implemented user journey

## Notes

- follow-up work:
- rollout or operational concerns:
