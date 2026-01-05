## ADDED Requirements
### Requirement: Baseline security headers on product API responses
All product API responses MUST include baseline security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`).

#### Scenario: Success response includes headers
- **WHEN** a client calls any `/api/*` endpoint
- **THEN** the response includes `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY`.

#### Scenario: Error response includes headers
- **WHEN** a client receives a 4xx or 5xx from any `/api/*` endpoint
- **THEN** the response includes `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY`.

### Requirement: Auth credentials are not accepted via query parameters
Authentication endpoints MUST accept credentials via a request body and MUST reject credentials supplied via query parameters to prevent log leakage.

#### Scenario: Credentials provided in JSON body
- **WHEN** a client POSTs credentials in the JSON body
- **THEN** the server authenticates the request using the body fields.

#### Scenario: Credentials provided via query string
- **WHEN** a client sends `username` or `password` in the query string
- **THEN** the server rejects the request with a 400-level error.

### Requirement: CORS credentials require explicit origins
When `allow_credentials` is enabled, the server MUST use explicit allowed origins and MUST NOT use a wildcard (`*`).

#### Scenario: Credentials enabled with explicit origins
- **WHEN** the server is configured with `allow_credentials=true`
- **THEN** the CORS configuration lists explicit origins and does not include `*`.
