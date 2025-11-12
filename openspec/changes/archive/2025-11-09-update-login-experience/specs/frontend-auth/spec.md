## ADDED Requirements

### Requirement: Responsive Split Login Layout
The unauthenticated `/login` route MUST render as a two-column layout (hero panel + form panel) on medium-and-up breakpoints and collapse to a single column on small screens without hiding content.

#### Scenario: Desktop viewport
- **WHEN** the viewport width is ≥ 960px
- **THEN** the hero panel appears on the left with marketing copy and the form panel on the right, both vertically centered with equal padding.

#### Scenario: Mobile viewport
- **WHEN** the viewport width is < 960px
- **THEN** the hero panel stacks above the form panel, preserving heading hierarchy and ensuring the form remains fully visible without horizontal scrolling.

### Requirement: Inline Form Feedback and Utilities
The login form MUST provide immediate inline validation, a password visibility toggle, and a remember-me control so users understand input requirements before submitting.

#### Scenario: Missing username or password
- **WHEN** a user focuses and blurs an empty required field (or submits empty fields)
- **THEN** the field displays an accessible helper/error message explaining that credentials are required, and the submit button reflects disabled/loading states appropriately.

#### Scenario: Password visibility
- **WHEN** the user activates the password visibility toggle
- **THEN** the password input switches between masked and plain text modes while retaining screen-reader labels.

### Requirement: Contextual Support Messaging
The login page MUST communicate either demo credentials (when `demoMode` is enabled) or a support CTA so operators can guide users who are blocked from signing in.

#### Scenario: Demo mode enabled
- **WHEN** `appConfig.demoMode` is true
- **THEN** the UI shows a highlighted message describing demo behavior and indicates any default credentials or warnings.

#### Scenario: Demo mode disabled
- **WHEN** `appConfig.demoMode` is false
- **THEN** the UI shows a “Need access?” support link (mailto or docs) near the form and optional status chip so users know how to request credentials.
