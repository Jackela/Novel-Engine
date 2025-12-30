# Real-time Events Frontend Integration

## Purpose
Define how the UI consumes and displays live SSE events.

## Requirements

### useRealtimeEvents hook
The frontend MUST provide a hook that manages the lifecycle of the SSE connection.

#### Scenario: Connection establishment
- **GIVEN** the `useRealtimeEvents` hook is mounted
- **WHEN** it initializes
- **THEN** it creates a new `EventSource` pointing to the events endpoint and sets `connectionState` to 'connected' on success

#### Scenario: Message processing
- **GIVEN** the SSE connection is active
- **WHEN** a new message arrives
- **THEN** the hook parses the JSON data, prepends it to the events array, and ensures the array does not exceed `maxEvents` (default 50)

#### Scenario: Error handling
- **GIVEN** the SSE connection fails or the server is down
- **WHEN** an error occurs
- **THEN** the hook sets `connectionState` to 'error' and provides a descriptive error message

### RealTimeActivity UI
The activity feed component MUST display real-time events and connection status.

#### Scenario: Live indicator
- **GIVEN** the component is rendered
- **WHEN** the hook reports 'connected'
- **THEN** a "● Live" indicator is shown in green

#### Scenario: Reconnect button
- **GIVEN** the connection has failed
- **WHEN** the error state is displayed
- **THEN** a "Retry Connection" button is available to allow the user to manually trigger a reconnect (reload)
