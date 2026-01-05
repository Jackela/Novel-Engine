import { useState, useEffect, useRef, useCallback } from 'react';
import { logger } from '@/services/logging/LoggerFactory';

export interface ProgressUpdate {
  generation_id: string;
  progress: number;
  stage: string;
  stage_detail: string;
  estimated_time_remaining: number;
  active_agents: string[];
  timestamp: string;
}

interface UseWebSocketProgressOptions {
  generationId: string | null;
  enabled?: boolean;
  onUpdate?: (update: ProgressUpdate) => void;
  onError?: (error: Error) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

interface WebSocketProgressState {
  isConnected: boolean;
  lastUpdate: ProgressUpdate | null;
  error: string | null;
  connectionAttempts: number;
  connectionQuality: 'excellent' | 'good' | 'poor' | 'unknown';
  lastHeartbeat: number | null;
  messageLatency: number | null;
}

const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY_BASE = 1000; // 1 second base delay
const CONNECTION_TIMEOUT = 10000; // 10 second connection timeout
const HEARTBEAT_INTERVAL = 30000; // 30 second heartbeat

const buildProgressWebSocketUrl = (generationId: string) => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/api/stories/progress/${generationId}`;
};

const resetProgressState = (): WebSocketProgressState => ({
  isConnected: false,
  lastUpdate: null,
  error: null,
  connectionAttempts: 0,
  connectionQuality: 'unknown',
  lastHeartbeat: null,
  messageLatency: null,
});

const updateConnectionQuality = (latency: number): WebSocketProgressState['connectionQuality'] => {
  if (latency < 200) return 'excellent';
  if (latency < 500) return 'good';
  return 'poor';
};

const useProgressState = () => {
  const [state, setState] = useState<WebSocketProgressState>(resetProgressState());
  const stateRef = useRef(state);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  return { state, setState, stateRef };
};

const useProgressMessageSender = (wsRef: React.MutableRefObject<WebSocket | null>) => {
  return useCallback((message: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    }
  }, [wsRef]);
};

const useProgressHeartbeat = (
  wsRef: React.MutableRefObject<WebSocket | null>,
  setState: React.Dispatch<React.SetStateAction<WebSocketProgressState>>
) => {
  const sendHeartbeat = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      setState((prev) => ({ ...prev, lastHeartbeat: Date.now() }));
      wsRef.current.send('ping');
    }
  }, [wsRef, setState]);

  const startHeartbeatMonitoring = useCallback(() => {
    const heartbeatTimer = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        sendHeartbeat();
      }
    }, HEARTBEAT_INTERVAL);

    return () => clearInterval(heartbeatTimer);
  }, [sendHeartbeat, wsRef]);

  return { sendHeartbeat, startHeartbeatMonitoring };
};

const useProgressOpenHandler = (params: {
  isUnmountedRef: React.MutableRefObject<boolean>;
  onConnect?: () => void;
  startHeartbeatMonitoring: () => void;
  setState: React.Dispatch<React.SetStateAction<WebSocketProgressState>>;
}) => {
  const { isUnmountedRef, onConnect, startHeartbeatMonitoring, setState } = params;

  return useCallback(
    (connectionTimer: NodeJS.Timeout) => {
      if (isUnmountedRef.current) return;

      clearTimeout(connectionTimer);

      setState((prev) => ({
        ...prev,
        isConnected: true,
        error: null,
        connectionAttempts: 0,
        connectionQuality: 'excellent',
        lastHeartbeat: Date.now(),
      }));
      onConnect?.();
      startHeartbeatMonitoring();
    },
    [isUnmountedRef, onConnect, setState, startHeartbeatMonitoring]
  );
};

const useProgressMessageHandler = (params: {
  isUnmountedRef: React.MutableRefObject<boolean>;
  stateRef: React.MutableRefObject<WebSocketProgressState>;
  onUpdate?: (update: ProgressUpdate) => void;
  onError?: (error: Error) => void;
  setState: React.Dispatch<React.SetStateAction<WebSocketProgressState>>;
}) => {
  const { isUnmountedRef, stateRef, onUpdate, onError, setState } = params;

  return useCallback(
    (event: MessageEvent) => {
      if (isUnmountedRef.current) return;

      const messageReceiveTime = Date.now();

      try {
        const data = JSON.parse(event.data);

        if (data.type === 'heartbeat') {
          const previousHeartbeat = stateRef.current.lastHeartbeat || messageReceiveTime;
          const latency = messageReceiveTime - previousHeartbeat;
          setState((prev) => ({
            ...prev,
            lastHeartbeat: messageReceiveTime,
            messageLatency: latency,
            connectionQuality: updateConnectionQuality(latency),
          }));
          return;
        }

        const update: ProgressUpdate = data;

        setState((prev) => ({
          ...prev,
          lastUpdate: update,
          error: null,
          lastHeartbeat: messageReceiveTime,
        }));

        onUpdate?.(update);
      } catch (error) {
        logger.error('Failed to parse WebSocket message:', error);
        const parseError = new Error('Failed to parse progress update');
        setState((prev) => ({
          ...prev,
          error: parseError.message,
        }));
        onError?.(parseError);
      }
    },
    [isUnmountedRef, onUpdate, onError, setState, stateRef]
  );
};

const useProgressErrorHandler = (params: {
  isUnmountedRef: React.MutableRefObject<boolean>;
  onError?: (error: Error) => void;
  setState: React.Dispatch<React.SetStateAction<WebSocketProgressState>>;
}) => {
  const { isUnmountedRef, onError, setState } = params;

  return useCallback(
    (error: Event) => {
      if (isUnmountedRef.current) return;

      logger.error('WebSocket error:', error);
      const wsError = new Error('WebSocket connection error');
      setState((prev) => ({
        ...prev,
        error: wsError.message,
        isConnected: false,
      }));
      onError?.(wsError);
    },
    [isUnmountedRef, onError, setState]
  );
};

const useProgressCloseHandler = (params: {
  isUnmountedRef: React.MutableRefObject<boolean>;
  stateRef: React.MutableRefObject<WebSocketProgressState>;
  reconnectTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  connectRef: React.MutableRefObject<() => void>;
  onDisconnect?: () => void;
  setState: React.Dispatch<React.SetStateAction<WebSocketProgressState>>;
}) => {
  const { isUnmountedRef, stateRef, reconnectTimeoutRef, connectRef, onDisconnect, setState } = params;

  return useCallback(
    (event: CloseEvent) => {
      if (isUnmountedRef.current) return;

      setState((prev) => ({
        ...prev,
        isConnected: false,
      }));
      onDisconnect?.();

      if (!event.wasClean && stateRef.current.connectionAttempts < MAX_RECONNECT_ATTEMPTS) {
        const delay = Math.min(
          RECONNECT_DELAY_BASE * Math.pow(1.5, stateRef.current.connectionAttempts),
          10000
        );

        setState((prev) => ({
          ...prev,
          connectionAttempts: prev.connectionAttempts + 1,
        }));

        logger.info(
          `WebSocket reconnecting in ${delay}ms (attempt ${stateRef.current.connectionAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})`
        );

        reconnectTimeoutRef.current = setTimeout(() => {
          if (!isUnmountedRef.current) {
            connectRef.current();
          }
        }, delay);
      } else if (!event.wasClean) {
        setState((prev) => ({
          ...prev,
          error: 'Connection failed after multiple attempts. Please refresh to retry.',
        }));
      }
    },
    [connectRef, isUnmountedRef, onDisconnect, reconnectTimeoutRef, setState, stateRef]
  );
};

const createProgressWebSocketConnection = (params: {
  generationId: string;
  wsRef: React.MutableRefObject<WebSocket | null>;
  handleOpen: (timer: NodeJS.Timeout) => void;
  handleMessage: (event: MessageEvent) => void;
  handleError: (event: Event) => void;
  handleClose: (event: CloseEvent) => void;
  setState: React.Dispatch<React.SetStateAction<WebSocketProgressState>>;
  onError?: (error: Error) => void;
}) => {
  const {
    generationId,
    wsRef,
    handleOpen,
    handleMessage,
    handleError,
    handleClose,
    setState,
    onError,
  } = params;

  if (wsRef.current) {
    wsRef.current.close();
  }

  try {
    const ws = new WebSocket(buildProgressWebSocketUrl(generationId));
    wsRef.current = ws;

    const connectionTimer = setTimeout(() => {
      if (ws.readyState === WebSocket.CONNECTING) {
        ws.close();
        setState((prev) => ({
          ...prev,
          error: 'Connection timeout. Please check your network.',
          connectionQuality: 'poor',
        }));
      }
    }, CONNECTION_TIMEOUT);

    ws.onopen = () => handleOpen(connectionTimer);
    ws.onmessage = handleMessage;
    ws.onerror = handleError;
    ws.onclose = handleClose;
  } catch (error) {
    logger.error('Failed to create WebSocket connection:', error);
    const connectionError = new Error('Failed to establish WebSocket connection');
    setState((prev) => ({
      ...prev,
      error: connectionError.message,
      isConnected: false,
    }));
    onError?.(connectionError);
  }
};

const useProgressConnectionHandlers = (params: {
  generationId: string | null;
  enabled: boolean;
  wsRef: React.MutableRefObject<WebSocket | null>;
  reconnectTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  isUnmountedRef: React.MutableRefObject<boolean>;
  handleOpen: (timer: NodeJS.Timeout) => void;
  handleMessage: (event: MessageEvent) => void;
  handleError: (event: Event) => void;
  handleClose: (event: CloseEvent) => void;
  setState: React.Dispatch<React.SetStateAction<WebSocketProgressState>>;
  onError?: (error: Error) => void;
}) => {
  const {
    generationId,
    enabled,
    wsRef,
    reconnectTimeoutRef,
    isUnmountedRef,
    handleOpen,
    handleMessage,
    handleError,
    handleClose,
    setState,
    onError,
  } = params;

  const connect = useCallback(() => {
    if (!generationId || !enabled || isUnmountedRef.current) {
      return;
    }

    createProgressWebSocketConnection({
      generationId,
      wsRef,
      handleOpen,
      handleMessage,
      handleError,
      handleClose,
      setState,
      onError,
    });
  }, [
    enabled,
    generationId,
    handleClose,
    handleError,
    handleMessage,
    handleOpen,
    isUnmountedRef,
    onError,
    setState,
    wsRef,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Component unmounting');
      wsRef.current = null;
    }

    setState(resetProgressState());
  }, [reconnectTimeoutRef, setState, wsRef]);

  return { connect, disconnect };
};

const useProgressLifecycleEffects = (params: {
  generationId: string | null;
  enabled: boolean;
  connect: () => void;
  disconnect: () => void;
  connectRef: React.MutableRefObject<() => void>;
  isUnmountedRef: React.MutableRefObject<boolean>;
}) => {
  const { generationId, enabled, connect, disconnect, connectRef, isUnmountedRef } = params;

  useEffect(() => {
    connectRef.current = connect;
  }, [connect, connectRef]);

  useEffect(() => {
    if (generationId && enabled) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [connect, disconnect, enabled, generationId]);

  useEffect(() => {
    return () => {
      isUnmountedRef.current = true;
      disconnect();
    };
  }, [disconnect, isUnmountedRef]);
};

const useProgressLifecycle = (params: {
  generationId: string | null;
  enabled: boolean;
  wsRef: React.MutableRefObject<WebSocket | null>;
  reconnectTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  isUnmountedRef: React.MutableRefObject<boolean>;
  connectRef: React.MutableRefObject<() => void>;
  handleOpen: (timer: NodeJS.Timeout) => void;
  handleMessage: (event: MessageEvent) => void;
  handleError: (event: Event) => void;
  handleClose: (event: CloseEvent) => void;
  setState: React.Dispatch<React.SetStateAction<WebSocketProgressState>>;
  onError?: (error: Error) => void;
}) => {
  const {
    generationId,
    enabled,
    wsRef,
    reconnectTimeoutRef,
    isUnmountedRef,
    connectRef,
    handleOpen,
    handleMessage,
    handleError,
    handleClose,
    setState,
    onError,
  } = params;

  const { connect, disconnect } = useProgressConnectionHandlers({
    generationId,
    enabled,
    wsRef,
    reconnectTimeoutRef,
    isUnmountedRef,
    handleOpen,
    handleMessage,
    handleError,
    handleClose,
    setState,
    onError,
  });

  useProgressLifecycleEffects({
    generationId,
    enabled,
    connect,
    disconnect,
    connectRef,
    isUnmountedRef,
  });

  return { connect, disconnect };
};

export function useWebSocketProgress({
  generationId,
  enabled = true,
  onUpdate,
  onError,
  onConnect,
  onDisconnect,
}: UseWebSocketProgressOptions) {
  const { state, setState, stateRef } = useProgressState();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isUnmountedRef = useRef(false);
  const connectRef = useRef<() => void>(() => {});

  const sendMessage = useProgressMessageSender(wsRef);
  const { sendHeartbeat, startHeartbeatMonitoring } = useProgressHeartbeat(wsRef, setState);
  const handleOpen = useProgressOpenHandler({
    isUnmountedRef,
    onConnect,
    startHeartbeatMonitoring,
    setState,
  });
  const handleMessage = useProgressMessageHandler({
    isUnmountedRef,
    stateRef,
    onUpdate,
    onError,
    setState,
  });
  const handleError = useProgressErrorHandler({
    isUnmountedRef,
    onError,
    setState,
  });
  const handleClose = useProgressCloseHandler({
    isUnmountedRef,
    stateRef,
    reconnectTimeoutRef,
    connectRef,
    onDisconnect,
    setState,
  });

  const { connect, disconnect } = useProgressLifecycle({
    generationId,
    enabled,
    wsRef,
    reconnectTimeoutRef,
    isUnmountedRef,
    connectRef,
    handleOpen,
    handleMessage,
    handleError,
    handleClose,
    setState,
    onError,
  });

  return {
    isConnected: state.isConnected,
    lastUpdate: state.lastUpdate,
    error: state.error,
    connectionAttempts: state.connectionAttempts,
    connectionQuality: state.connectionQuality,
    messageLatency: state.messageLatency,
    connect,
    disconnect,
    sendMessage,
    sendHeartbeat,
  };
}
