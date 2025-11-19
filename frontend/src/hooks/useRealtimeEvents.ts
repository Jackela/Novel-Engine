import { useEffect, useRef, useState } from 'react';

export interface RealtimeEvent {
  id: string | number;
  type: 'character' | 'story' | 'system' | 'interaction';
  title: string;
  description: string;
  timestamp: number;
  characterName?: string;
  severity: 'low' | 'medium' | 'high';
}

interface UseRealtimeEventsOptions {
  endpoint?: string;
  maxEvents?: number;
  enabled?: boolean;
}

type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

export function useRealtimeEvents({
  endpoint = (import.meta.env.VITE_DASHBOARD_EVENTS_ENDPOINT as string | undefined) ?? '/api/events/stream',
  maxEvents = 50,
  enabled = true,
}: UseRealtimeEventsOptions = {}) {
  const [events, setEvents] = useState<RealtimeEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting');

  const eventSourceRef = useRef<EventSource | null>(null);
  const eventsBufferRef = useRef<RealtimeEvent[]>([]);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      setConnectionState('disconnected');
      return;
    }

    // Create EventSource connection for Server-Sent Events
    const eventSource = new EventSource(endpoint);
    eventSourceRef.current = eventSource;

    // Connection opened successfully
    eventSource.onopen = () => {
      setConnectionState('connected');
      setLoading(false);
      setError(null);
    };

    // Receive event messages
    eventSource.onmessage = (event) => {
      try {
        const eventData: RealtimeEvent = JSON.parse(event.data);

        // Validate required fields
        if (!eventData.id || !eventData.type || !eventData.title) {
          console.warn('Received malformed event, skipping:', event.data);
          return;
        }

        // Add to buffer and maintain max size (newest first)
        eventsBufferRef.current = [eventData, ...eventsBufferRef.current].slice(0, maxEvents);
        setEvents([...eventsBufferRef.current]);

      } catch (err) {
        console.error('Failed to parse event data:', err, event.data);
      }
    };

    // Connection error or disconnection
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
  }, [endpoint, maxEvents, enabled]);

  return { events, loading, error, connectionState } as const;
}
