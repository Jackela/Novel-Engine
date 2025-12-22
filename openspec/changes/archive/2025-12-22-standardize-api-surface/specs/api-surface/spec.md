## ADDED Requirements

### Requirement: Canonical product API prefix
The system MUST expose the product API under the canonical prefix `/api/*`.

#### Scenario: Client calls canonical endpoint
- **WHEN** a client sends a request to a product endpoint under `/api/*` (e.g., `GET /api/characters`)
- **THEN** the server responds using the canonical contract for that endpoint and includes stable error handling and response shapes.

### Requirement: No path-based API versioning for product endpoints
The product API MUST NOT be served under versioned path prefixes such as `/api/v1/*` or `/api/v2/*`.

#### Scenario: Versioned path is not available
- **GIVEN** a product endpoint exists under `/api/*`
- **WHEN** a client calls the equivalent versioned path (e.g., `GET /api/v1/characters`)
- **THEN** the server responds with 404 (or an explicitly documented deprecation response) and does not serve product behavior under the versioned path.

### Requirement: API discovery output is accurate
Any endpoint map, discovery document, or “available endpoints” output MUST only list routes that are actually served by the running application.

#### Scenario: Endpoint map contains no stale routes
- **WHEN** a client reads the API’s published endpoint map (if present)
- **THEN** every listed route can be called and returns a non-404 response when invoked with valid inputs.
