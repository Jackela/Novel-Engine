## Quickstart — Project Best-Practice Refactor

1. **Check Out Feature Branch**
   ```bash
   git checkout 001-best-practice-refactor
   ```

2. **Review Constitution & ADR Blueprint**
   - Read `.specify/memory/constitution.md` to internalize the five governing principles.
   - Open `specs/001-best-practice-refactor/data-model.md` and planned ADR references (ARC-001) for bounded contexts, aggregates, and ports.

3. **Synchronize Tooling**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   npm install --prefix frontend
   ```
   - Ensure Pact/Dredd, Playwright, and k6 CLIs are available (see `README.md` for platform-specific setup).

4. **Apply Contract Updates**
   - Inspect `specs/001-best-practice-refactor/contracts/openapi-refactor.yaml`.
   - Run contract linting (placeholder command to be wired during implementation):
     ```bash
     ./scripts/contracts/lint.sh specs/001-best-practice-refactor/contracts/openapi-refactor.yaml
     ```

5. **Run Observability & QA Baselines**
   - Execute existing pytest suite and note coverage deltas:
     ```bash
     pytest --cov=src
     ```
   - Trigger Playwright smoke tests from `frontend/`:
     ```bash
     npm run --prefix frontend test:e2e
     ```
   - Collect current metrics dashboards/alerts for comparison once refactor changes land.

6. **Plan Implementation Tasks**
   - After validating this plan, run `/speckit.tasks` to generate story-aligned tasks.
   - Create ADRs and runbook updates referenced in the specification before modifying runtime code.

7. **Communicate with Stakeholders**
   - Share research findings (research.md) with architecture, QA, and operations leads.
   - Schedule review sessions for contract alignment and observability charter approval.
