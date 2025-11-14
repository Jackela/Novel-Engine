## Task Checklist

1. **Align toolchain metadata**
   - [x] Set `requires-python = ">=3.11"` in `pyproject.toml`.
   - [x] Update `Makefile` install/upgrade targets to reference `requirements/requirements-test.txt`.
2. **Ship guided dev bootstrap script**
   - [x] Add `scripts/dev_env.sh` that installs missing deps (optional), starts FastAPI (`src.api.main_api_server`) and Vite dev servers in the background, streams logs, and traps signals for cleanup.
   - [x] Document usage inline (usage text and `--help`) so developers know how to run/stop it.
3. **Enable AI-native Playwright validation**
   - [x] Create `frontend/tests/e2e/ai-usability.spec.ts` with mocked APIs and tag `@ai` scenarios.
   - [x] Add `npm run ai:test` (and supporting env vars) to execute the tagged Playwright suite with trace/video artifacts.
4. **Docs + CI integration**
   - [x] Document `scripts/dev_env.sh` and `npm run ai:test` in `README.md` + `docs/guides/PROCESS_MANAGEMENT.md`.
   - [x] Wire `npm run ai:test` into `tools/ci/run-all.sh` (respecting `RUN_AI_TESTS` env) and document the flag in `docs/guides/CI_PARITY.md`.
5. **Spec + validation**
   - [x] Add `process-management` spec delta describing the new dev bootstrap script and AI Playwright hook.
   - [x] Run `openspec validate update-dev-debugging --strict`.
   - [x] Execute regression checks: `npm run ai:test` (frontend) to ensure the new workflow passes.
