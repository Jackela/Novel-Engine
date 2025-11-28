import { useEffect, useRef, useState, useCallback } from 'react';
import { logger } from '../services/logging/LoggerFactory';

export interface RealtimeEvent {
  id: string | number;
  type: 'character' | 'story' | 'system' | 'interaction' | 'decision_required' | 'decision_accepted' | 'decision_finalized' | 'negotiation_required';
  title: string;
  description: string;
  timestamp: number;
  characterName?: string;
  severity: 'low' | 'medium' | 'high';
  data?: Record<string, unknown>;
}

export interface DecisionEventData {
  decision_id: string;
  decision_type: string;
  turn_number: number;
  title: string;
  description: string;
  narrative_context: string;
  options: Array<{
    option_id: number;
    label: string;
    description: string;
    icon?: string;
    impact_preview?: string;
    is_default?: boolean;
  }>;
  default_option_id?: number;
  timeout_seconds: number;
  dramatic_tension: number;
  emotional_intensity: number;
  created_at: string;
  expires_at: string;
}

interface UseRealtimeEventsOptions {
  endpoint?: string;
  maxEvents?: number;
  enabled?: boolean;
  /** Maximum reconnection attempts before giving up (default: 10) */
  maxRetries?: number;
  /** Initial reconnection delay in ms (default: 1000) */
  initialRetryDelay?: number;
  /** Maximum reconnection delay in ms (default: 30000) */
  maxRetryDelay?: number;
  /** Heartbeat timeout in ms - reconnect if no message received (default: 60000) */
  heartbeatTimeout?: number;
  /** Callback for decision events (decision_required, negotiation_required, etc.) */
  onDecisionEvent?: (event: RealtimeEvent) => void;
}

type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error' | 'reconnecting';

interface ConnectionStats {
  retryCount: number;
  lastConnectedAt: number | null;
  lastErrorAt: number | null;
  totalReconnections: number;
}

export function useRealtimeEvents({
  endpoint = (import.meta.env.VITE_DASHBOARD_EVENTS_ENDPOINT as string | undefined) ?? '/api/events/stream',
  maxEvents = 50,
  enabled = true,
  maxRetries = 10,
  initialRetryDelay = 1000,
  maxRetryDelay = 30000,
  heartbeatTimeout = 60000,
  onDecisionEvent,
}: UseRealtimeEventsOptions = {}) {
  const [events, setEvents] = useState<RealtimeEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting');
  const [stats, setStats] = useState<ConnectionStats>({
    retryCount: 0,
    lastConnectedAt: null,
    lastErrorAt: null,
    totalReconnections: 0,
  });

  const eventSourceRef = useRef<EventSource | null>(null);
  const eventsBufferRef = useRef<RealtimeEvent[]>([]);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isUnmountedRef = useRef(false);
  const connectionStateRef = useRef<ConnectionState>(connectionState);

  // Calculate exponential backoff delay
  const calculateRetryDelay = useCallback((retryCount: number): number => {
    const delay = Math.min(
      initialRetryDelay * Math.pow(2, retryCount),
      maxRetryDelay
    );
    // Add jitter (10-20% random variance) to prevent thundering herd
    const jitter = delay * (0.1 + Math.random() * 0.1);
    return Math.floor(delay + jitter);
  }, [initialRetryDelay, maxRetryDelay]);

  // Keep connectionStateRef in sync with state
  connectionStateRef.current = connectionState;

  // Reset heartbeat timer on message received
  const resetHeartbeatTimer = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
    }
    heartbeatTimeoutRef.current = setTimeout(() => {
      if (!isUnmountedRef.current && connectionStateRef.current === 'connected') {
        logger.warn('SSE heartbeat timeout - no message received, reconnecting');
        eventSourceRef.current?.close();
        setConnectionState('reconnecting');
      }
    }, heartbeatTimeout);
  }, [heartbeatTimeout]);

  // Create connection with retry logic
  const createConnection = useCallback(() => {
    if (isUnmountedRef.current || !enabled) return;

    // Close existing connection if any
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    setConnectionState(retryCountRef.current > 0 ? 'reconnecting' : 'connecting');

    try {
      const eventSource = new EventSource(endpoint);
      eventSourceRef.current = eventSource;

      // Connection opened successfully
      eventSource.onopen = () => {
        if (isUnmountedRef.current) return;

        const wasReconnection = retryCountRef.current > 0;

        setConnectionState('connected');
        setLoading(false);
        setError(null);

        setStats(prev => ({
          ...prev,
          retryCount: 0,
          lastConnectedAt: Date.now(),
          totalReconnections: wasReconnection ? prev.totalReconnections + 1 : prev.totalReconnections,
        }));

        retryCountRef.current = 0;
        resetHeartbeatTimer();

        logger.info('SSE connection established', {
          endpoint,
          wasReconnection,
        });
      };

      // Receive event messages
      eventSource.onmessage = (event) => {
        if (isUnmountedRef.current) return;

        // Reset heartbeat on any message
        resetHeartbeatTimer();

        try {
          const eventData: RealtimeEvent = JSON.parse(event.data);

          // Validate required fields
          if (!eventData.id || !eventData.type || !eventData.title) {
            logger.warn('Received malformed SSE event, skipping:', { data: event.data });
            return;
          }

          // Handle decision-related events via callback
          const decisionEventTypes = ['decision_required', 'decision_accepted', 'decision_finalized', 'negotiation_required'];
          if (decisionEventTypes.includes(eventData.type) && onDecisionEvent) {
            logger.info('Decision event received:', { type: eventData.type, id: eventData.id });
            onDecisionEvent(eventData);
          }

          // Add to buffer and maintain max size (newest first)
          eventsBufferRef.current = [eventData, ...eventsBufferRef.current].slice(0, maxEvents);
          setEvents([...eventsBufferRef.current]);

        } catch (err) {
          logger.error('Failed to parse SSE event data:', err);
        }
      };

      // Connection error or disconnection
      eventSource.onerror = () => {
        if (isUnmountedRef.current) return;

        // Clear heartbeat timer
        if (heartbeatTimeoutRef.current) {
          clearTimeout(heartbeatTimeoutRef.current);
        }

        eventSource.close();
        eventSourceRef.current = null;

        setStats(prev => ({
          ...prev,
          lastErrorAt: Date.now(),
          retryCount: retryCountRef.current,
        }));

        // Check if we should retry
        if (retryCountRef.current < maxRetries) {
          const delay = calculateRetryDelay(retryCountRef.current);
          retryCountRef.current += 1;

          logger.warn('SSE connection error, scheduling reconnect', {
            retryCount: retryCountRef.current,
            maxRetries,
            delayMs: delay,
          });

          setConnectionState('reconnecting');
          setError(new Error(`Connection lost. Reconnecting (attempt ${retryCountRef.current}/${maxRetries})...`));

          retryTimeoutRef.current = setTimeout(() => {
            if (!isUnmountedRef.current) {
              createConnection();
            }
          }, delay);
        } else {
          // Max retries exceeded
          logger.error(`SSE max retries exceeded (${maxRetries}), giving up - endpoint: ${endpoint}`);

          setConnectionState('error');
          setLoading(false);
          setError(new Error(
            `Failed to connect after ${maxRetries} attempts. Please check your connection and refresh the page.`
          ));
        }
      };

    } catch (err) {
      logger.error(`Failed to create SSE EventSource for ${endpoint}:`, err);
      setConnectionState('error');
      setLoading(false);
      setError(new Error('Failed to initialize event stream connection.'));
    }
  }, [endpoint, enabled, maxRetries, calculateRetryDelay, resetHeartbeatTimer, maxEvents, onDecisionEvent]);

  // Manual reconnect function exposed to consumers
  const reconnect = useCallback(() => {
    retryCountRef.current = 0;
    setError(null);
    createConnection();
  }, [createConnection]);

  useEffect(() => {
    isUnmountedRef.current = false;

    if (!enabled) {
      setLoading(false);
      setConnectionState('disconnected');
      return;
    }

    createConnection();

    // Cleanup on unmount
    return () => {
      isUnmountedRef.current = true;

      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }

      if (heartbeatTimeoutRef.current) {
        clearTimeout(heartbeatTimeoutRef.current);
        heartbeatTimeoutRef.current = null;
      }

      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }

      setConnectionState('disconnected');
    };
  }, [enabled, createConnection]);

  return {
    events,
    loading,
    error,
    connectionState,
    /** Connection statistics for monitoring */
    stats,
    /** Manually trigger reconnection */
    reconnect,
  } as const;
}
