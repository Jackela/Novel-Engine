# Design: Dashboard Live API Integration

## Architecture Overview

This change transitions the dashboard from demo/sample data to live API-driven real-time events using Server-Sent Events (SSE), with standardized environment configuration and role-based performance metrics visibility.

### Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                   Dashboard Frontend                        │
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │ RealTimeActivity │◄────────┤useRealtimeEvents │        │
│  │   Component      │         │   Hook (SSE)     │        │
│  └──────────────────┘         └────────┬─────────┘        │
│                                         │                   │
│  ┌──────────────────┐                  │                   │
│  │PerformanceMetrics│                  │                   │
│  │  (RBAC gated)    │                  │                   │
│  └──────────────────┘                  │                   │
└────────────────────────────────────────┼───────────────────┘
                                         │
                                         │ EventSource
                                         │ (SSE connection)
                                         │
                                         v
┌─────────────────────────────────────────────────────────────┐
│                   Backend API Server                        │
│                                                             │
│  ┌──────────────────────────────────────────────┐          │
│  │  /api/v1/events/stream                       │          │
│  │  (SSE endpoint)                              │          │
│  │                                              │          │
│  │  ┌────────────────┐      ┌────────────────┐ │          │
│  │  │ Event Generator│◄─────┤ Event Store/   │ │          │
│  │  │  (async gen)   │      │ Message Queue  │ │          │
│  │  └────────────────┘      └────────────────┘ │          │
│  │                                              │          │
│  │  Yields: data: {"id":..., "type":...}       │          │
│  └──────────────────────────────────────────────┘          │
│                                                             │
│  ┌──────────────────────────────────────────────┐          │
│  │  Authentication Middleware                   │          │
│  │  (Validates role for performance metrics)    │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

## Server-Sent Events (SSE) Design

### Why SSE Over WebSocket

| Aspect | SSE | WebSocket | Decision |
|--------|-----|-----------|----------|
| **Directionality** | Server → Client only | Bidirectional | SSE sufficient (events are server-initiated) |
| **Protocol** | HTTP/HTTPS | ws:// or wss:// | SSE reuses HTTP (simpler proxy/firewall config) |
| **Reconnection** | Automatic with `EventSource` | Manual implementation required | SSE built-in reconnection |
| **Browser Support** | All modern browsers | All modern browsers | Both supported |
| **Implementation** | Simpler (HTTP streaming) | More complex (handshake, framing) | SSE faster to implement |
| **Use Case Fit** | Event feeds, notifications | Chat, gaming, real-time collaboration | SSE matches our event feed use case |

**Decision**: Use **Server-Sent Events (SSE)** for simplicity, automatic reconnection, and unidirectional event streaming.

### SSE Protocol Flow

```
Client                                    Server
  │                                         │
  │  GET /api/v1/events/stream             │
  │  Accept: text/event-stream             │
  │────────────────────────────────────────>│
  │                                         │
  │  HTTP/1.1 200 OK                       │
  │  Content-Type: text/event-stream       │
  │  Cache-Control: no-cache               │
  │  Connection: keep-alive                │
  │<────────────────────────────────────────│
  │                                         │
  │  data: {"id":"evt-1","type":"character"}│
  │<────────────────────────────────────────│
  │                                         │
  │  data: {"id":"evt-2","type":"system"}  │
  │<────────────────────────────────────────│
  │                                         │
  │  (connection maintained)                │
  │                                         │
  │  [Network interruption]                 │
  │  X───────────────────────────────────X  │
  │                                         │
  │  [EventSource auto-reconnects]         │
  │  GET /api/v1/events/stream             │
  │  Last-Event-ID: evt-2                  │
  │────────────────────────────────────────>│
  │                                         │
  │  data: {"id":"evt-3","type":"story"}   │
  │<────────────────────────────────────────│
```

### Backend SSE Implementation

**FastAPI Endpoint** (`main_api_server.py`):

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import asyncio
import json

@app.get("/api/v1/events/stream")
async def stream_events() -> StreamingResponse:
    """
    Server-Sent Events endpoint for real-time dashboard events.
    Returns text/event-stream with continuous event updates.
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        """
        Async generator yielding SSE-formatted events.
        Connects to event store/message queue and streams updates.
        """
        # Connection header
        yield f"retry: 3000\n\n"  # Client retry interval (3 seconds)

        event_id = 0
        while True:
            try:
                # Fetch next event from event store, message queue, or database
                # Example: event = await event_store.get_next_event()

                # For MVP, simulate with async sleep
                await asyncio.sleep(2)  # Event frequency

                event_id += 1
                event_data = {
                    "id": f"evt-{event_id}",
                    "type": "character",  # 'character' | 'story' | 'system' | 'interaction'
                    "title": "Character Action",
                    "description": "Character performed an action",
                    "timestamp": int(time.time() * 1000),
                    "characterName": "Alice",
                    "severity": "medium"  # 'low' | 'medium' | 'high'
                }

                # SSE message format: "data: JSON\n\n"
                yield f"id: evt-{event_id}\n"
                yield f"data: {json.dumps(event_data)}\n\n"

            except asyncio.CancelledError:
                # Client disconnected
                break
            except Exception as e:
                # Log error but keep connection alive
                error_event = {
                    "id": f"err-{event_id}",
                    "type": "system",
                    "title": "Stream Error",
                    "description": str(e),
                    "timestamp": int(time.time() * 1000),
                    "severity": "high"
                }
                yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

**Event Store Integration Options**:

1. **In-Memory Queue** (MVP): `asyncio.Queue` for development/testing
2. **Redis Pub/Sub**: Production-ready message broker
3. **Database Polling**: Query events table with `last_event_id` filter
4. **External Queue**: RabbitMQ, Kafka, AWS SQS

### Frontend SSE Integration

**useRealtimeEvents Hook Migration** (`frontend/src/hooks/useRealtimeEvents.ts`):

```typescript
import { useState, useEffect, useRef } from 'react';

interface RealtimeEvent {
  id: string | number;
  type: 'character' | 'story' | 'system' | 'interaction';
  title: string;
  description: string;
  timestamp: number;
  characterName?: string;
  severity: 'low' | 'medium' | 'high';
}

interface UseRealtimeEventsReturn {
  events: RealtimeEvent[];
  loading: boolean;
  error: Error | null;
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
}

export function useRealtimeEvents(
  endpoint: string = import.meta.env.VITE_DASHBOARD_EVENTS_ENDPOINT || '/api/v1/events/stream',
  maxEvents: number = 50
): UseRealtimeEventsReturn {
  const [events, setEvents] = useState<RealtimeEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('connecting');

  const eventSourceRef = useRef<EventSource | null>(null);
  const eventsBufferRef = useRef<RealtimeEvent[]>([]);

  useEffect(() => {
    // Create EventSource connection
    const eventSource = new EventSource(endpoint);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setConnectionState('connected');
      setLoading(false);
      setError(null);
    };

    eventSource.onmessage = (event) => {
      try {
        const eventData: RealtimeEvent = JSON.parse(event.data);

        // Add to buffer and maintain max size
        eventsBufferRef.current = [eventData, ...eventsBufferRef.current].slice(0, maxEvents);
        setEvents([...eventsBufferRef.current]);

      } catch (err) {
        console.error('Failed to parse event data:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE connection error:', err);
      setConnectionState('error');
      setLoading(false);
      setError(new Error('Failed to connect to event stream. Please check your connection and try again.'));

      // EventSource automatically attempts reconnection
      // We update state but let browser handle retry
    };

    // Cleanup on unmount
    return () => {
      eventSource.close();
      eventSourceRef.current = null;
      setConnectionState('disconnected');
    };
  }, [endpoint, maxEvents]);

  return { events, loading, error, connectionState };
}
```

**RealTimeActivity Component Updates** (`frontend/src/components/dashboard/RealTimeActivity.tsx`):

```typescript
import { useRealtimeEvents } from '@/hooks/useRealtimeEvents';
import { AlertCircle } from 'lucide-react';

export function RealTimeActivity() {
  const { events, loading, error, connectionState } = useRealtimeEvents();

  // Error state UI (no demo fallback)
  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4" role="alert">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-red-600" aria-hidden="true" />
          <h3 className="font-semibold text-red-900">Unable to load live events</h3>
        </div>
        <p className="mt-2 text-sm text-red-700">{error.message}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-3 rounded bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return <div className="animate-pulse">Connecting to live feed...</div>;
  }

  // Connected state
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h2>Live Feed</h2>
        <span className={`text-xs ${connectionState === 'connected' ? 'text-green-600' : 'text-gray-500'}`}>
          {connectionState === 'connected' ? '● Live' : '○ Connecting'}
        </span>
      </div>

      {events.length === 0 ? (
        <p className="text-sm text-gray-500">No recent events</p>
      ) : (
        <ul className="space-y-2">
          {events.map((event) => (
            <li key={event.id} className="rounded border p-2">
              <div className="font-semibold">{event.title}</div>
              <div className="text-sm text-gray-600">{event.description}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

## Performance Metrics RBAC Design

### Role-Based Visibility Strategy

```typescript
// frontend/src/components/dashboard/PerformanceMetrics.tsx

import { useAuth } from '@/hooks/useAuth';  // Assumes auth context exists
import { usePerformance } from '@/hooks/usePerformance';  // Web Vitals hook

export function PerformanceMetrics() {
  const { user } = useAuth();
  const performanceData = usePerformance();

  // Check if user has developer or admin role
  const canViewMetrics = user?.roles?.includes('developer') || user?.roles?.includes('admin');

  // Return null if user doesn't have permission
  if (!canViewMetrics) {
    return null;  // Widget completely hidden
  }

  // Render Web Vitals for authorized users
  return (
    <div className="rounded-lg border p-4">
      <h2 className="mb-4 text-lg font-semibold">Performance Metrics (Dev)</h2>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-sm text-gray-600">LCP</div>
          <div className="text-2xl font-bold">{performanceData.lcp}ms</div>
        </div>
        <div>
          <div className="text-sm text-gray-600">FID</div>
          <div className="text-2xl font-bold">{performanceData.fid}ms</div>
        </div>
        {/* CLS, FCP, TTFB... */}
      </div>
    </div>
  );
}
```

### Authentication Requirement

This design assumes an authentication system exists with:
- `useAuth()` hook providing user context
- User object with `roles` array: `['developer', 'admin', 'user']`
- Role enforcement at component level (no backend metrics endpoint needed)

## Environment Configuration Standardization

### Current State Issues
- Mix of `REACT_APP_*` (Create React App legacy) and `VITE_*` prefixes
- No centralized dashboard configuration
- `VITE_DASHBOARD_EVENTS_ENDPOINT` references non-existent endpoint

### Proposed Standard

**Environment Variables** (`.env.example`):

```bash
# ========================================
# Dashboard Configuration
# ========================================

# Backend API base URL (used for relative path resolution)
VITE_API_BASE_URL=http://localhost:8000

# Real-time events SSE endpoint (relative to VITE_API_BASE_URL or absolute)
VITE_DASHBOARD_EVENTS_ENDPOINT=/api/v1/events/stream

# Characters data endpoint (canonical endpoint per dashboard-data-routing-hygiene)
VITE_DASHBOARD_CHARACTERS_ENDPOINT=/api/v1/characters

# Enable debug logging for dashboard components
VITE_DASHBOARD_DEBUG=false
```

**Vite Proxy Configuration** (`frontend/vite.config.ts`):

```typescript
export default defineConfig({
  server: {
    proxy: {
      // Proxy all /api/v1/* requests to backend
      '/api/v1': {
        target: process.env.VITE_API_BASE_URL || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v1/, '/api/v1'),
        // SSE-specific configuration
        configure: (proxy, _options) => {
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            // Preserve SSE headers
            if (req.url?.includes('/events/stream')) {
              proxyReq.setHeader('Accept', 'text/event-stream');
              proxyReq.setHeader('Cache-Control', 'no-cache');
              proxyReq.setHeader('Connection', 'keep-alive');
            }
          });
        }
      }
    }
  }
});
```

### Migration Path

1. **Audit existing env vars**: Search for `REACT_APP_*` and `VITE_*` usage
2. **Standardize to `VITE_DASHBOARD_*`**: Rename all dashboard-specific vars
3. **Update imports**: Replace `process.env.REACT_APP_*` with `import.meta.env.VITE_*`
4. **Document in `.env.example`**: Add dashboard section with all endpoints
5. **Update Vite config**: Ensure proxy supports SSE headers

## Testing Strategy

### Integration Tests

**SSE Connection Tests** (`frontend/src/hooks/__tests__/useRealtimeEvents.test.tsx`):

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { useRealtimeEvents } from '../useRealtimeEvents';
import { server } from '@/test/mocks/server';
import { rest } from 'msw';

describe('useRealtimeEvents', () => {
  it('establishes SSE connection and receives events', async () => {
    const { result } = renderHook(() => useRealtimeEvents());

    await waitFor(() => {
      expect(result.current.connectionState).toBe('connected');
      expect(result.current.loading).toBe(false);
    });

    // Simulate event arrival
    await waitFor(() => {
      expect(result.current.events.length).toBeGreaterThan(0);
    });
  });

  it('shows error state when connection fails', async () => {
    // Mock SSE endpoint failure
    server.use(
      rest.get('/api/v1/events/stream', (_req, res, ctx) => {
        return res(ctx.status(500));
      })
    );

    const { result } = renderHook(() => useRealtimeEvents());

    await waitFor(() => {
      expect(result.current.connectionState).toBe('error');
      expect(result.current.error).not.toBeNull();
    });
  });

  it('automatically reconnects after network interruption', async () => {
    // Test EventSource auto-reconnection behavior
    // This requires mocking EventSource and simulating disconnection
  });
});
```

**RBAC Tests** (`frontend/src/components/dashboard/__tests__/PerformanceMetrics.test.tsx`):

```typescript
import { render, screen } from '@testing-library/react';
import { PerformanceMetrics } from '../PerformanceMetrics';
import { AuthProvider } from '@/contexts/AuthContext';

describe('PerformanceMetrics RBAC', () => {
  it('renders for users with developer role', () => {
    render(
      <AuthProvider user={{ roles: ['developer'] }}>
        <PerformanceMetrics />
      </AuthProvider>
    );

    expect(screen.getByText(/Performance Metrics/i)).toBeInTheDocument();
  });

  it('renders for users with admin role', () => {
    render(
      <AuthProvider user={{ roles: ['admin'] }}>
        <PerformanceMetrics />
      </AuthProvider>
    );

    expect(screen.getByText(/Performance Metrics/i)).toBeInTheDocument();
  });

  it('hides for regular users without developer/admin role', () => {
    render(
      <AuthProvider user={{ roles: ['user'] }}>
        <PerformanceMetrics />
      </AuthProvider>
    );

    expect(screen.queryByText(/Performance Metrics/i)).not.toBeInTheDocument();
  });

  it('hides when user is not authenticated', () => {
    render(
      <AuthProvider user={null}>
        <PerformanceMetrics />
      </AuthProvider>
    );

    expect(screen.queryByText(/Performance Metrics/i)).not.toBeInTheDocument();
  });
});
```

### API Contract Tests

**Backend Endpoint Tests** (Python pytest):

```python
import pytest
from fastapi.testclient import TestClient
from main_api_server import app

@pytest.fixture
def client():
    return TestClient(app)

def test_events_stream_endpoint_exists(client):
    """Verify /api/v1/events/stream endpoint is available"""
    response = client.get("/api/v1/events/stream")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"

def test_events_stream_returns_sse_format(client):
    """Verify SSE format: 'data: {...}\n\n'"""
    with client.stream("GET", "/api/v1/events/stream") as response:
        for line in response.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])  # Strip "data: " prefix
                assert "id" in data
                assert "type" in data
                assert data["type"] in ["character", "story", "system", "interaction"]
                break

def test_events_stream_includes_retry_header(client):
    """Verify retry directive in SSE stream"""
    with client.stream("GET", "/api/v1/events/stream") as response:
        first_line = next(response.iter_lines())
        assert first_line.startswith("retry:")
```

## Integration Points

### Alignment with dashboard-data-routing-hygiene

This change extends the canonical `/api/v1/*` pattern established by dashboard-data-routing-hygiene:

- Characters: `/api/v1/characters` ✓ (existing)
- Events: `/api/v1/events/stream` ✓ (new)
- Consistent Vite proxy: `/api/v1/*` → backend ✓

### Authentication System Integration

Requires existing or new authentication system providing:
- `useAuth()` hook
- User context with `roles` array
- Role definitions: `'developer' | 'admin' | 'user'`

If authentication doesn't exist, Performance metrics visibility can be controlled via:
- Environment variable: `VITE_SHOW_PERFORMANCE_METRICS=true` (dev only)
- Build mode: Only show in development builds

## Risk Mitigation

### SSE Connection Failures
- **Risk**: Backend unavailable, network issues, proxy misconfiguration
- **Mitigation**: Clear error messages with retry button, automatic reconnection via EventSource

### Role System Dependency
- **Risk**: Authentication system not implemented yet
- **Mitigation**: Phase 1 uses env var toggle (`VITE_SHOW_PERFORMANCE_METRICS`), Phase 2 adds RBAC when auth system ready

### Event Flooding
- **Risk**: Backend sends events too fast, overwhelming frontend
- **Mitigation**:
  - Buffer limit (`maxEvents` parameter, default 50)
  - Backend rate limiting (max 1 event per second)
  - Client-side throttling/debouncing for UI updates

### Browser Compatibility
- **Risk**: EventSource not supported in older browsers
- **Mitigation**: Polyfill via `event-source-polyfill` package, or feature detection with graceful degradation

## Trade-offs

| Decision | Pro | Con | Rationale |
|----------|-----|-----|-----------|
| SSE over WebSocket | Simpler implementation, auto-reconnection, HTTP-based | Unidirectional only | Event feed is server-initiated; no need for client → server messages |
| Error-first (no demo fallback) | Clear failure states, forces API implementation | Users see errors if backend down | Better UX transparency; demo mode created false confidence |
| RBAC for Performance widget | Privacy, role separation | Requires auth system | Developer metrics shouldn't be visible to all users |
| EventSource over manual fetch | Browser-native, auto-reconnection | Less control over reconnection logic | Browser handles complexity; simpler hook implementation |
| In-memory queue for MVP | Fast implementation, no external dependencies | Not scalable, loses events on restart | Good for development; production can swap to Redis/Kafka |

## Future Enhancements

1. **Event Filtering**: Allow users to filter events by type/severity
2. **Event Persistence**: Store events in database for historical analysis
3. **Event Acknowledgment**: Mark events as "read" with Last-Event-ID tracking
4. **Backend Metrics Endpoint**: Add `/api/v1/metrics` for system health (separate from Web Vitals)
5. **WebSocket Migration**: Upgrade to WebSocket if bidirectional communication needed (e.g., event acknowledgment from client)
6. **Event Search**: Full-text search across historical events
7. **Event Notifications**: Browser notifications for high-severity events
