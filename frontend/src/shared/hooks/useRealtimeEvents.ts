/**
 * useRealtimeEvents - SSE connection for real-time narrative events
 * Features: exponential backoff reconnect, heartbeat detection
 */
import {
  useEffect,
  useRef,
  useCallback,
  useState,
  type Dispatch,
  type SetStateAction,
  type MutableRefObject,
} from 'react';

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

const getReconnectDelay = (retryCount: number) =>
  Math.min(1000 * Math.pow(2, retryCount), 30000);

const isHeartbeat = (data: string) => data === 'heartbeat' || data === 'ping';

const parseRealtimeEvent = (payload: string): RealtimeEvent | null => {
  try {
    const data = JSON.parse(payload) as Record<string, unknown>;
    return {
      type: typeof data.type === 'string' ? data.type : 'message',
      data: 'data' in data ? data.data : data,
      timestamp: Date.now(),
    };
  } catch {
    if (isHeartbeat(payload)) {
      return null;
    }
    return {
      type: 'raw',
      data: payload,
      timestamp: Date.now(),
    };
  }
};

const attachEventSourceHandlers = (params: {
  eventSource: EventSource;
  setIsConnected: Dispatch<SetStateAction<boolean>>;
  setLastEvent: Dispatch<SetStateAction<RealtimeEvent | null>>;
  onEvent?: ((event: RealtimeEvent) => void) | undefined;
  onConnect?: (() => void) | undefined;
  resetHeartbeat: () => void;
  scheduleReconnect: () => void;
  onError?: ((error: Error) => void) | undefined;
  eventSourceRef: MutableRefObject<EventSource | null>;
}) => {
  const {
    eventSource,
    setIsConnected,
    setLastEvent,
    onEvent,
    onConnect,
    resetHeartbeat,
    scheduleReconnect,
    onError,
    eventSourceRef,
  } = params;

  eventSource.onopen = () => {
    setIsConnected(true);
    resetHeartbeat();
    onConnect?.();
  };

  eventSource.onmessage = (event) => {
    resetHeartbeat();
    const realtimeEvent = parseRealtimeEvent(event.data);
    if (!realtimeEvent) {
      return;
    }
    setLastEvent(realtimeEvent);
    onEvent?.(realtimeEvent);
  };

  eventSource.onerror = () => {
    onError?.(new Error('EventSource connection error'));
    eventSource.close();
    eventSourceRef.current = null;
    setIsConnected(false);
    scheduleReconnect();
  };
};

const useEventSourceState = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<RealtimeEvent | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<number | null>(null);
  const heartbeatTimeoutRef = useRef<number | null>(null);
  const connectRef = useRef<() => void>(() => {});

  return {
    isConnected,
    setIsConnected,
    lastEvent,
    setLastEvent,
    eventSourceRef,
    retryCountRef,
    retryTimeoutRef,
    heartbeatTimeoutRef,
    connectRef,
  };
};

const useEventSourceTimers = (params: {
  enabled: boolean;
  maxRetries: number;
  heartbeatInterval: number;
  onDisconnect?: (() => void) | undefined;
  onError?: ((error: Error) => void) | undefined;
  retryCountRef: MutableRefObject<number>;
  retryTimeoutRef: MutableRefObject<number | null>;
  heartbeatTimeoutRef: MutableRefObject<number | null>;
  connectRef: MutableRefObject<() => void>;
  onHeartbeatTimeout: () => void;
}) => {
  const {
    enabled,
    maxRetries,
    heartbeatInterval,
    onDisconnect,
    onError,
    retryCountRef,
    retryTimeoutRef,
    heartbeatTimeoutRef,
    connectRef,
    onHeartbeatTimeout,
  } = params;

  const clearTimeouts = useCallback(() => {
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, [retryTimeoutRef, heartbeatTimeoutRef]);

  const scheduleReconnect = useCallback(() => {
    if (!enabled) {
      return;
    }

    if (retryCountRef.current < maxRetries) {
      const delay = getReconnectDelay(retryCountRef.current);
      retryCountRef.current += 1;
      retryTimeoutRef.current = window.setTimeout(() => {
        connectRef.current();
      }, delay);
    } else {
      onError?.(new Error('Max reconnection attempts reached'));
      onDisconnect?.();
    }
  }, [
    enabled,
    maxRetries,
    onError,
    onDisconnect,
    retryCountRef,
    retryTimeoutRef,
    connectRef,
  ]);

  const resetHeartbeat = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current);
    }
    heartbeatTimeoutRef.current = window.setTimeout(() => {
      onHeartbeatTimeout();
    }, heartbeatInterval * 2);
  }, [heartbeatInterval, heartbeatTimeoutRef, onHeartbeatTimeout]);

  return { clearTimeouts, scheduleReconnect, resetHeartbeat };
};

const useEventSourceDisconnect = (params: {
  clearTimeouts: () => void;
  eventSourceRef: MutableRefObject<EventSource | null>;
  setIsConnected: Dispatch<SetStateAction<boolean>>;
  onDisconnect?: (() => void) | undefined;
}) =>
  useCallback(() => {
    const { clearTimeouts, eventSourceRef, setIsConnected, onDisconnect } = params;
    clearTimeouts();
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
    onDisconnect?.();
  }, [params]);

const useEventSourceConnect = (params: {
  url: string;
  enabled: boolean;
  onEvent?: ((event: RealtimeEvent) => void) | undefined;
  onConnect?: (() => void) | undefined;
  onError?: ((error: Error) => void) | undefined;
  setIsConnected: Dispatch<SetStateAction<boolean>>;
  setLastEvent: Dispatch<SetStateAction<RealtimeEvent | null>>;
  eventSourceRef: MutableRefObject<EventSource | null>;
  retryCountRef: MutableRefObject<number>;
  resetHeartbeat: () => void;
  scheduleReconnect: () => void;
}) =>
  useCallback(() => {
    const {
      url,
      enabled,
      onEvent,
      onConnect,
      onError,
      setIsConnected,
      setLastEvent,
      eventSourceRef,
      retryCountRef,
      resetHeartbeat,
      scheduleReconnect,
    } = params;
    if (!enabled || eventSourceRef.current) return;

    try {
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;
      retryCountRef.current = 0;
      attachEventSourceHandlers({
        eventSource,
        setIsConnected,
        setLastEvent,
        onEvent,
        onConnect,
        resetHeartbeat,
        scheduleReconnect,
        onError,
        eventSourceRef,
      });
    } catch (error) {
      onError?.(error as Error);
    }
  }, [params]);

const useConnectRefEffect = (
  connect: () => void,
  connectRef: MutableRefObject<() => void>
) => {
  useEffect(() => {
    connectRef.current = connect;
  }, [connect, connectRef]);
};

const useReconnectHandler = (
  disconnect: () => void,
  connect: () => void,
  retryCountRef: MutableRefObject<number>
) =>
  useCallback(() => {
    disconnect();
    retryCountRef.current = 0;
    connect();
  }, [connect, disconnect, retryCountRef]);

const useAutoConnectEffect = (
  enabled: boolean,
  connect: () => void,
  disconnect: () => void
) => {
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
};

const useEventSourceLifecycle = (params: {
  url: string;
  enabled: boolean;
  onEvent?: ((event: RealtimeEvent) => void) | undefined;
  onConnect?: (() => void) | undefined;
  onDisconnect?: (() => void) | undefined;
  onError?: ((error: Error) => void) | undefined;
  setIsConnected: Dispatch<SetStateAction<boolean>>;
  setLastEvent: Dispatch<SetStateAction<RealtimeEvent | null>>;
  eventSourceRef: MutableRefObject<EventSource | null>;
  retryCountRef: MutableRefObject<number>;
  connectRef: MutableRefObject<() => void>;
  clearTimeouts: () => void;
  scheduleReconnect: () => void;
  resetHeartbeat: () => void;
}) => {
  const {
    url,
    enabled,
    onEvent,
    onConnect,
    onDisconnect,
    onError,
    setIsConnected,
    setLastEvent,
    eventSourceRef,
    retryCountRef,
    connectRef,
    clearTimeouts,
    scheduleReconnect,
    resetHeartbeat,
  } = params;

  const disconnect = useEventSourceDisconnect({
    clearTimeouts,
    eventSourceRef,
    setIsConnected,
    onDisconnect,
  });

  const connect = useEventSourceConnect({
    url,
    enabled,
    onEvent,
    onConnect,
    onError,
    setIsConnected,
    setLastEvent,
    eventSourceRef,
    retryCountRef,
    resetHeartbeat,
    scheduleReconnect,
  });

  useConnectRefEffect(connect, connectRef);

  const reconnect = useReconnectHandler(disconnect, connect, retryCountRef);

  useAutoConnectEffect(enabled, connect, disconnect);

  return { disconnect, reconnect };
};

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
  const {
    isConnected,
    setIsConnected,
    lastEvent,
    setLastEvent,
    eventSourceRef,
    retryCountRef,
    retryTimeoutRef,
    heartbeatTimeoutRef,
    connectRef,
  } = useEventSourceState();

  const handleHeartbeatTimeout = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setIsConnected(false);
    onDisconnect?.();
    retryCountRef.current = 0;
    if (enabled) {
      connectRef.current();
    }
  }, [
    connectRef,
    enabled,
    eventSourceRef,
    onDisconnect,
    retryCountRef,
    setIsConnected,
  ]);

  const { clearTimeouts, scheduleReconnect, resetHeartbeat } = useEventSourceTimers({
    enabled,
    maxRetries,
    heartbeatInterval,
    onDisconnect,
    onError,
    retryCountRef,
    retryTimeoutRef,
    heartbeatTimeoutRef,
    connectRef,
    onHeartbeatTimeout: handleHeartbeatTimeout,
  });

  const { disconnect, reconnect } = useEventSourceLifecycle({
    url,
    enabled,
    onEvent,
    onConnect,
    onDisconnect,
    onError,
    setIsConnected,
    setLastEvent,
    eventSourceRef,
    retryCountRef,
    connectRef,
    clearTimeouts,
    scheduleReconnect,
    resetHeartbeat,
  });

  return {
    isConnected,
    lastEvent,
    reconnect,
    disconnect,
  };
}
