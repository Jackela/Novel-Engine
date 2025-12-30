# E2E User Flows

## Overview
E2E tests covering complete user journeys through the application.

## ADDED Requirements

### Requirement: Complete User Journey Coverage
E2E tests MUST verify the full user journey from landing to dashboard interaction.

#### Scenario: New user journey
- **Given**: User is not authenticated
- **When**: User visits the application
- **Then**: Landing page is displayed
- **When**: User clicks "Launch Engine"
- **Then**: User is authenticated (guest mode)
- **And**: Dashboard is displayed
- **And**: Character list is visible
- **And**: Activity stream shows connection status

#### Scenario: Returning user journey
- **Given**: User has previously authenticated
- **When**: User returns to the application
- **Then**: Previous auth state is restored
- **And**: User can navigate directly to dashboard

### Requirement: Navigation Flow Coverage
E2E tests MUST verify browser navigation works correctly.

#### Scenario: Back navigation works
- **Given**: User is on dashboard
- **When**: User clicks browser back button
- **Then**: User is navigated to previous page
- **And**: Page state is preserved

#### Scenario: Forward navigation works
- **Given**: User clicked back from dashboard
- **When**: User clicks browser forward button
- **Then**: User returns to dashboard
- **And**: Page state is preserved

#### Scenario: Direct URL navigation
- **Given**: User is authenticated
- **When**: User enters `/dashboard` directly in URL bar
- **Then**: Dashboard is displayed without redirect

### Requirement: Error Boundary Coverage
E2E tests MUST verify error boundaries catch and display errors gracefully.

#### Scenario: Component error is caught
- **Given**: A component throws an error
- **When**: Error propagates to boundary
- **Then**: Error boundary UI is displayed
- **And**: Error message is shown
- **And**: Retry option is available

#### Scenario: Error recovery works
- **Given**: Error boundary is displaying error
- **When**: User clicks retry/refresh
- **Then**: Component attempts to re-render
- **And**: If successful, normal UI is restored
