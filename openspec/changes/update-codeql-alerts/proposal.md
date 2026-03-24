# Change: Update CodeQL Alert Remediation and Quality Gates

## Why
CodeQL currently reports a large backlog of open alerts, including security-relevant findings and quality debt that obscures real risk. We need to resolve the backlog and define a sustainable guardrail that keeps the default branch clean.

## What Changes
- Triage and resolve all open CodeQL alerts across backend, frontend, and tests.
- Prioritize security findings and enforce safe cookie handling patterns.
- Add a quality gate requirement that CodeQL on the default branch is clean or has documented suppressions.
- Update CodeQL configuration and suppressions for justified test/fixture findings.

## Impact
- Affected specs: tdd-workflow
- Affected code: src/, frontend/, tests/, .github/workflows/codeql.yml, CodeQL config files
