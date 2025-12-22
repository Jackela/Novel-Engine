## ADDED Requirements

### Requirement: Canonical app factory
The backend MUST expose a canonical FastAPI app factory (`create_app()`) that can be imported by tests and production runners without triggering side effects.

#### Scenario: Tests can create an app instance
- **GIVEN** a test suite imports `create_app()`
- **WHEN** the suite constructs the app and issues requests via a test client
- **THEN** the app responds without requiring global initialization order or background side effects.

### Requirement: Routes are organized by domain routers
Product API endpoints MUST be implemented via domain routers (e.g., characters, sessions, simulations, events) registered by the canonical app factory.

#### Scenario: Adding a new endpoint is localized
- **GIVEN** a new product endpoint is added to the backend
- **WHEN** a developer implements it
- **THEN** they add it to a single domain router module and do not need to duplicate logic across multiple server entrypoints.

### Requirement: Standardized error envelope
All product API endpoints MUST return errors using a standardized, documented error envelope with stable error codes.

#### Scenario: Validation error is normalized
- **WHEN** a client sends an invalid payload to a product endpoint
- **THEN** the API returns a 4xx response whose body includes a stable error code and human-readable message suitable for display and logging.

### Requirement: OpenAPI output matches the canonical app
The OpenAPI schema used for documentation and client generation MUST be produced by the canonical app factory and reflect the real deployed routes.

#### Scenario: OpenAPI can be used for typed client generation
- **WHEN** the OpenAPI schema is exported from the running app
- **THEN** it includes accurate routes and request/response shapes for the product API, enabling a generated client to call the API without manual patching.

