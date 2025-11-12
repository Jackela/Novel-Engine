# Implementation Plan: QA Pipeline Hardening

**Branch**: `003-qa-hardening` | **Date**: 2025-10-29 | **Spec**: [specs/003-qa-hardening/spec.md](../003-qa-hardening/spec.md)
**Input**: Feature specification from `/specs/003-qa-hardening/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Stabilize the QA pipeline by enforcing repository-wide formatting/linting policies, fixing the failing turn orchestration integration test, and aligning local tooling (validate script, `act`) so code-quality and test-suite jobs pass consistently.

## Technical Context

**Language/Version**: Python 3.11+ (formatters/pytest), Bash (automation scripts), GitHub Actions YAML; incidental TypeScript tooling unaffected  
**Primary Dependencies**: Black, isort, Flake8, MyPy, Pytest, Playwright, act CLI, Docker runtime  
**Storage**: N/A (documentation + scripts only; no new persistence)  
**Testing**: Pytest (`-m "not requires_services"`), Black/isort checkers, Playwright smoke (existing tests), act workflow emulation  
**Target Platform**: Linux development hosts and GitHub Actions runners  
**Project Type**: QA/tooling hardening (no runtime features)  
**Performance Goals**: QA workflows complete under 20 minutes; local script finishes <10 minutes on clean env  
**Constraints**: Must comply with constitution QA mandates, avoid modifying production data, and document environment prerequisites  
**Scale/Scope**: Affects entire repository formatting + regression suite; team-wide developer workflow impact

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Domain-Driven Narrative Core**: Context focus is Platform Operations; no domain aggregate changes—document that formatting/test adjustments do not violate bounded context boundaries.  
- **Contract-First Experience APIs**: No new APIs; ensure any tooling endpoints/scripts reference existing contracts only.  
- **Data Stewardship & Persistence Discipline**: No schema changes; note that test data mutations remain local-only and cleanup documented.  
- **Quality Engineering & Testing Discipline**: Central goal—define formatter/test coverage gates, tooling scripts, and QA workflow steps; must document coverage expectations and failing test fixes.  
- **Operability, Security & Reliability**: Update documentation/runbooks so QA tooling (validate script, act) includes observability logs (stdout), security considerations (no privileged installs), and resilience (retry guidance).

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
repo-root/
├── scripts/validate_ci_locally.sh       # QA tooling (to be enhanced)
├── scripts/contracts/run-tests.sh       # Used by QA pipeline
├── src/                                 # Application code (formatting target)
├── tests/                               # Test suite (formatting + regression fixes)
├── ai_testing/                          # Additional QA scripts/tests (formatting target)
├── .github/workflows/quality_assurance.yml
└── docs/                                # Updated with QA guidance
```

**Structure Decision**: Focus on QA tooling (`scripts/`), CI workflows (`.github/workflows/quality_assurance.yml`), and repository-wide formatting across `src/`, `tests/`, `ai_testing/`, plus documentation under `docs/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
