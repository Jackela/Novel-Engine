# Codex: Testing Strategy (TESTING.md)
*Document Version: 1.2*
*Last Updated: 2025-08-11*

This document defines the testing strategy and quality assurance processes for the Novel Engine.

## 1. The Liturgy of Test-Driven Sanctification (TDD)

All new functional code must be developed following a strict Test-Driven Development (TDD) workflow.
1.  **Write the Test First:** Before writing any implementation code, a failing test case must be written in the appropriate test suite. This test must clearly define the expected behavior of the new feature.
2.  **Write Code to Pass the Test:** Write the minimum amount of implementation code required to make the failing test pass.
3.  **Refactor:** Improve the implementation code's structure and clarity while ensuring all tests continue to pass.

All Pull Requests introducing new logic must include corresponding tests. A PR will not be merged if its tests fail or if it reduces overall test coverage.

## 2. Testing Layers

Our testing strategy is composed of multiple layers to ensure quality at every level of the system.

-   **Level 1: Unit Tests (`/tests/unit`)**
    -   **Scope:** Test individual functions and classes in isolation.
    -   **Examples:** Schema validation (`test_schemas.py`), utility functions, rule logic in the Adjudicator.
    -   **Mocks:** External dependencies (like the LLMClient or file system) are always mocked.

-   **Level 2: Service Tests (`/tests/service`)**
    -   **Scope:** Test the integrated behavior of a single service or major component (e.g., `DirectorAgent`, `ChroniclerAgent`).
    -   **Examples:** Testing the full turn execution sequence within the `DirectorAgent`, testing the narrative generation of the `ChroniclerAgent` from a sample log.
    -   **Mocks:** May use a `MockLLM` or `RecordedLLM`.

-   **Level 3: API Tests (`/tests/api`)**
    -   **Scope:** Test the FastAPI endpoints.
    -   **Examples:** Sending valid/invalid payloads to API endpoints and asserting the HTTP response code and body.
    -   **Tools:** `pytest-httpx`.

-   **Level 4: Integration Tests (`/evaluation`)**
    -   **Scope:** Test the end-to-end behavior of the entire system using seed scenarios.
    -   **Examples:** Running `evaluate_baseline.py`.
    -   **Mocks:** Uses a `RecordedLLM` or a real LLM with a cached key to ensure reproducibility.

-   **Level 5: Replay Tests**
    -   **Scope:** Validates that a recorded session can be replayed identically.
    -   **Process:** Takes a run log as input and re-executes it, asserting that the state after each turn matches the logged state.

## 3. Test Coverage

-   **Target:** A minimum of **85% statement coverage** is required for all new code.
-   **Tool:** `pytest-cov`.
-   **Exclusions:** The `__main__` block in scripts and auto-generated Pydantic methods may be excluded from coverage reports.

## 4. Test Fixtures & Mocking

-   **Location:** Reusable test fixtures are defined in `tests/conftest.py`.
-   **Core Fixtures:**
    -   `fixture_mock_llm`: Returns a `MockLLM` instance that provides fixed, predictable outputs.
    -   `fixture_recorded_llm`: Returns a `RecordedLLM` that replays responses from a "golden" recording.
    -   `fixture_world_min`: Provides a minimal, valid `WorldState` object.
    -   `fixture_persona_min`: Provides a minimal, valid `PersonaCardV2` object.
    -   `fixture_registry_neutral`: Provides a minimal, valid `CanonRegistry` object.

## 5. Stability and Reproducibility

-   **Random Seeds:** All tests involving randomness must use a fixed seed to ensure deterministic outcomes.
-   **Time:** Functions dependent on the current time must be mocked (e.g., using `freezegun`).
-   **Network:** API and integration tests must not make live network calls, except when explicitly testing against a staging environment. They should use the `RecordedLLM` or mock servers.

## 6. Continuous Integration (CI) Pipeline

The CI pipeline, defined in `.github/workflows/ci.yml`, is the ultimate gatekeeper of quality. A PR must pass all CI steps to be eligible for merging.

**CI Sequence:**
1.  **Linting:** Run `ruff` and `black` to enforce code style.
2.  **Term Guard:** Run `scripts/term_guard.py` to check for forbidden IP terms.
3.  **Unit & Service Tests:** Run `pytest -q tests/unit tests/service`.
4.  **API Tests:** Run `pytest -q tests/api`.
5.  **Build & Integration Test:** Run `scripts/build_kb.py` in `neutral` mode, then run `evaluate_baseline.py` on a small, dedicated CI seed scenario.
6.  **Coverage Report:** Generate and upload the test coverage report.
