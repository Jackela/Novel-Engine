/**
 * useRealtimeEvents - SSE connection for real-time narrative events
 * Features: exponential backoff reconnect, heartbeat detection
 */
import { useEffect, useRef, useCallback, useState } from 'react';

interface RealtimeEvent {
  type: string;
  data: unknown;
  timestamp: number;
}

interface UseRealtimeEventsOptions {
  url: string;
  onEvent?: (event: RealtimeEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
  enabled?: boolean;
  maxRetries?: number;
  heartbeatInterval?: number;
}

interface UseRealtimeEventsReturn {
  isConnected: boolean;
  lastEvent: RealtimeEvent | null;
  reconnect: () => void;
  disconnect: () => void;
}

export function useRealtimeEvents({
  url,
  onEvent,
  onConnect,
  onDisconnect,
  onError,
  enabled = true,
  maxRetries = 5,
  heartbeatInterval = 30000,
}: UseRealtimeEventsOptions): UseRealtimeEventsReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<RealtimeEvent | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<number | null>(null);
  const heartbeatTimeoutRef = useRef<number | null>(null);

  const clearTimeouts = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  const disconnect = useCallback(() => {
    clearTimeouts();
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
    onDisconnect?.();
  }, [clearTimeouts, onDisconnect]);

  const resetHeartbeat = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
    }
    heartbeatTimeoutRef.current = window.setTimeout(() => {
      // No heartbeat received, reconnect
      disconnect();
      retryCountRef.current = 0;
    }, heartbeatInterval * 2);
  }, [heartbeatInterval, disconnect]);

  const connect = useCallback(() => {
    if (!enabled || eventSourceRef.current) return;

    try {
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        retryCountRef.current = 0;
        resetHeartbeat();
        onConnect?.();
      };

      eventSource.onmessage = (event) => {
        resetHeartbeat();

        try {
          const data = JSON.parse(event.data);
          const realtimeEvent: RealtimeEvent = {
            type: data.type || 'message',
            data: data.data || data,
            timestamp: Date.now(),
          };

          setLastEvent(realtimeEvent);
          onEvent?.(realtimeEvent);
        } catch {
          // Handle non-JSON messages (like heartbeats)
          if (event.data === 'heartbeat' || event.data === 'ping') {
            return;
          }
          onEvent?.({
            type: 'raw',
            data: event.data,
            timestamp: Date.now(),
          });
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        eventSourceRef.current = null;
        setIsConnected(false);

        if (retryCountRef.current < maxRetries) {
          const delay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
          retryCountRef.current++;

          retryTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, delay);
        } else {
          onError?.(new Error('Max reconnection attempts reached'));
          onDisconnect?.();
        }
      };
    } catch (error) {
      onError?.(error as Error);
    }
  }, [url, enabled, maxRetries, onEvent, onConnect, onDisconnect, onError, resetHeartbeat]);

  const reconnect = useCallback(() => {
    disconnect();
    retryCountRef.current = 0;
    connect();
  }, [disconnect, connect]);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    isConnected,
    lastEvent,
    reconnect,
    disconnect,
  };
}
