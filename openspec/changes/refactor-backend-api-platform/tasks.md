# Tasks: Refactor Backend API Platform

## 1. Baseline and contracts
- [x] Identify the canonical “product API” endpoints and add/confirm integration tests for them (status codes + payload shape).
- [x] Freeze the current OpenAPI output as a reference artifact for later diffing.

## 2. Introduce a canonical app factory
- [x] Add `create_app()` that wires routers, middleware, exception handling, and config.
- [x] Ensure importing the app factory has no side effects (no server start, no filesystem writes).

## 3. Establish module boundaries
- [x] Move one domain at a time into `routers/*` + `services/*` while keeping routes stable.
- [x] Introduce dependency providers for services and stores (DI-friendly).

## 4. Standardize errors and response models
- [x] Create a consistent error envelope and convert product routes to use it.
- [x] Ensure validation errors are also normalized.

## 5. Validation gates
- [x] Run full backend tests, frontend tests, and CI-parity scripts.
- [x] Run `openspec validate refactor-backend-api-platform --strict`.
