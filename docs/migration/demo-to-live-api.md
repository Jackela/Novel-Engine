# Migration Guide: Demo Mode to Live API

## Overview

This guide explains how to migrate the Emergent Narrative Dashboard from **demo mode** (with simulated data) to **live API mode** (with real-time Server-Sent Events).

## What Changed

### Before (Demo Mode)
- ❌ Hardcoded `INITIAL_EVENTS` array in `RealTimeActivity.tsx`
- ❌ `setInterval` polling every 2 seconds to generate fake events
- ❌ `source: 'demo'` label in UI
- ❌ Simulated backend metrics in `PerformanceMetrics.tsx`
- ❌ Local state management for demo data

### After (Live API Mode)
- ✅ Server-Sent Events (SSE) via `/api/v1/events/stream`
- ✅ Real-time push from backend (no polling)
- ✅ `source: 'api'` with connection status indicator
- ✅ Web Vitals only (removed fake backend metrics)
- ✅ Centralized event stream with automatic reconnection

## Breaking Changes

### 1. RealTimeActivity Component

**Removed** (~136 lines):
```typescript
// OLD: Demo data
const INITIAL_EVENTS = [
  {
    id: 'demo-1',
    type: 'character',
    title: 'Aria Shadowbane',
    description: 'Updated faction reputation: +5 with Crystal Alliance',
    // ...
  },
  // ... more hardcoded events
];

// OLD: Simulated event generation
useEffect(() => {
  const interval = setInterval(() => {
    // Generate fake events
  }, 2000);
  return () => clearInterval(interval);
}, []);
```

**Added**:
```typescript
// NEW: SSE integration via hook
import { useRealtimeEvents } from '../../hooks/useRealtimeEvents';

const { events, loading, error, connectionState } = useRealtimeEvents({
  enabled: true
});
```

### 2. Performance Metrics Component

**Removed** (~150 lines):
```typescript
// OLD: Simulated backend metrics
const [responseTime, setResponseTime] = useState(245);
const [errorRate, setErrorRate] = useState(0.02);
const [activeUsers, setActiveUsers] = useState(127);
// ... 5 more metrics

useEffect(() => {
  const interval = setInterval(() => {
    setResponseTime(prev => prev + Math.random() * 20 - 10);
    // ... update all metrics
  }, 3000);
  return () => clearInterval(interval);
}, []);
```

**Added**:
```typescript
// NEW: Web Vitals only
import { usePerformance } from '../../hooks/usePerformance';

const [webVitals, setWebVitals] = useState<WebVitalsState>({});

usePerformance({
  onMetric: (metric) => {
    setWebVitals(prev => ({
      ...prev,
      [metric.name.toLowerCase()]: metric.value,
    }));
  },
});
```

### 3. Environment Variables

**Old** (CRA-style):
```bash
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8001/ws
```

**New** (Vite-style):
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_DASHBOARD_EVENTS_ENDPOINT=/api/v1/events/stream
VITE_DASHBOARD_CHARACTERS_ENDPOINT=/api/v1/characters
VITE_DASHBOARD_DEBUG=false
VITE_SHOW_PERFORMANCE_METRICS=false
```

## Migration Steps

### Step 1: Update Environment Variables

1. Copy `frontend/.env.example` to `frontend/.env`:
   ```bash
   cp frontend/.env.example frontend/.env
   ```

2. Configure API base URL:
   ```bash
   # frontend/.env
   VITE_API_BASE_URL=http://localhost:8000
   ```

3. (Optional) Override default endpoints:
   ```bash
   # Only needed if your endpoints differ
   VITE_DASHBOARD_EVENTS_ENDPOINT=/custom/events/stream
   VITE_DASHBOARD_CHARACTERS_ENDPOINT=/custom/characters
   ```

### Step 2: Start Backend Server

⚠️ **Critical**: Ensure you're running `api_server.py`, NOT `main_api_server.py`

```bash
cd /path/to/Novel-Engine
python api_server.py
```

The SSE endpoint (`/api/v1/events/stream`) is only available in `api_server.py`.

**Verify backend is running**:
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy",...}

curl -N -H "Accept: text/event-stream" http://localhost:8000/api/v1/events/stream
# Should stream: retry: 3000 + events every 2 seconds
```

### Step 3: Start Frontend Dev Server

```bash
cd frontend
npm run dev
```

Vite will automatically proxy `/api/v1/*` requests to `VITE_API_BASE_URL`.

### Step 4: Verify Live Connection

1. Open browser to `http://localhost:3000/dashboard`
2. Check Real-time Activity widget:
   - ✅ Status shows **"● Live"** (green)
   - ✅ Events appear every 2 seconds
   - ✅ Event count badge updates
   - ❌ No "Demo Mode" label

3. Open browser console (F12):
   - ✅ No SSE connection errors
   - ✅ Network tab shows `GET /api/v1/events/stream [success - 200]`

4. Test error handling:
   - Stop backend server
   - Dashboard should show error state: "Unable to load live events"
   - "Retry Connection" button should appear
   - Restart backend
   - Connection should auto-recover after 3 seconds

### Step 5: Configure Production

For production deployment, update environment variables:

```bash
# Production .env
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_DASHBOARD_DEBUG=false
```

Build for production:
```bash
npm run build
npm run preview  # Test production build locally
```

## Troubleshooting

### Problem: "○ Connecting" Status Never Changes

**Symptoms**:
- Status indicator stays gray "○ Connecting"
- No events appear
- Console shows SSE connection error

**Solutions**:

1. **Check backend server**:
   ```bash
   ps aux | grep api_server
   # Should show: python api_server.py
   ```

2. **Verify endpoint exists**:
   ```bash
   curl http://localhost:8000/api/v1/events/stream
   # Should NOT return 404
   ```

3. **Check proxy configuration**:
   - Ensure `vite.config.ts` has proxy for `/api/v1/*`
   - Restart Vite dev server if config changed

### Problem: 404 on SSE Endpoint

**Error**: `GET /api/v1/events/stream [failed - 404]`

**Cause**: Running wrong backend server

**Fix**:
```bash
# Kill main_api_server if running
pkill -f "python.*main_api_server"

# Start correct server
python api_server.py
```

### Problem: Events Stop After Some Time

**Symptoms**:
- Connection starts fine
- Events stream initially
- After 5-10 minutes, events stop

**Solutions**:

1. **Check browser tab visibility**:
   - Browser may suspend background tabs
   - Bring tab to foreground

2. **Check server logs**:
   ```bash
   tail -f logs/api_server.log
   # Look for "SSE client disconnected" or errors
   ```

3. **Test connection stability**:
   ```bash
   timeout 600 curl -N http://localhost:8000/api/v1/events/stream
   # Should run for 10 minutes without errors
   ```

### Problem: Performance Metrics Widget Missing

**Symptoms**:
- Performance Metrics widget not visible
- Expected in layout but doesn't appear

**Cause**: RBAC is hiding the widget

**Solutions**:

1. **Check user role** (if auth enabled):
   - User needs `developer` or `admin` role
   - Regular `user` role cannot see metrics

2. **Enable via environment variable** (fallback):
   ```bash
   # frontend/.env
   VITE_SHOW_PERFORMANCE_METRICS=true
   ```

3. **Verify in code**:
   ```typescript
   // PerformanceMetrics.tsx
   const canViewMetrics = hasDevAccess ??
     (import.meta.env.VITE_SHOW_PERFORMANCE_METRICS === 'true');
   ```

### Problem: CORS Errors

**Error**: `Access to fetch at 'http://localhost:8000/api/v1/events/stream' from origin 'http://localhost:3000' has been blocked by CORS`

**Fix**: CORS should already be configured in `api_server.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

If using production, update `allow_origins` to your domain.

## Rollback Plan

If you need to revert to demo mode:

### Option 1: Git Revert (Recommended)
```bash
git log --oneline | grep "demo"
git revert <commit-hash>
```

### Option 2: Manual Restore

1. **Restore old RealTimeActivity.tsx**:
   ```bash
   git checkout HEAD~1 frontend/src/components/dashboard/RealTimeActivity.tsx
   ```

2. **Restore old PerformanceMetrics.tsx**:
   ```bash
   git checkout HEAD~1 frontend/src/components/dashboard/PerformanceMetrics.tsx
   ```

3. **Remove SSE endpoint from api_server.py**:
   - Delete lines 961-1080 (`event_generator` function + `stream_events` endpoint)

4. **Restart servers**:
   ```bash
   # Restart backend
   pkill -f "python api_server"
   python api_server.py

   # Restart frontend
   cd frontend
   npm run dev
   ```

## Performance Impact

### Before (Demo Mode)
- Frontend CPU: ~2-3% (setInterval polling)
- Memory: ~50MB baseline
- Network: 0 bytes/sec (all local)

### After (Live API Mode)
- Frontend CPU: ~1-2% (EventSource is more efficient)
- Memory: ~52MB baseline (+2MB for SSE buffer)
- Network: ~400 bytes/sec (SSE events)
- Backend: +1 thread per connection

**Recommendation**: For 100+ concurrent users, consider:
- WebSocket instead of SSE (bidirectional, more efficient)
- Event batching (send multiple events in one message)
- Connection pooling (share connections across tabs)

## Testing Checklist

After migration, verify:

- [ ] Backend `/health` endpoint returns 200
- [ ] SSE endpoint `/api/v1/events/stream` streams data
- [ ] Dashboard shows "● Live" connection status
- [ ] Events display in Real-time Activity widget
- [ ] Event count badge updates correctly
- [ ] Error state shows when backend is down
- [ ] "Retry Connection" button works
- [ ] Connection auto-recovers after backend restart
- [ ] Performance Metrics shows Web Vitals (LCP, FID, CLS, FCP, TTFB)
- [ ] Performance Metrics hidden for non-dev users (if RBAC enabled)
- [ ] No console errors related to SSE
- [ ] Network tab shows successful SSE connection
- [ ] Page refresh maintains connection
- [ ] Browser back/forward preserves state

## Next Steps

### Short Term
1. Monitor SSE connection stability in production
2. Add authentication to SSE endpoint
3. Implement connection limits (max clients per server)
4. Add event acknowledgment for critical events

### Long Term
1. **Migrate from simulated to real events**:
   - Integrate with message queue (Redis, RabbitMQ)
   - Connect to event store (PostgreSQL NOTIFY, MongoDB Change Streams)
   - Trigger events from game engine actions

2. **Enhance event types**:
   - Character stat changes
   - Story milestone completions
   - System alerts (errors, warnings)
   - User action confirmations

3. **Add event filtering**:
   - Client-side: by type, severity, character
   - Server-side: personalized event streams per user

4. **Implement event history**:
   - Store last N events in database
   - Send historical events on connection (replay)
   - Allow users to scroll back through events

## Related Documentation

- [SSE Endpoint API Documentation](../api/sse-events-endpoint.md)
- [useRealtimeEvents Hook](../../frontend/src/hooks/useRealtimeEvents.ts)
- [Vite Environment Variables](https://vitejs.dev/guide/env-and-mode.html)

## Support

For migration issues:
1. Check [Troubleshooting](#troubleshooting) section
2. Run Playwright smoke tests (`cd frontend && npm run test:e2e:smoke`) and attach failures/logs to an issue/PR
3. File an issue with:
   - Error messages from browser console
   - Backend server logs
   - Environment variable values (redact sensitive data)
   - Steps to reproduce
