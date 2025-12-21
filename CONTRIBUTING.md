# Contributing

Thanks for helping improve Novel Engine.

## Prerequisites

- Python 3.11+
- Node.js 18+ (Node 20 recommended)
- npm

## Setup

- Backend:
  - `python -m venv .venv`
  - Activate venv:
    - Windows: `.\.venv\Scripts\activate`
    - macOS/Linux: `source .venv/bin/activate`
  - `pip install -U pip`
  - `pip install -r requirements.txt -r requirements/requirements-test.txt`

- Frontend:
  - `cd frontend`
  - `npm ci`

## Quality Gates (Required)

- Backend CI parity:
  - macOS/Linux: `bash scripts/validate_ci_locally.sh`
  - Windows: `powershell -ExecutionPolicy Bypass -File scripts/validate_ci_locally.ps1`

- Frontend gates:
  - `cd frontend`
  - `npm run lint:all`
  - `npm run type-check`
  - `npm test`
  - `npm run build`
  - `npm run test:e2e:smoke`

## Guidelines

- Keep PRs focused and avoid unrelated refactors.
- Do not commit generated artifacts (e.g., `dist/`, `node_modules/`, `playwright-report/`, screenshots, logs).
- Update docs only when they reflect the curated structure and current behavior.
