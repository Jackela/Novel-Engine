## Overview
To streamline debugging and support AI-driven usability tests, this change introduces a unified dev bootstrap script, aligns dependency metadata, and adds a curated Playwright flow dedicated to AI agents.

## Key Decisions
1. **Python Version Alignment**
   - Set `requires-python = ">=3.11"` to match FastAPI + dependency baselines already assumed in docs/CI.
2. **Makefile Fix**
   - Point `make install/upgrade` to `requirements/requirements-test.txt` so the helper works without manual pip commands.
3. **Dev Environment Script**
   - `scripts/dev_env.sh` is a portable Bash helper that:
     - Ensures commands run from repo root.
     - Starts FastAPI (`src.api.main_api_server:app`) via `uvicorn`.
     - Launches the Vite dev server.
     - Streams logs/stdout and terminates both processes when the user exits.
4. **AI Playwright Flow**
   - New spec (`frontend/tests/e2e/ai-usability.spec.ts`) stubs backend endpoints (health) allowing deterministic runs under `npm run ai:test`.
   - Scripted command captures trace/video artifacts by enabling Playwright tracing.
5. **Spec Update**
   - Extend `process-management` capability with requirements for a guided dev bootstrap helper and AI usability command so expectations remain auditable.
