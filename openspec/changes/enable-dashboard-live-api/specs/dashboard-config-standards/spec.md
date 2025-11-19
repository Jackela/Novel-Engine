## ADDED Requirements

### Requirement: Standardized dashboard environment variables
All dashboard-specific environment variables MUST use the `VITE_DASHBOARD_*` prefix with comprehensive `.env.example` documentation.

#### Scenario: Events endpoint is configurable via environment variable
- **GIVEN** the frontend is built or run in development mode
- **WHEN** the `VITE_DASHBOARD_EVENTS_ENDPOINT` environment variable is set (e.g., `/api/v1/events/stream`)
- **THEN** the `useRealtimeEvents` hook uses this value as the SSE endpoint, and falls back to `/api/v1/events/stream` if the variable is undefined

#### Scenario: Characters endpoint follows canonical pattern
- **GIVEN** the dashboard needs to fetch character data
- **WHEN** the `VITE_DASHBOARD_CHARACTERS_ENDPOINT` environment variable is set (e.g., `/api/v1/characters`)
- **THEN** the data fetching hook uses this value, defaulting to `/api/v1/characters` per dashboard-data-routing-hygiene spec

#### Scenario: API base URL is configurable
- **GIVEN** the frontend needs to resolve absolute API URLs
- **WHEN** the `VITE_API_BASE_URL` environment variable is set (e.g., `http://localhost:8000`)
- **THEN** all API requests use this base URL for absolute path resolution, defaulting to `http://localhost:8000` in development

#### Scenario: Debug mode is controllable via environment variable
- **GIVEN** developers need verbose logging for dashboard components
- **WHEN** the `VITE_DASHBOARD_DEBUG` environment variable is set to `true`
- **THEN** dashboard components log connection states, event arrivals, and data fetching activity to the console

#### Scenario: Environment variables are documented in .env.example
- **GIVEN** a developer clones the repository and needs to configure the frontend
- **WHEN** they open `.env.example`
- **THEN** they find a "Dashboard Configuration" section with all `VITE_DASHBOARD_*` variables, descriptions of each variable's purpose, default values, and example values

## MODIFIED Requirements

### Requirement: Legacy environment variable prefix removal
All references to `REACT_APP_*` environment variables MUST be removed and migrated to `VITE_*` equivalents.

#### Scenario: No REACT_APP_ imports in codebase
- **GIVEN** the frontend codebase is searched for environment variable usage
- **WHEN** a search is performed for `process.env.REACT_APP_` or `REACT_APP_`
- **THEN** zero matches are found in source files (excluding comments/documentation noting the migration)

#### Scenario: Vite-compatible imports are used
- **GIVEN** a frontend component or hook needs to access an environment variable
- **WHEN** the code imports the variable
- **THEN** it uses `import.meta.env.VITE_*` syntax, which is the Vite-standard approach, not `process.env.*`

## ADDED Requirements

### Requirement: Vite proxy configuration for SSE
Vite dev server proxy MUST support SSE-specific headers and streaming for `/api/v1/events/stream` endpoint.

#### Scenario: Proxy forwards SSE headers correctly
- **GIVEN** a client requests `/api/v1/events/stream` through the Vite dev server
- **WHEN** the proxy forwards the request to the backend
- **THEN** the proxy sets `Accept: text/event-stream`, `Cache-Control: no-cache`, and `Connection: keep-alive` headers on the proxied request

#### Scenario: Proxy preserves streaming response
- **GIVEN** the backend responds with `Content-Type: text/event-stream` and begins streaming
- **WHEN** the Vite proxy receives the streaming response
- **THEN** the proxy does not buffer the response, streams events to the client in real-time, and maintains the connection until the client or server closes it

#### Scenario: Proxy maps /api/v1/* to backend
- **GIVEN** the Vite dev server is configured with proxy rules
- **WHEN** a request is made to `/api/v1/characters`, `/api/v1/events/stream`, or any `/api/v1/*` path
- **THEN** the proxy forwards the request to the backend at `VITE_API_BASE_URL` (default: `http://localhost:8000`), preserving the `/api/v1/*` path structure

#### Scenario: Proxy handles backend unavailability
- **GIVEN** the backend server at `VITE_API_BASE_URL` is not running
- **WHEN** a client makes a request through the Vite proxy
- **THEN** the proxy returns a 502 Bad Gateway or appropriate error response, logs the connection failure, and allows the frontend to display error states

### Requirement: Configuration file organization
Environment configuration files MUST be organized with clear sections and comments for maintainability.

#### Scenario: .env.example has dashboard section
- **GIVEN** `.env.example` contains multiple environment variable categories
- **WHEN** the file is viewed
- **THEN** it includes a clearly marked "Dashboard Configuration" section (with comment header like `# ========================================`), grouping all `VITE_DASHBOARD_*` variables together

#### Scenario: Each variable has inline documentation
- **GIVEN** a developer reads `.env.example`
- **WHEN** they encounter a `VITE_DASHBOARD_*` variable
- **THEN** they see an inline comment above or beside the variable explaining its purpose, default value, and any important constraints (e.g., "# Real-time events SSE endpoint (relative to VITE_API_BASE_URL or absolute)")

#### Scenario: Example values are provided
- **GIVEN** `.env.example` documents dashboard variables
- **WHEN** a developer copies the file to `.env.local`
- **THEN** they can use the example values as-is for local development (e.g., `VITE_API_BASE_URL=http://localhost:8000`), requiring minimal or no changes to get started
