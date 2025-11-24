## MODIFIED Requirements

### Requirement: Performance metrics widget visibility control
PerformanceMetrics component MUST only be visible to users with 'developer' or 'admin' roles, enforced at the component level.

#### Scenario: Component renders for developers
- **GIVEN** a user is authenticated with roles array including 'developer'
- **WHEN** the PerformanceMetrics component renders
- **THEN** it displays the performance metrics UI with Web Vitals data (LCP, FID, CLS, FCP, TTFB) and shows a heading indicating developer-only content (e.g., "Performance Metrics (Dev)")

#### Scenario: Component renders for admins
- **GIVEN** a user is authenticated with roles array including 'admin'
- **WHEN** the PerformanceMetrics component renders
- **THEN** it displays the performance metrics UI with Web Vitals data and shows the same heading as for developers

#### Scenario: Component hidden for regular users
- **GIVEN** a user is authenticated with roles array containing only 'user' (no 'developer' or 'admin')
- **WHEN** the PerformanceMetrics component renders
- **THEN** it returns null, rendering nothing to the DOM, making the widget completely invisible

#### Scenario: Component hidden when not authenticated
- **GIVEN** no user is authenticated (user context is null or undefined)
- **WHEN** the PerformanceMetrics component renders
- **THEN** it returns null, rendering nothing to the DOM

#### Scenario: Component checks roles via authentication hook
- **GIVEN** the application provides a `useAuth()` hook returning user context
- **WHEN** the PerformanceMetrics component mounts
- **THEN** it calls `useAuth()` to retrieve the current user, checks if `user?.roles` includes 'developer' or 'admin', and conditionally renders based on this check

### Requirement: Web Vitals monitoring preservation
PerformanceMetrics component MUST continue displaying browser Web Vitals metrics, not backend system metrics.

#### Scenario: Component displays Web Vitals data
- **GIVEN** the `usePerformance` hook returns Web Vitals metrics (LCP, FID, CLS, FCP, TTFB)
- **WHEN** the PerformanceMetrics component renders for an authorized user
- **THEN** it displays these metrics with labels ("LCP", "FID", etc.), formatted values with units (e.g., "1234ms" for LCP), and does not display backend system metrics like memory usage or error rates

#### Scenario: Component does not fetch backend metrics
- **GIVEN** the PerformanceMetrics component is rendered
- **WHEN** it retrieves performance data via `usePerformance` hook
- **THEN** the hook uses browser Performance API or Web Vitals library, does not make HTTP requests to backend `/api/metrics` endpoints, and focuses solely on client-side performance monitoring

## ADDED Requirements

### Requirement: Hardcoded demo metrics removal
PerformanceMetrics component MUST NOT display hardcoded demo data (responseTime, errorRate, requestsPerSecond, activeUsers, systemLoad, memoryUsage, storageUsage, networkLatency).

#### Scenario: Component displays only Web Vitals
- **GIVEN** the PerformanceMetrics component is rendered for an authorized user
- **WHEN** the component UI is inspected
- **THEN** it displays exactly 5 Web Vitals metrics (LCP, FID, CLS, FCP, TTFB), does not show hardcoded demo metrics (responseTime, errorRate, etc.), and does not include interval-based simulation logic

#### Scenario: No demo data state in component
- **GIVEN** the PerformanceMetrics component source code is reviewed
- **WHEN** searching for state initialization or demo data
- **THEN** no hardcoded metric values (e.g., `responseTime: 245`, `errorRate: 0.02`) are found, no `setInterval` calls for metric simulation exist, and all displayed data comes from the `usePerformance` hook

### Requirement: Authentication system integration
Frontend MUST provide authentication context with user roles for RBAC checks.

#### Scenario: useAuth hook provides user context
- **GIVEN** the frontend has an authentication system
- **WHEN** a component calls `useAuth()`
- **THEN** the hook returns an object containing `user` property (or null if not authenticated), where `user` includes a `roles` array of strings (e.g., `['developer', 'admin', 'user']`)

#### Scenario: Authentication context is available application-wide
- **GIVEN** the React application is initialized
- **WHEN** any component in the tree needs authentication state
- **THEN** the component can access `useAuth()` hook via context provider (e.g., `<AuthProvider>` wrapping the app)

### Requirement: Fallback for missing authentication
If authentication system is not implemented, PerformanceMetrics visibility MUST be controlled via environment variable.

#### Scenario: Environment variable controls visibility when auth unavailable
- **GIVEN** the `useAuth` hook is not available or authentication system is not implemented
- **WHEN** the PerformanceMetrics component renders
- **THEN** it checks `import.meta.env.VITE_SHOW_PERFORMANCE_METRICS` (default: false), renders the widget if the variable is explicitly set to `'true'` or `true`, and returns null otherwise

#### Scenario: Environment variable only enables in development
- **GIVEN** `VITE_SHOW_PERFORMANCE_METRICS` is used as a fallback control
- **WHEN** the application is built for production
- **THEN** the variable defaults to false unless explicitly overridden, ensuring the widget is hidden in production builds by default

### Requirement: Testing support for RBAC
PerformanceMetrics tests MUST verify role-based visibility logic comprehensively.

#### Scenario: Test suite verifies developer role access
- **GIVEN** a test renders PerformanceMetrics with mocked `useAuth` returning `{user: {roles: ['developer']}}`
- **WHEN** the test checks the DOM
- **THEN** it asserts the component text "Performance Metrics" is present in the document

#### Scenario: Test suite verifies admin role access
- **GIVEN** a test renders PerformanceMetrics with mocked `useAuth` returning `{user: {roles: ['admin']}}`
- **WHEN** the test checks the DOM
- **THEN** it asserts the component text "Performance Metrics" is present in the document

#### Scenario: Test suite verifies regular user denied access
- **GIVEN** a test renders PerformanceMetrics with mocked `useAuth` returning `{user: {roles: ['user']}}`
- **WHEN** the test checks the DOM
- **THEN** it asserts the component text "Performance Metrics" is NOT present in the document

#### Scenario: Test suite verifies unauthenticated user denied access
- **GIVEN** a test renders PerformanceMetrics with mocked `useAuth` returning `{user: null}`
- **WHEN** the test checks the DOM
- **THEN** it asserts the component text "Performance Metrics" is NOT present in the document
