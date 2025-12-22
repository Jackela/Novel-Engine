# Tasks: Refactor Backend API Platform

## 1. Baseline and contracts
- [ ] Identify the canonical “product API” endpoints and add/confirm integration tests for them (status codes + payload shape).
- [ ] Freeze the current OpenAPI output as a reference artifact for later diffing.

## 2. Introduce a canonical app factory
- [ ] Add `create_app()` that wires routers, middleware, exception handling, and config.
- [ ] Ensure importing the app factory has no side effects (no server start, no filesystem writes).

## 3. Establish module boundaries
- [ ] Move one domain at a time into `routers/*` + `services/*` while keeping routes stable.
- [ ] Introduce dependency providers for services and stores (DI-friendly).

## 4. Standardize errors and response models
- [ ] Create a consistent error envelope and convert product routes to use it.
- [ ] Ensure validation errors are also normalized.

## 5. Validation gates
- [ ] Run full backend tests, frontend tests, and CI-parity scripts.
- [ ] Run `openspec validate refactor-backend-api-platform --strict`.
