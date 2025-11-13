## Why
- The repo contains hundreds of process/validation documents created before the flow-based dashboard refactor; many reference deprecated grid classes, blocking scripts (`npm run dev`), or missing act-based CI parity steps, making onboarding noisy and inaccurate.
- README / QUICK_START sections no longer match reality: the current workflow requires a non-blocking dual-stack startup (backend API + Vite) and Flow layout verification, but documentation still suggests manual terminals and lacks verified screenshots.
- Stakeholders explicitly asked for "使用脚本包装好启动命令" and fresh Chrome DevTools captures to prove the dashboard is less crowded. Without an authoritative doc + asset set, quality signals remain ambiguous.

## What Changes
- Audit and restructure documentation: consolidate redundant runbooks/process reports, remove archived validation artifacts from prominent entry points, and align README + docs/navigation with the actual flow layout behaviour, regression commands, and CI/act expectations.
- Introduce a supported non-blocking dev bootstrap (e.g., `scripts/dev_env_daemon.sh` plus npm wrapper) that brings up backend + frontend, waits on health checks, and frees the terminal; document usage plus cleanup/health verification.
- Run the real stack, capture updated dashboard screenshots via Chrome DevTools MCP (Activity Stream + Pipeline composite) and embed in README/docs along with guidance for rerunning the capture.
- Update OpenSpec specs to codify the doc accuracy + startup script expectations so future work must keep docs/automation in sync.

## Impact
- **Docs**: `README.md`, `README.en.md`, `docs/INDEX.md`, process/runbook folders, selected validation reports (either archived or summarized), new screenshot assets under `docs/assets/`.
- **Tooling**: new dev orchestration script + npm/yarn targets, possible updates to `scripts/validate_ci_locally.sh` to call the wrapper.
- **Specs**: `process-management` gains explicit requirement for the non-blocking script + documentation updates; new `docs-alignment` capability enumerates README/process alignment and screenshot evidence.
- **Testing**: Manual/manual+Playwright verification (login flow + dashboard interactions), lint/type-check/vitest, and `act -W .github/workflows/{frontend-ci,ci}.yml -j build-and-test/tests` to prove docs match reality.
