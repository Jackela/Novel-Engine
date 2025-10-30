# QA Tooling Contracts

## Local Validation Script
- Entry point: `scripts/validate_ci_locally.sh`
- Expected arguments: none (optional `PY_BIN`, `VENV_DIR` env variables)
- Output requirements:
  - Exit code 0 on success, >0 on failure.
  - Log start/end of formatting, linting, pytest phases.
  - Produce HTML coverage report and junit XML in repo root.

## GitHub Actions QA Workflow
- File: `.github/workflows/quality_assurance.yml`
- Jobs Updated:
  - `code-quality`: call shared formatting script, enforce 25 min timeout.
  - `test-suite`: run pytest (non service tests), reuse caching strategy.
- Artifacts: upload lint reports, junit XML, HTML coverage.
