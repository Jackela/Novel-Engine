## ADDED Requirements

### Requirement: SSE-based real-time events hook
Frontend MUST provide `useRealtimeEvents` hook that establishes SSE connection to `/api/events/stream` and manages event state, connection lifecycle, and error handling.

#### Scenario: Hook establishes SSE connection on mount
- **GIVEN** the `useRealtimeEvents` hook is called with an endpoint parameter (default: `/api/events/stream`)
- **WHEN** the component mounts
- **THEN** the hook creates an `EventSource` instance connecting to the endpoint, sets `connectionState` to 'connecting', and sets `loading` to true

#### Scenario: Hook updates state when connection opens
- **GIVEN** the EventSource connection is established
- **WHEN** the `onopen` event fires
- **THEN** the hook sets `connectionState` to 'connected', `loading` to false, and `error` to null

#### Scenario: Hook receives and parses event data
- **GIVEN** the SSE connection is active
- **WHEN** the backend sends an event via `onmessage`
- **THEN** the hook parses the JSON payload, validates the event structure (id, type, title, description, timestamp, severity), adds it to the events array (newest first), and maintains the maximum event buffer size (default 50)

#### Scenario: Hook handles connection errors
- **GIVEN** the SSE connection fails (network error, server unavailable, 5xx response)
- **WHEN** the `onerror` event fires
- **THEN** the hook sets `connectionState` to 'error', `loading` to false, `error` to a descriptive Error object with message "Failed to connect to event stream. Please check your connection and try again.", and allows EventSource automatic reconnection to proceed

#### Scenario: Hook cleans up connection on unmount
- **GIVEN** a component using `useRealtimeEvents` is unmounted
- **WHEN** the cleanup function runs
- **THEN** the hook calls `eventSource.close()`, sets the ref to null, and sets `connectionState` to 'disconnected'

#### Scenario: Hook respects maximum event buffer size
- **GIVEN** the hook has `maxEvents` parameter set to 50
- **WHEN** a new event arrives and the buffer already contains 50 events
- **THEN** the hook adds the new event at index 0 and removes the oldest event (index 50), keeping the array length at 50

### Requirement: Error-first RealTimeActivity UI
RealTimeActivity component MUST display clear error states when SSE connection fails, with no fallback to demo data.

#### Scenario: Component shows loading state during connection
- **GIVEN** the `useRealtimeEvents` hook returns `loading: true` and `connectionState: 'connecting'`
- **WHEN** the RealTimeActivity component renders
- **THEN** it displays "Connecting to live feed..." message with loading indicator

#### Scenario: Component displays error state with retry action
- **GIVEN** the `useRealtimeEvents` hook returns an error object
- **WHEN** the RealTimeActivity component renders
- **THEN** it displays a styled error container with role="alert", shows AlertCircle icon, heading "Unable to load live events", error message text, and a "Retry Connection" button that reloads the page

#### Scenario: Component shows connection status indicator
- **GIVEN** the `useRealtimeEvents` hook returns `connectionState` ('connecting' | 'connected' | 'disconnected' | 'error')
- **WHEN** the RealTimeActivity component renders in connected state
- **THEN** it displays a status indicator with "● Live" in green for 'connected' or "○ Connecting" in gray for other states

#### Scenario: Component renders events in chronological order
- **GIVEN** the `useRealtimeEvents` hook returns an array of events sorted newest-first
- **WHEN** the RealTimeActivity component renders
- **THEN** it maps over the events array and renders each event with key={event.id}, displaying title, description, and timestamp in a list format

#### Scenario: Component shows empty state when no events
- **GIVEN** the connection is active but `events` array is empty
- **WHEN** the RealTimeActivity component renders
- **THEN** it displays "No recent events" message instead of an empty list

### Requirement: Frontend SSE connection resilience
Frontend SSE integration MUST handle network interruptions, reconnections, and browser lifecycle events gracefully.

#### Scenario: Browser auto-reconnects after network interruption
- **GIVEN** an active SSE connection is interrupted by network failure
- **WHEN** the browser's EventSource detects the disconnection
- **THEN** EventSource automatically attempts to reconnect to `/api/events/stream`, sends `Last-Event-ID` header with the ID of the last received event, and the hook updates `connectionState` appropriately during reconnection

#### Scenario: Hook handles page visibility changes
- **GIVEN** the user switches to a different browser tab (page visibility: hidden)
- **WHEN** the user returns to the dashboard tab (page visibility: visible)
- **THEN** the SSE connection remains active (or reconnects if closed), and the hook receives any events that occurred while the tab was hidden

#### Scenario: Hook handles rapid unmount/remount cycles
- **GIVEN** the RealTimeActivity component unmounts and remounts quickly (e.g., React strict mode, navigation)
- **WHEN** the cleanup and initialization occur in rapid succession
- **THEN** the hook closes the previous EventSource before creating a new one, prevents memory leaks from duplicate connections, and correctly establishes a single active connection

### Requirement: Accessibility for error states
Error states in RealTimeActivity MUST be accessible to screen readers and keyboard users.

#### Scenario: Error messages are announced to screen readers
- **GIVEN** an SSE connection error occurs
- **WHEN** the error UI is rendered
- **THEN** the error container has `role="alert"` attribute, error text is readable by screen readers, and the heading conveys the severity ("Unable to load live events")

#### Scenario: Retry button is keyboard accessible
- **GIVEN** the error state is displayed with a "Retry Connection" button
- **WHEN** a keyboard user tabs to the button
- **THEN** the button receives focus with visible focus indicator, can be activated with Enter or Space key, and triggers page reload to retry the connection

#### Scenario: Connection status is accessible
- **GIVEN** the component displays a connection status indicator ("● Live" or "○ Connecting")
- **WHEN** a screen reader encounters the indicator
- **THEN** the status is conveyed through text content ("Live" or "Connecting"), not relying solely on color or symbols for meaning
