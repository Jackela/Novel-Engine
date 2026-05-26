# Verification Matrix

This matrix maps the canonical user journey to deterministic regression coverage and the required DashScope long-form gate.

| Flow | User intent | Coverage | Evidence |
| --- | --- | --- | --- |
| Landing -> guest workspace | enter from zero state without an account | Playwright smoke | `frontend/tests/e2e/frontend-smoke.spec.ts` |
| Login -> workshop | sign in with the canonical auth contract | Playwright smoke + API auth tests | `frontend/tests/e2e/frontend-smoke.spec.ts`, `tests/apps/api/test_auth.py` |
| Invalid login -> readable error | recover from auth failure | Playwright smoke + frontend API unit test | `frontend/tests/e2e/frontend-smoke.spec.ts`, `frontend/src/app/api.test.ts` |
| Back to landing -> resume workshop | leave the workshop and return without losing the session shell | Playwright smoke | `frontend/tests/e2e/frontend-smoke.spec.ts` |
| Session catalog restore | resume guest/user workspaces through validated session state instead of trusting one local blob | Playwright smoke + auth provider unit coverage | `frontend/tests/e2e/frontend-smoke.spec.ts`, `frontend/src/features/auth/AuthProvider.test.tsx` |
| Guest/user coexistence and switching | keep guest and signed-in workspaces side by side and switch without state corruption | Playwright smoke | `frontend/tests/e2e/frontend-smoke.spec.ts` |
| Create multiple manuscripts | manage more than one project in the same workspace | Playwright smoke | `frontend/tests/e2e/frontend-smoke.spec.ts` |
| Switch active manuscript | move between projects without corrupting state | Playwright smoke + hook/workbench unit coverage | `frontend/tests/e2e/frontend-smoke.spec.ts`, `frontend/src/features/story/StoryWorkbenchPage.test.tsx` |
| `/story` deep link restore | reopen the workshop with `story/run/view` query params and recover the same workspace/playback selection | Playwright smoke | `frontend/tests/e2e/frontend-smoke.spec.ts` |
| Create workspace -> run chapters -> review -> export | complete the canonical local-first author flow | Playwright smoke + API/CLI tests | `frontend/tests/e2e/frontend-smoke.spec.ts`, `tests/apps/api/test_workspaces.py`, `tests/apps/cli/test_novel_engine.py` |
| Run a workspace job on a new manuscript | use the workspace job endpoint from the workbench surface | Playwright smoke + workspace job tests | `frontend/tests/e2e/frontend-smoke.spec.ts`, `tests/apps/api/test_workspaces.py` |
| Rerun current workspace job | run an existing local workspace without reusing create-form state | Playwright smoke + workbench unit test | `frontend/tests/e2e/frontend-smoke.spec.ts`, `frontend/src/features/story/StoryWorkbenchPage.test.tsx` |
| Inspect run journal | audit run events, sidecar artifacts, review state, and exports | Playwright smoke + workbench unit tests | `frontend/tests/e2e/frontend-smoke.spec.ts`, `frontend/src/features/story/StoryWorkbenchPage.test.tsx` |
| Restore `/story` from session catalog | reopen the workshop directly through validated guest or user session state | Playwright smoke | `frontend/tests/e2e/frontend-smoke.spec.ts` |
| Guest -> user login without guest loss | promote into a signed-in workspace while preserving the guest context for later reuse | Playwright smoke + API auth tests | `frontend/tests/e2e/frontend-smoke.spec.ts`, `tests/apps/api/test_auth.py` |
| 20-chapter real-provider journey | validate end-user long-form creation via the real API and DashScope | Deterministic PR gate + manual live gate + canonical manual refresh | `.github/workflows/dashscope-longform-gate.yml` (`workflow_dispatch`, `run_live=true`), `python scripts/uat/run_dashscope_longform_uat.py --target-chapters 20 --write-canonical-reports` |

## Deterministic Gate

The default engineering gate remains:

```bash
pytest -q
ruff check src tests
mypy src tests --no-error-summary --show-column-numbers
lint-imports
npm --prefix frontend run type-check
npm --prefix frontend run test
npm --prefix frontend run build
npm --prefix frontend run test:e2e:smoke
```

## Long-Form Gate

`DashScope Longform Gate` now runs in deterministic mode for pull requests and does not call external provider APIs in PR CI. For real-provider validation, trigger the same workflow manually with `run_live=true`; that run uploads artifacts instead of rewriting tracked evidence. Use the manual canonical refresh only when you intentionally want to replace the checked-in UAT baseline:

```bash
python scripts/uat/run_dashscope_longform_uat.py --target-chapters 20 --write-canonical-reports
```

Acceptance is stricter than the earlier baseline:

- drafted chapters `>= 20`
- `export=success`
- final `blocker_count=0`
- warnings are recorded as editorial advice and do not block export
