# TDD Workflow & Quality Gates

## Purpose
Standardize local quality gates to keep changes test-driven and reviewable.

## Requirements

### Pre-commit hooks
All changes MUST be validated locally via pre-commit hooks before being pushed to the repository.

#### Scenario: Frontend linting
- **GIVEN** a developer attempts to commit changes to frontend files
- **WHEN** the pre-commit hook runs
- **THEN** it executes `npm run lint` within the `frontend` directory and fails the commit if lint errors are found

#### Scenario: Frontend type-checking
- **GIVEN** a developer attempts to commit changes to TypeScript files
- **WHEN** the pre-commit hook runs
- **THEN** it executes `npm run type-check` and blocks the commit on any type errors

### Coverage Enforcement
The test suite MUST maintain high code coverage to ensure narrative and system logic reliability.

#### Scenario: Vitest coverage thresholds
- **GIVEN** unit tests are executed via Vitest
- **WHEN** the coverage report is generated
- **THEN** it must meet a minimum threshold of 80% for lines, functions, branches, and statements, or the build fails

### SOLID Compliance Linting
Automated linting rules MUST enforce basic SOLID principles, specifically Single Responsibility.

#### Scenario: Function complexity
- **GIVEN** a TypeScript function or component is analyzed by ESLint
- **WHEN** the cyclomatic complexity exceeds 15
- **THEN** a warning is issued to encourage refactoring into smaller units

#### Scenario: Function length
- **GIVEN** a TypeScript function is analyzed
- **WHEN** the function exceeds 80 lines (excluding blanks and comments)
- **THEN** a warning is issued to maintain single responsibility
