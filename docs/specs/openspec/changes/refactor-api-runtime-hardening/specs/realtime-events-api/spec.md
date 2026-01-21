## ADDED Requirements
### Requirement: SSE streaming is non-blocking
The SSE endpoint MUST use non-blocking waits (e.g., `await asyncio.sleep`) so streaming does not block the event loop.

#### Scenario: Stream does not block other requests
- **GIVEN** a client is connected to `/api/events/stream`
- **WHEN** the server waits between events
- **THEN** other API requests continue to be served without delay.

### Requirement: SSE disconnects handle asyncio cancellation
The SSE endpoint MUST catch `asyncio.CancelledError` on disconnect and release resources cleanly.

#### Scenario: Client disconnects mid-stream
- **GIVEN** a client is connected to the SSE stream
- **WHEN** the client disconnects
- **THEN** the server logs the disconnect, handles `asyncio.CancelledError`, and cleans up.
