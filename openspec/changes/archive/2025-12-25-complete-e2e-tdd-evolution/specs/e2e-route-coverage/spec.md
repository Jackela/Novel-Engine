# E2E Route Coverage

## Overview
E2E tests covering all application routes to ensure navigation and rendering work correctly.

## ADDED Requirements

### Requirement: Landing Page E2E Coverage
E2E tests MUST verify the landing page loads and functions correctly.

#### Scenario: Landing page renders with expected content
- **Given**: The application is running
- **When**: User navigates to `/`
- **Then**: The page title "NARRATIVE ENGINE" is visible
- **And**: The "Launch Engine" button is present
- **And**: Three feature cards are displayed

#### Scenario: Landing page navigation works
- **Given**: User is on the landing page
- **When**: User clicks "Launch Engine" button
- **Then**: User is navigated to `/dashboard`

#### Scenario: Landing page is responsive
- **Given**: The application is running
- **When**: Viewport is set to mobile size (375x667)
- **Then**: Content stacks vertically
- **And**: Button remains clickable

### Requirement: Protected Route E2E Coverage
E2E tests MUST verify protected routes redirect unauthenticated users.

#### Scenario: Unauthenticated access redirects
- **Given**: User is not authenticated
- **When**: User navigates directly to `/dashboard`
- **Then**: User is redirected to `/`
- **And**: Landing page is displayed

#### Scenario: Authenticated access succeeds
- **Given**: User is authenticated (via guest mode or login)
- **When**: User navigates to `/dashboard`
- **Then**: Dashboard is displayed
- **And**: No redirect occurs

### Requirement: Login Page E2E Coverage
E2E tests MUST verify the login page placeholder renders.

#### Scenario: Login placeholder renders
- **Given**: The application is running
- **When**: User navigates to `/login`
- **Then**: Login placeholder message is displayed

### Requirement: Wildcard Route E2E Coverage
E2E tests MUST verify unknown routes redirect to landing.

#### Scenario: Unknown routes redirect to landing
- **Given**: The application is running
- **When**: User navigates to `/unknown-route`
- **Then**: User is redirected to `/`
- **And**: Landing page is displayed

#### Scenario: Deep unknown paths redirect
- **Given**: The application is running
- **When**: User navigates to `/some/deep/unknown/path`
- **Then**: User is redirected to `/`
