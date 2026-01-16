# Server-Sent Events (SSE) Endpoint

## Overview

The `/api/events/stream` endpoint provides real-time dashboard events via Server-Sent Events (SSE). This allows the frontend to receive continuous updates without polling.

## Endpoint Details

- **Path**: `/api/events/stream`
- **Method**: `GET`
- **Protocol**: Server-Sent Events (SSE)
- **Content-Type**: `text/event-stream`
- **Authentication**: None (currently public for MVP)
- **Query params**:
  - `limit` (int, optional): max events for test clients.
  - `interval` (float, optional): override simulated event interval in seconds (testing only; clamped 0.01–10.0).

## Connection Lifecycle

### 1. Client Connection

```javascript
const eventSource = new EventSource('/api/events/stream');
```

### 2. Retry Directive

The server sends a retry directive on connection:
```
retry: 3000
```

This instructs the browser to wait 3000ms (3 seconds) before reconnecting if the connection is lost.

### 3. Event Streaming

Events are sent every 2 seconds in SSE format (or faster when `interval` is set):

```
id: evt-1
data: {"id":"evt-1","type":"story","title":"Event 1","description":"Simulated dashboard event #1","timestamp":1763442751446,"severity":"medium"}

id: evt-2
data: {"id":"evt-2","type":"system","title":"Event 2","description":"Simulated dashboard event #2","timestamp":1763442753446,"severity":"high"}
```

### 4. Connection Termination

When the client closes the connection (e.g., page unload), the server logs the disconnection and decrements the active connection counter.

## Event Payload Structure

Each event contains the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Unique event identifier (format: `evt-{number}` or `err-{number}`) |
| `type` | string | ✅ | Event category: `character`, `story`, `system`, `interaction` |
| `title` | string | ✅ | Short event title |
| `description` | string | ✅ | Detailed event description |
| `timestamp` | number | ✅ | Unix timestamp in milliseconds |
| `severity` | string | ✅ | Priority level: `low`, `medium`, `high` |
| `characterName` | string | ❌ | Character name (only for `type: "character"`) |

### Example Payloads

#### Character Event
```json
{
  "id": "evt-4",
  "type": "character",
  "title": "Event 4",
  "description": "Simulated dashboard event #4",
  "timestamp": 1763442757446,
  "severity": "low",
  "characterName": "Character-4"
}
```

#### System Event
```json
{
  "id": "evt-2",
  "type": "system",
  "title": "Event 2",
  "description": "Simulated dashboard event #2",
  "timestamp": 1763442753446,
  "severity": "high"
}
```

#### Error Event
```json
{
  "id": "err-42",
  "type": "system",
  "title": "Stream Error",
  "description": "Internal error: Database connection timeout",
  "timestamp": 1763442800000,
  "severity": "high"
}
```

## Testing with curl

### Basic Connection Test

```bash
curl -N -H "Accept: text/event-stream" http://localhost:8000/api/events/stream
```

Expected output:
```
retry: 3000

id: evt-1
data: {"id":"evt-1","type":"story",...}

id: evt-2
data: {"id":"evt-2","type":"system",...}
```

### Timeout Test (10 seconds)

```bash
timeout 10 curl -N -H "Accept: text/event-stream" http://localhost:8000/api/events/stream
```

### Fast Test Stream (50ms interval)

```bash
curl -N -H "Accept: text/event-stream" "http://localhost:8000/api/events/stream?limit=5&interval=0.05"
```

## Frontend Integration

### React Hook (Recommended)

Use the provided `useRealtimeEvents` hook:

```typescript
import { useRealtimeEvents } from '@/hooks/useRealtimeEvents';

function MyComponent() {
  const { events, loading, error, connectionState } = useRealtimeEvents({
    enabled: true,
    maxEvents: 50
  });

  if (loading) return <div>Connecting...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      <p>Status: {connectionState}</p>
      <ul>
        {events.map(event => (
          <li key={event.id}>{event.description}</li>
        ))}
      </ul>
    </div>
  );
}
```

### Raw EventSource API

```javascript
const eventSource = new EventSource('/api/events/stream');

eventSource.onopen = () => {
  console.log('Connection opened');
};

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received event:', data);
};

eventSource.onerror = (error) => {
  console.error('SSE error:', error);
  // Browser will automatically retry based on retry directive
};

// Cleanup
window.addEventListener('beforeunload', () => {
  eventSource.close();
});
```

## Response Headers

The endpoint sets the following headers for proper SSE streaming:

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no  # Disables nginx buffering
```

## Connection Monitoring

The server tracks active connections in memory:

```python
active_sse_connections = {"count": 0}
```

This counter increments on connection and decrements on disconnection, useful for monitoring and debugging.

## Error Handling

### Server-Side Errors

If an error occurs during event generation, the server sends an error event and continues streaming:

```
id: err-123
data: {"id":"err-123","type":"system","title":"Stream Error","description":"Internal error: ...","timestamp":...,"severity":"high"}
```

### Client-Side Errors

The `EventSource` API automatically handles:
- Network disconnections (auto-reconnect with retry interval)
- HTTP errors (fires `onerror` event)
- Malformed data (skips invalid events)

## Current Implementation (MVP)

⚠️ **Note**: The current implementation generates **simulated events** for demonstration purposes.

Event generation logic:
```python
# MVP: Simulated events
event_types = ["character", "story", "system", "interaction"]
severities = ["low", "medium", "high"]

event_data = {
    "id": f"evt-{event_id}",
    "type": event_types[event_id % len(event_types)],  # Cycles through types
    "title": f"Event {event_id}",
    "description": f"Simulated dashboard event #{event_id}",
    "timestamp": int(time.time() * 1000),
    "severity": severities[event_id % len(severities)],  # Cycles through severities
}
```

**Production Migration**: Replace with actual event source (message queue, event store, database triggers, etc.).

## Performance Considerations

- **Event Frequency**: Current MVP sends events every 2 seconds (override via `interval` for tests)
- **Connection Limit**: No enforced limit (monitor `active_sse_connections["count"]`)
- **Memory**: Events are generated on-demand, no server-side buffering
- **Network**: Each event is ~150-200 bytes

## Browser Compatibility

| Browser | EventSource Support |
|---------|---------------------|
| Chrome | ✅ |
| Firefox | ✅ |
| Safari | ✅ |
| Edge | ✅ |
| IE 11 | ❌ (requires polyfill) |

For older browsers, use the [EventSource polyfill](https://github.com/Yaffle/EventSource).

## Security Considerations

### Current State (MVP)
- ❌ No authentication
- ❌ No rate limiting
- ❌ No input validation (no client input)
- ✅ CORS enabled
- ✅ No sensitive data in simulated events

### Production Requirements
- [ ] Add authentication token validation
- [ ] Implement per-user connection limits
- [ ] Add rate limiting middleware
- [ ] Sanitize event data for XSS prevention
- [ ] Log connection attempts for audit trail

## Troubleshooting

### Connection Fails (404)

**Problem**: `GET /api/events/stream` returns 404

**Solution**: Ensure you're running the main API entrypoint.

```bash
# Preferred
python -m src.api.main_api_server

# Legacy (still supported for compatibility)
python api_server.py
```

### No Events Received

**Problem**: Connection succeeds but no events appear

**Checklist**:
1. Check browser console for `EventSource` errors
2. Verify `Accept: text/event-stream` header is sent
3. Check backend logs for "SSE client connected" message
4. Test with curl to isolate frontend vs backend issue

### Events Stop After Some Time

**Problem**: Events stream initially but stop after a few minutes

**Possible Causes**:
- Nginx/proxy buffering (check `X-Accel-Buffering: no` header)
- Load balancer timeout (increase timeout or send heartbeat events)
- Browser tab suspended (check `document.visibilityState`)

## Future Enhancements

### Planned Features
- [ ] Authentication with JWT tokens
- [ ] Event filtering by type or severity
- [ ] Historical event replay (last N events on connection)
- [ ] Event acknowledgment mechanism
- [ ] Compression for large payloads
- [ ] Multiplexing (multiple event streams per connection)

### Migration to Real Events
When integrating with actual event sources:

```python
# Example: Redis Pub/Sub integration
import redis

async def event_generator(client_id: str):
    yield "retry: 3000\n\n"

    redis_client = redis.Redis()
    pubsub = redis_client.pubsub()
    pubsub.subscribe('dashboard-events')

    for message in pubsub.listen():
        if message['type'] == 'message':
            event_data = json.loads(message['data'])
            yield f"id: {event_data['id']}\n"
            yield f"data: {json.dumps(event_data)}\n\n"
```

## Related Documentation

- [Frontend Integration Guide](../migration/demo-to-live-api.md)
- [useRealtimeEvents Hook Documentation](../../frontend/src/hooks/useRealtimeEvents.ts)

## Support

For issues or questions:
- Check [Troubleshooting](#troubleshooting) section
- Run Playwright smoke tests (`cd frontend && npm run test:e2e:smoke`) and attach failures/logs to an issue/PR
- File an issue on GitHub
