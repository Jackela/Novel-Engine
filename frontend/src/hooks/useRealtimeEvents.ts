import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { logger } from '@/services/logging/LoggerFactory';

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

const DECISION_EVENT_TYPES: ReadonlySet<RealtimeEvent['type']> = new Set([
  'decision_required',
  'decision_accepted',
  'decision_finalized',
  'negotiation_required',
]);

const parseRealtimeEvent = (raw: string): RealtimeEvent | null => {
  try {
    const eventData: RealtimeEvent = JSON.parse(raw);
    if (!eventData.id || !eventData.type || !eventData.title) {
      logger.warn('Received malformed SSE event, skipping:', { data: raw });
      return null;
    }
    return eventData;
  } catch (error) {
    logger.error('Failed to parse SSE event data:', error as Error);
    return null;
  }
};

const pushBufferedEvent = (
  bufferRef: React.MutableRefObject<RealtimeEvent[]>,
  eventData: RealtimeEvent,
  maxEvents: number
) => {
  bufferRef.current = [eventData, ...bufferRef.current].slice(0, maxEvents);
  return bufferRef.current;
};

const updateStatsOnOpen = (
  setStats: React.Dispatch<React.SetStateAction<ConnectionStats>>,
  wasReconnection: boolean
) => {
  setStats(prev => ({
    ...prev,
    retryCount: 0,
    lastConnectedAt: Date.now(),
    totalReconnections: wasReconnection ? prev.totalReconnections + 1 : prev.totalReconnections,
  }));
};

const updateStatsOnError = (
  setStats: React.Dispatch<React.SetStateAction<ConnectionStats>>,
  retryCount: number
) => {
  setStats(prev => ({
    ...prev,
    lastErrorAt: Date.now(),
    retryCount,
  }));
};

const clearTimeoutRef = (ref: React.MutableRefObject<NodeJS.Timeout | null>) => {
  if (ref.current) {
    clearTimeout(ref.current);
    ref.current = null;
  }
};

const closeEventSource = (eventSourceRef: React.MutableRefObject<EventSource | null>) => {
  if (eventSourceRef.current) {
    eventSourceRef.current.close();
    eventSourceRef.current = null;
  }
};

const buildReconnectError = (retryCount: number, maxRetries: number) =>
  new Error(`Connection lost. Reconnecting (attempt ${retryCount}/${maxRetries})...`);

const buildMaxRetryError = (maxRetries: number) =>
  new Error(
    `Failed to connect after ${maxRetries} attempts. Please check your connection and refresh the page.`
  );

const createDecisionHandler = (onDecisionEvent?: (event: RealtimeEvent) => void) => {
  return (eventData: RealtimeEvent) => {
    if (!DECISION_EVENT_TYPES.has(eventData.type) || !onDecisionEvent) {
      return;
    }
    logger.info('Decision event received:', { type: eventData.type, id: eventData.id });
    onDecisionEvent(eventData);
  };
};

const createMessageHandler = (params: {
  isUnmountedRef: React.MutableRefObject<boolean>;
  resetHeartbeatTimer: () => void;
  handleDecisionEvent: (eventData: RealtimeEvent) => void;
  eventsBufferRef: React.MutableRefObject<RealtimeEvent[]>;
  maxEvents: number;
  setEvents: React.Dispatch<React.SetStateAction<RealtimeEvent[]>>;
}) => {
  return (event: MessageEvent) => {
    if (params.isUnmountedRef.current) return;
    params.resetHeartbeatTimer();

    const eventData = parseRealtimeEvent(event.data);
    if (!eventData) return;

    params.handleDecisionEvent(eventData);
    const updated = pushBufferedEvent(params.eventsBufferRef, eventData, params.maxEvents);
    params.setEvents([...updated]);
  };
};

const handleConnectionOpen = (params: {
  isUnmountedRef: React.MutableRefObject<boolean>;
  retryCountRef: React.MutableRefObject<number>;
  setConnectionState: React.Dispatch<React.SetStateAction<ConnectionState>>;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setError: React.Dispatch<React.SetStateAction<Error | null>>;
  setStats: React.Dispatch<React.SetStateAction<ConnectionStats>>;
  resetHeartbeatTimer: () => void;
  endpoint: string;
}) => {
  if (params.isUnmountedRef.current) return;
  const wasReconnection = params.retryCountRef.current > 0;
  params.setConnectionState('connected');
  params.setLoading(false);
  params.setError(null);
  updateStatsOnOpen(params.setStats, wasReconnection);
  params.retryCountRef.current = 0;
  params.resetHeartbeatTimer();
  logger.info('SSE connection established', {
    endpoint: params.endpoint,
    wasReconnection,
  });
};

const scheduleReconnect = (params: {
  retryCountRef: React.MutableRefObject<number>;
  maxRetries: number;
  calculateRetryDelay: (retryCount: number) => number;
  setConnectionState: React.Dispatch<React.SetStateAction<ConnectionState>>;
  setError: React.Dispatch<React.SetStateAction<Error | null>>;
  retryTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  isUnmountedRef: React.MutableRefObject<boolean>;
  createConnection: () => void;
}) => {
  const delay = params.calculateRetryDelay(params.retryCountRef.current);
  params.retryCountRef.current += 1;

  logger.warn('SSE connection error, scheduling reconnect', {
    retryCount: params.retryCountRef.current,
    maxRetries: params.maxRetries,
    delayMs: delay,
  });

  params.setConnectionState('reconnecting');
  params.setError(buildReconnectError(params.retryCountRef.current, params.maxRetries));

  params.retryTimeoutRef.current = setTimeout(() => {
    if (!params.isUnmountedRef.current) {
      params.createConnection();
    }
  }, delay);
};

const handleConnectionError = (params: {
  isUnmountedRef: React.MutableRefObject<boolean>;
  heartbeatTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  eventSourceRef: React.MutableRefObject<EventSource | null>;
  setStats: React.Dispatch<React.SetStateAction<ConnectionStats>>;
  retryCountRef: React.MutableRefObject<number>;
  maxRetries: number;
  calculateRetryDelay: (retryCount: number) => number;
  setConnectionState: React.Dispatch<React.SetStateAction<ConnectionState>>;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setError: React.Dispatch<React.SetStateAction<Error | null>>;
  retryTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  createConnection: () => void;
}) => {
  if (params.isUnmountedRef.current) return;
  clearTimeoutRef(params.heartbeatTimeoutRef);
  closeEventSource(params.eventSourceRef);
  updateStatsOnError(params.setStats, params.retryCountRef.current);

  if (params.retryCountRef.current < params.maxRetries) {
    scheduleReconnect({
      retryCountRef: params.retryCountRef,
      maxRetries: params.maxRetries,
      calculateRetryDelay: params.calculateRetryDelay,
      setConnectionState: params.setConnectionState,
      setError: params.setError,
      retryTimeoutRef: params.retryTimeoutRef,
      isUnmountedRef: params.isUnmountedRef,
      createConnection: params.createConnection,
    });
    return;
  }

  logger.error(`SSE max retries exceeded (${params.maxRetries}), giving up`);
  params.setConnectionState('error');
  params.setLoading(false);
  params.setError(buildMaxRetryError(params.maxRetries));
};

const useRealtimeEventState = () => {
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

  return {
    events,
    setEvents,
    loading,
    setLoading,
    error,
    setError,
    connectionState,
    setConnectionState,
    stats,
    setStats,
    eventSourceRef,
    eventsBufferRef,
    retryCountRef,
    retryTimeoutRef,
    heartbeatTimeoutRef,
    isUnmountedRef,
    connectionStateRef,
  };
};

const useRealtimeEventHandlers = (params: {
  initialRetryDelay: number;
  maxRetryDelay: number;
  heartbeatTimeout: number;
  onDecisionEvent?: (event: RealtimeEvent) => void;
  maxEvents: number;
  setEvents: React.Dispatch<React.SetStateAction<RealtimeEvent[]>>;
  eventsBufferRef: React.MutableRefObject<RealtimeEvent[]>;
  eventSourceRef: React.MutableRefObject<EventSource | null>;
  isUnmountedRef: React.MutableRefObject<boolean>;
  connectionStateRef: React.MutableRefObject<ConnectionState>;
  setConnectionState: React.Dispatch<React.SetStateAction<ConnectionState>>;
  heartbeatTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
}) => {
  const {
    initialRetryDelay,
    maxRetryDelay,
    heartbeatTimeout,
    onDecisionEvent,
    maxEvents,
    setEvents,
    eventsBufferRef,
    eventSourceRef,
    isUnmountedRef,
    connectionStateRef,
    setConnectionState,
    heartbeatTimeoutRef,
  } = params;

  const calculateRetryDelay = useCallback(
    (retryCount: number): number => {
      const delay = Math.min(initialRetryDelay * Math.pow(2, retryCount), maxRetryDelay);
      const jitter = delay * (0.1 + Math.random() * 0.1);
      return Math.floor(delay + jitter);
    },
    [initialRetryDelay, maxRetryDelay]
  );

  const resetHeartbeatTimer = useCallback(() => {
    clearTimeoutRef(heartbeatTimeoutRef);
    heartbeatTimeoutRef.current = setTimeout(() => {
      if (!isUnmountedRef.current && connectionStateRef.current === 'connected') {
        logger.warn('SSE heartbeat timeout - no message received, reconnecting');
        eventSourceRef.current?.close();
        setConnectionState('reconnecting');
      }
    }, heartbeatTimeout);
  }, [
    heartbeatTimeout,
    heartbeatTimeoutRef,
    isUnmountedRef,
    connectionStateRef,
    setConnectionState,
    eventSourceRef,
  ]);

  const handleDecisionEvent = useMemo(() => createDecisionHandler(onDecisionEvent), [onDecisionEvent]);

  const handleMessage = useMemo(
    () =>
      createMessageHandler({
        isUnmountedRef,
        resetHeartbeatTimer,
        handleDecisionEvent,
        eventsBufferRef,
        maxEvents,
        setEvents,
      }),
    [handleDecisionEvent, maxEvents, resetHeartbeatTimer, isUnmountedRef, eventsBufferRef, setEvents]
  );

  return { calculateRetryDelay, resetHeartbeatTimer, handleMessage };
};

const createConnectionErrorHandler = (params: {
  isUnmountedRef: React.MutableRefObject<boolean>;
  heartbeatTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  eventSourceRef: React.MutableRefObject<EventSource | null>;
  setStats: React.Dispatch<React.SetStateAction<ConnectionStats>>;
  retryCountRef: React.MutableRefObject<number>;
  maxRetries: number;
  calculateRetryDelay: (retryCount: number) => number;
  setConnectionState: React.Dispatch<React.SetStateAction<ConnectionState>>;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setError: React.Dispatch<React.SetStateAction<Error | null>>;
  retryTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  reconnect: () => void;
}) => {
  const {
    isUnmountedRef,
    heartbeatTimeoutRef,
    eventSourceRef,
    setStats,
    retryCountRef,
    maxRetries,
    calculateRetryDelay,
    setConnectionState,
    setLoading,
    setError,
    retryTimeoutRef,
    reconnect,
  } = params;

  return () =>
    handleConnectionError({
      isUnmountedRef,
      heartbeatTimeoutRef,
      eventSourceRef,
      setStats,
      retryCountRef,
      maxRetries,
      calculateRetryDelay,
      setConnectionState,
      setLoading,
      setError,
      retryTimeoutRef,
      createConnection: reconnect,
    });
};

const createEventSourceConnection = (params: {
  endpoint: string;
  maxRetries: number;
  calculateRetryDelay: (retryCount: number) => number;
  resetHeartbeatTimer: () => void;
  handleMessage: (event: MessageEvent) => void;
  setConnectionState: React.Dispatch<React.SetStateAction<ConnectionState>>;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setError: React.Dispatch<React.SetStateAction<Error | null>>;
  setStats: React.Dispatch<React.SetStateAction<ConnectionStats>>;
  eventSourceRef: React.MutableRefObject<EventSource | null>;
  retryCountRef: React.MutableRefObject<number>;
  retryTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  heartbeatTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  isUnmountedRef: React.MutableRefObject<boolean>;
  reconnect: () => void;
}) => {
  const {
    endpoint,
    maxRetries,
    calculateRetryDelay,
    resetHeartbeatTimer,
    handleMessage,
    setConnectionState,
    setLoading,
    setError,
    setStats,
    eventSourceRef,
    retryCountRef,
    retryTimeoutRef,
    heartbeatTimeoutRef,
    isUnmountedRef,
    reconnect,
  } = params;

  closeEventSource(eventSourceRef);
  setConnectionState(retryCountRef.current > 0 ? 'reconnecting' : 'connecting');

  try {
    const eventSource = new EventSource(endpoint);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () =>
      handleConnectionOpen({
        isUnmountedRef,
        retryCountRef,
        setConnectionState,
        setLoading,
        setError,
        setStats,
        resetHeartbeatTimer,
        endpoint,
      });

    eventSource.onmessage = handleMessage;

    eventSource.onerror = createConnectionErrorHandler({
      isUnmountedRef,
      heartbeatTimeoutRef,
      eventSourceRef,
      setStats,
      retryCountRef,
      maxRetries,
      calculateRetryDelay,
      setConnectionState,
      setLoading,
      setError,
      retryTimeoutRef,
      reconnect,
    });
  } catch (err) {
    logger.error(`Failed to create SSE EventSource for ${endpoint}:`, err as Error);
    setConnectionState('error');
    setLoading(false);
    setError(new Error('Failed to initialize event stream connection.'));
  }
};

const useEventSourceLifecycle = (params: {
  enabled: boolean;
  createConnection: () => void;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setConnectionState: React.Dispatch<React.SetStateAction<ConnectionState>>;
  retryTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  heartbeatTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  eventSourceRef: React.MutableRefObject<EventSource | null>;
  isUnmountedRef: React.MutableRefObject<boolean>;
}) => {
  const {
    enabled,
    createConnection,
    setLoading,
    setConnectionState,
    retryTimeoutRef,
    heartbeatTimeoutRef,
    eventSourceRef,
    isUnmountedRef,
  } = params;

  useEffect(() => {
    isUnmountedRef.current = false;

    if (!enabled) {
      setLoading(false);
      setConnectionState('disconnected');
      return;
    }

    createConnection();

    return () => {
      isUnmountedRef.current = true;

      clearTimeoutRef(retryTimeoutRef);
      clearTimeoutRef(heartbeatTimeoutRef);
      closeEventSource(eventSourceRef);
      setConnectionState('disconnected');
    };
  }, [
    enabled,
    createConnection,
    setConnectionState,
    setLoading,
    retryTimeoutRef,
    heartbeatTimeoutRef,
    eventSourceRef,
    isUnmountedRef,
  ]);
};

const useEventSourceConnector = (params: {
  enabled: boolean;
  endpoint: string;
  maxRetries: number;
  calculateRetryDelay: (retryCount: number) => number;
  resetHeartbeatTimer: () => void;
  handleMessage: (event: MessageEvent) => void;
  setConnectionState: React.Dispatch<React.SetStateAction<ConnectionState>>;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setError: React.Dispatch<React.SetStateAction<Error | null>>;
  setStats: React.Dispatch<React.SetStateAction<ConnectionStats>>;
  eventSourceRef: React.MutableRefObject<EventSource | null>;
  retryCountRef: React.MutableRefObject<number>;
  retryTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  heartbeatTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  isUnmountedRef: React.MutableRefObject<boolean>;
}) => {
  const {
    enabled,
    endpoint,
    maxRetries,
    calculateRetryDelay,
    resetHeartbeatTimer,
    handleMessage,
    setConnectionState,
    setLoading,
    setError,
    setStats,
    eventSourceRef,
    retryCountRef,
    retryTimeoutRef,
    heartbeatTimeoutRef,
    isUnmountedRef,
  } = params;

  const createConnection = useCallback(() => {
    if (isUnmountedRef.current || !enabled) return;
    createEventSourceConnection({
      endpoint,
      maxRetries,
      calculateRetryDelay,
      resetHeartbeatTimer,
      handleMessage,
      setConnectionState,
      setLoading,
      setError,
      setStats,
      eventSourceRef,
      retryCountRef,
      retryTimeoutRef,
      heartbeatTimeoutRef,
      isUnmountedRef,
      reconnect: createConnection,
    });
  }, [
    calculateRetryDelay,
    enabled,
    endpoint,
    handleMessage,
    heartbeatTimeoutRef,
    isUnmountedRef,
    maxRetries,
    resetHeartbeatTimer,
    retryCountRef,
    retryTimeoutRef,
    setConnectionState,
    setError,
    setLoading,
    setStats,
    eventSourceRef,
  ]);

  return createConnection;
};

const useRealtimeEventsConnection = (params: {
  enabled: boolean;
  endpoint: string;
  maxRetries: number;
  calculateRetryDelay: (retryCount: number) => number;
  resetHeartbeatTimer: () => void;
  handleMessage: (event: MessageEvent) => void;
  setConnectionState: React.Dispatch<React.SetStateAction<ConnectionState>>;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  setError: React.Dispatch<React.SetStateAction<Error | null>>;
  setStats: React.Dispatch<React.SetStateAction<ConnectionStats>>;
  eventSourceRef: React.MutableRefObject<EventSource | null>;
  retryCountRef: React.MutableRefObject<number>;
  retryTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  heartbeatTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  isUnmountedRef: React.MutableRefObject<boolean>;
}) => {
  const {
    enabled,
    endpoint,
    maxRetries,
    calculateRetryDelay,
    resetHeartbeatTimer,
    handleMessage,
    setConnectionState,
    setLoading,
    setError,
    setStats,
    eventSourceRef,
    retryCountRef,
    retryTimeoutRef,
    heartbeatTimeoutRef,
    isUnmountedRef,
  } = params;

  const createConnection = useEventSourceConnector({
    enabled,
    endpoint,
    maxRetries,
    calculateRetryDelay,
    resetHeartbeatTimer,
    handleMessage,
    setConnectionState,
    setLoading,
    setError,
    setStats,
    eventSourceRef,
    retryCountRef,
    retryTimeoutRef,
    heartbeatTimeoutRef,
    isUnmountedRef,
  });

  const reconnect = useCallback(() => {
    retryCountRef.current = 0;
    setError(null);
    createConnection();
  }, [createConnection, retryCountRef, setError]);

  useEventSourceLifecycle({
    enabled,
    createConnection,
    setLoading,
    setConnectionState,
    retryTimeoutRef,
    heartbeatTimeoutRef,
    eventSourceRef,
    isUnmountedRef,
  });

  return { reconnect };
};

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
  const {
    events,
    setEvents,
    loading,
    setLoading,
    error,
    setError,
    connectionState,
    setConnectionState,
    stats,
    setStats,
    eventSourceRef,
    eventsBufferRef,
    retryCountRef,
    retryTimeoutRef,
    heartbeatTimeoutRef,
    isUnmountedRef,
    connectionStateRef,
  } = useRealtimeEventState();

  connectionStateRef.current = connectionState;

  const { calculateRetryDelay, resetHeartbeatTimer, handleMessage } = useRealtimeEventHandlers({
    initialRetryDelay,
    maxRetryDelay,
    heartbeatTimeout,
    onDecisionEvent,
    maxEvents,
    setEvents,
    eventsBufferRef,
    eventSourceRef,
    isUnmountedRef,
    connectionStateRef,
    setConnectionState,
    heartbeatTimeoutRef,
  });

  const { reconnect } = useRealtimeEventsConnection({
    enabled,
    endpoint,
    maxRetries,
    calculateRetryDelay,
    resetHeartbeatTimer,
    handleMessage,
    setConnectionState,
    setLoading,
    setError,
    setStats,
    eventSourceRef,
    retryCountRef,
    retryTimeoutRef,
    heartbeatTimeoutRef,
    isUnmountedRef,
  });

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
