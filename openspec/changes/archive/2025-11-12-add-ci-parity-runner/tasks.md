## Task List

1. **Create unified CI entrypoint**
   - [x] Add `tools/ci/run-all.sh` that installs dependencies, runs lint/typecheck/unit/integration/build stages, exposes `RUN_INTEGRATION`/`RUN_E2E` toggles, and emits clear logs + exit codes.
   - [x] Update primary workflows (starting with `.github/workflows/ci.yml` and any other pipeline invoking tests) to call the script instead of ad-hoc commands.
2. **Provide runner container + Make targets**
   - [x] Add `devops/runner.Dockerfile` that mirrors `ubuntu-latest` toolchain (Python, Node, Java, Docker CLI, corepack, etc.).
   - [x] Add `Makefile` targets (`fast`, `ci`) to build the runner image and execute `tools/ci/run-all.sh` inside it with the correct volume mounts and docker socket sharing.
3. **Ship parity helpers**
   - [x] Add `docker/docker-compose.ci.yml` describing required integration services (e.g., Postgres/Redis) with health checks.
   - [x] Add `tools/ci/matrix-local.sh` to iterate through Node/Java/Python combinations using the runner container and allow developers to flip `RUN_INTEGRATION` as needed.
   - [x] Provide a pre-push hook template (e.g., `tools/git-hooks/pre-push`) plus documentation on symlinking it to `.git/hooks/pre-push` so `tools/ci/run-all.sh` runs before `git push`.
   - [x] Document `.env.ci.local` / dry-run conventions for secrets, caching, artifacts, and publish steps.
4. **Documentation + validation**
   - [x] Update project docs/README with instructions for running `make fast`, `make ci`, runner container usage, and troubleshooting tips.
   - [x] Ensure `openspec validate --strict` passes and capture evidence (screenshots/logs) showing the runner script used both locally and in CI.
