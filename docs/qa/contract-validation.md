# Contract Validation Playbook

## Goal

Ensure StoryForge experience APIs comply with the contract-first mandate and
pass automated linting/tests before deployment.

## Pre-checks

- [ ] OpenAPI spec updated (`specs/001-best-practice-refactor/contracts/openapi-refactor.yaml`)
- [ ] Security controls charter reviewed (`docs/governance/security-controls.md`)
- [ ] Data protection commitments reviewed (`docs/governance/data-protection.md`)

## Lint & Tests

1. **OpenAPI Lint**
   ```bash
   scripts/contracts/run-tests.sh
   ```
   - Expect zero errors/warnings. Fix issues before proceeding.

2. **Contract Tests (future automation)**
   ```bash
   # Placeholder for Pact/Dredd suites
   ./scripts/contracts/run-tests.sh specs/...  # extend with consumer tests
   ```

3. **CI Integration**
   - Ensure GitHub Actions step `contract-validation` invokes the script.
   - Upload lint output as build artifact for auditing.

## Sign-off

- [ ] Lint results attached to PR.
- [ ] Breaking changes communicated to frontend/automation teams.
- [ ] Constitution gate workbook updated with run date.

> Record outcomes in `docs/governance/constitution-checks.md` as part of each refactor cycle.
