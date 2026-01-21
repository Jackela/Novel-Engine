# test-pyramid-compliance Specification

## Purpose
Define the expected pyramid marker discipline (unit/integration/e2e) and the supporting tooling to keep the suite classified and measurable.
## Requirements
### Requirement: Test Pyramid Marker Compliance
All test functions in the repository MUST have exactly one pyramid marker (`@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.e2e`) applied at either the function level or inherited from a class-level decorator.

#### Scenario: Unit test in tests/unit/ directory
- **GIVEN** a test file located in `tests/unit/`
- **WHEN** the test pyramid validator runs
- **THEN** all test functions in that file SHALL have `@pytest.mark.unit` applied

#### Scenario: Integration test identified by filename
- **GIVEN** a test file with `_integration` or `_comprehensive` in its filename
- **WHEN** the test pyramid validator runs
- **THEN** all test functions in that file SHALL have `@pytest.mark.integration` applied

#### Scenario: Tests in tests/api/ directory
- **GIVEN** a test file located in `tests/api/`
- **WHEN** the test pyramid validator runs
- **THEN** all test functions in that file SHALL have `@pytest.mark.integration` applied

#### Scenario: Validation failure blocks CI
- **GIVEN** any test function without a pyramid marker
- **WHEN** CI runs `validate-test-markers.py --all`
- **THEN** the script SHALL exit with non-zero status and report the unmarked tests

### Requirement: Bulk Pyramid Marker Tooling
The repository MUST provide a script (`scripts/testing/add-pyramid-markers.py`) that automatically adds pyramid markers to uncategorized tests based on file location and naming conventions.

#### Scenario: Dry-run mode previews changes
- **GIVEN** the `--dry-run` flag is passed to `add-pyramid-markers.py`
- **WHEN** the script executes
- **THEN** it SHALL print proposed marker additions without modifying any files

#### Scenario: Class-level marker addition
- **GIVEN** a test class where all methods need the same pyramid marker
- **WHEN** the script runs without `--dry-run`
- **THEN** it SHALL add the marker at the class level to reduce redundancy

#### Scenario: Respects existing markers
- **GIVEN** a test function or class that already has a pyramid marker
- **WHEN** the script runs
- **THEN** it SHALL NOT add duplicate markers
