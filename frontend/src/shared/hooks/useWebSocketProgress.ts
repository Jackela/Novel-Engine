/**
 * useWebSocketProgress - WebSocket connection for generation progress
 * Features: connection quality monitoring, auto-reconnect
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

interface ProgressUpdate {
  taskId: string;
  progress: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  message?: string;
  metadata?: Record<string, unknown>;
}

interface UseWebSocketProgressOptions {
  url: string;
  taskId?: string;
  onProgress?: (update: ProgressUpdate) => void;
  onComplete?: (taskId: string) => void;
  onError?: (error: Error) => void;
  enabled?: boolean;
  maxRetries?: number;
}

interface ConnectionQuality {
  latency: number;
  status: 'excellent' | 'good' | 'poor' | 'disconnected';
}

interface UseWebSocketProgressReturn {
  isConnected: boolean;
  connectionQuality: ConnectionQuality;
  currentProgress: ProgressUpdate | null;
  reconnect: () => void;
  disconnect: () => void;
}

const getReconnectDelay = (retryCount: number) =>
  Math.min(1000 * Math.pow(2, retryCount), 30000);

const getLatencyStatus = (latency: number): ConnectionQuality['status'] => {
  if (latency < 100) return 'excellent';
  if (latency < 300) return 'good';
  return 'poor';
};

const buildProgressUpdate = (
  data: Record<string, unknown>,
  taskId?: string
): ProgressUpdate => ({
  taskId: typeof data.taskId === 'string' ? data.taskId : (taskId ?? ''),
  progress: typeof data.progress === 'number' ? data.progress : 0,
  status: (data.status as ProgressUpdate['status']) ?? 'running',
  ...(typeof data.message === 'string' ? { message: data.message } : {}),
  ...(data.metadata && typeof data.metadata === 'object'
    ? { metadata: data.metadata as Record<string, unknown> }
    : {}),
});

const handleProgressPayload = (
  data: Record<string, unknown>,
  taskId: string | undefined,
  setCurrentProgress: Dispatch<SetStateAction<ProgressUpdate | null>>,
  onProgress?: (update: ProgressUpdate) => void,
  onComplete?: (taskId: string) => void
) => {
  if (data.type !== 'progress' && data.progress === undefined) {
    return;
  }
  const update = buildProgressUpdate(data, taskId);
  setCurrentProgress(update);
  onProgress?.(update);
  if (update.status === 'completed') {
    onComplete?.(update.taskId);
  }
};

const attachWebSocketHandlers = (params: {
  ws: WebSocket;
  taskId?: string | undefined;
  setIsConnected: Dispatch<SetStateAction<boolean>>;
  setConnectionQuality: Dispatch<SetStateAction<ConnectionQuality>>;
  setCurrentProgress: Dispatch<SetStateAction<ProgressUpdate | null>>;
  onProgress?: ((update: ProgressUpdate) => void) | undefined;
  onComplete?: ((taskId: string) => void) | undefined;
  onError?: ((error: Error) => void) | undefined;
  measureLatency: () => void;
  lastPingRef: MutableRefObject<number>;
  pingIntervalRef: MutableRefObject<number | null>;
  scheduleReconnect: () => void;
  wsRef: MutableRefObject<WebSocket | null>;
  retryCountRef: MutableRefObject<number>;
}) => {
  const {
    ws,
    taskId,
    setIsConnected,
    setConnectionQuality,
    setCurrentProgress,
    onProgress,
    onComplete,
    onError,
    measureLatency,
    lastPingRef,
    pingIntervalRef,
    scheduleReconnect,
    wsRef,
    retryCountRef,
  } = params;

  ws.onopen = () => {
    setIsConnected(true);
    retryCountRef.current = 0;
    setConnectionQuality({ latency: 0, status: 'excellent' });
    pingIntervalRef.current = window.setInterval(measureLatency, 5000);
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as Record<string, unknown>;
      if (data.type === 'pong') {
        const latency = Date.now() - lastPingRef.current;
        setConnectionQuality({ latency, status: getLatencyStatus(latency) });
        return;
      }
      handleProgressPayload(data, taskId, setCurrentProgress, onProgress, onComplete);
    } catch {
      // Ignore non-JSON messages
    }
  };

  ws.onerror = (event) => {
    onError?.(new Error('WebSocket error: ' + (event as ErrorEvent).message));
    if (ws.readyState !== WebSocket.CLOSING && ws.readyState !== WebSocket.CLOSED) {
      ws.close();
    }
  };

  ws.onclose = () => {
    setIsConnected(false);
    setConnectionQuality({ latency: 0, status: 'disconnected' });
    wsRef.current = null;
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    scheduleReconnect();
  };
};

const disconnectSocket = (params: {
  manualCloseRef: MutableRefObject<boolean>;
  pingIntervalRef: MutableRefObject<number | null>;
  retryTimeoutRef: MutableRefObject<number | null>;
  wsRef: MutableRefObject<WebSocket | null>;
  setIsConnected: Dispatch<SetStateAction<boolean>>;
  setConnectionQuality: Dispatch<SetStateAction<ConnectionQuality>>;
}) => {
  const {
    manualCloseRef,
    pingIntervalRef,
    retryTimeoutRef,
    wsRef,
    setIsConnected,
    setConnectionQuality,
  } = params;

  manualCloseRef.current = true;
  if (pingIntervalRef.current) {
    clearInterval(pingIntervalRef.current);
    pingIntervalRef.current = null;
  }
  if (retryTimeoutRef.current) {
    clearTimeout(retryTimeoutRef.current);
    retryTimeoutRef.current = null;
  }
  if (wsRef.current) {
    wsRef.current.close();
    wsRef.current = null;
  }
  setIsConnected(false);
  setConnectionQuality({ latency: 0, status: 'disconnected' });
};

const scheduleSocketReconnect = (params: {
  enabled: boolean;
  maxRetries: number;
  manualCloseRef: MutableRefObject<boolean>;
  retryCountRef: MutableRefObject<number>;
  retryTimeoutRef: MutableRefObject<number | null>;
  connectRef: MutableRefObject<() => void>;
}) => {
  const {
    enabled,
    maxRetries,
    manualCloseRef,
    retryCountRef,
    retryTimeoutRef,
    connectRef,
  } = params;
  if (!enabled || manualCloseRef.current) {
    return;
  }
  if (retryCountRef.current < maxRetries) {
    const delay = getReconnectDelay(retryCountRef.current);
    retryCountRef.current += 1;
    retryTimeoutRef.current = window.setTimeout(() => {
      connectRef.current();
    }, delay);
  }
};

const measureSocketLatency = (params: {
  lastPingRef: MutableRefObject<number>;
  wsRef: MutableRefObject<WebSocket | null>;
}) => {
  const { lastPingRef, wsRef } = params;
  if (wsRef.current?.readyState === WebSocket.OPEN) {
    lastPingRef.current = Date.now();
    wsRef.current.send(JSON.stringify({ type: 'ping' }));
  }
};

const connectSocket = (params: {
  url: string;
  taskId?: string | undefined;
  enabled: boolean;
  onProgress?: ((update: ProgressUpdate) => void) | undefined;
  onComplete?: ((taskId: string) => void) | undefined;
  onError?: ((error: Error) => void) | undefined;
  setIsConnected: Dispatch<SetStateAction<boolean>>;
  setConnectionQuality: Dispatch<SetStateAction<ConnectionQuality>>;
  setCurrentProgress: Dispatch<SetStateAction<ProgressUpdate | null>>;
  scheduleReconnect: () => void;
  measureLatency: () => void;
  lastPingRef: MutableRefObject<number>;
  pingIntervalRef: MutableRefObject<number | null>;
  retryCountRef: MutableRefObject<number>;
  wsRef: MutableRefObject<WebSocket | null>;
  manualCloseRef: MutableRefObject<boolean>;
}) => {
  const {
    url,
    taskId,
    enabled,
    onProgress,
    onComplete,
    onError,
    setIsConnected,
    setConnectionQuality,
    setCurrentProgress,
    scheduleReconnect,
    measureLatency,
    lastPingRef,
    pingIntervalRef,
    retryCountRef,
    wsRef,
    manualCloseRef,
  } = params;

  if (!enabled || wsRef.current) return;

  try {
    manualCloseRef.current = false;
    const wsUrl = taskId ? `${url}?taskId=${taskId}` : url;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    attachWebSocketHandlers({
      ws,
      taskId,
      setIsConnected,
      setConnectionQuality,
      setCurrentProgress,
      onProgress,
      onComplete,
      onError,
      measureLatency,
      lastPingRef,
      pingIntervalRef,
      scheduleReconnect,
      wsRef,
      retryCountRef,
    });
  } catch (error) {
    onError?.(error as Error);
  }
};

const useWebSocketDisconnect = (params: {
  manualCloseRef: MutableRefObject<boolean>;
  pingIntervalRef: MutableRefObject<number | null>;
  retryTimeoutRef: MutableRefObject<number | null>;
  wsRef: MutableRefObject<WebSocket | null>;
  setIsConnected: Dispatch<SetStateAction<boolean>>;
  setConnectionQuality: Dispatch<SetStateAction<ConnectionQuality>>;
}) =>
  useCallback(() => {
    disconnectSocket(params);
  }, [params]);

const useWebSocketScheduleReconnect = (params: {
  enabled: boolean;
  maxRetries: number;
  manualCloseRef: MutableRefObject<boolean>;
  retryCountRef: MutableRefObject<number>;
  retryTimeoutRef: MutableRefObject<number | null>;
  connectRef: MutableRefObject<() => void>;
}) =>
  useCallback(() => {
    scheduleSocketReconnect(params);
  }, [params]);

const useWebSocketLatency = (params: {
  lastPingRef: MutableRefObject<number>;
  wsRef: MutableRefObject<WebSocket | null>;
}) =>
  useCallback(() => {
    measureSocketLatency(params);
  }, [params]);

const useWebSocketConnect = (params: {
  url: string;
  taskId?: string | undefined;
  enabled: boolean;
  onProgress?: ((update: ProgressUpdate) => void) | undefined;
  onComplete?: ((taskId: string) => void) | undefined;
  onError?: ((error: Error) => void) | undefined;
  setIsConnected: Dispatch<SetStateAction<boolean>>;
  setConnectionQuality: Dispatch<SetStateAction<ConnectionQuality>>;
  setCurrentProgress: Dispatch<SetStateAction<ProgressUpdate | null>>;
  scheduleReconnect: () => void;
  measureLatency: () => void;
  lastPingRef: MutableRefObject<number>;
  pingIntervalRef: MutableRefObject<number | null>;
  retryCountRef: MutableRefObject<number>;
  wsRef: MutableRefObject<WebSocket | null>;
  manualCloseRef: MutableRefObject<boolean>;
}) =>
  useCallback(() => {
    connectSocket(params);
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

const useWebSocketState = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [currentProgress, setCurrentProgress] = useState<ProgressUpdate | null>(null);
  const [connectionQuality, setConnectionQuality] = useState<ConnectionQuality>({
    latency: 0,
    status: 'disconnected',
  });

  const wsRef = useRef<WebSocket | null>(null);
  const pingIntervalRef = useRef<number | null>(null);
  const lastPingRef = useRef<number>(0);
  const retryCountRef = useRef(0);
  const retryTimeoutRef = useRef<number | null>(null);
  const manualCloseRef = useRef(false);
  const connectRef = useRef<() => void>(() => {});

  return {
    isConnected,
    setIsConnected,
    currentProgress,
    setCurrentProgress,
    connectionQuality,
    setConnectionQuality,
    wsRef,
    pingIntervalRef,
    lastPingRef,
    retryCountRef,
    retryTimeoutRef,
    manualCloseRef,
    connectRef,
  };
};

const useWebSocketLifecycle = (params: {
  url: string;
  taskId?: string | undefined;
  enabled: boolean;
  onProgress?: ((update: ProgressUpdate) => void) | undefined;
  onComplete?: ((taskId: string) => void) | undefined;
  onError?: ((error: Error) => void) | undefined;
  maxRetries: number;
  setIsConnected: Dispatch<SetStateAction<boolean>>;
  setCurrentProgress: Dispatch<SetStateAction<ProgressUpdate | null>>;
  setConnectionQuality: Dispatch<SetStateAction<ConnectionQuality>>;
  wsRef: MutableRefObject<WebSocket | null>;
  pingIntervalRef: MutableRefObject<number | null>;
  lastPingRef: MutableRefObject<number>;
  retryCountRef: MutableRefObject<number>;
  retryTimeoutRef: MutableRefObject<number | null>;
  manualCloseRef: MutableRefObject<boolean>;
  connectRef: MutableRefObject<() => void>;
}) => {
  const {
    url,
    taskId,
    enabled,
    onProgress,
    onComplete,
    onError,
    maxRetries,
    setIsConnected,
    setCurrentProgress,
    setConnectionQuality,
    wsRef,
    pingIntervalRef,
    lastPingRef,
    retryCountRef,
    retryTimeoutRef,
    manualCloseRef,
    connectRef,
  } = params;

  const disconnect = useWebSocketDisconnect({
    manualCloseRef,
    pingIntervalRef,
    retryTimeoutRef,
    wsRef,
    setIsConnected,
    setConnectionQuality,
  });

  const scheduleReconnect = useWebSocketScheduleReconnect({
    enabled,
    maxRetries,
    manualCloseRef,
    retryCountRef,
    retryTimeoutRef,
    connectRef,
  });

  const measureLatency = useWebSocketLatency({ lastPingRef, wsRef });

  const connect = useWebSocketConnect({
    url,
    taskId,
    enabled,
    onProgress,
    onComplete,
    onError,
    setIsConnected,
    setConnectionQuality,
    setCurrentProgress,
    scheduleReconnect,
    measureLatency,
    lastPingRef,
    pingIntervalRef,
    retryCountRef,
    wsRef,
    manualCloseRef,
  });

  useConnectRefEffect(connect, connectRef);

  const reconnect = useReconnectHandler(disconnect, connect, retryCountRef);

  useAutoConnectEffect(enabled, connect, disconnect);

  return { disconnect, reconnect };
};

export function useWebSocketProgress({
  url,
  taskId,
  onProgress,
  onComplete,
  onError,
  enabled = true,
  maxRetries = 5,
}: UseWebSocketProgressOptions): UseWebSocketProgressReturn {
  const {
    isConnected,
    setIsConnected,
    currentProgress,
    setCurrentProgress,
    connectionQuality,
    setConnectionQuality,
    wsRef,
    pingIntervalRef,
    lastPingRef,
    retryCountRef,
    retryTimeoutRef,
    manualCloseRef,
    connectRef,
  } = useWebSocketState();

  const { disconnect, reconnect } = useWebSocketLifecycle({
    url,
    taskId,
    enabled,
    onProgress,
    onComplete,
    onError,
    maxRetries,
    setIsConnected,
    setCurrentProgress,
    setConnectionQuality,
    wsRef,
    pingIntervalRef,
    lastPingRef,
    retryCountRef,
    retryTimeoutRef,
    manualCloseRef,
    connectRef,
  });

  return {
    isConnected,
    connectionQuality,
    currentProgress,
    reconnect,
    disconnect,
  };
}
