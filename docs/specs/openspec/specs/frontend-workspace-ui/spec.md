# Frontend Workspace UI

## Purpose
Define baseline usability expectations for guest and workspace flows in the UI.

## Requirements

### Guest-first entry is usable
The frontend MUST allow a visitor to enter the product as a guest and reach a functional dashboard without requiring credentials.

#### Scenario: Guest enters from landing page
- **GIVEN** a visitor starts at `/` without an existing session
- **WHEN** they choose “Continue as guest”
- **THEN** the app establishes a guest session (or resumes one) and navigates to a usable dashboard view.

### Character management uses real API
The frontend MUST provide character list + create/edit/delete flows backed by the character service API, with consistent loading/empty/error states.

#### Scenario: Create character from UI persists
- **GIVEN** the user is on the dashboard as a guest
- **WHEN** they create a character via the UI
- **THEN** the frontend POSTs to `/api/characters`, shows the created character in the list, and it remains visible after refresh.

### Usable story/run flow
The frontend MUST allow starting a simulation/story run and rendering the resulting narrative, including error handling and retry.

#### Scenario: User starts a run and sees output
- **GIVEN** at least one character exists in the workspace
- **WHEN** the user starts a run from the UI
- **THEN** the UI shows progress/loading feedback and then renders the resulting narrative output on success.

### API errors are consistently handled
API failures MUST be rendered using a consistent error pattern with actionable messaging (retry, offline indicator, or next steps).

#### Scenario: Backend is unavailable
- **WHEN** the backend API cannot be reached
- **THEN** the UI shows a clear error state (not demo/sample data) and provides a retry action and troubleshooting hint.
