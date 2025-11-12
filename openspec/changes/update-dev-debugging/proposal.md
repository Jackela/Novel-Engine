## Why
- Local debugging currently requires manually installing Python + Node deps, running multiple commands, and remembering which FastAPI entrypoint to launch, slowing iteration.
- `pyproject.toml` still claims compatibility with Python 3.8 even though docs and dependencies target Python 3.11+, causing confusing install errors.
- `Makefile`'s `install`/`upgrade` targets point to a non-existent `requirements-test.txt`, so onboarding and CI bootstrap fail without custom commands.
- There is no single `ai:test` workflow for Playwright to execute AI-native usability scenarios, making it harder to plug automated agents into the QA loop.

## What Changes
- Provide a `scripts/dev_env.sh` helper that verifies dependencies, spins up the FastAPI server via `src.api.main_api_server`, launches the Vite dev server, and tears everything down on exit to streamline debugging.
- Align tool metadata by setting `requires-python = ">=3.11"` in `pyproject.toml` and fixing the Makefile to install the correct `requirements/requirements-test.txt`.
- Add an AI-focused Playwright spec plus `npm run ai:test` wrapper so automated agents can run curated usability checks (gathering trace/video artifacts) in one command.
- Update the `process-management` capability to require a first-class dev bootstrap script and an AI validation command so expectations stay codified.

## Impact
- New contributors can run `make install`/`make upgrade` without path errors and know which Python version is supported.
- Debug sessions become faster because `scripts/dev_env.sh` orchestrates backend/frontend startup and handles cleanup automatically.
- QA agents (human or AI) gain a dedicated `npm run ai:test` hook that collects Playwright traces, enabling "AI native" usability checks on demand and in CI.
