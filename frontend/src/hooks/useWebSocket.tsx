/**
 * WebSocket Hook for Real-time Novel Engine Communication
 * =====================================================
 *
 * Advanced React hook for managing WebSocket connections with:
 * - Automatic reconnection with exponential backoff
 * - Message queuing and deduplication
 * - Connection state management
 * - Error handling and recovery
 * - Performance optimization
 */

/* eslint-disable react-refresh/only-export-components */
import React, { useEffect, useRef, useCallback, useState } from 'react';
import { usePerformanceOptimizer } from './usePerformanceOptimizer';
import { logger } from '@/services/logging/LoggerFactory';

// Types
export interface WebSocketMessage {
  id: string;
  type: string;
  data: unknown;
  timestamp: number;
  priority: 'low' | 'normal' | 'high' | 'critical';
}

export interface WebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  lastError: Error | null;
  reconnectAttempts: number;
  messageQueue: WebSocketMessage[];
  latency: number;
}

export interface WebSocketOptions {
  url: string;
  protocols?: string[];
  maxReconnectAttempts?: number;
  reconnectInterval?: number;
  maxReconnectInterval?: number;
  heartbeatInterval?: number;
  messageQueueSize?: number;
  enableCompression?: boolean;
  enableMessageDeduplication?: boolean;
}

export interface WebSocketHookResult {
  state: WebSocketState;
  sendMessage: (message: Omit<WebSocketMessage, 'id' | 'timestamp'>) => void;
  connect: () => void;
  disconnect: () => void;
  clearQueue: () => void;
  getConnectionHealth: () => ConnectionHealth;
}

interface ConnectionHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  latency: number;
  uptime: number;
  messagesSent: number;
  messagesReceived: number;
  errorsCount: number;
}

const createInitialWebSocketState = (): WebSocketState => ({
  isConnected: false,
  isConnecting: false,
  lastError: null,
  reconnectAttempts: 0,
  messageQueue: [],
  latency: 0,
});

const buildMessageId = () => `msg_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;

const sortMessageQueue = (queue: WebSocketMessage[]) => {
  const priorityOrder = { critical: 0, high: 1, normal: 2, low: 3 };
  return [...queue].sort((a, b) => {
    const priorityDiff = priorityOrder[a.priority] - priorityOrder[b.priority];
    return priorityDiff !== 0 ? priorityDiff : a.timestamp - b.timestamp;
  });
};

const useWebSocketState = () => {
  const [state, setState] = useState<WebSocketState>(createInitialWebSocketState());
  const stateRef = useRef(state);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  return { state, setState, stateRef };
};

const useMessageDeduplication = (params: {
  enableMessageDeduplication: boolean;
  messageHistoryRef: React.MutableRefObject<Set<string>>;
}) => {
  const { enableMessageDeduplication, messageHistoryRef } = params;

  return useCallback(
    (messageId: string): boolean => {
      if (!enableMessageDeduplication) return false;

      if (messageHistoryRef.current.has(messageId)) {
        return true;
      }

      messageHistoryRef.current.add(messageId);
      if (messageHistoryRef.current.size > 1000) {
        const oldestMessages = Array.from(messageHistoryRef.current).slice(0, 500);
        oldestMessages.forEach((id) => messageHistoryRef.current.delete(id));
      }

      return false;
    },
    [enableMessageDeduplication, messageHistoryRef]
  );
};

const useReconnectDelay = (params: {
  reconnectInterval: number;
  maxReconnectInterval: number;
}) => {
  const { reconnectInterval, maxReconnectInterval } = params;

  return useCallback(
    (attempt: number): number => {
      const delay = Math.min(reconnectInterval * Math.pow(2, attempt), maxReconnectInterval);
      return delay + Math.random() * 1000;
    },
    [reconnectInterval, maxReconnectInterval]
  );
};

const useHeartbeatSender = (params: {
  wsRef: React.MutableRefObject<WebSocket | null>;
  statsRef: React.MutableRefObject<{
    messagesSent: number;
    messagesReceived: number;
    errorsCount: number;
    lastPingTime: number;
    lastPongTime: number;
  }>;
}) => {
  const { wsRef, statsRef } = params;

  return useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const pingTime = Date.now();
      statsRef.current.lastPingTime = pingTime;

      wsRef.current.send(JSON.stringify({
        id: `heartbeat_${pingTime}`,
        type: 'ping',
        data: { timestamp: pingTime },
        priority: 'normal',
        timestamp: pingTime,
      }));
    }
  }, [wsRef, statsRef]);
};

const useQueueProcessor = (params: {
  wsRef: React.MutableRefObject<WebSocket | null>;
  enableCompression: boolean;
  setState: React.Dispatch<React.SetStateAction<WebSocketState>>;
  statsRef: React.MutableRefObject<{
    messagesSent: number;
    messagesReceived: number;
    errorsCount: number;
    lastPingTime: number;
    lastPongTime: number;
  }>;
}) => {
  const { wsRef, enableCompression, setState, statsRef } = params;

  return useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    setState((prevState) => {
      const queue = sortMessageQueue(prevState.messageQueue);

      for (const message of queue) {
        try {
          const messageString = enableCompression
            ? JSON.stringify(message)
            : JSON.stringify(message);

          wsRef.current!.send(messageString);
          statsRef.current.messagesSent++;
        } catch (error) {
          logger.error('Failed to send queued message:', error);
          statsRef.current.errorsCount++;
        }
      }

      return {
        ...prevState,
        messageQueue: [],
      };
    });
  }, [wsRef, enableCompression, setState, statsRef]);
};

const useWebSocketMessageHandler = (params: {
  statsRef: React.MutableRefObject<{
    messagesSent: number;
    messagesReceived: number;
    errorsCount: number;
    lastPingTime: number;
    lastPongTime: number;
  }>;
  isDuplicateMessage: (messageId: string) => boolean;
  setState: React.Dispatch<React.SetStateAction<WebSocketState>>;
}) => {
  const { statsRef, isDuplicateMessage, setState } = params;

  return useCallback(
    (event: MessageEvent) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);

        if (isDuplicateMessage(message.id)) {
          return;
        }

        if (message.type === 'pong') {
          statsRef.current.lastPongTime = Date.now();
          const latency = statsRef.current.lastPongTime - statsRef.current.lastPingTime;
          setState((prevState) => ({
            ...prevState,
            latency,
          }));
          return;
        }

        statsRef.current.messagesReceived++;

        window.dispatchEvent(new CustomEvent('websocket-message', {
          detail: message,
        }));
      } catch (error) {
        logger.error('Failed to parse WebSocket message:', error);
        statsRef.current.errorsCount++;
      }
    },
    [isDuplicateMessage, setState, statsRef]
  );
};

const useWebSocketOpenHandler = (params: {
  connectionStartTime: React.MutableRefObject<number>;
  heartbeatInterval: number;
  heartbeatIntervalRef: React.MutableRefObject<NodeJS.Timeout | null>;
  optimizeForRealTime: () => void;
  sendHeartbeat: () => void;
  processMessageQueue: () => void;
  setState: React.Dispatch<React.SetStateAction<WebSocketState>>;
}) => {
  const {
    connectionStartTime,
    heartbeatInterval,
    heartbeatIntervalRef,
    optimizeForRealTime,
    sendHeartbeat,
    processMessageQueue,
    setState,
  } = params;

  return useCallback(() => {
    logger.info('WebSocket connected');
    connectionStartTime.current = Date.now();

    setState((prevState) => ({
      ...prevState,
      isConnected: true,
      isConnecting: false,
      lastError: null,
      reconnectAttempts: 0,
    }));

    processMessageQueue();

    if (heartbeatInterval > 0) {
      heartbeatIntervalRef.current = setInterval(sendHeartbeat, heartbeatInterval);
    }

    optimizeForRealTime();
  }, [
    connectionStartTime,
    setState,
    processMessageQueue,
    heartbeatInterval,
    heartbeatIntervalRef,
    sendHeartbeat,
    optimizeForRealTime,
  ]);
};

const useWebSocketCloseHandler = (params: {
  getReconnectDelay: (attempt: number) => number;
  maxReconnectAttempts: number;
  heartbeatIntervalRef: React.MutableRefObject<NodeJS.Timeout | null>;
  reconnectTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  stateRef: React.MutableRefObject<WebSocketState>;
  connectRef: React.MutableRefObject<() => void>;
  setState: React.Dispatch<React.SetStateAction<WebSocketState>>;
}) => {
  const {
    getReconnectDelay,
    maxReconnectAttempts,
    heartbeatIntervalRef,
    reconnectTimeoutRef,
    stateRef,
    connectRef,
    setState,
  } = params;

  return useCallback(
    (event: CloseEvent) => {
      logger.info('WebSocket closed:', event.code, event.reason);

      setState((prevState) => ({
        ...prevState,
        isConnected: false,
        isConnecting: false,
      }));

      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }

      const attempts = stateRef.current.reconnectAttempts;
      if (event.code !== 1000 && attempts < maxReconnectAttempts) {
        const delay = getReconnectDelay(attempts);

        logger.info(`Reconnecting in ${delay}ms (attempt ${attempts + 1}/${maxReconnectAttempts})`);

        reconnectTimeoutRef.current = setTimeout(() => {
          setState((prevState) => ({
            ...prevState,
            reconnectAttempts: prevState.reconnectAttempts + 1,
            isConnecting: true,
          }));
          connectRef.current();
        }, delay);
      }
    },
    [
      getReconnectDelay,
      heartbeatIntervalRef,
      maxReconnectAttempts,
      reconnectTimeoutRef,
      setState,
      stateRef,
      connectRef,
    ]
  );
};

const useWebSocketErrorHandler = (params: {
  statsRef: React.MutableRefObject<{
    messagesSent: number;
    messagesReceived: number;
    errorsCount: number;
    lastPingTime: number;
    lastPongTime: number;
  }>;
  setState: React.Dispatch<React.SetStateAction<WebSocketState>>;
}) => {
  const { statsRef, setState } = params;

  return useCallback(
    (event: Event) => {
      logger.error('WebSocket error:', event);
      statsRef.current.errorsCount++;

      setState((prevState) => ({
        ...prevState,
        lastError: new Error('WebSocket connection error'),
        isConnecting: false,
      }));
    },
    [setState, statsRef]
  );
};

const useWebSocketLifecycle = (params: {
  url: string;
  protocols: string[];
  wsRef: React.MutableRefObject<WebSocket | null>;
  reconnectTimeoutRef: React.MutableRefObject<NodeJS.Timeout | null>;
  heartbeatIntervalRef: React.MutableRefObject<NodeJS.Timeout | null>;
  connectRef: React.MutableRefObject<() => void>;
  handleOpen: () => void;
  handleClose: (event: CloseEvent) => void;
  handleError: (event: Event) => void;
  handleMessage: (event: MessageEvent) => void;
  setState: React.Dispatch<React.SetStateAction<WebSocketState>>;
}) => {
  const {
    url,
    protocols,
    wsRef,
    reconnectTimeoutRef,
    heartbeatIntervalRef,
    connectRef,
    handleOpen,
    handleClose,
    handleError,
    handleMessage,
    setState,
  } = params;

  const connect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      setState((prevState) => ({
        ...prevState,
        isConnecting: true,
        lastError: null,
      }));

      const ws = new WebSocket(url, protocols);

      ws.onopen = handleOpen;
      ws.onclose = handleClose;
      ws.onerror = handleError;
      ws.onmessage = handleMessage;

      wsRef.current = ws;
    } catch (error) {
      logger.error('Failed to create WebSocket connection:', error);
      setState((prevState) => ({
        ...prevState,
        lastError: error as Error,
        isConnecting: false,
      }));
    }
  }, [url, protocols, wsRef, handleOpen, handleClose, handleError, handleMessage, setState]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setState((prevState) => ({
      ...prevState,
      isConnected: false,
      isConnecting: false,
      reconnectAttempts: 0,
    }));
  }, [reconnectTimeoutRef, heartbeatIntervalRef, wsRef, setState]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect, connectRef]);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { connect, disconnect };
};

const useWebSocketMessaging = (params: {
  wsRef: React.MutableRefObject<WebSocket | null>;
  statsRef: React.MutableRefObject<{
    messagesSent: number;
    messagesReceived: number;
    errorsCount: number;
    lastPingTime: number;
    lastPongTime: number;
  }>;
  enableCompression: boolean;
  messageQueueSize: number;
  setState: React.Dispatch<React.SetStateAction<WebSocketState>>;
}) => {
  const { wsRef, statsRef, enableCompression, messageQueueSize, setState } = params;

  const sendMessage = useCallback(
    (message: Omit<WebSocketMessage, 'id' | 'timestamp'>) => {
      const fullMessage: WebSocketMessage = {
        id: buildMessageId(),
        timestamp: Date.now(),
        ...message,
      };

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        try {
          const messageString = enableCompression
            ? JSON.stringify(fullMessage)
            : JSON.stringify(fullMessage);

          wsRef.current.send(messageString);
          statsRef.current.messagesSent++;
        } catch (error) {
          logger.error('Failed to send message:', error);
          statsRef.current.errorsCount++;

          setState((prevState) => ({
            ...prevState,
            messageQueue: [...prevState.messageQueue, fullMessage].slice(-messageQueueSize),
          }));
        }
      } else {
        setState((prevState) => ({
          ...prevState,
          messageQueue: [...prevState.messageQueue, fullMessage].slice(-messageQueueSize),
        }));
      }
    },
    [enableCompression, messageQueueSize, setState, wsRef, statsRef]
  );

  const clearQueue = useCallback(() => {
    setState((prevState) => ({
      ...prevState,
      messageQueue: [],
    }));
  }, [setState]);

  return { sendMessage, clearQueue };
};

const useWebSocketHealth = (params: {
  state: WebSocketState;
  connectionStartTime: React.MutableRefObject<number>;
  statsRef: React.MutableRefObject<{
    messagesSent: number;
    messagesReceived: number;
    errorsCount: number;
    lastPingTime: number;
    lastPongTime: number;
  }>;
}) => {
  const { state, connectionStartTime, statsRef } = params;

  return useCallback((): ConnectionHealth => {
    const now = Date.now();
    const uptime = now - connectionStartTime.current;

    let status: 'healthy' | 'degraded' | 'unhealthy' = 'healthy';

    if (!state.isConnected) {
      status = 'unhealthy';
    } else if (state.latency > 1000 || statsRef.current.errorsCount > 10) {
      status = 'degraded';
    }

    return {
      status,
      latency: state.latency,
      uptime,
      messagesSent: statsRef.current.messagesSent,
      messagesReceived: statsRef.current.messagesReceived,
      errorsCount: statsRef.current.errorsCount,
    };
  }, [state.isConnected, state.latency, connectionStartTime, statsRef]);
};

const useWebSocketResources = () => {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const messageHistoryRef = useRef<Set<string>>(new Set());
  const connectionStartTime = useRef<number>(Date.now());
  const connectRef = useRef<() => void>(() => {});
  const statsRef = useRef({
    messagesSent: 0,
    messagesReceived: 0,
    errorsCount: 0,
    lastPingTime: 0,
    lastPongTime: 0,
  });

  return {
    wsRef,
    reconnectTimeoutRef,
    heartbeatIntervalRef,
    messageHistoryRef,
    connectionStartTime,
    connectRef,
    statsRef,
  };
};

// WebSocket hook implementation
export const useWebSocket = (options: WebSocketOptions): WebSocketHookResult => {
  const {
    url,
    protocols = [],
    maxReconnectAttempts = 10,
    reconnectInterval = 1000,
    maxReconnectInterval = 30000,
    heartbeatInterval = 30000,
    messageQueueSize = 1000,
    enableCompression = true,
    enableMessageDeduplication = true
  } = options;

  // Performance optimization hook
  const { optimizeForRealTime } = usePerformanceOptimizer();

  const {
    wsRef,
    reconnectTimeoutRef,
    heartbeatIntervalRef,
    messageHistoryRef,
    connectionStartTime,
    connectRef,
    statsRef,
  } = useWebSocketResources();

  const { state, setState, stateRef } = useWebSocketState();
  const isDuplicateMessage = useMessageDeduplication({
    enableMessageDeduplication,
    messageHistoryRef,
  });
  const getReconnectDelay = useReconnectDelay({ reconnectInterval, maxReconnectInterval });
  const sendHeartbeat = useHeartbeatSender({ wsRef, statsRef });
  const processMessageQueue = useQueueProcessor({ wsRef, enableCompression, setState, statsRef });
  const handleMessage = useWebSocketMessageHandler({ statsRef, isDuplicateMessage, setState });
  const handleOpen = useWebSocketOpenHandler({
    connectionStartTime,
    heartbeatInterval,
    heartbeatIntervalRef,
    optimizeForRealTime,
    sendHeartbeat,
    processMessageQueue,
    setState,
  });
  const handleClose = useWebSocketCloseHandler({
    getReconnectDelay,
    maxReconnectAttempts,
    heartbeatIntervalRef,
    reconnectTimeoutRef,
    stateRef,
    connectRef,
    setState,
  });
  const handleError = useWebSocketErrorHandler({ statsRef, setState });

  const { connect, disconnect } = useWebSocketLifecycle({
    url,
    protocols,
    wsRef,
    reconnectTimeoutRef,
    heartbeatIntervalRef,
    connectRef,
    handleOpen,
    handleClose,
    handleError,
    handleMessage,
    setState,
  });

  const { sendMessage, clearQueue } = useWebSocketMessaging({
    wsRef,
    statsRef,
    enableCompression,
    messageQueueSize,
    setState,
  });

  const getConnectionHealth = useWebSocketHealth({ state, connectionStartTime, statsRef });

  return {
    state,
    sendMessage,
    connect,
    disconnect,
    clearQueue,
    getConnectionHealth
  };
};

// WebSocket context for sharing connection across components
export const WebSocketContext = React.createContext<WebSocketHookResult | null>(null);

export const WebSocketProvider: React.FC<{
  children: React.ReactNode;
  options: WebSocketOptions;
}> = ({ children, options }) => {
  const webSocket = useWebSocket(options);

  return (
    <WebSocketContext.Provider value={webSocket}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocketContext = (): WebSocketHookResult => {
  const context = React.useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within WebSocketProvider');
  }
  return context;
};
