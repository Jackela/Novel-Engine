# Performance Metrics RBAC

## Purpose
Control access to performance metrics so sensitive telemetry is limited to trusted roles.

## Requirements

### Role-based visibility for PerformanceMetrics
The performance metrics widget MUST only be visible to users with 'developer' or 'admin' roles to prevent exposure of system internals to end users.

#### Scenario: Authorized user views metrics
- **GIVEN** an authenticated user has the 'developer' or 'admin' role
- **WHEN** they navigate to the dashboard
- **THEN** the Performance Metrics widget is rendered and displays real-time Web Vitals

#### Scenario: Unauthorized user cannot see metrics
- **GIVEN** an authenticated user has only the 'user' role
- **WHEN** they navigate to the dashboard
- **THEN** the Performance Metrics widget is not rendered (returns null)

#### Scenario: Guest user cannot see metrics
- **GIVEN** a user is not authenticated (guest mode)
- **WHEN** they navigate to the dashboard
- **THEN** the Performance Metrics widget is hidden

### Environment variable fallback for RBAC
If the authentication service is unavailable or roles cannot be determined, an environment variable MUST control widget visibility.

#### Scenario: Control via environment variable
- **GIVEN** the `useAuth` hook is unavailable or returns no user
- **WHEN** the `VITE_SHOW_PERFORMANCE_METRICS` environment variable is set to 'true'
- **THEN** the Performance Metrics widget is shown to all users

#### Scenario: Default hidden state
- **GIVEN** the `useAuth` hook is unavailable
- **WHEN** the `VITE_SHOW_PERFORMANCE_METRICS` environment variable is undefined or set to 'false'
- **THEN** the widget remains hidden by default

### Removal of simulated demo metrics
All hardcoded or simulated performance metrics MUST be removed in favor of real browser-based Web Vitals.

#### Scenario: Only Web Vitals are displayed
- **GIVEN** the Performance Metrics widget is rendered
- **WHEN** metrics are displayed
- **THEN** only LCP, FID, CLS, FCP, and TTFB from the browser Performance API are shown, with no simulated backend metrics like 'systemLoad' or 'activeUsers'
