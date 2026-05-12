## Summary

- what changed:
- why it changed:

## Validation

- [ ] `uv run pytest -q`
- [ ] `uv run ruff check src tests`
- [ ] `uv run mypy src tests --no-error-summary --show-column-numbers`
- [ ] `uv run lint-imports`
- [ ] `npm --prefix frontend run type-check`
- [ ] `npm --prefix frontend run test`
- [ ] `npm --prefix frontend run build`
- [ ] `npm --prefix frontend audit --audit-level=high`
- [ ] `npm --prefix frontend run test:e2e:smoke`
- [ ] `npm --prefix frontend run test:e2e:full-audit`
- [ ] `npm --prefix frontend run audit:dependencies`
- [ ] `npm --prefix frontend run audit:exports`
- [ ] `uv run python scripts/qa/check_openapi_snapshot.py`
- [ ] `uv run python scripts/qa/run_api_public_audit.py`
- [ ] `DashScope Longform Gate` deterministic PR check passed
- [ ] If this PR requires external-provider validation: manually run workflow `DashScope Longform Gate` with `run_live=true`
- [ ] If this PR refreshes canonical UAT evidence: `uv run python scripts/uat/run_dashscope_longform_uat.py --target-chapters 20 --write-canonical-reports`

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
