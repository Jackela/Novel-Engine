# Real-time Events API (SSE)

## Purpose
Specify server behavior for streaming dashboard events via SSE.

## Requirements

### Backend SSE structure
The backend MUST provide a Server-Sent Events (SSE) endpoint for real-time dashboard updates.

#### Scenario: Endpoint availability
- **GIVEN** the API server is running
- **WHEN** a GET request is made to `/api/events/stream`
- **THEN** the server returns HTTP 200 with `Content-Type: text/event-stream` and standard SSE headers

#### Scenario: Event generation
- **GIVEN** a client is connected to the SSE stream
- **WHEN** events occur in the system (or every 2 seconds during simulation)
- **THEN** the server yields data in SSE format: `id: evt-{id}\ndata: {json}\n\n`

#### Scenario: Event schema
- **GIVEN** an event is sent through the stream
- **WHEN** the client parses the event data
- **THEN** it contains: `id`, `type`, `title`, `description`, `timestamp`, and `severity`

### Connection Management
The server MUST handle client connections and disconnections gracefully without resource leaks.

#### Scenario: Client disconnection
- **GIVEN** a client is connected to the SSE stream
- **WHEN** the client disconnects (e.g., closes tab)
- **THEN** the server catches the `asyncio.CancelledError`, logs the event, and cleans up the generator session
