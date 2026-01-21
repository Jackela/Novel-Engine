# E2E User Flows

## Purpose
Capture end-to-end user journeys that must remain stable across releases.

## Requirements

### Landing to Dashboard Flow
The application MUST support a seamless onboarding flow from the landing page to the dashboard.

#### Scenario: Launching the engine
- **GIVEN** a user is on the landing page
- **WHEN** they click the "Launch Engine" button
- **THEN** they are automatically entered into guest mode and redirected to the dashboard

### Persistent Sessions
User sessions and workspace data MUST persist across page refreshes.

#### Scenario: Refresh survival
- **GIVEN** a guest user has an active workspace
- **WHEN** they refresh the browser page
- **THEN** the application resumes the existing session using localStorage data and restores the workspace state
