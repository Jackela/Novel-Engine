## ADDED Requirements

### Requirement: Canonical product API prefix
The system MUST expose the product API under the canonical prefix `/api/*`.

#### Scenario: Client calls canonical endpoint
- **WHEN** a client sends a request to a product endpoint under `/api/*` (e.g., `GET /api/characters`)
- **THEN** the server responds using the canonical contract for that endpoint and includes stable error handling and response shapes.

### Requirement: Versioned v1 alias for the product API
The system MUST expose a versioned alias for the v1 product API under `/api/v1/*`, with behavior identical to `/api/*` for the v1 surface.

#### Scenario: Client calls versioned alias
- **GIVEN** a product endpoint exists under `/api/*`
- **WHEN** a client sends the same request to `/api/v1/*` (e.g., `GET /api/v1/characters`)
- **THEN** the response status, payload shape, and semantics match the canonical `/api/*` response for v1.

### Requirement: API discovery output is accurate
Any endpoint map, discovery document, or “available endpoints” output MUST only list routes that are actually served by the running application.

#### Scenario: Endpoint map contains no stale routes
- **WHEN** a client reads the API’s published endpoint map (if present)
- **THEN** every listed route can be called and returns a non-404 response when invoked with valid inputs.

