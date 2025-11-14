## Task List

1. **Documentation Audit & Plan**
   - [ ] Enumerate current README/process/runbook sections that conflict with flow layout + startup reality; produce shortlist of files to edit or archive.
   - [ ] Update OpenSpec references (project.md if needed) to reflect documentation goals and ensure no conflicting active changes.
2. **Non-blocking Dev Bootstrap**
   - [ ] Implement `scripts/dev_env_daemon.sh` (or equivalent) that launches backend + frontend in the background, waits on health endpoints, and prints access URLs; expose via `npm run dev:daemon` / `package.json` scripts.
   - [ ] Add cleanup instructions or helper script plus README section describing usage scenarios (desktop/mobile, Chrome DevTools capture, CI hooks).
3. **Doc & Asset Refresh**
   - [ ] Rewrite README / README.en and key docs (e.g., `docs/INDEX.md`, runbooks) with the new workflow, regression command list, and references to the flow-based dashboard layout.
   - [ ] Run the stack, capture fresh Chrome DevTools screenshots (Activity Stream + Pipeline) via MCP, store under `docs/assets/`, and embed into README with reproduction steps.
4. **Validation & Alignment**
   - [ ] Verify frontend + backend via `npm run lint`, `npm run type-check`, `npm test -- --run`, Playwright `login-flow` & `dashboard-interactions`, then `scripts/validate_ci_locally.sh` and `act --pull=false` for `frontend-ci` + `ci` workflows.
   - [ ] Update README/docs with a “Last validated” note referencing the commands above and ensure OpenSpec spec deltas reflect the finished state; run `openspec validate refactor-doc-quality --strict`.
